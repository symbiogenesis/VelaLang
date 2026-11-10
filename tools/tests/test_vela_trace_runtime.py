# SPDX-License-Identifier: Apache-2.0
"""Independent runtime inventory, cache freshness and bounded refusal controls."""

import hashlib
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import trace_runtime as runtime

INDEPENDENT_CASES = True


def _installation_inventory() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-runtime-inventory-") as temporary:
        base = Path(temporary)
        standard, extensions = base / "stdlib", base / "extensions"
        contents = {
            "stdlib/json/__init__.py": b"source",
            "stdlib/json/__pycache__/__init__.cpython-314.pyc": b"cached bytecode",
            "stdlib/site-packages/unrelated.py": b"third party",
            "stdlib/dist-packages/unrelated.py": b"third party",
            "stdlib/README.txt": b"documentation",
            "extensions/_json.so": b"extension",
            "lib/libpython3.14.so": b"shared Python",
            "lib/python314.zip": b"archived library",
        }
        for name, value in contents.items():
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        variables = {"DESTSHARED": str(extensions), "LDLIBRARY": "libpython3.14.so",
                     "LIBDIR": str(base / "lib")}
        with patch.object(runtime.sys, "platform", "linux"), \
                patch.object(runtime.sys, "base_prefix", str(base)), \
                patch.object(runtime.sysconfig, "get_path", return_value=str(standard)), \
                patch.object(runtime.sysconfig, "get_config_var", side_effect=variables.get):
            selected = runtime.installation_files()
            ensure({label: path.relative_to(base).as_posix() for label, path in selected.items()} == {
                "stdlib/json/__init__.py": "stdlib/json/__init__.py",
                "stdlib/json/__pycache__/__init__.cpython-314.pyc": "stdlib/json/__pycache__/__init__.cpython-314.pyc",
                "extensions/_json.so": "extensions/_json.so",
                "installation/lib/libpython3.14.so": "lib/libpython3.14.so",
                "installation/lib/python314.zip": "lib/python314.zip",
                "python-shared-library": "lib/libpython3.14.so",
            }, "runtime inventory differs from independently chosen files")
            expected = {label: hashlib.sha256(path.read_bytes()).hexdigest()
                        for label, path in selected.items()}
            ensure(runtime.identity() == hashlib.sha256(json.dumps(
                expected, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest(),
                "runtime identity differs from independent manifest digest")
            previous = runtime.identity()
            for name in ("stdlib/json/__init__.py", "stdlib/json/__pycache__/__init__.cpython-314.pyc",
                         "extensions/_json.so", "lib/libpython3.14.so", "lib/python314.zip"):
                (base / name).write_bytes(b"changed runtime file")
                current = runtime.identity()
                ensure(current != previous, f"runtime identity ignores {name}")
                previous = current
            added = standard / "new.py"
            added.write_bytes(b"new import")
            ensure(runtime.identity() != previous, "new runtime file retained identity")
            added.unlink()
            ensure(runtime.identity() == previous, "runtime deletion did not restore inventory")
            with patch.object(runtime, "MAX_FILES", 1):
                _refuses(runtime.installation_files)
            with patch.object(runtime, "MAX_BYTES", 1):
                _refuses(runtime.identity)
            (base / "lib/libpython3.14.so").unlink()
            _refuses(runtime.installation_files)


def _refuses(action: Callable[[], object]) -> None:
    try:
        action()
    except (OSError, ValueError):
        return
    raise AssertionError("unavailable or oversized Python runtime was accepted")


def _windows_inventory() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-runtime-windows-") as temporary:
        base = Path(temporary)
        for name in ("Lib/json.py", "DLLs/_json.pyd", "python314.dll", "vcruntime140.dll", "python314.zip"):
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"Windows runtime")
        variables = {"LDLIBRARY": "python314.dll", "LIBDIR": str(base / "libs")}
        with patch.object(runtime.sys, "platform", "win32"), \
                patch.object(runtime.sys, "base_prefix", str(base)), \
                patch.object(runtime.sysconfig, "get_path", return_value=str(base / "Lib")), \
                patch.object(runtime.sysconfig, "get_config_var", side_effect=variables.get):
            ensure(set(runtime.installation_files()) == {
                "stdlib/json.py", "extensions/_json.pyd", "installation/python314.dll",
                "installation/vcruntime140.dll", "installation/python314.zip", "python-shared-library",
            }, "Windows extension, archive or shared runtime omitted")
            (base / "DLLs/_json.pyd").unlink()
            (base / "DLLs").rmdir()
            _refuses(runtime.installation_files)


def _unavailable_inputs() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-runtime-missing-") as temporary:
        missing = Path(temporary) / "missing.py"
        with patch.object(runtime, "installation_files", return_value={"missing": missing}):
            _refuses(runtime.identity)
        with patch.object(runtime.sysconfig, "get_path", return_value=str(missing)):
            _refuses(runtime.installation_files)


def cases() -> list[Case]:
    return [Case("stdlib-cache-extension-and-shared-library-freshness", _installation_inventory),
            Case("windows-runtime-selection", _windows_inventory),
            Case("missing-runtime-inputs-refuse", _unavailable_inputs)]
