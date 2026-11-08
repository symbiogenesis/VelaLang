# SPDX-License-Identifier: Apache-2.0
"""Trace normalization, fingerprinting, and differential adjudication for simulator runs.

Supports two trace formats:
  - **Commit trace** (`--trace-commit`): fixed-radix instruction retire, register/SCR/CSR
    write, memory access, and trap records (`normalize_commit` and `digest`).
  - **Verbose trace** (`-v`): instruction retire, integer/capability register write, and
    memory read records normalized across the curated C++ simulator and upstream C oracle
    (`normalize` and `adjudicate`).
"""

import hashlib
import re
from dataclasses import dataclass

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


# --- Verbose simulator trace (`-v`) ----------------------------------------

# `[7]: 0x0000000080000054 (0x00000113) addi x2, x0, 0x0`         (curated)
# `[7] [M]: 0x0000000080000054 (0x00000113) addi sp, zero, 0x0`   (oracle)
RETIRE_RE = re.compile(r"^\[\d+\](?: \[\w+\])?: 0x([0-9A-Fa-f]+) \(0x([0-9A-Fa-f]+)\)")

# `x1 <- t:0 0x0000000000000000`                                  (curated)
# `x1 <-  t:0 s:0 perms:... type:... address:0x... base:... ...`  (oracle)
XWRITE_RE = {
    "curated": re.compile(r"^x(\d+) <- t:\d+ 0x([0-9A-Fa-f]+)\s*$"),
    "oracle": re.compile(r"^x(\d+) <-\s+t:\d+ .*\baddress:0x([0-9A-Fa-f]+)\b"),
}

# `mem[R,0x0000000080002000] -> 0x00AA00AA`         (oracle)
# `mem[R,0x080002000] -> t:0 0x00AA00AA`            (curated)
MEMREAD_RE = re.compile(r"^mem\[R,0x([0-9A-Fa-f]+)\] -> (?:t:\d+ )?0x([0-9A-Fa-f]+)\s*$")

DIALECTS = tuple(XWRITE_RE)


def normalize(lines: list[str], dialect: str) -> list[str]:
    xwrite = XWRITE_RE[dialect]
    records: list[str] = []
    for raw in lines:
        line = raw.rstrip("\n")
        m = RETIRE_RE.match(line)
        if m:
            records.append(f"I {int(m.group(1), 16):016X} {int(m.group(2), 16):08X}")
            continue
        m = xwrite.match(line)
        if m:
            records.append(f"X {int(m.group(1)):2d} {int(m.group(2), 16):016X}")
            continue
        m = MEMREAD_RE.match(line)
        if m:
            records.append(f"R {int(m.group(1), 16):016X} {m.group(2).upper()}")
    return records


def _first_retire_pc(records: list[str]) -> int | None:
    for record in records:
        if record.startswith("I "):
            return int(record.split()[1], 16)
    return None


def _align(records: list[str], first_pc: int) -> list[str]:
    """Drop records preceding the first retirement at `first_pc`."""
    for i, record in enumerate(records):
        if record.startswith("I ") and int(record.split()[1], 16) == first_pc:
            return records[i:]
    return []


@dataclass(frozen=True)
class Verdict:
    """Result of comparing two normalized trace streams."""

    prefix: int = 0
    compared: int = 0
    divergence: tuple[str, str] | None = None
    error: str | None = None
    agreed: tuple[str, ...] = ()          # the records just before a divergence

    @property
    def ok(self) -> bool:
        return self.error is None and self.divergence is None

    def line(self) -> str:
        if bool(self.error):
            return self.error
        if self.divergence:
            return f"prefix {self.prefix} of {self.compared} compared"
        return f"agreed over {self.compared} records"


def adjudicate(curated: list[str], oracle: list[str], context: int = 4) -> Verdict:
    """Align `oracle` to `curated`'s first retired PC and compare records up to the shorter stream's end."""
    start = _first_retire_pc(curated)
    if start is None:
        return Verdict(error="no retire records in the curated trace")
    aligned = _align(oracle, start)
    if not aligned:
        return Verdict(error="the oracle never reaches the curated model's first PC "
                             f"0x{start:016X}")

    compared = min(len(curated), len(aligned))
    for i in range(compared):
        if curated[i] != aligned[i]:
            return Verdict(prefix=i, compared=compared,
                           divergence=(curated[i], aligned[i]),
                           agreed=tuple(curated[max(0, i - context):i]))
    # One stream running out is not a divergence: the two machines halt on
    # different conditions, and a shorter range that agrees to its end is what
    # the corpus is asking about.
    return Verdict(prefix=compared, compared=compared)
