# SPDX-License-Identifier: Apache-2.0
"""Independent typed-expression consumers of pure compiler inspection."""

import copy
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import concrete, inspect_source, inspection, inspection_types
from toolchain.schema import validate

INDEPENDENT_CASES = True
SOURCE = ("// \U0001f600\r\nmodule Typed;\r\npublic const bool Ready = true;\r\n"
          "public const Nat Add(const Nat step, Nat value) => (value + step);\r\n"
          "public bool Use(Nat Add, bool flag) { let result = Add(step: 2, value: Add); "
          "if (flag) { return result >= 3 && !false; } "
          "else { return Add == 0 || flag; } }\r\n").encode()


def _request(snapshot: inspection.Snapshot, operation: str, **fields: object) -> dict[str, object]:
    return {"schema": 5, "snapshot": snapshot.export()["snapshot"], "operation": operation, **fields}


def _expressions(value: dict[str, object]) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value["expressions"])


def _expected_typed_tree() -> None:
    snapshot = inspection.inspect(SOURCE)
    publication = snapshot.export()
    validate(inspection.SCHEMA_PATH, publication)
    ensure(publication["status"] == "checked", "complete pure expression producer was unavailable")
    nodes = {node["id"]: node for node in cast("list[dict[str, object]]", publication["syntax"])}
    expected = [("true", "bool"), ("(value + step)", "Nat"), ("value + step", "Nat"),
                ("value", "Nat"), ("step", "Nat"), ("Add(step: 2, value: Add)", "Nat"),
                ("2", "Nat"), ("Add", "Nat"), ("flag", "bool"),
                ("result >= 3 && !false", "bool"), ("result >= 3", "bool"),
                ("result", "Nat"), ("3", "Nat"), ("!false", "bool"), ("false", "bool"),
                ("Add == 0 || flag", "bool"), ("Add == 0", "bool"), ("Add", "Nat"),
                ("0", "Nat"), ("flag", "bool")]
    actual = [(SOURCE[slice(*cast("list[int]", item["span"]))].decode(),
               cast("dict[str, object]", item["type"])["name"])
              for item in _expressions(publication)]
    ensure(actual == expected, "typed expression preorder differs from independently authored source meanings")
    for item in _expressions(publication):
        node = nodes[item["node"]]
        ensure(node["span"] == item["span"] and node["kind"] in inspection_types.KINDS,
               "typed expression overlay does not designate its source tree node")
        response = snapshot.query(SOURCE, _request(snapshot, "expression-type", node=item["node"]))
        validate(inspection.SCHEMA_PATH, response)
        ensure(response["items"] == [item], "node query changed a compiler-owned expression decision")
    response = snapshot.query(SOURCE, _request(snapshot, "expressions"))
    ensure(response["items"] == _expressions(publication) and response["total"] == len(expected),
           "bulk expression query differs from typed tree")
    module = next(node for node in nodes.values() if node["kind"] == "module")
    ensure(snapshot.query(SOURCE, _request(snapshot, "expression-type", node=module["id"]))["items"] == [],
           "nonexpression syntax node acquired a scalar type")


def _expression_locations_and_bounds() -> None:
    snapshot = inspection.inspect(SOURCE)
    for marker, selected, expected_type in [
            (b"+ step", b"value + step", "Nat"), (b"(value +", b"(value + step)", "Nat"),
            (b", value:", b"Add(step: 2, value: Add)", "Nat"),
            (b">= 3", b"result >= 3", "bool"), (b"&& !", b"result >= 3 && !false", "bool"),
            (b"!false", b"!false", "bool"), (b"false;", b"false", "bool")]:
        response = snapshot.query(SOURCE, _request(snapshot, "expression-at", offset=SOURCE.index(marker)))
        validate(inspection.SCHEMA_PATH, response)
        item, = cast("list[dict[str, object]]", response["items"])
        ensure(SOURCE[slice(*cast("list[int]", item["span"]))] == selected
               and item["type"] == {"kind": "scalar", "name": expected_type},
               "expression-at lost the smallest containing checked expression")
    call_offset = SOURCE.index(b"Add(step:")
    identifier = snapshot.query(SOURCE, _request(snapshot, "type-at", offset=call_offset))
    expression = snapshot.query(SOURCE, _request(snapshot, "expression-at", offset=call_offset))
    ensure(cast("dict[str, object]", cast("list[dict[str, object]]", identifier["items"])[0]["type"])["kind"]
           == "function" and cast("list[dict[str, object]]", expression["items"])[0]["type"]
           == {"kind": "scalar", "name": "Nat"}, "callable identifier and call result types were collapsed")
    for offset in (0, len(SOURCE), SOURCE.index(b"return result") + len(b"return result >= 3 && !false")):
        ensure(snapshot.query(SOURCE, _request(snapshot, "expression-at", offset=offset))["items"] == [],
               "trivia, a statement terminator or EOF acquired an expression type")
    for offset in (True, -1, len(SOURCE) + 1, SOURCE.index(b"\xf0\x9f") + 1, SOURCE.index(b"\r\n") + 1):
        ensure(snapshot.query(SOURCE, _request(snapshot, "expression-at", offset=offset))["reason"] == "invalid-offset",
               "expression-at accepted malformed byte coordinates")
    limited = snapshot.query(SOURCE, _request(snapshot, "expressions", limit=1))
    validate(inspection.SCHEMA_PATH, limited)
    ensure(limited["status"] == "partial" and limited["complete"] is False and limited["total"] == 20,
           "bounded expression query advertised a complete typed tree")
    handle = _expressions(snapshot.export())[0]["node"]
    other = inspection.inspect(SOURCE + b" ")
    ensure(other.query(SOURCE + b" ", _request(other, "expression-type", node=handle))["reason"]
           == "stale-or-unknown-node", "expression query reused a foreign node handle")
    ensure(snapshot.query(SOURCE + b" ", _request(snapshot, "expressions"))["reason"] == "stale-input",
           "typed expressions survived a changed source binding")
    for node in (None, [], {}, True, "unknown"):
        ensure(snapshot.query(SOURCE, _request(snapshot, "expression-type", node=node))["status"] == "refused",
               "expression query accepted a malformed node")


def _expression_worker_refusal() -> None:
    raw = {**inspect_source(SOURCE, syntax_tree=True), "concrete": concrete.parts(SOURCE)}
    corruptions: list[object] = [None, {}, [], cast("list[object]", raw["expressions"])[:-1]]
    for edit in ("duplicate", "site", "kind", "extra", "scalar", "callable", "name-type", "literal-type"):
        expressions = copy.deepcopy(cast("list[dict[str, object]]", raw["expressions"]))
        if edit == "duplicate":
            expressions[-1] = expressions[0]
        elif edit == "site":
            expressions[0]["column"] = True
        elif edit == "kind":
            expressions[0]["kind"] = "identifier"
        elif edit == "extra":
            expressions[0]["unknown"] = True
        elif edit == "scalar":
            expressions[0]["type"] = {"kind": "scalar", "name": "u32"}
        elif edit == "callable":
            expressions[0]["type"] = {"kind": "function", "result": "bool", "parameters": [], "const": True}
        else:
            target = next(item for item in expressions if item["kind"] == ("name" if edit == "name-type" else "bool"))
            target["type"] = {"kind": "scalar", "name": "bool" if edit == "name-type" else "Nat"}
        corruptions.append(expressions)
    for expressions in corruptions:
        with patch.object(inspection, "inspect_document", return_value={**raw, "expressions": expressions}):
            publication = inspection.inspect(SOURCE).export()
        validate(inspection.SCHEMA_PATH, publication)
        ensure(publication["status"] == "unavailable" and publication["expressions"] == []
               and publication["symbols"] == [] and publication["syntax"] == [],
               "malformed or incomplete typed decisions published checked facts")
    with patch.object(inspection, "inspect_document", return_value=raw), \
            patch.object(inspection_types, "MAX_EXPRESSIONS", 2):
        publication = inspection.inspect(SOURCE).export()
    ensure(publication["status"] == "unavailable" and publication["expressions"] == [],
           "expression decision bound published a truncated checked tree")


def cases() -> list[Case]:
    return [Case("independent-typed-expression-tree-and-node-consumer", _expected_typed_tree),
            Case("operator-group-call-locations-and-stale-bounded-queries", _expression_locations_and_bounds),
            Case("expression-worker-shape-type-inventory-and-bound-refusal", _expression_worker_refusal)]
