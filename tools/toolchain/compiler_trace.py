# SPDX-License-Identifier: Apache-2.0
"""Bounded, input-bound Chrome Trace Event recordings of the pure compiler."""

import hashlib
import json
import platform
import re
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from toolchain.jsonutil import unique_object

MAX_EVENTS = 4096
MAX_TRACE_BYTES = 2_097_152
MAX_DEPTH = 64
MAX_TIME = 2**53 - 1
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
type Object = dict[str, object]


def _encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def producer_identity() -> str:
    """Bind local implementation, parser input closure, and Python runtime version."""
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "toolchain").rglob("*.py"))
    paths.extend(sorted((root / "toolchain" / "parser").glob("*")))
    inputs = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in paths if path.is_file()}
    return _digest({"files": inputs, "python": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "platform": platform.system(), "machine": platform.machine()})


class Recorder:
    """One synchronous worker; bounded complete events retain nested start order."""

    def __init__(self, *, max_events: int = MAX_EVENTS,
                 clock: Callable[[], int] = time.perf_counter_ns) -> None:
        if type(max_events) is not int or not 1 <= max_events <= MAX_EVENTS:
            raise ValueError(f"max_events must be between 1 and {MAX_EVENTS}")
        self.max_events = max_events
        self.clock = clock
        self.origin: int | None = None
        self.last = 0
        self.last_reading = 0
        self.events: list[Object] = []
        self.depth = 0
        self.dropped = 0
        self.clock_fault = False
        self.overhead = 0

    def _now(self) -> int:
        reading = self.clock()
        if type(reading) is not int or reading < self.last_reading:
            self.clock_fault = True
            return self.last
        self.last_reading = reading
        if self.origin is None:
            self.origin = reading
        current = (reading - self.origin) // 1000
        if not self.last <= current <= MAX_TIME:
            self.clock_fault = True
            return self.last
        self.last = current
        return current

    def _retain(self, event: Object) -> bool:
        if len(self.events) >= self.max_events:
            self.dropped += 1
            return False
        self.events.append(event)
        return True

    @contextmanager
    def span(self, name: str) -> Generator[None]:
        if name not in {"compile", "parse", "elaborate-and-emit"}:
            raise ValueError("unsupported pure compiler phase")
        if self.depth >= MAX_DEPTH:
            raise ValueError("trace nesting exceeds limit")
        overhead = time.perf_counter_ns()
        start = self._now()
        event: Object = {"name": name, "cat": "vela.compiler", "ph": "X", "pid": 1,
                         "tid": 1, "ts": start, "dur": 0}
        retained = self._retain(event)
        self.depth += 1
        self.overhead += time.perf_counter_ns() - overhead
        try:
            yield
        finally:
            overhead = time.perf_counter_ns()
            end = self._now()
            if retained:
                event["dur"] = end - start
            self.depth -= 1
            self.overhead += time.perf_counter_ns() - overhead

    def counter(self, name: str, value: int) -> None:
        if name not in {"source_bytes", "gallina_bytes"} or type(value) is not int or not 0 <= value <= MAX_TIME:
            raise ValueError("unsupported counter or value")
        overhead = time.perf_counter_ns()
        self._retain({"name": name, "cat": "vela.compiler", "ph": "C", "pid": 1,
                      "tid": 1, "ts": self._now(), "args": {"bytes": value}})
        self.overhead += time.perf_counter_ns() - overhead

    def export(self, source: bytes, producer: str, *, outcome: str) -> Object:
        if outcome not in {"success", "refused", "cancelled"} or not _SHA256.fullmatch(producer):
            raise ValueError("invalid trace outcome or producer identity")
        manifest: Object = {
            "schema": 1, "scope": "pure-compiler-timing", "clock": "perf_counter_ns",
            "timestamp_unit": "microseconds", "origin": "recording-relative",
            "worker": "synchronous-host-including-parser-wait", "source_sha256": hashlib.sha256(source).hexdigest(),
            "producer_sha256": producer, "max_events": self.max_events,
            "event_count": len(self.events), "dropped_events": self.dropped,
            "incomplete_spans": self.depth, "clock_fault": self.clock_fault,
            "outcome": outcome, "recording_overhead_ns": self.overhead,
            "complete": outcome == "success" and not (self.dropped or self.depth or self.clock_fault),
        }
        # Copy the records so later span completion cannot mutate an exported manifest.
        document: Object = {"traceEvents": json.loads(_encoded(self.events)),
                            "displayTimeUnit": "ms", "vela": manifest}
        manifest["binding_sha256"] = _digest(document)
        if len(_encoded(document)) > MAX_TRACE_BYTES:
            raise ValueError("trace export exceeds byte limit")
        return document


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _natural(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_TIME


def validate(document: object, source: bytes, producer: str, *, require_complete: bool = True) -> Object:
    """Check event structure and freshness before handing a recording to a viewer.

    Hash bindings detect changed data; they supply no producer authentication.
    """
    _require(isinstance(document, dict), "trace must be an object")
    data = cast("Object", document)
    _require(set(data) == {"traceEvents", "displayTimeUnit", "vela"}, "unsupported trace fields")
    _require(data["displayTimeUnit"] == "ms" and isinstance(data["vela"], dict), "unsupported trace format")
    manifest = cast("Object", data["vela"])
    fields = {"schema", "scope", "clock", "timestamp_unit", "origin", "worker", "source_sha256",
              "producer_sha256", "max_events", "event_count", "dropped_events", "incomplete_spans",
              "clock_fault", "outcome", "recording_overhead_ns", "complete", "binding_sha256"}
    _require(set(manifest) == fields, "unsupported manifest fields")
    binding = manifest["binding_sha256"]
    unsigned = {key: value for key, value in manifest.items() if key != "binding_sha256"}
    _require(binding == _digest({**data, "vela": unsigned}), "trace binding mismatch")
    _require(type(manifest["schema"]) is int and manifest["schema"] == 1
             and manifest["scope"] == "pure-compiler-timing"
             and manifest["clock"] == "perf_counter_ns"
             and manifest["timestamp_unit"] == "microseconds"
             and manifest["origin"] == "recording-relative"
             and manifest["worker"] == "synchronous-host-including-parser-wait", "unsupported trace schema")
    _require(manifest["source_sha256"] == hashlib.sha256(source).hexdigest()
             and manifest["producer_sha256"] == producer, "stale trace input or producer")
    for name in ("max_events", "event_count", "dropped_events", "incomplete_spans", "recording_overhead_ns"):
        _require(_natural(manifest[name]), f"invalid {name}")
    _require(1 <= cast("int", manifest["max_events"]) <= MAX_EVENTS, "invalid event bound")
    _require(type(manifest["complete"]) is bool and type(manifest["clock_fault"]) is bool, "invalid completeness flags")
    _require(manifest["outcome"] in ("success", "refused", "cancelled"), "invalid outcome")
    complete = manifest["outcome"] == "success" and not (
        manifest["dropped_events"] or manifest["incomplete_spans"] or manifest["clock_fault"])
    _require(manifest["complete"] == complete, "false completeness claim")
    events = data["traceEvents"]
    _require(isinstance(events, list), "events must be an array")
    events = cast("list[object]", events)
    _require(len(events) == manifest["event_count"] and len(events) <= cast("int", manifest["max_events"]), "event count mismatch")
    previous = 0
    phases: list[str] = []
    counters: dict[str, int] = {}
    spans: dict[str, tuple[int, int]] = {}
    counter_times: dict[str, int] = {}
    ordered_names: list[str] = []
    for item in events:
        _require(isinstance(item, dict), "event must be an object")
        event = cast("Object", item)
        phase = event.get("ph")
        _require(phase in ("X", "C") and set(event) == {"name", "cat", "ph", "pid", "tid", "ts", "dur" if phase == "X" else "args"}, "unsupported event fields")
        _require(type(event["pid"]) is int and event["pid"] == 1
                 and type(event["tid"]) is int and event["tid"] == 1
                 and event["cat"] == "vela.compiler", "invalid worker")
        _require(_natural(event["ts"]), "invalid timestamp")
        start = cast("int", event["ts"])
        _require(start >= previous, "events out of start order")
        previous = start
        if phase == "X":
            _require(event["name"] in ("compile", "parse", "elaborate-and-emit") and _natural(event["dur"]), "invalid phase or duration")
            end = start + cast("int", event["dur"])
            _require(end <= MAX_TIME, "overflowing span")
            name = cast("str", event["name"])
            _require(name not in spans, "duplicate compiler phase")
            spans[name] = (start, end)
            phases.append(name)
        else:
            name = event["name"]
            args = event["args"]
            _require(name in ("source_bytes", "gallina_bytes") and isinstance(args, dict), "unsupported counter")
            args = cast("Object", args)
            _require(set(args) == {"bytes"} and _natural(args["bytes"]), "invalid counter value")
            _require(name not in counters, "duplicate counter")
            counters[cast("str", name)] = cast("int", args["bytes"])
            counter_times[cast("str", name)] = start
        ordered_names.append(cast("str", event["name"]))
    if complete:
        _require(phases == ["compile", "parse", "elaborate-and-emit"]
                 and set(counters) == {"source_bytes", "gallina_bytes"}, "incomplete compiler phase inventory")
        _require(counters["source_bytes"] == len(source), "source byte counter mismatch")
        _require(ordered_names == ["compile", "source_bytes", "parse", "elaborate-and-emit", "gallina_bytes"], "incorrect compiler event order")
        _require(0 == spans["compile"][0] <= counter_times["source_bytes"]
                 <= spans["parse"][0] <= spans["parse"][1]
                 <= spans["elaborate-and-emit"][0] <= spans["elaborate-and-emit"][1]
                 <= counter_times["gallina_bytes"] <= spans["compile"][1], "crossing or incorrectly nested compiler spans")
    _require(not require_complete or complete, "recording is incomplete")
    return manifest


def decode(raw: bytes) -> Object:
    if len(raw) > MAX_TRACE_BYTES:
        raise ValueError("trace exceeds byte limit")
    # The supported document has no deep user data; refuse pathological nesting before decoding.
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 8:
                raise ValueError("trace nesting exceeds limit")
        elif byte in (93, 125):
            depth -= 1
    def reject(value: str) -> object:
        raise ValueError(f"unsupported trace number: {value}")
    value = json.loads(raw, object_pairs_hook=unique_object, parse_float=reject, parse_constant=reject)
    _require(isinstance(value, dict), "trace must be an object")
    return cast("Object", value)
