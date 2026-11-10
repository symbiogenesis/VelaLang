# SPDX-License-Identifier: Apache-2.0
"""Secondary editor assets generated from the canonical Menhir syntax owner."""

import hashlib
import json
import re
from pathlib import Path

from toolchain.parser_checked import _strip_comments_and_actions

ASSETS = "tools/editor"
CONFLICTS = [
    ["postfix_with_19322a5ff8", "prefix_with_a37cc982c0"],
    ["value_identifier", "annotation_path"],
    ["type_modifier", "unary_operator"],
    ["lambda_parameter", "atom_with_e019598904"],
    ["parameter_open", "parenthesized_type_bba64590cf"],
    ["statement_expression", "local_kind"],
    ["prefix_with_cea602bb37", "postfix_with_6638f242a8"],
    ["qualified_name_0cae64d15c", "value_identifier"],
    ["qualified_name_0cae64d15c", "value_identifier", "annotation_path"],
    ["statement_expression", "open_paren", "parenthesized_type_bba64590cf", "atom_with_e019598904"],
    ["statement_expression", "open_paren", "parenthesized_type_bba64590cf"],
    ["qualified_name_0cae64d15c", "annotation_path"],
    ["open_paren", "parenthesized_type_bba64590cf"],
]
PUNCTUATION = {
    "LPAREN": "(", "RPAREN": ")", "LBRACE": "{", "RBRACE": "}", "LBRACKET": "[", "RBRACKET": "]",
    "SEMICOLON": ";", "COMMA": ",", "DOT": ".", "COLON": ":", "AT": "@", "QUESTION": "?",
    "RANGE": "..", "ARROW": "->", "FATARROW": "=>", "IMPLIES": "==>", "IFF": "<==>",
    "EQUAL": "=", "PLUS": "+", "STAR": "*", "EQ": "==", "LE": "<=", "MINUS": "-", "SLASH": "/",
    "PERCENT": "%", "LT": "<", "GT": ">", "GE": ">=", "NE": "!=", "AND": "&&", "OR": "||",
    "NOT": "!", "AMP": "&", "BAR": "|", "CARET": "^", "TILDE": "~", "PLUS_ASSIGN": "+=",
    "MINUS_ASSIGN": "-=", "STAR_ASSIGN": "*=", "SLASH_ASSIGN": "/=", "MOD_ASSIGN": "%=",
    "GENERIC_OPEN": "::<", "CALL_GENERIC_OPEN": "<", "ANNOTATION_OPEN": "(", "LAMBDA_OPEN": "(",
}


def _license_comment(prefix: str) -> str:
    return prefix + " SPDX-License-" + "Identifier: Apache-2.0"


def keywords(root: Path) -> dict[str, str]:
    """Read literal word/token pairs from the canonical lexer, including contextual types."""
    source = (root / "tools/toolchain/parser/lexer.mll").read_text(encoding="utf-8")
    section = source.split("let identifier state lexbuf =", 1)[1].split("let digit_run", 1)[0]
    pairs = {str(match[1]): str(match[2]) for match in re.finditer(r'\|\s*"([A-Za-z]+)"\s*->\s*([A-Z][A-Z_]+)', section)}
    pairs.update({"Nat": "NAT", "bool": "BOOL"})
    return pairs


def _call(name: str, *args: str) -> str:
    if not args:
        return ""
    if len(args) == 1 and name in {"seq", "choice"}:
        return args[0]
    return f"{name}({', '.join(args)})"


def _arguments(value: str) -> list[str]:
    start = value.index("(") + 1
    parts: list[str] = []
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(value) - 1):
        char = value[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:-1].strip())
    return parts


def _nullable(value: str, names: set[str]) -> bool:
    if value.startswith("$."):
        return value[2:] in names
    if value.startswith(("optional(", "repeat(")):
        return True
    if value.startswith("seq("):
        return all(_nullable(part, names) for part in _arguments(value))
    if value.startswith("choice("):
        return any(_nullable(part, names) for part in _arguments(value))
    return False


def tree_grammar(root: Path) -> str:
    """Translate Menhir productions and parameterized combinators, without semantic actions."""
    source = (root / "tools/toolchain/parser/parser.mly").read_text(encoding="utf-8")
    body = _strip_comments_and_actions(source.split("\n%%\n", 1)[1])
    headers = list(re.finditer(r"(?m)^(?:%inline\s+)?(\w+)(?:\(([^)]*)\))?\s*:", body))
    rules: dict[str, tuple[list[str], list[str]]] = {}
    for index, match in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
        rhs = re.sub(r"\b\w+\s*=\s*", "", body[match.end():end])
        rules[match[1]] = ([part.strip() for part in (match[2] or "").split(",") if part.strip()],
                            [part.strip() for part in rhs.split("|")])
    terminals = {token: json.dumps(word) for word, token in keywords(root).items()}
    terminals.update({name: json.dumps(value) for name, value in PUNCTUATION.items()})
    terminals.update({"IDENT": "$.identifier", "ANNOTATION_NAME": 'choice($.identifier, "Nat", "bool")',
                      "DECIMAL": "$.number", "NUMBER": "$.number", "STRING": "$.string",
                      "INTERPOLATED_STRING": "$.interpolated_string", "CHARACTER": "$.character",
                      "LIFETIME": "$.lifetime", "HOLE": "$.hole", "EOF": ""})
    emitted: dict[str, str] = {}
    pending: list[tuple[str, tuple[str, ...]]] = []
    instances: dict[tuple[str, tuple[str, ...]], str] = {}

    def expr(text: str, substitutions: dict[str, str]) -> str:
        symbols: list[str] = []
        cursor = 0
        while cursor < len(text):
            if text[cursor].isspace():
                cursor += 1
                continue
            match = re.match(r"\w+", text[cursor:])
            if match is None:
                raise ValueError(f"unsupported Menhir form: {text[cursor:]}")
            name = match[0]
            cursor += len(name)
            arguments: list[str] = []
            if cursor < len(text) and text[cursor] == "(":
                start = cursor + 1
                depth = 1
                cursor += 1
                while depth:
                    if text[cursor] == "(":
                        depth += 1
                    elif text[cursor] == ")":
                        depth -= 1
                    if depth == 0 or (text[cursor] == "," and depth == 1):
                        arguments.append(expr(text[start:cursor].strip(), substitutions))
                        start = cursor + 1
                    cursor += 1
            if name in substitutions:
                value = substitutions[name]
            elif name in terminals:
                value = terminals[name]
            elif name in {"list", "nonempty_list", "option", "ioption", "loption"}:
                value = _call({"list": "repeat", "nonempty_list": "repeat1"}.get(name, "optional"), *arguments)
            elif name in {"separated_list", "separated_nonempty_list"}:
                separator, item = arguments
                value = _call("seq", item, _call("repeat", _call("seq", separator, item)))
                if name == "separated_list":
                    value = _call("optional", value)
            elif name == "terminated":
                value = _call("seq", *arguments)
            elif name == "comma_list":
                item = arguments[0]
                value = _call("optional", _call("seq", item, _call("repeat", _call("seq", '","', item)), _call("optional", '","')))
            elif name == "comma_nonempty_list":
                item = arguments[0]
                value = _call("seq", item, _call("repeat", _call("seq", '","', item)), _call("optional", '","'))
            else:
                key = (name, tuple(arguments))
                if key not in instances:
                    suffix = "_" + hashlib.sha256(repr(key).encode()).hexdigest()[:10] if arguments else ""
                    instances[key] = (name.removeprefix("s_") + suffix)
                    pending.append(key)
                value = "$." + instances[key]
            if value:
                symbols.append(value)
        return _call("seq", *symbols)

    expr("surface_file", {})
    index = 0
    while index < len(pending):
        name, args = pending[index]
        index += 1
        params, alternatives = rules[name]
        substitutions = dict(zip(params, args, strict=True))
        options = list(dict.fromkeys(expr(part, substitutions) for part in alternatives))
        if "" in options:
            options.remove("")
            value = _call("optional", _call("choice", *options))
        else:
            value = _call("choice", *options)
        emitted[instances[(name, args)]] = value
    # Nullable owner productions are expanded at their call sites; Tree-sitter
    # permits empty matches only in the start rule.
    names: set[str] = set()
    for _ in range(len(emitted)):
        found = {name for name, value in emitted.items() if _nullable(value, names)}
        if found == names:
            break
        names = found
    nullable = {name: value for name, value in emitted.items() if name in names}
    for _ in range(len(nullable) + 1):
        changed = False
        for name, value in list(emitted.items()):
            current = value
            for empty_name, expansion in nullable.items():
                replacement = re.sub(r"\$\." + empty_name + r"\b", lambda _, expansion=expansion: expansion, current)
                changed |= replacement != current
                current = replacement
            emitted[name] = current
        if not changed:
            break
    for name in nullable:
        emitted.pop(name)
    lines = [_license_comment("//"), "// Generated from the canonical Menhir productions; regenerate with vela-highlight.",
             "module.exports = grammar({", "  name: 'vela',", "  word: $ => $.identifier,",
             "  extras: $ => [/\\s/, $.line_comment, $.block_comment],",
             "  externals: $ => [$.block_comment, $.raw_string, $.interpolated_string],",
             "  conflicts: $ => [" + ", ".join("[" + ", ".join("$." + name for name in group) + "]" for group in CONFLICTS) + "],",
             "  rules: {"]
    for name, value in emitted.items():
        lines.append(f"    {name}: $ => {value},")
    lines.extend([
        r"    identifier: $ => /[A-Za-z_][A-Za-z_0-9]*/,",
        r"    number: $ => /[0-9][A-Za-z_0-9]*/,",
        r"""    string: $ => choice($.raw_string, token(seq('"', repeat(choice(/[^"\\\r\n]/, /\\./)), '"'))),""",
        r"""    character: $ => token(seq("'", choice(/[^'\\\r\n]/, /\\./), "'")),""",
        r"    lifetime: $ => /'[A-Za-z_][A-Za-z_0-9]*(\.[A-Za-z_][A-Za-z_0-9]*)*/,",
        r"    hole: $ => /\?[A-Za-z_][A-Za-z_0-9]*/,",
        r"    line_comment: $ => token(seq('//', /[^\r\n]*/)),",
        "  },", "});", ""])
    return "\n".join(lines)


def textmate_grammar(root: Path) -> dict[str, object]:
    """Build lexical scopes from the same keyword inventory as the compiler lexer."""
    words = sorted(set(keywords(root)) - {"Nat", "bool", "true", "false"})
    return {
        "name": "Vela", "scopeName": "source.vela", "fileTypes": ["vela"],
        "patterns": [{"include": "#comments"}, {"include": "#raw-string"}, {"include": "#interpolated"},
                     {"include": "#string"}, {"include": "#character"}, {"include": "#tokens"}],
        "repository": {
            "comments": {"patterns": [{"name": "comment.line.double-slash.vela", "match": "//.*$"},
                                        {"include": "#block-comment"}]},
            "block-comment": {"name": "comment.block.vela", "begin": "/\\*", "end": "\\*/",
                              "patterns": [{"include": "#block-comment"}]},
            "raw-string": {"name": "string.quoted.other.raw.vela", "begin": '("{3,})', "end": '\\1(?!")'},
            "interpolated": {"name": "string.quoted.double.interpolated.vela", "begin": '\\$"', "end": '"',
                             "patterns": [{"name": "constant.character.escape.vela", "match": r"\\.|\{\{|\}\}"},
                                          {"name": "meta.interpolation.vela", "begin": r"\{(?!\{)", "end": r"\}",
                                           "patterns": [{"include": "#interpolation-brace"}, {"include": "$self"}]}]},
            "interpolation-brace": {"name": "meta.interpolation.block.vela", "begin": r"\{", "end": r"\}",
                                    "patterns": [{"include": "#interpolation-brace"}, {"include": "$self"}]},
            "string": {"name": "string.quoted.double.vela", "begin": '"', "end": '"|(?=$)',
                       "patterns": [{"name": "constant.character.escape.vela", "match": r"\\."}]},
            "character": {"name": "string.quoted.single.vela", "match": r"'(?:[^'\\\r\n]|\\.)'"},
            "tokens": {"patterns": [
                {"name": "keyword.control.vela", "match": r"\b(?:" + "|".join(words) + r")\b"},
                {"name": "storage.type.vela", "match": r"\b(?:Nat|bool)\b"},
                {"name": "constant.language.vela", "match": r"\b(?:true|false)\b"},
                {"name": "constant.numeric.vela", "match": r"\b[0-9][A-Za-z_0-9]*\b"},
                {"name": "entity.name.type.lifetime.vela", "match": r"'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*"},
                {"name": "invalid.deprecated.hole.vela", "match": r"\?[A-Za-z_][A-Za-z_0-9]*"},
                {"name": "keyword.operator.vela", "match": r"[+*/%=!<>&|^~?:@-]+"},
                {"name": "punctuation.separator.vela", "match": r"[(){}\[\],;.]"},
            ]},
        },
    }


def generated_assets(root: Path) -> dict[str, str]:
    """Return deterministic authored-asset bytes; generated parser/runtime bytes stay outside Git."""
    queries = [_license_comment(";"), "(identifier) @variable", "(number) @number",
               "(string) @string", "(character) @string", "(interpolated_string) @string",
               "(line_comment) @comment", "(block_comment) @comment", "(lifetime) @label", "(hole) @error",
               '["Nat" "bool"] @type.builtin',
               '((identifier) @type.builtin (#match? @type.builtin "^(Nat|bool)$"))',
               '["true" "false"] @boolean']
    words = sorted(set(keywords(root)) - {"Nat", "bool", "true", "false"})
    queries.append("[" + " ".join(json.dumps(word) for word in words) + "] @keyword")
    queries.append('["(" ")" "{" "}" "[" "]"] @punctuation.bracket')
    queries.append('[";" "," "."] @punctuation.delimiter')
    return {
        "tree-sitter/grammar.js": tree_grammar(root),
        "tree-sitter/queries/highlights.scm": "\n".join(queries) + "\n",
        "textmate/vela.tmLanguage.json": json.dumps(textmate_grammar(root), indent=2, ensure_ascii=False) + "\n",
    }
