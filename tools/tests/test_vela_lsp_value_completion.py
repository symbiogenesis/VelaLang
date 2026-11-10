# SPDX-License-Identifier: Apache-2.0
"""Independent expected value choices, source edits, and completion refusals."""

import copy
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from tests.test_vela_lsp_discovery import _message, _object, _params, _reply, _result
from toolchain import VelaError, inspect_source
from toolchain.lsp import Server
from toolchain.lsp_services import InspectionError, validate_inspection
from toolchain.protocol_json import MAX_BODY_BYTES, encode_message, read_frame
from toolchain.source import SourceSnapshot

INDEPENDENT_CASES = True
_URI = "untitled:discovery.vela"
_SOURCE = ("// \U0001f600\r\nmodule Values;\r"
           "/// Available capacity.\npublic const Nat amount = 7;\r\n"
           "public Nat Other(Nat ambient) => ambient;\n"
           "public Nat Use(Nat alpha, Nat axis, bool active) {\n"
           "    let added = alpha;\n"
           "    const Nat anchor = 2;\n"
           "    if (active) {\n"
           "        let ahead = axis;\n"
           "        return added + alpha;\n"
           "    } else {\n"
           "        let after = alpha;\n"
           "        return added + axis;\n"
           "    }\n}\npublic const Nat afterwards = 11;")


def _inspect(source: bytes) -> dict[str, object]:
    try:
        return inspect_source(source, completion_options=True)
    except VelaError as error:
        return {"status": "unavailable", "reason": error.kind}


def _server(source: str = _SOURCE) -> Server:
    server = Server(checker=lambda _: None, inspector=_inspect)
    _reply(server, "initialize")
    server.handle(_message("initialized", identity=None))
    server.handle(_message("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": source}}, None))
    return server


def _items(server: Server, line: int, column: int) -> list[dict[str, object]]:
    result = _object(_result(server, "textDocument/completion", line, column))
    ensure(result["isIncomplete"] is True, "bounded value choices claimed exhaustive completion")
    return cast("list[dict[str, object]]", result["items"])


def _labels(items: list[dict[str, object]]) -> list[str]:
    return [cast("str", item["label"]) for item in items]


def _scope_order_type_prefix_and_explicit_edits() -> None:
    server = _server()
    items = _items(server, 10, 16)
    ensure(_labels(items) == ["amount", "alpha", "axis", "added", "anchor", "ahead"],
           f"completion lost lexical scope, source order or scalar type: {items!r}")
    span = {"start": {"line": 10, "character": 15}, "end": {"line": 10, "character": 20}}
    for item in items:
        ensure(item["textEdit"] == {"range": span, "newText": item["label"]},
               "value completion failed to replace the complete original identifier")
        ensure(item["kind"] == (21 if item["label"] in {"amount", "anchor"} else 6),
               "completion confused constants and runtime values")
    ensure(items[0].get("documentation") == {"kind": "plaintext", "value": "Available capacity."},
           "constant completion lost source-bound documentation")
    ensure(_labels(_items(server, 10, 17)) == ["added"], "completion ignored a longer prefix")
    ensure(_labels(_items(server, 10, 20)) == ["added"], "completion lost identifier-end selection")
    ensure(_labels(_items(server, 13, 16)) == ["amount", "alpha", "axis", "added", "anchor", "after"],
           "a sibling branch local escaped into value choices")
    ensure(server.documents[_URI].text == _SOURCE, "value completion changed the source overlay")


def _constant_shadowing_initializer_and_namespaces() -> None:
    source = ("module Shadow; public const Nat amount = 5; public Nat Add(Nat alpha) => alpha; "
              "public Nat Use(Nat alpha) { let amount = alpha; let Add = amount; return Add + amount; }")
    server = _server(source)
    cursor = source.index("return Add") + len("return ")
    choices = _items(server, 0, cursor)
    ensure(_labels(choices) == ["alpha", "amount", "Add"],
           "value completion exposed a hidden constant or callable namespace")
    ensure(choices[1]["detail"] == "amount: Nat" and choices[1]["kind"] == 6,
           "value completion selected the hidden global constant")
    cursor = source.index("let amount = alpha") + len("let amount = ")
    ensure(_labels(_items(server, 0, cursor)) == ["amount", "alpha"],
           "a local became visible inside its own initializer")
    label_source = "module Named; public Nat Add(Nat alpha) => alpha; public Nat Use(Nat axis) => Add(alpha: axis);"
    labels = _items(_server(label_source), 0, label_source.index("alpha: axis"))
    ensure(labels == [], "a named-argument label became a value insertion context")


def _required_static_candidates_and_boolean_types() -> None:
    source = ("module Static; public const Nat Ambient = 1; public const bool Active = true; "
              "public const Nat Use(const Nat amount, Nat axis, bool active) { "
              "const Nat anchor = amount + Ambient; if (active) { return anchor; } else { return axis; } }")
    server = _server(source)
    cursor = source.index("amount + Ambient")
    ensure(_labels(_items(server, 0, cursor)) == ["Ambient", "amount"],
           "runtime parameter or self-initializer entered a required-static choice")
    cursor = source.index("return anchor") + len("return ")
    ensure(_labels(_items(server, 0, cursor)) == ["Ambient", "amount", "anchor"],
           "symbolic local constant lost static-compatible choices")
    cursor = source.index("if (active)") + len("if (")
    ensure(_labels(_items(server, 0, cursor)) == ["Active", "active"],
           "Boolean value context offered numeric candidates")


def _compiler_facts_are_opt_in_and_bounded() -> None:
    legacy = inspect_source(_SOURCE.encode())
    ensure("completions" not in legacy,
           "legacy compiler inspection silently changed its transport")
    server = _server()
    server.inspector = lambda _: legacy
    ensure(_items(server, 10, 16) == [], "legacy facts invented unrecorded value suggestions")
    server.inspector = lambda _: {**legacy, "completions": []}
    ensure(_items(server, 10, 16) == [], "empty optional completion sites claimed scope knowledge")
    raw = inspect_source(_SOURCE.encode(), completion_options=True)
    snapshot = SourceSnapshot(_URI, 1, _SOURCE, 1)
    checked = validate_inspection(snapshot, raw)
    ensure(checked is not None and bool(checked.completions), "resolver did not record value choices")
    with patch("toolchain.facts.MAX_COMPLETION_OPTIONS", 1):
        try:
            inspect_source(_SOURCE.encode(), completion_options=True)
        except VelaError as error:
            ensure(error.kind == "inspection-limit", "completion budget used an unrelated refusal")
        else:
            raise AssertionError("completion budget returned partial compiler choices")
    with patch("toolchain.lsp_services.MAX_COMPLETION_OPTIONS", 1):
        try:
            validate_inspection(snapshot, raw)
        except InspectionError:
            pass
        else:
            raise AssertionError("completion consumer accepted over-budget facts")


def _malformed_and_detached_choices_refuse() -> None:
    raw = inspect_source(_SOURCE.encode(), completion_options=True)
    snapshot = SourceSnapshot(_URI, 1, _SOURCE, 1)
    symbols = cast("list[dict[str, object]]", raw["symbols"])
    function = next(index for index, item in enumerate(symbols) if item["kind"] == "function")
    for mutation in ("unknown", "duplicate", "function", "empty", "site", "unordered", "bool"):
        broken = copy.deepcopy(raw)
        copied = cast("list[dict[str, object]]", broken["completions"])
        options = cast("list[int]", copied[0]["symbols"])
        if mutation == "unknown":
            options.append(999999)
        elif mutation == "duplicate":
            options.append(options[-1])
        elif mutation == "function":
            options.append(function)
            options.sort()
        elif mutation == "empty":
            copied[0]["symbols"] = []
        elif mutation == "site":
            copied[0]["line"] = 1
        elif mutation == "unordered":
            copied.reverse()
        else:
            options[0] = True
        try:
            validate_inspection(snapshot, broken)
        except InspectionError:
            pass
        else:
            raise AssertionError(f"malformed {mutation} completion facts were accepted")
    server = _server()
    server.inspector = lambda _: raw
    expected = _items(server, 10, 16)
    selected = next(item for item in cast("list[dict[str, object]]", raw["completions"])
                    if item["line"] == 11 and item["column"] == 16)
    selected["symbols"] = []
    ensure(_items(server, 10, 16) == expected, "mutable producer response changed cached value choices")


def _lifecycle_current_producer_and_reply_bounds() -> None:
    server = _server()
    _items(server, 10, 16)
    snapshot = server.documents[_URI]
    server.handle(_message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
        "contentChanges": [{"text": "// \U0001f600 moved\r\n" + _SOURCE}]}, None))
    ensure(_labels(_items(server, 11, 16)) == ["amount", "alpha", "axis", "added", "anchor", "ahead"],
           "value completion reused source coordinates after an unsaved update")
    ensure(server.documents[_URI] is not snapshot, "completion test did not change source generation")
    server.handle(_message("workspace/didChangeConfiguration", {}, None))
    ensure(bool(_items(server, 11, 16)), "configuration invalidation failed to reconstruct current value choices")

    def replaced(source: bytes) -> dict[str, object]:
        server.inspector = _inspect
        return _inspect(source)

    server.inspector = replaced
    ensure(_object(_reply(server, "textDocument/completion", _params(11, 16))["error"])["code"] == -32803,
           "late value completion survived a producer replacement")
    request = _message("textDocument/completion", _params(11, 16))
    request["id"] = "x" * (MAX_BODY_BYTES - 180)
    encode_message(request)
    ensure(_object(server.handle(request)[0]["error"])["code"] == -32803,
           "value completion published a truncated over-bound result")
    server.handle(_message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 3},
        "contentChanges": [{"text": "module Broken; public Nat Use() => missing;"}]}, None))
    ensure(_items(server, 0, 40) == [], "refused source retained prior value choices")


def _real_process_value_choices_and_unicode_edit() -> None:
    messages = [_message("initialize", identity=1), _message("initialized", identity=None),
        _message("textDocument/didOpen", {"textDocument": {
            "uri": _URI, "languageId": "vela", "version": 1, "text": _SOURCE}}, None),
        _message("textDocument/completion", _params(10, 16), 2),
        _message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
            "contentChanges": [{"text": "// \U0001f600 moved\r\n" + _SOURCE}]}, None),
        _message("textDocument/completion", _params(11, 16), 3),
        _message("shutdown", identity=4), _message("exit", identity=None)]
    tools = str(Path(__file__).resolve().parents[1])
    script = (f"import sys; sys.path.insert(0, {tools!r}); "
              "from toolchain.cli.vela_lsp import main; raise SystemExit(main())")
    completed = subprocess.run([sys.executable, "-I", "-c", script],
                               input=b"".join(encode_message(message) for message in messages),
                               capture_output=True, timeout=30, check=False)
    ensure(completed.returncode == 0 and completed.stderr == b"", f"value completion process failed: {completed.stderr!r}")
    replies: dict[int, dict[str, object]] = {}
    stream = BytesIO(completed.stdout)
    while (frame := read_frame(stream)) is not None:
        reply = _object(json.loads(frame))
        if "id" in reply:
            replies[cast("int", reply["id"])] = reply
    ensure(set(replies) == {1, 2, 3, 4}, "value completion process lost correlated replies")
    for identity, line in ((2, 10), (3, 11)):
        items = cast("list[dict[str, object]]", _object(replies[identity].get("result"))["items"])
        ensure(_labels(items) == ["amount", "alpha", "axis", "added", "anchor", "ahead"],
               "stdio value completion changed expected compatible visible values")
        ensure(all(_object(_object(item["textEdit"])["range"])["start"] == {
            "line": line, "character": 15} for item in items), "stdio value completion retained old edit coordinates")


def cases() -> list[Case]:
    return [Case("value-completion-scope-order-types-prefixes-and-explicit-edits", _scope_order_type_prefix_and_explicit_edits),
            Case("value-completion-shadowing-initializers-and-distinct-namespaces", _constant_shadowing_initializer_and_namespaces),
            Case("value-completion-static-readiness-and-boolean-types", _required_static_candidates_and_boolean_types),
            Case("value-completion-opt-in-producer-and-complete-bounds", _compiler_facts_are_opt_in_and_bounded),
            Case("value-completion-malformed-source-detached-and-unknown-choices", _malformed_and_detached_choices_refuse),
            Case("value-completion-lifecycle-producer-invalidation-and-reply-bounds", _lifecycle_current_producer_and_reply_bounds),
            Case("real-process-value-completion-and-unsaved-unicode-edit", _real_process_value_choices_and_unicode_edit)]
