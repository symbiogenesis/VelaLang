# SPDX-License-Identifier: Apache-2.0
"""Closed-world Markdown lint and link gate."""

import sys

from toolchain import corpus, markdown


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print("usage: run.py markdown\n\nValidate tools/rumdl.toml and lint the indexed Markdown corpus.")
        return 0
    if args:
        print(f"run.py markdown takes no arguments: {' '.join(args)}", file=sys.stderr)
        return 2
    rep = markdown.run(corpus.find_root())
    if rep.findings:
        rep.line(f"{rep.findings} finding(s).")
    else:
        rep.line("the Markdown corpus holds to its contract.")
    print("\n".join(rep.out))
    return 1 if rep.findings else 0
