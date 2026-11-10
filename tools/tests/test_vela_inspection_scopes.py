# SPDX-License-Identifier: Apache-2.0
"""Independent consumers of compiler-owned pure lexical scope facts."""

import copy
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import concrete, inspect_source, inspection, inspection_scopes
from toolchain.schema import validate

INDEPENDENT_CASES = True
SOURCE = ("// \U0001f600\r\nmodule Scope;\r\npublic const Nat Global = 7;\r\n"
          "public Nat Helper(Nat value) => value + 1;\r\n"
          "public Nat Pick(bool flag, Nat Global) { let seed = Global; "
          "if (flag) { let local = Helper(value: seed); return local; } "
          "else { let local = Global + 2; return local; } }\r\n"
          "public Nat Later() => Global;\r\n").encode()


def _request(snapshot: inspection.Snapshot, operation: str, **fields: object) -> dict[str, object]:
    return {"schema": 6, "snapshot": snapshot.export()["snapshot"], "operation": operation, **fields}


def _records(value: dict[str, object], key: str) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value[key])


def _expected_scope_tree() -> None:
    snapshot = inspection.inspect(SOURCE)
    value = snapshot.export()
    validate(inspection.SCHEMA_PATH, value)
    ensure(value["status"] == "checked", "pure scope producer unavailable")
    scopes = _records(value, "scopes")
    symbols = _records(value, "symbols")
    by_scope = {scope["id"]: index for index, scope in enumerate(scopes)}
    expected = [("module", None, ["Global", "Helper", "Pick", "Later"]),
                ("function", 0, ["value"]), ("block", 1, []),
                ("function", 0, ["flag", "Global"]), ("block", 3, ["seed"]),
                ("block", 4, ["local"]), ("block", 4, ["local"]),
                ("function", 0, []), ("block", 7, [])]
    for scope, (kind, parent, names) in zip(scopes, expected, strict=True):
        ensure(scope["kind"] == kind and by_scope.get(scope["parent"]) == parent,
               "scope tree differs from independently expected lexical nesting")
        declared = [symbol for symbol in symbols if symbol["id"] in cast("list[str]", scope["symbols"])]
        ensure([symbol["name"] for symbol in declared] == names
               and all(symbol["scope"] == scope["id"] for symbol in declared),
               "scope declaration ownership differs from source")
        ensure(scope["children"] == [item["id"] for item in scopes if item["parent"] == scope["id"]],
               "scope child links differ from parent links")
        nodes = _records(value, "syntax")
        node = next(node for node in nodes if node["id"] == scope["node"])
        ensure(scope["span"] == node["span"], "scope has no exact source syntax extent")
    global_symbols = [symbol for symbol in symbols if symbol["name"] == "Global"]
    ensure(len(global_symbols) == 2 and global_symbols[0]["scope"] != global_symbols[1]["scope"],
           "parameter shadowing lost separate declaration owners")
    for marker, expected_symbol, expected_scope in (
            (b"seed = Global", global_symbols[1], 4),
            (b"Global + 2", global_symbols[1], 6),
            (b"=> Global", global_symbols[0], 8)):
        offset = SOURCE.index(marker) + marker.index(b"Global")
        occurrence = next(item for item in _records(value, "occurrences")
                          if cast("list[int]", item["span"])[0] == offset)
        ensure(occurrence["symbol"] == expected_symbol["id"] and by_scope[occurrence["scope"]] == expected_scope,
               "scope overlay altered compiler resolution or reference environment")
    helper_parameter = next(symbol for symbol in symbols if symbol["name"] == "value")
    label = next(item for item in _records(value, "occurrences")
                 if cast("list[int]", item["span"])[0] == SOURCE.index(b"value: seed"))
    ensure(label["symbol"] == helper_parameter["id"] and by_scope[label["scope"]] == 5,
           "named argument label confused declaration owner and occurrence environment")
    seed = next(symbol for symbol in symbols if symbol["name"] == "seed")
    helper = next(symbol for symbol in symbols if symbol["name"] == "Helper")
    ensure(seed["available_from"] == SOURCE.index(b"; if (flag)") + 1
           and helper["available_from"] == SOURCE.index(b";\r\npublic Nat Pick") + 1
           and helper_parameter["available_from"] == SOURCE.index(b"=> value"),
           "availability offsets do not preserve initializer and forward-call boundaries")


def _queries_and_lifetimes() -> None:
    snapshot = inspection.inspect(SOURCE)
    value = snapshot.export()
    scopes = _records(value, "scopes")
    for marker, index in ((b"module Scope", 0), (b"Helper(Nat", 1), (b"value + 1", 2),
                          (b"let seed", 4), (b"value: seed", 5), (b"Global + 2", 6)):
        reply = snapshot.query(SOURCE, _request(snapshot, "scope-at", offset=SOURCE.index(marker)))
        validate(inspection.SCHEMA_PATH, reply)
        ensure(reply["items"] == [scopes[index]], "scope-at did not select the innermost lexical environment")
    for index in (0, len(SOURCE)):
        ensure(snapshot.query(SOURCE, _request(snapshot, "scope-at", offset=index))["items"] == [],
               "leading trivia or EOF selected a source scope")
    for scope in scopes:
        reply = snapshot.query(SOURCE, _request(snapshot, "scope-symbols", scope=scope["id"]))
        validate(inspection.SCHEMA_PATH, reply)
        ensure([item["id"] for item in _records(reply, "items")] == scope["symbols"],
               "scope-symbols included declarations from a parent or sibling")
    limited = snapshot.query(SOURCE, _request(snapshot, "scopes", limit=2))
    validate(inspection.SCHEMA_PATH, limited)
    ensure(limited["status"] == "partial" and limited["complete"] is False and limited["total"] == 9,
           "bounded scope query advertised truncated nesting as complete")
    changed = inspection.inspect(SOURCE + b" ")
    ensure(changed.query(SOURCE + b" ", _request(changed, "scope-symbols", scope=scopes[0]["id"]))["reason"]
           == "stale-or-unknown-scope", "foreign scope handle designated a new environment")
    for handle in (None, [], {}, True, "missing"):
        ensure(snapshot.query(SOURCE, _request(snapshot, "scope-symbols", scope=handle))["status"] == "refused",
               "malformed scope handle escaped refusal")
    for offset in (True, -1, len(SOURCE) + 1, SOURCE.index(b"\xf0") + 1):
        ensure(snapshot.query(SOURCE, _request(snapshot, "scope-at", offset=offset))["reason"] == "invalid-offset",
               "scope query accepted invalid byte coordinates")
    ensure(snapshot.query(SOURCE, _request(snapshot, "scopes", schema=5))["reason"] == "schema-version",
           "old schema query acquired new scope semantics")


def _worker_scope_refusals() -> None:
    raw = {**inspect_source(SOURCE, syntax_tree=True), "concrete": concrete.parts(SOURCE)}
    for corruption in ("missing", "extra", "omitted-scope", "parent", "boolean-parent", "kind", "site",
                       "symbol-owner", "occurrence-owner", "omitted-symbol", "boolean-symbol"):
        changed = copy.deepcopy(raw)
        decisions = cast("dict[str, object]", changed["scopes"])
        scopes = _records(decisions, "scopes")
        if corruption == "missing":
            del changed["scopes"]
        elif corruption == "extra":
            decisions["extra"] = True
        elif corruption == "omitted-scope":
            scopes.pop()
        elif corruption in {"parent", "boolean-parent"}:
            scopes[2]["parent"] = 0 if corruption == "parent" else True
        elif corruption == "kind":
            scopes[1]["kind"] = "block"
        elif corruption == "site":
            scopes[0]["column"] = cast("int", scopes[0]["column"]) + 1
        elif corruption == "occurrence-owner":
            cast("list[object]", decisions["occurrences"])[-1] = 0
        elif corruption == "omitted-symbol":
            cast("list[object]", decisions["symbols"]).pop()
        else:
            cast("list[object]", decisions["symbols"])[0] = 1 if corruption == "symbol-owner" else False
        with patch.object(inspection, "inspect_document", return_value=changed):
            value = inspection.inspect(SOURCE).export()
        validate(inspection.SCHEMA_PATH, value)
        ensure(value["status"] == "unavailable" and value["scopes"] == [] and value["symbols"] == [],
               "malformed resolver scope decisions published checked facts")
    with patch.object(inspection, "inspect_document", return_value=raw), \
            patch.object(inspection_scopes, "MAX_SCOPES", 2):
        value = inspection.inspect(SOURCE).export()
    ensure(value["status"] == "unavailable" and value["scopes"] == [],
           "scope inventory bound silently truncated checked facts")


def cases() -> list[Case]:
    return [Case("independent-lexical-scope-tree-shadowing-and-availability", _expected_scope_tree),
            Case("scope-query-location-truncation-and-handle-lifetimes", _queries_and_lifetimes),
            Case("scope-worker-shape-membership-site-and-bound-refusal", _worker_scope_refusals)]
