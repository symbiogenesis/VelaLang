# SPDX-License-Identifier: Apache-2.0
"""One bounded pure-prototype check, run by the host language server's worker."""

import hashlib
import json
import sys
from pathlib import Path

from toolchain import MAX_SOURCE_BYTES, VelaError, inspect_source, translate
from toolchain.authoring import format_source
from toolchain.protocol_json import MAX_BODY_BYTES


def worker_command(*args: str) -> list[str]:
    """Build an isolated `-I` command line for the checkout's fixed worker."""
    tools = str(Path(__file__).resolve().parents[1])
    script = (f"import sys; sys.path.insert(0, {tools!r}); "
              "from toolchain.lsp_worker import main; raise SystemExit(main())")
    return [sys.executable, "-I", "-c", script, *args]


def main() -> int:
    source = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
    if sys.argv[1:] == ["--format"]:
        result: dict[str, object] = {"source_sha256": hashlib.sha256(source).hexdigest()}
        try:
            result.update(status="ok", formatted=format_source(source).decode("utf-8"))
        except VelaError as error:
            result.update(status="unavailable", reason=error.kind)
        encoded = json.dumps(result, ensure_ascii=True)
        if len(encoded.encode("utf-8")) > MAX_BODY_BYTES:
            return 1
        print(encoded, end="")
        return 0
    if sys.argv[1:] == ["--inspect"]:
        digest = hashlib.sha256(source).hexdigest()
        try:
            inspection = inspect_source(source)
        except VelaError as error:
            inspection = {"status": "unavailable", "reason": error.kind}
        inspection["source_sha256"] = digest
        encoded = json.dumps(inspection, ensure_ascii=True)
        if len(encoded.encode("utf-8")) > MAX_BODY_BYTES:
            encoded = json.dumps({"status": "unavailable", "reason": "inspection-limit",
                                  "source_sha256": digest})
        print(encoded, end="")
        return 0
    if sys.argv[1:]:
        return 2
    error_data: dict[str, object] | None = None
    try:
        translate(source)
    except VelaError as error:
        error_data = {"kind": error.kind, "line": error.line, "column": error.column,
                      "message": error.message[:4096]}
    print(json.dumps(error_data, ensure_ascii=True))
    return 0
