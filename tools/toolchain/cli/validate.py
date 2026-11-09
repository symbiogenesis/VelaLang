# SPDX-License-Identifier: Apache-2.0
"""Run an explicit local validation profile with sequential, logged verdicts."""

import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from toolchain import corpus, env, proofenv
from toolchain.cli.test import switches

DEFAULT_JOBS = 4
TAIL_BYTES = 16_384


@dataclass(frozen=True)
class Step:
    name: str
    command: tuple[str, ...]
    seconds: int


def require_toolchains() -> int:
    """Refuse full validation when either exact native opam switch is absent."""
    installed = switches()
    missing = sorted({env.SAIL_SWITCH, proofenv.ROCQ_SWITCH} - installed)
    if missing:
        print("FAIL full validation: missing required opam switch(es): " + ", ".join(missing))
        return 1
    print("Both required Sail and Rocq opam switches are installed; qualification checks their contents.")
    return 0


def plan(platform: str, jobs: int, *, full: bool = False, static: bool = False) -> tuple[Step, ...]:
    """Select complete command invocations without duplicating native qualification."""
    if platform not in {"win32", "linux"} or jobs < 1 or (full and static):
        raise ValueError("validation requires Windows/Linux, positive jobs and one profile")
    local = (sys.executable, "tools/run.py")
    guest = ("wsl", "-u", "root", "-e", "python3", "tools/run.py") if platform == "win32" else local
    if static:
        return (Step("typecheck", (*local, "typecheck"), 600),
                Step("markdown", (*local, "markdown"), 600))
    if not full:
        return (Step("gate", (*local, "gate"), 900),
                Step("tests", (*local, "test", "--jobs", str(jobs)), 1800))
    probe = ("import sys; sys.path.insert(0, 'tools'); "
             "from toolchain.cli.validate import require_toolchains; "
             "raise SystemExit(require_toolchains())")
    preflight = (("wsl", "-u", "root", "-e", "python3", "-c", probe)
                 if platform == "win32" else (sys.executable, "-c", probe))
    tests = (*local, "test", "--slow", "--jobs", str(jobs))
    if platform == "linux":
        tests = (*tests, "--require-toolchain")
    steps = [Step("native-prerequisites", preflight, 90),
             Step("gate", (*local, "gate"), 900),
             Step("tests-with-slow-cases", tests, 1800),
             Step("isolated-generated-tests", (*local, "vela", "generated-tests"), 240)]
    if platform == "win32":
        steps.append(Step("guest-tests-with-slow-cases", (
            *guest, "test", "--slow", "--require-toolchain", "--jobs", str(jobs)), 1800))
    steps.extend((Step("fresh-checked-parser-support", (*guest, "vela-parser", "support"), 3600),
                  Step("syntax-campaigns-and-migration", (*guest, "vela-parser", "syntax-campaigns"), 1800),
                  Step("elaboration-kernel-replay", (*guest, "vela-parser", "elaborate-qualify"), 1800)))
    return tuple(steps)


def _tail(path: Path) -> str:
    with path.open("rb") as stream:
        stream.seek(0, 2)
        stream.seek(max(0, stream.tell() - TAIL_BYTES))
        return stream.read(TAIL_BYTES).decode("utf-8", errors="replace")


def run(root: Path, steps: tuple[Step, ...], profile: str) -> int:
    """Run every required step or stop at the first failure, retaining its complete log."""
    if not steps:
        raise ValueError("validation requires at least one step")
    logs = root / "out" / "validation"
    logs.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f"{profile}-", dir=logs))
    print(f"Validation logs: {directory}", flush=True)
    for index, step in enumerate(steps, 1):
        log = directory / f"{index:02}-{step.name}.log"
        print(f"[{index}/{len(steps)}] {step.name}", flush=True)
        error: str | None = None
        with log.open("wb") as stream:
            try:
                result = subprocess.run(step.command, cwd=root, stdin=subprocess.DEVNULL,
                                        stdout=stream, stderr=subprocess.STDOUT,
                                        timeout=step.seconds, check=False)
            except subprocess.TimeoutExpired:
                error = f"exceeded {step.seconds} seconds"
            except OSError as failure:
                error = f"could not start: {failure}"
            else:
                if result.returncode != 0:
                    error = f"exited {result.returncode}"
        if error is not None:
            print(f"FAIL {step.name}: {error}; log: {log}", flush=True)
            print(_tail(log), flush=True)
            return 1
        print(f"ok {step.name}: {log}", flush=True)
    print(f"All {len(steps)} steps passed for the {profile} profile; logs: {directory}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(suggest_on_error=True, description=__doc__)
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--static", action="store_true", help="only Python and Markdown checks; no native parser")
    profile.add_argument("--full", action="store_true", help="also run slow/native cases and fresh parser/kernel qualification")
    parser.add_argument("--jobs", type=int, default=DEFAULT_JOBS,
                        help=f"behavioral-test worker processes (default: {DEFAULT_JOBS}); steps run sequentially")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    name = "full" if args.full else "static" if args.static else "default"
    try:
        return run(corpus.find_root(), plan(sys.platform, args.jobs, full=args.full, static=args.static), name)
    except (OSError, ValueError) as error:
        print(f"FAIL validate: {error}", file=sys.stderr)
        return 1
