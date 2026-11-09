# SPDX-License-Identifier: Apache-2.0
"""Independent semantic-token delta reconstruction and snapshot lifetime controls."""

import json
import subprocess
import sys
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from typing import BinaryIO, cast

from tests.harness import Case, ensure
from tests.test_vela_lsp_editor import _server as _compiler_server
from tests.test_vela_lsp_projection import _TEXT, _URI, _facts, _notice, _request
from toolchain.lsp import Server
from toolchain.lsp_services import InspectionError
from toolchain.lsp_tokens import token_edits
from toolchain.protocol_json import MAX_BODY_BYTES, decode_message, encode_message, read_frame

INDEPENDENT_CASES = True
_FULL = "textDocument/semanticTokens/full"
_DELTA = _FULL + "/delta"
_DATA = [2, 11, 2, 0, 1, 0, 7, 5, 1, 3, 0, 16, 5, 1, 2]


def _object(value: object) -> dict[str, object]:
    ensure(isinstance(value, dict), f"expected object: {value!r}")
    return cast("dict[str, object]", value)


def _inspect(source: bytes) -> dict[str, object]:
    if source == b"unavailable":
        return {"status": "unavailable", "reason": "syntax"}
    raw = _facts()
    if source != _TEXT.encode():
        ensure(source == ("// \U0001f600\r\n" + _TEXT).encode(), "unexpected test source")
        for record in cast("list[dict[str, object]]", raw["symbols"]) + cast(
                "list[dict[str, object]]", raw["occurrences"]):
            record["line"] = cast("int", record["line"]) + 1
    return raw


def _opened(delta: bool = True) -> Server:
    server = Server(checker=lambda _: None, inspector=_inspect)
    params = {"capabilities": {"textDocument": {"semanticTokens": {"requests": {"full": {"delta": delta}}}}}}
    reply = server.handle(_request("initialize", params))[0]
    ensure("result" in reply, f"initialization failed: {reply!r}")
    server.handle(_notice("initialized"))
    server.handle(_notice("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": _TEXT}}))
    return server


def _query(server: Server, previous: object = None, *, uri: str = _URI,
           identity: object = 1) -> dict[str, object]:
    params: dict[str, object] = {"textDocument": {"uri": uri}}
    method = _FULL
    if previous is not None:
        method = _DELTA
        params["previousResultId"] = previous
    return server.handle({"jsonrpc": "2.0", "id": identity, "method": method, "params": params})[0]


def _result(server: Server, previous: object = None, *, uri: str = _URI) -> dict[str, object]:
    reply = _query(server, previous, uri=uri)
    ensure("result" in reply, f"token query failed: {reply!r}")
    return _object(reply["result"])


def _reconstruct(previous: list[int], result: dict[str, object]) -> list[int]:
    ensure(isinstance(result.get("resultId"), str) and len(cast("str", result["resultId"])) == 64,
           "delta-capable result lacks bounded opaque identity")
    if "data" in result:
        ensure(set(result) == {"resultId", "data"}, "full fallback has invalid fields")
        return cast("list[int]", result["data"])
    ensure(set(result) == {"resultId", "edits"}, "delta result has invalid fields")
    data = previous.copy()
    edits = cast("list[dict[str, object]]", result["edits"])
    for edit in reversed(edits):
        start, count = cast("int", edit["start"]), cast("int", edit["deleteCount"])
        ensure(0 <= start <= start + count <= len(previous), "delta deletion is out of bounds")
        data[start:start + count] = cast("list[int]", edit.get("data", []))
    return data


def _change(server: Server, text: str, version: int = 2) -> None:
    server.handle(_notice("textDocument/didChange", {"textDocument": {"uri": _URI, "version": version},
                                                   "contentChanges": [{"text": text}]}))


def _exact_edits_and_negotiation() -> None:
    full_only = _opened(False)
    ensure(_result(full_only) == {"data": _DATA} and not full_only._token_history,
           "full-only client acquired unsolicited token identity or history")
    seeded = _result(full_only, "unknown")
    ensure(_reconstruct([], seeded) == _DATA, "unknown delta ID did not return current full tokens")
    server = _opened()
    first = _result(server)
    ensure(_reconstruct([], first) == _DATA, "negotiated full tokens differ from exact source sites")
    unchanged = _result(server, first["resultId"])
    ensure(unchanged["edits"] == [] and unchanged["resultId"] != first["resultId"],
           "unchanged delta replaced data or failed to advance its result identity")
    _change(server, "// \U0001f600\r\n" + _TEXT)
    changed = _result(server, unchanged["resultId"])
    ensure(changed.get("edits") == [{"start": 0, "deleteCount": 1, "data": [3]}],
           "leading Unicode/CRLF insertion did not yield the expected integer delta")
    ensure(_reconstruct(_DATA, changed) == [3, *_DATA[1:]], "client could not reconstruct moved tokens")
    # The sole retained result is replaced after successful publication.
    stale = _result(server, first["resultId"])
    ensure(stale.get("data") == [3, *_DATA[1:]] and len(server._token_history) == 1,
           "evicted ID reused stale tokens or unbounded history")
    _change(server, "unavailable", 3)
    refused = _result(server, stale["resultId"])
    ensure(refused.get("edits") == [{"start": 0, "deleteCount": 15}]
           and _reconstruct([3, *_DATA[1:]], refused) == [], "failed source retained semantic tokens")
    _change(server, _TEXT, 4)
    recovered = _result(server, refused["resultId"])
    ensure(_reconstruct([], recovered) == _DATA, "recovered source did not insert current complete tokens")


def _history_lifetimes_and_isolation() -> None:
    def replacement(source: bytes) -> dict[str, object]:
        return _inspect(source)
    for method in ("textDocument/didSave", "workspace/didChangeConfiguration", "workspace/didChangeWatchedFiles"):
        server = _opened()
        first = _result(server)
        server.handle(_notice(method, {"textDocument": {"uri": _URI}}))
        ensure(not server._token_history, f"{method} retained a delta base")
        ensure(_result(server, first["resultId"]).get("data") == _DATA,
               f"{method} used invalidated token history")
    for replace in (False, True):
        server = _opened()
        first = _result(server)
        if replace:
            server.inspector = replacement
        else:
            server.invalidate_inspections()
        ensure(_result(server, first["resultId"]).get("data") == _DATA,
               "producer replacement or generation advance reused token history")
    server = _opened()
    first = _result(server)
    other = "untitled:other.vela"
    server.handle(_notice("textDocument/didOpen", {"textDocument": {
        "uri": other, "languageId": "vela", "version": 1, "text": _TEXT}}))
    ensure(_result(server, first["resultId"], uri=other).get("data") == _DATA,
           "another document's result identity selected a delta base")
    with redirect_stderr(StringIO()):
        server.handle(_notice("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
                                                       "contentChanges": [{"range": {}, "text": "bad"}]}))
    ensure(_URI not in server._token_history
           and _object(_query(server, first["resultId"])["error"])["code"] == -32801,
           "refused update retained or exposed its delta base")
    _change(server, _TEXT, 3)
    ensure(_result(server, first["resultId"]).get("data") == _DATA, "recovery revived refused history")
    last = _result(server)
    server.handle(_notice("textDocument/didClose", {"textDocument": {"uri": _URI}}))
    server.handle(_notice("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": _TEXT}}))
    ensure(_result(server, last["resultId"]).get("data") == _DATA, "reopen revived a previous document lifetime")
    server.handle(_request("shutdown"))
    ensure(not server._token_history, "shutdown retained token history")
    server = _opened()
    _result(server)
    server.handle(_notice("exit"))
    ensure(not server._token_history, "exit retained token history")


def _failures_and_atomic_publication() -> None:
    server = _opened()
    first = _result(server)
    for invalid in (True, 1, [], {}):
        ensure(_object(_query(server, invalid)["error"])["code"] == -32602,
               "malformed previousResultId was accepted")
    source = "module Bounds;\n" + "".join(f"public Nat F{index}()=>0;\n" for index in range(20))
    server = _compiler_server(source)
    server.handle(_notice("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": source}}))
    first = _result(server, "unknown")
    previous = server._token_history[_URI]
    request: dict[str, object] = {"jsonrpc": "2.0", "id": "", "method": _DELTA,
                                  "params": {"textDocument": {"uri": _URI}, "previousResultId": "x" * 64}}
    overhead = len(json.dumps(request, separators=(",", ":")).encode())
    request["id"] = "i" * (MAX_BODY_BYTES - overhead)
    encode_message(request)
    reply = server.handle(request)[0]
    ensure(_object(reply.get("error"))["code"] == -32803 and server._token_history[_URI] is previous,
           "oversized reply advanced history without publishing its token result")
    ensure(_result(server, first["resultId"]).get("edits") == [], "reply refusal poisoned the prior delta base")
    server.invalidate_inspections()
    def failed(_: bytes) -> dict[str, object]:
        raise InspectionError("worker failed")
    server.inspector = failed
    ensure(_object(_query(server, "unknown")["error"])["code"] == -32803 and not server._token_history,
           "worker failure published token history")
    for full in ({"delta": "yes"}, 1, []):
        initialized = Server().handle(_request("initialize", {"capabilities": {
            "textDocument": {"semanticTokens": {"requests": {"full": full}}}}}))[0]
        ensure(_object(initialized["error"])["code"] == -32602, "malformed delta capability initialized server")


def _integer_edit_reconstruction() -> None:
    streams = ((), (1,), (2,), (1, 2), (1, 2, 3), (1, 9, 3), (1, 2, 3, 4), (9, 2, 8, 4))
    for previous in streams:
        for current in streams:
            edits = token_edits(previous, current)
            result: dict[str, object] = {"resultId": "0" * 64, "edits": edits}
            ensure(_reconstruct(list(previous), result) == list(current), "integer edit changed reconstructed tokens")
            ensure(len(edits) <= 1 and (edits != [] or previous == current), "delta emitted redundant edits")


def _process_scenario() -> None:
    tools = str(Path(__file__).resolve().parents[1])
    script = (f"import sys; sys.path.insert(0, {tools!r}); "
              "from toolchain.cli.vela_lsp import main; raise SystemExit(main())")
    with subprocess.Popen([sys.executable, "-I", "-c", script], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        ensure(process.stdin is not None and process.stdout is not None, "stdio pipes unavailable")
        input_stream = cast("BinaryIO", process.stdin)
        output_stream = cast("BinaryIO", process.stdout)
        def send(message: dict[str, object]) -> None:
            input_stream.write(encode_message(message))
            input_stream.flush()
        def receive() -> dict[str, object]:
            raw = read_frame(output_stream)
            ensure(raw is not None, "server closed before correlated reply")
            return decode_message(cast("bytes", raw))
        send(_request("initialize", {"capabilities": {"textDocument": {
            "semanticTokens": {"requests": {"full": {"delta": True}}}}}}))
        ensure("result" in receive(), "real server refused delta negotiation")
        send(_notice("initialized"))
        send(_notice("textDocument/didOpen", {"textDocument": {
            "uri": _URI, "languageId": "vela", "version": 1, "text": _TEXT}}))
        ensure(_object(receive()["params"])["diagnostics"] == [], "real initial source was refused")
        send(_request(_FULL, {"textDocument": {"uri": _URI}}, 2))
        first = _object(receive()["result"])
        ensure(_reconstruct([], first) == _DATA, "real full stream differs from expected compiler facts")
        send(_notice("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
            "contentChanges": [{"range": {"start": {"line": 0, "character": 0},
                                          "end": {"line": 0, "character": 0}}, "text": "// \U0001f600\r\n"}]}))
        ensure(_object(receive()["params"])["version"] == 2, "real unsaved overlay lost its version")
        send(_request(_DELTA, {"textDocument": {"uri": _URI}, "previousResultId": first["resultId"]}, 3))
        changed = _object(receive()["result"])
        ensure(_reconstruct(_DATA, changed) == [3, *_DATA[1:]] and "edits" in changed,
               "real delta did not reconstruct unsaved Unicode/CRLF overlay")
        send(_request("shutdown", identity=4))
        ensure(receive().get("id") == 4, "shutdown lost request correlation")
        send(_notice("exit"))
        _, stderr = process.communicate(timeout=5)
        ensure(process.returncode == 0 and not stderr, f"real delta session failed: {stderr!r}")


def _real_process() -> None:
    tools = str(Path(__file__).resolve().parents[1])
    script = (f"import sys; sys.path.insert(0, {tools!r}); "
              "from tests.test_vela_lsp_delta import _process_scenario; _process_scenario()")
    done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, timeout=35, check=False)
    ensure(done.returncode == 0, f"real semantic delta session failed: {done.stderr.decode(errors='replace')}")


def cases() -> list[Case]:
    return [Case("semantic-delta-exact-edits-negotiation-and-recovery", _exact_edits_and_negotiation),
            Case("semantic-delta-history-lifetimes-and-document-isolation", _history_lifetimes_and_isolation),
            Case("semantic-delta-failures-and-atomic-publication", _failures_and_atomic_publication),
            Case("semantic-delta-independent-integer-reconstruction", _integer_edit_reconstruction),
            Case("semantic-delta-real-process-unsaved-overlay", _real_process)]
