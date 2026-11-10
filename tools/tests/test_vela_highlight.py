# SPDX-License-Identifier: Apache-2.0
"""Independent asset drift, lexical-consumer and publication refusal controls."""

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from tests.harness import Case, ensure
from toolchain import checks, highlight
from toolchain import highlight_qualification as qualification

ROOT = Path(__file__).resolve().parents[2]


def _reject(fn: Callable[[], object]) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected refusal")


def _generated() -> None:
    ensure(qualification.check_generated(ROOT) == [], "shipped grammar/query drift")
    grammar = highlight.tree_grammar(ROOT)
    ensure("s_decl" not in grammar and "declaration:" in grammar, "canonical rule translation disappeared")
    ensure('"record"' in grammar and '"effects"' in grammar and '"machine"' in grammar,
           "secondary grammar omitted wider syntax owners")
    ensure("seq(\"'\"" in grammar, "character delimiters drifted")


def _owner_drift() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-highlight-test-") as temporary:
        root = Path(temporary)
        shutil.copytree(ROOT / "tools/editor", root / "tools/editor", ignore=shutil.ignore_patterns("parser.c", "tree_sitter"))
        shutil.copytree(ROOT / "tools/toolchain/parser", root / "tools/toolchain/parser")
        lexer = root / "tools/toolchain/parser/lexer.mll"
        lexer.write_text(lexer.read_text(encoding="utf-8").replace('"public" -> PUBLIC', '"exposed" -> PUBLIC'), encoding="utf-8")
        findings = qualification.check_generated(root)
        ensure(len(findings) == 3, "lexer edit did not invalidate both grammars and query inventory")
        generated = highlight.generated_assets(root)
        ensure('"exposed"' in generated["tree-sitter/grammar.js"], "syntax token mapping retained old owner")
        ensure("exposed" in generated["textmate/vela.tmLanguage.json"], "lexical grammar retained old owner")


def _output_refusals() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-highlight-output-") as temporary:
        root = Path(temporary)
        (root / "out").mkdir()
        consumer = root / "out/consumer"
        textmate, oniguruma = root / "out/textmate", root / "out/oniguruma"
        for requested in (root / "examples/first_slice.vela", root / "README.md", root / "out/bad.vela",
                          textmate / "package.json", oniguruma / "package.json"):
            _reject(lambda requested=requested: qualification.output_path(root, requested, consumer, textmate, oniguruma, consumer))
        report = root / "out/report.json"
        ensure(qualification.output_path(root, report, consumer, textmate, oniguruma, consumer) == report.resolve(),
               "regular ignored report was refused")
        selected = root / "out/selected.json"
        _reject(lambda: qualification.output_path(root, selected, selected, textmate, oniguruma, consumer))


def _stale_publication() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-highlight-stale-") as temporary:
        root = Path(temporary)
        source, engine, node = root / "source", root / "engine", root / "node"
        for path in (source, engine, node):
            path.write_text("initial", encoding="utf-8")
        report: dict[str, object] = {"inputs": {"source": qualification.digest(source)},
                                     "tree_sitter": {"sha256": qualification.digest(engine)},
                                     "node": {"sha256": qualification.digest(node)}}
        node.write_text("changed", encoding="utf-8")
        _reject(lambda: qualification.recheck(root, report, engine, root, root, node))
        node.write_text("initial", encoding="utf-8")
        source.write_text("changed", encoding="utf-8")
        _reject(lambda: qualification.recheck(root, report, engine, root, root, node))


def _package_corruption() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-highlight-pin-") as temporary:
        root = Path(temporary)
        (root / "package.json").write_text(json.dumps({"version": "9.2.0"}), encoding="utf-8")
        (root / "engine.js").write_text("changed", encoding="utf-8")
        _reject(lambda: qualification._package(root, {"engine.js": "0" * 64}, "9.2.0"))
        _reject(lambda: qualification._package(root, {}, "2.0.1"))


def _html_and_coordinates() -> None:
    reader = qualification.HighlightHTML()
    reader.feed("<tr><td class=line-number>1</td><td class=line><span class='string'>&quot;🧭&amp;&quot;</span>\n</td></tr>")
    ensure(reader.spans == [('"🧭&"', ("string",)), ("\n", ())], "stock HTML Unicode/escaping was misread")
    first = subprocess.CompletedProcess([], 1, "(ERROR [0, 0] - [0, 1])\nbefore\tParse: 1 ms\n\tEdit: 2 ms\n")
    second = subprocess.CompletedProcess([], 1, "(ERROR [0, 0] - [0, 1])\nafter\tParse: 3 ms\n")
    ensure(qualification._tree(first) == qualification._tree(second), "timing labels entered tree comparison")
    ensure(qualification._error(first), "actual recovery marker was lost")
    _reject(lambda: qualification._error(subprocess.CompletedProcess([], 0, "(ERROR [0, 0] - [0, 1])")))


def _javascript_dsl() -> None:
    grammar = highlight.tree_grammar(ROOT)
    ensure(checks._js_module_findings("tools/editor/tree-sitter/grammar.js", grammar) == [], "real DSL globals were refused")
    findings = checks._js_module_findings("tools/editor/tree-sitter/grammar.js", grammar + "\nunknownHook();\n")
    ensure(any("unknownHook" in finding for finding in findings), "DSL allowance hid an undeclared identifier")
    ensure(bool(checks._js_module_findings("other.js", "grammar();")), "DSL globals escaped their grammar owner")


def cases() -> list[Case]:
    return [Case("generated assets bind canonical syntax", _generated),
            Case("canonical keyword changes invalidate all projections", _owner_drift),
            Case("reports refuse source and consumer aliases", _output_refusals),
            Case("publication refuses changed Node and source bytes", _stale_publication),
            Case("consumer code and metadata pins refuse corruption", _package_corruption),
            Case("independent HTML and full incremental tree comparison", _html_and_coordinates),
            Case("grammar DSL globals have an exact owner", _javascript_dsl)]
