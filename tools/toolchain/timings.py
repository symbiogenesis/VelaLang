# SPDX-License-Identifier: Apache-2.0
"""Diagnostic component timings recorded alongside a command's report.

When `VOS_GATE_TIMINGS` names an output path, a command claims and removes the
variable from `os.environ` (so child processes do not overwrite their parent's
file) and writes its measured units as JSON. Timings are purely diagnostic:
I/O errors are ignored and never affect a command's report or exit code.
"""

import json
import os
from pathlib import Path

from toolchain.atomic import atomic_path

ENV = "VOS_GATE_TIMINGS"

type Unit = dict[str, object]


def claim() -> Path | None:
    """This process's timings file, if the gate named one, taken out of the environment."""
    value = os.environ.pop(ENV, "")
    return Path(value) if value else None


def write(path: Path | None, units: list[Unit]) -> None:
    """Atomically replace a diagnostic snapshot, keeping its predecessor on failure."""
    if path is None:
        return
    try:
        with (atomic_path(path) as pending,
              pending.open("w", encoding="utf-8", newline="") as stream):
            stream.write(json.dumps(units, indent=1) + "\n")
    except OSError:
        pass
