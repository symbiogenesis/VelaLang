# VelaLang Plan and Backlog

This document is the source of truth for Vela language design, parser and elaborator qualification, authoring tooling, first-release delivery, and whole-system authoring proposals, extracted from [VerifiedOS](https://github.com/symbiogenesis/VerifiedOS).

## Current Summary

The table estimates completion of the priced development and qualification
backlog, including the supported release, its shared prerequisites and conditional
language/toolchain/whole-system options. The [planning basis](#planning-basis-and-scope)
fixes scope, effort units and reuse assumptions. Completed design decisions and
bounded investigations retain their own acceptance boundaries: Q25w's blocked
investigation is complete, while full first-slice artifact acceptance remains open.

<!-- estimate-summary:start -->
| Measure | Value |
| --- | --- |
| Total estimate midpoint h | 21,457.9 |
| Total estimate range h | 11,179.9–31,735.9 |
| Completed scope h | 411.9 |
| Complete by estimate % | 1.9 |
| Remaining h | 21,046 |
| Open class I h | 2,962 |
| Open class X h | 18,084 |
| Retained completion estimate h | 408.5 |
| Unmeasured completed items | 29 |
<!-- estimate-summary:end -->

The [checklist](#checklist-items-q25-series) owns completion status and the
[calibration record](#calibration-record-q25-series) owns hours. Following
[VerifiedOS's approach](https://github.com/symbiogenesis/VerifiedOS/blob/main/PLAN.md#current-summary),
completed scope sums recorded actual hours, retaining each completed leaf's
estimate when its actual is unavailable. Total midpoint is completed scope plus
open leaf estimates; the range adds open lower and upper bounds to completed
scope. Completion is `100 × completed scope / total midpoint`, rounded to one
decimal (`n/a` when the total is zero). Parents contribute no duplicate hours.
An open leaf needs a priced estimate and range before entering this accounting.

Every open Q25 cell contributes once, including conditional options that are
not release prerequisites. Shared laws and producer semantics belong to their
named cells; adapters and migrations pay only for their additional work. The
remaining estimate covers the finite baseline, not unlimited future support or
unrelated VerifiedOS delivery. This percentage is an effort-weighted planning
indicator, not a release-readiness claim or elapsed-time forecast. The
[completion log](docs/assurance/completion-log.md) owns landing evidence.

`python tools/run.py check` checks the generated table for drift;
`python tools/run.py check --fix` refreshes it from the checklist and calibration
record. Update this scope description when the priced backlog changes.

## Current execution

The current parallel delivery qualifies existing development producers within
their frozen scope and strengthens local receipt integration:

| Slice | Delivered development behavior | Open acceptance boundary |
| --- | --- | --- |
| Mathematical elaboration | Guarded `Option`/`Result` propagation preserves Boolean short-circuiting; unsupported effect sequencing is refused under the [elaboration contract](docs/tooling/elaboration-prototype.md#commands-and-acceptance) | General checked source correspondence and machine-connected composition remain with Q25as/at |
| Pure compiler inspection | `vela inspect` exports versioned source-preserving snapshots, structured pure identifier types and bounded symbol/type/reference queries under the [pure inspection contract](docs/tooling/tooling-protocols.md#pure-development-snapshot-increment) | Wider syntax, typed trees, generated, proof and lowering views retain Q25ch/ci's producer prerequisites |
| Pure semantic editor | Negotiated semantic token deltas reconstruct current pure compiler tokens across unsaved edits under the [LSP contract](docs/tooling/lsp-prototype.md) | Q25ci retains wider producers, editor operations and two-client delta qualification |
| Kernel replay | Imported checker sources and Python dependency owners enter input identity; malformed assumption reports refuse | Kernel checking of emitted terms supplies no source or artifact correspondence |
| Local first-slice source proofs | All 69 exports kernel-replay with an empty solver-trust ledger within unchanged elaboration budgets under [first-slice qualification](docs/language/first-release.md#first-slice-qualification) | Q25ba retains source correspondence and exact-artifact producer joins |
| Local first-slice receipts | Schema-2 binding checks verify retained subjects, capacity and semantic-negative coverage, assumption ledgers and process transcripts as well as producer/tool/runtime/parser identities | Q25ar remains open for external checked producer receipts and complete declared coverage |
| Pure compiler traces | Bounded phase/counter recordings and paired tracing comparisons bind source, producer and measurement metadata under the [trace increment](docs/tooling/pure-prototype.md#bounded-compiler-traces) | Q25cp retains wider phases/workers, external-viewer qualification and runtime closure |

The full first-slice replay reports zero solver-trusted obligations and source
`accepted: true`; its binding check verifies retained evidence without proof replay.
[First-slice qualification](docs/language/first-release.md#first-slice-qualification)
retains unavailable local CompCert replay and the external artifact-acceptance joins.

The [completion log](docs/assurance/completion-log.md) records the scoped landing
evidence. Q25am–aq and the supported-release cells retain their stated entry and
acceptance predicates; these development increments close no whole release cell.

## Planning basis and scope

The open cells price the remaining work for the supported synchronous release
and the optional language, toolchain and whole-system portfolio already described
below. They are prospective attended engineering hours, including design,
implementation or proof construction, independent review preparation, tests,
documentation and initial qualification. They are judgment ranges, not measured
productivity, statistical confidence intervals or calendar promises. The existing
four core estimates and 27 detailed extension ranges are allocated once into
checklist cells; their descriptive owner tables add no second budget.

The baseline is one canonical CHERI-RISC-V profile/ABI and one retained compiler
route. The first release uses the existing packet validator and a second client
selected independently before the trial. Optional software/proof/machine/hardware
migration covers the first-party implementation, proof, configuration and authored
block inventory tracked at
[VerifiedOS revision 3529ecd](https://github.com/symbiogenesis/VerifiedOS/tree/3529ecd08b8288b004d71766066b0c3367b9cb40),
with Vela's existing implementation at `0354004` as the reuse baseline. Inventory
freezing at each option's entry records exact paths, theorem subjects, target
features and permitted generated/imported artifacts; additions require repricing.
No estimate assumes a new processor, arbitrary future language features, a public
package registry, an interactive proof-admission path, or fabrication/laboratory
delivery. Windows/Linux host tooling is included; resident protocol endpoints
are a different product scope from resident compiler rebuilding.

The [shared foundation and retained-route cells](#shared-foundation-and-retained-route)
price the residual work needed by Vela's selected endpoint, retaining VerifiedOS's
machine-logic, byte-instance, scoped-resource, compiler, security and admission
owners. Their already booked narrow Q35/M1/TAL slices are dependencies, not
duplicate charges here. These local allowances neither edit the other project's
estimates nor report its work completed; do not add both repositories' overlapping
totals. Original OS algorithms, device design and unrelated whole-system proofs
remain with their existing owners. Vela migration cells pay for language-specific
representation, transport, replay and adoption, reusing those supplied results.

**Pricing does not open implementation.** Every cell needs its named concrete
inputs, reviewed target/client inventory and acceptance predicate before dispatch.
Missing laws or exhausted investigation budgets stop dependent work. Record a
bounded investigation's result and reprice unresolved implementation explicitly;
never mark a requested theorem, feature or release complete because its allowance
was spent. A proof-producing implementation still needs checked terms and
independent intended-behavior review. New upstream incorporation includes its
revision-specific licence and dependency qualification at that cell's entry.

The supported-release path reuses the validator's source proofs and narrow
lowering, qualifies its exact first-client machine/compiler/security/admission
receipts, then accepts that artifact. Broader represented libraries, packages and
general lowering follow, then the independent package trial, release and one
maintenance rehearsal. Source-to-interpreted-core correspondence belongs to
`core-frontend`; represented-core-to-Clight belongs to `runtime-lowering`;
Clight-to-canonical-Sail belongs to `retained-compiler`; artifact admission
composes those supplied theorems and validates the final image.

Consumers may use an independently checked subset receipt before its producer's
whole checklist cell closes. The first slice needs first-client receipts; the
independent client subsequently needs its own receipts, and shared admission and
receipt-integration cells close only after their complete declared coverage.
Likewise, library source representations/laws unblock per-operation lowering,
whose checked runtime receipts join final library acceptance. No partial receipt
earns whole-cell completion credit. Scoped law/frontend work may run in parallel
once those exact interfaces exist. Extension,
adapter, web-output, native/bootstrap and model/hardware migration cells remain
conditional options; their presence in the total selects no adoption. Independent
proof, native and hardware work retains the joins in the whole-system contract.

Release maintenance and optional-portfolio maintenance each price one finite
coordinated upgrade/requalification cycle after their relevant delivery. Record
actual effort and a new estimate before each later cycle; indefinite operation
has no finite completion percentage. Keep human attended effort, summed
agent-session wall time and machine time in separate ledgers. The historical
actuals do not supply a productivity multiplier for the new research-heavy work,
and the assurance strategy's person-month/year comparisons are not converted
into these hours.

<a id="q-assessment-actions"></a>
<a id="checklist-conventions"></a>

## Checklist items (Q25 series)

Each checklist item pairs with a single [completion-log](docs/assurance/completion-log.md) entry carrying the exact `Q25* · Title` heading when landed, and records its prospective estimate, range, class (`I` implementation or `X` investigation), and actual hours (`n/a` when shared across a batch). The [first-release delivery sequence](#vela-first-release-delivery) governs new Vela work: existing parser, mathematical, and editor increments may finish their frozen qualification, while broader surface and adapter work waits for the concrete synchronous component.

- [x] **Q25 · Design the full graded dependent language and its control and mutation rules**
  - The graded, control, mutation and assurance-policy designs are reviewed together, with implementation debts and admission decisions recorded by Q25d ([note](docs/assurance/completion-log.md#q25-design-the-full-graded-dependent-language-and-its-control-and-mutation-rules))
  - [x] **Q25a · Specify the graded dependent foundation** · 0.2 h actual · agent-parallel
    - Specifies graded dependent rules, schematic derivations and the shared resource interface, with missing laws assigned to the combined review. ([note](docs/assurance/completion-log.md#q25a-specify-the-graded-dependent-foundation))
  - [x] **Q25b · Specify handlers and structured async lifecycles** · 0.2 h actual · agent-parallel
    - Specifies handler capture and resumption, bounded async reactions, cancellation races and terminal-resource accounting. ([note](docs/assurance/completion-log.md#q25b-specify-handlers-and-structured-async-lifecycles))
  - [x] **Q25c · Specify interior mutability and interference guardrails** · 0.2 h actual · agent-parallel
    - Specifies cell and borrow interfaces, snapshot and interference rules, and the scalar counter's commit and reuse protocol. ([note](docs/assurance/completion-log.md#q25c-specify-interior-mutability-and-interference-guardrails))
- [x] **Q25d · Review the combined calculus and price its implementation** · 0.9 h actual · agent-parallel
  - The combined calculus is reviewed against R-05-009's frontend admission and the arm propagated, with the implementation and admission decisions it still owes named at their owners. ([note](docs/assurance/completion-log.md#q25d-review-the-combined-calculus-and-price-its-implementation))
- [x] **Q25e · Build a pure Vela-to-Gallina prototype** · 0.3 h actual · agent-parallel
  - Implements bounded pure-source checking, hygienic Gallina emission and atomic publication with independent translation and rejection cases; kernel replay and stronger language qualification remain open. ([note](docs/assurance/completion-log.md#q25e-build-a-pure-vela-to-gallina-prototype))
- [x] **Q25f · Align the executable Vela subset with its proposed surface** · 0.1 h actual · agent-parallel
  - Aligns public declarations, parameters, bool, local statements, returns and conditional blocks with the proposed Vela surface, retaining explicit limits and the pure translation boundary. ([note](docs/assurance/completion-log.md#q25f-align-the-executable-vela-subset-with-its-proposed-surface))
- [x] **Q25g · Build the Menhir development parser for pure Vela** · 6 h retained estimate, actual n/a · agent-parallel
  - Builds and qualifies the strict locked Menhir (`20260209`) and OCaml (`5.4.1`) pure syntax parser (`vela-parser qualify`) with deterministic regeneration and 70 independent AST/span/refusal fixtures. ([note](docs/assurance/completion-log.md#q25g-build-the-menhir-development-parser-for-pure-vela))
- [x] **Q25h · Qualify checked Vela parsing and retire the Python parser** · 16 h retained estimate, actual n/a · agent-parallel
  - Qualifies the `MenhirLib` support library, drift-checked `VelaPureGrammar.v`, nine zero-axiom Rocq parser theorems, recursive `rocqchk`, and extracted `vela-checked-parser` runtime (`vela-parser support`) across 70 pure and 173 migration fixtures on Linux and Windows, retiring the handwritten Python `_Parser`. ([note](docs/assurance/completion-log.md#q25h-qualify-checked-vela-parsing-and-retire-the-python-parser))
- [x] **Q25i · Extend the Menhir grammar across the Vela authoring surface** · 24 h retained estimate, actual n/a · agent-parallel
  - Extends the single Menhir grammar with the `surface_file` (schema-2) entry covering dependent, resource, contract, grade, handler/task, proof and machine/hardware syntax across 400 independent surface fixtures (`vela-parser qualify`). ([note](docs/assurance/completion-log.md#q25i-extend-the-menhir-grammar-across-the-vela-authoring-surface))
- [x] **Q25j · Prototype path-sensitive loan-end inference over explicit flow facts** · 12 h retained estimate, actual n/a · agent-parallel
  - The bounded explicit-flow diagnostic infers path-specific loan ends while retaining unresolved restoration, interpretation and overlap obligations. ([note](docs/assurance/completion-log.md#q25j-prototype-path-sensitive-loan-end-inference-over-explicit-flow-facts))
- [x] **Q25k · Elaborate generic dependent mathematics and first-class proofs** · 24 h retained estimate, actual n/a · agent-parallel
  - Elaborates generic and dependent mathematics, indexed vectors, fixed-width integers, records with lifted invariants, `Slots`, `out` loans, coherent interfaces, multi-module imports, exhaustive pattern matching and first-class proofs into Gallina, verified by 142 native parser/Rocq kernel replay cases (`vela-parser elaborate-qualify`). ([note](docs/assurance/completion-log.md#q25k-elaborate-generic-dependent-mathematics-and-first-class-proofs))
- [x] **Q25l · Clarify Vela borrowing, evidence and resource interfaces** · 0.3 h actual · agent-parallel
  - The design contracts specify receiver borrowing, visible claim evidence and compositional handler summaries, retaining the existing syntax and executable implementation owners. ([note](docs/assurance/completion-log.md#q25l-clarify-vela-borrowing-evidence-and-resource-interfaces))
- [x] **Q25m · Specify staged Vela metaprogramming and compiler services** · 0.5 h actual · agent-parallel
  - The language contracts specify static evaluation, opt-in descriptions, resource-aware generation and shared compiler services, with implementation and artifact qualification retained at their proposed owners. ([note](docs/assurance/completion-log.md#q25m-specify-staged-vela-metaprogramming-and-compiler-services))
- [x] **Q25n · Prototype and qualify Vela LSP lifecycle and pure diagnostics** · 6 h retained estimate, actual n/a · agent-parallel
  - Serves bounded stdio lifecycle, UTF-8/UTF-16 coordinate conversion, full and incremental overlays and pure diagnostics in `vela-lsp`, qualified across pinned Neovim `0.11.0` and Vim `9.1.2141` + `yegappan/lsp` clients (`vela-lsp --qualify-clients`). ([note](docs/assurance/completion-log.md#q25n-prototype-and-qualify-vela-lsp-lifecycle-and-pure-diagnostics))
- [x] **Q25o · Add and qualify pure Vela LSP navigation** · 8 h retained estimate, actual n/a · agent-parallel
  - Drives hover, definition, references and flat document symbols from compiler-owned resolution facts over synchronized open buffers, qualified across both pinned Neovim and Vim LSP clients. ([note](docs/assurance/completion-log.md#q25o-add-and-qualify-pure-vela-lsp-navigation))
- [x] **Q25p · Improve Vela authoring syntax and editor hints** · 8 h retained estimate, actual n/a · agent-parallel
  - Adds inferred lambdas, `=>` expression bodies, trailing commas, token-shape constructor patterns, canonical `Unit`/`this`, bounded `foreach`, declaration-order named arguments, typed required-static `const` declarations and LSP `textDocument/inlayHint` local type hints. ([note](docs/assurance/completion-log.md#q25p-improve-vela-authoring-syntax-and-editor-hints))
- [x] **Q25q · Implement compositional Vela constant functions and parameters** · 16 h retained estimate, actual n/a · agent-parallel
  - Implements `const` callable modifiers and symbolic/specialized `const` value parameters across both Menhir entries, the pure and mathematical compilers, editor signatures and native Rocq kernel replay. ([note](docs/assurance/completion-log.md#q25q-implement-compositional-vela-constant-functions-and-parameters))
- [x] **Q25r · Add Vela numeric digit separators** · 12 h retained estimate, actual n/a · agent-parallel
  - Supports `_` digit separators across pure decimal and surface decimal/hexadecimal/binary literals while preserving original located spellings and actual-digit bounds. ([note](docs/assurance/completion-log.md#q25r-add-vela-numeric-digit-separators))
- [x] **Q25s · Attach Vela documentation comments to compiler facts** · 12 h retained estimate, actual n/a · agent-parallel
  - Source-bound declaration documentation drives bounded plain-text hover, preserves attachment through formatting and refuses forged or stale records. ([note](docs/assurance/completion-log.md#q25s-attach-vela-documentation-comments-to-compiler-facts))
- [x] **Q25t · Integrate default Vela formatting and lints** · 24 h retained estimate, actual n/a · agent-parallel
  - Pure formatting and advisory lints preserve ordinary compiler source, publish only explicit source edits and bind emission to the checked snapshot. ([note](docs/assurance/completion-log.md#q25t-integrate-default-vela-formatting-and-lints))
- [x] **Q25u · Add pure Vela editor formatting and semantic tokens** · 12 h retained estimate, actual n/a · agent-parallel
  - Serves isolated canonical `textDocument/formatting` edits and full identifier `textDocument/semanticTokens/full` streams from compiler facts, qualified across both pinned Neovim and Vim LSP clients. ([note](docs/assurance/completion-log.md#q25u-add-pure-vela-editor-formatting-and-semantic-tokens))
- [x] **Q25v · Settle the bounded Vela release and practical language contracts** · 0.7 h actual · agent-parallel
  - Selects a synchronous release, checked interpretation and concrete primitive/package contracts, with practical ownership, assurance, tooling and staged-delivery acceptance. ([note](docs/assurance/completion-log.md#q25v-settle-the-bounded-vela-release-and-practical-language-contracts))
- [x] **Q25w · Investigate the concrete Vela buffer foundation within a fixed budget** · 24 h retained estimate, actual n/a · agent-parallel
  - Records a blocked outcome: a concrete `Span<byte>` carrier, packet validator and purecap Sail and CompCert execution slice whose laws, scenarios and restoration obligations mostly reach the kernel as tautologies, alongside the upstream Sail and machine-logic blockers that keep full machine refinement and subsequent delivery stages closed. ([note](docs/assurance/completion-log.md#q25w-investigate-the-concrete-vela-buffer-foundation-within-a-fixed-budget))
- [x] **Q25x · Qualify generated tests for existing Vela development tools** · 6 h retained estimate, actual n/a · agent-parallel
  - Qualifies deterministic `hypothesis==6.170.14` campaigns (`vela generated-tests`) over source coordinates, synchronous LSP overlays, supported requests and pure formatting against independent models, killing all three seeded faults and retaining `hypothesis` as an isolated on-demand instrument with shrunk explicit JSON replays in the Apache-2.0 suite. ([note](docs/assurance/completion-log.md#q25x-qualify-generated-tests-for-existing-vela-development-tools))
- [x] **Q25y · Qualify Menhir-generated syntax campaigns** · 4.5 h retained estimate, actual n/a · agent-parallel
  - Qualifies seeded Menhir sentence generation, payload rendering and batch `--interpret --interpret-show-cst` (`vela-parser syntax-campaigns`) against `IndependentPureAstOracle`, killing all three semantic-action/span faults and shrinking failing sentences to deterministic JSON replays without a second grammar or `menhirLib` runtime dependency. ([note](docs/assurance/completion-log.md#q25y-qualify-menhir-generated-syntax-campaigns))
- [x] **Q25z · Qualify the familiar Vela authoring surface** · 32 h retained estimate, actual n/a · agent-parallel
  - Qualifies ordinary `F<T>(...)` generic calls, `=>` bodies, fat-arrow `match` arms, `if` expressions, labeled constructor patterns, `with` updates, `let ... else` and `if (x is ...)` guards, `property` declarations, collection-loop syntax, raw strings, interpolated `$"..."` format templates and assist-don't-coerce helpers across the grammar and supported consumers, with represented runtime lowering and wider editor slices retained in the [ergonomics follow-through](#remaining-vela-ergonomics). ([note](docs/assurance/completion-log.md#q25z-qualify-the-familiar-vela-authoring-surface))
- [x] **Q25aa · Build a local Vela browser playground** · 12 h retained estimate, actual n/a · agent-parallel
  - The local Monaco playground connects the pure compiler and LSP to source editing, Gallina output and a bounded compile-time expression console. ([note](docs/assurance/completion-log.md#q25aa-build-a-local-vela-browser-playground))
- [x] **Q25ab · Extend the Vela playground authoring and inspection controls** · 8 h retained estimate, actual n/a · agent-parallel
  - The playground exposes compiler-backed lint checks, symbol inspection, editor display controls and explicit browser downloads. ([note](docs/assurance/completion-log.md#q25ab-extend-the-vela-playground-authoring-and-inspection-controls))
- [x] **Q25ac · Extend pure Vela expressions and playground examples** · 8 h retained estimate, actual n/a · agent-parallel
  - Extends both pure routes and the playground with Boolean negation, short-circuit conjunction/disjunction, all non-chaining comparisons and saturating natural subtraction, verified by migration agreement and native kernel replay. ([note](docs/assurance/completion-log.md#q25ac-extend-pure-vela-expressions-and-playground-examples))
- [x] **Q25ad · Add natural division and remainder to Vela and its playground** · 6 h retained estimate, actual n/a · agent-parallel
  - Adds total natural `/` and `%` at multiplication's left-associative precedence across both pure routes, the static evaluator, formatter, playground examples and native kernel replay. ([note](docs/assurance/completion-log.md#q25ad-add-natural-division-and-remainder-to-vela-and-its-playground))
- [x] **Q25ae · Bring dependent Vela mathematics into the playground** · 16 h retained estimate, actual n/a · agent-parallel
  - Unifies `vela-playground` with automatic pure/mathematical compiler selection, closed dependent expression reduction (`evaluate_mathematical`), `VELA105` generic type-parameter naming lints and runnable dependent examples. ([note](docs/assurance/completion-log.md#q25ae-bring-dependent-vela-mathematics-into-the-playground))
- [x] **Q25af · Make Vela elaboration evidence kernel-honest** · 24 h retained estimate, actual n/a · agent-parallel
  - Emits the real proposition for every contract, `restores` and theorem obligation, records solver-trusted obligations as named assumptions in `solver_trust`, and defines fixed-width integer arithmetic, shifts, signed comparisons and conversions over bit lists in Gallina. ([note](docs/assurance/completion-log.md#q25af-make-vela-elaboration-evidence-kernel-honest))
- [x] **Q25ag · Conform the Vela first slice to the synchronous design** · 24 h retained estimate, actual n/a · agent-parallel
  - Rewrites the first slice and its CompCert/Sail harness to the synchronous design with `Result<ValidatedPacket<'dst>, ValidationError>`, returned subslice views, explicit `effects writes(...)`, independent format-model contracts, capacity-wide symbolic loops and semantic negative controls. ([note](docs/assurance/completion-log.md#q25ag-conform-the-vela-first-slice-to-the-synchronous-design))
- [x] **Q25ah · Resolve Vela surface collisions and redundant spellings** · 16 h retained estimate, actual n/a · agent-parallel
  - Adopts `open (...) lifts ...` for invariant lifting, automatic `ref` descriptor preservation, mandatory `let`/`var` local keywords, token-shape constructor patterns (retiring `VELA106`) and unified fat-arrow `match` arms across parsers, elaborators, formatters and examples. ([note](docs/assurance/completion-log.md#q25ah-resolve-vela-surface-collisions-and-redundant-spellings))
- [x] **Q25ai · Publish the Vela language reference and separate extension research** · 12 h retained estimate, actual n/a · agent-parallel
  - Publishes the compact [language reference](docs/language/reference.md), moves extension dossiers under `docs/extensions/` and dated language comparisons to background, and records first-release authoring-cost measurements. ([note](docs/assurance/completion-log.md#q25ai-publish-the-vela-language-reference-and-separate-extension-research))
- [x] **Q25aj · Unify Vela playground assets, single-source grammar sync, and single-pass worker execution** · 8 h retained estimate, actual n/a · agent-parallel
  - Retires the duplicated `tools/toolchain/playground/` asset tree in favor of canonical `docs/` assets, unifies the in-browser lexer/parser/evaluator and syntax highlighters with exact `lexer.mll`/`Q25ah`/`Corelib` Gallina parity and Web Crypto `sha256Hex`, and eliminates redundant two-pass source compilation during expression evaluation. ([note](docs/assurance/completion-log.md#q25aj-unify-vela-playground-assets-single-source-grammar-sync-and-single-pass-worker-execution))
- [x] **Q25ak · Close remaining elaboration solver axioms and promote source-bound borrow and mutation-invalidation checking** · 16 h retained estimate, actual n/a · agent-parallel
  - Replaces the remaining `solver_trust` axioms in `vela-parser elaborate-qualify` with constructive Rocq proof synthesis across unit-step counter loops and sequential/branching `out`-parameter arithmetic, enforces zero `solver_trust` assumptions across all positive elaboration fixtures, and connects path-sensitive loan-end analysis (`loans.py`) and mutation-invalidation rules into statement elaboration (`elaborate_statements.py`) to discharge the source-bound [borrow-analysis promotion joins](docs/language/core-design.md#borrow-analysis-promotion). ([note](docs/assurance/completion-log.md#q25ak-close-remaining-elaboration-solver-axioms-and-promote-source-bound-borrow-and-mutation-invalidation-checking))
- [x] **Q25al · Elaborate consuming ownership (`owned` parameters and `move` transfers), general `in`/`ref` runtime value loans, and closed `effects` footprints (`reads`/`writes`/`calls`)** · 12 h retained estimate, actual n/a · agent-parallel
  - Elaborates consuming `owned T` parameters and data fields, `move expr` transfers (including consuming record updates `move base with { ... }` and call-site `move` arguments), flow-sensitive use-after-move (`use-after-owner-move`), partial-move (`partial-owner-move-unsupported`), and move-through-loan (`move-through-loan-unsupported`) refusals, general `in T` and `ref T` runtime value loans across all runtime value types, and closed `effects` contract verification across `reads(...)`, `writes(...)`, `calls(...)` (including transitive callee and higher-order parameter calls), and `effects none`. ([note](docs/assurance/completion-log.md#q25al-elaborate-consuming-ownership-owned-parameters-and-move-transfers-general-in-ref-runtime-value-loans-and-closed-effects-footprints-reads-writes-calls))

### Shared foundation and retained route

<a id="q25am"></a>

- [ ] **Q25am · Establish the selected machine-logic interpretation and adequacy** · 800 h, range 400–1,200 · X
  - **Owner:** `machine-logic`. **Start:** Canonical Sail term and Q35 compatibility evidence; retain the external machine-logic owner. **Check:** Supply the selected synchronous subset's checked operational/resource interpretation, adequacy and observation interfaces over that exact term; replay inhabited byte and invalid-operation cases. This is residual logic work beyond already booked Q35 slices.

<a id="q25an"></a>

- [ ] **Q25an · Establish concrete byte and scoped-resource laws** · 400 h, range 200–600 · X
  - **Owner:** `concrete-resources`. **Start:** machine-logic and the existing byte-instance/scoped-resources owners. **Check:** Prove CHERI read/write/frame, initialization, split/join, nested loan/restoration and returned-view laws over the admitted carrier. Reuse the source-level Span/Slots laws from Q25af/ag/ak/al; no abstract dictionary substitutes for the machine connection.

<a id="q25ao"></a>

- [ ] **Q25ao · Close the retained source-to-target compiler refinement** · 800 h, range 400–1,200 · X
  - **Owner:** `retained-compiler`. **Start:** machine-logic, concrete-resources and the retained Q35d/M1.2g/Q35j compiler producers. **Check:** Connect the selected Clight representation and purecap ABI through the retained compiler to canonical Sail execution, including calls, loops, failure exits and composition. Budget only residual proof/compatibility work beyond those producers' booked slices.

<a id="q25ap"></a>

- [ ] **Q25ap · Establish contextual security preservation for the release closure** · 1,200 h, range 600–1,800 · X
  - **Owner:** `context-preservation`. **Start:** machine-logic, retained-compiler and an independently reviewed observation/adversarial-context contract. **Check:** Prove the required authority/confidentiality and contextual-preservation statement at the selected endpoint, including linking, callbacks, leakage and resource assumptions; finite generated-code tests and source effect annotations supply no substitute.

<a id="q25aq"></a>

- [ ] **Q25aq · Close TAL and exact-artifact admission for the release closure** · 800 h, range 400–1,200 · X
  - **Owner:** `artifact-admission`. **Start:** Supplied retained-compiler/context-preservation theorem interfaces and existing TAL/image-validation owners. **Check:** Supply the required TAL/checker soundness joins, post-compiler assembly/link/image validation, theorem composition and applicable binary constant-time/resource evidence progressively for each release client. Publish the independently checked first-client receipt before the second-client trial; close this cell only after both clients have exact-source-to-final-byte admission. Reject stale, changed and malformed artifacts; source kernel replay alone cannot admit bytes.

<a id="q25ar"></a>

- [ ] **Q25ar · Integrate and recheck prerequisite producer receipts** · 40 h, range 24–56 · X
  - **Owner:** `producer-receipts`. **Start:** Named local and externally supplied producer revisions. **Check:** Bind each independently checked subset receipt to source closure, canonical model, assumptions, tool versions and target, including review of user-supplied hosted verdicts. Publish first-client receipts before the second trial and close this cell after complete declared coverage. Missing/skipped receipts remain blockers. This task performs local replay and review; hosted execution remains user-managed.
  - Local first-slice development identities and retained-output binding checks are implemented; [partial evidence](docs/assurance/completion-log.md#q25ar-integrate-and-recheck-prerequisite-producer-receipts) carries no external-producer or artifact-admission verdict.

### Supported-release implementation

<a id="q25as"></a>

- [ ] **Q25as · Prove the synchronous core interpretation and composition laws** · 160 h, range 80–240 · X
  - **Owner:** `core-soundness`. **Start:** concrete-resources and the admitted elaboration-image interpretation. **Check:** Discharge the existing core-soundness package in the [core obligation matrix](docs/language/core-design.md#proof-obligations-and-proposed-work-packages), including substitution, preservation, phase separation and borrow/exit restoration. Carry forward its existing estimate once.

<a id="q25at"></a>

- [ ] **Q25at · Qualify checked synchronous frontend correspondence** · 140 h, range 80–200 · I
  - **Owner:** `core-frontend`. **Start:** core-soundness interfaces and the existing checked parser/elaborator. **Check:** Implement and independently qualify source-to-interpreted-core SourcePackage correspondence, resolution, derivations, reconstruction and frontend erasure. Publish the checked first-client subset before completing wider release coverage. Reuse landed parsing, mathematical elaboration, owned loans and effects; represented-core-to-Clight lowering belongs to runtime-lowering.

<a id="q25au"></a>

- [ ] **Q25au · Qualify contextual diagnostics and invalidation** · 64 h, range 40–88 · I
  - **Owner:** `core-diagnostics`. **Start:** core-frontend's checked derivations. **Check:** Complete the existing core-diagnostics producer for typed holes, exact residual propositions, locations, status and dependency invalidation; invalid edits withdraw stale evidence. This does not buy the wider LSP server.

<a id="q25av"></a>

- [ ] **Q25av · Qualify the composed synchronous fixture and repair protocol** · 48 h, range 32–64 · X
  - **Owner:** `core-repair-trial`. **Start:** core-soundness, core-frontend and concrete-resources. **Check:** Construct the inhabited PreparationOpen/finish fixture and run its independently reviewed negative neighbors, semantic/refactor/representation edits and repair measurements under the [core fixture contract](docs/language/core-design.md#composed-qualification-fixture). Reuse supplied primitive laws.

<a id="q25aw"></a>

- [ ] **Q25aw · Qualify represented scalar and text library behavior** · 96 h, range 64–128 · I
  - **Owner:** `runtime-primitives`. **Start:** Accepted narrow first slice, core-frontend/concrete-resource interfaces and fixed target/ABI. **Check:** Connect existing mathematical integer/UTF-8/raw-string/TextBuilder/Format support to represented runtime definitions; deliver source representation/law interfaces before general lowering and join its per-operation receipts for final runtime acceptance. Qualify aliases, arithmetic/conversions, malformed text, exact-fit/exhaustion and static/runtime agreement under [primitive and text semantics](docs/language/first-release.md#primitive-semantics).

<a id="q25ax"></a>

- [ ] **Q25ax · Implement locked package and build closure** · 96 h, range 64–128 · I
  - **Owner:** `packages`. **Start:** core-frontend and frozen first-release module/instance semantics. **Check:** Deliver manifests, lockfiles, reproducible dependency/target closure and a batch build graph; qualify nominal identity, coherent instances, import order, cycles, missing dependencies and stale configurations across two independently authored packages. No public registry service is required.

<a id="q25ay"></a>

- [ ] **Q25ay · Qualify represented sequence and ownership libraries** · 120 h, range 80–160 · I
  - **Owner:** `runtime-ownership`. **Start:** Accepted narrow first slice and primitive/concrete-resource/core-law interfaces. **Check:** Reuse existing mathematical Seq/Slots/iterator/invariant-lifting support and supply represented library laws and generic clients for initialized/vacant ranges, selective lifting, bounded iteration and bulk relocation under [ownership libraries](docs/language/first-release.md#ownership-libraries). Publish source/law interfaces before general lowering, then join its per-operation receipts for runtime acceptance. Tiny and billion-element capacities retain the same obligation/proof complexity.

<a id="q25az"></a>

- [ ] **Q25az · Qualify general synchronous lowering through the retained route** · 112 h, range 64–160 · I
  - **Owner:** `runtime-lowering`. **Start:** Accepted narrow first slice, core-frontend correspondence, published primitive/ownership representation-law interfaces and retained-compiler theorem interface. **Check:** Extend the existing validator-specific lowering to the declared synchronous release subset with checked represented-core-to-Clight mapping and source maps for calls, branches, loops, errors and resource exits. Publish per-operation runtime receipts for library acceptance, reusing frontend/source and retained-backend theorems; refuse unsupported constructs explicitly.

<a id="q25ba"></a>

- [ ] **Q25ba · Accept the synchronous component at the exact-artifact endpoint** · 96 h, range 48–144 · X
  - **Owner:** `vela-first-slice`. **Start:** Existing validator-specific source/lowering and independently checked first-client core, machine, compiler, security and admission receipts. **Check:** Retain the closed source proof in [first-slice qualification](docs/language/first-release.md#first-slice-qualification), then bind the authored slice to those exact receipts and bytes; independent output, alias/restoration, wrong-operation, stale-input and corruption controls pass. Broader library/general lowering and the second client's receipts are subsequent work. Existing closed source proofs and Sail/C execution receive no second completion credit.
  - All three source residuals now kernel-replay within unchanged budgets; [partial evidence](docs/assurance/completion-log.md#q25ba-accept-the-synchronous-component-at-the-exact-artifact-endpoint) closes no source-correspondence or artifact-admission join.

<a id="q25bb"></a>

- [ ] **Q25bb · Run the independent package and developer-value trial** · 80 h, range 48–112 · X
  - **Owner:** `vela-package-trial`. **Start:** Accepted first slice, packages, represented-library runtime receipts and general lowering. **Check:** Freeze a genuinely independent second client, baseline and thresholds under the [adoption protocol](docs/assurance/workflow-contract.md#first-release-qualification-and-adoption); qualify real errors/exits, contract/representation/refactor changes, explicit native proof transfer, annotation/review/repair costs and target resources at the same endpoint. Obtain this client's own admission receipt before acceptance; its selection/authorship precedes that receipt.

<a id="q25bc"></a>

- [ ] **Q25bc · Publish a supported and reproducible release closure** · 72 h, range 48–96 · I
  - **Owner:** `vela-release`. **Start:** Accepted first slice and package trial, all required producer receipts. **Check:** Version the supported language/libraries, conformance and refusal corpus, compatibility policy, installation/tutorial/reference material, dependency notices and reproducible Windows/Linux artifacts. Cold install/build/proof replay and independent release review pass; every published guarantee names its endpoint.

<a id="q25bd"></a>

- [ ] **Q25bd · Rehearse one supported-release maintenance cycle** · 64 h, range 32–96 · I
  - **Owner:** `release-maintenance`. **Start:** vela-release and pinned compiler/kernel/dependency closure. **Check:** Perform one coordinated dependency/tool upgrade, semantic cache invalidation, compatibility/migration, security-response and rollback rehearsal with proof/conformance replay. Record actual human/agent/machine costs separately; this finite cycle does not fund indefinite support.

### Language extensions

<a id="q25be"></a>

- [ ] **Q25be · Qualify the six graded-foundation law packages** · 296 h, range 168–424 · X
  - **Owner:** `graded-laws`. **Start:** Released synchronous resources and the independently selected graded client. **Check:** Discharge GF-domain, GF-substitution, GF-elimination, GF-cbv, GF-control-mutation and GF-erasure-source under the [reviewed extension predicates](docs/extensions/full-language-review.md#reviewed-implementation-pricing). This single cell aggregates their six existing ranges without extending core-soundness's baseline.

<a id="q25bf"></a>

- [ ] **Q25bf · Qualify capture, resumption, suspension and cancellation laws** · 176 h, range 96–256 · X
  - **Owner:** `handler-laws`. **Start:** Concrete scoped resources and a named control/service client. **Check:** Discharge HA-capture-substitution, HA-resume-dispose, HA-suspend-scope and HA-cancel-progress under the [control contract](docs/extensions/handlers-async.md), including fresh clone frames, terminal resources, cancellation races and finite masked distance. This aggregates four existing review rows.

<a id="q25bg"></a>

- [ ] **Q25bg · Qualify the combined handler embedding** · 40 h, range 22–58 · X
  - **Owner:** `handler-embedding`. **Start:** handler-laws and its selected frontend/lowering. **Check:** Discharge HA-combined-embedding over the actual carrier and returned resources; reject adapter-only capture checks and unsupported-feature substitutes. Preserve the existing reviewed range.

<a id="q25bh"></a>

- [ ] **Q25bh · Qualify the five cell and interference law packages** · 200 h, range 110–290 · X
  - **Owner:** `mutation-laws`. **Start:** Concrete resources, supplied atomic/publication laws, interference/observation contract and a named mutation client. **Check:** Discharge MUT-CELL, MUT-BORROW, MUT-SNAPSHOT, MUT-SHARE and MUT-EXIT under the [mutation contract](docs/extensions/interior-mutability.md), using the supplied atomic commit laws for snapshot validity, scoped invariant opening and safe backing reuse. Aggregate the five existing review rows once; machine atomicity/publication construction has a separate extension-machine-laws allocation.

<a id="q25bi"></a>

- [ ] **Q25bi · Qualify the combined mutation client** · 32 h, range 18–46 · I
  - **Owner:** `mutation-client`. **Start:** mutation-laws and its actual frontend/runtime support. **Check:** Run the existing MUT-CLIENT predicate with independent scalar-counter behavior, interference, commit/reuse and negative neighbors; source syntax alone earns no verdict.

<a id="q25bj"></a>

- [ ] **Q25bj · Reconstruct checked graded-domain evidence** · 72 h, range 40–104 · X
  - **Owner:** `graded-frontend`. **Start:** graded-laws and core-frontend. **Check:** Implement the existing reviewed elaboration/domain/grade reconstruction row, carrying dictionaries, substitutions and replayable certificates; unresolved or exhausted solver work remains an explicit goal.

<a id="q25bk"></a>

- [ ] **Q25bk · Check and lower the selected handler and async constructs** · 64 h, range 36–92 · X
  - **Owner:** `handler-lowering`. **Start:** handler-laws, core-frontend and a supplied runtime graph interpretation. **Check:** Complete the existing reviewed handler/async frontend row and selected HA-lowering-erasure join with checked capture boundaries, frame/state/reaction graphs and indexed exits. Retained/native backend producers supply their target theorem once.

<a id="q25bl"></a>

- [ ] **Q25bl · Check selected cell protocols and snapshot invalidation** · 40 h, range 22–58 · X
  - **Owner:** `cell-frontend`. **Start:** mutation-laws and core-frontend. **Check:** Complete the existing reviewed cell frontend row, preserving ownership/interference identities, fresh snapshots and invalidation at writes; source-bound positives and well-formed negatives reach the intended rules.

<a id="q25bm"></a>

- [ ] **Q25bm · Prove correspondence for the selected extension combination** · 48 h, range 26–70 · X
  - **Owner:** `extension-correspondence`. **Start:** Selected graded/handler/cell frontend rows and their interpretation laws. **Check:** Complete the reviewed extension SourcePackage row across source binding, insertion, erasure and combined terms; no generated term is accepted solely because it kernel-checks.

<a id="q25bn"></a>

- [ ] **Q25bn · Qualify diagnostics for the added extension rules** · 40 h, range 22–58 · X
  - **Owner:** `extension-diagnostics`. **Start:** Selected extension derivations and core-diagnostics. **Check:** Complete the reviewed additional-diagnostics row with exact source goals, authority/effect traces and freshness after changes. Wider editor projection remains separately budgeted.

<a id="q25bo"></a>

- [ ] **Q25bo · Implement assurance-preset selection and evidence status** · 48 h, range 26–70 · I
  - **Owner:** `preset-policy`. **Start:** Checked frontend and the [assurance policy](docs/extensions/assurance-profiles.md). **Check:** Complete the reviewed selection/status-engine row with unchanged shared construct meaning, truthful missing-evidence/assumption status and no proof-dependent optimization after its proof is disabled.

<a id="q25bp"></a>

- [ ] **Q25bp · Qualify mixed-assurance linking and closure declarations** · 40 h, range 24–56 · I
  - **Owner:** `preset-linking`. **Start:** preset-policy, packages and applicable artifact/context evidence. **Check:** Complete the reviewed mixed-linking row over reachable implementations, instances, dependencies, generated code and runtime components; downgrade and foreign-boundary changes invalidate dependent guarantees.

<a id="q25bq"></a>

- [ ] **Q25bq · Qualify assurance-policy refusals** · 24 h, range 14–34 · I
  - **Owner:** `preset-qualification`. **Start:** preset-policy and preset-linking. **Check:** Run the reviewed policy-semantics predicate against invented invariants, unresolved safety, hidden assumptions and retained theorem-dependent optimizations; reject at the actual policy rule.

<a id="q25br"></a>

- [ ] **Q25br · Qualify ordinary applications under increasing assurance** · 24 h, range 14–34 · I
  - **Owner:** `preset-client`. **Start:** preset-policy and real parser/collection/service application interfaces. **Check:** Complete the reviewed ordinary-application row with executable reuse, explicit changes and no manual verified rewrite hidden by a preset label.

<a id="q25bs"></a>

- [ ] **Q25bs · Qualify the asynchronous systems-resource boundary** · 32 h, range 18–46 · I
  - **Owner:** `systems-extension-trial`. **Start:** handler-laws, mutation-laws, selected runtime and concrete resources. **Check:** Complete the reviewed systems-qualification row over an explicit arena and asynchronous operation: cancellation, late completion, failure/exhaustion, quiescence and actual release-gate backing reuse.

<a id="q25bt"></a>

- [ ] **Q25bt · Establish concrete resource laws required by selected extensions** · 400 h, range 200–600 · X
  - **Owner:** `extension-machine-laws`. **Start:** Shared machine/resource interfaces and frozen selected grade/control/mutation clients. **Check:** Supply additional GF-resource, MUT-ATOMIC and MUT-PUBLISH machine-connected laws, including atomic counter linearization, publication ordering, frame/address stability, capability invariants and service backing reuse. These are beyond the synchronous concrete-resources baseline and outside the 27 parameterized review ranges.

<a id="q25bu"></a>

- [ ] **Q25bu · Prove target transport for the selected language extensions** · 360 h, range 180–540 · X
  - **Owner:** `extension-target-transport`. **Start:** Selected extension interpretations/frontend and extension-machine-laws. **Check:** Close GF-target, HA-lowering-erasure and added source/IR representation-to-target simulation for the chosen graded/handler/cell/service constructs. Reuse shared retained-compiler and native interfaces; this is incremental extension transport, separate from source graph reconstruction and original synchronous compilation.

<a id="q25bv"></a>

- [ ] **Q25bv · Qualify extension security, cost and admission joins** · 240 h, range 120–360 · X
  - **Owner:** `extension-security-admission`. **Start:** extension-target-transport and shared contextual-security/admission laws. **Check:** Close MUT-OBSERVE and selected extension leakage, cost/schedule, attribute/TAL and exact-artifact admission joins over real clients. Prove added premises and counterexamples without rebuilding the shared base theorems or inventing new attribute authority.

<a id="q25bw"></a>

- [ ] **Q25bw · Implement and qualify one bounded asynchronous service runtime** · 160 h, range 80–240 · I
  - **Owner:** `vela-service`. **Start:** Accepted synchronous release, handler-laws/lowering and service-specific storage/control laws. **Check:** Implement one named service with direct helper await and one explicit child, capacity failure, ready/pending outcomes, commit/cancel races and cleanup failure. Supply required lifecycle/manifest/register acts and cost/schedule joins before acceptance; this adds runtime implementation, not a second budget for general HA proofs.

<a id="q25bx"></a>

- [ ] **Q25bx · Qualify an explicit bounded-pool library** · 128 h, range 64–192 · I
  - **Owner:** `bounded-pool`. **Start:** Concrete ownership laws and the release or service client needing allocation. **Check:** Supply allocator/free-list representation, manifests, capacity/exhaustion, initialization, cancellation/quiescence and reuse proofs under the [bounded-pool boundary](docs/language/first-release.md#release-boundary). Reuse shared backing laws; no implicit allocation, retry or new OS allocator is assumed.

<a id="q25by"></a>

- [ ] **Q25by · Compare fixed modes with a bounded grading increment** · 32 h, range 16–48 · X
  - **Owner:** `grading-trial`. **Start:** Independent client and frozen baseline/benefit threshold. **Check:** Run the [graded selection protocol](docs/extensions/graded-foundation.md#extension-selection-and-qualification), separately justifying general domains and type-use accounting; retain the smaller supported account when prerequisite or material benefit is absent.

<a id="q25bz"></a>

- [ ] **Q25bz · Trial derived modality combinators** · 64 h, range 32–96 · X
  - **Owner:** `grade-derivation`. **Start:** Selected lawful grades, measured boilerplate and checked generation services. **Check:** Qualify the derived-combinator branch of the [conditional usability producers](docs/extensions/graded-foundation.md#conditional-usability-producers) against independent intent and authority preservation. Reuse generic meta construction rather than reimplement it.

<a id="q25ca"></a>

- [ ] **Q25ca · Trial grade-directed synthesis** · 48 h, range 24–72 · X
  - **Owner:** `grade-synthesis`. **Start:** Selected grade interpretation, independent synthesis intent and finite search budget. **Check:** Qualify the synthesis branch of the conditional-usability contract with checked output, explicit residuals/timeouts and measured benefit; proposals receive no proof authority.

<a id="q25cb"></a>

- [ ] **Q25cb · Trial zero-type-use substitution skipping** · 32 h, range 16–48 · X
  - **Owner:** `substitution-skipping`. **Start:** Proved selected type-use irrelevance and a measured substitution bottleneck. **Check:** Prove the selected skip transformation preserves elaborated meaning and compare total checking work, certificate size and replay cost; a toy speedup or zero annotation alone is insufficient.

<a id="q25cc"></a>

- [ ] **Q25cc · Compare borrow-checking alternatives on held-out clients** · 32 h, range 16–48 · X
  - **Owner:** `borrow-comparison`. **Start:** Package-trial friction measurements and pinned equivalent comparison modes. **Check:** Run the [borrow comparison boundary](docs/language/loan-analysis.md#conditional-borrowing-comparison) with fixed behavior/evidence endpoints, unsupported cases and analysis-budget refusals; this is a selection trial, not implementation of a competing checker.

<a id="q25cd"></a>

- [ ] **Q25cd · Trial a selected two-phase receiver-borrow extension** · 96 h, range 48–144 · X
  - **Owner:** `two-phase-borrow`. **Start:** Measured receiver friction and borrow-comparison selection. **Check:** Construct interpretation, checked analysis/lowering and invalid-neighbor cases for one selected two-phase receiver rule; preserve evaluation order, effects, alias safety and source/artifact evidence. Ordinary release receivers remain sufficient until this passes.

<a id="q25ce"></a>

- [ ] **Q25ce · Trial a selected local borrowing-alias extension** · 96 h, range 48–144 · X
  - **Owner:** `borrow-alias`. **Start:** Measured alias need and borrow-comparison selection. **Check:** Qualify one selected local-alias rule with explicit identity/lifetime, restoration, interference and escape controls under the [borrowing promotion contract](docs/language/core-design.md#borrow-analysis-promotion). No general alias facility follows from this envelope.

<a id="q25cf"></a>

- [ ] **Q25cf · Trial selected loop-carried borrowing** · 96 h, range 48–144 · X
  - **Owner:** `loop-borrow`. **Start:** Measured loop-client need and borrow-comparison selection. **Check:** Qualify one loop-carried loan shape with loop/exit invariants, termination, initialization and borrow restoration, and held-out valid/invalid neighbors; reuse general flow and concrete laws.

<a id="q25cg"></a>

- [ ] **Q25cg · Trial representation-proof transfer automation** · 32 h, range 16–48 · X
  - **Owner:** `proof-transfer`. **Start:** Package-trial explicit-relation baseline exposes repeated work. **Check:** Run a bounded [CoqEAL/Trocq comparison](docs/assurance/workflow-contract.md#representation-transfer-comparison), including exact version/licence/assumption closure and maintenance measurement. Preserve the same client laws, preconditions and locked prover; the native baseline remains in the package trial.

### Tooling and metaprogramming

<a id="q25ch"></a>

- [ ] **Q25ch · Publish qualified compiler inspection services** · 112 h, range 64–160 · I
  - **Owner:** `vela-compiler-services`. **Start:** Qualified frontend/diagnostic producers; backend for lowering views. **Check:** Meet the [inspection contract](docs/tooling/tooling-protocols.md#compiler-inspection-api) with versioned schemas, bounded snapshots/queries, origins, source reconstruction and stale-handle/input refusal in an independent consumer. Shared identities and producer semantics are charged once here and at their existing producers.
  - The existing pure producer supplies source snapshots, structured identifier types and resolved queries; [partial evidence](docs/assurance/completion-log.md#q25ch-publish-qualified-compiler-inspection-services) retains the wider views and their producer prerequisites.

<a id="q25ci"></a>

- [ ] **Q25ci · Extend semantic editor services beyond the pure prototype** · 112 h, range 64–160 · I
  - **Owner:** `vela-lsp`. **Start:** Compiler services and qualified wider-language facts. **Check:** Meet the [LSP contract](docs/tooling/tooling-protocols.md#language-server-protocol) for selected workspace navigation, completion/signatures, rename, checked actions, token deltas and read-only proof inspection in two clients. Reuse Q25n/o/u and refuse stale or capturing edits.
  - Pure semantic token deltas use bounded document history and invalidate changed producer generations; [partial evidence](docs/assurance/completion-log.md#q25ci-extend-semantic-editor-services-beyond-the-pure-prototype) retains wider editor scope and two-client qualification.

<a id="q25cj"></a>

- [ ] **Q25cj · Distribute Tree-sitter and TextMate syntax assets** · 56 h, range 32–80 · I
  - **Owner:** `vela-highlight`. **Start:** Canonical Menhir grammar/corpus and named editor consumers. **Check:** Meet the [highlighting contract](docs/tooling/tooling-protocols.md#syntax-grammars-and-highlighting) with both asset formats, fresh/incremental agreement and malformed/Unicode cases; assets grant no semantic acceptance.

<a id="q25ck"></a>

- [ ] **Q25ck · Extend canonical formatting, lints and checked previews** · 72 h, range 40–104 · I
  - **Owner:** `vela-authoring`. **Start:** Qualified wider syntax and semantic fact producers. **Check:** Meet the [authoring contract](docs/tooling/authoring-tools.md) with token/comment/documentation preservation, reparse equivalence, idempotence and source-bound explicit previews. Reuse Q25t/z/ah; default commands preserve source bytes.

<a id="q25cl"></a>

- [ ] **Q25cl · Export qualified batch diagnostics as SARIF** · 28 h, range 16–40 · I
  - **Owner:** `vela-sarif`. **Start:** Diagnostic producers and compiler-service snapshots. **Check:** Meet the [diagnostic export contract](docs/tooling/tooling-protocols.md#diagnostic-and-semantic-index-exports) with a pinned schema and independent importer for Unicode/cross-file locations, fixes and incomplete status; partial analysis cannot appear clean.

<a id="q25cm"></a>

- [ ] **Q25cm · Export a qualified offline SCIP index** · 44 h, range 24–64 · I
  - **Owner:** `vela-scip`. **Start:** Resolved identities, package closure and compiler services. **Check:** Meet the semantic-index export contract with independent offline definition/reference/implementation queries across imports, shadowing, generation and rename; refuse stale bindings and incomplete absence claims.

<a id="q25cn"></a>

- [ ] **Q25cn · Expose the actual build graph through BSP** · 44 h, range 24–64 · I
  - **Owner:** `vela-build`. **Start:** The packages cell's real locked batch graph and a named client. **Check:** Meet the [build contract](docs/tooling/tooling-protocols.md#build-integration) for targets, dependencies, options and actual bridge commands; cancellation, stale graphs and failed builds preserve batch verdicts. This funds projection, not graph construction.

<a id="q25co"></a>

- [ ] **Q25co · Export optimization decisions and explanations** · 28 h, range 16–40 · I
  - **Owner:** `vela-remarks`. **Start:** An actual qualified optimization producer. **Check:** Meet the [remarks contract](docs/tooling/tooling-protocols.md#compiler-decisions-and-performance-traces) in an independent reader for applied/missed/refused cases and source origins; this funds export, not transformations or a speedup claim.

<a id="q25cp"></a>

- [ ] **Q25cp · Expose bounded compiler performance traces** · 28 h, range 16–40 · I
  - **Owner:** `vela-traces`. **Start:** Named compiler phases and an independent trace consumer. **Check:** Meet the trace contract for clocks, nesting/workers, overhead and bounded recording; dropped events, truncation and cancellation remain explicit. Compiler timing supplies no emitted-program WCET proof.
  - The pure compiler records bounded input-bound phase/counter traces; [partial evidence](docs/assurance/completion-log.md#q25cp-expose-bounded-compiler-performance-traces) retains external-viewer qualification and wider measurement coverage.

<a id="q25cq"></a>

- [ ] **Q25cq · Emit and qualify exact-image native debug information** · 144 h, range 80–208 · I
  - **Owner:** `vela-dwarf`. **Start:** Executable backend, fixed purecap ABI and compiler-owned maps. **Check:** Meet the [DWARF contract](docs/tooling/tooling-protocols.md#dwarf-native-debug-information) for scopes/types/locations/inlining/unwind and capability metadata in independent readers, including optimized-away values, malformed sections and stale-image refusal.

<a id="q25cr"></a>

- [ ] **Q25cr · Qualify a simulator execution and inspection backend** · 96 h, range 48–144 · I
  - **Owner:** `debug-runtime`. **Start:** An executable simulator route, exact images and debug maps. **Check:** Implement known stops/stepping, stack/register/capability inspection, reconnect and bounded read-only evaluation against independent expected states; no code patching or hardware trigger is needed. This is the producer missing from the former adapter-only plan.

<a id="q25cs"></a>

- [ ] **Q25cs · Qualify a source debugger through DAP** · 112 h, range 64–160 · I
  - **Owner:** `vela-dap`. **Start:** debug-runtime and vela-dwarf. **Check:** Meet the [DAP contract](docs/tooling/tooling-protocols.md#debug-adapter-protocol) for lifecycle, source stepping, scopes/values and stale/unauthorized requests in two clients; reuse the execution producer.

<a id="q25ct"></a>

- [ ] **Q25ct · Qualify conditional RSP and GDB-MI integration** · 76 h, range 40–112 · I
  - **Owner:** `vela-debug-backend`. **Start:** A separately selected debugger engine and its required packet/command subset. **Check:** Meet the [debugger backend contract](docs/tooling/tooling-protocols.md#debugger-backend-protocols) for registers/capabilities, malformed packets, reconnect and stale state in an independent engine. Direct DAP backends need not select this option.

<a id="q25cu"></a>

- [ ] **Q25cu · Qualify a bounded web-output producer** · 192 h, range 96–288 · I
  - **Owner:** `web-output`. **Start:** A selected pure release subset and independently reviewed JavaScript/WebAssembly semantics. **Check:** Implement and check one bounded output route with exact-source correspondence, independent execution/refusals and fixed runtime/resource limits before offering source maps. The existing Gallina playground is reused as UI, not counted as this compiler backend.

<a id="q25cv"></a>

- [ ] **Q25cv · Export qualified generated-output source maps** · 38 h, range 20–56 · I
  - **Owner:** `vela-source-maps`. **Start:** web-output or an independently qualified compatible producer and a named consumer. **Check:** Meet the [source-map contract](docs/tooling/tooling-protocols.md#generated-source-maps) for composed/Unicode/unmapped sites and exact map/output/source identities; mismatches fail before handoff. This funds maps, not output generation.

<a id="q25cw"></a>

- [ ] **Q25cw · Qualify target-aware aggregate and text static evaluation** · 72 h, range 40–104 · I
  - **Owner:** `meta-evaluation`. **Start:** Selected static interpretation subject, target types and sealed dependency closure. **Check:** Construct the incremental phase/evaluation preservation laws and meet the [phase/evaluation contract](docs/extensions/metaprogramming.md#evaluation-and-phase-boundaries) for aggregate/table freezing, deterministic inputs and budgets; refuse runtime layout fallback and host-width substitution. Reuse Q25q's scalar constant functions and the fixed core laws without expanding their budget.

<a id="q25cx"></a>

- [ ] **Q25cx · Qualify opt-in descriptions and one codec derivation** · 112 h, range 64–160 · I
  - **Owner:** `meta-descriptors`. **Start:** meta-evaluation interfaces, nominal declarations and an independently fixed wire-format intent. **Check:** First freeze the description protocol and prove its incremental privacy/coherence/interpretation laws under the [description contract](docs/extensions/metaprogramming.md#typed-introspection-and-derivation). That milestone unblocks meta-construction before this cell closes. Final codec acceptance consumes its checked construction interface, length checks and independently expected bytes; two mutually agreeing incorrect codecs fail.

<a id="q25cy"></a>

- [ ] **Q25cy · Qualify hygienic typed construction and generated evidence** · 152 h, range 80–224 · I
  - **Owner:** `meta-construction`. **Start:** Compiler services and the independently reviewed descriptor-protocol/law milestone from meta-descriptors, without waiting for its final codec. **Check:** Prove the incremental hygienic-substitution/construction preservation laws and meet the [construction contract](docs/extensions/metaprogramming.md#hygienic-construction-and-composition) for dependent binders, freshness, capture/effects/resources and exact source/output evidence. Publish its checked interface for codec acceptance; reject binder escape and duplicated authority without adding a proof-admission path or widening core-soundness's budget.

<a id="q25cz"></a>

- [ ] **Q25cz · Qualify selected cross-feature metaprogramming clients** · 116 h, range 56–176 · X
  - **Owner:** `meta-composition`. **Start:** Selected meta and graded/resource/control laws plus the actual backend endpoint. **Check:** Run the [meta qualification](docs/extensions/metaprogramming.md#qualification) on independently specified clients, well-formed negatives, stale dependency edits and runtime/code-growth controls. This funds client composition, not the other extensions' underlying proofs.

<a id="q25da"></a>

- [ ] **Q25da · Rehearse one coordinated optional-portfolio refresh** · 192 h, range 96–288 · I
  - **Owner:** `tool-maintenance`. **Start:** The adopted tool/meta/native/model/hardware subset and pinned dependency/consumer closure. **Check:** Perform one finite coordinated schema/client/dependency or model-interface refresh, compatibility and security triage, regression/proof/consumer requalification and rollback across adopted options. Reuse release infrastructure and record actual recurring costs; stop and reprice an exhausted cycle, and budget each later cycle separately.

### Whole-system delivery

<a id="q25db"></a>

- [ ] **Q25db · Qualify complete proof authorship for the frozen proof inventory** · 640 h, range 320–960 · X
  - **Owner:** `vela-proofs`. **Start:** Checked frontend and independently reviewed proof subjects. **Check:** Meet the [proof-authorship boundary](docs/extensions/unified-source-contract.md#software-and-proof-boundary) for the frozen package inventory, including universes, inductive/coinductive reasoning and logical relations; reconstruct/audit kernel terms with no mandatory handwritten fallback. The underlying machine/security theorems retain their shared owners.

<a id="q25dc"></a>

- [ ] **Q25dc · Migrate the frozen operational software inventory** · 1,280 h, range 640–1,920 · X
  - **Owner:** `vela-software`. **Start:** Accepted release, its retained target route and supplied component contracts. **Check:** Meet the software-authoring boundary beyond the two release clients: every frozen first-party component, exit, resource/security contract and exact final-byte join uses the same Vela-authored implementation, without a separate optimized rewrite. Existing OS functionality/algorithm construction is not repriced as migration.

<a id="q25dd"></a>

- [ ] **Q25dd · Define and admit the native compiler interpretations** · 320 h, range 160–480 · X
  - **Owner:** `native-ir`. **Start:** Accepted source interpretation, target contract and reviewed replacement duties. **Check:** Define the selected native IRs, source/IR meanings, pass interfaces and admission subjects under the [native compiler contract](docs/extensions/unified-source-contract.md#native-verified-compiler-and-self-hosting); independently review the complete pipeline scope before implementation.

<a id="q25de"></a>

- [ ] **Q25de · Author the selected native parser and compiler in Vela** · 480 h, range 240–720 · X
  - **Owner:** `native-implementation`. **Start:** native-ir and sufficient supported Vela implementation/proof facilities. **Check:** Implement the declared compiler/parser closure in Vela, preserving grammar/source identities and explicit unsupported diagnostics. Reuse the qualified frontend specification and corpus; seed/development dependency retirement waits for bootstrap.

<a id="q25df"></a>

- [ ] **Q25df · Prove native representation and erasure preservation** · 800 h, range 400–1,200 · X
  - **Owner:** `native-representation`. **Start:** native-ir, native-implementation and concrete target resource laws. **Check:** Prove each selected source/IR representation and erasure pass, including ownership, dependent/static information and authority; compose checked pass theorems over actual emitted terms.

<a id="q25dg"></a>

- [ ] **Q25dg · Qualify the selected native optimization families** · 960 h, range 480–1,440 · X
  - **Owner:** `native-optimization`. **Start:** native-ir, native-representation and frozen held-out workloads, retained-route baselines, thresholds and hard envelopes. **Check:** Meet the [optimization evidence contract](docs/extensions/unified-source-contract.md#optimization-stages-and-evidence) for selected specialization, inlining, redundant-check elimination and scoped loop/layout/vector families where the target supports them; freeze the chosen list before dispatch. Qualify independent behavior, relational/resource preservation and measured applied/missed cases. No LLVM parity or blanket performance saving is assumed.

<a id="q25dh"></a>

- [ ] **Q25dh · Prove native selection, allocation and final image construction** · 960 h, range 480–1,440 · X
  - **Owner:** `native-target`. **Start:** Admitted IRs, exact purecap ABI, canonical machine semantics and qualified passes. **Check:** Construct/prove selection, register/stack allocation, calling convention, assembly, relocations, linkage and image formation to exact target bytes; preserve calls, failures, resources and tag-bearing authority. Interim compiler evidence remains required until replacement acceptance.

<a id="q25di"></a>

- [ ] **Q25di · Compose native security, resource and artifact preservation** · 800 h, range 400–1,200 · X
  - **Owner:** `native-preservation`. **Start:** native-representation/optimization/target and the shared semantic/security/admission interfaces. **Check:** Transport the shared contextual-security, leakage and hard-resource theorems through this replacement pipeline and compose its final-byte/source correspondence. This funds native transport only, not a second construction of the shared machine logic or security property.

<a id="q25dj"></a>

- [ ] **Q25dj · Qualify the native compiler closure on held-out consumers** · 320 h, range 160–480 · X
  - **Owner:** `native-qualification`. **Start:** Complete native pipeline and separately frozen systems/compute consumers. **Check:** Run independent positive/negative/change trials at the required source/artifact endpoint, measure target envelopes, and audit commercial redistribution/rebuild rights for the exact helper/runtime dependency closure; missing rights/evidence blocks adoption.

<a id="q25dk"></a>

- [ ] **Q25dk · Qualify verified self-hosting and resident rebuilding** · 640 h, range 320–960 · X
  - **Owner:** `vela-bootstrap`. **Start:** Qualified native compiler definition and sufficient Vela proof authorship. **Check:** Meet the [bootstrap contract](docs/extensions/unified-source-contract.md#bootstrap-and-qualification): connect proved definition, reviewed seed and successive exact binaries, self-compile the declared closure, and qualify reproducibility, runtime/helper/licence closure and resident rebuilding. Reproducibility alone is not the compiler theorem.

<a id="q25dl"></a>

- [ ] **Q25dl · Qualify the frozen Vela machine-model replacement** · 1,280 h, range 640–1,920 · X
  - **Owner:** `vela-machine`. **Start:** Admitted interpretation and the pinned canonical Sail/profile contract. **Check:** Meet the [machine-model contract](docs/extensions/unified-source-contract.md#machine-model) for every frozen operation/configuration with behavior/progress and relational leakage/cost agreement, independent executable cases and malformed/stale refusals. Original machine-logic construction remains in the shared prerequisite cells.

<a id="q25dm"></a>

- [ ] **Q25dm · Qualify hardware interpretation and migrate the frozen blocks** · 1,920 h, range 960–2,880 · X
  - **Owner:** `vela-hardware`. **Start:** Reviewed cycle/register meaning, block contracts and canonical machine interface. **Check:** Meet the [hardware contract](docs/extensions/unified-source-contract.md#hardware) for every frozen authored block with checked generation to exact synthesis inputs, cycle/commit/progress/refinement evidence and its existing artifact tier. Reuse supplied original block theorems; physical fabrication/lab work is outside language migration.

<a id="q25dn"></a>

- [ ] **Q25dn · Adopt the shared model and retire legacy authoring dependencies** · 640 h, range 320–960 · X
  - **Owner:** `vela-retirement`. **Start:** Accepted machine agreement and complete affected-consumer inventory. **Check:** Meet the [migration gate](docs/extensions/unified-source-contract.md#migration-and-retirement) by rebinding every frozen compiler, logic, TAL, constant-time, timing and hardware consumer in one admitted generation, with explicit amendments and historical evidence retention. No private model or missing consumer is permitted.

## Calibration record (Q25 series)

| Item | Class | Estimate (h) | Range (h) | Actual (h) | Ratio |
| --- | --- | --- | --- | --- | --- |
| Q25a | X-authored | 10 | n/a | 0.2 | 0.02 |
| Q25b | X-authored | 12 | n/a | 0.2 | 0.02 |
| Q25c | X-authored | 10 | n/a | 0.2 | 0.02 |
| Q25d | X-authored | 10 | n/a | 0.9 | 0.09 |
| Q25e | I | 8 | n/a | 0.3 | 0.04 |
| Q25f | I | 2 | n/a | 0.1 | 0.05 |
| Q25g | I | 6 | 4–8 | n/a | n/a |
| Q25h | X | 16 | 8–24 | n/a | n/a |
| Q25i | I | 24 | 16–32 | n/a | n/a |
| Q25j | I | 12 | 8–16 | n/a | n/a |
| Q25k | I | 24 | 16–32 | n/a | n/a |
| Q25l | I | 2 | n/a | 0.3 | 0.15 |
| Q25m | n/a | n/a | n/a | 0.5 | n/a |
| Q25n | I | 6 | 4–8 | n/a | n/a |
| Q25o | I | 8 | 6–10 | n/a | n/a |
| Q25p | I | 8 | 6–10 | n/a | n/a |
| Q25q | I | 16 | 8–24 | n/a | n/a |
| Q25r | I | 12 | 8–16 | n/a | n/a |
| Q25s | I | 12 | 8–16 | n/a | n/a |
| Q25t | I | 24 | 16–32 | n/a | n/a |
| Q25u | I | 12 | 8–16 | n/a | n/a |
| Q25v | I | 4 | 2–6 | 0.7 | 0.18 |
| Q25w | X | 24 | 16–32 | n/a | n/a |
| Q25x | X | 6 | 4–8 | n/a | n/a |
| Q25y | X | 4.5 | 3–6 | n/a | n/a |
| Q25z | I | 32 | 24–40 | n/a | n/a |
| Q25aa | I | 12 | 8–16 | n/a | n/a |
| Q25ab | I | 8 | 6–10 | n/a | n/a |
| Q25ac | I | 8 | 6–10 | n/a | n/a |
| Q25ad | I | 6 | 4–8 | n/a | n/a |
| Q25ae | I | 16 | 12–20 | n/a | n/a |
| Q25af | I | 24 | 16–32 | n/a | n/a |
| Q25ag | I | 24 | 16–32 | n/a | n/a |
| Q25ah | I | 16 | 12–20 | n/a | n/a |
| Q25ai | I | 12 | 8–16 | n/a | n/a |
| Q25aj | I | 8 | 6–12 | n/a | n/a |
| Q25ak | I | 16 | 12–20 | n/a | n/a |
| Q25al | I | 12 | 8–16 | n/a | n/a |
| Q25am | X | 800 | 400–1,200 | n/a | n/a |
| Q25an | X | 400 | 200–600 | n/a | n/a |
| Q25ao | X | 800 | 400–1,200 | n/a | n/a |
| Q25ap | X | 1,200 | 600–1,800 | n/a | n/a |
| Q25aq | X | 800 | 400–1,200 | n/a | n/a |
| Q25ar | X | 40 | 24–56 | n/a | n/a |
| Q25as | X | 160 | 80–240 | n/a | n/a |
| Q25at | I | 140 | 80–200 | n/a | n/a |
| Q25au | I | 64 | 40–88 | n/a | n/a |
| Q25av | X | 48 | 32–64 | n/a | n/a |
| Q25aw | I | 96 | 64–128 | n/a | n/a |
| Q25ax | I | 96 | 64–128 | n/a | n/a |
| Q25ay | I | 120 | 80–160 | n/a | n/a |
| Q25az | I | 112 | 64–160 | n/a | n/a |
| Q25ba | X | 96 | 48–144 | n/a | n/a |
| Q25bb | X | 80 | 48–112 | n/a | n/a |
| Q25bc | I | 72 | 48–96 | n/a | n/a |
| Q25bd | I | 64 | 32–96 | n/a | n/a |
| Q25be | X | 296 | 168–424 | n/a | n/a |
| Q25bf | X | 176 | 96–256 | n/a | n/a |
| Q25bg | X | 40 | 22–58 | n/a | n/a |
| Q25bh | X | 200 | 110–290 | n/a | n/a |
| Q25bi | I | 32 | 18–46 | n/a | n/a |
| Q25bj | X | 72 | 40–104 | n/a | n/a |
| Q25bk | X | 64 | 36–92 | n/a | n/a |
| Q25bl | X | 40 | 22–58 | n/a | n/a |
| Q25bm | X | 48 | 26–70 | n/a | n/a |
| Q25bn | X | 40 | 22–58 | n/a | n/a |
| Q25bo | I | 48 | 26–70 | n/a | n/a |
| Q25bp | I | 40 | 24–56 | n/a | n/a |
| Q25bq | I | 24 | 14–34 | n/a | n/a |
| Q25br | I | 24 | 14–34 | n/a | n/a |
| Q25bs | I | 32 | 18–46 | n/a | n/a |
| Q25bt | X | 400 | 200–600 | n/a | n/a |
| Q25bu | X | 360 | 180–540 | n/a | n/a |
| Q25bv | X | 240 | 120–360 | n/a | n/a |
| Q25bw | I | 160 | 80–240 | n/a | n/a |
| Q25bx | I | 128 | 64–192 | n/a | n/a |
| Q25by | X | 32 | 16–48 | n/a | n/a |
| Q25bz | X | 64 | 32–96 | n/a | n/a |
| Q25ca | X | 48 | 24–72 | n/a | n/a |
| Q25cb | X | 32 | 16–48 | n/a | n/a |
| Q25cc | X | 32 | 16–48 | n/a | n/a |
| Q25cd | X | 96 | 48–144 | n/a | n/a |
| Q25ce | X | 96 | 48–144 | n/a | n/a |
| Q25cf | X | 96 | 48–144 | n/a | n/a |
| Q25cg | X | 32 | 16–48 | n/a | n/a |
| Q25ch | I | 112 | 64–160 | n/a | n/a |
| Q25ci | I | 112 | 64–160 | n/a | n/a |
| Q25cj | I | 56 | 32–80 | n/a | n/a |
| Q25ck | I | 72 | 40–104 | n/a | n/a |
| Q25cl | I | 28 | 16–40 | n/a | n/a |
| Q25cm | I | 44 | 24–64 | n/a | n/a |
| Q25cn | I | 44 | 24–64 | n/a | n/a |
| Q25co | I | 28 | 16–40 | n/a | n/a |
| Q25cp | I | 28 | 16–40 | n/a | n/a |
| Q25cq | I | 144 | 80–208 | n/a | n/a |
| Q25cr | I | 96 | 48–144 | n/a | n/a |
| Q25cs | I | 112 | 64–160 | n/a | n/a |
| Q25ct | I | 76 | 40–112 | n/a | n/a |
| Q25cu | I | 192 | 96–288 | n/a | n/a |
| Q25cv | I | 38 | 20–56 | n/a | n/a |
| Q25cw | I | 72 | 40–104 | n/a | n/a |
| Q25cx | I | 112 | 64–160 | n/a | n/a |
| Q25cy | I | 152 | 80–224 | n/a | n/a |
| Q25cz | X | 116 | 56–176 | n/a | n/a |
| Q25da | I | 192 | 96–288 | n/a | n/a |
| Q25db | X | 640 | 320–960 | n/a | n/a |
| Q25dc | X | 1,280 | 640–1,920 | n/a | n/a |
| Q25dd | X | 320 | 160–480 | n/a | n/a |
| Q25de | X | 480 | 240–720 | n/a | n/a |
| Q25df | X | 800 | 400–1,200 | n/a | n/a |
| Q25dg | X | 960 | 480–1,440 | n/a | n/a |
| Q25dh | X | 960 | 480–1,440 | n/a | n/a |
| Q25di | X | 800 | 400–1,200 | n/a | n/a |
| Q25dj | X | 320 | 160–480 | n/a | n/a |
| Q25dk | X | 640 | 320–960 | n/a | n/a |
| Q25dl | X | 1,280 | 640–1,920 | n/a | n/a |
| Q25dm | X | 1,920 | 960–2,880 | n/a | n/a |
| Q25dn | X | 640 | 320–960 | n/a | n/a |

## Language core proposals

Source design and missing-law analysis remain in [the core design](docs/language/core-design.md#proof-obligations-and-proposed-work-packages).

The [Vela whole-system proposal](#vela-whole-system-authoring-proposal) extends the intended authoring surface to general proofs, the ISA model and hardware. The bounded packages below retain their own scope and estimates; none includes that extension's full establishment or migration work.

The owner keys below identify technical contracts; their linked open checklist cells now own the planning budgets. The four existing estimates are carried forward once, while [shared foundations](#shared-foundation-and-retained-route) and [additional represented runtime work](#supported-release-implementation) have separate allocations. The [planning basis](#planning-basis-and-scope) distinguishes pricing from implementation entry and preserves Q21's historical rejection and all missing-evidence gates.

| Owner | Budget cell | Work and acceptance boundary |
| --- | --- | --- |
| `core-soundness` | [Q25as](#q25as) | Define judgments/interpreter and prove substitution, phase separation, preservation, loan/exit restoration and kinded authority/effect composition for this fragment over actual supplied logic laws; discharge the [borrow-analysis promotion joins](docs/language/core-design.md#borrow-analysis-promotion), including current-fact validity across writes. Excludes concrete CHERI primitive discovery, frontend and backend. |
| `core-frontend` | [Q25at](#q25at) | Restricted parsing/resolution, bounded flow analysis, reconstructed arithmetic, checked elaboration/SourcePackage correspondence and erasure preservation; derive source-bound loan/capture/effect facts and emit the promotion contract's checked derivations, with unknown facts and exhausted budgets explicit. Excludes general dependent inference, effect polymorphism, kernel, backend and editor. |
| `core-diagnostics` | [Q25au](#q25au) | Adapt the qualified interaction path to frontend derivations, typed holes, status and invalidation; demonstrate the specified source residuals. Excludes Q19a's existing-tool qualification and a new language server. |
| `core-repair-trial` | [Q25av](#q25av) | Author and qualify the combined fixture/negative neighbors and its concrete `PreparationOpen`/`finish` interpretation using the supplied resource laws, then measure semantic/refactor/representation replay and review. Excludes discovering those laws, a repair service and Q20's held-out staging adaptation. |

### Vela first-release delivery

[The first-release contract](docs/language/first-release.md#release-boundary)
owns the supported synchronous surface; its [qualification](docs/language/first-release.md#qualification)
and [workflow decision criteria](docs/assurance/workflow-contract.md#first-release-qualification-and-adoption)
own acceptance. R-05-020a and the dossiers settle interpretation policy without
supplying concrete machine laws or commissioning the production frontend.
Q25af/ag/ak/al supply current source-level kernel proofs and the authored
synchronous validator, owned loans and closed effects. The open
[release cells](#supported-release-implementation) price their general
correspondence, represented runtime and exact-artifact follow-through; the
[shared prerequisite cells](#shared-foundation-and-retained-route) separately
price missing machine logic, retained compilation, contextual security, TAL and
final-byte admission. The existing source proof and C/Sail execution evidence are
reused. Entry and acceptance remain distinct: a price supplies no missing law or
producer receipt.

| Stage and owner | Start and delivered result | Acceptance and stop condition |
| --- | --- | --- |
| Concrete foundation - Q25w and [shared follow-through](#shared-foundation-and-retained-route) | Q25w's finite investigation is closed; Q25af/ag/ak/al supply the current source carrier proofs, while shared cells own remaining canonical-machine/resource and retained-route laws | Reuse inhabited source cases; independently checked machine interpretation, compiler, security and admission evidence is still required before full artifact acceptance |
| Synchronous component - [Q25ba](#q25ba), `vela-first-slice` | Reuse the authored validator, failure exits, returned view and source proofs in [first_slice.vela](examples/first_slice.vela); consume independently checked first-client concrete-law, correspondence, compiler and admission receipts under [first-slice qualification](docs/language/first-release.md#first-slice-qualification) | Exact source connects to executable output and its checked contract; independently expected bytes/status, bounds, aliasing, restoration, wrong-operation and stale-input controls pass at the declared endpoint. Unsupported syntax is not a semantic rejection. Missing backend evidence stops artifact acceptance rather than relabeling a source theorem |
| Independent package trial - `vela-package-trial` | Working first slice and separately priced primitive/module/library support; a second client selected independently of the first API design | Separate modules, locked dependencies, explicit instances, real library calls and contract/representation/refactor changes; receiver snapshots, partial initialization, error propagation and exhaustion work without hidden rewrites. Measure annotations, review/repair effort, diagnostic and batch latency, stack/code/storage and target costs separately; freeze baseline and material-benefit threshold before the trial |
| Supported release - `vela-release` | Accepted slice and independent trial, versioned language/library scope and the required producer/admission closure | Publish the supported primitive/module semantics and conformance cases, truthful unsupported-feature diagnostics and reproducible build/proof artifacts. Every exported contract meets every policy; tests do not substitute for source/artifact/security proofs. The retained route and exact production-byte duties remain required |
| Bounded service extension - `vela-service` | Released synchronous core, a named asynchronous service and separately priced runtime classification/lifecycle, storage and control laws | Direct sequential helper await, one explicit child, declared task outcomes, capacity failure, ready/pending paths, both sides of commit, cleanup failure, simultaneous results and safe backing reuse. R-08-046 inventory/prose and manifests land before runtime implementation; no multi-shot search or shared counter is required unless that service needs it |
| Graded extension - Q25's existing soundness/frontend owners | Qualified synchronous resources, an independently selected client and a separately priced [selection trial](docs/extensions/graded-foundation.md#extension-selection-and-qualification) | Compare fixed modes and checked trace libraries with a bounded exact/bounded grading increment; justify general domains and type-use tracking independently. Preserve the same behavior/assurance endpoint and applicable GF proofs; freeze benefit thresholds and stop at the smaller qualified account when benefit or prerequisite evidence is absent. Optional [derivation and synthesis](docs/extensions/graded-foundation.md#conditional-usability-producers) need separate client/budget predicates and checked output; no first-release dependency or implementation commission follows |
| Other extensions - existing proposal owners | A concrete consumer and comparison showing material benefit over the smaller supported language | Multi-shot/shallow handlers, broad reflection, concurrent cells, extra tooling adapters, new native compiler/bootstrap, ISA migration and hardware authorship each retain separate scope, proofs, budget and adoption decision. None is a first-release dependency |

Existing parser, mathematical and basic editor qualification may finish within
its frozen scope. Q25x and conditional Q25y qualify generated tests for those
existing implementations under finite adoption decisions; neither adds a release
prerequisite, language feature or adapter. Q25w records the concrete foundation
investigation and blocking machine-refinement owners; subsequent delivery stages
now carry conditional budgets and retain those prerequisite gates. Q25z records the selected [familiar authoring surface](docs/language/surface-grammar.md#familiar-authoring-migration)
with bounded syntax and existing-consumer preparation permitted independently;
the validator's narrow runtime subset qualifies with its first artifact;
broader represented-library, ownership and production qualification follows that
accepted slice. Its [ergonomic refinement](docs/language/surface-grammar.md#ergonomic-authoring-and-bounded-collection-iteration)
adds no concrete-law prerequisite or semantic acceptance claim. Other syntax and
adapter breadth remain consumer-gated until the first slice works. Prioritize immutable batch inputs, diagnostics, navigation,
explicit formatting and inspectable proof obligations. The first release may
consume retained Rocq definitions and proofs; complete Vela proof authorship is
an independent option. Preserve the existing mandatory compiler, hardware and
OS work rather than putting this language experiment on their release path.

The independent package trial qualifies the [borrow-analysis promotion joins](docs/language/core-design.md#borrow-analysis-promotion)
on its real clients, with source-level positive and invalid-neighbor cases.
Any selected comparison with another borrow checker follows the diagnostic's
[comparison boundary](docs/language/loan-analysis.md#conditional-borrowing-comparison),
including pinned versions/modes, equivalent behavior and evidence endpoints,
unsupported cases and analysis-budget refusals. Receiver friction is measured
under the selected snapshot rule before a separate two-phase borrowing decision;
Ante-style aliases and general loop-carried borrowing retain their gated scope.

The independent package trial uses the [representation-transfer comparison](docs/assurance/workflow-contract.md#representation-transfer-comparison) to
test whether explicit native Rocq relations suffice before a separately priced
CoqEAL/Trocq experiment. It reuses Q25w and the machine-logic owners' concrete
laws; a new proof-transfer package supplies none of those prerequisites. Format
and protocol generation consume their existing descriptions, and compiler-service
adapters project shared facts. The [compiler evidence contract](docs/extensions/unified-source-contract.md#optimization-stages-and-evidence)
owns pass-theorem reuse and any proposed replacement of mandatory validation.
These are reuse boundaries within existing owners, not extra foundation or
compiler workstreams.

Technical feasibility, recurring developer value and economic adoption are
separate decisions. Full setup and maintenance costs stay visible; the first two
small clients need not amortize them. Freeze concrete target envelopes and
workloads before performance comparison, permitting declared size/speed/storage
tradeoffs inside mandatory limits. A safety, confidentiality or admission failure
cannot be averaged into an improvement. Q20's canceled comparison keeps its own
historical thresholds and gains no implicit recommissioning.

#### Remaining Vela ergonomics

These are the remaining delivery allocations for the
[implemented syntax and selected ergonomics](docs/language/surface-grammar.md#ergonomic-authoring-and-bounded-collection-iteration).
The open [release](#supported-release-implementation) and
[tooling cells](#tooling-and-metaprogramming) own their incremental budgets;
landed Q25 cells retain their completed scope. Q25z's syntax estimate does not
fund represented runtime producers, general correspondence or admission work.
Charge each shared law, frontend fact and projection once at its owner; the
following table allocates that work rather than creating extra estimate cells.

| Remaining slice and owner | Entry and delivery | Acceptance and stop condition | Pricing |
| --- | --- | --- | --- |
| Hosted syntax/consumer qualification — Q25g, Q25i, Q25k and Q25z | The settled parser, examples, exact-source consumers and retained independent fixtures | User-managed hosted Host CI and the applicable Guest CI parser/regeneration, migration and mathematical kernel replay pass for the selected revision. Missing, skipped or canceled verdicts remain pending. Q25h's Rocq-extracted checked parser and Python-parser retirement are qualified; user-managed hosted CI remains separate from local guest qualification. | Existing qualification cells; no duplicate estimate |
| Numeric aliases, raw strings, static formatting and library resolution — `core-frontend` | Accepted synchronous slice, actual represented scalar/text types, target/ABI and locked module producers; deliver the standard-library alias definitions, raw-string UTF-8 lowering and `Format<T>` / `TextBuilder<capacity>` buffer-writing formatting under the [numeric alias](docs/language/first-release.md#primitive-semantics) and [text/ownership contracts](docs/language/first-release.md#bytes-and-text) | Explicit import and qualification preserve alias/target type identity, layout, arithmetic, instance selection and source identity; raw strings strip closing-line indentation and normalize interior line breaks to LF (`\n`); `Format.Write(ref builder, $"...")` resolves coherent static `Format<T>` instances per hole without heap allocation, reflection or ambient locale and returns `Result<usize, CapacityError>` with declared prefix/rollback behavior. Boundary values, name/import collisions, standalone heap `$"..."` bindings, missing `Format<T>` instances, receiver-loan conflicts in holes and implicit conversion/default-type attempts reach the intended checks. Parser recognition supplies no library verdict. | [Q25aw](#q25aw), [Q25ax](#q25ax); shared prerequisites counted once |
| Represented contextual inference — `core-frontend`, joining `core-soundness` | Qualified represented types and the [contextual-inference contract](docs/language/first-release.md#contextual-inference); implement inference for the chosen runtime client | Explicit and inferred clients have the same checked interpretation and artifact endpoint. Cover unsuffixed range bounds, generics, lambdas and stable dependent indices; refuse conflicting widths, out-of-range literals, ambiguous types/instances and unstable indices. Preserve reviewed public signatures and explicit resource modes; never repair a typed operand with a coercion. | [Q25as](#q25as), [Q25at](#q25at); shared prerequisites counted once |
| Bounded iterator and `.Model` sequence laws, checking and lowering — `core-soundness`, `core-frontend` and `vela-software` | A real bounded iterator representation (`ISequenceModel<T>` / `IBoundedIterable<T>`), pre-proved `Seq<T>` `.Model` predicates/slices (`.All`, `.Any`, `.Contains`, `.Take`, `.Skip`, `.Slice`, `.Count`), named `invariant Clause: ...` conjuncts with selective `open (...) lifts Clause, ...` invariant lifting, two-step `CopyRepresentation`/`TransferType<T>` bulk relocation over vacant-slot storage (`Slots<T, capacity>`), and supplied concrete resource laws under the [ownership library contract](docs/language/first-release.md#ownership-libraries) and [refinement/domain tier](docs/language/core-design.md#refinement-effects-and-staging); checked derivations connect to the retained compiler route | Evaluate the collection once; establish value-copy permission or the selected `in`/`ref` element loan, bounds, initialization and termination/WCET, connect step `k` to `Model.At(k)`, `Model.Take(k)` and `Model.Skip(k)`, and discharge bounded finite-sequence `.Model` predicates and sparse prefix/suffix slot ranges through standard-library domain lemmas rather than open quantifier instantiation, stateful `IEnumerable<T>` enumerators or runtime `IQueryable<T>` reflection. Verify restoration on exhaustion, continue, break, return and propagation; verify that `open (...) lifts ...` keeps unlifted conjuncts active across disjoint/non-invalidating writes while refusing early exits, suspension or whole-receiver calls until lifted clauses are re-proved at block exit; verify that `CopyRepresentation` copies tag-preserving representation into vacant slots without arming destructors or duplicating linear ownership before erased `TransferType<T>` transfers prefix ownership in one range step; and pass the capacity-invariance gate ($N = 4$ versus $N = 10^9$ producing identical obligation counts, proof/certificate complexity and replay cost). Reject owned-element copying, reads of vacant slots, escaping/overlapping loans and invalidating mutation. Independent concrete outputs and source-to-artifact evidence qualify lowering; syntax alone does not. | [Q25ay](#q25ay), [Q25az](#q25az); shared prerequisites counted once |
| Borrow-aware diagnostics and editor assistance — `core-frontend`/`core-diagnostics` producers, `vela-compiler-services` facts and `vela-lsp` projections | Actual loan/effect/resource-exit analysis, resolved constructors, current versioned snapshots and a separately scoped editor consumer under the [LSP contract](docs/tooling/tooling-protocols.md#language-server-protocol) | Show exact receiver modes/views and both conflicting accesses. Snapshot edits preserve once-only evaluation, order, effects and lifetimes. Exhaustive Option/Result templates and propagation retain mandatory outcomes, cleanup, restoration and out-initialization. Refuse stale/unsupported suggestions; advertise each provider only after its producer and independent client controls qualify. | [Q25au](#q25au), [Q25ch](#q25ch), [Q25ci](#q25ci); shared prerequisites counted once |
| Wider formatting, binding lints and checked edit previews — `vela-authoring`, with `vela-lsp` only for a separately qualified editor action | Qualified wider syntax and compiler facts under the [authoring contract](docs/tooling/authoring-tools.md#lint-policy); extend beyond the implemented pure Nat/bool subset | Cover the canonical declarations, matches, generic calls and collection modes with token/comment/documentation preservation, idempotence and equivalent reparsed meaning. Generate assist-don't-coerce edit previews only from checked compiler facts; preserve source bytes by default, exact candidate interpretation and allow/deny policy, and reject changed or stale inputs without publication. | [Q25ck](#q25ck), [Q25ci](#q25ci); shared prerequisites counted once |
| Independent ergonomics and adoption evidence — `vela-package-trial` | Accepted synchronous slice plus an independently authored library client under the [first-release adoption protocol](docs/assurance/workflow-contract.md#first-release-qualification-and-adoption) | Exercise bounded input, buffer transformation, ordinary errors, resource-returning exits and a representation/refactor change. Freeze the baseline and material-benefit threshold; measure annotations, authoring/diagnosis effort and target/resource costs separately at the same assurance endpoint. Teach common modes before advanced grading; no safety or admission failure is averaged into a usability gain. | [Q25bb](#q25bb); shared prerequisites counted once |

### Deferred numerical workload selection

`numerical-client-selection` retains the [e-means research candidate](docs/extensions/numerical-workloads.md)
for a later bounded numerical verification workload. It is outside the priced
Q25 portfolio and supplies no first-release client or implementation commission.

Revisit when an independently named search-index or quantization-codebook
consumer has a frozen behavior contract and the required represented arithmetic,
sequence libraries and compiler joins are qualified. Select and price one bounded
assignment-and-update pilot, including any separately justified numerical
semantics work, before dispatch. Accept only under the dossier's
[bounded pilot contract](docs/extensions/numerical-workloads.md#bounded-pilot-acceptance),
with independent oracle results, checked source/artifact and resource evidence,
and separately measured numerical quality and target costs. Missing inputs leave
this deferred; the synchronous release and its independent package trial retain
their existing order and scope.

### Vela whole-system authoring proposal

The [pure translation prototype](docs/tooling/pure-prototype.md) is Q25e's
separately commissioned first executable tool; Q25f aligns it with the proposed
source surface. Its Nat/bool fragment denotes
generated CIC terms and exercises parsing, explicit checking and Gallina emission.
The selected development parser goal is
[Menhir generation](docs/assurance/verification-strategy.md#development-parser-and-grammar),
with a reviewed grammar of the proposed surface, located syntax trees and separate
elaboration. The `vela-parser` row below owns qualification and migration from the
handwritten prototype. Pinned-kernel replay of emitted definitions and independently
expected evaluations, followed by checked source correspondence, remain additional
work at the broader language boundary. The documented parser and mathematical
subsets already have kernel replay; general checked source correspondence remains
open. Each increment uses its reviewed cell and entry predicate before dispatch.
The full-language frontend retains Q25d's admission prerequisites.

The separately commissioned long-term option is one authored Vela codebase for operational software, independently reviewed contracts, mathematical proofs, the architectural machine model and hardware descriptions. The [unified-source contract](docs/extensions/unified-source-contract.md) owns the technical acceptance boundary. Generated Clight, Rocq proof terms, executable simulators, binaries and RTL remain permitted; the software golden artifact is the proof-connected production implementation. A separately maintained optimized rewrite is outside this goal.

A separate future option is a [native, verified, self-hosting compiler](docs/extensions/unified-source-contract.md#native-verified-compiler-and-self-hosting), authored in Vela and using its own intermediate representations to reach exact target bytes without a mandatory Clight/CompCert or LLVM stage. Reusable transformation proofs compose during compilation; independent kernel checking, verified bootstrap and final-artifact correspondence remain required. Competitive target optimization and commercial use, redistribution and resident rebuilding of the complete dependency closure need their own qualification. Interim compiler bridges remain valid while that endpoint is unbuilt.

The intended toolchain includes [compiler inspection, editor/debug protocols and
interchange exports](docs/tooling/tooling-protocols.md): versioned compiler
views, LSP semantic services, Tree-sitter/TextMate assets, SARIF, SCIP, build
integration, optimization remarks and compilation traces, with backend-dependent
RSP/GDB-MI and generated-source maps alongside DAP/DWARF. The separate stages
below own their interface and consumer qualification. They reuse
parser/frontend, contextual-diagnostic and backend work at its existing owners;
the `core-diagnostics` estimate excludes a new server. Semantic editor features
retain the concrete-law and source-correspondence prerequisites, while syntax-only development support can be scoped
earlier. Native debugging waits for its executable backend and exact-image debug
maps. Q25n, Q25o and Q25u supply bounded LSP lifecycle, pure-prototype diagnostics,
navigation, formatting and semantic tokens qualified across two independent editor
clients; the wider language-service interfaces remain open.

Prioritize immutable batch inputs, useful diagnostics, basic navigation, explicit
formatting and inspectable proof obligations for the supported subset. Freeze
additional syntax and adapter breadth until the synchronous component works.
Shared inspection, SARIF/SCIP, editor grammar distribution, build integration,
remarks/traces, remote-debug protocols and generated-output maps require actual
producers, named consumers and separately commissioned slices. Their existence
in this option portfolio makes none a first-release dependency.
The open [tooling/metaprogramming](#tooling-and-metaprogramming) and
[whole-system cells](#whole-system-delivery) now price these incremental stages.
The owner table below supplies technical joins; it adds no second estimate or
implementation acceptance to the current prototypes.

The [metaprogramming contract](docs/extensions/metaprogramming.md) adds ordinary
static computation, opt-in structural descriptions and contextual checked
generation to the intended surface. `vela-meta` first qualifies a scoped static
evaluation slice, then descriptor/derivation and cross-feature composition slices;
runtime-cost acceptance additionally needs the selected backend. Public semantic
snapshots belong to `vela-compiler-services`, shared with generation and LSP
clients. Q25m specifies these boundaries only. Q25k's mathematical prototype,
Q25i's existing syntax increment and the proposal estimates fund no additional
implementation. Each selected slice needs its own priced entry and acceptance
predicate; source and final-artifact qualification remain distinct.

Q25g/Q25h/Q25i already qualify the development/checked parser increments. The open cells now price the other owners' establishment and initial qualification, with finite release/tool maintenance rehearsals. Native compiler work is split into interpreted IRs, Vela implementation, representation/erasure, optimization, target construction, preservation and independent qualification; bootstrap, model adoption and hardware migration keep separate cells. Before implementation, freeze each selected inventory, satisfy its entry predicate, charge shared foundations once and take the required register/prose acts. The existing compiler, machine-logic and hardware work retains its accepted subjects until a successor passes the migration gate. AI may propose programs, proofs and optimizations; acceptance still requires checked evidence and independent review of intended behavior.

| Proposed owner and order | Start | Owns | Check | Join |
| --- | --- | --- | --- | --- |
| `vela-parser` · Menhir during development | Q25f's pure source baseline and the [bounded qualification and migration contract](docs/tooling/parser.md); Q25g commissions the pure syntax increment, Q25i the full development surface, and Q25h checked parsing and Python retirement | Q25g and Q25h own their separately priced qualification; broader parser construction stays in `core-frontend`'s existing scope and is charged once | The [development parser contract](docs/assurance/verification-strategy.md#development-parser-and-grammar), refined by Q25g/Q25h/Q25i's acceptance predicates; current compatibility and licensing records are inputs, not acceptance | The generated parser replaces Python parsing only after Q25h's migration predicates pass; full frontend admission retains Q25d's prerequisites, and Vela-authored parsing and retirement of seed/development dependencies remain `vela-native`/`vela-bootstrap` duties |
| `vela-meta` · staged evaluation and generation | A separately scoped interpretation and required-static interface, reviewed descriptor/construction protocol and the existing frontend-release predicates | Static evaluation, type/declaration descriptions, contextual hygienic derivation and evidence generation; separately qualify the selected dependent/graded/resource/effect interactions | [Metaprogramming qualification](docs/extensions/metaprogramming.md#qualification): independent codec intent and refusals, static/runtime separation, privacy/coherence, target semantics, stale dependency rejection and runtime-artifact cost evidence | Reuse `core-soundness`, frontend, diagnostics and compiler duties at the [composition joins](docs/extensions/full-language-review.md#metaprogramming-and-compiler-service-extension); no new kernel conversion or admission path, and no implicit budget extension |
| `vela-compiler-services` · shared source and inspection services | A separately priced supported subset and [inspection contract](docs/tooling/tooling-protocols.md#compiler-inspection-api); semantic operations retain their frontend prerequisites and lowering views their backend | Versioned concrete/resolved/typed/elaborated, analysis/proof and lowering views; machine-checkable schemas, bounded queries/bulk snapshots, generated origins and separately checked generation requests | [Inspection acceptance](docs/tooling/tooling-protocols.md#compiler-inspection-api): independent facts/client, source reconstruction, scoped handles, schema versions, partial statuses and stale dependency/configuration/target refusal | Compiler owners implement semantics once; `core-diagnostics` supplies judgments and adapters consume the same identities; no independent proof acceptance or mandatory LLVM representation |
| `vela-lsp` · editor services | Q25n's bounded lifecycle/diagnostic increment, with later compiler-service subsets gated by the first-release delivery and separately priced consumers under the [LSP contract](docs/tooling/tooling-protocols.md#language-server-protocol) | Overlays, navigation, diagnostics, source edits, semantic tokens and selected folding/selection/inlay/hierarchy capabilities; optional versioned proof-state presentation | [Protocol qualification](docs/tooling/tooling-protocols.md#qualification-and-delivery), including two clients, Unicode positions, dependency invalidation, semantic-token legend/deltas, stale replies and refusal of interactive proof acceptance | Shared compiler facts and batch-only evidence; semantic/proof features retain their producer prerequisites and Q25n buys no wider feature slice |
| `vela-highlight` · syntax grammar distribution | A separately priced consumer profile, canonical Menhir grammar/corpus and [highlighting contract](docs/tooling/tooling-protocols.md#syntax-grammars-and-highlighting) | Tree-sitter grammar/queries and TextMate lexical grammar for selected editor consumers | Intended consumers recover expected tokens/structure; fresh and incremental syntax agree after edits; malformed, Unicode and cross-feature cases retain declared recovery limits | Syntax-only assets follow the compiler grammar and grant no semantic acceptance; LSP semantic tokens remain `vela-lsp` work |
| `vela-authoring` · wider formatting and lints | Q25t's pure prototype, the [common authoring contract](docs/tooling/authoring-tools.md), qualified canonical syntax and separately priced frontend fact producers | Extend the shared StyleCop-inspired formatter and stable lints to the selected wider-language features and editor formatting requests | Token/comment and documentation-attachment preservation, idempotence, equivalent reparsed syntax, truthful supported scope, source-bound findings and immutable default checks and explicit source edits | Reuse compiler syntax/facts and default command policy; semantic/resource findings require their qualified checker, and no second grammar or admission route is introduced |
| `vela-sarif` · batch diagnostic export | A separately priced supported finding set, existing diagnostic producers and [SARIF contract](docs/tooling/tooling-protocols.md#diagnostic-and-semantic-index-exports) | SARIF 2.1.0 rules, findings, locations, related evidence, supported fixes/flows and input-bound completion status | Pinned schema and independent importer agree with expected cross-file/Unicode locations and fixes; malformed references, stale inputs and incomplete analysis cannot masquerade as a clean completed run | Reuse `core-diagnostics` judgments and shared snapshot identities; reports grant no proof/admission authority |
| `vela-scip` · offline semantic index | A separately priced resolved-symbol subset, source/configuration closure and [SCIP contract](docs/tooling/tooling-protocols.md#diagnostic-and-semantic-index-exports) | Pinned SCIP schema, symbol rules and offline projection; hash-bound provenance/scope manifest and Vela validation wrapper | Independent consumer queries expected definitions/references/implementations without LSP across shadowing/import/generation/rename cases; wrapper refuses stale bindings and reports incomplete scope without claiming reference absence | Consume compiler-resolved identities once; no substitute typed AST or proof-state schema |
| `vela-build` · build context and operations | A separately priced actual build/package graph, supported client and [build contract](docs/tooling/tooling-protocols.md#build-integration) | BSP targets/options/dependencies and bounded operations; compile_commands.json export for actual C/C++ bridge invocations | Independent clients recover target/configuration/generated-source facts and exact bridge arguments; cancellation, failed builds and stale graphs preserve batch verdicts | Build owners supply graph/tools once; no assumed C stage, duplicate module graph or interactive admission |
| `vela-remarks` · optimization explanations | A separately priced actual optimization producer and [remarks contract](docs/tooling/tooling-protocols.md#compiler-decisions-and-performance-traces) | LLVM-remarks-compatible export with pass/site decisions and documented Vela-specific reason records | Independent reader and chosen applied/missed/refused cases agree on decisions, source/IR origins and unsupported extensions | Existing compiler owns transformations and proofs; compatibility adds no mandatory LLVM pipeline or measured speedup claim |
| `vela-traces` · compiler performance visibility | A separately priced phase instrumentation profile and [trace contract](docs/tooling/tooling-protocols.md#compiler-decisions-and-performance-traces) | Chrome Trace Event JSON or native Perfetto export with clocks/units, nesting, workers, counters, identities and bounded recording | Independent viewer recovers deterministic fixture ordering/durations; recorder and Vela wrapper validate bound completeness metadata so dropped events, truncation, malformed time and cancellation cannot claim a complete measurement | Compiler phases own work once; overhead is measured separately and traces supply no emitted-program WCET evidence |
| `vela-dwarf` · native debug information | An executable producer with a fixed ABI, compiler source maps and the [DWARF contract](docs/tooling/tooling-protocols.md#dwarf-native-debug-information) | Emit and preserve source/type/scope/location/unwind data through final composition; exact-image sidecars, CHERI encodings and consumer compatibility | [Protocol qualification](docs/tooling/tooling-protocols.md#qualification-and-delivery), including independent reading, optimized locations, capability values, malformed sections and source/image mismatch | Native lowering and final-layout owners supply mappings once; metadata remains outside execution SRAM and the install path |
| `vela-dap` · source debugger | A separately qualified execution backend, matching source/debug artifacts and the [DAP contract](docs/tooling/tooling-protocols.md#debug-adapter-protocol); physical targets additionally require authorized development/RMA access | DAP lifecycle, source stops/stepping, stacks/scopes/values and bounded read-only evaluation; simulator first, explicit backend capabilities | [Protocol qualification](docs/tooling/tooling-protocols.md#qualification-and-delivery), including independently expected stops/values, stale handles, unauthorized inspection and production-target refusal | Consume `vela-dwarf` for native images; preserve hardware trigger exclusion and immutable code, without charging backend construction to the adapter |
| `vela-debug-backend` · conditional debugger integration | A named debugger-engine/simulator or authorized target connection, separately priced protocol subset and [backend contract](docs/tooling/tooling-protocols.md#debugger-backend-protocols) | GDB RSP for the selected engine/target link; GDB/MI only when driving GDB; exact registers and CHERI metadata | Independent engine observes expected stops/values and capability metadata; stale/reconnected targets, malformed packets and unauthorized operations are refused | Consume existing DAP/DWARF/backend work; no hardware triggers, code patching or production debug access; direct adapters need no RSP/MI layer |
| `vela-source-maps` · conditional generated-output maps | A selected compatible JavaScript/WebAssembly output consumer, separately priced exporter and [source-map contract](docs/tooling/tooling-protocols.md#generated-source-maps) | Pinned ECMA-426 export and hash-bound map/output/source manifest, with compiler-owned expansion origins and a Vela validation wrapper | Independent consumer resolves composed/Unicode/unmapped sites; separately the wrapper refuses changed map/output/source identities before consumer handoff; draft-only extensions stay explicit | Reuse compiler source maps once; native locations/types/unwinding remain DWARF duties and native-only stages need no ECMA-426 export |
| `vela-software` · operational software migration | Accepted first release, frozen software inventory and supplied component contracts/laws | Vela authorship, representation and source/artifact qualification beyond the two already priced release clients; reuse the retained compiler route | [Software acceptance](docs/extensions/unified-source-contract.md#software-and-proof-boundary), including every selected error/resource path, source edit and exact installed bytes | Current compiler/admission and canonical Sail consumers; no handwritten optimized implementation or second budget for the first-release bridge |
| `vela-proofs` · complete proof authorship | The interpreted frontend and reviewed theorem subjects for a selected library or metatheory package | General mathematical definitions and proofs in Vela, interoperating with retained checked libraries | [Proof-surface acceptance](docs/extensions/unified-source-contract.md#software-and-proof-boundary); no mandatory handwritten Rocq fallback for the accepted package | Rocq/CIC rechecks generated terms and exact assumptions; replacing its checker is a separate decision |
| `vela-native` · native verified compiler | Admitted source/IR interpretations, concrete CHERI laws, selected target and reviewed replacement-duty scope; independent of machine-authoring migration | Vela-authored native pipeline, representation and optimization proofs, selection/allocation, ABI, assembly/link/image construction and complete licence closure | [Native-compiler acceptance](docs/extensions/unified-source-contract.md#native-verified-compiler-and-self-hosting), including held-out systems/compute clients, checked search proposals, relational security, resources and final bytes | Current producers and validation remain required until equivalent evidence and explicit amendments admit the replacement; no assumed LLVM parity or performance saving |
| `vela-bootstrap` · verified self-hosting | Qualified native compiler definition, sufficient Vela implementation/proof surface and a reviewed seed/evaluation trust boundary | Connection from proved compiler definition to running binary, exact bootstrap stages and checked self-compilation of its declared source closure | [Bootstrap acceptance](docs/extensions/unified-source-contract.md#native-verified-compiler-and-self-hosting); source/binary correspondence and assumptions check, with reproducibility additional to the theorem | Resident-toolchain runtime/admission and distribution duties; independent evidence checking remains required |
| `vela-machine` · qualify the ISA replacement | An admitted interpretation, independently reviewed machine contract and the pinned Sail model | Vela-authored machine definition, parameterized configuration closure, executable semantics and migration agreement | [Machine-model acceptance](docs/extensions/unified-source-contract.md#machine-model) and its [negative cases](docs/extensions/unified-source-contract.md#qualification-cases) | Qualification replays binary logic, TAL, constant-time, timing and hardware evidence over one candidate term; accepted-generation consumers switch at adoption |
| `vela-hardware` · hardware authoring and generation | The hardware subset's reviewed cycle/register interpretation and selected block contract; machine adoption need not wait for every hardware port | Vela hardware descriptions and checked generation/refinement for each selected block | [Hardware acceptance](docs/extensions/unified-source-contract.md#hardware), preserving the block's required evidence or theorem tier | Retained RTL and imported-core paths through explicit interfaces; the final whole-system authoring claim needs every in-scope authored block |
| `vela-retirement` · canonical-model adoption and retirement | Accepted machine agreement, reviewed amendment dossier and completed affected-consumer inventory | Atomic adoption of the shared replacement model and retirement of active Sail authoring/tool dependencies | [Migration and retirement](docs/extensions/unified-source-contract.md#migration-and-retirement); no private semantics, circular oracle or missing consumer evidence | Updated register/prose and all affected compiler, admission, proof, emulator, timing and hardware artifacts in the same admitted generation |

The proof surface, native compiler and hardware subset may be qualified independently once their own inputs exist; verified self-hosting consumes the qualified native compiler. Machine adoption is a separate decision from hardware-source migration: both sides of the retained hardware theorem must name the newly admitted canonical model before Sail retires, even when the hardware description is still authored through the current route. Historical Sail evidence remains retained. Complete single-language authorship additionally requires replacing every in-scope handwritten implementation and proof surface and, for the declared toolchain closure, qualifying the native compiler and bootstrap; a successful compiler frontend alone closes none of those claims.

### Owner-to-budget allocation

These links allocate the stage tables to checklist cells; they add no hours.

| Owner or delivery slice | Budget cells |
| --- | --- |
| `Shared prerequisite owners` | [Q25am](#q25am), [Q25an](#q25an), [Q25ao](#q25ao), [Q25ap](#q25ap), [Q25aq](#q25aq), [Q25ar](#q25ar) |
| `Core interpretation/frontend/diagnostics/fixture` | [Q25as](#q25as), [Q25at](#q25at), [Q25au](#q25au), [Q25av](#q25av) |
| `Represented runtime libraries/packages/lowering` | [Q25aw](#q25aw), [Q25ax](#q25ax), [Q25ay](#q25ay), [Q25az](#q25az) |
| `vela-first-slice / vela-package-trial / vela-release` | [Q25ba](#q25ba), [Q25bb](#q25bb), [Q25bc](#q25bc) |
| `vela-service / bounded pools` | [Q25bw](#q25bw), [Q25bx](#q25bx) |
| `Graded/control/mutation and assurance-policy extensions` | [Q25be](#q25be), [Q25bf](#q25bf), [Q25bg](#q25bg), [Q25bh](#q25bh), [Q25bi](#q25bi), [Q25bj](#q25bj), [Q25bk](#q25bk), [Q25bl](#q25bl), [Q25bm](#q25bm), [Q25bn](#q25bn), [Q25bo](#q25bo), [Q25bp](#q25bp), [Q25bq](#q25bq), [Q25br](#q25br), [Q25bs](#q25bs), [Q25bt](#q25bt), [Q25bu](#q25bu), [Q25bv](#q25bv) |
| `Conditional usability, borrowing and proof-transfer trials` | [Q25by](#q25by), [Q25bz](#q25bz), [Q25ca](#q25ca), [Q25cb](#q25cb), [Q25cc](#q25cc), [Q25cd](#q25cd), [Q25ce](#q25ce), [Q25cf](#q25cf), [Q25cg](#q25cg) |
| `vela-meta` | [Q25cw](#q25cw), [Q25cx](#q25cx), [Q25cy](#q25cy), [Q25cz](#q25cz) |
| `vela-native` | [Q25dd](#q25dd), [Q25de](#q25de), [Q25df](#q25df), [Q25dg](#q25dg), [Q25dh](#q25dh), [Q25di](#q25di), [Q25dj](#q25dj) |
| `Maintenance` | [Q25bd](#q25bd), [Q25da](#q25da) |
| `vela-compiler-services` | [Q25ch](#q25ch) |
| `vela-lsp` | [Q25ci](#q25ci) |
| `vela-highlight` | [Q25cj](#q25cj) |
| `vela-authoring` | [Q25ck](#q25ck) |
| `vela-sarif` | [Q25cl](#q25cl) |
| `vela-scip` | [Q25cm](#q25cm) |
| `vela-build` | [Q25cn](#q25cn) |
| `vela-remarks` | [Q25co](#q25co) |
| `vela-traces` | [Q25cp](#q25cp) |
| `vela-dwarf` | [Q25cq](#q25cq) |
| `debug-runtime` | [Q25cr](#q25cr) |
| `vela-dap` | [Q25cs](#q25cs) |
| `vela-debug-backend` | [Q25ct](#q25ct) |
| `web-output` | [Q25cu](#q25cu) |
| `vela-source-maps` | [Q25cv](#q25cv) |
| `vela-proofs` | [Q25db](#q25db) |
| `vela-software` | [Q25dc](#q25dc) |
| `vela-bootstrap` | [Q25dk](#q25dk) |
| `vela-machine` | [Q25dl](#q25dl) |
| `vela-hardware` | [Q25dm](#q25dm) |
| `vela-retirement` | [Q25dn](#q25dn) |

The existing `vela-parser` stage reuses completed Q25g/h/i; later Vela-authored
parsing is in the native implementation and bootstrap cells. Source maps have
an explicit web-output producer; DAP has an explicit simulator execution producer.
Host protocol projections do not silently acquire resident transports or admission.
