# SPDX-License-Identifier: Apache-2.0
"""Bounded value and callable discovery from checked pure compiler facts."""

from dataclasses import dataclass
from typing import cast

from toolchain import concrete
from toolchain.ast import VelaError
from toolchain.lsp_services import Inspection, InspectionError, Position
from toolchain.source import SourceSnapshot

METHODS = frozenset({"textDocument/completion", "textDocument/signatureHelp"})


def _range(first: Position, last: Position) -> dict[str, object]:
    return {"start": {"line": first[0], "character": first[1]},
            "end": {"line": last[0], "character": last[1]}}


def _parameters(inspection: Inspection, identity: int) -> list[str]:
    symbol = inspection.symbols[identity]
    parameters = symbol.value_type.parameters
    if parameters is None:
        raise InspectionError("Callable discovery requires a function type")
    return [f"{'const ' if required_static else ''}{value_type} {parameter.name}"
            for parameter, (value_type, required_static) in zip(
                inspection.symbols[identity + 1:identity + 1 + len(parameters)], parameters, strict=True)]


def _completion(snapshot: SourceSnapshot, inspection: Inspection, position: Position) -> object:
    selected = next((item for item in inspection.occurrences
                     if not item.declaration and item.start <= position <= item.end), None)
    if selected is None:
        return {"isIncomplete": False, "items": []}
    symbol = inspection.symbols[selected.symbol]
    first = snapshot.position_byte_offset(*selected.start)
    cursor = snapshot.position_byte_offset(*position)
    prefix = snapshot.source[first:cursor].decode("ascii")
    callable_use = symbol.kind == "function"
    parameters = _parameters(inspection, selected.symbol) if callable_use else []
    choices = next((identities for start, identities in inspection.completions
                    if start == selected.start), ())
    items: list[dict[str, object]] = []
    for identity, candidate in enumerate(inspection.symbols):
        if callable_use and (candidate.kind != "function" or candidate.start > symbol.start
                or candidate.value_type != symbol.value_type or not candidate.name.startswith(prefix)
                or _parameters(inspection, identity) != parameters):
            continue
        if not callable_use and (identity not in choices or not candidate.name.startswith(prefix)):
            continue
        item: dict[str, object] = {"label": candidate.name, "kind": 3 if callable_use else (
                                      21 if candidate.kind == "constant" else 6), "detail": candidate.detail,
                                  "textEdit": {"range": _range(selected.start, selected.end),
                                               "newText": candidate.name}}
        if candidate.documentation is not None:
            item["documentation"] = {"kind": "plaintext", "value": candidate.documentation}
        items.append(item)
    # Empty and incomplete-source insertion sites need additional compiler facts.
    return {"isIncomplete": True, "items": items}


@dataclass(frozen=True)
class _Call:
    first: int
    last: int
    symbol: int
    commas: tuple[int, ...]


def _calls(snapshot: SourceSnapshot, inspection: Inspection) -> list[_Call]:
    resolved = {snapshot.position_byte_offset(*item.start): item.symbol
                for item in inspection.occurrences
                if not item.declaration and inspection.symbols[item.symbol].kind == "function"}
    try:
        tokens = [piece for piece in concrete.parts(snapshot.source)
                  if piece["kind"] in concrete.TOKEN_KINDS]
    except (ValueError, VelaError) as error:
        raise InspectionError("Callable token context unavailable or exceeds bounds") from error
    stack: list[tuple[int, int | None, list[int]]] = []
    result: list[_Call] = []
    previous: dict[str, object] | None = None
    for token in tokens:
        first, last = cast("list[int]", token["span"])
        spelling = token["text"]
        if spelling == "(":
            identity = None if previous is None else resolved.get(cast("list[int]", previous["span"])[0])
            stack.append((last, identity, []))
        elif spelling == "," and stack:
            stack[-1][2].append(first)
        elif spelling == ")":
            if not stack:
                raise InspectionError("Unbalanced callable token context")
            start, identity, commas = stack.pop()
            if identity is not None:
                result.append(_Call(start, first, identity, tuple(commas)))
        previous = token
    if stack:
        raise InspectionError("Unbalanced callable token context")
    return result


def project(snapshot: SourceSnapshot, inspection: Inspection | None, method: str,
            position: Position | None) -> object:
    """Project current checked call identities; completion publishes only explicit edits."""
    if inspection is not None and inspection.snapshot != snapshot.identity:
        raise InspectionError("Callable facts differ from the current snapshot")
    if position is None:
        raise InspectionError("Callable discovery requires a position")
    if inspection is None:
        return {"isIncomplete": True, "items": []} if method == "textDocument/completion" else None
    if method == "textDocument/completion":
        return _completion(snapshot, inspection, position)
    if method != "textDocument/signatureHelp":
        raise InspectionError("Unknown callable discovery method")
    cursor = snapshot.position_byte_offset(*position)
    selected = min((call for call in _calls(snapshot, inspection) if call.first <= cursor <= call.last),
                   key=lambda call: call.last - call.first, default=None)
    if selected is None:
        return None
    symbol = inspection.symbols[selected.symbol]
    parameters = _parameters(inspection, selected.symbol)
    signature: dict[str, object] = {"label": symbol.detail,
                                    "parameters": [{"label": label} for label in parameters]}
    if symbol.documentation is not None:
        signature["documentation"] = {"kind": "plaintext", "value": symbol.documentation}
    result: dict[str, object] = {"signatures": [signature], "activeSignature": 0}
    if parameters:
        result["activeParameter"] = min(sum(offset < cursor for offset in selected.commas), len(parameters) - 1)
    return result
