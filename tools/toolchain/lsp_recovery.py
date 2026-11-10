# SPDX-License-Identifier: Apache-2.0
"""Explicit incomplete-source completion edits from one checked compiler repair."""

import hashlib
import subprocess
from collections.abc import Callable
from typing import cast

from toolchain.completion import repair_span
from toolchain.lsp_discovery import project
from toolchain.lsp_services import (
    INSPECTION_SECONDS,
    InspectionError,
    Position,
    validate_inspection,
)
from toolchain.lsp_worker import worker_command
from toolchain.protocol_json import MAX_BODY_BYTES, decode_message, encode_message
from toolchain.source import SourceSnapshot

type Completer = Callable[[bytes, int], dict[str, object]]


def inspect_recovery(source: bytes, cursor: int) -> dict[str, object]:
    """Use the checkout's isolated compiler worker with a fixed two-repair budget."""
    try:
        done = subprocess.run(worker_command("--complete-at", str(cursor)), input=source,
                              capture_output=True, timeout=INSPECTION_SECONDS, check=False)
        if done.returncode != 0 or len(done.stdout) > MAX_BODY_BYTES:
            raise InspectionError("Completion worker failed or exceeded its output bound")
        result = decode_message(done.stdout)
        if result.pop("source_sha256", None) != hashlib.sha256(source).hexdigest():
            raise InspectionError("Completion repair differs from the current source")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise InspectionError("Completion repair worker unavailable or exceeded its budget") from error
    return result


def _project_recovery(snapshot: SourceSnapshot, position: Position,
                      raw: dict[str, object]) -> dict[str, object]:
    """Validate repaired facts, then translate only their selected edit to the original overlay."""
    encode_message(raw)
    empty: dict[str, object] = {"isIncomplete": True, "items": []}
    if raw == {"status": "unavailable"}:
        return empty
    if set(raw) != {"status", "span", "literal", "facts"} or raw["status"] != "recovered":
        raise InspectionError("Invalid completion repair response")
    cursor = snapshot.position_byte_offset(*position)
    span = repair_span(snapshot.source, cursor)
    literal = raw["literal"]
    span_raw = raw["span"]
    if (span is None or not isinstance(span_raw, list) or len(span_raw) != 2
            or any(type(value) is not int for value in span_raw) or span_raw != list(span)
            or not isinstance(literal, str) or literal not in {"0", "false"}
            or not isinstance(raw["facts"], dict)):
        raise InspectionError("Completion repair differs from the selected source site")
    first, last = span
    repaired = snapshot.source[:first] + cast("str", literal).encode("ascii") + snapshot.source[last:]
    candidate = SourceSnapshot(snapshot.uri, snapshot.version, repaired.decode("utf-8"), snapshot.generation)
    facts = validate_inspection(candidate, cast("dict[str, object]", raw["facts"]))
    if facts is None:
        raise InspectionError("Completion repair lacks checked facts")
    point = candidate.byte_position(first)
    selected = (point["line"], point["character"])
    result = cast("dict[str, object]", project(candidate, facts, "textDocument/completion", selected))
    prefix = snapshot.source[first:cursor].decode("ascii")
    start, end = snapshot.byte_position(first), snapshot.byte_position(last)
    items: list[dict[str, object]] = [
        {**value, "textEdit": {"range": {"start": start, "end": end}, "newText": value["label"]}}
        for value in cast("list[dict[str, object]]", result["items"])
        if cast("str", value["label"]).startswith(prefix)]
    return {"isIncomplete": True, "items": items}


def project_recovery(snapshot: SourceSnapshot, position: Position,
                     raw: dict[str, object]) -> dict[str, object]:
    """Treat malformed compiler responses as failed inspection, preserving the original overlay."""
    try:
        return _project_recovery(snapshot, position, raw)
    except (ValueError, TypeError, KeyError) as error:
        raise InspectionError("Invalid source-bound completion repair") from error
