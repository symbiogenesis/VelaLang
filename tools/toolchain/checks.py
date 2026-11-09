# SPDX-License-Identifier: Apache-2.0
"""Repository-wide REUSE, SPDX header, EditorConfig, glyph, and source-reference checks."""

import ast
import configparser
import io
import re
import subprocess
import sys
import sysconfig
import tokenize
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import toolchain as vela
from toolchain import authoring, corpus, markdown, toolenv
from toolchain.cli import typecheck
from toolchain.report import Reporter

TIMEOUT = 120

_SPDX_TAG = "SPDX-License-" + "Identifier:"
_SPDX_FENCE_RE = re.compile(rf"```(?:text)?\n(# {_SPDX_TAG} ([A-Za-z0-9.-]+))\n```")
_LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\s]+)\)")
_HASH_NAMES = frozenset({".editorconfig", ".gitattributes", ".gitignore", "REUSE.toml"})
_NO_MARK_SUFFIXES = (".md", ".json", ".lock")
_SOURCE_REF_SUFFIXES = (
    ".py",
    ".vela",
    ".ml",
    ".mli",
    ".mll",
    ".mly",
    ".v",
    ".mjs",
    ".js",
    ".css",
    ".yml",
    ".yaml",
)
_PURE_EXAMPLES = frozenset({
    "examples/pure.vela",
    "examples/constants.vela",
    "examples/expressions.vela",
})
_FORMATTED_EXAMPLES = frozenset({
    "examples/pure.vela",
    "examples/constants.vela",
})

_FORBIDDEN_CODEPOINTS = frozenset({
    0x200B, 0x200C, 0x200D, 0x200E, 0x200F,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2060, 0x2066, 0x2067, 0x2068, 0x2069,
    0xFEFF, 0xFFFD,
})
_MOJIBAKE_TOKENS = (
    "\u00e2\u20ac\u201d",
    "\u00e2\u20ac\u201c",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u0153",
    "\u00c3\u00a9",
    "\u00c3\u00a8",
    "\u00c3\u00a2",
    "\u00c2\u00a7",
    "\u00c2\u00b7",
)

_JS_KEYWORDS = frozenset({
    "async", "await", "break", "case", "catch", "class", "const", "continue",
    "debugger", "default", "delete", "do", "else", "export", "extends", "false",
    "finally", "for", "from", "function", "if", "import", "in", "instanceof",
    "let", "new", "null", "of", "return", "static", "super", "switch", "this",
    "throw", "true", "try", "typeof", "undefined", "var", "void", "while",
    "with", "yield",
})

_JS_GLOBALS = frozenset({
    "AbortController", "Array", "Blob", "Boolean", "BigInt", "Console",
    "CustomEvent", "DataView", "Date", "Document", "Element", "Error", "Event",
    "EventSource", "FileReader", "Float32Array", "Float64Array", "FormData",
    "Function", "HTMLElement", "Headers", "History", "Image", "Infinity",
    "Int8Array", "Int16Array", "Int32Array", "Intl", "JSON", "KeyboardEvent",
    "Map", "Math", "MouseEvent", "MutationObserver", "NaN", "Node", "NodeList",
    "Number", "Object", "Promise", "Proxy", "RangeError", "ReferenceError",
    "Reflect", "RegExp", "ResizeObserver", "Request", "Response", "Set",
    "SharedArrayBuffer", "String", "Symbol", "SyntaxError", "TextDecoder",
    "TextEncoder", "TypeError", "URIError", "URL", "URLSearchParams",
    "Uint8Array", "Uint8ClampedArray", "Uint16Array", "Uint32Array", "WeakMap",
    "WeakSet", "WebSocket", "Window", "Worker", "alert", "atob", "btoa",
    "cancelAnimationFrame", "clearInterval", "clearTimeout", "confirm",
    "console", "crypto", "decodeURI", "decodeURIComponent", "document",
    "encodeURI", "encodeURIComponent", "eval", "fetch", "getComputedStyle",
    "globalThis", "history", "isFinite", "isNaN", "localStorage", "location",
    "navigator", "parseFloat", "parseInt", "performance", "process",
    "queueMicrotask", "requestAnimationFrame", "self", "sessionStorage",
    "setInterval", "setTimeout", "structuredClone", "window",
})

_JS_REGEX_PREV_PUNC = frozenset({
    "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "${",
    "+", "-", "*", "/", "%", "~", "^", "<", ">", "<=", ">=", "==", "!=",
    "===", "!==", "&&", "||", "??", "=>", "...", "+=", "-=", "*=", "/=",
    "%=", "&&=", "||=", "??=",
})

_JS_REGEX_PREV_KW = frozenset({
    "return", "throw", "case", "in", "of", "typeof", "void", "delete",
    "new", "instanceof", "yield", "await", "else", "do",
})

_JS_NON_METHOD_HEADS = frozenset({
    "if", "for", "while", "switch", "catch", "with", "return", "throw",
    "typeof", "delete", "void", "new", "await", "yield", "case", "in",
    "of", "instanceof", "else",
})

_JS_MULTI_OPS = (
    "===", "!==", ">>>", "<<=", ">>=", "&&=", "||=", "??=", "...",
    "<=", ">=", "==", "!=", "&&", "||", "??", "=>", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<", ">>", "?.",
)

_HTML_ID_RE = re.compile(r'\bid="([^"]+)"')
_HTML_TAB_RE = re.compile(r'\bdata-tab="([^"]+)"')
_HTML_LOAD_EXAMPLE_RE = re.compile(r'\bdata-load-example="([^"]+)"')
_HTML_EXPAND_TARGET_RE = re.compile(r'\bdata-expand-target="([^"]+)"')
_HTML_ARIA_CONTROLS_RE = re.compile(r'\baria-controls="([^"]+)"')
_HTML_EXAMPLES_SELECT_RE = re.compile(r'<select[^>]*\bid="examples"[^>]*>(.*?)</select>', re.DOTALL)
_HTML_OPTION_VALUE_RE = re.compile(r'<option[^>]*\bvalue="([^"]+)"')
_JS_DOLLAR_ID_RE = re.compile(r'\$\(\s*"([A-Za-z0-9_-]+)"\s*\)')
_JS_SELECT_TAB_RE = re.compile(r'\bselectTab\(\s*"([A-Za-z0-9_-]+)"\s*\)')


def _reuse_executable() -> Path | None:
    scripts = Path(sysconfig.get_path("scripts"))
    candidate = scripts / ("reuse.exe" if sys.platform == "win32" else "reuse")
    return candidate if candidate.is_file() else None


def reuse_findings(root: Path) -> list[str]:
    """Run the pinned FSFE REUSE v3.3 linter against REUSE.toml and LICENSES/."""
    try:
        pin = toolenv.checker_pins(root)["reuse"]
    except (OSError, TypeError, ValueError, KeyError) as err:
        return [f"cannot read pinned reuse version: {err}"]
    executable = _reuse_executable()
    if executable is None:
        return [
            f"reuse {pin} is not installed in the tools environment; "
            "run a command through tools/run.py to synchronize tools/uv.lock"
        ]
    try:
        ver = subprocess.run(
            [str(executable), "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as err:
        return [f"reuse --version failed: {err}"]
    first_line = ver.stdout.splitlines()[0].strip() if ver.stdout else ""
    if ver.returncode != 0 or first_line != f"reuse, version {pin}":
        return [
            f"reuse ({first_line or 'unknown'}) does not match pinned {pin}; "
            "run a command through tools/run.py to synchronize tools/uv.lock"
        ]
    try:
        done = subprocess.run(
            [str(executable), "--root", str(root), "lint", "--lines"],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as err:
        return [f"reuse lint failed: {err}"]
    lines = [line.strip() for line in done.stdout.splitlines() if line.strip()]
    if done.returncode == 0 and not lines:
        return []
    if lines:
        return lines
    detail = (done.stderr.strip() or done.stdout.strip())[-200:]
    return [f"reuse lint exited {done.returncode}: {detail}"]


def _expected_spdx_ident(loaded: corpus.Corpus) -> tuple[str | None, list[str]]:
    doc = loaded.get("COPYRIGHT.md")
    if doc is None:
        return None, ["COPYRIGHT.md is missing from the indexed corpus"]
    match = _SPDX_FENCE_RE.search(doc.raw)
    if match is None:
        return None, [f"COPYRIGHT.md does not declare a canonical `# {_SPDX_TAG}` block"]
    return str(match.group(2)), []


def marks_findings(root: Path, loaded: corpus.Corpus) -> list[str]:
    """Hold every markable file to the SPDX header syntax for its file kind."""
    ident, findings = _expected_spdx_ident(loaded)
    if ident is None:
        return findings
    tag = f"{_SPDX_TAG} {ident}"
    expected_by_suffix: dict[str, tuple[str, ...]] = {
        ".py": (f"# {tag}",),
        ".toml": (f"# {tag}",),
        ".yml": (f"# {tag}",),
        ".yaml": (f"# {tag}",),
        ".ml": (f"(* {tag} *)",),
        ".mli": (f"(* {tag} *)",),
        ".mll": (f"(* {tag} *)",),
        ".v": (f"(* {tag} *)",),
        ".mly": (f"/* {tag} */",),
        ".css": (f"/* {tag} */",),
        ".mjs": (f"// {tag}",),
        ".js": (f"// {tag}",),
        ".vela": (f"/* {tag} */", f"// {tag}"),
        ".html": (f"<!-- {tag} -->",),
    }
    hash_mark = (f"# {tag}",)
    for rel in loaded.tracked:
        if rel.startswith("LICENSES/") and rel.endswith(".txt"):
            continue
        if rel.endswith(_NO_MARK_SUFFIXES):
            continue
        name = PurePosixPath(rel).name
        suffix = PurePosixPath(rel).suffix
        allowed = hash_mark if name in _HASH_NAMES else expected_by_suffix.get(suffix)
        if allowed is None:
            findings.append(f"{rel}: file kind has no SPDX comment syntax ruling")
            continue
        try:
            lines = (root / rel).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as err:
            findings.append(f"{rel}: cannot read file for SPDX check: {err}")
            continue
        if not lines:
            findings.append(f"{rel}: empty file is missing its opening SPDX mark")
            continue
        first = lines[1] if lines[0].startswith("#!") and len(lines) > 1 else lines[0]
        if first not in allowed:
            findings.append(f"{rel}: expected opening mark {allowed[0]!r}, found {first!r}")
    return findings


def editorconfig_findings(root: Path, tracked: Sequence[str]) -> list[str]:
    """Enforce .editorconfig UTF-8, LF, single final newline, trailing-space, and tab rules."""
    cfg_path = root / ".editorconfig"
    if not cfg_path.is_file():
        return [".editorconfig is missing from the repository root"]
    parser = configparser.ConfigParser()
    try:
        parser.read_string("[__root__]\n" + cfg_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, configparser.Error) as err:
        return [f".editorconfig could not be parsed: {err}"]
    if "*" not in parser or parser["*"].get("end_of_line") != "lf":
        return [".editorconfig must declare [*] with end_of_line = lf"]
    findings: list[str] = []
    for rel in tracked:
        try:
            raw = (root / rel).read_bytes()
        except OSError as err:
            findings.append(f"{rel}: cannot read bytes: {err}")
            continue
        if raw.startswith(b"\xef\xbb\xbf"):
            findings.append(f"{rel}:1: UTF-8 BOM is not permitted")
        if b"\r" in raw:
            findings.append(f"{rel}: CR byte is not permitted (end_of_line = lf)")
        if not raw.endswith(b"\n"):
            findings.append(f"{rel}: missing final newline")
        elif raw.endswith(b"\n\n"):
            findings.append(f"{rel}: multiple trailing newlines at end of file")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as err:
            findings.append(f"{rel}: invalid UTF-8 ({err})")
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.endswith((" ", "\t")):
                findings.append(f"{rel}:{lineno}: trailing whitespace is not permitted")
            if line.startswith("\t"):
                findings.append(f"{rel}:{lineno}: leading tab indentation is not permitted")
    return findings


def glyph_findings(root: Path, tracked: Sequence[str]) -> list[str]:
    """Refuse bidi/zero-width formatting characters, control characters, tabs, and mojibake."""
    findings: list[str] = []
    for rel in tracked:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            findings.append(f"{rel}: cannot read UTF-8 text: {err}")
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            findings.extend(
                f"{rel}:{lineno}:{col}: forbidden control or formatting character U+{ord(ch):04X}"
                for col, ch in enumerate(line, 1)
                if ord(ch) in _FORBIDDEN_CODEPOINTS or (ord(ch) < 0x20 and ch != "\n") or ord(ch) == 0x7F
            )
            findings.extend(
                f"{rel}:{lineno}: suspected UTF-8/CP1252 mojibake {token!r}"
                for token in _MOJIBAKE_TOKENS
                if token in line
            )
    return findings


def _comment_and_docstring_chunks(rel: str, text: str) -> list[tuple[int, str]]:
    chunks: list[tuple[int, str]] = []
    if rel.endswith(".py"):
        try:
            tree = ast.parse(text, filename=rel)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    body = node.body
                    if (
                        body
                        and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)
                    ):
                        chunks.append((body[0].lineno, body[0].value.value))
            chunks.extend(
                (tok.start[0], tok.string)
                for tok in tokenize.generate_tokens(io.StringIO(text).readline)
                if tok.type == tokenize.COMMENT
            )
        except (SyntaxError, tokenize.TokenError) as err:
            chunks.append((1, f"[invalid-python](__syntax_error__:{err})"))
        return chunks
    if rel.endswith((".yml", ".yaml")):
        return [
            (lineno, line)
            for lineno, line in enumerate(text.splitlines(), 1)
            if line.lstrip().startswith("#")
        ]
    return [
        (lineno, line)
        for lineno, line in enumerate(text.splitlines(), 1)
        if any(marker in line for marker in ("//", "/*", "(*"))
    ]


def source_ref_findings(root: Path, loaded: corpus.Corpus) -> list[str]:
    """Verify relative Markdown links and #fragments in source comments and docstrings."""
    findings: list[str] = []
    base = root.resolve()
    indexed = loaded.indexed
    directories = {
        parent.as_posix()
        for path in indexed
        for parent in PurePosixPath(path).parents
        if parent.as_posix() != "."
    }
    for rel in loaded.tracked:
        if not rel.endswith(_SOURCE_REF_SUFFIXES):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            findings.append(f"{rel}: cannot read source file: {err}")
            continue
        parent_dir = (base / rel).parent
        for lineno, chunk in _comment_and_docstring_chunks(rel, text):
            for match in _LINK_RE.finditer(chunk):
                url = match.group(2)
                if (
                    url.startswith(("http://", "https://", "mailto:", "#"))
                    or "<" in url
                    or "{" in url
                ):
                    continue
                path_part, sep, fragment = url.partition("#")
                if not path_part:
                    continue
                resolved = (parent_dir / path_part).resolve()
                if not resolved.is_relative_to(base):
                    findings.append(f"{rel}:{lineno}: link {url!r} escapes repository root")
                    continue
                target_rel = resolved.relative_to(base).as_posix()
                if target_rel not in indexed and target_rel not in directories:
                    findings.append(
                        f"{rel}:{lineno}: relative link {url!r} resolves to untracked path {target_rel!r}"
                    )
                    continue
                if sep and target_rel.endswith(".md"):
                    doc = loaded.get(target_rel)
                    if doc is not None and fragment not in doc.targets:
                        findings.append(
                            f"{rel}:{lineno}: link {url!r} fragment #{fragment} not found in {target_rel}"
                        )
    return findings


def vela_example_findings(root: Path, tracked: Sequence[str]) -> list[str]:
    """Check tracked pure Vela example files for translation and canonical layout."""
    findings: list[str] = []
    for rel in tracked:
        if rel not in _PURE_EXAMPLES:
            continue
        try:
            raw = (root / rel).read_bytes()
        except OSError as err:
            findings.append(f"{rel}: cannot read Vela example: {err}")
            continue
        try:
            vela.translate(raw)
        except vela.VelaError as err:
            findings.append(f"{rel}: pure Vela example failed translation: {err.message}")
            continue
        if rel in _FORMATTED_EXAMPLES:
            try:
                formatted = authoring.format_source(raw)
            except vela.VelaError as err:
                findings.append(f"{rel}: pure Vela example failed formatting: {err.message}")
                continue
            if formatted != raw:
                findings.append(f"{rel}: pure Vela example is not in canonical format_source layout")
    return findings


def _tokenize_js(rel: str, src: str) -> tuple[list[tuple[str, str, int, int]], list[str]]:
    tokens: list[tuple[str, str, int, int]] = []
    findings: list[str] = []
    delim_stack: list[tuple[str, int, int, bool]] = []
    n = len(src)
    i = 0
    line = 1
    col = 1

    def scan_template(pos: int, ln: int, cl: int) -> tuple[int, int, int]:
        seg_ln, seg_cl = ln, cl
        while pos < n:
            c = src[pos]
            if c == "\\":
                if pos + 1 < n and src[pos + 1] == "\n":
                    ln += 1
                    cl = 1
                else:
                    cl += 2
                pos += 2
                continue
            if c == "`":
                tokens.append(("tpl", "``", seg_ln, seg_cl))
                return pos + 1, ln, cl + 1
            if c == "$" and pos + 1 < n and src[pos + 1] == "{":
                tokens.append(("tpl", "``", seg_ln, seg_cl))
                tokens.append(("punc", "${", ln, cl))
                delim_stack.append(("}", ln, cl, True))
                return pos + 2, ln, cl + 2
            if c == "\n":
                ln += 1
                cl = 1
            else:
                cl += 1
            pos += 1
        findings.append(f"{rel}:{seg_ln}:{seg_cl}: unterminated template literal")
        return pos, ln, cl

    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1
            col = 1
            i += 1
            continue
        if ch in " \t\r":
            col += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            s_ln, s_cl = line, col
            i += 2
            col += 2
            closed = False
            while i < n:
                if src[i] == "*" and i + 1 < n and src[i + 1] == "/":
                    i += 2
                    col += 2
                    closed = True
                    break
                if src[i] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1
            if not closed:
                findings.append(f"{rel}:{s_ln}:{s_cl}: unterminated block comment")
            continue
        if ch in ('"', "'"):
            quote = ch
            s_ln, s_cl = line, col
            i += 1
            col += 1
            buf: list[str] = []
            closed = False
            while i < n:
                c = src[i]
                if c == "\\":
                    if i + 1 < n:
                        buf.append(src[i : i + 2])
                    i += 2
                    col += 2
                    continue
                if c == quote:
                    i += 1
                    col += 1
                    closed = True
                    break
                if c == "\n":
                    break
                buf.append(c)
                i += 1
                col += 1
            if not closed:
                findings.append(f"{rel}:{s_ln}:{s_cl}: unterminated string literal")
            tokens.append(("str", "".join(buf), s_ln, s_cl))
            continue
        if ch == "`":
            i, line, col = scan_template(i + 1, line, col + 1)
            continue
        if ch == "/":
            prev = tokens[-1] if tokens else None
            is_regex = (
                prev is None
                or (prev[0] == "punc" and prev[1] in _JS_REGEX_PREV_PUNC)
                or (prev[0] == "id" and prev[1] in _JS_REGEX_PREV_KW)
            )
            if is_regex and not (
                i + 1 < n and src[i + 1] == "=" and prev is not None and prev[0] in {"id", "num"}
            ):
                s_ln, s_cl = line, col
                i += 1
                col += 1
                in_class = False
                closed = False
                while i < n:
                    c = src[i]
                    if c == "\\":
                        i += 2
                        col += 2
                        continue
                    if c == "[":
                        in_class = True
                    elif c == "]":
                        in_class = False
                    elif c == "/" and not in_class:
                        i += 1
                        col += 1
                        while i < n and src[i].isalpha():
                            i += 1
                            col += 1
                        closed = True
                        break
                    elif c == "\n":
                        break
                    i += 1
                    col += 1
                if not closed:
                    findings.append(f"{rel}:{s_ln}:{s_cl}: unterminated regular expression literal")
                tokens.append(("rx", "//", s_ln, s_cl))
                continue
        if ch.isalpha() or ch in "_$":
            s_ln, s_cl = line, col
            start = i
            i += 1
            col += 1
            while i < n and (src[i].isalnum() or src[i] in "_$"):
                i += 1
                col += 1
            tokens.append(("id", src[start:i], s_ln, s_cl))
            continue
        if ch.isdigit():
            s_ln, s_cl = line, col
            start = i
            i += 1
            col += 1
            while i < n and (src[i].isalnum() or src[i] in "_."):
                i += 1
                col += 1
            tokens.append(("num", src[start:i], s_ln, s_cl))
            continue
        matched_op = next((op for op in _JS_MULTI_OPS if src.startswith(op, i)), None)
        if matched_op is not None:
            tokens.append(("punc", matched_op, line, col))
            i += len(matched_op)
            col += len(matched_op)
            continue
        if ch in "({[":
            close = {"(": ")", "{": "}", "[": "]"}[ch]
            delim_stack.append((close, line, col, False))
            tokens.append(("punc", ch, line, col))
            i += 1
            col += 1
            continue
        if ch in ")}]":
            if not delim_stack or delim_stack[-1][0] != ch:
                findings.append(f"{rel}:{line}:{col}: unmatched delimiter {ch!r}")
                tokens.append(("punc", ch, line, col))
                i += 1
                col += 1
                continue
            _, _, _, is_tpl = delim_stack.pop()
            tokens.append(("punc", ch, line, col))
            i += 1
            col += 1
            if is_tpl:
                i, line, col = scan_template(i, line, col)
            continue
        tokens.append(("punc", ch, line, col))
        i += 1
        col += 1

    findings.extend(
        f"{rel}:{ln}:{cl}: unclosed delimiter expecting {expected!r}"
        for expected, ln, cl, _ in delim_stack
    )
    return tokens, findings


def _collect_js_pattern_ids(
    tokens: Sequence[tuple[str, str, int, int]],
    start: int,
    stop_tokens: frozenset[str],
) -> tuple[set[str], int]:
    declared: set[str] = set()
    j = start
    m = len(tokens)
    depth = 0
    skip_default_depth: int | None = None
    while j < m:
        tk, tv, _, _ = tokens[j]
        if skip_default_depth is not None:
            if tk == "punc" and tv in {"(", "[", "{", "${"}:
                depth += 1
            elif tk == "punc" and tv in {")", "]", "}"}:
                if depth == skip_default_depth:
                    skip_default_depth = None
                    continue
                depth -= 1
            elif tk == "punc" and tv == "," and depth == skip_default_depth:
                skip_default_depth = None
                j += 1
                continue
            j += 1
            continue
        if depth == 0 and tk in {"punc", "id"} and tv in stop_tokens:
            break
        if tk == "punc" and tv in {"(", "[", "{", "${"}:
            depth += 1
        elif tk == "punc" and tv in {")", "]", "}"}:
            if depth == 0:
                break
            depth -= 1
        elif tk == "punc" and tv == "=":
            if "=" in stop_tokens and depth == 0:
                break
            skip_default_depth = depth
        elif tk == "id" and tv not in _JS_KEYWORDS:
            nxt = tokens[j + 1] if j + 1 < m else None
            if nxt is not None and nxt[0] == "punc" and nxt[1] == ":":
                j += 1
            else:
                declared.add(tv)
        j += 1
    return declared, j


def _collect_js_declarations(tokens: Sequence[tuple[str, str, int, int]]) -> set[str]:
    declared: set[str] = set()
    m = len(tokens)
    decl_stops = frozenset({"=", ";", "in", "of", ","})
    paren_stops = frozenset({")"})
    for idx, (kind, val, _, _) in enumerate(tokens):
        if kind == "id" and val in {"const", "let", "var"}:
            j = idx + 1
            while j < m:
                ids, j = _collect_js_pattern_ids(tokens, j, decl_stops)
                declared.update(ids)
                if j < m and tokens[j][0] == "punc" and tokens[j][1] == "=":
                    j += 1
                    d = 0
                    while j < m:
                        tk, tv, _, _ = tokens[j]
                        if tk == "punc" and tv in {"(", "[", "{", "${"}:
                            d += 1
                        elif tk == "punc" and tv in {")", "]", "}"}:
                            if d == 0:
                                break
                            d -= 1
                        elif d == 0 and tk == "punc" and tv in {",", ";"}:
                            break
                        j += 1
                if j < m and tokens[j][0] == "punc" and tokens[j][1] == ",":
                    j += 1
                    continue
                break
        elif kind == "id" and val in {"function", "class"}:
            j = idx + 1
            if j < m and tokens[j][0] == "punc" and tokens[j][1] == "*":
                j += 1
            if j < m and tokens[j][0] == "id" and tokens[j][1] not in _JS_KEYWORDS:
                declared.add(tokens[j][1])
                j += 1
            if val == "function" and j < m and tokens[j][0] == "punc" and tokens[j][1] == "(":
                ids, _ = _collect_js_pattern_ids(tokens, j + 1, paren_stops)
                declared.update(ids)
        elif (
            kind == "id"
            and val == "catch"
            and idx + 1 < m
            and tokens[idx + 1][0] == "punc"
            and tokens[idx + 1][1] == "("
        ):
            ids, _ = _collect_js_pattern_ids(tokens, idx + 2, paren_stops)
            declared.update(ids)
        elif kind == "id" and val == "import":
            j = idx + 1
            while (
                j < m
                and not (tokens[j][0] == "id" and tokens[j][1] == "from")
                and not (tokens[j][0] == "punc" and tokens[j][1] == ";")
            ):
                if tokens[j][0] == "id" and tokens[j][1] not in _JS_KEYWORDS and tokens[j][1] != "as":
                    if j + 1 < m and tokens[j + 1][0] == "id" and tokens[j + 1][1] == "as":
                        j += 2
                        if j < m and tokens[j][0] == "id":
                            declared.add(tokens[j][1])
                    else:
                        declared.add(tokens[j][1])
                j += 1
        elif kind == "punc" and val == "=>":
            if idx - 1 >= 0:
                prev_k, prev_v, _, _ = tokens[idx - 1]
                if prev_k == "id" and prev_v not in _JS_KEYWORDS:
                    declared.add(prev_v)
                elif prev_k == "punc" and prev_v == ")":
                    d = 1
                    j = idx - 2
                    while j >= 0 and d > 0:
                        tk, tv, _, _ = tokens[j]
                        if tk == "punc" and tv == ")":
                            d += 1
                        elif tk == "punc" and tv == "(":
                            d -= 1
                        j -= 1
                    ids, _ = _collect_js_pattern_ids(tokens, j + 2, paren_stops)
                    declared.update(ids)
        elif (
            kind == "punc"
            and val == "("
            and idx - 1 >= 0
            and tokens[idx - 1][0] == "id"
            and tokens[idx - 1][1] not in _JS_NON_METHOD_HEADS
        ):
            ids, end_j = _collect_js_pattern_ids(tokens, idx + 1, paren_stops)
            if end_j + 1 < m and tokens[end_j + 1][0] == "punc" and tokens[end_j + 1][1] == "{":
                declared.update(ids)
    return declared


def _js_module_findings(rel: str, text: str) -> list[str]:
    tokens, findings = _tokenize_js(rel, text)
    if findings:
        return findings
    declared = _collect_js_declarations(tokens)
    known = declared | _JS_GLOBALS | _JS_KEYWORDS
    paren_stops = frozenset({")"})
    m = len(tokens)
    for idx, (kind, val, ln, cl) in enumerate(tokens):
        if kind != "id" or val in known:
            continue
        prev = tokens[idx - 1] if idx > 0 else None
        nxt = tokens[idx + 1] if idx + 1 < m else None
        if prev is not None and prev[0] == "punc" and prev[1] in {".", "?."}:
            continue
        if (
            nxt is not None
            and nxt[0] == "punc"
            and nxt[1] == ":"
            and prev is not None
            and prev[0] == "punc"
            and prev[1] in {"{", ","}
        ):
            continue
        if (
            val in {"get", "set"}
            and nxt is not None
            and nxt[0] == "id"
            and idx + 2 < m
            and tokens[idx + 2][0] == "punc"
            and tokens[idx + 2][1] == "("
        ):
            continue
        if nxt is not None and nxt[0] == "punc" and nxt[1] == "(":
            _, end_j = _collect_js_pattern_ids(tokens, idx + 2, paren_stops)
            if end_j + 1 < m and tokens[end_j + 1][0] == "punc" and tokens[end_j + 1][1] == "{":
                continue
        findings.append(f"{rel}:{ln}:{cl}: reference to undeclared JavaScript identifier {val!r}")
    return findings


def _extract_js_object_keys(
    tokens: Sequence[tuple[str, str, int, int]],
    const_name: str,
) -> set[str] | None:
    m = len(tokens)
    for idx in range(m - 2):
        if (
            tokens[idx][0] == "id"
            and tokens[idx][1] == const_name
            and tokens[idx + 1][0] == "punc"
            and tokens[idx + 1][1] == "="
            and tokens[idx + 2][0] == "punc"
            and tokens[idx + 2][1] == "{"
        ):
            keys: set[str] = set()
            depth = 1
            j = idx + 3
            while j < m and depth > 0:
                tk, tv, _, _ = tokens[j]
                if tk == "punc" and tv in {"{", "(", "[", "${"}:
                    depth += 1
                elif tk == "punc" and tv in {"}", ")", "]"}:
                    depth -= 1
                elif (
                    depth == 1
                    and tk == "id"
                    and j + 1 < m
                    and tokens[j + 1][0] == "punc"
                    and tokens[j + 1][1] == ":"
                    and tokens[j - 1][0] == "punc"
                    and tokens[j - 1][1] in {"{", ","}
                ):
                    keys.add(tv)
                j += 1
            return keys
    return None


def _playground_asset_findings(root: Path, loaded: corpus.Corpus) -> list[str]:
    indexed = loaded.indexed
    findings: list[str] = [
        f"{rel}: duplicate playground asset; docs/ is the single canonical asset directory"
        for rel in sorted(indexed)
        if rel.startswith("tools/toolchain/playground/")
    ]

    app_rel = "docs/app.mjs"
    html_rel = "docs/index.html"
    if app_rel not in indexed or html_rel not in indexed:
        return findings
    try:
        app_text = (root / app_rel).read_text(encoding="utf-8")
        html_text = (root / html_rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        findings.append(f"{app_rel}: cannot read playground assets: {err}")
        return findings

    html_ids = set(_HTML_ID_RE.findall(html_text))
    html_tabs = set(_HTML_TAB_RE.findall(html_text))
    findings.extend(
        f"{app_rel}: DOM lookup $({dom_id!r}) has no matching id in {html_rel}"
        for dom_id in sorted(set(_JS_DOLLAR_ID_RE.findall(app_text)) - html_ids)
    )
    findings.extend(
        f"{html_rel}: [data-tab={tab!r}] has no matching id='{tab}-panel'"
        for tab in sorted(html_tabs)
        if f"{tab}-panel" not in html_ids
    )
    findings.extend(
        f"{app_rel}: selectTab({tab!r}) has no matching [data-tab={tab!r}] in {html_rel}"
        for tab in sorted(set(_JS_SELECT_TAB_RE.findall(app_text)) - html_tabs)
    )
    findings.extend(
        f"{html_rel}: data-expand-target={target!r} has no matching id in {html_rel}"
        for target in sorted(set(_HTML_EXPAND_TARGET_RE.findall(html_text)) - html_ids)
    )
    findings.extend(
        f"{html_rel}: aria-controls={target!r} has no matching id in {html_rel}"
        for target in sorted(set(_HTML_ARIA_CONTROLS_RE.findall(html_text)) - html_ids)
    )

    app_tokens, _ = _tokenize_js(app_rel, app_text)
    example_keys = _extract_js_object_keys(app_tokens, "EXAMPLES")
    if example_keys is None:
        findings.append(f"{app_rel}: missing EXAMPLES catalog definition")
        return findings
    findings.extend(
        f"{html_rel}: data-load-example={key!r} is not defined in {app_rel} EXAMPLES"
        for key in sorted(set(_HTML_LOAD_EXAMPLE_RE.findall(html_text)) - example_keys)
    )
    select_match = _HTML_EXAMPLES_SELECT_RE.search(html_text)
    if select_match is None:
        findings.append(f"{html_rel}: missing #examples <select> element")
    else:
        option_keys = set(_HTML_OPTION_VALUE_RE.findall(select_match.group(1)))
        findings.extend(
            f"{html_rel}: #examples option value={key!r} is not defined in {app_rel} EXAMPLES"
            for key in sorted(option_keys - example_keys)
        )

    if "export const EXAMPLES = {" in app_text and "\nconst UTF8_ENCODER" in app_text:
        examples_block = app_text.split("export const EXAMPLES = {", 1)[1].split("\nconst UTF8_ENCODER", 1)[0]
        for key, raw_source in re.findall(
            r"^\s{2}([A-Za-z_][A-Za-z0-9_]*):\s*\{.*?source:\s*`([^`]*)`",
            examples_block,
            re.MULTILINE | re.DOTALL,
        ):
            raw_bytes = raw_source.encode("utf-8")
            try:
                vela.translate(raw_bytes)
            except vela.VelaError:
                continue
            try:
                if authoring.format_source(raw_bytes) != raw_bytes:
                    findings.append(f"{app_rel}: EXAMPLES.{key} is not canonically formatted")
            except vela.VelaError as err:
                findings.append(f"{app_rel}: EXAMPLES.{key} failed canonical formatting: {err}")

    lexer_rel = "tools/toolchain/parser/lexer.mll"
    if lexer_rel in indexed and "export const VELA_GRAMMAR = Object.freeze({" in app_text:
        try:
            lexer_source = (root / lexer_rel).read_text(encoding="utf-8")
            ident_table = lexer_source.split("let identifier state lexbuf =", 1)[1].split("let digit_run", 1)[0]
            lexer_active: set[str] = set()
            lexer_retired: set[str] = set()
            for word, action in re.findall(r'\|\s*"([A-Za-z0-9_]+)"\s*->\s*([^|\n]+)', ident_table):
                if action.strip().startswith("refuse "):
                    lexer_retired.add(word)
                else:
                    lexer_active.add(word)
            grammar_block = app_text.split("export const VELA_GRAMMAR = Object.freeze({", 1)[1].split("});", 1)[0]
            js_sets: dict[str, set[str]] = {}
            for field in ("keywords", "typeKeywords", "constants", "retiredKeywords"):
                section = grammar_block.split(f"{field}: Object.freeze([", 1)[1].split("]),", 1)[0]
                js_sets[field] = set(re.findall(r'"([^"]+)"', section))
            js_active = js_sets["keywords"] | js_sets["typeKeywords"] | js_sets["constants"]
            missing_active = sorted(lexer_active - js_active)
            if missing_active:
                findings.append(f"{app_rel}: VELA_GRAMMAR omitted lexer keywords: {', '.join(missing_active)}")
            if js_sets["retiredKeywords"] != lexer_retired:
                findings.append(f"{app_rel}: VELA_GRAMMAR retiredKeywords drifted from {lexer_rel}")
        except (OSError, UnicodeDecodeError, IndexError) as err:
            findings.append(f"{app_rel}: cannot verify VELA_GRAMMAR against {lexer_rel}: {err}")
    return findings


def javascript_findings(root: Path, loaded: corpus.Corpus) -> list[str]:
    """Check tracked JavaScript modules for lexical/identifier integrity and playground DOM bindings."""
    findings: list[str] = []
    for rel in loaded.tracked:
        if not rel.endswith((".mjs", ".js")):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            findings.append(f"{rel}: cannot read JavaScript file: {err}")
            continue
        findings.extend(_js_module_findings(rel, text))
    findings.extend(_playground_asset_findings(root, loaded))
    return findings


def run(root: Path) -> Reporter:
    """Run all repository hygiene, licensing, EditorConfig, and source-reference checks."""
    rep = Reporter()
    rep.line("=== check ===")
    try:
        loaded = corpus.load(root)
    except (OSError, ValueError, RuntimeError) as err:
        rep.report("corpus", "load error(s):", [f"cannot load repository corpus: {err}"])
        return rep
    rep.report(
        "reuse",
        "REUSE v3.3 compliance finding(s):",
        reuse_findings(root),
        f"REUSE v3.3 linter accepts all {len(loaded.tracked)} tracked file(s)",
    )
    rep.report(
        "marks",
        "SPDX file-header finding(s):",
        marks_findings(root, loaded),
        "every markable tracked file opens with its canonical SPDX-License-Identifier header",
    )
    rep.report(
        "editorconfig",
        "EditorConfig finding(s):",
        editorconfig_findings(root, loaded.tracked),
        f"all {len(loaded.tracked)} tracked file(s) obey .editorconfig encoding, newline, and whitespace rules",
    )
    rep.report(
        "glyphs",
        "Unicode hygiene finding(s):",
        glyph_findings(root, loaded.tracked),
        "no tracked file contains forbidden bidi, control, tab, or mojibake characters",
    )
    rep.report(
        "source-refs",
        "source-comment link finding(s):",
        source_ref_findings(root, loaded),
        "every relative link and #fragment in source comments and docstrings resolves",
    )
    rep.report(
        "vela-examples",
        "Vela example finding(s):",
        vela_example_findings(root, loaded.tracked),
        "all tracked pure Vela example files translate and hold to their canonical layout",
    )
    rep.report(
        "javascript",
        "JavaScript and playground asset finding(s):",
        javascript_findings(root, loaded),
        "all tracked JavaScript modules and playground DOM/asset bindings resolve cleanly",
    )
    return rep


def run_gate(root: Path) -> Reporter:
    """Run check, markdown, and typecheck in one unified static gate."""
    rep = run(root)
    rep.extend(markdown.run(root))
    rep.extend(typecheck.run(root))
    return rep
