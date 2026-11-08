# SPDX-License-Identifier: Apache-2.0
"""Serve unqualified pure Vela diagnostics and navigation over standard input/output."""

import argparse
import json
import sys
from pathlib import Path

from toolchain import lsp_clients
from toolchain.atomic import atomic_path
from toolchain.lsp import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(suggest_on_error=True, description=__doc__)
    parser.add_argument(
        "--transcript",
        type=Path,
        metavar="FILE",
        help="Write a JSON bidirectional wire transcript on session termination",
    )
    parser.add_argument(
        "--qualify-clients",
        action="store_true",
        help="Run the pinned two-client Neovim and Vim LSP interoperability qualification",
    )
    parser.add_argument(
        "--output",
        type=Path,
        metavar="FILE",
        help="Write the JSON qualification report to FILE instead of standard output",
    )
    args = parser.parse_args(argv)
    if args.qualify_clients:
        if args.transcript is not None:
            parser.error("--transcript cannot be combined with --qualify-clients")
        try:
            report = lsp_clients.qualify_clients()
            serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
            if args.output is not None:
                with atomic_path(args.output) as pending:
                    pending.write_text(serialized, encoding="utf-8", newline="")
            else:
                sys.stdout.buffer.write(serialized.encode("utf-8"))
                sys.stdout.buffer.flush()
        except (OSError, RuntimeError, ValueError) as error:
            print(f"vela-lsp: qualification failed: {error}", file=sys.stderr)
            return 1
        return 0
    if args.output is not None:
        parser.error("--output requires --qualify-clients")
    frames: list[dict[str, object]] | None = [] if args.transcript is not None else None
    exit_code = serve(sys.stdin.buffer, sys.stdout.buffer, transcript=frames)
    if args.transcript is not None and frames is not None:
        try:
            payload = {"exit_code": exit_code, "frames": frames}
            with atomic_path(args.transcript) as pending:
                pending.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                    newline="",
                )
        except OSError as error:
            print(f"vela-lsp: transcript write failed: {str(error)[:256]}", file=sys.stderr)
            return 1
    return exit_code
