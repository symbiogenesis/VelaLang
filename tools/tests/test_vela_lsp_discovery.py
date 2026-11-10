# SPDX-License-Identifier: Apache-2.0
"""Independent callable-completion and signature-help protocol expectations."""

import copy
import json
import subprocess
import sys
from contextlib import redirect_stderr
from io import BytesIO, StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import VelaError, inspect_source
from toolchain.lsp import Server
from toolchain.lsp_discovery import project
from toolchain.lsp_services import InspectionError, validate_inspection
from toolchain.protocol_json import MAX_BODY_BYTES, encode_message, read_frame
from toolchain.source import SourceSnapshot

INDEPENDENT_CASES = True
_URI = "untitled:discovery.vela"
_SOURCE = ("// \U0001f600\r\nmodule Discovery;\r"
           "/// Earlier choice.\npublic Nat Add(Nat value, Nat extra) => value + extra;\r\n"
           "public bool Another(Nat value, Nat extra) => value == extra;\n"
           "public Nat Apply(Nat value, Nat extra) => value * extra;\n"
           "public Nat Use(Nat x) {\n"
           "    let Apply = x;\n"
           "    return Apply(Add(value: x, extra: 1), (Apply + 2));\n}")


def _object(value: object) -> dict[str, object]:
    ensure(isinstance(value, dict), f"expected protocol object: {value!r}")
    return cast("dict[str, object]", value)


def _message(method: str, params: object = None, identity: int | None = 1) -> dict[str, object]:
    result: dict[str, object] = {"jsonrpc": "2.0", "method": method,
                                "params": {} if params is None else params}
    if identity is not None:
        result["id"] = identity
    return result


def _params(line: int, column: int, uri: str = _URI) -> dict[str, object]:
    return {"textDocument": {"uri": uri}, "position": {"line": line, "character": column}}


def _reply(server: Server, method: str, params: object = None) -> dict[str, object]:
    replies = server.handle(_message(method, params))
    ensure(len(replies) == 1 and replies[0].get("id") == 1, "discovery lost request correlation")
    return replies[0]


def _result(server: Server, method: str, line: int, column: int) -> object:
    reply = _reply(server, method, _params(line, column))
    ensure("result" in reply, f"discovery request failed: {reply!r}")
    return reply["result"]


def _inspect(source: bytes) -> dict[str, object]:
    try:
        return inspect_source(source)
    except VelaError as error:
        return {"status": "unavailable", "reason": error.kind}


def _server(source: str = _SOURCE) -> Server:
    server = Server(checker=lambda _: None, inspector=_inspect)
    capabilities = _object(_object(_reply(server, "initialize")["result"])["capabilities"])
    ensure(capabilities.get("completionProvider") == {"resolveProvider": False},
           "callable completion capability differs")
    ensure(capabilities.get("signatureHelpProvider") == {
        "triggerCharacters": ["(", ","], "retriggerCharacters": [","]},
        "signature help capability differs")
    server.handle(_message("initialized", identity=None))
    server.handle(_message("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": source}}, None))
    return server


def _signature(name: str, active: int) -> dict[str, object]:
    signature: dict[str, object] = {
        "label": f"public Nat {name}(Nat value, Nat extra)",
        "parameters": [{"label": "Nat value"}, {"label": "Nat extra"}]}
    if name == "Add":
        signature["documentation"] = {"kind": "plaintext", "value": "Earlier choice."}
    return {"signatures": [signature], "activeSignature": 0, "activeParameter": active}


def _completion_candidates_and_explicit_edits() -> None:
    server = _server()
    result = _object(_result(server, "textDocument/completion", 8, 12))
    items = cast("list[dict[str, object]]", result["items"])
    ensure(result["isIncomplete"] is True and [item["label"] for item in items] == ["Add", "Apply"],
           f"completion invented forward/incompatible/local candidates: {result!r}")
    expected_range = {"start": {"line": 8, "character": 11}, "end": {"line": 8, "character": 16}}
    for item in items:
        ensure(item["kind"] == 3 and item["textEdit"] == {"range": expected_range, "newText": item["label"]},
               "completion lost exact source edit or function identity")
    ensure(items[0].get("documentation") == {"kind": "plaintext", "value": "Earlier choice."},
           "completion lost authored documentation")
    ensure(_object(_result(server, "textDocument/completion", 8, 13))["items"] == items[1:],
           "completion ignored the typed prefix")
    ensure(_object(_result(server, "textDocument/completion", 8, 16))["items"] == items[1:],
           "completion failed at the identifier end")
    for line, column in ((7, 10), (8, 42), (3, 13), (0, 3), (8, 40)):
        ensure(_object(_result(server, "textDocument/completion", line, column))["items"] == [],
               "completion treated a value, declaration, comment or punctuation as a callable use")
    ensure(server.documents[_URI].text == _SOURCE, "completion applied its preview to the live overlay")


def _nested_arguments_labels_and_trivia() -> None:
    server = _server()
    for column in (21, 25, 26, 28, 29, 30, 38, 39):
        expected = _signature("Add", 0 if column <= 29 else 1)
        ensure(_result(server, "textDocument/signatureHelp", 8, column) == expected,
               f"inner call signature or argument differs at {column}")
    ensure(_result(server, "textDocument/signatureHelp", 8, 37) == _signature("Add", 1),
           "inner call's closing delimiter lost its active parameter")
    for column in (41, 42, 47, 50, 53):
        ensure(_result(server, "textDocument/signatureHelp", 8, column) == _signature("Apply", 1),
               f"nested commas/grouping changed outer parameter at {column}")
    for line, column in ((0, 3), (3, 20), (7, 14), (8, 11), (8, 54)):
        ensure(_result(server, "textDocument/signatureHelp", line, column) is None,
               "non-call context manufactured a signature")
    commented = _SOURCE.replace("extra: 1", "extra: /* invalid */ 1")
    ensure(_result(_server(commented), "textDocument/signatureHelp", 8, 30) is None,
           "unsupported source retained a signature")
    trivia = _SOURCE.replace("extra: 1", "extra: // ), ( , \U0001f600\r\n1")
    ensure(_result(_server(trivia), "textDocument/signatureHelp", 9, 0) == _signature("Add", 1),
           "comment punctuation or supplementary CRLF confused compiler token context")


def _zero_static_and_trailing_parameters() -> None:
    source = ("module Static;\n/// Zero.\npublic const Nat Zero() => 0;\n"
              "public const Nat Scale(const Nat width, Nat value) => width * value;\n"
              "public Nat Use() => Scale(width: Zero(), value: 2,);")
    server = _server(source)
    zero = _result(server, "textDocument/signatureHelp", 4, 38)
    ensure(zero == {"signatures": [{"label": "public const Nat Zero()", "parameters": [],
        "documentation": {"kind": "plaintext", "value": "Zero."}}], "activeSignature": 0},
        f"zero-argument signature supplied an invalid active parameter: {zero!r}")
    scale = _result(server, "textDocument/signatureHelp", 4, 50)
    ensure(scale == {"signatures": [{"label": "public const Nat Scale(const Nat width, Nat value)",
        "parameters": [{"label": "const Nat width"}, {"label": "Nat value"}]}],
        "activeSignature": 0, "activeParameter": 1},
        f"required-static or trailing-comma signature differs: {scale!r}")


def _lifecycle_edits_and_invalidated_facts() -> None:
    server = Server(checker=lambda _: None, inspector=_inspect)
    for method in ("textDocument/completion", "textDocument/signatureHelp"):
        ensure(_object(_reply(server, method, _params(8, 12))["error"])["code"] == -32002,
               "uninitialized callable request did not refuse")
    server = _server()
    before = _result(server, "textDocument/signatureHelp", 8, 30)
    server.handle(_message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
        "contentChanges": [{"range": {"start": {"line": 0, "character": 0},
                                      "end": {"line": 0, "character": 0}}, "text": "// moved\n"}]}, None))
    ensure(_result(server, "textDocument/signatureHelp", 9, 30) == before,
           "unsaved incremental edit lost the current signature")
    ensure(_object(_result(server, "textDocument/completion", 9, 12))["items"] != [],
           "unsaved incremental edit lost callable completion")
    server.handle(_message("workspace/didChangeWatchedFiles", {}, None))
    ensure(_result(server, "textDocument/signatureHelp", 9, 30) == before,
           "dependency invalidation failed to reconstruct current discovery facts")
    with redirect_stderr(StringIO()):
        server.handle(_message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 3},
            "contentChanges": [{"range": {}, "text": "refused"}]}, None))
    for method in ("textDocument/completion", "textDocument/signatureHelp"):
        ensure(_object(_reply(server, method, _params(9, 30))["error"])["code"] == -32801,
               "desynchronized source exposed discovery facts")
    server.handle(_message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 4},
        "contentChanges": [{"text": _SOURCE.replace("return Apply(", "return Unknown(")}]}, None))
    ensure(_result(server, "textDocument/signatureHelp", 8, 30) is None,
           "invalid source retained old signature")
    ensure(_result(server, "textDocument/completion", 8, 12) == {"isIncomplete": True, "items": []},
           "invalid source presented completion as complete")
    server.handle(_message("textDocument/didClose", {"textDocument": {"uri": _URI}}, None))
    ensure(_object(_reply(server, "textDocument/completion", _params(8, 12))["error"])["code"] == -32602,
           "closed document supplied completion")


def _malformed_coordinates_failures_and_stale_producer() -> None:
    server = _server()
    for method in ("textDocument/completion", "textDocument/signatureHelp"):
        for params in ({}, _params(-1, 0), _params(0, 4), _params(True, 0),
                       _params(100, 0), _params(8, 12, "file:///unopened.vela")):
            ensure(_object(_reply(server, method, params)["error"])["code"] == -32602,
                   "invalid discovery coordinates did not refuse")
    bad = copy.deepcopy(inspect_source(_SOURCE.encode()))
    cast("list[dict[str, object]]", bad["symbols"])[0]["detail"] = "forged"
    server.inspector = lambda _: bad
    ensure(_object(_reply(server, "textDocument/signatureHelp", _params(8, 30))["error"])["code"] == -32803,
           "malformed callable facts supplied signature help")

    def replaced(source: bytes) -> dict[str, object]:
        server.inspector = _inspect
        return _inspect(source)

    server.inspector = replaced
    ensure(_object(_reply(server, "textDocument/completion", _params(8, 12))["error"])["code"] == -32803,
           "producer replacement published a late completion")
    snapshot = SourceSnapshot(_URI, 1, _SOURCE, 1)
    facts = validate_inspection(snapshot, inspect_source(snapshot.source))
    try:
        project(SourceSnapshot(_URI, 2, _SOURCE, 2), facts, "textDocument/signatureHelp", (8, 30))
    except InspectionError:
        pass
    else:
        raise AssertionError("stale callable facts were accepted")


def _candidate_visibility_static_and_parameter_names() -> None:
    source = ("module Filter; public Nat Add(Nat value, Nat extra) => value + extra; "
              "public const Nat Alter(Nat value, Nat extra) => value + extra; "
              "public Nat Alien(Nat width, Nat count) => width + count; "
              "public Nat Apply(Nat value, Nat extra) => value * extra; "
              "public Nat Again(Nat value, Nat extra) => value + extra; "
              "public Nat Use() => Apply(value: 2, extra: 3); "
              "public Nat Afterwards(Nat value, Nat extra) => value + extra;")
    cursor = source.index("Apply(value:") + 1
    result = _object(_result(_server(source), "textDocument/completion", 0, cursor))
    ensure([item["label"] for item in cast("list[dict[str, object]]", result["items"])] == ["Add", "Apply"],
           "completion included incompatible static modes, parameter names or declarations after the selected target")


def _complete_bounds_and_worker_refusals() -> None:
    server = _server()
    with patch("toolchain.concrete.MAX_CONCRETE_PARTS", 1):
        reply = _reply(server, "textDocument/signatureHelp", _params(8, 30))
        ensure(_object(reply.get("error"))["code"] == -32803,
               "token budget exhaustion supplied a partial signature")
    ensure(_result(server, "textDocument/signatureHelp", 8, 30) == _signature("Add", 1),
           "token refusal poisoned later discovery requests")
    for method in ("textDocument/completion", "textDocument/signatureHelp"):
        request = _message(method, _params(8, 12 if method.endswith("completion") else 30))
        request["id"] = "x" * (MAX_BODY_BYTES - 180)
        encode_message(request)
        reply = server.handle(request)[0]
        ensure(_object(reply.get("error"))["code"] == -32803 and reply.get("id") == request["id"],
               "oversized discovery result was published or lost correlation")
        encode_message(reply)

    def failed(_: bytes) -> dict[str, object]:
        raise InspectionError("worker timeout")

    server.inspector = failed
    for method in ("textDocument/completion", "textDocument/signatureHelp"):
        ensure(_object(_reply(server, method, _params(8, 30))["error"])["code"] == -32803,
               "failed inspection exposed old callable discovery facts")


def _real_process_and_unsaved_edit() -> None:
    messages = [_message("initialize", identity=1), _message("initialized", identity=None),
        _message("textDocument/didOpen", {"textDocument": {
            "uri": _URI, "languageId": "vela", "version": 1, "text": _SOURCE}}, None),
        _message("textDocument/completion", _params(8, 12), 2),
        _message("textDocument/signatureHelp", _params(8, 30), 3),
        _message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
            "contentChanges": [{"text": "// \U0001f600 moved\r\n" + _SOURCE}]}, None),
        _message("textDocument/completion", _params(9, 12), 4),
        _message("textDocument/signatureHelp", _params(9, 30), 5),
        _message("shutdown", identity=6), _message("exit", identity=None)]
    tools = str(Path(__file__).resolve().parents[1])
    script = (f"import sys; sys.path.insert(0, {tools!r}); "
              "from toolchain.cli.vela_lsp import main; raise SystemExit(main())")
    completed = subprocess.run([sys.executable, "-I", "-c", script],
                               input=b"".join(encode_message(message) for message in messages),
                               capture_output=True, timeout=30, check=False)
    ensure(completed.returncode == 0 and completed.stderr == b"", f"discovery process failed: {completed.stderr!r}")
    stream = BytesIO(completed.stdout)
    replies: dict[int, dict[str, object]] = {}
    while (frame := read_frame(stream)) is not None:
        reply = _object(json.loads(frame))
        if "id" in reply:
            replies[cast("int", reply["id"])] = reply
    ensure(set(replies) == set(range(1, 7)), "discovery process lost correlated replies")
    ensure(replies[3].get("result") == _signature("Add", 1)
           and replies[5].get("result") == _signature("Add", 1), "wire signature help did not follow the unsaved edit")
    for identity, line in ((2, 8), (4, 9)):
        result = _object(replies[identity].get("result"))
        items = cast("list[dict[str, object]]", result["items"])
        ensure([item["label"] for item in items] == ["Add", "Apply"], "wire completion candidates differ")
        ensure(all(_object(_object(item["textEdit"])["range"])["start"] == {
            "line": line, "character": 11} for item in items), "wire completion reused old coordinates")


def cases() -> list[Case]:
    return [Case("callable-completion-candidates-prefixes-and-explicit-edits", _completion_candidates_and_explicit_edits),
            Case("nested-signatures-named-arguments-and-comment-delimiters", _nested_arguments_labels_and_trivia),
            Case("zero-static-and-trailing-parameter-signatures", _zero_static_and_trailing_parameters),
            Case("callable-lifecycle-edits-and-invalidation", _lifecycle_edits_and_invalidated_facts),
            Case("callable-malformed-coordinates-producer-and-stale-facts", _malformed_coordinates_failures_and_stale_producer),
            Case("callable-candidate-visibility-static-modes-and-parameter-names", _candidate_visibility_static_and_parameter_names),
            Case("callable-complete-bounds-and-worker-refusals", _complete_bounds_and_worker_refusals),
            Case("real-process-callable-discovery-and-unsaved-edit", _real_process_and_unsaved_edit)]
