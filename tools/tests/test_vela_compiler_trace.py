# SPDX-License-Identifier: Apache-2.0
"""Independent trace timeline, completeness, binding and command controls."""

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

import toolchain as vela
from tests.harness import Case, ensure
from toolchain import compiler_trace as trace
from toolchain import parser as vela_parser
from toolchain import parser_checked
from toolchain.cli import vela as cli

INDEPENDENT_CASES = True
SOURCE = b"module Timed; public Nat Twice(Nat x) => x + x;"
PRODUCER = "a" * 64


def _fixture(*, max_events: int = trace.MAX_EVENTS) -> trace.Object:
    ticks = iter(range(1_000_000, 1_020_000, 1000))
    recorder = trace.Recorder(max_events=max_events, clock=lambda: next(ticks))
    with recorder.span("compile"):
        recorder.counter("source_bytes", len(SOURCE))
        with recorder.span("parse"):
            pass
        with recorder.span("elaborate-and-emit"):
            pass
        recorder.counter("gallina_bytes", 48)
    return recorder.export(SOURCE, PRODUCER, outcome="success")


def _bind(document: trace.Object) -> None:
    manifest = cast("trace.Object", document["vela"])
    manifest.pop("binding_sha256", None)
    manifest["binding_sha256"] = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                   allow_nan=False).encode("ascii")).hexdigest()


def _refuses(document: object, *, source: bytes = SOURCE, producer: str = PRODUCER) -> None:
    try:
        trace.validate(document, source, producer)
    except ValueError:
        return
    raise AssertionError("accepted malformed, stale or incomplete trace")


def _independent_timeline() -> None:
    document = _fixture()
    trace.validate(document, SOURCE, PRODUCER)
    # A separate consumer reads only standard Chrome events, without the recorder or validator.
    decoded = json.loads(json.dumps(document))
    slices = [(event["name"], event["ts"], event["dur"], event["pid"], event["tid"])
              for event in decoded["traceEvents"] if event["ph"] == "X"]
    ensure(slices == [("compile", 0, 7, 1, 1), ("parse", 2, 1, 1, 1),
                      ("elaborate-and-emit", 4, 1, 1, 1)], "independent timeline differs")
    counters = [(event["name"], event["ts"], event["args"]["bytes"])
                for event in decoded["traceEvents"] if event["ph"] == "C"]
    ensure(counters == [("source_bytes", 1, len(SOURCE)), ("gallina_bytes", 6, 48)],
           "independent counter interpretation differs")


def _bindings_and_completeness() -> None:
    document = _fixture()
    _refuses(document, source=SOURCE + b" ")
    _refuses(document, producer="b" * 64)
    changed = copy.deepcopy(document)
    cast("trace.Object", changed["vela"])["outcome"] = "cancelled"
    _refuses(changed)
    for field, value in (("dropped_events", 1), ("incomplete_spans", 1),
                         ("clock_fault", True), ("outcome", "cancelled"), ("outcome", "refused")):
        changed = copy.deepcopy(document)
        manifest = cast("trace.Object", changed["vela"])
        manifest[field] = value
        _bind(changed)
        _refuses(changed)
        manifest["complete"] = False
        _bind(changed)
        trace.validate(changed, SOURCE, PRODUCER, require_complete=False)
        _refuses(changed)
    truncated = _fixture(max_events=2)
    summary = trace.validate(truncated, SOURCE, PRODUCER, require_complete=False)
    ensure(summary["dropped_events"] == 3 and summary["complete"] is False,
           "overflow did not retain its dropped count")
    _refuses(truncated)


def _malformed_timeline() -> None:
    for field, value in (("ts", -1), ("ts", True), ("ts", 1.5), ("ts", trace.MAX_TIME + 1),
                         ("dur", -1), ("dur", 100), ("pid", True), ("tid", 2), ("ph", "B")):
        changed = _fixture()
        events = cast("list[trace.Object]", changed["traceEvents"])
        events[2][field] = value
        _bind(changed)
        _refuses(changed)
    for mutate in ("missing-phase", "missing-counter", "bad-counter", "out-of-order", "extra-field"):
        changed = _fixture()
        events = cast("list[trace.Object]", changed["traceEvents"])
        if mutate == "missing-phase":
            events[2]["name"] = "elaborate-and-emit"
        elif mutate == "missing-counter":
            events.pop()
            cast("trace.Object", changed["vela"])["event_count"] = len(events)
        elif mutate == "bad-counter":
            events[1]["args"] = {"bytes": len(SOURCE) + 1}
        elif mutate == "out-of-order":
            events[3]["ts"] = 1
        else:
            events[2]["unexpected"] = True
        _bind(changed)
        _refuses(changed)


def _clock_and_open_spans() -> None:
    for readings in ((1000, 0), (1000, -1), (1000, True), (900, 100), (0, (trace.MAX_TIME + 1) * 1000)):
        ticks = iter(readings)
        recorder = trace.Recorder(clock=ticks.__next__)
        with recorder.span("compile"):
            pass
        document = recorder.export(SOURCE, PRODUCER, outcome="success")
        ensure(cast("trace.Object", document["vela"])["clock_fault"] is True, "bad clock was hidden")
        _refuses(document)
    ticks = iter((1000, 5000))
    recorder = trace.Recorder(clock=lambda: next(ticks))
    with recorder.span("compile"):
        document = recorder.export(SOURCE, PRODUCER, outcome="success")
    ensure(cast("trace.Object", document["vela"])["incomplete_spans"] == 1, "open span omitted")
    trace.validate(document, SOURCE, PRODUCER, require_complete=False)
    _refuses(document)
    for bound in (0, -1, trace.MAX_EVENTS + 1, True):
        try:
            trace.Recorder(max_events=bound)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid recorder bound accepted")


def _quantized_boundaries() -> None:
    for readings in ((0, 0, 0, 0, 0, 0, 0, 0), (0, 1000, 2000, 3000, 4000, 5000, 6000, 6000)):
        ticks = iter(readings)
        recorder = trace.Recorder(clock=ticks.__next__)
        with recorder.span("compile"):
            recorder.counter("source_bytes", len(SOURCE))
            with recorder.span("parse"):
                pass
            with recorder.span("elaborate-and-emit"):
                pass
            recorder.counter("gallina_bytes", 0)
        trace.validate(recorder.export(SOURCE, PRODUCER, outcome="success"), SOURCE, PRODUCER)


def _bounded_decoder() -> None:
    ensure(trace.decode(json.dumps(_fixture()).encode())["displayTimeUnit"] == "ms", "decode failed")
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.1}',
                b"[" * 20 + b"0" + b"]" * 20, b" " * (trace.MAX_TRACE_BYTES + 1)):
        try:
            trace.decode(raw)
        except ValueError:
            pass
        else:
            raise AssertionError("unbounded or malformed trace decoded")


def _producer_file_freshness() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-trace-producer-") as directory:
        module = Path(directory) / "tools" / "toolchain" / "compiler_trace.py"
        module.parent.mkdir(parents=True)
        module.write_text("first implementation", encoding="utf-8")
        parser = module.parent / "parser" / "parser.mly"
        parser.parent.mkdir()
        parser.write_text("first grammar", encoding="utf-8")
        owners = [module.parents[1] / name for name in (
            "run.py", "pyproject.toml", "uv.lock", "opam/rocq.lock", "opam/sail.lock")]
        for path in owners:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"first dependency owner")
        runtime: trace.Object = {"parser_sha256": "a" * 64}
        with patch.object(trace, "__file__", str(module)), \
                patch.object(trace, "_runtime_identity", return_value=runtime):
            first = trace.producer_identity()
            module.write_text("changed implementation", encoding="utf-8")
            second = trace.producer_identity()
            parser.write_text("changed grammar", encoding="utf-8")
            third = trace.producer_identity()
            ensure(len({first, second, third}) == 3, "producer closure ignores Python or parser inputs")
            previous = third
            for path in owners:
                path.write_bytes(b"changed dependency owner")
                current = trace.producer_identity()
                ensure(current != previous, f"producer closure ignores {path.name}")
                previous = current
            runtime["parser_sha256"] = "b" * 64
            ensure(trace.producer_identity() != previous, "native runtime change retained producer identity")
            owners[0].unlink()
            try:
                trace.producer_identity()
            except OSError:
                pass
            else:
                raise AssertionError("missing dependency owner silently omitted from identity")


def _runtime_executable_identity() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-trace-runtime-") as directory:
        executable = Path(directory) / "python"
        executable.write_bytes(b"first interpreter")
        with patch.object(trace.sys, "executable", str(executable)):
            first = trace._python_identity()
            executable.write_bytes(b"changed interpreter")
            ensure(trace._python_identity() != first, "same-version interpreter bytes omitted")
        parser = Path(directory) / "vela-checked-parser"
        parser.write_bytes(b"native parser")
        digest = hashlib.sha256(parser.read_bytes()).hexdigest()
        compiled = vela_parser.Build(Path(directory), parser, {"generated_sha256": {"vela-parser": digest}})
        with patch.object(parser_checked, "ensure_checked_build", return_value=compiled):
            native = trace._native_runtime_identity()
            ensure(native["parser_sha256"] == digest, "native executable bytes omitted")
            parser.write_bytes(b"changed after build observation")
            try:
                trace._native_runtime_identity()
            except ValueError:
                pass
            else:
                raise AssertionError("late native executable mutation accepted")
        with patch.object(trace.sys, "platform", "win32"):
            result = subprocess.CompletedProcess(["wsl"], 0, json.dumps(native).encode(), b"")
            with patch.object(trace.subprocess, "run", return_value=result) as launch:
                ensure(trace._runtime_identity(Path(directory)) == native, "guest runtime identity differs")
                ensure(launch.call_args.kwargs["cwd"] == Path(directory), "guest identity uses another checkout")
            for raw in (b"{}", b'{"python":{},"parser_sha256":"bad"}',
                        b'{"python":{},"python":{},"parser_sha256":"bad"}', b"[]", b"x" * 8193):
                with patch.object(trace.subprocess, "run", return_value=subprocess.CompletedProcess(["wsl"], 0, raw, b"")):
                    try:
                        trace._runtime_identity(Path(directory))
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("malformed guest identity accepted")


def _compiler_and_command() -> None:
    expected = vela.translate(SOURCE)
    recorder = trace.Recorder()
    ensure(vela.translate(SOURCE, trace=recorder) == expected, "tracing changed emitted terms")
    trace.validate(recorder.export(SOURCE, PRODUCER, outcome="success"), SOURCE, PRODUCER)
    with tempfile.TemporaryDirectory(prefix="vela-trace-") as directory:
        source, output = Path(directory) / "source.vela", Path(directory) / "trace.json"
        source.write_bytes(SOURCE)
        def run(*args: str) -> int:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return cli.main(list(args))
        with patch.object(trace, "producer_identity", return_value=PRODUCER):
            ensure(run("trace", str(source), "--output", str(output)) == 0, "trace command failed")
            ensure(run("trace-validate", str(output), "--source", str(source)) == 0, "trace validation failed")
            ensure(source.read_bytes() == SOURCE, "tracing edited source")
            previous = output.read_bytes()
            with patch.object(trace, "producer_identity", side_effect=[PRODUCER, "b" * 64]):
                ensure(run("trace-validate", str(output), "--source", str(source)) == 1,
                       "producer changed during validation without refusal")
            ensure(run("trace", str(source), "--output", str(source)) == 1, "source alias permitted")
            ensure(run("trace", str(source), "--output", str(output), "--max-events", "0") == 1, "invalid bound permitted")
            ensure(output.read_bytes() == previous, "failed preparation replaced trace")
            with patch.object(trace, "producer_identity", side_effect=[PRODUCER, PRODUCER, "b" * 64]):
                ensure(run("trace", str(source), "--output", str(output)) == 1,
                       "late producer change published a stale recording")
            ensure(output.read_bytes() == previous, "late producer change replaced existing trace")
            source.write_bytes(b"module Bad; public Nat Wrong() => missing;")
            ensure(run("trace", str(source), "--output", str(output)) == 1, "refused source succeeded")
            manifest = trace.validate(trace.decode(output.read_bytes()), source.read_bytes(), PRODUCER,
                                      require_complete=False)
            ensure(manifest["outcome"] == "refused", "failed compilation lost refusal status")
            ensure(run("trace-validate", str(output), "--source", str(source)) == 1, "refused trace appeared complete")


def cases() -> list[Case]:
    return [Case("independent-chrome-timeline", _independent_timeline),
            Case("bound-events-status-and-freshness", _bindings_and_completeness),
            Case("malformed-and-crossing-timeline", _malformed_timeline),
            Case("bad-clocks-and-open-spans", _clock_and_open_spans),
            Case("quantized-zero-spans-and-inclusive-endpoints", _quantized_boundaries),
            Case("bounded-strict-json", _bounded_decoder),
            Case("producer-python-and-parser-freshness", _producer_file_freshness),
            Case("host-and-guest-runtime-executable-identities", _runtime_executable_identity),
            Case("same-compiler-output-and-read-only-command", _compiler_and_command)]
