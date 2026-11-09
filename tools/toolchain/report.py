# SPDX-License-Identifier: Apache-2.0
"""Structured reporting for static checks and test runners.

Each rule records a single verdict line: `ok <rule>: ...` when clean, or
`FAIL <rule>: <count> <label>` followed by seven-space-indented finding lines.
Output is accumulated in memory so callers can inspect `findings` and `out`
directly before printing.
"""

from collections.abc import Iterable


class Reporter:
    """Collects a run's output and counts its findings."""

    def __init__(self) -> None:
        self.findings = 0
        self.out: list[str] = []

    def line(self, text: str = "") -> None:
        self.out.append(text)

    def extend(self, other: Reporter) -> None:
        self.findings += other.findings
        self.out.extend(other.out)

    def report(self, rule: str, label: str, items: Iterable[object],
               ok: str = "", pad: str = "", count: int | None = None) -> None:
        """Record one rule's verdict.

        Falsy items in `items` are ignored. `count` overrides `len(found)` when
        `items` is a grouped summary (such as [toolchain/cli/typecheck.py](cli/typecheck.py)'s
        per-rule sample cap) rather than one line per finding.
        """
        found = [str(i) for i in items if i]
        if found:
            total = len(found) if count is None else count
            self.findings += total
            self.out.append(f"{pad}FAIL {rule}: {total} {label}")
            self.out.extend(f"{pad}       {f}" for f in found)
        else:
            self.out.append(f"{pad}ok {rule}: {ok or label}")
