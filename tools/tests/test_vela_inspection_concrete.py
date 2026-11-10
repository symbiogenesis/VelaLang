# SPDX-License-Identifier: Apache-2.0
"""Independent concrete-piece consumer and worker-corruption controls."""

import copy
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import concrete, inspect_source, inspection
from toolchain.schema import validate

INDEPENDENT_CASES = True

SOURCE = ("/// docs \U0001f600\r\nmodule Pieces;\r// line \U0001f600\n"
          "public bool Ready(Nat input) => input >= 1_000 && true;  ").encode()
EXPECTED = [
    ("documentation-comment", "/// docs \U0001f600"), ("whitespace", "\r\n"),
    ("keyword", "module"), ("whitespace", " "), ("identifier", "Pieces"), ("punctuation", ";"),
    ("whitespace", "\r"), ("line-comment", "// line \U0001f600"), ("whitespace", "\n"),
    ("keyword", "public"), ("whitespace", " "), ("keyword", "bool"), ("whitespace", " "),
    ("identifier", "Ready"), ("punctuation", "("), ("keyword", "Nat"), ("whitespace", " "),
    ("identifier", "input"), ("punctuation", ")"), ("whitespace", " "), ("punctuation", "=>"),
    ("whitespace", " "), ("identifier", "input"), ("whitespace", " "), ("punctuation", ">="),
    ("whitespace", " "), ("decimal", "1_000"), ("whitespace", " "), ("punctuation", "&&"),
    ("whitespace", " "), ("keyword", "true"), ("punctuation", ";"), ("whitespace", "  ")]


def _request(snapshot: inspection.Snapshot, operation: str, **fields: object) -> dict[str, object]:
    return {"schema": 4, "snapshot": snapshot.export()["snapshot"], "operation": operation, **fields}


def _reconstruct_and_locate() -> None:
    snapshot = inspection.inspect(SOURCE)
    publication = snapshot.export()
    validate(inspection.SCHEMA_PATH, publication)
    ensure(publication["status"] == "checked", "successful source has no concrete inspection")
    pieces = cast("list[dict[str, object]]", publication["concrete"])
    ensure([(piece["kind"], piece["text"]) for piece in pieces] == EXPECTED,
           "concrete piece kinds, spelling, comments or whitespace changed")
    ensure("".join(cast("str", piece["text"]) for piece in pieces).encode() == SOURCE,
           "consumer could not reconstruct exact source from pieces")
    cursor = 0
    for piece, (_, spelling) in zip(pieces, EXPECTED, strict=True):
        last = cursor + len(spelling.encode())
        ensure(piece["span"] == [cursor, last], "concrete byte span differs from independent spelling")
        for offset in (cursor, last - len(spelling[-1].encode())):
            response = snapshot.query(SOURCE, _request(snapshot, "token-at", offset=offset))
            validate(inspection.SCHEMA_PATH, response)
            if SOURCE[offset - 1:offset + 1] == b"\r\n":
                ensure(response["status"] == "refused", "token-at split a CRLF coordinate")
            else:
                ensure(response["items"] == [piece], "token-at lost trivia or half-open selection")
        cursor = last
    end = snapshot.query(SOURCE, _request(snapshot, "token-at", offset=len(SOURCE)))
    ensure(end["status"] == "checked" and end["items"] == [], "EOF invented a concrete piece")
    interior = SOURCE.index("\U0001f600".encode()) + 1
    invalid = snapshot.query(SOURCE, _request(snapshot, "token-at", offset=interior))
    ensure(invalid["reason"] == "invalid-offset", "token-at accepted an interior Unicode byte")


def _bounds_and_freshness() -> None:
    snapshot = inspection.inspect(SOURCE)
    query = _request(snapshot, "tokens", limit=2)
    response = snapshot.query(SOURCE, query)
    validate(inspection.SCHEMA_PATH, response)
    ensure(response["status"] == "partial" and response["complete"] is False
           and response["total"] == len(EXPECTED) and len(cast("list[object]", response["items"])) == 2,
           "bounded token query masqueraded as a complete partition")
    ensure(snapshot.query(SOURCE + b" ", query)["reason"] == "stale-input", "stale concrete pieces reused")
    old = snapshot.query(SOURCE, {**query, "schema": 2})
    ensure(old["reason"] == "schema-version", "schema-2 query silently selected schema-3 concrete semantics")
    raw = {**inspect_source(SOURCE, syntax_tree=True), "concrete": concrete.parts(SOURCE)}
    with patch.object(inspection, "inspect_document", return_value=raw), patch.object(concrete, "MAX_CONCRETE_PARTS", 2):
        bounded = inspection.inspect(SOURCE).export()
    ensure(bounded["status"] == "unavailable" and bounded["concrete"] == []
           and bounded["symbols"] == [], "piece bound escaped as a successful partial snapshot")


def _corrupt_worker_refusal() -> None:
    raw = {**inspect_source(SOURCE, syntax_tree=True), "concrete": concrete.parts(SOURCE)}
    pieces = raw["concrete"]
    corruptions: list[object] = [None, pieces[:-1], pieces[1:], [*pieces, pieces[-1]]]
    for index, fields in ((0, {"kind": "line-comment"}), (2, {"kind": "identifier"}),
                          (1, {"kind": "punctuation"}), (0, {"span": [0, 1]}),
                          (0, {"text": "/// altered"}), (2, {"extra": True})):
        changed = copy.deepcopy(pieces)
        changed[index].update(fields)
        corruptions.append(changed)
    changed = copy.deepcopy(pieces)
    first, last = cast("list[int]", pieces[2]["span"])
    changed[2:3] = [{"kind": "identifier", "text": "mod", "span": [first, first + 3]},
                    {"kind": "identifier", "text": "ule", "span": [first + 3, last]}]
    corruptions.append(changed)
    for value in corruptions:
        changed_raw = {**raw, "concrete": value}
        with patch.object(inspection, "inspect_document", return_value=changed_raw):
            result = inspection.inspect(SOURCE).export()
        validate(inspection.SCHEMA_PATH, result)
        ensure(result["status"] == "unavailable" and result["concrete"] == []
               and result["symbols"] == [], "corrupt worker concrete pieces published as checked")
    for source in (b"module Broken; public Nat F(", b"module Wrong; public Nat F() => true;"):
        result = inspection.inspect(source).export()
        ensure(result["status"] == "unavailable" and result["concrete"] == [],
               "failed semantic producer advertised checked concrete syntax")


def cases() -> list[Case]:
    return [Case("concrete-source-reconstruction-and-byte-token-consumer", _reconstruct_and_locate),
            Case("concrete-query-bounds-schema-and-freshness", _bounds_and_freshness),
            Case("concrete-worker-corruption-and-incomplete-source-refusal", _corrupt_worker_refusal)]
