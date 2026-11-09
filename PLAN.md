# VelaLang Plan and Backlog

This document is the source of truth for Vela language design, parser and elaborator qualification, authoring tooling, first-release delivery, and whole-system authoring proposals, extracted from [VerifiedOS](https://github.com/symbiogenesis/VerifiedOS).

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
- [ ] **Q25al · Elaborate consuming ownership (`owned` parameters and `move` transfers), general `in`/`ref` runtime value loans, and closed `effects` footprints (`reads`/`writes`/`calls`)** · 12 h retained estimate, actual n/a · agent-parallel
  - Elaborates consuming `owned T` parameters and data fields, `move expr` transfers (including consuming record updates `move base with { ... }` and call-site `move` arguments), flow-sensitive use-after-move (`use-after-owner-move`), partial-move (`partial-owner-move-unsupported`), and move-through-loan (`move-through-loan-unsupported`) refusals, general `in T` and `ref T` runtime value loans across all runtime value types, and closed `effects` contract verification across `reads(...)`, `writes(...)`, `calls(...)` (including transitive callee and higher-order parameter calls), and `effects none`.

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

## Language core proposals

Source design and missing-law analysis remain in [the core design](docs/language/core-design.md#proof-obligations-and-proposed-work-packages).

The [Vela whole-system proposal](#vela-whole-system-authoring-proposal) extends the intended authoring surface to general proofs, the ISA model and hardware. The bounded packages below retain their own scope and estimates; none includes that extension's full establishment or migration work.

The following owner keys are proposals, not schedule IDs or proof constants. Each selected package needs a reviewed checklist cell and entry predicate before implementation dispatch. Estimates are prospective attended-work design judgments, not measured agent-session results or conversions of the strategy's person-month bands. They exclude the unbounded foundation work and therefore do not establish a complete implementation price. Keep eventual human attended work, summed agent-session wall time and machine time in separate ledgers under Q20a. The general-logic and machine connections remain [Q2c's prerequisites](PLAN.md#q-assessment-actions); its rejection supplies neither an implementation budget nor a law.

| Proposed owner | Estimate | Work and acceptance boundary |
| --- | --- | --- |
| `core-soundness` | 160 h, range 80-240 | Define judgments/interpreter and prove substitution, phase separation, preservation, loan/exit restoration and kinded authority/effect composition for this fragment over actual supplied logic laws; discharge the [borrow-analysis promotion joins](docs/language/core-design.md#borrow-analysis-promotion), including current-fact validity across writes. Excludes concrete CHERI primitive discovery, frontend and backend. |
| `core-frontend` | 140 h, range 80-200 | Restricted parsing/resolution, bounded flow analysis, reconstructed arithmetic, checked elaboration/SourcePackage correspondence and erasure preservation; derive source-bound loan/capture/effect facts and emit the promotion contract's checked derivations, with unknown facts and exhausted budgets explicit. Excludes general dependent inference, effect polymorphism, kernel, backend and editor. |
| `core-diagnostics` | 64 h, range 40-88 | Adapt the qualified interaction path to frontend derivations, typed holes, status and invalidation; demonstrate the specified source residuals. Excludes Q19a's existing-tool qualification and a new language server. |
| `core-repair-trial` | 48 h, range 32-64 | Author and qualify the combined fixture/negative neighbors and its concrete `PreparationOpen`/`finish` interpretation using the supplied resource laws, then measure semantic/refactor/representation replay and review. Excludes discovering those laws, a repair service and Q20's held-out staging adaptation. |

### Vela first-release delivery

[The first-release contract](docs/language/first-release.md#release-boundary)
owns the supported synchronous surface; its [qualification](docs/language/first-release.md#qualification)
and [workflow decision criteria](docs/assurance/workflow-contract.md#first-release-qualification-and-adoption)
own acceptance. R-05-020a and the dossiers settle interpretation policy without
supplying concrete laws or commissioning the production frontend. Q25w is the
only newly priced foundation investigation. These successive implementation
owners remain unpriced until its evidence makes their scope responsibly estimable;
they add nothing to the checklist totals. Before any implementation, each selected
stage becomes a reviewed checklist cell with a complete prerequisite inventory,
finite budget, acceptance predicate and stop condition. No stage may hide missing
machine logic, CHERI compilation, TAL, contextual security or final-byte work in
its upper range; existing owners supply those joins once.

| Stage and owner | Start and delivered result | Acceptance and stop condition |
| --- | --- | --- |
| Concrete foundation - Q25w | Named decoder destination, reviewed interpretation and one canonical machine carrier; produce actual primitive/representation laws and an inhabited byte case | Its finite investigation predicate above; absent or pending evidence keeps every dependent implementation closed |
| Synchronous component - `vela-first-slice` | Qualified concrete laws and a separately priced retained backend/source-correspondence closure; author one bounded initialize/copy/validate component ([first_slice.vela](examples/first_slice.vela)) with actual failure exits and a returned view ([first-slice qualification](docs/language/first-release.md#first-slice-qualification)) | Exact source connects to executable output and its checked contract; independently expected bytes/status, bounds, aliasing, restoration, wrong-operation and stale-input controls pass at the declared endpoint. Unsupported syntax is not a semantic rejection. Missing backend evidence stops artifact acceptance rather than relabeling a source theorem |
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
remain unpriced until those prerequisites close. Q25z records the selected [familiar authoring surface](docs/language/surface-grammar.md#familiar-authoring-migration)
with bounded syntax and existing-consumer preparation permitted independently;
represented-library, ownership and production qualification follow the accepted
first slice. Its [ergonomic refinement](docs/language/surface-grammar.md#ergonomic-authoring-and-bounded-collection-iteration)
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
They add no estimate cells or implementation commission. Existing Q25 cells own
their remaining qualification; runtime/library and wider editor slices are
**unpriced** until their concrete prerequisites permit a reviewed checklist cell
with its own budget and acceptance predicate. Q25z's syntax estimate does not
fund those producers or absorb missing foundation, compiler or admission work.
Charge each shared law, frontend fact and projection once at its owner.

| Remaining slice and owner | Entry and delivery | Acceptance and stop condition | Pricing |
| --- | --- | --- | --- |
| Hosted syntax/consumer qualification — Q25g, Q25i, Q25k and Q25z | The settled parser, examples, exact-source consumers and retained independent fixtures | User-managed hosted Host CI and the applicable Guest CI parser/regeneration, migration and mathematical kernel replay pass for the selected revision. Missing, skipped or canceled verdicts remain pending. Q25h's Rocq-extracted checked parser and Python-parser retirement are qualified; user-managed hosted CI remains separate from local guest qualification. | Existing qualification cells; no duplicate estimate |
| Numeric aliases, raw strings, static formatting and library resolution — `core-frontend` | Accepted synchronous slice, actual represented scalar/text types, target/ABI and locked module producers; deliver the standard-library alias definitions, raw-string UTF-8 lowering and `Format<T>` / `TextBuilder<capacity>` buffer-writing formatting under the [numeric alias](docs/language/first-release.md#primitive-semantics) and [text/ownership contracts](docs/language/first-release.md#bytes-and-text) | Explicit import and qualification preserve alias/target type identity, layout, arithmetic, instance selection and source identity; raw strings strip closing-line indentation and normalize interior line breaks to LF (`\n`); `Format.Write(ref builder, $"...")` resolves coherent static `Format<T>` instances per hole without heap allocation, reflection or ambient locale and returns `Result<usize, CapacityError>` with declared prefix/rollback behavior. Boundary values, name/import collisions, standalone heap `$"..."` bindings, missing `Format<T>` instances, receiver-loan conflicts in holes and implicit conversion/default-type attempts reach the intended checks. Parser recognition supplies no library verdict. | Unpriced outside Q25z; price the concrete library/frontend slice at entry |
| Represented contextual inference — `core-frontend`, joining `core-soundness` | Qualified represented types and the [contextual-inference contract](docs/language/first-release.md#contextual-inference); implement inference for the chosen runtime client | Explicit and inferred clients have the same checked interpretation and artifact endpoint. Cover unsuffixed range bounds, generics, lambdas and stable dependent indices; refuse conflicting widths, out-of-range literals, ambiguous types/instances and unstable indices. Preserve reviewed public signatures and explicit resource modes; never repair a typed operand with a coercion. | Unpriced concrete frontend/law slice; reuse existing laws once |
| Bounded iterator and `.Model` sequence laws, checking and lowering — `core-soundness`, `core-frontend` and `vela-software` | A real bounded iterator representation (`ISequenceModel<T>` / `IBoundedIterable<T>`), pre-proved `Seq<T>` `.Model` predicates/slices (`.All`, `.Any`, `.Contains`, `.Take`, `.Skip`, `.Slice`, `.Count`), named `invariant Clause: ...` conjuncts with selective `open (...) lifts Clause, ...` invariant lifting, two-step `CopyRepresentation`/`TransferType<T>` bulk relocation over vacant-slot storage (`Slots<T, capacity>`), and supplied concrete resource laws under the [ownership library contract](docs/language/first-release.md#ownership-libraries) and [refinement/domain tier](docs/language/core-design.md#refinement-effects-and-staging); checked derivations connect to the retained compiler route | Evaluate the collection once; establish value-copy permission or the selected `in`/`ref` element loan, bounds, initialization and termination/WCET, connect step `k` to `Model.At(k)`, `Model.Take(k)` and `Model.Skip(k)`, and discharge bounded finite-sequence `.Model` predicates and sparse prefix/suffix slot ranges through standard-library domain lemmas rather than open quantifier instantiation, stateful `IEnumerable<T>` enumerators or runtime `IQueryable<T>` reflection. Verify restoration on exhaustion, continue, break, return and propagation; verify that `open (...) lifts ...` keeps unlifted conjuncts active across disjoint/non-invalidating writes while refusing early exits, suspension or whole-receiver calls until lifted clauses are re-proved at block exit; verify that `CopyRepresentation` copies tag-preserving representation into vacant slots without arming destructors or duplicating linear ownership before erased `TransferType<T>` transfers prefix ownership in one range step; and pass the capacity-invariance gate ($N = 4$ versus $N = 10^9$ producing identical obligation counts, proof/certificate complexity and replay cost). Reject owned-element copying, reads of vacant slots, escaping/overlapping loans and invalidating mutation. Independent concrete outputs and source-to-artifact evidence qualify lowering; syntax alone does not. | Unpriced iterator, sequence-domain, frontend and route joins; no hidden addition to syntax or foundation estimates |
| Borrow-aware diagnostics and editor assistance — `core-frontend`/`core-diagnostics` producers, `vela-compiler-services` facts and `vela-lsp` projections | Actual loan/effect/resource-exit analysis, resolved constructors, current versioned snapshots and a separately scoped editor consumer under the [LSP contract](docs/tooling/tooling-protocols.md#language-server-protocol) | Show exact receiver modes/views and both conflicting accesses. Snapshot edits preserve once-only evaluation, order, effects and lifetimes. Exhaustive Option/Result templates and propagation retain mandatory outcomes, cleanup, restoration and out-initialization. Refuse stale/unsupported suggestions; advertise each provider only after its producer and independent client controls qualify. | Unpriced selected producer/projection slices; the diagnostic estimate buys no new server |
| Wider formatting, binding lints and checked edit previews — `vela-authoring`, with `vela-lsp` only for a separately qualified editor action | Qualified wider syntax and compiler facts under the [authoring contract](docs/tooling/authoring-tools.md#lint-policy); extend beyond the implemented pure Nat/bool subset | Cover the canonical declarations, matches, generic calls and collection modes with token/comment/documentation preservation, idempotence and equivalent reparsed meaning. Generate assist-don't-coerce edit previews only from checked compiler facts; preserve source bytes by default, exact candidate interpretation and allow/deny policy, and reject changed or stale inputs without publication. | Unpriced wider slice; pure Q25t/Q25z implementation is reused |
| Independent ergonomics and adoption evidence — `vela-package-trial` | Accepted synchronous slice plus an independently authored library client under the [first-release adoption protocol](docs/assurance/workflow-contract.md#first-release-qualification-and-adoption) | Exercise bounded input, buffer transformation, ordinary errors, resource-returning exits and a representation/refactor change. Freeze the baseline and material-benefit threshold; measure annotations, authoring/diagnosis effort and target/resource costs separately at the same assurance endpoint. Teach common modes before advanced grading; no safety or admission failure is averaged into a usability gain. | Existing unpriced package-trial owner; no separate duplicate experiment |

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
work. Each increment needs its own reviewed cell and estimate before dispatch.
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
All stages below remain unpriced beyond their explicitly commissioned Q25 slices;
adding an owner does not add an implementation to the current prototypes or spend
the existing core estimates.

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

Q25g and Q25h commission the bounded parser increments in the table; Q25i commissions the wider syntax portion of core-frontend. The other proposal owner keys have establishment and maintenance costs **unpriced**. They are not checklist IDs, checked artifacts or additions to the priced totals. Before implementation, split a selected stage into reviewed checklist cells with its own budget and entry predicate, charge shared foundation work once, and take the required register/prose acts. The existing compiler, machine-logic and hardware work retains its accepted subjects until a successor passes the migration gate. AI may propose programs, proofs and optimizations; acceptance still requires checked evidence and independent review of intended behavior.

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
| `vela-software` · first software bridge | The first-release commissioning predicates and the actual CHERI laws required by the selected component | Vela source/contract correspondence and explicit-memory lowering through the retained compiler route | [Software acceptance](docs/extensions/unified-source-contract.md#software-and-proof-boundary), including error paths, source edits and exact installed bytes | Current compiler/admission and canonical Sail consumers; no handwritten optimized implementation for the accepted family |
| `vela-proofs` · complete proof authorship | The interpreted frontend and reviewed theorem subjects for a selected library or metatheory package | General mathematical definitions and proofs in Vela, interoperating with retained checked libraries | [Proof-surface acceptance](docs/extensions/unified-source-contract.md#software-and-proof-boundary); no mandatory handwritten Rocq fallback for the accepted package | Rocq/CIC rechecks generated terms and exact assumptions; replacing its checker is a separate decision |
| `vela-native` · native verified compiler | Admitted source/IR interpretations, concrete CHERI laws, selected target and reviewed replacement-duty scope; independent of machine-authoring migration | Vela-authored native pipeline, representation and optimization proofs, selection/allocation, ABI, assembly/link/image construction and complete licence closure | [Native-compiler acceptance](docs/extensions/unified-source-contract.md#native-verified-compiler-and-self-hosting), including held-out systems/compute clients, checked search proposals, relational security, resources and final bytes | Current producers and validation remain required until equivalent evidence and explicit amendments admit the replacement; no assumed LLVM parity or performance saving |
| `vela-bootstrap` · verified self-hosting | Qualified native compiler definition, sufficient Vela implementation/proof surface and a reviewed seed/evaluation trust boundary | Connection from proved compiler definition to running binary, exact bootstrap stages and checked self-compilation of its declared source closure | [Bootstrap acceptance](docs/extensions/unified-source-contract.md#native-verified-compiler-and-self-hosting); source/binary correspondence and assumptions check, with reproducibility additional to the theorem | Resident-toolchain runtime/admission and distribution duties; independent evidence checking remains required |
| `vela-machine` · qualify the ISA replacement | An admitted interpretation, independently reviewed machine contract and the pinned Sail model | Vela-authored machine definition, parameterized configuration closure, executable semantics and migration agreement | [Machine-model acceptance](docs/extensions/unified-source-contract.md#machine-model) and its [negative cases](docs/extensions/unified-source-contract.md#qualification-cases) | Qualification replays binary logic, TAL, constant-time, timing and hardware evidence over one candidate term; accepted-generation consumers switch at adoption |
| `vela-hardware` · hardware authoring and generation | The hardware subset's reviewed cycle/register interpretation and selected block contract; machine adoption need not wait for every hardware port | Vela hardware descriptions and checked generation/refinement for each selected block | [Hardware acceptance](docs/extensions/unified-source-contract.md#hardware), preserving the block's required evidence or theorem tier | Retained RTL and imported-core paths through explicit interfaces; the final whole-system authoring claim needs every in-scope authored block |
| `vela-retirement` · canonical-model adoption and retirement | Accepted machine agreement, reviewed amendment dossier and completed affected-consumer inventory | Atomic adoption of the shared replacement model and retirement of active Sail authoring/tool dependencies | [Migration and retirement](docs/extensions/unified-source-contract.md#migration-and-retirement); no private semantics, circular oracle or missing consumer evidence | Updated register/prose and all affected compiler, admission, proof, emulator, timing and hardware artifacts in the same admitted generation |

The proof surface, native compiler and hardware subset may be qualified independently once their own inputs exist; verified self-hosting consumes the qualified native compiler. Machine adoption is a separate decision from hardware-source migration: both sides of the retained hardware theorem must name the newly admitted canonical model before Sail retires, even when the hardware description is still authored through the current route. Historical Sail evidence remains retained. Complete single-language authorship additionally requires replacing every in-scope handwritten implementation and proof surface and, for the declared toolchain closure, qualifying the native compiler and bootstrap; a successful compiler frontend alone closes none of those claims.
