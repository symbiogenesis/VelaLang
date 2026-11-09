# SPDX-License-Identifier: Apache-2.0
"""Untrusted host LSP adapter for the pure Vela diagnostic producer."""

import hashlib
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import BinaryIO, Never, cast

from toolchain.lsp_format import Formatter, format_document, formatting_edits
from toolchain.lsp_services import (
    METHODS,
    SEMANTIC_TOKEN_MODIFIERS,
    SEMANTIC_TOKEN_TYPES,
    Inspection,
    InspectionError,
    Inspector,
    QueryRange,
    inspect_document,
    project_inspection,
    validate_inspection,
)
from toolchain.lsp_tokens import token_edits
from toolchain.lsp_worker import worker_command
from toolchain.protocol_json import (
    MAX_BODY_BYTES,
    FrameError,
    MessageError,
    decode_message,
    encode_message,
    read_frame,
)
from toolchain.source import SourceSnapshot

MAX_DOCUMENTS = 16
MAX_CHANGES = 64
WORKER_SECONDS = 5
type Checker = Callable[[bytes], dict[str, object] | None]
_SEMANTIC_DELTA = "textDocument/semanticTokens/full/delta"
_SEMANTIC_FULL = "textDocument/semanticTokens/full"


@dataclass(frozen=True)
class _CachedInspection:
    snapshot: str
    generation: int
    producer: Inspector
    facts: Inspection


@dataclass(frozen=True)
class _TokenHistory:
    result_id: str
    generation: int
    producer: Inspector
    data: tuple[int, ...]


def _invalid(message: str) -> Never:
    raise ValueError(message)


def diagnose(source: bytes) -> dict[str, object] | None:
    """Use the same interpreter and compiler checkout, without client-selected paths."""
    try:
        done = subprocess.run(worker_command(), input=source,
                              capture_output=True, timeout=WORKER_SECONDS, check=False)
        if done.returncode != 0 or len(done.stdout) > MAX_BODY_BYTES:
            _invalid("pure diagnostic worker failed")
        if done.stdout.strip() == b"null":
            return None
        result = decode_message(done.stdout)
        if (set(result) != {"kind", "line", "column", "message"}
                or not isinstance(result["kind"], str)
                or result["kind"] not in {"syntax", "name", "type", "unsupported", "limit", "encoding"}
                or not isinstance(result["message"], str)
                or type(result["line"]) is not int or type(result["column"]) is not int):
            _invalid("invalid pure diagnostic worker result")
        encode_message(result)
        # Malformed producer sites are worker failures, not refused client edits.
        # Validate through the shared coordinate adapter so failed publication
        # cannot mark an otherwise valid client overlay out of synchronization.
        snapshot = SourceSnapshot("untitled:diagnostic-worker", 1, source.decode("utf-8"), 1)
        snapshot.diagnostic_position(result["line"], result["column"])
    except subprocess.TimeoutExpired:
        return {"kind": "timeout", "line": 1, "column": 1,
                "message": "Pure prototype check exceeded 5 seconds; no acceptance verdict"}
    except (OSError, ValueError):
        return {"kind": "internal", "line": 1, "column": 1,
                "message": "Pure prototype diagnostic worker unavailable; no acceptance verdict"}
    else:
        return result


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        _invalid("expected an object")
    return cast("dict[str, object]", value)


def _string(value: object) -> str:
    if not isinstance(value, str):
        _invalid("expected a string")
    return value


def _integer(value: object) -> int:
    if type(value) is not int or not -(2 ** 31) <= value < 2 ** 31:
        raise ValueError("expected a 32-bit integer")
    return value


def _error(request_id: object, code: int, message: str) -> dict[str, object]:
    reply: dict[str, object] = {"jsonrpc": "2.0", "id": request_id,
                                "error": {"code": code, "message": message}}
    try:
        encode_message(reply)
    except (FrameError, UnicodeError):
        # Some valid requests leave less space for an error envelope than their
        # ID needs. Retain correlation whenever even the shortest refusal fits.
        reply = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32803, "message": ""}}
        try:
            encode_message(reply)
        except (FrameError, UnicodeError):
            reply = {"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32803, "message": "Request ID exceeds reply bounds"}}
    return reply


class Server:
    def __init__(self, checker: Checker | None = None, inspector: Inspector | None = None,
                 formatter: Formatter | None = None) -> None:
        self.checker = diagnose if checker is None else checker
        self.inspector = inspect_document if inspector is None else inspector
        self.formatter = format_document if formatter is None else formatter
        self.documents: dict[str, SourceSnapshot] = {}
        self.desynchronized: set[str] = set()
        self.received_versions: dict[str, int] = {}
        self._inspections: dict[str, _CachedInspection] = {}
        self._inspection_generation = 0
        self._token_history: dict[str, _TokenHistory] = {}
        self._token_serial = 0
        self._token_deltas = False
        self.generation = 0
        self.initialized = False
        self.ready = False
        self.shutdown = False
        self.exit_code: int | None = None

    def invalidate_inspections(self) -> None:
        """Advance the producer generation after a toolchain or configuration change."""
        self._inspections.clear()
        self._token_history.clear()
        self._inspection_generation += 1

    def _tokens(self, snapshot: SourceSnapshot, previous: str | None,
                delta: bool) -> tuple[dict[str, object], _TokenHistory | None]:
        projected = cast("dict[str, object]", project_inspection(
            snapshot, self._inspection(snapshot), _SEMANTIC_FULL, None))
        if not delta and not self._token_deltas:
            return projected, None
        data = tuple(cast("list[int]", projected["data"]))
        identity = hashlib.sha256(
            f"{snapshot.identity}:{self._inspection_generation}:{self._token_serial + 1}".encode()).hexdigest()
        candidate = _TokenHistory(identity, self._inspection_generation, self.inspector, data)
        old = self._token_history.get(snapshot.uri)
        if (delta and old is not None and old.result_id == previous
                and old.generation == self._inspection_generation and old.producer is self.inspector):
            return {"resultId": identity, "edits": token_edits(old.data, data)}, candidate
        return {"resultId": identity, "data": list(data)}, candidate

    def _inspection(self, snapshot: SourceSnapshot) -> Inspection | None:
        inspector, generation = self.inspector, self._inspection_generation
        cached = self._inspections.get(snapshot.uri)
        if (cached is not None and cached.snapshot == snapshot.identity
                and cached.generation == generation and cached.producer is inspector):
            return cached.facts
        self._inspections.pop(snapshot.uri, None)
        facts = validate_inspection(snapshot, inspector(snapshot.source))
        if (inspector is not self.inspector or generation != self._inspection_generation
                or self.documents.get(snapshot.uri) is not snapshot
                or snapshot.uri in self.desynchronized):
            raise InspectionError("Inspection producer or source changed during inspection")
        if facts is not None:
            self._inspections[snapshot.uri] = _CachedInspection(
                snapshot.identity, generation, inspector, facts)
        return facts

    def _snapshot(self, uri: str, version: int, text: str) -> SourceSnapshot:
        candidate = SourceSnapshot(uri, version, text, self.generation + 1)
        self.generation += 1
        return candidate

    def _clear(self, uri: str) -> dict[str, object]:
        return {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                "params": {"uri": uri, "diagnostics": []}}

    def _changed_snapshot(self, old: SourceSnapshot, version: int,
                          changes: object) -> SourceSnapshot:
        if not isinstance(changes, list) or len(changes) > MAX_CHANGES:
            _invalid("expected at most 64 ordered content changes")
        if old.uri in self.desynchronized and (not changes or "range" in _object(changes[0])):
            _invalid("a complete replacement is required to restore synchronization")
        candidate = old
        for value in changes:
            change = _object(value)
            text = _string(change.get("text"))
            if "range" in change:
                if set(change) - {"range", "rangeLength", "text"}:
                    _invalid("invalid ranged content change")
                span = _object(change["range"])
                start, end = _object(span.get("start")), _object(span.get("end"))
                first_position = _integer(start.get("line")), _integer(start.get("character"))
                last_position = _integer(end.get("line")), _integer(end.get("character"))
                if first_position > last_position:
                    _invalid("content change range is reversed")
                first = candidate.position_byte_offset(*first_position)
                last = candidate.position_byte_offset(*last_position)
                source = candidate.source
                if "rangeLength" in change:
                    length = _integer(change["rangeLength"])
                    removed = source[first:last].decode("utf-8")
                    if length < 0 or length != len(removed.encode("utf-16-le")) // 2:
                        _invalid("rangeLength differs from removed UTF-16 units")
                text = (source[:first] + text.encode("utf-8") + source[last:]).decode("utf-8")
            elif set(change) != {"text"}:
                _invalid("invalid complete content replacement")
            # Every intermediate is bounded. Nothing becomes current, and no
            # generation is consumed, until all ordered edits have succeeded.
            candidate = SourceSnapshot(old.uri, version, text, self.generation + 1)
        return self._snapshot(old.uri, version, candidate.text)

    def _diagnostics(self, snapshot: SourceSnapshot) -> dict[str, object]:
        diagnostics: list[dict[str, object]] = []
        result = self.checker(snapshot.source)
        if result is not None:
            position = snapshot.diagnostic_position(cast("int", result["line"]),
                                                    cast("int", result["column"]))
            diagnostics.append({"range": {"start": position, "end": position}, "severity": 1,
                                "source": "vela-pure-prototype", "code": result["kind"],
                                "message": _string(result["message"])[:4096],
                                "data": {"snapshot": snapshot.identity,
                                         "generation": snapshot.generation, "unqualified": True}})
        return {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                "params": {"uri": snapshot.uri, "version": snapshot.version,
                           "diagnostics": diagnostics}}

    def _navigation(self, request_id: object, method: str,
                    params: dict[str, object]) -> dict[str, object]:
        if not self.ready:
            return _error(request_id, -32002, "Initialized notification required")
        document = _object(params.get("textDocument"))
        uri = _string(document.get("uri"))
        if uri not in self.documents:
            _invalid("document is not open")
        if uri in self.desynchronized:
            return _error(request_id, -32801, "Document is out of synchronization")
        snapshot = self.documents[uri]
        position: tuple[int, int] | None = None
        requested_range: QueryRange | None = None
        include_declaration = False
        previous_result: str | None = None
        if method == _SEMANTIC_DELTA:
            previous_result = _string(params.get("previousResultId"))
        if method == "textDocument/inlayHint":
            span = _object(params.get("range"))
            start, end = _object(span.get("start")), _object(span.get("end"))
            first = _integer(start.get("line")), _integer(start.get("character"))
            last = _integer(end.get("line")), _integer(end.get("character"))
            if first > last:
                _invalid("hint range is reversed")
            first_position = snapshot.byte_position(snapshot.position_byte_offset(*first))
            last_position = snapshot.byte_position(snapshot.position_byte_offset(*last))
            requested_range = ((first_position["line"], first_position["character"]),
                               (last_position["line"], last_position["character"]))
        elif method not in {"textDocument/documentSymbol", "textDocument/semanticTokens/full",
                            "textDocument/formatting", _SEMANTIC_DELTA}:
            point = _object(params.get("position"))
            offset = snapshot.position_byte_offset(_integer(point.get("line")),
                                                    _integer(point.get("character")))
            converted = snapshot.byte_position(offset)
            position = converted["line"], converted["character"]
        if method == "textDocument/references":
            context = _object(params.get("context"))
            include = context.get("includeDeclaration")
            if type(include) is not bool:
                _invalid("includeDeclaration must be a boolean")
            include_declaration = include
        if method == "textDocument/formatting":
            options = _object(params.get("options"))
            if _integer(options.get("tabSize")) <= 0 or type(options.get("insertSpaces")) is not bool:
                _invalid("formatting requires positive tabSize and Boolean insertSpaces")
        try:
            token_history = None
            if method == "textDocument/formatting":
                result = formatting_edits(snapshot, self.formatter(snapshot.source))
            elif method in {_SEMANTIC_FULL, _SEMANTIC_DELTA}:
                result, token_history = self._tokens(snapshot, previous_result, method == _SEMANTIC_DELTA)
            else:
                result = project_inspection(snapshot, self._inspection(snapshot), method,
                                            position, include_declaration, requested_range)
            reply: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "result": result}
            encode_message(reply)
        except (InspectionError, FrameError, OSError, subprocess.SubprocessError):
            # Keep the error envelope smaller than the smallest valid navigation
            # request, including when a string ID nearly fills the frame budget.
            return _error(request_id, -32803, "Inspection failed or exceeded bounds")
        else:
            if token_history is not None:
                self._token_history[uri] = token_history
                self._token_serial += 1
            return reply

    def handle(self, message: dict[str, object]) -> list[dict[str, object]]:
        if self.exit_code is not None:
            return []
        request = "id" in message
        request_id = message.get("id")
        method = message.get("method")
        if (message.get("jsonrpc") != "2.0" or not isinstance(method, str)
                or (request and not (isinstance(request_id, str) or type(request_id) is int))):
            return [_error(None, -32600, "Invalid Request")]
        if method == "exit" and not request:
            self.invalidate_inspections()
            self.exit_code = 0 if self.shutdown else 1
            return []
        if not self.initialized and method != "initialize":
            return [_error(request_id, -32002, "Server not initialized")] if request else []
        if self.shutdown:
            return [_error(request_id, -32600, "Server has shut down")] if request else []
        try:
            params_value = message.get("params")
            params = {} if params_value is None else _object(params_value)
            if method == "initialize" and request:
                if self.initialized:
                    return [_error(request_id, -32600, "Server already initialized")]
                capabilities = _object(params.get("capabilities", {}))
                general = _object(capabilities.get("general", {}))
                encodings = general.get("positionEncodings", ["utf-16"])
                if not isinstance(encodings, list) or not all(isinstance(e, str) for e in encodings):
                    _invalid("invalid positionEncodings")
                text_capabilities = _object(capabilities.get("textDocument", {}))
                semantic = _object(text_capabilities.get("semanticTokens", {}))
                token_requests = _object(semantic.get("requests", {}))
                full_tokens = token_requests.get("full", False)
                token_deltas = False
                if isinstance(full_tokens, dict):
                    token_deltas = full_tokens.get("delta", False)
                    if type(token_deltas) is not bool:
                        _invalid("semantic token delta capability must be a boolean")
                elif type(full_tokens) is not bool:
                    _invalid("semantic token full capability must be a boolean or object")
                # UTF-16 is mandatory in LSP even when omitted from the offer.
                reply: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "result": {
                    "capabilities": {"positionEncoding": "utf-16", "hoverProvider": True,
                        "definitionProvider": True, "referencesProvider": True, "documentSymbolProvider": True,
                        "inlayHintProvider": True,
                        "documentFormattingProvider": True,
                        "semanticTokensProvider": {
                            "legend": {"tokenTypes": list(SEMANTIC_TOKEN_TYPES),
                                       "tokenModifiers": list(SEMANTIC_TOKEN_MODIFIERS)},
                            "full": {"delta": True}, "range": False},
                        "textDocumentSync": {
                        "openClose": True, "change": 2, "save": {"includeText": False}}},
                    "serverInfo": {"name": "Vela pure prototype (unqualified)", "version": "0"}}}
                try:
                    encode_message(reply)
                except (FrameError, UnicodeError):
                    return [_error(request_id, -32803, "Initialization reply exceeds bounds")]
                self.initialized = True
                self._token_deltas = token_deltas
                return [reply]
            if method == "shutdown" and request:
                self.invalidate_inspections()
                self.shutdown = True
                self.documents.clear()
                self.desynchronized.clear()
                self.received_versions.clear()
                return [{"jsonrpc": "2.0", "id": request_id, "result": None}]
            if request:
                if method in METHODS or method in {"textDocument/formatting", _SEMANTIC_DELTA}:
                    return [self._navigation(request_id, method, params)]
                return [_error(request_id, -32601, "Method not found")]
            if method == "initialized":
                self.ready = True
                return []
            if method == "$/cancelRequest":
                return []
            if not self.ready:
                _invalid("initialized notification is required before document work")
            if method in {"workspace/didChangeConfiguration", "workspace/didChangeWatchedFiles"}:
                self.invalidate_inspections()
                output: list[dict[str, object]] = []
                for uri, old in list(self.documents.items()):
                    if uri in self.desynchronized:
                        continue
                    snapshot = self._snapshot(uri, old.version, old.text)
                    self.documents[uri] = snapshot
                    output.append(self._diagnostics(snapshot))
                return output
            if method not in {"textDocument/didOpen", "textDocument/didChange",
                              "textDocument/didSave", "textDocument/didClose"}:
                return []
            document = _object(params.get("textDocument"))
            uri = _string(document.get("uri"))
            if method == "textDocument/didOpen":
                if uri in self.documents or len(self.documents) >= MAX_DOCUMENTS:
                    _invalid("duplicate open or document count exceeds limit")
                if document.get("languageId") != "vela":
                    _invalid("expected Vela languageId")
                snapshot = self._snapshot(uri, _integer(document.get("version")),
                                          _string(document.get("text")))
                self.received_versions[uri] = snapshot.version
            else:
                if uri not in self.documents:
                    _invalid("document is not open")
                old = self.documents[uri]
                if method == "textDocument/didClose":
                    self._inspections.pop(uri, None)
                    self._token_history.pop(uri, None)
                    del self.documents[uri]
                    self.desynchronized.discard(uri)
                    del self.received_versions[uri]
                    self.generation += 1
                    return [self._clear(uri)]
                if method == "textDocument/didSave":
                    self._inspections.pop(uri, None)
                    self._token_history.pop(uri, None)
                    if uri in self.desynchronized:
                        return [self._clear(uri)]
                    return [self._diagnostics(old)]
                version = _integer(document.get("version"))
                if version <= self.received_versions[uri]:
                    _invalid("document version must strictly increase")
                # Remember newer received versions even if their text is refused.
                # An older later update cannot resynchronize the document.
                self.received_versions[uri] = version
                snapshot = self._changed_snapshot(old, version, params.get("contentChanges"))
            self._inspections.pop(uri, None)
            self.documents[uri] = snapshot
            self.desynchronized.discard(uri)
            return [self._diagnostics(snapshot)]
        except (ValueError, UnicodeError) as error:
            if request:
                return [_error(request_id, -32602, str(error)[:256])]
            print(f"vela-lsp: ignored {method}: {str(error)[:256]}", file=sys.stderr)
            params_value = message.get("params")
            if isinstance(params_value, dict):
                document_value = params_value.get("textDocument")
                if isinstance(document_value, dict):
                    uri_value = document_value.get("uri")
                    if isinstance(uri_value, str) and uri_value in self.documents:
                        self._inspections.pop(uri_value, None)
                        self._token_history.pop(uri_value, None)
                        self.desynchronized.add(uri_value)
                        return [self._clear(uri_value)]
            return []


def serve(input_stream: BinaryIO, output_stream: BinaryIO,
          *, transcript: list[dict[str, object]] | None = None) -> int:
    server = Server()
    try:
        while server.exit_code is None:
            raw = read_frame(input_stream)
            if raw is None:
                return 1
            decoded: dict[str, object] | None = None
            try:
                decoded = decode_message(raw)
            except FrameError:
                raise
            except MessageError:
                replies = [_error(None, -32600, "Invalid Request")]
            except (ValueError, UnicodeError):
                replies = [_error(None, -32700, "Parse error")]
            else:
                replies = server.handle(decoded)
            if transcript is not None:
                transcript.append({"index": len(transcript), "direction": "client_to_server",
                                   "body_bytes": len(raw),
                                   "body_sha256": hashlib.sha256(raw).hexdigest(),
                                   "message": decoded})
            for reply in replies:
                encoded = encode_message(reply)
                if transcript is not None:
                    transcript.append({"index": len(transcript), "direction": "server_to_client",
                                       "frame_bytes": len(encoded),
                                       "frame_sha256": hashlib.sha256(encoded).hexdigest(),
                                       "message": reply})
                output_stream.write(encoded)
            output_stream.flush()
    except (FrameError, OSError, ValueError) as error:
        print(f"vela-lsp: session closed: {str(error)[:256]}", file=sys.stderr)
        return 1
    return server.exit_code
