# VelaLang Design and Conformance Critique

Critique dispositions for Vela's practical release, kernel-honest elaboration evidence, first-slice conformance, and surface ergonomics, extracted from [VerifiedOS](https://github.com/symbiogenesis/VerifiedOS).

## Vela practical release <a id="vela-interface-clarity"></a>

[Q25v](../PLAN.md#q-assessment-actions) accepts the practical-design review
as changes to the owning contracts. The first product is [bounded synchronous
software](first-release.md#release-boundary), with checked
contracts and one retained compiler route. The project retains its security-first
priority: reducing implementation coupling never weakens binary admission,
source correspondence, resource bounds, confidentiality or independent review.

| Finding and judgment | Disposition and implementation owner |
| --- | --- |
| A broad language portfolio does not establish a deliverable critical path | [Q25w and the delivery sequence](../PLAN.md#vela-first-release-delivery) first investigate one concrete buffer carrier within a finite budget. Subsequent source, artifact, package and release stages require actual prerequisites and separately priced checklist cells. Missing foundations remain visible. |
| General grade algebras and runtime continuation cloning lack a demonstrated first-release consumer | Fixed usage/ownership modes and erased proof data serve the initial runtime. [General grades](extensions/graded-foundation.md), multi-shot/shallow handlers and broad reflection are optional extensions, requiring a useful client and independent qualification. Native self-hosting, ISA replacement and hardware authorship remain separate decisions. |
| Adopting Granule/Gerty's central ideas establishes neither an implemented graded language nor an optimal feature set | [Q25's graded-extension selection](../PLAN.md#vela-first-release-delivery) compares checked library accounting and bounded source grades before general domains or full type-use tracking. The [qualification protocol](extensions/graded-foundation.md#extension-selection-and-qualification) separates semantic proofs, client benefit and the conditional substitution optimization; derived combinators and synthesis retain their own producer predicates. R-05-020a and R-05-132 through R-05-134 keep correspondence and TAL obligations unchanged. |
| Sequential async helpers should not require child concurrency machinery | [Direct await](extensions/handlers-async.md#frames-child-ownership-and-reaction-execution) consumes a dormant computation in the current task's bounded graph, with storage, checkpoints and cleanup accounted. `vela-service` qualifies it before general handler combinations; spawn remains explicit child registration. |
| Ordinary domain errors and task failure need different meanings | [The task lifecycle](extensions/handlers-async.md#frames-child-ownership-and-reaction-execution) separates completed payloads, cancellation resources and declared task failure. A completed `Err` alone does not cancel siblings; explicit early exit/failure follows the scope's cancel-and-join contract. |
| An accepted interface displaying an unestablished `ensures` is a human review trap even if proof search ignores it | [The assurance contract](extensions/assurance-profiles.md) makes authored exported clauses obligations under every preset. Omitted optional contracts and separately marked scratch conjectures remain available; unfinished interface evidence blocks acceptance. `vela-first-slice` and `vela-package-trial` qualify configuration and dependency invalidation. |
| Primitive and module principles need an implementable language contract | [Primitive semantics](first-release.md#primitive-semantics) settle arithmetic, representations and bytes/text; [module/package rules](first-release.md#modules-and-packages) settle identity, instances, imports and locked closure. The package trial exercises independently authored libraries and changed contracts. Grammar support alone supplies no semantics. |
| Safe ownership rules need usable collection and construction interfaces | [Ownership libraries](first-release.md#ownership-libraries) cover partial/fallible initialization and rollback without weakening `out`, plus receiver-conflict diagnostics and snapshot rewrites. The independent client decides whether later two-phase borrowing earns its extra proof cost. |
| Default checking/emission should preserve its input | [The authoring contract](authoring-tools.md#compiler-commands-and-publication) selects immutable batch inputs and explicit formatting. Q25t implements source-preserving default checks and emission, with independent snapshot, refusal and explicit-write controls; hosted validation remains user-managed. |
| Early pilot economics should not substitute for product criteria | [The new workflow criteria](workflow-contract.md#first-release-qualification-and-adoption) separate feasibility, recurring value and adoption, retaining all setup costs without requiring two tiny clients to amortize the language. Declared performance tradeoffs remain inside mandatory limits. Canceled Q20 thresholds retain their historical scope. |

[R-05-020a](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/spec.md#r-05-020a) settles the untrusted-elaborator classification,
with the dossiers' laws interpreted in existing anchors. It supplies no new
trusted checker or checked machine law. The source/production proof endpoints
remain distinct, and the later task/continuation/guard inventory amendment stays
owed before that runtime extension. This disposition changes design and planning;
it claims no implemented ownership language, service runtime or performance gain.

## Vela evidence, conformance and surface review <a id="vela-evidence-and-surface-review"></a>

A review of the first slice, its elaborator and the release documents found that
the [Q25w](../PLAN.md#q-assessment-actions) candidate's kernel evidence does
not carry its source claims, that the slice departs from the synchronous design it
qualifies, and that the surface and documents impose avoidable costs. The
judgments below are accepted; Q25af through Q25ai own the follow-through.

| Finding and judgment | Disposition and implementation owner |
| --- | --- |
| Solver-discharged contracts and theorems reach Rocq as `true = true`. The elaborator replaces every proposition its Python solver discharges, and every theorem with mutated `ref` parameters, by `eq_refl true`; `restores` obligations for `ref` parameters are emitted as `x = x`. `Closed under the global context` therefore checks tautologies for most of the first slice's laws, scenarios and contracts, contrary to the [untrusted-elaboration boundary](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/spec.md#r-05-020a). | Q25af emits the real proposition for every obligation, kernel-proves what it can and records every remaining solver-trusted obligation as a named, counted assumption that blocks acceptance. The [Q25w record](completion-log.md#q25w-investigate-the-concrete-vela-buffer-foundation-within-a-fixed-budget) is a blocked outcome with no candidate acceptance. |
| The Gallina integer model disagrees with the source semantics: multiplication, division, remainder, negation and shifts are identity functions of their first operand; saturating and checked operations, conversions and `to_nat` are placeholders; signed comparisons compare unsigned bit patterns. A kernel statement over these operations describes a different program from the one the solver and target execute. | Q25af defines every primitive by the [primitive contract](first-release.md#primitive-semantics), with independent value controls. |
| The first slice contradicts the design it qualifies: an explicit `Span.Restore` call, capability fields in client contracts, `Span.AllocZeroed` fabricating a span from an integer base in executable code, a flag-plus-error record instead of a `Result` carrying a place-named view, no `effects` clauses, and a returned view into `dst` after `dst` is restored, which [the core design](core-design.md#intended-negative-neighbors) lists as a required refusal. Its contracts state no content facts; scenarios mirror the implementation's checksum rather than an independent format model. | Q25ag rewrites the slice to the synchronous design, adds the missing elaborator rules and an independent format model, and turns the restore-then-return pattern into a semantic negative control. |
| The capacity-invariance gate cannot fail for the intended reason: no obligation in its fixture ranges over the capacity. | Q25ag replaces the fixture with a capacity-wide bounded loop whose obligations must stay symbolic. |
| The surface overloads `scope` for task scopes and invariant lifting, gives `restores` different meanings in design and implementation, accepts two spellings for an immutable typed local, needs `None()` plus an advisory lint because bare pattern names bind, and keeps two match forms. | Q25ah renames invariant lifting to `open (...) lifts`, settles `restores` on its returned-loan meaning, requires `let`/`var`, distinguishes constructors from binders by token shape and unifies match arms. |
| The release has no compact language reference; extension research and dated market comparisons sit beside the release contract, and the product contract omits the costs of representability proofs, closed effect lists and the borrow restrictions. | Q25ai adds the reference, separates extension dossiers and background comparisons from the release documents, and states the costs with the package trial's measurement duties. |
| The development frontend is a Python elaborator beside the selected Menhir/OCaml route. | Retained: kernel rechecking bounds its trust once Q25af lands; [Q25h](../PLAN.md#q-assessment-actions) keeps parser migration and the native frontend keeps elaboration. |
