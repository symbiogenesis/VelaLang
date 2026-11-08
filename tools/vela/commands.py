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
    Command("test", "vela.cli.test",
            "the Vela toolchain's behavioral tests"),
    Command("typecheck", "vela.cli.typecheck",
            "the tools' own Python, under two pinned checkers"),
    Command("prepare", "vela.cli.prepare",
            "format selected changed files with locked tools, without builds",
            lane="guest", host_ok=frozenset({"python"})),
    Command("vela", "vela.cli.vela",
            "check pure Vela prototype source and emit unqualified Gallina definitions"),
    Command("vela-lsp", "vela.cli.vela_lsp",
            "serve host LSP diagnostics and navigation for unqualified pure Vela over stdio"),
    Command("vela-playground", "vela.cli.vela_playground",
            "serve the unified Vela browser editor with dependent mathematics", lane="guest"),
    Command("vela-parser", "vela.cli.vela_parser",
            "parse Vela, elaborate dependent mathematics and replay proofs", lane="guest"),
)

BY_NAME: dict[str, Command] = {command.name: command for command in COMMANDS}

HELP_FLAGS = frozenset({"--help", "-h"})
LANE_REFERENCE = "tools/generated/command-lanes.md"


def help_declarations() -> frozenset[tuple[str, str]]:
    """Usage-only declarations; operational handlers still need independent fixtures."""
    return frozenset((command.name, flag) for command in COMMANDS
                     for flag in command.host_ok & HELP_FLAGS)
