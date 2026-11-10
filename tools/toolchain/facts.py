# SPDX-License-Identifier: Apache-2.0
"""Bounded diagnostic facts recorded by the pure compiler's own resolver."""

from dataclasses import dataclass
from typing import Literal

from toolchain.ast import Name, Site, ValueType, VelaError
from toolchain.documentation import DocumentationSource

MAX_SYMBOLS = 1024
MAX_OCCURRENCES = 4096
MAX_EXPRESSIONS = 8192
MAX_SCOPES = 2048
MAX_COMPLETION_OPTIONS = 8192
type SymbolKind = Literal["function", "parameter", "variable", "constant"]


@dataclass(frozen=True)
class PureType:
    """Compiler-owned scalar or callable type, independent of display labels."""

    result: ValueType
    parameters: tuple[tuple[ValueType, bool], ...] | None = None
    const: bool = False

    def export(self) -> dict[str, object]:
        if self.parameters is None:
            return {"kind": "scalar", "name": self.result}
        return {"kind": "function", "result": self.result, "const": self.const,
                "parameters": [{"type": value_type, "required_static": required_static}
                               for value_type, required_static in self.parameters]}


@dataclass(frozen=True)
class _Symbol:
    name: Name
    kind: SymbolKind
    detail: str
    value_type: PureType
    inferred: bool | None = None


@dataclass(frozen=True)
class _Occurrence:
    symbol: int
    site: Site
    declaration: bool


class Facts:
    """Collect decisions, without performing name resolution or semantic checks."""

    def __init__(self, source: bytes | None = None,
                 declaration_sites: dict[Site, Site] | None = None, *,
                 expression_types: bool = False, completion_options: bool = False) -> None:
        self.symbols: list[_Symbol] = []
        self.occurrences: list[_Occurrence] = []
        self.expression_types: dict[tuple[Site, str], ValueType] = {}
        self.collect_expression_types = expression_types
        self.scopes: list[tuple[str, Site, int | None]] = []
        self.current_scope: int | None = None
        self.symbol_scopes: list[int] = []
        self.occurrence_scopes: list[int] = []
        self.collect_completion_options = completion_options
        self.completions: dict[Site, tuple[int, ...]] = {}
        self.literal_completions: dict[Site, tuple[str, ValueType, bool, tuple[int, ...], tuple[int, ...]]] = {}
        self.completion_count = 0
        self.documentation = None if source is None else DocumentationSource(source)
        self.declaration_sites = {} if declaration_sites is None else dict(declaration_sites)

    def enter_scope(self, kind: str, site: Site) -> None:
        """Record the resolver's lexical environment boundaries for full snapshots."""
        if not self.collect_expression_types:
            return
        if len(self.scopes) >= MAX_SCOPES:
            raise VelaError("inspection-limit", site.line, site.column,
                            "pure inspection exceeds scope limit")
        self.scopes.append((kind, site, self.current_scope))
        self.current_scope = len(self.scopes) - 1

    def leave_scope(self) -> None:
        if self.collect_expression_types:
            if self.current_scope is None:
                raise ValueError("pure inspection scope stack is empty")
            self.current_scope = self.scopes[self.current_scope][2]

    def declare(self, name: Name, kind: SymbolKind, detail: str, value_type: PureType, *,
                inferred: bool | None = None) -> int:
        if len(self.symbols) >= MAX_SYMBOLS:
            raise VelaError("inspection-limit", name.site.line, name.site.column,
                            "pure inspection exceeds declaration limit")
        identity = len(self.symbols)
        if inferred is not None and (inferred is not False or kind != "variable"):
            raise ValueError("only an explicitly annotated variable carries an inference flag")
        self.symbols.append(_Symbol(name, kind, detail, value_type, inferred))
        if self.collect_expression_types:
            if self.current_scope is None:
                raise ValueError("pure inspection declaration has no scope")
            self.symbol_scopes.append(self.current_scope)
        self.reference(identity, name.site, declaration=True)
        return identity

    def reference(self, identity: int, site: Site, *, declaration: bool = False) -> None:
        if len(self.occurrences) >= MAX_OCCURRENCES:
            raise VelaError("inspection-limit", site.line, site.column,
                            "pure inspection exceeds occurrence limit")
        self.occurrences.append(_Occurrence(identity, site, declaration))
        if self.collect_expression_types:
            if self.current_scope is None:
                raise ValueError("pure inspection occurrence has no scope")
            self.occurrence_scopes.append(self.current_scope)

    def expression(self, kind: str, site: Site, value_type: ValueType) -> None:
        """Retain the checker's expression decision without inferring another type."""
        if not self.collect_expression_types:
            return
        key = site, kind
        if key not in self.expression_types and len(self.expression_types) >= MAX_EXPRESSIONS:
            raise VelaError("inspection-limit", site.line, site.column,
                            "pure inspection exceeds expression limit")
        previous = self.expression_types.setdefault(key, value_type)
        if previous != value_type:
            raise ValueError("pure inspection expression has inconsistent checked types")

    def visible_values(self, site: Site, identities: tuple[int, ...]) -> None:
        """Record the resolver's compatible visible values at one checked value use."""
        if not self.collect_completion_options:
            return
        if site in self.completions:
            raise ValueError("pure inspection repeats a completion site")
        self.completion_count += len(identities)
        if (self.completion_count > MAX_COMPLETION_OPTIONS
                or len(self.literal_completions) + len(self.completions) >= MAX_OCCURRENCES):
            raise VelaError("inspection-limit", site.line, site.column,
                            "pure completion facts exceed option limit")
        self.completions[site] = identities

    def literal_values(self, site: Site, spelling: str, value_type: ValueType,
                       identities: tuple[int, ...], static: tuple[int, ...]) -> None:
        """Retain resolver choices at a checked literal, including its static alternatives."""
        if not self.collect_completion_options:
            return
        if site in self.literal_completions:
            raise ValueError("pure inspection repeats a literal completion site")
        self.completion_count += len(identities)
        if (self.completion_count > MAX_COMPLETION_OPTIONS
                or len(self.literal_completions) + len(self.completions) >= MAX_OCCURRENCES):
            raise VelaError("inspection-limit", site.line, site.column,
                            "pure literal completion facts exceed limit")
        self.literal_completions[site] = spelling, value_type, False, identities, static

    def require_static_literal(self, site: Site) -> None:
        """Narrow an already checked literal when its enclosing use requires static input."""
        if site in self.literal_completions:
            spelling, value_type, _, _, static = self.literal_completions[site]
            self.literal_completions[site] = spelling, value_type, True, static, static

    def result(self, *, expression_types: bool = False) -> dict[str, object]:
        ordered = sorted(enumerate(self.symbols),
                         key=lambda item: (item[1].name.site.line, item[1].name.site.column))
        identities = {old: new for new, (old, _) in enumerate(ordered)}
        symbols: list[dict[str, object]] = [
            {"name": symbol.name.text, "kind": symbol.kind, "detail": symbol.detail,
             "type": symbol.value_type.export(),
             "line": symbol.name.site.line, "column": symbol.name.site.column}
            for _, symbol in ordered]
        for data, (_, symbol) in zip(symbols, ordered, strict=True):
            if symbol.inferred is not None:
                data["inferred"] = symbol.inferred
            site = self.declaration_sites.get(symbol.name.site)
            if site is not None and self.documentation is not None:
                try:
                    documentation = self.documentation.at(site)
                except ValueError as error:
                    raise VelaError("inspection-limit", site.line, site.column, str(error)) from error
                if documentation is not None:
                    data["documentation"] = documentation.record()
        occurrences: list[dict[str, object]] = [
            {"symbol": identities[occurrence.symbol], "line": occurrence.site.line,
             "column": occurrence.site.column, "declaration": occurrence.declaration}
            for occurrence in sorted(self.occurrences,
                                     key=lambda item: (item.site.line, item.site.column))]
        result: dict[str, object] = {"status": "ok", "symbols": symbols, "occurrences": occurrences}
        if self.collect_completion_options:
            result["completions"] = [
                {"line": site.line, "column": site.column,
                 "symbols": sorted(identities[identity] for identity in choices)}
                for site, choices in sorted(self.completions.items(), key=lambda item: (
                    item[0].line, item[0].column))]
            result["literal_completions"] = [
                {"line": site.line, "column": site.column, "spelling": spelling,
                 "type": value_type, "required_static": required_static,
                 "symbols": sorted(identities[identity] for identity in choices)}
                for site, (spelling, value_type, required_static, choices, _) in sorted(
                    self.literal_completions.items(), key=lambda item: (item[0].line, item[0].column))]
        if expression_types:
            result["scopes"] = {
                "scopes": [{"kind": kind, "line": site.line, "column": site.column, "parent": parent}
                           for kind, site, parent in self.scopes],
                "symbols": [self.symbol_scopes[old] for old, _ in ordered],
                "occurrences": [self.occurrence_scopes[index] for index, _ in sorted(
                    enumerate(self.occurrences), key=lambda item: (item[1].site.line, item[1].site.column))]}
            result["expressions"] = [
                {"kind": kind, "line": site.line, "column": site.column,
                 "type": {"kind": "scalar", "name": value_type}}
                for (site, kind), value_type in sorted(self.expression_types.items(),
                    key=lambda item: (item[0][0].line, item[0][0].column, item[0][1]))]
        return result
