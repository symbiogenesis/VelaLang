# VelaLang Documentation Index

## Language specification and release contracts

| Document | Subject |
| --- | --- |
| [reference.md](reference.md) | Compact language reference: declarations, types, loans (`in`/`ref`/`out`), contracts, expressions, statements, patterns, proofs |
| [first-release.md](first-release.md) | First-release boundary, primitive semantics, module/package rules, ownership libraries, and first-slice qualification |
| [core-design.md](core-design.md) | Core design, explicit loan and mutation rules, refinement/domain tier, and proof obligations |
| [surface-grammar.md](surface-grammar.md) | Concrete syntax, precedence, patterns, required-static constants, and familiar authoring ergonomics |
| [verification-strategy.md](verification-strategy.md) | Verification strategy, kernel-honest elaboration boundary, permanent exclusions, and tool qualification |
| [compiler-route-contract.md](compiler-route-contract.md) | Retained compiler route and source-to-artifact correspondence contract |
| [workflow-contract.md](workflow-contract.md) | Workflow contract, representation-transfer comparison, and first-release adoption criteria |
| [loan-analysis.md](loan-analysis.md) | Path-sensitive loan-end inference over explicit flow facts |

## Prototypes and tooling

| Document | Subject |
| --- | --- |
| [vela-prototype.md](vela-prototype.md) | Pure Vela-to-Gallina translation prototype, extended expressions, and natural division/remainder |
| [vela-parser.md](vela-parser.md) | Menhir development parser, checked-parser migration contract, and generated syntax campaigns |
| [elaboration-prototype.md](elaboration-prototype.md) | Generic dependent mathematics, first-class proofs, and native Rocq kernel replay |
| [authoring-tools.md](authoring-tools.md) | Canonical formatter, advisory lints (`VELA101`–`VELA105`), numeric separators, and binding previews |
| [lsp-prototype.md](lsp-prototype.md) | Language Server Protocol lifecycle, diagnostics, navigation, inlay hints, formatting, and semantic tokens |
| [playground.md](playground.md) | Local browser playground with Monaco editor, pure and dependent elaboration, and expression console |
| [tooling-protocols.md](tooling-protocols.md) | Compiler inspection API, LSP, Tree-sitter/TextMate, SARIF, SCIP, BSP, remarks/traces, DWARF, and DAP |
| [documentation-qualification.md](documentation-qualification.md) | Declaration-documentation attachment and hover qualification |

## Extension dossiers and background

| Document | Subject |
| --- | --- |
| [extensions/README.md](extensions/README.md) | Index of post-first-release extension dossiers |
| [extensions/graded-foundation.md](extensions/graded-foundation.md) | Graded dependent foundation and mode semiring |
| [extensions/handlers-async.md](extensions/handlers-async.md) | Algebraic effect handlers and structured async lifecycles |
| [extensions/interior-mutability.md](extensions/interior-mutability.md) | Interior mutability cells and interference guardrails |
| [extensions/assurance-profiles.md](extensions/assurance-profiles.md) | Assurance profiles and exported contract obligations |
| [extensions/metaprogramming.md](extensions/metaprogramming.md) | Staged metaprogramming, structural descriptions, and compiler services |
| [extensions/unified-source-contract.md](extensions/unified-source-contract.md) | Whole-system authoring proposal and native verified compiler |
| [extensions/full-language-review.md](extensions/full-language-review.md) | Combined calculus review and admission prerequisites |
| [language-landscape.md](language-landscape.md) | Language landscape behind Vela's handler, async, and surface decisions |
| [critique.md](critique.md) | Design and conformance critique dispositions |
| [completion-log.md](completion-log.md) | Landing evidence for completed `Q25` items |
| [findings-register.md](findings-register.md) | Assurance findings (`F-353`–`F-356`) raised during Vela specification |
