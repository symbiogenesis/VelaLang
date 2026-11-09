# SPDX-License-Identifier: Apache-2.0
"""Support-source authentication, bounded compatibility and qualification refusals."""

import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

import toolchain as vela
from tests.harness import Case, ensure
from toolchain import parser as vela_parser
from toolchain import parser_checked as checked


def _tar(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as bundle:
        root = tarfile.TarInfo("release")
        root.type = tarfile.DIRTYPE
        bundle.addfile(root)
        for name, contents in files.items():
            member = tarfile.TarInfo(f"release/{name}")
            member.size = len(contents)
            bundle.addfile(member, io.BytesIO(contents))
    return stream.getvalue()


def _files() -> dict[str, bytes]:
    files = {f"coq-menhirlib/src/{name}.v": b"fixture source\n" for name in checked.MODULES}
    files.update({"coq-menhirlib/src/_CoqProject": b"fixture project\n",
                  "LICENSE": b"generator terms\n", "coq-menhirlib/LICENSE": b"support terms\n"})
    return files


def _archive_controls() -> None:
    files = _files()
    licenses = {name: checked._sha256(files[name]) for name in checked.LICENSES}
    version = checked._sha256(files["coq-menhirlib/src/Version.v"])
    original = _tar(files)
    with patch.object(checked, "LICENSES", licenses), patch.object(checked, "VERSION_SHA256", version):
        with patch.object(checked, "ARCHIVE_SHA512", hashlib.sha512(original).hexdigest()):
            ensure(checked._release_sources(original) == files, "authenticated selected sources changed")
            try:
                checked._release_sources(original + b"corruption")
            except ValueError as error:
                ensure("digest" in str(error), "archive corruption lost its cause")
            else:
                raise AssertionError("corrupt archive consumed")
        for change in ("missing", "license", "version", "escape"):
            changed = dict(files)
            if change == "missing":
                changed.pop("coq-menhirlib/src/Main.v")
            elif change == "license":
                changed["coq-menhirlib/LICENSE"] += b"changed"
            elif change == "version":
                changed["coq-menhirlib/src/Version.v"] = b"Definition require_unreleased := tt.\n"
            else:
                changed["../escape"] = b"unsafe"
            archive = _tar(changed)
            with patch.object(checked, "ARCHIVE_SHA512", hashlib.sha512(archive).hexdigest()):
                try:
                    checked._release_sources(archive)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"unsupported {change} archive accepted")


def _proof_footprint() -> None:
    # Original authored fixtures: no upstream proof text is incorporated here.
    original = b"".join(f"Definition {name} : nat.\nrefine 0.\nProof.\nexact 0.\nDefined.\n".encode()
                         for name in checked.TARGETS)
    candidate = original.replace(b"refine 0.\nProof.\n", b"Proof.\nrefine 0.\n")
    reference = original.replace(b"Proof.\n", b"")
    with patch.object(checked, "INTERPRETER_SHA256", checked._sha256(original)), \
            patch.object(checked, "CANDIDATE_SHA256", checked._sha256(candidate)), \
            patch.object(checked, "REFERENCE_SHA256", checked._sha256(reference)):
        ensure(checked._proof_openings(original) == candidate, "repair changed more than proof openings")
        ensure(checked._proof_openings(original, reference=True) == reference, "diagnostic twin changed terms")
        for source in (original + b"changed", candidate):
            try:
                checked._proof_openings(source)
            except ValueError as error:
                ensure("unsupported" in str(error), "unsupported source repair lost its cause")
            else:
                raise AssertionError("repair accepted different or already modified source")
        with patch.object(checked, "CANDIDATE_SHA256", "0" * 64):
            try:
                checked._proof_openings(original)
            except ValueError as error:
                ensure("reviewed candidate" in str(error), "changed repair digest lost its cause")
            else:
                raise AssertionError("unexpected repaired bytes accepted")


def _validator_items_map_footprint() -> None:
    original = (
        b"Proof.\n"
        b"  intros -> Hval1 Hval2 Val st prod fut lookahead (pos & -> & Hlookahead).\n"
        b"  rewrite /forallb_items StateProdPosMap.fold_1 in Val.\n"
        b"  assert (match future_of_prod prod pos with\n"
        b"          | [] => b1 st prod pos (find_items_map (items_map ()) st prod pos)\n"
        b"          | s :: fut' => b2 st prod pos (find_items_map (items_map ()) st prod pos) s fut'\n"
        b"          end = true).\n"
        b"  - unfold find_items_map in *.\n"
        b"    assert (Hfind := @StateProdPosMap.find_2 _ (items_map ()) (st, prod, pos)).\n"
    )
    candidate = (
        b"Proof.\n"
        b"  intros Him Hval1 Hval2 Val st prod fut lookahead (pos & -> & Hlookahead).\n"
        b"  rewrite -Him in Hlookahead.\n"
        b"  rewrite /forallb_items StateProdPosMap.fold_1 in Val.\n"
        b"  assert (match future_of_prod prod pos with\n"
        b"          | [] => b1 st prod pos (find_items_map im st prod pos)\n"
        b"          | s :: fut' => b2 st prod pos (find_items_map im st prod pos) s fut'\n"
        b"          end = true).\n"
        b"  - unfold find_items_map in *.\n"
        b"    assert (Hfind := @StateProdPosMap.find_2 _ im (st, prod, pos)).\n"
    )
    with patch.object(checked, "VALIDATOR_COMPLETE_SHA256", checked._sha256(original)), \
            patch.object(checked, "VALIDATOR_COMPLETE_CANDIDATE_SHA256", checked._sha256(candidate)):
        ensure(checked._validator_items_map(original) == candidate, "items_map repair changed unexpected bytes")
        ensure(checked._validator_items_map(original, reference=True) == original, "reference items_map changed")
        for source in (original + b"changed", candidate):
            try:
                checked._validator_items_map(source)
            except ValueError as error:
                ensure("unsupported" in str(error), "unsupported Validator_complete source lost its cause")
            else:
                raise AssertionError("Validator_complete repair accepted unexpected source")
        with patch.object(checked, "VALIDATOR_COMPLETE_CANDIDATE_SHA256", "0" * 64):
            try:
                checked._validator_items_map(original)
            except ValueError as error:
                ensure("reviewed candidate" in str(error), "changed Validator_complete digest lost its cause")
            else:
                raise AssertionError("unexpected Validator_complete repaired bytes accepted")


def _pure_grammar_view_and_assumptions() -> None:
    root = Path(__file__).resolve().parents[2]
    mly_text = (root / "tools/toolchain/parser/parser.mly").read_text(encoding="utf-8")
    pure_mly, token_stub = checked._pure_grammar_view(mly_text)
    ensure(pure_mly == checked.VELA_PURE_GRAMMAR_MLY, "pure grammar view differed from checked specification")
    ensure("type token =" in token_stub and "let generic_call_prefix _ _ : unit = raise Error" in token_stub,
           "token stub omitted token definitions or prefix entry")
    for mutated in (
        mly_text.replace("MODULE module_name=name SEMICOLON", "MODULE module_name=name"),
        mly_text.replace("%token MODULE ", "%token "),
    ):
        try:
            checked._pure_grammar_view(mutated)
        except ValueError:
            pass
        else:
            raise AssertionError("drifted parser.mly pure grammar skeleton accepted")
    closed = "Closed under the global context\n" * len(checked.THEOREMS)
    checked._check_closed_assumptions(closed, len(checked.THEOREMS))
    for unclosed in ("Axioms:\nAut.Gram.token : Type\n", "Closed under the global context\n"):
        try:
            checked._check_closed_assumptions(unclosed, len(checked.THEOREMS))
        except ValueError as error:
            ensure("unclosed assumptions" in str(error), "unclosed assumption refusal lost its cause")
        else:
            raise AssertionError("unclosed concrete theorem assumptions accepted")


def _process_controls() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-support-") as temporary:
        directory = Path(temporary)
        for code, output, expected in ((1, b"require_unreleased was not found", True),
                                       (0, b"require_unreleased", False),
                                       (1, b"unrelated error", False),
                                       (127, b"require_unreleased", False)):
            process = subprocess.CompletedProcess(["rocq"], code, b"", output)
            steps: list[dict[str, object]] = []
            with patch.object(checked.subprocess, "run", return_value=process) as run:
                try:
                    checked._run(["rocq"], directory, directory / "control.stdout", steps,
                                 refusal="require_unreleased")
                except RuntimeError:
                    ensure(not expected, "genuine mismatched-version refusal failed")
                else:
                    ensure(expected, "successful or unrelated failure counted as negative control")
            ensure(run.call_args.kwargs["timeout"] == checked.TIMEOUT, "command lost its duration bound")
            ensure(steps[0]["exit"] == code, "command verdict not journalled")
        with patch.object(checked.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                "rocq", checked.TIMEOUT, output=b"partial", stderr=b"diagnostic")):
            steps = []
            try:
                checked._run(["rocq"], directory, directory / "timeout.stdout", steps)
            except RuntimeError as error:
                ensure("exceeded" in str(error), "timeout lacks a diagnostic")
            else:
                raise AssertionError("timed-out support command passed")
            ensure(steps[0]["status"] == "timeout", "timed-out attempt lost its verdict")
            ensure((directory / "timeout.stdout").read_bytes() == b"partialdiagnostic", "partial failure log lost")


def _refused_qualification() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-support-") as temporary:
        directory = Path(temporary)
        latest = directory / "qualification.json"
        latest.write_text('{"status":"passed","old":true}', encoding="utf-8")
        with patch.object(checked, "_work_root", return_value=directory), \
                patch.object(checked, "_inputs", return_value={}), \
                patch.object(checked, "_toolchain", side_effect=ValueError("different locked prover")):
            try:
                checked.qualify(directory)
            except ValueError as error:
                ensure("different locked prover" in str(error), "qualification failure swallowed")
            else:
                raise AssertionError("unsupported toolchain acquired a passing receipt")
        ensure(not latest.exists(), "failed qualification preserved old success")
        attempts = list(directory.glob("support-*/attempt.json"))
        ensure(len(attempts) == 1 and '"status": "failed"' in attempts[0].read_text(encoding="utf-8"),
               "failed qualification lost its retained attempt")


def _toolchain_controls() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-support-") as temporary:
        directory = Path(temporary)
        locks = directory / "tools/opam"
        locks.mkdir(parents=True)
        sail = locks / "sail.lock"
        sail.write_text(f'"menhir.{checked.RELEASE}"\n', encoding="utf-8")
        (locks / "rocq.lock").write_text(f'"rocq-core.{checked.proofenv.ROCQ_VERSION}"\n', encoding="utf-8")
        for name in ("rocq", "rocqchk", "ocamlc", "ocamllex", "menhir"):
            (directory / name).write_bytes(b"tool identity")
        expected = [
            f"The Rocq Prover, version {checked.proofenv.ROCQ_VERSION}",
            checked.proofenv.OCAML_VERSION,
            str(directory),
            f"menhir, version {checked.RELEASE}",
            str(directory),
        ]
        with patch.object(checked, "_run", side_effect=expected):
            identity = checked._toolchain(directory, directory, [])
        digests = identity["binary_sha256"]
        ensure(isinstance(digests, dict) and len(digests) == 5, "support tools lost executable identities")
        for index in (0, 1, 2, 3, 4):
            changed = [*expected]
            changed[index] = "different identity"
            with patch.object(checked, "_run", side_effect=changed):
                try:
                    checked._toolchain(directory, directory, [])
                except ValueError:
                    pass
                else:
                    raise AssertionError("unsupported tool identity accepted")
        sail.write_text('"menhir.different"\n', encoding="utf-8")
        with patch.object(checked, "_run") as run:
            try:
                checked._toolchain(directory, directory, [])
            except ValueError as error:
                ensure("Sail snapshot" in str(error), "different generator source lost its cause")
            else:
                raise AssertionError("support source disagreed with locked generator")
            run.assert_not_called()


def _changed_observations() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-support-observations-") as temporary:
        root = Path(temporary)
        candidate, reference = root / "candidate", root / "reference"
        candidate.mkdir()
        reference.mkdir()
        guard = f"Definition guard := Version.require_{checked.RELEASE}.\n"
        files = {candidate / "Frozen.v": checked.FROZEN_QUERY, reference / "Frozen.v": checked.FROZEN_QUERY,
                 candidate / "Assumptions.v": checked.ASSUMPTIONS_QUERY,
                 candidate / "VersionAccepted.v": guard,
                 candidate / "VersionRefused.v": guard.replace(f"require_{checked.RELEASE}", "require_unreleased"),
                 root / "run.stdout": "Closed under the global context\n", root / "run.stderr": ""}
        steps: list[dict[str, object]] = [{"stdout": str(root / "run.stdout"), "stderr": str(root / "run.stderr"),
                                         "stdout_sha256": checked._sha256(files[root / "run.stdout"].encode()),
                                         "stderr_sha256": checked._sha256(b"")}]
        for changed in (None, *files):
            for path, text in files.items():
                path.write_text(text, encoding="utf-8", newline="")
            if changed is not None:
                changed.write_bytes(b"substituted observation")
            try:
                checked._observations(candidate, reference, guard, steps)
            except ValueError as error:
                ensure(changed is not None and "changed" in str(error), "unexpected observation refusal")
            else:
                ensure(changed is None, "changed proof probe or transcript acquired qualification")


def _host_replacement_and_retirement() -> None:
    ensure(not hasattr(vela, "_Parser"), "legacy Python recursive-descent parser is still present")
    source = b"module M; public const Nat Base = 4; public Nat F(Nat x) => x + Base;"
    envelope = checked.parse_checked(source)
    ensure(envelope.get("schema") == 1 and envelope.get("source_sha256") == checked._sha256(source),
           "checked host parser returned an invalid envelope")
    module = vela.parse_module(source)
    ensure(module.name.text == "M" and len(module.declarations) == 2,
           "checked host parser decoded unexpected declarations")
    ensure(vela.translate_ast(source, envelope) == vela.translate(source),
           "translate and translate_ast diverged under the checked parser")
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="vela-checked-runtime-") as temporary:
        runtime_dir = Path(temporary)
        exe = runtime_dir / "vela-checked-parser"
        exe.write_bytes(b"original binary")
        receipt: dict[str, object] = {
            "schema": 1,
            "inputs": checked._runtime_inputs(root),
            "generated_sha256": {"vela-parser": checked._sha256(b"different binary")},
        }
        (runtime_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        with patch.object(checked, "_runtime_root", return_value=runtime_dir):
            try:
                checked.ensure_checked_build(root)
            except ValueError as error:
                ensure("changed after its build" in str(error), "tampered runtime binary lost its cause")
            else:
                raise AssertionError("tampered runtime binary was accepted")
        tampered = vela_parser.Build(runtime_dir, exe, receipt)
        try:
            checked.parse_checked(source, compiled=tampered)
        except ValueError as error:
            ensure("changed after its build" in str(error), "tampered explicit build lost its cause")
        else:
            raise AssertionError("tampered explicit build was accepted")


def cases() -> list[Case]:
    return [Case("immutable-source-and-version-controls", _archive_controls),
            Case("proof-opening-byte-footprint", _proof_footprint),
            Case("validator-items-map-byte-footprint", _validator_items_map_footprint),
            Case("pure-grammar-view-and-closed-assumptions", _pure_grammar_view_and_assumptions),
            Case("bounded-command-and-negative-verdict-controls", _process_controls),
            Case("locked-generator-and-prover-controls", _toolchain_controls),
            Case("changed-probes-and-transcripts-refuse", _changed_observations),
            Case("failed-qualification-discards-stale-success", _refused_qualification),
            Case("host-replacement-and-python-retirement", _host_replacement_and_retirement)]
