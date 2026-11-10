# Third-Party Software and References

This file records third-party dependencies, development tools, and reference readings for the VelaLang repository, following [COPYRIGHT.md](COPYRIGHT.md).

## CI environment setup

The [static workflow](.github/workflows/static.yml) invokes `actions/setup-python`
v7.0.0 at `5fda3b95a4ea91299a34e894583c3862153e4b97` to select the Python minor
owned by [tools/pyproject.toml](tools/pyproject.toml). Its revision's
[LICENSE](https://github.com/actions/setup-python/blob/5fda3b95a4ea91299a34e894583c3862153e4b97/LICENSE)
was read on 2026-11-09: MIT, copyright 2018 GitHub, Inc. and contributors.
The action runs as a hosted development tool with its upstream notices; no action
source or runtime binary is copied into this tree or a Vela/VerifiedOS image.
The workflow installs the existing exact `uv` version from that same manifest
and synchronizes the repository's locked Python dependencies.

<a id="browser-editor-assets"></a>

## Browser playground assets

The [Vela playground](docs/tooling/playground.md) loads `monaco-editor` 0.55.1's
browser distribution from its version-pinned jsDelivr package URL. The release's
[LICENSE.txt](https://github.com/microsoft/monaco-editor/blob/v0.55.1/LICENSE.txt),
[package manifest](https://github.com/microsoft/monaco-editor/blob/v0.55.1/package.json),
and [third-party notices](https://github.com/microsoft/monaco-editor/blob/v0.55.1/ThirdPartyNotices.txt)
were read on 2026-11-03: Monaco is MIT, copyright Microsoft Corporation, and
its notices cover bundled TypeScript, Unicode, DOM, WebGL, HTML, beautifier, and
documentation material under their stated terms. The license permits use,
modification, and distribution with its copyright and permission notice. Browser
assets and upstream notices are served directly from the package CDN rather than
vendored into this repository or shipped in a VerifiedOS image.

<a id="independent-trace-importer"></a>

## Independent trace importer

The optional [pure trace qualification](docs/tooling/pure-prototype.md#bounded-compiler-traces)
uses an externally provisioned Perfetto `v58.2` `trace_processor_shell`, revision
`add693d8b338ba9599dbcbc3e300b1ab8c000897`. Its revision's
[LICENSE](https://github.com/google/perfetto/blob/v58.2/LICENSE)
was read on 2026-11-09 (SHA-256
`9a682a56cffc9524dfa9b0b1c0dca9cb81a19e96d5bd0793aaf02c08a95ee7ca`):
Apache-2.0 for the principal work, copyright 2017 The Android Open Source
Project, with the file-specific Chromium BSD notice, syntaqlite Apache-2.0
notice, public-domain parser-grammar declaration and Niels Provos BSD notice
stated in that same file. The reader runs only as an independent local
development tool; no upstream source, executable, library or wrapper is copied
into the tracked tree, compiler runtime or a Vela/VerifiedOS image. This record
does not authorize a distribution closure.

The harness accepts these exact official standalone prebuilts, checking bytes
before and after qualification and checking their reported source revision:

| Target | Official executable | SHA-256 |
| --- | --- | --- |
| Windows AMD64 | [trace_processor_shell.exe](https://commondatastorage.googleapis.com/perfetto-luci-artifacts/v58.2/windows-amd64/trace_processor_shell.exe) | `adfa6bad3d72be3ba9b83fa2b17b69fa13b3ab1cad0f42e52b86188bd5f0f997` |
| Linux AMD64 | [trace_processor_shell](https://commondatastorage.googleapis.com/perfetto-luci-artifacts/v58.2/linux-amd64/trace_processor_shell) | `58042408e6cc861fb1a731c26bb082dc222285561eaa4e12a48a8b2b90dca7b9` |
| Linux ARM64 | [trace_processor_shell](https://commondatastorage.googleapis.com/perfetto-luci-artifacts/v58.2/linux-arm64/trace_processor_shell) | `0e6e0c5452c505c8d46fe472fd196a0d17d963460727e2ce2013b02aa1309555` |

The command requires the reader path explicitly and performs no downloads or
dependency installation. The executable remains in an ignored external-tool
directory alongside the upstream license; retained reports contain Vela-authored
fixture data, SQL observations and tool identities. Qualification of one target
does not claim execution on every target in the pin table or browser UI coverage.

<a id="independent-syntax-consumers"></a>

## Independent syntax consumers

The optional [editor-asset qualification](docs/tooling/highlighting.md) runs
Tree-sitter CLI `0.25.10`, revision
`da6fe9beb4f7f67beb75914ca8e0d48ae48d6406`, as an independent parser/query
consumer and generator. Its revision's
[LICENSE](https://github.com/tree-sitter/tree-sitter/blob/v0.25.10/LICENSE)
was read on 2026-11-09: MIT, copyright 2018-2024 Max Brunsfeld; SHA-256
`5f9cf9fb6acb1972b35ae29119ce563bb60ec097656bc4b69b9bac2d04c7a147`.
The official
[Linux ARM64 release archive](https://github.com/tree-sitter/tree-sitter/releases/download/v0.25.10/tree-sitter-linux-arm64.gz)
has SHA-256 `07fbff8ae0eeb0d3e496e14fc1a30dcc730cc2c97d70e601e5357f2e51958af5`;
its executable has SHA-256
`6329ea4be486c26ef87fdc45ead60c1b1fb9ffab62fe9bd295932ec8e0645751`.
Generated parser C, Tree-sitter runtime headers, compiled language libraries and
the CLI remain in isolated/ignored development directories with upstream
notices; none is copied into tracked source or a Vela/VerifiedOS image. The
tracked grammar, queries and external scanner are original Apache-2.0 work.

The lexical consumer is Microsoft's VS Code tokenization engine
[`vscode-textmate` `9.2.0`](https://registry.npmjs.org/vscode-textmate/-/vscode-textmate-9.2.0.tgz)
(archive SHA-256 `1f4aed19818315f5b2822bf485eb1a9efc02b0a8b88f5d4e9409d6d289ff61cf`)
with [`vscode-oniguruma` `2.0.1`](https://registry.npmjs.org/vscode-oniguruma/-/vscode-oniguruma-2.0.1.tgz)
(archive SHA-256 `3b42911fd9609f2cc3b9c6dd52236b3da73780e633aa7dc381267006b7e7da21`),
running on the existing Node.js `22.22.1` host runtime. Both published packages'
own licenses were read on 2026-11-09: MIT, copyright Microsoft Corporation;
`vscode-textmate/LICENSE.md` SHA-256
`b5cb7ff7859e7d282d98fc43ab081b0dda5dc659dc3385cf65740c759a7e6a6c`
and `vscode-oniguruma/LICENSE.txt` SHA-256
`ddde8aba8fe72b4830e27901fc78733eb6db7b6c653161075de213a6adeda3fd`.
The latter's complete `NOTICES.txt` was also read (SHA-256
`615d94d89eacc046241518c247f6650a5df80d1adf4b284a756f500867620b35`):
its bundled Oniguruma `6.9.5_rev1` is BSD-2-Clause, copyright 2002-2020 K. Kosako.
Their pinned JavaScript/Wasm implementation bytes and release metadata are
checked by the [qualifier](tools/toolchain/highlight_qualification.py).
Packages and notices remain externally provisioned local development tools;
no upstream JavaScript, Wasm, package or Node runtime is vendored, added to the
Python environment or distributed in the syntax extension or a Vela/VerifiedOS
image. The harness records the exact selected Node executable and refuses
changed runtime bytes before report publication. This use grants no additional
runtime or generated-parser distribution closure.

<a id="development-tools-contained-by-use"></a>

## Development parser generator

| Package | Version | License | Role |
| --- | --- | --- | --- |
| Menhir | 20260209 | Generator `GPL-2.0-only`; `MenhirLib`, `MenhirSdk`, `MenhirCST`, and `MenhirGLR` `LGPL-2.0-only WITH OCaml-LGPL-linking-exception` | Parser generator installed in the Sail, QuickChick, CertiRocq, and contained compiler snapshots at 20260209, each installing all five packages. The release `LICENSE` (SHA-256 `9c97527b92b577647880abd2a5eaf5bf0f3b3df1bd09d9f93fc4e103eb1d30d5`, re-read 2026-10-31; source archive [opam SHA-512](https://opam.ocaml.org/packages/menhir/menhir.20260209/) `aafad186f328ae8dd4cc69af0f30c1a0b208cf5148a7a94c150099be03838503c5ec12918de26cd7f794b5a72f114bc1bae8d81058bd0ea10372a3b06818687e`) places the generator under `GPL-2.0-only`, its OCaml runtime libraries and SDK under `LGPL-2.0-only WITH OCaml-LGPL-linking-exception`, and its separately packaged Rocq library `coq-menhirlib` (installed in the CertiRocq snapshot and the private Q35e `vst2` switch; see [its record](https://github.com/symbiogenesis/VerifiedOS/blob/main/tools/opam/c-refinement-qualification-switches.md)) under `LGPL-3.0-or-later`. VerifiedOS Q39 builds the contained compiler's parser from that release and records its vendored Rocq runtime terms in the [license receipt](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/implementation/evidence/q39-20261010-license-readings.json). Vela Q25g runs the code backend only in native build directories, links no Menhir runtime, and retains JSON receipts rather than generated source or binaries. GPL v2 section 0 conditions coverage of generator output on whether the output is a work based on the generator; this reading claims no blanket license over generated artifacts. Distributing generated sources, binaries, or a compiler bootstrap closure requires separate terms qualification under [Q25h](docs/tooling/parser.md#promotion-and-retirement). |

### Vela parser support library

Vela's [Q25h checked-parser and support-library qualification](docs/tooling/parser.md#rocq-support-prerequisite)
builds `coq-menhirlib` from the authenticated Menhir 20260209 archive above.
Its root `LICENSE` (`9c97527b92b577647880abd2a5eaf5bf0f3b3df1bd09d9f93fc4e103eb1d30d5`)
and `coq-menhirlib/LICENSE` (`218c42550a9b4ff6e48bf38218908755fe156b2e5c586531c2eb8893248a102d`,
`LGPL-3.0-or-later`) were re-read on 2026-10-31. The bounded `Interpreter.v`
proof-command relocation and `Validator_complete.v` abstract `IsItemsMap` proof
adaptation, the generated `VelaPureGrammar.v`, the compiled Rocq library, and the
extracted `vela-checked-parser` executable remain in isolated native build
directories with `LICENSE.generator` and `LICENSE.support` staged alongside them.
Only JSON receipts are exported; this use conveys no upstream source, library,
generator, or runtime binary into the tracked tree. Host distribution of
generated sources or binaries retains Q25h's separate terms qualification.

### Vela development and proof-reuse candidates

[Q25x](PLAN.md#q-assessment-actions) qualifies Hypothesis 6.170.14 and its sole
runtime dependency `sortedcontainers` 2.4.0 as an isolated development test
generator under the `2026-10-31T07:17:33Z` dependency cooldown and Python 3.14
floor. The 2026-11-07 reading inspected Hypothesis 6.170.14's `LICENSE.txt`
(SHA-256 `ac89037bac63550644dce8cf32c6765e5fab9dc1a1ce94b89f8a805f341a6750`,
MPL-2.0) across its
[release source archive](https://files.pythonhosted.org/packages/d6/0f/10b2076a1314c554eee58c26e1dbe630fd26a32773df2a63bd5dba5d9947/hypothesis-6.170.14.tar.gz)
(`8272913eb34c4399a88cf8a9ecdb351c9ef8f621c061f2ac323362d4a66b755d`),
[Windows ARM64 wheel](https://files.pythonhosted.org/packages/ab/72/482a68ae0e94b24acd964196cca830d1dd65efbf3d4821599d1c9527f8e2/hypothesis-6.170.14-cp311-abi3-win_arm64.whl)
(`7dbaec9a62b7792b0b04b7ebc933aeafd3ff019b81d67d763c36ebcf4d56f864`,
`hypothesis/_native.pyd`
`b7722a385d97a5ce0e0a5800770516ce5557f4abed4503b12b7f8e6c6a202c3b`),
[Windows x86_64 wheel](https://files.pythonhosted.org/packages/08/c6/9c47f183e5a8a4059d7c1c39e85f7b140f4416961b5ed0dac5d35dc6e1f7/hypothesis-6.170.14-cp314-cp314-win_amd64.whl)
(`31c6a4015c02c45ba0285ff48538f4eb2c2de7e836f313bb8832fd8d86f71d62`,
`hypothesis/_native.cp314-win_amd64.pyd`
`d53f91b1afbf54b0acbfa42b893221e8248f93fb810271eb9973a098231b7cfd`),
[Linux ARM64 wheel](https://files.pythonhosted.org/packages/1c/c3/252db9362dab21e3c3351abb89e715fa1ef598ebaf30abb9c9b1dd3b3aab/hypothesis-6.170.14-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.whl)
(`67d17e8b91d3913e7aa2b1179957df4e0634caea3868b5ba4fe2bf1945334134`,
`hypothesis/_native.cpython-314-aarch64-linux-gnu.so`
`1a25e29e9b879fb3de4bdd805e11d416dc8a4fc62d2f81472095fbfa8630ea61`), and
[Linux x86_64 wheel](https://files.pythonhosted.org/packages/f8/41/573468979e9579eb6df937e6a94c1a944dfe2765c73624156571e3cc4b34/hypothesis-6.170.14-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl)
(`96f9f8a684c88ad2280129b28bc609adb6b31cd63b1b83b397b86d552391e947`,
`hypothesis/_native.cpython-314-x86_64-linux-gnu.so`
`e40780bfbfb364b2fcc2b65e7baba953e4e1eaacb19fdd39578130889f0ec427`).
Within the source archive, `src/hypothesis/vendor/pretty.py`
(`f22120dafc8868a2332b0a212ceea61b2f94ba02329b893eecd495ce35434523`) carries an
MPL-2.0 header and a BSD notice copyright 2007 Armin Ronacher;
`src/hypothesis/vendor/leap-seconds.txt`
(`db5a895f16853b03bfc865e8d68f9fc8710ef1740e3400c701cd46a5bbbc3433`) is public
domain, and `src/hypothesis/vendor/tlds-alpha-by-domain.txt`
(`f9816a9e5f92191d4a3d73045a579f57eda381dd1ad7b4c535505c7ec610218c`) is the IANA
root-zone table. The compiled `hypothesis/_native` extension builds from MPL-2.0
Rust sources (`rust/Cargo.toml`
`e91723305e334b174f6beab1136cccefa1f93af0d44b29effb7d9f00983e0c97` and
`rust/Cargo.lock`
`67625309eeadb4cc462e3e6dbda8f1c90d9321c73ba211babb79e85120def77c`) linking
`pyo3` 0.30.1 and its Cargo closure (`libc` 0.2.186, `once_cell` 1.21.4,
`portable-atomic` 1.13.1, `pyo3-build-config` 0.30.1, `pyo3-ffi` 0.30.1,
`pyo3-macros` 0.30.1, `pyo3-macros-backend` 0.30.1, `proc-macro2` 1.0.106,
`quote` 1.0.46, `syn` 3.0.9, `heck` 0.5.0, `target-lexicon` 0.13.5, and
`unicode-ident` 1.0.24), for which the published wheels bundle no separate crate
license files beyond `LICENSE.txt`. The transitive Python package
`sortedcontainers` 2.4.0 carries `LICENSE`
(`1db7cae7fce6452e2e608e401a0f953e0133e4c2d75db69fb8ae851d2086f5b6`,
Apache-2.0, copyright 2014-2019 Grant Jenks) in both its
[source archive](https://files.pythonhosted.org/packages/e8/c4/ba2f8066cceb6f23394729afe52f3bf7adec04bf9ed2c820b39e19299111/sortedcontainers-2.4.0.tar.gz)
(`25caa5a06cc30b6b83d11423433f65d1f9d76c4c6a0c90e3379eaa43b9bfdb88`) and
[universal wheel](https://files.pythonhosted.org/packages/32/46/9cb0e58b2deb7f82b84065f37f3bffeb12413f947f9388e4cac22c4621ce/sortedcontainers-2.4.0-py2.py3-none-any.whl)
(`a163dcaede0f1c021485e957a39245190e74249897e2ae4b2aa38595db237ee0`).
The candidate remains an isolated development instrument provisioned in a
temporary virtual environment by `vela generated-tests`; no upstream source,
wheel, native extension or reproduction blob is copied, distributed or added to
`tools/pyproject.toml` or `tools/uv.lock`, while minimized counterexamples are
retained as explicit Apache-2.0 regression data under the
[test contract](docs/tooling/tooling-protocols.md#generated-development-tests).
[Q25y](PLAN.md#q-assessment-actions) reuses the locked Menhir `20260209` binary
(`290c659064d26cb1c51b743ec6a414ed4269e7f686821637656d526333c6c7a2`) in
`verifiedos-sail-0.20.3-ocaml-5.4.1` and its
[generator and output reading](#development-tools-contained-by-use):
`menhir --random-sentence` emits only terminal symbol names from the
repository's own Apache-2.0 grammar (`tools/toolchain/parser/parser.mly`),
`menhir --interpret --interpret-show-cst` emits ephemeral bracketed
nonterminal/terminal trees inspected in memory, and retained replay cases store
only Apache-2.0 terminal sequences, rendered Vela sources and expected
observations without linking `menhirLib`, enabling `--table`, or retaining
`--list-errors` / `.messages` catalogs.
[Q25n](PLAN.md#q-assessment-actions), [Q25o](PLAN.md#q-assessment-actions), and
[Q25u](PLAN.md#q-assessment-actions) qualify two independent editor clients
against `vela-lsp` via `python tools/run.py vela-lsp --qualify-clients`
([`lsp_clients.py`](tools/toolchain/lsp_clients.py)). The 2026-11-08 reading
inspected Neovim `v0.11.0` (`Apache-2.0 AND Vim`, copyright 2014-present Neovim
contributors and 1994-2023 Bram Moolenaar), whose root `LICENSE.txt`
(`e1ff044cabc90a87faf9356618a5c43078c020c3c5e98a4dee570dd098da043d`, `Apache-2.0`
plus the Vim license notice) and bundled `netrw` runtime notice
(`share/nvim/runtime/pack/dist/opt/netrw/LICENSE.txt`, Windows
`0dac5aa0e9035a9624a8310aaf5749a94a767651263faadbf85d566dc726a9a4`, Linux
`9c65b12c2e22ab4e628508c7baf96ecbf7016eaa608756ddd8476b5b23e46037`) were
verified across the official
[Windows archive](https://github.com/neovim/neovim/releases/download/v0.11.0/nvim-win64.zip)
(`00ea1a0fd3252a883974a3411159087196924f214000583257188b205d173a23`,
`bin/nvim.exe`
`9f1ef87c6e9222e513bc920246e67ea8e99be1b66f59e25aea6f11801fa9ee3d`,
`bin/lua51.dll`
`d64fae51493f47ec066890cc9e938415648919292a961577040f3df3f356206d`,
`share/nvim/runtime/lua/vim/lsp.lua`
`7afd6fd4d07619dfaf76f3e13c50571f5a5ae6f1a1172710483a5acd2c8a9abd`),
[Linux ARM64 archive](https://github.com/neovim/neovim/releases/download/v0.11.0/nvim-linux-arm64.tar.gz)
(`6959583f45042da20e0a082dc65108725629a4739ab91246c678fd084ecaf50e`, `bin/nvim`
`5f4e2752e39bdf160d621302bb568b66ae6170ce81048abb43b348ed41c54a3f`,
`share/nvim/runtime/lua/vim/lsp.lua`
`8fe04154882cee269190126d67f9b44c276bf710f00ed6dabc5b621bf97bb24d`), and
[Linux x86_64 archive](https://github.com/neovim/neovim/releases/download/v0.11.0/nvim-linux-x86_64.tar.gz)
(`fe0a5bc79e64c5e4d9f844cd96157ebd3919ef1343b329e9ebc3f455924cc7d6`, `bin/nvim`
`1d6c61d3290f4e78c5a0fa10ddb522a1fc6e3ee5cbd71dc294cdd1c73de58384`). The second
independent client combines Vim `9.1.2141` (`Vim AND ISC`, copyright 1994-2023
Bram Moolenaar and 2013-2024 Frank Denis) with `yegappan/lsp` commit
`58eac06e81bad174cfa897614ae01adf0d31d10a` (`MIT`, copyright 2021 Yegappan
Lakshmanan). `yegappan/lsp`'s
[pinned archive](https://codeload.github.com/yegappan/lsp/zip/58eac06e81bad174cfa897614ae01adf0d31d10a)
(`3c7d0eeb410708b0096251401da4a4290e10b3aff233a75358468b69c0f1d9cb`) carries
`LICENSE`
(`1cd90ab40fd08eeff7573eecc935d076e45c7e01e7a86ff96c89f8a58b6094f6`),
`plugin/lsp.vim`
(`3d8d083485fdc56009cfbaee42f2e76f85d87f01d4dc536cb7619dfaa10d04e3`), and
`autoload/lsp/lspserver.vim`
(`816d57d2f5620e22e57ba8ccd63eb60bbabfcf765eca62abc99d870668183b6c`). On
Windows, `lsp_clients.py` authenticates the official
[Vim `v9.1.2141` ARM64 archive](https://github.com/vim/vim-win32-installer/releases/download/v9.1.2141/gvim_9.1.2141_arm64.zip)
(`7d2236366ae48b908b24e098e3cb1983e1cd6e3587ea121b261ecb71aed063ff`, `vim.exe`
`0e6ac7181288b7f880efd03f342c9699124cb8424a2c6f9998832b3bc6297426`, `vim64.dll`
`92a13be885e0b9ce06f69cefd4194b5d37dff306cc7ea4123a635f9afcbd7a26`,
`libsodium.dll`
`515d8f360540fa2a18e9b4402b738a7572cb3ec0b010f446f7a8facf47eeb96a`,
`LICENSE.txt`
`85b94ff37491a7c25873c8b18ba3cb843c7ced100712788e16d80d629d5d5f0d`) or
[x86_64 archive](https://github.com/vim/vim-win32-installer/releases/download/v9.1.2141/gvim_9.1.2141_x64.zip)
(`85ea6c1955770d6a12cf919d279af1c44c7fe48a2e86f767ac9f6c6ba36fb73c`, `vim.exe`
`f79a4bcd8bbcb01d9ce9938ef1890afc35a09d8db85bbb609c84043fe1b66e62`, `vim64.dll`
`0ed4298eda1f55b2f2ed655fc9216c3a5c48f1e1391619fabeed92346a65f131`,
`libsodium.dll`
`f1b56eb55a86edee37a2614c8bd38272ac325ec6fa6fa7a4088a4d1a42815c4c`,
`LICENSE.txt`
`0b3f1f330cb1b179bb17c7c687d4cec601e0aa3462bc7f890ad4c3888d37d720`) with
`doc/uganda.txt`
(`2368b1d5cb54728c1f689130175706dfb43f9798ecf60730f486b44d8944446e`), extracting
only those allowlisted files and `runtime/` into a temporary staging directory
and never extracting the archive's optional `diff.exe`, `libiconv-2.dll`, or
`libintl-8.dll` helpers. On Ubuntu 24.04 (`aarch64`), it authenticates the
system `vim-common` / `vim` `2:9.1.0016-1ubuntu7.10` binary (`/usr/bin/vim.basic`
`600795c5eaa3320daa68a7b56e14efce25bd3bf4bb2181a02a28344f587137a6`,
`/usr/share/vim/vim91/doc/uganda.txt`
`e8863e53a3a6e4e2ae33c4465f189f439d3125a5099865f7b0233d03e13e8226`,
`/usr/share/doc/vim-common/copyright`
`302e996bdc0ed227fafe0531c2b6fb5359c69efe1592f34ba22186be2497c3c9`). Both
clients execute only in ephemeral directories during
`vela-lsp --qualify-clients`; no third-party editor source, plugin, or binary is
copied into the tracked repository.

[CoqEAL and Trocq](docs/assurance/verification-strategy.md#existing-tooling-and-implementation-owners)
remain conditional proof-transfer references. A concrete consumer and separately
priced qualification must select the revision and read its own complete licence
and dependency closure; neither is installed or incorporated by this decision.
QCheck is similarly conditional on an actual OCaml test consumer and has no
selected package. The [Plinth/Plutus paper](docs/assurance/verification-strategy.md#compilation-and-executable-models)
is a compiler-architecture reference only. No software source is taken from its
artifact, and the paper's publication licence supplies no software grant.
