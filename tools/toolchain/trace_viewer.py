# SPDX-License-Identifier: Apache-2.0
"""Offline qualification of a pinned independent Perfetto trace importer."""

import copy
import csv
import hashlib
import json
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from typing import cast

from toolchain import compiler_trace as trace

RELEASE = "v58.2"
REVISION = "add693d8b338ba9599dbcbc3e300b1ab8c000897"
PINS = {
    "windows-amd64": "adfa6bad3d72be3ba9b83fa2b17b69fa13b3ab1cad0f42e52b86188bd5f0f997",
    "linux-amd64": "58042408e6cc861fb1a731c26bb082dc222285561eaa4e12a48a8b2b90dca7b9",
    "linux-arm64": "0e6e0c5452c505c8d46fe472fd196a0d17d963460727e2ce2013b02aa1309555",
}
MAX_READER_BYTES = 20_000_000
MAX_OUTPUT_BYTES = 65_536
MAX_REPORT_BYTES = 524_288
TIMEOUT_SECONDS = 30
SOURCE = b"module Timed; public Nat Twice(Nat x) => x + x;"
FIXTURE_PRODUCER = "a" * 64
SLICES_SQL = (
    "SELECT s.name, s.ts, s.dur, s.depth, t.tid, p.pid FROM slice s "
    "JOIN thread_track tt ON tt.id = s.track_id JOIN thread t ON t.utid = tt.utid "
    "JOIN process p ON p.upid = t.upid ORDER BY s.ts, s.depth"
)
COUNTERS_SQL = (
    "SELECT t.name, c.ts, CAST(c.value AS INT) AS value FROM counter c "
    "JOIN counter_track t ON t.id = c.track_id ORDER BY c.ts, t.name"
)
EXPECTED_SLICES = [
    ["name", "ts", "dur", "depth", "tid", "pid"],
    ["compile", "0", "9000", "0", "1", "1"],
    ["parse", "2000", "1000", "1", "1", "1"],
    ["elaborate-and-emit", "4000", "3000", "1", "1", "1"],
    ["declaration", "5000", "1000", "2", "1", "1"],
]
EXPECTED_COUNTERS = [
    ["name", "ts", "value"],
    ["source_bytes bytes", "1000", "47"],
    ["gallina_bytes bytes", "8000", "48"],
]
NEGATIVE_CONTROLS = ("stale-source", "stale-producer", "missing-phase", "crossing-span",
                     "negative-timestamp", "dropped-events", "cancelled")
type Object = dict[str, object]


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def reader_identity(executable: Path) -> Object:
    """Refuse unreviewed bytes before executing the externally provisioned reader."""
    with executable.open("rb") as stream:
        raw = stream.read(MAX_READER_BYTES + 1)
    if len(raw) > MAX_READER_BYTES:
        raise ValueError("trace reader exceeds executable byte limit")
    digest = hashlib.sha256(raw).hexdigest()
    for target, expected in PINS.items():
        if digest == expected:
            return {"release": RELEASE, "revision": REVISION, "target": target, "sha256": digest}
    raise ValueError("trace reader does not match a pinned Perfetto executable")


def harness_identity() -> str:
    root = Path(__file__).resolve().parent
    return _digest({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    for name in ("compiler_trace.py", "trace_viewer.py", "cli/vela.py")})


def check_current(executable: Path, report: Object) -> None:
    if (reader_identity(executable) != report["reader"]
            or harness_identity() != report["harness_sha256"]):
        raise ValueError("reader or qualification harness changed before publication")


def decode(raw: bytes) -> Object:
    """Decode a bounded retained receipt, refusing duplicates and deep objects."""
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("trace viewer report exceeds byte limit")
    return trace.decode(raw)


def _transcript(value: object) -> Object:
    if not isinstance(value, dict) or set(value) != {"stdout", "stderr", "returncode"}:
        raise ValueError("invalid retained reader transcript")
    transcript = cast("Object", value)
    if type(transcript["returncode"]) is not int or transcript["returncode"] != 0:
        raise ValueError("retained reader did not complete successfully")
    for field in ("stdout", "stderr"):
        output = transcript[field]
        if not isinstance(output, str) or len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ValueError("invalid or oversized retained reader output")
    return transcript


def validate(document: object, executable: Path) -> Object:
    """Recheck retained observations and current identities without rerunning a reader.

    These checks detect stale or inconsistent data and authenticate no transcript.
    A fresh external observation still requires the qualification command.
    """
    fields = {"schema", "scope", "accepted", "reader", "harness_sha256", "version", "trace",
              "source", "producer_sha256", "negative_controls", "queries", "binding_sha256"}
    if (not isinstance(document, dict) or set(document) != fields
            or len(json.dumps(document).encode("utf-8")) > MAX_REPORT_BYTES):
        raise ValueError("unsupported or oversized trace viewer report")
    report = cast("Object", document)
    unsigned = {key: value for key, value in report.items() if key != "binding_sha256"}
    if report["binding_sha256"] != _digest(unsigned):
        raise ValueError("trace viewer report binding mismatch")
    if (type(report["schema"]) is not int or report["schema"] != 1
            or report["scope"] != "pure-trace-independent-importer" or report["accepted"] is not True
            or report["source"] != SOURCE.decode("ascii")
            or report["producer_sha256"] != FIXTURE_PRODUCER):
        raise ValueError("unsupported trace viewer qualification subject or outcome")
    check_current(executable, report)
    trace.validate(report["trace"], SOURCE, FIXTURE_PRODUCER)
    fixture = cast("Object", report["trace"])
    if (fixture["traceEvents"] != _fixture()["traceEvents"]
            or report["negative_controls"] != list(NEGATIVE_CONTROLS)
            or _negative_controls(fixture) != list(NEGATIVE_CONTROLS)):
        raise ValueError("retained fixture or negative controls disagree with qualification")
    version = _transcript(report["version"])
    if f"Perfetto {RELEASE}-add693d8b ({REVISION})" not in cast("str", version["stdout"]):
        raise ValueError("retained reader version disagrees with its pinned release")
    queries = report["queries"]
    if not isinstance(queries, dict) or set(queries) != {"slices", "counters"}:
        raise ValueError("invalid retained reader queries")
    for name, sql, expected in (("slices", SLICES_SQL, EXPECTED_SLICES),
                                 ("counters", COUNTERS_SQL, EXPECTED_COUNTERS)):
        query = queries[name]
        if (not isinstance(query, dict) or set(query) != {"sql", "transcript", "rows"}
                or query["sql"] != sql or query["rows"] != expected
                or _rows(_transcript(query["transcript"])) != expected):
            raise ValueError("retained reader disagrees with expected query observations")
    check_current(executable, report)
    return report


def _fixture() -> Object:
    ticks = iter(range(1_000_000, 1_020_000, 1000))
    recorder = trace.Recorder(clock=ticks.__next__)
    with recorder.span("compile"):
        recorder.counter("source_bytes", len(SOURCE))
        with recorder.span("parse"):
            pass
        with recorder.span("elaborate-and-emit"), recorder.declaration("Twice", "function", 1, 26):
            pass
        recorder.counter("gallina_bytes", 48)
    return recorder.export(SOURCE, FIXTURE_PRODUCER, outcome="success")


def _negative_controls(document: Object) -> list[str]:
    refused: list[str] = []
    for name in NEGATIVE_CONTROLS:
        changed = copy.deepcopy(document)
        manifest = cast("Object", changed["vela"])
        events = cast("list[Object]", changed["traceEvents"])
        source, producer = SOURCE, FIXTURE_PRODUCER
        if name == "stale-source":
            source += b" "
        elif name == "stale-producer":
            producer = "b" * 64
        elif name == "missing-phase":
            events[2]["name"] = "elaborate-and-emit"
        elif name == "crossing-span":
            events[2]["dur"] = 100
        elif name == "negative-timestamp":
            events[2]["ts"] = -1
        elif name == "dropped-events":
            manifest.update(dropped_events=1, complete=False)
        else:
            manifest.update(outcome="cancelled", complete=False)
        manifest.pop("binding_sha256")
        manifest["binding_sha256"] = _digest(changed)
        try:
            trace.validate(changed, source, producer)
        except ValueError:
            refused.append(name)
        else:
            raise ValueError(f"trace handoff accepted negative control: {name}")
    return refused


def _run(executable: Path, arguments: list[str]) -> Object:
    try:
        result = subprocess.run([str(executable), *arguments], stdin=subprocess.DEVNULL,
                                capture_output=True, check=False, timeout=TIMEOUT_SECONDS)
    except subprocess.SubprocessError as error:
        raise ValueError("independent trace reader timed out or could not finish") from error
    if (result.returncode or len(result.stdout) > MAX_OUTPUT_BYTES
            or len(result.stderr) > MAX_OUTPUT_BYTES):
        raise ValueError("independent trace reader failed or exceeded output bounds")
    return {"stdout": result.stdout.decode("utf-8", errors="strict"),
            "stderr": result.stderr.decode("utf-8", errors="strict"), "returncode": result.returncode}


def _rows(transcript: Object) -> list[list[str]]:
    try:
        return list(csv.reader(StringIO(cast("str", transcript["stdout"])), strict=True))
    except csv.Error as error:
        raise ValueError("malformed independent reader CSV") from error


def qualify(executable: Path) -> Object:
    """Compare independently chosen nanosecond rows with an actual external importer.

    The command accepts an existing pinned binary and performs no downloads. Only
    a completely validated deterministic fixture reaches the external reader.
    """
    executable = executable.resolve(strict=True)
    reader, harness = reader_identity(executable), harness_identity()
    document = _fixture()
    trace.validate(document, SOURCE, FIXTURE_PRODUCER)
    refused = _negative_controls(document)
    version = _run(executable, ["--version"])
    if f"Perfetto {RELEASE}-add693d8b ({REVISION})" not in cast("str", version["stdout"]):
        raise ValueError("independent reader version disagrees with its pinned release")
    with tempfile.TemporaryDirectory(prefix="vela-trace-viewer-") as temporary:
        fixture = Path(temporary) / "fixture.json"
        fixture.write_text(json.dumps(document), encoding="utf-8")
        slices = _run(executable, ["query", str(fixture), SLICES_SQL])
        counters = _run(executable, ["query", str(fixture), COUNTERS_SQL])
    slice_rows, counter_rows = _rows(slices), _rows(counters)
    if slice_rows != EXPECTED_SLICES or counter_rows != EXPECTED_COUNTERS:
        raise ValueError("independent reader disagrees with expected spans, nesting, workers or counters")
    if reader_identity(executable) != reader or harness_identity() != harness:
        raise ValueError("reader or qualification harness changed during qualification")
    report: Object = {
        "schema": 1, "scope": "pure-trace-independent-importer", "accepted": True,
        "reader": reader, "harness_sha256": harness, "version": version,
        "trace": document, "source": SOURCE.decode("ascii"), "producer_sha256": FIXTURE_PRODUCER,
        "negative_controls": refused,
        "queries": {"slices": {"sql": SLICES_SQL, "transcript": slices, "rows": slice_rows},
                    "counters": {"sql": COUNTERS_SQL, "transcript": counters, "rows": counter_rows}},
    }
    report["binding_sha256"] = _digest(report)
    return report
