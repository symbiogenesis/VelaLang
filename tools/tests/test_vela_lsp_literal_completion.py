# SPDX-License-Identifier: Apache-2.0
"""Independent literal replacements, static contexts and malformed completion controls."""

import copy
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from tests.test_vela_lsp_discovery import _message, _object, _params
from tests.test_vela_lsp_value_completion import _items, _labels, _server
from toolchain import VelaError, inspect_source
from toolchain.lsp_services import InspectionError, validate_inspection
from toolchain.protocol_json import encode_message, read_frame
from toolchain.source import SourceSnapshot

INDEPENDENT_CASES = True
_URI = "untitled:discovery.vela"


def _literal_ranges_and_scope() -> None:
    source = ("// \U0001f600\r\nmodule Literals;\r\npublic const Nat Capacity = 7;\r\n"
              "public Nat Use(Nat amount, bool active) {\r\n"
              "    let earlier = amount;\r\n"
              "    if (true) { let local = 1_024; return 1_024; }\r\n"
              "    else { let sibling = 2; return 1_024; }\r\n}")
    server = _server(source)
    text = source.split("\r\n")[5]
    first = text.index("return 1_024") + len("return ")
    for column in (first, first + 2, first + 5):
        choices = _items(server, 5, column)
        ensure(_labels(choices) == ["Capacity", "amount", "earlier", "local"],
               f"literal completion lost expected scope/type order: {choices!r}")
        ensure(all(item["textEdit"] == {"range": {
            "start": {"line": 5, "character": first},
            "end": {"line": 5, "character": first + 5}}, "newText": item["label"]}
                   for item in choices), "literal completion did not replace the entire numeric token")
    condition = text.index("true")
    ensure(_labels(_items(server, 5, condition + 1)) == ["active"],
           "Boolean literal completion included numeric values")
    sibling = source.split("\r\n")[6].index("return 1_024") + len("return ")
    ensure(_labels(_items(server, 6, sibling)) == ["Capacity", "amount", "earlier", "sibling"],
           "sibling-branch literal completion leaked a local")
    initializer = text.index("1_024")
    ensure(_labels(_items(server, 5, initializer)) == ["Capacity", "amount", "earlier"],
           "literal completion exposed its own initializer's binding")
    ensure(server.documents[_URI].text == source, "literal completion changed the open source")


def _static_contexts_and_shadowing() -> None:
    source = ("module Static; public const Nat Count = 2; "
              "public const Nat Pick(const Nat bound, Nat value) => value + bound; "
              "public Nat Use(const Nat limit, Nat amount) { "
              "let Count = amount; const Nat fixed = 3; "
              "return Pick(4, 5) + 6; }")
    server = _server(source)
    fixed = source.index("fixed = 3") + len("fixed = ")
    ensure(_labels(_items(server, 0, fixed)) == ["limit"],
           "static literal completion offered runtime values or hidden module constant")
    const_argument = source.index("Pick(4") + len("Pick(")
    ensure(_labels(_items(server, 0, const_argument)) == ["limit", "fixed"],
           "required-static call argument included runtime candidates")
    runtime_argument = const_argument + 3
    ensure(_labels(_items(server, 0, runtime_argument)) == ["limit", "amount", "Count", "fixed"],
           "ordinary call argument lost runtime candidates")
    nested = source.replace("Pick(4, 5)", "Pick(4 + 7, 5)")
    nested_server = _server(nested)
    for spelling in ("4 +", "7, 5"):
        ensure(_labels(_items(nested_server, 0, nested.index(spelling))) == ["limit", "fixed"],
               "nested required-static expression retained runtime literal choices")


def _source_binding_legacy_and_empty_sites() -> None:
    source = "module Empty; public Nat Use() => 1;"
    server = _server(source)
    ensure(_items(server, 0, source.index("1;")) == [], "empty lexical scope invented values")
    raw = inspect_source(source.encode(), completion_options=True)
    legacy = {key: value for key, value in raw.items() if key != "literal_completions"}
    server.inspector = lambda _: legacy
    ensure(server.handle({"jsonrpc": "2.0", "id": 8, "method": "textDocument/completion", "params": {
        "textDocument": {"uri": _URI}, "position": {"line": 0, "character": source.index("1;")}}})[0]["result"]
           == {"isIncomplete": False, "items": []}, "legacy facts invented literal contexts")
    ensure("literal_completions" not in inspect_source(source.encode()),
           "ordinary inspection acquired optional literal facts")
    invalid = "module Empty; public Nat Use() => missing + 1;"
    try:
        inspect_source(invalid.encode(), completion_options=True)
    except VelaError:
        pass
    else:
        raise AssertionError("invalid source supplied literal completion facts")


def _malformed_literals_refuse() -> None:
    source = ("module Bound; public const Nat Count = 2; public Nat Use(Nat amount, bool active) "
              "{ const Nat fixed = 1; return 1_024 + amount; }")
    raw = inspect_source(source.encode(), completion_options=True)
    snapshot = SourceSnapshot(_URI, 1, source, 1)
    checked = validate_inspection(snapshot, raw)
    ensure(checked is not None and bool(checked.literal_completions), "literal facts did not validate")
    for mutation in ("spelling", "interior", "comment", "type", "runtime", "unknown", "duplicate", "bool-id", "order"):
        broken = copy.deepcopy(raw)
        contexts = cast("list[dict[str, object]]", broken["literal_completions"])
        context = contexts[-1]
        if mutation == "spelling":
            context["spelling"] = "1024"
        elif mutation == "interior":
            context["column"] = cast("int", context["column"]) + 2
            context["spelling"] = "024"
        elif mutation == "comment":
            context["column"] = 1
        elif mutation == "type":
            context["type"] = "bool"
        elif mutation == "runtime":
            context["required_static"] = True
        elif mutation == "unknown":
            context["symbols"] = [999999]
        elif mutation == "duplicate":
            context["symbols"] = [0, 0]
        elif mutation == "bool-id":
            context["symbols"] = [True]
        else:
            contexts.reverse()
        try:
            validate_inspection(snapshot, broken)
        except InspectionError:
            pass
        else:
            raise AssertionError(f"malformed {mutation} literal context was accepted")


def _combined_bounds_and_detachment() -> None:
    source = "module Bounds; public Nat Use(Nat amount) => amount + 1;"
    with patch("toolchain.facts.MAX_COMPLETION_OPTIONS", 1):
        try:
            inspect_source(source.encode(), completion_options=True)
        except VelaError as error:
            ensure(error.kind == "inspection-limit", "combined budget used an unrelated refusal")
        else:
            raise AssertionError("combined name/literal producer choices exceeded their budget")
    raw = inspect_source(source.encode(), completion_options=True)
    with patch("toolchain.lsp_services.MAX_COMPLETION_OPTIONS", 1):
        try:
            validate_inspection(SourceSnapshot(_URI, 1, source, 1), raw)
        except InspectionError:
            pass
        else:
            raise AssertionError("combined name/literal consumer choices exceeded their budget")
    server = _server(source)
    server.inspector = lambda _: raw
    column = source.index("1;")
    ensure(_labels(_items(server, 0, column)) == ["amount"], "literal fixture did not start valid")
    contexts = cast("list[dict[str, object]]", raw["literal_completions"])
    contexts[0]["symbols"] = []
    ensure(_labels(_items(server, 0, column)) == ["amount"],
           "mutable producer response changed cached literal choices")
    server.handle(_message("workspace/didChangeConfiguration", {}, None))
    ensure(_items(server, 0, column) == [], "configuration change reused predecessor literal facts")


def _real_process_unicode_update() -> None:
    source = "// \U0001f600\r\nmodule Process; public Nat Use(Nat amount) => 1_024;"
    column = source.split("\r\n")[1].index("1_024")
    moved = "// changed\r\n" + source
    messages = [_message("initialize", identity=1), _message("initialized", identity=None),
        _message("textDocument/didOpen", {"textDocument": {
            "uri": _URI, "languageId": "vela", "version": 1, "text": source}}, None),
        _message("textDocument/completion", _params(1, column + 2), 2),
        _message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
            "contentChanges": [{"text": moved}]}, None),
        _message("textDocument/completion", _params(2, column + 2), 3),
        _message("shutdown", identity=4), _message("exit", identity=None)]
    tools = str(Path(__file__).resolve().parents[1])
    script = (f"import sys; sys.path.insert(0, {tools!r}); "
              "from toolchain.cli.vela_lsp import main; raise SystemExit(main())")
    completed = subprocess.run([sys.executable, "-I", "-c", script],
                               input=b"".join(encode_message(message) for message in messages),
                               capture_output=True, timeout=30, check=False)
    ensure(completed.returncode == 0 and completed.stderr == b"", "literal completion process failed")
    stream = BytesIO(completed.stdout)
    replies: dict[int, dict[str, object]] = {}
    while (frame := read_frame(stream)) is not None:
        reply = _object(json.loads(frame))
        if "id" in reply:
            replies[cast("int", reply["id"])] = reply
    ensure(set(replies) == {1, 2, 3, 4}, "literal completion process lost correlated replies")
    for identity, line in ((2, 1), (3, 2)):
        items = cast("list[dict[str, object]]", _object(replies[identity].get("result"))["items"])
        ensure(_labels(items) == ["amount"] and items[0]["textEdit"] == {
            "range": {"start": {"line": line, "character": column},
                      "end": {"line": line, "character": column + 5}}, "newText": "amount"},
            "stdio completion retained stale source coordinates or partial literal edits")


def cases() -> list[Case]:
    return [Case("literal-completion-ranges-types-scope-and-unicode", _literal_ranges_and_scope),
            Case("literal-completion-static-call-contexts-and-shadowing", _static_contexts_and_shadowing),
            Case("literal-completion-legacy-invalid-and-empty-contexts", _source_binding_legacy_and_empty_sites),
            Case("literal-completion-malformed-and-detached-context-refusals", _malformed_literals_refuse),
            Case("literal-completion-shared-bounds-cache-and-invalidation", _combined_bounds_and_detachment),
            Case("real-process-literal-completion-unsaved-unicode-update", _real_process_unicode_update)]
