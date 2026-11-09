# SPDX-License-Identifier: Apache-2.0
"""Bounded, read-only LSP access to the compiler's canonical formatter."""

import hashlib
import subprocess
from collections.abc import Callable

from toolchain.ast import MAX_SOURCE_BYTES
from toolchain.lsp_services import INSPECTION_SECONDS, InspectionError
from toolchain.lsp_worker import worker_command
from toolchain.protocol_json import MAX_BODY_BYTES, decode_message, encode_message
from toolchain.source import SourceSnapshot

type Formatter = Callable[[bytes], dict[str, object]]


def format_document(source: bytes) -> dict[str, object]:
    """Run the fixed compiler library without invoking its file-writing command."""
    try:
        done = subprocess.run(worker_command("--format"),
                              input=source, capture_output=True,
                              timeout=INSPECTION_SECONDS, check=False)
        if done.returncode != 0 or len(done.stdout) > MAX_BODY_BYTES:
            raise InspectionError("Pure prototype formatting worker failed or exceeded its output bound")
        return decode_message(done.stdout)
    except subprocess.TimeoutExpired as error:
        raise InspectionError("Pure prototype formatting exceeded 5 seconds") from error
    except (OSError, ValueError) as error:
        raise InspectionError("Pure prototype formatting worker unavailable") from error


def formatting_edits(snapshot: SourceSnapshot, raw: dict[str, object]) -> list[dict[str, object]]:
    """Validate the complete current worker response before offering one source edit."""
    try:
        if not isinstance(raw, dict):
            raise InspectionError("Invalid pure prototype formatting object")
        encode_message(raw)
        if raw.get("source_sha256") != hashlib.sha256(snapshot.source).hexdigest():
            raise InspectionError("Formatting result differs from the current source")
        if raw.get("status") == "unavailable":
            if (set(raw) == {"status", "reason", "source_sha256"}
                    and raw["reason"] in {"syntax", "name", "type", "unsupported", "encoding"}):
                return []
            raise InspectionError("Pure prototype formatter unavailable or exceeds its bounds")
        formatted = raw.get("formatted")
        if (set(raw) != {"status", "formatted", "source_sha256"} or raw["status"] != "ok"
                or not isinstance(formatted, str) or not formatted
                or len(formatted.encode("utf-8")) > MAX_SOURCE_BYTES):
            raise InspectionError("Invalid pure prototype formatting result")
        if formatted == snapshot.text:
            return []
        return [{"range": {"start": {"line": 0, "character": 0},
                           "end": snapshot.byte_position(len(snapshot.source))},
                 "newText": formatted}]
    except (ValueError, TypeError, KeyError) as error:
        raise InspectionError("Invalid pure prototype formatting result") from error
