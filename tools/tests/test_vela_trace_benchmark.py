# SPDX-License-Identifier: Apache-2.0
"""Paired trace overhead measurements, report integrity and publication controls."""

import copy
import hashlib
import json
import tempfile
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import Translation, VelaError, compiler_trace
from toolchain import trace_benchmark as benchmark
from toolchain.cli import vela as cli

INDEPENDENT_CASES = True
SOURCE = b"module Timed; public Nat Twice(Nat x) => x + x;"
PRODUCER = "a" * 64


def _compile(source: bytes, *, trace: compiler_trace.Recorder | None = None) -> Translation:
    if trace is not None:
        with trace.span("compile"):
            trace.counter("source_bytes", len(source))
            with trace.span("parse"):
                with trace.span("checked-parse"):
                    pass
                with trace.span("syntax-decode"):
                    pass
            with trace.span("elaborate-and-emit"):
                pass
            trace.counter("gallina_bytes", 6)
    return Translation("Timed", "output")


def _fixture(durations: tuple[int, ...] = (10, 40, 50, 20, 30, 60, 70, 40), *,
             warmups: int = 1) -> benchmark.Object:
    readings: list[int] = []
    current = 0
    for duration in durations:
        readings.extend((current, current + duration))
        current += duration + 1
    ticks = iter(readings)
    with patch.object(benchmark, "translate", side_effect=_compile):
        return benchmark.measure(SOURCE, PRODUCER, samples=len(durations) // 2 - warmups,
                                 warmups=warmups, clock=ticks.__next__)


def _bind(report: benchmark.Object) -> None:
    report.pop("binding_sha256", None)
    report["binding_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()


def _refuses(report: object, *, source: bytes = SOURCE, producer: str = PRODUCER) -> None:
    try:
        benchmark.validate(report, source, producer)
    except ValueError:
        return
    raise AssertionError("accepted a stale or inconsistent tracing comparison")


def _paired_timings() -> None:
    order: list[str] = []
    def compile_and_record(source: bytes, *, trace: compiler_trace.Recorder | None = None) -> Translation:
        order.append("traced" if trace is not None else "plain")
        return _compile(source, trace=trace)
    ticks = iter(range(16))
    with patch.object(benchmark, "translate", side_effect=compile_and_record):
        benchmark.measure(SOURCE, PRODUCER, samples=3, warmups=1, clock=ticks.__next__)
    ensure(order == ["plain", "traced", "traced", "plain", "plain", "traced", "traced", "plain"],
           "warmups or measurement pairs did not alternate")
    report = _fixture()
    benchmark.validate(report, SOURCE, PRODUCER)
    pairs = cast("list[benchmark.Object]", report["pairs"])
    ensure([(pair["plain_ns"], pair["traced_ns"]) for pair in pairs]
           == [(20, 50), (30, 60), (40, 70)], "warmup leaked into raw measurements")
    # Expected arithmetic is chosen independently of the measurement implementation.
    ensure(report["summary"] == {
        "plain": {"total_ns": 90, "min_ns": 20, "max_ns": 40, "median_ns": 30},
        "traced": {"total_ns": 180, "min_ns": 50, "max_ns": 70, "median_ns": 60},
        "elapsed_delta_ns": 90, "overhead_ppm": 1_000_000}, "paired summary differs")
    for durations, delta, ppm in (((0, 0), 0, None), ((40, 10), -30, -750_000)):
        summary = cast("benchmark.Object", _fixture(durations, warmups=0)["summary"])
        ensure(summary["elapsed_delta_ns"] == delta and summary["overhead_ppm"] == ppm,
               "zero baseline or negative measured overhead was misrepresented")


def _report_integrity() -> None:
    report = _fixture()
    _refuses(report, source=SOURCE + b" ")
    _refuses(report, producer="b" * 64)
    for field, value in (("warmups", True), ("samples", 4), ("samples", benchmark.MAX_SAMPLES + 1),
                         ("clock", "time"), ("scope", "program-timing"), ("gallina_sha256", "bad")):
        changed = copy.deepcopy(report)
        changed[field] = value
        _bind(changed)
        _refuses(changed)
    changed = copy.deepcopy(report)
    cast("benchmark.Object", changed["summary"])["elapsed_delta_ns"] = 1
    _refuses(changed)
    _bind(changed)
    _refuses(changed)
    for field, value in (("plain_ns", -1), ("traced_ns", True), ("recording_overhead_ns", 1.5),
                         ("first", "plain")):
        changed = copy.deepcopy(report)
        cast("list[benchmark.Object]", changed["pairs"])[0][field] = value
        _bind(changed)
        _refuses(changed)
    changed = copy.deepcopy(report)
    changed["pairs"] = [None] * 3
    _bind(changed)
    _refuses(changed)
    ensure(benchmark.decode(json.dumps(report).encode()) == report, "benchmark decoding changed report")
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b"[" * 20 + b"0" + b"]" * 20,
                b" " * (benchmark.MAX_REPORT_BYTES + 1)):
        try:
            benchmark.decode(raw)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed or unbounded report decoded")


def _limits_and_failures() -> None:
    with patch.object(benchmark, "translate", side_effect=_compile) as compile_mock:
        for samples, warmups in ((0, 0), (True, 0), (benchmark.MAX_SAMPLES + 1, 0),
                                 (1, -1), (1, True), (1, benchmark.MAX_WARMUPS + 1)):
            try:
                benchmark.measure(SOURCE, PRODUCER, samples=samples, warmups=warmups)
            except ValueError:
                pass
            else:
                raise AssertionError("unbounded benchmark configuration accepted")
        ensure(not compile_mock.called, "invalid limits invoked the compiler")
        for readings in ((-1,), (True,), (0.5,), (10, 9), (0, compiler_trace.MAX_TIME + 1)):
            ticks = iter(readings)
            try:
                benchmark.measure(SOURCE, PRODUCER, samples=1, warmups=0,
                                  clock=cast("Callable[[], int]", ticks.__next__))
            except ValueError:
                pass
            else:
                raise AssertionError("invalid benchmark clock accepted")
    def changed_output(source: bytes, *, trace: compiler_trace.Recorder | None = None) -> Translation:
        result = _compile(source, trace=trace)
        return result if trace is None else Translation("Timed", "different")
    with patch.object(benchmark, "translate", side_effect=changed_output):
        try:
            benchmark.measure(SOURCE, PRODUCER, samples=1, warmups=0)
        except ValueError as error:
            ensure("changed emitted output" in str(error), "wrong output mismatch refusal")
        else:
            raise AssertionError("instrumentation changed emitted terms without refusal")
    recorder = compiler_trace.Recorder(max_events=2)
    with patch.object(benchmark, "translate", side_effect=_compile), \
            patch.object(compiler_trace, "Recorder", return_value=recorder):
        try:
            benchmark.measure(SOURCE, PRODUCER, samples=1, warmups=0)
        except ValueError as error:
            ensure("incomplete" in str(error), "wrong incomplete recording refusal")
        else:
            raise AssertionError("truncated recording produced an accepted comparison")


def _command_publication() -> None:
    report = _fixture()
    with tempfile.TemporaryDirectory(prefix="vela-trace-benchmark-") as directory:
        source, output = Path(directory) / "source.vela", Path(directory) / "comparison.json"
        source.write_bytes(SOURCE)
        def run(*args: str) -> int:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return cli.main(list(args))
        arguments = ("trace-benchmark", str(source), "--output", str(output), "--samples", "3")
        with patch.object(compiler_trace, "producer_identity", return_value=PRODUCER), \
                patch.object(benchmark, "measure", return_value=report):
            ensure(run(*arguments) == 0, "benchmark command failed")
            ensure(run("trace-benchmark-validate", str(output), "--source", str(source)) == 0,
                   "benchmark validation command failed")
            previous = output.read_bytes()
            ensure(source.read_bytes() == SOURCE, "benchmark command changed source")
            ensure(run("trace-benchmark", str(source), "--output", str(source)) == 1,
                   "benchmark overwrote its input")
            with patch.object(compiler_trace, "producer_identity", side_effect=[PRODUCER, PRODUCER, "b" * 64]):
                ensure(run(*arguments) == 1, "late producer change published stale measurement")
            ensure(output.read_bytes() == previous, "late failure replaced report")
            for failure in (ValueError("bad clock"), VelaError("unsupported", 1, 1, "refused source"), KeyboardInterrupt()):
                with patch.object(benchmark, "measure", side_effect=failure):
                    try:
                        status = run(*arguments)
                    except KeyboardInterrupt:
                        ensure(isinstance(failure, KeyboardInterrupt), "unexpected cancellation")
                    else:
                        ensure(status == 1, "failed measurement claimed success")
                ensure(output.read_bytes() == previous, "failed or cancelled measurement replaced report")
            source.write_bytes(SOURCE + b" ")
            ensure(run("trace-benchmark-validate", str(output), "--source", str(source)) == 1,
                   "stale source measurement validated")


def _real_compiler() -> None:
    report = benchmark.measure(SOURCE, PRODUCER, samples=2, warmups=0)
    benchmark.validate(report, SOURCE, PRODUCER)
    ensure(len(cast("list[object]", report["pairs"])) == 2, "real compilation lost samples")


def cases() -> list[Case]:
    return [Case("alternating-pairs-warmups-and-independent-arithmetic", _paired_timings),
            Case("bound-raw-samples-and-recomputed-summaries", _report_integrity),
            Case("bounded-work-clocks-and-output-equivalence", _limits_and_failures),
            Case("atomic-read-only-publication-and-cancellation", _command_publication),
            Case("real-pure-compiler-comparison", _real_compiler)]
