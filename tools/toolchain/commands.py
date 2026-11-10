# SPDX-License-Identifier: Apache-2.0
"""Every command the VelaLang repository's tools offer, and the lane each one runs in."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    """One command: what to import, what it decides, and where it can decide it."""

    name: str
    module: str
    decides: str
    lane: str = "host"
    host_ok: frozenset[str] = field(default_factory=frozenset)

    def guest_only(self, argv: list[str]) -> bool:
        """Whether this invocation must run in the guest rather than here."""
        if self.lane != "guest":
            return False
        return not argv or argv[0] not in self.host_ok


COMMANDS: tuple[Command, ...] = (
    Command("validate", "toolchain.cli.validate",
            "run logged local checks and tests; --static and --full select explicit coverage"),
    Command("gate", "toolchain.cli.gate",
            "run check, markdown, and typecheck in one static verdict"),
    Command("check", "toolchain.cli.check",
            "repository hygiene, licensing, source-comment links, and plan-summary arithmetic"),
    Command("markdown", "toolchain.cli.markdown",
            "closed-world Markdown linting and link validation under pinned rumdl"),
    Command("typecheck", "toolchain.cli.typecheck",
            "the tools' own Python, under two pinned checkers"),
    Command("prepare", "toolchain.cli.prepare",
            "format selected Python or Markdown files with locked tools, without builds"),
    Command("test", "toolchain.cli.test",
            "the Vela toolchain's behavioral tests"),
    Command("vela", "toolchain.cli.vela",
            "check pure Vela prototype source and emit unqualified Gallina definitions"),
    Command("vela-lsp", "toolchain.cli.vela_lsp",
            "serve host LSP diagnostics and navigation for unqualified pure Vela over stdio"),
    Command("vela-highlight", "toolchain.cli.vela_highlight",
            "generate and qualify syntax-only Tree-sitter and TextMate editor assets",
            lane="guest", host_ok=frozenset({"check", "generate", "--help", "-h"})),
    Command("vela-playground", "toolchain.cli.vela_playground",
            "serve the unified Vela browser editor with dependent mathematics", lane="guest"),
    Command("vela-parser", "toolchain.cli.vela_parser",
            "parse Vela, elaborate dependent mathematics and replay proofs", lane="guest"),
)

BY_NAME: dict[str, Command] = {command.name: command for command in COMMANDS}
