# SPDX-License-Identifier: Apache-2.0
"""Validation profiles require every selected step and retain failure evidence."""

import subprocess
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import BinaryIO, cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import env, proofenv
from toolchain.cli import validate


def _profiles() -> None:
    for platform in ("win32", "linux"):
        ordinary = validate.plan(platform, 3)
        ensure([step.name for step in ordinary] == ["gate", "tests"], "default profile omitted required checks")
        ensure(ordinary[1].command[-2:] == ("--jobs", "3"), "worker override was dropped")
        static = validate.plan(platform, 4, static=True)
        ensure([step.command[-1] for step in static] == ["typecheck", "markdown"],
               "static profile either requires a native parser or omits a checker")
        full = validate.plan(platform, 4, full=True)
        ensure(full[0].name == "native-prerequisites", "full profile does work before checking toolchains")
        tests = [step for step in full if "test" in step.name and "generated" not in step.name]
        ensure(len(tests) == (2 if platform == "win32" else 1), "full profile repeated or omitted a platform suite")
        ensure(all("--slow" in step.command for step in tests), "full profile skipped slow cases")
        ensure("--require-toolchain" in tests[-1].command, "native full tests can silently skip toolchain cases")
        ensure([step.command[-1] for step in full[-3:]] == ["support", "syntax-campaigns", "elaborate-qualify"],
               "full profile omitted fresh qualification or duplicated parser/migration qualification")
        ensure(sum("generated-tests" in step.command for step in full) == 1,
               "full profile must run exactly one isolated generated campaign")
        ensure(all(step.seconds > 0 for step in full), "a validation step has no finite timeout")
        if platform == "win32":
            ensure(all(step.command[:5] == ("wsl", "-u", "root", "-e", "python3") for step in full[-3:]),
                   "Windows native qualification did not use the existing local WSL lane")


def _prerequisites() -> None:
    required = {env.SAIL_SWITCH, proofenv.ROCQ_SWITCH}
    for installed in (set(), {env.SAIL_SWITCH}, {proofenv.ROCQ_SWITCH}, required):
        output = StringIO()
        with patch.object(validate, "switches", return_value=installed), redirect_stdout(output):
            code = validate.require_toolchains()
        ensure(code == (0 if installed == required else 1), "full prerequisite admitted a missing switch")
        for missing in required - installed:
            ensure(missing in output.getvalue(), "prerequisite failure hid the missing exact switch")


def _step_execution() -> None:
    steps = (validate.Step("first", ("fixture", "one"), 10), validate.Step("second", ("fixture", "two"), 20))
    with tempfile.TemporaryDirectory(prefix="vela-validation-") as temporary:
        root = Path(temporary)
        commands: list[tuple[str, ...]] = []

        def complete(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            commands.append(command)
            cast("BinaryIO", kwargs["stdout"]).write(b"independent step evidence\n")
            ensure(kwargs["cwd"] == root and kwargs["stdin"] == subprocess.DEVNULL,
                   "validation step changed checkout or inherited interactive input")
            ensure(kwargs["stderr"] == subprocess.STDOUT and kwargs["timeout"] in {10, 20},
                   "validation step dropped its combined log or timeout")
            return subprocess.CompletedProcess(command, 0)

        with patch.object(validate.subprocess, "run", side_effect=complete), redirect_stdout(StringIO()):
            ensure(validate.run(root, steps, "fixture") == 0, "successful selected steps failed")
        logs = sorted((root / "out" / "validation").glob("*/*.log"))
        ensure(commands == [step.command for step in steps] and len(logs) == 2,
               "validation did not execute/log every selected step exactly once")
        ensure(all(path.read_bytes() == b"independent step evidence\n" for path in logs),
               "validation lost step evidence")


def _fail_fast() -> None:
    steps = (validate.Step("first", ("fixture",), 10), validate.Step("must-not-run", ("later",), 10))
    failures: tuple[object, ...] = (subprocess.CompletedProcess(("fixture",), 7),
                                  subprocess.TimeoutExpired("fixture", 10), OSError("unavailable tool"))
    for failure in failures:
        with tempfile.TemporaryDirectory(prefix="vela-validation-failure-") as temporary:
            output = StringIO()
            with patch.object(validate.subprocess, "run", side_effect=[failure]) as run, redirect_stdout(output):
                ensure(validate.run(Path(temporary), steps, "fixture") == 1, "failed validation returned success")
            ensure(run.call_count == 1 and "All " not in output.getvalue(), "failed validation ran later work or claimed completion")
            ensure("FAIL first:" in output.getvalue() and ".log" in output.getvalue(),
                   "failed validation omitted the failing step or log path")
    try:
        validate.run(Path(), (), "empty")
    except ValueError:
        pass
    else:
        raise AssertionError("empty validation plan returned success")


def _bounded_log_tail() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-validation-tail-") as temporary:
        path = Path(temporary) / "step.log"
        path.write_bytes(b"discarded prefix" + b"x" * validate.TAIL_BYTES + b"\nlast finding\n")
        tail = validate._tail(path)
        ensure("discarded prefix" not in tail and tail.endswith("last finding\n")
               and len(tail.encode()) == validate.TAIL_BYTES, "failure log tail was incomplete or unbounded")


def _cli_selection_and_errors() -> None:
    with patch.object(validate.corpus, "find_root", return_value=Path("fixture")), \
            patch.object(validate, "run", return_value=1) as run:
        ensure(validate.main(["--full", "--jobs", "2"]) == 1, "CLI lost failed-profile exit status")
        ensure(run.call_args.args[2] == "full" and "2" in run.call_args.args[1][2].command,
               "CLI lost the full profile or job override")
    for args in (["--jobs", "0"], ["--jobs", "-1"], ["--full", "--static"], ["--unknown"]):
        with redirect_stderr(StringIO()):
            try:
                validate.main(args)
            except SystemExit as error:
                ensure(error.code == 2, "invalid validation arguments returned the wrong status")
            else:
                raise AssertionError("invalid validation arguments were accepted")


def cases() -> list[Case]:
    return [Case("validation-profiles-preserve-required-platform-coverage", _profiles),
            Case("full-validation-requires-both-exact-opam-switches", _prerequisites),
            Case("validation-executes-required-steps-and-retains-logs", _step_execution),
            Case("validation-fails-fast-on-exit-timeout-and-launch-failure", _fail_fast),
            Case("validation-failure-tail-is-bounded", _bounded_log_tail),
            Case("validation-cli-profile-propagation-and-argument-refusals", _cli_selection_and_errors)]
