# SPDX-License-Identifier: Apache-2.0
"""Closed-world Markdown validation with the pinned rumdl linter and schema-checked policy."""

import re
import subprocess
import tempfile
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath

from vela import corpus, schema, toolenv
from vela.report import Reporter

CONFIG = "tools/rumdl.toml"
SCHEMA = "tools/rumdl-config.schema.json"
ADMITTED_DISABLED = frozenset({"MD013", "MD063", "MD082", "MD093"})
TIMEOUT = 120

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "rumdl-config.schema.json"
_DIAGNOSTIC_RE = re.compile(r"^(.+:\d+:\d+): \[(MD\d{3})\] (.+?)(?: \[\*\])?$")
_SUPPRESSION_RE = re.compile(
    r"<!--\s*(?:markdownlint|rumdl)-(?:disable|ignore|capture)\b", re.IGNORECASE
)


def settings_findings(config: Path) -> list[str]:
    """Hold tools/rumdl.toml to its reviewed schema and exact disabled-rule set."""
    name = config.name
    try:
        with config.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as err:
        return [f"{name} could not be read ({err}); the Markdown gate requires its reviewed configuration"]
    try:
        schema.validate(_SCHEMA_PATH, data)
    except ValueError as err:
        return [f"{name}: {err}"]
    global_cfg = data.get("global", {})
    disabled = global_cfg.get("disable", [])
    if len(disabled) != len(set(disabled)) or set(disabled) != ADMITTED_DISABLED:
        wanted = ", ".join(sorted(ADMITTED_DISABLED))
        return [f"{name}: global.disable must be the exact reviewed set [{wanted}]"]
    return []


def suppression_findings(documents: Iterable[corpus.Document]) -> list[str]:
    """Refuse inline Markdown linter suppression comments outside fenced code blocks."""
    findings: list[str] = []
    for doc in documents:
        for index, line in enumerate(doc.lines):
            if not doc.fenced[index] and _SUPPRESSION_RE.search(line):
                findings.append(
                    f"{doc.name}:{index + 1}: inline Markdown linter suppression comment is refused"
                )
    return findings


def _probe_version(executable: Path) -> str:
    try:
        done = subprocess.run(
            [str(executable), "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as err:
        return f"unreachable ({err})"
    words = done.stdout.split()
    return words[1] if done.returncode == 0 and len(words) >= 2 else "unknown"


def _parse_diagnostics(output: str) -> list[str]:
    findings: list[str] = []
    for raw_line in output.splitlines():
        if match := _DIAGNOSTIC_RE.match(raw_line):
            location, code, message = match.groups()
            findings.append(f"{location}: {code} {message}")
    return findings


def batch_findings(
    root: Path,
    documents: Sequence[corpus.Document],
    tracked: Iterable[str],
    *,
    config: Path | None = None,
) -> list[str]:
    """Run rumdl in closed-world stdin-batch mode over the supplied corpus."""
    if not documents:
        return ["the index supplies no Markdown documents to validate"]
    try:
        pin = toolenv.checker_pins(root)["rumdl"]
        executable = toolenv.ensure_rumdl(root)
    except (OSError, TypeError, ValueError, KeyError) as err:
        return [f"cannot resolve pinned rumdl executable: {err}"]
    if executable is None:
        return [
            f"rumdl {pin} is not installed in the tools environment; "
            "run a command through tools/run.py to synchronize tools/uv.lock"
        ]
    installed = _probe_version(executable)
    if installed != pin:
        return [
            f"rumdl {installed} is installed and this tree pins {pin}; "
            "run a command through tools/run.py to synchronize tools/uv.lock"
        ]
    cfg = (root / CONFIG) if config is None else config
    for doc in documents:
        if "\0" in doc.name or "\0" in doc.raw:
            return [f"{doc.name}: NUL byte is not permitted in Markdown batch input"]
    tracked_list = list(tracked)
    directories = {
        parent.as_posix() + "/"
        for path in tracked_list
        for parent in PurePosixPath(path).parents
        if parent.as_posix() != "."
    }
    non_md_targets = sorted(
        {path for path in tracked_list if not path.endswith(".md")} | directories
    )
    stdin_payload = b"".join(
        doc.name.encode("utf-8") + b"\0" + doc.raw.encode("utf-8") + b"\0"
        for doc in documents
    )
    targets_payload = b"".join(target.encode("utf-8") + b"\0" for target in non_md_targets)
    with tempfile.NamedTemporaryFile(prefix="vela-rumdl-targets-", delete=False) as handle:
        handle.write(targets_payload)
        targets_path = Path(handle.name)
    try:
        done = subprocess.run(
            [
                str(executable),
                "check",
                "--no-cache",
                "--config",
                str(cfg),
                "--stdin-batch",
                "--stdin-batch-closed-world",
                "--stdin-batch-targets",
                str(targets_path),
            ],
            cwd=root,
            input=stdin_payload,
            capture_output=True,
            check=False,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as err:
        return [f"rumdl failed to execute: {err}"]
    finally:
        targets_path.unlink(missing_ok=True)
    stdout = done.stdout.decode("utf-8", errors="replace")
    stderr = done.stderr.decode("utf-8", errors="replace")
    findings = _parse_diagnostics(stdout)
    if done.returncode not in (0, 1):
        detail = (stderr.strip() or stdout.strip())[-200:]
        findings.append(f"rumdl exited {done.returncode}: {detail}")
    elif done.returncode != 0 and not findings:
        detail = (stderr.strip() or stdout.strip())[-200:]
        findings.append(f"rumdl exited {done.returncode} and no diagnostic was recognized: {detail}")
    return findings


def run(root: Path) -> Reporter:
    """Validate tools/rumdl.toml, bookmark hygiene, and closed-world Markdown rules."""
    rep = Reporter()
    rep.line("=== markdown ===")
    cfg_path = root / CONFIG
    rep.report(
        "rumdl-config",
        "configuration finding(s):",
        settings_findings(cfg_path),
        "tools/rumdl.toml satisfies the reviewed schema and rule policy",
    )
    try:
        loaded = corpus.load(root)
    except (OSError, ValueError, RuntimeError) as err:
        rep.report("markdown", "corpus error(s):", [f"cannot read the indexed Markdown corpus: {err}"])
        return rep
    anchor_findings = [*loaded.buried, *loaded.declared_twice, *suppression_findings(loaded.docs)]
    rep.report(
        "markdown-anchors",
        "bookmark or suppression finding(s):",
        anchor_findings,
        "every bookmark is unique and unfenced, with no inline linter suppressions",
    )
    lint_findings = batch_findings(root, loaded.docs, loaded.tracked, config=cfg_path)
    rep.report(
        "rumdl",
        "Markdown lint finding(s):",
        lint_findings,
        f"rumdl accepts all {len(loaded.docs)} indexed Markdown document(s) in closed-world mode",
    )
    return rep
