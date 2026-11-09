# SPDX-License-Identifier: Apache-2.0
"""Independent controls for immutable, bounded LSP inspection reuse."""

import json
import subprocess
from contextlib import redirect_stderr
from io import StringIO
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from tests.test_vela_lsp_projection import (
    _TEXT,
    _URI,
    _error_code,
    _facts,
    _notice,
    _opened,
    _params,
    _request,
)
from toolchain import lsp_services
from toolchain.lsp import MAX_DOCUMENTS, Server
from toolchain.lsp_services import InspectionError, project_inspection, validate_inspection
from toolchain.protocol_json import MAX_BODY_BYTES, encode_message
from toolchain.source import SourceSnapshot


def _query(server: Server, method: str = "textDocument/hover", uri: str = _URI) -> dict[str, object]:
    params = _params(uri)
    if method == "textDocument/references":
        params["context"] = {"includeDeclaration": True}
    if method == "textDocument/inlayHint":
        params["range"] = {"start": {"line": 0, "character": 0},
                           "end": {"line": 3, "character": 0}}
    return server.handle(_request(method, params))[0]


def _reuses_validated_facts() -> None:
    raw = _facts()
    with (patch("toolchain.lsp.validate_inspection", wraps=validate_inspection) as validate,
          patch("toolchain.lsp.inspect_document", return_value=raw) as inspect):
        server = _opened(inspect)
        for method in ("textDocument/hover", "textDocument/definition", "textDocument/references",
                       "textDocument/documentSymbol", "textDocument/inlayHint", "textDocument/semanticTokens/full"):
            ensure("result" in _query(server, method), f"cached {method} failed")
        ensure(inspect.call_count == validate.call_count == 1,
               "unchanged editor queries repeated compiler work or response validation")
        cast("list[dict[str, object]]", raw["symbols"])[1]["detail"] = "mutated untrusted response"
        hover = _query(server)
        ensure("value: Nat" in str(hover.get("result"))
               and "mutated" not in str(hover.get("result")),
               "cached facts retained mutable producer-owned objects")
        hover["result"] = "mutated client reply"
        ensure("value: Nat" in str(_query(server).get("result")),
               "a client reply changed the cached facts")


def _snapshot_and_lifecycle_invalidation() -> None:
    with patch("toolchain.lsp.inspect_document", side_effect=lambda _: _facts()) as inspect:
        server = _opened(inspect)
        ensure("result" in _query(server), "initial inspection failed")
        expected = 1
        version = 1
        for changes in ([{"text": _TEXT}], [], [{"range": {
                "start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}, "text": ""}]):
            version += 1
            server.handle(_notice("textDocument/didChange", {
                "textDocument": {"uri": _URI, "version": version}, "contentChanges": changes}))
            ensure(not server._inspections, "a replacement retained the previous cached inspection")
            ensure("result" in _query(server), "replacement snapshot could not be inspected")
            expected += 1
            ensure(inspect.call_count == expected, "same-text changes reused an earlier snapshot's facts")
        for method in ("textDocument/didSave", "workspace/didChangeConfiguration", "workspace/didChangeWatchedFiles"):
            server.handle(_notice(method, {"textDocument": {"uri": _URI}}))
            ensure(not server._inspections, f"{method} retained cached facts")
            ensure("result" in _query(server), f"{method} prevented a fresh inspection")
            expected += 1
            ensure(inspect.call_count == expected, f"{method} reused the previous inspection")
        with redirect_stderr(StringIO()):
            server.handle(_notice("textDocument/didChange", {
                "textDocument": {"uri": _URI, "version": version}, "contentChanges": [{"text": _TEXT}]}))
        ensure(not server._inspections and _error_code([_query(server)]) == -32801,
               "a refused update retained or exposed cached facts")
        version += 1
        server.handle(_notice("textDocument/didChange", {
            "textDocument": {"uri": _URI, "version": version}, "contentChanges": [{"text": _TEXT}]}))
        ensure("result" in _query(server), "full replacement did not restore fresh inspection")
        expected += 1
        ensure(inspect.call_count == expected, "recovery revived the refused snapshot's facts")
        server.handle(_notice("textDocument/didClose", {"textDocument": {"uri": _URI}}))
        ensure(not server._inspections, "close retained the document's facts")
        server.handle(_notice("textDocument/didOpen", {"textDocument": {
            "uri": _URI, "languageId": "vela", "version": 1, "text": _TEXT}}))
        ensure("result" in _query(server), "reopen could not be inspected")
        ensure(inspect.call_count == expected + 1, "reopen reused a previous session's facts")
        server.handle(_request("shutdown"))
        ensure(not server._inspections, "shutdown retained cached facts")
        exited = _opened(inspect)
        _query(exited)
        exited.handle(_notice("exit"))
        ensure(not exited._inspections, "exit retained cached facts")


def _producer_replacement_and_generation() -> None:
    with patch("toolchain.lsp.inspect_document", side_effect=lambda _: _facts()) as first:
        server = _opened(first)
        ensure("result" in _query(server), "initial producer failed")
        with patch("toolchain.lsp.inspect_document", side_effect=lambda _: _facts()) as second:
            server.inspector = second
            ensure("result" in _query(server) and first.call_count == second.call_count == 1,
                   "replacing the producer reused the old producer's facts")
            server.invalidate_inspections()
            ensure("result" in _query(server) and second.call_count == 2,
                   "explicit producer generation change reused cached facts")

            def changes_generation(_source: bytes) -> dict[str, object]:
                server.invalidate_inspections()
                return _facts()

            server.inspector = changes_generation
            ensure(_error_code([_query(server)]) == -32803 and not server._inspections,
                   "a producer generation change during inspection published or cached old facts")
            server.inspector = second
            ensure("result" in _query(server) and second.call_count == 3,
                   "producer generation refusal prevented a later fresh inspection")

            def changes_source(_source: bytes) -> dict[str, object]:
                server.handle(_notice("textDocument/didChange", {
                    "textDocument": {"uri": _URI, "version": 2}, "contentChanges": [{"text": _TEXT}]}))
                return _facts()

            server.inspector = changes_source
            ensure(_error_code([_query(server)]) == -32803 and not server._inspections,
                   "an inspection published or cached facts after its source changed")
            server.inspector = second
            ensure("result" in _query(server) and second.call_count == 4,
                   "source change during inspection prevented a later fresh result")


def _failures_retry() -> None:
    invalid = {"status": "ok", "symbols": [], "occurrences": [{"symbol": 0}]}
    oversized = {"status": "ok", "symbols": [], "occurrences": [], "extra": "x" * MAX_BODY_BYTES}
    failures: tuple[object, ...] = (
        InspectionError("producer failed"), OSError("producer unavailable"),
        subprocess.TimeoutExpired("producer", 5), invalid, oversized,
        {"status": "unavailable", "reason": "inspection-limit"},
        {"status": "unavailable", "reason": "syntax"},
    )
    for failure in failures:
        with patch("toolchain.lsp.inspect_document", side_effect=[failure, _facts()]) as inspect:
            server = _opened(inspect)
            first = _query(server)
            ensure("error" in first or first.get("result") is None, "failed inspection exposed facts")
            ensure(not server._inspections, "failed or unavailable inspection was cached")
            ensure("value: Nat" in str(_query(server).get("result")) and inspect.call_count == 2,
                   "failed inspection was reused instead of retried")


def _cache_and_reply_bounds() -> None:
    with patch("toolchain.lsp.inspect_document", side_effect=lambda _: _facts()) as inspect:
        server = _opened(inspect)
        _query(server)
        for index in range(1, MAX_DOCUMENTS):
            uri = f"untitled:cache-{index}"
            server.handle(_notice("textDocument/didOpen", {"textDocument": {
                "uri": uri, "languageId": "vela", "version": 1, "text": _TEXT}}))
            ensure("result" in _query(server, uri=uri), "another document could not be inspected")
        ensure(len(server._inspections) == inspect.call_count == MAX_DOCUMENTS,
               "cache exceeded the open-document bound or shared facts between URIs")
        with redirect_stderr(StringIO()):
            server.handle(_notice("textDocument/didOpen", {"textDocument": {
                "uri": "untitled:overflow", "languageId": "vela", "version": 1, "text": _TEXT}}))
        ensure(len(server._inspections) == MAX_DOCUMENTS, "refused document enlarged the cache")
        request = _request("textDocument/documentSymbol", {"textDocument": {"uri": _URI}})
        request["id"] = ""
        size = len(json.dumps(request, separators=(",", ":")).encode())
        request["id"] = "x" * (MAX_BODY_BYTES - size)
        refused = server.handle(request)
        ensure(_error_code(refused) == -32803, "cached facts bypassed the reply byte bound")
        encode_message(refused[0])
        ensure("result" in _query(server) and inspect.call_count == MAX_DOCUMENTS,
               "a reply size refusal poisoned otherwise valid cached facts")


def _validated_source_binding() -> None:
    first = SourceSnapshot(_URI, 1, _TEXT, 1)
    facts = validate_inspection(first, _facts())
    second = SourceSnapshot(_URI, 2, _TEXT, 2)
    try:
        project_inspection(second, facts, "textDocument/documentSymbol", None)
    except InspectionError:
        pass
    else:
        raise AssertionError("validated facts projected under a different snapshot identity")
    with patch("toolchain.lsp_services.MAX_SYMBOLS", 1):
        try:
            lsp_services.validate_inspection(first, _facts())
        except InspectionError:
            pass
        else:
            raise AssertionError("immutable fact validation skipped the symbol bound")


def cases() -> list[Case]:
    return [Case("unchanged-queries-reuse-immutable-validated-facts", _reuses_validated_facts),
            Case("snapshot-save-refusal-and-lifecycle-invalidation", _snapshot_and_lifecycle_invalidation),
            Case("producer-replacement-and-generation-invalidation", _producer_replacement_and_generation),
            Case("failed-and-unavailable-inspections-retry", _failures_retry),
            Case("open-document-and-every-reply-bounds", _cache_and_reply_bounds),
            Case("validated-inspection-retains-source-and-symbol-bounds", _validated_source_binding)]
