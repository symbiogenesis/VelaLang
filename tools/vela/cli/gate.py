# SPDX-License-Identifier: Apache-2.0
"""Unified static gate combining check, markdown, and typecheck."""

import sys

from vela import checks, corpus


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print("usage: run.py gate\n\nRun check, markdown, and typecheck in one verdict.")
        return 0
    if args:
        print(f"run.py gate takes no arguments: {' '.join(args)}", file=sys.stderr)
        return 2
    rep = checks.run_gate(corpus.find_root())
    if rep.findings:
        rep.line(f"{rep.findings} finding(s).")
    else:
        rep.line("every repository, Markdown, and Python static gate passed.")
    print("\n".join(rep.out))
    return 1 if rep.findings else 0
