# SPDX-License-Identifier: Apache-2.0
"""Prepare explicitly selected files with the locked formatters, without builds."""

import argparse
import subprocess
import sys
import sysconfig
from pathlib import Path

from toolchain import corpus, markdown, pyversion, toolenv
from toolchain.cli import Table, dispatch


def selected(root: Path, names: list[str], scope: str) -> list[str]:
    """Resolve ordinary files inside the selected owner; refuse aliasing and escapes."""
    if not names or scope not in {"python", "markdown"}:
        raise ValueError("preparation requires explicit files and a known owner")
    base = root.resolve()
    result: list[str] = []
    for name in names:
        path = Path(name)
        if not path.is_absolute():
            path = base / path
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(base) or not path.is_file() or path.is_symlink():
            raise ValueError(f"not an ordinary contained file: {name}")
        relative = resolved.relative_to(base)
        if path.absolute() != resolved:
            raise ValueError(f"symlink or ambiguous path: {name}")
        if scope == "python":
            if relative.parts[0] != "tools" or relative.suffix != ".py":
                raise ValueError(f"Python preparation requires tools/*.py: {name}")
        elif relative.suffix != ".md":
            raise ValueError(f"Markdown preparation requires *.md files: {name}")
        spelling = relative.as_posix()
        if spelling in result:
            raise ValueError(f"duplicate selected file: {name}")
        result.append(spelling)
    return result


def python_prepare(root: Path, names: list[str], *, check: bool) -> int:
    """Only import ordering is automatically rewritten; type acceptance remains separate."""
    paths = selected(root, names, "python")
    executable = Path(sysconfig.get_path("scripts")) / ("ruff.exe" if sys.platform == "win32" else "ruff")
    pin = toolenv.checker_pins(root)["ruff"]
    tools = root / "tools"
    version = subprocess.run([str(executable), "--version"], cwd=tools,
                             capture_output=True, text=True, check=True, timeout=30)
    if version.stdout.strip() != f"ruff {pin}":
        raise ValueError("preparation requires the locked environment's exact Ruff edition")
    argv = [str(executable), "check", "--config", str(root / "tools" / "ruff.toml"),
            "--select", "I", "--no-cache", "--no-respect-gitignore",
            "--target-version", "py" + pyversion.supported_minor(root).replace(".", "")]
    if not check:
        argv.append("--fix")
    return subprocess.run([*argv, "--", *(str(root / path) for path in paths)],
                          cwd=tools, check=False, timeout=120).returncode


def markdown_prepare(root: Path, names: list[str], *, check: bool) -> int:
    """Format or check explicitly selected Markdown files with the locked rumdl edition."""
    paths = selected(root, names, "markdown")
    executable = toolenv.ensure_rumdl(root)
    if executable is None:
        raise ValueError("preparation requires the locked environment's rumdl executable")
    pin = toolenv.checker_pins(root)["rumdl"]
    version = subprocess.run([str(executable), "--version"], cwd=root,
                             capture_output=True, text=True, check=True, timeout=30)
    if version.stdout.strip() != f"rumdl {pin}":
        raise ValueError("preparation requires the locked environment's exact rumdl edition")
    cfg_findings = markdown.settings_findings(root / markdown.CONFIG)
    if cfg_findings:
        raise ValueError("; ".join(cfg_findings))
    argv = [str(executable), "check", "--no-cache", "--config", str(root / markdown.CONFIG)]
    if not check:
        argv.append("--fix")
    return subprocess.run([*argv, "--", *(str(root / path) for path in paths)],
                          cwd=root, check=False, timeout=120).returncode


def run(args: argparse.Namespace) -> int:
    try:
        root = corpus.find_root()
        code = (python_prepare(root, args.path, check=args.check) if args.command == "python"
                else markdown_prepare(root, args.path, check=args.check))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"FAIL prepare: {error}")
        return 1
    print("Review selected-file diffs; full acceptance remains with hosted CI.")
    return code


TABLE: Table = {"python": (run, "locked Ruff import ordering on selected Python files"),
                "markdown": (run, "locked rumdl formatting on selected Markdown files")}


def flags(_name: str, parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", action="append", required=True, help="selected file; repeatable")
    parser.add_argument("--check", action="store_true", help="report findings without rewriting")


def main(argv: list[str] | None = None) -> int:
    return dispatch(__doc__, TABLE, argv, flags, prog="run.py prepare")
