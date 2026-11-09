# SPDX-License-Identifier: Apache-2.0
"""Repository document and Git index loader for static checks.

Parses tracked Markdown files once, recording raw text, line-start offsets for
binary-search line resolution, fenced/indented code masks, headings, and HTML
`<a id="...">` anchors outside code blocks.
"""

import bisect
import os
import re
import subprocess
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from toolchain import proofenv

if TYPE_CHECKING:
    from markdown_it import MarkdownIt

# Semantic readers retain their prescribed line forms. General Markdown structure
# comes from the shared CommonMark parser, without serializing its tokens to disk.
ANCHOR_RE = re.compile(r'<a id="([^"]+)"')

_TAG_RE = re.compile(r"<[^>]+>")
_PUNCT_RE = re.compile(r"[^\w\s-]")
_SPACE_RE = re.compile(r"\s+")


@cache
def _markdown() -> MarkdownIt:
    # The launcher imports corpus to find its root before entering the locked
    # environment. Resolve third-party parser code only when a document is read.
    from markdown_it import MarkdownIt  # noqa: PLC0415

    # Structural readers need block maps and the unexpanded inline token's
    # content, never its children. Keep the same block grammar and normalization;
    # omitting inline expansion avoids parsing every document's links twice.
    return MarkdownIt("commonmark", {"html": True}).enable("table").disable("inline")


def _syntax(lines: list[str]) -> tuple[list[bool], list[tuple[int, str]]]:
    """Read code regions and headings from maintained token source maps."""
    fenced = [False] * len(lines)
    headings: list[tuple[int, str]] = []
    tokens = _markdown().parse("\n".join(line.removesuffix("\r") for line in lines))
    for index, token in enumerate(tokens):
        if token.type not in {"fence", "code_block", "heading_open"}:
            continue
        if token.map is None:
            raise ValueError(f"Markdown {token.type} token has no source map")
        start, end = token.map
        if not 0 <= start < end <= len(lines):
            raise ValueError(f"Markdown {token.type} token has an invalid source map")
        if token.type in {"fence", "code_block"}:
            fenced[start:end] = [True] * (end - start)
        else:
            if index + 1 == len(tokens) or tokens[index + 1].type != "inline":
                raise ValueError("Markdown heading has no inline content token")
            headings.append((start, tokens[index + 1].content))
    return fenced, headings


def slug(heading: str) -> str:
    """A heading's fragment id: tags and backticks vanish, punctuation vanishes,
    spaces hyphenate. Markdown makes no distinction between a slug and a declared
    bookmark, so a link may name either."""
    text = _TAG_RE.sub("", heading).replace("`", "").strip().lower()
    return _SPACE_RE.sub("-", _PUNCT_RE.sub("", text))


@dataclass
class Document:
    name: str
    raw: str
    lines: list[str]
    starts: list[int]
    fenced: list[bool]
    targets: set[str] = field(default_factory=set)
    headings: list[tuple[int, str]] = field(default_factory=list)

    def line_of(self, offset: int) -> int:
        """The 0-based line containing a raw-text offset."""
        return bisect.bisect_right(self.starts, offset) - 1


def _read(path: Path, name: str) -> Document:
    try:
        raw = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        # Include the document path when UTF-8 decoding fails.
        raise RuntimeError(f"{name} is not valid UTF-8: {exc}") from exc

    return from_text(raw, name)


def from_text(raw: str, name: str) -> Document:
    """Build a `Document` from decoded text, computing line offsets, code masks, and headings."""
    parts = raw.split("\n")
    starts: list[int] = []
    offset = 0
    for part in parts:
        starts.append(offset)
        offset += len(part) + 1

    body = parts[:-1] if parts and parts[-1] == "" else parts
    lines = [p.removesuffix("\r") for p in body]

    try:
        fenced, headings = _syntax(lines)
    except ValueError as exc:
        raise RuntimeError(f"{name}: {exc}") from exc
    return Document(name=name, raw=raw, lines=lines, starts=starts, fenced=fenced,
                    headings=headings)


# Directory prefix excluded from Markdown corpus loading.
UNREAD_PREFIX = "model/"

# an index entry's mode, which is what tells a submodule from a file
GITLINK_MODE = "160000"
GIT_TIMEOUT = 30


class Corpus:
    """The tracked Markdown of the repository, and what a link may name in it."""

    def __init__(self, root: Path, docs: list[Document], gitlinks: dict[str, str],
                 tracked: list[str], indexed: set[str] | None = None) -> None:
        self.root = root
        self.docs = docs
        self.by_name = {d.name: d for d in docs}
        # Submodule path -> indexed commit. Link checks use path membership;
        # pin checks use the commit without another Git invocation.
        self.gitlinks = gitlinks
        # Tracked files present in the working tree, including non-Markdown and
        # model files. Each whole-tree check defines its own exclusions.
        self.tracked = tracked
        # Stage-zero files, including working-tree deletions. Rules asking whether
        # the index carries a file need its membership, not a subprocess reading
        # its entire blob. Conflicted entries have no stage zero; gitlinks point at
        # commits rather than blobs. Neither can supply an indexed file.
        self.indexed = frozenset(tracked if indexed is None else indexed)

        # Semantic citations use each file's own heading and bookmark targets.
        for d in docs:
            for _, heading in d.headings:
                d.targets.add(slug(heading))

        self.buried: list[str] = []              # anchors code displays instead of declaring
        self.declared_twice: list[str] = []
        for d in docs:
            self._read_anchors(d)

    def _read_anchors(self, d: Document) -> None:
        here: dict[str, int] = {}
        for m in ANCHOR_RE.finditer(d.raw):
            i = d.line_of(m.start())
            ident = m.group(1)
            if d.fenced[i]:
                self.buried.append(
                    f"{d.name}:{i + 1} buries #{ident} in a code block, "
                    "where it is text and not a bookmark"
                )
                continue
            d.targets.add(ident)
            here[ident] = here.get(ident, 0) + 1
            if here[ident] == 2:
                self.declared_twice.append(
                    f"{d.name} declares #{ident} more than once; "
                    "a link to it resolves to whichever comes first"
                )

    def get(self, name: str) -> Document | None:
        return self.by_name.get(name)


def _git_environment(root: Path) -> dict[str, str] | None:
    """Return an environment dict with [proofenv.py](proofenv.py)'s Git worktree overlay, or `None` if unneeded.

    A linked worktree created by Windows Git stores a Windows path in its `.git`
    pointer file; inside WSL, `proofenv.git_env(root)` translates that pointer into
    `GIT_DIR` and `GIT_WORK_TREE` so `git` commands succeed.
    """
    overlay = proofenv.git_env(root)
    return {**os.environ, **overlay} if overlay else None


def _git(root: Path, *args: str) -> list[str]:
    """Read a NUL-framed listing without quoting or newline translation of paths."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, check=False,
            env=_git_environment(root), stdin=subprocess.DEVNULL, timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"git {' '.join(args)} exceeded {GIT_TIMEOUT} seconds") from error
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout.decode("utf-8").split("\0")[:-1]


def find_root(start: Path | None = None) -> Path:
    """Locate the repository root by walking upward from `start` (or this file)."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / ".git").exists() and (candidate / "docs" / "language" / "reference.md").exists():
            return candidate
    raise SystemExit(
        f"no repository root above '{here}': expected a .git and docs/language/reference.md"
    )


@dataclass(frozen=True)
class Index:
    """The index's file membership and pins, without reading the working tree.

    `files` includes deleted and unmerged paths, once each in Git's order.
    `indexed` is narrower: only stage-zero files can supply an indexed blob.
    """

    files: tuple[str, ...]
    gitlinks: dict[str, str]
    indexed: frozenset[str]


def read_index(root: Path) -> Index:
    """Read file membership, stage-zero membership and gitlinks in one Git call.

    Callers that only need the index need not parse every document or stat every
    tracked path. Working-tree existence is deliberately left to each reader.
    """
    files: list[str] = []
    gitlinks: dict[str, str] = {}
    indexed: set[str] = set()
    seen: set[str] = set()
    for entry in _git(root, "ls-files", "--stage", "--full-name", "-z"):
        staged, _, path = entry.partition("\t")
        mode, oid, stage = staged.split()
        if stage == "0" and mode != GITLINK_MODE:
            indexed.add(path)
        # A conflict lists each stage separately. Retain the first entry's kind
        # and pin, as load does, rather than silently choosing the last side.
        if path in seen:
            continue
        seen.add(path)
        if mode == GITLINK_MODE:
            gitlinks[path] = oid
        else:
            files.append(path)
    return Index(tuple(files), gitlinks, frozenset(indexed))


def load(root: Path) -> Corpus:
    """Load all tracked Markdown documents and gitlinks from the repository at `root`.

    Uses `git ls-files` so ignored files and submodule contents are excluded
    automatically, and skips tracked paths deleted from the working tree so
    downstream checks can report missing files cleanly instead of aborting on I/O
    errors.
    """
    # Read file membership, gitlink paths and pinned commits in one listing.
    # Gitlinks resolve for link and pin checks even when submodules are uninitialized.
    index = read_index(root)
    names: list[str] = []
    tracked: list[str] = []
    for path in index.files:
        if not (root / path).is_file():
            continue
        tracked.append(path)
        if path.endswith(".md") and not path.startswith(UNREAD_PREFIX):
            names.append(path)

    docs = []
    for n in sorted(names):
        try:
            docs.append(_read(root / n, n))
        except FileNotFoundError:
            # Treat deletion after listing like any missing file: let each rule
            # report its absence rather than aborting the corpus load.
            continue
    return Corpus(root, docs, index.gitlinks, sorted(tracked), set(index.indexed))
