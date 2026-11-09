# Vela development parser qualification

The [primary Vela design and examples](../assurance/verification-strategy.md) explains the language;
this contract owns the development parser's bounded qualification and retirement.

The [complete development surface grammar](../language/surface-grammar.md) extends syntax through
Q25i's separate entry point; the pure entry below remains the migration baseline.
The selected [familiar authoring migration](../language/surface-grammar.md#familiar-authoring-migration)
is Q25z's bounded grammar/consumer increment. Public syntax entries share an
internal token-only generic-call probe over the same authored generic productions,
with parse-local aggregate work bounds. The parser accepts canonical generic
calls, mathematical bodies, expression arms, typed pure locals and collection-loop
modes; semantic consumers retain their own supported subsets and acceptance.
Native local diagnostics do not replace hosted parser/kernel qualification.

## Bounded increment

[Q25g](../../PLAN.md#q-assessment-actions) commissions syntax-only Menhir parsing
of the [prototype grammar](pure-prototype.md#source-fragment), consuming the whole
file before separate resolution, typing, elaboration and Gallina emission.
Duplicate declarations and `true + 1` parse without a name/type verdict. Unsupported
extension keywords, invalid UTF-8, incomplete input and exhaustion give located refusals.

The authored OCaml grammar and AST types own syntax; actions construct located
syntax only. Nodes carry half-open original-source byte spans. Diagnostics use
one-based lines/columns, treating CRLF and bare CR as line endings. Keep decimal
spellings, including leading zeros, as strings without machine-integer bounds.
Comments may be UTF-8; identifiers are ASCII. Provenance hashes unnormalized bytes.

Use Menhir 20260209's code backend and the [Sail snapshot's](../../tools/opam/sail.lock)
exact generator/OCaml compiler; refuse version mismatches. Native-lane build receipts
bind authored-input digests, tool identities, arguments and generated-file digests.
Fresh generations must be byte-identical. Track no generated parser/upstream runtime
source and link no Menhir runtime. Before incorporation, read the release's licence
and record output terms in [THIRD-PARTY.md](../../THIRD-PARTY.md).

Input is bounded by the prototype's source-byte and literal-digit limits. The
native driver also bounds delimiter nesting and raw syntax-tree depth at 256 before exposing
an AST, and reports stack exhaustion as a limit refusal. Raw syntax counts groups
and file/function/block/return wrappers; the separate AST consumer retains the
prototype's expression and block/binding limits of 64. Independent migration
fixtures cover their individual boundaries and combined paths. The command wrapper
bounds process duration and reads source files with a bounded read. Refused input
publishes no AST. Success emits deterministic JSON containing the complete located
syntax tree and the exact source digest. A successful build alone is no parser
qualification verdict.

## Acceptance and commands

`python tools/run.py vela-parser build` generates and compiles the parser in the
native guest lane. `vela-parser parse SOURCE` emits its JSON syntax tree.
`vela-parser qualify` builds it and runs independent expected-tree fixtures,
whole-file positive/refusal cases, source spans, LF/CRLF/bare-CR positions,
UTF-8 comments and invalid encoding, decimal spelling, precedence and
associativity, incomplete editor input, excessive nesting and oversized input.
Fixtures must show that name and type errors parse as syntax. Qualification also
compares two fresh generations and records the inputs and available verdicts.
Focused local builds and helper tests may guide implementation; hosted execution
supplies acceptance. Guest CI runs qualification in its model lane using its
already installed Sail snapshot. Complete the
[local validation handoff](../../AGENTS.md#tool-execution-and-validation), then
record the settled revision and recommended Host/Guest CI checks. The user owns
hosted execution; its pending parser verdict remains pending.

An independent reviewer compares grammar with the prototype contract and selects
expected trees independently of actions. Retain the Python prototype/tests. Q25g
qualifies executable development syntax only; checked parsing, lexer correctness,
source correspondence and the full frontend need separate evidence.

## Generated syntax campaigns

[Q25y](../../PLAN.md#q-assessment-actions) qualifies reuse of the
[Menhir manual's](https://gallium.inria.fr/~fpottier/menhir/manual.html) seeded
sentence generation and interpreter/CST inspection after the exact locked Q25g
qualification. The [first-release delivery order](../../PLAN.md#vela-first-release-delivery)
retains Q25w's concrete foundation priority. This campaign changes neither the
existing code backend/runtime closure nor Q25h's checked-parsing prerequisites.

Freeze the pure entry point, grammar/tool digests, deterministic seed set,
independent expected cases and numeric time, output, token and memory budgets
before implementation. `--random-seed`, `--random-sentence-length` and
`--random-sentence` generate terminal names; the length argument is a goal, not a
hard output bound. Enforce the declared bounds independently, and qualify a
small token-payload renderer before sending generated source through the actual
lexer and parser. Record terminal input, rendered source and selected entry so
a failure replays without random generation. No second grammar is introduced.

Interpreter acceptance and `--interpret-show-cst` can expose automaton and
production-action disagreements, but share the grammar's possible mistakes.
Retain independently selected expected ASTs, source spans and refusal cases.
Generate bounded whitespace, comment, newline and token-payload variants;
compare the expected syntax and exact-source binding while preserving resource
refusals. A deliberately wrong action or span must be detected by an independent
expected observation, not merely by comparing two grammar-derived trees.

Keep `--list-errors` and `.messages` exploration a separately priced follow-up
after an actual diagnostic-maintenance need. The manual warns that enumeration
can consume gigabytes; do not place it unbounded on every parser build. Retain
complete enumeration separately from selected replay cases, and use Menhir's
update/comparison facilities to detect stale state/message coverage. Truncation
or timeout establishes no completeness. Review diagnostic meaning independently
after grammar changes. This reading selects no runtime error-message API, table
backend or Menhir runtime dependency; such changes need their own qualification.

Freeze a named syntax interaction the existing hand-authored corpus does not
systematically vary, and the expected maintenance benefit, before implementation.
Retain a campaign only when it exercises that interaction reproducibly and
reduces explicit case construction or failure reduction under the same controls.
Acceptance preserves syntax/migration fixtures and deterministic regeneration,
demonstrates bounded replay and an independent seeded-defect kill, and records
the exact generator, grammar and rendered-input identities. Stop a campaign
whose bound or renderer cannot be qualified; generation alone supplies no result
about source meaning. Host helper checks and native Guest CI qualification
retain their existing owners and pending status. The
[generated-test boundary](tooling-protocols.md#generated-development-tests)
keeps these development results separate from proof and product acceptance.

[`python tools/run.py vela-parser syntax-campaigns`](../../tools/toolchain/syntax_campaigns.py)
implements this qualification over the `file` entry of
[`parser.mly`](../../tools/toolchain/parser/parser.mly)
(`c249a367a6c7cadae2caf42d613afccb54173270ed453d97593c301c561373d2`) using the
locked `verifiedos-sail-0.20.3-ocaml-5.4.1` toolchain (`menhir, version 20260209`,
binary SHA-256 `290c659064d26cb1c51b743ec6a414ed4269e7f686821637656d526333c6c7a2`;
`ocamlc 5.4.1`, binary SHA-256
`454b023dfdebe17bd760300da10dd5b97833a11597cc5f2287444d0ed428a9fc`). It freezes
the `multi-declaration-precedence-trailing-comma-and-trivia-boundaries`
interaction across deterministic seeds `20261108..20261171` (`64` sentences,
`goal_length = 36`, `max_sentence_tokens = 512`, `max_rendered_source_bytes = 65536`,
`max_interpreter_output_bytes = 4194304`, `max_campaign_seconds = 60`,
`max_memory_bytes = 536870912`). Before invoking the parser,
[`qualify_renderer`](../../tools/toolchain/syntax_campaigns.py) qualifies all `37`
pure terminals across `canonical`
(`2cd098a78292d4714a11705ce547b266d5c9774b700121ce432d09113693237e`),
`utf8_comments_crlf`
(`08dbc326b3ff684f1c2e979221498db6e80a2dac6599e9b9d4d7a0f0e2ff8587`) and
`bare_cr_separators`
(`a66574b5431441dcc59ea87f609c2487b616d88122e28eb3768c49aa90fb3174`), plus six
negative controls (`empty-sentence`, `missing-eof`, `premature-eof`,
`surface-only-terminal`, `unknown-terminal`, `exceeds-token-budget`). Batch
`menhir --interpret --interpret-show-cst` accepts all `64` generated sentences
and rejects `3` malformed negative controls; across all `192` rendered
trivia/payload checks, [`IndependentPureAstOracle`](../../tools/toolchain/syntax_campaigns.py)
independently matches `63` accepted native ASTs and `1` automaton-accepted /
semantic-action-refused bare-typed local sentence (seed `20261116`, where the
`value_type name EQUAL expression SEMICOLON` production accepts in the LR(1)
automaton and raises a located `syntax` refusal at `line 3, column 1`). Seeded
fault evaluation records `stillborn-mutant` as `stillborn`, kills all three
semantic-action and byte-span faults that `--interpret` alone accepts
(`right-associative-subtraction-or-division-action`: `35 -> 16` tokens;
`trailing-comma-span-or-arity-corruption`: `34 -> 15` tokens; held-out
`expression-body-excludes-arrow-or-semicolon-span`: `29 -> 14` tokens), and
verifies deterministic JSON replay in
[`test_vela_syntax_campaigns.py`](../../tools/tests/test_vela_syntax_campaigns.py)
without random generation, a second grammar or a `menhirLib` runtime dependency.

## Promotion and retirement

[Q25h](../../PLAN.md#q-assessment-actions) owns promotion and Python parser
retirement. It must qualify the exact generator and Rocq support-library closure
with the locked prover, preserving version checks, and name the checked parser
correctness/completeness theorems and their exact assumptions. A conflict-free
grammar and checked completeness evidence are required for that claim; source
spans, diagnostics and lexing need their own evidence. Any backend grammar view
must be generated from one owner and checked for drift.

Prefer released Rocq adaptations; otherwise qualify a reviewed upstream revision
or maintained fork with licence reading, reproducible pin and bounded semantic
comparison. Contribute qualified fixes upstream. Preserve meaningful release/version
checks; disabling them qualifies no pair. The [compatibility record](https://github.com/symbiogenesis/VerifiedOS/blob/main/tools/opam/certirocq-compatibility.md#native-trial-verdict)
identifies proof-command relocation and the remaining version issue.

Before switching the prototype, provide a supported build/runtime route on
Windows and Ubuntu; route the generated AST through separate resolution, typing
and emission; pass all existing independent translation, refusal, resource-limit
and atomic-publication fixtures; and add independently expected AST fixtures and
held-out source edits. Compare accepted translations and diagnostic categories,
disposition every difference, and exercise malformed input without output or
unbounded failure. Once these predicates pass, remove Python lexing/parsing and
its fallback, retaining Python orchestration only where useful. The full-language
frontend remains subject to [Q25d's interpretation and admission prerequisites](../extensions/full-language-review.md#r-05-009-r-05-020-and-what-holds-the-frontend-rows).

### Executable migration preparation

The Rocq-extracted `vela-checked-parser` and the code-backend development parser
(`vela-parser`) both emit located JSON syntax envelopes consumed by the same strict
generated-AST decoder and separate resolution, typing and Gallina emission pipeline.
The generated-tree decoder checks the complete schema, exact source digest, spans
and token spellings, child containment and resource budgets before elaboration. The
legacy handwritten Python recursive-descent `_Parser` has been retired from
[`tools/toolchain/__init__.py`](../../tools/toolchain/__init__.py), and
`vela.parse_module` routes all pure Vela parsing (`translate`, `evaluate`,
`inspect_source`, `format_source`, `lint_source`) through
[`parser_checked.parse_checked`](../../tools/toolchain/parser_checked.py) without a
Python lexer or parser fallback.

`python tools/run.py vela-parser migration` builds and qualifies the syntax parser,
then compares the active `vela.translate` route (`vela-checked-parser`) and the
development `vela-parser` route (`vela.translate_ast`) on independently categorized
fixtures, source edits, semantic diagnostic locations and resource boundaries.
Accepted module identities and complete emitted bytes must agree. Every difference
is retained in `migration.json` and produces a nonzero verdict; changed consumer,
source, toolchain or generated-parser bytes invalidate the report. Guest CI's model
lane runs this comparison and retains its verdict separately from syntax
qualification.

Whole-file syntax precedes semantics: a multiply-invalid file may report a later
syntax error before an earlier name/type error. Independent single-fault semantic
fixtures retain their categories and locations.

### Rocq support prerequisite

[`python tools/run.py vela-parser support`](../../tools/toolchain/parser_checked.py)
authenticates the Menhir 20260209 release archive
(`69f0414b047d1d5b3507eb8277cd328a60d430bdff51de912b47adb2c25de4f3`), builds its
Rocq support library in `verifiedos-rocq-9.3.0-ocaml-5.4.1`, generates the concrete
pure grammar from [`parser.mly`](../../tools/toolchain/parser/parser.mly) with
`menhir 20260209 --coq --strict` in `verifiedos-sail-0.20.3-ocaml-5.4.1`, proves its
concrete parser theorems, runs the recursive kernel checker across all 14 modules,
extracts and compiles `vela-checked-parser`, installs the verified runtime build, and
verifies runtime correspondence. An optional `--archive FILE` uses the same
authenticated bytes without downloading them.

Two bounded source adaptations are guarded by exact SHA-256 digests:

1. `Interpreter.v` (`4891ad9d65843fefa4d9d424e0d065e241760f705464efc233796d445b16294f`
   to `69cfbdd086858ef37fa50eed10866379a51bd858113a9716331d88f9e46e7fde`) relocates the
   three late `Proof` commands (`pop`, `reduce_step`, `parse`) identified in the
   [same-prover compatibility record](https://github.com/symbiogenesis/VerifiedOS/blob/main/tools/opam/certirocq-compatibility.md#native-trial-verdict),
   compared against the diagnostic reference twin
   (`04aa7bda193a67219fea99ee6f1b86eb7db3da735b04e32f662ac1e5c041b02c`).
2. `Validator_complete.v` (`c7e1f4f25be2a4371d06dd1d01ea2adb21d889c1c18739ebf74afca8408b4f64`
   to `1a284ece0e5b547e2b816c0f7623ee1ee628d30385f5d3dde4dd1a180589cb66`) keeps the
   `IsItemsMap im` parameter abstract across `StateProdPosMap.fold_1` in the opaque
   `is_validator_forall_items` proof (`intros Him ... rewrite -Him in Hlookahead`) so
   `rocqchk` does not unroll `List.fold_left` over the concrete 665-entry `items_map ()`
   AVL tree when checking functor instantiations.

Both trees' frozen public types, universes, executable bodies and assumptions match
byte-for-byte (`17c1e9beb756127c9079803fc99e6273c0515188ab8c4d42d36bc3ffafb85ae9`). No
source is installed into either switch. The release's `Version.v`
(`3746feeefa899fe0d43e4db0ec53f2d7ddd72076d9fab29cdcc9ecb0250072e6`) stays
byte-identical, and positive and negative guard clients test `require_20260209`.

[`_pure_grammar_view`](../../tools/toolchain/parser_checked.py) extracts and checks
all `37` pure terminals and `29` reachable pure productions from the single owner
[`parser.mly`](../../tools/toolchain/parser/parser.mly)
(`c249a367a6c7cadae2caf42d613afccb54173270ed453d97593c301c561373d2`), expanding the
single `%inline ioption(CONST)` modifier in `pure_declaration` into its two explicit
branches to emit `VelaPureGrammar.mly`
(`71325e79c1c655d83210bf5c1589373ef827841b6f668f9b73cafea085004aca`). Two fresh runs
of `menhir --coq --strict` produce byte-identical `VelaPureGrammar.v`
(`27a38fdde4322a39e056ba89a1b0d0b2470338e55d91c37c4b584e27753ed1e9`) preserving
`MenhirLib.Version.require_20260209`. Over `VelaPureAst.v`
(`84185bbcefd234f97361476d1b491437ae8a7d252dde981574ed5e019dbb8a67`) and
`VelaPureGrammar.v`, `VelaPureProofs.v`
(`f6dbcd0a4aa8f0de1d940e2d96412a261a764ebe9f55c5c27752659c72a06e9c`) proves nine
concrete theorems (`vela_file_safe`, `vela_file_complete_validator`,
`vela_file_correct`, `vela_file_complete`, `vela_file_unambiguity`,
`vela_file_positive_precedence`, `vela_file_bare_local_refused`,
`vela_file_empty_module_rejected`, and `vela_file_zero_fuel_timeout`), each verified
as `Closed under the global context` (`0` axioms, reading SHA-256
`308b14375eb599e10c9320eefc5e0fef85a89b5ebeee30d98ec395be842e7d86`) and checked by
recursive `rocqchk` across all 14 `MenhirLib.*` modules.

`VelaPureExtraction.v`
(`55036ec0e9a8713d1d8878808e3320a243615fbc787d289a32775392fe2b1987` / deterministic
`vela_checked_parser.ml`
`0cb4541b65af4a606b075bd6dee0450929ea887ae3d60a3b2a9251a56b0050bd` and
`vela_checked_parser.mli`
`fe89d4abf4193f1b54e428e95b9be8d6d2f671521b7bb851de67bf5aa2af610b`) extracts
`VelaPureGrammar.file` to OCaml and links it with `ast.ml`, `lexer.mll`, a token-only
`parser.ml` stub (linking zero code-backend Menhir tables) and `checked_main.ml` into
`vela-checked-parser`
(`2bf312bd2e1e38f62878c8cb4f2fdbc8d8288dbab5488a7a127393ae7a735529`).
[`ensure_checked_build`](../../tools/toolchain/parser_checked.py) maintains the
receipt-verified runtime binary at `/root/build/vela-parser-checked-runtime/vela-checked-parser`
and [`parse_checked`](../../tools/toolchain/parser_checked.py) drives its `--batch`
framed protocol on both Ubuntu (`linux`) and Windows (`win32` via `wsl.exe`). The
extracted executable passes all `70` pure qualification fixtures, matches `vela-parser`
byte-for-byte on [`examples/pure.vela`](../../examples/pure.vela),
[`examples/constants.vela`](../../examples/constants.vela) and
[`examples/expressions.vela`](../../examples/expressions.vela), and agrees on all `173`
migration fixtures (`0` differences), retiring the Python `_Parser`
(`"python_retired": true`, `"host_routes": ["linux", "win32"]`, `"deferred": []`).
User-managed Host CI and Guest CI verdicts remain separate from local qualification.
