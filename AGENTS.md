# Working rules

Read [README.md](README.md) first for the project's purpose, design goals, and current status.

[PLAN.md](PLAN.md) is the source of truth for all outstanding work.

AGENTS.md owns shared agent instructions. Edit shared rules here. The linked artifacts own the detailed contracts summarized below; check them before changing the relevant area and resolve disagreements at their source.

Follow the [validation handoff](#tool-execution-and-validation): finish locally,
record the selected checks, and leave all pushes and hosted CI to the user.

## Repository map

| Artifact | Purpose |
| --- | --- |
| [README.md](README.md) | Overview, scope, and document map |
| [docs/reference.md](docs/reference.md) | Vela language reference and semantic rules |
| [docs/surface-grammar.md](docs/surface-grammar.md) | Lexical, syntactic, and formatting rules |
| [docs/elaboration-prototype.md](docs/elaboration-prototype.md) | Dependent mathematics, elaboration, and proof kernel boundary |
| [docs/verification-strategy.md](docs/verification-strategy.md) | Mechanization, proof-tooling qualification, and extraction boundaries |
| [docs/tooling-protocols.md](docs/tooling-protocols.md) | Formatter, linter, LSP, and generated-test contracts |
| [docs/playground.md](docs/playground.md) | Browser playground architecture and security boundary |
| [PLAN.md](PLAN.md) | Backlog, build order, acceptance predicates, and execution state |
| [docs/completion-log.md](docs/completion-log.md) | Recorded landing evidence |
| [tools/README.md](tools/README.md) | Commands, toolchain, validation, and tool-development rules |
| [COPYRIGHT.md](COPYRIGHT.md) | Repository licensing and file-marking policy |
| [THIRD-PARTY.md](THIRD-PARTY.md) | Upstream licenses and incorporation status |

## Before editing a document

- **Use current-state prose.** State the current decision, finding, and evidence; replace superseded accounts instead of appending review or search history. Write `n/a` for a not-applicable table cell, never a blank or bare dash.
- **Link section references to their owners and read their targets.** The closed-world Markdown gate (`python tools/run.py markdown`) verifies every relative link and heading or `<a id="...">` fragment across the tracked corpus.
- **Keep landing evidence in its assigned place.** Landed or struck items have one [completion-log](docs/completion-log.md) entry with the exact checklist label. Follow the [checklist conventions](PLAN.md#checklist-conventions).

## Before incorporating an upstream

Read the selected revision's own license files at the milestone that would incorporate it. Record the intended use and distribution in [THIRD-PARTY.md](THIRD-PARTY.md), following [the project's licensing rules](COPYRIGHT.md#terms-this-tree-does-not-carry). Do not infer terms from a project's lineage or treat a pin as permission to copy its source.

## Before writing source comments

Use [checked Markdown references](tools/README.md#checked-references-in-source-comments)
when a comment or docstring sends readers to a local file, document section, or
supported declaration. `python tools/run.py check` reports stale references
across tracked Python, OCaml, Menhir, Coq, JavaScript, and Vela sources.

## Tool execution and validation

Use one universal Python minor version everywhere. `project.requires-python` in
[tools/pyproject.toml](tools/pyproject.toml) is its sole owner. The bootstrap,
Windows host, WSL guest, CI, standalone scripts, and developer commands all require
that same version; do not maintain older-version compatibility paths or separate
interpreter floors. Upgrade every consumer together when changing the owner.

Use `python tools/run.py <command>` on Windows; it dispatches guest-only commands into WSL. On Linux, including the WSL guest, use `python3 tools/run.py <command>` directly. `python tools/run.py --help` lists commands and `python tools/run.py <command> --help` gives their options. Read [the tool guide](tools/README.md) before changing Python tools or their configuration.

For a settled change:

1. Run `python tools/run.py gate` to execute the full static gate (`check`, `markdown`, and `typecheck`) and `python tools/run.py test` to run the behavioral test suite.
2. Track intended deliverables by path (`git status --short` and `git diff -- <path>`); never use `git add -A`.
3. Never push or dispatch hosted CI unless the user explicitly directs that action.
