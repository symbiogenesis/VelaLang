# SPDX-License-Identifier: Apache-2.0
"""Locked Python dependencies and a separate environment for each checkout and OS."""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tomllib
from pathlib import Path

from toolchain import env, pyversion

READY = "_VOS_TOOL_ENV"
PROJECT = "tools/pyproject.toml"
LOCK = "tools/uv.lock"
REQUIRED_DEV_PINS = frozenset({"charset-normalizer", "reuse", "ruff", "rumdl", "ty"})


def checker_pins(root: Path) -> dict[str, str]:
    project = tomllib.loads((root / PROJECT).read_text(encoding="utf-8"))
    dependencies = project["dependency-groups"]["dev"]
    if not isinstance(dependencies, list):
        raise TypeError("dependency-groups.dev must be a list of exact checker pins")
    pins: dict[str, str] = {}
    for dependency in dependencies:
        if not isinstance(dependency, str):
            raise TypeError("every checker dependency must be an exact pin")
        spec, _, _marker = dependency.partition(";")
        name, separator, version = spec.strip().partition("==")
        if (not separator or not name or not version
                or any(ch.isspace() for ch in name + version) or name in pins):
            raise ValueError(f"invalid or duplicate checker pin: {dependency}")
        pins[name] = version
    if set(pins) != REQUIRED_DEV_PINS:
        raise ValueError(
            "dependency-groups.dev must pin " + ", ".join(sorted(REQUIRED_DEV_PINS)))
    return pins


def _locked_wheel_hash(root: Path, package_name: str, version: str, suffix: str) -> str:
    lock = tomllib.loads((root / LOCK).read_text(encoding="utf-8"))
    packages = lock.get("package")
    if not isinstance(packages, list):
        raise TypeError(f"{LOCK} has no package list")
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        if pkg.get("name") == package_name and pkg.get("version") == version:
            wheels = pkg.get("wheels")
            if not isinstance(wheels, list):
                break
            for wheel in wheels:
                if isinstance(wheel, dict):
                    url = wheel.get("url")
                    digest = wheel.get("hash")
                    if isinstance(url, str) and url.endswith(suffix) and isinstance(digest, str):
                        return digest
    raise ValueError(f"{LOCK} does not record a {suffix} wheel for {package_name}=={version}")


def ensure_rumdl(root: Path) -> Path | None:
    """Resolve the pinned rumdl binary, provisioning the x86_64 wheel on win_arm64."""
    scripts = Path(sysconfig.get_path("scripts"))
    candidate = scripts / ("rumdl.exe" if sys.platform == "win32" else "rumdl")
    if candidate.is_file():
        return candidate
    if sys.platform != "win32" or platform.machine().upper() != "ARM64":
        return None
    pin = checker_pins(root)["rumdl"]
    wheel_hash = _locked_wheel_hash(root, "rumdl", pin, "win_amd64.whl")
    target = root / "out" / "rumdl-win32"
    binary = target / "bin" / "rumdl.exe"
    stamp = target / ".lock-hash"
    if binary.is_file() and stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == wheel_hash:
        return binary
    uv = shutil.which("uv")
    if uv is None:
        return None
    target.mkdir(parents=True, exist_ok=True)
    requirement = f"rumdl=={pin} --hash={wheel_hash}\n"
    done = subprocess.run(
        [uv, "pip", "install", "--no-build", "--require-hashes", "--no-deps",
         "--python-platform", "x86_64-pc-windows-msvc", "--target", str(target), "-r", "-"],
        input=requirement, text=True, capture_output=True, check=False, timeout=60)
    if done.returncode != 0 or not binary.is_file():
        return None
    stamp.write_text(wheel_hash + "\n", encoding="utf-8", newline="\n")
    return binary


def environment(root: Path, platform_name: str) -> Path:
    if platform_name == "linux" and env.filesystem(root.resolve()) in env.CROSS_OS_FILESYSTEMS:
        target = env.lane_root(env.lane_of(root)).resolve() / "venv-linux"
        if (target.is_relative_to(root.resolve())
                # These are refused locations, never temporary-file destinations.
                or target.is_relative_to(Path("/tmp"))  # noqa: S108
                or target.is_relative_to(Path("/var/tmp"))  # noqa: S108
                or env.filesystem(target) in env.CROSS_OS_FILESYSTEMS | env.VOLATILE_FILESYSTEMS):
            raise ValueError(f"the guest Python environment needs persistent native storage: {target}")
        return target
    return root / "out" / f"venv-{platform_name}"


def identity(root: Path, platform_name: str) -> str:
    digest = hashlib.sha256(str(environment(root, platform_name)).encode("utf-8"))
    for name in (PROJECT, LOCK):
        digest.update((root / name).read_bytes())
    return digest.hexdigest()


def bootstrap(root: Path, argv: list[str]) -> int | None:
    """Synchronize before dispatch; children inherit the settled environment."""
    try:
        pyversion.require_supported(root)
    except (OSError, ValueError) as err:
        print(str(err), file=sys.stderr)
        return 1
    try:
        target = environment(root, sys.platform)
        token = identity(root, sys.platform)
    except (OSError, ValueError) as err:
        print(f"the tools require {PROJECT} and {LOCK}: {err}", file=sys.stderr)
        return 1
    if Path(sys.prefix) == target and os.environ.get(READY) == token:
        return None
    uv = shutil.which("uv")
    if uv is None:
        print(f"uv is required; install the version in {PROJECT}'s "
              "tool.uv.required-version, then rerun this command", file=sys.stderr)
        return 1
    child_env = os.environ.copy()
    child_env.pop("VIRTUAL_ENV", None)
    child_env["UV_PROJECT_ENVIRONMENT"] = str(target)
    child_env["PYTHONUTF8"] = "1"
    child_env[READY] = token
    try:
        return subprocess.run(
            [uv, "run", "--project", str((root / PROJECT).parent), "--locked", "--exact",
             "--no-python-downloads", "python",
             str(root / "tools" / "run.py"), *argv],
            env=child_env, check=False).returncode
    except OSError as err:
        print(f"the tools environment could not be started: {err}", file=sys.stderr)
        return 1
