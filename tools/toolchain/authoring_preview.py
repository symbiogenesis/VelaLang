# SPDX-License-Identifier: Apache-2.0
"""Explicit, source-bound Boolean lint edits over checked pure compiler syntax."""

import hashlib
import json
from dataclasses import fields, is_dataclass
from typing import cast

import toolchain as vela
from toolchain import ast, concrete, inspection
from toolchain.source import SourceSnapshot

SCHEMA_VERSION = 1


def _meaning(value: object) -> object:
    """Compare checked syntax modulo grouping and Boolean equality identities."""
    if isinstance(value, ast.Expression):
        if value.kind == "group":
            return _meaning(value.children[0])
        if value.kind == "binary" and value.value == "==":
            for index in (1, 0):
                literal = value.children[index]
                while literal.kind == "group":
                    literal = literal.children[0]
                if literal.kind == "bool":
                    operand = _meaning(value.children[1 - index])
                    return operand if literal.value is True else ("unary", "!", (operand,), ())
        return value.kind, value.value, tuple(_meaning(child) for child in value.children), _meaning(value.labels)
    if is_dataclass(value) and not isinstance(value, type):
        return type(value).__name__, tuple((field.name, _meaning(getattr(value, field.name)))
                                           for field in fields(value) if field.name != "site")
    if isinstance(value, tuple):
        return tuple(_meaning(child) for child in value)
    return value


def preview(source: bytes, line: int, column: int) -> dict[str, object]:
    """Propose one checked VELA103 edit at a one-based compiler operator site.

    The [authoring contract](../../docs/tooling/authoring-tools.md#checked-boolean-comparison-previews)
    owns the supported rewrite and the source-preserving publication boundary.
    """
    if any(type(value) is not int or value < 1 for value in (line, column)):
        raise ValueError("preview requires positive integer compiler coordinates")
    original = vela.parse_module(source)
    vela._translate(source, original)
    snapshot = inspection.inspect(source)
    publication = snapshot.export()
    if publication["status"] != "checked":
        raise ValueError("complete compiler inspection is required for a lint preview")
    document = SourceSnapshot("memory:vela", 1, source.decode("utf-8"), 1)
    position = document.diagnostic_position(line, column)
    offset = document.position_byte_offset(position["line"], position["character"])
    nodes = cast("list[dict[str, object]]", publication["syntax"])
    by_id = {node["id"]: node for node in nodes}
    operator = next((node for node in nodes if node["kind"] == "operator"
                     and node["value"] == "==" and cast("list[int]", node["span"])[0] == offset), None)
    if operator is None:
        raise ValueError("preview site is not the start of a checked equality operator")
    comparison = by_id[operator["parent"]]
    children = {by_id[child]["role"]: by_id[child] for child in cast("list[str]", comparison["children"])}
    operand: dict[str, object] | None = None
    literal: dict[str, object] | None = None
    for side, other in (("right", "left"), ("left", "right")):
        selected = children[side]
        while selected["kind"] == "group":
            selected = by_id[cast("list[str]", selected["children"])[0]]
        if selected["kind"] == "bool":
            literal, operand = selected, children[other]
            break
    if literal is None or operand is None:
        raise ValueError("preview requires a Boolean literal operand (VELA103)")
    first, last = cast("list[int]", comparison["span"])
    pieces = cast("list[dict[str, object]]", publication["concrete"])
    if any(piece["kind"] not in concrete.TOKEN_KINDS | {"whitespace"}
           and cast("list[int]", piece["span"])[0] < last
           and cast("list[int]", piece["span"])[1] > first for piece in pieces):
        raise ValueError("preview refuses comparisons containing comments")
    begin, end = cast("list[int]", operand["span"])
    replacement = (b"(" if literal["value"] is True else b"!(") + source[begin:end] + b")"
    candidate = source[:first] + replacement + source[last:]
    parsed = vela.parse_module(candidate)
    vela._translate(candidate, parsed)
    if _meaning(original) != _meaning(parsed):
        raise ValueError("Boolean comparison preview changed checked syntax meaning")
    current = inspection.producer_identity()
    if current != cast("dict[str, object]", publication["binding"])["producer"]:
        raise ValueError("compiler producer changed during lint preview")
    return {"schema": SCHEMA_VERSION, "scope": "vela-pure-boolean-lint-preview", "rule": "VELA103",
            "binding": publication["binding"], "snapshot": publication["snapshot"],
            "line": line, "column": column, "span": [first, last],
            "replacement": replacement.decode("utf-8"), "candidate": candidate.decode("utf-8"),
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(), "status": "checked",
            "qualification": "pure-development; no source/artifact correspondence"}


def validate(publication: object, source: bytes) -> bytes:
    """Recheck an exact preview against the current source and producer before use."""
    if not isinstance(publication, dict):
        raise TypeError("invalid Boolean comparison preview")
    line, column = publication.get("line"), publication.get("column")
    if type(line) is not int or type(column) is not int:
        raise ValueError("invalid Boolean comparison preview coordinates")
    expected = preview(source, line, column)
    try:
        matches = json.dumps(publication, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid Boolean comparison preview fields") from error
    if not matches:
        raise ValueError("stale or changed Boolean comparison preview")
    return cast("str", publication["candidate"]).encode("utf-8")
