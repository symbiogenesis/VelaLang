#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The one way into the VelaLang repository's tools.

    python tools/run.py                      run the behavioral test suite
    python tools/run.py test                 run the behavioral test suite
    python tools/run.py vela --help          pure Vela CLI, formatter, linter and Gallina emitter
    python tools/run.py vela-lsp --help      pure Vela language server over stdio
    python tools/run.py vela-playground      unified Vela browser playground [wsl]
    python tools/run.py vela-parser --help   Menhir parser, dependent elaborator and Rocq replay [wsl]
"""

import io
import shlex
import subprocess
import sys
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vela import pyversion

if __name__ == "__main__":
    try:
        pyversion.require_supported(Path(__file__).resolve().parents[1])
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error

from vela import corpus as corpus_mod
from vela import toolenv
from vela.commands import BY_NAME, COMMANDS, Command

type Main = Callable[[list[str]], int]

GUEST = ("wsl", "-u", "root", "-e", "python3", "tools/run.py")


def _utf8_output() -> None:
    """Make redirected output obey UTF-8 encoding, on either lane."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def _usage() -> str:
    """Every command, what it decides, and the lane it decides it in."""
    width = max(len(command.name) for command in COMMANDS)
    lines = [__doc__.split("\n\n")[0], "", "commands:"]
    for command in COMMANDS:
        lane = "" if command.lane == "host" else "  [wsl]"
        lines.append(f"  {command.name:<{width}}  {command.decides}{lane}")
    lines += ["",
              "`run.py <command> --help` is that command's own help.",
              "A [wsl] command asked for here is re-launched in the guest."]
    return "\n".join(lines)


def _in_guest(root: Path, command: Command, argv: list[str]) -> int:
    """Re-launch a guest command through WSL, from the repository root."""
    print(f"== {command.name} runs in WSL; re-launching there", file=sys.stderr, flush=True)
    try:
        return subprocess.run([*GUEST, command.name, *argv],
                              cwd=root, check=False).returncode
    except OSError as err:
        retry = shlex.join(["python3", "tools/run.py", command.name, *argv])
        print(f"the guest lane could not be reached: {err}\n"
              f"run it inside WSL as: {retry}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    _utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("help", "--help", "-h"):
        print(_usage())
        return 0

    name, rest = ("test", args) if not args or args[0].startswith("-") else (args[0], args[1:])

    command = BY_NAME.get(name)
    if command is None:
        print(f"no such command: {name}\n\n{_usage()}", file=sys.stderr)
        return 2

    root = corpus_mod.find_root()
    if command.guest_only(rest) and sys.platform == "win32":
        return _in_guest(root, command, rest)

    if (code := toolenv.bootstrap(root, args)) is not None:
        return code

    module = import_module(command.module)
    return cast("Main", module.main)(rest)


if __name__ == "__main__":
    sys.exit(main())
