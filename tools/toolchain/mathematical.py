# SPDX-License-Identifier: Apache-2.0
"""Native syntax adapter for bounded mathematical compilation and observation."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from toolchain import (
    StaticEvaluation,
    ValueType,
)
from toolchain import (
    elaborate as vela_elaborate,
)
from toolchain import (
    parser as vela_parser,
)
from toolchain.ast import Name, position
from toolchain.authoring import Finding, generic_type_findings
from toolchain.elaborate import Elaboration
from toolchain.surface import nodes

_BUILD_CACHE: tuple[tuple[Path, int, int, int], vela_parser.Build] | None = None


def _build(parser: Path) -> vela_parser.Build:
    global _BUILD_CACHE  # noqa: PLW0603
    stat = parser.stat()
    key = (parser, stat.st_mtime_ns, stat.st_size, stat.st_ino)
    if _BUILD_CACHE is not None and _BUILD_CACHE[0] == key:
        return _BUILD_CACHE[1]
    digest = hashlib.sha256(parser.read_bytes()).hexdigest()
    built = vela_parser.Build(parser.parent, parser, {"generated_sha256": {"vela-parser": digest}})
    _BUILD_CACHE = (key, built)
    return built


@dataclass(frozen=True)
class Compilation(Elaboration):
    findings: tuple[Finding, ...] = ()


def inspect_source(source: bytes, parsed: object) -> Compilation:
    """Inspect type binders only after complete exact-source semantic acceptance.

    The [generic naming contract](../../docs/tooling/authoring-tools.md#generic-type-parameter-naming)
    keeps this advisory inspection separate from mathematical acceptance.
    """
    translation = vela_elaborate.elaborate(source, parsed)
    ast = cast("vela_parser.Json", cast("dict[str, object]", parsed)["ast"])
    names: list[tuple[int, Name]] = []
    for item in nodes(ast):
        if item.get("kind") == "generic_parameter" and item.get("mode") == "type":
            identifier = cast("dict[str, vela_parser.Json]", item["name"])
            offset = cast("int", cast("list[vela_parser.Json]", identifier["span"])[0])
            names.append((offset, Name(cast("str", identifier["text"]),
                                       position(source[:offset].decode("utf-8")))))
    names.sort(key=lambda item: item[0])
    findings = sorted(
        generic_type_findings(tuple(name for _, name in names)),
        key=lambda item: (item.line, item.column, item.code),
    )
    return Compilation(translation.module, translation.gallina, tuple(findings))


def compile_source(source: bytes, parser: Path) -> Compilation:
    """Parse and elaborate Vela source with the given native parser binary."""
    parsed = vela_parser.parse_source(_build(parser), source, surface=True)
    return inspect_source(source, parsed)


def evaluate_source(source: bytes, expression: str, value_type: ValueType,
                    parser: Path) -> StaticEvaluation:
    """Check the entire module before parsing and reducing one console initializer."""
    compiled = _build(parser)
    parsed = vela_parser.parse_source(compiled, source, surface=True)
    return vela_elaborate.evaluate(
        source, parsed, expression, value_type,
        parse=lambda probe: vela_parser.parse_source(compiled, probe, surface=True))
