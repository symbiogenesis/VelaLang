# SPDX-License-Identifier: Apache-2.0
"""Static gates share one indexed corpus and bounded environment probes."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import checks, corpus, markdown, proofenv
from toolchain.report import Reporter

INDEPENDENT_CASES = True


def _shared_corpus_and_verdicts() -> None:
    root = Path("checkout")
    loaded = corpus.Corpus(root, [], {}, [])
    check_report, markdown_report, type_report = Reporter(), Reporter(), Reporter()
    check_report.report("check-fixture", "findings:", ["first"])
    markdown_report.report("markdown-fixture", "findings:", ["second"])
    type_report.report("type-fixture", "findings:", ["third"])
    expected = [*check_report.out, *markdown_report.out, *type_report.out]
    with patch.object(corpus, "load", return_value=loaded) as load, \
            patch.object(checks, "run", return_value=check_report) as check, \
            patch.object(markdown, "run", return_value=markdown_report) as lint, \
            patch.object(checks.typecheck, "run", return_value=type_report):
        report = checks.run_gate(root)
    load.assert_called_once_with(root)
    check.assert_called_once_with(root, loaded=loaded)
    lint.assert_called_once_with(root, loaded=loaded)
    ensure(report.findings == 3 and report.out == expected,
           "sharing the corpus lost an independent verdict or changed report ordering")
    ensure("first" in report.out[1] and "second" in report.out[3] and "third" in report.out[5],
           "the static gate must retain all three components' findings in order")


def _shared_load_failure() -> None:
    root = Path("checkout")
    type_report = Reporter()
    type_report.report("type-fixture", "findings:", ["independent failure"])
    with patch.object(corpus, "load", side_effect=RuntimeError("index unavailable")) as load, \
            patch.object(markdown, "settings_findings", return_value=["bad Markdown config"]), \
            patch.object(checks.typecheck, "run", return_value=type_report):
        report = checks.run_gate(root)
    load.assert_called_once_with(root)
    ensure(report.findings == 4, "corpus failure hid a checker, Markdown configuration, or Python failure")
    ensure(sum("index unavailable" in line for line in report.out) == 2,
           "both corpus-dependent gate components must explain their unavailable input")
    ensure(any("independent failure" in line for line in report.out),
           "a failed corpus load prevented independent Python checking")


def _git_deadline() -> None:
    with patch.object(corpus, "_git_environment", return_value=None), \
            patch.object(corpus.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 30)) as run:
        try:
            corpus._git(Path("checkout"), "ls-files", "-z")
        except RuntimeError as error:
            ensure("git ls-files -z exceeded" in str(error), "Git timeout lost its command context")
        else:
            raise AssertionError("a stalled Git index probe was accepted")
    ensure(run.call_args.kwargs["timeout"] == corpus.GIT_TIMEOUT
           and run.call_args.kwargs["stdin"] == subprocess.DEVNULL,
           "the Git index probe must have a deadline and cannot wait for interactive input")


def _translation_deadline() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-path-probe-") as directory:
        root = Path(directory)
        (root / ".git").write_text("gitdir: C:/missing-vela-checkout/.git/worktrees/review\n", encoding="utf-8")
        with patch.dict(proofenv.os.environ, {}, clear=True), \
                patch.object(proofenv.shutil, "which", return_value="wslpath"), \
                patch.object(proofenv.subprocess, "run",
                             side_effect=subprocess.TimeoutExpired("wslpath", 10)) as run:
            try:
                proofenv.git_dir(root)
            except RuntimeError as error:
                ensure("path translation exceeded" in str(error), "WSL timeout lost its purpose")
            else:
                raise AssertionError("a stalled worktree path translation was accepted")
        ensure(run.call_args.kwargs["timeout"] == proofenv.PATH_TIMEOUT,
               "worktree translation must have a finite deadline")


def cases() -> list[Case]:
    return [Case("static gate shares corpus and preserves verdicts", _shared_corpus_and_verdicts),
            Case("static gate shares load failure without hiding independent checks", _shared_load_failure),
            Case("Git index probe has a deadline", _git_deadline),
            Case("WSL worktree translation has a deadline", _translation_deadline)]
