# Copyright and Licensing

Copyright 2026 Edward Miller.

*Two licenses govern this repository, one per kind of content, and every original tracked path falls under one of them, as declared in [REUSE.toml](REUSE.toml). Where this document and a license file disagree, the license file wins. [THIRD-PARTY.md](THIRD-PARTY.md) carries everything somebody else wrote and the terms it arrives under.*

## The map

| Path | License | Ground |
| --- | --- | --- |
| Every original `.md` file and `docs/evidence/*.json`, including [docs/](docs/) and [README.md](README.md) | `CC-BY-4.0`, in [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) | The prose is a language specification meant to be cited, quoted, and inherited, and a document license says what a software license only gestures at. |
| Every non-Markdown original file, including [tools/](tools/), [.editorconfig](.editorconfig), [.gitattributes](.gitattributes), [.gitignore](.gitignore), and [REUSE.toml](REUSE.toml) | `Apache-2.0`, in [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt) | Explicit software and patent grant for the toolchain, parser, elaborator, playground, and verification harnesses. |
| [tools/uv.lock](tools/uv.lock) | `Apache-2.0`, via [REUSE.toml](REUSE.toml) | Resolver-generated dependency lock metadata recording package names, versions, sources, and SHA-256 checksums; each upstream package retains its own terms. |
| [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt), [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) | the stewards' own terms | Verbatim license texts required by the REUSE Specification v3.3. |

## Marking a new file

Every original file whose kind can carry a comment opens with an SPDX line, in that kind's own comment syntax:

```text
# SPDX-License-Identifier: Apache-2.0
```

`python tools/run.py check` reads the identifier out of that block, holds every markable file against it, and runs the pinned FSFE `reuse lint` checker against [REUSE.toml](REUSE.toml) and [LICENSES/](LICENSES/). A file that arrives unmarked, marked with another identifier, or marked in another kind's comment syntax is a finding. The tool carries an explicit table of comment syntaxes rather than a list of files to skip, so a file kind it has no ruling for is a finding too.

Authored Menhir `.mly` grammars, CSS `.css` stylesheets, and Vela `.vela` sources use `/* ... */` (or `// ...` for `.vela`) for their opening mark; OCaml `.ml`/`.mli` sources, `.mll` lexer definitions, and Coq/Rocq `.v` files use `(* ... *)`; JavaScript `.mjs`/`.js` files use `// ...`; HTML `.html` files use `<!-- ... -->`.

These kinds carry no in-file mark and are covered by [REUSE.toml](REUSE.toml):

| Kind | Ground |
| --- | --- |
| `.md` | The map above and [REUSE.toml](REUSE.toml) already reach it by path. |
| `.json` | JSON admits no comment, so a mark would make the file unparseable. |
| `.lock` | Resolver-generated dependency metadata rather than authored content; the resolver regenerates it without authored headers. |
| `.txt` under `LICENSES/` | Verbatim license texts governed by the REUSE Specification. |

## Terms this tree does not carry

No tracked file is subject to a reciprocal or non-commercial term. That is a property of today's tree rather than a standing guarantee, and the [implementation plan](PLAN.md)'s milestone gates are what preserve it: an upstream's license is read at the milestone that would incorporate it, never at release. [THIRD-PARTY.md](THIRD-PARTY.md) records the reviewed development tools, browser editor CDN assets, and candidate proof-tooling references.
