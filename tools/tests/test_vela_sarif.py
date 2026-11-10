# SPDX-License-Identifier: Apache-2.0
"""Independent SARIF coordinate, edit, status, binding and batch-command controls."""

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
from toolchain import sarif
from toolchain.cli import vela as cli
from toolchain.lsp_services import InspectionError

INDEPENDENT_CASES = True
PRODUCER = "a" * 64
SOURCE = sarif.Input("file:///fixture/first%20%CE%BB.vela",
                     "module Fixture;\r\n// \U0001f600\r\npublic Nat F() => 1;".encode())
SECOND = sarif.Input("file:///fixture/second.vela", b"module Second; public Nat F() => true;")


def _checked(_source: bytes) -> sarif.Object | None:
    return None


def _diagnostic(kind: str = "type", *, line: int = 1, column: int = 34) -> sarif.Object:
    return {"kind": kind, "line": line, "column": column, "message": "Independent expected finding"}


def _run(document: sarif.Object) -> sarif.Object:
    return cast("list[sarif.Object]", document["runs"])[0]


def _manifest(document: sarif.Object) -> sarif.Object:
    return cast("sarif.Object", cast("sarif.Object", _run(document)["properties"])["vela"])


def _rebind(document: sarif.Object) -> None:
    manifest = _manifest(document)
    manifest.pop("binding_sha256", None)
    manifest["binding_sha256"] = hashlib.sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()


def _refuses(document: sarif.Object, inputs: tuple[sarif.Input, ...] = (SOURCE,),
             producer: str = PRODUCER) -> None:
    try:
        sarif.validate(document, inputs, producer)
    except ValueError:
        return
    raise AssertionError("accepted corrupt or stale SARIF handoff")


def _batch() -> None:
    document = sarif.export((SOURCE, SECOND), PRODUCER,
                            checker=lambda source: None if source == SOURCE.source else _diagnostic())
    manifest = sarif.validate(document, (SOURCE, SECOND), PRODUCER)
    ensure(manifest["complete"] is True, "ordinary rejected source is not an unfinished analysis")
    run = json.loads(json.dumps(document))["runs"][0]
    ensure(run["columnKind"] == "utf16CodeUnits", "SARIF coordinate units omitted")
    ensure([item["status"] for item in cast("list[sarif.Object]", manifest["inputs"])] == ["checked", "rejected"],
           "batch input verdicts differ")
    result = run["results"][0]
    ensure(result["ruleId"] == "VELA-TYPE" and result["level"] == "error", "diagnostic meaning changed")
    ensure(result["locations"][0]["physicalLocation"] == {
        "artifactLocation": {"uri": SECOND.uri, "index": 1},
        "region": {"startLine": 1, "startColumn": 34}}, "cross-file finding moved to first source")
    ensure(run["invocations"][0]["executionSuccessful"] is True, "finished check treated as unavailable")
    ensure(run["artifacts"][0]["hashes"]["sha-256"] == hashlib.sha256(SOURCE.source).hexdigest(),
           "exact CRLF source bytes not bound")


def _unicode() -> None:
    # This adapter control exercises a site after a supplementary character;
    # the current pure lexer permits Unicode in line comments only.
    item = sarif.Input("file:///fixture/unicode.vela", "// \U0001f600\u03bb site\r\n".encode())
    document = sarif.export((item,), PRODUCER, checker=lambda _source: _diagnostic(line=1, column=7))
    sarif.validate(document, (item,), PRODUCER)
    result = json.loads(json.dumps(document))["runs"][0]["results"][0]
    ensure(result["locations"][0]["physicalLocation"]["region"] == {
        "startLine": 1, "startColumn": 8}, "producer code points were not adapted to SARIF UTF-16")
    for column in (5, 99):
        changed = copy.deepcopy(document)
        results = cast("list[sarif.Object]", _run(changed)["results"])
        physical = cast("sarif.Object", cast("list[sarif.Object]", results[0]["locations"])[0]["physicalLocation"])
        cast("sarif.Object", physical["region"])["startColumn"] = column
        _rebind(changed)
        _refuses(changed, (item,))


def _fixes() -> None:
    formatted = "module Fixture;\n\n// \U0001f600\npublic Nat F() => 1;\n"
    document = sarif.export((SOURCE,), PRODUCER, format_fixes=True, checker=_checked,
                            formatter=lambda source: {"status": "ok", "formatted": formatted,
                                                       "source_sha256": hashlib.sha256(source).hexdigest()})
    sarif.validate(document, (SOURCE,), PRODUCER)
    result = json.loads(json.dumps(document))["runs"][0]["results"][0]
    replacement = result["fixes"][0]["artifactChanges"][0]["replacements"][0]
    start = replacement["deletedRegion"]["byteOffset"]
    end = start + replacement["deletedRegion"]["byteLength"]
    applied = SOURCE.source[:start] + replacement["insertedContent"]["text"].encode() + SOURCE.source[end:]
    ensure(applied == formatted.encode(), "independent UTF-8 fix application differs")
    changed = copy.deepcopy(document)
    json_run = json.loads(json.dumps(_run(changed)))
    json_run["results"][0]["fixes"][0]["artifactChanges"][0]["replacements"][0]["deletedRegion"]["byteLength"] -= 1
    changed["runs"] = [json_run]
    _rebind(changed)
    _refuses(changed)


def _incomplete() -> None:
    for kind in ("unsupported", "limit", "timeout", "internal"):
        document = sarif.export((SOURCE,), PRODUCER,
                                checker=lambda _source, kind=kind: _diagnostic(kind, line=1, column=1))
        manifest = sarif.validate(document, (SOURCE,), PRODUCER)
        ensure(manifest["complete"] is False, f"{kind} appeared complete")
        run = _run(document)
        invocations = cast("list[sarif.Object]", run["invocations"])
        ensure(invocations[0]["executionSuccessful"] is False
               and bool(invocations[0]["toolExecutionNotifications"]), "incomplete status hidden from standard readers")
        changed = copy.deepcopy(document)
        _manifest(changed)["complete"] = True
        _rebind(changed)
        _refuses(changed)
        changed = copy.deepcopy(document)
        _run(changed)["results"] = []
        _rebind(changed)
        _refuses(changed)

    def unavailable(_source: bytes) -> sarif.Object:
        raise InspectionError("formatter exceeded its time bound")

    document = sarif.export((SOURCE,), PRODUCER, checker=_checked, formatter=unavailable, format_fixes=True)
    ensure(sarif.validate(document, (SOURCE,), PRODUCER)["complete"] is False,
           "requested but unavailable formatter appeared complete")


def _corruptions() -> None:
    document = sarif.export((SOURCE,), PRODUCER, checker=lambda _source: _diagnostic(line=3, column=12))
    _refuses(document, (sarif.Input(SOURCE.uri, SOURCE.source + b" "),))
    _refuses(document, (sarif.Input(SOURCE.uri + "2", SOURCE.source),))
    _refuses(document, producer="b" * 64)
    for field, value in (("ruleId", "VELA-UNKNOWN"), ("ruleIndex", 99), ("level", "note")):
        changed = copy.deepcopy(document)
        cast("list[sarif.Object]", _run(changed)["results"])[0][field] = value
        _rebind(changed)
        _refuses(changed)
    changed = copy.deepcopy(document)
    cast("list[sarif.Object]", _run(changed)["results"])[0]["message"] = {"text": "changed"}
    _refuses(changed)
    changed = copy.deepcopy(document)
    _run(changed)["invocations"] = [{"executionSuccessful": False}]
    _rebind(changed)
    _refuses(changed)
    changed = copy.deepcopy(document)
    _manifest(changed)["schema"] = True
    _rebind(changed)
    _refuses(changed)
    changed = copy.deepcopy(document)
    cast("list[sarif.Object]", _run(changed)["results"])[0]["message"] = {}
    _rebind(changed)
    _refuses(changed)
    for value in ({}, {"runs": None}, {"runs": [None]}):
        _refuses(cast("sarif.Object", value))


def _bounds() -> None:
    for inputs in ((), (SOURCE, SOURCE), tuple(sarif.Input(f"file:///{i}", b"") for i in range(17)),
                   (sarif.Input(SOURCE.uri, b"x" * 65_537),)):
        try:
            sarif.export(inputs, PRODUCER, checker=_checked)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted invalid SARIF batch bounds")
    for producer in ("g" * 64, "A" * 64, "a" * 63):
        try:
            sarif.export((SOURCE,), producer, checker=_checked)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted a malformed producer SHA-256 identity")
    for raw in (b'{"version":1,"version":2}', b"[]", b"x" * (sarif.MAX_REPORT_BYTES + 1),
                b'{"x":' + b"[" * 65 + b"0" + b"]" * 65 + b"}", b'{"x":NaN}', b'{"x":1e999}'):
        try:
            sarif.decode(raw)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted malformed or oversized SARIF JSON")


def _command() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-sarif-") as temporary:
        root = Path(temporary)
        source, output, schema = root / "input.vela", root / "report.sarif", root / "schema.json"
        source.write_bytes(SOURCE.source)
        exporter = sarif.export
        with (patch.object(cli.compiler_trace, "producer_identity", return_value=PRODUCER),
              patch.object(sarif, "export", wraps=lambda inputs, producer, **_options:
                           exporter(inputs, producer, checker=_checked)),
              patch.object(sarif, "validate_schema"), patch.object(sarif, "check_schema_current"),
              redirect_stdout(StringIO()), redirect_stderr(StringIO())):
            args = ["sarif", str(source), "--output", str(output), "--schema", str(schema)]
            ensure(cli.main(args) == 0, "SARIF batch command failed")
            ensure(source.read_bytes() == SOURCE.source, "SARIF command rewrote source")
            ensure(cli.main(["sarif-validate", str(output), "--sources", str(source),
                             "--schema", str(schema)]) == 0, "current SARIF handoff refused")
            source.write_bytes(SOURCE.source + b" ")
            ensure(cli.main(["sarif-validate", str(output), "--sources", str(source),
                             "--schema", str(schema)]) == 1, "stale SARIF handoff accepted")
            source.write_bytes(SOURCE.source)
            ensure(cli.main(["sarif", str(source), "--output", str(source),
                             "--schema", str(schema)]) == 1, "SARIF output aliased source")
            ensure(cli.main(["sarif", str(source), "--output", str(schema),
                             "--schema", str(schema)]) == 1, "SARIF output aliased schema")
            ensure(source.read_bytes() == SOURCE.source, "failed publication changed source")
            retained = output.read_bytes()
            with patch.object(cli.compiler_trace, "producer_identity", side_effect=[PRODUCER, "b" * 64]):
                ensure(cli.main(args) == 1, "changed producer published a SARIF report")
            ensure(output.read_bytes() == retained, "producer change replaced retained output")
            with patch.object(sarif, "check_schema_current", side_effect=[None, ValueError("schema changed")]):
                ensure(cli.main(args) == 1, "changed schema published a SARIF report")
            ensure(output.read_bytes() == retained, "schema change committed staged output")


def cases() -> list[Case]:
    return [Case("sarif-batch-locations", _batch), Case("sarif-unicode-coordinates", _unicode),
            Case("sarif-format-fixes", _fixes), Case("sarif-incomplete-status", _incomplete),
            Case("sarif-corrupt-and-stale", _corruptions), Case("sarif-resource-bounds", _bounds),
            Case("sarif-batch-command", _command)]
