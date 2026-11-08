# SPDX-License-Identifier: Apache-2.0
"""Structured reporting for static checks and test runners.

Each rule records a single verdict line: `ok <rule>: ...` when clean, or
`FAIL <rule>: <count> <label>` followed by seven-space-indented finding lines.
Output is accumulated in memory so callers can inspect `findings`, `decisions`,
and `out` directly before printing.
"""

from collections.abc import Iterable


class Reporter:
    """Collects a run's output and counts its findings."""

    def __init__(self) -> None:
        self.findings = 0
        self.out: list[str] = []
        self.decisions: list[str] = []

    def line(self, text: str = "") -> None:
        self.out.append(text)

    def report(self, rule: str, label: str, items: Iterable[object],
               ok: str = "", pad: str = "", count: int | None = None) -> None:
        """Record one rule's verdict.

        Falsy items in `items` are ignored. `count` overrides `len(found)` when
        `items` is a grouped summary (such as [toolchain/cli/typecheck.py](cli/typecheck.py)'s
        per-rule sample cap) rather than one line per finding.
        """
        self.decisions.append(rule)
        found = [str(i) for i in items if i]
        if found:
            total = len(found) if count is None else count
            self.findings += total
            self.out.append(f"{pad}FAIL {rule}: {total} {label}")
            self.out.extend(f"{pad}       {f}" for f in found)
        else:
            self.out.append(f"{pad}ok {rule}: {ok or label}")


def sites(name: str, lines: list[int], cap: int = 12) -> str:
    """Format a filename and 1-based line numbers, truncating after `cap` lines."""
    shown = (", ".join(str(n) for n in lines[:cap]) + f", and {len(lines) - cap} more"
             if len(lines) > cap else ", ".join(str(n) for n in lines))
    return f"{name}: {len(lines)} line(s): {shown}"


def apart(ref: str, commit: str) -> tuple[str, str]:
    """Format two revision hashes to at least 12 characters, or one character past their common prefix."""
    if ref == commit:
        return ref[:12], commit[:12]
    shown = max(12, next((i + 1 for i, (a, b) in enumerate(zip(ref, commit, strict=False))
                          if a != b), min(len(ref), len(commit)) + 1))
    return ref[:shown], commit[:shown]
