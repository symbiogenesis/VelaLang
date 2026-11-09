# SPDX-License-Identifier: Apache-2.0
"""Source-preserving pieces from the existing pure authoring token producer."""

from typing import cast

from toolchain import _tokens
from toolchain.ast import VelaError

MAX_CONCRETE_PARTS = 16_384
TOKEN_KINDS = frozenset({"keyword", "identifier", "decimal", "punctuation"})
TRIVIA_KINDS = frozenset({"whitespace", "line-comment", "documentation-comment"})


def parts(source: bytes) -> list[dict[str, object]]:
    """Partition successful pure source without normalizing spelling or trivia."""
    text = source.decode("utf-8")
    offsets, lines = [0], [0]
    byte_offset, previous_cr = 0, False
    for character in text:
        byte_offset += len(character.encode("utf-8"))
        if character == "\n" and previous_cr:
            offsets[-1] = byte_offset
            previous_cr = False
            continue
        offsets.append(byte_offset)
        if character in "\r\n":
            lines.append(len(offsets) - 1)
        previous_cr = character == "\r"
    result: list[dict[str, object]] = []

    def append(kind: str, first: int, last: int) -> None:
        if len(result) >= MAX_CONCRETE_PARTS:
            raise VelaError("limit", 1, 1, "concrete inspection exceeds piece limit")
        result.append({"kind": kind, "text": source[first:last].decode("utf-8"), "span": [first, last]})

    cursor = 0
    for token in _tokens(source):
        first = len(source) if token.kind == "eof" else offsets[lines[token.line - 1] + token.column - 1]
        while cursor < first:
            last = cursor
            if source[cursor] in b" \t\r\n":
                while last < first and source[last] in b" \t\r\n":
                    last += 1
                kind = "whitespace"
            elif source.startswith(b"//", cursor):
                while last < first and source[last] not in b"\r\n":
                    last += 1
                kind = "documentation-comment" if source.startswith(b"///", cursor) else "line-comment"
            else:
                raise ValueError("pure token producer left uncovered nontrivia source")
            append(kind, cursor, last)
            cursor = last
        if token.kind == "eof":
            break
        last = first + len(token.text.encode("utf-8"))
        if cursor != first or source[first:last].decode("utf-8") != token.text:
            raise ValueError("pure token producer differs from source spelling")
        append({"name": "identifier", "symbol": "punctuation"}.get(token.kind, token.kind), first, last)
        cursor = last
    return result


def validate(source: bytes, value: object) -> list[dict[str, object]]:
    """Check bounded worker pieces and exact contiguous reconstruction before export."""
    if not isinstance(value, list) or len(value) > MAX_CONCRETE_PARTS:
        raise ValueError("invalid concrete inspection piece inventory")
    cursor = 0
    result: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"kind", "text", "span"}:
            raise ValueError("invalid concrete inspection piece")
        piece = cast("dict[str, object]", item)
        kind, spelling, span = piece["kind"], piece["text"], piece["span"]
        if (not isinstance(kind, str) or kind not in TOKEN_KINDS | TRIVIA_KINDS
                or not isinstance(spelling, str) or not spelling
                or not isinstance(span, list) or len(span) != 2
                or any(type(offset) is not int for offset in span)):
            raise ValueError("invalid concrete inspection piece fields")
        first, last = cast("list[int]", span)
        if first != cursor or not first < last <= len(source) or spelling.encode("utf-8") != source[first:last]:
            raise ValueError("concrete inspection does not reconstruct source")
        if first and source[first - 1:first + 1] == b"\r\n":
            raise ValueError("concrete inspection splits CRLF")
        if kind == "whitespace" and any(character not in " \t\r\n" for character in spelling):
            raise ValueError("concrete whitespace contains nontrivia")
        if kind in {"line-comment", "documentation-comment"} and (
                not spelling.startswith("//") or "\r" in spelling or "\n" in spelling
                or (kind == "documentation-comment") != spelling.startswith("///")):
            raise ValueError("concrete comment kind differs from spelling")
        result.append(piece)
        cursor = last
    if cursor != len(source):
        raise ValueError("concrete inspection omits source")
    if result != parts(source):
        raise ValueError("concrete inspection differs from the bounded pure token producer")
    return result
