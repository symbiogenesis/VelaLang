# SPDX-License-Identifier: Apache-2.0
"""Offline qualification of an exact-pinned independent SARIF importer."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

from toolchain import compiler_trace, sarif

WHEEL_PINS = {
    "sarif_tools-3.0.5-py3-none-any.whl": "682d22559095ca4a210a401e21f0585fdb8015e826c0d160ab3cbadee326952f",
    "jsonpath_ng-1.7.0-py3-none-any.whl": "f3d7f9e848cba1b6da28c55b1c26ff915dc9e0b1ba7e752a53d6da8d5cbd00b6",
    "ply-3.11-py2.py3-none-any.whl": "096f9b8350b65ebd2fd1346b12452efe5b9607f7482813ffca50c22722a807ce",
    "pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl":
        "501a031947e3a9025ed4405a168e6ef5ae3126c59f90ce0cd6f2bfc477be31b7",
}
MAX_WHEEL_BYTES = 2_000_000
MAX_READER_OUTPUT = 65_536
READER_SECONDS = 15
NEGATIVE_CONTROLS = ("stale-source", "stale-producer", "source-location", "rule-reference",
                     "completion-status", "missing-finding", "fix-range", "report-corruption")
FIRST = sarif.Input("file:///sarif%20fixture/%CE%BB%F0%9F%98%80.vela",
                    "module Fixture;\r\n// \U0001f600 \u03bb\r\npublic Nat First()=>1;".encode())
SECOND = sarif.Input("file:///sarif%20fixture/other.vela",
                     "module Other;\n// \u03bb\U0001f600\npublic Nat Wrong() => true;".encode())
UNSUPPORTED = sarif.Input("file:///sarif%20fixture/unfinished.vela",
                          b"module Unfinished; public Nat Wait() { return await; }")
EXPECTED_FORMATTED = "module Fixture;\n\n// \U0001f600 \u03bb\npublic Nat First() => 1;\n"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reader_identity(directory: Path) -> sarif.Object:
    """Verify every imported external wheel before any reader code executes."""
    hashes: dict[str, str] = {}
    for name, expected in WHEEL_PINS.items():
        with (directory / name).open("rb") as stream:
            raw = stream.read(MAX_WHEEL_BYTES + 1)
        if len(raw) > MAX_WHEEL_BYTES or _digest(raw) != expected:
            raise ValueError(f"SARIF reader wheel does not match its reviewed pin: {name}")
        hashes[name] = expected
    return {"name": "sarif-tools", "version": "3.0.5", "wheels": hashes,
            "python_executable_sha256": _digest(Path(sys.executable).read_bytes()),
            "python": sys.version, "mode": "isolated-wheel-zip-import-pure-python"}


def harness_identity() -> str:
    root = Path(__file__).resolve().parent
    identities = {name: _digest((root / name).read_bytes())
                  for name in ("sarif.py", "sarif_reader.py", "cli/vela.py")}
    return _digest(json.dumps(identities, sort_keys=True).encode())


def check_current(directory: Path, report: sarif.Object) -> None:
    if reader_identity(directory) != report["reader"] or harness_identity() != report["harness_sha256"]:
        raise ValueError("SARIF reader or qualification harness changed before publication")


def _read(directory: Path, document: sarif.Object) -> sarif.Object:
    paths = [str((directory / name).resolve()) for name in WHEEL_PINS]
    script = (
        "import sys,json; sys.path[:0]=json.loads(sys.argv[1]); "
        "from sarif.loader import load_sarif_file; "
        "f=load_sarif_file(sys.argv[2]); "
        "print(json.dumps({'records':[r for run in f.runs for r in run.get_records()],"
        "'results':[r for run in f.runs for r in run.get_results()],"
        "'invocations':[i for run in f.runs for i in run.run_data['invocations']]},sort_keys=True))"
    )
    with tempfile.TemporaryDirectory(prefix="vela-sarif-reader-") as temporary:
        path = Path(temporary) / "fixture.sarif"
        path.write_text(json.dumps(document), encoding="utf-8")
        try:
            done = subprocess.run([sys.executable, "-I", "-c", script, json.dumps(paths), str(path)],
                                  stdin=subprocess.DEVNULL, capture_output=True, check=False,
                                  timeout=READER_SECONDS)
        except subprocess.SubprocessError as error:
            raise ValueError("independent SARIF reader exceeded its process bound") from error
    if (done.returncode != 0 or len(done.stdout) > MAX_READER_OUTPUT
            or len(done.stderr) > MAX_READER_OUTPUT):
        raise ValueError("independent SARIF reader failed or exceeded output bounds")
    result = sarif.decode(done.stdout)
    result["stderr"] = done.stderr.decode("utf-8")
    return result


def _rebind(document: sarif.Object) -> None:
    manifest = cast("sarif.Object", cast("sarif.Object", cast("list[sarif.Object]", document["runs"])[0]["properties"])["vela"])
    manifest.pop("binding_sha256", None)
    manifest["binding_sha256"] = _digest(json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii"))


def _controls(document: sarif.Object, producer: str, schema: Path) -> list[str]:
    refused: list[str] = []
    for name in NEGATIVE_CONTROLS:
        changed = json.loads(json.dumps(document))
        inputs, current_producer = (FIRST, SECOND), producer
        run = changed["runs"][0]
        if name == "stale-source":
            inputs = (sarif.Input(FIRST.uri, FIRST.source + b" "), SECOND)
        elif name == "stale-producer":
            current_producer = "b" * 64
        elif name == "source-location":
            run["results"][1]["locations"][0]["physicalLocation"]["region"]["startColumn"] = 999
        elif name == "rule-reference":
            run["results"][1]["ruleIndex"] = 999
        elif name == "completion-status":
            run["invocations"][0]["executionSuccessful"] = False
        elif name == "missing-finding":
            run["results"].pop()
        elif name == "fix-range":
            run["results"][0]["fixes"][0]["artifactChanges"][0]["replacements"][0]["deletedRegion"]["byteLength"] -= 1
        else:
            run["results"][0]["message"]["text"] = "changed after export"
        if name != "report-corruption":
            _rebind(changed)
        try:
            sarif.validate(changed, inputs, current_producer, schema_path=schema)
        except ValueError:
            refused.append(name)
        else:
            raise ValueError(f"SARIF handoff accepted negative control: {name}")
    return refused


def qualify(directory: Path, schema: Path) -> sarif.Object:
    """Run real producers and independently expected records, coordinates and fix application."""
    reader = reader_identity(directory)
    harness = harness_identity()
    producer = compiler_trace.producer_identity()
    document = sarif.export((FIRST, SECOND), producer, format_fixes=True)
    sarif.validate(document, (FIRST, SECOND), producer, schema_path=schema)
    observed = _read(directory, document)
    records = cast("list[sarif.Object]", observed["records"])
    projection = [[record["Code"], record["Severity"], record["Location"], record["Line"]]
                  for record in records]
    expected = [["VELA-FORMAT", "warning", FIRST.uri, 1],
                ["VELA-TYPE", "error", SECOND.uri, 3]]
    if projection != expected:
        raise ValueError(f"independent SARIF records differ: {projection!r}")
    results = json.loads(json.dumps(observed["results"]))
    physical = results[1]["locations"][0]["physicalLocation"]
    if physical != {"artifactLocation": {"uri": SECOND.uri, "index": 1},
                    "region": {"startLine": 3, "startColumn": 23}}:
        raise ValueError(f"independent SARIF type-error location differs: {physical!r}")
    replacement = results[0]["fixes"][0]["artifactChanges"][0]["replacements"][0]
    offset = replacement["deletedRegion"]["byteOffset"]
    end = offset + replacement["deletedRegion"]["byteLength"]
    applied = FIRST.source[:offset] + replacement["insertedContent"]["text"].encode() + FIRST.source[end:]
    if applied != EXPECTED_FORMATTED.encode():
        raise ValueError(f"independent SARIF format edit differs: {applied!r}")
    unfinished = sarif.export((UNSUPPORTED,), producer)
    incomplete = sarif.validate(unfinished, (UNSUPPORTED,), producer, schema_path=schema)
    observed_unfinished = json.loads(json.dumps(_read(directory, unfinished)))
    if incomplete["complete"] is not False or observed_unfinished["invocations"][0]["executionSuccessful"] is not False:
        raise ValueError("unsupported source lost its incomplete-analysis status")
    corrupted = json.loads(json.dumps(unfinished))
    corrupted["runs"][0]["properties"]["vela"]["complete"] = True
    _rebind(corrupted)
    try:
        sarif.validate(corrupted, (UNSUPPORTED,), producer, schema_path=schema)
    except ValueError:
        pass
    else:
        raise ValueError("unfinished source was accepted as complete")
    report: sarif.Object = {
        "schema": 1, "scope": sarif.SCOPE, "accepted": True,
        "reader": reader, "harness_sha256": harness, "producer_sha256": producer,
        "schema_sha256": sarif.SCHEMA_SHA256, "observed": observed,
        "observed_unfinished": observed_unfinished, "expected_records": expected,
        "expected_formatted_sha256": _digest(EXPECTED_FORMATTED.encode()),
        "negative_controls": [*_controls(document, producer, schema), "unfinished-status-corruption"],
        "fixture_inputs": [{"uri": item.uri, "sha256": _digest(item.source)}
                           for item in (FIRST, SECOND, UNSUPPORTED)]}
    check_current(directory, report)
    sarif.check_schema_current(schema)
    if compiler_trace.producer_identity() != producer:
        raise ValueError("SARIF producer changed during qualification")
    return report
