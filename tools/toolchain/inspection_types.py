# SPDX-License-Identifier: Apache-2.0
"""Source-bound expression type decisions from the existing pure compiler."""

from typing import cast

from toolchain.facts import MAX_EXPRESSIONS
from toolchain.source import SourceSnapshot

KINDS = frozenset({"nat", "bool", "name", "call", "binary", "unary", "group"})


def expressions(document: SourceSnapshot, raw: object, syntax: list[dict[str, object]],
                symbols: list[object], occurrences: list[object]) -> list[dict[str, object]]:
    """Join complete checker decisions to syntax nodes without running type inference.

    The [pure inspection contract](../../docs/tooling/tooling-protocols.md#pure-development-snapshot-increment)
    owns the typed overlay and its snapshot-scoped node identities.
    """
    if not isinstance(raw, list) or len(raw) > MAX_EXPRESSIONS:
        raise ValueError("pure inspection expression decisions are missing or over budget")
    by_handle = {cast("str", node["id"]): node for node in syntax}
    expected: dict[tuple[str, int], dict[str, object]] = {}
    for node in syntax:
        kind = cast("str", node["kind"])
        if kind not in KINDS:
            continue
        site = node
        if kind == "binary":
            site = next(by_handle[child] for child in cast("list[str]", node["children"])
                        if by_handle[child]["role"] == "operator")
        key = kind, cast("list[int]", site["span"])[0]
        if key in expected:
            raise ValueError("pure inspection expression sites are ambiguous")
        expected[key] = node
    if len(expected) != len(raw):
        raise ValueError("pure inspection expression inventory differs from source syntax")
    decided: dict[str, dict[str, object]] = {}
    for value in raw:
        if not isinstance(value, dict) or set(value) != {"kind", "line", "column", "type"}:
            raise ValueError("invalid pure inspection expression decision")
        if (not isinstance(value["kind"], str) or value["kind"] not in KINDS
                or type(value["line"]) is not int or type(value["column"]) is not int
                or value["line"] < 1 or value["column"] < 1):
            raise ValueError("invalid pure inspection expression site")
        position = document.diagnostic_position(value["line"], value["column"])
        offset = document.position_byte_offset(position["line"], position["character"])
        node = expected.get((value["kind"], offset))
        value_type = value["type"]
        if (node is None or node["id"] in decided or not isinstance(value_type, dict)
                or set(value_type) != {"kind", "name"} or value_type["kind"] != "scalar"
                or value_type["name"] not in {"Nat", "bool"}):
            raise ValueError("pure inspection expression decision differs from source syntax")
        decided[cast("str", node["id"])] = {"node": node["id"], "span": node["span"], "type": value_type}
    symbol_types = {cast("dict[str, object]", symbol)["id"]: cast("dict[str, object]", symbol)["type"]
                    for symbol in symbols}
    reference_types = {tuple(cast("list[int]", occurrence["span"])): symbol_types[occurrence["symbol"]]
                       for item in occurrences for occurrence in [cast("dict[str, object]", item)]}
    for node in syntax:
        handle = cast("str", node["id"])
        if handle not in decided:
            continue
        value_type = cast("dict[str, object]", decided[handle]["type"])
        kind = node["kind"]
        if kind in {"name", "call"}:
            child = by_handle[cast("list[str]", node["children"])[0]]
            resolved = cast("dict[str, object]", reference_types[tuple(cast("list[int]", child["span"]))])
            selected = resolved.get("name") if kind == "name" else resolved.get("result")
            if selected != value_type["name"]:
                raise ValueError("pure inspection expression type differs from its resolved symbol")
        elif kind == "group":
            child = cast("list[str]", node["children"])[0]
            if decided[child]["type"] != value_type:
                raise ValueError("pure inspection grouped type differs from its checked operand")
        else:
            if kind == "binary":
                operator = next(by_handle[child]["value"] for child in cast("list[str]", node["children"])
                                if by_handle[child]["role"] == "operator")
                selected = "Nat" if operator in {"+", "-", "*", "/", "%"} else "bool"
            else:
                selected = "Nat" if kind == "nat" else "bool"
            if value_type["name"] != selected:
                raise ValueError("pure inspection expression type differs from its checked syntax kind")
    return [decided[cast("str", node["id"])] for node in syntax if node["id"] in decided]
