# VelaLang

**Vela** is a verification-aware systems and mathematical authoring language designed alongside [VerifiedOS](https://github.com/symbiogenesis/VerifiedOS). It combines explicit ownership and loan modes (`in`, `ref`, `out`), bounded loop and resource contracts, dependent mathematics and first-class proof terms, and hygienic elaboration to Rocq/Gallina (`rocq c` and `rocqchk`) and Clight/CompCert.

## Repository map

| Path | Purpose |
| --- | --- |
| [PLAN.md](PLAN.md) | Vela backlog (`Q25` series), first-release delivery stages, ergonomics roadmap, and whole-system authoring proposals |
| [docs/README.md](docs/README.md) | Index of Vela language specifications, contracts, and extension dossiers |
| [docs/reference.md](docs/reference.md) | Compact language reference for the synchronous first-release surface |
| [docs/first-release.md](docs/first-release.md) | First-release boundary, primitive and module semantics, ownership libraries, and qualification |
| [docs/core-design.md](docs/core-design.md) | Core calculus, explicit loan/ownership rules, refinement tier, and proof obligations |
| [docs/surface-grammar.md](docs/surface-grammar.md) | Concrete syntax, operator precedence, patterns, constants, and ergonomic surface |
| [docs/elaboration-prototype.md](docs/elaboration-prototype.md) | Generic dependent mathematics, first-class proofs, and kernel-honest Rocq replay |
| [docs/vela-parser.md](docs/vela-parser.md) | Menhir development parser, checked-parser promotion contract, and syntax campaigns |
| [docs/lsp-prototype.md](docs/lsp-prototype.md) | Language Server Protocol lifecycle, diagnostics, navigation, hints, and formatting |
| [docs/playground.md](docs/playground.md) | Local browser playground with Monaco editor, pure and dependent elaboration, and expression console |
| [docs/extensions/](docs/extensions/README.md) | Extension dossiers: graded foundation, handlers/async, interior mutability, metaprogramming, assurance profiles, unified source |
| [examples/](examples/) | Authored `.vela` examples (`pure.vela`, `constants.vela`, `expressions.vela`, `surface.vela`, `dependent.vela`, `first_slice.vela`) |
| [tools/toolchain/parser/](tools/toolchain/parser/) | Menhir grammar (`parser.mly`), OCaml lexer (`lexer.mll`), AST, and native driver |
| [tools/toolchain/playground/](tools/toolchain/playground/) | Browser playground UI (`index.html`, `app.mjs`, `style.css`) |
| [tools/toolchain/](tools/toolchain/) | Vela compiler, elaborator, loan analysis, formatter, linter, LSP server, playground worker, and first-slice harness |
| [tools/tests/](tools/tests/) | Behavioral test suite (`test_vela*.py`) |
| [THIRD-PARTY.md](THIRD-PARTY.md) | Third-party dependencies, parser generator readings, and development tool licenses |

## Commands

Run all commands via `python tools/run.py`:

```text
python tools/run.py                      run the behavioral test suite
python tools/run.py test                 run the behavioral test suite
python tools/run.py typecheck            typecheck the Python toolchain
python tools/run.py vela --help          pure Vela CLI, formatter, linter, and Gallina emitter
python tools/run.py vela-lsp --help      pure Vela language server over stdio
python tools/run.py vela-playground      unified Vela browser playground [wsl]
python tools/run.py vela-parser --help   Menhir parser, dependent elaborator, and Rocq replay [wsl]
```
