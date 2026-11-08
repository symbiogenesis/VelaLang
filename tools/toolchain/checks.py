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
from toolchain import authoring, corpus, toolenv
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
        chunks.extend(
            (lineno, line)
            for lineno, line in enumerate(text.splitlines(), 1)
            if line.lstrip().startswith("#")
        )
        return chunks
    chunks.extend(
        (lineno, line)
        for lineno, line in enumerate(text.splitlines(), 1)
        if any(marker in line for marker in ("//", "/*", "(*"))
    )
    return chunks


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
    return rep


def run_gate(root: Path) -> Reporter:
    """Run check, markdown, and typecheck in one unified static gate."""
    rep = run(root)
    md_rep = corpus_markdown_run(root)
    rep.findings += md_rep.findings
    rep.out.extend(md_rep.out)
    rep.decisions.extend(md_rep.decisions)
    tc_rep = typecheck.run(root)
    rep.findings += tc_rep.findings
    rep.out.extend(tc_rep.out)
    rep.decisions.extend(tc_rep.decisions)
    return rep


def corpus_markdown_run(root: Path) -> Reporter:
    from toolchain import markdown  # noqa: PLC0415

    return markdown.run(root)
