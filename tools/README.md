# VelaLang Tools

`python tools/run.py` is the single entry point for the VelaLang toolchain and test runner.

## Commands

| Command | Lane | Purpose |
| --- | --- | --- |
| `python tools/run.py test` | host / guest | Run the `test_vela*.py` behavioral test suite |
| `python tools/run.py typecheck` | host | Typecheck the Python tools under `mypy` and `basedpyright` |
| `python tools/run.py prepare python` | host / guest | Check and format Python sources with `ruff` |
| `python tools/run.py vela` | host | Pure Vela prototype checker, formatter, linter, Gallina emitter, and generated-test runner |
| `python tools/run.py vela-lsp` | host | Pure Vela Language Server Protocol server over stdio |
| `python tools/run.py vela-playground` | guest (`[wsl]`) | Unified Vela browser playground with dependent mathematics |
| `python tools/run.py vela-parser` | guest (`[wsl]`) | Menhir parser build/qualification, dependent elaboration, first-slice harness, and Rocq kernel replay |
