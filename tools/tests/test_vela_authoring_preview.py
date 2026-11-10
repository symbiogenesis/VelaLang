# SPDX-License-Identifier: Apache-2.0
"""Independent Boolean identities, exact edits and stale-preview publication controls."""

import contextlib
import copy
import hashlib
import io
import json
import tempfile
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import VelaError, ast, authoring_preview, inspection, parse_module
from toolchain.cli import vela as cli

INDEPENDENT_CASES = True


def _site(source: bytes, occurrence: int = 0) -> tuple[int, int]:
    offset = -1
    for _ in range(occurrence + 1):
        offset = source.index(b"==", offset + 1)
    site = ast.position(source[:offset].decode())
    return site.line, site.column


def _value(expression: ast.Expression, flag: bool, other: bool) -> bool:
    if expression.kind == "bool":
        return cast("bool", expression.value)
    if expression.kind == "name":
        return flag if expression.value == "flag" else other
    if expression.kind == "group":
        return _value(expression.children[0], flag, other)
    if expression.kind == "unary":
        return not _value(expression.children[0], flag, other)
    left = _value(expression.children[0], flag, other)
    right = _value(expression.children[1], flag, other)
    return {"==": left == right, "!=": left != right, "&&": left and right, "||": left or right}[
        cast("str", expression.value)]


def _return(source: bytes) -> ast.Expression:
    function = cast("ast.Function", parse_module(source).declarations[0])
    return cast("ast.Return", function.body.terminal).value


def _identities_and_edits() -> None:
    for expression, expected in (
        ("flag == true", "(flag)"), ("flag == false", "!(flag)"),
        ("true == flag", "(flag)"), ("false == flag", "!(flag)"),
        ("(false) == (flag || other)", "!((flag || other))"),
        ("flag && other == false", "flag && !(other)"),
        ("(flag == true) == false", "((flag)) == false"),
        ("false == false", "!(false)"), ("true == true", "(true)"),
    ):
        prefix = "// \U0001f600 preserved\r\nmodule Preview;\r\n/// Preserve documentation.\r\n"
        template = prefix + "public bool Check(bool flag, bool other)=>EXPRESSION; // suffix\r\n"
        source = template.replace("EXPRESSION", expression).encode()
        publication = authoring_preview.preview(source, *_site(source))
        candidate = authoring_preview.validate(publication, source)
        ensure(candidate == template.replace("EXPRESSION", expected).encode(),
               "preview differs from independently expected exact bytes")
        ensure(publication["candidate_sha256"] == hashlib.sha256(candidate).hexdigest(),
               "candidate digest is not bound to exact Unicode/CRLF candidate")
        for flag in (False, True):
            for other in (False, True):
                ensure(_value(_return(source), flag, other) == _value(_return(candidate), flag, other),
                       "Boolean comparison edit changed an independent truth-table observation")


def _refusals() -> None:
    for source, line, column in (
        (b"module M;public bool Check(bool flag)=>flag == flag;", 1, 45),
        (b"module M;public bool Check(bool flag)=>flag // preserve\n== true;", 2, 1),
        (b"module M;public bool Check(bool flag)=>flag == (// preserve\ntrue);", 1, 43),
        (b"module M;public Nat Check()=>true == false;", 1, 33),
        (b"module M;public bool Check(bool flag)=>flag == true;", True, 43),
        (b"module M;public bool Check(bool flag)=>flag == true;", 0, 1),
        (b"module M;public bool Check(bool flag)=>flag == true;", 1, 44),
        (b"module M;public bool Check(bool flag)=>flag == true;", 999, 1),
    ):
        try:
            authoring_preview.preview(source, line, column)
        except (ValueError, VelaError):
            continue
        raise AssertionError("unsafe or unsupported Boolean comparison preview was accepted")
    for source in (
        b"module M;public bool Check(bool flag)=>flag // preserve\n== true;",
        b"module M;public bool Check(bool flag)=>flag == (// preserve\ntrue);",
    ):
        try:
            authoring_preview.preview(source, *_site(source))
        except ValueError as error:
            ensure("comments" in str(error), "comment refusal used the wrong boundary")
        else:
            raise AssertionError("preview discarded authored comments")


def _stale_and_tampered() -> None:
    source = b"module M;public bool Check(bool flag)=>flag == true;"
    publication = authoring_preview.preview(source, *_site(source))
    changes = {"schema": True, "replacement": "false", "candidate": "", "candidate_sha256": "0" * 64,
               "snapshot": "0" * 64, "status": "unchecked", "span": [0, 1], "extra": False}
    for key, replacement in changes.items():
        changed = copy.deepcopy(publication)
        changed[key] = replacement
        try:
            authoring_preview.validate(changed, source)
        except ValueError:
            continue
        raise AssertionError(f"forged preview field {key} was accepted")
    try:
        authoring_preview.validate(publication, source + b" ")
    except ValueError:
        pass
    else:
        raise AssertionError("preview survived a changed source")
    identity = inspection.producer_identity()
    with patch.object(inspection, "producer_identity", return_value={**identity, "version": "0" * 64}):
        try:
            authoring_preview.validate(publication, source)
        except ValueError:
            pass
        else:
            raise AssertionError("preview survived a changed compiler producer")


def _cli_publication() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-boolean-preview-") as directory:
        path = Path(directory) / "source.vela"
        source = b"module M;public bool Check(bool flag)=>flag == false;"
        path.write_bytes(source)
        before = path.stat()
        line, column = _site(source)
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = cli.main(["lint-preview", str(path), "--line", str(line), "--column", str(column)])
        ensure(code == 0 and not errors.getvalue(), "explicit CLI preview failed")
        publication = json.loads(output.getvalue())
        ensure(authoring_preview.validate(publication, source).endswith(b"!(flag);"),
               "CLI did not publish the checked candidate")
        ensure(path.read_bytes() == source and path.stat().st_mtime_ns == before.st_mtime_ns,
               "preview command changed source bytes or metadata")
        preview = authoring_preview.preview

        def edit_during_preview(data: bytes, line: int, column: int) -> dict[str, object]:
            result = preview(data, line, column)
            path.write_bytes(data + b" // concurrent editor")
            return result

        output, errors = io.StringIO(), io.StringIO()
        with (patch.object(authoring_preview, "preview", side_effect=edit_during_preview),
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
            code = cli.main(["lint-preview", str(path), "--line", str(line), "--column", str(column)])
        ensure(code == 1 and not output.getvalue() and "source changed" in errors.getvalue(),
               "CLI published a preview after a concurrent source edit")


def cases() -> list[Case]:
    return [Case("vela-authoring-preview:truth-tables-and-exact-edits", _identities_and_edits),
            Case("vela-authoring-preview:refusals", _refusals),
            Case("vela-authoring-preview:stale-and-tampered", _stale_and_tampered),
            Case("vela-authoring-preview:cli-publication", _cli_publication)]
