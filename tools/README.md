# VelaLang Tools

`python tools/run.py` is the single entry point for the VelaLang toolchain, static gates, and test runner.

## Commands

| Command | Lane | Purpose |
| --- | --- | --- |
| `python tools/run.py validate` | host / guest | Run the static gate and behavioral suite sequentially with bounded worker concurrency |
| `python tools/run.py validate --full` | host + guest | Run the complete local development qualification profile with native prerequisites required |
| `python tools/run.py validate --static` | host / guest | Run Python and Markdown checks without invoking the native parser |
| `python tools/run.py gate` | host / guest | Run `check`, `markdown`, and `typecheck` in one verdict |
| `python tools/run.py check` | host / guest | Enforce REUSE v3.3, SPDX headers, EditorConfig, glyph hygiene, source-comment links, JavaScript/playground asset bindings, and plan-summary arithmetic |
| `python tools/run.py check --fix` | host / guest | Refresh only the generated estimate table in [PLAN.md](../PLAN.md#current-summary), then run all `check` rules |
| `python tools/run.py markdown` | host / guest | Validate `tools/rumdl.toml` and run closed-world `rumdl` Markdown linting across the corpus |
| `python tools/run.py typecheck` | host / guest | Typecheck and lint `tools/` under pinned `ty` (`linux` + `win32`) and `ruff` |
| `python tools/run.py prepare python` | host / guest | Order imports in explicitly selected `tools/*.py` files with locked `ruff` |
| `python tools/run.py prepare markdown` | host / guest | Format explicitly selected `.md` files with locked `rumdl` |
| `python tools/run.py test` | host / guest | Run the `test_*.py` behavioral test suite |
| `python tools/run.py vela` | host | Pure Vela prototype checker, formatter, linter, Gallina emitter, and generated-test runner |
| `python tools/run.py vela-lsp` | host | Pure Vela Language Server Protocol server over stdio, wire-transcript recorder, and two-client interoperability qualifier |
| `python tools/run.py vela-playground` | guest (`[wsl]`) | Unified Vela browser playground with dependent mathematics |
| `python tools/run.py vela-parser` | guest (`[wsl]`) | Menhir parser build/qualification, syntax campaigns, dependent elaboration, first-slice harness, and Rocq kernel replay |

The test runner reports executed cases and skips separately. By default it omits
`--slow` cases and cases requiring another execution lane or an unavailable
toolchain. `--slow` includes slow cases in the current lane; it does not enable
guest or kernel checks on Windows. Parser and elaborator qualification commands
retain their own native build and replay requirements.

## Validation profiles

`validate` combines the usual `gate` and `test` handoff. It runs one command at a
time and defaults to four test workers; `--jobs N` selects another positive
worker count. The gate shares one indexed document corpus between repository
and Markdown checks. It retains sequential checker execution: overlapping proof
and editor jobs can exhaust the editor workers' independent time budgets.
Each run writes per-step logs under `out/validation/`. A failed or timed-out step
stops the profile and prints its log path and a bounded tail for diagnosis.

`validate --full` requires the pinned Sail and Rocq switches before qualification.
It includes slow behavioral cases, live editor interoperability, isolated
generated tests, fresh checked-parser support qualification, syntax campaigns
and elaboration/kernel replay. Syntax campaigns already include parser
qualification and migration comparison, so the profile does not repeat those
commands. On Windows it also runs the guest behavioral suite in WSL; on Linux
the current suite supplies that coverage once. Required toolchain cases cannot
silently become skips. These are development-tool verdicts; the first-slice
artifact and external compiler/admission requirements retain their own owners.

`validate --static` runs only `typecheck` and `markdown`. The broader `gate` also
checks authored Vela examples through the checked parser and therefore needs the
native runtime, including WSL on Windows. The
[static CI workflow](../.github/workflows/static.yml) uses the narrower profile
on Ubuntu and Windows stock runners. It provides automatic Python and Markdown
regression checks; it supplies no behavioral or native qualification verdict.
Hosted execution remains user-managed under the
[shared workflow](../AGENTS.md#git-workflow-and-worktrees).

## Dependency and version policy

- **Single Python version owner**: `project.requires-python` in [tools/pyproject.toml](pyproject.toml) (`>=3.14,<3.15`) is the sole owner of the supported Python minor version.
- **Exact checker pins**: `dependency-groups.dev` in [tools/pyproject.toml](pyproject.toml) pins exact versions of `ty`, `ruff`, `rumdl`, `reuse`, and `charset-normalizer`, resolved with `no-build = true`, `python-downloads = "never"`, and `exclude-newer = "3 days"` in [tools/uv.lock](uv.lock).
- **Reviewed checker schemas**: [tools/ty.toml](ty.toml), [tools/ruff.toml](ruff.toml), and [tools/rumdl.toml](rumdl.toml) are validated against [tools/ty-config.schema.json](ty-config.schema.json), [tools/ruff-config.schema.json](ruff-config.schema.json), and [tools/rumdl-config.schema.json](rumdl-config.schema.json) before any checker runs.

<a id="checked-references-in-source-comments"></a>

## Checked references in source comments

Inline Markdown links in source comments and Python docstrings (`[label](target)` and `[label](target#fragment)`) are checked by `python tools/run.py check` across tracked `.py`, `.vela`, `.ml`, `.mli`, `.mll`, `.mly`, `.v`, `.mjs`, `.js`, `.css`, `.yml`, and `.yaml` files. Relative paths resolve from the containing source file's directory against the Git index, and `#fragment` anchors resolve against the target Markdown document's headings and `<a id="...">` bookmarks.
