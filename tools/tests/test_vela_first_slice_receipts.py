# SPDX-License-Identifier: Apache-2.0
"""Exact-subject and failure controls for first-slice development receipts."""

import copy
import json
import tempfile
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.harness import TOOLS, Case, ensure
from toolchain import first_slice as slice_harness
from toolchain.cli import vela_parser as cli

INDEPENDENT_CASES = True


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
    for mutation in ("none", "source", "revision", "execution", "prover", "runtime", "parser", "failure"):
        with tempfile.TemporaryDirectory(prefix="vela-slice-publication-") as temporary, ExitStack() as stack:
            root = Path(temporary)
            latest = root / "qualification.json"
            latest.write_text('{"status":"passed","stale":true}', encoding="utf-8")
            parser_receipt: dict[str, object] = {"toolchain": {"menhir": "locked"}}
            compiled = slice_harness.vela_parser.Build(root, root / "parser", parser_receipt)
            stack.enter_context(patch.object(slice_harness, "_work_root", return_value=root))
            for name, original in (("_inputs", {"source": "old"}), ("_revision", "a" * 40),
                                   ("_execution_inputs", {"simulator": "old"})):
                changed = {"source": "new"} if name == "_inputs" else (
                    "b" * 40 if name == "_revision" else {"simulator": "new"})
                subject = {"_inputs": "source", "_revision": "revision", "_execution_inputs": "execution"}[name]
                stack.enter_context(patch.object(slice_harness, name,
                                                  side_effect=[original, changed if mutation == subject else original]))
            for name, subject in (("_toolchain", "prover"), ("_runtime", "runtime")):
                stack.enter_context(patch.object(slice_harness.replay, name,
                                                  side_effect=[{}, {"changed": True} if mutation == subject else {}]))
            stack.enter_context(patch.object(slice_harness.vela_parser, "build", return_value=compiled))
            stack.enter_context(patch.object(slice_harness.vela_parser, "_toolchain", return_value={"menhir": "locked"}))
            stack.enter_context(patch.object(slice_harness.replay, "_parser_outputs", return_value={"parser": "old"}))

            def run(_root: Path, directory: Path, _steps: list[dict[str, object]],
                    _compiler: Path | None, _compiled: object, *, case: str = mutation,
                    receipt: dict[str, object] = parser_receipt) -> dict[str, object]:
                (directory / "FirstSlice.vo").write_bytes(b"checked fixture")
                if case == "parser":
                    receipt["toolchain"] = {"menhir": "changed"}
                if case == "failure":
                    raise ValueError("native producer refused")
                return {"status": "passed", "kernel_checked": True, "accepted": True}

            stack.enter_context(patch.object(slice_harness, "_qualify_attempt", side_effect=run))
            try:
                report = slice_harness.qualify(root)
            except ValueError as error:
                ensure(mutation != "none", f"unchanged producer failed: {error}")
                ensure(not latest.exists(), "failed attempt preserved a stale passing receipt")
                journals = list(root.glob("slice-*/attempt.json"))
                ensure(len(journals) == 1, "failed producer lost its attempt journal")
                row = json.loads(journals[0].read_text(encoding="utf-8"))
                ensure(row["status"] == "failed" and not row["kernel_checked"] and not row["accepted"],
                       "failed producer retained source-proof acceptance")
            else:
                ensure(mutation == "none", f"{mutation} changed without withdrawing acceptance")
                ensure(report["schema"] == 2 and report["status"] == "passed" and latest.is_file(),
                       "unchanged local producer did not publish")
                ensure(not report["artifact_accepted"] and not report["source_correspondence"]
                       and not report["production_admission"] and not report["full_machine_refinement_closed"],
                       "local proof producer claimed complete release evidence")
                ensure(bool(report["artifacts_sha256"]), "passing receipt omitted retained outputs")


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
                               ("runtime", {"changed": True})):
            damaged = copy.deepcopy(report)
            damaged[field] = changed
            write(damaged)
            try:
                slice_harness.verify_bindings(root, receipt)
            except (ValueError, TypeError, OSError):
                pass
            else:
                raise AssertionError(f"changed {field} was accepted")
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
            Case("first-slice output directory and inventory bounds", _output_bounds),
            Case("first-slice binding CLI and refusal", _cli_dispatch)]
