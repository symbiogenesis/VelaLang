# SPDX-License-Identifier: Apache-2.0
"""Generate Vela syntax assets or qualify pinned independent highlighting consumers."""

import argparse
import json
import sys
from pathlib import Path

from toolchain import highlight, highlight_qualification
from toolchain.atomic import atomic_path


def _check(root: Path) -> None:
    findings = highlight_qualification.check_generated(root)
    if findings:
        raise ValueError("; ".join(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(suggest_on_error=True, description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="refuse generated grammar/query drift without changing source")
    commands.add_parser("generate", help="explicitly refresh secondary editor assets from Menhir")
    qualifier = commands.add_parser("qualify", help="exercise exact-pinned syntax consumers in an isolated build")
    for name in ("tree-sitter", "textmate-package", "oniguruma-package", "node", "output"):
        qualifier.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    try:
        if args.command == "generate":
            for name, content in highlight.generated_assets(root).items():
                path = root / highlight.ASSETS / name
                path.parent.mkdir(parents=True, exist_ok=True)
                with atomic_path(path) as pending:
                    pending.write_text(content, encoding="utf-8", newline="")
        elif args.command == "check":
            _check(root)
        else:
            output = highlight_qualification.output_path(root, args.output, args.tree_sitter,
                                                        args.textmate_package, args.oniguruma_package, args.node)
            result = highlight_qualification.qualify(root, args.tree_sitter, args.textmate_package,
                                                     args.oniguruma_package, args.node)
            with atomic_path(output) as pending:
                pending.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
                highlight_qualification.recheck(root, result, args.tree_sitter, args.textmate_package,
                                               args.oniguruma_package, args.node)
            print(f"syntax assets qualified: {output}")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"vela-highlight: {error}", file=sys.stderr)
        return 1
    return 0
