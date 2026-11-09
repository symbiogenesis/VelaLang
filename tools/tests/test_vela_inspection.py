# SPDX-License-Identifier: Apache-2.0
"""Independent consumer expectations for the versioned pure inspection subset."""

import copy
import hashlib
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import inspection
from toolchain.cli import vela as cli
from toolchain.lsp_services import InspectionError
from toolchain.schema import validate

INDEPENDENT_CASES = True

SOURCE = ("module Inspect;\r\n// supplementary: 😀\r\n"
          "public Nat First(Nat value) { let result = value + 1; return result; }\r\n"
          "public Nat Second(Nat value) { return First(value); }\r\n").encode()


def _request(snapshot: inspection.Snapshot, operation: str, **fields: object) -> dict[str, object]:
    return {"schema": 1, "snapshot": snapshot.export()["snapshot"], "operation": operation, **fields}


def _symbols(value: dict[str, object]) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", value["symbols"])


def _reconstruction_and_expected_facts() -> None:
    snapshot = inspection.inspect(SOURCE)
    value = snapshot.export()
    validate(inspection.SCHEMA_PATH, value)
    ensure(value["status"] == "checked" and value["complete"] is True, "valid pure inspection unavailable")
    ensure(cast("str", value["source"]).encode() == SOURCE, "export normalized Unicode or source newlines")
    binding = cast("dict[str, object]", value["binding"])
    ensure(binding["source_sha256"] == hashlib.sha256(SOURCE).hexdigest()
           and binding["coordinate_unit"] == "utf8-byte", "consumer cannot reconstruct byte identity")
    symbols = _symbols(value)
    ensure([(symbol["name"], symbol["kind"]) for symbol in symbols] == [
        ("First", "function"), ("value", "parameter"), ("result", "variable"),
        ("Second", "function"), ("value", "parameter")], "unexpected declaration order or binding inventory")
    ensure(symbols[2]["detail"] == "result: Nat", "inferred local type did not come from compiler")
    for symbol in symbols:
        first, last = cast("list[int]", symbol["span"])
        ensure(SOURCE[first:last].decode() == symbol["name"], "byte span differs from independent source bytes")
        ensure(symbol["origin"] == {"kind": "authored", "span": [first, last]}, "authored origin changed")
    exported = snapshot.export()
    _symbols(exported)[0]["name"] = "Corrupted"
    ensure(_symbols(snapshot.export())[0]["name"] == "First", "export mutation changed retained facts")


def _query_consumer() -> None:
    snapshot = inspection.inspect(SOURCE)
    symbols = _symbols(snapshot.export())
    first_value = SOURCE.index(b"value +")
    second_value = SOURCE.index(b"value);")
    for offset, expected in ((first_value, symbols[1]), (second_value, symbols[4])):
        response = snapshot.query(SOURCE, _request(snapshot, "symbol-at", offset=offset))
        validate(inspection.SCHEMA_PATH, response)
        ensure(response["items"] == [expected], "symbol-at conflated same-spelled parameters")
        references = snapshot.query(SOURCE, _request(snapshot, "references", symbol=expected["id"]))
        items = cast("list[dict[str, object]]", references["items"])
        ensure(references["total"] == 2 and [item["declaration"] for item in items] == [True, False],
               "reference query lost declaration or scoped use")
    empty = snapshot.query(SOURCE, _request(snapshot, "symbol-at", offset=first_value + len(b"value")))
    ensure(empty["status"] == "checked" and empty["items"] == [], "identifier end was not half-open")
    unicode_inside = SOURCE.index("😀".encode()) + 1
    for offset in (unicode_inside, True, -1, len(SOURCE) + 1):
        refused = snapshot.query(SOURCE, _request(snapshot, "symbol-at", offset=offset))
        ensure(refused["reason"] == "invalid-offset", "invalid UTF-8 query position accepted")


def _determinism_and_cross_snapshot_handles() -> None:
    first = inspection.inspect(SOURCE)
    again = inspection.inspect(SOURCE)
    ensure(first.publication == again.publication, "unchanged producer/input made unstable snapshot IDs")
    changed_source = SOURCE + b"// changed\r\n"
    second = inspection.inspect(changed_source)
    ensure(first.export()["snapshot"] != second.export()["snapshot"], "source edit retained snapshot identity")
    handle = _symbols(first.export())[0]["id"]
    response = second.query(changed_source, _request(second, "references", symbol=handle))
    ensure(response["status"] == "refused" and response["reason"] == "stale-or-unknown-symbol",
           "old symbol handle silently designated current declaration")
    response = second.query(changed_source, _request(first, "symbols"))
    ensure(response["reason"] == "stale-snapshot", "old snapshot query accepted")


def _nested_scope_consumer() -> None:
    source = (b"module Scope; public Nat Pick(bool flag, Nat value) { "
              b"if (flag) { let local = value; return local; } "
              b"else { let local = value + 1; return local; } }")
    snapshot = inspection.inspect(source)
    locals_ = [symbol for symbol in _symbols(snapshot.export()) if symbol["name"] == "local"]
    ensure(len(locals_) == 2 and locals_[0]["id"] != locals_[1]["id"],
           "sibling block bindings were collapsed by spelling")
    expected_offsets = [source.index(b"return local") + len(b"return "),
                        source.rindex(b"return local") + len(b"return ")]
    for symbol, offset in zip(locals_, expected_offsets, strict=True):
        response = snapshot.query(source, _request(snapshot, "symbol-at", offset=offset))
        ensure(response["items"] == [symbol], "nested block reference resolved to sibling declaration")


def _binding_invalidation() -> None:
    snapshot = inspection.inspect(SOURCE)
    request = _request(snapshot, "symbols")
    for options in ({"uri": "memory:other"}, {"configuration": "changed"}, {"target": "native-other"}):
        response = snapshot.query(SOURCE, request, **options)
        ensure(response["status"] == "refused" and response["reason"] == "stale-input",
               "changed context retained current semantic evidence")
    ensure(snapshot.query(SOURCE + b" ", request)["reason"] == "stale-input", "changed source retained facts")
    producer = inspection.producer_identity()
    dependencies = cast("dict[str, object]", producer["dependencies"])
    ensure("tools/toolchain/ast.py" in dependencies and "tools/toolchain/parser/parser.mly" in dependencies
           and "tools/uv.lock" in dependencies, "producer closure omits compiler/dependency owners")
    changed = copy.deepcopy(producer)
    cast("dict[str, object]", changed["dependencies"])["tools/toolchain/ast.py"] = "0" * 64
    with patch.object(inspection, "producer_identity", return_value=changed):
        ensure(snapshot.query(SOURCE, request)["reason"] == "stale-input", "dependency edit retained facts")
    with patch.object(inspection, "producer_identity", side_effect=[producer, changed]):
        current = inspection.inspect(SOURCE).export()
    ensure(current["status"] == "refused" and current["symbols"] == [], "mid-check producer edit published facts")


def _bounded_and_malformed_queries() -> None:
    snapshot = inspection.inspect(SOURCE)
    partial = snapshot.query(SOURCE, _request(snapshot, "symbols", limit=1))
    validate(inspection.SCHEMA_PATH, partial)
    ensure(partial["status"] == "partial" and partial["complete"] is False
           and partial["total"] == 5 and len(cast("list[object]", partial["items"])) == 1,
           "bounded query disguised truncation as complete")
    for bad in (None, [], {}, _request(snapshot, "symbols", extra=True),
                _request(snapshot, "symbols", schema=True), _request(snapshot, "symbols", schema=2),
                _request(snapshot, "symbols", limit=0), _request(snapshot, "symbols", limit=257),
                _request(snapshot, "symbols", limit=True)):
        response = snapshot.query(SOURCE, bad)
        validate(inspection.SCHEMA_PATH, response)
        ensure(response["status"] == "refused" and response["complete"] is False,
               "malformed or over-budget query accepted")
    unsupported = snapshot.query(SOURCE, _request(snapshot, "proof-state"))
    ensure(unsupported["status"] == "unsupported", "unavailable proof operation was advertised")
    for operation in ([], {}, True):
        request = _request(snapshot, "symbols")
        request["operation"] = operation
        ensure(snapshot.query(SOURCE, request)["status"] == "unsupported", "malformed operation crashed query")


def _unavailable_status_and_schema() -> None:
    for source in (b"module Broken; public Nat F(", b"module Bad; public Nat F() { return true; }"):
        snapshot = inspection.inspect(source)
        value = snapshot.export()
        validate(inspection.SCHEMA_PATH, value)
        ensure(value["status"] == "unavailable" and value["complete"] is False
               and value["symbols"] == [] and value["occurrences"] == [], "failed source published partial facts")
        response = snapshot.query(source, _request(snapshot, "symbols"))
        ensure(response["status"] == "unavailable" and response["complete"] is False,
               "unavailable facts looked like verified reference absence")
    unsupported = inspection.inspect(SOURCE, target="machine").export()
    ensure(unsupported["status"] == "unsupported", "unsupported target used a silent runtime fallback")
    with patch.object(inspection, "inspect_document", side_effect=InspectionError("exceeded 5 seconds")):
        timed = inspection.inspect(SOURCE).export()
    ensure(timed["status"] == "timed-out" and timed["symbols"] == [], "timeout retained successful status")
    for change in ({"schema": 2}, {"complete": True}, {"unknown": "field"}):
        invalid = {**timed, **change}
        try:
            validate(inspection.SCHEMA_PATH, invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("independent schema validator accepted malformed inspection")


def _export_bound() -> None:
    full = inspection.inspect(SOURCE).export()
    empty = {**full, "symbols": [], "occurrences": [], "status": "unavailable", "complete": False,
             "reason": "export-limit"}
    bound = len(json.dumps(empty, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()) + 1
    with patch.object(inspection, "MAX_EXPORT_BYTES", bound):
        snapshot = inspection.inspect(SOURCE)
    value = snapshot.export()
    validate(inspection.SCHEMA_PATH, value)
    ensure(len(snapshot.publication) <= bound and value["status"] == "unavailable"
           and value["reason"] == "export-limit" and value["symbols"] == [],
           "export bound published truncated facts as a successful snapshot")


def _cli_source_preservation() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-inspection-") as directory:
        path = Path(directory) / "source.vela"
        path.write_bytes(SOURCE)
        before = path.stat()
        with redirect_stdout(output := StringIO()), redirect_stderr(errors := StringIO()):
            code = cli.main(["inspect", str(path)])
        ensure(code == 0 and not errors.getvalue(), "inspection CLI failed")
        value = json.loads(output.getvalue())
        validate(inspection.SCHEMA_PATH, value)
        query = Path(directory) / "query.json"
        query.write_text(json.dumps({"schema": 1, "snapshot": value["snapshot"], "operation": "symbols"}),
                         encoding="utf-8")
        with redirect_stdout(output := StringIO()), redirect_stderr(errors := StringIO()):
            code = cli.main(["inspect", str(path), "--query", str(query)])
        ensure(code == 0 and not errors.getvalue() and json.loads(output.getvalue())["total"] == 5,
               "CLI did not accept previous same-input snapshot query")
        ensure(path.read_bytes() == SOURCE and path.stat().st_ino == before.st_ino
               and path.stat().st_mtime_ns == before.st_mtime_ns, "read-only inspection rewrote source")


def cases() -> list[Case]:
    return [Case("source-preserving-schema-and-fact-consumer", _reconstruction_and_expected_facts),
            Case("byte-position-and-scoped-reference-consumer", _query_consumer),
            Case("deterministic-snapshot-and-handle-lifetime", _determinism_and_cross_snapshot_handles),
            Case("nested-sibling-scope-consumer", _nested_scope_consumer),
            Case("source-config-target-and-producer-invalidation", _binding_invalidation),
            Case("query-bounds-and-malformed-input-refusal", _bounded_and_malformed_queries),
            Case("unavailable-timeout-and-schema-refusal", _unavailable_status_and_schema),
            Case("bounded-export-without-partial-fact-publication", _export_bound),
            Case("source-preserving-inspection-cli", _cli_source_preservation)]
