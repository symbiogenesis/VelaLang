# SPDX-License-Identifier: Apache-2.0
"""Independent offline consumer qualification with source-owned expected answers."""

import copy
import hashlib
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from functools import cache
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import inspection, inspection_reader
from toolchain.cli import vela as cli
from toolchain.schema import validate

INDEPENDENT_CASES = True
SOURCE = ("/// reader 😀\r\nmodule Reader;\r\n"
          "public const Nat value = 7;\r\n"
          "public const Nat Add(const Nat left, Nat right) => left + right;\r\n"
          "public Nat Pick(bool flag, Nat value) {\r\n"
          " if (flag) { let local = Add(left: 2, right: value); return local; }\r\n"
          " else { let local = value + 1; return local; }\r\n"
          "}\r\n").encode()


@cache
def _fixture() -> bytes:
    snapshot = inspection.inspect(SOURCE)
    ensure(snapshot.export()["status"] == "checked", "reader fixture did not compile")
    return snapshot.publication


def _read() -> inspection_reader.Reader:
    return inspection_reader.read(_fixture(), SOURCE, binding=inspection.current_binding(SOURCE))


def _records(value: dict[str, object], key: str) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value[key])


def _query(reader: inspection_reader.Reader, operation: str, **fields: object) -> dict[str, object]:
    result = reader.query(SOURCE, {"schema": 6, "snapshot": reader.export()["snapshot"],
                                  "operation": operation, **fields}, binding=inspection.current_binding(SOURCE))
    validate(inspection_reader.SCHEMA_PATH, result)
    return result


def _expected_source_and_symbols() -> None:
    reader = _read()
    value = reader.export()
    ensure(cast("str", value["source"]).encode() == SOURCE, "reader normalized CRLF or supplementary characters")
    pieces = _records(_query(reader, "tokens"), "items")
    ensure("".join(cast("str", piece["text"]) for piece in pieces).encode() == SOURCE,
           "offline concrete query did not reconstruct exact source")
    symbols = _records(_query(reader, "symbols"), "items")
    ensure([(item["name"], item["kind"]) for item in symbols] == [
        ("value", "constant"), ("Add", "function"), ("left", "parameter"), ("right", "parameter"),
        ("Pick", "function"), ("flag", "parameter"), ("value", "parameter"),
        ("local", "variable"), ("local", "variable")], "offline declaration inventory differs from expected source")
    ensure(symbols[1]["type"] == {"kind": "function", "result": "Nat", "const": True,
        "parameters": [{"type": "Nat", "required_static": True}, {"type": "Nat", "required_static": False}]},
        "offline reader lost ordered required-static callable type")
    value["source"] = "changed"
    symbols[0]["name"] = "changed"
    ensure(cast("str", reader.export()["source"]).encode() == SOURCE, "detached client mutation changed retained publication")


def _expected_reference_type_and_scope_queries() -> None:
    reader = _read()
    symbols = _records(reader.export(), "symbols")
    sites = [(SOURCE.index(b"right: value") + len(b"right: "), 6),
             (SOURCE.index(b"return local") + len(b"return "), 7),
             (SOURCE.rindex(b"return local") + len(b"return "), 8),
             (SOURCE.index(b"Add(left:"), 1), (SOURCE.index(b"left: 2"), 2)]
    for offset, index in sites:
        ensure(_query(reader, "symbol-at", offset=offset)["items"] == [symbols[index]],
               "offline lookup conflated shadowed values, sibling locals or named-argument parameter")
        typed = _records(_query(reader, "type-at", offset=offset), "items")
        ensure(typed == [{"symbol": symbols[index]["id"], "span": [offset, offset + len(cast("str", symbols[index]["name"]))],
                          "type": symbols[index]["type"]}], "offline identifier type has wrong source site")
    references = _records(_query(reader, "references", symbol=symbols[6]["id"]), "items")
    expected = [SOURCE.index(b"Nat value) ") + len(b"Nat "),
                SOURCE.index(b"right: value") + len(b"right: "), SOURCE.index(b"local = value") + len(b"local = ")]
    ensure([item["span"] for item in references] == [[offset, offset + 5] for offset in expected],
           "offline reference query differs from independent shadowing expectation")
    first_scope = _records(_query(reader, "scope-at", offset=sites[1][0]), "items")[0]
    second_scope = _records(_query(reader, "scope-at", offset=sites[2][0]), "items")[0]
    ensure(first_scope["id"] != second_scope["id"], "sibling blocks collapsed into one lexical scope")
    ensure(_query(reader, "scope-symbols", scope=first_scope["id"])["items"] == [symbols[7]],
           "offline scope query included sibling or inherited declarations")
    expression = _records(_query(reader, "expression-at", offset=SOURCE.index(b"Add(left:")), "items")[0]
    ensure(expression["type"] == {"kind": "scalar", "name": "Nat"}, "call result became callable type")
    ensure(_query(reader, "expression-type", node=expression["node"])["items"] == [expression],
           "offline expression handle lost type overlay")
    node = _records(_query(reader, "syntax-at", offset=SOURCE.index(b"Add(left:")), "items")[0]
    ensure(node["kind"] == "identifier" and node["value"] == "Add", "offline smallest-node selection changed")
    root = _records(_query(reader, "syntax"), "items")[0]
    children = _records(_query(reader, "syntax-children", node=root["id"]), "items")
    ensure([item["kind"] for item in children] == ["identifier", "constant", "function", "function"],
           "offline child query lost source-field order")
    ensure([item["kind"] for item in _records(_query(reader, "scopes"), "items")] == [
        "module", "function", "block", "function", "block", "block", "block"],
        "offline scope inventory differs from expected lexical source environments")
    expressions = _records(_query(reader, "expressions"), "items")
    expected_expressions = [("7", "Nat"), ("left + right", "Nat"), ("left", "Nat"), ("right", "Nat"),
                            ("flag", "bool"), ("Add(left: 2, right: value)", "Nat"), ("2", "Nat"),
                            ("value", "Nat"), ("local", "Nat"), ("value + 1", "Nat"),
                            ("value", "Nat"), ("1", "Nat"), ("local", "Nat")]
    ensure([(SOURCE[cast("list[int]", item["span"])[0]:cast("list[int]", item["span"])[1]].decode(),
             cast("dict[str, object]", item["type"])["name"]) for item in expressions] == expected_expressions,
           "offline expression inventory lost expected scalar types or source expressions")


def _malformed_inventory_and_binding_refusals() -> None:
    original = json.loads(_fixture())
    corruptions: list[dict[str, object]] = []
    mutations = [
        ("concrete", 0, {"span": [0, 1]}),
        ("syntax", 0, {"children": []}),
        ("syntax", 1, {"parent": None}),
        ("syntax", 1, {"id": "0" * 64 + ":node:1"}),
        ("symbols", 0, {"origin": {"kind": "authored", "span": [0, 1]}}),
        ("symbols", 0, {"available_from": 0}),
        ("scopes", 0, {"symbols": []}),
        ("scopes", 1, {"node": original["syntax"][0]["id"]}),
        ("occurrences", 0, {"symbol": original["symbols"][1]["id"]}),
        ("occurrences", 0, {"declaration": False}),
        ("expressions", 0, {"span": [0, 1]}),
    ]
    for key, index, fields in mutations:
        changed = copy.deepcopy(original)
        changed[key][index].update(fields)
        corruptions.append(changed)
    changed = copy.deepcopy(original)
    changed["expressions"] = changed["expressions"][:-1]
    corruptions.append(changed)
    changed = copy.deepcopy(original)
    references = changed["occurrences"]
    omitted = next(index for index, item in enumerate(references) if not item["declaration"])
    del references[omitted]
    corruptions.append(changed)
    changed = copy.deepcopy(original)
    removed = changed["symbols"].pop()
    changed["occurrences"] = [item for item in changed["occurrences"] if item["symbol"] != removed["id"]]
    for scope in changed["scopes"]:
        scope["symbols"] = [handle for handle in scope["symbols"] if handle != removed["id"]]
    corruptions.append(changed)
    changed = copy.deepcopy(original)
    scopes = changed["scopes"]
    moved = scopes[2]
    moved["parent"] = scopes[0]["id"]
    scopes[1]["children"].remove(moved["id"])
    scopes[0]["children"].insert(1, moved["id"])
    corruptions.append(changed)
    changed = copy.deepcopy(original)
    changed["source"] += " "
    corruptions.append(changed)
    changed = copy.deepcopy(original)
    changed["snapshot"] = "0" * 64
    corruptions.append(changed)
    for value in corruptions:
        try:
            inspection_reader.read(json.dumps(value).encode(), SOURCE, binding=inspection.current_binding(SOURCE))
        except ValueError:
            pass
        else:
            raise AssertionError("independent consumer accepted corrupt serialized inspection")
    for binding in (inspection.current_binding(SOURCE, uri="memory:other"),
                    inspection.current_binding(SOURCE, configuration="changed"),
                    inspection.current_binding(SOURCE, target="changed")):
        try:
            inspection_reader.read(_fixture(), SOURCE, binding=binding)
        except ValueError:
            pass
        else:
            raise AssertionError("offline handoff accepted changed URI, configuration or target")
    duplicate = _fixture()[:-1] + b',"schema":6}'
    for publication in (duplicate, b'{"schema":true}', b"[", b"\xff", b" " * (inspection_reader.MAX_PUBLICATION_BYTES + 1)):
        try:
            inspection_reader.read(publication, SOURCE, binding=inspection.current_binding(SOURCE))
        except ValueError:
            pass
        else:
            raise AssertionError("consumer accepted duplicate, malformed or over-budget JSON")


def _bounded_queries_stale_and_failed_status() -> None:
    reader = _read()
    response = _query(reader, "symbols", limit=2)
    ensure(response["status"] == "partial" and response["complete"] is False
           and response["reason"] == "result-limit" and response["total"] == 9,
           "offline result truncation claimed complete symbol absence")
    for offset in (-1, True, len(SOURCE) + 1, SOURCE.index("😀".encode()) + 1, SOURCE.index(b"\r\n") + 1):
        ensure(_query(reader, "symbol-at", offset=offset)["reason"] == "invalid-offset",
               "offline coordinate admitted an invalid byte or CRLF interior")
    ensure(_query(reader, "token-at", offset=len(SOURCE))["items"] == [], "offline EOF selected a token")
    for operation, fields in (("references", {"symbol": "0" * 64 + ":symbol:0"}),
                              ("syntax-children", {"node": "0" * 64 + ":node:0"}),
                              ("scope-symbols", {"scope": "0" * 64 + ":scope:0"})):
        ensure(_query(reader, operation, **fields)["status"] == "refused", "foreign handle accepted offline")
    request = {"schema": 6, "snapshot": reader.export()["snapshot"], "operation": "symbols"}
    for bad in (None, [], {}, {**request, "schema": True}, {**request, "schema": 5},
                {**request, "snapshot": "0" * 64}, {**request, "limit": True},
                {**request, "limit": 0}, {**request, "limit": 257}, {**request, "extra": True}):
        ensure(reader.query(SOURCE, bad, binding=inspection.current_binding(SOURCE))["status"] == "refused",
               "offline malformed query accepted")
    ensure(_query(reader, "proof-state")["status"] == "unsupported", "offline reader invented proof producer")
    ensure(reader.query(SOURCE + b" ", request, binding=inspection.current_binding(SOURCE))["reason"] == "stale-input",
           "offline reader reused changed source")
    changed = inspection.current_binding(SOURCE)
    cast("dict[str, object]", changed["producer"])["version"] = "0" * 64
    ensure(reader.query(SOURCE, request, binding=changed)["reason"] == "stale-input", "changed producer retained facts")
    for status in ("unavailable", "timed-out", "unsupported", "refused"):
        failed = reader.export()
        failed.update(status=status, complete=False, reason="fixture-incomplete")
        for key in ("symbols", "occurrences", "concrete", "syntax", "expressions", "scopes"):
            failed[key] = []
        retained = inspection_reader.read(json.dumps(failed).encode(), SOURCE, binding=inspection.current_binding(SOURCE))
        response = retained.query(SOURCE, request, binding=inspection.current_binding(SOURCE))
        ensure(response["status"] == status and response["complete"] is False and response["items"] == [],
               "offline failed producer became checked absence")


def _cli_roundtrip_without_worker() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-inspection-reader-") as directory:
        source = Path(directory) / "reader.vela"
        source.write_bytes(SOURCE)
        before = source.stat()
        snapshot = inspection.inspect(SOURCE, uri=source.resolve().as_uri())
        publication = Path(directory) / "snapshot.json"
        publication.write_bytes(snapshot.publication)
        query = Path(directory) / "request.json"
        query.write_text(json.dumps({"schema": 6, "snapshot": snapshot.export()["snapshot"],
                                     "operation": "symbols"}), encoding="utf-8")
        with (patch.object(inspection, "inspect_document", side_effect=AssertionError("offline reader invoked compiler")),
              redirect_stdout(output := StringIO()), redirect_stderr(errors := StringIO())):
            code = cli.main(["inspect", str(source), "--snapshot", str(publication), "--query", str(query)])
        result = json.loads(output.getvalue())
        ensure(code == 0 and not errors.getvalue() and result["total"] == 9,
               "CLI did not project retained snapshot independently of compiler worker")
        ensure(source.read_bytes() == SOURCE and source.stat().st_mtime_ns == before.st_mtime_ns,
               "offline query rewrote authored source")
        ensure(hashlib.sha256(source.read_bytes()).hexdigest() == result["binding"]["source_sha256"],
               "CLI handoff lost source digest")
        source.write_bytes(SOURCE + b" ")
        with redirect_stdout(output := StringIO()), redirect_stderr(errors := StringIO()):
            code = cli.main(["inspect", str(source), "--snapshot", str(publication)])
        ensure(code == 1 and not output.getvalue() and "does not bind current inputs" in errors.getvalue(),
               "CLI handed stale snapshot to offline consumer")


def cases() -> list[Case]:
    return [Case("offline-source-and-explicit-callable-fact-consumer", _expected_source_and_symbols),
            Case("offline-expected-shadowing-reference-type-and-tree-queries", _expected_reference_type_and_scope_queries),
            Case("offline-malformed-graphs-bindings-and-publications-refused", _malformed_inventory_and_binding_refusals),
            Case("offline-bounded-stale-and-incomplete-query-statuses", _bounded_queries_stale_and_failed_status),
            Case("offline-cli-source-preserving-roundtrip-without-compiler", _cli_roundtrip_without_worker)]
