# SPDX-License-Identifier: Apache-2.0
"""Proof-toolchain paths, filesystem classification, worktree Git overlays, and worker sizing.

Shared by [env.py](env.py) and [corpus.py](corpus.py) without
importing model-build state from [env.py](env.py).
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Default guest build root for all worktree lanes.
BUILD_ROOT = Path("/root/build")

# Filesystem types that cross the host/guest OS boundary or network mounts.
CROSS_OS_FILESYSTEMS: frozenset[str] = frozenset({"9p", "drvfs", "virtiofs", "cifs", "smb3"})

# In-memory filesystems that do not persist across WSL instance restarts.
VOLATILE_FILESYSTEMS: frozenset[str] = frozenset({"tmpfs", "ramfs"})

# Linux mount table read by `filesystem()`.
MOUNTINFO = Path("/proc/self/mountinfo")

OCAML_VERSION = "5.4.1"
OPAM_LOCKS = Path(__file__).resolve().parents[1] / "opam"

ROCQ_VERSION = "9.3.0"
ROCQ_SWITCH = f"verifiedos-rocq-{ROCQ_VERSION}-ocaml-{OCAML_VERSION}"

ROCQ_INSTALL: tuple[tuple[str, ...], ...] = (
    ("opam", "switch", "create", ROCQ_SWITCH, "--repos=rocq-released,default",
     "--empty", "--no-switch", "-y"),
    ("opam", "switch", "import", str(OPAM_LOCKS / "rocq.lock"),
     f"--switch={ROCQ_SWITCH}", "-y"),
)


def install_line(steps: tuple[tuple[str, ...], ...]) -> str:
    """Format a sequence of command tuples as a shell command line joined by `&&`."""
    return " && ".join(shlex.join(step) for step in steps)


def _env_path(name: str, default: Path) -> Path:
    return Path(os.environ[name]) if bool(os.environ.get(name)) else default


def _gitdir_pointer(root: Path) -> str | None:
    """Return the raw `gitdir:` target from a linked worktree's `.git` file, or `None`."""
    dot_git = root / ".git"
    if not dot_git.is_file():
        return None
    try:
        pointer = dot_git.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not pointer.startswith("gitdir:"):
        return None
    return pointer.removeprefix("gitdir:").strip()


def lane_of(root: Path, *, declared: bool = True) -> str:
    """Return the worktree lane name for `root`, or `""` for the primary worktree.

    Honors `VOS_LANE` when `declared=True`. Otherwise inspects `.git`: if it is a
    pointer file targeting `<repo>/.git/worktrees/<name>`, returns `<name>` in
    lowercase (distinguishing linked worktrees from submodules under `.git/modules/`).
    """
    if declared:
        override = os.environ.get("VOS_LANE")
        if override is not None:
            return override.strip().lower()
    target = _gitdir_pointer(root)
    if target is None:
        return ""
    admin = PurePosixPath(target.replace("\\", "/"))
    return admin.name.lower() if admin.parent.name == "worktrees" else ""


def _cpus() -> int:
    """Return the number of CPUs available to this process (at least 1)."""
    return os.process_cpu_count() or 1


def _read_mem_available_mb() -> int | None:
    """Guest memory available without swapping, in MiB; None when unreadable."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                fields = line.split()
                if len(fields) == 3 and fields[2] == "kB":
                    value = int(fields[1])
                    if value >= 0:
                        return value // 1024
                return None
    except OSError, ValueError:
        return None
    return None


# Per-worker memory budgets in MiB for proof compilation and kernel re-checking.
PROOF_COMPILE_WORKER_MIB = 1024
PROOF_KERNEL_WORKER_MIB = 10240


@dataclass(frozen=True)
class Workers:
    """Computed worker limit along with the CPU count and `MemAvailable` reading (MiB) used to size it."""

    jobs: int
    cpus: int
    mem_available_mb: int | None


def proof_jobs(*, kernel: bool = False) -> int:
    """Return the worker count for proof compilation (`kernel=False`) or kernel checking (`kernel=True`)."""
    return proof_workers(kernel=kernel).jobs


def proof_workers(*, kernel: bool = False) -> Workers:
    """Size proof workers after a 2 GiB reserve using `PROOF_KERNEL_WORKER_MIB` or `PROOF_COMPILE_WORKER_MIB`."""
    return size_workers(PROOF_KERNEL_WORKER_MIB if kernel else PROOF_COMPILE_WORKER_MIB,
                        fallback=1 if kernel else 4,
                        label="kernel" if kernel else "compile/audit")


def worker_jobs(memory_mb: int, *, fallback: int = 1, label: str = "worker") -> int:
    """Limit workers to usable CPUs and a per-worker MiB budget after a 2 GiB reserve."""
    return size_workers(memory_mb, fallback=fallback, label=label).jobs


def size_workers(memory_mb: int, *, fallback: int = 1, label: str = "worker") -> Workers:
    """Compute worker count from usable CPUs and `/proc/meminfo` `MemAvailable` with a 2 GiB reserve."""
    cpus = _cpus()
    available = _read_mem_available_mb()
    if available is None:
        jobs = min(cpus, fallback)
        print(f"WARNING no MemAvailable figure from /proc/meminfo: automatic {label} "
              f"jobs limited to {jobs}; use --jobs to override", file=sys.stderr)
        return Workers(jobs, cpus, None)
    return Workers(min(cpus, max(1, (available - 2048) // memory_mb)), cpus, available)


def build_root() -> Path:
    """Return the guest build root (`VOS_BUILD_ROOT` or `BUILD_ROOT`)."""
    return _env_path("VOS_BUILD_ROOT", BUILD_ROOT)


def lane_dir(root: Path, lane: str) -> Path:
    """Return `root / f"lane-{lane}"` for a named worktree lane, or `root` for the primary worktree."""
    return root / f"lane-{lane}" if lane else root


def lane_root(lane: str) -> Path:
    """Where the named lane's guest outputs land, under this machine's build root."""
    return lane_dir(build_root(), lane)


def mount_type(mountinfo: str, path: PurePosixPath | str) -> str:
    """Return the filesystem type of the longest mount point in `mountinfo` prefixing `path`, or `""`."""
    wanted = PurePosixPath(path).as_posix()
    best, kind = -1, ""
    for line in mountinfo.splitlines():
        head, sep, tail = line.partition(" - ")
        fields = head.split()
        if not sep or len(fields) < 5:
            continue
        point = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), fields[4])
        holds = (wanted == point or (point == "/" and wanted.startswith("/"))
                 or wanted.startswith(point.rstrip("/") + "/"))
        if holds and len(point) > best:
            kinds = tail.split()
            best, kind = len(point), kinds[0] if kinds else ""
    return kind


def filesystem(path: Path | str) -> str:
    """Return the filesystem type for `path` from `/proc/self/mountinfo`, or `""` when unavailable."""
    try:
        text = MOUNTINFO.read_text(encoding="utf-8")
    except OSError:
        return ""
    return mount_type(text, Path(path).as_posix())


def opam_root() -> Path:
    """Return the opam root directory (`OPAMROOT` or `~/.opam`)."""
    return _env_path("OPAMROOT", Path.home() / ".opam")


def rocq_command() -> list[str]:
    """Resolve the Rocq compiler command (`[rocq, "c"]`) from `VOS_ROCQ`, `ROCQ_SWITCH`, or `PATH`."""
    override = os.environ.get("VOS_ROCQ")
    if bool(override):
        return [override, "c"]
    pinned = opam_root() / ROCQ_SWITCH / "bin" / "rocq"
    if pinned.is_file():
        return [str(pinned), "c"]
    found = shutil.which("rocq")
    if bool(found):
        return [found, "c"]
    raise SystemExit(f"no prover: neither $VOS_ROCQ, nor {pinned}, nor rocq on PATH. "
                     f"{install_line(ROCQ_INSTALL)}")


def rocqchk_command() -> list[str]:
    """Resolve the Rocq kernel checker (`[rocqchk]`) from `VOS_ROCQCHK`, `ROCQ_SWITCH`, or `PATH`."""
    override = os.environ.get("VOS_ROCQCHK")
    if bool(override):
        return [override]
    pinned = opam_root() / ROCQ_SWITCH / "bin" / "rocqchk"
    if pinned.is_file():
        return [str(pinned)]
    found = shutil.which("rocqchk")
    if bool(found):
        return [found]
    raise SystemExit(f"no kernel re-checker: neither $VOS_ROCQCHK, nor {pinned}, nor "
                     f"rocqchk on PATH. {install_line(ROCQ_INSTALL)}")


def git_dir(root: Path) -> Path | None:
    """Translate a Windows-created linked worktree's `.git` pointer via `wslpath` when running in WSL.

    Returns `VOS_GIT_DIR` when set, the translated Linux path when `.git` contains a
    Windows drive path (`C:/...`), or `None` when no translation is needed.
    """
    override = os.environ.get("VOS_GIT_DIR")
    if bool(override):
        return Path(override)
    target = _gitdir_pointer(root)
    if target is None:
        return None
    if Path(target).is_dir():
        return None
    if not re.match(r"^[A-Za-z]:[/\\]", target):
        return None
    tool = shutil.which("wslpath")
    if tool is None:
        return None
    done = subprocess.run([tool, "-u", target], capture_output=True, text=True, check=False)
    translated = Path(done.stdout.strip())
    return translated if done.returncode == 0 and translated.is_dir() else None


def git_overlay(admin: Path, root: Path) -> dict[str, str]:
    """Return `GIT_DIR` and `GIT_WORK_TREE` environment bindings for a translated worktree."""
    return {"GIT_DIR": str(admin), "GIT_WORK_TREE": str(root)}


def git_env(root: Path) -> dict[str, str]:
    """Return the `GIT_DIR`/`GIT_WORK_TREE` environment overlay for `root`, or `{}` if none is needed."""
    admin = git_dir(root)
    return {} if admin is None else git_overlay(admin, root)
