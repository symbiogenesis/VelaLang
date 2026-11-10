# SPDX-License-Identifier: Apache-2.0
"""Purecap compiler differential harness, assembly composer, and simulator runner."""

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from toolchain import asm, dialect, image, trace
from toolchain.dialect import AsmError

# Harness stack size in bytes in `.data`.
STACK_BYTES: Final = 16384

# HTIF exit-code offset distinguishing traps (`TRAP_BASE | mcause`) from `main` return values (`0..255`).
TRAP_BASE: Final = 0x100

INST_LIMIT: Final = 1_000_000
COMPILE_TIMEOUT: Final = 120
RUN_TIMEOUT: Final = 60


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _observe_process(command: list[str], done: subprocess.CompletedProcess[str], log: Path,
                     observations: list[dict[str, object]] | None, cwd: Path | None = None) -> None:
    """Retain complete decoded streams only when an evidence consumer requests them."""
    if observations is None:
        return
    stdout, stderr = done.stdout.encode("utf-8"), done.stderr.encode("utf-8")
    raw = stdout + stderr
    log.write_bytes(raw)
    observation: dict[str, object] = {
        "command": command, "returncode": done.returncode,
        "log": str(log), "log_sha256": _sha256(raw),
        "stdout_bytes": len(stdout), "stdout_sha256": _sha256(stdout),
        "stderr_bytes": len(stderr), "stderr_sha256": _sha256(stderr),
    }
    if cwd is not None:
        observation["cwd"] = str(cwd)
    observations.append(observation)


# =====================================================================================
# The scan: what the in-tree assembler refuses in an emitted stream, by name and by line
# =====================================================================================


@dataclass(frozen=True)
class Refusal:
    """One line of an emitted stream the in-tree assembler will not take, and why.

    `kind` is `mnemonic` for a name the dialect table and the pseudo-instructions do not
    spell, `directive` for a directive the parser does not know, `section` for a `.section`
    naming one the image does not have, `label` for a numeric local label, which the
    assembler's label grammar has no form for, `relocation` for a `%pcrel_hi(...)`-style
    operator, which the assembler has none of by design (R-15-002b, R-15-036l: layout is
    absolute, so there is nothing to relocate), `operand` for a known mnemonic or directive
    whose operands the assembler refused, `symbol` for a stream that defines no `main`, and
    `layout` for an image the composer cannot place. `line` is 1-based in the emitted
    stream, and 0 where the refusal is not a line's.
    """

    kind: str
    name: str
    line: int
    detail: str = ""


_NUMERIC_LABEL_RE = re.compile(r"(\d+)\s*:")
_RELOCATION_RE = re.compile(r"%[A-Za-z_]+\(")
_ASM_ERROR_RE = re.compile(r"^(.*?):(\d+): (.*)$", re.DOTALL)


def normalize(stream: str) -> str:
    """The emitted stream with every tab a space, which is the one rewrite the driver makes.

    CompCert's printer separates a mnemonic from its operands with a tab and the assembler's
    line parse splits the two on a space alone, so an unnormalized stream is refused whole,
    every instruction reading as a mnemonic with its first operand glued on. A tab inside a
    string literal would move with the rest, which the generator never writes and a reader
    of the refusal list would see as a changed `.ascii`.
    """
    return stream.replace("\t", " ")


def _split(raw: str) -> tuple[list[str], str]:
    """One line as the assembler reads it: the labels it declares, and what follows them
    once the comment is gone.

    A numeric local label is taken off the front too, spelled with its colon so a reader
    tells `1:` from a symbol: the assembler does not read one, and leaving it in place
    would make the mnemonic behind it read as the refusal.
    """
    text = raw.split("#", 1)[0].split("//", 1)[0].strip()
    labels: list[str] = []
    while text:
        label = asm.LABEL_RE.match(text) or _NUMERIC_LABEL_RE.match(text)
        if not label:
            break
        labels.append(label.group(1) + (":" if label.re is _NUMERIC_LABEL_RE else ""))
        text = text[label.end():].strip()
    return labels, text


def _head(raw: str) -> tuple[str, str] | None:
    """A line's mnemonic or directive and its operand text, or `None` for a line carrying
    neither."""
    _, text = _split(raw)
    if not text:
        return None
    head, _, rest = text.partition(" ")
    return head.lower(), rest.strip()


def _directive_refusal(head: str, rest: str, number: int) -> Refusal | None:
    """Whether the assembler takes this directive line on its own, and how it refuses it.

    The parser is asked rather than a list of its directives restated here: the line is
    parsed alone, which is enough to decide a directive's name and a section's, and an
    operand the parser refuses is reported as the parser words it.
    """
    try:
        asm.Assembler(f"{head} {rest}".strip(), "stream")
    except AsmError as exc:
        said = str(exc).partition(": ")[2] or str(exc)
        if said.startswith("no directive"):
            return Refusal("directive", head, number)
        if said.startswith("no section"):
            return Refusal("section", rest.partition(",")[0].strip(), number)
        return Refusal("operand", head, number, said)
    return None


def refusals(stream: str) -> list[Refusal]:
    """Every line of `stream` the assembler refuses by name, before anything is laid out.

    A mnemonic is decided against the dialect table and the pseudo-instructions, a
    directive by parsing its line alone. Operand-level refusals of an instruction are not
    found here, because deciding one needs the layout; `assemble` reports those.
    """
    found: list[Refusal] = []
    for number, raw in enumerate(normalize(stream).splitlines(), 1):
        labels, text = _split(raw)
        found += [Refusal("label", label, number) for label in labels if label[0].isdigit()]
        found += [Refusal("relocation", found_at.group()[:-1], number)
                  for found_at in _RELOCATION_RE.finditer(text)]
        parsed = _head(raw)
        if parsed is None:
            continue
        head, rest = parsed
        if head.startswith("."):
            refused = _directive_refusal(head, rest, number)
            if refused is not None:
                found.append(refused)
        elif head not in asm.PSEUDOS and head not in dialect.TABLE:
            found.append(Refusal("mnemonic", head, number))
    return found


def _defines_main(stream: str) -> bool:
    return any("main" in _split(raw)[0] for raw in stream.splitlines())


# =====================================================================================
# The harness, and assembling a stream under it
# =====================================================================================

_SETUP: Final = f"""\
        .text
        .globl _start
_start:
        cmove   c4, c1
        la      c9, __vela_handler
        cspecialrw cnull, mtcc, c9
        li      t0, __vela_stack
        csetaddr csp, c4, t0
        li      t1, {STACK_BYTES}
__vela_stack_bounds:
        csetbounds csp, csp, t1
        li      t1, 0xFFE
        candperm csp, csp, t1
        li      t0, __vela_stack_top
        csetaddr csp, csp, t0
        call    main
"""

PROLOGUE: Final = f"""\
# The M1.2f driver's harness around an emitted stream. Every authority is derived off the
# store-side root (R-15-001c). c4 is reserved by the selected scalar ABI; c8, like every
# allocatable register, can be overwritten by main. Clearing expanded permission bit 0
# removes globality while retaining root_data_cap's store-local stack shape.
{_SETUP}\
        beqz    a0, __vela_pass
        andi    gp, a0, 0xFF
        bnez    gp, __vela_fail
        li      gp, 0xFF
__vela_fail:
        slli    t0, gp, 1
        ori     t0, t0, 1
        j       __vela_exit
__vela_pass:
        li      t0, 1
__vela_exit:
        li      t1, tohost
        csetaddr c31, c4, t1
        sd      t0, 0(c31)
__vela_halt:
        j       __vela_halt
__vela_handler:
        csrr    t0, mcause
        andi    t0, t0, 0xFF
        ori     gp, t0, 0x100
        j       __vela_fail
# --- the emitted stream follows ---
"""

EPILOGUE: Final = f"""\
# --- the emitted stream ends ---
        .data
        .align  3
tohost:
        .dword  0
        .align  8
__vela_stack:
        .space  {STACK_BYTES}
__vela_stack_top:
"""


def compose(stream: str, prologue: str = PROLOGUE) -> str:
    """The composite the assembler is handed: the harness around the normalized stream."""
    body = normalize(stream)
    if body and not body.endswith("\n"):
        body += "\n"
    return prologue + body + EPILOGUE


def assemble(stream: str, name: str, elf: Path,
             prologue: str = PROLOGUE) -> tuple[list[Refusal], int]:
    """Assemble `stream` under the harness into `elf`.

    Returns the refusals found and the image's byte count; the image is written only where
    the list is empty. The scan runs first so that a stream the dialect refuses is reported
    whole rather than at its first refused line, and the layout runs second so that an
    operand the parser could not decide alone is still named by its line.
    """
    found = refusals(stream)
    if found:
        return found, 0
    if not _defines_main(stream):
        return [Refusal("symbol", "main", 0, "the stream defines no `main`")], 0
    assembler = asm.Assembler(compose(stream, prologue), name)
    try:
        sections, symbols, entry = assembler.assemble()
    except AsmError as exc:
        return [_layout_refusal(exc, stream, prologue.count("\n"))], 0
    text = sum(len(s.data) for s in sections if s.name == ".text")
    if text > asm.DATA_BASE - asm.TEXT_BASE:
        return [Refusal("layout", ".text", 0,
                        f"{text} bytes of text reach the data section at "
                        f"{asm.DATA_BASE:#x}")], 0
    image.write_elf(elf, sections, symbols, entry)
    return [], sum(len(s.data) for s in sections)


def _layout_refusal(exc: AsmError, stream: str, offset: int) -> Refusal:
    """An assembler diagnostic over the composite, named by the stream's own line;
    `offset` is the line count of the harness prologue ahead of the stream."""
    said = str(exc)
    matched = _ASM_ERROR_RE.match(said)
    if matched is None:
        return Refusal("operand", "?", 0, said)
    number = int(matched.group(2)) - offset
    message = matched.group(3)
    lines = normalize(stream).splitlines()
    if 1 <= number <= len(lines):
        parsed = _head(lines[number - 1])
        return Refusal("operand", parsed[0] if parsed else "?", number, message)
    # Outside the stream is the harness, and a harness that does not assemble is this
    # driver's defect rather than the stream's; it is still reported and never raised,
    # because a run's report is the artifact and a traceback is not one.
    return Refusal("operand", "harness", 0, f"line {matched.group(2)} of the composite: "
                                            f"{message}")


# =====================================================================================
# The compiler, and the emulator
# =====================================================================================


@dataclass(frozen=True)
class Preprocessed:
    """The exact self-contained translation unit handed to both compiler readings.

    `.c` runs through this compiler's `-E` in its source directory, preserving relative
    includes. `.i` is already preprocessed and is copied byte for byte. The digest binds
    the effective transitive include closure, not a separately guessed include list.
    """

    argv: tuple[str, ...]
    cwd: str
    exit_code: int
    said: str
    path: Path
    source_sha256: str
    sha256: str


def preprocess_c(ccomp: list[str], source: Path, fresh: Path,
                 timeout: int = COMPILE_TIMEOUT, *,
                 observations: list[dict[str, object]] | None = None) -> Preprocessed:
    source, fresh = source.resolve(), fresh.resolve()
    fresh.mkdir(parents=True, exist_ok=True)
    unit = fresh / f"{source.stem}.i"
    argv = (*ccomp, "-E", source.name, "-o", str(unit))
    digest = ""
    try:
        raw = source.read_bytes()
        digest = _sha256(raw)
        unit.unlink(missing_ok=True)
        done = subprocess.run(argv, cwd=source.parent, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
        _observe_process(list(argv), done, fresh / f"{source.stem}.preprocess.log",
                         observations, source.parent)
        said = (done.stderr + done.stdout).strip()[:600]
        if done.returncode != 0 or not unit.is_file():
            return Preprocessed(argv, str(source.parent), done.returncode,
                                said or "preprocessor wrote nothing", unit, digest, "")
        if source.read_bytes() != raw:
            return Preprocessed(argv, str(source.parent), -1,
                                "source changed during preprocessing", unit, digest, "")
        return Preprocessed(argv, str(source.parent), 0, said, unit, digest,
                            _sha256(unit.read_bytes()))
    except subprocess.TimeoutExpired:
        said = f"preprocessor had no exit within {timeout}s"
    except (OSError, ValueError) as err:
        said = f"could not preprocess: {err}"
    return Preprocessed(argv, str(source.parent), -1, said, unit, digest, "")


@dataclass(frozen=True)
class Compiled:
    """One `ccomp -S`: how it was asked, what it said, and the stream it wrote."""

    argv: tuple[str, ...]
    exit_code: int
    said: str
    stream: str | None
    stream_sha256: str
    lines: int
    preprocessed: Preprocessed


def compile_c(ccomp: list[str], source: Path, fresh: Path,
              timeout: int = COMPILE_TIMEOUT, *,
              observations: list[dict[str, object]] | None = None) -> Compiled:
    """Run `ccomp -S` over one source in `fresh`, a directory holding nothing else.

    The source is preprocessed once and the resulting `.i` compiled there. This directory is
    not an OS sandbox. Remove any previous assembly first, so a reused --keep directory
    cannot supply a successful invocation that wrote nothing with stale output, and any
    partial assembly an interrupted run left, because the typed route creates that file
    exclusively and would refuse a rerun over it. The argv records the compiler's path
    and two names relative to this directory. Preprocessing has its own recorded cwd.
    """
    fresh = fresh.resolve()
    fresh.mkdir(parents=True, exist_ok=True)
    out = fresh / f"{source.stem}.s"
    out.unlink(missing_ok=True)
    out.with_name(f"{out.name}.partial").unlink(missing_ok=True)
    prepared = preprocess_c(ccomp, source, fresh, timeout, observations=observations)
    argv = [*ccomp, "-S", prepared.path.name, "-o", out.name]
    if not prepared.sha256:
        return Compiled(tuple(argv), prepared.exit_code, prepared.said, None, "", 0, prepared)
    said = ""
    exit_code = -1
    try:
        done = subprocess.run(argv, cwd=fresh, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        said = f"no exit within {timeout}s"
    except OSError as err:
        said = f"could not run: {err}"
    else:
        _observe_process(argv, done, fresh / f"{source.stem}.compile.log", observations, fresh)
        exit_code = done.returncode
        said = (done.stderr + done.stdout).strip()[:600]
    try:
        if _sha256(prepared.path.read_bytes()) != prepared.sha256:
            return Compiled(tuple(argv), -1, "preprocessed input changed during compilation",
                            None, "", 0, prepared)
    except (OSError, ValueError) as err:
        return Compiled(tuple(argv), -1, str(err), None, "", 0, prepared)
    if exit_code != 0 or not out.is_file():
        return Compiled(tuple(argv), exit_code, said or "(wrote nothing)", None, "", 0, prepared)
    raw = out.read_bytes()
    stream = raw.decode("utf-8", errors="replace")
    return Compiled(tuple(argv), 0, said, stream, _sha256(raw), len(stream.splitlines()), prepared)


@dataclass(frozen=True)
class Ran:
    """One emulator run under the corpus's two questions, and the third reading."""

    verdict: str
    code: int | None
    records: int
    digest: str
    cap_roundtrip: bool
    emitted: bytes
    detail: str


_FAILURE_RE = re.compile(r"FAILURE: (\d+)")


def htif_verdict(said: str, returncode: int) -> tuple[str, int | None, str]:
    """Read the emulator's output back as the program's own verdict.

    The exit code is what the program left in the harness's `gp`, on the corpus's own
    convention; the harness puts `main`'s return below `TRAP_BASE` and a trap's cause at or
    above it. An emulator that printed neither line gave no verdict, and a trap loop is
    that case named, because it is what a fault inside the handler itself looks like.
    """
    failed = _FAILURE_RE.search(said)
    if failed:
        code = int(failed.group(1))
        if code >= TRAP_BASE:
            return "trap", code, f"HTIF {code}: cause {code - TRAP_BASE} reached the handler"
        return "fail", code, f"HTIF {code}: main returned {code}"
    if returncode == 0 and re.search(r"^SUCCESS\s*$", said, re.MULTILINE):
        return "pass", 0, "HTIF 0"
    if "trap loop" in said:
        return "no-verdict", None, "the emulator detected a trap loop"
    return "no-verdict", None, f"rc={returncode}, no HTIF verdict"


def cap_roundtrip(records: list[str]) -> bool:
    """Find a stored capability read back intact in normalized commit records.

    R-15-203's capability granule is eight bytes. Every write touching a candidate's
    granule invalidates it, including an ordinary byte store or a block zeroing. A new
    aligned tagged capability write can then supply a fresh candidate. Malformed memory
    records cannot be skipped because a skipped write could hide an intervening change.
    """
    written: dict[int, str] = {}
    for record in records:
        parts = record.split()
        if not parts or parts[0] not in ("W", "R"):
            continue
        if trace.COMMIT_RE.fullmatch(record) is None:
            return False
        address, width = int(parts[1], 16), int(parts[2])
        if width <= 0 or len(parts[4]) != width * 2:
            return False
        capability = width == 8 and address % 8 == 0 and parts[3] == "1"
        if parts[0] == "W":
            for granule in range(address // 8, (address + width - 1) // 8 + 1):
                written.pop(granule * 8, None)
            if capability:
                written[address] = parts[4]
        elif capability and written.get(address) == parts[4]:
            return True
    return False


def run_image(simulator: list[str], profile: Path, elf: Path, workdir: Path,
              timeout: int = RUN_TIMEOUT, inst_limit: int = INST_LIMIT, *,
              observations: list[dict[str, object]] | None = None) -> Ran:
    """Run one image the way `run.py model corpus` runs a member, plus the terminal log.

    The commit trace is read off the merged streams by shape, as the corpus runner reads
    it; the terminal log is the HTIF console, which is where a component's emitted bytes
    land, and it is a file rather than the console so that the emulator's own lines and
    the trace never mix with them. An observation collector additionally retains the
    exact command and separate stdout/stderr identities with a combined process log.
    """
    term = workdir / f"{elf.stem}.term"
    term.unlink(missing_ok=True)
    argv = [*simulator, "--config", str(profile), "--trace-commit",
            "--inst-limit", str(inst_limit), "--terminal-log", str(term), str(elf)]
    try:
        done = subprocess.run(argv, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return Ran("no-verdict", None, 0, "", False, b"",
                   f"no HTIF write within {timeout}s")
    except OSError as err:
        return Ran("no-verdict", None, 0, "", False, b"", f"the emulator could not run: {err}")
    said = done.stdout + done.stderr
    _observe_process(argv, done, workdir / f"{elf.stem}.sail.log", observations)
    records = trace.normalize_commit(said.splitlines())
    emitted = term.read_bytes() if term.is_file() else b""
    verdict, code, detail = htif_verdict(said, done.returncode)
    if verdict == "pass" and not records:
        verdict, code, detail = "no-verdict", None, "HTIF 0 without a commit trace"
    return Ran(verdict, code, len(records), trace.digest(records), cap_roundtrip(records),
               emitted, detail)


# =====================================================================================
# The program-level loop over one input
# =====================================================================================


@dataclass(frozen=True)
class Program:
    """One input: its name, the pattern it exercises, its text, how many checks it
    carries, and what `main` is expected to return.

    Each check returns its own number from `main` on the corpus's convention that a
    failure names the check. `expect` is 0 for an ordinary program and, for a perturbed
    one, the number of the check whose expected constant was moved off by one, so the
    campaign's negative control names the check it must fail at."""

    name: str
    pattern: str
    source: str
    checks: int
    expect: int = 0


@dataclass(frozen=True)
class Interpreted:
    """One `ccomp -interp` run: CompCert's reference interpreter for the source, which is
    the program-level loop's source-side reading of what `main` returns."""

    argv: tuple[str, ...]
    exit_code: int
    code: int | None
    said: str


_TERMINATED_RE = re.compile(
    r"^Time \d+: program terminated \(exit code = (-?\d+)\)\s*$", re.MULTILINE)


def interpret_c(ccomp: list[str], source: Path, fresh: Path,
                timeout: int = COMPILE_TIMEOUT, *, expected_sha256: str = "",
                observations: list[dict[str, object]] | None = None) -> Interpreted:
    """Run the same compiler's `-interp` over one source in `fresh`.

    The reading is the exit code the interpreter reports for `main`, and only where it
    reports exactly one termination; a stuck state, an undefined behaviour the
    interpreter detects, a timeout or a second termination line leave it `None`.
    """
    fresh = fresh.resolve()
    prepared = preprocess_c(ccomp, source, fresh, timeout, observations=observations)
    argv = [*ccomp, "-interp", prepared.path.name]
    if not prepared.sha256 or (expected_sha256 and prepared.sha256 != expected_sha256):
        return Interpreted(tuple(argv), -1, None,
                           prepared.said if not prepared.sha256 else "preprocessed input changed")
    try:
        done = subprocess.run(argv, cwd=fresh, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return Interpreted(tuple(argv), -1, None, f"no exit within {timeout}s")
    except OSError as err:
        return Interpreted(tuple(argv), -1, None, f"could not run: {err}")
    _observe_process(argv, done, fresh / f"{source.stem}.interpret.log", observations, fresh)
    said = done.stdout + done.stderr
    if (not prepared.path.is_file()
            or _sha256(prepared.path.read_bytes()) != prepared.sha256):
        return Interpreted(tuple(argv), -1, None, "preprocessed input changed during interpretation")
    ended = _TERMINATED_RE.findall(done.stdout)
    code = int(ended[0]) if done.returncode == 0 and len(ended) == 1 else None
    return Interpreted(tuple(argv), done.returncode, code, said.strip()[-600:])


@dataclass(frozen=True)
class Report:
    """One program through the loop, as far as it got."""

    name: str
    pattern: str
    source_sha256: str
    checks: int
    compiled: Compiled | None
    refusals: tuple[Refusal, ...]
    image_bytes: int
    ran: Ran | None
    verdict: str
    detail: str
    expect: int = 0
    interpreted: Interpreted | None = None


def target_code(ran: Ran | None) -> int | None:
    """What the image says `main` returned: 0 on success, the code below `TRAP_BASE`
    on a failed check, and nothing for a trap or a run with no verdict."""
    if ran is None:
        return None
    if ran.verdict == "pass":
        return 0
    if ran.verdict == "fail" and ran.code is not None and ran.code < TRAP_BASE:
        return ran.code
    return None


def as_expected(report: Report) -> bool:
    """Whether the program ended where its source says it ends: every check held for an
    ordinary program, and the one moved check failed for a perturbed twin."""
    if report.expect == 0:
        return report.verdict == "pass"
    return report.verdict == "fail" and target_code(report.ran) == report.expect


def run_program(program: Program, ccomp: list[str], workdir: Path,
                simulator: list[str] | None, profile: Path, waits: str, *,
                compile_timeout: int = COMPILE_TIMEOUT, run_timeout: int = RUN_TIMEOUT,
                inst_limit: int = INST_LIMIT, interp: bool = False,
                observations: list[dict[str, object]] | None = None) -> Report:
    """Compile, scan, assemble, and run one program, stopping at the first thing that
    does not go through and saying which it was.

    With `interp`, the same compiler's reference interpreter also runs the source, and
    an image whose `main` returned something other than what the interpreter reports is
    `source-disagrees` rather than a pass or a failure.
    """
    source = workdir / f"{program.name}.c"
    source.write_text(program.source, encoding="utf-8", newline="\n")
    compiled = compile_c(ccomp, source, workdir / program.name, compile_timeout,
                         observations=observations)
    digest = compiled.preprocessed.source_sha256
    interpreted = (interpret_c(ccomp, compiled.preprocessed.path,
                               workdir / f"{program.name}.interp", compile_timeout,
                               expected_sha256=compiled.preprocessed.sha256, observations=observations)
                   if interp and compiled.stream is not None else None)

    def report(compiled: Compiled | None, found: tuple[Refusal, ...], size: int,
               ran: Ran | None, verdict: str, detail: str) -> Report:
        return Report(program.name, program.pattern, digest, program.checks, compiled,
                      found, size, ran, verdict, detail, program.expect, interpreted)

    if compiled.stream is None:
        return report(compiled, (), 0, None, "ccomp-refused",
                      f"ccomp exited {compiled.exit_code}: {compiled.said}")
    elf = workdir / f"{program.name}.elf"
    found, size = assemble(compiled.stream, program.name, elf)
    if found:
        mnemonics = sum(1 for r in found if r.kind == "mnemonic")
        return report(compiled, tuple(found), 0, None, "dialect-refused",
                      f"{len(found)} refusal(s) the dialect does not assemble, "
                      f"{mnemonics} of them mnemonics")
    if simulator is None:
        return report(compiled, (), size, None, "assembled",
                      f"{size} bytes of image; {waits}")
    ran = run_image(simulator, profile, elf, workdir, run_timeout, inst_limit,
                    observations=observations)
    target = target_code(ran)
    if interpreted is not None and target is not None and interpreted.code != target:
        return report(compiled, (), size, ran, "source-disagrees",
                      f"the image's main returned {target}; the interpreter reports "
                      f"{interpreted.code}")
    return report(compiled, (), size, ran, ran.verdict, ran.detail)
