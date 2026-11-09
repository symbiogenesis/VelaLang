# SPDX-License-Identifier: Apache-2.0
"""Ordinary parser caching preserves identity, fresh qualification, and live users."""

import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Barrier, Event
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import parser

INDEPENDENT_CASES = True


@dataclass
class _Fixture:
    root: Path
    native: Path
    tools: dict[str, object] = field(default_factory=lambda: {"compiler": "fixture-1"})
    builds: int = 0

    @property
    def cache(self) -> Path:
        return self.native / "ordinary-cache"

    def run(self, arguments: list[str], directory: Path) -> str:
        if "-o" in arguments:
            self.builds += 1
            for name in (*parser.GENERATED, "vela-parser"):
                (directory / name).write_bytes(b"generated " + name.encode())
        return ""

    def toolchain(self, _root: Path) -> dict[str, object]:
        return self.tools.copy()


@contextmanager
def _fixture() -> Generator[_Fixture]:
    with tempfile.TemporaryDirectory(prefix="vela-parser-cache-") as temporary:
        root = Path(temporary)
        files = [*(f"tools/toolchain/parser/{name}" for name in parser.SOURCES),
                 "tools/opam/sail.lock", "tools/toolchain/parser.py", "tools/toolchain/surface.py",
                 *(f"examples/{name}.vela" for name in ("pure", "surface", "constants", "expressions"))]
        for name in files:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("authored input\n", encoding="utf-8")
        native = root / "native"
        native.mkdir()
        fixture = _Fixture(root, native)
        with (patch.object(parser, "_work_root", return_value=native),
              patch.object(parser, "_toolchain", side_effect=fixture.toolchain),
              patch.object(parser, "_run", side_effect=fixture.run)):
            yield fixture


def _hit_and_fresh_builds() -> None:
    with _fixture() as fixture:
        with parser.cached_build(fixture.root) as first, parser.cached_build(fixture.root) as second:
            ensure(first.directory == second.directory and fixture.builds == 1,
                   "concurrent users of identical inputs must share one immutable generation")
            ensure(first.receipt["status"] == "built" and "checked_parser" not in first.receipt,
                   "a cached build must not claim parser qualification")
        with parser.cached_build(fixture.root) as third:
            ensure(third.directory == first.directory and fixture.builds == 1,
                   "an unchanged, verified cache hit recompiled the parser")
        fresh = parser.build(fixture.root)
        another = parser.build(fixture.root)
        ensure(fixture.builds == 3 and fresh.directory != another.directory
               and fresh.directory.parent == fixture.native and first.directory.parent == fixture.cache,
               "explicit fresh builds must stay outside the ordinary cache")


def _changed_identity() -> None:
    with _fixture() as fixture:
        with parser.cached_build(fixture.root) as original:
            original_directory = original.directory
        for change in ("source", "toolchain", "commands"):
            if change == "source":
                (fixture.root / "tools/toolchain/parser/parser.mly").write_text("changed grammar\n", encoding="utf-8")
            elif change == "toolchain":
                fixture.tools["compiler"] = "fixture-2"
            flags = (*parser.GENERATION_FLAGS, "--fixture") if change == "commands" else parser.GENERATION_FLAGS
            with patch.object(parser, "GENERATION_FLAGS", flags), parser.cached_build(fixture.root) as changed:
                ensure(changed.directory != original_directory,
                       f"changed {change} reused the old cache generation")
                original_directory = changed.directory
        ensure(fixture.builds == 4 and len(list(fixture.cache.glob("entry-*"))) == 1,
               "identity changes must rebuild and remove obsolete unused generations")


def _damaged_cache() -> None:
    with _fixture() as fixture:
        with parser.cached_build(fixture.root) as built:
            directory = built.directory
        damages = [*parser.GENERATED, "vela-parser", "receipt", "nested-receipt", "oversized-receipt",
                   "status", "commands", "directory", "pointer", "oversized-pointer", "entry-file"]
        for damage in damages:
            if damage in {*parser.GENERATED, "vela-parser"}:
                (directory / damage).write_bytes(b"damaged output")
            elif damage == "receipt":
                (directory / "receipt.json").write_bytes(b'{"schema":1,"schema":1}')
            elif damage == "nested-receipt":
                (directory / "receipt.json").write_bytes(b"[" * 2_000 + b"]" * 2_000)
            elif damage == "oversized-receipt":
                (directory / "receipt.json").write_bytes(b" " * (parser.CACHE_RECEIPT_BYTES + 1))
            elif damage == "pointer":
                (fixture.cache / "current").write_text("../qualification-artifact\n", encoding="utf-8")
            elif damage == "oversized-pointer":
                (fixture.cache / "current").write_text(directory.name + " " * 129, encoding="utf-8")
            elif damage == "entry-file":
                shutil.rmtree(directory)
                directory.write_bytes(b"damaged entry")
            else:
                path = directory / "receipt.json"
                receipt = json.loads(path.read_text(encoding="utf-8"))
                receipt[damage] = "passed" if damage == "status" else "changed"
                path.write_text(json.dumps(receipt), encoding="utf-8")
            with parser.cached_build(fixture.root) as repaired:
                ensure(repaired.directory != directory and repaired.receipt["status"] == "built",
                       f"damaged {damage} was reused or promoted to qualified evidence")
                ensure(repaired.executable.read_bytes() == b"generated vela-parser",
                       "cache recovery failed to regenerate parser output")
                directory = repaired.directory
        ensure(fixture.builds == 1 + len(damages)
               and len(list(fixture.cache.glob("entry-*"))) == 1,
               "damaged generation recovery must keep the idle cache bounded")


def _failed_rebuild() -> None:
    with _fixture() as fixture:
        with parser.cached_build(fixture.root) as original:
            pass
        pointer = (fixture.cache / "current").read_bytes()
        preserved = fixture.native / "build-qualification"
        preserved.mkdir()
        (preserved / "receipt.json").write_text("qualification evidence", encoding="utf-8")
        (fixture.root / "tools/toolchain/parser/parser.mly").write_text("changed\n", encoding="utf-8")
        original_atomic = parser.atomic_path
        for failure in ("compile", "publication"):
            def compile_run(arguments: list[str], directory: Path, mode: str = failure) -> str:
                if mode == "compile":
                    raise RuntimeError("generator failed")
                return fixture.run(arguments, directory)

            @contextmanager
            def publish(path: Path) -> Generator[Path]:
                if path.name == "current":
                    raise OSError("publication failed")
                with original_atomic(path) as pending:
                    yield pending

            with patch.object(parser, "_run", side_effect=compile_run), \
                    patch.object(parser, "atomic_path", side_effect=publish):
                try:
                    with parser.cached_build(fixture.root):
                        raise AssertionError("a failed rebuild acquired a usable generation")
                except (RuntimeError, OSError) as error:
                    ensure("failed" in str(error), "cache cleanup hid the primary build failure")
            ensure((fixture.cache / "current").read_bytes() == pointer and original.executable.is_file()
                   and len(list(fixture.cache.glob("entry-*"))) == 1,
                   "failed reconstruction changed the previous publication or leaked its candidate")
            ensure((preserved / "receipt.json").read_text(encoding="utf-8") == "qualification evidence",
                   "ordinary cache cleanup removed qualification artifacts")


def _active_and_crashed_users() -> None:
    with _fixture() as fixture:
        with parser.cached_build(fixture.root) as old:
            abandoned = fixture.cache / f"lease-{old.directory.name}-abandoned.lock"
            abandoned.write_text("", encoding="utf-8")
            with parser.cached_build(fixture.root):
                ensure(not abandoned.exists() and old.executable.is_file(),
                       "current-generation pruning kept an abandoned marker or removed a live generation")
            (fixture.root / "tools/toolchain/parser/parser.mly").write_text("changed\n", encoding="utf-8")
            with parser.cached_build(fixture.root) as current:
                ensure(old.executable.is_file() and current.directory != old.directory,
                       "rebuilding pruned a generation still leased by a running user")
            ensure(old.executable.is_file(), "an idle current generation invalidated another live user")
        ensure(not old.directory.exists() and current.directory.is_dir(),
               "the final old user must release its obsolete generation")
        marker = fixture.cache / f"lease-{current.directory.name}-crashed.lock"
        child = subprocess.run(
            [sys.executable, "-c", "import os,sys; from filelock import FileLock; "
             "lock = FileLock(sys.argv[1]); lock.acquire(timeout=2); os._exit(23)", str(marker)],
            capture_output=True, check=False, timeout=15)
        ensure(child.returncode == 23 and marker.is_file(), "crashed-user fixture did not acquire its lease")
        fixture.tools["compiler"] = "fixture-2"
        with parser.cached_build(fixture.root):
            ensure(not marker.exists() and not current.directory.exists(),
                   "a crashed process's released OS lock prevented stale generation cleanup")


def _concurrent_builders() -> None:
    with _fixture() as fixture:
        original_compile = parser._compile
        compiling, contender, release = Event(), Event(), Event()
        readers = Barrier(2)

        def delayed(root: Path, directory: Path, tools: dict[str, object]) -> parser.Build:
            compiling.set()
            ensure(release.wait(10), "concurrent-build fixture was not released")
            return original_compile(root, directory, tools)

        def consume(*, second: bool = False) -> Path:
            if second:
                contender.set()
            with parser.cached_build(fixture.root) as compiled:
                readers.wait(timeout=10)
                ensure(compiled.executable.is_file(), "another reader pruned this live generation")
                return compiled.directory

        with patch.object(parser, "_compile", side_effect=delayed), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(consume)
            try:
                ensure(compiling.wait(10), "first concurrent build did not begin")
                second = pool.submit(consume, second=True)
                ensure(contender.wait(10), "second concurrent user did not begin")
            finally:
                release.set()
            ensure(first.result(timeout=15) == second.result(timeout=15) and fixture.builds == 1,
                   "contending ordinary users rebuilt or observed different partial generations")


def cases() -> list[Case]:
    return [Case("ordinary parser cache hits preserve fresh-build behavior", _hit_and_fresh_builds),
            Case("ordinary parser cache binds inputs, tools, and commands", _changed_identity),
            Case("ordinary parser cache repairs damaged outputs and receipts", _damaged_cache),
            Case("ordinary parser cache preserves publication on failure", _failed_rebuild),
            Case("ordinary parser cache retains active users and recovers crashed leases", _active_and_crashed_users),
            Case("ordinary parser cache serializes builders and shares readers", _concurrent_builders)]
