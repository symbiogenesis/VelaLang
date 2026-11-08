#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the tools' own behavioral tests.

Modules under `tools/tests/` run in separate worker processes so environment
overrides, patched modules, and redirected streams cannot interfere across
modules. Workers may be reused for later modules; tests still restore their
temporary state. Cases within a module run in order, and reports merge in sorted
module order regardless of scheduling. Discovering no modules or loading a
module that declares no cases is a failure, though lane, `--slow`, and `--shard`
filtering may leave a module with zero selected cases in a given run. When
`VOS_GATE_TIMINGS` is set (see [toolchain/timings.py](../timings.py)), each
module's case count and duration are written to that file.

`--shard INDEX/TOTAL` strides across the sorted modules. A module whose cases
share no state and whose `cases()` returns the same ordered list on every run
may declare `INDEPENDENT_CASES = True` at the left margin; it keeps its position
in the module stride so no other module moves, while every shard runs the cases
at positions `j` where `j % TOTAL == INDEX - 1`.

Exits 0 when clean, 1 on any finding.
"""

import argparse
import importlib
import multiprocessing
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from functools import partial
from io import StringIO
from pathlib import Path

from tests.harness import Case, Lane
from toolchain import env, sharding, timings
from toolchain.report import Reporter
from toolchain.sharding import Shard


def switches() -> set[str]:
    """Installed opam switches on the current machine."""
    try:
        done = subprocess.run(
            ["opam", "switch", "list", "--short"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
            stdin=subprocess.DEVNULL,
            env=env.declining_environment(),
        )
    except OSError, subprocess.SubprocessError:
        return set()
    return set(done.stdout.splitlines()) if done.returncode == 0 else set()

# Execution lane of the current process.
LANE: Lane = "host" if sys.platform == "win32" else "guest"

TESTS = Path(__file__).resolve().parents[2] / "tests"

# Top-level declaration marking a test module's cases as independent across shards.
# The parent process scans the module source with `_DECLARED`, and the worker verifies
# that the imported module's attribute matches.
INDEPENDENT = "INDEPENDENT_CASES"
_DECLARED = re.compile(rf"(?m)^{INDEPENDENT} = True$")


class ModuleReport(Reporter):
    """Per-module test report, tracking executed case count and elapsed seconds."""

    def __init__(self) -> None:
        super().__init__()
        self.cases = 0
        self.seconds = 0.0


def _lanes() -> frozenset[Lane]:
    """Return the `Case.lane` values runnable in this process.

    Admits `"any"` and the current platform lane (`"host"` on Windows, `"guest"` on
    Linux), plus `"toolchain"` on a Linux guest when the expected opam switch is
    installed.
    """
    lanes: set[Lane] = {"any", LANE}
    if LANE == "guest" and env.SAIL_SWITCH in switches():
        lanes.add("toolchain")
    return frozenset(lanes)


def _module_names(only: str | None) -> list[str]:
    """Every test module under `tools/tests/`, sorted so the report order is fixed."""
    if only is not None and not only.strip():
        raise ValueError("--only requires a nonempty module-name substring")
    names = sorted(path.stem for path in TESTS.glob("test_*.py"))
    if only is not None:
        names = [name for name in names if only in name]
    return names


def _declares(name: str) -> bool:
    """Whether a test module's source declares `INDEPENDENT_CASES = True`."""
    try:
        return _DECLARED.search((TESTS / f"{name}.py").read_text(encoding="utf-8")) is not None
    except OSError, UnicodeDecodeError:
        return False


def _load(name: str, split: bool | None = None) -> list[Case] | str:
    """Import a test module inside a worker and return its validated `Case` list or an error string.

    Importing inside the worker allows cases to carry unpicklable closures and keeps
    module patches isolated. When `split` is not `None`, verifies that the module's
    runtime `INDEPENDENT_CASES` attribute matches the source scan.
    """
    try:
        module = importlib.import_module(f"tests.{name}")
        found: object = module.cases()
    except (Exception, SystemExit) as err:  # importing a test must not exit the runner
        return f"failed to load: {err!r}"
    declared = getattr(module, INDEPENDENT, False) is True
    if split is not None and declared != split:
        return (f"sets {INDEPENDENT} in a form a sharded run does not read; state it as "
                f"'{INDEPENDENT} = True' at the left margin" if declared else
                f"its source reads '{INDEPENDENT} = True', but the module does not set it")
    # Validate the dynamic return value of cases() before running.
    if not isinstance(found, list):
        return f"cases() returned {type(found).__name__}, not a list"
    if not found:
        return "cases() returned an empty list"
    narrowed: list[Case] = []
    for item in found:
        if not isinstance(item, Case):
            return f"cases() returned a member that is not a Case: {item!r}"
        narrowed.append(item)
    return narrowed


def _run_cases(name: str, cases: list[Case] | str, slow: bool,
               lanes: frozenset[Lane], share: Shard | None = None) -> ModuleReport:
    """Run a module's selected cases (or `share`'s stride before `--slow` and lane filtering)."""
    rep = ModuleReport()
    if isinstance(cases, str):
        rep.report(name, "module error(s):", [cases])
        return rep

    listed = len(cases)
    failures: list[str] = []
    for case in cases if share is None else share.share(cases):
        if (case.slow and not slow) or case.lane not in lanes:
            continue
        rep.cases += 1
        try:
            case.fn()
        except (Exception, SystemExit) as err:  # an unexpected exit is a failed case
            failures.append(f"{case.name}: {err}")
    rep.report(name, "failure(s):", failures,
               ok=f"{rep.cases} case(s)"
               + ("" if share is None else f", this shard's share of {listed}"))
    return rep


def _run_module(name: str, slow: bool, lanes: frozenset[Lane], shard: Shard | None = None,
                splits: frozenset[str] = frozenset()) -> ModuleReport:
    """Load and run one module, retaining its captured output on failure. Under `shard`,
    a module named in `splits` runs that shard's share of its cases."""
    split = name in splits
    started = time.perf_counter()
    output = StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        report = _run_cases(name, _load(name, None if shard is None else split), slow, lanes,
                            shard if split else None)
    if report.findings:
        report.out.extend(output.getvalue().splitlines())
    report.seconds = time.perf_counter() - started
    return report


def run(only: str | None = None, slow: bool = False, jobs: int | None = None,
        shard: Shard | None = None, record: Path | None = None) -> Reporter:
    """Run the selected test suite and return the aggregated `Reporter`.

    If `record` is set, writes per-module case counts and durations to that path.
    """
    if jobs is not None and jobs < 1:
        raise ValueError("jobs must be positive")
    if only is not None and shard is not None:
        raise ValueError("--only cannot be combined with --shard")
    rep = Reporter()
    rep.line("=== tests ===")

    names = _module_names(only)
    splits = frozenset[str]()
    if shard is not None:
        total = len(names)
        try:
            selected = shard.select(names)
        except ValueError as err:
            rep.report("tests", "invalid partition:", [str(err)])
            return rep
        # Partition over all modules before separating split modules so adding
        # INDEPENDENT_CASES to a module does not shift other modules between shards.
        splits = frozenset(name for name in names if _declares(name))
        whole = [name for name in selected if name not in splits]
        rep.line(f"shard {shard}: {len(whole)} of {total - len(splits)} modules"
                 + (f", and its share of the cases of {len(splits)} more" if splits else "")
                 + "; every shard must pass")
        names = [name for name in names if name in splits or name in whole]
    units: list[timings.Unit] = []
    if not names:
        rep.report("tests", "empty suite:",
                   ["nothing under tools/tests/ matches test_*.py"
                    + (f" and --only '{only}'" if bool(only) else "")])
    else:
        # Probe runnable lanes once before spawning workers.
        lanes = _lanes()
        workers = min(jobs or min(8, os.process_cpu_count() or 1), len(names))
        # Use spawn on all platforms so workers never inherit live threads or module patches.
        with ProcessPoolExecutor(max_workers=workers,
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            parts = pool.map(partial(_run_module, slow=slow, lanes=lanes, shard=shard,
                                     splits=splits), names)
            for name, part in zip(names, parts, strict=True):
                rep.out.extend(part.out)
                rep.findings += part.findings
                units.append({"kind": "module", "name": name, "cases": part.cases,
                              "share": str(shard) if name in splits else None,
                              "seconds": round(part.seconds, 3)})
    timings.write(record, units)

    if rep.findings:
        rep.line(f"{rep.findings} finding(s).")
    else:
        rep.line("the tools behave as their tests hold them to.")
    return rep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(suggest_on_error=True, description="Run the tools' own behavioral tests.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--only", metavar="SUBSTRING",
                        help="run only the modules whose name carries this")
    selection.add_argument("--shard", type=sharding.parse, metavar="INDEX/TOTAL",
                           help="run a disjoint partition of the discovered modules, and "
                                "this shard's share of the cases of each module declaring "
                                "INDEPENDENT_CASES = True")
    parser.add_argument("--slow", action="store_true",
                        help="include the cases marked slow")
    parser.add_argument("--jobs", type=int,
                        help="worker processes (default: available CPUs, capped at eight)")
    args = parser.parse_args(argv)
    if args.jobs is not None and args.jobs < 1:
        parser.error("--jobs must be positive")
    if args.only is not None and not args.only.strip():
        parser.error("--only requires a nonempty module-name substring")

    report = run(only=args.only, slow=args.slow, jobs=args.jobs, shard=args.shard,
                 record=timings.claim())
    print("\n".join(report.out))
    return 1 if report.findings else 0
