# Third-Party Software and References

This file records third-party dependencies, development tools, and reference readings for the VelaLang repository, following [COPYRIGHT.md](COPYRIGHT.md).

<a id="browser-editor-assets"></a>
<a id="pinned-as-submodules"></a>
<a id="compcert-and-secomp"></a>
<a id="the-cryptography-upstreams"></a>
<a id="vélus"></a>

## Browser playground assets

The local [Vela playground](docs/tooling/playground.md) loads
`monaco-editor` 0.55.1's browser distribution from the version-pinned jsDelivr
package URL. The selected release's own
[LICENSE.txt](https://github.com/microsoft/monaco-editor/blob/v0.55.1/LICENSE.txt)
and [package manifest](https://github.com/microsoft/monaco-editor/blob/v0.55.1/package.json),
with its [third-party notices](https://github.com/microsoft/monaco-editor/blob/v0.55.1/ThirdPartyNotices.txt),
were read on 2026-11-03: Monaco is MIT, copyright Microsoft Corporation. The
notices retain included TypeScript, Unicode, DOM, WebGL, HTML, beautifier and
documentation material under their stated terms.
The license permits use, modification and distribution with its copyright and
permission notice. Browser assets and their upstream notices are served by the
package CDN, rather than copied into this repository or shipped in a VerifiedOS
image. This is a development-host editor dependency; no editor source is
copied or redistributed.

### Vela parser support library

Vela's [Q25h support-library prerequisite](docs/tooling/parser.md#rocq-support-prerequisite)
builds `coq-menhirlib` from the same authenticated Menhir 20260209 archive the
table below records. Its root `LICENSE` was re-read on 2026-10-31 at SHA-256
`9c97527b92b577647880abd2a5eaf5bf0f3b3df1bd09d9f93fc4e103eb1d30d5`;
`coq-menhirlib/LICENSE`, SHA-256
`218c42550a9b4ff6e48bf38218908755fe156b2e5c586531c2eb8893248a102d`,
states `LGPL-3.0-or-later`. The bounded proof-command adaptation, original and
modified sources and compiled Rocq library remain in native build directories.
Only JSON receipts are exported; this use conveys no upstream source, library,
generator or runtime binary. Parser or bootstrap distribution retains Q25h's
separate terms qualification.

### Development tools, contained by use

## Development parser generator

| Package | Version | License | Role |
| --- | --- | --- | --- |
| Menhir | 20260209 | Generator `GPL-2.0-only`; `MenhirLib`, `MenhirSdk`, `MenhirCST` and `MenhirGLR` `LGPL-2.0-only WITH OCaml-LGPL-linking-exception` | Parser generator installed in the Sail, QuickChick, CertiRocq and contained compiler snapshots at 20260209, each installing all five packages. The `LICENSE` that release installs, SHA-256 `9c97527b92b577647880abd2a5eaf5bf0f3b3df1bd09d9f93fc4e103eb1d30d5`, puts the generator under GPL version 2, its runtime libraries and SDK under the Library General Public License version 2 with the static-linking exception, and its separately packaged Rocq library `coq-menhirlib`, which the CertiRocq snapshot installs for CompCert, as the private Q35e `vst2` qualification switch does ([its record](https://github.com/symbiogenesis/VerifiedOS/blob/main/tools/opam/c-refinement-qualification-switches.md)), under `LGPL-3.0-or-later`. Q39 builds the contained compiler's parser from that release and reads its vendored Rocq runtime terms in the [license receipt](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/implementation/evidence/q39-20261010-license-readings.json); the source and compiled parser stay contained. The generator and generated parser sources remain outside the tracked tree. Vela Q25g uses its code backend only in native build directories, links no Menhir runtime, and retains JSON receipts rather than generated source or binaries. The 20260209 source archive was re-read for this use on 2026-10-31: its `LICENSE` has the SHA-256 above and its archive has the [opam-recorded SHA-512](https://opam.ocaml.org/packages/menhir/menhir.20260209/) `aafad186f328ae8dd4cc69af0f30c1a0b208cf5148a7a94c150099be03838503c5ec12918de26cd7f794b5a72f114bc1bae8d81058bd0ea10372a3b06818687e`. GPL section 0 conditions coverage of output on whether it constitutes a work based on the program; this reading grants no blanket licence to generated artifacts. Distribution of generated sources, binaries or a compiler bootstrap closure needs its own terms qualification under [Q25h](docs/tooling/parser.md#promotion-and-retirement). |

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
[Linux x86_64 wheel](https://files.pythonhosted.org/packages/f8/41/573468979e9579eb6df937e6a96c1a944dfe2765c73624156571e3cc4b34/hypothesis-6.170.14-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl)
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
Q25y reuses the selected Menhir and its
[generator and output reading](#development-tools-contained-by-use); it still reads the actual
outputs its additional facilities would retain.

[CoqEAL and Trocq](docs/assurance/verification-strategy.md#existing-tooling-and-implementation-owners)
remain conditional proof-transfer references. A concrete consumer and separately
priced qualification must select the revision and read its own complete licence
and dependency closure; neither is installed or incorporated by this decision.
QCheck is similarly conditional on an actual OCaml test consumer and has no
selected package. The [Plinth/Plutus paper](docs/assurance/verification-strategy.md#compilation-and-executable-models)
is a compiler-architecture reference only. No software source is taken from its
artifact, and the paper's publication licence supplies no software grant.
