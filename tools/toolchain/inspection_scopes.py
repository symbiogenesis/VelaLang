# SPDX-License-Identifier: Apache-2.0
"""Source-bound lexical environments recorded by the pure compiler resolver."""

from typing import cast

from toolchain.facts import MAX_SCOPES
from toolchain.source import SourceSnapshot


def scopes(document: SourceSnapshot, raw: object, syntax: list[dict[str, object]],
           symbols: list[object], occurrences: list[object], identity: str) -> list[dict[str, object]]:
    """Validate resolver scope decisions against the complete checked syntax inventory.

    The [inspection contract](../../docs/tooling/tooling-protocols.md#pure-development-snapshot-increment)
    owns these structural links; this adapter performs no name resolution.
    """
    if not isinstance(raw, dict) or set(raw) != {"scopes", "symbols", "occurrences"}:
        raise ValueError("invalid pure inspection scope decisions")
    recorded = raw["scopes"]
    if not isinstance(recorded, list) or not 1 <= len(recorded) <= MAX_SCOPES:
        raise ValueError("pure inspection scope inventory is missing or over budget")
    by_node = {cast("str", node["id"]): node for node in syntax}
    owners: dict[str, int] = {}
    expected_sites: list[int] = []
    result: list[dict[str, object]] = []

    def child(node: dict[str, object], role: str) -> dict[str, object]:
        return next(by_node[handle] for handle in cast("list[str]", node["children"])
                    if by_node[handle]["role"] == role)

    for node in syntax:
        parent = node["parent"]
        inherited = None if parent is None else owners[cast("str", parent)]
        kind = node["kind"]
        if kind in {"module", "function", "block", "expression-body"}:
            index = len(result)
            if kind in {"module", "function"}:
                site = child(node, "name")
            elif kind == "block":
                site = by_node[cast("list[str]", node["children"])[0]]
            else:
                site = child(node, "value")
                if site["kind"] == "binary":
                    site = child(site, "operator")
            expected_sites.append(cast("list[int]", site["span"])[0])
            result.append({"id": f"{identity}:scope:{index}",
                           "kind": "block" if kind == "expression-body" else kind,
                           "node": node["id"], "span": node["span"],
                           "parent": None if inherited is None else f"{identity}:scope:{inherited}",
                           "children": [], "symbols": []})
            if inherited is not None:
                cast("list[str]", result[inherited]["children"]).append(f"{identity}:scope:{index}")
            owners[cast("str", node["id"])] = index
        elif inherited is not None:
            owners[cast("str", node["id"])] = inherited
        else:
            raise ValueError("pure inspection syntax has no containing module scope")
    if len(recorded) != len(result):
        raise ValueError("pure inspection scope inventory differs from source syntax")
    for index, value in enumerate(recorded):
        if (not isinstance(value, dict) or set(value) != {"kind", "line", "column", "parent"}
                or type(value["line"]) is not int or type(value["column"]) is not int
                or value["line"] < 1 or value["column"] < 1
                or (value["parent"] is not None and type(value["parent"]) is not int)):
            raise ValueError("invalid pure inspection scope site")
        position = document.diagnostic_position(value["line"], value["column"])
        offset = document.position_byte_offset(position["line"], position["character"])
        parent = None if value["parent"] is None else f"{identity}:scope:{value['parent']}"
        if (value["kind"] != result[index]["kind"] or parent != result[index]["parent"]
                or offset != expected_sites[index]):
            raise ValueError("pure inspection scope decision differs from source syntax")

    identifiers = {tuple(cast("list[int]", node["span"])): node
                   for node in syntax if node["kind"] == "identifier"}
    for key, facts in (("symbols", symbols), ("occurrences", occurrences)):
        links = raw[key]
        if not isinstance(links, list) or len(links) != len(facts):
            raise ValueError("pure inspection scope links omit compiler facts")
        for value, item in zip(links, facts, strict=True):
            fact = cast("dict[str, object]", item)
            node = identifiers[tuple(cast("list[int]", fact["span"]))]
            owner = owners[cast("str", node["id"])]
            declaration = key == "symbols" or fact["declaration"] is True
            parent_node = by_node[cast("str", node["parent"])]
            if declaration and parent_node["kind"] == "function":
                owner = owners[cast("str", parent_node["parent"])]
            if type(value) is not int or value != owner:
                raise ValueError("pure inspection scope link differs from source syntax")
            fact["scope"] = result[owner]["id"]
            if key == "symbols":
                cast("list[str]", result[owner]["symbols"]).append(cast("str", fact["id"]))
                availability = (cast("list[int]", child(by_node[cast("str", parent_node["parent"])], "body")["span"])[0]
                                if fact["kind"] == "parameter" else cast("list[int]", parent_node["span"])[1])
                fact["available_from"] = availability
    return result
