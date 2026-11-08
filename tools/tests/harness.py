# SPDX-License-Identifier: Apache-2.0
"""Shared test helpers and fixture builders.

Each module under `tools/tests/` exports `cases()` returning `Case` objects that
signal failure by raising. `ensure` raises `AssertionError` explicitly so checks
remain active under `python -O`. `sandbox_tree` builds a temporary git-tracked
repository for tests that mutate files or git state.
"""

import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

TOOLS = Path(__file__).resolve().parents[1]

type Lane = Literal["any", "host", "guest", "toolchain"]


@dataclass(frozen=True)
class Case:
    """A single test case (`fn` returns `None` on pass and raises on failure).

    `slow` cases run only under `--slow`. `lane` is `"any"`, `"host"`, `"guest"`, or
    `"toolchain"` (guest with the Sail opam switch provisioned).
    """

    name: str
    fn: Callable[[], None]
    slow: bool = False
    lane: Lane = "any"


def ensure(cond: bool, msg: str) -> None:
    """Raise `AssertionError(msg)` if `cond` is false, even under `python -O`."""
    if not cond:
        raise AssertionError(msg)


def with_env(name: str, value: str | None, fn: Callable[[], None]) -> None:
    """Run `fn` with environment variable `name` set to `value` (or unset if `None`), then restore it."""
    was = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        fn()
    finally:
        if was is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = was


@contextmanager
def sandbox_tree(files: dict[str, str]) -> Generator[Path]:
    """Yield a temporary git-tracked directory populated with `files` (relative path -> UTF-8 text)."""
    with tempfile.TemporaryDirectory(prefix="vela-test-") as td:
        root = Path(td).resolve()
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="")
        if any(Path(rel).parts[:1] == (".git",) for rel in files):
            _git(root, "init", "-q")
        else:
            directories, written = git_skeleton()
            admin = root / ".git"
            admin.mkdir()
            for rel in directories:
                (admin / rel).mkdir(parents=True, exist_ok=True)
            for rel, data, mode in written:
                (admin / rel).write_bytes(data)
                (admin / rel).chmod(mode)
        _git(root, "add", "-A")
        yield root


# Cached .git directory structure: (relative directory paths, (relative file path, bytes, mode)).
type Skeleton = tuple[tuple[str, ...], tuple[tuple[str, bytes, int], ...]]


@cache
def git_skeleton() -> Skeleton:
    """Return the cached `.git` skeleton produced by `git init` in a temporary directory."""
    with tempfile.TemporaryDirectory(prefix="vela-test-init-") as td:
        admin = Path(td).resolve() / ".git"
        _git(admin.parent, "init", "-q")
        # Reject an init redirected by GIT_DIR so we never cache an empty .git directory.
        if not (admin / "HEAD").is_file():
            raise RuntimeError(f"git init wrote no repository at {admin}")
        directories: list[str] = []
        written: list[tuple[str, bytes, int]] = []
        for dirpath, _dirnames, filenames in admin.walk():
            if dirpath != admin:
                directories.append(dirpath.relative_to(admin).as_posix())
            for name in filenames:
                path = dirpath / name
                written.append((path.relative_to(admin).as_posix(), path.read_bytes(),
                                stat.S_IMODE(path.stat().st_mode)))
    return tuple(sorted(directories)), tuple(sorted(written))


def cli_argv(root: Path, module: str, *args: str) -> list[str]:
    """Build a `sys.executable -c` command line that runs `module.main(args)` from `root / "tools"`."""
    return [sys.executable, "-c",
            "import sys; from importlib import import_module; "
            "sys.path.insert(0, sys.argv[1]); "
            "raise SystemExit(import_module(sys.argv[2]).main(sys.argv[3:]))",
            str(root / "tools"), module, *args]


def _git(root: Path, *args: str) -> None:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          encoding="utf-8", errors="replace", check=False, timeout=60)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} exited {done.returncode}: "
                           f"{done.stderr.strip()}")
