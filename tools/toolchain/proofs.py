# SPDX-License-Identifier: Apache-2.0
"""Lexical sentence splitting, comment stripping, and `Require` dependency ordering for Rocq sources."""

import re
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from types import MappingProxyType

from toolchain import prooflex

# Matches `From X Require [Import|Export] Y ...` and bare `Require` commands.
REQUIRE = re.compile(r"^(?:From\s+(\S+)\s+)?Require(?:\s+(?:Import|Export))?\s+(.+)$")

# A Rocq sentence ends at `.` followed by whitespace or EOF (`...` also ends a sentence,
# whereas `..` is a token and does not).
SENTENCE_END = re.compile(r"(?<!(?<!\.)\.)\.(?=\s|$)")
_SENTENCE_TOKEN = re.compile(r'"[^"]*(?:"|\Z)|' + SENTENCE_END.pattern)

# Prefixes that may precede a command within a sentence: proof bullets/braces/goal selectors,
# `vernac_control` flags (`Time`, `Fail`, `Succeed`, `Timeout`, `Redirect`, etc.),
# `#[...]` attributes, and legacy locality/polymorphism modifiers.
_QUOTED = r'"(?:[^"]|"")*"\s*'
_ATTRIBUTE_VALUES = r'(?:[^\[\]"]|"[^"]*")*'
BULLETS = r"[-+*{}]\s*|(?:\d+|\[[\w']+\]|!)\s*:\s*\{\s*"
CONTROL_FLAGS = (r"(?:Time|Instructions|Fail|Succeed)(?![\w'])\s*"
                 r"|Profile(?![\w'])\s*(?:" + _QUOTED + r")?|Redirect\s*" + _QUOTED
                 + r"|Timeout\s+\d+\s*|AllocLimit\s+\d+\s*(?:Mw|kw)(?![\w'])\s*")
ATTRIBUTE_OPEN = r"#\[" + _ATTRIBUTE_VALUES
LEGACY_ATTRIBUTES = (r"(?:Local|Global|Export|Polymorphic|Monomorphic|Cumulative"
                     r"|NonCumulative|Private|Program)(?![\w'])\s*")
CONTROL_PREFIXES = ("(?:" + BULLETS + "|" + CONTROL_FLAGS + "|" + ATTRIBUTE_OPEN + r"\]\s*|"
                    + LEGACY_ATTRIBUTES + ")*")
VERNAC_CONTROL = ("(?:" + CONTROL_FLAGS + "|" + ATTRIBUTE_OPEN + r"\]\s*|" + LEGACY_ATTRIBUTES
                  + ")*")
DECORATION = re.compile("(?P<bullet>" + BULLETS + r")|(?=(?P<word>[A-Za-z]+))(?:"
                        + CONTROL_FLAGS + "|" + LEGACY_ATTRIBUTES + r")|#\[(?P<attributes>"
                        + _ATTRIBUTE_VALUES + r")\]\s*")
# Control flags that discard the effect of the command they wrap.
VOID = ("Fail", "Succeed")
_BLANK = re.compile(r"\s*")

# Theorem-stating vernacular keywords in Rocq 9.3.
STATEMENTS = ("Theorem", "Lemma", "Fact", "Remark", "Corollary", "Proposition", "Property",
              "Example")
# Top-level declaration vernaculars in Rocq 9.3 (excluding `Class`).
DECLARATIONS = ("Definition", *STATEMENTS, "Instance", "Fixpoint", "CoFixpoint",
                "Inductive", "CoInductive", "Variant", "Record", "Structure")


def strip_comments(text: str, *, keep_offsets: bool = False) -> str:
    """Replace nested `(* ... *)` comments with whitespace while preserving string literals and line numbers.

    By default, each outer comment is replaced by its newlines (or a single space if
    single-line). With `keep_offsets=True`, each comment character other than `\\n` is
    replaced by a space so character offsets remain aligned with `text`.
    """
    blank = _spaces if keep_offsets else _separator
    out: list[str] = []
    start = 0
    for region in prooflex.regions(text, strings_in_comments=True):
        if region.kind == "comment":
            out.append(text[start:region.start])
            out.append(blank(text, region.start, region.end))
            start = region.end
    out.append(text[start:])
    return "".join(out)


def _separator(text: str, start: int, end: int) -> str:
    """Return the newlines inside `text[start:end]`, or a single space if there are none."""
    return "\n" * text.count("\n", start, end) or " "


def _spaces(text: str, start: int, end: int) -> str:
    """Replace non-newline characters in `text[start:end]` with spaces of equal length."""
    return "\n".join(" " * len(line) for line in text[start:end].split("\n"))


def sentences(text: str) -> list[str]:
    """Return all comment-stripped, whitespace-trimmed Rocq sentences in `text`."""
    code = strip_comments(text)
    if '"' not in code:
        return [trimmed for s in SENTENCE_END.split(code) if (trimmed := s.strip())]
    found: list[str] = []
    start = 0
    for end in sentence_ends(code):
        found.append(code[start:end])
        start = end + 1
    found.append(code[start:])
    return [trimmed for s in found if (trimmed := s.strip())]


def sentence_ends(code: str) -> list[int]:
    """Return the character offsets of sentence-ending periods in comment-free `code`."""
    if '"' not in code:
        return [end.start() for end in SENTENCE_END.finditer(code)]
    return [token.start() for token in _SENTENCE_TOKEN.finditer(code) if token.group() == "."]


def decorations(code: str, at: int = 0) -> tuple[list[re.Match[str]], int]:
    """Scan control flags, attributes, and bullets starting at `at` in comment-free `code`.

    Because bullets, braces, and goal selectors are standalone commands in Rocq 9.3's
    grammar, any control flags preceding a bullet apply to the bullet itself; the list
    of active decorations therefore resets at each bullet.
    """
    found: list[re.Match[str]] = []
    while (decoration := DECORATION.match(code, at)) is not None:
        if decoration.group("bullet") is not None:
            found.clear()
        found.append(decoration)
        at = decoration.end()
    return found, at


def void_flag(code: str, opened: int, ends: Sequence[int]) -> str | None:
    """Return `"Fail"` or `"Succeed"` if the command at `opened` is governed by that control flag."""
    before = bisect_left(ends, opened)
    start = ends[before - 1] + 1 if before else 0
    blank = _BLANK.match(code, start)
    found, at = decorations(code, blank.end() if blank else start)
    if at < opened:
        return None
    for decoration in found:
        if decoration.group("word") in VOID:
            return str(decoration.group("word"))
    return None


def local_requires(source: Path, stems: set[str]) -> set[str]:
    """Return the file stems in `stems` that `source` imports via `Require`."""
    return _requires(sentences(source.read_text(encoding="utf-8")), stems)


def _requires(statements: list[str] | tuple[str, ...], stems: set[str]) -> set[str]:
    """Extract imported module names from `statements` and intersect with local `stems`."""
    named: set[str] = set()
    for sentence in statements:
        found = REQUIRE.fullmatch(sentence)
        if found:
            prefix = found.group(1)
            named.update(f"{prefix}.{name}" if prefix else name
                         for name in found.group(2).split())
    return named & stems


@dataclass(frozen=True)
class SourceIndex:
    """Immutable snapshot of parsed `.v` sources, `Require` edges, and topological waves."""

    texts: Mapping[Path, str]
    statements: Mapping[Path, tuple[str, ...]]
    needs: Mapping[Path, frozenset[Path]]
    ordered: tuple[tuple[Path, ...], ...]
    imports: Mapping[Path, tuple[Path, ...]]

    @classmethod
    def read(cls, sources: list[Path]) -> SourceIndex:
        texts = {source: source.read_text(encoding="utf-8") for source in sources}
        statements = {source: tuple(sentences(text)) for source, text in texts.items()}
        by_stem = {source.stem: source for source in sources}
        stems = set(by_stem)
        needs = {source: frozenset(by_stem[stem] for stem in _requires(parsed, stems))
                 for source, parsed in statements.items()}
        ordered = tuple(tuple(wave) for wave in _waves(
            {source: set(required) for source, required in needs.items()}))
        closures: dict[Path, frozenset[Path]] = {}
        for wave in ordered:
            for source in wave:
                closures[source] = needs[source].union(
                    *(closures[required] for required in needs[source]))
        imports = {source: tuple(sorted(reached, key=lambda path: path.stem))
                   for source, reached in closures.items()}
        return cls(MappingProxyType(texts), MappingProxyType(statements),
                   MappingProxyType(needs), ordered, MappingProxyType(imports))


def marker_depths(text: str, marker: str) -> dict[int, int]:
    """Return the comment nesting depth before each occurrence of `marker` outside string literals."""
    depth = 0
    found: dict[int, int] = {}
    for token in re.finditer(r'\(\*|\*\)|"(?:[^"]|"")*"', text):
        if token.group() == "(*":
            if text.startswith(marker, token.start()):
                found[token.start()] = depth
            depth += 1
        elif token.group() == "*)":
            depth -= 1
    return found


def _dependencies(sources: list[Path]) -> dict[Path, set[Path]]:
    """Map each file in `sources` to the local files it imports via `Require`."""
    by_stem = {source.stem: source for source in sources}
    stems = set(by_stem)
    return {source: {by_stem[stem] for stem in local_requires(source, stems)}
            for source in sources}


def _waves(needs: dict[Path, set[Path]]) -> list[list[Path]]:
    sorter = TopologicalSorter(needs)
    # Drain acyclic predecessors even when a cycle exists so the error lists only blocked files.
    with suppress(CycleError):
        sorter.prepare()
    out: list[list[Path]] = []
    remaining = set(needs)
    while sorter.is_active():
        ready = sorted(sorter.get_ready())
        out.append(ready)
        sorter.done(*ready)
        remaining.difference_update(ready)
    if remaining:
        stuck = ", ".join(source.name for source in sorted(remaining))
        raise SystemExit(f"FAIL: a Require cycle among {stuck}; "
                         f"no compile order satisfies it")
    return out


def waves(sources: list[Path]) -> list[list[Path]]:
    """Return `sources` grouped into deterministic topological `Require` waves."""
    return _waves(_dependencies(sources))


def dependents(sources: list[Path], stem: str) -> list[list[Path]]:
    """Return the topological waves containing `stem` and every file that transitively Requires it."""
    needs = _dependencies(sources)
    reach = {source for source in sources if source.stem == stem}
    out: list[list[Path]] = []
    for wave in _waves(needs):
        affected = [source for source in wave
                    if source in reach or not needs[source].isdisjoint(reach)]
        if affected:
            reach.update(affected)
            out.append(affected)
    return out
