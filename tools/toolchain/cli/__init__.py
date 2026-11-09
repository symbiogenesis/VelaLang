# SPDX-License-Identifier: Apache-2.0
"""Command-module dispatch and argument helpers.

[toolchain/commands.py](../commands.py) registers each command's module and lane, and
[run.py](../../run.py) imports only the requested command module so `run.py <name> --help`
displays that command's own help.
"""

import argparse
from collections.abc import Callable

# Subcommand handler and dispatch table mapping each subcommand name to its
# handler and `--help` summary.
type Handler = Callable[[argparse.Namespace], int]
type Table = dict[str, tuple[Handler, str]]


def dispatch(doc: str | None, table: Table, argv: list[str] | None,
             flags: Callable[[str, argparse.ArgumentParser], None] | None = None,
             prog: str | None = None) -> int:
    """Parse a command's subcommands and invoke the selected handler.

    If provided, `flags(name, subparser)` registers subcommand-specific arguments as
    each subparser is built.
    """
    parser = argparse.ArgumentParser(
        suggest_on_error=True, prog=prog, description=(doc or "").splitlines()[0] if bool(doc) else None)
    subs = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in table.items():
        sub = subs.add_parser(name, suggest_on_error=True, help=help_text)
        if flags is not None:
            flags(name, sub)
    args = parser.parse_args(argv)
    handler, _ = table[args.command]
    return handler(args)
