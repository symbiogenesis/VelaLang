# VelaLang Tools

`python tools/run.py` is the single entry point for the VelaLang toolchain, static gates, and test runner.

## Commands

| Command | Lane | Purpose |
| --- | --- | --- |
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

## Dependency and version policy

- **Single Python version owner**: `project.requires-python` in [tools/pyproject.toml](pyproject.toml) (`>=3.14,<3.15`) is the sole owner of the supported Python minor version.
- **Exact checker pins**: `dependency-groups.dev` in [tools/pyproject.toml](pyproject.toml) pins exact versions of `ty`, `ruff`, `rumdl`, `reuse`, and `charset-normalizer`, resolved with `no-build = true`, `python-downloads = "never"`, and `exclude-newer = "3 days"` in [tools/uv.lock](uv.lock).
- **Reviewed checker schemas**: [tools/ty.toml](ty.toml), [tools/ruff.toml](ruff.toml), and [tools/rumdl.toml](rumdl.toml) are validated against [tools/ty-config.schema.json](ty-config.schema.json), [tools/ruff-config.schema.json](ruff-config.schema.json), and [tools/rumdl-config.schema.json](rumdl-config.schema.json) before any checker runs.

<a id="checked-references-in-source-comments"></a>

## Checked references in source comments

Inline Markdown links in source comments and Python docstrings (`[label](target)` and `[label](target#fragment)`) are checked by `python tools/run.py check` across tracked `.py`, `.vela`, `.ml`, `.mli`, `.mll`, `.mly`, `.v`, `.mjs`, `.js`, `.css`, `.yml`, and `.yaml` files. Relative paths resolve from the containing source file's directory against the Git index, and `#fragment` anchors resolve against the target Markdown document's headings and `<a id="...">` bookmarks.
