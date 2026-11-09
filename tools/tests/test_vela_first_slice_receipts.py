# SPDX-License-Identifier: Apache-2.0
"""Exact-subject and failure controls for first-slice development receipts."""

import copy
import json
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


def _proof_fixture(root: Path, outputs: Path, *, trusted: bool = False) -> dict[str, object]:
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
    (outputs / "FirstSliceAssumptions.v").write_text(
        "From VelaFirstSlice Require Import FirstSlice.\n" + "".join(
            f"Print Assumptions FirstSlice.{module}.{name}.\n" for name in names), encoding="utf-8")
    (outputs / "FirstSlice.assumptions.log").write_text("".join(
        f"Axioms:\n{module}.{axiom} : True\n" if trusted and index == 16
        else "Closed under the global context\n" for index in range(len(names))), encoding="utf-8")
    for name in ("FirstSlice.vo", "FirstSliceAssumptions.vo", "first_slice.c"):
        (outputs / name).write_bytes(f"retained {name}".encode())
    source = root / slice_harness.EXAMPLE
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"module Vela.FirstSlice;")
    commands = {
        "FirstSlice.compile.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "FirstSlice.v"],
        "FirstSlice.assumptions.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "FirstSliceAssumptions.v"],
        "FirstSlice.kernel.log": ["rocqchk", "-R", str(outputs), "VelaFirstSlice", "VelaFirstSlice.FirstSlice"],
        "FirstSliceCorrupted.compile.log": ["rocq", "c", "-q", "-R", str(outputs), "VelaFirstSlice", "FirstSliceCorrupted.v"],
    }
    steps: list[dict[str, object]] = []
    for name, command in commands.items():
        log = outputs / name
        if not log.is_file():
            log.write_bytes(b"independent retained transcript")
        refused = name == "FirstSliceCorrupted.compile.log"
        row: dict[str, object] = {
            "command": ["opam", "exec", "--switch", slice_harness.proofenv.ROCQ_SWITCH, "--", *command],
            "cwd": str(outputs), "returncode": 1 if refused else 0,
            "log": str(log), "log_sha256": slice_harness._sha256(log.read_bytes()),
        }
        if refused:
            row["expected_refusal"] = True
        steps.append(row)
    report: dict[str, object] = {
        "steps": steps, "accepted": not trusted, "kernel_checked": not trusted,
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
        execution = {"files": {}, "compcert_available": False}
        report: dict[str, object] = {
            "schema": 2, "scope": "vela-first-slice-qualification", "status": "passed",
            "artifact_accepted": False, "source_correspondence": False,
            "production_admission": False, "full_machine_refinement_closed": False,
            "inputs": source_inputs, "producer_revision": "a" * 40,
            "execution_inputs": execution, "toolchain": {}, "runtime": {},
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
            Case("first-slice output directory and inventory bounds", _output_bounds),
            Case("first-slice binding CLI and refusal", _cli_dispatch)]
