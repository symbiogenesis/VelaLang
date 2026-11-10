# SPDX-License-Identifier: Apache-2.0
"""Bounded qualification of editor assets in pinned independent syntax consumers."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import cast, override

from toolchain import highlight, surface
from toolchain import parser as canonical
from toolchain.ast import VelaError

MAX_SOURCE_BYTES = 65_536
PROCESS_SECONDS = 60
PARSE_MICROSECONDS = 2_000_000
TREE_SITTER_VERSION = "tree-sitter 0.25.10 (da6fe9beb4f7f67beb75914ca8e0d48ae48d6406)"
TREE_SITTER_SHA256 = "6329ea4be486c26ef87fdc45ead60c1b1fb9ffab62fe9bd295932ec8e0645751"
TEXTMATE_PINS = {
    "package.json": None,
    "release/main.js": "67136e26f9fbb5c4f60345935170239253cd4ace03ddd9171f3f6ff17fe5ea13",
    "LICENSE.md": "b5cb7ff7859e7d282d98fc43ab081b0dda5dc659dc3385cf65740c759a7e6a6c",
}
ONIGURUMA_PINS = {
    "package.json": None,
    "release/main.js": "d49f2bfcbffca8732aac82fb84db5aab2521bcf0acb612f27454dc75cab85b82",
    "release/onig.wasm": "76ebc1f0d87b2e7449a45ff3cd1a1546a9f05f54bdac44ee03e8a2b8348897be",
    "LICENSE.txt": "ddde8aba8fe72b4830e27901fc78733eb6db7b6c653161075de213a6adeda3fd",
    "NOTICES.txt": "615d94d89eacc046241518c247f6650a5df80d1adf4b284a756f500867620b35",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_generated(root: Path) -> list[str]:
    findings: list[str] = []
    for name, expected in highlight.generated_assets(root).items():
        path = root / highlight.ASSETS / name
        if not path.is_file() or path.read_bytes() != expected.encode():
            findings.append(f"{highlight.ASSETS}/{name}: generated asset differs from canonical syntax")
    return findings


def _run(arguments: list[str], directory: Path, *, error: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, cwd=directory, capture_output=True, text=True, encoding="utf-8",
                            timeout=PROCESS_SECONDS, check=False, stdin=subprocess.DEVNULL)
    if result.returncode not in ({0, 1} if error else {0}):
        raise ValueError(f"consumer failed ({result.returncode}): {result.stderr[-2000:]}")
    if len(result.stdout.encode()) > 16 * 1024 * 1024:
        raise ValueError("consumer output exceeds 16 MiB")
    return result


def _package(path: Path, pins: dict[str, str | None], version: str) -> dict[str, str]:
    identities = {name: digest(path / name) for name in pins}
    for name, expected in pins.items():
        if expected is not None and identities[name] != expected:
            raise ValueError(f"pinned consumer differs: {path / name}")
    package = json.loads((path / "package.json").read_text(encoding="utf-8"))
    if package.get("version") != version:
        raise ValueError("consumer package version differs")
    return identities


def output_path(root: Path, requested: Path, engine: Path, textmate: Path, oniguruma: Path, node: Path) -> Path:
    """Keep reports within ignored output storage and disjoint from every selected consumer."""
    root = root.resolve()
    output = requested.resolve()
    if (requested.is_symlink() or (root / "out").is_symlink() or output.suffix != ".json"
            or not output.is_relative_to(root / "out") or (output.exists() and not output.is_file())):
        raise ValueError("qualification requires a regular .json report inside repository out/")
    protected = {engine.resolve(), node.resolve()}
    protected.update((textmate / name).resolve() for name in TEXTMATE_PINS)
    protected.update((oniguruma / name).resolve() for name in ONIGURUMA_PINS)
    if output in protected:
        raise ValueError("qualification output aliases a selected consumer input")
    return output


def recheck(root: Path, report: dict[str, object], engine: Path, textmate: Path, oniguruma: Path, node: Path) -> None:
    """Recheck input and consumer bytes immediately before atomic publication."""
    bindings = cast("dict[str, str]", report["inputs"])
    if {name: digest(root / name) for name in bindings} != bindings:
        raise ValueError("qualification input changed before publication")
    if digest(engine) != cast("dict[str, str]", report["tree_sitter"])["sha256"]:
        raise ValueError("Tree-sitter changed before publication")
    if digest(node) != cast("dict[str, str]", report["node"])["sha256"]:
        raise ValueError("Node.js changed before publication")
    if report["packages"] != {"textmate": _package(textmate, TEXTMATE_PINS, "9.2.0"),
                              "oniguruma": _package(oniguruma, ONIGURUMA_PINS, "2.0.1")}:
        raise ValueError("syntax package changed before publication")


class HighlightHTML(HTMLParser):
    """Read stock Tree-sitter HTML without recomputing its classifications."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_line = False
        self.scopes: list[str] = []
        self.spans: list[tuple[str, tuple[str, ...]]] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "td" and values.get("class") == "line":
            self.in_line = True
        if tag == "span" and self.in_line:
            self.scopes.append(values.get("class") or "")

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self.in_line = False
        elif tag == "span" and self.in_line:
            self.scopes.pop()

    @override
    def handle_data(self, data: str) -> None:
        if self.in_line:
            self.spans.append((data, tuple(self.scopes)))


def _parse(engine: Path, directory: Path, source: Path, edits: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    arguments = [str(engine), "parse", "--timeout", str(PARSE_MICROSECONDS), str(source)]
    if edits is not None:
        arguments += ["--edits", *edits]
    return _run(arguments, directory, error=True)


def _tree(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(line for line in result.stdout.splitlines()
                     if "\tParse:" not in line and "\tEdit:" not in line).strip()


def _error(result: subprocess.CompletedProcess[str]) -> bool:
    found = "(ERROR" in result.stdout or "(MISSING" in result.stdout
    if bool(result.returncode) != found:
        raise ValueError("consumer verdict does not match syntax recovery markers")
    return found


def _fixtures(root: Path) -> dict[str, list[dict[str, object]]]:
    data = json.loads((root / highlight.ASSETS / "fixtures.json").read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("unknown highlight fixture schema")
    for group in ("positive", "negative", "editor_recovery", "edits"):
        for item in data[group]:
            source = item.get("source")
            if not isinstance(source, str) or len(source.encode()) > MAX_SOURCE_BYTES:
                raise ValueError("fixture source exceeds qualification limit")
    return cast("dict[str, list[dict[str, object]]]", data)


def _canonical(compiled: canonical.Build, source: str, expected_error: bool) -> None:
    try:
        canonical.parse_source(compiled, source.encode(), surface=True)
    except VelaError:
        if expected_error:
            return
        raise
    if expected_error:
        raise ValueError("negative highlighting fixture is accepted by the canonical syntax owner")


def qualify(root: Path, engine: Path, textmate: Path, oniguruma: Path, node: Path) -> dict[str, object]:
    """Exercise shipped grammars, query rendering, recovery, and fresh/incremental agreement."""
    root, engine, textmate, oniguruma, node = (p.resolve() for p in (root, engine, textmate, oniguruma, node))
    findings = check_generated(root)
    if findings:
        raise ValueError("; ".join(findings))
    if digest(engine) != TREE_SITTER_SHA256:
        raise ValueError("Tree-sitter executable differs from the qualified Linux ARM64 pin")
    if _run([str(engine), "--version"], root).stdout.strip() != TREE_SITTER_VERSION:
        raise ValueError("Tree-sitter version/revision differs")
    node_digest = digest(node)
    if _run([str(node), "--version"], root).stdout.strip() != "v22.22.1":
        raise ValueError("qualification requires Node.js v22.22.1")
    packages = {"textmate": _package(textmate, TEXTMATE_PINS, "9.2.0"),
                "oniguruma": _package(oniguruma, ONIGURUMA_PINS, "2.0.1")}
    assets = root / highlight.ASSETS
    inputs = [*assets.rglob("*")]
    inputs = [p for p in inputs if p.is_file() and p.suffix in {".js", ".json", ".mjs", ".c", ".scm"}
              and p.name not in {"parser.c", "grammar.json", "node-types.json"} and "tree_sitter" not in p.parts]
    inputs += [root / "tools/toolchain/parser" / name for name in ("parser.mly", "lexer.mll")]
    inputs += [root / "tools/toolchain" / name for name in ("highlight.py", "highlight_qualification.py", "surface.py", "parser_checked.py")]
    inputs += sorted((root / "examples").glob("*.vela"))
    bindings = {p.relative_to(root).as_posix(): digest(p) for p in inputs}
    fixtures = _fixtures(root)
    syntax: list[dict[str, object]] = []
    incremental: list[dict[str, object]] = []
    rendered: list[dict[str, object]] = []
    shared: list[dict[str, object]] = []
    tm_shared: list[dict[str, object]] = []
    disposition = json.loads((assets / "recovery.json").read_text(encoding="utf-8"))
    positive_recovery = disposition["positive_recovery"]
    negative_parses = {name: group["reason"] for group in disposition["negative_parse_groups"] for name in group["cases"]}
    if (not set(positive_recovery) <= {fixture.name for fixture in surface.POSITIVE}
            or not set(negative_parses) <= {name for name, _, _ in surface.NEGATIVE}):
        raise ValueError("known recovery inventory names a case absent from the canonical corpus")
    with tempfile.TemporaryDirectory(prefix="vela-highlight-") as temporary, canonical.cached_build(root) as compiled:
        stage = Path(temporary)
        grammar = stage / "tree-sitter-vela"
        shutil.copytree(assets / "tree-sitter", grammar, ignore=shutil.ignore_patterns("parser.c", "grammar.json", "node-types.json", "tree_sitter"))
        _run([str(engine), "generate", "--abi", "15"], grammar)
        _run(["cc", "-fsyntax-only", "-Wall", "-Wextra", "-Werror", "-I", str(grammar / "src"),
              str(grammar / "src/scanner.c")], grammar)
        config = stage / "config.json"
        config.write_text(json.dumps({"parser-directories": [str(stage)]}), encoding="utf-8")
        for path in sorted((root / "examples").glob("*.vela")):
            source = path.read_text(encoding="utf-8")
            _canonical(compiled, source, False)
            result = _parse(engine, grammar, path)
            if _error(result):
                raise ValueError(f"authored corpus recovered instead of parsing: {path.name}")
            syntax.append({"name": path.name, "canonical": "parsed", "tree_sitter": "parsed"})
        for fixture in surface.POSITIVE:
            _canonical(compiled, fixture.source, False)
            path = stage / "shared.vela"
            path.write_text(fixture.source, encoding="utf-8")
            actual_error = _error(_parse(engine, grammar, path))
            if actual_error != (fixture.name in positive_recovery):
                raise ValueError(f"canonical positive changed its declared editor recovery: {fixture.name}")
            shared.append({"name": fixture.name, "canonical": "parsed", "tree_sitter_error": actual_error,
                           "disposition": positive_recovery.get(fixture.name, "syntax parsed without recovery")})
            tm_shared.append({"name": "canonical-positive:" + fixture.name, "source": fixture.source, "scopes": []})
        for name, data, kind in surface.NEGATIVE:
            try:
                canonical.parse_source(compiled, data, surface=True)
            except VelaError as error:
                if error.kind != kind:
                    raise ValueError(f"canonical refusal kind changed: {name}") from error
            else:
                raise ValueError(f"canonical negative unexpectedly parsed: {name}")
            if kind != "syntax":
                shared.append({"name": name, "canonical": kind, "projected": False,
                               "disposition": disposition["outside_editor_envelope"]})
                continue
            path = stage / "shared.vela"
            path.write_bytes(data)
            actual_error = _error(_parse(engine, grammar, path))
            if actual_error != (name not in negative_parses):
                raise ValueError(f"canonical negative changed its declared editor recovery: {name}")
            shared.append({"name": name, "canonical": "syntax", "tree_sitter_error": actual_error,
                           "disposition": negative_parses.get(name, "syntax recovery visible")})
            tm_shared.append({"name": "canonical-negative:" + name, "source": data.decode(), "scopes": []})
        for group in ("positive", "negative", "editor_recovery"):
            for item in fixtures[group]:
                name, source = cast("str", item["name"]), cast("str", item["source"])
                path = stage / (name + ".vela")
                path.write_text(source, encoding="utf-8")
                expected_error = group == "negative"
                _canonical(compiled, source, group != "positive")
                result = _parse(engine, grammar, path)
                if _error(result) != expected_error:
                    raise ValueError(f"unexpected recovery verdict: {name}")
                syntax.append({"name": name, "canonical_error": group != "positive", "tree_sitter_error": expected_error})
                if group == "positive":
                    result = _run([str(engine), "highlight", "--config-path", str(config), "--scope", "source.vela",
                                   "--html", "--css-classes", str(path)], grammar)
                    reader = HighlightHTML()
                    reader.feed(result.stdout)
                    if "".join(text for text, _ in reader.spans) != source:
                        raise ValueError("highlight rendering did not preserve exact Unicode source")
                    # Expectations describe lexical categories, independently of
                    # generated rule names and the translator's AST choices.
                    expected_scopes = cast("list[dict[str, str]]", item["scopes"])
                    for expected in expected_scopes:
                        target = expected["text"]
                        scope = expected["scope"].split(".", 1)[0]
                        wanted = expected.get("tree_scope") or {
                            "storage": "type builtin", "constant": "number", "keyword": "keyword",
                            "comment": "comment", "string": "string", "meta": "string"}[scope]
                        if not any(target in text and wanted in classes for text, classes in reader.spans):
                            raise ValueError(f"Tree-sitter query did not highlight {name}: {target} as {wanted}")
                    rendered.append({"name": name, "html_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
                                     "assertions": len(expected_scopes)})
        for item in fixtures["edits"]:
            name, source = cast("str", item["name"]), cast("str", item["source"])
            needle, replacement = cast("str", item["needle"]), cast("str", item["replacement"])
            data = source.encode()
            first = data.index(needle.encode())
            updated = data[:first] + replacement.encode() + data[first + len(needle.encode()):]
            before, after = stage / "before.vela", stage / "after.vela"
            before.write_bytes(data)
            after.write_bytes(updated)
            incremental_result = _parse(engine, grammar, before, [f"{first} {len(needle.encode())} {replacement}"])
            fresh_result = _parse(engine, grammar, after)
            expected_error = cast("bool", item["error"])
            _canonical(compiled, updated.decode(), expected_error)
            if _tree(incremental_result) != _tree(fresh_result) or _error(fresh_result) != expected_error:
                raise ValueError(f"incremental/fresh tree or expected recovery differs: {name}")
            incremental.append({"name": name, "fresh_agrees": True, "error": expected_error,
                                "tree_sha256": hashlib.sha256(_tree(fresh_result).encode()).hexdigest()})
        tm_fixtures = stage / "textmate-fixtures.json"
        tm_fixtures.write_text(json.dumps(fixtures["positive"] + fixtures["negative"] + fixtures["editor_recovery"] + tm_shared), encoding="utf-8")
        tm_result = _run([str(node), str(assets / "textmate/qualify.mjs"), str(assets / "textmate/vela.tmLanguage.json"),
                          str(textmate), str(oniguruma), str(tm_fixtures)], root)
        tm_observation = json.loads(tm_result.stdout)
    if {p.relative_to(root).as_posix(): digest(p) for p in inputs} != bindings:
        raise ValueError("source, grammar, queries or qualification inputs changed during the run")
    if digest(node) != node_digest or digest(engine) != TREE_SITTER_SHA256 or packages != {
        "textmate": _package(textmate, TEXTMATE_PINS, "9.2.0"), "oniguruma": _package(oniguruma, ONIGURUMA_PINS, "2.0.1")
    }:
        raise ValueError("syntax consumer changed during qualification")
    return {"schema": 1, "accepted_syntax_assets": True, "semantic_acceptance": False,
            "budgets": {"source_bytes": MAX_SOURCE_BYTES, "process_seconds": PROCESS_SECONDS,
                        "parse_microseconds": PARSE_MICROSECONDS, "textmate_line_milliseconds": 100},
            "inputs": bindings, "tree_sitter": {"version": TREE_SITTER_VERSION, "sha256": digest(engine)},
            "node": {"version": "v22.22.1", "sha256": node_digest}, "packages": packages,
            "syntax": syntax, "incremental": incremental, "rendered": rendered, "textmate": tm_observation,
            "shared_corpus": shared,
            "canonical_parser": compiled.receipt}
