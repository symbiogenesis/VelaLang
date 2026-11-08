# SPDX-License-Identifier: Apache-2.0
"""Menhir-generated syntax campaign, CST/renderer, and independent AST/span oracle controls (Q25y)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

import toolchain as vela
from tests.harness import TOOLS, Case, ensure
from toolchain import MAX_LITERAL_DIGITS, MAX_SOURCE_BYTES, VelaError
from toolchain import parser as vela_parser
from toolchain import syntax_campaigns as campaigns
from toolchain.cli import vela_parser as cli

INDEPENDENT_CASES = True


def _renderer_and_token_payload_controls() -> None:
    report = campaigns.qualify_renderer()
    ensure(report["status"] == "qualified", "renderer qualification did not pass")
    ensure(report["terminal_count"] == len(campaigns.PURE_TERMINALS), "terminal coverage count mismatch")
    ensure(
        set(cast("list[str]", report["variants"])) == set(campaigns.RENDER_VARIANTS),
        "renderer variants mismatch",
    )

    sentence = campaigns.parse_sentence_line(
        "file: MODULE IDENT SEMICOLON PUBLIC NAT IDENT LPAREN BOOL IDENT COMMA RPAREN "
        "FATARROW DECIMAL MINUS DECIMAL SEMICOLON EOF\n"
    )
    ensure(sentence[0] == "MODULE" and sentence[-1] == "EOF", "sentence line parsing failed")

    canonical = campaigns.render_sentence(sentence, variant="canonical", seed=7)
    crlf = campaigns.render_sentence(sentence, variant="utf8_comments_crlf", seed=7)
    bare_cr = campaigns.render_sentence(sentence, variant="bare_cr_separators", seed=7)
    ensure(
        len({canonical.source, crlf.source, bare_cr.source}) == 3,
        "trivia variants did not vary raw source bytes",
    )
    ensure(
        campaigns.strip_spans(campaigns.IndependentPureAstOracle.parse(canonical.source)["ast"])
        == campaigns.strip_spans(campaigns.IndependentPureAstOracle.parse(crlf.source)["ast"])
        == campaigns.strip_spans(campaigns.IndependentPureAstOracle.parse(bare_cr.source)["ast"]),
        "trivia variants changed span-erased AST",
    )

    for bad_line in ("", "surface_file: MODULE IDENT SEMICOLON EOF", "MODULE IDENT SEMICOLON EOF"):
        try:
            campaigns.parse_sentence_line(bad_line)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted malformed sentence line {bad_line!r}")

    for bad_variant in ("unknown", ""):
        try:
            campaigns.render_sentence(sentence, variant=bad_variant)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted unsupported render variant {bad_variant!r}")


def _cst_parser_and_sentence_verification_controls() -> None:
    sentence = ("MODULE", "IDENT", "SEMICOLON", "PUBLIC", "NAT", "IDENT", "LPAREN", "RPAREN", "FATARROW", "DECIMAL", "SEMICOLON", "EOF")
    cst_text = (
        "Ready!\n"
        "ACCEPT\n"
        "[file:\n"
        "  MODULE\n"
        "  [name: IDENT]\n"
        "  SEMICOLON\n"
        "  [nonempty_list(declaration):\n"
        "    [declaration:\n"
        "      PUBLIC\n"
        "      [option(CONST):]\n"
        "      [value_type: NAT]\n"
        "      [name: IDENT]\n"
        "      [declaration_tail:\n"
        "        LPAREN\n"
        "        [separated_or_terminated_list(COMMA,parameter):]\n"
        "        RPAREN\n"
        "        [function_body: FATARROW [expression: DECIMAL] SEMICOLON]\n"
        "      ]\n"
        "    ]\n"
        "  ]\n"
        "]\n"
        "REJECT\n"
    )
    parsed = campaigns.parse_interpreter_cst(cst_text)
    ensure(len(parsed) == 2 and parsed[0] is not None and parsed[1] is None, "failed to parse ACCEPT + REJECT batch")
    campaigns.verify_cst_against_sentence(parsed[0], sentence)

    for bad_cst, expected in (
        (None, "rejected"),
        (campaigns.CstNode("surface_file", ("MODULE",)), "root symbol"),
        (campaigns.CstNode("file", ("MODULE", "IDENT")), "leaf terminals"),
    ):
        try:
            campaigns.verify_cst_against_sentence(bad_cst, sentence)
        except ValueError as error:
            ensure(expected in str(error), f"unexpected CST verification message: {error}")
        else:
            raise AssertionError(f"invalid CST {bad_cst!r} passed verification")

    for malformed in (
        "ACCEPT\n",
        "Ready!\nACCEPT\n",
        "Ready!\nACCEPT\n[file: MODULE\n",
        "Ready!\nACCEPT\n[: MODULE]\n",
        "Ready!\nUNKNOWN\n",
        "Ready!\nACCEPT\n" + ("[a:" * (campaigns.MAX_SYNTAX_DEPTH * 2 + 2)) + (" ]" * (campaigns.MAX_SYNTAX_DEPTH * 2 + 2)),
    ):
        try:
            campaigns.parse_interpreter_cst(malformed)
        except ValueError:
            pass
        else:
            raise AssertionError(f"malformed CST output accepted: {malformed[:40]!r}")


def _independent_oracle_and_refusal_controls() -> None:
    precedence_src = b"module M; public Nat F() { return 1 + 2 * 3; }"
    ensure(
        campaigns.IndependentPureAstOracle.parse(precedence_src)["ast"] == vela_parser._precedence_oracle(),
        "IndependentPureAstOracle disagreed with parser._precedence_oracle()",
    )

    repo_root = TOOLS.parent
    for rel in ("examples/pure.vela", "examples/constants.vela", "examples/expressions.vela"):
        raw = (repo_root / rel).read_bytes()
        oracle_env = campaigns.IndependentPureAstOracle.parse(raw)
        vela_parser._validate_tree(oracle_env["ast"], raw)
        ensure(
            vela.translate_ast(raw, oracle_env) == vela.translate(raw),
            f"IndependentPureAstOracle translation disagreed with vela.translate on {rel}",
        )

    complex_source = (
        b"// UTF-8 comment \xc3\xa9\r\n"
        b"module Complex;\r\n"
        b"public const Nat Base = 10 - 3 - 2;\r\n"
        b"public Nat Step(Nat value) => value + Base;\r\n"
        b"public Nat Compute(const Nat step, bool flag,) {\r\n"
        b"  const bool LocalConst = !false && true || false;\r\n"
        b"  let Nat total = (step + Base) * 2 / 1 % 3;\r\n"
        b"  if (flag == LocalConst) {\r\n"
        b"    return Step(value: total,);\r\n"
        b"  } else {\r\n"
        b"    return 0;\r\n"
        b"  }\r\n"
        b"}\r\n"
    )
    complex_env = campaigns.IndependentPureAstOracle.parse(complex_source)
    vela_parser._validate_tree(complex_env["ast"], complex_source)
    ensure(
        vela.translate_ast(complex_source, complex_env) == vela.translate(complex_source),
        "IndependentPureAstOracle disagreed on multi-declaration precedence/trailing-comma module",
    )

    refusal_cases: tuple[tuple[bytes, str, int, int, str], ...] = (
        (
            b"module M;\npublic Nat F() {\n  Nat x = 1;\n  return x;\n}\n",
            "syntax",
            3,
            3,
            "local declaration requires 'let' or 'var' before its type",
        ),
        (
            b"module M;\npublic const const Nat K = 1;\n",
            "syntax",
            2,
            14,
            "unexpected token",
        ),
        (
            b"module M;\npublic const K = 1;\n",
            "syntax",
            2,
            14,
            "unexpected token",
        ),
        (
            b"module M;\npublic Nat F(const const Nat x) => x;\n",
            "syntax",
            2,
            20,
            "unexpected token",
        ),
        (
            b"module M;\npublic bool F() => 1 == 2 <= 3;\n",
            "syntax",
            2,
            27,
            "unexpected token",
        ),
        (
            b"module M;\npublic Nat F() {\n  var x = 1;\n  return x;\n}\n",
            "unsupported",
            3,
            3,
            "'var' declares a mutable binding",
        ),
        (
            b"module M;\npublic Bool F() => true;\n",
            "unsupported",
            2,
            8,
            "outside the pure prototype",
        ),
        (
            b"module M;\npublic Int F() => 1;\n",
            "syntax",
            2,
            8,
            "unexpected token",
        ),
        (
            b"module M;\npublic Nat F() => " + b"9" * (MAX_LITERAL_DIGITS + 1) + b";\n",
            "limit",
            2,
            19,
            "digits",
        ),
        (
            b"module M;\npublic Nat F() => "
            + b"(" * (campaigns.MAX_DELIMITER_DEPTH + 1)
            + b"1"
            + b")" * (campaigns.MAX_DELIMITER_DEPTH + 1)
            + b";\n",
            "limit",
            2,
            275,
            "delimiter nesting",
        ),
        (
            b"module M;\npublic Nat F() {\n"
            + b"".join(f"  let x_{i} = 1;\n".encode() for i in range(65))
            + b"  return 0;\n}\n",
            "limit",
            2,
            16,
            "block exceeds 64 bindings",
        ),
        (
            b" " * (MAX_SOURCE_BYTES + 1),
            "limit",
            1,
            1,
            "exceeds 65536 bytes",
        ),
    )
    for raw, kind, line, col, snippet in refusal_cases:
        try:
            campaigns.IndependentPureAstOracle.parse(raw)
        except VelaError as error:
            ensure(
                (error.kind, error.line, error.column) == (kind, line, col) and snippet in error.message,
                f"oracle refusal mismatch for {snippet!r}: got {(error.kind, error.line, error.column, error.message)}",
            )
        else:
            raise AssertionError(f"oracle accepted refusal case {snippet!r}")


def _seeded_faults_shrinking_and_replay_controls() -> None:
    stillborn = campaigns.evaluate_seeded_fault("stillborn-mutant")
    ensure(stillborn["status"] == "stillborn", f"expected stillborn status, got {stillborn}")

    expected_reductions = {
        "right-associative-subtraction-or-division-action": (35, 16),
        "trailing-comma-span-or-arity-corruption": (34, 15),
        "expression-body-excludes-arrow-or-semicolon-span": (29, 14),
    }
    for fault in campaigns.SEEDED_FAULTS:
        verdict = campaigns.evaluate_seeded_fault(fault)
        ensure(verdict["status"] == "killed", f"seeded fault {fault} was not killed: {verdict}")
        ensure(
            verdict["held_out"] is (fault == campaigns.HELD_OUT_FAULT),
            f"held_out flag mismatch for {fault}",
        )
        exp_init, exp_shrunk = expected_reductions[fault]
        ensure(
            (verdict["initial_tokens"], verdict["shrunk_tokens"]) == (exp_init, exp_shrunk),
            f"unexpected shrink counts for {fault}: {(verdict['initial_tokens'], verdict['shrunk_tokens'])}",
        )
        replay = cast("dict[str, object]", verdict["shrunk_replay"])
        replayed = campaigns.replay_sentence_case(replay)
        ensure(replayed["status"] == "accepted", f"shrunk replay failed on unmutated oracle: {replayed}")

        # Verify the shrunk sentence still triggers the seeded fault:
        shrunk_terminals = tuple(cast("list[str]", replay["terminals"]))
        try:
            campaigns.verify_sentence_against_oracle(shrunk_terminals, fault_name=fault)
        except campaigns.CampaignObservationError:
            pass
        else:
            raise AssertionError(f"shrunk replay sentence no longer kills {fault}")

        # Tampered replay digest must fail closed:
        tampered = {**replay, "source_sha256": "0" * 64}
        try:
            campaigns.replay_sentence_case(tampered)
        except ValueError as error:
            ensure("digest" in str(error), f"unexpected tamper error: {error}")
        else:
            raise AssertionError("tampered replay digest accepted")

    survived = campaigns.evaluate_seeded_fault(
        campaigns.HELD_OUT_FAULT,
        runner=lambda _sent: None,
    )
    ensure(survived["status"] == "survived", f"no-op runner did not report survived: {survived}")


def _campaign_freshness_and_cli_controls() -> None:
    sample_sentence = (
        "MODULE",
        "IDENT",
        "SEMICOLON",
        "PUBLIC",
        "NAT",
        "IDENT",
        "LPAREN",
        "RPAREN",
        "FATARROW",
        "DECIMAL",
        "SEMICOLON",
        "EOF",
    )
    sample_cst = campaigns.CstNode("file", sample_sentence[:-1])

    with tempfile.TemporaryDirectory(prefix="vela-syntax-campaigns-") as temporary:
        root = Path(temporary)
        directory = root / "build"
        directory.mkdir()
        inputs = {"consumer": "original"}
        menhir_bytes = b"locked-menhir-binary"
        menhir_hash = hashlib.sha256(menhir_bytes).hexdigest()
        menhir_path = directory / "menhir"
        menhir_path.write_bytes(menhir_bytes)
        toolchain = {"compiler": "original", "binary_sha256": {"menhir": menhir_hash}}

        for mode in ("inputs", "toolchain", "output", "negative-cst", "none"):
            for name in (*vela_parser.GENERATED, "vela-parser"):
                (directory / name).write_bytes(b"original")
            outputs = {
                name: hashlib.sha256(b"original").hexdigest()
                for name in (*vela_parser.GENERATED, "vela-parser")
            }
            receipt = {
                "directory": str(directory),
                "toolchain": toolchain,
                "generated_sha256": outputs,
            }
            latest = root / "syntax-campaigns.json"
            latest.write_text('{"status":"qualified","stale":true}', encoding="utf-8")

            def fake_interpret(
                _menhir: Path,
                _grammar: Path,
                lines: list[str],
                current_mode: str = mode,
            ) -> list[campaigns.CstNode | None]:
                if current_mode == "output":
                    (directory / "parser.ml").write_bytes(b"changed")
                if current_mode == "negative-cst":
                    return [sample_cst for _ in lines]
                return [sample_cst, sample_cst, None, None, None]

            with (
                patch.object(campaigns.vela_parser, "_work_root", return_value=root),
                patch.object(
                    campaigns.vela_migration,
                    "qualify",
                    return_value={"status": "agreed", "differences": [], "build": receipt},
                ),
                patch.object(campaigns, "_menhir_binary", return_value=menhir_path),
                patch.object(campaigns, "_generate_menhir_sentence", return_value=sample_sentence),
                patch.object(campaigns, "_interpret_menhir_sentences", side_effect=fake_interpret),
                patch.object(
                    campaigns.vela_parser,
                    "parse_source",
                    side_effect=lambda _compiled, raw: campaigns.IndependentPureAstOracle.parse(raw),
                ),
                patch.object(
                    campaigns,
                    "_inputs",
                    side_effect=[inputs, {"consumer": "changed"}] if mode == "inputs" else [inputs, inputs],
                ),
                patch.object(
                    campaigns.vela_parser,
                    "_toolchain",
                    return_value={"compiler": "changed"} if mode == "toolchain" else toolchain,
                ),
            ):
                try:
                    report = campaigns.qualify(root, seed_start=100, count=2, goal_length=20)
                except ValueError:
                    ensure(
                        mode != "none" and not latest.exists(),
                        f"stale syntax-campaigns receipt survived {mode} failure",
                    )
                else:
                    ensure(mode == "none", f"corrupted mode {mode} unexpectedly qualified")
                    ensure(
                        report["status"] == "qualified"
                        and report["checked_parser"] is False
                        and report["second_grammar_introduced"] is False
                        and report["menhir_runtime_linked"] is False,
                        "qualified campaign report flags violated boundary invariants",
                    )
                    ensure(
                        json.loads(latest.read_text(encoding="utf-8")) == report,
                        "written syntax-campaigns.json differs from returned report",
                    )

    with (
        redirect_stdout(out := StringIO()),
        redirect_stderr(err := StringIO()),
        patch.object(
            cli.vela_syntax_campaigns,
            "qualify",
            return_value={"status": "qualified", "scope": "vela-menhir-generated-syntax-campaigns"},
        ) as mocked_qualify,
    ):
        code = cli.main(["syntax-campaigns", "--seed-start", "42", "--count", "8", "--goal-length", "24"])
    ensure(code == 0 and not err.getvalue(), f"CLI syntax-campaigns failed: {err.getvalue()}")
    ensure(
        json.loads(out.getvalue())["status"] == "qualified",
        "CLI syntax-campaigns output lost status",
    )
    mocked_qualify.assert_called_once()

    for bad_args in (
        {"count": 0},
        {"count": campaigns.MAX_SENTENCE_TOKENS + 1},
        {"goal_length": 0},
        {"goal_length": campaigns.MAX_SENTENCE_TOKENS + 1},
    ):
        try:
            campaigns.qualify(TOOLS.parent, **bad_args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"out-of-range campaign args {bad_args} were accepted")

    with patch.object(
        campaigns.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired("menhir", campaigns.PROCESS_TIMEOUT_SECONDS),
    ):
        try:
            campaigns._generate_menhir_sentence(Path("menhir"), Path("parser.mly"), 1, 20)
        except RuntimeError as error:
            ensure("exceeded" in str(error), f"missing timeout message: {error}")
        else:
            raise AssertionError("timed-out menhir --random-sentence was accepted")


def cases() -> list[Case]:
    return [
        Case("renderer-and-token-payload-controls", _renderer_and_token_payload_controls),
        Case("cst-parser-and-sentence-verification-controls", _cst_parser_and_sentence_verification_controls),
        Case("independent-oracle-and-refusal-controls", _independent_oracle_and_refusal_controls),
        Case("seeded-faults-shrinking-and-replay-controls", _seeded_faults_shrinking_and_replay_controls),
        Case("campaign-freshness-and-cli-controls", _campaign_freshness_and_cli_controls),
    ]
