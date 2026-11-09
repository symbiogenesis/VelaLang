# SPDX-License-Identifier: Apache-2.0
"""Bounded paired measurements of pure compilation with and without tracing."""

import hashlib
import json
import re
import time
from collections.abc import Callable
from typing import cast

from toolchain import Translation, compiler_trace, translate

DEFAULT_SAMPLES = 7
DEFAULT_WARMUPS = 1
MAX_SAMPLES = 31
MAX_WARMUPS = 5
MAX_REPORT_BYTES = 65_536
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
type Object = dict[str, object]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def _limits(samples: object, warmups: object) -> None:
    _require(type(samples) is int and 1 <= samples <= MAX_SAMPLES,
             f"samples must be between 1 and {MAX_SAMPLES}")
    _require(type(warmups) is int and 0 <= warmups <= MAX_WARMUPS,
             f"warmups must be between 0 and {MAX_WARMUPS}")


def _natural(value: object) -> bool:
    return type(value) is int and 0 <= value <= compiler_trace.MAX_TIME


def _statistics(values: list[int]) -> Object:
    ordered = sorted(values)
    return {"total_ns": sum(values), "min_ns": ordered[0], "max_ns": ordered[-1],
            "median_ns": (ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) // 2}


def _summary(pairs: list[Object]) -> Object:
    plain = _statistics([cast("int", pair["plain_ns"]) for pair in pairs])
    traced = _statistics([cast("int", pair["traced_ns"]) for pair in pairs])
    delta = cast("int", traced["total_ns"]) - cast("int", plain["total_ns"])
    total = cast("int", plain["total_ns"])
    return {"plain": plain, "traced": traced, "elapsed_delta_ns": delta,
            "overhead_ppm": delta * 1_000_000 // total if total else None}


def measure(source: bytes, producer: str, *, samples: int = DEFAULT_SAMPLES,
            warmups: int = DEFAULT_WARMUPS,
            clock: Callable[[], int] = time.perf_counter_ns) -> Object:
    """Measure translation only; compare every result and validate every traced run.

    Recorder construction, trace export/validation and report publication lie outside
    each timed interval. Warmups execute both paths and are excluded from summaries.
    """
    _limits(samples, warmups)
    _require(isinstance(producer, str) and _SHA256.fullmatch(producer) is not None,
             "invalid producer identity")
    expected: Translation | None = None
    previous = 0
    pairs: list[Object] = []

    def reading() -> int:
        nonlocal previous
        value = clock()
        _require(type(value) is int and value >= previous, "invalid benchmark clock")
        previous = value
        return value

    for index in range(warmups + samples):
        order = ("plain", "traced") if index % 2 == 0 else ("traced", "plain")
        pair: Object = {"first": order[0]}
        for mode in order:
            recorder = compiler_trace.Recorder() if mode == "traced" else None
            start = reading()
            result = translate(source, trace=recorder)
            elapsed = reading() - start
            _require(_natural(elapsed), "benchmark duration exceeds limit")
            if expected is None:
                expected = result
            _require(result == expected, "tracing or repeated compilation changed emitted output")
            pair[f"{mode}_ns"] = elapsed
            if recorder is not None:
                manifest = compiler_trace.validate(
                    recorder.export(source, producer, outcome="success"), source, producer)
                pair["recording_overhead_ns"] = manifest["recording_overhead_ns"]
        if index >= warmups:
            pairs.append(pair)
    _require(expected is not None, "benchmark produced no output")
    expected = cast("Translation", expected)
    report: Object = {
        "schema": 1, "scope": "pure-compiler-tracing-comparison",
        "clock": "perf_counter_ns", "unit": "nanoseconds",
        "measurement": "warm-process-wall-time-including-parser-wait",
        "order": "alternating-pairs", "samples": samples, "warmups": warmups,
        "source_sha256": hashlib.sha256(source).hexdigest(), "producer_sha256": producer,
        "gallina_sha256": hashlib.sha256(expected.gallina.encode("utf-8")).hexdigest(),
        "pairs": pairs, "summary": _summary(pairs),
    }
    report["binding_sha256"] = _digest(report)
    validate(report, source, producer)
    return report


def validate(document: object, source: bytes, producer: str) -> Object:
    """Check report freshness, bounded samples, order and independently derived totals."""
    _require(isinstance(document, dict), "benchmark report must be an object")
    report = cast("Object", document)
    _require(set(report) == {"schema", "scope", "clock", "unit", "measurement", "order",
                             "samples", "warmups", "source_sha256", "producer_sha256",
                             "gallina_sha256", "pairs", "summary", "binding_sha256"},
             "unsupported benchmark report fields")
    unsigned = {key: value for key, value in report.items() if key != "binding_sha256"}
    _require(report["binding_sha256"] == _digest(unsigned), "benchmark binding mismatch")
    _require(type(report["schema"]) is int and report["schema"] == 1
             and report["scope"] == "pure-compiler-tracing-comparison"
             and report["clock"] == "perf_counter_ns" and report["unit"] == "nanoseconds"
             and report["measurement"] == "warm-process-wall-time-including-parser-wait"
             and report["order"] == "alternating-pairs", "unsupported benchmark schema")
    _require(report["source_sha256"] == hashlib.sha256(source).hexdigest()
             and isinstance(producer, str) and _SHA256.fullmatch(producer) is not None
             and report["producer_sha256"] == producer, "stale benchmark input or producer")
    output = report["gallina_sha256"]
    _require(isinstance(output, str) and _SHA256.fullmatch(output) is not None,
             "invalid output identity")
    _limits(report["samples"], report["warmups"])
    pairs = report["pairs"]
    _require(isinstance(pairs, list) and len(pairs) == report["samples"],
             "benchmark sample count mismatch")
    pairs = cast("list[Object]", pairs)
    for index, pair in enumerate(pairs, cast("int", report["warmups"])):
        _require(isinstance(pair, dict)
                 and set(pair) == {"first", "plain_ns", "traced_ns", "recording_overhead_ns"},
                 "invalid benchmark pair")
        _require(pair["first"] == ("plain" if index % 2 == 0 else "traced"),
                 "incorrect benchmark pair order")
        for name in ("plain_ns", "traced_ns", "recording_overhead_ns"):
            _require(_natural(pair[name]), f"invalid {name}")
    _require(_digest(report["summary"]) == _digest(_summary(pairs)), "benchmark summary mismatch")
    _require(len(json.dumps(report).encode("utf-8")) <= MAX_REPORT_BYTES,
             "benchmark report exceeds byte limit")
    return report


def decode(raw: bytes) -> Object:
    _require(len(raw) <= MAX_REPORT_BYTES, "benchmark report exceeds byte limit")
    return compiler_trace.decode(raw)
