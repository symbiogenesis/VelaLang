# SPDX-License-Identifier: Apache-2.0
"""Bounded Python installation file identities for compiler measurements."""

import hashlib
import json
import sys
import sysconfig
from pathlib import Path

MAX_FILES = 20_000
MAX_BYTES = 512 * 1024 * 1024
_SUFFIXES = frozenset({".py", ".pyc", ".pyd", ".dll", ".so", ".zip"})


def _raise(error: OSError) -> None:
    raise error


def installation_files() -> dict[str, Path]:
    """Select stdlib, bytecode, extensions, archives and Python shared libraries.

    Third-party package trees and operating-system libraries are outside this
    inventory. Bytecode is included because imports can execute cached code.
    """
    standard = Path(sysconfig.get_path("stdlib"))
    if not standard.is_dir():
        raise ValueError("Python standard library is unavailable")
    roots = {"stdlib": standard}
    extension = sysconfig.get_config_var("DESTSHARED")
    if isinstance(extension, str) and extension:
        roots["extensions"] = Path(extension)
    if sys.platform == "win32":
        roots["extensions"] = Path(sys.base_prefix) / "DLLs"
    files: dict[str, Path] = {}

    def retain(label: str, path: Path) -> None:
        if len(files) >= MAX_FILES:
            raise ValueError("Python runtime inventory exceeds file limit")
        files[label] = path

    for label, root in roots.items():
        if not root.is_dir():
            raise ValueError("Python extension directory is unavailable")
        for directory, folders, names in root.walk(on_error=_raise):
            folders[:] = sorted(name for name in folders if name not in {"site-packages", "dist-packages"})
            for name in sorted(names):
                path = directory / name
                if path.is_symlink() and path.is_dir():
                    raise ValueError("Python runtime inventory cannot traverse directory aliases")
                if path.suffix in _SUFFIXES:
                    retain(f"{label}/{path.relative_to(root).as_posix()}", path)
    base = Path(sys.base_prefix)
    for directory in (base, base / "lib"):
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix in {".dll", ".so", ".zip"}:
                    retain(f"installation/{path.relative_to(base).as_posix()}", path)
    library = sysconfig.get_config_var("LDLIBRARY")
    libdir = sysconfig.get_config_var("LIBDIR")
    if sys.platform == "win32":
        libdir = str(base)
    if isinstance(library, str) and isinstance(libdir, str) and library.endswith((".dll", ".so")):
        path = Path(libdir) / library
        if not path.is_file():
            raise ValueError("Python shared library is unavailable")
        retain("python-shared-library", path)
    if not files:
        raise ValueError("Python runtime inventory is empty")
    return files


def identity() -> str:
    """Hash the declared inventory; missing, unreadable and oversized files refuse."""
    inventory: dict[str, str] = {}
    size = 0
    for label, path in sorted(installation_files().items()):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while raw := stream.read(min(1024 * 1024, MAX_BYTES - size + 1)):
                size += len(raw)
                if size > MAX_BYTES:
                    raise ValueError("Python runtime inventory exceeds byte limit")
                digest.update(raw)
        inventory[label] = digest.hexdigest()
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("ascii")).hexdigest()
