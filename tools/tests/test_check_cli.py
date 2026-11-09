# SPDX-License-Identifier: Apache-2.0
"""CLI controls for read-only checks and explicit estimate-summary repair."""

import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import estimates
from toolchain.cli import check
from toolchain.report import Reporter

INDEPENDENT_CASES = True

_ORIGINAL = (
    "# Plan\n\nBefore.\n\n<!-- estimate-summary:start -->\n"
    "old figures\n<!-- estimate-summary:end -->\n\nAfter.\n"
)
_UPDATED = _ORIGINAL.replace("old figures", "new figures")


def _default_is_read_only() -> None:
    rep = Reporter()
    rep.report("fixture", "finding(s):", ["summary is stale"])
    with tempfile.TemporaryDirectory(prefix="vela-check-cli-") as td:
        root = Path(td)
        plan = root / "PLAN.md"
        plan.write_bytes(_ORIGINAL.encode("utf-8"))
        output = StringIO()
        with patch.object(check.corpus, "find_root", return_value=root), \
                patch.object(check.checks, "run", return_value=rep) as run, \
                patch.object(estimates, "update_summary") as update, \
                redirect_stdout(output):
            code = check.main([])
        ensure(code == 1, "a failed check must return failure")
        run.assert_called_once_with(root)
        update.assert_not_called()
        ensure(plan.read_bytes() == _ORIGINAL.encode("utf-8"),
               "ordinary checks must leave stale summary bytes unchanged")
        ensure("summary is stale" in output.getvalue() and "1 finding(s)." in output.getvalue(),
               "the CLI must print the check reporter and its finding count")


def _fix_then_check() -> None:
    rep = Reporter()
    rep.report("fixture", "finding(s):", ["unrelated hygiene failure"])
    with tempfile.TemporaryDirectory(prefix="vela-check-cli-") as td:
        root = Path(td)
        plan = root / "PLAN.md"
        plan.write_bytes(_ORIGINAL.encode("utf-8"))

        def checked(repaired_root: Path) -> Reporter:
            ensure(repaired_root == root, "checks must use the selected repository")
            ensure(plan.read_bytes() == _UPDATED.encode("utf-8"),
                   "all checks must observe the repaired summary")
            return rep

        output = StringIO()
        with patch.object(check.corpus, "find_root", return_value=root), \
                patch.object(check.checks, "run", side_effect=checked) as run, \
                patch.object(estimates, "update_summary", return_value=_UPDATED) as update, \
                redirect_stdout(output):
            code = check.main(["--fix"])
        ensure(code == 1, "summary repair must not hide remaining check failures")
        update.assert_called_once_with(_ORIGINAL)
        run.assert_called_once_with(root)
        ensure("unrelated hygiene failure" in output.getvalue(),
               "repair must retain the normal check reporter")


def _malformed_fix_preserves_input() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-check-cli-") as td:
        root = Path(td)
        plan = root / "PLAN.md"
        plan.write_bytes(_ORIGINAL.encode("utf-8"))
        output, errors = StringIO(), StringIO()
        with patch.object(check.corpus, "find_root", return_value=root), \
                patch.object(check.checks, "run") as run, \
                patch.object(estimates, "update_summary", side_effect=ValueError("malformed input")), \
                redirect_stdout(output), redirect_stderr(errors):
            code = check.main(["--fix"])
        ensure(code == 1, "malformed summary input must fail repair")
        ensure(plan.read_bytes() == _ORIGINAL.encode("utf-8"),
               "a refused repair must preserve all original bytes")
        ensure("malformed input" in output.getvalue() + errors.getvalue(),
               "repair refusal must explain the malformed input")
        run.assert_not_called()


def _unknown_arguments_are_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-check-cli-") as td:
        root = Path(td)
        plan = root / "PLAN.md"
        plan.write_bytes(_ORIGINAL.encode("utf-8"))
        for args in (["--unknown"], ["--fix", "--unknown"]):
            output, errors = StringIO(), StringIO()
            with patch.object(check.corpus, "find_root", return_value=root), \
                    patch.object(check.checks, "run") as run, \
                    patch.object(estimates, "update_summary") as update, \
                    redirect_stdout(output), redirect_stderr(errors):
                code = check.main(args)
            ensure(code == 2, f"unknown arguments must return usage status: {args!r}")
            ensure(plan.read_bytes() == _ORIGINAL.encode("utf-8"),
                   "invalid arguments must not write the plan")
            run.assert_not_called()
            update.assert_not_called()
            ensure(bool(output.getvalue() + errors.getvalue()),
                   "invalid arguments must print usage guidance")


def _help_is_read_only() -> None:
    output = StringIO()
    with patch.object(check.corpus, "find_root") as root, \
            patch.object(check.checks, "run") as run, \
            patch.object(estimates, "update_summary") as update, \
            redirect_stdout(output):
        code = check.main(["--help"])
    ensure(code == 0 and "--fix" in output.getvalue(),
           "help must describe explicit summary repair and return success")
    root.assert_not_called()
    run.assert_not_called()
    update.assert_not_called()


def cases() -> list[Case]:
    return [
        Case("check CLI default is read-only", _default_is_read_only),
        Case("check CLI fixes before checking", _fix_then_check),
        Case("check CLI malformed repair preserves input", _malformed_fix_preserves_input),
        Case("check CLI rejects unknown arguments", _unknown_arguments_are_rejected),
        Case("check CLI help is read-only", _help_is_read_only),
    ]
