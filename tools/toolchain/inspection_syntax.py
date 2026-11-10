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

    visit(cast("dict[str, object]", cast("dict[str, object]", response)["ast"]), None, "root", None)
    return result
