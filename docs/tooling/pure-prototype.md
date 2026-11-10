# Pure Vela translation prototype

Start with the [primary Vela design and examples](../assurance/verification-strategy.md).
This document specifies the implemented pure fragment and its development commands.
The opt-in [mathematical elaborator](elaboration-prototype.md) adds generics,
dependent types, higher-order inference and explicit proof terms through the
existing native surface parser. The pure command below retains its narrow scope.

## Commission and interpretation

[Q25e/Q25f](../../PLAN.md#q-assessment-actions) commission a bounded host tool
translating explicitly typed pure functions to Gallina. Accepted expressions mean
their generated CIC terms, with no independent evaluator, reduction relation or
semantic anchor. `Nat` and `bool` denote mathematical naturals and booleans, not
machine words, layouts or CHERI permissions.

The [narrower-fixture rule](../language/core-design.md#decision-and-reopening-evidence) keeps
this separate from the returned-loan trial and [held full-frontend rows](../extensions/full-language-review.md#r-05-009-r-05-020-and-what-holds-the-frontend-rows).
The full calculus retains its interpretation/register duties. Untrusted Python
parsing/checking supplies no kernel acceptance, checked source correspondence,
`SourcePackage`, metatheory, compiler qualification or binary admission.

## Development parser goal

The [Menhir development route](../assurance/verification-strategy.md#development-parser-and-grammar)
produces located syntax before separate checking/elaboration. Both the Rocq-extracted
`vela-checked-parser` and the code-backend `vela-parser` feed the strict generated-AST
decoder and shared resolution, typing and emission pipeline under the
[plan's qualification](../../PLAN.md#vela-whole-system-authoring-proposal)
and [parser/migration contract](parser.md).

`python tools/run.py vela-parser parse SOURCE` exercises generated syntax;
`vela-parser qualify` checks independent AST fixtures/regeneration;
`vela-parser migration` compares source edits and independently expected
acceptance/refusal categories, retaining all differences; and `vela-parser support`
qualifies the Rocq-extracted `vela-checked-parser`. Ordinary `vela` commands parse
pure source through `vela-checked-parser` (`vela.parse_module`) on both Ubuntu and
Windows (`wsl.exe`), with the legacy handwritten Python `_Parser` retired (`Q25h`).
Retain current examples/refusals as migration fixtures.

## Source fragment

This subset follows the [proposed surface](../assurance/verification-strategy.md#an-ideal-surface):
return types precede operation names, parameter types precede bindings, immutable
locals use `let` with an optional type, required-static values use typed `const`, and exits use `return`
or an expression body. Contracts, grades,
effects, loans and machine representations are unsupported and diagnosed,
never ignored.

The prototype accepts UTF-8 source with ASCII identifiers and `//` line comments.
Identifiers match `[A-Za-z_][A-Za-z0-9_]*`, excluding grammar and reserved extension
keywords; the latter produce unsupported-feature diagnostics. Decimal
literals match `[0-9](?:_?[0-9])*`; underscores separate digits, while leading
zeros are permitted. Separators and leading zeros normalize on emission; their
authored spelling and source locations remain intact in syntax. The
[separator contract](authoring-tools.md#numeric-separators) owns the digit bounds
and wider surface's hexadecimal, binary and representation-suffix rules.
Every file contains one named module and at least one function or constant.
Declarations are resolved in source order. Every parameter and return type is
explicit. A function can call only earlier functions; recursion and forward calls
are refused. Local bindings are immutable.

```text
module Example;
public const Nat Twice(Nat x) => x + x;
public const Nat Limit = Twice(x: 8);
public Nat Scale(const Nat factor, Nat value) {
  const Nat multiplier = Twice(factor);
  return multiplier * value;
}
public Nat Runtime(Nat value) => Scale(factor: Limit, value: value);
public Nat Select(bool flag, Nat x) {
  const Nat fallback = Twice(x: 0);
  let result = Twice(x: x);
  if (flag) { return result; } else { return fallback; }
}
```

The accepted grammar is:

```text
file      := 'module' name ';' declaration+
declaration:= function | 'public' constant
function  := 'public' 'const'? type name '(' parameters? ')' body
body      := block | '=>' expression ';'
parameters:= parameter (',' parameter)* ','?
parameter := 'const'? type name
type      := 'Nat' | 'bool'
block     := '{' binding* exit '}'
binding   := 'let' type? name '=' expression ';' | constant
constant  := 'const' type name '=' expression ';'
exit      := 'return' expression ';'
           | 'if' '(' expression ')' block 'else' block
expression:= disjunction
disjunction:= conjunction ('||' conjunction)*
conjunction:= comparison ('&&' comparison)*
comparison:= sum (('==' | '!=' | '<' | '<=' | '>' | '>=') sum)?
sum       := product (('+' | '-') product)*
product   := unary (('*' | '/' | '%') unary)*
unary     := '!' unary | atom
atom      := decimal | 'true' | 'false' | name
           | name '(' arguments? ')' | '(' expression ')'
arguments := argument (',' argument)* ','?
argument  := (name ':')? expression
```

Arithmetic and ordering take naturals; equality and inequality take two operands
of the same type. Negation, conjunction and disjunction take booleans.
A condition is Boolean and every reachable branch returns the declared
function result type. An expression body checks exactly like a single return;
its expression is evaluated once. Optional trailing commas apply to nonempty
parameter and argument lists, never to grouping. Statements after a terminal
return or conditional are refused, and a block without a terminal result is a syntax error. Calls have the
declared arity and argument types. A positional prefix may be followed by a
labeled suffix; each label must name the next declared parameter. Reordered,
duplicate or unknown labels, omitted arguments and positional arguments after a
label are refused. Labels preserve once-only left-to-right evaluation and do
not change the emitted application. Local annotations must match the initializer's
`Nat` or `bool` type exactly; unannotated locals infer it. Bare `type name = expression;`
locals are refused as syntax, directing authors to explicit `let`.
Duplicate functions, parameters, local bindings in an active
scope (including active parameters) and unbound values are errors. Function and
value namespaces are separate. Equality returns `bool`. Natural arithmetic,
equality and comparison map to `Corelib.Init.Nat.add`, `.sub`, `.mul`, `.div`, `.modulo`, `.eqb`,
`.ltb` and `.leb`.
Boolean equality maps to pure nested conditionals returning the Boolean
constructors. Types and constructors come from `Corelib.Init.Datatypes`.
Constants follow the [required-static contract](../language/surface-grammar.md#required-static-constants):
their typed initializers evaluate from earlier constants and pure calls with
static arguments, under finite work and numeric bounds. The supported constant
types are `Nat` and `bool`. Unmarked runtime parameters and
ordinary outer locals are refused before evaluation, including ignored or dead
dependencies. Constants denote evaluated values and cannot be reassigned or
called. Compiler-recorded constant symbols support the existing editor services.
An ordinary local inside a pure function evaluated with static arguments belongs
to that evaluation; it is not an outer runtime dependency. Constants with machine
types such as `usize` require the wider selected-target interpretation and are
outside this pure prototype.

The function modifier records constant-evaluation support without restricting
runtime calls. A static parameter is checked symbolically in its definition and
requires a static argument at every call. Instantiation substitutes that argument
and computes the required local constants, leaving ordinary data arguments in
their original order. Forwarding a static parameter preserves its availability;
neither a ghost binder nor a runtime local acquires that availability implicitly.
Logical template definitions may retain symbolic static expressions; this host
prototype establishes no target erasure or source-correspondence theorem.

Every user name is mapped to a generated identifier so Gallina keywords and
library names cannot capture source references. There is no raw Gallina escape.

Whole-source size, block/binding nesting, expression nesting and decimal-literal length have explicit
implementation limits, reported as limit diagnostics rather than acceptance.
These are host parser limits, not target resource bounds or integer widths.

## Extended pure expressions

Q25ac in [the plan](../../PLAN.md#q-assessment-actions) commissions an
expression increment over the source fragment above. Both the checked pure route
and the development pure entry accept `!`, `&&`, `||`, `!=`, `<`, `>`, `>=` and binary
`-`, using the existing wider surface's spellings and precedence. From weakest
to strongest, precedence is `||`, `&&`, a single comparison (`==`, `!=`, `<`,
`<=`, `>`, `>=`), left-associative `+`/`-`, left-associative `*`, prefix `!`,
then atoms/calls/grouping. Comparisons do not chain; parentheses are required.
Repeated negation is permitted within the existing expression bounds. Unary
minus and machine integer types remain outside this increment. Division and
remainder have their own increment below.

`!`, `&&` and `||` require Boolean operands. Equality and inequality require
two operands of the same supported type; ordering and subtraction require
naturals. Subtraction saturates at zero: `2 - 5` is `0`. Emission uses existing
`Corelib.Init.Nat.sub`, `.ltb` and `.leb`, Boolean equality's once-only bindings,
and Boolean conditionals for negation and short-circuit logic. Reversed ordering
must preserve left-to-right once-only operand evaluation through fresh bindings.
All generated binders remain disjoint from mapped source names.

Both logical operands undergo name/type and required-static dependency checks,
including dead operands. Evaluation and emitted conditionals evaluate the left
operand once and evaluate the right only when needed. Thus
`false && (huge * huge == 0)` can avoid a static arithmetic limit, while
`false && runtimeFlag` still cannot initialize a required-static constant.
Existing work, depth, output and numeric budgets apply; no new evaluator or
browser-side interpretation is introduced.

Acceptance requires independently expected terms and values for every operator,
mixed precedence/associativity, nested negation, Nat underflow, both equality
types, named calls, static parameters and short-circuit limit behavior. Semantic
negative neighbors must reach the intended type/name/static-dependency refusal;
malformed/chained operators, unary minus and excessive depth remain refused.
Native AST controls cover exact operator/operand spans, trivia, Unicode and
newlines, and reject omitted, substituted or extra source tokens. Retain existing
translations and migration controls. Formatting must preserve token/comment
order and reparsed meaning, be idempotent and space prefix negation correctly;
compiler facts and existing LSP operations must remain usable.

The [playground](playground.md#extended-expression-examples) exposes examples and
console suggestions through the same compiler and bounded worker. Focused real
HTTP/worker controls cover new values, Gallina and semantic refusals. Exercise
browser editing, formatting, compilation and console evaluation when browser
infrastructure is available; record its absence explicitly otherwise. Run focused
host tests and the [local validation handoff](../../AGENTS.md#tool-execution-and-validation),
then record the local revision and recommended hosted checks. The user owns Host CI
and Guest CI, including native generation and kernel replay; no pending verdict
counts as qualification or production acceptance.

Hosted `vela-parser elaborate-qualify` includes native pure parsing and the
shared pure translator, alongside the mathematical consumer. Independently
expected equalities check emitted runtime functions and evaluated constants;
the kernel and assumption audit cover both the generated library and these
observations. A syntax refusal cannot satisfy a semantic negative fixture.

## Natural division and remainder

Q25ad in [the plan](../../PLAN.md#q-assessment-actions) adds binary `/` and
`%` to both pure syntax routes, using the existing wider surface spellings.
They require two `Nat` operands and return `Nat`, with the same precedence as
`*`; all three associate left to right. Thus `20 / 3 * 2` is `12`,
`20 % 6 * 2` is `4`, and `20 / (3 * 2)` is `3`.

These operations denote `Corelib.Init.Nat.div` and `.modulo`. For a positive
divisor, division is the natural quotient and remainder is the nonnegative
remainder. The operations are total: `n / 0` is `0`, and `n % 0` is `n`.
The static evaluator must match these terms, including zero divisors, without
Python division exceptions. Both operands remain checked; the static evaluator
evaluates them once in source order, including when the divisor is zero.
Existing static work, depth, numeric and emission bounds apply. There is no represented integer,
target divide instruction, timing claim or new proof-admission route.
This reuses the mathematical elaborator's existing total `Nat` interpretation.
Represented first-release arithmetic retains the nonzero-divisor and
representability obligations in [primitive semantics](../language/first-release.md#primitive-semantics);
these demonstration terms do not discharge those obligations.

Acceptance requires independent values and exact emitted terms for both
operators, zero and unit divisors, smaller/equal/larger operands, mixed
precedence and grouping, named calls, constants and static parameters. Invalid
Boolean/mixed operands must reach type refusals; missing operands, repeated
operators, `/=` and `%=` remain refused. Native AST controls must preserve
operator/operand spans and reject omitted, substituted or additional source
tokens, including comments, Unicode and CRLF boundaries. Retain existing
arithmetic, short-circuit and resource-limit controls. Zero results must not
hide non-static dependencies or avoid evaluating an expensive operand.

Formatting must preserve tokens, comments and interpretation and be idempotent;
LSP diagnostics, hover, formatting and semantic tokens must retain their
existing source identities. Add independently expected runtime and constant
observations to hosted native pure kernel replay and retain migration controls.
The [playground examples](playground.md#division-and-remainder-examples) must use
the shared compiler and isolated worker for compilation and evaluation.
Exercise Monaco and plain-text editing, formatting, evaluation, type refusals
and recovery with available browser infrastructure, or record its absence.
Run focused host tests and the [local validation handoff](../../AGENTS.md#tool-execution-and-validation),
then record the settled revision and recommended hosted checks.
Native regeneration and kernel replay require user-managed hosted evidence;
pending verdicts do not close qualification.

## Command and publication

`python tools/run.py vela check SOURCE` parses and checks the complete file,
preserves the exact source bytes and runs advisory lints before reporting
its prototype status. The [authoring-tools contract](authoring-tools.md) owns the
StyleCop-inspired style, documentation, lint policy and publication checks.
`vela fmt SOURCE` applies formatting explicitly; `vela fmt SOURCE --check` and
`vela lint SOURCE` leave source unchanged. Normal compiler commands accept
`--format check` for read-only style enforcement, `--format off` to state the
source-preserving default, or `--format write` to opt into canonical formatting.
`--no-lint` disables optional lints; repeatable `--allow ID` and
`--deny ID` control individual findings without disabling language checks.
`VELA104` and `vela lint --preview-bindings` are permanently retired (`Q25ah`)
now that local declarations require an explicit `let` or `var` keyword; the
library `preview_bindings` helper retains its [source-bound migration contract](authoring-tools.md#lint-policy)
for legacy inputs without exposing a CLI flag or reusing the rule ID.

`python tools/run.py vela emit SOURCE` uses the same default authoring passes and
writes Gallina to standard output; `--output FILE` publishes it through the shared
atomic writer only after complete validation. Reject overwriting the input,
including aliases. Do not create missing output parent directories implicitly.
Explicit source rewriting requires an unchanged regular file and a completely
checked formatted candidate; library and language-server calls never rewrite.
Diagnostics identify the file, line and column, distinguishing syntax, name,
type, unsupported-feature, encoding, limit and I/O failures. Rejected source
produces no generated output. Atomic file publication preserves existing output
after a failed write; standard output cannot roll back bytes already consumed.

Deterministic output uses fully qualified CIC operations and SHA-256 provenance
for the exact authored bytes, or post-format bytes after an explicit formatting write,
without a correspondence theorem. Emit definitions only:
no axioms, admissions, proof scripts or machine-code escape.

## Acceptance

Land this contract and its priced checklist cells before implementation. A separate
reviewer reads the scope and independently authored expected translations.
Focused behavioral tests must cover the example, precedence, lexical scope,
both types and each operation, plus deterministic output, source binding and
name hygiene. Well-formed negative neighbors must fail on return type, condition,
branch, call, duplicate-name or resolution premises. Trailing input, unsupported
constructs, malformed/invalid UTF-8, excessive nesting and oversized literals
must produce bounded diagnostics. Surface-conformance cases use the same declaration,
parameter, return and control-flow spellings as the design dossier. Cover expression
bodies and equivalent return blocks, trailing commas and malformed adjacent forms
through both syntax routes, with unchanged terms apart from exact source provenance.
Reject `fn`, colon-typed parameter, arrow-return and undelimited expression
body forms, along with missing returns and unreachable trailing statements. CLI tests must establish successful publication
and preservation of existing output on rejection, input aliases and write errors.

Complete the [local validation handoff](../../AGENTS.md#tool-execution-and-validation)
and record the settled revision and recommended Host/Guest CI checks. The user
owns hosted execution; missing verdicts remain pending.
The translation tests do not establish that a kernel has accepted emitted terms;
a generated-term kernel replay is a separately identified follow-up unless hosted
evidence explicitly supplies it. Production language and whole-system migration
retain the [unified-source acceptance contract](../extensions/unified-source-contract.md).

## Try the prototype

From the repository root on Windows (use `python3` on Linux):

```console
python tools/run.py vela check examples/pure.vela
python tools/run.py vela emit examples/pure.vela --output out/Pure.v
```

Create the output directory first, or omit `--output` to print definitions.
The [example](../../examples/pure.vela) defines a cube and Boolean
selection: intended `Choose(true, 1)` is true, `Choose(true, 2)` false. Output is
module `Vela_Oracle` with `f_Cube`/`f_Choose`. The
[expression example](../../examples/expressions.vela) adds Boolean
logic, comparisons and saturating natural subtraction. The playground console
evaluates closed expressions through the bounded static evaluator; kernel
acceptance requires the separate replay.

## Bounded compiler traces

The pure development compiler supplies a scoped increment of
[Q25cp](../../PLAN.md#q25cp) under the
[performance trace contract](tooling-protocols.md#compiler-decisions-and-performance-traces).
Create the destination directory, then run:

```console
python tools/run.py vela trace examples/pure.vela --output out/pure-trace.json
python tools/run.py vela trace-validate out/pure-trace.json --source examples/pure.vela
python tools/run.py vela trace-benchmark examples/pure.vela --output out/pure-trace-comparison.json
python tools/run.py vela trace-benchmark-validate out/pure-trace-comparison.json --source examples/pure.vela
python tools/run.py vela trace-qualify-viewer --trace-processor /path/to/trace_processor_shell --output out/trace-viewer.json
```

The read-only trace command records `compile`, nested `parse` and
`elaborate-and-emit` phases from the existing pure producer. Resolution and Gallina
emission share one elaborator and remain one measured phase. The synchronous host
worker includes time waiting for the checked parser process; it does not report
that process's internal phases. Source and Gallina byte counters use Chrome
Trace Event `C` records, and completed phases use `X` records with recording-relative
integer microseconds derived from `perf_counter_ns`. The fixed worker identities
are `pid: 1`, `tid: 1`; they describe this recording, not operating-system IDs.
[Perfetto documents these event formats](https://perfetto.dev/docs/getting-started/other-formats)
as an input to its viewer. The optional qualification command checks a pinned
independent importer as described below.

The `vela` schema-1 manifest binds events and completeness metadata, exact source
bytes, local Python/compiler/parser input files and Python/platform versions.
The producer identity also binds the Python and opam lock owners, the command
bootstrap, host Python executable bytes and the checked parser executable bytes
validated against its build receipt. On Windows it observes the selected WSL
parser and guest Python executable in the same checkout. Identity observation
lies outside the measured intervals; unavailable or changed executables refuse.
These hashes detect changed data; they authenticate no producer and carry no
complete installed-library/operating-system closure, theorem or artifact-admission verdict. The validation
command refuses changed source or producer identities, malformed events, crossing
spans, invalid clocks, missing phases or counters, and incomplete recordings.
A successful complete recording measures a successful pure check only.

Recording retains at most 4,096 events; `--max-events` selects a smaller positive
limit. Phase names, counters, nesting and exported/decoded bytes have fixed bounds.
Dropped events, open spans, clock faults and refused or cancelled work prevent a
complete measurement claim. A refused source writes a diagnostic trace and returns
failure. Publication is atomic, refuses source aliases and rechecks source and
producer freshness; failed preparation preserves an existing output. Validation
also rechecks producer freshness after reading the recording. The manifest
reports measured recorder bookkeeping in nanoseconds, excluding identity hashing,
serialization and file publication. No hard elapsed-time overhead bound is claimed.

The comparative benchmark runs both plain and traced translation in alternating
pairs in the same host process, including checked-parser wait time. It defaults to
one warmup pair followed by seven measured pairs; `--warmups` accepts 0–5 and
`--samples` accepts 1–31. Every translation must emit the same module and Gallina,
and every traced run must pass complete-recording validation. Only translation
lies inside the measured intervals: recorder construction, trace export and
validation, identity hashing and report publication are excluded. Warmup intervals
are discarded, while compiler caches and operating-system scheduling remain part
of the observed conditions. The command bounds compilation count and report size;
it establishes no hard elapsed-time bound or stable overhead threshold.

The separate schema-1 comparison report retains each pair's execution order,
elapsed nanoseconds and traced bookkeeping, output identity, source and producer
bindings, and exact summaries. Totals, minima, maxima and medians summarize each
path; an even-sample median rounds down to whole nanoseconds. `elapsed_delta_ns`
is traced total minus plain total. `overhead_ppm` is that difference divided by
plain total in parts per million, rounded down; a zero plain total reports `null`.
Negative observations are retained without claiming that instrumentation improves
performance. Validation recomputes summaries and refuses stale identities,
changed samples, invalid durations, incorrect pair order and malformed reports.
Refused, cancelled or stale measurements preserve an existing report. A hash-bound
report detects changed data and supplies no authentication of the measurement or
its environment.

[Independent timeline fixtures](../../tools/tests/test_vela_compiler_trace.py)
recover expected order, durations, nesting and counters with a separate JSON reader
and exercise corruption, overflow, clock and refusal controls.
[Paired-measurement fixtures](../../tools/tests/test_vela_trace_benchmark.py) check
independently chosen timing totals, warmup exclusion, output equivalence, binding
and publication refusals.

`trace-qualify-viewer` accepts an already provisioned Perfetto `v58.2`
`trace_processor_shell`; it performs no downloads and changes no dependencies.
The selected executable must match one of the reviewed Windows AMD64, Linux
AMD64 or Linux ARM64 SHA-256 pins in the
[qualification harness](../../tools/toolchain/trace_viewer.py), then report
revision `add693d8b338ba9599dbcbc3e300b1ab8c000897`. The
[license and use record](../../THIRD-PARTY.md#independent-trace-importer) owns
provisioning links and terms. Other binaries refuse before execution.

The harness validates a deterministic Chrome trace and verifies seven negative
controls before handoff: stale source/producer, missing phases, crossing spans,
negative timestamps, dropped events and cancellation. Perfetto imports the valid
fixture and executes two fixed SQL queries. Independently chosen expected rows
require three spans with exact nanosecond timestamps/durations, parent/child
depth and worker identities, plus both byte counters. The report retains the
fixture, queries, imported CSV and parsed rows, version/diagnostic transcripts,
negative-control results, executable/revision and harness identities, and a
binding over the complete report. Each reader invocation has a 30-second timeout
and bounded accepted output. Hashes detect changes and authenticate no measurement.
Reader/harness changes withdraw qualification; atomic publication preserves
existing evidence after failures or cancellation and refuses output aliases.
[Reader qualification tests](../../tools/tests/test_vela_trace_viewer.py) cover
wrong independent observations, disabled negative checks, unknown binaries,
timeouts, output bounds, aliases and late identity changes.

This qualifies the selected Perfetto importer for the deterministic pure trace
profile. Browser UI rendering, wider phase/worker coverage, exact runtime closure
and workload-specific overhead qualification remain open under Q25cp. Compiler
timings supply no execution time, WCET or constant-time evidence for emitted programs.
