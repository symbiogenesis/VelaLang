# SPDX-License-Identifier: Apache-2.0
"""Bounded projection of the pure compiler's resolved facts into LSP results."""

import hashlib
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from toolchain.ast import (
    IDENTIFIER,
    KEYWORDS,
    MAX_LITERAL_DIGITS,
    MAX_SOURCE_BYTES,
    UNSUPPORTED,
    Name,
    Site,
    ValueType,
)
from toolchain.documentation import DocumentationSource
from toolchain.facts import MAX_OCCURRENCES, MAX_SYMBOLS, PureType
from toolchain.lsp_worker import worker_command
from toolchain.protocol_json import MAX_BODY_BYTES, decode_message, encode_message
from toolchain.source import SourceSnapshot

INSPECTION_SECONDS = 5
SEMANTIC_TOKEN_TYPES = ("function", "parameter", "variable")
SEMANTIC_TOKEN_MODIFIERS = ("declaration", "readonly")
METHODS = frozenset({"textDocument/hover", "textDocument/definition",
                     "textDocument/references", "textDocument/documentSymbol", "textDocument/inlayHint",
                     "textDocument/semanticTokens/full"})
type Inspector = Callable[[bytes], dict[str, object]]
type Position = tuple[int, int]
type QueryRange = tuple[Position, Position]


class InspectionError(ValueError):
    """The current source cannot supply a complete bounded inspection result."""


def inspect_document(source: bytes) -> dict[str, object]:
    """Run only the checkout's fixed fact producer, never a client-selected tool."""
    try:
        done = subprocess.run(worker_command("--inspect"),
                              input=source, capture_output=True,
                              timeout=INSPECTION_SECONDS, check=False)
        if done.returncode != 0 or len(done.stdout) > MAX_BODY_BYTES:
            raise InspectionError("Pure prototype inspection worker failed or exceeded its output bound")
        result = decode_message(done.stdout)
        if result.pop("source_sha256", None) != hashlib.sha256(source).hexdigest():
            raise InspectionError("Inspection result differs from the requested source")
    except subprocess.TimeoutExpired as error:
        raise InspectionError("Pure prototype inspection exceeded 5 seconds") from error
    except (OSError, ValueError) as error:
        raise InspectionError("Pure prototype inspection worker unavailable") from error
    else:
        return result


@dataclass(frozen=True)
class _Symbol:
    name: str
    kind: str
    detail: str
    value_type: PureType
    start: Position
    end: Position
    type_hint: str | None
    documentation: str | None


@dataclass(frozen=True)
class _Occurrence:
    symbol: int
    start: Position
    end: Position
    declaration: bool


@dataclass(frozen=True)
class Inspection:
    snapshot: str
    symbols: tuple[_Symbol, ...]
    occurrences: tuple[_Occurrence, ...]


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise InspectionError("Invalid pure prototype inspection object")
    return cast("dict[str, object]", value)


def _integer(value: object) -> int:
    if type(value) is not int or not 0 <= value < 2 ** 31:
        raise InspectionError("Invalid pure prototype inspection integer")
    return value


def _value_type(value: object) -> ValueType:
    if value not in ("Nat", "bool"):
        raise InspectionError("Invalid pure prototype scalar type")
    return cast("ValueType", value)


def _pure_type(value: object, kind: object) -> PureType:
    if kind != "function":
        record = _object(value, {"kind", "name"})
        if record["kind"] != "scalar":
            raise InspectionError("Invalid pure prototype scalar type kind")
        return PureType(_value_type(record["name"]))
    record = _object(value, {"kind", "result", "parameters", "const"})
    raw = record["parameters"]
    if (record["kind"] != "function" or type(record["const"]) is not bool
            or not isinstance(raw, list) or len(raw) > MAX_SYMBOLS):
        raise InspectionError("Invalid pure prototype callable type")
    parameters: list[tuple[ValueType, bool]] = []
    for item in raw:
        parameter = _object(item, {"type", "required_static"})
        if type(parameter["required_static"]) is not bool:
            raise InspectionError("Invalid pure prototype static parameter type")
        parameters.append((_value_type(parameter["type"]), parameter["required_static"]))
    return PureType(_value_type(record["result"]), tuple(parameters), record["const"])


def _span(snapshot: SourceSnapshot, lines: list[str], name: str,
          record: dict[str, object]) -> tuple[Position, Position]:
    line, column = _integer(record["line"]), _integer(record["column"])
    if not 1 <= line <= len(lines) or column < 1:
        raise InspectionError("Pure prototype inspection site is outside source")
    text, start = lines[line - 1], column - 1
    end = start + len(name)
    if (text[start:end] != name
            or (start and (text[start - 1].isascii() and (text[start - 1].isalnum() or text[start - 1] == "_")))
            or (end < len(text) and (text[end].isascii() and (text[end].isalnum() or text[end] == "_")))):
        raise InspectionError("Pure prototype inspection identifier differs from source")
    # The compiler's sites count normalized Unicode code points. Only the shared
    # source adapter converts those units to LSP's UTF-16 coordinates.
    first = snapshot.diagnostic_position(line, column)
    last = snapshot.diagnostic_position(line, column + len(name))
    return (first["line"], first["character"]), (last["line"], last["character"])


def _validate(snapshot: SourceSnapshot, raw: dict[str, object]) -> Inspection | None:
    encode_message(raw)
    if raw.get("status") == "unavailable":
        record = _object(raw, {"status", "reason"})
        if record["reason"] in {"syntax", "name", "type", "unsupported", "limit", "encoding"}:
            return None
        raise InspectionError("Pure prototype inspection unavailable or exceeds its bounds")
    record = _object(raw, {"status", "symbols", "occurrences"})
    symbols_raw, occurrences_raw = record["symbols"], record["occurrences"]
    if (record["status"] != "ok" or not isinstance(symbols_raw, list)
            or not isinstance(occurrences_raw, list) or len(symbols_raw) > MAX_SYMBOLS
            or len(occurrences_raw) > MAX_OCCURRENCES):
        raise InspectionError("Pure prototype inspection exceeds its bounds or has invalid status")
    lines = snapshot.text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    documentation = DocumentationSource(snapshot.source)
    symbols: list[_Symbol] = []
    for value in symbols_raw:
        fields = {"name", "kind", "detail", "type", "line", "column"}
        if isinstance(value, dict) and "documentation" in value:
            fields.add("documentation")
        if isinstance(value, dict) and "inferred" in value:
            fields.add("inferred")
        symbol = _object(value, fields)
        name, kind, detail = symbol["name"], symbol["kind"], symbol["detail"]
        if (not isinstance(name, str) or not IDENTIFIER.fullmatch(name)
                or name in KEYWORDS | UNSUPPORTED or kind not in {"function", "parameter", "variable", "constant"}
                or not isinstance(detail, str) or not detail or len(detail) > MAX_SOURCE_BYTES):
            raise InspectionError("Invalid pure prototype inspection symbol")
        if "inferred" in symbol and (symbol["inferred"] is not False or kind != "variable"):
            raise InspectionError("Invalid pure prototype local inference flag")
        value_type = _pure_type(symbol["type"], kind)
        first, last = _span(snapshot, lines, name, symbol)
        if symbols and first <= symbols[-1].start:
            raise InspectionError("Pure prototype inspection declarations are unordered or duplicated")
        type_hint = None
        if kind == "variable":
            # The compiler records each checked local type and whether an
            # explicit annotation supplied it. The adapter never infers a type.
            if detail != f"{name}: {value_type.result}":
                raise InspectionError("Invalid pure prototype inferred local type")
            type_hint = f": {value_type.result}"
            if symbol.get("inferred") is False:
                type_hint = None
        elif kind == "parameter":
            if detail not in {f"{name}: {value_type.result}", f"const {name}: {value_type.result}"}:
                raise InspectionError("Invalid pure prototype parameter detail")
        elif kind == "constant":
            natural_prefix = f"const Nat {name} = "
            natural = detail.removeprefix(natural_prefix)
            valid_natural = (detail.startswith(natural_prefix)
                             and 1 <= len(natural) <= MAX_LITERAL_DIGITS
                             and natural.isascii() and natural.isdecimal()
                             and (natural == "0" or not natural.startswith("0")))
            if not valid_natural and detail not in {
                    f"const bool {name} = true", f"const bool {name} = false",
                    f"const Nat {name}", f"const bool {name}"}:
                raise InspectionError("Invalid pure prototype constant detail")
            if not detail.startswith(f"const {value_type.result} {name}"):
                raise InspectionError("Pure prototype constant type differs from its label")
        doc = None
        if "documentation" in symbol:
            site = Site(_integer(symbol["line"]), _integer(symbol["column"]))
            doc = documentation.validate(symbol["documentation"], Name(name, site), cast("str", kind))
        symbols.append(_Symbol(name, cast("str", kind), detail, value_type, first, last, type_hint, doc))
    owned_parameters: set[int] = set()
    for index, symbol in enumerate(symbols):
        parameters = symbol.value_type.parameters
        if parameters is None:
            continue
        end = index + 1
        while end < len(symbols) and symbols[end].kind == "parameter":
            end += 1
        declared = symbols[index + 1:end]
        if len(declared) != len(parameters):
            raise InspectionError("Pure prototype callable parameter inventory differs from its type")
        owned_parameters.update(range(index + 1, end))
        labels: list[str] = []
        for parameter, (value_type, required_static) in zip(declared, parameters, strict=True):
            prefix = "const " if required_static else ""
            if (parameter.kind != "parameter" or parameter.value_type != PureType(value_type)
                    or parameter.detail != f"{prefix}{parameter.name}: {value_type}"):
                raise InspectionError("Pure prototype callable type differs from its parameters")
            labels.append(f"{prefix}{value_type} {parameter.name}")
        prefix = "const " if symbol.value_type.const else ""
        expected = f"public {prefix}{symbol.value_type.result} {symbol.name}({', '.join(labels)})"
        if symbol.detail != expected:
            raise InspectionError("Pure prototype callable type differs from its label")
    if any(symbol.kind == "parameter" and index not in owned_parameters
           for index, symbol in enumerate(symbols)):
        raise InspectionError("Pure prototype parameter has no callable owner")
    occurrences: list[_Occurrence] = []
    declarations: set[int] = set()
    for value in occurrences_raw:
        occurrence = _object(value, {"symbol", "line", "column", "declaration"})
        identity = _integer(occurrence["symbol"])
        declaration = occurrence["declaration"]
        if identity >= len(symbols) or type(declaration) is not bool:
            raise InspectionError("Invalid pure prototype inspection occurrence link")
        symbol = symbols[identity]
        first, last = _span(snapshot, lines, symbol.name, occurrence)
        if occurrences and first < occurrences[-1].end:
            raise InspectionError("Pure prototype inspection occurrences overlap or are unordered")
        if declaration:
            if identity in declarations or first != symbol.start:
                raise InspectionError("Invalid pure prototype inspection declaration link")
            declarations.add(identity)
        elif first == symbol.start:
            raise InspectionError("Pure prototype declaration mislabeled as reference")
        occurrences.append(_Occurrence(identity, first, last, declaration))
    if len(declarations) != len(symbols):
        raise InspectionError("Pure prototype inspection omits declaration occurrences")
    return Inspection(snapshot.identity, tuple(symbols), tuple(occurrences))


def _range(start: Position, end: Position) -> dict[str, object]:
    return {"start": {"line": start[0], "character": start[1]},
            "end": {"line": end[0], "character": end[1]}}


def _location(uri: str, start: Position, end: Position) -> dict[str, object]:
    return {"uri": uri, "range": _range(start, end)}


def project(snapshot: SourceSnapshot, raw: dict[str, object], method: str,
            position: Position | None, include_declaration: bool = False,
            requested_range: QueryRange | None = None) -> object:
    """Project only complete current facts; malformed producer data is a refusal."""
    return project_inspection(snapshot, validate_inspection(snapshot, raw), method,
                              position, include_declaration, requested_range)


def validate_inspection(snapshot: SourceSnapshot, raw: dict[str, object]) -> Inspection | None:
    """Validate an untrusted response once into immutable, source-bound facts."""
    try:
        return _validate(snapshot, raw)
    except (ValueError, TypeError, KeyError) as error:
        raise InspectionError("Invalid pure prototype inspection result") from error


def project_inspection(snapshot: SourceSnapshot, inspection: Inspection | None, method: str,
                       position: Position | None, include_declaration: bool = False,
                       requested_range: QueryRange | None = None) -> object:
    """Project validated facts; the caller binds their lifetime to the exact snapshot."""
    if inspection is not None and inspection.snapshot != snapshot.identity:
        raise InspectionError("Inspection facts differ from the current snapshot")
    empty: object = [] if method in {
        "textDocument/references", "textDocument/documentSymbol", "textDocument/inlayHint"} else None
    if method == "textDocument/semanticTokens/full":
        empty = {"data": []}
    if inspection is None:
        return empty
    if method == "textDocument/semanticTokens/full":
        data: list[int] = []
        previous_line, previous_start = 0, 0
        for occurrence in inspection.occurrences:
            symbol = inspection.symbols[occurrence.symbol]
            line, start = occurrence.start
            token_type = {"function": 0, "parameter": 1, "variable": 2, "constant": 2}[symbol.kind]
            modifiers = int(occurrence.declaration) | (0 if symbol.kind == "function" else 2)
            data.extend((line - previous_line,
                         start - previous_start if line == previous_line else start,
                         occurrence.end[1] - start, token_type, modifiers))
            previous_line, previous_start = line, start
        return {"data": data}
    if method == "textDocument/inlayHint":
        if requested_range is None:
            raise InspectionError("Pure prototype hints require a source range")
        first, last = requested_range
        return [{"position": {"line": symbol.end[0], "character": symbol.end[1]},
                 "label": symbol.type_hint, "kind": 1}
                for symbol in inspection.symbols
                if symbol.type_hint is not None and first <= symbol.start and symbol.end <= last]
    if method == "textDocument/documentSymbol":
        kinds = {"function": 12, "constant": 14, "parameter": 13, "variable": 13}
        return [{"name": symbol.name, "kind": kinds[symbol.kind],
                 "location": _location(snapshot.uri, symbol.start, symbol.end)}
                for symbol in inspection.symbols]
    selected = next((occurrence for occurrence in inspection.occurrences
                     if position is not None and occurrence.start <= position < occurrence.end), None)
    if selected is None:
        return empty
    symbol = inspection.symbols[selected.symbol]
    if method == "textDocument/hover":
        doc = "" if symbol.documentation is None else "\n\n" + symbol.documentation
        return {"contents": {"kind": "plaintext", "value": symbol.detail + doc + "\nVela pure prototype (unqualified)"},
                "range": _range(selected.start, selected.end)}
    if method == "textDocument/definition":
        return _location(snapshot.uri, symbol.start, symbol.end)
    return [_location(snapshot.uri, occurrence.start, occurrence.end)
            for occurrence in inspection.occurrences
            if occurrence.symbol == selected.symbol and (include_declaration or not occurrence.declaration)]
