# SPDX-License-Identifier: Apache-2.0
"""Independent binding, edit, coordinate and invalidation controls for local rename."""

import copy
from contextlib import redirect_stderr
from io import StringIO
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from tests.test_vela_lsp_projection import _error_code, _notice, _request
from toolchain import VelaError, inspect_source
from toolchain.lsp import Server
from toolchain.lsp_services import InspectionError
from toolchain.protocol_json import FrameError, encode_message
from toolchain.source import SourceSnapshot

INDEPENDENT_CASES = True
_URI = "file:///not-read/rename.vela"
_TEXT = ("// \U0001f600\r\nmodule Rename;\r\n"
         "public Nat F(Nat input) { let value = input; let other = input; return value + other; }\r\n")


def _inspect(source: bytes) -> dict[str, object]:
    try:
        return inspect_source(source)
    except VelaError as error:
        return {"status": "unavailable", "reason": error.kind}


def _server(text: str = _TEXT, versioned: bool = True) -> Server:
    server = Server(checker=lambda _: None, inspector=_inspect)
    server.handle(_request("initialize", {"capabilities": {
        "workspace": {"workspaceEdit": {"documentChanges": versioned}}}}))
    server.handle(_notice("initialized"))
    server.handle(_notice("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 7, "text": text}}))
    return server


def _query(server: Server, name: object = "renamed", *, column: int = 32,
           method: str = "textDocument/rename") -> list[dict[str, object]]:
    return server.handle(_request(method, {"textDocument": {"uri": _URI},
        "position": {"line": 2, "character": column}, "newName": name}))


def _range(start: int, end: int) -> dict[str, object]:
    return {"start": {"line": 2, "character": start}, "end": {"line": 2, "character": end}}


def _preview_and_scope() -> None:
    server = _server()
    snapshot = server.documents[_URI]
    ensure(_query(server, method="textDocument/prepareRename")[0]["result"] == {
        "range": _range(30, 35), "placeholder": "value"}, "prepare did not select the local declaration")
    expected = {"documentChanges": [{"textDocument": {"uri": _URI, "version": 7}, "edits": [
        {"range": _range(30, 35), "newText": "renamed"},
        {"range": _range(71, 76), "newText": "renamed"}]}]}
    ensure(_query(server)[0].get("result") == expected, "rename changed the independently expected edit set")
    ensure(_query(server, column=72)[0].get("result") == expected,
           "reference selection did not share declaration identity")
    ensure(server.documents[_URI] is snapshot and server.documents[_URI].text == _TEXT,
           "rename preview modified the open overlay")
    same = _query(server, "value")[0]["result"]
    ensure(cast("dict[str, object]", same)["documentChanges"] == [
        {"textDocument": {"uri": _URI, "version": 7}, "edits": []}], "same-name rename produced edits")
    for column in (11, 17, 35, 36):
        ensure(_query(server, column=column)[0].get("result") is None,
               "rename selected an exported declaration, parameter, punctuation or token end")
    no_versions = _server(versioned=False)
    ensure(_error_code(_query(no_versions)) == -32803, "unversioned client received rename edits")
    initialize = Server().handle(_request("initialize", {"capabilities": {
        "workspace": {"workspaceEdit": {"documentChanges": True}}}}))[0]
    result = cast("dict[str, object]", initialize["result"])
    ensure(cast("dict[str, object]", result["capabilities"])["renameProvider"] == {"prepareProvider": True},
           "versioned client did not receive the prepare capability")


def _capture_and_namespaces() -> None:
    # The local may shadow a module constant, so an unchanged use of that
    # constant can be captured while the edited source still checks.
    text = ("// \U0001f600\r\nmodule Rename;\r\n"
            "public const Nat Other = 10; public Nat F(Nat input) { let value = input; "
            "return value + Other; }\r\n")
    server = _server(text)
    column = text.splitlines()[2].index("value")
    ensure(_inspect(text.replace("value", "Other").encode())["status"] == "ok",
           "capture control was rejected before the binding-preservation comparison")
    ensure(_error_code(_query(server, "Other", column=column)) == -32803,
           "type-correct capture was offered as a safe rename")
    ensure(_error_code(_query(_server(), "other")) == -32803,
           "duplicate local declaration rename was accepted")
    for name in ("if", "Nat", "async", "x.y", "", "\U0001f600", "a\n", 1, True):
        ensure(_error_code(_query(_server(), name)) == -32602, f"invalid rename accepted: {name!r}")
    independent = ("// \U0001f600\r\nmodule Rename;\r\n"
                   "public Nat Helper(Nat input) => input;\r\n"
                   "public Nat F(Nat input) { let value = input; return Helper(value); }\r\n")
    server = _server(independent)
    params = {"textDocument": {"uri": _URI}, "position": {"line": 3, "character": 30}, "newName": "Helper"}
    ensure("result" in server.handle(_request("textDocument/rename", params))[0],
           "rename incorrectly merged the pure call and value namespaces")


def _unicode_and_branch_identity() -> None:
    text = ("module Rename;\r\n// retained \U0001f600\r\n"
            "public Nat F(Nat input) { if (true) { let value = input; return value; } "
            "else { let value = input; return value; } }\r\n")
    server = _server(text)
    column = text.splitlines()[2].index("value")
    reply = _query(server, "longerName", column=column)[0]
    edits = cast("list[dict[str, object]]", cast("dict[str, object]", reply["result"])["documentChanges"])
    replacements = cast("list[dict[str, object]]", edits[0]["edits"])
    ensure(replacements == [{"range": _range(42, 47), "newText": "longerName"},
                            {"range": _range(64, 69), "newText": "longerName"}],
           "same-spelled sibling binding entered the rename edit set")
    snapshot = SourceSnapshot(_URI, 7, text, 1)
    data = snapshot.source
    for item in reversed(replacements):
        span = cast("dict[str, dict[str, int]]", item["range"])
        first, last = span["start"], span["end"]
        begin = snapshot.position_byte_offset(first["line"], first["character"])
        end = snapshot.position_byte_offset(last["line"], last["character"])
        data = data[:begin] + str(item["newText"]).encode() + data[end:]
    ensure(data.decode().count("longerName") == 2 and data.decode().count("value") == 2
           and data.count(b"\r\n") == 3, "rename changed unrelated identifiers or newline bytes")


def _stale_and_failed_candidate() -> None:
    server = _server()
    ensure("result" in _query(server)[0], "initial candidate check failed")
    server.handle(_notice("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 8},
        "contentChanges": [{"text": _TEXT.replace("value", "updated")}]}))
    ensure(_query(server, column=30)[0].get("result") is not None,
           "current source could not supply a new rename")
    with redirect_stderr(StringIO()):
        server.handle(_notice("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 8},
            "contentChanges": [{"text": _TEXT}]}))
    ensure(_error_code(_query(server)) == -32801, "desynchronized overlay offered an edit")
    for failure in (InspectionError("unavailable"), {"status": "unavailable", "reason": "type"}):
        server = _server()
        _query(server, method="textDocument/prepareRename")

        def inspect(_source: bytes) -> dict[str, object]:
            if isinstance(failure, Exception):
                raise failure
            return copy.deepcopy(failure)

        server.inspector = inspect
        reply = _query(server)
        ensure((_error_code(reply) == -32803) if isinstance(failure, Exception)
               else reply[0].get("result") is None, "failed producer published rename edits")
    for invalidation in ("source", "generation", "producer"):
        server = _server()
        original = server.documents[_URI]

        def inspect(source: bytes, kind: str = invalidation) -> dict[str, object]:
            if source != original.source:
                if kind == "generation":
                    server.invalidate_inspections()
                elif kind == "producer":
                    server.inspector = _inspect
                else:
                    server.handle(_notice("textDocument/didChange", {
                        "textDocument": {"uri": _URI, "version": 8}, "contentChanges": [{"text": _TEXT}]}))
            return _inspect(source)

        server.inspector = inspect
        ensure(_error_code(_query(server)) == -32803,
               f"{invalidation} change during candidate recheck published stale edits")
    server = _server()

    def bounded(message: dict[str, object]) -> bytes:
        if "result" in message:
            raise FrameError("reply exceeds bound")
        return encode_message(message)

    with patch("toolchain.lsp.encode_message", side_effect=bounded):
        ensure(_error_code(_query(server)) == -32803, "over-budget rename reply was published")
    ensure(server.documents[_URI].text == _TEXT, "refused rename changed the source")


def cases() -> list[Case]:
    return [Case("local rename preview and scope", _preview_and_scope),
            Case("local rename capture and namespaces", _capture_and_namespaces),
            Case("local rename Unicode and branch identities", _unicode_and_branch_identity),
            Case("local rename stale and failed candidates", _stale_and_failed_candidate)]
