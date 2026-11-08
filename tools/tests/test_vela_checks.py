# SPDX-License-Identifier: Apache-2.0
"""Behavioral controls for Markdown, REUSE/SPDX, EditorConfig, glyph, and source-reference gates."""

import tempfile
from pathlib import Path

from tests.harness import Case, ensure
from vela import checks, corpus, markdown
from vela.cli import prepare

INDEPENDENT_CASES = True


def _rumdl_settings_policy() -> None:
    root = corpus.find_root()
    committed = root / markdown.CONFIG
    ensure(markdown.settings_findings(committed) == [],
           "the committed tools/rumdl.toml must pass its schema and disabled-rule policy")
    valid_text = committed.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="vela-rumdl-cfg-") as td:
        cfg = Path(td) / "rumdl.toml"
        for mutated in (
            valid_text.replace('"MD013"', '"MD013", "MD001"'),
            valid_text.replace("editorconfig = true", "editorconfig = false"),
            valid_text + '\n[per-file-ignores]\n"README.md" = ["MD001"]\n',
            "[broken\n",
        ):
            cfg.write_text(mutated, encoding="utf-8", newline="\n")
            findings = markdown.settings_findings(cfg)
            ensure(bool(findings), f"invalid rumdl.toml was accepted: {mutated!r}")


def _markdown_suppression_and_batch_controls() -> None:
    root = corpus.find_root()
    fenced_ok = corpus.from_text(
        "# Title\n\n```markdown\n<!-- markdownlint-disable MD001 -->\n```\n",
        "docs/ok.md",
    )
    ensure(markdown.suppression_findings([fenced_ok]) == [],
           "suppression comments inside fenced code blocks must not be refused")
    for comment in ("<!-- markdownlint-disable MD001 -->", "<!-- rumdl-disable MD001 -->"):
        bad_doc = corpus.from_text(f"# Title\n\n{comment}\n", "docs/bad.md")
        ensure(len(markdown.suppression_findings([bad_doc])) == 1,
               f"unfenced suppression comment was not refused: {comment}")

    clean_doc = corpus.from_text(
        "# Heading\n\nSee [tool](tools/run.py) and [self](#heading).\n",
        "README.md",
    )
    ensure(markdown.batch_findings(root, [clean_doc], ["README.md", "tools/run.py"]) == [],
           "clean closed-world Markdown document must pass rumdl batch validation")

    broken_link = corpus.from_text("# Heading\n\nSee [missing](untracked.md).\n", "README.md")
    link_findings = markdown.batch_findings(root, [broken_link], ["README.md"])
    ensure(any("MD057" in item for item in link_findings),
           f"closed-world batch must refuse links to untracked files: {link_findings!r}")

    broken_frag = corpus.from_text("# Heading\n\nSee [missing](#absent).\n", "README.md")
    frag_findings = markdown.batch_findings(root, [broken_frag], ["README.md"])
    ensure(any("MD051" in item for item in frag_findings),
           f"closed-world batch must refuse missing heading fragments: {frag_findings!r}")


def _spdx_marks_controls() -> None:
    tag = "SPDX-License-" + "Identifier: Apache-2.0"
    bad_tag = "SPDX-License-" + "Identifier: MIT"
    copyright_doc = corpus.from_text(
        f"# Copyright\n\n```text\n# {tag}\n```\n",
        "COPYRIGHT.md",
    )
    with tempfile.TemporaryDirectory(prefix="vela-marks-") as td:
        root = Path(td)
        (root / "ok.py").write_text(f"# {tag}\nx = 1\n", encoding="utf-8")
        (root / "ok.ml").write_text(f"(* {tag} *)\n", encoding="utf-8")
        (root / "ok.vela").write_text(f"// {tag}\nmodule M;\n", encoding="utf-8")
        (root / "data.json").write_text("{}\n", encoding="utf-8")
        clean_corpus = corpus.Corpus(
            root, [copyright_doc], {}, ["COPYRIGHT.md", "data.json", "ok.ml", "ok.py", "ok.vela"]
        )
        ensure(checks.marks_findings(root, clean_corpus) == [],
               "valid SPDX marks across file kinds must pass")

        (root / "bad.py").write_text(f"# {bad_tag}\n", encoding="utf-8")
        (root / "unknown.xyz").write_text(f"# {tag}\n", encoding="utf-8")
        bad_corpus = corpus.Corpus(
            root, [copyright_doc], {}, ["COPYRIGHT.md", "bad.py", "unknown.xyz"]
        )
        found = checks.marks_findings(root, bad_corpus)
        ensure(len(found) == 2, f"wrong identifier and unknown suffix must both refuse: {found!r}")


def _editorconfig_and_glyph_controls() -> None:
    tag = "SPDX-License-" + "Identifier: Apache-2.0"
    with tempfile.TemporaryDirectory(prefix="vela-ec-") as td:
        root = Path(td)
        (root / ".editorconfig").write_text(
            f"# {tag}\nroot = true\n\n[*]\nend_of_line = lf\n",
            encoding="utf-8",
            newline="\n",
        )
        (root / "clean.py").write_bytes(b"x = 1\n")
        ensure(checks.editorconfig_findings(root, [".editorconfig", "clean.py"]) == [],
               "compliant UTF-8 LF files must pass editorconfig_findings")
        ensure(checks.glyph_findings(root, [".editorconfig", "clean.py"]) == [],
               "compliant files must pass glyph_findings")

        (root / "bom.py").write_bytes(b"\xef\xbb\xbfx = 1\n")
        (root / "crlf.py").write_bytes(b"x = 1\r\n")
        (root / "trail.py").write_bytes(b"x = 1 \n")
        (root / "tab.py").write_bytes(b"\tx = 1\n")
        (root / "double_nl.py").write_bytes(b"x = 1\n\n")
        ec_found = checks.editorconfig_findings(
            root, ["bom.py", "crlf.py", "trail.py", "tab.py", "double_nl.py"]
        )
        ensure(len(ec_found) == 5, f"every EditorConfig violation must be reported: {ec_found!r}")

        (root / "bidi.py").write_text("x = '\u202e'\n", encoding="utf-8", newline="\n")
        (root / "mojibake.py").write_text("# \u00e2\u20ac\u201d\n", encoding="utf-8", newline="\n")
        glyph_found = checks.glyph_findings(root, ["bidi.py", "mojibake.py"])
        ensure(len(glyph_found) == 2, f"bidi and mojibake must both be reported: {glyph_found!r}")


def _source_reference_controls() -> None:
    doc = corpus.from_text("# Guide\n\n## Section One\n\nText.\n", "docs/guide.md")
    with tempfile.TemporaryDirectory(prefix="vela-refs-") as td:
        root = Path(td)
        (root / "docs").mkdir()
        (root / "tools").mkdir()
        (root / "docs" / "guide.md").write_text(doc.raw, encoding="utf-8", newline="\n")
        (root / "tools" / "good.py").write_text(
            '"""See [guide](../docs/guide.md#section-one)."""\n',
            encoding="utf-8",
            newline="\n",
        )
        good_corpus = corpus.Corpus(
            root, [doc], {}, ["docs/guide.md", "tools/good.py"], {"docs/guide.md", "tools/good.py"}
        )
        ensure(checks.source_ref_findings(root, good_corpus) == [],
               "valid relative docstring link and fragment must pass")

        (root / "tools" / "bad.py").write_text(
            '"""See [missing](../docs/missing.md) and [frag](../docs/guide.md#absent)."""\n',
            encoding="utf-8",
            newline="\n",
        )
        bad_corpus = corpus.Corpus(
            root, [doc], {}, ["docs/guide.md", "tools/bad.py"], {"docs/guide.md", "tools/bad.py"}
        )
        found = checks.source_ref_findings(root, bad_corpus)
        ensure(len(found) == 2, f"missing file and missing fragment must both be reported: {found!r}")


def _prepare_selection_controls() -> None:
    root = corpus.find_root()
    ensure(prepare.selected(root, ["tools/run.py"], "python") == ["tools/run.py"],
           "prepare python must accept tools/*.py")
    ensure(prepare.selected(root, ["README.md"], "markdown") == ["README.md"],
           "prepare markdown must accept tracked *.md")
    for scope, bad in (("python", ["README.md"]), ("markdown", ["tools/run.py"]), ("unknown", ["README.md"])):
        try:
            prepare.selected(root, bad, scope)
        except ValueError:
            continue
        raise AssertionError(f"invalid prepare selection accepted: {scope} {bad!r}")


def cases() -> list[Case]:
    return [
        Case("rumdl-settings-schema-and-policy", _rumdl_settings_policy),
        Case("markdown-suppression-and-closed-world-batch", _markdown_suppression_and_batch_controls),
        Case("spdx-marks-across-file-kinds", _spdx_marks_controls),
        Case("editorconfig-and-glyph-hygiene", _editorconfig_and_glyph_controls),
        Case("source-comment-and-docstring-references", _source_reference_controls),
        Case("prepare-python-and-markdown-selection", _prepare_selection_controls),
    ]
