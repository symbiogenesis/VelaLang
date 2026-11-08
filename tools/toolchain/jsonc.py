# SPDX-License-Identifier: Apache-2.0
"""JSON-with-comments (JSONC) parser supporting `//`, `/* */`, and trailing commas.

Replaces comments and trailing commas outside string literals with spaces so
line and column offsets in `json.loads` diagnostics match the original input.
"""

import json
import re
from pathlib import Path
from typing import cast

# Recursive JSON value type returned by `load()`.
type Json = dict[str, Json] | list[Json] | str | int | float | bool | None


# Strings include an unterminated final token, so comment syntax inside one stays
# untouched and json.loads reports the original malformed string. Escapes consume
# exactly one following character, including a newline in invalid input.
_STRING = r'"[^"\\]*(?:\\[\s\S][^"\\]*)*(?:"|\\?$)'
_COMMENTS = re.compile(_STRING + r"|//[^\r\n]*|/\*(?:/|[\s\S]*?(?:\*/|$))")
_TRAILING_COMMAS = re.compile(_STRING + r"|,(?=\s*[}\]])")


def _blank_comment(match: re.Match[str]) -> str:
    token = match.group()
    return token if token.startswith('"') else "\n".join(" " * len(line) for line in token.split("\n"))


def strip_comments(text: str) -> str:
    """Blank comments and trailing commas while retaining every source offset."""
    uncommented = _COMMENTS.sub(_blank_comment, text)
    return _TRAILING_COMMAS.sub(lambda match: " " if match.group() == "," else match.group(),
                                uncommented)


def load(path: str | Path) -> Json:
    # `json.loads` is typed `Any`, and `Json` is by construction everything it can
    # return, so this narrows an untyped boundary rather than asserting past one.
    return cast("Json", json.loads(strip_comments(Path(path).read_text(encoding="utf-8"))))
