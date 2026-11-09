# SPDX-License-Identifier: Apache-2.0
"""Working-directory independence and external identity controls for Rocq receipts."""

from pathlib import Path

from tests.harness import Case, ensure
from toolchain import elaboration_check as replay


def _directory_identity() -> None:
    header = "Installed / Logical Path / Physical path:\n"
    first = header + "i Corelib /runtime/theories\ni Extra /runtime/plugin\n  <> /qualification-a\n"
    second = header + "i Corelib /runtime/theories\ni Extra /runtime/plugin\n  <> /qualification-b\n"
    before = replay._load_path_identity(first, Path("/qualification-a"))
    after = replay._load_path_identity(second, Path("/qualification-b"))
    ensure(before == after, "qualification directory changed the installed runtime identity")
    ensure(before[0] == {Path("/runtime/theories").resolve(), Path("/runtime/plugin").resolve()},
           "qualification cwd entered the installed runtime inventory")
    ensure(before[1] == header + "i Corelib /runtime/theories\ni Extra /runtime/plugin\n  <> <qualification-directory>\n",
           "normalization changed an external path, logical name or installation marker")
    for changed in (first.replace("Extra", "Other"), first.replace("/runtime/plugin", "/other/plugin"),
                    first.replace("i Extra", "  Extra"), first.replace("  <>", "  Local"),
                    first.replace("/qualification-a", "/qualification-a/nested")):
        ensure(replay._load_path_identity(changed, Path("/qualification-a")) != before,
               "external or logical load-path change was hidden by cwd normalization")
    for malformed in ("", "unsupported\n", header + "  relative /\n", header + "  Extra relative\n"):
        try:
            replay._load_path_identity(malformed, Path("/qualification-a"))
        except ValueError:
            pass
        else:
            raise AssertionError("unsupported load-path listing acquired an identity")


def cases() -> list[Case]:
    return [Case("qualification cwd normalization preserves external load-path identity", _directory_identity)]
