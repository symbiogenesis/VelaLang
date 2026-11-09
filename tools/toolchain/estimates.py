# SPDX-License-Identifier: Apache-2.0
"""Derive the priced-checklist summary in [PLAN.md](../../PLAN.md#current-summary)."""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

START = "<!-- estimate-summary:start -->"
END = "<!-- estimate-summary:end -->"
_ID = r"Q25[a-z]*"
_NUMBER = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_CHECKBOX = re.compile(r"^(?P<indent> *)[-*] \[(?P<status>[ x])\] (?P<label>.*)$")
_LABEL = re.compile(rf"^\*\*(?P<id>{_ID}) · .+?\*\*(?P<cell>.*)$")
_RECORD_HEADER = ["Item", "Class", "Estimate (h)", "Range (h)", "Actual (h)", "Ratio"]


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line == heading]
    if len(starts) != 1:
        raise ValueError(f"expected exactly one {heading!r} section")
    start = starts[0] + 1
    end = next((index for index in range(start, len(lines))
                if lines[index].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def _leaves(text: str) -> dict[str, bool]:
    checkboxes = []
    for line in _section(text, "## Checklist items (Q25 series)").splitlines():
        match = _CHECKBOX.fullmatch(line)
        if match is not None:
            checkboxes.append(match)
        elif re.search(r"^\s*[-*] \[.*Q25", line):
            raise ValueError(f"malformed Q25 checklist item: {line.strip()}")
    leaves: dict[str, bool] = {}
    seen: set[str] = set()
    for index, match in enumerate(checkboxes):
        label = _LABEL.fullmatch(match["label"])
        if label is None:
            raise ValueError(f"malformed Q25 checklist label: {match['label']}")
        item = label["id"]
        if item in seen:
            raise ValueError(f"duplicate checklist item {item}")
        seen.add(item)
        if index + 1 < len(checkboxes) and len(checkboxes[index + 1]["indent"]) > len(match["indent"]):
            if label["cell"].strip():
                raise ValueError(f"parent {item} must not carry an hours cell")
            continue
        leaves[item] = match["status"] == "x"
    if not leaves:
        raise ValueError("the Q25 checklist contains no priced leaves")
    return leaves


def _number(value: str, context: str) -> Decimal:
    try:
        number = Decimal(value.replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"{context}: invalid number {value!r}") from error
    if not number.is_finite() or number < 0 or re.fullmatch(_NUMBER, value) is None:
        raise ValueError(f"{context}: expected a finite nonnegative number, found {value!r}")
    return number


def _optional(value: str, context: str) -> Decimal | None:
    return None if value == "n/a" else _number(value, context)


def _range(value: str, estimate: Decimal | None, item: str) -> tuple[Decimal, Decimal] | None:
    if value == "n/a":
        return None
    bounds = re.fullmatch(rf"({_NUMBER})[–-]({_NUMBER})", value)
    if bounds is None or estimate is None:
        raise ValueError(f"{item}: invalid estimate range {value!r}")
    low, high = (_number(bound, item) for bound in bounds.groups())
    if not low <= estimate <= high:
        raise ValueError(f"{item}: range must contain the estimate midpoint")
    return low, high


def _records(text: str) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    header_seen = False
    for line in _section(text, "## Calibration record (Q25 series)").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells == _RECORD_HEADER and not header_seen:
            header_seen = True
            continue
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) != len(_RECORD_HEADER) or re.fullmatch(_ID, cells[0]) is None:
            raise ValueError(f"malformed Q25 calibration row: {line}")
        item = cells[0]
        if item in records:
            raise ValueError(f"duplicate calibration row {item}")
        records[item] = cells
    if not header_seen:
        raise ValueError("the Q25 calibration table header is missing or malformed")
    return records


def _hours(value: Decimal) -> str:
    formatted = f"{value:,f}"
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def render_summary(text: str) -> str:
    """Render the hours-weighted summary, refusing inconsistent source records."""
    leaves = _leaves(text)
    records = _records(text)
    if leaves.keys() != records.keys():
        missing = ", ".join(sorted(leaves.keys() - records.keys())) or "n/a"
        extra = ", ".join(sorted(records.keys() - leaves.keys())) or "n/a"
        raise ValueError(f"calibration membership differs from checklist leaves; missing: {missing}; extra: {extra}")
    completed = retained_hours = low = high = Decimal(0)
    unmeasured = 0
    opened = {"I": Decimal(0), "X": Decimal(0)}
    for item, done in leaves.items():
        _, cls, estimate_text, range_text, actual_text, ratio_text = records[item]
        estimate = _optional(estimate_text, item)
        actual = _optional(actual_text, item)
        _optional(ratio_text, item)
        bounds = _range(range_text, estimate, item)
        if cls not in {"I", "X", "X-authored", "X-read", "n/a"}:
            raise ValueError(f"{item}: unknown calibration class {cls!r}")
        cls = "X" if cls.startswith("X") else cls
        if done:
            hours = actual if actual is not None else estimate
            if hours is None:
                raise ValueError(f"{item}: completed leaf requires an actual or retained estimate")
            completed += hours
            if actual is None:
                retained_hours += hours
                unmeasured += 1
        else:
            if actual is not None:
                raise ValueError(f"{item}: open leaf cannot carry actual hours")
            if estimate is None or bounds is None or cls == "n/a":
                raise ValueError(f"{item}: open leaf requires a priced estimate, range and class")
            hours = estimate
            opened[cls] += hours
            low += bounds[0]
            high += bounds[1]
    remaining = sum(opened.values(), Decimal(0))
    total = completed + remaining
    percentage = (str((completed * 100 / total).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
                  if total else "n/a")
    rows = [
        ("Total estimate midpoint h", _hours(total)),
        ("Total estimate range h", f"{_hours(completed + low)}–{_hours(completed + high)}"),
        ("Completed scope h", _hours(completed)),
        ("Complete by estimate %", percentage),
        ("Remaining h", _hours(remaining)),
        ("Open class I h", _hours(opened["I"])),
        ("Open class X h", _hours(opened["X"])),
        ("Retained completion estimate h", _hours(retained_hours)),
        ("Unmeasured completed items", str(unmeasured)),
    ]
    return "\n".join(["| Measure | Value |", "| --- | --- |",
                      *(f"| {label} | {value} |" for label, value in rows)])


def update_summary(text: str) -> str:
    """Replace exactly one marked summary after all source records validate."""
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("the estimate summary requires exactly one start and end marker")
    start = text.index(START) + len(START)
    end = text.index(END)
    if start >= end:
        raise ValueError("the estimate summary markers are out of order")
    return text[:start] + "\n" + render_summary(text) + "\n" + text[end:]


def findings(text: str) -> list[str]:
    """Report source errors or a stale generated table without mutating text."""
    try:
        updated = update_summary(text)
    except ValueError as error:
        return [str(error)]
    return ([] if updated == text else
            ["the estimate summary is stale; run python tools/run.py check --fix"])
