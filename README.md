# VelaLang

**Vela** is a programming language for writing low-level systems code and mathematical proofs in the same file. Designed alongside [VerifiedOS](https://github.com/symbiogenesis/VerifiedOS), it combines a familiar, readable syntax (inspired by C# and Rust) with explicit memory control and direct translation to the [Rocq Prover](https://rocq-prover.org/) and CompCert C.

> **Try Vela in your browser:** Open the **[Vela Interactive Playground & Language Tour](https://symbiogenesis.github.io/VelaLang/)** to run examples, evaluate expressions, and inspect generated Rocq/Gallina code with zero setup.

## Why Vela?

Usually, building verified systems software means writing your fast, low-level code in one language and rewriting a model of it in a separate theorem prover. When a proof breaks, hidden compiler magic—like implicit copies, silent type conversions, or invisible borrows—makes it hard to see why.

Vela brings the code and the proof together on one explicit surface:

- **Nothing happens behind your back.** Every borrow or ownership transfer is spelled out at both the function declaration and the call site: `in` for read-only borrows, `ref` for read-write borrows, `out` for initializing an output variable, and `move` for transferring ownership. There are no hidden copies or surprise heap allocations.
- **Code and proofs live side by side.** Functions can state what they expect (`requires`) and what they guarantee (`ensures`). Right next to them, you can write `definition` helpers and `lemma` or `theorem` blocks that the toolchain translates into Gallina for independent checking by the Rocq kernel (`rocq c` and `rocqchk`).
- **Invariants you can temporarily open and restore.** Data types can declare named rules—such as `invariant Ordered: Low <= High`. When a method needs to update several fields at once, `open (ref this) lifts Ordered { ... }` pauses just that rule for the block and checks that it holds again at the end, leaving every other rule intact.
- **Predictable control flow and memory.** Vela has no exceptions, no stack unwinding, and no garbage collector. Errors are returned as ordinary `Option<T>` or `Result<T, E>` values (with `?` for clean early returns), loops carry explicit bounds or `decreases` measures, and text formatting writes into fixed-capacity `TextBuilder<cap>` buffers.
- **Fast, unambiguous syntax.** Vela can be parsed from tokens alone without consulting a symbol table or import order, so editors, formatters, and verification tools always read your source the same way.

## A quick look at Vela

Here is a small Vela module from the [authored examples](examples/dependent.vela). It defines a range window that must stay ordered, a method that temporarily lifts that rule while updating both bounds, an `out`-parameter initializer, and a small proof:

```dafny
module Demo.Window;

public record RangeWindow(u32 Low, u32 High)
    invariant Ordered: Low <= High
{
    public definition u32 SpanWidth() => High - Low;
}

public RangeWindow RebalanceWindow()
    ensures result.Low == 4u32 && result.High == 9u32
{
    var window = RangeWindow(2u32, 5u32);
    open (ref window) lifts Ordered
    {
        window.Low = 4u32;
        window.High = 9u32;
    }
    return window;
}

public Unit InitBounds(u32 baseVal, out u32 low, out u32 high)
    requires baseVal <= 100u32
    ensures low == baseVal + 1u32
    ensures high == baseVal + 2u32
{
    low = baseVal + 1u32;
    high = low + 1u32;
    return;
}

public lemma TransitiveStep(Nat a, Nat b, Nat c)
    requires a == b
    requires b == c
    ensures a == c
    proof
    {
        calc
        {
            assert a == b;
            assert b == c;
        }
        assert a == c;
    }
```

## What works today

Vela is under active development. The repository is split into working development prototypes and the staged plan for the first production release:

| Area | Current status | Where to look |
| --- | --- | --- |
| **Pure compiler & IDE tools** | Runs on Windows and Linux. Typechecks pure `Nat` and `bool` modules, formats source code, runs style lints (`VELA101`–`VELA105`), emits Gallina, and serves IDE features over stdio (`vela-lsp`). | [docs/tooling/pure-prototype.md](docs/tooling/pure-prototype.md), [docs/tooling/lsp-prototype.md](docs/tooling/lsp-prototype.md) |
| **Surface parser & math elaborator** | Runs on Linux / WSL. Parses the wider Vela grammar with Menhir and elaborates generics, length-checked vectors (`Vec<T, length>`, `Fin<length>`), fixed-width integers, records with lifted invariants, `out` loans, interfaces, bounded loops, and proofs into Gallina for Rocq kernel replay. | [docs/tooling/parser.md](docs/tooling/parser.md), [docs/tooling/elaboration-prototype.md](docs/tooling/elaboration-prototype.md) |
| **Interactive playground** | Runs in the browser on [GitHub Pages](https://symbiogenesis.github.io/VelaLang/) or locally via `vela-playground`. Includes a Monaco editor, live diagnostics, a compile-time expression evaluator, Gallina output preview, and guided examples. | [docs/tooling/playground.md](docs/tooling/playground.md), [docs/index.html](docs/index.html) |
| **First-release delivery** | In progress. Tracks the remaining work to qualify checked parsing, editor clients, standard libraries, and the machine-level compiler route ([examples/first_slice.vela](examples/first_slice.vela)). | [PLAN.md](PLAN.md), [docs/language/first-release.md](docs/language/first-release.md) |

<a id="commands"></a>

## Quick start

Every tool and test in this repository runs through `python tools/run.py` (using Python 3.14; on Linux or inside WSL, use `python3 tools/run.py`). When you run a Linux-only command like `vela-parser` or `vela-playground` on Windows, `tools/run.py` automatically forwards it into WSL.

| Command | What it does |
| --- | --- |
| `python tools/run.py test` | Run the behavioral test suite (also the default when no command is given) |
| `python tools/run.py gate` | Run all static checks (`check`, `markdown`, and `typecheck`) in one pass |
| `python tools/run.py vela --help` | Check, format, lint, or emit Gallina for pure Vela files |
| `python tools/run.py vela-lsp --help` | Start the pure Vela Language Server over stdio |
| `python tools/run.py vela-playground` | Launch the local browser playground with dependent math support (`[wsl]`) |
| `python tools/run.py vela-parser --help` | Build the Menhir parser, elaborate dependent Vela, and run Rocq replay (`[wsl]`) |

See [tools/README.md](tools/README.md) for the full command list and toolchain policies.

## Repository map

| Path | What you will find there |
| --- | --- |
| [PLAN.md](PLAN.md) | Project backlog (`Q25` series), first-release delivery stages, and current execution state |
| [docs/README.md](docs/README.md) | Master index of all language specifications, tooling contracts, and extension dossiers |
| [docs/index.html](docs/index.html) | GitHub Pages language overview, interactive tour, compact reference, and browser playground |
| [docs/language/reference.md](docs/language/reference.md) | Compact language reference with syntax, examples, operator precedence, and status markers |
| [docs/language/first-release.md](docs/language/first-release.md) | Scope and semantic rules for the first supported synchronous Vela release |
| [docs/language/core-design.md](docs/language/core-design.md) | Core calculus, explicit loan and ownership rules, refinements, and proof obligations |
| [docs/language/surface-grammar.md](docs/language/surface-grammar.md) | Concrete syntax, formatting layout, pattern rules, and compile-time constants |
| [docs/tooling/elaboration-prototype.md](docs/tooling/elaboration-prototype.md) | How generic dependent math and first-class proofs translate to Rocq/Gallina |
| [docs/tooling/parser.md](docs/tooling/parser.md) | Menhir grammar, AST schemas, and checked-parser migration contract |
| [docs/tooling/lsp-prototype.md](docs/tooling/lsp-prototype.md) | Language Server Protocol diagnostics, navigation, type hints, and formatting |
| [docs/tooling/playground.md](docs/tooling/playground.md) | Browser playground architecture, expression console, and security boundary |
| [docs/assurance/verification-strategy.md](docs/assurance/verification-strategy.md) | Verification strategy, kernel-checking boundaries, and tool qualification rules |
| [docs/extensions/](docs/extensions/README.md) | Post-first-release designs: graded types, effect handlers/async, interior mutability, metaprogramming, and whole-system authoring |
| [examples/](examples/) | Working `.vela` examples ([pure.vela](examples/pure.vela), [constants.vela](examples/constants.vela), [expressions.vela](examples/expressions.vela), [surface.vela](examples/surface.vela), [dependent.vela](examples/dependent.vela), [first_slice.vela](examples/first_slice.vela)) |
| [tools/toolchain/](tools/toolchain/) | Compiler, dependent elaborator, loan analysis, formatter, linter, LSP server, Menhir parser ([parser/](tools/toolchain/parser/)), and playground ([playground/](tools/toolchain/playground/)) |
| [tools/tests/](tools/tests/) | Behavioral test suite (`test_vela*.py`) |
| [COPYRIGHT.md](COPYRIGHT.md) | Licensing overview (`Apache-2.0` for code and examples, `CC-BY-4.0` for documentation) |
| [THIRD-PARTY.md](THIRD-PARTY.md) | Third-party tool pins, browser editor assets, and upstream license records |
