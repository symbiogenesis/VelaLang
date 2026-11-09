# SPDX-License-Identifier: Apache-2.0
"""Independent planning fixtures check arithmetic, ownership and safe repair."""

from tests.harness import Case, ensure
from toolchain import estimates

INDEPENDENT_CASES = True

_PLAN = """# Plan

## Current summary

<!-- estimate-summary:start -->
stale
<!-- estimate-summary:end -->

## Checklist items (Q25 series)

- [x] **Q25 · Parent**
  - [x] **Q25a · Measured leaf** · 2.5 h actual · agent-parallel
  - [x] **Q25b · Retained leaf** · 10 h retained estimate, actual n/a
- [x] **Q25m · Actual-only leaf** · 0.5 h actual
- [ ] **Q25n · Implementation** · 12 h, range 8–16 · I
- [ ] **Q25o · Investigation** · 5 h, range 2–8 · X

## Calibration record (Q25 series)

| Item | Class | Estimate (h) | Range (h) | Actual (h) | Ratio |
| --- | --- | --- | --- | --- | --- |
| Q25a | I | 20 | n/a | 2.5 | 0.125 |
| Q25b | I | 10 | 6–14 | n/a | n/a |
| Q25m | n/a | n/a | n/a | 0.5 | n/a |
| Q25n | I | 12 | 8–16 | n/a | n/a |
| Q25o | X | 5 | 2–8 | n/a | n/a |

## Unpriced proposals

| Proposed owner | Estimate |
| --- | --- |
| another-scope | 1,000 h, range 500–1500 |
"""


def _reject(text: str, fragment: str) -> None:
    try:
        estimates.update_summary(text)
    except ValueError as error:
        ensure(fragment in str(error), f"expected {fragment!r}, found {error!r}")
    else:
        raise AssertionError(f"invalid source accepted: {fragment}")
    ensure(bool(estimates.findings(text)), "invalid sources must also produce check findings")


def _mixed_status_arithmetic() -> None:
    expected = """| Measure | Value |
| --- | --- |
| Total estimate midpoint h | 30 |
| Total estimate range h | 23–37 |
| Completed scope h | 13 |
| Complete by estimate % | 43.3 |
| Remaining h | 17 |
| Open class I h | 12 |
| Open class X h | 5 |
| Retained completion estimate h | 10 |
| Unmeasured completed items | 1 |"""
    ensure(estimates.render_summary(_PLAN) == expected,
           "mixed statuses must use actuals/retained weights once and exclude parents/proposals")


def _drift_and_repair() -> None:
    ensure(any("check --fix" in finding for finding in estimates.findings(_PLAN)),
           "stale figures must carry a repair command")
    updated = estimates.update_summary(_PLAN)
    ensure(estimates.update_summary(updated) == updated and estimates.findings(updated) == [],
           "a repaired summary must be stable and clean")
    prefix, rest = _PLAN.split(estimates.START)
    _, suffix = rest.split(estimates.END)
    ensure(updated.startswith(prefix + estimates.START)
           and updated.endswith(estimates.END + suffix),
           "repair must preserve text outside the markers")
    edited = updated.replace("| Remaining h | 17 |", "| Remaining h | 1 |")
    ensure(bool(estimates.findings(edited)), "manual table drift must be detected")


def _source_membership() -> None:
    _reject(_PLAN.replace("| Q25b | I | 10 | 6–14 | n/a | n/a |\n", ""), "missing: Q25b")
    _reject(_PLAN.replace("| Q25a | I", "| Q25 | I"), "extra: Q25")
    row = "| Q25a | I | 20 | n/a | 2.5 | 0.125 |"
    _reject(_PLAN.replace(row, row + "\n" + row), "duplicate calibration")
    leaf = "- [x] **Q25m · Actual-only leaf** · 0.5 h actual"
    _reject(_PLAN.replace(leaf, leaf + "\n" + leaf), "duplicate checklist")
    _reject(_PLAN.replace("**Q25 · Parent**", "**Q25 · Parent** · 99 h actual"),
            "parent Q25")


def _invalid_numbers_and_status() -> None:
    row = "| Q25n | I | 12 | 8–16 | n/a | n/a |"
    for bad in ("NaN", "Infinity", "-1", "1,2", ""):
        _reject(_PLAN.replace(row, row.replace("| 12 |", f"| {bad} |")), "Q25n")
    _reject(_PLAN.replace(row, row.replace("| 8–16 |", "| 13–16 |")), "range must contain")
    _reject(_PLAN.replace(row, row.replace("| 8–16 |", "| 16–8 |")), "range must contain")
    _reject(_PLAN.replace(row, row.replace("| 8–16 |", "| n/a |")), "requires a priced")
    _reject(_PLAN.replace(row, row.replace("| n/a | n/a |", "| 1 | n/a |")),
            "open leaf cannot carry actual")
    _reject(_PLAN.replace(row, row.replace("| I |", "| n/a |")), "requires a priced")
    _reject(_PLAN.replace("| Q25m | n/a | n/a | n/a | 0.5 | n/a |",
                          "| Q25m | n/a | n/a | n/a | n/a | n/a |"),
            "requires an actual or retained")


def _marker_refusals() -> None:
    _reject(_PLAN.replace(estimates.START, ""), "exactly one")
    _reject(_PLAN.replace(estimates.END, ""), "exactly one")
    _reject(_PLAN + "\n" + estimates.START, "exactly one")
    _reject(_PLAN.replace(estimates.START, "sentinel").replace(estimates.END, estimates.START)
            .replace("sentinel", estimates.END), "out of order")


def _zero_and_decimal_formatting() -> None:
    text = _PLAN[:_PLAN.index("## Checklist items")]
    text += """## Checklist items (Q25 series)

- [x] **Q25a · Zero** · 0 h actual

## Calibration record (Q25 series)

| Item | Class | Estimate (h) | Range (h) | Actual (h) | Ratio |
| --- | --- | --- | --- | --- | --- |
| Q25a | I | n/a | n/a | 0 | n/a |
"""
    zero = estimates.render_summary(text)
    ensure("| Complete by estimate % | n/a |" in zero,
           "zero total scope must not claim a completion percentage")
    ensure("| Total estimate range h | 0–0 |" in zero, "zero range must stay explicit")
    large = estimates.render_summary(text.replace("0 h actual", "1,200.10 h actual")
                                    .replace("| 0 | n/a |", "| 1,200.10 | n/a |"))
    ensure("| Completed scope h | 1,200.1 |" in large
           and "| Complete by estimate % | 100.0 |" in large,
           "Decimal formatting must preserve hours and one-decimal percentages")


def cases() -> list[Case]:
    return [Case("summary mixed-status arithmetic", _mixed_status_arithmetic),
            Case("summary drift and idempotent repair", _drift_and_repair),
            Case("summary reconciles leaf membership", _source_membership),
            Case("summary refuses invalid numbers and statuses", _invalid_numbers_and_status),
            Case("summary refuses missing and duplicated markers", _marker_refusals),
            Case("summary zero denominator and decimal formatting", _zero_and_decimal_formatting)]
