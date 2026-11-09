# SPDX-License-Identifier: Apache-2.0
"""Commit-trace normalization and fingerprinting for simulator runs."""

import hashlib
import re

# --- Commit trace (`--trace-commit`) ---------------------------------------
#
# Fixed-radix records emitted per retired instruction and architectural effect:
#   I <order> <pc> <insn>                  instruction retired
#   X <reg> <tag> <value>                  register write (with capability tag)
#   S <scr> <tag> <value>                  special capability register write
#   C <csr> <value>                        CSR write
#   R <addr> <width> <tag> <value>         memory read
#   W <addr> <width> <tag> <value>         memory write
#   T <interrupt> <cause>                  trap
COMMIT_RE = re.compile(r"^(?:I \d+ [0-9A-F]{16} [0-9A-F]{8}"
                       r"|X \d+ [01] [0-9A-F]{16}"
                       r"|S \d+ [01] [0-9A-F]{16}"
                       r"|C [0-9A-F]{3} [0-9A-F]{16}"
                       r"|[RW] [0-9A-F]+ \d+ [01] [0-9A-F]+"
                       r"|T [01] \d+)$")

# Strip the retirement counter from `I <order> ...` so traces remain comparable
# across executors that enter through different reset sequences.
ORDER_RE = re.compile(r"^I \d+ ")


def normalize_commit(lines: list[str]) -> list[str]:
    """Filter `lines` to commit-trace records and strip retirement order numbers."""
    records: list[str] = []
    for raw in lines:
        line = raw.rstrip("\n").rstrip()
        if COMMIT_RE.match(line):
            records.append(ORDER_RE.sub("I ", line))
    return records


def digest(records: list[str]) -> str:
    """Return the first 16 hex digits of the SHA-256 digest of newline-joined `records`."""
    blob = "\n".join(records).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
