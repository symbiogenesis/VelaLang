# SPDX-License-Identifier: Apache-2.0
"""Test-selection coverage stays explicit across filters, failures, and shards."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.harness import Case, Lane, ensure
from toolchain.cli import test as runner
from toolchain.sharding import Shard

INDEPENDENT_CASES = True

_LANES: frozenset[Lane] = frozenset({"any", "host"})


def _fixture(calls: list[str]) -> list[Case]:
    return [Case("ordinary", lambda: calls.append("ordinary")),
            Case("slow", lambda: calls.append("slow"), slow=True),
            Case("kernel", lambda: calls.append("kernel"), lane="toolchain"),
            Case("slow-kernel", lambda: calls.append("slow-kernel"), slow=True, lane="toolchain")]


def _filter_coverage() -> None:
    for slow, expected, skipped_slow, skipped_lane in (
        (False, ["ordinary"], 2, 1),
        (True, ["ordinary", "slow"], 0, 2),
    ):
        calls: list[str] = []
        report = runner._run_cases("fixture", _fixture(calls), slow, _LANES)
        ensure(calls == expected and report.cases == len(expected),
               "coverage reporting changed the selected test population")
        ensure(report.findings == 0 and report.skipped_slow == skipped_slow
               and report.skipped_lane == skipped_lane,
               "each skipped case needs exactly one reason, with slow filtering first")
        ensure(any(f"{skipped_slow} slow case(s), {skipped_lane} case(s) for unavailable lanes" in line
                   for line in report.out), "module report hid its skipped coverage")


def _shard_coverage() -> None:
    calls: list[str] = []
    report = runner._run_cases("fixture", _fixture(calls), False, _LANES, Shard(2, 2))
    ensure(not calls and report.cases == 0 and report.skipped_slow == 2
           and report.skipped_lane == 0,
           "shard reports must count only their own selected cases, including overlapping filters")
    ensure(report.findings == 0, "a valid shard with only skipped cases became a failure")


def _failure_coverage() -> None:
    def failed() -> None:
        raise ValueError("fixture failure")

    report = runner._run_cases("fixture", [Case("failure", failed), *_fixture([])], False, _LANES)
    ensure(report.findings == 1 and report.cases == 2 and report.skipped_slow == 2
           and report.skipped_lane == 1,
           "failed executed cases must stay counted without absorbing skipped cases")
    ensure(any("fixture failure" in line for line in report.out)
           and any("skipped:" in line for line in report.out),
           "failure reports must retain both the finding and skipped coverage")


def _aggregate_coverage() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-runner-coverage-") as directory:
        record = Path(directory) / "timings.json"
        with patch.object(runner, "_module_names", return_value=["alpha", "beta"]), \
                patch.object(runner, "_lanes", return_value=_LANES), \
                patch.object(runner, "_load", side_effect=lambda *_args: _fixture([])), \
                patch.object(runner, "ProcessPoolExecutor") as pool:
            pool.return_value.__enter__.return_value.map.side_effect = map
            report = runner.run(record=record)
        ensure(report.findings == 0 and any(
            line == "2 case(s) run; 4 slow case(s) skipped; 2 case(s) skipped for unavailable lanes."
            for line in report.out), "suite report must aggregate worker coverage")
        units = json.loads(record.read_text(encoding="utf-8"))
        ensure([unit["name"] for unit in units] == ["alpha", "beta"]
               and all(unit["cases"] == 1 and unit["skipped_slow"] == 2
                       and unit["skipped_lane"] == 1 for unit in units),
               "timings must preserve module ordering and the same coverage as the report")


def _required_toolchain_lane() -> None:
    with patch.object(runner, "_module_names", return_value=["fixture"]), \
            patch.object(runner, "_lanes", return_value=_LANES), \
            patch.object(runner, "ProcessPoolExecutor") as pool:
        report = runner.run(require_toolchain=True)
        ensure(report.findings == 1 and not pool.called,
               "required native lane silently skipped tests or started workers without prerequisites")
        ensure(any("required lane unavailable" in line for line in report.out),
               "missing required native lane was not explained")
    calls: list[str] = []
    with patch.object(runner, "_module_names", return_value=["fixture"]), \
            patch.object(runner, "_lanes", return_value=frozenset({"any", "guest", "toolchain"})), \
            patch.object(runner, "_load", side_effect=lambda *_args: _fixture(calls)), \
            patch.object(runner, "ProcessPoolExecutor") as pool:
        pool.return_value.__enter__.return_value.map.side_effect = map
        report = runner.run(require_toolchain=True, slow=True)
        ensure(report.findings == 0 and calls == ["ordinary", "slow", "kernel", "slow-kernel"],
               "available required native lane did not execute all its selected cases")


def cases() -> list[Case]:
    return [Case("runner reports slow and unavailable-lane skips", _filter_coverage),
            Case("runner counts only its shard's skipped cases", _shard_coverage),
            Case("runner retains skipped coverage alongside failures", _failure_coverage),
            Case("runner aggregates coverage in reports and timings", _aggregate_coverage),
            Case("runner can require the native toolchain lane", _required_toolchain_lane)]
