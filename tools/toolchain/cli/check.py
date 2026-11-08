# SPDX-License-Identifier: Apache-2.0
"""Repository hygiene, REUSE v3.3, EditorConfig, glyph, and source-reference gate."""

import sys

from toolchain import checks, corpus


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(
            "usage: run.py check\n\n"
            "Enforce REUSE v3.3, SPDX headers, EditorConfig, glyph hygiene, and source-comment links."
        )
        return 0
    if args:
        print(f"run.py check takes no arguments: {' '.join(args)}", file=sys.stderr)
        return 2
    rep = checks.run(corpus.find_root())
    if rep.findings:
        rep.line(f"{rep.findings} finding(s).")
    else:
        rep.line("the repository holds to its hygiene and licensing contracts.")
    print("\n".join(rep.out))
    return 1 if rep.findings else 0
