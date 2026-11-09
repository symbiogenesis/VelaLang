# Vela first supported release

This contract owns the first supported Vela software release's scope, primitive
semantics, module boundary and required library behavior. The
[primary design](../assurance/verification-strategy.md) supplies rationale and examples, and
the [language reference](reference.md) gives each construct's syntax, meaning,
example and implementation status;
[PLAN.md](../../PLAN.md#vela-first-release-delivery) owns commissioning,
budgets and delivery order. The [requirements register](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/requirements-register.md)
remains normative for VerifiedOS. These are design decisions and acceptance
predicates, not a claim that the current prototypes implement them.

## Release boundary

The first product is a synchronous, bounded systems-language subset connected to
one retained compiler route. It supports explicit machine representations,
records and finite tagged sums, generics, stable dependent lengths and states,
exhaustive matching, `Option`/`Result`, bounded loops, shared and exclusive loans,
ownership transfer, resource-aware exits, closed effects and checked contracts.
Its resource discipline has fixed unrestricted, affine, relevant-verdict and
linear-obligation cases. Their permissions and disposal rules come from the
actual resource interpretation; an erased token or numeric annotation supplies
no authority by itself. Public interfaces fix representations, required-static
inputs, effects and resource contracts; ordinary local inference hides routine
derivations without weakening them.

The release accepts three authoring costs for these guarantees. Ordinary `+`,
`-` and `*` carry the representability obligations of
[primitive semantics](#primitive-semantics): linear facts discharge
automatically, while nonlinear facts need explicit proof or a checked, wrapping
or saturating operation. Public `effects` lists are closed and propagate through
every caller, with no effect polymorphism. Receiver loans start before argument
evaluation, with no two-phase receiver borrows, and no loan is carried across
loop iterations. [Qualification](#qualification) measures each cost.

Specifications and proofs may use the admitted mathematical definitions and
libraries in the existing kernel. A mathematical definition's expressiveness
does not imply a runtime representation or admission to executable type
conversion. The [mathematical prototype](../tooling/elaboration-prototype.md) retains its
own supported subset; the [pure prototype](../tooling/pure-prototype.md) and
[surface parser](surface-grammar.md) retain theirs. Parsing a larger feature does
not make it part of this release.

The selected [familiar authoring surface](surface-grammar.md#familiar-authoring-migration)
uses explicit `let`/`var` local conventions, ordinary numeric aliases, concise
expression matches, one function-expression body marker and ordinary generic
calls. Q25z migrates syntax and existing consumers independently; represented
libraries and runtime qualification follow the first synchronous slice under
the [delivery order](../../PLAN.md#vela-first-release-delivery). Typed
immutable locals, canonical generic calls, expression arms and mathematical
bodies have development parser support; collection modes remain syntax-only.
Their adoption preserves this release's semantic scope and
does not become a prerequisite for its concrete foundation investigation or
first executable slice.

All language laws concern the elaborated image in an existing semantic anchor
under [the untrusted-elaboration boundary](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/spec.md#r-05-020a). Located source
syntax, binding and resource derivations are inputs to checked interpretation
and source correspondence, not an independently authoritative operational
semantics. The kernel must check the interpretation and requested laws for the
actual source closure. A well-typed generated term alone proves neither intended
source meaning nor concrete memory safety. Concrete CHERI laws, representation,
lowering, final bytes and applicable admission remain separate obligations.

The first end-to-end client uses caller-supplied storage and the
[synchronous core](core-design.md). Bounded pool allocation is a later library
increment within this software product, requiring its actual allocator, manifest,
exhaustion and reuse proofs; there is no implicit heap or boxing. The release
does not require arbitrary grade domains, runtime multi-shot or shallow handlers,
general reflection/generation, concurrent interior mutation, native self-hosting,
ISA replacement or hardware authorship. Async and one-shot control capture need
a separately accepted consumer and their own resource/lowering slice.

The [extension designs](../extensions/README.md), including the
[extended grade dossier](../extensions/graded-foundation.md),
[control dossier](../extensions/handlers-async.md), [mutation dossier](../extensions/interior-mutability.md),
[metaprogramming design](../extensions/metaprogramming.md) and
[whole-system contract](../extensions/unified-source-contract.md), retain their extension
obligations and define no part of this release. Selecting an extension requires a named client, a comparison with
the supported subset, a bounded implementation/qualification budget and a
decision predicate. Grading follows the [incremental selection protocol](../extensions/graded-foundation.md#extension-selection-and-qualification),
with type-use accounting and generated usability tools justified separately.
A proposal's syntax or a demonstration assembled to exercise
the proposal is insufficient evidence of product need. Its omission changes no
VerifiedOS guarantee or mandatory compiler obligation.

## Primitive semantics

Every operation below has the same meaning in constant evaluation and runtime
code and under every assurance preset. Runtime representations come from the
selected target, never the build host. The
[existing integer policy](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/spec.md#r-05-144) requires explicit conversions,
total ordinary arithmetic and named modular/saturating operations. The language
binds that policy as follows; the target bridge must prove the binding.

| Surface or operation | First-release meaning |
| --- | --- |
| `bool`, `Unit` | Exactly `false`/`true`, and the single unit value `()`. Integers have no truthiness conversion. |
| `u8`, `u16`, `u32`, `u64`; `i8`, `i16`, `i32`, `i64` | Unsigned values range from zero to `2^w - 1`; signed values range from `-2^(w-1)` to `2^(w-1) - 1`. Bitwise signed representation is two's complement. `byte` is an alias for `u8`. |
| Standard numeric aliases | The standard library module `Vela.Numerics` exports ordinary public aliases `int = i32`, `uint = u32`, `long = i64` and `ulong = u64`. Each denotes exactly its target type, including representation, arithmetic and proof obligations. Width-named spellings remain available. |
| `usize` | Unsigned index/count arithmetic at the target's declared XLEN width. This is not a capability's representation, permission to address all values of that width, or a pointer/integer conversion. Target specialization fixes the width and its representability obligations. |
| Mathematical `Nat` and integers | Specification/static values with their mathematical operations. Runtime use needs a selected finite representation and a proved range relation; there is no implicit arbitrary-precision runtime. |
| Integer literals | Decimal, binary and hexadecimal digits with the [separator rules](../tooling/authoring-tools.md#numeric-separators) denote exact mathematical magnitudes. A suffix or expected type determines the representation; an unconstrained runtime literal needs an annotation. No machine-default integer type is guessed. A syntactic negative integer literal is checked as one signed value, admitting the signed minimum; negation of an already typed expression obeys the ordinary range rule. An out-of-range literal is a compile-time error. |
| Ordinary `+`, `-`, `*` and unary `-` | Exact mathematical result with a proof that it is representable in the result type. Failure to discharge the premise is an unresolved obligation, not wrapping, trapping or a debug/release distinction. Operands have one explicitly determined type. |
| Ordinary `/` and `%` | Division truncates toward zero. For the mathematical quotient `q`, `a = q*b + r`, with `r` zero or of the dividend's sign and `abs(r) < abs(b)`. Both operations require a nonzero divisor; division additionally requires a representable quotient, excluding signed `MIN / -1`. Signed `MIN % -1` is exactly zero. A pair of runtime quotient/remainder results satisfies the equation only when the quotient is representable; the mathematical equation also describes the exceptional division input. |
| Checked arithmetic | Named `CheckedAdd`, `CheckedSub`, `CheckedMul`, `CheckedNeg`, `CheckedDiv` and `CheckedRem` return `Result<T, ArithmeticError>` with the ordinary value on `Ok`, otherwise the named `Overflow` or `ZeroDivisor` case. Division checks zero before signed quotient overflow; `CheckedRem(MIN, -1)` returns `Ok(0)`. They do not mutate their inputs or expose a partial result. |
| Modular and saturating arithmetic | Named `WrappingAdd`, `WrappingSub`, `WrappingMul` and `WrappingNeg` reduce modulo `2^w`, interpreting the resulting bits as the selected signed/unsigned type. `SaturatingAdd`, `SaturatingSub`, `SaturatingMul` and `SaturatingNeg` clamp the exact result to that type's minimum/maximum. There is no implicit modular conversion and no wrapping division/remainder in this initial vocabulary. |
| Bitwise operations and shifts | Bitwise operations use the selected `w` bits. Named `ShiftLeft` and `ShiftRight` take a `usize` count and require `count < w`; no implicit masking of excessive counts. Numeric left shift additionally requires the mathematical result to fit. Explicit `WrappingShiftLeft` discards high bits but retains the count bound. Right shift is zero-filling for unsigned and sign-extending for signed values, equivalent to floor division by `2^count`. `CheckedShiftLeft` and `CheckedShiftRight` return `InvalidShift` for an excessive count; the former returns `Overflow` for numeric left-shift range failure. |
| Conversions and comparisons | Infallibly wider scalar conversion uses `T.From(x)` (such as `long.From(x)` from `int`); range- or sign-checked conversion uses `T.TryFrom(x)` (such as `usize.TryFrom(x)` from `int`) and returns a named range failure; a proved conversion requires its range premise. Explicit truncation/reinterpretation uses a separately named bit operation. Ordering compares mathematical values within one type. Executable equality is Boolean through a selected decidable operation; proposition equality and transport stay in proof/contract interpretation. |
| Layout and encoding | Scalar representation/alignment is fixed by the target/ABI. Integer-to-byte encoding uses explicitly named little- or big-endian library operations; native record layout and padding never define a wire format. Capability fabrication and implicit pointer/integer conversion remain excluded. |
| Floating point | Not in this initial runtime release. A future consumer must select formats, NaN/signed-zero/rounding and exception behavior, equality/ordering, constant evaluation and target correspondence together. Parser recognition or existing hardware floating-point instructions supply no Vela support claim. |

Numeric aliases follow the [module rules](#modules-and-packages): use an explicit
`import Vela.Numerics;` or the fully qualified name, such as `Vela.Numerics.int`.
The dependency lock binds the standard library package and its definitions;
there is no implicit prelude or import-order precedence. A duplicate local or
imported alias name is diagnosed under the same rules as another duplicate
binding; explicit qualification identifies the intended declaration. The source
facts retain that alias declaration and source spelling while type equality,
instance coherence, representation and lowering use the target type identity.
An alias creates no new nominal type, distinct implementation instance, runtime
conversion, numeric suffix or default integer type. Literals use the existing
suffix or expected-type rule; C# spelling does not import its conversion or
overflow behavior. Q25z's [migration qualification](surface-grammar.md#familiar-authoring-migration)
checks alias/target agreement, qualified and imported resolution, collisions,
range refusals and source provenance before these aliases are supported.

Named operations are library interface commitments. The surface parser may need
no new productions for them, but implementations and operation laws remain to be
qualified. No generic operator overload can change these primitive meanings or
silently insert a conversion. Bounds failures use explicit checked APIs or proof
premises under the same rule; there is no unchecked indexing shortcut.

### Contextual inference

Local inference removes an annotation only when the selected declaration and
checking context determine its meaning. Expected types may determine exact
integer literal representations, generic arguments, lambda parameters and
stable dependent indices. Range bounds share a selected integer representation:
`0..buffer.Length` can infer `usize` for the literal from that upper bound.
A suffix or annotation conflicting with the bound is an error; an already typed
operand never changes type to make the range fit. Ambiguous runtime widths need
an annotation, including an otherwise unconstrained `let count = 0;`.

Inferred indices retain stability and representation checks. Inference never
changes instance coherence, supplies authority, converts an existing value,
inserts ownership transfer or drops an obligation. An inferred proof is still
checked evidence; an unresolved goal remains unresolved. Public signatures keep
reviewed representations, static inputs, resource modes, effects and exits.
Qualification compares explicit and inferred clients at the same interpretation
and artifact endpoint, with exact boundary literals, ambiguity, wrong widths,
unstable indices and stale-source controls. Current pure/mathematical prototypes
retain their own scalar types; parsing a machine literal or loop supplies no
represented-inference implementation.

### Bytes and text

Source files are strict UTF-8. First-release identifiers retain the prototype's
ASCII identifier alphabet; string contents may contain Unicode. A `char` denotes
one Unicode scalar value (`U+0000` through `U+10FFFF`, excluding surrogates), with
a checked finite representation. A string literal denotes its exact UTF-8 bytes
without normalization, a terminator or implicit allocation. Embedded `U+0000`
is an ordinary scalar. Literal escapes are `\\`, `\"`, `\'`, `\n`, `\r`, `\t`,
`\0`, and `\u{H...}` with one through six hexadecimal digits denoting a scalar;
malformed/unknown escapes, invalid UTF-8 and non-scalar escapes are rejected.
Character literals decode to exactly one scalar. Raw string literals open with
three or more double quotes (`"""..."""`) and close with the matching quote
count without escape processing. Single-line raw strings contain no line breaks
between delimiters; multi-line raw strings follow the opening delimiter with a
newline, place the closing delimiter on its own whitespace-indented line, strip
that closing line's leading horizontal whitespace from every non-empty content
line (rejecting non-empty content lines with less indentation), exclude the
opening newline and the newline immediately preceding the closing delimiter, and
normalize interior line breaks to LF (`\n`). Raw byte data uses byte buffers
and explicit encoders rather than malformed text literals.

The initial text library uses an immutable validated UTF-8 view with represented
byte extent and the ordinary loan/lifetime contract. Decoding untrusted bytes
returns either that view with its validity proof or a typed encoding error;
neither path invents ownership or extends the input's lifetime. A mutable byte
alias cannot survive beside a validity-dependent immutable text view.

`ByteLength` counts encoded bytes. `ScalarCount` is an explicitly bounded
traversal; neither claims to count grapheme clusters or display cells. Text has
no ambiguous integer indexing operation: access its byte view, iterate scalars,
or use a checked byte-range slice whose endpoints are UTF-8 boundaries. Text
equality compares exact encoded bytes; canonically equivalent but differently
encoded scalar sequences remain distinct. Normalization, locale collation and
grapheme segmentation require separately specified libraries. Runtime-built
text uses explicit bounded storage, capacity outcomes and validation; literals'
read-only backing is charged to the composed image. Instead of C#/Kotlin's
heap-allocating `$"..."` string interpolation, runtime `Object.ToString()`
reflection or ambient `CultureInfo` locale formatting, Vela provides an explicit
buffer-writing interpolation and format surface (comparable to C# 10's
`InterpolatedStringHandler` or Rust's `write!`) such as
`Format.Write(ref builder, $"...")` that targets an explicit
`ref TextBuilder<capacity>` or `ref Span<byte>`, resolves a coherent static
`Format<T>` interface per interpolation hole (`{value}` or compile-time checked
`{value:spec}`) without runtime reflection, boxing or ambient locale, and
returns an explicit `Result<usize, CapacityError>`. Standalone `$"..."`
expressions without an explicit destination buffer are rejected; capacity
exhaustion returns `Err(CapacityError)` under the target builder or span's
declared rollback/prefix contract.

## Modules and packages

The module boundary must support two independently authored libraries before
public generic APIs qualify. A package manifest names its canonical package,
language edition, module roots, direct dependencies, explicit build inputs and
target/profile. A lock records each resolved package's exact source digest,
selected version/revision, transitive closure, generator/tool identities and
configuration. Locked builds neither resolve a different version nor read
undeclared ambient inputs. Fetching dependencies is an explicit preparation
operation; missing locked inputs produce an incomplete-build result.

The initial import graph is acyclic and imports are explicit. Cycles report the
cycle rather than depending on traversal order. Modules have no runtime
initializers. Required-static initialization evaluates ordinary total pure
definitions: each required-static input must resolve to an admissible closed
value when its use is specialized, or the build reports a located obligation or
refusal with no runtime fallback. [`const` declarations](surface-grammar.md#required-static-constants)
spell the interface, and [the core's staging rules](core-design.md#refinement-effects-and-staging)
bound conversion and erasure.
Qualified names resolve independently of import order. Duplicate local/imported
bindings are errors unless an explicit alias distinguishes them. A public nominal
identity comprises the resolved package instance, module path and declaration
identity. Two package revisions with the same printed type name are distinct;
neither structural similarity nor reflection can equate their private types.

The first interface implementation model uses explicit nonoverlapping
instances. The defining package must own the interface or the outer
nominal implementing type. A bare type parameter does not establish ownership;
foreign interfaces on foreign primitive types require a local nominal wrapper.
Instance heads use nominal type constructors, rigid constants and type
parameters, with structural unification deciding possible overlap. Arbitrary
computed type families and proof search are unavailable in instance selection.
Potentially overlapping instances are rejected without specialization, priority,
negative bounds or import-dependent choice. An interface fixes its qualified
instances or explicit dictionary parameters; adding an unrelated dependency
cannot change a selected implementation. Required laws are checked fields of
that dictionary, not facts obtained by finding its name.

An unqualified interface method name or receiver call must identify one visible
interface by method name and source argument count, counting the receiver as
the first argument. If several interfaces remain, qualify the call as
`Interface.Method(...)`, including when their implementations accept disjoint
argument types. Argument types, result types, contracts and declaration/import
order do not choose between interface names. After choosing the interface, its
ordinary type, instance and contract checks still apply.

Public signatures specify generic and required-static parameters, result types,
effects, call modes, transitive capture constraints, pre/postconditions and
resource exits. Private representations stay abstract except through explicit
published views or derivation interfaces. Implementation changes must re-establish
the exported contract. An interface fingerprint binds these semantic declarations,
the nominal identities and any exposed representation/ABI; source maps have a
separate exact-byte identity. Dependency records also include implementation and
proof bodies actually consumed, accepted assumptions, target and tools. An equal
interface fingerprint alone cannot reuse stale compilation or proof evidence.
Until finer dependency tracking is qualified, a semantic dependency change
invalidates the reachable component closure conservatively.

## Ownership libraries

The initial client needs a small, proved library of buffers, immutable/mutable
spans, bounded iteration, records/sums, initialization and typed errors. Public
operations state capacity, bounds, overlap, initialization, retained loans and
resource states on every exit. Every sequence-modeled view or buffer implements
the law-carrying `ISequenceModel<T>` interface, projecting the container to its
canonical erased pure `Model : Seq<T>` (`Nat(Length) == Model.Count`) while
keeping the C#/Kotlin-style collection predicates and slice combinators—`.All(x => ...)`,
`.Any(x => ...)`, `.Contains(x)`, `.Take(n)`, `.Skip(n)`, `.Slice(a, b)` and
`.Count` alongside `.At(i)`, `.Update(i, v)` and `.Append(x)`—as concrete
operations on `Seq<T>` backed by pre-proved standard-library lemmas. Contracts
on concrete or `ISequenceModel<T>`-bounded containers write
`requires items.Model.All(x => x > 0)` rather than raw `forall`/`exists`
index quantifiers, and bounded predicates over finite sequences with decidable
element bodies discharge in the
[decidable/domain refinement tier](core-design.md#refinement-effects-and-staging)
rather than open quantifier instantiation or polymorphic LINQ dispatch. No
runtime `IQueryable<T>` or reflection-based expression-tree interface is
introduced; contract checking inspects `Seq<T>` predicate lambdas statically, and
compile-time query specialization is an extension under the [staging design](../extensions/metaprogramming.md#evaluation-and-phase-boundaries).
Iterators carry their bounds and loan contracts; they do not require ordinary
users to reconstruct a separation-logic proof at each element. Codecs retain the
platform's required format-description and
[boundary initialization obligations](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/spec.md#r-05-124).

The [collection-loop surface](surface-grammar.md#ergonomic-authoring-and-bounded-collection-iteration)
uses a law-carrying `IBoundedIterable<T>` interface refining `ISequenceModel<T>`
rather than C#'s stateful `IEnumerable<T>` / `IEnumerator<T>` (`MoveNext`/`Current`/`IDisposable`).
Value iteration requires copy permission; shared/exclusive iteration selects an
explicit element loan. The source is evaluated once, a declared `Model.Count`
bound and stable footprint determine iteration, and step `k` connects directly to
`Model.At(k)`, `Model.Take(k)` and `Model.Skip(k)`. All exhaustion and early-exit
paths restore or explicitly return the resources promised by the iterator
contract. No enumerator allocation, implicit disposal, owned-element copy,
escaping element loan or invalidating mutation is introduced. Parser support is
syntax-only until a real iterator library and represented checker discharge those
duties.

`out T` retains its simple rule: no reads before initialization and a fully
initialized `T` on every normal return, including an error return. Fallible
construction instead consumes an owned storage/builder state and returns an
outcome-indexed state: a completed value, an explicitly retained initialized
prefix, or restored empty storage after total rollback. These are library types
and resource contracts, not an unchecked `MaybeUninit` escape. The initialization
map names exactly the fields/elements that may be read or disposed; dropping a
partially built object visits only those entries, accounts for their resources,
and restores the promised storage state. Failure must return storage and
unconsumed inputs or discharge them through an explicit proved operation.
Boundary-mandated whole-buffer initialization and zeroization are unchanged.
`TextBuilder<capacity>` and `Format.Write(ref builder, $"...")` (or
`Format.Write(ref span, $"...")` over `ref Span<byte>`) follow the bounded
buffer-writing contract in [Bytes and text](#bytes-and-text), evaluating hole
arguments left-to-right under the active receiver loan and returning
`Result<usize, CapacityError>` with the declared prefix/rollback state on
`Err(CapacityError)`.

Construction, replacement and bounded collection growth must demonstrate failure
before the first write, partial failure, successful completion and rollback with
a live unrelated frame. Multi-step container updates that temporarily decouple
fields declare named invariant conjuncts (`invariant Clause: ...`) and open only
the affected clauses through `open (ref this) lifts Clause, ... { ... }`:
unlifted conjuncts remain active without re-proof across disjoint or
non-invalidating field writes, while the linear close debt forbids early exits
(`return`, `break`, `continue`, `?`), suspension, handler capture or whole-receiver
calls until the lifted clauses are re-established at the closing brace. Bulk prefix
relocation between vacant-slot buffers (`Slots<T, capacity>`) separates physical
representation copying from logical ownership transfer: `CopyRepresentation`
performs a CHERI-tag-preserving copy of `[0..count)` into logically vacant
destination slots (`Vacant<T>`), leaving the destination vacant/unowned and
recording a revision-bound representation-equality fact without arming destructors
or duplicating linear ownership, and the erased operation `TransferType<T>`
consumes that representation-equality fact with the initialized source prefix and
vacant destination prefix to transition source `[0..count)` to vacant and
destination `[0..count)` to live initialized `T` in one capacity-independent range
step. No allocation, emergency capacity or cleanup retry is
implicit. A later explicit bounded-pool library additionally satisfies the
[pool declaration and exhaustion contracts](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/spec.md#r-08-046), with
reuse/quiescence proof before returned backing is lent again.

The receiver loan starts before explicit argument evaluation, using its declared
whole-object or named-view footprint. Preserve this simple first-release rule.
For a whole-buffer receiver, `buffer.Append(buffer.Length)` conflicts when the
argument reads the borrowed footprint. A diagnostic names both accesses and
offers a preceding immutable snapshot only when its evaluation and lifetime
preserve the program's meaning. Named disjoint views can avoid the conflict.
Two-phase receiver borrowing remains a separately priced option, triggered by
measured client friction rather than made a prerequisite for ordinary ownership.
No diagnostic may silently reorder effectful arguments or insert hidden loans.

## C# transition guide <a id="csharp-transition-guide"></a>

Use type-first declarations, PascalCase members, camelCase locals, `this`, ordinary
generic calls, expression bodies and inferred lambdas consistently. The
[authoring style](../tooling/authoring-tools.md#common-style) and
[binding guidance](../tooling/authoring-tools.md#lint-policy) keep `let`/`var` visible whether
the type is inferred or explicit. These familiar spellings retain Vela's rules:

| Surface | Vela meaning to explain |
| --- | --- |
| `let T value` | Immutable binding (bare `T value = ...;` is refused; use `let` or `var`); writing through an eligible exclusive loan is a separate operation |
| `var T value` | Mutable binding, with no implicit shared-write permission |
| `in`, `ref`, `out` | Explicit shared-read, initialized-exclusive and initialization-exclusive loans; ordinary calls repeat their mode, and [assist-don't-coerce tooling](../tooling/authoring-tools.md#compiler-verified-assist-dont-coerce-tooling) offers a checked insertion when omitted |
| `out T` with a fallible result | `T` is initialized on every normal return, including errors; partial construction uses outcome-indexed owned storage |
| Labeled arguments | Labels name the next declared parameter in declaration order, preserving dependent substitution and left-to-right evaluation; no reordering or defaults |
| `int` and ordinary arithmetic | Explicitly imported exact alias; representability obligations and checked-result alternatives follow [primitive semantics](#primitive-semantics), and conversion diagnostics suggest `long.From(x)` or `usize.TryFrom(x)` |
| `Option<T>`, `None` and propagation | Absence is an explicit case (`None => ...` in `match`, written bare without `()`); `?` is early-return propagation rather than C# `?.`, so member access writes `(Read()?).Value` or a local `match` |
| Explicit `effects(...)` on public functions | Public signatures declare a closed read/write/call footprint; when omitted or under-specified, the compiler offers a checked `effects(...)` preview |
| `if (cond) a else b` (instead of `cond ? a : b`) | Conflict-free conditional expression with mandatory `else`, desugaring to the same exhaustive Boolean elimination and resource join as a two-arm `match` |
| `Accepted(packet: p, receipt: r)` | Optional declaration-order field labels in constructor patterns, symmetric with labeled call arguments |
| `base with { Field = value }` / `move base with { ... }` | Postfix record/model update evaluated left-to-right in declaration order; linear or affine records require `move base with { ... }` |
| `let Some(v) = expr else { return ...; }` and `if (x is Some(v))` | Scoped early-exit guard where `else` must exit the enclosing scope, or flow-refined conditional pattern matching binding `v` in `then` |
| `public usize Length => ...;` / `public ghost Seq<T> Model => ...;` | Get-only, total, effect-free expression properties (`a.B` is always a pure, allocation-free read); `set` accessors and effectful or fallible getters are excluded |
| `"""..."""` (raw string literals) | Exact UTF-8 bytes without escape processing; multi-line forms strip the closing delimiter line's indentation prefix and normalize interior line breaks to LF (`\n`) |
| `Format.Write(ref builder, $"...")` (instead of heap `$"..."` / `ToString()`) | Allocation-free checked formatting into an explicit `ref TextBuilder<capacity>` or `ref Span<byte>` via static `Format<T>` instances, returning `Result<usize, CapacityError>` |
| `.Model.All(x => ...)`, `.Any(x => ...)`, `.Contains(x)`, `.Take(n)`, `.Skip(n)`, `.Slice(a, b)`, `.Count` | Pure mathematical `Seq<T>` predicates and slices in contracts, discharged in the finite-sequence refinement/domain tier instead of raw `forall`/`exists` index quantifiers |
| `ISequenceModel<T>`, `IBoundedIterable<T>` (instead of `IEnumerable<T>` / `IQueryable<T>`) | Law-carrying interfaces projecting containers to `Model : Seq<T>` and linking bounded `foreach` steps to `Model.At(k)`, `Model.Take(k)` and `Model.Skip(k)` with explicit element loans and zero enumerator allocation |
| `invariant Clause: P` and `open (ref this) lifts Clause, ... { ... }` | Named invariant conjuncts and lexical selective lifting; keeps unlifted conjuncts active, forbids early exits or whole-receiver calls while open, and re-proves only the lifted clauses at block exit |
| `CopyRepresentation(in src, ref dst, count)` then `TransferType<T>(ref src, ref dst, count)` | Two-step bulk relocation over `Slots<T, capacity>`: tag-preserving representation copy into vacant storage followed by erased linear ownership transfer in one capacity-independent range step |
| `interface I...` and `impl I... for Type`, `where I...(type T)` | Law-carrying interfaces with explicit nonoverlapping `impl` instances and proved `lemma`/`theorem` law fields in the static witness dictionary |

Receiver signature help shows the selected mode and named view. A conflict names
both accesses and may offer a preceding immutable snapshot only when evaluation,
effects and lifetimes preserve meaning. Completion can offer exhaustive
`Option`/`Result` arms and explicit propagation only from the current resolved
type and resource exits. These wider editor features require their qualified
[compiler facts](../tooling/tooling-protocols.md#language-server-protocol); the pure language
server cannot infer a borrow verdict or advertise unsupported code actions.

## Qualification

The [delivery plan](../../PLAN.md#vela-first-release-delivery) selects a real
bounded byte-buffer consumer and an independently chosen second client before
implementation. Their contracts must identify actual formats, entry states and
independently expected success/failure results. A candidate that only parses,
emits a term or returns an unconstrained theorem has not met this predicate.

| Subject | Acceptance evidence |
| --- | --- |
| Interpretation and concrete resources | Checked elaboration-image laws, an inhabited carrier state, read/write/initialization/frame and loan restoration, with wrong-offset, alias, premature-restoration and partial-initialization neighbors rejected at the intended obligations. Missing laws remain missing; no axiom or source judgment substitutes for them. |
| Scalar and text behavior | Independent boundary fixtures for every supported type and operation, signed division/remainder signs, zero and minimum/-1, shift zero/width-1/width, exact/wrapping/saturating arithmetic, target versus host width, invalid conversions, embedded NUL, malformed UTF-8/escapes, raw-string delimiter/indentation and LF-normalization rules, static `Format<T>` checked formatting (`Result<usize, CapacityError>` on exact fit and `CapacityError` exhaustion without heap allocation or ambient locale), scalar boundaries and byte slicing. Static and runtime meanings agree under the same target. Generate finite boundary classes from an independently reviewed oracle; a shared implementation is not an independent expectation. |
| Package composition | Two independently authored packages compose with fixed instances; reordered imports preserve meaning; overlap, cycles and conflicting nominal identities are diagnosed. Locked builds reproduce their source/input closure. Contract, representation, proof assumption and tool changes invalidate affected evidence before reuse. |
| Everyday ownership | Bounded collection/iterator, `.Model` sequence-predicate/slice, `TextBuilder<capacity>` / `Format<T>` checked formatting, receiver-snapshot, selective invariant lifting (`invariant Clause: ...` / `open (...) lifts ...`), two-step bulk relocation (`CopyRepresentation` + `TransferType<T>`), fallible-builder and error-propagation clients compile under their actual representations and the [borrow-analysis promotion contract](core-design.md#borrow-analysis-promotion); escaped views, duplicated tokens, reads of unwritten or moved-out vacant slots, early exits or whole-receiver calls while an invariant clause is lifted, stale current-content facts and lost mandatory outcomes fail at the responsible resource rule. Bounded buffer, builder and bulk-relocation proofs/certificates pass a **capacity-invariance gate**: checking at tiny static capacity ($N = 4$) and large static capacity ($N = 10^9$) produces identical obligation counts, proof-term/certificate complexity and replay cost with no per-element unfolding proportional to static capacity. |
| Complete software path | Authored source and independent contract reach one retained backend with checked correspondence, representation and lowering; applicable final-byte, resource, observation and admission duties meet their existing owners. Report source, artifact and production evidence separately. |
| Developer usefulness | Record annotation burden, first useful diagnostic, checking latency, code/stack/storage consequences and repair after a semantic-preserving refactor, a representation change and a real contract change on both clients. Attribute annotation burden and repair effort separately to arithmetic representability obligations, closed `effects` lists propagated through callers, and the absence of two-phase receiver and loop-carried borrows, counting each explicit lemma, checked operation, widened effect list, snapshot, named view or restructured loop they force; these records decide whether a separately priced relaxation is warranted. A held-out client cannot be redesigned to fit the candidate unnoticed. |

Hard safety, resource and admission limits are mandatory. Technical feasibility,
recurring authoring/maintenance benefit and eventual economic adoption are
separate decisions. Charge setup and shared maintenance fully, without requiring
the first two small clients to repay the entire language foundation. Any accepted
size/speed trade has a declared target envelope and per-case evidence; no average
hides a missed hard bound. The canceled [workflow comparison](../assurance/workflow-contract.md)
retains its frozen experiment's identity and verdict, and supplies no current
product acceptance by implication.

### First-slice component and concrete `Span<byte>` carrier <a id="first-slice-qualification"></a>

[examples/first_slice.vela](../../examples/first_slice.vela)
authors the bounded packet/manifest validator `PrepareAndValidatePacket(ref<'dst> Span<byte> dst, in Span<byte> pkt) -> Result<ValidatedPacket<'dst>, ValidationError>`
and its supporting helpers (`WritePacket8`, `PrepareSliceHeader`,
`SpecPacketChecksum`, `SpecPacketValid`, `CopyPacketToDst`,
`ComputePacketChecksum`) over the concrete `Span<byte>` carrier in
[tools/toolchain/elaborate.py](../../tools/toolchain/elaborate.py) and the
CompCert Clight/C and purecap CHERI-RISC-V target harness in
[tools/toolchain/first_slice.py](../../tools/toolchain/first_slice.py).
Obligations the elaborator cannot kernel-prove reach Rocq with their real
statements as named solver-trust axioms recorded in `solver_trust`, so
`Print Assumptions` and the harness report kernel-proved definitions and
solver-trusted obligations separately; a non-empty solver-trust ledger leaves
the slice unaccepted as a closed kernel proof. The current local replay audits
69 exports with `solver_trusted_count == 0`, `accepted: true` and
`kernel_checked: true`. Inference rollback retains normalization caches only
when metavariable state is unchanged; this closes
`PrepareAndValidatePacket_ensures_0`, `PrepareAndValidatePacket_ensures_2` and
`ValidateEmptyPacketOk` within the existing work/reduction budgets. All exported
definitions report `Closed under the global context`. These source proofs do
not establish checked source correspondence or machine/artifact acceptance.

- **Concrete `Span<byte>` carrier and contract obligations:** `Span<byte>` lowers
  in the mathematical consumer to `vela_Span` (`vela_ByteStore` paired with
  `Base`, `Length`, `Tag`, `PermRead`, `PermWrite` and derived
  `CanRead` / `CanWrite` predicates), while `Span.AllocZeroed` is restricted to
  specification and theorem contexts so executable code cannot fabricate
  capabilities from raw addresses. Bounded operations `Span.Read`, `Span.Write`,
  `Span.Fill`, `Span.Slice`, `Span.ReadOnly`, `Span.Invalidate`,
  `Span.Disjoint`, `Span.CopyPrefix` and `Span.Restore` require checked bounds,
  read/write capability permissions, loan-mode discipline (`in Span<byte>`
  read-only vs `ref Span<byte>` read-write), read-only enforcement on record
  fields of type `in<'a> Span<byte>`, and disjoint base intervals before
  emitting terms. Function contracts elaborate `requires` into typing premises,
  automatic `ref` descriptor preservation (`restores`) into five kernel-proved
  metadata-preservation obligations (`Base`, `Length`, `Tag`, `PermRead`,
  `PermWrite` between the post-state of each `ref` `Span`/`Slots` parameter and
  its entry state), and `ensures` into postcondition obligations with `result`
  bound to the function body and `ref` parameters bound to their kernel
  post-state images (`_post_<param>`).
- **Elaborated laws, synchronous validator and scenario theorems:** `Vela.FirstSlice`
  elaborates eleven carrier laws (`LawInhabitedByteCase`, `LawAllocZeroedRead`,
  `LawReadOverWriteSame`, `LawReadOverWriteOther`,
  `LawLoopFramePreservesDisjointSuffix`, `LawFillAndFrame`,
  `LawSliceMetadataAndRead`, `LawReadOnlyAndInvalidate`,
  `LawDisjointCopyAndFrame`, `LawCapacityInvarianceSmall`,
  `LawCapacityInvarianceLarge`), two zeroed-header lemmas
  (`LawZeroedHeaderHasZeroMagic`, `LawZeroedHeaderHasZeroFlags`), synchronous
  `WritePacket8`, `PrepareSliceHeader`, `SpecPacketChecksum`, `SpecPacketValid`,
  `CopyPacketToDst`, `ComputePacketChecksum` and `PrepareAndValidatePacket`
  (with `Result<ValidatedPacket<'dst>, ValidationError>`, fat-arrow `match`,
  explicit `effects writes(...), reads(...)` lists, returned subslice views in
  `ValidatedPacket<'dst>`, `foreach` loops with `invariant`/`decreases`, 20
  kernel-proved automatic `ref` descriptor preservation obligations and
  kernel-proved `ensures` contracts), and seven symbolic scenario theorems
  (`ValidateEmptyPacketOk`, `ValidateFullPacketOk`,
  `ValidatePartialPacketScrubsStaleAndTrailingBytes`, `RejectFramingShort`,
  `RejectBadMagic`, `RejectLengthOutOfBounds`,
  `RejectChecksumScrubsDestinationAndRestores`) with separation-logic framing
  (`dst[frameIdx] == old(dst[frameIdx])`) over loops and slices.
- **End-to-end qualification (`python tools/run.py vela-parser first-slice`):**
  1. Parses `first_slice.vela` through the native Menhir `--surface` parser,
     elaborates all declarations into `FirstSlice.v`, compiles with `rocq c`,
     audits all 69 exported definitions via `Print Assumptions` against the
     explicit `solver_trust` ledger, requiring an empty ledger for acceptance,
     and runs `rocqchk`, plus a fail-closed proof-corruption negative control.
  2. Runs the capacity-invariance gate at $N = 8$ (`8usize`) and $N = 10^9$
     (`1_000_000_000usize`), checking that obligation count, inference work
     steps, reduction steps and emitted Gallina structure are invariant across
     both capacities and that both pass `rocq c` and `rocqchk`.
  3. Replays 17 schema-2 semantic negative controls (`oob-read`, `oob-write`,
     `oob-slice`, `oob-fill`, `mutate-in-borrow`, `mutate-readonly-view`,
     `mutate-readonly-record-view`, `read-invalidated-view`,
     `overlapping-copyprefix`, `foreign-restore`, `broken-restores-contract`,
     `restore-then-return-view`, `capability-fabrication`,
     `missing-write-effect`, `wrong-expected-byte`, `stale-input-leak`,
     `loop-frame-overlap`) through the native parser and confirms each fails with
     `category == "type"`.
  4. Executes the purecap CHERI-RISC-V hardware capability slice (`csetbounds`,
     `candperm`, capability round-trip and byte checks) and three hardware fault
     controls (`bounds-trap`, `perm-trap`, `tag-trap`) on `sail_riscv_sim`.
  5. When a CompCert executable is supplied, lowers the executable union, record and function AST declarations
     (`ValidationError`, `ValidatedPacket`, `WritePacket8`, `CopyPacketToDst`,
     `ComputePacketChecksum`, `PrepareAndValidatePacket`) and their seven scenario
     drivers to CompCert Clight/C (`-fverifiedos-typed -dclight`), executes the C
     harness under both `ccomp -interp` and purecap `sail_riscv_sim`, and verifies
     four perturbed C negative controls (`wrong-expected-byte`,
     `stale-trailing-leak`, `checksum-scrub-omitted`,
     `restores-length-corrupted`). The current local endpoint has no CompCert
     executable and records `compcert_sail.available: false`.
- **Retained development receipts:** schema 2 binds the producer Git revision,
  current local toolchain Python sources, parser sources and generated outputs,
  dependency locks, instruction-encoding data, locked prover binaries and runtime
  libraries, Python interpreter, simulator, target profile, optional CompCert
  executable, retained outputs and process transcripts. Source, tool, profile,
  parser or runtime changes during qualification withdraw publication; a failed
  attempt removes the latest passing receipt and retains its failed journal.
  `python tools/run.py vela-parser first-slice-bindings <receipt.json>` checks
  these identities against the current checkout and installed inputs, refusing
  changed, missing or malformed data. Its `status: matched` reports byte binding;
  `proof_replayed: false` states that it does not rerun the proof commands.
  Before matching, it checks the declared source, Gallina and C subjects against
  their retained hashes, requires the source compilation, complete export
  assumption query, recursive kernel check and proof-corruption transcripts,
  and re-reads the retained Gallina and assumption reports. Missing exports,
  omitted libraries, changed process subjects or verdicts and source-proof
  status inconsistent with the actual solver-trust ledger refuse, including
  attempts to promote a nonempty ledger by changing `accepted` or `kernel_checked`.
  Both capacity compilation transcripts and their joint kernel-check transcript
  are required, together with retained capacity sources and libraries. The
  declared small/large capacities, nonnegative work metrics and retained Gallina
  byte lengths are checked. All 17 semantic-negative observations must name each
  current control exactly once, report successful surface parsing and the
  expected semantic refusal with a positive source location. Omitted, duplicate,
  syntax-only or unrelated refusals cannot preserve a matching receipt. These
  checks establish retained coverage; they do not rerun the controls or recompute
  elaboration work counters.
  Native proof observations bind separate UTF-8 stdout/stderr byte lengths and
  hashes within each combined retained transcript. The assumption audit consumes
  that checked stdout segment; tool diagnostics on stderr remain retained without
  becoming assumption reports or weakening malformed-stdout refusals.
  Output directories must belong to the current checkout's local lane; inventories
  reject aliases and exceedance of 4,096 entries or 256 MiB. Runtime identity
  normalizes only the qualification working-directory load-path entry, retaining
  external library paths, logical names, installation markers and file hashes.
  Full local proof replay uses `first-slice`. These receipts preserve
  `accepted` as the source proof's empty solver-trust verdict and explicitly
  record `source_correspondence: false`, `artifact_accepted: false` and
  `production_admission: false`. A missing CompCert run stays visible as
  `compcert_sail.available: false`. No checked canonical-model, compiler,
  contextual-security or admission receipt is supplied by this binding check;
  the [producer-receipt cell](../../PLAN.md#q25ar) remains open.
- **Remaining full-chain boundaries:** this slice connects exact Vela source to
  kernel-checked Gallina obligations, AST-lowered CompCert Clight/C and purecap
  `sail_riscv_sim` execution, and emits an explicit law, assumption and
  blocking-dependency inventory (`inventory` in `vela-parser first-slice`).
  Whole-term canonical Sail machine-term compilation (`rv64d.v` at Rocq 9.3.0;
  `Q35b`/`Q35o`/`Q35p`), machine-logic `byte-instance` laws over `rv64d.v`
  (`Q35c`/`Q35m`/`Q35k`/`Q35l` and [cheri-foundation-map.md](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/hardware/cheri-foundation-map.md)),
  `Q2b`'s flat `BasicC64Semantics` decoder scope, mechanized Sail-to-Clight/CompCert
  refinement (`Q35d`, `M1.2g`, `Q35j`), broader frontend/admission closure and
  user-managed Host CI and Guest CI verdicts remain separate open obligations.
