# SPDX-License-Identifier: Apache-2.0
"""Independent consumers of the bounded source syntax inspection contract."""

import copy
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import concrete, inspect_source, inspection, inspection_syntax
from toolchain.schema import validate

INDEPENDENT_CASES = True
SOURCE = ("/// tree \U0001f600\r\nmodule Tree;\r\n"
          "public const Nat One = 1_000;\r\n"
          "public const bool Ready(const Nat input) {\r\n"
          " const Nat limit = 2; let bool ok = input >= limit;\r\n"
          " if (ok) { return !false; } else { return input == One; }\r\n}\r\n"
          "public Nat Identity(Nat x) => x;\r\n"
          "public Nat Call(Nat x) => Identity(x: (x + 1));\r\n").encode()


def _request(snapshot: inspection.Snapshot, operation: str, **fields: object) -> dict[str, object]:
    return {"schema": 4, "snapshot": snapshot.export()["snapshot"], "operation": operation, **fields}


def _nodes(value: dict[str, object]) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value["syntax"])


def _shape_consumer() -> None:
    snapshot = inspection.inspect(SOURCE)
    publication = snapshot.export()
    validate(inspection.SCHEMA_PATH, publication)
    ensure(publication["status"] == "checked", "valid source did not publish source syntax")
    nodes = _nodes(publication)
    indexed = {cast("str", node["id"]): node for node in nodes}

    def shape(node: dict[str, object]) -> object:
        return (node["kind"], node["role"], node["index"], node["value"], node["const"],
                [shape(indexed[handle]) for handle in cast("list[str]", node["children"])])

    def leaf(kind: str, role: str, value: str | bool) -> object:
        return (kind, role, None, value, None, [])

    def branch(kind: str, role: str, children: list[object], *, index: int | None = None,
               const: bool | None = None) -> object:
        return (kind, role, index, None, const, children)

    def name(role: str, spelling: str) -> object:
        return branch("name", role, [leaf("identifier", "name", spelling)])

    def parameter(spelling: str, *, const: bool = False) -> object:
        return branch("parameter", "parameters", [leaf("type", "type", "Nat"),
                      leaf("identifier", "name", spelling)], index=0, const=const)

    expected = branch("module", "root", [leaf("identifier", "name", "Tree"),
        branch("constant", "declarations", [leaf("type", "type", "Nat"),
               leaf("identifier", "name", "One"), leaf("nat", "value", "1_000")], index=0),
        branch("function", "declarations", [leaf("type", "result", "bool"),
            leaf("identifier", "name", "Ready"), parameter("input", const=True),
            branch("block", "body", [
                branch("local-constant", "bindings", [leaf("type", "type", "Nat"),
                       leaf("identifier", "name", "limit"), leaf("nat", "value", "2")], index=0),
                branch("binding", "bindings", [leaf("type", "type", "bool"),
                    leaf("identifier", "name", "ok"), branch("binary", "value", [
                        name("left", "input"), leaf("operator", "operator", ">="), name("right", "limit")])], index=1),
                branch("if", "exit", [name("condition", "ok"),
                    branch("block", "then", [branch("return", "exit", [branch("unary", "value", [
                        leaf("operator", "operator", "!"), leaf("bool", "value", False)])])]),
                    branch("block", "else", [branch("return", "exit", [branch("binary", "value", [
                        name("left", "input"), leaf("operator", "operator", "=="), name("right", "One")])])])])])],
            index=1, const=True),
        branch("function", "declarations", [leaf("type", "result", "Nat"),
            leaf("identifier", "name", "Identity"), parameter("x"),
            branch("expression-body", "body", [name("value", "x")])], index=2, const=False),
        branch("function", "declarations", [leaf("type", "result", "Nat"),
            leaf("identifier", "name", "Call"), parameter("x"),
            branch("expression-body", "body", [branch("call", "value", [
                leaf("identifier", "callee", "Identity"), branch("argument", "arguments", [
                    leaf("identifier", "label", "x"), branch("group", "value", [branch("binary", "value", [
                        name("left", "x"), leaf("operator", "operator", "+"), leaf("nat", "right", "1")])])], index=0)])])],
            index=3, const=False)])
    ensure(shape(nodes[0]) == expected, "source syntax differs from independently authored structure")
    for index, node in enumerate(nodes):
        ensure(node["id"] == f"{publication['snapshot']}:node:{index}", "node handles lack deterministic snapshot scope")
        first, last = cast("list[int]", node["span"])
        ensure(0 <= first < last <= len(SOURCE), "syntax span escapes authored source")
        spelling = SOURCE[first:last].decode()
        if node["kind"] in {"identifier", "operator", "nat", "type"}:
            ensure(spelling == node["value"], "syntax leaf spelling differs from its independently selected source")
        elif node["kind"] == "bool":
            ensure(spelling == str(node["value"]).lower(), "Boolean leaf spelling differs from source")
        for child in cast("list[str]", node["children"]):
            descendant = indexed[child]
            low, high = cast("list[int]", descendant["span"])
            ensure(descendant["parent"] == node["id"] and first <= low < high <= last,
                   "syntax parent, child or containing span link differs")


def _query_consumer() -> None:
    snapshot = inspection.inspect(SOURCE)
    nodes = _nodes(snapshot.export())
    all_nodes = snapshot.query(SOURCE, _request(snapshot, "syntax"))
    validate(inspection.SCHEMA_PATH, all_nodes)
    ensure(all_nodes["items"] == nodes and all_nodes["total"] == len(nodes), "bulk syntax query lost nodes")
    for node in nodes:
        response = snapshot.query(SOURCE, _request(snapshot, "syntax-children", node=node["id"]))
        validate(inspection.SCHEMA_PATH, response)
        ensure([item["id"] for item in cast("list[dict[str, object]]", response["items"])] == node["children"],
               "independent syntax child traversal differs from bulk tree")
    offset = SOURCE.index(b"1_000") + 2
    selected = snapshot.query(SOURCE, _request(snapshot, "syntax-at", offset=offset))
    ensure(cast("list[dict[str, object]]", selected["items"])[0]["value"] == "1_000",
           "syntax-at did not select the innermost containing source node")
    for offset in (0, len(SOURCE)):
        ensure(snapshot.query(SOURCE, _request(snapshot, "syntax-at", offset=offset))["items"] == [],
               "syntax-at invented nodes in leading trivia or EOF")
    for offset in (SOURCE.index("\U0001f600".encode()) + 1, SOURCE.index(b"\r\n") + 1):
        ensure(snapshot.query(SOURCE, _request(snapshot, "syntax-at", offset=offset))["reason"] == "invalid-offset",
               "syntax-at accepted split Unicode/CRLF offsets")
    limited = snapshot.query(SOURCE, _request(snapshot, "syntax", limit=1))
    ensure(limited["status"] == "partial" and limited["complete"] is False and limited["total"] == len(nodes),
           "limited syntax query disguised missing nodes as complete")
    other = inspection.inspect(SOURCE + b" ")
    old = _request(other, "syntax-children", node=nodes[0]["id"])
    ensure(other.query(SOURCE + b" ", old)["reason"] == "stale-or-unknown-node", "cross-snapshot node reused")
    ensure(snapshot.query(SOURCE + b" ", _request(snapshot, "syntax"))["reason"] == "stale-input",
           "stale source retained syntax queries")
    for handle in (None, [], {}, True, "unknown"):
        ensure(snapshot.query(SOURCE, _request(snapshot, "syntax-children", node=handle))["status"] == "refused",
               "malformed syntax handle accepted")
    for version in (1, 2, 3):
        ensure(snapshot.query(SOURCE, {**_request(snapshot, "syntax"), "schema": version})["reason"] == "schema-version",
               "obsolete schema query accepted the new tree contract")


def _worker_corruption_and_bounds() -> None:
    raw = {**inspect_source(SOURCE, syntax_tree=True), "concrete": concrete.parts(SOURCE)}
    syntax = cast("dict[str, object]", raw["syntax"])
    corruptions: list[object] = [None, {}, {**syntax, "source_sha256": "0" * 64}]
    for edit in ("omitted", "operator", "escaping", "trailing-trivia", "extra", "non-node"):
        changed = copy.deepcopy(syntax)
        module = cast("dict[str, object]", changed["ast"])
        declarations = cast("list[dict[str, object]]", module["declarations"])
        if edit == "omitted":
            declarations.pop()
        elif edit == "operator":
            declarations[0]["value"] = {"kind": "nat", "span": [0, 1], "value": "0"}
        elif edit == "escaping":
            module["span"] = [0, len(SOURCE) + 1]
        elif edit == "trailing-trivia":
            module["span"] = [cast("list[int]", module["span"])[0], len(SOURCE)]
        elif edit == "non-node":
            declarations[0]["value"] = None
        else:
            module["extra"] = True
        corruptions.append(changed)
    for syntax in corruptions:
        with patch.object(inspection, "inspect_document", return_value={**raw, "syntax": syntax}):
            result = inspection.inspect(SOURCE).export()
        validate(inspection.SCHEMA_PATH, result)
        ensure(result["status"] == "unavailable" and result["syntax"] == [] and result["symbols"] == [],
               "corrupt syntax worker response published successful facts")
    with patch.object(inspection_syntax, "MAX_SYNTAX_NODES", 2):
        result = inspection.inspect(SOURCE).export()
    ensure(result["status"] == "unavailable" and result["syntax"] == [] and result["symbols"] == [],
           "syntax node bound escaped as a partially successful tree")
    malformed = inspection.inspect(b"module Broken; public Nat F() => true;").export()
    ensure(malformed["status"] == "unavailable" and malformed["syntax"] == [],
           "failed complete semantic check advertised checked source syntax")


def _semantic_inventory_corruption() -> None:
    source = SOURCE + b"// Identity\r\n"
    raw = {**inspect_source(source, syntax_tree=True), "concrete": concrete.parts(source)}
    corruptions: list[dict[str, object]] = []
    empty = copy.deepcopy(raw)
    empty.update(symbols=[], occurrences=[])
    corruptions.append(empty)
    omitted = copy.deepcopy(raw)
    symbols = cast("list[dict[str, object]]", omitted["symbols"])
    constant = next(index for index, symbol in enumerate(symbols) if symbol["name"] == "One")
    symbols.pop(constant)
    retained = [occurrence for occurrence in cast("list[dict[str, object]]", omitted["occurrences"])
                if occurrence["symbol"] != constant]
    for occurrence in retained:
        if cast("int", occurrence["symbol"]) > constant:
            occurrence["symbol"] = cast("int", occurrence["symbol"]) - 1
    omitted["occurrences"] = retained
    corruptions.append(omitted)
    for token in (b"Identity(x:", b"x: (x"):
        missing = copy.deepcopy(raw)
        offset = source.index(token)
        prefix = source[:offset].decode().replace("\r\n", "\n")
        line, column = prefix.count("\n") + 1, len(prefix.rsplit("\n", 1)[-1]) + 1
        occurrences = cast("list[dict[str, object]]", missing["occurrences"])
        missing["occurrences"] = [item for item in occurrences
                                   if (item["line"], item["column"]) != (line, column)]
        ensure(len(missing["occurrences"]) == len(occurrences) - 1,
               "independent omission fixture did not remove its selected callee/label")
        corruptions.append(missing)
    extra = copy.deepcopy(raw)
    symbols = cast("list[dict[str, object]]", extra["symbols"])
    identity = next(index for index, symbol in enumerate(symbols) if symbol["name"] == "Identity")
    cast("list[dict[str, object]]", extra["occurrences"]).append(
        {"symbol": identity, "line": source.count(b"\n"), "column": 4, "declaration": False})
    corruptions.append(extra)
    for changed in corruptions:
        with patch.object(inspection, "inspect_document", return_value=changed):
            snapshot = inspection.inspect(source)
        publication = snapshot.export()
        validate(inspection.SCHEMA_PATH, publication)
        ensure(publication["status"] == "unavailable" and publication["complete"] is False
               and publication["syntax"] == [] and publication["symbols"] == []
               and publication["occurrences"] == [] and publication["concrete"] == [],
               "missing or invented semantic sites masqueraded as a complete checked view")
        for operation in ("symbols", "syntax", "tokens"):
            reply = snapshot.query(source, _request(snapshot, operation))
            ensure(reply["status"] == "unavailable" and reply["complete"] is False and reply["items"] == [],
                   "incomplete producer inventory became a checked empty query")


def cases() -> list[Case]:
    return [Case("independent-pure-syntax-shape-source-spans-and-parent-links", _shape_consumer),
            Case("bounded-syntax-location-and-child-query-consumer", _query_consumer),
            Case("syntax-worker-corruption-stale-schema-and-node-bound-refusal", _worker_corruption_and_bounds),
            Case("complete-source-declaration-and-reference-inventories", _semantic_inventory_corruption)]
