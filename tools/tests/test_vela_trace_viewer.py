# SPDX-License-Identifier: Apache-2.0
"""Independent importer observations, wrong-reader controls and atomic evidence."""

import copy
import hashlib
import json
import subprocess
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import trace_viewer as viewer
from toolchain.cli import vela as cli

INDEPENDENT_CASES = True
READER_BYTES = b"test reader fixture"
DIGEST = hashlib.sha256(READER_BYTES).hexdigest()


def _reader(path: Path, arguments: list[str]) -> viewer.Object:
    ensure(path.read_bytes() == READER_BYTES, "qualification launched another reader")
    if arguments == ["--version"]:
        output = f"Perfetto v58.2-add693d8b ({viewer.REVISION})\nTrace Processor RPC API version: 14\n"
    else:
        ensure(arguments[0] == "query" and len(arguments) == 3, "unexpected reader arguments")
        document = json.loads(Path(arguments[1]).read_text(encoding="utf-8"))
        ensure(document["vela"]["complete"] is True and len(document["traceEvents"]) == 8,
               "an incomplete or negative fixture reached the reader")
        if "FROM slice s" in arguments[2]:
            output = ('"name","ts","dur","depth","tid","pid"\n'
                      '"compile",0,13000,0,1,1\n"parse",2000,5000,1,1,1\n'
                      '"checked-parse",3000,1000,2,1,1\n"syntax-decode",5000,1000,2,1,1\n"elaborate-and-emit",8000,3000,1,1,1\n'
                      '"declaration",9000,1000,2,1,1\n')
        else:
            ensure("FROM counter c" in arguments[2], "unexpected SQL query")
            output = '"name","ts","value"\n"source_bytes bytes",1000,47\n"gallina_bytes bytes",12000,48\n'
    return {"stdout": output, "stderr": "reader diagnostic\n", "returncode": 0}


def _independent_observations() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-viewer-test-") as directory:
        binary = Path(directory) / "reader"
        binary.write_bytes(READER_BYTES)
        with patch.object(viewer, "PINS", {"test": DIGEST}), \
                patch.object(viewer, "_run", side_effect=_reader) as launch:
            report = viewer.qualify(binary)
        ensure(launch.call_count == 3, "negative controls were sent to the external reader")
        ensure(report["accepted"] is True and cast("viewer.Object", report["reader"])["sha256"] == DIGEST,
               "report lost accepted reader identity")
        queries = cast("dict[str, viewer.Object]", report["queries"])
        slices = cast("list[list[str]]", queries["slices"]["rows"])
        ensure(slices[2] == ["parse", "2000", "5000", "1", "1", "1"],
               "independent nanosecond, nesting or worker observations changed")
        ensure(report["negative_controls"] == ["stale-source", "stale-producer", "missing-phase",
                                               "crossing-span", "negative-timestamp", "dropped-events", "cancelled"],
               "negative handoff controls were omitted")
        unsigned = {key: value for key, value in report.items() if key != "binding_sha256"}
        expected = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
        ensure(report["binding_sha256"] == expected, "report does not bind exact retained observations")


def _wrong_results_and_late_changes() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-viewer-test-") as directory:
        binary = Path(directory) / "reader"
        binary.write_bytes(READER_BYTES)
        with patch.object(viewer, "PINS", {"test": DIGEST}):
            for field in ("duration", "worker", "nesting", "counter", "version"):
                def wrong(path: Path, arguments: list[str], chosen: str = field) -> viewer.Object:
                    result = _reader(path, arguments)
                    output = cast("str", result["stdout"])
                    replacements = {"duration": ("13000", "13001"), "worker": ("0,1,1", "0,2,1"),
                                    "nesting": ("5000,1,1,1", "5000,0,1,1"),
                                    "counter": ("12000,48", "12000,49"), "version": ("v58.2", "v58.1")}
                    before, after = replacements[chosen]
                    result["stdout"] = output.replace(before, after)
                    return result
                with patch.object(viewer, "_run", side_effect=wrong):
                    try:
                        viewer.qualify(binary)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f"wrong independent {field} accepted")
            with patch.object(viewer, "_run", side_effect=_reader), \
                    patch.object(viewer, "harness_identity", side_effect=["a" * 64, "b" * 64]):
                try:
                    viewer.qualify(binary)
                except ValueError:
                    pass
                else:
                    raise AssertionError("changed harness retained qualification")
        with patch.object(viewer, "_run") as launch:
            try:
                viewer.qualify(binary)
            except ValueError:
                pass
            else:
                raise AssertionError("unreviewed reader bytes executed")
            ensure(not launch.called, "unreviewed reader reached execution")


def _negative_gate_failure() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-viewer-test-") as directory:
        binary = Path(directory) / "reader"
        binary.write_bytes(READER_BYTES)
        with patch.object(viewer, "PINS", {"test": DIGEST}), \
                patch.object(viewer.trace, "validate", return_value={}), \
                patch.object(viewer, "_run") as launch:
            try:
                viewer.qualify(binary)
            except ValueError as error:
                ensure("negative control" in str(error), "negative gate failure lost its cause")
            else:
                raise AssertionError("disabled completeness gate qualified")
            ensure(not launch.called, "failed controls reached importer")


def _bounded_reader_failures() -> None:
    for result in (subprocess.CompletedProcess([], 1, b"", b"reader failed"),
                   subprocess.CompletedProcess([], 0, b"x" * (viewer.MAX_OUTPUT_BYTES + 1), b""),
                   subprocess.CompletedProcess([], 0, b"", b"x" * (viewer.MAX_OUTPUT_BYTES + 1))):
        with patch.object(viewer.subprocess, "run", return_value=result):
            try:
                viewer._run(Path("reader"), ["--version"])
            except ValueError:
                pass
            else:
                raise AssertionError("failed or unbounded reader output accepted")
    with patch.object(viewer.subprocess, "run", side_effect=subprocess.TimeoutExpired("reader", 30)):
        try:
            viewer._run(Path("reader"), ["--version"])
        except ValueError:
            pass
        else:
            raise AssertionError("reader timeout lost")


def _publication() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-viewer-test-") as directory:
        binary, output = Path(directory) / "reader", Path(directory) / "report.json"
        binary.write_bytes(READER_BYTES)
        output.write_bytes(b"previous evidence")
        def command(destination: Path) -> int:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return cli.main(["trace-qualify-viewer", "--trace-processor", str(binary),
                                 "--output", str(destination)])
        with patch.object(viewer, "PINS", {"test": DIGEST}), patch.object(viewer, "_run", side_effect=_reader):
            ensure(command(output) == 0, "qualified evidence was not published")
            previous = output.read_bytes()
            ensure(json.loads(previous)["accepted"] is True, "published evidence is incomplete")
            ensure(command(binary) == 1 and binary.read_bytes() == READER_BYTES, "output overwrote reader")
            with patch.object(viewer, "harness_identity", side_effect=["a" * 64, "a" * 64, "b" * 64]):
                ensure(command(output) == 1, "late harness mutation published evidence")
            ensure(output.read_bytes() == previous, "late mutation replaced existing evidence")
            with patch.object(viewer, "qualify", side_effect=KeyboardInterrupt):
                try:
                    command(output)
                except KeyboardInterrupt:
                    pass
                else:
                    raise AssertionError("cancellation was hidden")
            ensure(output.read_bytes() == previous, "cancelled qualification replaced evidence")


def _bind(report: viewer.Object) -> None:
    unsigned = {key: value for key, value in report.items() if key != "binding_sha256"}
    report["binding_sha256"] = hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()


def _retained_observations() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-viewer-retained-") as directory:
        binary, receipt = Path(directory) / "reader", Path(directory) / "receipt.json"
        binary.write_bytes(READER_BYTES)
        with patch.object(viewer, "PINS", {"test": DIGEST}):
            with patch.object(viewer, "_run", side_effect=_reader):
                report = viewer.qualify(binary)
            with patch.object(viewer, "_run", side_effect=AssertionError("offline validation executed reader")):
                ensure(viewer.validate(report, binary) == report, "retained receipt did not validate")
                receipt.write_text(json.dumps(report), encoding="utf-8")
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    ensure(cli.main(["trace-viewer-validate", str(receipt), "--trace-processor", str(binary)]) == 0,
                           "offline receipt command failed")
                ensure(json.loads(receipt.read_bytes()) == report, "offline command changed evidence")
                for field in ("schema", "scope", "accepted", "source", "producer", "negative", "query",
                              "rows", "csv", "version", "returncode", "transcript", "fixture", "extra"):
                    changed = copy.deepcopy(report)
                    queries = cast("dict[str, viewer.Object]", changed["queries"])
                    if field == "schema":
                        changed["schema"] = True
                    elif field == "scope":
                        changed["scope"] = "another qualification"
                    elif field == "accepted":
                        changed["accepted"] = False
                    elif field == "source":
                        changed["source"] = str(changed["source"]) + " "
                    elif field == "producer":
                        changed["producer_sha256"] = "b" * 64
                    elif field == "negative":
                        changed["negative_controls"] = list(viewer.NEGATIVE_CONTROLS[:-1])
                    elif field == "query":
                        queries["slices"]["sql"] = "SELECT 1"
                    elif field == "rows":
                        cast("list[list[str]]", queries["slices"]["rows"])[1][2] = "9001"
                    elif field == "csv":
                        cast("viewer.Object", queries["counters"]["transcript"])["stdout"] = (
                            '"name","ts","value"\n"source_bytes bytes",1000,47\n"gallina_bytes bytes",12000,49\n')
                    elif field == "version":
                        cast("viewer.Object", changed["version"])["stdout"] = "Perfetto v58.1"
                    elif field == "returncode":
                        cast("viewer.Object", changed["version"])["returncode"] = False
                    elif field == "transcript":
                        cast("viewer.Object", changed["version"])["stderr"] = "x" * (viewer.MAX_OUTPUT_BYTES + 1)
                    elif field == "fixture":
                        fixture = cast("viewer.Object", changed["trace"])
                        event = cast("list[viewer.Object]", fixture["traceEvents"])[6]
                        cast("viewer.Object", event["args"])["kind"] = "constant"
                        manifest = cast("viewer.Object", fixture["vela"])
                        manifest.pop("binding_sha256")
                        manifest["binding_sha256"] = hashlib.sha256(json.dumps(
                            fixture, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                            allow_nan=False).encode("ascii")).hexdigest()
                    else:
                        changed["extra"] = True
                    _bind(changed)
                    try:
                        viewer.validate(changed, binary)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f"rebound wrong {field} retained qualification")
                with patch.object(viewer, "harness_identity", side_effect=[viewer.harness_identity(), "b" * 64]):
                    try:
                        viewer.validate(report, binary)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("late harness change retained offline qualification")
                binary.write_bytes(b"changed reader")
                try:
                    viewer.validate(report, binary)
                except ValueError:
                    pass
                else:
                    raise AssertionError("stale reader retained offline qualification")


def _bounded_retained_receipts() -> None:
    for raw in (b"{}", b'{"schema":1,"schema":1}', b"[" * 30 + b"0" + b"]" * 30,
                b" " * (viewer.MAX_REPORT_BYTES + 1)):
        try:
            viewer.validate(viewer.decode(raw), Path("reader"))
        except ValueError:
            pass
        else:
            raise AssertionError("malformed or unbounded retained receipt accepted")


def cases() -> list[Case]:
    return [Case("independent-nanosecond-nesting-workers-and-counter-rows", _independent_observations),
            Case("wrong-reader-observations-and-late-identity-refusal", _wrong_results_and_late_changes),
            Case("negative-completeness-controls-precede-handoff", _negative_gate_failure),
            Case("bounded-output-and-reader-timeouts", _bounded_reader_failures),
            Case("atomic-evidence-alias-freshness-and-cancellation", _publication),
            Case("offline-receipts-recheck-independent-observations-and-identities", _retained_observations),
            Case("malformed-and-unbounded-offline-receipts-refuse", _bounded_retained_receipts)]
