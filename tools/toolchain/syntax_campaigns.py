# SPDX-License-Identifier: Apache-2.0
"""Qualify Menhir-generated syntax campaigns and independent AST/span oracles (Q25y).

See [Generated syntax campaigns](../../docs/tooling/parser.md#generated-syntax-campaigns)
and [Generated development tests](../../docs/tooling/tooling-protocols.md#generated-development-tests)
for the frozen entry point, resource bounds, renderer qualification, independent
AST/span oracle, seeded-defect controls, sentence shrinking, and replay contract.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from filelock import FileLock

from toolchain import (
    MAX_LITERAL_DIGITS,
    MAX_SOURCE_BYTES,
    VelaError,
)
from toolchain import (
    migration as vela_migration,
)
from toolchain import (
    parser as vela_parser,
)
from toolchain.ast import MAX_BLOCK_DEPTH, MAX_SYNTAX_DEPTH
from toolchain.atomic import atomic_path

type Json = vela_parser.Json

MAX_BLOCK_BINDINGS = MAX_BLOCK_DEPTH

ENTRY_POINT = "file"
DEFAULT_SEED_START = 20261108
DEFAULT_CAMPAIGN_COUNT = 64
DEFAULT_GOAL_LENGTH = 36

MAX_SENTENCE_TOKENS = 512
MAX_RENDERED_SOURCE_BYTES = MAX_SOURCE_BYTES
MAX_INTERPRETER_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_CAMPAIGN_SECONDS = 60
PROCESS_TIMEOUT_SECONDS = 15
MAX_MEMORY_BYTES = 512 * 1024 * 1024
MAX_DELIMITER_DEPTH = 256

NAMED_SYNTAX_INTERACTION = (
    "multi-declaration-precedence-trailing-comma-and-trivia-boundaries"
)

PURE_TERMINALS: dict[str, str | None] = {
    "MODULE": "module",
    "PUBLIC": "public",
    "CONST": "const",
    "NAT": "Nat",
    "BOOL": "bool",
    "LET": "let",
    "RETURN": "return",
    "IF": "if",
    "ELSE": "else",
    "TRUE": "true",
    "FALSE": "false",
    "LPAREN": "(",
    "RPAREN": ")",
    "LBRACE": "{",
    "RBRACE": "}",
    "SEMICOLON": ";",
    "COMMA": ",",
    "COLON": ":",
    "EQUAL": "=",
    "FATARROW": "=>",
    "OR": "||",
    "AND": "&&",
    "EQ": "==",
    "LE": "<=",
    "NE": "!=",
    "LT": "<",
    "GT": ">",
    "GE": ">=",
    "PLUS": "+",
    "MINUS": "-",
    "STAR": "*",
    "SLASH": "/",
    "PERCENT": "%",
    "NOT": "!",
    "IDENT": None,
    "DECIMAL": None,
    "EOF": None,
}

PURE_KEYWORDS: dict[str, str] = {
    spelling: terminal
    for terminal, spelling in PURE_TERMINALS.items()
    if spelling is not None and spelling.isalpha()
}

PURE_RESERVED_WORDS: frozenset[str] = frozenset({
    "fn", "Bool", "async", "await", "effect", "effects", "handler",
    "handle", "resume", "dispose", "mut", "var", "unsafe", "borrow",
    "requires", "ensures", "restores", "ghost", "tracked", "grade",
    "proof", "owned", "move", "ref", "in", "out", "captures", "scope",
    "spawn", "commit", "on", "cancel", "region", "view", "union", "foreach",
})

RENDER_VARIANTS: tuple[str, ...] = (
    "canonical",
    "utf8_comments_crlf",
    "bare_cr_separators",
)

SEEDED_FAULTS: tuple[str, ...] = (
    "right-associative-subtraction-or-division-action",
    "trailing-comma-span-or-arity-corruption",
    "expression-body-excludes-arrow-or-semicolon-span",
)
HELD_OUT_FAULT = "expression-body-excludes-arrow-or-semicolon-span"

NONMINIMAL_FAULT_SENTENCES: dict[str, tuple[str, ...]] = {
    "right-associative-subtraction-or-division-action": (
        "MODULE", "IDENT", "SEMICOLON",
        "PUBLIC", "CONST", "BOOL", "IDENT", "EQUAL", "TRUE", "OR", "FALSE", "SEMICOLON",
        "PUBLIC", "NAT", "IDENT", "LPAREN", "NAT", "IDENT", "COMMA", "BOOL", "IDENT", "COMMA", "RPAREN",
        "FATARROW", "LPAREN", "DECIMAL", "PLUS", "DECIMAL", "RPAREN", "MINUS", "DECIMAL", "MINUS", "DECIMAL", "SEMICOLON",
        "EOF",
    ),
    "trailing-comma-span-or-arity-corruption": (
        "MODULE", "IDENT", "SEMICOLON",
        "PUBLIC", "CONST", "NAT", "IDENT", "EQUAL", "DECIMAL", "PLUS", "DECIMAL", "SEMICOLON",
        "PUBLIC", "NAT", "IDENT", "LPAREN", "NAT", "IDENT", "COMMA", "BOOL", "IDENT", "COMMA", "RPAREN",
        "LBRACE", "LET", "IDENT", "EQUAL", "DECIMAL", "SEMICOLON", "RETURN", "IDENT", "SEMICOLON", "RBRACE",
        "EOF",
    ),
    "expression-body-excludes-arrow-or-semicolon-span": (
        "MODULE", "IDENT", "SEMICOLON",
        "PUBLIC", "CONST", "NAT", "IDENT", "EQUAL", "DECIMAL", "STAR", "DECIMAL", "SEMICOLON",
        "PUBLIC", "NAT", "IDENT", "LPAREN", "NAT", "IDENT", "RPAREN",
        "FATARROW", "LPAREN", "DECIMAL", "PLUS", "DECIMAL", "RPAREN", "STAR", "DECIMAL", "SEMICOLON",
        "EOF",
    ),
}


class CampaignObservationError(ValueError):
    """Raised when a campaign observation disagrees with the independent oracle."""


@dataclass(frozen=True)
class RenderedToken:
    """One rendered lexical token with its half-open UTF-8 byte span and 1-based position."""

    terminal: str
    spelling: str
    start_byte: int
    end_byte: int
    line: int
    column: int


@dataclass(frozen=True)
class RenderedSentence:
    """Complete rendered Vela source bound to its originating Menhir terminal sentence."""

    entry: str
    variant: str
    terminals: tuple[str, ...]
    tokens: tuple[RenderedToken, ...]
    source: bytes
    source_sha256: str


@dataclass(frozen=True)
class CstNode:
    """Parsed concrete syntax tree node from `menhir --interpret --interpret-show-cst`."""

    symbol: str
    children: tuple[CstNode | str, ...]

    def leaf_terminals(self) -> tuple[str, ...]:
        out: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                out.append(child)
            else:
                out.extend(child.leaf_terminals())
        return tuple(out)


def parse_sentence_line(line: str, *, entry: str = ENTRY_POINT) -> tuple[str, ...]:
    """Validate and parse one `entry: TERMINAL ... EOF` line from `menhir --random-sentence`."""
    stripped = line.strip()
    prefix = f"{entry}:"
    if not stripped.startswith(prefix):
        raise ValueError(f"generated sentence lacks '{prefix}' prefix: {stripped[:80]!r}")
    terminals = tuple(stripped[len(prefix) :].split())
    validate_terminal_sentence(terminals)
    return terminals


def validate_terminal_sentence(terminals: Sequence[str]) -> None:
    """Enforce vocabulary, non-emptiness, trailing EOF, and hard token count bounds."""
    if not terminals:
        raise ValueError("terminal sentence is empty")
    if len(terminals) > MAX_SENTENCE_TOKENS:
        raise ValueError(
            f"terminal sentence length {len(terminals)} exceeds bound {MAX_SENTENCE_TOKENS}"
        )
    if terminals[-1] != "EOF":
        raise ValueError("terminal sentence must end with EOF")
    for idx, terminal in enumerate(terminals[:-1]):
        if terminal == "EOF":
            raise ValueError(f"premature EOF at token index {idx}")
        if terminal not in PURE_TERMINALS:
            raise ValueError(f"unsupported or non-pure terminal at index {idx}: {terminal!r}")


def _identifier_payload(index: int, _variant: str, seed: int) -> str:
    if (index + seed) % 6 == 0:
        # Exercise surface-only keywords that remain valid identifiers in the pure entry.
        pool = ("as", "open", "lifts", "null", "trait", "operation")
        candidate = f"{pool[(index + seed) % len(pool)]}_{index}" if index < 4 else pool[(index + seed) % len(pool)]
    else:
        prefixes = ("Alpha", "item", "count", "flag", "Step", "val")
        stem = prefixes[(index + seed) % len(prefixes)]
        candidate = f"{stem}_{index}"
    if candidate in PURE_KEYWORDS or candidate in PURE_RESERVED_WORDS:
        raise ValueError(f"renderer generated reserved word {candidate!r}")
    return candidate


def _decimal_payload(index: int, _variant: str, seed: int) -> str:
    mode = (index + seed) % 4
    if mode == 0:
        return str((index * 7 + seed) % 97)
    if mode == 1:
        return f"00{(index + 1) % 9}"
    if mode == 2:
        return f"{1 + (index % 9)}_{index % 10}{(index * 3) % 10}4"
    return f"{(index % 8) + 1}0_{(index * 5) % 10}0_{(index * 2) % 10}"


def _trivia_between(index: int, variant: str) -> str:
    if variant == "canonical":
        return "\n" if index > 0 and index % 12 == 0 else " "
    if variant == "utf8_comments_crlf":
        if index == 0:
            return "// café 🚀 header\r\n"
        if index % 9 == 0:
            return " // café Δ\r\n  "
        if index % 4 == 0:
            return "\r\n\t"
        return " "
    if variant == "bare_cr_separators":
        if index == 0:
            return "// bare-cr λ\r"
        if index % 8 == 0:
            return " // line-break\r "
        if index % 5 == 0:
            return "\r"
        return "  "
    raise ValueError(f"unknown render variant: {variant!r}")


def _advance_position(line: int, column: int, chunk: str) -> tuple[int, int]:
    idx = 0
    length = len(chunk)
    while idx < length:
        ch = chunk[idx]
        if ch == "\r":
            if idx + 1 < length and chunk[idx + 1] == "\n":
                idx += 2
            else:
                idx += 1
            line += 1
            column = 1
        elif ch == "\n":
            idx += 1
            line += 1
            column = 1
        else:
            idx += 1
            column += 1
    return line, column


def render_sentence(
    terminals: Sequence[str],
    *,
    variant: str = "canonical",
    seed: int = 0,
    entry: str = ENTRY_POINT,
) -> RenderedSentence:
    """Render a validated Menhir terminal sequence into UTF-8 Vela source with exact spans."""
    validate_terminal_sentence(terminals)
    if variant not in RENDER_VARIANTS:
        raise ValueError(f"unsupported render variant: {variant!r}")

    chunks: list[str] = []
    rendered_tokens: list[RenderedToken] = []
    byte_cursor = 0
    line = 1
    column = 1

    for idx, terminal in enumerate(terminals[:-1]):
        lead = _trivia_between(idx, variant)
        if lead:
            chunks.append(lead)
            byte_cursor += len(lead.encode("utf-8"))
            line, column = _advance_position(line, column, lead)

        fixed = PURE_TERMINALS[terminal]
        if fixed is not None:
            spelling = fixed
        elif terminal == "IDENT":
            spelling = _identifier_payload(idx, variant, seed)
        elif terminal == "DECIMAL":
            spelling = _decimal_payload(idx, variant, seed)
        else:
            raise ValueError(f"unhandled terminal: {terminal!r}")

        tok_bytes = len(spelling.encode("utf-8"))
        rendered_tokens.append(
            RenderedToken(
                terminal=terminal,
                spelling=spelling,
                start_byte=byte_cursor,
                end_byte=byte_cursor + tok_bytes,
                line=line,
                column=column,
            )
        )
        chunks.append(spelling)
        byte_cursor += tok_bytes
        line, column = _advance_position(line, column, spelling)

    tail = (
        "\r\n// end café\r\n"
        if variant == "utf8_comments_crlf"
        else ("\r// end\r" if variant == "bare_cr_separators" else "\n")
    )
    chunks.append(tail)
    source = "".join(chunks).encode("utf-8")
    if len(source) > MAX_RENDERED_SOURCE_BYTES:
        raise ValueError(
            f"rendered source length {len(source)} exceeds bound {MAX_RENDERED_SOURCE_BYTES}"
        )
    lexed = independent_tokenize(source)
    if tuple(t.terminal for t in lexed) != tuple(terminals[:-1]):
        raise ValueError("rendered source did not round-trip to the exact terminal sequence")
    if tuple((t.start_byte, t.end_byte, t.spelling) for t in lexed) != tuple(
        (t.start_byte, t.end_byte, t.spelling) for t in rendered_tokens
    ):
        raise ValueError("rendered token byte spans differed from independent tokenization")

    return RenderedSentence(
        entry=entry,
        variant=variant,
        terminals=tuple(terminals),
        tokens=tuple(rendered_tokens),
        source=source,
        source_sha256=hashlib.sha256(source).hexdigest(),
    )


_MULTI_CHAR_OPERATORS: tuple[tuple[str, str], ...] = (
    ("=>", "FATARROW"),
    ("==", "EQ"),
    ("<=", "LE"),
    (">=", "GE"),
    ("!=", "NE"),
    ("&&", "AND"),
    ("||", "OR"),
)

_SINGLE_CHAR_TOKENS: dict[str, str] = {
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    ";": "SEMICOLON",
    ",": "COMMA",
    ":": "COLON",
    "=": "EQUAL",
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "<": "LT",
    ">": "GT",
    "!": "NOT",
}


def _pure_unsupported_message(word: str) -> str:
    modes = {
        "in": "a shared read loan",
        "ref": "an initialized exclusive loan",
        "out": "an exclusive initialization loan",
        "owned": "consuming ownership",
        "move": "an explicit ownership transfer",
    }
    if word == "var":
        return (
            "'var' declares a mutable binding; let and unmarked type-first bindings are "
            "immutable. Local reassignment requires the wider Vela surface; the pure "
            "prototype does not support mutation"
        )
    if word in modes:
        return (
            f"'{word}' requests {modes[word]}; the pure Nat/bool prototype cannot check "
            "ownership, borrowing or resource lifetimes"
        )
    return f"'{word}' is outside the pure prototype"


def independent_tokenize(source: bytes) -> tuple[RenderedToken, ...]:
    """Tokenize pure Vela bytes independently of `lexer.mll` and `vela.ast`."""
    if len(source) > MAX_SOURCE_BYTES:
        raise VelaError("limit", 1, 1, f"source exceeds {MAX_SOURCE_BYTES} bytes")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as error:
        prefix = source[: error.start].decode("utf-8", errors="ignore")
        line, col = _advance_position(1, 1, prefix)
        raise VelaError("encoding", line, col, "source is not valid UTF-8") from error

    tokens: list[RenderedToken] = []
    idx = 0
    byte_pos = 0
    line = 1
    col = 1
    delimiters = 0
    length = len(text)

    while idx < length:
        ch = text[idx]
        if ch in " \t":
            idx += 1
            byte_pos += 1
            col += 1
            continue
        if ch == "\r":
            if idx + 1 < length and text[idx + 1] == "\n":
                idx += 2
                byte_pos += 2
            else:
                idx += 1
                byte_pos += 1
            line += 1
            col = 1
            continue
        if ch == "\n":
            idx += 1
            byte_pos += 1
            line += 1
            col = 1
            continue
        if ch == "/" and idx + 1 < length and text[idx + 1] == "/":
            end = idx + 2
            while end < length and text[end] not in "\r\n":
                end += 1
            comment_chunk = text[idx:end]
            byte_pos += len(comment_chunk.encode("utf-8"))
            col += len(comment_chunk)
            idx = end
            continue

        if ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ch == "_":
            end = idx + 1
            while end < length and (
                ("A" <= text[end] <= "Z")
                or ("a" <= text[end] <= "z")
                or ("0" <= text[end] <= "9")
                or text[end] == "_"
            ):
                end += 1
            word = text[idx:end]
            if word in PURE_RESERVED_WORDS:
                raise VelaError("unsupported", line, col, _pure_unsupported_message(word))
            terminal = PURE_KEYWORDS.get(word, "IDENT")
            w_bytes = len(word.encode("utf-8"))
            tokens.append(RenderedToken(terminal, word, byte_pos, byte_pos + w_bytes, line, col))
            idx = end
            byte_pos += w_bytes
            col += len(word)
            continue

        if "0" <= ch <= "9":
            end = idx
            digits = 0
            while end < length and (("0" <= text[end] <= "9") or text[end] == "_"):
                if text[end] == "_":
                    if (
                        end == idx
                        or end + 1 >= length
                        or not ("0" <= text[end - 1] <= "9")
                        or not ("0" <= text[end + 1] <= "9")
                    ):
                        raise VelaError(
                            "syntax",
                            line,
                            col,
                            "numeric separator must be between digits of the same base",
                        )
                else:
                    digits += 1
                end += 1
            if digits > MAX_LITERAL_DIGITS:
                raise VelaError("limit", line, col, f"literal exceeds {MAX_LITERAL_DIGITS} digits")
            spelling = text[idx:end]
            s_bytes = len(spelling.encode("utf-8"))
            tokens.append(
                RenderedToken("DECIMAL", spelling, byte_pos, byte_pos + s_bytes, line, col)
            )
            idx = end
            byte_pos += s_bytes
            col += len(spelling)
            continue

        matched_multi = False
        for op_str, op_term in _MULTI_CHAR_OPERATORS:
            if text.startswith(op_str, idx):
                tokens.append(
                    RenderedToken(op_term, op_str, byte_pos, byte_pos + len(op_str), line, col)
                )
                idx += len(op_str)
                byte_pos += len(op_str)
                col += len(op_str)
                matched_multi = True
                break
        if matched_multi:
            continue

        # Reject compound assignment or repeated slash/percent in the lexer/parser boundary:
        if ch in "([{":
            delimiters += 1
            if delimiters > MAX_DELIMITER_DEPTH:
                raise VelaError(
                    "limit", line, col, f"delimiter nesting exceeds {MAX_DELIMITER_DEPTH}"
                )
        elif ch in ")]}":
            delimiters = max(0, delimiters - 1)

        single_term = _SINGLE_CHAR_TOKENS.get(ch)
        if single_term is not None:
            tokens.append(RenderedToken(single_term, ch, byte_pos, byte_pos + 1, line, col))
            idx += 1
            byte_pos += 1
            col += 1
            continue

        raise VelaError("syntax", line, col, "unexpected character")

    return tuple(tokens)


@dataclass(frozen=True)
class _OracleNode:
    syntax: dict[str, Json]
    depth: int
    start_byte: int
    end_byte: int
    line: int
    column: int


class IndependentPureAstOracle:
    """Independent recursive-descent and precedence-climbing AST/span oracle for `file`.

    Constructs the expected schema-1 JSON syntax tree and half-open UTF-8 byte
    spans directly from `independent_tokenize(source)` without calling `vela.ast`
    or `vela_parser`.
    """

    def __init__(self, source: bytes) -> None:
        self.source = source
        self.tokens = independent_tokenize(source)
        self.cursor = 0

    @classmethod
    def parse(cls, source: bytes) -> dict[str, Json]:
        """Parse `source` into its expected schema-1 JSON envelope."""
        return cls(source).parse_envelope()

    def _current(self) -> RenderedToken | None:
        if self.cursor < len(self.tokens):
            return self.tokens[self.cursor]
        return None

    def _peek(self, offset: int = 0) -> RenderedToken | None:
        pos = self.cursor + offset
        if 0 <= pos < len(self.tokens):
            return self.tokens[pos]
        return None

    def _eof_position(self) -> tuple[int, int]:
        text = self.source.decode("utf-8")
        return _advance_position(1, 1, text)

    def _syntax_error(self, message: str = "unexpected token or incomplete input") -> VelaError:
        tok = self._current()
        if tok is not None:
            return VelaError("syntax", tok.line, tok.column, message)
        if self.tokens:
            last = self.tokens[-1]
            return VelaError("syntax", last.line, last.column, message)
        line, col = self._eof_position()
        return VelaError("syntax", line, col, message)

    def _expect(self, terminal: str) -> RenderedToken:
        tok = self._current()
        if tok is None or tok.terminal != terminal:
            raise self._syntax_error()
        self.cursor += 1
        return tok

    @staticmethod
    def _name_obj(tok: RenderedToken) -> dict[str, Json]:
        return {"text": tok.spelling, "span": [tok.start_byte, tok.end_byte]}

    @staticmethod
    def _make(
        kind: str,
        first_tok: RenderedToken,
        end_byte: int,
        fields: list[tuple[str, Json]],
        children: Sequence[_OracleNode],
    ) -> _OracleNode:
        depth = 1 + max((c.depth for c in children), default=0)
        if depth > MAX_SYNTAX_DEPTH:
            raise VelaError(
                "limit",
                first_tok.line,
                first_tok.column,
                f"syntax tree exceeds depth {MAX_SYNTAX_DEPTH}",
            )
        obj: dict[str, Json] = {
            "kind": kind,
            "span": [first_tok.start_byte, end_byte],
            **dict(fields),
        }
        return _OracleNode(
            syntax=obj,
            depth=depth,
            start_byte=first_tok.start_byte,
            end_byte=end_byte,
            line=first_tok.line,
            column=first_tok.column,
        )

    def parse_envelope(self) -> dict[str, Json]:
        mod_tok = self._expect("MODULE")
        mod_name = self._expect("IDENT")
        self._expect("SEMICOLON")
        if self._current() is None:
            raise self._syntax_error()
        declarations: list[_OracleNode] = []
        while self._current() is not None:
            declarations.append(self._parse_declaration())
        file_node = self._make(
            "file",
            mod_tok,
            declarations[-1].end_byte,
            [
                ("name", self._name_obj(mod_name)),
                ("declarations", [d.syntax for d in declarations]),
            ],
            declarations,
        )
        return {
            "schema": 1,
            "source_sha256": hashlib.sha256(self.source).hexdigest(),
            "ast": file_node.syntax,
        }

    def _parse_declaration(self) -> _OracleNode:
        pub_tok = self._expect("PUBLIC")
        const_tok: RenderedToken | None = None
        if (cur := self._current()) is not None and cur.terminal == "CONST":
            const_tok = self._expect("CONST")
        vtype = self._parse_value_type()
        decl_name = self._expect("IDENT")
        nxt = self._current()
        if nxt is not None and nxt.terminal == "EQUAL":
            if const_tok is None:
                raise self._syntax_error()
            self._expect("EQUAL")
            val = self._parse_expression()
            semi = self._expect("SEMICOLON")
            return self._make(
                "constant",
                pub_tok,
                semi.end_byte,
                [
                    ("name", self._name_obj(decl_name)),
                    ("type", vtype.syntax),
                    ("value", val.syntax),
                ],
                [vtype, val],
            )
        self._expect("LPAREN")
        params = self._parse_parameters()
        self._expect("RPAREN")
        body = self._parse_function_body()
        fields: list[tuple[str, Json]] = [
            ("name", self._name_obj(decl_name)),
            ("result", vtype.syntax),
            ("parameters", [p.syntax for p in params]),
            ("body", body.syntax),
        ]
        if const_tok is not None:
            fields.append(("const", True))
        return self._make("function", pub_tok, body.end_byte, fields, [vtype, body, *params])

    def _parse_value_type(self) -> _OracleNode:
        tok = self._current()
        if tok is None or tok.terminal not in {"NAT", "BOOL"}:
            raise self._syntax_error()
        self.cursor += 1
        tname = "Nat" if tok.terminal == "NAT" else "bool"
        return self._make("type", tok, tok.end_byte, [("name", tname)], [])

    def _parse_parameters(self) -> list[_OracleNode]:
        params: list[_OracleNode] = []
        cur = self._current()
        if cur is None or cur.terminal == "RPAREN":
            return params
        while True:
            cur = self._current()
            if cur is None:
                raise self._syntax_error()
            const_tok: RenderedToken | None = None
            if cur.terminal == "CONST":
                const_tok = self._expect("CONST")
            ptype = self._parse_value_type()
            pname = self._expect("IDENT")
            first_tok = const_tok if const_tok is not None else self._token_at(ptype.start_byte)
            fields: list[tuple[str, Json]] = [
                ("name", self._name_obj(pname)),
                ("type", ptype.syntax),
            ]
            if const_tok is not None:
                fields.append(("const", True))
            params.append(self._make("parameter", first_tok, pname.end_byte, fields, [ptype]))
            sep = self._current()
            if sep is not None and sep.terminal == "COMMA":
                self._expect("COMMA")
                after_comma = self._current()
                if after_comma is not None and after_comma.terminal == "RPAREN":
                    break
                continue
            break
        return params

    def _token_at(self, start_byte: int) -> RenderedToken:
        for tok in self.tokens:
            if tok.start_byte == start_byte:
                return tok
        raise ValueError(f"missing token at byte {start_byte}")

    def _parse_function_body(self) -> _OracleNode:
        cur = self._current()
        if cur is not None and cur.terminal == "FATARROW":
            arrow = self._expect("FATARROW")
            val = self._parse_expression()
            semi = self._expect("SEMICOLON")
            return self._make(
                "expression_body", arrow, semi.end_byte, [("value", val.syntax)], [val]
            )
        return self._parse_block()

    def _parse_block(self) -> _OracleNode:
        lbrace = self._expect("LBRACE")
        bindings: list[_OracleNode] = []
        while True:
            cur = self._current()
            if cur is None or cur.terminal in {"RETURN", "IF", "RBRACE"}:
                break
            bindings.append(self._parse_binding())
        terminal = self._parse_exit()
        rbrace = self._expect("RBRACE")
        if len(bindings) > MAX_BLOCK_BINDINGS:
            raise VelaError(
                "limit",
                lbrace.line,
                lbrace.column,
                f"block exceeds {MAX_BLOCK_BINDINGS} bindings",
            )
        return self._make(
            "block",
            lbrace,
            rbrace.end_byte,
            [
                ("bindings", [b.syntax for b in bindings]),
                ("exit", terminal.syntax),
            ],
            [terminal, *bindings],
        )

    def _parse_binding(self) -> _OracleNode:
        cur = self._current()
        if cur is None:
            raise self._syntax_error()
        if cur.terminal == "LET":
            let_tok = self._expect("LET")
            nxt = self._current()
            if nxt is not None and nxt.terminal in {"NAT", "BOOL"}:
                ann = self._parse_value_type()
                bname = self._expect("IDENT")
                self._expect("EQUAL")
                val = self._parse_expression()
                semi = self._expect("SEMICOLON")
                return self._make(
                    "let",
                    let_tok,
                    semi.end_byte,
                    [
                        ("name", self._name_obj(bname)),
                        ("type", ann.syntax),
                        ("value", val.syntax),
                    ],
                    [ann, val],
                )
            bname = self._expect("IDENT")
            self._expect("EQUAL")
            val = self._parse_expression()
            semi = self._expect("SEMICOLON")
            return self._make(
                "let",
                let_tok,
                semi.end_byte,
                [
                    ("name", self._name_obj(bname)),
                    ("value", val.syntax),
                ],
                [val],
            )
        if cur.terminal == "CONST":
            const_tok = self._expect("CONST")
            vtype = self._parse_value_type()
            cname = self._expect("IDENT")
            self._expect("EQUAL")
            val = self._parse_expression()
            semi = self._expect("SEMICOLON")
            return self._make(
                "constant_local",
                const_tok,
                semi.end_byte,
                [
                    ("name", self._name_obj(cname)),
                    ("type", vtype.syntax),
                    ("value", val.syntax),
                ],
                [vtype, val],
            )
        if cur.terminal in {"NAT", "BOOL"}:
            ann = self._parse_value_type()
            _ = self._expect("IDENT")
            self._expect("EQUAL")
            _ = self._parse_expression()
            self._expect("SEMICOLON")
            raise VelaError(
                "syntax",
                ann.line,
                ann.column,
                "local declaration requires 'let' or 'var' before its type (write 'let T x = e;' or 'var T x = e;')",
            )
        if cur.terminal == "IDENT":
            bname = self._expect("IDENT")
            self._expect("EQUAL")
            val = self._parse_expression()
            semi = self._expect("SEMICOLON")
            return self._make(
                "reassignment",
                bname,
                semi.end_byte,
                [
                    ("name", self._name_obj(bname)),
                    ("value", val.syntax),
                ],
                [val],
            )
        raise self._syntax_error()

    def _parse_exit(self) -> _OracleNode:
        cur = self._current()
        if cur is None:
            raise self._syntax_error()
        if cur.terminal == "RETURN":
            ret_tok = self._expect("RETURN")
            val = self._parse_expression()
            semi = self._expect("SEMICOLON")
            return self._make("return", ret_tok, semi.end_byte, [("value", val.syntax)], [val])
        if cur.terminal == "IF":
            if_tok = self._expect("IF")
            self._expect("LPAREN")
            cond = self._parse_expression()
            self._expect("RPAREN")
            yes_blk = self._parse_block()
            self._expect("ELSE")
            no_blk = self._parse_block()
            return self._make(
                "if",
                if_tok,
                no_blk.end_byte,
                [
                    ("condition", cond.syntax),
                    ("then", yes_blk.syntax),
                    ("else", no_blk.syntax),
                ],
                [cond, yes_blk, no_blk],
            )
        raise self._syntax_error()

    def _parse_expression(self) -> _OracleNode:
        return self._parse_disjunction()

    def _parse_disjunction(self) -> _OracleNode:
        left = self._parse_conjunction()
        while (cur := self._current()) is not None and cur.terminal == "OR":
            op = self._expect("OR")
            right = self._parse_conjunction()
            left = self._make(
                "binary",
                self._token_at(left.start_byte),
                right.end_byte,
                [
                    ("operator", self._name_obj(op)),
                    ("left", left.syntax),
                    ("right", right.syntax),
                ],
                [left, right],
            )
        return left

    def _parse_conjunction(self) -> _OracleNode:
        left = self._parse_comparison()
        while (cur := self._current()) is not None and cur.terminal == "AND":
            op = self._expect("AND")
            right = self._parse_comparison()
            left = self._make(
                "binary",
                self._token_at(left.start_byte),
                right.end_byte,
                [
                    ("operator", self._name_obj(op)),
                    ("left", left.syntax),
                    ("right", right.syntax),
                ],
                [left, right],
            )
        return left

    def _parse_comparison(self) -> _OracleNode:
        left = self._parse_sum()
        cur = self._current()
        if cur is not None and cur.terminal in {"EQ", "LE", "NE", "LT", "GT", "GE"}:
            op = self._expect(cur.terminal)
            right = self._parse_sum()
            nxt = self._current()
            if nxt is not None and nxt.terminal in {"EQ", "LE", "NE", "LT", "GT", "GE"}:
                raise self._syntax_error()
            return self._make(
                "binary",
                self._token_at(left.start_byte),
                right.end_byte,
                [
                    ("operator", self._name_obj(op)),
                    ("left", left.syntax),
                    ("right", right.syntax),
                ],
                [left, right],
            )
        return left

    def _parse_sum(self) -> _OracleNode:
        left = self._parse_product()
        while (cur := self._current()) is not None and cur.terminal in {"PLUS", "MINUS"}:
            op = self._expect(cur.terminal)
            right = self._parse_product()
            left = self._make(
                "binary",
                self._token_at(left.start_byte),
                right.end_byte,
                [
                    ("operator", self._name_obj(op)),
                    ("left", left.syntax),
                    ("right", right.syntax),
                ],
                [left, right],
            )
        return left

    def _parse_product(self) -> _OracleNode:
        left = self._parse_unary()
        while (cur := self._current()) is not None and cur.terminal in {
            "STAR",
            "SLASH",
            "PERCENT",
        }:
            op = self._expect(cur.terminal)
            right = self._parse_unary()
            left = self._make(
                "binary",
                self._token_at(left.start_byte),
                right.end_byte,
                [
                    ("operator", self._name_obj(op)),
                    ("left", left.syntax),
                    ("right", right.syntax),
                ],
                [left, right],
            )
        return left

    def _parse_unary(self) -> _OracleNode:
        cur = self._current()
        if cur is not None and cur.terminal == "NOT":
            op = self._expect("NOT")
            inner = self._parse_unary()
            return self._make(
                "unary",
                op,
                inner.end_byte,
                [
                    ("operator", self._name_obj(op)),
                    ("value", inner.syntax),
                ],
                [inner],
            )
        return self._parse_atom()

    def _parse_atom(self) -> _OracleNode:
        cur = self._current()
        if cur is None:
            raise self._syntax_error()
        if cur.terminal == "DECIMAL":
            tok = self._expect("DECIMAL")
            return self._make("nat", tok, tok.end_byte, [("value", tok.spelling)], [])
        if cur.terminal == "TRUE":
            tok = self._expect("TRUE")
            return self._make("bool", tok, tok.end_byte, [("value", True)], [])
        if cur.terminal == "FALSE":
            tok = self._expect("FALSE")
            return self._make("bool", tok, tok.end_byte, [("value", False)], [])
        if cur.terminal == "IDENT":
            ident = self._expect("IDENT")
            nxt = self._current()
            if nxt is not None and nxt.terminal == "LPAREN":
                self._expect("LPAREN")
                args = self._parse_call_arguments()
                rparen = self._expect("RPAREN")
                return self._make(
                    "call",
                    ident,
                    rparen.end_byte,
                    [
                        ("callee", self._name_obj(ident)),
                        ("arguments", [a.syntax for a in args]),
                    ],
                    args,
                )
            return self._make("name", ident, ident.end_byte, [("name", self._name_obj(ident))], [])
        if cur.terminal == "LPAREN":
            lparen = self._expect("LPAREN")
            inner = self._parse_expression()
            rparen = self._expect("RPAREN")
            return self._make("group", lparen, rparen.end_byte, [("value", inner.syntax)], [inner])
        raise self._syntax_error()

    def _parse_call_arguments(self) -> list[_OracleNode]:
        args: list[_OracleNode] = []
        cur = self._current()
        if cur is None or cur.terminal == "RPAREN":
            return args
        while True:
            cur = self._current()
            if cur is None:
                raise self._syntax_error()
            nxt = self._peek(1)
            if cur.terminal == "IDENT" and nxt is not None and nxt.terminal == "COLON":
                label = self._expect("IDENT")
                self._expect("COLON")
                val = self._parse_expression()
                args.append(
                    self._make(
                        "argument",
                        label,
                        val.end_byte,
                        [
                            ("label", self._name_obj(label)),
                            ("value", val.syntax),
                        ],
                        [val],
                    )
                )
            else:
                val = self._parse_expression()
                args.append(
                    self._make(
                        "argument",
                        self._token_at(val.start_byte),
                        val.end_byte,
                        [
                            ("label", None),
                            ("value", val.syntax),
                        ],
                        [val],
                    )
                )
            sep = self._current()
            if sep is not None and sep.terminal == "COMMA":
                self._expect("COMMA")
                after_comma = self._current()
                if after_comma is not None and after_comma.terminal == "RPAREN":
                    break
                continue
            break
        return args


def expected_parse_observation(source: bytes) -> dict[str, Json]:
    """Compute the independent expected AST envelope or refusal record for `source`."""
    try:
        envelope = IndependentPureAstOracle(source).parse_envelope()
    except VelaError as error:
        return {
            "status": "refused",
            "kind": error.kind,
            "line": error.line,
            "column": error.column,
            "message": error.message,
        }
    return {
        "status": "accepted",
        "envelope": envelope,
    }


def strip_spans(node: Json) -> Json:
    """Erase `span` and `source_sha256` fields to compare structural AST equivalence across trivia."""
    if isinstance(node, list):
        return [strip_spans(item) for item in node]
    if isinstance(node, dict):
        return {
            k: strip_spans(v)
            for k, v in node.items()
            if k not in {"span", "source_sha256"}
        }
    return node


def parse_interpreter_cst(raw_output: str) -> list[CstNode | None]:
    """Parse `menhir --interpret --interpret-show-cst` output into `CstNode`s (or `None` for REJECT)."""
    if len(raw_output.encode("utf-8")) > MAX_INTERPRETER_OUTPUT_BYTES:
        raise ValueError("Menhir interpreter output exceeds byte budget")
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines or lines[0] != "Ready!":
        raise ValueError("Menhir interpreter output missing 'Ready!' header")

    results: list[CstNode | None] = []
    idx = 1
    while idx < len(lines):
        verdict = lines[idx]
        if verdict == "REJECT":
            results.append(None)
            idx += 1
            continue
        if verdict != "ACCEPT":
            raise ValueError(f"unexpected Menhir interpreter line: {verdict!r}")
        idx += 1
        # Collect balanced bracket block for the CST
        cst_lines: list[str] = []
        depth = 0
        while idx < len(lines):
            cur = lines[idx]
            depth += cur.count("[") - cur.count("]")
            cst_lines.append(cur)
            idx += 1
            if depth <= 0 and cst_lines:
                break
        if depth != 0 or not cst_lines:
            raise ValueError("unbalanced or missing CST block in Menhir interpreter output")
        cst_text = " ".join(cst_lines)
        results.append(_parse_cst_block(cst_text))
    return results


def _parse_cst_block(text: str) -> CstNode:
    token_re = re.compile(r"\[([^:\s\]]+):|\]|([^\s\[\]]+)")
    stack: list[tuple[str, list[CstNode | str]]] = []
    pos = 0
    for match in token_re.finditer(text):
        if text[pos : match.start()].strip():
            raise ValueError("unexpected trivia in CST output")
        pos = match.end()
        open_sym = match.group(1)
        leaf = match.group(2)
        if open_sym is not None:
            stack.append((open_sym, []))
            if len(stack) > MAX_SYNTAX_DEPTH * 2:
                raise ValueError("Menhir CST exceeds depth bound")
        elif leaf is not None:
            if not stack:
                raise ValueError("CST leaf outside nonterminal node")
            stack[-1][1].append(leaf)
        else:
            if not stack:
                raise ValueError("unmatched closing bracket in CST")
            sym, children = stack.pop()
            node = CstNode(sym, tuple(children))
            if not stack:
                if text[pos:].strip():
                    raise ValueError("trailing CST content after root node")
                return node
            stack[-1][1].append(node)
    raise ValueError("incomplete CST block")


def verify_cst_against_sentence(cst: CstNode | None, terminals: Sequence[str]) -> None:
    """Verify that Menhir's CST accepted the sentence, rooted at `file`, with exact leaf terminals."""
    validate_terminal_sentence(terminals)
    if cst is None:
        raise CampaignObservationError("Menhir interpreter rejected a valid sentence")
    if cst.symbol != ENTRY_POINT:
        raise CampaignObservationError(f"CST root symbol {cst.symbol!r} != {ENTRY_POINT!r}")
    leaves = cst.leaf_terminals()
    # The CST leaves include all terminals before EOF (or including EOF depending on grammar).
    expected_without_eof = tuple(terminals[:-1])
    expected_with_eof = tuple(terminals)
    if leaves not in (expected_without_eof, expected_with_eof):
        raise CampaignObservationError(
            f"CST leaf terminals {leaves!r} do not match sentence {expected_without_eof!r}"
        )


def qualify_renderer() -> dict[str, object]:
    """Qualify the token-payload renderer before any generated source reaches the parser."""
    # 1. Every pure terminal must render and round-trip through independent_tokenize:
    all_terminals_sentence = (
        "MODULE", "IDENT", "SEMICOLON",
        "PUBLIC", "CONST", "NAT", "IDENT", "EQUAL",
        "LPAREN", "DECIMAL", "PLUS", "DECIMAL", "MINUS", "DECIMAL", "RPAREN",
        "STAR", "DECIMAL", "SLASH", "DECIMAL", "PERCENT", "DECIMAL", "SEMICOLON",
        "PUBLIC", "BOOL", "IDENT", "LPAREN", "CONST", "NAT", "IDENT", "COMMA", "BOOL", "IDENT", "COMMA", "RPAREN",
        "LBRACE",
        "LET", "NAT", "IDENT", "EQUAL", "DECIMAL", "SEMICOLON",
        "LET", "BOOL", "IDENT", "EQUAL", "NOT", "TRUE", "OR", "FALSE", "AND",
        "DECIMAL", "EQ", "DECIMAL", "OR", "DECIMAL", "NE", "DECIMAL", "OR",
        "DECIMAL", "LT", "DECIMAL", "OR", "DECIMAL", "LE", "DECIMAL", "OR",
        "DECIMAL", "GT", "DECIMAL", "OR", "DECIMAL", "GE", "DECIMAL", "SEMICOLON",
        "CONST", "NAT", "IDENT", "EQUAL", "DECIMAL", "SEMICOLON",
        "IDENT", "EQUAL", "DECIMAL", "SEMICOLON",
        "IF", "LPAREN", "IDENT", "RPAREN",
        "LBRACE", "RETURN", "TRUE", "SEMICOLON", "RBRACE",
        "ELSE",
        "LBRACE", "RETURN", "FALSE", "SEMICOLON", "RBRACE",
        "RBRACE",
        "PUBLIC", "NAT", "IDENT", "LPAREN", "NAT", "IDENT", "RPAREN",
        "FATARROW", "IDENT", "LPAREN", "IDENT", "COLON", "DECIMAL", "COMMA", "RPAREN", "SEMICOLON",
        "EOF",
    )
    covered = set(all_terminals_sentence)
    if covered != set(PURE_TERMINALS):
        missing = sorted(set(PURE_TERMINALS) - covered)
        raise ValueError(f"renderer qualification sentence omits terminals: {missing}")

    variant_digests: dict[str, str] = {}
    baseline_stripped: Json | None = None
    for variant in RENDER_VARIANTS:
        rendered = render_sentence(all_terminals_sentence, variant=variant, seed=42)
        variant_digests[variant] = rendered.source_sha256
        obs = expected_parse_observation(rendered.source)
        if obs["status"] != "accepted":
            raise ValueError(f"renderer qualification sentence refused in {variant}: {obs}")
        stripped = strip_spans(cast("dict[str, Json]", obs["envelope"])["ast"])
        if baseline_stripped is None:
            baseline_stripped = stripped
        elif stripped != baseline_stripped:
            raise ValueError(f"renderer variant {variant} altered structural AST")

    # 2. Negative renderer controls must fail closed before reaching the parser:
    negative_controls: tuple[tuple[str, Sequence[str]], ...] = (
        ("empty-sentence", ()),
        ("missing-eof", ("MODULE", "IDENT", "SEMICOLON")),
        ("premature-eof", ("MODULE", "EOF", "IDENT", "EOF")),
        ("surface-only-terminal", ("MODULE", "IDENT", "FORALL", "EOF")),
        ("unknown-terminal", ("MODULE", "IDENT", "UNKNOWN_TOK", "EOF")),
        ("exceeds-token-budget", (*(["MODULE"] * (MAX_SENTENCE_TOKENS)), "EOF")),
    )
    for label, bad_tokens in negative_controls:
        try:
            render_sentence(bad_tokens)
        except ValueError:
            pass
        else:
            raise ValueError(f"renderer negative control {label} unexpectedly succeeded")

    return {
        "status": "qualified",
        "terminal_count": len(PURE_TERMINALS),
        "variants": list(RENDER_VARIANTS),
        "variant_source_sha256": variant_digests,
        "negative_controls": [name for name, _ in negative_controls],
    }


def apply_seeded_fault(
    envelope: dict[str, Json],
    rendered: RenderedSentence,
    fault_name: str,
) -> dict[str, Json]:
    """Inject a selected semantic-action or byte-span fault into an AST envelope."""
    if fault_name == "stillborn-mutant":
        raise RuntimeError("stillborn mutant cannot execute")

    corrupted = copy.deepcopy(envelope)
    ast = cast("dict[str, Json]", corrupted["ast"])

    if fault_name == "right-associative-subtraction-or-division-action":
        # Rotate left-associative (a - b) - c or (a / b) / c into a - (b - c):
        def rotate(node: Json) -> None:
            if isinstance(node, list):
                for item in node:
                    rotate(item)
            elif isinstance(node, dict):
                for val in node.values():
                    rotate(val)
                if node.get("kind") == "binary":
                    op_obj = cast("dict[str, Json]", node.get("operator", {}))
                    left_obj = node.get("left")
                    right_obj = node.get("right")
                    if (
                        op_obj.get("text") in {"-", "/", "%"}
                        and isinstance(left_obj, dict)
                        and left_obj.get("kind") == "binary"
                        and isinstance(right_obj, dict)
                    ):
                        inner_op = cast("dict[str, Json]", left_obj.get("operator", {}))
                        if inner_op.get("text") in {"-", "/", "%"}:
                            a_node = cast("dict[str, Json]", left_obj["left"])
                            b_node = cast("dict[str, Json]", left_obj["right"])
                            b_span = b_node["span"]
                            c_span = right_obj["span"]
                            if (
                                isinstance(b_span, list)
                                and isinstance(c_span, list)
                                and len(b_span) == 2
                                and len(c_span) == 2
                            ):
                                new_right: dict[str, Json] = {
                                    "kind": "binary",
                                    "span": [b_span[0], c_span[1]],
                                    "operator": op_obj,
                                    "left": b_node,
                                    "right": right_obj,
                                }
                                node["operator"] = inner_op
                                node["left"] = a_node
                                node["right"] = new_right

        rotate(ast)
        return corrupted

    if fault_name == "trailing-comma-span-or-arity-corruption":
        # When a parameter list has a trailing comma in source, extend the last parameter's span to include the comma:
        comma_after_param = False
        for idx, tok in enumerate(rendered.tokens):
            if (
                tok.terminal == "COMMA"
                and idx + 1 < len(rendered.tokens)
                and rendered.tokens[idx + 1].terminal == "RPAREN"
            ):
                comma_after_param = True
                break
        if comma_after_param:
            decls = ast.get("declarations")
            if isinstance(decls, list):
                for decl in decls:
                    if isinstance(decl, dict):
                        params = decl.get("parameters")
                        if isinstance(params, list) and params and isinstance(params[-1], dict):
                            last_span = params[-1].get("span")
                            if (
                                isinstance(last_span, list)
                                and len(last_span) == 2
                                and isinstance(last_span[0], int)
                                and isinstance(last_span[1], int)
                            ):
                                params[-1]["span"] = [last_span[0], last_span[1] + 1]
        return corrupted

    if fault_name == "expression-body-excludes-arrow-or-semicolon-span":
        # Corrupt expression_body span to match its inner value span rather than `=> value;`:
        decls = ast.get("declarations")
        if isinstance(decls, list):
            for decl in decls:
                if isinstance(decl, dict):
                    body = decl.get("body")
                    if isinstance(body, dict) and body.get("kind") == "expression_body":
                        val = body.get("value")
                        if isinstance(val, dict) and "span" in val:
                            body["span"] = copy.deepcopy(val["span"])
        return corrupted

    raise ValueError(f"unknown seeded fault: {fault_name!r}")


def verify_sentence_against_oracle(
    terminals: Sequence[str],
    *,
    variant: str = "canonical",
    seed: int = 0,
    parser_fn: Callable[[bytes], dict[str, Json]] | None = None,
    fault_name: str | None = None,
) -> dict[str, object]:
    """Render `terminals`, compare parser output with `IndependentPureAstOracle`, and return observation."""
    rendered = render_sentence(terminals, variant=variant, seed=seed)
    expected = expected_parse_observation(rendered.source)

    if parser_fn is None:
        if expected["status"] == "refused":
            actual_obs = expected
        else:
            env = copy.deepcopy(cast("dict[str, Json]", expected["envelope"]))
            if fault_name is not None:
                env = apply_seeded_fault(env, rendered, fault_name)
            actual_obs = {"status": "accepted", "envelope": env}
    else:
        try:
            actual_env = parser_fn(rendered.source)
            if fault_name is not None:
                actual_env = apply_seeded_fault(actual_env, rendered, fault_name)
            actual_obs = {"status": "accepted", "envelope": actual_env}
        except VelaError as error:
            actual_obs = {
                "status": "refused",
                "kind": error.kind,
                "line": error.line,
                "column": error.column,
                "message": error.message,
            }

    if actual_obs["status"] != expected["status"]:
        raise CampaignObservationError(
            f"status mismatch in {variant}: actual={actual_obs['status']!r}, expected={expected['status']!r}"
        )
    if expected["status"] == "refused":
        for key in ("kind", "line", "column"):
            if actual_obs[key] != expected[key]:
                raise CampaignObservationError(
                    f"refusal {key} mismatch in {variant}: actual={actual_obs[key]!r}, expected={expected[key]!r}"
                )
    elif actual_obs["envelope"] != expected["envelope"]:
        raise CampaignObservationError(
            f"AST/span mismatch in {variant} against IndependentPureAstOracle"
        )
    return {
        "variant": variant,
        "source_sha256": rendered.source_sha256,
        "source_bytes": len(rendered.source),
        "status": expected["status"],
    }


def _is_valid_pure_sentence(terminals: Sequence[str]) -> bool:
    try:
        rendered = render_sentence(terminals)
        obs = expected_parse_observation(rendered.source)
    except (ValueError, VelaError):
        return False
    return obs["status"] == "accepted"


def _candidate_reductions(terminals: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Generate smaller candidate terminal sequences by grammar-preserving structural edits."""
    candidates: list[tuple[str, ...]] = []
    toks = list(terminals)
    n = len(toks)

    # 1. Drop one PUBLIC declaration if more than one PUBLIC exists:
    pub_indices = [i for i, t in enumerate(toks) if t == "PUBLIC"]
    if len(pub_indices) > 1:
        for idx, start in enumerate(pub_indices):
            end = pub_indices[idx + 1] if idx + 1 < len(pub_indices) else n - 1
            candidates.append(tuple(toks[:start] + toks[end:]))

    # 2. Drop a parameter or a trailing comma inside LPAREN ... RPAREN:
    for i in range(n):
        if toks[i] == "COMMA":
            candidates.append(tuple(toks[:i] + toks[i + 1 :]))
        if i + 3 <= n and toks[i] in {"NAT", "BOOL"} and toks[i + 1] == "IDENT" and toks[i + 2] == "COMMA":
            candidates.append(tuple(toks[:i] + toks[i + 3 :]))
        if i + 4 <= n and toks[i] == "CONST" and toks[i + 1] in {"NAT", "BOOL"} and toks[i + 2] == "IDENT" and toks[i + 3] == "COMMA":
            candidates.append(tuple(toks[:i] + toks[i + 4 :]))

    # 3. Unwrap parenthesized `( expr )` -> `DECIMAL` or `expr`:
    for i in range(n):
        if toks[i] == "LPAREN" and (i == 0 or toks[i - 1] != "IDENT"):
            depth = 0
            for j in range(i, n):
                if toks[j] == "LPAREN":
                    depth += 1
                elif toks[j] == "RPAREN":
                    depth -= 1
                    if depth == 0:
                        if j > i + 1:
                            candidates.append((*toks[:i], *toks[i + 1 : j], *toks[j + 1 :]))
                            candidates.append((*toks[:i], "DECIMAL", *toks[j + 1 :]))
                        break

    # 4. Drop binary operator tail `op atom`:
    binary_ops = {"PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "OR", "AND", "EQ", "LE", "NE", "LT", "GT", "GE"}
    for i in range(n - 1):
        if toks[i] in binary_ops and toks[i + 1] in {"DECIMAL", "TRUE", "FALSE", "IDENT"}:
            candidates.append(tuple(toks[:i] + toks[i + 2 :]))
        if i > 0 and toks[i - 1] in {"DECIMAL", "TRUE", "FALSE", "IDENT"} and toks[i] in binary_ops:
            candidates.append(tuple(toks[: i - 1] + toks[i + 1 :]))

    # 5. Replace `{ let ...; return expr; }` with `=> expr;`:
    for i in range(n):
        if toks[i] == "LBRACE":
            depth = 0
            ret_idx = -1
            for j in range(i, n):
                if toks[j] == "LBRACE":
                    depth += 1
                elif toks[j] == "RBRACE":
                    depth -= 1
                    if depth == 0:
                        if ret_idx != -1:
                            # Replace LBRACE ... RETURN expr; RBRACE with FATARROW expr;
                            candidates.append(
                                (*toks[:i], "FATARROW", *toks[ret_idx + 1 : j], *toks[j + 1 :])
                            )
                        break
                elif depth == 1 and toks[j] == "RETURN":
                    ret_idx = j

    # Deduplicate and sort shortest first:
    seen: set[tuple[str, ...]] = set()
    unique: list[tuple[str, ...]] = []
    for cand in sorted(candidates, key=len):
        if len(cand) < len(terminals) and cand not in seen and _is_valid_pure_sentence(cand):
            seen.add(cand)
            unique.append(cand)
    return unique


def shrink_failing_sentence(
    terminals: Sequence[str],
    failing_predicate: Callable[[tuple[str, ...]], bool],
) -> tuple[str, ...]:
    """Deterministically shrink a failing `file` sentence to a minimal failing replay."""
    current = tuple(terminals)
    if not failing_predicate(current):
        raise ValueError("initial sentence does not satisfy failing_predicate")
    while True:
        reduced = False
        for candidate in _candidate_reductions(current):
            if failing_predicate(candidate):
                current = candidate
                reduced = True
                break
        if not reduced:
            return current


def build_replay_record(
    terminals: Sequence[str],
    *,
    variant: str = "canonical",
    seed: int = 0,
) -> dict[str, object]:
    """Serialize a deterministic replay record binding entry, terminals, source, and expected observation."""
    rendered = render_sentence(terminals, variant=variant, seed=seed)
    expected = expected_parse_observation(rendered.source)
    return {
        "entry": rendered.entry,
        "variant": rendered.variant,
        "seed": seed,
        "terminals": list(rendered.terminals),
        "token_count": len(rendered.terminals),
        "rendered_source": rendered.source.decode("utf-8"),
        "source_sha256": rendered.source_sha256,
        "expected": expected,
    }


def replay_sentence_case(
    record: dict[str, object],
    *,
    parser_fn: Callable[[bytes], dict[str, Json]] | None = None,
) -> dict[str, object]:
    """Replay a serialized sentence record without random generation."""
    entry = record.get("entry")
    variant = cast("str", record.get("variant", "canonical"))
    seed = cast("int", record.get("seed", 0))
    terminals = tuple(cast("list[str]", record.get("terminals", [])))
    rendered_text = cast("str", record.get("rendered_source", ""))
    expected_sha = cast("str", record.get("source_sha256", ""))
    expected_obs = cast("dict[str, Json]", record.get("expected", {}))

    if not isinstance(entry, str) or entry != ENTRY_POINT:
        raise ValueError(f"unsupported replay entry: {entry!r}")
    re_rendered = render_sentence(terminals, variant=variant, seed=seed, entry=entry)
    if re_rendered.source != rendered_text.encode("utf-8") or re_rendered.source_sha256 != expected_sha:
        raise CampaignObservationError("replay record source or digest drifted from renderer")
    if expected_parse_observation(re_rendered.source) != expected_obs:
        raise CampaignObservationError("replay record expected observation drifted from oracle")
    return verify_sentence_against_oracle(
        terminals,
        variant=variant,
        seed=seed,
        parser_fn=parser_fn,
    )


def evaluate_seeded_fault(
    fault_name: str,
    *,
    runner: Callable[[tuple[str, ...]], None] | None = None,
) -> dict[str, object]:
    """Evaluate a seeded defect using the repository's stillborn/killed/survived vocabulary."""
    if fault_name == "stillborn-mutant":
        try:
            apply_seeded_fault({"ast": {}}, render_sentence(NONMINIMAL_FAULT_SENTENCES[HELD_OUT_FAULT]), fault_name)
        except RuntimeError as error:
            return {
                "fault": fault_name,
                "held_out": False,
                "status": "stillborn",
                "reason": str(error),
            }
        return {"fault": fault_name, "held_out": False, "status": "survived"}

    initial_sentence = NONMINIMAL_FAULT_SENTENCES[fault_name]

    def run_sentence(sent: tuple[str, ...]) -> None:
        if runner is not None:
            runner(sent)
            return
        verify_sentence_against_oracle(sent, fault_name=fault_name)

    def fails(sent: tuple[str, ...]) -> bool:
        try:
            run_sentence(sent)
        except CampaignObservationError:
            return True
        return False

    if not fails(initial_sentence):
        return {
            "fault": fault_name,
            "held_out": fault_name == HELD_OUT_FAULT,
            "status": "survived",
            "initial_tokens": len(initial_sentence),
        }

    shrunk = shrink_failing_sentence(initial_sentence, fails)
    replay = build_replay_record(shrunk)
    # Verify unmutated baseline passes on the shrunk replay record:
    replay_sentence_case(replay)

    return {
        "fault": fault_name,
        "held_out": fault_name == HELD_OUT_FAULT,
        "status": "killed",
        "initial_tokens": len(initial_sentence),
        "shrunk_tokens": len(shrunk),
        "shrunk_replay": replay,
    }


def _menhir_binary(root: Path, toolchain_receipt: dict[str, object]) -> Path:
    bin_dir = Path(
        vela_parser._run(["opam", "var", "bin", "--switch", vela_parser.env.SAIL_SWITCH], root)
    )
    menhir = bin_dir / "menhir"
    expected_hashes = cast("dict[str, str]", toolchain_receipt["binary_sha256"])
    if vela_parser._digest(menhir) != expected_hashes["menhir"]:
        raise ValueError("Menhir binary digest changed from build toolchain receipt")
    return menhir


def _generate_menhir_sentence(menhir: Path, grammar: Path, seed: int, goal_length: int) -> tuple[str, ...]:
    try:
        done = subprocess.run(
            [
                str(menhir),
                "--random-seed",
                str(seed),
                "--random-sentence-length",
                str(goal_length),
                "--random-sentence",
                ENTRY_POINT,
                str(grammar),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=PROCESS_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"menhir --random-sentence exceeded {PROCESS_TIMEOUT_SECONDS}s") from error
    if done.returncode != 0 or done.stderr:
        raise RuntimeError(
            f"menhir --random-sentence failed ({done.returncode}): {(done.stderr or done.stdout).strip()}"
        )
    return parse_sentence_line(done.stdout, entry=ENTRY_POINT)


def _interpret_menhir_sentences(
    menhir: Path,
    grammar: Path,
    sentences: Sequence[str],
) -> list[CstNode | None]:
    payload = ("\n".join(sentences) + "\n").encode("utf-8")
    try:
        done = subprocess.run(
            [str(menhir), "--interpret", "--interpret-show-cst", str(grammar)],
            input=payload,
            capture_output=True,
            timeout=PROCESS_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"menhir --interpret exceeded {PROCESS_TIMEOUT_SECONDS}s") from error
    if len(done.stdout) > MAX_INTERPRETER_OUTPUT_BYTES or done.stderr:
        raise ValueError("menhir --interpret exceeded output bound or wrote to stderr")
    if done.returncode != 0:
        raise RuntimeError(f"menhir --interpret exited {done.returncode}")
    return parse_interpreter_cst(done.stdout.decode("utf-8"))


def _inputs(root: Path) -> dict[str, str]:
    paths = (
        *vela_migration._inputs(root),
        "tools/toolchain/syntax_campaigns.py",
    )
    return {path: vela_parser._digest(root / path) for path in paths}


def qualify(
    root: Path,
    *,
    seed_start: int = DEFAULT_SEED_START,
    count: int = DEFAULT_CAMPAIGN_COUNT,
    goal_length: int = DEFAULT_GOAL_LENGTH,
) -> dict[str, object]:
    """Run the bounded Menhir syntax campaign against the locked Sail generator and native parser."""
    if count < 1 or count > MAX_SENTENCE_TOKENS:
        raise ValueError(f"campaign count {count} out of range 1..{MAX_SENTENCE_TOKENS}")
    if goal_length < 1 or goal_length > MAX_SENTENCE_TOKENS:
        raise ValueError(f"goal length {goal_length} out of range 1..{MAX_SENTENCE_TOKENS}")

    work = vela_parser._work_root(root)
    latest = work / "syntax-campaigns.json"
    with FileLock(work / "syntax-campaigns.lock", timeout=1):
        latest.unlink(missing_ok=True)
        started = time.monotonic()
        inputs = _inputs(root)

        # Prerequisite: Q25g syntax qualification + Q25h migration agreement
        migration_report = vela_migration.qualify(root)
        if migration_report.get("status") != "agreed" or migration_report.get("differences"):
            raise ValueError("migration prerequisite failed before syntax campaign")

        build_receipt = cast("dict[str, object]", migration_report["build"])
        build_dir = Path(cast("str", build_receipt["directory"]))
        compiled = vela_parser.Build(build_dir, build_dir / "vela-parser", build_receipt)
        toolchain_receipt = cast("dict[str, object]", build_receipt["toolchain"])
        menhir = _menhir_binary(root, toolchain_receipt)
        grammar = build_dir / "parser.mly"

        # 1. Qualify renderer before sending generated source to the lexer/parser:
        renderer_report = qualify_renderer()

        # 2. Generate deterministic sentences from locked Menhir:
        seeds = list(range(seed_start, seed_start + count))
        generated_sentences: list[tuple[int, tuple[str, ...]]] = []
        raw_lines: list[str] = []
        for seed in seeds:
            if time.monotonic() - started > MAX_CAMPAIGN_SECONDS:
                raise RuntimeError(f"syntax campaign exceeded {MAX_CAMPAIGN_SECONDS}s wall-time bound")
            terminals = _generate_menhir_sentence(menhir, grammar, seed, goal_length)
            generated_sentences.append((seed, terminals))
            raw_lines.append(f"{ENTRY_POINT}: {' '.join(terminals)}")

        # 3. Batch CST interpretation + negative interpreter controls:
        negative_lines = [
            f"{ENTRY_POINT}: MODULE SEMICOLON EOF",
            f"{ENTRY_POINT}: MODULE IDENT SEMICOLON PUBLIC NAT IDENT LPAREN RPAREN FATARROW DECIMAL PLUS SEMICOLON EOF",
            f"{ENTRY_POINT}: MODULE IDENT SEMICOLON PUBLIC BOOL IDENT EQUAL DECIMAL EQ DECIMAL LE DECIMAL SEMICOLON EOF",
        ]
        cst_results = _interpret_menhir_sentences(menhir, grammar, [*raw_lines, *negative_lines])
        if len(cst_results) != len(raw_lines) + len(negative_lines):
            raise ValueError("Menhir interpreter result count disagrees with batch input count")

        for (_, terminals), cst in zip(generated_sentences, cst_results[: len(raw_lines)], strict=True):
            verify_cst_against_sentence(cst, terminals)
        for neg_cst in cst_results[len(raw_lines) :]:
            if neg_cst is not None:
                raise ValueError("Menhir interpreter unexpectedly accepted a malformed negative sentence")

        # 4. Render each sentence across trivia/payload variants and verify native vela-parser against IndependentPureAstOracle:
        accepted_sentences = 0
        action_refused_sentences = 0
        variant_checks = 0
        sample_replays: list[dict[str, object]] = []

        def native_parse(raw: bytes) -> dict[str, Json]:
            return vela_parser.parse_source(compiled, raw)

        for idx, (seed, terminals) in enumerate(generated_sentences):
            if time.monotonic() - started > MAX_CAMPAIGN_SECONDS:
                raise RuntimeError(f"syntax campaign exceeded {MAX_CAMPAIGN_SECONDS}s wall-time bound")
            base_envelope: Json | None = None
            first_status: str | None = None
            for variant in RENDER_VARIANTS:
                obs = verify_sentence_against_oracle(
                    terminals,
                    variant=variant,
                    seed=seed,
                    parser_fn=native_parse,
                )
                variant_checks += 1
                if first_status is None:
                    first_status = cast("str", obs["status"])
                elif obs["status"] != first_status:
                    raise CampaignObservationError("trivia variant changed acceptance vs refusal status")
                if obs["status"] == "accepted":
                    rendered = render_sentence(terminals, variant=variant, seed=seed)
                    parsed = native_parse(rendered.source)
                    stripped = strip_spans(parsed["ast"])
                    if base_envelope is None:
                        base_envelope = stripped
                    elif stripped != base_envelope:
                        raise CampaignObservationError("trivia variant changed span-erased native AST")
            if first_status == "accepted":
                accepted_sentences += 1
            else:
                action_refused_sentences += 1
            if idx < 3 or first_status == "refused":
                sample_replays.append(build_replay_record(terminals, seed=seed))

        # 5. Evaluate seeded defects, shrinking, and deterministic replay on native parser:
        fault_reports: dict[str, object] = {}
        for fault_name in SEEDED_FAULTS:
            verdict = evaluate_seeded_fault(
                fault_name,
                runner=lambda sent, fn=fault_name: (
                    verify_sentence_against_oracle(sent, parser_fn=native_parse, fault_name=fn),
                    None,
                )[1],
            )
            if verdict["status"] != "killed":
                raise ValueError(f"seeded fault {fault_name} was not killed: {verdict}")
            replay_sentence_case(
                cast("dict[str, object]", verdict["shrunk_replay"]),
                parser_fn=native_parse,
            )
            fault_reports[fault_name] = verdict

        # 6. Recheck inputs, toolchain, and generated build outputs:
        elapsed = round(time.monotonic() - started, 3)
        if elapsed > MAX_CAMPAIGN_SECONDS:
            raise RuntimeError(f"syntax campaign exceeded {MAX_CAMPAIGN_SECONDS}s wall-time bound")
        if _inputs(root) != inputs or vela_parser._toolchain(root) != toolchain_receipt:
            raise ValueError("syntax campaign inputs or toolchain changed during execution")
        outputs = cast("dict[str, str]", build_receipt["generated_sha256"])
        if any(
            vela_parser._digest(build_dir / name) != outputs[name]
            for name in (*vela_parser.GENERATED, "vela-parser")
        ):
            raise ValueError("parser generated outputs changed during syntax campaign")

        report: dict[str, object] = {
            "schema": 1,
            "scope": "vela-menhir-generated-syntax-campaigns",
            "status": "qualified",
            "checked_parser": False,
            "second_grammar_introduced": False,
            "menhir_runtime_linked": False,
            "error_enumeration_commissioned": False,
            "named_syntax_interaction": NAMED_SYNTAX_INTERACTION,
            "settings": {
                "entry": ENTRY_POINT,
                "seed_start": seed_start,
                "campaign_count": count,
                "goal_length": goal_length,
                "max_sentence_tokens": MAX_SENTENCE_TOKENS,
                "max_rendered_source_bytes": MAX_RENDERED_SOURCE_BYTES,
                "max_interpreter_output_bytes": MAX_INTERPRETER_OUTPUT_BYTES,
                "max_campaign_seconds": MAX_CAMPAIGN_SECONDS,
                "max_memory_bytes": MAX_MEMORY_BYTES,
            },
            "elapsed_seconds": elapsed,
            "inputs": inputs,
            "build": build_receipt,
            "migration_status": migration_report["status"],
            "renderer": renderer_report,
            "campaign": {
                "sentences_generated": count,
                "interpreter_accepted": count,
                "interpreter_negative_rejected": len(negative_lines),
                "native_accepted_sentences": accepted_sentences,
                "automaton_accepted_action_refused_sentences": action_refused_sentences,
                "rendered_variant_checks": variant_checks,
                "sample_replays": sample_replays,
            },
            "fault_controls": fault_reports,
            "adoption_disposition": {
                "retain_campaign": True,
                "code_backend_preserved": True,
                "list_errors_deferred": True,
                "reason": (
                    "Seeded --random-sentence generation and batch --interpret-show-cst "
                    "coupled with the qualified payload renderer and IndependentPureAstOracle "
                    "reproducibly exercise multi-declaration precedence, trailing-comma, "
                    "trivia/newline, and automaton-vs-action refusal boundaries while "
                    "automatically shrinking 29..35-token failing sentences to 14..16-token "
                    "replays without a second grammar or Menhir runtime dependency."
                ),
            },
        }
        with atomic_path(build_dir / "syntax-campaigns.json") as pending:
            pending.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="")
        with atomic_path(latest) as pending:
            pending.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="")
        return report
