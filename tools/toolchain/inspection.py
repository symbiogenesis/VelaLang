# SPDX-License-Identifier: Apache-2.0
"""Versioned read-only snapshots of the existing bounded pure compiler facts."""

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from toolchain import VelaError, concrete, inspection_syntax
from toolchain.lsp_services import (
    Inspection,
    InspectionError,
    inspect_document,
    validate_inspection,
)
from toolchain.source import SourceSnapshot

SCHEMA_VERSION = 4
CONFIGURATION = "pure-default-v1"
TARGET = "gallina-pure-v1"
MAX_QUERY_RESULTS = 256
MAX_EXPORT_BYTES = 1_048_576
SCHEMA_PATH = Path(__file__).with_name("inspection.schema.json")


def _encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def producer_identity() -> dict[str, object]:
    """Conservatively bind all local compiler sources and locked tool dependencies."""
    root = Path(__file__).resolve().parents[2]
    paths = sorted((root / "tools/toolchain").rglob("*.py"))
    paths.extend(sorted((root / "tools/toolchain/parser").glob("*")))
    paths.extend(root / name for name in (
        "tools/opam/rocq.lock", "tools/opam/sail.lock", "tools/pyproject.toml", "tools/uv.lock"))
    paths.append(SCHEMA_PATH)
    dependencies = {path.relative_to(root).as_posix(): _digest(path.read_bytes())
                    for path in paths if path.is_file()}
    return {"name": "vela-pure-development", "stage": "pure-resolution",
            "version": _digest(_encoded(dependencies)), "dependencies": dependencies,
            "python": sys.version, "implementation": sys.implementation.name}


def _binding(document: SourceSnapshot, configuration: str, target: str) -> dict[str, object]:
    return {"uri": document.uri, "source_sha256": _digest(document.source),
            "producer": producer_identity(), "configuration": configuration, "target": target,
            "coordinate_unit": "utf8-byte", "symbol_lifetime": "snapshot"}


def _span(document: SourceSnapshot, first: tuple[int, int], last: tuple[int, int]) -> list[int]:
    return [document.position_byte_offset(*first), document.position_byte_offset(*last)]


def _facts(document: SourceSnapshot, inspection: Inspection, identity: str) -> tuple[list[object], list[object]]:
    symbols: list[object] = []
    for index, symbol in enumerate(inspection.symbols):
        span = _span(document, symbol.start, symbol.end)
        symbols.append({"id": f"{identity}:symbol:{index}", "name": symbol.name,
                        "kind": symbol.kind, "detail": symbol.detail,
                        "type": symbol.value_type.export(), "span": span,
                        "origin": {"kind": "authored", "span": span},
                        "documentation": symbol.documentation})
    occurrences: list[object] = [
        {"symbol": f"{identity}:symbol:{occurrence.symbol}",
         "span": _span(document, occurrence.start, occurrence.end),
         "declaration": occurrence.declaration}
        for occurrence in inspection.occurrences]
    return symbols, occurrences


@dataclass(frozen=True)
class Snapshot:
    """Immutable publication; identifiers designate facts only in this exact binding."""

    document: SourceSnapshot
    publication: bytes

    def export(self) -> dict[str, object]:
        """Return a detached JSON value; caller mutations cannot change retained facts."""
        return cast("dict[str, object]", json.loads(self.publication))

    def query(self, source: bytes, request: object, *, uri: str | None = None,
              configuration: str = CONFIGURATION, target: str = TARGET) -> dict[str, object]:
        """Answer bounded queries only while the caller's input and producer closure match."""
        current = self.export()
        response: dict[str, object] = {
            "schema": SCHEMA_VERSION, "scope": "vela-pure-inspection-query",
            "snapshot": current["snapshot"], "binding": current["binding"],
            "status": "refused", "complete": False, "reason": None,
            "items": [], "total": 0}

        def refuse(reason: str, status: str = "refused") -> dict[str, object]:
            response.update(status=status, reason=reason)
            return response

        try:
            document = SourceSnapshot(self.document.uri if uri is None else uri, 1,
                                      source.decode("utf-8"), 1)
            if _binding(document, configuration, target) != current["binding"]:
                return refuse("stale-input")
        except (OSError, ValueError):
            return refuse("stale-input")
        if not isinstance(request, dict) or not all(isinstance(key, str) for key in request):
            return refuse("malformed-request")
        query = cast("dict[str, object]", request)
        if type(query.get("schema")) is not int or query["schema"] != SCHEMA_VERSION:
            return refuse("schema-version")
        if query.get("snapshot") != current["snapshot"]:
            return refuse("stale-snapshot")
        operation = query.get("operation")
        if not isinstance(operation, str) or operation not in {
                "symbol-at", "type-at", "references", "symbols", "tokens", "token-at",
                "syntax", "syntax-at", "syntax-children"}:
            return refuse("unsupported-operation", "unsupported")
        required = {"schema", "snapshot", "operation"}
        if operation in {"symbol-at", "type-at", "token-at", "syntax-at"}:
            required.add("offset")
        elif operation == "references":
            required.add("symbol")
        elif operation == "syntax-children":
            required.add("node")
        if set(query) - {"limit"} != required:
            return refuse("malformed-request")
        limit = query.get("limit", MAX_QUERY_RESULTS)
        if type(limit) is not int or not 1 <= limit <= MAX_QUERY_RESULTS:
            return refuse("query-limit")
        if current["status"] != "checked":
            return refuse(str(current["reason"]), str(current["status"]))
        symbols = cast("list[dict[str, object]]", current["symbols"])
        occurrences = cast("list[dict[str, object]]", current["occurrences"])
        items: list[dict[str, object]]
        if operation == "symbols":
            items = symbols
        elif operation == "tokens":
            items = cast("list[dict[str, object]]", current["concrete"])
        elif operation == "syntax":
            items = cast("list[dict[str, object]]", current["syntax"])
        elif operation == "syntax-children":
            nodes = cast("list[dict[str, object]]", current["syntax"])
            node = next((item for item in nodes if item["id"] == query["node"]), None)
            if node is None:
                return refuse("stale-or-unknown-node")
            items = [item for item in nodes if item["parent"] == node["id"]]
        elif operation == "references":
            handle = query["symbol"]
            if not isinstance(handle, str) or not any(item["id"] == handle for item in symbols):
                return refuse("stale-or-unknown-symbol")
            items = [item for item in occurrences if item["symbol"] == handle]
        else:
            offset = query["offset"]
            try:
                self.document.byte_position(cast("int", offset))
            except (ValueError, TypeError):
                return refuse("invalid-offset")
            if operation == "syntax-at":
                candidates = cast("list[dict[str, object]]", current["syntax"])
                containing = [item for item in reversed(candidates)
                              if cast("list[int]", item["span"])[0] <= cast("int", offset)
                              < cast("list[int]", item["span"])[1]]
                selected = min(containing, key=lambda item: cast("list[int]", item["span"])[1]
                               - cast("list[int]", item["span"])[0], default=None)
                items = [] if selected is None else [selected]
                response.update(status="checked", complete=True, reason=None, total=len(items), items=items)
                return response
            candidates = cast("list[dict[str, object]]", current["concrete"]) if operation == "token-at" else occurrences
            selected = next((item for item in candidates
                             if cast("list[int]", item["span"])[0] <= cast("int", offset)
                             < cast("list[int]", item["span"])[1]), None)
            items = ([] if selected is None else [selected]) if operation == "token-at" else (
                [] if selected is None else [item for item in symbols if item["id"] == selected["symbol"]])
            if operation == "type-at" and selected is not None:
                items = [{"symbol": item["id"], "span": selected["span"], "type": item["type"]}
                         for item in items]
        count = len(items)
        response.update(status="checked" if count <= limit else "partial",
                        complete=count <= limit, reason=None if count <= limit else "result-limit",
                        total=count, items=items[:limit])
        return response


def inspect(source: bytes, *, uri: str = "memory:vela", configuration: str = CONFIGURATION,
            target: str = TARGET) -> Snapshot:
    """Build a complete source-preserving snapshot using the isolated pure fact producer.

    The [inspection contract](../../docs/tooling/tooling-protocols.md#compiler-inspection-api)
    defines this diagnostic view's boundary. Wider syntax and proof views are unavailable.
    """
    document = SourceSnapshot(uri, 1, source.decode("utf-8"), 1)
    binding = _binding(document, configuration, target)
    identity = _digest(_encoded(binding))
    publication: dict[str, object] = {
        "schema": SCHEMA_VERSION, "scope": "vela-pure-inspection",
        "snapshot": identity, "binding": binding, "status": "unavailable", "complete": False,
        "reason": None, "source": document.text, "symbols": [], "occurrences": [], "concrete": [], "syntax": [],
        "supported_views": ["source-text", "pure-concrete-pieces", "pure-resolved-identifiers", "pure-syntax-tree"],
        "unsupported_views": ["typed-expression-tree", "imports", "generated-origins", "proof", "lowering"]}
    if configuration != CONFIGURATION or target != TARGET:
        publication.update(status="unsupported", reason="unsupported-configuration-or-target")
    else:
        try:
            raw = dict(inspect_document(source, concrete=True))
            raw_concrete = raw.pop("concrete", None)
            raw_syntax = raw.pop("syntax", None)
            facts = validate_inspection(document, raw)
            if facts is None:
                publication["reason"] = raw["reason"]
            else:
                symbols, occurrences = _facts(document, facts, identity)
                pieces = concrete.validate(source, raw_concrete)
                nodes = inspection_syntax.nodes(source, raw_syntax, identity)
                inspection_syntax.validate_inventory(nodes, symbols, occurrences)
                publication.update(status="checked", complete=True, symbols=symbols,
                                   occurrences=occurrences, concrete=pieces, syntax=nodes)
        except InspectionError as error:
            timed_out = "exceeded 5 seconds" in str(error)
            publication.update(status="timed-out" if timed_out else "unavailable",
                               reason="producer-timeout" if timed_out else "producer-failure")
        except VelaError as error:
            publication["reason"] = error.kind
        except (ValueError, TypeError, KeyError):
            publication["reason"] = "producer-failure"
    if _binding(document, configuration, target) != binding:
        publication.update(status="refused", complete=False, reason="producer-changed",
                           symbols=[], occurrences=[], concrete=[], syntax=[])
    encoded = _encoded(publication)
    if len(encoded) > MAX_EXPORT_BYTES:
        publication.update(status="unavailable", complete=False, reason="export-limit",
                           symbols=[], occurrences=[], concrete=[], syntax=[])
        encoded = _encoded(publication)
        if len(encoded) > MAX_EXPORT_BYTES:
            raise ValueError("inspection source and provenance exceed export limit")
    return Snapshot(document, encoded)
