# SPDX-License-Identifier: Apache-2.0
"""Format, lint and check pure Vela, or emit its unqualified Gallina translation."""

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from toolchain import MAX_SOURCE_BYTES, VelaError, compiler_trace, trace_benchmark, translate
from toolchain.atomic import atomic_path
from toolchain.authoring import LINT_CODES, format_source, lint_source
from toolchain.generated_tests import (
    DEFAULT_MAX_EXAMPLES,
    DEFAULT_SEED,
    DEFAULT_STEP_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
    qualify_isolated_campaign,
)
from toolchain.inspection import MAX_EXPORT_BYTES, inspect
from toolchain.protocol_json import decode_message


@dataclass(frozen=True)
class _Source:
    path: Path
    data: bytes
    identity: tuple[int, int, int, int]
    mode: int


def _identity(value: os.stat_result) -> tuple[int, int, int, int]:
    # Windows path stat and descriptor fstat expose different legacy ctime
    # meanings after a write. File identity, size, mtime and exact bytes agree.
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _read_source(path: Path) -> _Source:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("source must be a regular file, not a symbolic link or special file")
    with path.open("rb") as stream:
        if _identity(os.fstat(stream.fileno())) != _identity(before):
            raise OSError("source changed while it was opened")
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if _identity(path.lstat()) != _identity(before):
        raise OSError("source changed while it was read")
    return _Source(path, data, _identity(before), stat.S_IMODE(before.st_mode))


def _unchanged(source: _Source) -> None:
    current = _read_source(source.path)
    if current.identity != source.identity or current.data != source.data:
        raise OSError("source changed during compilation; no pending source rewrite was applied")


def _destination(source: Path, destination: Path) -> None:
    if (source.resolve() == destination.resolve()
            or (destination.exists() and source.samefile(destination))):
        raise OSError("output aliases the input")
    if not destination.parent.is_dir():
        raise OSError("output parent directory does not exist")
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise OSError("output must be a regular file, not a symbolic link or special file")


def _rewrite(source: _Source, formatted: bytes) -> _Source:
    _unchanged(source)
    if formatted == source.data:
        return source
    with atomic_path(source.path) as pending:
        pending.write_bytes(formatted)
        pending.chmod(source.mode)
        _unchanged(source)
    current = _read_source(source.path)
    if current.data != formatted:
        raise OSError("source changed after formatting; generated output was not published")
    return current


def _lint(path: Path, source: bytes, allowed: set[str], denied: set[str], *,
          require_complete: bool = True) -> bool:
    failed = False
    try:
        findings = lint_source(source)
    except VelaError as error:
        if error.kind != "inspection-limit":
            raise
        level = "error" if require_complete else "warning"
        print(f"{path}:{error.line}:{error.column}: {level} lint-unavailable: {error.message}",
              file=sys.stderr)
        return not require_complete
    for finding in findings:
        if finding.code in allowed:
            continue
        is_error = finding.code in denied
        failed |= is_error
        level = "error" if is_error else "warning"
        print(f"{path}:{finding.line}:{finding.column}: {level} {finding.code}: {finding.message}",
              file=sys.stderr)
    return not failed


def _trace(args: argparse.Namespace) -> int:
    source_path = args.source
    try:
        source = _read_source(source_path)
        producer = compiler_trace.producer_identity()
        if args.command == "trace-validate":
            with args.trace.open("rb") as stream:
                data = stream.read(compiler_trace.MAX_TRACE_BYTES + 1)
            compiler_trace.validate(compiler_trace.decode(data), source.data, producer)
            _unchanged(source)
            print("ok vela: complete pure compiler recording; no program timing verdict")
            return 0
        _destination(source_path, args.output)
        recorder = compiler_trace.Recorder(max_events=args.max_events)
        outcome = "success"
        result = 0
        try:
            translate(source.data, trace=recorder)
        except VelaError as error:
            outcome, result = "refused", 1
            print(f"{source_path}:{error.line}:{error.column}: {error.kind}: {error.message}", file=sys.stderr)
        except BaseException as error:
            outcome, result = "cancelled" if isinstance(error, KeyboardInterrupt) else "refused", 1
            raise
        finally:
            document = recorder.export(source.data, producer, outcome=outcome)
            manifest = compiler_trace.validate(document, source.data, producer, require_complete=False)
            _unchanged(source)
            if compiler_trace.producer_identity() != producer:
                raise OSError("compiler inputs changed during recording")
            _destination(source_path, args.output)
            with atomic_path(args.output) as pending:
                pending.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="")
                _unchanged(source)
                if compiler_trace.producer_identity() != producer:
                    raise OSError("compiler inputs changed before trace publication")
    except (OSError, ValueError) as error:
        print(f"{source_path}:1:1: trace: {error}", file=sys.stderr)
        return 1
    else:
        print(f"vela: {args.output}: {outcome}; recording complete: {manifest['complete']}")
        return result


def _producer_unchanged(producer: str, when: str) -> None:
    if compiler_trace.producer_identity() != producer:
        raise OSError(f"compiler inputs changed {when}")


def _trace_benchmark(args: argparse.Namespace) -> int:
    source_path = args.source
    try:
        source = _read_source(source_path)
        producer = compiler_trace.producer_identity()
        if args.command == "trace-benchmark-validate":
            with args.report.open("rb") as stream:
                data = stream.read(trace_benchmark.MAX_REPORT_BYTES + 1)
            trace_benchmark.validate(trace_benchmark.decode(data), source.data, producer)
            _unchanged(source)
            _producer_unchanged(producer, "during benchmark validation")
            print("ok vela: bound tracing comparison; no overhead bound or program timing verdict")
            return 0
        _destination(source_path, args.output)
        report = trace_benchmark.measure(source.data, producer, samples=args.samples,
                                         warmups=args.warmups)
        _unchanged(source)
        _producer_unchanged(producer, "during benchmark")
        _destination(source_path, args.output)
        with atomic_path(args.output) as pending:
            pending.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8", newline="")
            _unchanged(source)
            _producer_unchanged(producer, "before benchmark publication")
    except VelaError as error:
        print(f"{source_path}:{error.line}:{error.column}: {error.kind}: {error.message}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"{source_path}:1:1: trace-benchmark: {error}", file=sys.stderr)
        return 1
    else:
        print(f"vela: {args.output}: {args.samples} tracing comparison pairs")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(suggest_on_error=True, description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "emit", "fmt", "lint"):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        if name == "fmt":
            command.add_argument("--check", action="store_true",
                                 help="report formatting differences without writing")
        else:
            command.add_argument("--allow", action="append", choices=sorted(LINT_CODES), default=[],
                                 help="suppress an optional lint (repeatable)")
            command.add_argument("--deny", action="append", choices=sorted(LINT_CODES), default=[],
                                 help="make an optional lint an error (repeatable)")
        if name in {"check", "emit"}:
            command.add_argument("--format", choices=("write", "check", "off"), default="off",
                                 help="source formatting mode (default: off; write requires explicit opt-in)")
            command.add_argument("--no-lint", action="store_true",
                                 help="disable optional lints; language checks remain required")
        if name == "emit":
            command.add_argument("--output", type=Path,
                                 help="atomically replace a file in an existing directory")
    trace = commands.add_parser("trace", help="record bounded pure compiler phase timings")
    trace.add_argument("source", type=Path)
    trace.add_argument("--output", type=Path, required=True)
    trace.add_argument("--max-events", type=int, default=compiler_trace.MAX_EVENTS)
    trace_validation = commands.add_parser("trace-validate", help="refuse incomplete or stale compiler traces")
    trace_validation.add_argument("trace", type=Path)
    trace_validation.add_argument("--source", type=Path, required=True)
    benchmark = commands.add_parser("trace-benchmark", help="compare plain and traced pure compilation")
    benchmark.add_argument("source", type=Path)
    benchmark.add_argument("--output", type=Path, required=True)
    benchmark.add_argument("--samples", type=int, default=trace_benchmark.DEFAULT_SAMPLES)
    benchmark.add_argument("--warmups", type=int, default=trace_benchmark.DEFAULT_WARMUPS)
    benchmark_validation = commands.add_parser(
        "trace-benchmark-validate", help="refuse stale or inconsistent tracing comparisons")
    benchmark_validation.add_argument("report", type=Path)
    benchmark_validation.add_argument("--source", type=Path, required=True)
    generated = commands.add_parser(
        "generated-tests",
        help="qualify isolated Hypothesis generated development tests (Q25x)",
    )
    generated.add_argument("--seed", type=int, default=DEFAULT_SEED)
    generated.add_argument("--max-examples", type=int, default=DEFAULT_MAX_EXAMPLES)
    generated.add_argument("--step-count", type=int, default=DEFAULT_STEP_COUNT)
    generated.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    inspection = commands.add_parser("inspect", help="export versioned pure compiler facts (Q25ch subset)")
    inspection.add_argument("source", type=Path)
    inspection.add_argument("--query", type=Path,
                            help="read a version-2 bounded query JSON object instead of exporting all facts")
    args = parser.parse_args(argv)
    if args.command in {"trace", "trace-validate"}:
        return _trace(args)
    if args.command in {"trace-benchmark", "trace-benchmark-validate"}:
        return _trace_benchmark(args)
    if args.command == "generated-tests":
        root = Path(__file__).resolve().parents[3]
        try:
            report = qualify_isolated_campaign(
                root,
                seed=args.seed,
                max_examples=args.max_examples,
                step_count=args.step_count,
                timeout_seconds=args.timeout,
            )
        except Exception as error:
            print(f"generated-tests:1:1: campaign: {error}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    allowed = set(getattr(args, "allow", []))
    denied = set(getattr(args, "deny", []))
    if allowed & denied:
        parser.error("a lint cannot be both allowed and denied")
    if getattr(args, "no_lint", False) and (allowed or denied):
        parser.error("--no-lint cannot be combined with --allow or --deny")
    path = Path(args.source)
    try:
        source = _read_source(path)
        if args.command == "inspect":
            snapshot = inspect(source.data, uri=path.resolve().as_uri())
            result = snapshot.export()
            if args.query is not None:
                with args.query.open("rb") as stream:
                    request = stream.read(MAX_EXPORT_BYTES + 1)
                result = snapshot.query(source.data, decode_message(request))
            _unchanged(source)
            encoded = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            print(encoded)
            return 0 if result["status"] == "checked" else 1
        # A failed complete check never rewrites even syntactically valid input.
        translation = translate(source.data)
        if args.command == "lint":
            if not _lint(path, source.data, allowed, denied):
                return 1
            return 0
        formatting = "check" if args.command == "fmt" and args.check else (
            "write" if args.command == "fmt" else args.format)
        candidate = source.data if formatting == "off" else format_source(source.data)
        if formatting == "check" and candidate != source.data:
            print(f"{path}:1:1: format: source differs from Vela style; run vela fmt", file=sys.stderr)
            return 1
        # Fresh emission and lint locations bind exactly the candidate bytes.
        if candidate != source.data:
            translation = translate(candidate)
        if args.command != "fmt" and not args.no_lint:
            # A denied lint keeps the original source unchanged, so its locations
            # must describe that original snapshot, not the uncommitted layout.
            try:
                findings = lint_source(source.data)
            except VelaError as error:
                if error.kind != "inspection-limit":
                    raise
                if denied:
                    _lint(path, source.data, allowed, denied)
                    return 1
                findings = ()
            if any(finding.code in denied for finding in findings):
                _lint(path, source.data, allowed, denied)
                return 1
        destination = args.output if args.command == "emit" else None
        if destination is not None:
            _destination(path, destination)
            # Stage output before changing source, so a preparation failure writes neither.
            with atomic_path(destination) as pending:
                pending.write_text(translation.gallina, encoding="utf-8", newline="")
                _destination(path, destination)
                current = _rewrite(source, candidate)
                _unchanged(current)
        else:
            current = _rewrite(source, candidate)
            _unchanged(current)
        if (args.command != "fmt" and not args.no_lint
                and not _lint(path, candidate, allowed, denied, require_complete=bool(denied))):
            return 1
        if args.command == "check":
            print(f"ok vela: {translation.module}: pure prototype checked; unqualified")
        elif args.command == "emit" and destination is None:
            print(translation.gallina, end="")
        elif args.command == "fmt":
            print(f"ok vela: {translation.module}: style checked" if args.check else
                  f"ok vela: {translation.module}: source formatted")
    except VelaError as error:
        print(f"{path}:{error.line}:{error.column}: {error.kind}: {error.message}",
              file=sys.stderr)
        return 1
    except OSError as error:
        print(f"{path}:1:1: io: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"{path}:1:1: inspection: {error}", file=sys.stderr)
        return 1
    return 0
