# SPDX-License-Identifier: Apache-2.0
"""Two-client Neovim and Vim LSP interoperability qualification for pure Vela."""

import hashlib
import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

from filelock import FileLock

from toolchain import inspect_source, translate
from toolchain.atomic import atomic_path
from toolchain.authoring import format_source
from toolchain.lsp import diagnose
from toolchain.lsp_format import format_document, formatting_edits
from toolchain.lsp_services import SEMANTIC_TOKEN_MODIFIERS, SEMANTIC_TOKEN_TYPES, project
from toolchain.source import SourceSnapshot

TIMEOUT_SECONDS = 120
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_MEMBER_COUNT = 4096

NEOVIM_VERSION = "0.11.0"
NEOVIM_TAG = f"v{NEOVIM_VERSION}"
NEOVIM_LICENSE_URL = f"https://raw.githubusercontent.com/neovim/neovim/{NEOVIM_TAG}/LICENSE.txt"
NEOVIM_LICENSE_SHA256 = "e1ff044cabc90a87faf9356618a5c43078c020c3c5e98a4dee570dd098da043d"

VIM_VERSION = "9.1.2141"
VIM_TAG = f"v{VIM_VERSION}"
VIM_LINUX_BINARY = Path("/usr/bin/vim")
VIM_LINUX_UGANDA = Path("/usr/share/vim/vim91/doc/uganda.txt")
VIM_LINUX_COPYRIGHT = Path("/usr/share/doc/vim-common/copyright")
VIM_LINUX_UGANDA_SHA256 = "e8863e53a3a6e4e2ae33c4465f189f439d3125a5099865f7b0233d03e13e8226"
VIM_LINUX_COPYRIGHT_SHA256 = "302e996bdc0ed227fafe0531c2b6fb5359c69efe1592f34ba22186be2497c3c9"
VIM_LINUX_AARCH64_SHA256 = "600795c5eaa3320daa68a7b56e14efce25bd3bf4bb2181a02a28344f587137a6"

YEGAPPAN_LSP_COMMIT = "58eac06e81bad174cfa897614ae01adf0d31d10a"
YEGAPPAN_LSP_URL = f"https://github.com/yegappan/lsp/archive/{YEGAPPAN_LSP_COMMIT}.tar.gz"
YEGAPPAN_LSP_ARCHIVE_SHA256 = "3c7d0eeb410708b0096251401da4a4290e10b3aff233a75358468b69c0f1d9cb"
YEGAPPAN_LSP_PREFIX = f"lsp-{YEGAPPAN_LSP_COMMIT}"
YEGAPPAN_LSP_FILES_SHA256: dict[str, str] = {
    "LICENSE": "1cd90ab40fd08eeff7573eecc935d076e45c7e01e7a86ff96c89f8a58b6094f6",
    "plugin/lsp.vim": "3d8d083485fdc56009cfbaee42f2e76f85d87f01d4dc536cb7619dfaa10d04e3",
    "autoload/lsp/lspserver.vim": "816d57d2f5620e22e57ba8ccd63eb60bbabfcf765eca62abc99d870668183b6c",
}


@dataclass(frozen=True, slots=True)
class ArchivePin:
    """Hash-pinned external client archive and its reviewed member digests."""

    url: str
    filename: str
    archive_sha256: str
    prefix: str
    executable: str
    required_sha256: dict[str, str]


NEOVIM_PINS: dict[tuple[str, str], ArchivePin] = {
    ("win32", "AMD64"): ArchivePin(
        url=f"https://github.com/neovim/neovim/releases/download/{NEOVIM_TAG}/nvim-win64.zip",
        filename=f"nvim-{NEOVIM_TAG}-win64.zip",
        archive_sha256="00ea1a0fd3252a883974a3411159087196924f214000583257188b205d173a23",
        prefix="nvim-win64",
        executable="bin/nvim.exe",
        required_sha256={
            "bin/nvim.exe": "9f1ef87c6e9222e513bc920246e67ea8e99be1b66f59e25aea6f11801fa9ee3d",
            "bin/lua51.dll": "d64fae51493f47ec066890cc9e938415648919292a961577040f3df3f356206d",
            "share/nvim/runtime/lua/vim/lsp.lua": (
                "7afd6fd4d07619dfaf76f3e13c50571f5a5ae6f1a1172710483a5acd2c8a9abd"
            ),
            "share/nvim/runtime/pack/dist/opt/netrw/LICENSE.txt": (
                "0dac5aa0e9035a9624a8310aaf5749a94a767651263faadbf85d566dc726a9a4"
            ),
        },
    ),
    ("linux", "aarch64"): ArchivePin(
        url=f"https://github.com/neovim/neovim/releases/download/{NEOVIM_TAG}/nvim-linux-arm64.tar.gz",
        filename=f"nvim-{NEOVIM_TAG}-linux-arm64.tar.gz",
        archive_sha256="6959583f45042da20e0a082dc65108725629a4739ab91246c678fd084ecaf50e",
        prefix="nvim-linux-arm64",
        executable="bin/nvim",
        required_sha256={
            "bin/nvim": "5f4e2752e39bdf160d621302bb568b66ae6170ce81048abb43b348ed41c54a3f",
            "share/nvim/runtime/lua/vim/lsp.lua": (
                "8fe04154882cee269190126d67f9b44c276bf710f00ed6dabc5b621bf97bb24d"
            ),
            "share/nvim/runtime/pack/dist/opt/netrw/LICENSE.txt": (
                "9c65b12c2e22ab4e628508c7baf96ecbf7016eaa608756ddd8476b5b23e46037"
            ),
        },
    ),
    ("linux", "x86_64"): ArchivePin(
        url=f"https://github.com/neovim/neovim/releases/download/{NEOVIM_TAG}/nvim-linux-x86_64.tar.gz",
        filename=f"nvim-{NEOVIM_TAG}-linux-x86_64.tar.gz",
        archive_sha256="fe0a5bc79e64c5e4d9f844cd96157ebd3919ef1343b329e9ebc3f455924cc7d6",
        prefix="nvim-linux-x86_64",
        executable="bin/nvim",
        required_sha256={
            "bin/nvim": "1d6c61d3290f4e78c5a0fa10ddb522a1fc6e3ee5cbd71dc294cdd1c73de58384",
            "share/nvim/runtime/lua/vim/lsp.lua": (
                "8fe04154882cee269190126d67f9b44c276bf710f00ed6dabc5b621bf97bb24d"
            ),
            "share/nvim/runtime/pack/dist/opt/netrw/LICENSE.txt": (
                "9c65b12c2e22ab4e628508c7baf96ecbf7016eaa608756ddd8476b5b23e46037"
            ),
        },
    ),
}
NEOVIM_PINS[("win32", "ARM64")] = NEOVIM_PINS[("win32", "AMD64")]

VIM_WINDOWS_PINS: dict[str, ArchivePin] = {
    "ARM64": ArchivePin(
        url=f"https://github.com/vim/vim-win32-installer/releases/download/{VIM_TAG}/gvim_{VIM_VERSION}_arm64.zip",
        filename=f"gvim_{VIM_VERSION}_arm64.zip",
        archive_sha256="7d2236366ae48b908b24e098e3cb1983e1cd6e3587ea121b261ecb71aed063ff",
        prefix="vim/vim91",
        executable="vim.exe",
        required_sha256={
            "vim.exe": "0e6ac7181288b7f880efd03f342c9699124cb8424a2c6f9998832b3bc6297426",
            "vim64.dll": "92a13be885e0b9ce06f69cefd4194b5d37dff306cc7ea4123a635f9afcbd7a26",
            "libsodium.dll": "515d8f360540fa2a18e9b4402b738a7572cb3ec0b010f446f7a8facf47eeb96a",
            "LICENSE.txt": "85b94ff37491a7c25873c8b18ba3cb843c7ced100712788e16d80d629d5d5f0d",
            "doc/uganda.txt": "2368b1d5cb54728c1f689130175706dfb43f9798ecf60730f486b44d8944446e",
        },
    ),
    "AMD64": ArchivePin(
        url=f"https://github.com/vim/vim-win32-installer/releases/download/{VIM_TAG}/gvim_{VIM_VERSION}_x64.zip",
        filename=f"gvim_{VIM_VERSION}_x64.zip",
        archive_sha256="85ea6c1955770d6a12cf919d279af1c44c7fe48a2e86f767ac9f6c6ba36fb73c",
        prefix="vim/vim91",
        executable="vim.exe",
        required_sha256={
            "vim.exe": "f79a4bcd8bbcb01d9ce9938ef1890afc35a09d8db85bbb609c84043fe1b66e62",
            "vim64.dll": "0ed4298eda1f55b2f2ed655fc9216c3a5c48f1e1391619fabeed92346a65f131",
            "libsodium.dll": "f1b56eb55a86edee37a2614c8bd38272ac325ec6fa6fa7a4088a4d1a42815c4c",
            "LICENSE.txt": "0b3f1f330cb1b179bb17c7c687d4cec601e0aa3462bc7f890ad4c3888d37d720",
            "doc/uganda.txt": "2368b1d5cb54728c1f689130175706dfb43f9798ecf60730f486b44d8944446e",
        },
    ),
}

DISK_SENTINEL = "// disk sentinel: must never be read or modified by vela-lsp\n"

INITIAL_SOURCE = (
    "// 😀 café\n"
    "module Interop;\n"
    "public const Nat Limit = 1000;\n"
    "/// Computes a square for café 😀.\n"
    "public const Nat Square(const Nat value)=>value*value;\n"
    "public Nat Adjust(Nat base, const Nat multiplier, bool boost) {\n"
    "  const Nat start = Square(multiplier);\n"
    "  let scaled = start + base;\n"
    "  let Nat explicit = scaled;\n"
    "  if (boost) {\n"
    "    let branch = explicit + Limit;\n"
    "    return branch;\n"
    "  } else {\n"
    "    let branch = explicit;\n"
    "    return branch;\n"
    "  }\n"
    "}\n"
)

FORMATTED_SOURCE = format_source(INITIAL_SOURCE.encode("utf-8")).decode("utf-8")

UNICODE_DOC_SOURCE = FORMATTED_SOURCE.replace(
    "/// Computes a square for café 😀.",
    "/// Computes a square for café 😀!",
)

TYPE_ERROR_SOURCE = UNICODE_DOC_SOURCE.replace(
    "public const Nat Square(const Nat value) => value * value;",
    "// 😀 shift\npublic const Nat Square(const Nat value) => true;",
)

UNSUPPORTED_ERROR_SOURCE = TYPE_ERROR_SOURCE.replace(
    "public const Nat Square(const Nat value) => true;",
    "public const Nat Square(const Nat value) => value * value;",
).replace(
    "    const Nat start = Square(multiplier);",
    "    const Nat start = Square(base);",
)

RECOVERED_SOURCE = UNSUPPORTED_ERROR_SOURCE.replace(
    "    const Nat start = Square(base);",
    "    const Nat start = Square(multiplier);",
)

NEOVIM_SCRIPT = r"""
local target_path = vim.env.VELA_TARGET_FILE
local python_exe = vim.env.VELA_PYTHON_EXE
local run_py = vim.env.VELA_RUN_PY
local transcript_path = vim.env.VELA_TRANSCRIPT_FILE
local out_path = vim.env.VELA_CLIENT_OUT

local function fail(msg)
  io.stderr:write("neovim client failure: " .. tostring(msg) .. "\n")
  vim.cmd("cquit 1")
end

local function read_lines(text)
  local lines = vim.split(text, "\n", { plain = true })
  if lines[#lines] == "" then
    table.remove(lines, #lines)
  end
  return lines
end

local initial_source = table.concat({
  "// 😀 café",
  "module Interop;",
  "public const Nat Limit = 1000;",
  "/// Computes a square for café 😀.",
  "public const Nat Square(const Nat value)=>value*value;",
  "public Nat Adjust(Nat base, const Nat multiplier, bool boost) {",
  "  const Nat start = Square(multiplier);",
  "  let scaled = start + base;",
  "  let Nat explicit = scaled;",
  "  if (boost) {",
  "    let branch = explicit + Limit;",
  "    return branch;",
  "  } else {",
  "    let branch = explicit;",
  "    return branch;",
  "  }",
  "}",
}, "\n")

vim.cmd("edit " .. vim.fn.fnameescape(target_path))
local bufnr = vim.api.nvim_get_current_buf()
vim.bo[bufnr].filetype = "vela"
vim.bo[bufnr].swapfile = false
vim.bo[bufnr].fileformat = "unix"
vim.api.nvim_buf_set_lines(bufnr, 0, -1, false, read_lines(initial_source))

local diag_events = {}
vim.api.nvim_create_autocmd("DiagnosticChanged", {
  buffer = bufnr,
  callback = function()
    local items = vim.diagnostic.get(bufnr)
    local converted = {}
    for _, d in ipairs(items) do
      local user_data = (d.user_data and d.user_data.lsp) or {}
      table.insert(converted, {
        line = d.lnum,
        character = d.col,
        end_line = d.end_lnum,
        end_character = d.end_col,
        code = d.code or user_data.code,
        severity = d.severity,
        source = d.source,
        message = d.message,
      })
    end
    table.insert(diag_events, converted)
  end,
})

local client_id = vim.lsp.start({
  name = "vela-lsp",
  cmd = { python_exe, run_py, "vela-lsp", "--transcript", transcript_path },
  root_dir = vim.fn.fnamemodify(target_path, ":h"),
}, { bufnr = bufnr })

if not client_id then
  fail("vim.lsp.start returned nil")
end

local client = vim.lsp.get_client_by_id(client_id)
local ok_init = vim.wait(10000, function()
  return client and client.initialized and #diag_events >= 1
end, 10)
if not ok_init then
  fail("timed out waiting for initialization and initial diagnostics")
end

local uri = vim.uri_from_bufnr(bufnr)

local function sync_request(method, params)
  local done = false
  local res_err = nil
  local res_val = nil
  local ok_send = client:request(method, params, function(err, result)
    res_err = err
    res_val = result
    done = true
  end, bufnr)
  if not ok_send then
    fail("client:request failed for " .. method)
  end
  local ok_wait = vim.wait(10000, function() return done end, 10)
  if not ok_wait then
    fail("timed out waiting for " .. method)
  end
  if res_err ~= nil then
    fail(method .. " returned error: " .. vim.json.encode(res_err))
  end
  return res_val
end

local function pos_params(line, character)
  return {
    textDocument = { uri = uri },
    position = { line = line, character = character },
  }
end

local function ref_params(line, character, include_decl)
  return {
    textDocument = { uri = uri },
    position = { line = line, character = character },
    context = { includeDeclaration = include_decl },
  }
end

local function range_params(sline, schar, eline, echar)
  return {
    textDocument = { uri = uri },
    range = {
      start = { line = sline, character = schar },
      ["end"] = { line = eline, character = echar },
    },
  }
end

local stage1 = {
  diagnostics = diag_events[#diag_events],
  hover_limit = sync_request("textDocument/hover", pos_params(2, 17)),
  hover_square_call = sync_request("textDocument/hover", pos_params(6, 20)),
  hover_multiplier = sync_request("textDocument/hover", pos_params(6, 27)),
  hover_scaled = sync_request("textDocument/hover", pos_params(7, 6)),
  hover_non_symbol = sync_request("textDocument/hover", pos_params(0, 3)),
  hover_half_open_end = sync_request("textDocument/hover", pos_params(6, 26)),
  definition_square_call = sync_request("textDocument/definition", pos_params(6, 20)),
  definition_branch_then = sync_request("textDocument/definition", pos_params(11, 11)),
  definition_branch_else = sync_request("textDocument/definition", pos_params(14, 11)),
  references_explicit_incl = sync_request("textDocument/references", ref_params(8, 10, true)),
  references_explicit_excl = sync_request("textDocument/references", ref_params(8, 10, false)),
  document_symbols = sync_request("textDocument/documentSymbol", { textDocument = { uri = uri } }),
  inlay_hints_full = sync_request("textDocument/inlayHint", range_params(0, 0, 17, 0)),
  inlay_hints_subrange = sync_request("textDocument/inlayHint", range_params(7, 0, 8, 0)),
  semantic_tokens_initial = sync_request("textDocument/semanticTokens/full", { textDocument = { uri = uri } }),
}

local fmt_edits = sync_request("textDocument/formatting", {
  textDocument = { uri = uri },
  options = { tabSize = 4, insertSpaces = true },
})
local prev_diag_count = #diag_events
vim.lsp.util.apply_text_edits(vim.deepcopy(fmt_edits), bufnr, client.offset_encoding)
local ok_fmt_diag = vim.wait(10000, function() return #diag_events > prev_diag_count end, 10)
if not ok_fmt_diag then
  fail("timed out waiting for diagnostics after applying formatting edits")
end

local formatted_lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
if formatted_lines[#formatted_lines] == "" then
  table.remove(formatted_lines, #formatted_lines)
end
local formatted_buffer_text = table.concat(formatted_lines, "\n") .. "\n"

local stage2 = {
  formatting_edits_initial = fmt_edits,
  formatted_buffer_text = formatted_buffer_text,
  diagnostics = diag_events[#diag_events],
  formatting_edits_idempotent = sync_request("textDocument/formatting", {
    textDocument = { uri = uri },
    options = { tabSize = 4, insertSpaces = true },
  }),
  semantic_tokens_formatted = sync_request("textDocument/semanticTokens/full", { textDocument = { uri = uri } }),
}

-- Stage 3: Same-line edit after supplementary character 😀 on line 5
prev_diag_count = #diag_events
vim.api.nvim_buf_set_lines(bufnr, 5, 6, false, { "/// Computes a square for café 😀!" })
local ok_doc_diag = vim.wait(10000, function() return #diag_events > prev_diag_count end, 10)
if not ok_doc_diag then
  fail("timed out waiting for diagnostics after same-line Unicode doc edit")
end
local stage3 = {
  diagnostics = diag_events[#diag_events],
  hover_square_unicode_doc = sync_request("textDocument/hover", pos_params(6, 17)),
}

-- Stage 4: Introduce type error after inserted // 😀 shift line
prev_diag_count = #diag_events
vim.api.nvim_buf_set_lines(bufnr, 6, 7, false, {
  "// 😀 shift",
  "public const Nat Square(const Nat value) => true;",
})
local ok_type_diag = vim.wait(10000, function()
  return #diag_events > prev_diag_count and #diag_events[#diag_events] == 1
end, 10)
if not ok_type_diag then
  fail("timed out waiting for type error diagnostic")
end
local stage4 = {
  diagnostics = diag_events[#diag_events],
  broken_hover = sync_request("textDocument/hover", pos_params(11, 22)),
  broken_definition = sync_request("textDocument/definition", pos_params(11, 22)),
  broken_references = sync_request("textDocument/references", ref_params(13, 12, true)),
  broken_document_symbols = sync_request("textDocument/documentSymbol", { textDocument = { uri = uri } }),
  broken_inlay_hints = sync_request("textDocument/inlayHint", range_params(0, 0, 25, 0)),
  broken_formatting = sync_request("textDocument/formatting", {
    textDocument = { uri = uri },
    options = { tabSize = 4, insertSpaces = true },
  }),
  broken_semantic_tokens = sync_request("textDocument/semanticTokens/full", { textDocument = { uri = uri } }),
}

-- Stage 5: Introduce unsupported constant-initializer error on shifted line 11
prev_diag_count = #diag_events
vim.api.nvim_buf_set_lines(bufnr, 7, 8, false, {
  "public const Nat Square(const Nat value) => value * value;",
})
vim.api.nvim_buf_set_lines(bufnr, 11, 12, false, {
  "    const Nat start = Square(base);",
})
local ok_unsup_diag = vim.wait(10000, function()
  return #diag_events > prev_diag_count
    and #diag_events[#diag_events] == 1
    and diag_events[#diag_events][1].code == "unsupported"
end, 10)
if not ok_unsup_diag then
  fail("timed out waiting for unsupported error diagnostic")
end
local stage5 = {
  diagnostics = diag_events[#diag_events],
}

-- Stage 6: Restore valid source at shifted coordinates, send workspace notifications, close, stop
prev_diag_count = #diag_events
vim.api.nvim_buf_set_lines(bufnr, 11, 12, false, {
  "    const Nat start = Square(multiplier);",
})
local ok_rec_diag = vim.wait(10000, function()
  return #diag_events > prev_diag_count and #diag_events[#diag_events] == 0
end, 10)
if not ok_rec_diag then
  fail("timed out waiting for recovery diagnostics")
end

local recovered_hover_square = sync_request("textDocument/hover", pos_params(11, 22))
local recovered_definition_multiplier = sync_request("textDocument/definition", pos_params(11, 29))
local recovered_inlay_hints = sync_request("textDocument/inlayHint", range_params(0, 0, 25, 0))
local recovered_semantic_tokens = sync_request("textDocument/semanticTokens/full", { textDocument = { uri = uri } })

prev_diag_count = #diag_events
client:notify("workspace/didChangeConfiguration", { settings = {} })
local ok_cfg_diag = vim.wait(10000, function() return #diag_events > prev_diag_count end, 10)
if not ok_cfg_diag then
  fail("timed out waiting for didChangeConfiguration diagnostics")
end

prev_diag_count = #diag_events
client:notify("workspace/didChangeWatchedFiles", {
  changes = { { uri = uri .. ".deleted", type = 3 } },
})
local ok_watch_diag = vim.wait(10000, function() return #diag_events > prev_diag_count end, 10)
if not ok_watch_diag then
  fail("timed out waiting for didChangeWatchedFiles diagnostics")
end

client:notify("$/cancelRequest", { id = 99999 })

vim.api.nvim_buf_delete(bufnr, { force = true })
local stage6 = {
  diagnostics = diag_events[#diag_events],
  recovered_hover_square = recovered_hover_square,
  recovered_definition_multiplier = recovered_definition_multiplier,
  recovered_inlay_hints = recovered_inlay_hints,
  recovered_semantic_tokens = recovered_semantic_tokens,
}

local out = {
  client = "neovim",
  version = string.format("%d.%d.%d", vim.version().major, vim.version().minor, vim.version().patch),
  uri = uri,
  offset_encoding = client.offset_encoding,
  server_info = client.server_info,
  server_capabilities = client.server_capabilities,
  stage1 = stage1,
  stage2 = stage2,
  stage3 = stage3,
  stage4 = stage4,
  stage5 = stage5,
  stage6 = stage6,
}

client:stop()
local ok_stop = vim.wait(10000, function() return client:is_stopped() end, 10)
if not ok_stop then
  fail("timed out waiting for client:stop()")
end

local fh = assert(io.open(out_path, "wb"))
fh:write(vim.json.encode(out))
fh:close()
vim.cmd("qall!")
"""

VIM_SCRIPT = r"""vim9script
filetype on
execute 'set runtimepath^=' .. fnameescape($VELA_YEGAPPAN_LSP_ROOT)
execute 'source ' .. fnameescape($VELA_YEGAPPAN_LSP_ROOT .. '/plugin/lsp.vim')
import autoload 'lsp/buffer.vim' as buf
import autoload 'lsp/diag.vim' as diag

def Fail(msg: string)
  writefile(['vim client failure: ' .. msg], $VELA_CLIENT_OUT .. '.err')
  cquit 1
enddef

def WaitUntil(Pred: func(): bool, label: string)
  var loops = 0
  while !Pred() && loops < 500
    sleep 20m
    loops += 1
  endwhile
  if !Pred()
    Fail('timed out waiting for ' .. label)
  endif
enddef

def ConvertDiags(items: list<dict<any>>): list<dict<any>>
  var res: list<dict<any>> = []
  for d in items
    res->add({
      line: d.range.start.line,
      character: d.range.start.character,
      end_line: d.range.end.line,
      end_character: d.range.end.character,
      code: d->get('code', ''),
      severity: d->get('severity', 0),
      source: d->get('source', ''),
      message: d.message,
    })
  endfor
  return res
enddef

def RpcResult(lserver: dict<any>, method: string, params: dict<any>): any
  var reply = lserver.rpc(method, params, {timeout: 10000, handleError: false})
  if reply->has_key('error')
    Fail(method .. ' returned error: ' .. json_encode(reply.error))
  endif
  return reply->get('result', v:null)
enddef

def RunQualification()
  var target_path = $VELA_TARGET_FILE
  var python_exe = $VELA_PYTHON_EXE
  var run_py = $VELA_RUN_PY
  var transcript_path = $VELA_TRANSCRIPT_FILE
  var out_path = $VELA_CLIENT_OUT
  var inc_sync = $VELA_VIM_INCREMENTAL == '1'

  autocmd BufNewFile,BufRead *.vela setfiletype vela
  g:LspEnable()
  g:LspOptionsSet({
    autoHighlightDiags: true,
    showInlayHints: true,
    semanticHighlight: true,
    ultisnipsSupport: false,
    incrementalSync: inc_sync,
  })
  g:LspAddServer([{
    name: 'vela-lsp',
    filetype: ['vela'],
    path: python_exe,
    args: [run_py, 'vela-lsp', '--transcript', transcript_path],
    features: {diagnostics: true, documentFormatting: true, inlayHints: true, semanticHighlight: true},
    syncInit: true,
  }])

  execute 'edit ' .. fnameescape(target_path)
  setlocal fileformat=unix
  setlocal expandtab
  setlocal shiftwidth=4
  setlocal tabstop=4
  var bnr = bufnr('%')

  WaitUntil(() => g:LspServerReady(), 'LspServerReady')
  var lserver = buf.BufLspServerGet(bnr)
  if lserver->empty()
    Fail('BufLspServerGet returned empty dict')
  endif

  var initial_lines = [
    '// 😀 café',
    'module Interop;',
    'public const Nat Limit = 1000;',
    '/// Computes a square for café 😀.',
    'public const Nat Square(const Nat value)=>value*value;',
    'public Nat Adjust(Nat base, const Nat multiplier, bool boost) {',
    '  const Nat start = Square(multiplier);',
    '  let scaled = start + base;',
    '  let Nat explicit = scaled;',
    '  if (boost) {',
    '    let branch = explicit + Limit;',
    '    return branch;',
    '  } else {',
    '    let branch = explicit;',
    '    return branch;',
    '  }',
    '}',
  ]
  silent! :%delete _
  setline(1, initial_lines)
  listener_flush()

  var uri = lserver.getTextDocPosition(false).textDocument.uri
  WaitUntil(() => diag.GetDiagsForBuf(bnr)->empty(), 'initial clean diagnostics')

  var PosParams = (line: number, character: number): dict<any> => ({
    textDocument: {uri: uri},
    position: {line: line, character: character},
  })
  var RefParams = (line: number, character: number, inc: bool): dict<any> => ({
    textDocument: {uri: uri},
    position: {line: line, character: character},
    context: {includeDeclaration: inc},
  })
  var RangeParams = (sline: number, schar: number, eline: number, echar: number): dict<any> => ({
    textDocument: {uri: uri},
    range: {
      start: {line: sline, character: schar},
      end: {line: eline, character: echar},
    },
  })

  # Exercise high-level yegappan/lsp editor commands on Stage 1 buffer
  cursor(7, 21)
  LspGotoDefinition
  var goto_def_cursor = [line('.'), col('.')]

  var stage1 = {
    diagnostics: ConvertDiags(diag.GetDiagsForBuf(bnr)),
    goto_definition_cursor_1based: goto_def_cursor,
    hover_limit: RpcResult(lserver, 'textDocument/hover', PosParams(2, 17)),
    hover_square_call: RpcResult(lserver, 'textDocument/hover', PosParams(6, 20)),
    hover_multiplier: RpcResult(lserver, 'textDocument/hover', PosParams(6, 27)),
    hover_scaled: RpcResult(lserver, 'textDocument/hover', PosParams(7, 6)),
    hover_non_symbol: RpcResult(lserver, 'textDocument/hover', PosParams(0, 3)),
    hover_half_open_end: RpcResult(lserver, 'textDocument/hover', PosParams(6, 26)),
    definition_square_call: RpcResult(lserver, 'textDocument/definition', PosParams(6, 20)),
    definition_branch_then: RpcResult(lserver, 'textDocument/definition', PosParams(11, 11)),
    definition_branch_else: RpcResult(lserver, 'textDocument/definition', PosParams(14, 11)),
    references_explicit_incl: RpcResult(lserver, 'textDocument/references', RefParams(8, 10, true)),
    references_explicit_excl: RpcResult(lserver, 'textDocument/references', RefParams(8, 10, false)),
    document_symbols: RpcResult(lserver, 'textDocument/documentSymbol', {textDocument: {uri: uri}}),
    inlay_hints_full: RpcResult(lserver, 'textDocument/inlayHint', RangeParams(0, 0, 17, 0)),
    inlay_hints_subrange: RpcResult(lserver, 'textDocument/inlayHint', RangeParams(7, 0, 8, 0)),
    semantic_tokens_initial: RpcResult(lserver, 'textDocument/semanticTokens/full', {textDocument: {uri: uri}}),
  }

  # Stage 2: Query formatting edits, then run :LspFormat to apply them in the Vim buffer
  var fmt_edits = RpcResult(lserver, 'textDocument/formatting', {
    textDocument: {uri: uri},
    options: {tabSize: 4, insertSpaces: true},
  })
  LspFormat
  listener_flush()
  WaitUntil(() => line('$') >= 24, 'formatted buffer line count')
  var fmt_lines = getline(1, '$')
  if !fmt_lines->empty() && fmt_lines[-1] == ''
    fmt_lines->remove(-1)
  endif
  var formatted_buffer_text = fmt_lines->join("\n") .. "\n"

  var stage2 = {
    formatting_edits_initial: fmt_edits,
    formatted_buffer_text: formatted_buffer_text,
    diagnostics: ConvertDiags(diag.GetDiagsForBuf(bnr)),
    formatting_edits_idempotent: RpcResult(lserver, 'textDocument/formatting', {
      textDocument: {uri: uri},
      options: {tabSize: 4, insertSpaces: true},
    }),
    semantic_tokens_formatted: RpcResult(lserver, 'textDocument/semanticTokens/full', {textDocument: {uri: uri}}),
  }

  # Stage 3: Same-line edit after supplementary character 😀 on line 6 (1-based)
  setline(6, '/// Computes a square for café 😀!')
  listener_flush()
  var stage3 = {
    diagnostics: ConvertDiags(diag.GetDiagsForBuf(bnr)),
    hover_square_unicode_doc: RpcResult(lserver, 'textDocument/hover', PosParams(6, 17)),
  }

  # Stage 4: Introduce type error after inserted // 😀 shift line
  setline(7, '// 😀 shift')
  append(7, 'public const Nat Square(const Nat value) => true;')
  listener_flush()
  WaitUntil(() => diag.GetDiagsForBuf(bnr)->len() == 1 && diag.GetDiagsForBuf(bnr)[0]->get('code', '') == 'type', 'type diagnostic')
  var stage4 = {
    diagnostics: ConvertDiags(diag.GetDiagsForBuf(bnr)),
    broken_hover: RpcResult(lserver, 'textDocument/hover', PosParams(11, 22)),
    broken_definition: RpcResult(lserver, 'textDocument/definition', PosParams(11, 22)),
    broken_references: RpcResult(lserver, 'textDocument/references', RefParams(13, 12, true)),
    broken_document_symbols: RpcResult(lserver, 'textDocument/documentSymbol', {textDocument: {uri: uri}}),
    broken_inlay_hints: RpcResult(lserver, 'textDocument/inlayHint', RangeParams(0, 0, 25, 0)),
    broken_formatting: RpcResult(lserver, 'textDocument/formatting', {
      textDocument: {uri: uri},
      options: {tabSize: 4, insertSpaces: true},
    }),
    broken_semantic_tokens: RpcResult(lserver, 'textDocument/semanticTokens/full', {textDocument: {uri: uri}}),
  }

  # Stage 5: Introduce unsupported constant-initializer error on shifted 1-based line 12
  setline(8, 'public const Nat Square(const Nat value) => value * value;')
  setline(12, '    const Nat start = Square(base);')
  listener_flush()
  WaitUntil(() => diag.GetDiagsForBuf(bnr)->len() == 1 && diag.GetDiagsForBuf(bnr)[0]->get('code', '') == 'unsupported', 'unsupported diagnostic')
  var stage5 = {
    diagnostics: ConvertDiags(diag.GetDiagsForBuf(bnr)),
  }

  # Stage 6: Restore valid source at shifted coordinates, send workspace notifications, close, stop
  setline(12, '    const Nat start = Square(multiplier);')
  listener_flush()
  WaitUntil(() => diag.GetDiagsForBuf(bnr)->empty(), 'recovered clean diagnostics')

  var recovered_hover_square = RpcResult(lserver, 'textDocument/hover', PosParams(11, 22))
  var recovered_definition_multiplier = RpcResult(lserver, 'textDocument/definition', PosParams(11, 29))
  var recovered_inlay_hints = RpcResult(lserver, 'textDocument/inlayHint', RangeParams(0, 0, 25, 0))
  var recovered_semantic_tokens = RpcResult(lserver, 'textDocument/semanticTokens/full', {textDocument: {uri: uri}})

  lserver.sendNotification('workspace/didChangeConfiguration', {settings: {}})
  lserver.sendNotification('workspace/didChangeWatchedFiles', {
    changes: [{uri: uri .. '.deleted', type: 3}],
  })
  lserver.sendNotification('$/cancelRequest', {id: 99999})
  WaitUntil(() => diag.GetDiagsForBuf(bnr)->empty(), 'post-notification clean diagnostics')

  var raw_caps = lserver.caps->deepcopy()
  var srv_info = raw_caps->get('~additionalInitResult_serverInfo', {})
  if raw_caps->has_key('~additionalInitResult_serverInfo')
    raw_caps->remove('~additionalInitResult_serverInfo')
  endif
  var offset_enc = raw_caps->get('positionEncoding', '')

  execute 'bwipeout! ' .. bnr
  lserver.stopServer()

  var out = {
    client: 'vim-yegappan-lsp',
    version: string(v:version) .. '.' .. string(v:versionlong % 10000),
    incremental_sync: inc_sync,
    uri: uri,
    offset_encoding: offset_enc,
    server_info: srv_info,
    server_capabilities: raw_caps,
    stage1: stage1,
    stage2: stage2,
    stage3: stage3,
    stage4: stage4,
    stage5: stage5,
    stage6: {
      diagnostics: [],
      recovered_hover_square: recovered_hover_square,
      recovered_definition_multiplier: recovered_definition_multiplier,
      recovered_inlay_hints: recovered_inlay_hints,
      recovered_semantic_tokens: recovered_semantic_tokens,
    },
  }
  writefile([json_encode(out)], out_path)
enddef

try
  RunQualification()
catch
  Fail(v:exception .. ' at ' .. v:throwpoint)
endtry
"""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _object(value: object, label: str = "object") -> dict[str, object]:
    _require(isinstance(value, dict), f"expected {label} to be an object")
    return cast("dict[str, object]", value)


def _array(value: object, label: str = "array") -> list[object]:
    _require(isinstance(value, list), f"expected {label} to be an array")
    return cast("list[object]", value)


def _platform_key() -> tuple[str, str]:
    machine = platform.machine()
    normalized = {"arm64": "aarch64", "amd64": "x86_64"}.get(machine.lower(), machine)
    if sys.platform == "win32":
        normalized = "ARM64" if machine.upper() == "ARM64" else "AMD64"
    key = (sys.platform, normalized)
    if key not in NEOVIM_PINS:
        raise ValueError(f"unsupported platform for LSP client qualification: {key!r}")
    return key


def _download_bytes(url: str, expected_sha256: str, cache_dir: Path, filename: str) -> bytes:
    _require(url.startswith("https://"), f"refusing non-HTTPS client artifact URL: {url}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / filename
    if cached.is_file():
        existing = cached.read_bytes()
        if _sha256(existing) == expected_sha256:
            return existing
        cached.unlink(missing_ok=True)
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        data = cast("bytes", response.read(MAX_DOWNLOAD_BYTES + 1))
    _require(len(data) <= MAX_DOWNLOAD_BYTES, f"downloaded artifact exceeds byte limit: {filename}")
    actual = _sha256(data)
    _require(
        actual == expected_sha256,
        f"downloaded artifact digest mismatch for {filename}: expected {expected_sha256}, got {actual}",
    )
    with atomic_path(cached) as pending:
        pending.write_bytes(data)
    return data


def _validate_relative_member(name: str, prefix: str) -> str | None:
    if "\\" in name:
        raise ValueError(f"archive member contains backslash: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member path: {name!r}")
    prefix_parts = PurePosixPath(prefix).parts
    if path.parts[: len(prefix_parts)] != prefix_parts:
        raise ValueError(f"archive member outside expected prefix {prefix!r}: {name!r}")
    tail = path.parts[len(prefix_parts) :]
    if not tail:
        return None
    return PurePosixPath(*tail).as_posix()


def extract_verified_archive(
    archive_bytes: bytes,
    pin: ArchivePin,
    destination: Path,
    *,
    allow_predicate: tuple[str, ...] = (),
) -> dict[str, str]:
    """Authenticate an archive's SHA-256 and extract only reviewed members."""
    actual_archive = _sha256(archive_bytes)
    _require(
        actual_archive == pin.archive_sha256,
        f"archive SHA-256 mismatch for {pin.filename}: expected {pin.archive_sha256}, got {actual_archive}",
    )
    extracted_digests: dict[str, str] = {}
    allowed_exact = set(pin.required_sha256)

    def _permitted(rel: str) -> bool:
        return rel in allowed_exact or any(rel.startswith(prefix) for prefix in allow_predicate)

    def _write_member(rel: str, payload: bytes) -> None:
        extracted_digests[rel] = _sha256(payload)
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        if rel == pin.executable and sys.platform != "win32":
            target.chmod(target.stat().st_mode | stat.S_IXUSR)

    if pin.filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as bundle:
            infos = bundle.infolist()
            _require(len(infos) <= MAX_MEMBER_COUNT, "zip archive exceeds member limit")
            for info in infos:
                if info.is_dir():
                    continue
                rel = _validate_relative_member(info.filename, pin.prefix)
                if rel is None or not _permitted(rel):
                    continue
                _require(rel not in extracted_digests, f"duplicate zip member {rel!r}")
                _require(0 <= info.file_size <= MAX_DOWNLOAD_BYTES, f"oversized zip member {rel!r}")
                _write_member(rel, bundle.read(info))
    elif pin.filename.endswith(".tar.gz"):
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as bundle:
            members = bundle.getmembers()
            _require(len(members) <= MAX_MEMBER_COUNT, "tar archive exceeds member limit")
            for member in members:
                if member.isdir():
                    continue
                rel = _validate_relative_member(member.name, pin.prefix)
                if rel is None or not _permitted(rel):
                    continue
                _require(member.isfile(), f"selected tar member {rel!r} is not a regular file")
                _require(rel not in extracted_digests, f"duplicate tar member {rel!r}")
                _require(0 <= member.size <= MAX_DOWNLOAD_BYTES, f"oversized tar member {rel!r}")
                stream = bundle.extractfile(member)
                if stream is None:
                    raise ValueError(f"unreadable tar member {rel!r}")
                with stream:
                    payload = stream.read(MAX_DOWNLOAD_BYTES + 1)
                _write_member(rel, payload)
    else:
        raise ValueError(f"unsupported archive format: {pin.filename}")

    for required_rel, expected_digest in pin.required_sha256.items():
        actual_digest = extracted_digests.get(required_rel)
        _require(
            actual_digest == expected_digest,
            f"member digest mismatch for {required_rel}: expected {expected_digest}, got {actual_digest}",
        )
    return extracted_digests


def _stage_neovim(cache_dir: Path, stage_dir: Path) -> tuple[Path, dict[str, object]]:
    key = _platform_key()
    pin = NEOVIM_PINS[key]
    archive_bytes = _download_bytes(pin.url, pin.archive_sha256, cache_dir, pin.filename)
    license_bytes = _download_bytes(
        NEOVIM_LICENSE_URL,
        NEOVIM_LICENSE_SHA256,
        cache_dir,
        f"neovim-{NEOVIM_TAG}-LICENSE.txt",
    )
    nvim_root = stage_dir / "neovim"
    digests = extract_verified_archive(
        archive_bytes,
        pin,
        nvim_root,
        allow_predicate=("share/nvim/runtime/lua/",),
    )
    (nvim_root / "LICENSE.txt").write_bytes(license_bytes)
    executable = nvim_root / pin.executable
    done = subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    first_line = done.stdout.splitlines()[0].strip() if done.stdout else ""
    _require(
        done.returncode == 0 and first_line == f"NVIM v{NEOVIM_VERSION}",
        f"unexpected Neovim --version output: {first_line!r}",
    )
    return executable, {
        "name": "neovim",
        "version": NEOVIM_VERSION,
        "license": "Apache-2.0 AND Vim",
        "archive_url": pin.url,
        "archive_sha256": pin.archive_sha256,
        "license_url": NEOVIM_LICENSE_URL,
        "license_sha256": _sha256(license_bytes),
        "executable_sha256": digests[pin.executable],
        "verified_files_sha256": {rel: digests[rel] for rel in sorted(pin.required_sha256)},
        "extracted_file_count": len(digests),
    }


def _stage_vim_and_plugin(cache_dir: Path, stage_dir: Path) -> tuple[Path, Path, dict[str, object]]:
    plugin_pin = ArchivePin(
        url=YEGAPPAN_LSP_URL,
        filename=f"yegappan-lsp-{YEGAPPAN_LSP_COMMIT[:12]}.tar.gz",
        archive_sha256=YEGAPPAN_LSP_ARCHIVE_SHA256,
        prefix=YEGAPPAN_LSP_PREFIX,
        executable="plugin/lsp.vim",
        required_sha256=YEGAPPAN_LSP_FILES_SHA256,
    )
    plugin_archive = _download_bytes(
        plugin_pin.url,
        plugin_pin.archive_sha256,
        cache_dir,
        plugin_pin.filename,
    )
    plugin_root = stage_dir / "yegappan-lsp"
    plugin_digests = extract_verified_archive(
        plugin_archive,
        plugin_pin,
        plugin_root,
        allow_predicate=("autoload/lsp/",),
    )

    key = _platform_key()
    if key[0] == "win32":
        vim_pin = VIM_WINDOWS_PINS[key[1]]
        vim_archive = _download_bytes(vim_pin.url, vim_pin.archive_sha256, cache_dir, vim_pin.filename)
        vim_root = stage_dir / "vim"
        vim_digests = extract_verified_archive(vim_archive, vim_pin, vim_root)
        # Never extract non-allowlisted third-party binaries/DLLs from the Windows installer zip.
        _require(
            set(vim_digests) == set(vim_pin.required_sha256),
            f"unexpected extracted files in Windows Vim staging tree: {sorted(vim_digests)}",
        )
        vim_exe = vim_root / vim_pin.executable
        vim_metadata: dict[str, object] = {
            "source": "vim-win32-installer",
            "archive_url": vim_pin.url,
            "archive_sha256": vim_pin.archive_sha256,
            "executable_sha256": vim_digests[vim_pin.executable],
            "verified_files_sha256": {rel: vim_digests[rel] for rel in sorted(vim_pin.required_sha256)},
        }
    else:
        _require(VIM_LINUX_BINARY.is_file(), f"missing pinned Linux Vim binary at {VIM_LINUX_BINARY}")
        _require(VIM_LINUX_UGANDA.is_file(), f"missing Vim license file at {VIM_LINUX_UGANDA}")
        _require(VIM_LINUX_COPYRIGHT.is_file(), f"missing Vim copyright file at {VIM_LINUX_COPYRIGHT}")
        uganda_sha = _sha256(VIM_LINUX_UGANDA.read_bytes())
        copyright_sha = _sha256(VIM_LINUX_COPYRIGHT.read_bytes())
        _require(
            uganda_sha == VIM_LINUX_UGANDA_SHA256,
            f"Linux Vim uganda.txt SHA-256 mismatch: {uganda_sha}",
        )
        _require(
            copyright_sha == VIM_LINUX_COPYRIGHT_SHA256,
            f"Linux Vim copyright SHA-256 mismatch: {copyright_sha}",
        )
        resolved_vim = VIM_LINUX_BINARY.resolve()
        exe_sha = _sha256(resolved_vim.read_bytes())
        if key[1] == "aarch64":
            _require(
                exe_sha == VIM_LINUX_AARCH64_SHA256,
                f"Linux aarch64 Vim binary SHA-256 mismatch: {exe_sha}",
            )
        vim_exe = resolved_vim
        vim_metadata = {
            "source": "ubuntu-24.04-vim",
            "executable_path": str(resolved_vim),
            "executable_sha256": exe_sha,
            "uganda_sha256": uganda_sha,
            "copyright_sha256": copyright_sha,
        }

    done = subprocess.run(
        [str(vim_exe), "--version"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    _require(
        done.returncode == 0
        and "VIM - Vi IMproved 9.1" in done.stdout
        and "-2141" in done.stdout,
        "unexpected Vim --version output",
    )
    return vim_exe, plugin_root, {
        "name": "vim-yegappan-lsp",
        "vim_version": VIM_VERSION,
        "vim_license": "Vim AND ISC AND MIT",
        "vim": vim_metadata,
        "plugin": {
            "repository": "https://github.com/yegappan/lsp",
            "commit": YEGAPPAN_LSP_COMMIT,
            "license": "MIT",
            "archive_url": YEGAPPAN_LSP_URL,
            "archive_sha256": YEGAPPAN_LSP_ARCHIVE_SHA256,
            "verified_files_sha256": {
                rel: plugin_digests[rel] for rel in sorted(YEGAPPAN_LSP_FILES_SHA256)
            },
            "extracted_file_count": len(plugin_digests),
        },
    }


def expected_scenario_oracle(uri: str) -> dict[str, object]:
    """Compute the independent pure Vela oracle expectations for the 6-stage scenario."""
    snap1 = SourceSnapshot(uri, 1, INITIAL_SOURCE, 1)
    facts1 = inspect_source(INITIAL_SOURCE.encode("utf-8"))
    fmt1 = format_document(INITIAL_SOURCE.encode("utf-8"))

    snap2 = SourceSnapshot(uri, 2, FORMATTED_SOURCE, 2)
    facts2 = inspect_source(FORMATTED_SOURCE.encode("utf-8"))
    fmt2 = format_document(FORMATTED_SOURCE.encode("utf-8"))

    snap3 = SourceSnapshot(uri, 3, UNICODE_DOC_SOURCE, 3)
    facts3 = inspect_source(UNICODE_DOC_SOURCE.encode("utf-8"))

    snap4 = SourceSnapshot(uri, 4, TYPE_ERROR_SOURCE, 4)
    diag4_raw = diagnose(TYPE_ERROR_SOURCE.encode("utf-8"))
    if diag4_raw is None or diag4_raw.get("kind") != "type":
        raise ValueError("oracle missing type error")
    diag4_pos = snap4.diagnostic_position(
        cast("int", diag4_raw["line"]),
        cast("int", diag4_raw["column"]),
    )

    snap5 = SourceSnapshot(uri, 5, UNSUPPORTED_ERROR_SOURCE, 5)
    diag5_raw = diagnose(UNSUPPORTED_ERROR_SOURCE.encode("utf-8"))
    if diag5_raw is None or diag5_raw.get("kind") != "unsupported":
        raise ValueError("oracle missing unsupported error")
    diag5_pos = snap5.diagnostic_position(
        cast("int", diag5_raw["line"]),
        cast("int", diag5_raw["column"]),
    )

    snap6 = SourceSnapshot(uri, 6, RECOVERED_SOURCE, 6)
    facts6 = inspect_source(RECOVERED_SOURCE.encode("utf-8"))
    _require(diagnose(RECOVERED_SOURCE.encode("utf-8")) is None, "oracle recovery source failed")
    _require(translate(RECOVERED_SOURCE.encode("utf-8")).module == "Interop", "oracle module mismatch")

    return {
        "uri": uri,
        "capabilities": {
            "positionEncoding": "utf-16",
            "hoverProvider": True,
            "definitionProvider": True,
            "referencesProvider": True,
            "documentSymbolProvider": True,
            "inlayHintProvider": True,
            "documentFormattingProvider": True,
            "semanticTokensProvider": {
                "legend": {
                    "tokenTypes": list(SEMANTIC_TOKEN_TYPES),
                    "tokenModifiers": list(SEMANTIC_TOKEN_MODIFIERS),
                },
                "full": True,
                "range": False,
            },
            "textDocumentSync": {
                "openClose": True,
                "change": 2,
                "save": {"includeText": False},
            },
        },
        "stage1": {
            "hover_limit": project(snap1, facts1, "textDocument/hover", (2, 17), False),
            "hover_square_call": project(snap1, facts1, "textDocument/hover", (6, 20), False),
            "hover_multiplier": project(snap1, facts1, "textDocument/hover", (6, 27), False),
            "hover_scaled": project(snap1, facts1, "textDocument/hover", (7, 6), False),
            "hover_non_symbol": project(snap1, facts1, "textDocument/hover", (0, 3), False),
            "hover_half_open_end": project(snap1, facts1, "textDocument/hover", (6, 26), False),
            "definition_square_call": project(snap1, facts1, "textDocument/definition", (6, 20), False),
            "definition_branch_then": project(snap1, facts1, "textDocument/definition", (11, 11), False),
            "definition_branch_else": project(snap1, facts1, "textDocument/definition", (14, 11), False),
            "references_explicit_incl": project(snap1, facts1, "textDocument/references", (8, 10), True),
            "references_explicit_excl": project(snap1, facts1, "textDocument/references", (8, 10), False),
            "document_symbols": project(snap1, facts1, "textDocument/documentSymbol", None, False),
            "inlay_hints_full": project(
                snap1, facts1, "textDocument/inlayHint", None, False, ((0, 0), (17, 0))
            ),
            "inlay_hints_subrange": project(
                snap1, facts1, "textDocument/inlayHint", None, False, ((7, 0), (8, 0))
            ),
            "semantic_tokens_initial": project(
                snap1, facts1, "textDocument/semanticTokens/full", None, False
            ),
        },
        "stage2": {
            "formatting_edits_initial": formatting_edits(snap1, fmt1),
            "formatted_buffer_text": FORMATTED_SOURCE,
            "formatting_edits_idempotent": formatting_edits(snap2, fmt2),
            "semantic_tokens_formatted": project(
                snap2, facts2, "textDocument/semanticTokens/full", None, False
            ),
        },
        "stage3": {
            "hover_square_unicode_doc": project(snap3, facts3, "textDocument/hover", (6, 17), False),
        },
        "stage4": {
            "diagnostic": {
                "line": diag4_pos["line"],
                "character": diag4_pos["character"],
                "end_line": diag4_pos["line"],
                "end_character": diag4_pos["character"],
                "code": "type",
                "severity": 1,
                "source": "vela-pure-prototype",
                "message": str(diag4_raw["message"]),
            },
            "broken_hover": None,
            "broken_definition": None,
            "broken_references": [],
            "broken_document_symbols": [],
            "broken_inlay_hints": [],
            "broken_formatting": [],
            "broken_semantic_tokens": {"data": []},
        },
        "stage5": {
            "diagnostic": {
                "line": diag5_pos["line"],
                "character": diag5_pos["character"],
                "end_line": diag5_pos["line"],
                "end_character": diag5_pos["character"],
                "code": "unsupported",
                "severity": 1,
                "source": "vela-pure-prototype",
                "message": str(diag5_raw["message"]),
            },
        },
        "stage6": {
            "recovered_hover_square": project(snap6, facts6, "textDocument/hover", (11, 22), False),
            "recovered_definition_multiplier": project(
                snap6, facts6, "textDocument/definition", (11, 29), False
            ),
            "recovered_inlay_hints": project(
                snap6, facts6, "textDocument/inlayHint", None, False, ((0, 0), (25, 0))
            ),
            "recovered_semantic_tokens": project(
                snap6, facts6, "textDocument/semanticTokens/full", None, False
            ),
        },
    }


def verify_client_observation(observation: dict[str, object], oracle: dict[str, object]) -> None:
    """Verify a client's recorded scenario observations against the independent oracle."""
    label = str(observation.get("client", "unknown"))
    _require(observation.get("offset_encoding") == "utf-16", f"{label}: offset_encoding is not utf-16")
    _require(
        observation.get("server_capabilities") == oracle["capabilities"],
        f"{label}: negotiated server_capabilities differ from oracle",
    )
    for provider in ("completionProvider", "renameProvider"):
        _require(
            provider not in _object(observation.get("server_capabilities")),
            f"{label}: unimplemented {provider} advertised",
        )

    stage1 = _object(observation.get("stage1"), f"{label}.stage1")
    oracle1 = _object(oracle["stage1"])
    _require(stage1.get("diagnostics") == [], f"{label}: stage1 initial diagnostics not empty")
    for key, expected in oracle1.items():
        _require(stage1.get(key) == expected, f"{label}: stage1.{key} mismatch")
    if "goto_definition_cursor_1based" in stage1:
        _require(
            stage1["goto_definition_cursor_1based"] == [5, 18],
            f"{label}: :LspGotoDefinition landed at wrong 1-based cursor {stage1['goto_definition_cursor_1based']!r}",
        )

    stage2 = _object(observation.get("stage2"), f"{label}.stage2")
    oracle2 = _object(oracle["stage2"])
    _require(stage2.get("diagnostics") == [], f"{label}: stage2 formatted diagnostics not empty")
    for key, expected in oracle2.items():
        _require(stage2.get(key) == expected, f"{label}: stage2.{key} mismatch")

    stage3 = _object(observation.get("stage3"), f"{label}.stage3")
    oracle3 = _object(oracle["stage3"])
    _require(stage3.get("diagnostics") == [], f"{label}: stage3 Unicode doc diagnostics not empty")
    _require(
        stage3.get("hover_square_unicode_doc") == oracle3["hover_square_unicode_doc"],
        f"{label}: stage3.hover_square_unicode_doc mismatch",
    )

    stage4 = _object(observation.get("stage4"), f"{label}.stage4")
    oracle4 = _object(oracle["stage4"])
    _require(
        stage4.get("diagnostics") == [oracle4["diagnostic"]],
        f"{label}: stage4 type diagnostic mismatch: {stage4.get('diagnostics')!r}",
    )
    for key in (
        "broken_hover",
        "broken_definition",
        "broken_references",
        "broken_document_symbols",
        "broken_inlay_hints",
        "broken_formatting",
        "broken_semantic_tokens",
    ):
        _require(stage4.get(key) == oracle4[key], f"{label}: stage4.{key} exposed stale facts")

    stage5 = _object(observation.get("stage5"), f"{label}.stage5")
    oracle5 = _object(oracle["stage5"])
    _require(
        stage5.get("diagnostics") == [oracle5["diagnostic"]],
        f"{label}: stage5 unsupported diagnostic mismatch: {stage5.get('diagnostics')!r}",
    )

    stage6 = _object(observation.get("stage6"), f"{label}.stage6")
    oracle6 = _object(oracle["stage6"])
    _require(stage6.get("diagnostics") == [], f"{label}: stage6 recovery diagnostics not empty")
    for key, expected in oracle6.items():
        _require(stage6.get(key) == expected, f"{label}: stage6.{key} mismatch")


def verify_wire_transcript(
    transcript_payload: dict[str, object],
    *,
    require_ranged_change: bool,
) -> dict[str, object]:
    """Verify a server-recorded bidirectional JSON-RPC wire transcript."""
    _require(
        transcript_payload.get("exit_code") == 0,
        f"wire transcript recorded non-zero exit_code: {transcript_payload.get('exit_code')!r}",
    )
    frames = _array(transcript_payload.get("frames"), "transcript.frames")
    _require(len(frames) >= 40, f"wire transcript has too few frames: {len(frames)}")

    client_methods: list[str] = []
    server_methods: list[str] = []
    request_by_id: dict[object, str] = {}
    correlated_responses = 0
    ranged_change_count = 0
    same_line_unicode_ranged_change = False
    published_codes: list[list[str]] = []

    for expected_index, item in enumerate(frames):
        frame = _object(item, f"frame[{expected_index}]")
        _require(frame.get("index") == expected_index, f"frame index mismatch at {expected_index}")
        direction = frame.get("direction")
        message = _object(frame.get("message"), f"frame[{expected_index}].message")
        _require(message.get("jsonrpc") == "2.0", f"frame[{expected_index}] missing jsonrpc 2.0")

        if direction == "client_to_server":
            method = str(message.get("method", ""))
            _require(bool(method), f"client frame[{expected_index}] missing method")
            client_methods.append(method)
            if "id" in message:
                req_id = message["id"]
                _require(req_id not in request_by_id, f"duplicate client request id {req_id!r}")
                request_by_id[req_id] = method
            if method == "textDocument/didChange":
                params = _object(message.get("params"))
                changes = _array(params.get("contentChanges"))
                for raw_change in changes:
                    change = _object(raw_change)
                    if "range" in change:
                        ranged_change_count += 1
                        span = _object(change["range"])
                        start = _object(span.get("start"))
                        if start.get("line") == 5:
                            same_line_unicode_ranged_change = True
        elif direction == "server_to_client":
            if "method" in message:
                method = str(message["method"])
                server_methods.append(method)
                if method == "textDocument/publishDiagnostics":
                    params = _object(message.get("params"))
                    diags = _array(params.get("diagnostics"))
                    codes: list[str] = []
                    for raw_diag in diags:
                        diag = _object(raw_diag)
                        data = _object(diag.get("data"))
                        _require(
                            data.get("unqualified") is True
                            and isinstance(data.get("snapshot"), str)
                            and isinstance(data.get("generation"), int),
                            "published diagnostic missing unqualified snapshot provenance",
                        )
                        codes.append(str(diag.get("code", "")))
                    published_codes.append(codes)
            else:
                _require("id" in message, f"server response frame[{expected_index}] missing id")
                req_id = message["id"]
                _require(req_id in request_by_id, f"uncorrelated server response id {req_id!r}")
                _require("error" not in message, f"unexpected error reply on wire: {message!r}")
                correlated_responses += 1
        else:
            raise ValueError(f"invalid frame direction: {direction!r}")

    _require(
        client_methods[0] == "initialize" and client_methods[1] == "initialized",
        f"session did not begin with initialize -> initialized: {client_methods[:3]!r}",
    )
    _require(
        client_methods[-2:] == ["shutdown", "exit"],
        f"session did not end with shutdown -> exit: {client_methods[-3:]!r}",
    )
    required_methods = {
        "initialize",
        "initialized",
        "textDocument/didOpen",
        "textDocument/didChange",
        "textDocument/didClose",
        "textDocument/hover",
        "textDocument/definition",
        "textDocument/references",
        "textDocument/documentSymbol",
        "textDocument/inlayHint",
        "textDocument/formatting",
        "textDocument/semanticTokens/full",
        "workspace/didChangeConfiguration",
        "workspace/didChangeWatchedFiles",
        "$/cancelRequest",
        "shutdown",
        "exit",
    }
    missing = required_methods - set(client_methods)
    _require(not missing, f"wire transcript missing required client methods: {sorted(missing)}")
    _require(
        correlated_responses == len(request_by_id),
        f"request/response count mismatch: {len(request_by_id)} requests vs {correlated_responses} responses",
    )
    _require(
        ["type"] in published_codes and ["unsupported"] in published_codes and published_codes[-1] == [],
        f"wire transcript missing expected diagnostic lifecycle: {published_codes!r}",
    )
    if require_ranged_change:
        _require(ranged_change_count > 0, "incremental client session sent no ranged didChange edits")
        _require(
            same_line_unicode_ranged_change,
            "incremental client session did not send a ranged edit after 😀 on line 5",
        )
    return {
        "frame_count": len(frames),
        "client_frame_count": len(client_methods),
        "server_frame_count": len(frames) - len(client_methods),
        "request_count": len(request_by_id),
        "ranged_did_change_count": ranged_change_count,
        "same_line_unicode_ranged_change": same_line_unicode_ranged_change,
        "diagnostic_publications": len(published_codes),
    }


def _verify_editor_session_artifacts(
    target_file: Path,
    client_out_file: Path,
    transcript_file: Path,
    *,
    label: str,
    sentinel_error: str,
    require_ranged_change: bool,
) -> tuple[str, str, dict[str, object]]:
    _require(target_file.read_text(encoding="utf-8") == DISK_SENTINEL, sentinel_error)
    observation_raw = client_out_file.read_bytes()
    transcript_raw = transcript_file.read_bytes()
    observation = _object(json.loads(observation_raw), f"{label} observation")
    transcript = _object(json.loads(transcript_raw), f"{label} transcript")
    oracle = expected_scenario_oracle(str(observation.get("uri", "")))
    verify_client_observation(observation, oracle)
    summary = verify_wire_transcript(transcript, require_ranged_change=require_ranged_change)
    return _sha256(observation_raw), _sha256(transcript_raw), summary


def _run_neovim_session(
    nvim_exe: Path,
    run_py: Path,
    session_dir: Path,
) -> dict[str, object]:
    workspace = session_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    target_file = workspace / "interop.vela"
    target_file.write_text(DISK_SENTINEL, encoding="utf-8", newline="")

    script_file = session_dir / "neovim_client.lua"
    script_file.write_text(NEOVIM_SCRIPT, encoding="utf-8", newline="")
    transcript_file = session_dir / "neovim-transcript.json"
    client_out_file = session_dir / "neovim-observation.json"

    env = os.environ.copy()
    env.update(
        VELA_TARGET_FILE=str(target_file),
        VELA_PYTHON_EXE=sys.executable,
        VELA_RUN_PY=str(run_py),
        VELA_TRANSCRIPT_FILE=str(transcript_file),
        VELA_CLIENT_OUT=str(client_out_file),
    )
    started = time.monotonic()
    done = subprocess.run(
        [str(nvim_exe), "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", str(script_file)],
        cwd=workspace,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    elapsed = round(time.monotonic() - started, 4)
    _require(
        done.returncode == 0,
        f"Neovim headless session exited {done.returncode}: {done.stderr.strip() or done.stdout.strip()}",
    )
    obs_sha, tx_sha, summary = _verify_editor_session_artifacts(
        target_file,
        client_out_file,
        transcript_file,
        label="neovim",
        sentinel_error="Neovim session modified or replaced the on-disk sentinel file",
        require_ranged_change=True,
    )
    return {
        "client": "neovim",
        "version": NEOVIM_VERSION,
        "seconds": elapsed,
        "observation_sha256": obs_sha,
        "transcript_sha256": tx_sha,
        "summary": summary,
    }


def _run_vim_session(
    vim_exe: Path,
    plugin_root: Path,
    run_py: Path,
    session_dir: Path,
    *,
    incremental: bool,
) -> dict[str, object]:
    mode_tag = "incremental" if incremental else "full"
    workspace = session_dir / f"workspace-{mode_tag}"
    workspace.mkdir(parents=True, exist_ok=True)
    target_file = workspace / "interop.vela"
    target_file.write_text(DISK_SENTINEL, encoding="utf-8", newline="")

    script_file = session_dir / f"vim_client_{mode_tag}.vim"
    script_file.write_text(VIM_SCRIPT, encoding="utf-8", newline="")
    transcript_file = session_dir / f"vim-{mode_tag}-transcript.json"
    client_out_file = session_dir / f"vim-{mode_tag}-observation.json"

    env = os.environ.copy()
    env.update(
        VELA_YEGAPPAN_LSP_ROOT=plugin_root.as_posix(),
        VELA_TARGET_FILE=target_file.as_posix(),
        VELA_PYTHON_EXE=Path(sys.executable).as_posix(),
        VELA_RUN_PY=run_py.as_posix(),
        VELA_TRANSCRIPT_FILE=transcript_file.as_posix(),
        VELA_CLIENT_OUT=client_out_file.as_posix(),
        VELA_VIM_INCREMENTAL="1" if incremental else "0",
    )
    started = time.monotonic()
    done = subprocess.run(
        [
            str(vim_exe),
            "-u",
            "NONE",
            "-U",
            "NONE",
            "-i",
            "NONE",
            "--noplugin",
            "-N",
            "--not-a-term",
            "--cmd",
            "set nomore | set debug=beep | set encoding=utf-8 | set noswapfile",
            "-S",
            str(script_file),
            "-c",
            "qall!",
        ],
        cwd=workspace,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    elapsed = round(time.monotonic() - started, 4)
    err_file = Path(f"{client_out_file}.err")
    err_detail = err_file.read_text(encoding="utf-8").strip() if err_file.is_file() else ""
    _require(
        done.returncode == 0 and client_out_file.is_file(),
        f"Vim ({mode_tag}) session exited {done.returncode}: {err_detail or done.stderr.strip() or done.stdout.strip()}",
    )
    obs_sha, tx_sha, summary = _verify_editor_session_artifacts(
        target_file,
        client_out_file,
        transcript_file,
        label=f"vim ({mode_tag})",
        sentinel_error=f"Vim ({mode_tag}) session modified or replaced the on-disk sentinel file",
        require_ranged_change=incremental,
    )
    return {
        "client": "vim-yegappan-lsp",
        "version": VIM_VERSION,
        "plugin_commit": YEGAPPAN_LSP_COMMIT,
        "sync_mode": mode_tag,
        "seconds": elapsed,
        "observation_sha256": obs_sha,
        "transcript_sha256": tx_sha,
        "summary": summary,
    }


def _default_cache_root() -> Path:
    return Path(tempfile.gettempdir()) / "vela-lsp-clients-v1"


def qualify_clients(*, cache_root: Path | None = None) -> dict[str, object]:
    """Authenticate and run the pinned Neovim and Vim LSP clients against vela-lsp."""
    root = Path(__file__).resolve().parents[2]
    run_py = root / "tools" / "run.py"
    effective_cache = _default_cache_root() if cache_root is None else cache_root
    effective_cache.mkdir(parents=True, exist_ok=True)
    downloads_dir = effective_cache / "downloads"

    with FileLock(effective_cache / "clients.lock", timeout=TIMEOUT_SECONDS):
        stage_dir = Path(tempfile.mkdtemp(prefix="run-", dir=effective_cache))
        try:
            nvim_exe, nvim_meta = _stage_neovim(downloads_dir, stage_dir)
            vim_exe, plugin_root, vim_meta = _stage_vim_and_plugin(downloads_dir, stage_dir)

            neovim_run = _run_neovim_session(nvim_exe, run_py, stage_dir / "neovim-session")
            vim_full_run = _run_vim_session(
                vim_exe,
                plugin_root,
                run_py,
                stage_dir / "vim-session",
                incremental=False,
            )
            vim_inc_run = _run_vim_session(
                vim_exe,
                plugin_root,
                run_py,
                stage_dir / "vim-session",
                incremental=True,
            )
            key = _platform_key()
            return {
                "schema": 1,
                "scope": "vela-lsp-two-client-interoperability",
                "status": "passed",
                "platform": {"os": key[0], "arch": key[1]},
                "clients": {
                    "neovim": nvim_meta,
                    "vim": vim_meta,
                },
                "sessions": {
                    "neovim": neovim_run,
                    "vim_full_sync": vim_full_run,
                    "vim_incremental_sync": vim_inc_run,
                },
            }
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)
