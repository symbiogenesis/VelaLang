# SPDX-License-Identifier: Apache-2.0
"""Stable source syntax nodes projected from the existing checked parser protocol."""

from typing import cast

from toolchain import ast

MAX_SYNTAX_NODES = 8192
KINDS = frozenset({"module", "function", "constant", "parameter", "type", "block", "binding",
                   "local-constant", "return", "if", "expression-body", "nat", "bool", "name",
                   "call", "argument", "binary", "unary", "group", "identifier", "operator"})
_FIELDS = {
    "file": ("name", "declarations"), "function": ("result", "name", "parameters", "body"),
    "constant": ("type", "name", "value"), "parameter": ("type", "name"),
    "type": (), "block": ("bindings", "exit"), "let": ("type", "name", "value"),
    "constant_local": ("type", "name", "value"), "return": ("value",),
    "if": ("condition", "then", "else"), "expression_body": ("value",),
    "nat": (), "bool": (), "name": ("name",), "call": ("callee", "arguments"),
    "argument": ("label", "value"), "binary": ("left", "operator", "right"),
    "unary": ("operator", "value"), "group": ("value",),
}
_KINDS = {"file": "module", "let": "binding", "constant_local": "local-constant",
          "expression_body": "expression-body"}


def nodes(source: bytes, response: object, identity: str) -> list[dict[str, object]]:
    """Validate source correspondence and flatten only the declared pure syntax fields.

    The [pure inspection contract](../../docs/tooling/tooling-protocols.md#pure-development-snapshot-increment)
    owns this presentation schema; compiler implementation objects are not serialized.
    """
    ast.decode(source, response)
    module = cast("dict[str, object]", cast("dict[str, object]", response)["ast"])
    declarations = cast("list[dict[str, object]]", module["declarations"])
    if cast("list[int]", module["span"])[1] != cast("list[int]", declarations[-1]["span"])[1]:
        raise ValueError("pure inspection module span includes trailing source trivia")
    result: list[dict[str, object]] = []

    def visit(raw: dict[str, object], parent: str | None, role: str, index: int | None) -> str:
        if len(result) >= MAX_SYNTAX_NODES:
            raise ast.VelaError("limit", 1, 1, "syntax inspection exceeds node limit")
        handle = f"{identity}:node:{len(result)}"
        raw_kind = cast("str", raw.get("kind", "operator" if role == "operator" else "identifier"))
        kind = _KINDS.get(raw_kind, raw_kind)
        if kind not in KINDS:
            raise ValueError("unsupported pure inspection syntax kind")
        value = raw.get("value") if raw_kind in {"nat", "bool"} else (
            raw.get("name") if raw_kind == "type" else raw.get("text"))
        children: list[str] = []
        result.append({"id": handle, "kind": kind, "span": raw["span"], "parent": parent,
                       "role": role, "index": index, "children": children, "value": value,
                       "const": raw.get("const", False) if raw_kind in {"function", "parameter"} else None})
        for field in _FIELDS.get(raw_kind, ()):
            child = raw.get(field)
            if child is None:
                continue
            if isinstance(child, list):
                for position, item in enumerate(child):
                    children.append(visit(cast("dict[str, object]", item), handle, field, position))
            else:
                children.append(visit(cast("dict[str, object]", child), handle, field, None))
        return handle

    visit(module, None, "root", None)
    return result


def validate_inventory(syntax: list[dict[str, object]], symbols: list[object],
                       occurrences: list[object]) -> None:
    """Require every authored declaration/reference site without resolving it again."""
    parents = {node["id"]: node for node in syntax}
    kinds = {"function": "function", "constant": "constant", "parameter": "parameter",
             "binding": "variable", "local-constant": "constant"}
    expected_symbols: list[tuple[str, str, int, int]] = []
    expected_occurrences: list[tuple[str, int, int, bool]] = []
    for node in syntax:
        if node["kind"] != "identifier":
            continue
        parent = parents[node["parent"]]
        if parent["kind"] == "module":
            continue
        name = cast("str", node["value"])
        first, last = cast("list[int]", node["span"])
        declaration_kind = kinds.get(cast("str", parent["kind"])) if node["role"] == "name" else None
        if declaration_kind is not None:
            expected_symbols.append((declaration_kind, name, first, last))
        elif (parent["kind"], node["role"]) not in {
                ("name", "name"), ("call", "callee"), ("argument", "label")}:
            raise ValueError("pure inspection identifier has an unsupported source role")
        expected_occurrences.append((name, first, last, declaration_kind is not None))
    declared = [cast("dict[str, object]", symbol) for symbol in symbols]
    actual_symbols = [(cast("str", symbol["kind"]), cast("str", symbol["name"]),
                       *cast("list[int]", symbol["span"])) for symbol in declared]
    if sorted(actual_symbols) != sorted(expected_symbols):
        raise ValueError("pure inspection declaration inventory differs from source syntax")
    by_handle = {symbol["id"]: symbol for symbol in declared}
    references = [cast("dict[str, object]", occurrence) for occurrence in occurrences]
    actual_occurrences = [(cast("str", by_handle[occurrence["symbol"]]["name"]),
                           *cast("list[int]", occurrence["span"]), cast("bool", occurrence["declaration"]))
                          for occurrence in references]
    if sorted(actual_occurrences) != sorted(expected_occurrences):
        raise ValueError("pure inspection occurrence inventory differs from source syntax")
