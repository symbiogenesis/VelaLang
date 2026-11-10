# SPDX-License-Identifier: Apache-2.0
"""Independent archive authentication, oracle, and wire-transcript controls for LSP clients."""

import copy
import hashlib
import io
import json
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import lsp_clients
from toolchain.cli import vela_lsp
from toolchain.lsp import serve
from toolchain.protocol_json import encode_message

INDEPENDENT_CASES = True
_URI = "file:///workspace/interop.vela"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _refuses(operation: Callable[[], object], label: str) -> None:
    try:
        operation()
    except (ValueError, SystemExit):
        return
    raise AssertionError(f"accepted {label}")


def _make_zip(members: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, payload in members.items():
            bundle.writestr(name, payload)
    return stream.getvalue()


def _make_targz(members: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as bundle:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            bundle.addfile(info, io.BytesIO(payload))
    return stream.getvalue()


def _archive_and_license_authentication() -> None:
    exe_bytes = b"binary-payload"
    lic_bytes = b"MIT License\n"
    lua_bytes = b"return { lsp = true }\n"
    unwanted_bytes = b"GPL-3.0-or-later disallowed tool"
    zip_data = _make_zip(
        {
            "pkg/bin/tool.exe": exe_bytes,
            "pkg/LICENSE.txt": lic_bytes,
            "pkg/share/nvim/runtime/lua/vim/lsp.lua": lua_bytes,
            "pkg/unwanted/diff.exe": unwanted_bytes,
        }
    )
    pin = lsp_clients.ArchivePin(
        url="https://example.com/pkg.zip",
        filename="pkg.zip",
        archive_sha256=_sha256(zip_data),
        prefix="pkg",
        executable="bin/tool.exe",
        required_sha256={
            "bin/tool.exe": _sha256(exe_bytes),
            "LICENSE.txt": _sha256(lic_bytes),
        },
    )
    with tempfile.TemporaryDirectory(prefix="vela-lsp-archive-") as td:
        dest = Path(td) / "zip-out"
        digests = lsp_clients.extract_verified_archive(
            zip_data,
            pin,
            dest,
            allow_predicate=("share/nvim/runtime/lua/",),
        )
        ensure(
            set(digests)
            == {
                "bin/tool.exe",
                "LICENSE.txt",
                "share/nvim/runtime/lua/vim/lsp.lua",
            },
            f"unexpected extracted member set: {sorted(digests)}",
        )
        ensure(not (dest / "unwanted" / "diff.exe").exists(), "disallowed member was extracted")
        ensure((dest / "bin" / "tool.exe").read_bytes() == exe_bytes, "extracted binary mismatch")

        bad_archive_pin = lsp_clients.ArchivePin(
            url=pin.url,
            filename=pin.filename,
            archive_sha256="0" * 64,
            prefix=pin.prefix,
            executable=pin.executable,
            required_sha256=pin.required_sha256,
        )
        _refuses(
            lambda: lsp_clients.extract_verified_archive(zip_data, bad_archive_pin, Path(td) / "bad1"),
            "tampered archive digest",
        )

        bad_member_pin = lsp_clients.ArchivePin(
            url=pin.url,
            filename=pin.filename,
            archive_sha256=pin.archive_sha256,
            prefix=pin.prefix,
            executable=pin.executable,
            required_sha256={"bin/tool.exe": "f" * 64, "LICENSE.txt": _sha256(lic_bytes)},
        )
        _refuses(
            lambda: lsp_clients.extract_verified_archive(zip_data, bad_member_pin, Path(td) / "bad2"),
            "tampered member digest",
        )

        for unsafe_name in ("pkg/../escape.txt", "/abs/path.txt", "other/LICENSE.txt", "pkg\\back.txt"):
            unsafe_tar = _make_targz({unsafe_name: lic_bytes, "pkg/LICENSE.txt": lic_bytes})
            unsafe_pin = lsp_clients.ArchivePin(
                url="https://example.com/pkg.tar.gz",
                filename="pkg.tar.gz",
                archive_sha256=_sha256(unsafe_tar),
                prefix="pkg",
                executable="LICENSE.txt",
                required_sha256={"LICENSE.txt": _sha256(lic_bytes)},
            )
            _refuses(
                lambda u=unsafe_tar, p=unsafe_pin: lsp_clients.extract_verified_archive(
                    u, p, Path(td) / "unsafe"
                ),
                f"unsafe tar member {unsafe_name!r}",
            )

        cache_dir = Path(td) / "cache"
        _refuses(
            lambda: lsp_clients._download_bytes("http://example.com/x", _sha256(lic_bytes), cache_dir, "x"),
            "non-HTTPS download URL",
        )
        cached_file = cache_dir / "lic.txt"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_file.write_bytes(lic_bytes)
        ensure(
            lsp_clients._download_bytes(
                "https://example.com/lic.txt",
                _sha256(lic_bytes),
                cache_dir,
                "lic.txt",
            )
            == lic_bytes,
            "verified cached file was not reused",
        )


def _wire_transcript_recording_and_cli() -> None:
    req_init: dict[str, object] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"capabilities": {}},
    }
    notif_init: dict[str, object] = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    req_shutdown: dict[str, object] = {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None}
    notif_exit: dict[str, object] = {"jsonrpc": "2.0", "method": "exit", "params": None}

    wire_in = b"".join(
        encode_message(msg) for msg in (req_init, notif_init, req_shutdown, notif_exit)
    )
    frames: list[dict[str, object]] = []
    out_stream = io.BytesIO()
    exit_code = serve(io.BytesIO(wire_in), out_stream, transcript=frames)
    ensure(exit_code == 0, f"expected clean exit 0, got {exit_code}")
    ensure(len(frames) == 6, f"expected 6 recorded frames, got {len(frames)}")
    directions = [frame["direction"] for frame in frames]
    ensure(
        directions
        == [
            "client_to_server",
            "server_to_client",
            "client_to_server",
            "client_to_server",
            "server_to_client",
            "client_to_server",
        ],
        f"unexpected frame direction sequence: {directions}",
    )

    with tempfile.TemporaryDirectory(prefix="vela-lsp-cli-") as td:
        transcript_path = Path(td) / "session-transcript.json"
        with (
            patch("sys.stdin", new=io.TextIOWrapper(io.BytesIO(wire_in))),
            patch("sys.stdout", new=io.TextIOWrapper(io.BytesIO())),
        ):
            rc = vela_lsp.main(["--transcript", str(transcript_path)])
        ensure(rc == 0 and transcript_path.is_file(), "CLI --transcript did not write transcript file")
        loaded = json.loads(transcript_path.read_text(encoding="utf-8"))
        ensure(
            loaded.get("exit_code") == 0 and len(loaded.get("frames", [])) == 6,
            f"unexpected CLI transcript payload: {loaded!r}",
        )

        with redirect_stderr(io.StringIO()):
            _refuses(lambda: vela_lsp.main(["--output", str(Path(td) / "out.json")]), "--output alone")
            _refuses(
                lambda: vela_lsp.main(
                    ["--qualify-clients", "--transcript", str(Path(td) / "tr.json")]
                ),
                "--qualify-clients with --transcript",
            )

        report_path = Path(td) / "qualification.json"
        fake_report = {"schema": 1, "status": "passed"}
        with patch("toolchain.lsp_clients.qualify_clients", return_value=fake_report):
            rc = vela_lsp.main(["--qualify-clients", "--output", str(report_path)])
        ensure(
            rc == 0 and json.loads(report_path.read_text(encoding="utf-8")) == fake_report,
            "CLI --qualify-clients --output did not write report",
        )


def _synthetic_session(
    *,
    incremental: bool,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    oracle = lsp_clients.expected_scenario_oracle(_URI)
    next_id = 1
    wire_chunks: list[bytes] = []

    def send_req(method: str, params: object = None) -> int:
        nonlocal next_id
        rid = next_id
        next_id += 1
        wire_chunks.append(
            encode_message({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        )
        return rid

    def send_notif(method: str, params: object = None) -> None:
        wire_chunks.append(
            encode_message(
                {"jsonrpc": "2.0", "method": method, "params": {} if params is None else params}
            )
        )

    send_req("initialize", {"capabilities": {"general": {"positionEncodings": ["utf-16"]},
        "workspace": {"workspaceEdit": {"documentChanges": True}}}})
    send_notif("initialized")
    send_notif(
        "textDocument/didOpen",
        {
            "textDocument": {
                "uri": _URI,
                "languageId": "vela",
                "version": 1,
                "text": lsp_clients.INITIAL_SOURCE,
            }
        },
    )

    for pos in ((2, 17), (6, 20), (6, 27), (7, 6), (0, 3), (6, 26)):
        send_req(
            "textDocument/hover",
            {"textDocument": {"uri": _URI}, "position": {"line": pos[0], "character": pos[1]}},
        )
    send_req("textDocument/completion", {
        "textDocument": {"uri": _URI}, "position": {"line": 6, "character": 22}})
    send_req("textDocument/signatureHelp", {
        "textDocument": {"uri": _URI}, "position": {"line": 6, "character": 27}})
    for pos in ((6, 20), (11, 11), (14, 11)):
        send_req(
            "textDocument/definition",
            {"textDocument": {"uri": _URI}, "position": {"line": pos[0], "character": pos[1]}},
        )
    for inc in (True, False):
        send_req(
            "textDocument/references",
            {
                "textDocument": {"uri": _URI},
                "position": {"line": 8, "character": 10},
                "context": {"includeDeclaration": inc},
            },
        )
    send_req("textDocument/documentSymbol", {"textDocument": {"uri": _URI}})
    for rstart, rend in (((0, 0), (17, 0)), ((7, 0), (8, 0))):
        send_req(
            "textDocument/inlayHint",
            {
                "textDocument": {"uri": _URI},
                "range": {
                    "start": {"line": rstart[0], "character": rstart[1]},
                    "end": {"line": rend[0], "character": rend[1]},
                },
            },
        )
    send_req("textDocument/semanticTokens/full", {"textDocument": {"uri": _URI}})
    send_req("textDocument/prepareRename", {"textDocument": {"uri": _URI},
        "position": {"line": 7, "character": 7}})
    send_req("textDocument/rename", {"textDocument": {"uri": _URI},
        "position": {"line": 7, "character": 7}, "newName": "rescaled"})
    send_req(
        "textDocument/formatting",
        {"textDocument": {"uri": _URI}, "options": {"tabSize": 4, "insertSpaces": True}},
    )

    # Stage 2: Apply formatting
    send_notif(
        "textDocument/didChange",
        {
            "textDocument": {"uri": _URI, "version": 2},
            "contentChanges": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 17, "character": 0},
                    },
                    "text": lsp_clients.FORMATTED_SOURCE,
                }
                if incremental
                else {"text": lsp_clients.FORMATTED_SOURCE}
            ],
        },
    )
    send_req(
        "textDocument/formatting",
        {"textDocument": {"uri": _URI}, "options": {"tabSize": 4, "insertSpaces": True}},
    )
    send_req("textDocument/semanticTokens/full", {"textDocument": {"uri": _URI}})

    # Stage 3: Same-line edit after 😀 on line 5
    send_notif(
        "textDocument/didChange",
        {
            "textDocument": {"uri": _URI, "version": 3},
            "contentChanges": [
                {
                    "range": {
                        "start": {"line": 5, "character": 33},
                        "end": {"line": 5, "character": 34},
                    },
                    "text": "!",
                }
                if incremental
                else {"text": lsp_clients.UNICODE_DOC_SOURCE}
            ],
        },
    )
    send_req(
        "textDocument/hover",
        {"textDocument": {"uri": _URI}, "position": {"line": 6, "character": 17}},
    )

    # Stage 4: Type error
    send_notif(
        "textDocument/didChange",
        {
            "textDocument": {"uri": _URI, "version": 4},
            "contentChanges": [{"text": lsp_clients.TYPE_ERROR_SOURCE}],
        },
    )
    send_req(
        "textDocument/hover",
        {"textDocument": {"uri": _URI}, "position": {"line": 11, "character": 22}},
    )
    send_req(
        "textDocument/definition",
        {"textDocument": {"uri": _URI}, "position": {"line": 11, "character": 22}},
    )
    send_req(
        "textDocument/references",
        {
            "textDocument": {"uri": _URI},
            "position": {"line": 13, "character": 12},
            "context": {"includeDeclaration": True},
        },
    )
    send_req("textDocument/documentSymbol", {"textDocument": {"uri": _URI}})
    send_req(
        "textDocument/inlayHint",
        {
            "textDocument": {"uri": _URI},
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 25, "character": 0}},
        },
    )
    send_req(
        "textDocument/formatting",
        {"textDocument": {"uri": _URI}, "options": {"tabSize": 4, "insertSpaces": True}},
    )
    send_req("textDocument/semanticTokens/full", {"textDocument": {"uri": _URI}})

    # Stage 5: Unsupported error
    send_notif(
        "textDocument/didChange",
        {
            "textDocument": {"uri": _URI, "version": 5},
            "contentChanges": [{"text": lsp_clients.UNSUPPORTED_ERROR_SOURCE}],
        },
    )

    # Stage 6: Recovery + notifications + close + shutdown/exit
    send_notif(
        "textDocument/didChange",
        {
            "textDocument": {"uri": _URI, "version": 6},
            "contentChanges": [{"text": lsp_clients.RECOVERED_SOURCE}],
        },
    )
    send_req(
        "textDocument/hover",
        {"textDocument": {"uri": _URI}, "position": {"line": 11, "character": 22}},
    )
    send_req(
        "textDocument/definition",
        {"textDocument": {"uri": _URI}, "position": {"line": 11, "character": 29}},
    )
    send_req(
        "textDocument/inlayHint",
        {
            "textDocument": {"uri": _URI},
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 25, "character": 0}},
        },
    )
    send_req("textDocument/semanticTokens/full", {"textDocument": {"uri": _URI}})
    send_notif("workspace/didChangeConfiguration", {"settings": {}})
    send_notif(
        "workspace/didChangeWatchedFiles",
        {"changes": [{"uri": _URI + ".deleted", "type": 3}]},
    )
    send_notif("$/cancelRequest", {"id": 99999})
    send_notif("textDocument/didClose", {"textDocument": {"uri": _URI}})
    send_req("shutdown")
    send_notif("exit")

    frames: list[dict[str, object]] = []
    exit_code = serve(io.BytesIO(b"".join(wire_chunks)), io.BytesIO(), transcript=frames)
    transcript = {"exit_code": exit_code, "frames": frames}

    stage1_obs = dict(cast("dict[str, object]", copy.deepcopy(oracle["stage1"])))
    stage1_obs["diagnostics"] = []
    stage1_obs["goto_definition_cursor_1based"] = [5, 18]

    stage2_obs = dict(cast("dict[str, object]", copy.deepcopy(oracle["stage2"])))
    stage2_obs["diagnostics"] = []

    stage3_obs = dict(cast("dict[str, object]", copy.deepcopy(oracle["stage3"])))
    stage3_obs["diagnostics"] = []

    oracle4 = cast("dict[str, object]", oracle["stage4"])
    stage4_obs: dict[str, object] = {
        "diagnostics": [copy.deepcopy(oracle4["diagnostic"])],
        "broken_hover": oracle4["broken_hover"],
        "broken_definition": oracle4["broken_definition"],
        "broken_references": copy.deepcopy(oracle4["broken_references"]),
        "broken_document_symbols": copy.deepcopy(oracle4["broken_document_symbols"]),
        "broken_inlay_hints": copy.deepcopy(oracle4["broken_inlay_hints"]),
        "broken_formatting": copy.deepcopy(oracle4["broken_formatting"]),
        "broken_semantic_tokens": copy.deepcopy(oracle4["broken_semantic_tokens"]),
    }

    oracle5 = cast("dict[str, object]", oracle["stage5"])
    stage5_obs: dict[str, object] = {"diagnostics": [copy.deepcopy(oracle5["diagnostic"])]}

    stage6_obs = dict(cast("dict[str, object]", copy.deepcopy(oracle["stage6"])))
    stage6_obs["diagnostics"] = []

    observation: dict[str, object] = {
        "client": "synthetic",
        "uri": _URI,
        "offset_encoding": "utf-16",
        "server_capabilities": copy.deepcopy(oracle["capabilities"]),
        "stage1": stage1_obs,
        "stage2": stage2_obs,
        "stage3": stage3_obs,
        "stage4": stage4_obs,
        "stage5": stage5_obs,
        "stage6": stage6_obs,
    }
    return oracle, observation, transcript


def _scenario_oracle_and_observation_controls() -> None:
    oracle, observation, _ = _synthetic_session(incremental=True)
    lsp_clients.verify_client_observation(observation, oracle)
    identified = copy.deepcopy(observation)
    tokens = cast("dict[str, object]", cast("dict[str, object]", identified["stage1"])["semantic_tokens_initial"])
    tokens["resultId"] = "0" * 64
    lsp_clients.verify_client_observation(identified, oracle)
    for invalid_identity in (True, "", "z" * 64, "0" * 65):
        tokens["resultId"] = invalid_identity
        _refuses(lambda: lsp_clients.verify_client_observation(identified, oracle), "malformed semantic result ID")

    for mutator, label in (
        (lambda obs: obs.update(offset_encoding="utf-8"), "wrong offset_encoding"),
        (
            lambda obs: cast("dict[str, object]", obs["server_capabilities"]).update(
                completionProvider=True
            ),
            "advertised completionProvider",
        ),
        (
            lambda obs: cast("dict[str, object]", obs["stage1"]).update(
                goto_definition_cursor_1based=[5, 19]
            ),
            "wrong :LspGotoDefinition cursor",
        ),
        (
            lambda obs: cast("dict[str, object]", obs["stage2"]).update(
                formatting_edits_idempotent=[{"newText": "x"}]
            ),
            "non-idempotent second formatting",
        ),
        (
            lambda obs: cast("dict[str, object]", obs["stage4"]).update(
                broken_hover={"contents": "stale"}
            ),
            "stale hover on broken buffer",
        ),
        (
            lambda obs: cast("dict[str, object]", obs["stage4"]).update(diagnostics=[]),
            "missing type diagnostic in stage4",
        ),
        (
            lambda obs: cast("dict[str, object]", obs["stage5"]).update(diagnostics=[]),
            "missing unsupported diagnostic in stage5",
        ),
        (
            lambda obs: cast("dict[str, object]", obs["stage6"]).update(
                recovered_hover_square=None
            ),
            "missing recovered hover in stage6",
        ),
    ):
        tampered = copy.deepcopy(observation)
        mutator(tampered)
        _refuses(
            lambda t=tampered: lsp_clients.verify_client_observation(t, oracle),
            label,
        )


def _wire_transcript_replay_and_controls() -> None:
    _, _, inc_transcript = _synthetic_session(incremental=True)
    inc_summary = lsp_clients.verify_wire_transcript(inc_transcript, require_ranged_change=True)
    ensure(
        inc_summary["ranged_did_change_count"] == 2
        and inc_summary["same_line_unicode_ranged_change"] is True,
        f"unexpected incremental transcript summary: {inc_summary!r}",
    )

    _, _, full_transcript = _synthetic_session(incremental=False)
    full_summary = lsp_clients.verify_wire_transcript(full_transcript, require_ranged_change=False)
    ensure(
        full_summary["ranged_did_change_count"] == 0,
        f"unexpected full-sync transcript summary: {full_summary!r}",
    )
    _refuses(
        lambda: lsp_clients.verify_wire_transcript(full_transcript, require_ranged_change=True),
        "full-sync transcript when ranged changes are required",
    )

    bad_exit = copy.deepcopy(inc_transcript)
    bad_exit["exit_code"] = 1
    _refuses(
        lambda: lsp_clients.verify_wire_transcript(bad_exit, require_ranged_change=True),
        "non-zero exit_code in transcript",
    )

    bad_unqualified = copy.deepcopy(inc_transcript)
    for raw_frame in cast("list[dict[str, object]]", bad_unqualified["frames"]):
        msg = cast("dict[str, object]", raw_frame["message"])
        if msg.get("method") == "textDocument/publishDiagnostics":
            params = cast("dict[str, object]", msg["params"])
            diags = cast("list[dict[str, object]]", params["diagnostics"])
            if diags:
                cast("dict[str, object]", diags[0]["data"])["unqualified"] = False
                break
    _refuses(
        lambda: lsp_clients.verify_wire_transcript(bad_unqualified, require_ranged_change=True),
        "diagnostic publication without unqualified provenance",
    )


def _delta_consumer_controls() -> None:
    change: dict[str, object] = {"range": {
        "start": {"line": 0, "character": 3}, "end": {"line": 1, "character": 1}},
        "text": "delta\r\n"}
    ensure(lsp_clients._wire_source_edit("a\U0001f600b\r\nc", change) == "a\U0001f600delta\r\n",
           "wire consumer did not independently apply UTF-16/CRLF coordinates")
    invalid_change = copy.deepcopy(change)
    cast("dict[str, object]", cast("dict[str, object]", invalid_change["range"])["start"])["character"] = 2
    _refuses(lambda: lsp_clients._wire_source_edit("a\U0001f600b\r\nc", invalid_change),
             "wire edit splitting a supplementary character")
    oracle = lsp_clients.expected_scenario_oracle(_URI)
    recovered = cast("dict[str, object]", oracle["stage6"])
    base = cast("list[int]", cast("dict[str, object]", recovered["recovered_semantic_tokens"])["data"])
    expected = [2, 11, 2, 0, 1, 0, 7, 5, 1, 3, 0, 10, 5, 1, 2]
    observation: dict[str, object] = {
        "base": {"resultId": "1" * 64, "data": base},
        "changed": {"resultId": "2" * 64,
                    "edits": [{"start": 0, "deleteCount": len(base), "data": expected}]},
        "unchanged": {"resultId": "3" * 64, "edits": []},
        "unknown": {"resultId": "4" * 64, "data": expected},
        "invalidated": {"resultId": "5" * 64, "data": expected},
    }
    lsp_clients._verify_delta_observation(observation, base)
    for key, replacement in (
        ("base", {"resultId": "1" * 64, "data": []}),
        ("changed", {"resultId": "2" * 64, "data": expected}),
        ("changed", {"resultId": "2" * 64, "edits": []}),
        ("changed", {"resultId": "2" * 64,
                     "edits": [{"start": True, "deleteCount": len(base), "data": expected}]}),
        ("changed", {"resultId": "2" * 64,
                     "edits": [{"start": 0, "deleteCount": len(base) + 1, "data": expected}]}),
        ("changed", {"resultId": "2" * 64,
                     "edits": [{"start": 0, "deleteCount": len(base), "data": expected[:-1]}]}),
        ("unchanged", {"resultId": "3" * 64,
                       "edits": [{"start": 0, "deleteCount": 0}]}),
        ("unknown", {"resultId": "4" * 64, "edits": []}),
        ("invalidated", {"resultId": "5" * 64, "data": []}),
        ("invalidated", {"resultId": "4" * 64, "data": expected}),
    ):
        corrupted = copy.deepcopy(observation)
        corrupted[key] = replacement
        _refuses(lambda c=corrupted: lsp_clients._verify_delta_observation(c, base),
                 f"corrupted {key} observation")
    _refuses(lambda: lsp_clients._verify_delta_observation({}, base), "missing delta sequence")
    _, _, transcript = _synthetic_session(incremental=True)
    _refuses(lambda: lsp_clients.verify_wire_transcript(
        transcript, require_ranged_change=True, require_token_deltas=True),
        "full-token-only transcript presented as delta qualification")


def _delta_wire_fixture() -> tuple[dict[str, object], dict[str, object]]:
    frames: list[dict[str, object]] = []
    request_id = 0

    def frame(direction: str, payload: dict[str, object]) -> None:
        frames.append({"index": len(frames), "direction": direction,
                       "message": {"jsonrpc": "2.0", **payload}})

    def note(method: str, params: object = None) -> None:
        frame("client_to_server", {"method": method, "params": params})

    def request(method: str, params: object, result: object) -> None:
        nonlocal request_id
        request_id += 1
        frame("client_to_server", {"id": request_id, "method": method, "params": params})
        frame("server_to_client", {"id": request_id, "result": result})

    request("initialize", {"capabilities": {"textDocument": {
        "semanticTokens": {"requests": {"full": {"delta": True}}}}}}, {})
    note("initialized", {})
    note("textDocument/didOpen", {"textDocument": {
        "uri": _URI, "languageId": "vela", "version": 1, "text": lsp_clients.RECOVERED_SOURCE}})
    for method in ("hover", "definition", "references", "documentSymbol", "inlayHint",
                   "formatting", "hover", "hover"):
        request("textDocument/" + method, {"textDocument": {"uri": _URI},
            "position": {"line": 0, "character": 0}, "context": {"includeDeclaration": True},
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
            "options": {"tabSize": 4, "insertSpaces": True}}, {})
    for code in ("type", "unsupported", None):
        frame("server_to_client", {"method": "textDocument/publishDiagnostics", "params": {
            "uri": _URI, "diagnostics": [] if code is None else [{"code": code, "data": {
                "unqualified": True, "snapshot": "fixture", "generation": 1}}]}})
    before = [0, 0, 1, 0, 0]
    after = [2, 11, 2, 0, 1, 0, 7, 5, 1, 3, 0, 10, 5, 1, 2]
    observed: dict[str, object] = {
        "base": {"resultId": "1" * 64, "data": before},
        "changed": {"resultId": "2" * 64, "edits": [
            {"start": 0, "deleteCount": len(before), "data": after}]},
        "unchanged": {"resultId": "3" * 64, "edits": []},
        "unknown": {"resultId": "4" * 64, "data": after},
        "invalidated": {"resultId": "5" * 64, "data": after},
    }
    full = "textDocument/semanticTokens/full"
    request(full, {"textDocument": {"uri": _URI}}, copy.deepcopy(observed["base"]))
    note("textDocument/didChange", {"textDocument": {"uri": _URI, "version": 2},
                                  "contentChanges": [{"text": lsp_clients.DELTA_SOURCE}]})
    for key, previous in (("changed", "1" * 64), ("unchanged", "2" * 64),
                          ("unknown", "unknown-client-base"), ("invalidated", "4" * 64)):
        if key == "invalidated":
            note("workspace/didChangeConfiguration", {"settings": {}})
        request(full + "/delta", {"textDocument": {"uri": _URI}, "previousResultId": previous},
                copy.deepcopy(observed[key]))
    note("workspace/didChangeWatchedFiles", {"changes": []})
    note("$/cancelRequest", {"id": 99999})
    note("textDocument/didClose", {"textDocument": {"uri": _URI}})
    request("shutdown", None, None)
    note("exit", None)
    return {"exit_code": 0, "frames": frames}, observed


def _delta_wire_evidence_controls() -> None:
    transcript, observed = _delta_wire_fixture()

    def verify(value: dict[str, object]) -> None:
        lsp_clients.verify_wire_transcript(value, require_ranged_change=False,
            require_token_deltas=True, delta_observation=observed)

    verify(transcript)
    for identity, replacement in (
        ("2" * 64, {"resultId": "2" * 64, "edits": []}),
        ("5" * 64, {"resultId": "5" * 64, "edits": []}),
        ("4" * 64, {"resultId": "4" * 64, "data": [0, 0, 1, 0, 0]}),
    ):
        corrupted = copy.deepcopy(transcript)
        for raw_frame in cast("list[dict[str, object]]", corrupted["frames"]):
            message = cast("dict[str, object]", raw_frame["message"])
            result = message.get("result")
            if isinstance(result, dict) and result.get("resultId") == identity:
                message["result"] = replacement
        _refuses(lambda c=corrupted: verify(c), "wrong token data or stale-base edits on wire")
    wrong_observation = copy.deepcopy(observed)
    cast("dict[str, object]", wrong_observation["base"])["data"] = []
    _refuses(lambda: lsp_clients.verify_wire_transcript(transcript, require_ranged_change=False,
        require_token_deltas=True, delta_observation=wrong_observation),
        "observation that disagrees with its exact wire response")


def _live_two_client_qualification() -> None:
    with redirect_stdout(io.StringIO()):
        report = lsp_clients.qualify_clients()
    ensure(report.get("status") == "passed", f"live qualification failed: {report!r}")
    ensure(report.get("schema") == 2, "qualification report lacks retained delta evidence")
    sessions = cast("dict[str, dict[str, object]]", report["sessions"])
    for name, session in sessions.items():
        observation_raw = cast("str", session["observation_json"]).encode("utf-8")
        transcript_raw = cast("str", session["transcript_json"]).encode("utf-8")
        ensure(_sha256(observation_raw) == session["observation_sha256"],
               f"{name}: retained observation hash mismatch")
        ensure(_sha256(transcript_raw) == session["transcript_sha256"],
               f"{name}: retained transcript hash mismatch")
        observation = json.loads(observation_raw)
        lsp_clients.verify_client_observation(observation, lsp_clients.expected_scenario_oracle(
            observation["uri"]), require_token_deltas=True)
        lsp_clients.verify_wire_transcript(json.loads(transcript_raw),
            require_ranged_change=name != "vim_full_sync", require_token_deltas=True,
            delta_observation=observation["delta"], require_local_rename=True,
            rename_observation=observation["stage1"], discovery_observation=observation["stage1"])


def _rename_wire_evidence_controls() -> None:
    _, observation, transcript = _synthetic_session(incremental=True)
    prepared = cast("dict[str, object]", observation["stage1"])

    def verify(value: dict[str, object]) -> dict[str, object]:
        return lsp_clients.verify_wire_transcript(value, require_ranged_change=True,
            require_local_rename=True, rename_observation=prepared)

    ensure(verify(transcript)["local_rename_responses"] == 2,
           "wire evidence omitted one local rename response")
    for field, replacement in (("version", 2), ("version", True), ("edits", [])):
        corrupted = copy.deepcopy(transcript)
        for frame in cast("list[dict[str, object]]", corrupted["frames"]):
            message = cast("dict[str, object]", frame["message"])
            result = message.get("result")
            if isinstance(result, dict) and "documentChanges" in result:
                change = cast("list[dict[str, object]]", result["documentChanges"])[0]
                if field == "version":
                    cast("dict[str, object]", change["textDocument"])[field] = replacement
                else:
                    change[field] = replacement
        _refuses(lambda c=corrupted: verify(c), "stale or incomplete local rename wire response")
    changed_observation = copy.deepcopy(prepared)
    changed_observation["rename_prepared"] = None
    _refuses(lambda: lsp_clients.verify_wire_transcript(transcript, require_ranged_change=True,
        require_local_rename=True, rename_observation=changed_observation),
        "rename observation not joined to wire evidence")


def _callable_discovery_wire_controls() -> None:
    _, observation, transcript = _synthetic_session(incremental=True)
    observed = cast("dict[str, object]", observation["stage1"])

    def verify(value: dict[str, object]) -> dict[str, object]:
        return lsp_clients.verify_wire_transcript(value, require_ranged_change=True,
                                                discovery_observation=observed)

    ensure(verify(transcript)["callable_discovery_responses"] == 2,
           "wire evidence omitted a callable discovery response")
    for method in ("textDocument/completion", "textDocument/signatureHelp"):
        corrupted = copy.deepcopy(transcript)
        requested: set[object] = set()
        for frame in cast("list[dict[str, object]]", corrupted["frames"]):
            message = cast("dict[str, object]", frame["message"])
            if frame["direction"] == "client_to_server" and message.get("method") == method:
                requested.add(message["id"])
            elif frame["direction"] == "server_to_client" and message.get("id") in requested:
                message["result"] = {}
        _refuses(lambda c=corrupted: verify(c), "changed callable discovery wire response")
        misplaced = copy.deepcopy(transcript)
        for frame in cast("list[dict[str, object]]", misplaced["frames"]):
            message = cast("dict[str, object]", frame["message"])
            if message.get("method") == method:
                cast("dict[str, object]", message["params"])["position"] = {"line": 6, "character": 0}
        _refuses(lambda c=misplaced: verify(c), "callable discovery joined to a different source cursor")
    wrong_observation = copy.deepcopy(observed)
    wrong_observation["signature_square_call"] = None
    _refuses(lambda: lsp_clients.verify_wire_transcript(transcript, require_ranged_change=True,
        discovery_observation=wrong_observation), "callable discovery observation disagrees with wire")


def cases() -> list[Case]:
    return [
        Case("archive-and-license-authentication", _archive_and_license_authentication),
        Case("wire-transcript-recording-and-cli", _wire_transcript_recording_and_cli),
        Case("scenario-oracle-and-observation-controls", _scenario_oracle_and_observation_controls),
        Case("wire-transcript-replay-and-controls", _wire_transcript_replay_and_controls),
        Case("delta-consumer-controls", _delta_consumer_controls),
        Case("delta-wire-evidence-controls", _delta_wire_evidence_controls),
        Case("rename-wire-evidence-controls", _rename_wire_evidence_controls),
        Case("callable-discovery-wire-evidence-controls", _callable_discovery_wire_controls),
        Case("live-two-client-qualification", _live_two_client_qualification, slow=True),
    ]
