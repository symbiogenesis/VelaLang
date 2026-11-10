# Copyright and Licensing

Copyright 2026 Edward Miller.

*Two licenses govern this repository, as declared in [REUSE.toml](REUSE.toml). Where this summary and a license file disagree, the license file governs. [THIRD-PARTY.md](THIRD-PARTY.md) records third-party dependencies, development tools, and reference readings.*

## The map

| Path | License | Ground |
| --- | --- | --- |
| Every original `.md` file (including [README.md](README.md), [PLAN.md](PLAN.md), and Markdown specifications under [docs/](docs/)) and `docs/evidence/*.json` | `CC-BY-4.0`, in [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) | Language specifications and design documents meant to be cited, quoted, and adapted. |
| Every non-Markdown original file, including [.github/](.github/), [examples/](examples/), [tools/](tools/), the GitHub Pages assets under [docs/](docs/) (`*.html`, `*.mjs`, `*.css`), [.editorconfig](.editorconfig), [.gitattributes](.gitattributes), [.gitignore](.gitignore), and [REUSE.toml](REUSE.toml) | `Apache-2.0`, in [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt) | Software and patent grant for the toolchain, parser, elaborator, playground, and verification harnesses. |
| [tools/uv.lock](tools/uv.lock) | `Apache-2.0`, via [REUSE.toml](REUSE.toml) | Resolver-generated dependency lock metadata recording package names, versions, sources, and SHA-256 checksums; each upstream package retains its own terms. |
| [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt), [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) | the stewards' own terms | Verbatim license texts required by the REUSE Specification v3.3. |

## Marking a new file

Every original file whose format admits comments opens with an SPDX header in that format's comment syntax:

```text
# SPDX-License-Identifier: Apache-2.0
```

`python tools/run.py check` reads the identifier from that block, checks every markable file against it, and runs the pinned FSFE `reuse lint` checker against [REUSE.toml](REUSE.toml) and [LICENSES/](LICENSES/). Any file that is unmarked, carries another identifier, uses the wrong comment syntax, or has an unrecognized file extension is reported as a finding.

Opening mark syntax by file kind:

- `# ...`: Python (`.py`), TOML (`.toml`), YAML (`.yml`, `.yaml`), and root config files (`.editorconfig`, `.gitattributes`, `.gitignore`)
- `/* ... */`: Menhir grammars (`.mly`), C scanners (`.c`), CSS stylesheets (`.css`), and Vela sources (`.vela`, which also admit `// ...`)
- `; ...`: Tree-sitter highlighting queries (`.scm`)
- `(* ... *)`: OCaml sources (`.ml`, `.mli`), ocamllex definitions (`.mll`), and Rocq sources (`.v`)
- `// ...`: JavaScript modules (`.mjs`, `.js`)
- `<!-- ... -->`: HTML documents (`.html`)

These file kinds carry no in-file header and are covered by [REUSE.toml](REUSE.toml):

| Kind | Ground |
| --- | --- |
| `.md` | Covered by path in [REUSE.toml](REUSE.toml). |
| `.json` | JSON admits no comments. |
| `.lock` | Resolver-generated lockfile regenerated without comment headers. |
| `.txt` under `LICENSES/` | Verbatim license texts governed by the REUSE Specification. |

## Terms this tree does not carry

No tracked file is subject to a reciprocal or non-commercial license. That is a property of the current tree maintained by the [implementation plan](PLAN.md)'s milestone gates: an upstream's license is read at the milestone that would incorporate it, never deferred to release. [THIRD-PARTY.md](THIRD-PARTY.md) records the reviewed development tools, browser editor CDN assets, and candidate proof-tooling references.
