# SPDX-License-Identifier: Apache-2.0
"""Source-preserving local rename previews checked by the existing pure producer."""

from toolchain.ast import IDENTIFIER, KEYWORDS, UNSUPPORTED
from toolchain.lsp_services import (
    Inspection,
    InspectionError,
    Inspector,
    Position,
    validate_inspection,
)
from toolchain.source import SourceSnapshot


def valid_name(name: str) -> bool:
    """Accept the same identifier vocabulary as the pure compiler."""
    return IDENTIFIER.fullmatch(name) is not None and name not in KEYWORDS | UNSUPPORTED


def _selected(snapshot: SourceSnapshot, facts: Inspection | None, position: Position | None) -> int | None:
    if facts is None:
        return None
    if facts.snapshot != snapshot.identity:
        raise InspectionError("Rename facts differ from the current source")
    selected = next((item.symbol for item in facts.occurrences
                     if position is not None and item.start <= position < item.end), None)
    # Public declarations and parameters need package-wide reference coverage.
    if selected is None or facts.symbols[selected].kind != "variable":
        return None
    return selected


def _range(first: Position, last: Position) -> dict[str, object]:
    return {"start": {"line": first[0], "character": first[1]},
            "end": {"line": last[0], "character": last[1]}}


def prepare(snapshot: SourceSnapshot, facts: Inspection | None, position: Position | None) -> object:
    """Offer only compiler-resolved local variables, using the selected occurrence."""
    selected = _selected(snapshot, facts, position)
    if selected is None or facts is None:
        return None
    occurrence = next(item for item in facts.occurrences
                      if position is not None and item.start <= position < item.end)
    return {"range": _range(occurrence.start, occurrence.end),
            "placeholder": facts.symbols[selected].name}


def rename(snapshot: SourceSnapshot, facts: Inspection | None, position: Position | None,
           name: str, inspector: Inspector) -> object:
    """Recheck the edited source and every binding before publishing a versioned edit."""
    if not valid_name(name):
        raise ValueError("newName must be a supported pure identifier")
    selected = _selected(snapshot, facts, position)
    if selected is None or facts is None:
        return None
    old_name = facts.symbols[selected].name
    occurrences = tuple(item for item in facts.occurrences if item.symbol == selected)
    edits = [{"range": _range(item.start, item.end), "newText": name} for item in occurrences]
    if name == old_name:
        edits = []
    else:
        source = snapshot.source
        for item in reversed(occurrences):
            first = snapshot.position_byte_offset(*item.start)
            last = snapshot.position_byte_offset(*item.end)
            source = source[:first] + name.encode("ascii") + source[last:]
        candidate = SourceSnapshot(snapshot.uri, snapshot.version, source.decode("utf-8"), snapshot.generation)
        checked = validate_inspection(candidate, inspector(candidate.source))
        if checked is None or len(checked.symbols) != len(facts.symbols):
            raise InspectionError("Renamed source did not preserve checked declarations")
        difference = len(name) - len(old_name)

        def shifted(point: Position) -> Position:
            return (point[0], point[1] + difference * sum(
                item.end[0] == point[0] and item.end <= point for item in occurrences))

        for identity, (before, after) in enumerate(zip(facts.symbols, checked.symbols, strict=True)):
            expected_name = name if identity == selected else before.name
            if (after.name != expected_name or after.kind != before.kind
                    or after.value_type != before.value_type or after.type_hint != before.type_hint
                    or after.documentation != before.documentation
                    or after.start != shifted(before.start) or after.end != shifted(before.end)):
                raise InspectionError("Rename changed a declaration or its type")
        if len(checked.occurrences) != len(facts.occurrences):
            raise InspectionError("Rename changed the resolved reference inventory")
        for before, after in zip(facts.occurrences, checked.occurrences, strict=True):
            if (after.symbol != before.symbol or after.declaration != before.declaration
                    or after.start != shifted(before.start) or after.end != shifted(before.end)):
                raise InspectionError("Rename captured or rebound a source occurrence")
    return {"documentChanges": [{"textDocument": {"uri": snapshot.uri, "version": snapshot.version},
                                 "edits": edits}]}
