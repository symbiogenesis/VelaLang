# SPDX-License-Identifier: Apache-2.0
"""Exact-subject and failure controls for first-slice development receipts."""

import copy
import hashlib
import json
import subprocess
import tempfile
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import TOOLS, Case, ensure
from toolchain import first_slice as slice_harness
from toolchain.cli import vela_parser as cli

INDEPENDENT_CASES = True


def _execution_fixture(outputs: Path, *, available: bool = False) -> dict[str, object]:
    """Assemble retained controls with independently specified process and trace facts."""
    files: dict[str, object] = {
        "simulator": {"path": str(outputs.parent / "simulator"), "sha256": "1" * 64},
        "profile": {"path": str(outputs.parent / "profile.json"), "sha256": "2" * 64},
    }
    runs: dict[str, object] = {}
    trace_lines = ["I 1 0000000080000000 00000013", "W 80008000 8 1 0000000000000042",
                   "R 80008000 8 1 0000000000000042"]
    normalized = ["I 0000000080000000 00000013", *trace_lines[1:]]
    digest = hashlib.sha256("\n".join(normalized).encode()).hexdigest()[:16]
    for mode in ("pass", "bounds-trap", "tag-trap", "perm-trap"):
        elf = outputs / f"purecap_{mode}.elf"
        refused, size = slice_harness.cd.assemble(slice_harness._purecap_cheri_asm_stream(mode), elf.stem, elf)
        ensure(not refused, "independent receipt fixture image did not assemble")
        stdout = ("\n".join(trace_lines) + ("\nSUCCESS\n" if mode == "pass" else "\nFAILURE: 284\n")).encode()
        stderr = "diagnostic λ\n".encode()
        log = outputs / f"purecap_{mode}.sail.log"
        log.write_bytes(stdout + stderr)
        process: dict[str, object] = {
            "command": [str(outputs.parent / "simulator"), "--config", str(outputs.parent / "profile.json"),
                        "--trace-commit", "--inst-limit", "1000000", "--terminal-log",
                        str(outputs / f"purecap_{mode}.term"), str(elf)],
            "returncode": 0 if mode == "pass" else 1,
            "log": str(log), "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "stdout_bytes": len(stdout), "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_bytes": len(stderr), "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        }
        runs[mode] = {"verdict": "pass" if mode == "pass" else "trap", "code": 0 if mode == "pass" else 284,
                      "records": 3, "trace_digest": digest, "cap_roundtrip": True,
                      "image_bytes": size, "process": process}
    compiler: dict[str, object] = {"available": available}
    if available:
        ccomp = {"path": str(outputs.parent / "ccomp"), "sha256": "3" * 64}
        files["ccomp"] = ccomp
        clight, assembly = outputs / "first_slice/first_slice.light.c", outputs / "first_slice/first_slice.s"
        clight.parent.mkdir(exist_ok=True)
        clight.write_bytes(b"retained Clight\n")
        assembly.write_bytes(b".text\n.globl main\nmain:\nli a0, 0\nret\n")
        compiler.update({
            "ccomp_path": ccomp["path"], "ccomp_sha256": ccomp["sha256"],
            "clight_path": str(clight), "clight_sha256": hashlib.sha256(clight.read_bytes()).hexdigest(),
            "asm_sha256": hashlib.sha256(assembly.read_bytes()).hexdigest(), "asm_lines": 5,
            "interp_exit_code": 0, "sail_verdict": "pass", "sail_records": 3,
            "sail_trace_digest": digest, "sail_cap_roundtrip": True,
            "perturbed_controls": [
                {"name": label, "check_id": check, "verdict": "fail", "target_code": check, "interp_code": check}
                for check, label in ((7, "perturbed-wrong-payload-byte"), (12, "perturbed-stale-trailing-byte"),
                                     (16, "perturbed-checksum-error-code"), (17, "perturbed-unscrubbed-checksum-dst"))],
        })
        compiler["programs"] = _compiler_fixture(outputs, files, trace_lines)
    return {"execution_inputs": {"files": files, "compcert_available": available},
            "purecap_cheri_runs": runs, "compcert_sail": compiler}


def _compiler_fixture(directory: Path, files: dict[str, object], trace_lines: list[str]) -> list[dict[str, object]]:
    programs: list[dict[str, object]] = []
    compiler, simulator, profile = (cast("dict[str, str]", files[key])["path"]
                                   for key in ("ccomp", "simulator", "profile"))
    command = [compiler, "-fverifiedos-typed", "-dclight"]
    for name, code in (("first_slice", 0), ("perturbed-wrong-payload-byte", 7),
                       ("perturbed-stale-trailing-byte", 12), ("perturbed-checksum-error-code", 16),
                       ("perturbed-unscrubbed-checksum-dst", 17)):
        fresh, interpreted = directory / name, directory / f"{name}.interp"
        fresh.mkdir(exist_ok=True)
        interpreted.mkdir(exist_ok=True)
        source, unit, interp_unit = directory / f"{name}.c", fresh / f"{name}.i", interpreted / f"{name}.i"
        for path in (source, unit, interp_unit):
            path.write_bytes(f"int main(void) {{ return {code}; }}\n".encode())
        assembly, elf = fresh / f"{name}.s", directory / f"{name}.elf"
        assembly.write_bytes(f".text\n.globl main\nmain:\nli a0, {code}\nret\n".encode())
        refused, image_bytes = slice_harness.cd.assemble(assembly.read_text(encoding="utf-8"), name, elf)
        ensure(not refused, "independent compiler receipt image did not assemble")
        stages = (
            (fresh / f"{name}.preprocess.log", [*command, "-E", source.name, "-o", str(unit)], directory, ""),
            (fresh / f"{name}.compile.log", [*command, "-S", unit.name, "-o", assembly.name], fresh, ""),
            (interpreted / f"{name}.preprocess.log", [*command, "-E", unit.name, "-o", str(interp_unit)], fresh, ""),
            (interpreted / f"{name}.interpret.log", [*command, "-interp", interp_unit.name], interpreted,
             f"Time 42: program terminated (exit code = {code})\n"),
            (directory / f"{name}.sail.log",
             [simulator, "--config", profile, "--trace-commit", "--inst-limit", "1000000",
              "--terminal-log", str(directory / f"{name}.term"), str(elf)], None,
             "\n".join(trace_lines) + ("\nSUCCESS\n" if code == 0 else f"\nFAILURE: {code}\n")),
        )
        processes: list[dict[str, object]] = []
        for log, argv, working, stdout in stages:
            stderr = "diagnostic \u03bb\n"
            raw = (stdout + stderr).encode()
            log.write_bytes(raw)
            process: dict[str, object] = {
                "command": argv, "returncode": 1 if code != 0 and working is None else 0,
                "log": str(log), "log_sha256": hashlib.sha256(raw).hexdigest(),
                "stdout_bytes": len(stdout.encode()), "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                "stderr_bytes": len(stderr.encode()), "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            }
            if working is not None:
                process["cwd"] = str(working)
            processes.append(process)
        programs.append({"name": name, "expect": code, "image_bytes": image_bytes, "processes": processes,
                         "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                         "preprocessed_sha256": hashlib.sha256(unit.read_bytes()).hexdigest()})
    return programs


def _proof_fixture(root: Path, outputs: Path, *, trusted: bool = False,
                   assumption_stderr: bytes = b"") -> dict[str, object]:
    """Retain an independently assembled local proof report for binding-only checks."""
    labels = (
        "LawInhabitedByteCase", "LawAllocZeroedRead", "LawReadOverWriteSame", "LawReadOverWriteOther",
        "LawLoopFramePreservesDisjointSuffix", "LawFillAndFrame", "LawSliceMetadataAndRead",
        "LawReadOnlyAndInvalidate", "LawDisjointCopyAndFrame", "LawCapacityInvarianceSmall",
        "LawCapacityInvarianceLarge", "PrepareAndValidatePacket_restores_0_Base",
        "PrepareAndValidatePacket_restores_0_Length", "PrepareAndValidatePacket_restores_0_Tag",
        "PrepareAndValidatePacket_restores_0_PermRead", "PrepareAndValidatePacket_restores_0_PermWrite",
        "PrepareAndValidatePacket_ensures_0", "PrepareAndValidatePacket_ensures_1",
        "PrepareAndValidatePacket_ensures_2", "ValidateEmptyPacketOk", "ValidateFullPacketOk",
        "ValidatePartialPacketScrubsStaleAndTrailingBytes", "RejectFramingShort", "RejectBadMagic",
        "RejectLengthOutOfBounds", "RejectChecksumScrubsDestinationAndRestores",
    )
    names = [f"vela_d{index}_{label}" for index, label in enumerate(labels)]
    module = "Vela_Vela_FirstSlice"
    axiom = f"vela_solver_{names[16]}"
    prefix = (f"(* vela-solver-trust: {names[16]} at 12:7; retained test residual *)\n"
              f"Axiom {axiom} : True.\n" if trusted else "")
    gallina = f"Module {module}.\n" + prefix + "".join(
        f"Definition {name} : True := {axiom if trusted and index == 16 else 'I'}.\n"
        for index, name in enumerate(names)) + f"End {module}.\n"
    (outputs / "FirstSlice.v").write_text(gallina, encoding="utf-8")
    corruption = (
        "\nDefinition vela_corrupted_check : @Corelib.Init.Logic.eq Corelib.Init.Datatypes.bool "
        "Corelib.Init.Datatypes.true Corelib.Init.Datatypes.false := "
        "@Corelib.Init.Logic.eq_refl Corelib.Init.Datatypes.bool Corelib.Init.Datatypes.true.\n")
    (outputs / "FirstSliceCorrupted.v").write_bytes((gallina + corruption).encode())
    (outputs / "FirstSliceCorrupted.compile.log").write_bytes((
        f'File "./FirstSliceCorrupted.v", line {gallina.count(chr(10)) + 2}, characters 144-230:\n'
        'Error: The term "eq_refl true" has type "true = true"\n'
        'while it is expected to have type "true = false".\n').encode())
    (outputs / "FirstSliceAssumptions.v").write_text(
        "From VelaFirstSlice Require Import FirstSlice.\n" + "".join(
            f"Print Assumptions FirstSlice.{module}.{name}.\n" for name in names), encoding="utf-8")
    assumption_stdout = "".join(
        f"Axioms:\n{module}.{axiom} : True\n" if trusted and index == 16
        else "Closed under the global context\n" for index in range(len(names))).encode("utf-8")
    (outputs / "FirstSlice.assumptions.log").write_bytes(assumption_stdout + assumption_stderr)
    for name in ("FirstSlice.vo", "FirstSliceAssumptions.vo", "first_slice.c"):
        (outputs / name).write_bytes(f"retained {name}".encode())
    capacity_gallina = b"Definition capacity_fixture : True := I.\n"
    for stem in ("CapSmall", "CapLarge"):
        literal = "8usize" if stem == "CapSmall" else "1_000_000_000usize"
        (outputs / f"{stem}.vela").write_bytes(slice_harness._capacity_fixture(literal))
        (outputs / f"{stem}.v").write_bytes(capacity_gallina)
        (outputs / f"{stem}.vo").write_bytes(b"retained capacity proof")
    controls = outputs / "negative-controls"
    controls.mkdir(exist_ok=True)
    for control in slice_harness.NEGATIVE_CONTROLS:
        (controls / f"{control.name}.vela").write_bytes(control.source.encode())
    source = root / slice_harness.EXAMPLE
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"module Vela.FirstSlice;")
    commands = {
        "FirstSlice.compile.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "FirstSlice.v"],
        "FirstSlice.assumptions.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "FirstSliceAssumptions.v"],
        "FirstSlice.kernel.log": ["rocqchk", "-R", str(outputs), "VelaFirstSlice", "VelaFirstSlice.FirstSlice"],
        "CapSmall.compile.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "CapSmall.v"],
        "CapLarge.compile.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "CapLarge.v"],
        "CapGate.kernel.log": ["rocqchk", "-R", str(outputs), "VelaFirstSlice",
                               "VelaFirstSlice.CapSmall", "VelaFirstSlice.CapLarge"],
        "FirstSliceCorrupted.compile.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "FirstSliceCorrupted.v"],
    }
    steps: list[dict[str, object]] = []
    for name, command in commands.items():
        log = outputs / name
        if not log.is_file():
            log.write_bytes(b"independent retained transcript")
        refused = name == "FirstSliceCorrupted.compile.log"
        stdout = assumption_stdout if name == "FirstSlice.assumptions.log" else log.read_bytes()
        stderr = assumption_stderr if name == "FirstSlice.assumptions.log" else b""
        row: dict[str, object] = {
            "command": ["opam", "exec", "--switch", slice_harness.proofenv.ROCQ_SWITCH, "--", *command],
            "cwd": str(outputs), "returncode": 1 if refused else 0,
            "log": str(log), "log_sha256": slice_harness._sha256(log.read_bytes()),
            "stdout_bytes": len(stdout), "stdout_sha256": slice_harness._sha256(stdout),
            "stderr_bytes": len(stderr), "stderr_sha256": slice_harness._sha256(stderr),
        }
        if refused:
            row["expected_refusal"] = True
        steps.append(row)
    report: dict[str, object] = {
        "steps": steps, "accepted": not trusted, "kernel_checked": not trusted,
        "capacity_invariance": {"small_capacity": "8usize", "large_capacity": "1_000_000_000usize",
                                "obligation_count": 9, "work_steps": 14, "reduction_steps": 0,
                                "gallina_bytes": len(capacity_gallina), "kernel_checked": True},
        "negative_controls_count": len(slice_harness.NEGATIVE_CONTROLS),
        "negative_controls": [
            {"name": control.name, "parsed_surface": True, "category": control.expected_kind,
             "line": 2, "column": 1, "message": control.expected_substring}
            for control in slice_harness.NEGATIVE_CONTROLS],
        "proof_corruption_refused": True, "assumption_exports_count": len(names),
        "solver_trusted_count": int(trusted),
        "solver_trusted_axioms": [f"{module}.{axiom}"] if trusted else [],
        "inventory": {"solver_trusted_obligations": [
            {"export": names[16], "axiom": axiom, "line": 12, "column": 7,
             "reason": "retained test residual"}] if trusted else [],
            "global_assumptions": "1 solver-trusted axioms; no other assumptions" if trusted
            else "Closed under the global context (0 axioms)"},
    }
    for field, path in (("source", source), ("gallina", outputs / "FirstSlice.v"),
                         ("lowered_c", outputs / "first_slice.c")):
        report[field] = str(path)
        report[f"{field}_sha256"] = slice_harness._sha256(path.read_bytes())
    return report


def _source_inventory() -> None:
    inputs = slice_harness._inputs(TOOLS.parent)
    expected = {slice_harness.EXAMPLE, "tools/generated/dialect-table.json",
                "tools/toolchain/elaborate.py", "tools/toolchain/solver_ledger.py",
                "tools/toolchain/first_slice.py", "tools/toolchain/jsonutil.py",
                "tools/toolchain/source.py", "tools/opam/rocq.lock", "tools/uv.lock"}
    ensure(expected <= inputs.keys(), "receipt omitted a source, data or dependency input")
    with tempfile.TemporaryDirectory(prefix="vela-slice-inputs-") as temporary:
        root = Path(temporary)
        for name in inputs:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        before = slice_harness._inputs(root)
        (root / "tools/toolchain/solver_ledger.py").write_bytes(b"changed audit")
        after = slice_harness._inputs(root)
        ensure(before != after, "changed assumption audit preserved receipt identity")
        (root / "tools/toolchain/new_semantics.py").write_bytes(b"new semantic dependency")
        ensure("tools/toolchain/new_semantics.py" in slice_harness._inputs(root),
               "new producer module escaped the input inventory")
        (root / slice_harness.EXAMPLE).unlink()
        try:
            slice_harness._inputs(root)
        except OSError:
            pass
        else:
            raise AssertionError("missing source produced a complete inventory")


def _publication_freshness() -> None:
    for mutation in ("none", "source", "revision", "execution", "prover", "runtime", "parser", "failure",
                     "source_output", "gallina_output", "lowered_c_output", "object_output",
                     "deleted_object", "metadata", "new_probe_log"):
        with tempfile.TemporaryDirectory(prefix="vela-slice-publication-") as temporary, ExitStack() as stack:
            root = Path(temporary)
            latest = root / "qualification.json"
            latest.write_text('{"status":"passed","stale":true}', encoding="utf-8")
            parser_receipt: dict[str, object] = {"toolchain": {"menhir": "locked"}}
            compiled = slice_harness.vela_parser.Build(root, root / "parser", parser_receipt)
            produced: dict[str, Path] = {}
            stack.enter_context(patch.object(slice_harness, "_work_root", return_value=root))
            for name, original in (("_inputs", {"source": "old"}), ("_revision", "a" * 40),
                                   ("_execution_inputs", {"simulator": "old"})):
                changed = {"source": "new"} if name == "_inputs" else (
                    "b" * 40 if name == "_revision" else {"simulator": "new"})
                subject = {"_inputs": "source", "_revision": "revision", "_execution_inputs": "execution"}[name]
                stack.enter_context(patch.object(slice_harness, name,
                                                  side_effect=[original, changed if mutation == subject else original]))
            def probe(_root: Path, directory: Path, _steps: list[dict[str, object]], *,
                      case: str = mutation, paths: dict[str, Path] = produced) -> dict[str, object]:
                if paths:
                    if case.endswith("_output"):
                        paths[case.removesuffix("_output")].write_bytes(b"changed after producer")
                    elif case == "deleted_object":
                        paths["object"].unlink()
                    elif case == "new_probe_log":
                        (directory / "late-probe.log").write_bytes(b"independent final probe")
                return {"changed": True} if case == "prover" and paths else {}

            stack.enter_context(patch.object(slice_harness.replay, "_toolchain", side_effect=probe))
            stack.enter_context(patch.object(slice_harness.replay, "_runtime",
                                              side_effect=[{}, {"changed": True} if mutation == "runtime" else {}]))
            stack.enter_context(patch.object(slice_harness.vela_parser, "build", return_value=compiled))
            stack.enter_context(patch.object(slice_harness.vela_parser, "_toolchain", return_value={"menhir": "locked"}))
            stack.enter_context(patch.object(slice_harness.replay, "_parser_outputs", return_value={"parser": "old"}))

            def run(_root: Path, directory: Path, _steps: list[dict[str, object]],
                    _compiler: Path | None, _compiled: object, *, case: str = mutation,
                    receipt: dict[str, object] = parser_receipt,
                    paths: dict[str, Path] = produced) -> dict[str, object]:
                paths.update(source=directory / "source.vela", gallina=directory / "FirstSlice.v",
                             lowered_c=directory / "first_slice.c", object=directory / "FirstSlice.vo")
                for name, path in paths.items():
                    path.write_bytes(f"checked {name}".encode())
                if case == "parser":
                    receipt["toolchain"] = {"menhir": "changed"}
                if case == "failure":
                    raise ValueError("native producer refused")
                report: dict[str, object] = {"status": "passed", "kernel_checked": True, "accepted": True}
                for field in ("source", "gallina", "lowered_c"):
                    report[field] = str(paths[field])
                    report[f"{field}_sha256"] = slice_harness._sha256(paths[field].read_bytes())
                if case == "metadata":
                    report["gallina_sha256"] = "0" * 64
                return report

            stack.enter_context(patch.object(slice_harness, "_qualify_attempt", side_effect=run))
            try:
                report = slice_harness.qualify(root)
            except ValueError as error:
                ensure(mutation not in {"none", "new_probe_log"}, f"unchanged producer failed: {error}")
                ensure(not latest.exists(), "failed attempt preserved a stale passing receipt")
                journals = list(root.glob("slice-*/attempt.json"))
                ensure(len(journals) == 1, "failed producer lost its attempt journal")
                row = json.loads(journals[0].read_text(encoding="utf-8"))
                ensure(row["status"] == "failed" and not row["kernel_checked"] and not row["accepted"],
                       "failed producer retained source-proof acceptance")
            else:
                ensure(mutation in {"none", "new_probe_log"}, f"{mutation} changed without withdrawing acceptance")
                ensure(report["schema"] == 2 and report["status"] == "passed" and latest.is_file(),
                       "unchanged local producer did not publish")
                ensure(not report["artifact_accepted"] and not report["source_correspondence"]
                       and not report["production_admission"] and not report["full_machine_refinement_closed"],
                       "local proof producer claimed complete release evidence")
                ensure(bool(report["artifacts_sha256"]), "passing receipt omitted retained outputs")
                if mutation == "new_probe_log":
                    ensure(str(produced["source"].parent / "late-probe.log") in
                           cast("dict[str, str]", report["artifacts_sha256"]),
                           "final probe log was omitted from the retained inventory")


def _binding_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-bindings-") as temporary, ExitStack() as stack:
        root = Path(temporary)
        outputs = root / "slice-fixture"
        outputs.mkdir()
        artifact = outputs / "FirstSlice.vo"
        artifact.write_bytes(b"checked library")
        parser = root / "build-fixture"
        parser.mkdir()
        for name in (*slice_harness.vela_parser.GENERATED, "vela-parser"):
            (parser / name).write_bytes(name.encode())
        parser_hashes = {name: slice_harness._sha256((parser / name).read_bytes())
                         for name in (*slice_harness.vela_parser.GENERATED, "vela-parser")}
        source_inputs = {"source": "old"}
        execution_fixture = _execution_fixture(outputs)
        execution = execution_fixture["execution_inputs"]
        report: dict[str, object] = {
            "schema": 2, "scope": "vela-first-slice-qualification", "status": "passed",
            "artifact_accepted": False, "source_correspondence": False,
            "production_admission": False, "full_machine_refinement_closed": False,
            "inputs": source_inputs, "producer_revision": "a" * 40,
            **execution_fixture, "toolchain": {}, "runtime": {},
            "parser": {"directory": str(parser), "generated_sha256": parser_hashes,
                       "inputs": {}, "toolchain": {}},
            "parser_outputs": parser_hashes, "directory": str(outputs),
            **_proof_fixture(root, outputs),
            "artifacts_sha256": slice_harness._artifacts(outputs),
        }
        receipt = root / "receipt.json"
        stack.enter_context(patch.object(slice_harness, "_inputs", return_value=source_inputs))
        stack.enter_context(patch.object(slice_harness, "_revision", return_value="a" * 40))
        stack.enter_context(patch.object(slice_harness, "_execution_inputs", return_value=execution))
        stack.enter_context(patch.object(slice_harness, "_work_root", return_value=root))
        stack.enter_context(patch.object(slice_harness.vela_parser, "_inputs", return_value={}))
        stack.enter_context(patch.object(slice_harness.vela_parser, "_toolchain", return_value={}))
        stack.enter_context(patch.object(slice_harness.vela_parser, "_work_root", return_value=root))
        stack.enter_context(patch.object(slice_harness.replay, "_toolchain", return_value={}))
        stack.enter_context(patch.object(slice_harness.replay, "_runtime", return_value={}))

        def write(value: object) -> None:
            receipt.write_text(json.dumps(value), encoding="utf-8")

        write(report)
        result = slice_harness.verify_bindings(root, receipt)
        ensure(result["status"] == "matched" and not result["proof_replayed"]
               and not result["artifact_accepted"] and not result["production_admission"],
               "binding check claimed fresh proof or admission authority")
        for owner, field, original, changed in (
                (slice_harness, "_inputs", source_inputs, {"source": "changed during probes"}),
                (slice_harness, "_revision", "a" * 40, "b" * 40),
                (slice_harness, "_execution_inputs", execution, {"files": {}, "changed": True}),
                (slice_harness.vela_parser, "_inputs", {}, {"source": "changed parser"}),
                (slice_harness.vela_parser, "_toolchain", {}, {"menhir": "changed generator"})):
            with patch.object(owner, field, side_effect=[original, changed]):
                try:
                    slice_harness.verify_bindings(root, receipt)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"{field} changed during binding checks without refusal")
        for mutation in ("artifact", "parser", "receipt"):
            target = {"artifact": artifact, "parser": parser / "vela-parser", "receipt": receipt}[mutation]
            before = target.read_bytes()

            def change_during_probe(_directory: Path, _steps: list[dict[str, object]], *,
                                    path: Path = target) -> dict[str, object]:
                path.write_bytes(b"changed during final runtime probe")
                return {}

            with patch.object(slice_harness.replay, "_runtime", side_effect=change_during_probe):
                try:
                    slice_harness.verify_bindings(root, receipt)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"{mutation} changed during final probes without refusal")
                finally:
                    target.write_bytes(before)
        for field, changed in (("schema", True), ("status", "skipped"), ("status", "failed"),
                               ("producer_revision", "b" * 40), ("inputs", {}),
                               ("artifact_accepted", True), ("source_correspondence", True),
                               ("execution_inputs", None), ("parser", {}),
                               ("artifacts_sha256", {}), ("directory", str(root)),
                               ("runtime", {"changed": True}),
                               ("source", str(outputs / "FirstSlice.v")),
                               ("source_sha256", "0" * 64), ("gallina", str(artifact)),
                               ("lowered_c_sha256", "0" * 64), ("steps", []),
                               ("steps", [None]), ("accepted", False), ("kernel_checked", False),
                               ("solver_trusted_count", True), ("solver_trusted_axioms", ["invented"]),
                               ("assumption_exports_count", 0), ("inventory", {}),
                               ("capacity_invariance", {}), ("negative_controls", []),
                               ("negative_controls_count", 0),
                               ("purecap_cheri_runs", {}), ("compcert_sail", {"available": True}),
                               ("proof_corruption_refused", False)):
            damaged = copy.deepcopy(report)
            damaged[field] = changed
            write(damaged)
            try:
                slice_harness.verify_bindings(root, receipt)
            except (ValueError, TypeError, OSError):
                pass
            else:
                raise AssertionError(f"changed {field} was accepted")
        for field, changed in (("command", ["rocqchk", "another.subject"]),
                               ("cwd", str(root)), ("returncode", True), ("returncode", 0),
                               ("expected_refusal", False), ("log_sha256", "0" * 64),
                               ("log", str(root / "outside.log"))):
            damaged = copy.deepcopy(report)
            steps = cast("list[dict[str, object]]", damaged["steps"])
            steps[-1][field] = changed
            write(damaged)
            try:
                slice_harness.verify_bindings(root, receipt)
            except (ValueError, TypeError, OSError):
                pass
            else:
                raise AssertionError(f"changed process {field} was accepted")
        write(report)
        for path in (artifact, parser / "vela-parser"):
            before = path.read_bytes()
            for payload in (b"replacement bytes", None):
                if payload is None:
                    path.unlink()
                else:
                    path.write_bytes(payload)
                try:
                    slice_harness.verify_bindings(root, receipt)
                except (ValueError, OSError):
                    pass
                else:
                    raise AssertionError("changed or missing producer output was accepted")
                path.write_bytes(before)
        for raw in (b'{"schema":2,"schema":2}', b"[" * 2_000 + b"]" * 2_000, b"{}\xff"):
            receipt.write_bytes(raw)
            try:
                slice_harness.verify_bindings(root, receipt)
            except ValueError:
                pass
            else:
                raise AssertionError("malformed receipt was accepted")
        with patch.object(slice_harness, "RECEIPT_BYTES", 4):
            receipt.write_bytes(b" " * 5)
            try:
                slice_harness.verify_bindings(root, receipt)
            except ValueError as error:
                ensure("size bound" in str(error), "oversized receipt lost its bounded refusal")
            else:
                raise AssertionError("oversized receipt was accepted")
        trusted_report = {**report, **_proof_fixture(root, outputs, trusted=True),
                          "artifacts_sha256": slice_harness._artifacts(outputs)}
        write(trusted_report)
        ensure(slice_harness.verify_bindings(root, receipt)["status"] == "matched",
               "binding-only check refused honestly reported source residuals")
        for field, changed in (("accepted", True), ("kernel_checked", True),
                               ("solver_trusted_count", 0), ("solver_trusted_axioms", [])):
            damaged = copy.deepcopy(trusted_report)
            damaged[field] = changed
            write(damaged)
            try:
                slice_harness.verify_bindings(root, receipt)
            except ValueError:
                pass
            else:
                raise AssertionError(f"solver-trusted report promoted by changing {field}")


def _retained_coverage() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-proof-coverage-") as temporary:
        root = Path(temporary)
        outputs = root / "slice-fixture"
        outputs.mkdir()
        for mutation in ("missing-export", "audit-query", "audit-log", "missing-library", "unledgered-axiom"):
            report = _proof_fixture(root, outputs)
            if mutation == "missing-export":
                path = outputs / "FirstSlice.v"
                path.write_text(path.read_text(encoding="utf-8").replace("RejectBadMagic", "SkippedError"),
                                encoding="utf-8")
                report["gallina_sha256"] = slice_harness._sha256(path.read_bytes())
            elif mutation == "audit-query":
                (outputs / "FirstSliceAssumptions.v").write_bytes(b"Print Assumptions I.\n")
            elif mutation == "audit-log":
                (outputs / "FirstSlice.assumptions.log").write_bytes(b"Closed under the global context\n")
            elif mutation == "missing-library":
                (outputs / "FirstSlice.vo").unlink()
            else:
                path = outputs / "FirstSlice.v"
                path.write_text(path.read_text(encoding="utf-8") + "Axiom hidden : False.\n", encoding="utf-8")
                report["gallina_sha256"] = slice_harness._sha256(path.read_bytes())
            artifacts: dict[str, object] = dict(slice_harness._artifacts(outputs))
            try:
                slice_harness._retained_proof(root, report, outputs, artifacts)
            except ValueError:
                pass
            else:
                raise AssertionError(f"rehashed {mutation} concealed incomplete local proof coverage")


def _process_streams() -> None:
    warning = b"[WARNING] Running as root is not recommended\n"
    with tempfile.TemporaryDirectory(prefix="vela-slice-streams-") as temporary:
        root = Path(temporary)
        outputs = root / "slice-fixture"
        outputs.mkdir()
        for trusted in (False, True):
            report = _proof_fixture(root, outputs, trusted=trusted, assumption_stderr=warning)
            artifacts: dict[str, object] = dict(slice_harness._artifacts(outputs))
            slice_harness._retained_proof(root, report, outputs, artifacts)
            ensure((outputs / "FirstSlice.assumptions.log").read_bytes().endswith(warning),
                   "stderr warning was discarded from the retained transcript")
        report = _proof_fixture(root, outputs, assumption_stderr=warning)
        artifacts = dict(slice_harness._artifacts(outputs))
        for field, changed in (("stdout_bytes", True), ("stdout_bytes", -1), ("stdout_bytes", 0),
                               ("stdout_bytes", 100_000), ("stdout_sha256", "0" * 64),
                               ("stderr_bytes", True), ("stderr_bytes", -1), ("stderr_bytes", 0),
                               ("stderr_sha256", "0" * 64)):
            damaged = copy.deepcopy(report)
            rows = cast("list[dict[str, object]]", damaged["steps"])
            rows[1][field] = changed
            try:
                slice_harness._retained_proof(root, damaged, outputs, artifacts)
            except ValueError:
                pass
            else:
                raise AssertionError(f"tampered assumption stream {field} was accepted")
        for mutation in ("missing-stream-identity", "duplicate-observation", "warning-on-stdout"):
            damaged = copy.deepcopy(report)
            rows = cast("list[dict[str, object]]", damaged["steps"])
            if mutation == "missing-stream-identity":
                del rows[1]["stdout_sha256"]
            elif mutation == "duplicate-observation":
                rows.append(copy.deepcopy(rows[1]))
            else:
                raw = (outputs / "FirstSlice.assumptions.log").read_bytes()
                rows[1].update(stdout_bytes=len(raw), stdout_sha256=slice_harness._sha256(raw),
                               stderr_bytes=0, stderr_sha256=slice_harness._sha256(b""))
            try:
                slice_harness._retained_proof(root, damaged, outputs, artifacts)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{mutation} concealed malformed stdout or provenance")
        stdout, stderr = "Closed under the global context\n", "diagnostic λ\n"
        command = ["independent-command"]
        completed = subprocess.CompletedProcess(command, 0, stdout, stderr)
        steps: list[dict[str, object]] = []
        log = outputs / "run.log"
        with patch.object(slice_harness.subprocess, "run", return_value=completed):
            result = slice_harness._run(command, outputs, log, steps)
        ensure(result == stdout and log.read_bytes() == (stdout + stderr).encode("utf-8"),
               "producer merged diagnostics into stdout or discarded retained bytes")
        ensure(steps[0]["stdout_bytes"] == len(stdout.encode("utf-8"))
               and steps[0]["stderr_bytes"] == len(stderr.encode("utf-8"))
               and steps[0]["stdout_sha256"] == slice_harness._sha256(stdout.encode("utf-8"))
               and steps[0]["stderr_sha256"] == slice_harness._sha256(stderr.encode("utf-8")),
               "producer stream identity uses character positions or another byte subject")
        probe_log = outputs / "runtime-config.log"
        probe_log.write_bytes(b"bound replay probe")
        probe: dict[str, object] = {
            "command": ["opam", "exec", "--switch", "fixture", "--", "rocq", "c", "-config"],
            "directory": str(outputs), "exit": 0, "status": "passed", "seconds": 0.001,
            "log": str(probe_log), "log_sha256": slice_harness._sha256(probe_log.read_bytes()),
        }
        report = _proof_fixture(root, outputs, assumption_stderr=warning)
        rows = cast("list[dict[str, object]]", report["steps"])
        rows.append(probe)
        artifacts = dict(slice_harness._artifacts(outputs))
        slice_harness._retained_proof(root, report, outputs, artifacts)
        for field, changed in (("directory", str(root)), ("exit", True), ("exit", 1),
                               ("status", "skipped"), ("status", "failed"),
                               ("cwd", str(outputs)), ("returncode", 0)):
            damaged = copy.deepcopy(report)
            cast("list[dict[str, object]]", damaged["steps"])[-1][field] = changed
            try:
                slice_harness._retained_proof(root, damaged, outputs, artifacts)
            except ValueError:
                pass
            else:
                raise AssertionError(f"malformed replay-probe {field} was accepted")


def _corruption_control_subjects() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-corruption-subjects-") as temporary:
        root = Path(temporary)
        outputs = root / "slice-fixture"
        outputs.mkdir()
        for mutation in ("none", "missing-source", "unrelated-source", "uncorrupted-source", "signal",
                         "accepted", "empty-diagnostic", "unrelated-file", "unrelated-line",
                         "syntax-error", "duplicate-error", "extra-unrelated-error"):
            report = _proof_fixture(root, outputs)
            steps = cast("list[dict[str, object]]", report["steps"])
            observation = steps[-1]
            source, log = outputs / "FirstSliceCorrupted.v", outputs / "FirstSliceCorrupted.compile.log"
            if mutation == "missing-source":
                source.unlink()
            elif mutation == "unrelated-source":
                source.write_bytes(b"Definition unrelated := 0.\n")
            elif mutation == "uncorrupted-source":
                source.write_bytes((outputs / "FirstSlice.v").read_bytes())
            elif mutation in {"signal", "accepted"}:
                observation["returncode"] = -9 if mutation == "signal" else 0
            elif mutation != "none":
                diagnostic = log.read_bytes()
                if mutation == "empty-diagnostic":
                    diagnostic = b""
                elif mutation == "unrelated-file":
                    diagnostic = diagnostic.replace(b"FirstSliceCorrupted.v", b"MissingLibrary.v")
                elif mutation == "unrelated-line":
                    diagnostic = diagnostic.replace(b", line 30,", b", line 1,")
                elif mutation == "syntax-error":
                    diagnostic = diagnostic.split(b"Error:")[0] + b"Error: Syntax error.\n"
                elif mutation == "extra-unrelated-error":
                    diagnostic += b'File "./MissingLibrary.v", line 1, characters 0-1:\nError: Library missing.\n'
                else:
                    diagnostic += diagnostic
                log.write_bytes(diagnostic)
                observation.update(log_sha256=slice_harness._sha256(diagnostic),
                                   stdout_bytes=len(diagnostic), stdout_sha256=slice_harness._sha256(diagnostic))
            artifacts: dict[str, object] = dict(slice_harness._artifacts(outputs))
            try:
                slice_harness._retained_proof(root, report, outputs, artifacts)
            except ValueError as error:
                ensure(mutation != "none", f"intended type refusal was rejected: {error}")
            else:
                ensure(mutation == "none", f"{mutation} was mistaken for the intended proof corruption refusal")


def _control_coverage() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-control-coverage-") as temporary:
        root = Path(temporary)
        outputs = root / "slice-fixture"
        outputs.mkdir()
        for mutation in ("none", "missing-capacity", "small-capacity", "large-capacity", "unchecked",
                         "boolean-metric", "negative-metric", "zero-obligations", "wrong-size",
                         "missing-capacity-object", "missing-capacity-source", "changed-capacity-source",
                         "missing-capacity-input", "changed-capacity-input", "swapped-capacity-inputs",
                         "missing-controls", "count", "boolean-count", "duplicate", "unknown",
                         "unparsed", "syntax-refusal", "wrong-reason", "bad-line", "bad-column",
                         "missing-control-source", "changed-control-source", "out-of-range-line", "out-of-range-column"):
            report = _proof_fixture(root, outputs)
            capacity = cast("dict[str, object]", report["capacity_invariance"])
            rows = cast("list[dict[str, object]]", report["negative_controls"])
            if mutation == "missing-capacity":
                del report["capacity_invariance"]
            elif mutation in {"small-capacity", "large-capacity"}:
                capacity[mutation.replace("-", "_")] = "8usize" if mutation == "large-capacity" else "9usize"
            elif mutation == "unchecked":
                capacity["kernel_checked"] = False
            elif mutation in {"boolean-metric", "negative-metric", "zero-obligations"}:
                capacity["obligation_count"] = {"boolean-metric": True, "negative-metric": -1,
                                                "zero-obligations": 0}[mutation]
            elif mutation == "wrong-size":
                capacity["gallina_bytes"] = 1
            elif mutation == "missing-capacity-object":
                (outputs / "CapLarge.vo").unlink()
            elif mutation == "missing-capacity-source":
                (outputs / "CapSmall.v").unlink()
            elif mutation == "changed-capacity-source":
                (outputs / "CapSmall.v").write_bytes(b"another capacity subject")
            elif mutation == "missing-capacity-input":
                (outputs / "CapSmall.vela").unlink()
            elif mutation == "changed-capacity-input":
                path = outputs / "CapLarge.vela"
                path.write_bytes(path.read_bytes().replace(b"1_000_000_000usize", b"1_000_000_001usize"))
            elif mutation == "swapped-capacity-inputs":
                (outputs / "CapLarge.vela").write_bytes((outputs / "CapSmall.vela").read_bytes())
            elif mutation == "missing-controls":
                rows.pop()
            elif mutation in {"count", "boolean-count"}:
                report["negative_controls_count"] = 0 if mutation == "count" else True
            elif mutation == "duplicate":
                rows[-1] = copy.deepcopy(rows[0])
            elif mutation == "unknown":
                rows[0]["name"] = "unrelated-control"
            elif mutation == "unparsed":
                rows[0]["parsed_surface"] = False
            elif mutation == "syntax-refusal":
                rows[0]["category"] = "syntax"
            elif mutation == "wrong-reason":
                rows[0]["message"] = "unrelated semantic refusal"
            elif mutation == "bad-line":
                rows[0]["line"] = True
            elif mutation == "bad-column":
                rows[0]["column"] = 0
            elif mutation == "missing-control-source":
                (outputs / "negative-controls/oob-read.vela").unlink()
            elif mutation == "changed-control-source":
                path = outputs / "negative-controls/oob-read.vela"
                path.write_bytes(path.read_bytes().replace(b"Bad", b"Bogus"))
            elif mutation == "out-of-range-line":
                rows[0]["line"] = 100_000
            elif mutation == "out-of-range-column":
                rows[0]["column"] = 100_000
            artifacts: dict[str, object] = dict(slice_harness._artifacts(outputs))
            try:
                slice_harness._retained_controls(report, outputs, artifacts)
            except ValueError as error:
                ensure(mutation != "none", f"complete retained controls refused: {error}")
            else:
                ensure(mutation == "none", f"{mutation} concealed incomplete qualification coverage")
        report = _proof_fixture(root, outputs)
        steps = cast("list[dict[str, object]]", report["steps"])
        for name in ("CapSmall.compile.log", "CapLarge.compile.log", "CapGate.kernel.log"):
            damaged = copy.deepcopy(report)
            damaged["steps"] = [step for step in steps if Path(str(step["log"])).name != name]
            try:
                slice_harness._retained_proof(root, damaged, outputs, dict(slice_harness._artifacts(outputs)))
            except ValueError:
                pass
            else:
                raise AssertionError(f"omitted capacity process {name} was accepted")


def _execution_coverage() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-execution-coverage-") as temporary:
        directory = Path(temporary) / "slice-fixture"
        directory.mkdir()
        mutations = ("none", "missing-run", "unknown-run", "missing-process", "command", "image-command",
                     "profile-command", "missing-log", "log-alias", "log-hash", "signal", "boolean-returncode",
                     "stdout-size", "stderr-hash", "verdict", "code", "record-count", "boolean-count",
                     "trace-digest", "roundtrip", "image-size", "missing-image", "rehashed-image",
                     "rehashed-trace", "rehashed-verdict", "no-trace", "missing-simulator", "missing-profile",
                     "promoted-compiler", "boolean-available", "unavailable-claims")
        for mutation in mutations:
            report = _execution_fixture(directory)
            runs = cast("dict[str, dict[str, object]]", report["purecap_cheri_runs"])
            row = runs["pass"]
            process = cast("dict[str, object]", row["process"])
            log, elf = directory / "purecap_pass.sail.log", directory / "purecap_pass.elf"
            if mutation == "missing-run":
                del runs["bounds-trap"]
            elif mutation == "unknown-run":
                runs["unrelated"] = copy.deepcopy(row)
            elif mutation == "missing-process":
                del row["process"]
            elif mutation in {"command", "image-command", "profile-command"}:
                command = cast("list[str]", process["command"])
                command[{"command": 0, "profile-command": 2, "image-command": -1}[mutation]] = "other-subject"
            elif mutation == "missing-log":
                log.unlink()
            elif mutation == "log-alias":
                process["log"] = str(directory / "purecap_bounds-trap.sail.log")
            elif mutation == "log-hash":
                process["log_sha256"] = "0" * 64
            elif mutation in {"signal", "boolean-returncode", "stdout-size", "stderr-hash"}:
                field, changed = {"signal": ("returncode", -9), "boolean-returncode": ("returncode", False),
                                  "stdout-size": ("stdout_bytes", 0), "stderr-hash": ("stderr_sha256", "0" * 64)}[mutation]
                process[field] = changed
            elif mutation in {"verdict", "code", "record-count", "boolean-count", "trace-digest", "roundtrip", "image-size"}:
                field, changed = {"verdict": ("verdict", "trap"), "code": ("code", True),
                                  "record-count": ("records", 0), "boolean-count": ("records", True),
                                  "trace-digest": ("trace_digest", "0" * 16), "roundtrip": ("cap_roundtrip", False),
                                  "image-size": ("image_bytes", 0)}[mutation]
                row[field] = changed
            elif mutation == "missing-image":
                elf.unlink()
            elif mutation == "rehashed-image":
                elf.write_bytes(b"substitute image")
            elif mutation in {"rehashed-trace", "rehashed-verdict", "no-trace"}:
                raw = log.read_bytes()
                raw = (raw.replace(b"00000013", b"00000093") if mutation == "rehashed-trace"
                       else raw.replace(b"SUCCESS", b"FAILURE: 7") if mutation == "rehashed-verdict"
                       else b"SUCCESS\n")
                log.write_bytes(raw)
                process.update(log_sha256=hashlib.sha256(raw).hexdigest(), stdout_bytes=len(raw),
                               stdout_sha256=hashlib.sha256(raw).hexdigest(), stderr_bytes=0,
                               stderr_sha256=hashlib.sha256(b"").hexdigest())
                if mutation == "no-trace":
                    row.update(records=0, trace_digest=hashlib.sha256(b"").hexdigest()[:16], cap_roundtrip=False)
            elif mutation in {"missing-simulator", "missing-profile"}:
                files = cast("dict[str, object]", cast("dict[str, object]", report["execution_inputs"])["files"])
                del files[mutation.removeprefix("missing-")]
            elif mutation in {"promoted-compiler", "boolean-available", "unavailable-claims"}:
                compiler = cast("dict[str, object]", report["compcert_sail"])
                compiler["available" if mutation != "unavailable-claims" else "interp_exit_code"] = (
                    True if mutation == "promoted-compiler" else 0)
            artifacts: dict[str, object] = dict(slice_harness._artifacts(directory))
            try:
                slice_harness._retained_execution(report, directory, artifacts)
            except (ValueError, TypeError, OSError) as error:
                ensure(mutation != "none", f"complete execution coverage refused: {error}")
            else:
                ensure(mutation == "none", f"{mutation} concealed incomplete execution coverage")


def _compiler_coverage() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-compiler-coverage-") as temporary:
        directory = Path(temporary) / "slice-fixture"
        directory.mkdir()
        for mutation in ("none", "availability", "compiler-path", "compiler-hash", "clight-path", "clight-hash",
                         "assembly-hash", "assembly-lines", "interp-code", "boolean-code", "sail-verdict",
                         "trace-count", "trace-digest", "roundtrip", "missing-control", "duplicate-control",
                         "wrong-control", "target-code", "interp-control-code", "missing-clight", "missing-assembly"):
            report = _execution_fixture(directory, available=True)
            compiler = cast("dict[str, object]", report["compcert_sail"])
            fields: dict[str, tuple[str, object]] = {
                "availability": ("available", False), "compiler-path": ("ccomp_path", "other-compiler"),
                "compiler-hash": ("ccomp_sha256", "0" * 64), "clight-path": ("clight_path", "other-clight"),
                "clight-hash": ("clight_sha256", "0" * 64), "assembly-hash": ("asm_sha256", "0" * 64),
                "assembly-lines": ("asm_lines", 0), "interp-code": ("interp_exit_code", 1),
                "boolean-code": ("interp_exit_code", False), "sail-verdict": ("sail_verdict", "fail"),
                "trace-count": ("sail_records", 0), "trace-digest": ("sail_trace_digest", "malformed"),
                "roundtrip": ("sail_cap_roundtrip", 1),
            }
            if mutation in fields:
                field, changed = fields[mutation]
                compiler[field] = changed
            elif mutation in {"missing-control", "duplicate-control", "wrong-control", "target-code", "interp-control-code"}:
                controls = cast("list[dict[str, object]]", compiler["perturbed_controls"])
                if mutation == "missing-control":
                    controls.pop()
                elif mutation == "duplicate-control":
                    controls[-1] = controls[0]
                else:
                    field = {"wrong-control": "name", "target-code": "target_code", "interp-control-code": "interp_code"}[mutation]
                    controls[0][field] = "another-control" if mutation == "wrong-control" else 0
            elif mutation in {"missing-clight", "missing-assembly"}:
                (directory / "first_slice" / ("first_slice.light.c" if mutation == "missing-clight" else "first_slice.s")).unlink()
            try:
                slice_harness._retained_execution(report, directory, dict(slice_harness._artifacts(directory)))
            except (ValueError, TypeError, OSError) as error:
                ensure(mutation != "none", f"complete optional compiler coverage refused: {error}")
            else:
                ensure(mutation == "none", f"{mutation} concealed missing optional compiler coverage")


def _compiler_process_coverage() -> None:
    mutations = ("none", "missing-programs", "missing-program", "duplicate-program", "unknown-program",
                 "wrong-expect", "boolean-expect", "missing-process", "duplicate-process", "command", "cwd",
                 "process-exit", "boolean-exit", "log-hash", "stream-length", "stream-hash", "source",
                 "effective-input", "interpreter-input", "image", "image-size", "boolean-image-size",
                 "interpreter-verdict", "interpreter-stderr", "interpreter-duplicate", "target-verdict",
                 "target-trace", "target-empty", "summary-trace", "summary-count", "summary-roundtrip")
    with tempfile.TemporaryDirectory(prefix="vela-slice-compiler-processes-") as temporary:
        directory = Path(temporary) / "slice-fixture"
        directory.mkdir()
        for mutation in mutations:
            report = _execution_fixture(directory, available=True)
            compiler = cast("dict[str, object]", report["compcert_sail"])
            programs = cast("list[dict[str, object]]", compiler["programs"])
            program = programs[0]
            processes = cast("list[dict[str, object]]", program["processes"])
            if mutation == "missing-programs":
                del compiler["programs"]
            elif mutation == "missing-program":
                programs.pop()
            elif mutation == "duplicate-program":
                programs[-1] = copy.deepcopy(program)
            elif mutation == "unknown-program":
                program["name"] = "unrelated"
            elif mutation in {"wrong-expect", "boolean-expect"}:
                program["expect"] = 7 if mutation == "wrong-expect" else False
            elif mutation == "missing-process":
                processes.pop()
            elif mutation == "duplicate-process":
                processes[-1] = copy.deepcopy(processes[0])
            elif mutation in {"command", "cwd", "process-exit", "boolean-exit", "log-hash", "stream-length", "stream-hash"}:
                field, changed = {
                    "command": ("command", ["another-compiler"]), "cwd": ("cwd", str(directory)),
                    "process-exit": ("returncode", 1), "boolean-exit": ("returncode", False),
                    "log-hash": ("log_sha256", "0" * 64), "stream-length": ("stdout_bytes", True),
                    "stream-hash": ("stderr_sha256", "0" * 64),
                }[mutation]
                processes[1][field] = changed
            elif mutation in {"source", "effective-input", "interpreter-input", "image"}:
                path = {"source": directory / "first_slice.c",
                        "effective-input": directory / "first_slice/first_slice.i",
                        "interpreter-input": directory / "first_slice.interp/first_slice.i",
                        "image": directory / "first_slice.elf"}[mutation]
                path.write_bytes(b"changed retained subject")
            elif mutation in {"image-size", "boolean-image-size"}:
                program["image_bytes"] = 1 if mutation == "image-size" else True
            elif mutation in {"summary-trace", "summary-count", "summary-roundtrip"}:
                field, changed = {"summary-trace": ("sail_trace_digest", "0" * 16),
                                  "summary-count": ("sail_records", 4),
                                  "summary-roundtrip": ("sail_cap_roundtrip", False)}[mutation]
                compiler[field] = changed
            elif mutation != "none":
                process = processes[3 if mutation.startswith("interpreter-") else 4]
                stdout = slice_harness._retained_stdout(process).decode()
                stderr = "diagnostic \u03bb\n"
                if mutation == "interpreter-verdict":
                    stdout = "Time 42: program terminated (exit code = 7)\n"
                elif mutation == "interpreter-stderr":
                    stdout, stderr = "", stdout
                elif mutation == "interpreter-duplicate":
                    stdout += stdout
                elif mutation == "target-verdict":
                    stdout = stdout.replace("SUCCESS", "FAILURE: 7")
                elif mutation == "target-trace":
                    stdout = stdout.replace("00000013", "00000093")
                else:
                    stdout = "SUCCESS\n"
                raw = (stdout + stderr).encode()
                Path(str(process["log"])).write_bytes(raw)
                process.update(log_sha256=hashlib.sha256(raw).hexdigest(), stdout_bytes=len(stdout.encode()),
                               stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(), stderr_bytes=len(stderr.encode()),
                               stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest())
            try:
                slice_harness._retained_execution(report, directory, dict(slice_harness._artifacts(directory)))
            except (ValueError, TypeError, OSError) as error:
                ensure(mutation != "none", f"complete compiler processes refused: {error}")
            else:
                ensure(mutation == "none", f"{mutation} concealed changed compiler process evidence")


def _compiler_observations() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-compiler-observations-") as temporary:
        directory = Path(temporary)
        stdout, stderr = "compiler output \u03bb\n", "diagnostic \U0001f680\n" * 100

        def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            working = Path(str(kwargs.get("cwd", directory)))
            if "-E" in argv:
                Path(argv[-1]).write_bytes((working / argv[-3]).read_bytes())
            elif "-S" in argv:
                (working / argv[-1]).write_bytes(b".text\n.globl main\nmain:\nli a0, 7\nret\n")
            said = ("Time 1: program terminated (exit code = 7)\n" if "-interp" in argv else
                    "I 1 0000000080000000 00000013\nFAILURE: 7\n" if "--config" in argv else stdout)
            return subprocess.CompletedProcess(argv, 1 if "--config" in argv else 0, said, stderr)

        observations: list[dict[str, object]] = []
        program = slice_harness.cd.Program("independent", "given", "int main(void) { return 7; }\n", 1, 7)
        with patch.object(slice_harness.cd.subprocess, "run", side_effect=run):
            report = slice_harness.cd.run_program(program, ["ccomp", "-dclight"], directory, ["simulator"],
                                                  directory / "profile.json", "", interp=True, observations=observations)
        ensure(slice_harness.cd.as_expected(report) and report.interpreted is not None
               and report.interpreted.code == 7 and len(observations) == 5,
               "observing compiler stages changed interpretation or lost a process")
        for observation in observations:
            log = Path(str(observation["log"]))
            raw = log.read_bytes()
            ensure(observation["log_sha256"] == hashlib.sha256(raw).hexdigest()
                   and observation["stderr_bytes"] == len(stderr.encode()) and raw.endswith(stderr.encode()),
                   "compiler observation truncated or misbound diagnostics")
            slice_harness._retained_stdout(observation)
        ensure([Path(str(row["log"])).name for row in observations] == [
            "independent.preprocess.log", "independent.compile.log", "independent.preprocess.log",
            "independent.interpret.log", "independent.sail.log"], "compiler process order is incomplete")

        def failed_interpreter(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            completed = run(argv, **kwargs)
            if "-interp" in argv:
                completed.returncode = 1
            return completed

        with patch.object(slice_harness.cd.subprocess, "run", side_effect=failed_interpreter):
            interpreted = slice_harness.cd.interpret_c(["ccomp"], directory / "independent/independent.i",
                                                       directory / "refused.interp")
        ensure(interpreted.code is None and interpreted.exit_code == 1,
               "failed interpreter process promoted a printed termination to a source verdict")


def _simulator_observation() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-simulator-observation-") as temporary:
        directory = Path(temporary)
        elf, profile = directory / "control.elf", directory / "profile.json"
        stdout, stderr = "I 1 0000000080000000 00000013\nSUCCESS\n", "diagnostic λ\n"
        observations: list[dict[str, object]] = []
        completed = subprocess.CompletedProcess(["simulator"], 0, stdout, stderr)
        with patch.object(slice_harness.cd.subprocess, "run", return_value=completed) as run:
            result = slice_harness.cd.run_image(["simulator"], profile, elf, directory, observations=observations)
        ensure(result.verdict == "pass" and result.records == 1 and len(observations) == 1,
               "retaining a simulator observation changed its verdict or lost its process")
        row = observations[0]
        raw = (stdout + stderr).encode()
        ensure(row["command"] == run.call_args.args[0] and row["returncode"] == 0,
               "simulator observation names another command or exit status")
        ensure(Path(str(row["log"])).read_bytes() == raw and row["log_sha256"] == hashlib.sha256(raw).hexdigest(),
               "simulator process log is not bound to exact retained bytes")
        ensure(row["stdout_bytes"] == len(stdout.encode()) and row["stderr_bytes"] == len(stderr.encode())
               and row["stdout_sha256"] == hashlib.sha256(stdout.encode()).hexdigest()
               and row["stderr_sha256"] == hashlib.sha256(stderr.encode()).hexdigest(),
               "simulator observation lost Unicode byte stream boundaries")
        with patch.object(slice_harness.cd.subprocess, "run", side_effect=subprocess.TimeoutExpired(["simulator"], 1)):
            result = slice_harness.cd.run_image(["simulator"], profile, elf, directory, observations=observations)
        ensure(result.verdict == "no-verdict" and len(observations) == 1,
               "timed-out simulation fabricated a completed observation")


def _output_bounds() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-slice-output-bounds-") as temporary:
        root = Path(temporary)
        output = root / "slice-fixture"
        output.mkdir()
        artifact = output / "FirstSlice.vo"
        artifact.write_bytes(b"checked fixture")
        ensure(slice_harness._receipt_directory(str(output), root, "slice-") == output,
               "expected local output directory was refused")
        for name in (str(root), str(output / ".."), "slice-fixture", str(artifact)):
            try:
                slice_harness._receipt_directory(name, root, "slice-")
            except ValueError:
                pass
            else:
                raise AssertionError("receipt escaped the expected output directory scope")
        for bound, value, message in (("ARTIFACT_ENTRIES", 0, "entry bound"),
                                      ("ARTIFACT_BYTES", 1, "byte bound")):
            with patch.object(slice_harness, bound, value):
                try:
                    slice_harness._artifacts(output)
                except ValueError as error:
                    ensure(message in str(error), "oversized output inventory lost its bound diagnostic")
                else:
                    raise AssertionError("oversized output inventory was hashed")


def _cli_dispatch() -> None:
    expected = {"status": "matched", "proof_replayed": False, "artifact_accepted": False}
    with patch.object(cli.vela_first_slice, "verify_bindings", return_value=expected) as verify, \
            redirect_stdout(out := StringIO()), redirect_stderr(err := StringIO()):
        code = cli.main(["first-slice-bindings", "retained.json"])
    ensure(code == 0 and not err.getvalue() and json.loads(out.getvalue()) == expected,
           "binding CLI altered the receipt verdict")
    ensure(verify.call_args.args[1] == Path("retained.json"), "binding CLI selected another receipt")
    with patch.object(cli.vela_first_slice, "verify_bindings", side_effect=ValueError("changed output")), \
            redirect_stdout(out := StringIO()), redirect_stderr(err := StringIO()):
        code = cli.main(["first-slice-bindings", "retained.json"])
    ensure(code == 1 and not out.getvalue() and "changed output" in err.getvalue(),
           "binding CLI published a stale verdict")


def cases() -> list[Case]:
    return [Case("local producer source and dependency inventory", _source_inventory),
            Case("changed inputs withdraw first-slice publication", _publication_freshness),
            Case("retained first-slice identities and malformed refusals", _binding_checks),
            Case("retained proof coverage and assumption consistency", _retained_coverage),
            Case("stdout audit provenance preserves stderr diagnostics", _process_streams),
            Case("proof corruption binds the intended source and type refusal", _corruption_control_subjects),
            Case("retained capacity and semantic refusal coverage", _control_coverage),
            Case("retained capability execution transcripts and images", _execution_coverage),
            Case("retained optional compiler availability and controls", _compiler_coverage),
            Case("retained compiler process subjects and rehashed contradictions", _compiler_process_coverage),
            Case("compiler observations retain complete stage streams", _compiler_observations),
            Case("simulator observation preserves exact process streams", _simulator_observation),
            Case("first-slice output directory and inventory bounds", _output_bounds),
            Case("first-slice binding CLI and refusal", _cli_dispatch)]
