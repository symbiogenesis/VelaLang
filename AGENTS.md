# Working rules

Read [README.md](README.md) first for the project's purpose, design goals, and current status.

[PLAN.md](PLAN.md) is the source of truth for all outstanding work.

AGENTS.md owns shared agent instructions. Edit shared rules here. The linked artifacts own the detailed contracts summarized below; check them before changing the relevant area and resolve disagreements at their source.

Follow the [git workflow](#git-workflow-and-worktrees) and [validation handoff](#tool-execution-and-validation):
develop in dedicated worktree(s), record each logical change in a separate commit,
merge back to local `main`, finish validation locally, and never push to remote `main`
or dispatch hosted CI.

## Repository map

| Artifact | Purpose |
| --- | --- |
| [README.md](README.md) | Overview, scope, and document map |
| [docs/language/reference.md](docs/language/reference.md) | Vela language reference and semantic rules |
| [docs/language/surface-grammar.md](docs/language/surface-grammar.md) | Lexical, syntactic, and formatting rules |
| [docs/tooling/elaboration-prototype.md](docs/tooling/elaboration-prototype.md) | Dependent mathematics, elaboration, and proof kernel boundary |
| [docs/assurance/verification-strategy.md](docs/assurance/verification-strategy.md) | Mechanization, proof-tooling qualification, and extraction boundaries |
| [docs/tooling/tooling-protocols.md](docs/tooling/tooling-protocols.md) | Formatter, linter, LSP, and generated-test contracts |
| [docs/tooling/playground.md](docs/tooling/playground.md) | Browser playground architecture and security boundary |
| [PLAN.md](PLAN.md) | Backlog, build order, acceptance predicates, and execution state |
| [docs/assurance/completion-log.md](docs/assurance/completion-log.md) | Recorded landing evidence |
| [tools/README.md](tools/README.md) | Commands, toolchain, validation, and tool-development rules |
| [COPYRIGHT.md](COPYRIGHT.md) | Repository licensing and file-marking policy |
| [THIRD-PARTY.md](THIRD-PARTY.md) | Upstream licenses and incorporation status |

## Before editing a document

- **Use current-state prose.** State the current decision, finding, and evidence; replace superseded accounts instead of appending review or search history. Write `n/a` for a not-applicable table cell, never a blank or bare dash.
- **Link section references to their owners and read their targets.** The closed-world Markdown gate (`python tools/run.py markdown`) verifies every relative link and heading or `<a id="...">` fragment across the tracked corpus.
- **Keep landing evidence in its assigned place.** Landed or struck items have one [completion-log](docs/assurance/completion-log.md) entry with the exact checklist label. Follow the [checklist conventions](PLAN.md#checklist-conventions).

## Before incorporating an upstream

Read the selected revision's own license files at the milestone that would incorporate it. Record the intended use and distribution in [THIRD-PARTY.md](THIRD-PARTY.md), following [the project's licensing rules](COPYRIGHT.md#terms-this-tree-does-not-carry). Do not infer terms from a project's lineage or treat a pin as permission to copy its source.

## Before writing source comments

Use [checked Markdown references](tools/README.md#checked-references-in-source-comments)
when a comment or docstring sends readers to a local file, document section, or
supported declaration. `python tools/run.py check` reports stale references
across tracked Python, OCaml, Menhir, Coq, JavaScript, and Vela sources.

## Git workflow and worktrees

- **Work in worktrees.** Put changes into dedicated Git worktree(s) under `.worktrees/` (`git worktree add .worktrees/<branch> -b <branch>`) rather than making edits directly on `main`.
- **Commit logical changes separately.** Record each logical change in its own separate commit. Stage intended deliverables explicitly by path (`git status --short`, `git diff -- <path>`, and `git add -- <path>`); never use `git add -A`.
- **Merge back to local `main` and clean up.** After validation passes, merge the worktree branch(es) back into local `main` using a fast-forward or regular merge that preserves the individual logical commits on `main`, then remove the temporary worktree (`git worktree remove .worktrees/<branch>`) and delete the merged branch (`git branch -d <branch>`).
- **Never push to remote `main`.** Do not push to remote `main` or dispatch hosted CI unless the user explicitly directs that action.

## Tool execution and validation

Use one universal Python minor version everywhere. `project.requires-python` in
[tools/pyproject.toml](tools/pyproject.toml) is its sole owner. The bootstrap,
Windows host, WSL guest, CI, standalone scripts, and developer commands all require
that same version; do not maintain older-version compatibility paths or separate
interpreter floors. Upgrade every consumer together when changing the owner.

Use `python tools/run.py <command>` on Windows; it dispatches guest-only commands into WSL. On Linux, including the WSL guest, use `python3 tools/run.py <command>` directly. `python tools/run.py --help` lists commands and `python tools/run.py <command> --help` gives their options. Read [the tool guide](tools/README.md) before changing Python tools or their configuration.

For a settled change:

1. Develop in dedicated worktree(s) and commit each logical change separately, staging intended deliverables by path (`git status --short` and `git diff -- <path>`; never use `git add -A`).
2. Run `python tools/run.py gate` to execute the full static gate (`check`, `markdown`, and `typecheck`) and `python tools/run.py test` to run the behavioral test suite.
3. Merge the validated worktree branch(es) back to local `main` (preserving the individual logical commits) and remove the worktree(s).
4. Never push to remote `main` or dispatch hosted CI unless the user explicitly directs that action.

`python tools/run.py validate` runs the required gate and behavioral suite
sequentially. The [validation profiles](tools/README.md#validation-profiles)
describe the broader local `--full` qualification and the narrower `--static`
CI checks; `--static` alone does not satisfy the settled-change handoff.
