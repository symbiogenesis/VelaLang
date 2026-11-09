# SPDX-License-Identifier: Apache-2.0
"""Repository hygiene, licensing, source-reference, and plan-summary gate."""

import sys

from toolchain import checks, corpus, estimates


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(
            "usage: run.py check [--fix]\n\n"
            "Enforce repository hygiene, licensing, source-comment links, and the plan summary.\n"
            "--fix refreshes only the generated plan-summary table before checking."
        )
        return 0
    if args not in ([], ["--fix"]):
        print(f"unsupported run.py check arguments: {' '.join(args)}", file=sys.stderr)
        return 2
    root = corpus.find_root()
    if args == ["--fix"]:
        try:
            path = root / "PLAN.md"
            text = path.read_text(encoding="utf-8")
            updated = estimates.update_summary(text)
            if updated != text:
                path.write_text(updated, encoding="utf-8", newline="\n")
                print("Updated PLAN.md's generated estimate summary.")
        except (OSError, ValueError) as error:
            print(f"FAIL estimates: {error}", file=sys.stderr)
            return 1
    rep = checks.run(root)
    if rep.findings:
        rep.line(f"{rep.findings} finding(s).")
    else:
        rep.line("the repository holds to its hygiene, licensing, and plan-summary contracts.")
    print("\n".join(rep.out))
    return 1 if rep.findings else 0
