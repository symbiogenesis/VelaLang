# SPDX-License-Identifier: Apache-2.0
"""Bounded semantic-token deltas over complete compiler-projected streams."""


def token_edits(previous: tuple[int, ...], current: tuple[int, ...]) -> list[dict[str, object]]:
    """Replace the differing integer interval, retaining equal prefix and suffix."""
    first = 0
    common = min(len(previous), len(current))
    while first < common and previous[first] == current[first]:
        first += 1
    if first == len(previous) == len(current):
        return []
    tail = 0
    while (tail < common - first
           and previous[len(previous) - tail - 1] == current[len(current) - tail - 1]):
        tail += 1
    end = len(current) - tail
    edit: dict[str, object] = {"start": first, "deleteCount": len(previous) - tail - first}
    if end > first:
        edit["data"] = list(current[first:end])
    return [edit]
