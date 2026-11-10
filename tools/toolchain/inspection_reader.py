# SPDX-License-Identifier: Apache-2.0
"""Independent, read-only consumer of serialized pure inspection publications."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from toolchain.jsonutil import unique_object
from toolchain.schema import validate

MAX_PUBLICATION_BYTES = 1_048_576
MAX_SOURCE_BYTES = 65_536
MAX_RESULTS = 256
SCHEMA_PATH = Path(__file__).with_name("inspection.schema.json")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _records(value: dict[str, object], key: str) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value[key])


def _span(record: dict[str, object]) -> tuple[int, int]:
    first, last = cast("list[int]", record["span"])
    return first, last


def _contains(outer: dict[str, object], inner: dict[str, object]) -> bool:
    first, last = _span(outer)
    start, end = _span(inner)
    return first <= start <= end <= last


def _offset(source: bytes, offset: object) -> bool:
    if type(offset) is not int or not 0 <= offset <= len(source):
        return False
    try:
        source[:offset].decode("utf-8")
    except UnicodeDecodeError:
        return False
    return source[offset - 1:offset + 1] != b"\r\n"


def _inventory(value: dict[str, object], source: bytes) -> None:
    """Check graph and source relationships without parsing or resolving Vela."""
    identity = value["snapshot"]
    pieces = _records(value, "concrete")
    cursor = 0
    for piece in pieces:
        first, last = _span(piece)
        if first != cursor or first == last or source[first:last] != cast("str", piece["text"]).encode():
            raise ValueError("inspection concrete partition does not reconstruct current source")
        cursor = last
    if cursor != len(source):
        raise ValueError("inspection concrete partition omits source bytes")

    nodes = _records(value, "syntax")
    scopes = _records(value, "scopes")
    symbols = _records(value, "symbols")
    for kind, records in (("node", nodes), ("scope", scopes), ("symbol", symbols)):
        if any(record["id"] != f"{identity}:{kind}:{index}" for index, record in enumerate(records)):
            raise ValueError("inspection contains a foreign, duplicate or reordered handle")
        for record in records:
            first, last = _span(record)
            if not first < last or not _offset(source, first) or not _offset(source, last):
                raise ValueError("inspection has an invalid source span")

    def tree(records: list[dict[str, object]], root_kind: str) -> dict[str, dict[str, object]]:
        by_id = {cast("str", record["id"]): record for record in records}
        if not records or records[0]["parent"] is not None or records[0]["kind"] != root_kind:
            raise ValueError("inspection tree has no unique root")
        expected: dict[str, list[str]] = {handle: [] for handle in by_id}
        visited: set[str] = set()
        for record in records:
            handle = cast("str", record["id"])
            parent = record["parent"]
            if parent is not None:
                if parent not in visited or not _contains(by_id[cast("str", parent)], record):
                    raise ValueError("inspection tree has a foreign, cyclic or uncontained parent")
                expected[cast("str", parent)].append(handle)
            elif record is not records[0]:
                raise ValueError("inspection tree has multiple roots")
            visited.add(handle)
        if any(record["children"] != expected[cast("str", record["id"])] for record in records):
            raise ValueError("inspection tree has inconsistent ordered child links")
        pending = [cast("str", records[0]["id"])]
        preorder: list[str] = []
        while pending:
            handle = pending.pop()
            preorder.append(handle)
            pending.extend(reversed(expected[handle]))
        if preorder != [record["id"] for record in records]:
            raise ValueError("inspection tree is not in preorder")
        return by_id

    by_node = tree(nodes, "module")
    by_scope = tree(scopes, "module")
    by_symbol = {cast("str", symbol["id"]): symbol for symbol in symbols}
    for node in nodes:
        if node["kind"] in {"identifier", "operator", "type", "nat", "bool"}:
            first, last = _span(node)
            spelling = str(node["value"]).lower() if type(node["value"]) is bool else node["value"]
            if source[first:last].decode() != spelling:
                raise ValueError("inspection syntax spelling differs from source")
    expected_scope_nodes = [node["id"] for node in nodes
                            if node["kind"] in {"module", "function", "block", "expression-body"}]
    if [scope["node"] for scope in scopes] != expected_scope_nodes:
        raise ValueError("inspection scope inventory omits source environments")
    scope_nodes = {scope["node"]: scope for scope in scopes}
    owners: dict[str, str] = {}
    for node in nodes:
        handle = cast("str", node["id"])
        inherited = None if node["parent"] is None else owners[cast("str", node["parent"])]
        if handle in scope_nodes:
            scope = scope_nodes[handle]
            if scope["parent"] != inherited:
                raise ValueError("inspection lexical nesting differs from source syntax")
            owners[handle] = cast("str", scope["id"])
        elif inherited is not None:
            owners[handle] = inherited
    declaration_kinds = {"function": "function", "constant": "constant", "parameter": "parameter",
                         "binding": "variable", "local-constant": "constant"}
    expected_symbols: list[tuple[str, str, tuple[int, int], str, int]] = []
    expected_occurrences: list[tuple[str, tuple[int, int], bool, str]] = []
    for node in nodes:
        if node["kind"] != "identifier":
            continue
        parent = by_node[cast("str", node["parent"])]
        if parent["kind"] == "module":
            continue
        declaration = declaration_kinds.get(cast("str", parent["kind"])) if node["role"] == "name" else None
        owner = owners[cast("str", node["id"])]
        if declaration == "function":
            owner = cast("str", by_scope[owner]["parent"])
        if declaration is not None:
            available = _span(parent)[1]
            if declaration == "parameter":
                function = by_node[cast("str", parent["parent"])]
                bodies = [by_node[handle] for handle in cast("list[str]", function["children"])
                          if by_node[handle]["role"] == "body"]
                if len(bodies) != 1:
                    raise ValueError("inspection parameter has no unique source function body")
                available = _span(bodies[0])[0]
            expected_symbols.append((declaration, cast("str", node["value"]), _span(node), owner, available))
        elif (parent["kind"], node["role"]) not in {
                ("name", "name"), ("call", "callee"), ("argument", "label")}:
            raise ValueError("inspection identifier has an unsupported source role")
        expected_occurrences.append((cast("str", node["value"]), _span(node), declaration is not None, owner))
    if [(symbol["kind"], symbol["name"], _span(symbol), symbol["scope"], symbol["available_from"])
            for symbol in symbols] != expected_symbols:
        raise ValueError("inspection declaration inventory differs from complete source syntax")
    memberships: dict[str, list[str]] = {handle: [] for handle in by_scope}
    for scope in scopes:
        node = by_node[cast("str", scope["node"])]
        if scope["span"] != node["span"] or scope["kind"] != (
                "block" if node["kind"] == "expression-body" else node["kind"]):
            raise ValueError("inspection scope differs from its syntax node")
    previous = -1
    for symbol in symbols:
        first, last = _span(symbol)
        if first <= previous or source[first:last].decode() != symbol["name"]:
            raise ValueError("inspection declarations are reordered or do not name source identifiers")
        previous = first
        if symbol["origin"] != {"kind": "authored", "span": symbol["span"]}:
            raise ValueError("inspection authored origin differs from declaration")
        owner = by_scope.get(cast("str", symbol["scope"]))
        if owner is None or not _contains(owner, symbol) or not last <= cast("int", symbol["available_from"]) <= len(source):
            raise ValueError("inspection declaration has invalid scope or availability")
        memberships[cast("str", symbol["scope"])].append(cast("str", symbol["id"]))
    if any(scope["symbols"] != memberships[cast("str", scope["id"])] for scope in scopes):
        raise ValueError("inspection scope membership differs from declaration inventory")
    declarations: list[str] = []
    actual_occurrences: list[tuple[str, tuple[int, int], bool, str]] = []
    sites: set[tuple[int, int]] = set()
    for occurrence in _records(value, "occurrences"):
        symbol = by_symbol.get(cast("str", occurrence["symbol"]))
        owner = by_scope.get(cast("str", occurrence["scope"]))
        first, last = _span(occurrence)
        if (symbol is None or owner is None or not _contains(owner, occurrence)
                or not _offset(source, first) or not _offset(source, last)
                or source[first:last].decode() != symbol["name"] or (first, last) in sites):
            raise ValueError("inspection occurrence has inconsistent symbol, scope or source")
        sites.add((first, last))
        actual_occurrences.append((cast("str", symbol["name"]), (first, last),
                                   cast("bool", occurrence["declaration"]), cast("str", occurrence["scope"])))
        if occurrence["declaration"]:
            if occurrence["span"] != symbol["span"] or occurrence["scope"] != symbol["scope"]:
                raise ValueError("inspection declaration occurrence disagrees with its symbol")
            declarations.append(cast("str", symbol["id"]))
    if declarations != list(by_symbol):
        raise ValueError("inspection occurrence inventory omits or duplicates declarations")
    if sorted(actual_occurrences) != sorted(expected_occurrences):
        raise ValueError("inspection occurrence inventory differs from complete source identifiers")
    expressions = _records(value, "expressions")
    if [expression["node"] for expression in expressions] != [node["id"] for node in nodes
            if node["kind"] in {"nat", "bool", "name", "call", "binary", "unary", "group"}]:
        raise ValueError("inspection typed expression inventory differs from source syntax")
    if any(expression["span"] != by_node[cast("str", expression["node"])]["span"] for expression in expressions):
        raise ValueError("inspection expression span differs from its syntax node")


@dataclass(frozen=True)
class Reader:
    """Detached immutable JSON facts; this consumer does not invoke a compiler worker."""

    publication: bytes

    def export(self) -> dict[str, object]:
        return cast("dict[str, object]", json.loads(self.publication))

    def query(self, source: bytes, request: object, *, binding: dict[str, object]) -> dict[str, object]:
        """Project bounded stored facts only for an independently supplied current binding."""
        value = self.export()
        response = {key: value[key] for key in ("schema", "snapshot", "binding")}
        response.update(scope="vela-pure-inspection-query", status="refused", complete=False,
                        reason="malformed-request", items=[], total=0)

        def refuse(reason: str, status: object = "refused") -> dict[str, object]:
            response.update(reason=reason, status=status)
            return response

        if binding != value["binding"] or _hash(source) != binding.get("source_sha256"):
            return refuse("stale-input")
        if not isinstance(request, dict):
            return response
        if type(request.get("schema")) is not int or request["schema"] != 6:
            return refuse("schema-version")
        if request.get("snapshot") != value["snapshot"]:
            return refuse("stale-snapshot")
        operation = request.get("operation")
        inventories = {"symbols": "symbols", "tokens": "concrete", "syntax": "syntax",
                       "expressions": "expressions", "scopes": "scopes"}
        locations = {"symbol-at", "type-at", "token-at", "syntax-at", "expression-at", "scope-at"}
        handles = {"references": "symbol", "syntax-children": "node", "expression-type": "node",
                   "scope-symbols": "scope"}
        if not isinstance(operation, str) or operation not in {*inventories, *locations, *handles}:
            return refuse("unsupported-operation", "unsupported")
        required = {"schema", "snapshot", "operation"}
        if operation in locations:
            required.add("offset")
        if operation in handles:
            required.add(handles[operation])
        if set(request) - {"limit"} != required:
            return response
        limit = request.get("limit", MAX_RESULTS)
        if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
            return refuse("query-limit")
        if value["status"] != "checked":
            return refuse(cast("str", value["reason"]), value["status"])
        items: list[dict[str, object]]
        if operation in inventories:
            items = _records(value, inventories[operation])
        elif operation in handles:
            field = handles[operation]
            inventory = "symbols" if field == "symbol" else "syntax" if field == "node" else "scopes"
            if not any(item["id"] == request[field] for item in _records(value, inventory)):
                return refuse(f"stale-or-unknown-{field}")
            if operation == "references":
                items = [item for item in _records(value, "occurrences") if item["symbol"] == request[field]]
            elif operation == "syntax-children":
                items = [item for item in _records(value, "syntax") if item["parent"] == request[field]]
            elif operation == "expression-type":
                items = [item for item in _records(value, "expressions") if item["node"] == request[field]]
            else:
                items = [item for item in _records(value, "symbols") if item["scope"] == request[field]]
        else:
            offset = request["offset"]
            if not _offset(source, offset):
                return refuse("invalid-offset")
            inventory = {"token-at": "concrete", "syntax-at": "syntax", "expression-at": "expressions",
                         "scope-at": "scopes"}.get(operation, "occurrences")
            containing = [item for item in reversed(_records(value, inventory))
                          if _span(item)[0] <= cast("int", offset) < _span(item)[1]]
            selected = min(containing, key=lambda item: _span(item)[1] - _span(item)[0], default=None)
            items = [] if selected is None else [selected]
            if inventory == "occurrences" and selected is not None:
                items = [item for item in _records(value, "symbols") if item["id"] == selected["symbol"]]
                if operation == "type-at":
                    items = [{"symbol": item["id"], "span": selected["span"], "type": item["type"]} for item in items]
        response.update(status="checked" if len(items) <= limit else "partial", complete=len(items) <= limit,
                        reason=None if len(items) <= limit else "result-limit", total=len(items), items=items[:limit])
        return response


def read(publication: bytes, source: bytes, *, binding: dict[str, object]) -> Reader:
    """Verify a current serialized snapshot before offline fact queries.

    The caller supplies the current compiler/configuration/target binding; the
    [consumer contract](../../docs/tooling/tooling-protocols.md#pure-development-snapshot-increment)
    distinguishes this structural reader from a source-correspondence proof.
    """
    if len(source) > MAX_SOURCE_BYTES:
        raise ValueError("inspection source exceeds consumer byte bound")
    if len(publication) > MAX_PUBLICATION_BYTES:
        raise ValueError("inspection publication exceeds consumer byte bound")
    try:
        value = json.loads(publication.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError("inspection publication is not bounded unique-key JSON") from error
    validate(SCHEMA_PATH, value)
    if value["scope"] != "vela-pure-inspection":
        raise ValueError("inspection consumer requires a bulk snapshot")
    if (value["binding"] != binding or value["snapshot"] != _hash(_canonical(binding))
            or binding["source_sha256"] != _hash(source) or value["source"].encode("utf-8") != source):
        raise ValueError("inspection publication does not bind current inputs")
    if value["status"] == "checked":
        _inventory(value, source)
    return Reader(_canonical(value))
