# SPDX-License-Identifier: Apache-2.0
"""Canonical 32-bit instruction encodings and register tables for the purecap assembler.

Loads the generated instruction encoding table (`tools/generated/dialect-table.json`)
along with the authored `fence` row and register/CSR/SCR name mappings used by
[asm.py](asm.py).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from . import corpus

TABLE_PATH = "tools/generated/dialect-table.json"
VERSION = 1

# Architectural and ABI names for the 32 merged integer/capability registers.
ABI_NAMES = (
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
)


def _registers() -> dict[str, int]:
    """Build the lookup table mapping `xN`, `cN`, `cxN`, ABI, and `c`-prefixed ABI register names to indices `0..31`."""
    table: dict[str, int] = {}
    for number, abi in enumerate(ABI_NAMES):
        table[f"x{number}"] = number
        table[f"c{number}"] = number
        table[f"cx{number}"] = number
        table[abi] = number
        table[f"c{abi}"] = number
    table["fp"] = 8
    table["cfp"] = 8
    table["cnull"] = 0
    return table


REGISTERS: Final[dict[str, int]] = _registers()

# Named Control and Status Registers (CSRs) and their 12-bit addresses.
CSRS: dict[str, int] = {
    "mstatus": 0x300, "misa": 0x301, "mie": 0x304,
    "mtvec": 0x305, "mepc": 0x341,
    "mcause": 0x342, "mtval": 0x343, "mip": 0x344,
    "mvendorid": 0xF11, "marchid": 0xF12, "mimpid": 0xF13,
    "mhartid": 0xF14, "mconfigptr": 0xF15,
    "vstart": 0x008, "vxsat": 0x009, "vxrm": 0x00A, "vcsr": 0x00F,
    "vl": 0xC20, "vtype": 0xC21, "vlenb": 0xC22,
    "dcsr": 0x7B0, "dpc": 0x7B1, "dscratch0": 0x7B2, "dscratch1": 0x7B3,
}

# Special Capability Registers (SCRs) addressed by `cspecialrw`.
SCRS: dict[str, int] = {"pcc": 0b00000, "mtcc": 0b11100, "mtdc": 0b11101,
                        "mepcc": 0b11111}


def _vregisters() -> dict[str, int]:
    """Return vector register names `v0` through `v31` (kept distinct from integer/capability `REGISTERS`)."""
    return {f"v{number}": number for number in range(32)}


VREGISTERS: Final[dict[str, int]] = _vregisters()


class AsmError(Exception):
    """Error raised when an assembly source program violates syntax, operand, or layout constraints."""


# ---------------------------------------------------------------------------
# Encoding table structures

@dataclass(frozen=True)
class Slot:
    """Bit-field placement and range rules for one instruction operand.

    `pieces` holds `(word_hi, word_lo, src_hi, src_lo)` bit slices; `align` is the
    required power-of-two alignment factor (`1` when unshifted).
    """

    kind: str
    name: str
    width: int
    signed: bool
    align: int
    pieces: tuple[tuple[int, int, int, int], ...]


@dataclass(frozen=True)
class Require:
    """Operand guard constraint (`ne` or `in`) extracted from the model's `when` clause."""

    kind: str
    operand: str
    values: tuple[int, ...]
    guard: str


@dataclass(frozen=True)
class Row:
    """Encoding specification for one instruction mnemonic."""

    ctor: str
    site: str
    word: int
    mask: int
    guard: str
    signature: tuple[str, ...]
    slots: tuple[Slot, ...]
    requires: tuple[Require, ...]


# Human-readable labels for operand kinds in diagnostic messages.
KINDS: Final[dict[str, str]] = {
    "reg": "register", "vreg": "vector register", "vm": "vector mask",
    "csr": "CSR address", "scr": "special capability register",
    "imm": "", "sym": "displacement", "mem": "", "mem0": "", "index": "", "v0": "",
}


def _fence() -> Row:
    """Return the authored `fence` row (whose unstructured assembly clause in the model omits operand slots)."""
    return Row(
        ctor="FENCE",
        site="model/model/extensions/I/base_insts.sail",
        word=0b0001111,
        mask=0xF00FFFFF,
        guard="",
        signature=("imm", "imm"),
        slots=(
            Slot(kind="imm", name="pred", width=4, signed=False, align=1,
                 pieces=((27, 24, 3, 0),)),
            Slot(kind="imm", name="succ", width=4, signed=False, align=1,
                 pieces=((23, 20, 3, 0),)),
        ),
        requires=(),
    )


def _load(root: Path | None = None) -> dict[str, Row]:
    """Load the generated dialect table from `TABLE_PATH` and add the authored `fence` row."""
    here = root or corpus.find_root(Path(__file__).resolve())
    raw = json.loads((here / TABLE_PATH).read_text(encoding="utf-8"))
    header = raw.get("header", {})
    if header.get("version") != VERSION:
        raise AssertionError(
            f"{TABLE_PATH} states version {header.get('version')!r} and this reader is "
            f"written against version {VERSION}")
    table: dict[str, Row] = {}
    for name, row in raw.get("rows", {}).items():
        table[name] = Row(
            ctor=str(row["ctor"]),
            site=str(row["site"]),
            word=int(row["word"]),
            mask=int(row["mask"]),
            guard=str(row["guard"]),
            signature=tuple(str(kind) for kind in row["signature"]),
            slots=tuple(Slot(kind=str(s["kind"]), name=str(s["name"]),
                             width=int(s["width"]), signed=bool(s["signed"]),
                             align=int(s["align"]),
                             pieces=tuple((int(p[0]), int(p[1]), int(p[2]), int(p[3]))
                                          for p in s["pieces"]))
                        for s in row["slots"]),
            requires=tuple(Require(kind=str(r[0]), operand=str(r[1]),
                                   values=tuple(int(v) for v in r[2]),
                                   guard=str(row["guard"]))
                           for r in row["requires"]),
        )
    fence = _fence()
    if "fence" in table:
        raise AssertionError("the generated table now carries `fence`, so the authored "
                             "row beside it is a second copy of one fact")
    table["fence"] = fence
    return table


TABLE: Final[dict[str, Row]] = _load()

# Sorted tuple of all supported instruction mnemonics.
MNEMONICS = tuple(sorted(TABLE))


def signature(mnemonic: str) -> tuple[str, ...]:
    """Return the expected operand-kind tuple for `mnemonic` in source order."""
    return TABLE[mnemonic].signature


def _fit(slot: Slot, value: int, _mnemonic: str) -> int:
    """Validate `value`'s alignment and signed/unsigned range for `slot`, returning its masked bit pattern."""
    label = KINDS.get(slot.kind) or slot.name
    if slot.align > 1 and value % slot.align:
        raise AsmError(f"{label} {value} is not a multiple of {slot.align}")
    scaled = value // slot.align
    bits = slot.width - (slot.align.bit_length() - 1)
    low, high = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if slot.signed \
        else (0, (1 << bits) - 1)
    if not low <= scaled <= high:
        raise AsmError(f"{label} {value} is outside "
                       f"[{low * slot.align}, {high * slot.align}]")
    return value & ((1 << slot.width) - 1)


def _required(row: Row, mnemonic: str, values: list[int]) -> None:
    """Verify that `values` satisfy all `Require` guard constraints on `row`."""
    for want in row.requires:
        for slot, value in zip(row.slots, values, strict=True):
            if slot.name != want.operand:
                continue
            spelled = ", ".join(str(v) for v in want.values)
            if want.kind == "ne" and value in want.values:
                raise AsmError(f"{mnemonic} takes no {slot.name} of {spelled}: the "
                               f"model decodes it only `when {want.guard}`")
            if want.kind == "in" and value not in want.values:
                raise AsmError(f"{mnemonic} takes {slot.name} of {spelled} and no "
                               f"other: the model decodes it only "
                               f"`when {want.guard}`")


def encode(mnemonic: str, operands: list[int], pc: int) -> int:
    """Encode `mnemonic` with resolved `operands` at `pc` into a 32-bit instruction word."""
    row = TABLE[mnemonic]
    if len(operands) != len(row.slots):
        raise AssertionError(f"{mnemonic} places {len(row.slots)} operands and was "
                             f"handed {len(operands)}")
    _required(row, mnemonic, operands)
    word = row.word
    for slot, given in zip(row.slots, operands, strict=True):
        # Convert `sym` target addresses into PC-relative displacements.
        value = _fit(slot, given - pc if slot.kind == "sym" else given, mnemonic)
        for _word_hi, word_lo, src_hi, src_lo in slot.pieces:
            run = (1 << (src_hi - src_lo + 1)) - 1
            word |= ((value >> src_lo) & run) << word_lo
    if not 0 <= word < (1 << 32):
        raise AssertionError(f"{mnemonic} encoded outside 32 bits: {word:#x}")
    return word
