# VelaLang Documentation Index

## Language specification (`docs/language/`)

| Document | Subject |
| --- | --- |
| [language/reference.md](language/reference.md) | Compact language reference: declarations, types, loans (`in`/`ref`/`out`), contracts, expressions, statements, patterns, proofs |
| [language/first-release.md](language/first-release.md) | First-release boundary, primitive semantics, module/package rules, ownership libraries, and first-slice qualification |
| [language/core-design.md](language/core-design.md) | Core design, explicit loan and mutation rules, refinement/domain tier, and proof obligations |
| [language/surface-grammar.md](language/surface-grammar.md) | Concrete syntax, precedence, patterns, required-static constants, and familiar authoring ergonomics |
| [language/loan-analysis.md](language/loan-analysis.md) | Path-sensitive loan-end inference over explicit flow facts |
| [language/language-landscape.md](language/language-landscape.md) | Language landscape behind Vela's handler, async, and surface decisions |

## Toolchain and IDE (`docs/tooling/`)

| Document | Subject |
| --- | --- |
| [tooling/pure-prototype.md](tooling/pure-prototype.md) | Pure Vela-to-Gallina translation prototype, extended expressions, and natural division/remainder |
| [tooling/parser.md](tooling/parser.md) | Menhir development parser, checked-parser migration contract, and generated syntax campaigns |
| [tooling/elaboration-prototype.md](tooling/elaboration-prototype.md) | Generic dependent mathematics, first-class proofs, and native Rocq kernel replay |
| [tooling/authoring-tools.md](tooling/authoring-tools.md) | Canonical formatter, advisory lints (`VELA101`–`VELA105`), numeric separators, and binding previews |
| [tooling/documentation-qualification.md](tooling/documentation-qualification.md) | Declaration-documentation attachment and hover qualification |
| [tooling/lsp-prototype.md](tooling/lsp-prototype.md) | Language Server Protocol lifecycle, diagnostics, navigation, inlay hints, formatting, and semantic tokens |
| [tooling/playground.md](tooling/playground.md) | Browser playground architecture, local loopback transport, and GitHub Pages in-browser runtime |
| [index.html](index.html) | GitHub Pages language overview, interactive tour, compact reference, and embedded Vela Playground |
| [tooling/tooling-protocols.md](tooling/tooling-protocols.md) | Compiler inspection API, LSP, Tree-sitter/TextMate, SARIF, SCIP, BSP, remarks/traces, DWARF, and DAP |

## Assurance and verification (`docs/assurance/`)

| Document | Subject |
| --- | --- |
| [assurance/verification-strategy.md](assurance/verification-strategy.md) | Verification strategy, kernel-honest elaboration boundary, permanent exclusions, and tool qualification |
| [assurance/compiler-route-contract.md](assurance/compiler-route-contract.md) | Retained compiler route and source-to-artifact correspondence contract |
| [assurance/workflow-contract.md](assurance/workflow-contract.md) | Workflow contract, representation-transfer comparison, and first-release adoption criteria |
| [assurance/critique.md](assurance/critique.md) | Design and conformance critique dispositions |
| [assurance/findings-register.md](assurance/findings-register.md) | Assurance findings (`F-353`–`F-356`) raised during Vela specification |
| [assurance/completion-log.md](assurance/completion-log.md) | Landing evidence for completed `Q25` items |

## Extension dossiers (`docs/extensions/`)

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
