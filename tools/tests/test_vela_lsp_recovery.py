# SPDX-License-Identifier: Apache-2.0
"""Independent one-hole completion edits, ambiguity refusals and overlay lifecycle controls."""

import copy
import hashlib
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from tests.test_vela_lsp_clients import _recovery_completion_wire_controls
from tests.test_vela_lsp_discovery import _inspect, _message, _object
from toolchain import translate
from toolchain.completion import recover
from toolchain.lsp import Server
from toolchain.lsp_recovery import inspect_recovery, project_recovery
from toolchain.lsp_services import InspectionError
from toolchain.protocol_json import encode_message, read_frame
from toolchain.source import SourceSnapshot

INDEPENDENT_CASES = True
_URI = "untitled:recovery.vela"
_PREFIX = "// \U0001f600\r\nmodule Recovery;\r\npublic const Nat Count = 3;\r\n"


def _fixture(marked: str) -> tuple[Server, SourceSnapshot, tuple[int, int]]:
    source, cursor = marked.replace("|", ""), len(marked[:marked.index("|")].encode())
    server = Server(checker=lambda _: None, inspector=_inspect, completer=recover)
    server.handle(_message("initialize"))
    server.handle(_message("initialized", identity=None))
    server.handle(_message("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": source}}, None))
    snapshot = server.documents[_URI]
    point = snapshot.byte_position(cursor)
    return server, snapshot, (point["line"], point["character"])


def _reply(server: Server, point: tuple[int, int]) -> dict[str, object]:
    return server.handle(_message("textDocument/completion", {
        "textDocument": {"uri": _URI}, "position": {"line": point[0], "character": point[1]}}))[0]


def _choices(marked: str) -> list[dict[str, object]]:
    server, snapshot, point = _fixture(marked)
    reply = _reply(server, point)
    result = _object(reply.get("result"))
    ensure(result.get("isIncomplete") is True, "recovered source claimed complete analysis")
    ensure(server.documents[_URI] is snapshot, "recovery replaced the original source overlay")
    return cast("list[dict[str, object]]", result["items"])


def _labels(items: list[dict[str, object]]) -> list[object]:
    return [item["label"] for item in items]


def _typed_empty_sites_and_full_token_edits() -> None:
    marked = _PREFIX + "public Nat Use(Nat amount, bool active) { let earlier = amount; return |; }"
    items = _choices(marked)
    ensure(_labels(items) == ["Count", "amount", "earlier"], "empty return lost type or source order")
    column = marked.split("\r\n")[-1].index("|")
    ensure(all(item["textEdit"] == {"range": {
        "start": {"line": 3, "character": column}, "end": {"line": 3, "character": column}},
        "newText": item["label"]} for item in items), "empty completion edit was not an insertion")
    unfinished = marked.replace("return |", "return ear|zzz")
    items = _choices(unfinished)
    ensure(_labels(items) == ["earlier"], "unfinished identifier completion ignored its prefix")
    ensure(items[0]["textEdit"] == {"range": {
        "start": {"line": 3, "character": column}, "end": {"line": 3, "character": column + 6}},
        "newText": "earlier"}, "unfinished completion failed to replace the entire identifier")
    boolean = _PREFIX + "public Nat Use(Nat amount, bool active) { if (|) { return amount; } else { return 1; } }"
    ensure(_labels(_choices(boolean)) == ["active"], "empty Boolean condition acquired numeric candidates")


def _scope_static_and_diagnostic_preservation() -> None:
    static = (_PREFIX + "public const Nat Pick(const Nat limit, Nat value) => value; "
              "public Nat Use(const Nat limit, Nat amount) { return Pick(|, amount); }")
    ensure(_labels(_choices(static)) == ["Count", "limit"], "missing static argument exposed runtime values")
    branches = (_PREFIX + "public Nat Use(Nat amount, bool active) { if (active) { "
                "let left = amount; return |; } else { let right = amount; return amount; } }")
    ensure(_labels(_choices(branches)) == ["Count", "amount", "left"], "recovery leaked a sibling scope")
    server, snapshot, point = _fixture(static)
    before = _inspect(snapshot.source)
    ensure(before.get("status") == "unavailable", "fixture was already accepted source")
    _reply(server, point)
    ensure(_inspect(snapshot.source) == before, "recovery changed original-source diagnostic status")
    for item in _choices(static):
        edit = _object(item["textEdit"])
        selected = _object(edit["range"])
        first, last = _object(selected["start"]), _object(selected["end"])
        start = snapshot.position_byte_offset(cast("int", first["line"]), cast("int", first["character"]))
        end = snapshot.position_byte_offset(cast("int", last["line"]), cast("int", last["character"]))
        translate(snapshot.source[:start] + cast("str", edit["newText"]).encode() + snapshot.source[end:])


def _ambiguity_unrelated_errors_and_token_boundaries() -> None:
    for marked in (
            _PREFIX + "public Nat Use(Nat amount, bool active) { let value = |; return amount; }",
            _PREFIX + "public Nat Use(Nat amount) { return | + missing; }",
            _PREFIX + "public Nat Use(Nat amount) { return | }",
            _PREFIX + "public Nat Use(Nat amount) { // co|mment\r\n return missing; }",
            _PREFIX + "public Nat Use(Nat amount) { return mi|ssing(amount); }",
            _PREFIX + "public Nat Use(Nat amount) { ret|urn missing; }"):
        ensure(_choices(marked) == [], f"unsupported or ambiguous recovery published candidates: {marked!r}")
    for offset in (True, -1, 100_000):
        try:
            recover(b"module M;", offset)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid recovery cursor was accepted")


def _malformed_repairs_and_late_results_refuse() -> None:
    marked = _PREFIX + "public Nat Use(Nat amount) { return am|zzz; }"
    server, snapshot, point = _fixture(marked)
    cursor = snapshot.position_byte_offset(*point)
    raw = recover(snapshot.source, cursor)
    ensure(raw.get("status") == "recovered", "valid repair fixture failed")
    for mutation in ("span", "literal", "literal-object", "facts", "extra"):
        broken = copy.deepcopy(raw)
        if mutation == "span":
            broken["span"] = [0, 1]
        elif mutation == "literal":
            broken["literal"] = "true"
        elif mutation == "literal-object":
            broken["literal"] = []
        elif mutation == "facts":
            broken["facts"] = {"status": "unavailable", "reason": "syntax"}
        else:
            broken["accepted"] = True
        try:
            project_recovery(snapshot, point, broken)
        except InspectionError:
            pass
        else:
            raise AssertionError(f"malformed {mutation} recovery facts were accepted")
    def late(source: bytes, offset: int) -> dict[str, object]:
        server.invalidate_inspections()
        return recover(source, offset)
    server.completer = late
    ensure(_object(_reply(server, point).get("error")).get("code") == -32803,
           "recovery reply survived producer-generation invalidation")
    ensure(server.documents[_URI] is snapshot, "late recovery mutated the source")
    with patch("toolchain.lsp_recovery.subprocess.run", return_value=subprocess.CompletedProcess(
            [], 0, b'{"status":"unavailable","source_sha256":"stale"}', b"")):
        try:
            inspect_recovery(snapshot.source, cursor)
        except InspectionError:
            pass
        else:
            raise AssertionError("worker recovery accepted a stale source binding")
    ensure(hashlib.sha256(snapshot.source).hexdigest() != "stale", "digest control did not differ")
    with patch("toolchain.lsp_recovery.subprocess.run", side_effect=subprocess.TimeoutExpired([], 5)):
        try:
            inspect_recovery(snapshot.source, cursor)
        except InspectionError:
            pass
        else:
            raise AssertionError("timed-out recovery worker supplied proposals")
    with patch("toolchain.lsp_recovery.MAX_BODY_BYTES", 1), patch(
            "toolchain.lsp_recovery.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"{}", b"")):
        try:
            inspect_recovery(snapshot.source, cursor)
        except InspectionError:
            pass
        else:
            raise AssertionError("over-budget recovery worker supplied a partial result")


def _real_stdio_incomplete_source_and_unsaved_unicode_edit() -> None:
    source = _PREFIX + "public Nat Use(Nat amount) { return amzzz; }"
    column = source.split("\r\n")[-1].index("amzzz") + 2
    messages = [
        _message("initialize", identity=1), _message("initialized", identity=None),
        _message("textDocument/didOpen", {"textDocument": {
            "uri": _URI, "languageId": "vela", "version": 1, "text": source}}, None),
        _message("textDocument/completion", {"textDocument": {"uri": _URI},
            "position": {"line": 3, "character": column}}, 2),
        _message("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
            "contentChanges": [{"text": "// unsaved \U0001f600\r\n" + source}]}, None),
        _message("textDocument/completion", {"textDocument": {"uri": _URI},
            "position": {"line": 4, "character": column}}, 3),
        _message("shutdown", identity=4), _message("exit", identity=None)]
    root = Path(__file__).resolve().parents[1]
    script = (f"import sys; sys.path.insert(0, {str(root)!r}); "
              "from toolchain.lsp import serve; raise SystemExit(serve(sys.stdin.buffer, sys.stdout.buffer))")
    completed = subprocess.run([sys.executable, "-I", "-c", script],
                               input=b"".join(encode_message(message) for message in messages),
                               capture_output=True, timeout=40, check=False)
    ensure(completed.returncode == 0 and not completed.stderr, f"recovery stdio session failed: {completed.stderr!r}")
    output = BytesIO(completed.stdout)
    replies: dict[object, dict[str, object]] = {}
    diagnostics: list[dict[str, object]] = []
    while (frame := read_frame(output)) is not None:
        message = cast("dict[str, object]", json.loads(frame))
        if "id" in message:
            replies[message["id"]] = message
        else:
            diagnostics.append(_object(message["params"]))
    ensure(set(replies) == {1, 2, 3, 4}, "recovery stdio session lost request correlation")
    for identity, line in ((2, 3), (3, 4)):
        result = _object(replies[identity]["result"])
        items = cast("list[dict[str, object]]", result["items"])
        ensure(_labels(items) == ["amount"], "real worker lost unfinished identifier prefix or type")
        ensure(_object(_object(_object(items[0]["textEdit"])["range"])["start"])["line"] == line,
               "unsaved edit retained old recovery coordinates")
    ensure(len(diagnostics) == 2 and all(cast("list[object]", item["diagnostics"]) for item in diagnostics),
           "recovery completion cleared the original-source errors")


def cases() -> list[Case]:
    return [Case("recovery-completion-empty-typed-sites-and-full-identifier-edits", _typed_empty_sites_and_full_token_edits),
            Case("recovery-completion-static-scope-and-original-diagnostics", _scope_static_and_diagnostic_preservation),
            Case("recovery-completion-ambiguity-unrelated-errors-and-token-boundaries", _ambiguity_unrelated_errors_and_token_boundaries),
            Case("recovery-completion-malformed-stale-and-late-worker-refusals", _malformed_repairs_and_late_results_refuse),
            Case("recovery-completion-independent-client-wire-evidence-controls", _recovery_completion_wire_controls),
            Case("real-stdio-recovery-completion-unsaved-unicode-crlf-source", _real_stdio_incomplete_source_and_unsaved_unicode_edit)]
