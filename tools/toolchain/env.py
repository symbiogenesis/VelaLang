# SPDX-License-Identifier: Apache-2.0
"""Guest build environment, opam switch configuration, and per-lane build paths.

Proof-environment settings shared with static and proof checks live in
[proofenv.py](proofenv.py) and are re-exported here.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from toolchain import proofenv

# Canonical model build directory name under a lane's build root.
MODEL_TREE = "verifiedos-model"

# Re-export proof and worktree environment helpers from [proofenv.py](proofenv.py).
CROSS_OS_FILESYSTEMS = proofenv.CROSS_OS_FILESYSTEMS
VOLATILE_FILESYSTEMS = proofenv.VOLATILE_FILESYSTEMS
OCAML_VERSION = proofenv.OCAML_VERSION
lane_of = proofenv.lane_of
build_root = proofenv.build_root
lane_dir = proofenv.lane_dir
lane_root = proofenv.lane_root
filesystem = proofenv.filesystem
_env_path = proofenv._env_path

# Default model profile configuration path relative to the model directory.
PROFILE_CONFIG = "config/verifiedos.json"

SAIL_VERSION = "0.20.3"
SAIL_SWITCH = f"verifiedos-sail-{SAIL_VERSION}-ocaml-{OCAML_VERSION}"

# Opam environment variables that auto-confirm interactive prompts.
OPAM_ANSWERS: tuple[str, ...] = ("OPAMYES", "OPAMCONFIRMLEVEL")


def declining_environment() -> dict[str, str]:
    """Return `os.environ` without `OPAM_ANSWERS` so read-only `opam` invocations never auto-confirm root upgrades."""
    return {key: value for key, value in os.environ.items()
            if key.upper() not in OPAM_ANSWERS}


@dataclass
class Environment:
    """Checkout, lane, and simulator build-path metadata."""

    root: Path
    model: Path
    build_root: Path
    lane: str

    @property
    def lane_root(self) -> Path:
        """Build directory root for this checkout's lane (`build_root` on the primary worktree)."""
        return lane_dir(self.build_root, self.lane)

    @property
    def build_dir(self) -> Path:
        """Canonical model build directory for this lane (or `VOS_BUILD_DIR` when set)."""
        return _env_path("VOS_BUILD_DIR", self.lane_root / MODEL_TREE)

    @property
    def simulator(self) -> Path:
        return self.build_dir / "c_emulator" / "sail_riscv_sim"

    @property
    def profile(self) -> Path:
        """Frozen profile configuration passed to the simulator."""
        candidate = self.model / PROFILE_CONFIG
        if not candidate.is_file():
            built = self.build_dir / PROFILE_CONFIG
            if built.is_file():
                return built
        return candidate


def load(*, toolchain: bool = True) -> Environment:
    """Return checkout and simulator build-path metadata."""
    if sys.platform == "win32" and toolchain:
        raise SystemExit("the model loops run inside WSL: "
                         "python tools/run.py model <command>")
    tools = Path(__file__).resolve().parent.parent
    root = _env_path("VOS_ROOT", tools.parent)
    return Environment(
        root=root,
        model=_env_path("VOS_MODEL", root / "model"),
        build_root=build_root(),
        lane=lane_of(root),
    )
