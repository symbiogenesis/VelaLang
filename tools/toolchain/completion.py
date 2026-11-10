# SPDX-License-Identifier: Apache-2.0
"""Bounded single-expression repair using the existing pure parser and resolver."""

from typing import cast

from toolchain import inspect_source
from toolchain.ast import VelaError, source_text
from toolchain.concrete import parts


def repair_span(source: bytes, cursor: int) -> tuple[int, int] | None:
    """Select one whole identifier or an empty insertion boundary, never trivia text."""
    source_text(source)
    if type(cursor) is not int or not 0 <= cursor <= len(source):
        raise ValueError("completion cursor is outside the source")
    prefix = source[:cursor].decode("utf-8")
    if prefix.endswith("\r") and source[cursor:cursor + 1] == b"\n":
        raise ValueError("completion cursor splits CRLF")
    pieces = parts(source)
    for piece in pieces:
        first, last = cast("list[int]", piece["span"])
        if piece["kind"] == "identifier" and first <= cursor <= last:
            return first, last
        if piece["kind"] in {"line-comment", "documentation-comment"} and first <= cursor <= last:
            return None
        if first < cursor < last and piece["kind"] != "whitespace":
            return None
    return cursor, cursor


def recover(source: bytes, cursor: int) -> dict[str, object]:
    """Check at most two literal repairs; ambiguous or unrepaired input supplies no facts."""
    unavailable: dict[str, object] = {"status": "unavailable"}
    try:
        span = repair_span(source, cursor)
    except VelaError:
        return unavailable
    if span is None:
        return unavailable
    first, last = span
    repairs: list[dict[str, object]] = []
    for literal in ("0", "false"):
        repaired = source[:first] + literal.encode("ascii") + source[last:]
        try:
            facts = inspect_source(repaired, completion_options=True)
        except VelaError:
            continue
        line = repaired[:first].decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        contexts = cast("list[dict[str, object]]", facts["literal_completions"])
        if any(item["line"] == len(line) and item["column"] == len(line[-1]) + 1
               and item["spelling"] == literal for item in contexts):
            repairs.append({"literal": literal, "facts": facts})
    if len(repairs) != 1:
        return unavailable
    return {"status": "recovered", "span": [first, last], **repairs[0]}
