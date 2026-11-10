# SPDX-License-Identifier: Apache-2.0
"""Offline trace layout, browser observations and source-bound publication controls."""

import copy
import hashlib
import html
import json
import subprocess
import tempfile
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

from tests.harness import Case, ensure
from toolchain import compiler_trace, trace_browser, trace_html, trace_viewer
from toolchain.cli import vela as cli

INDEPENDENT_CASES = True


def _refuses(action: Callable[[], object]) -> None:
    try:
        action()
    except (OSError, ValueError):
        return
    raise AssertionError("invalid or stale trace browser handoff accepted")


def _fixture() -> compiler_trace.Object:
    return trace_viewer._fixture()


def _html_geometry() -> None:
    document = _fixture()
    artifact = trace_html.render(document, trace_viewer.SOURCE, trace_viewer.FIXTURE_PRODUCER)
    ensure('x="153.846154" y="44" width="384.615385"' in artifact,
           "parse span does not preserve the independently chosen 2/13 start and 5/13 width")
    ensure('x="692.307692" y="88" width="76.923077"' in artifact,
           "declaration does not preserve its 9/13 start, 1/13 duration and nesting depth")
    ensure("declaration: function Twice at 1:26" in artifact, "declaration source detail missing")
    ensure("<td>source_bytes</td><td>1</td><td>47</td>" in artifact,
           "source counter changed during rendering")
    ensure("connect-src 'none'" in artifact and "default-src 'none'" in artifact,
           "offline viewer can reach undeclared resources")
    ensure("<code>" + hashlib.sha256(trace_viewer.SOURCE).hexdigest() + "</code>" in artifact,
           "rendered timeline lost exact source identity")
    ensure(trace_html.identity() in artifact, "viewer bytes absent from artifact identity")
    ensure(len(artifact.encode()) <= trace_html.MAX_HTML_BYTES, "HTML exceeds its bound")
    _refuses(lambda: trace_html.render(document, trace_viewer.SOURCE + b" ", trace_viewer.FIXTURE_PRODUCER))
    _refuses(lambda: trace_html.render(document, trace_viewer.SOURCE, "b" * 64))
    with patch.object(trace_html, "MAX_HTML_BYTES", 1):
        _refuses(lambda: trace_html.render(document, trace_viewer.SOURCE, trace_viewer.FIXTURE_PRODUCER))
    recorder = compiler_trace.Recorder(clock=lambda: 0)
    with recorder.span("compile"):
        recorder.counter("source_bytes", len(trace_viewer.SOURCE))
        with recorder.span("parse"):
            with recorder.span("checked-parse"):
                pass
            with recorder.span("syntax-decode"):
                pass
        with recorder.span("elaborate-and-emit"):
            pass
        recorder.counter("gallina_bytes", 0)
    zero = trace_html.render(recorder.export(trace_viewer.SOURCE, trace_viewer.FIXTURE_PRODUCER,
                                             outcome="success"),
                             trace_viewer.SOURCE, trace_viewer.FIXTURE_PRODUCER)
    ensure(zero.count('width="0.500000"') == 5 and "0 microseconds" in zero,
           "zero-time recording lost exact times or minimum focus targets")
    ticks = iter(range(20))
    recorder = compiler_trace.Recorder(max_events=1, clock=ticks.__next__)
    with recorder.span("compile"):
        recorder.counter("source_bytes", len(trace_viewer.SOURCE))
    incomplete = recorder.export(trace_viewer.SOURCE, trace_viewer.FIXTURE_PRODUCER, outcome="cancelled")
    _refuses(lambda: trace_html.render(incomplete, trace_viewer.SOURCE, trace_viewer.FIXTURE_PRODUCER))


def _browser_observation() -> None:
    def dom(value: object) -> bytes:
        return ('<pre id="vela-browser-observation">' + html.escape(json.dumps(value)) + "</pre>").encode()
    ensure(trace_browser.observe(dom(trace_browser.EXPECTED)) == trace_browser.EXPECTED,
           "complete independent browser observations refused")
    for key, value in (("width", 0), ("counters", []), ("visible", []), ("titles", [])):
        changed = copy.deepcopy(trace_browser.EXPECTED)
        changed[key] = value
        _refuses(lambda changed=changed: trace_browser.observe(dom(changed)))
    changed = copy.deepcopy(trace_browser.EXPECTED)
    cast("list[list[object]]", changed["spans"])[1][4] = 154
    _refuses(lambda: trace_browser.observe(dom(changed)))
    changed = copy.deepcopy(trace_browser.EXPECTED)
    cast("list[list[object]]", changed["spans"])[0][1] = False
    _refuses(lambda: trace_browser.observe(dom(changed)))
    for raw in (b"<html>not rendered</html>", b"\xff", dom(trace_browser.EXPECTED) * 2,
                b" " * (trace_browser.MAX_OUTPUT_BYTES + 1)):
        _refuses(lambda raw=raw: trace_browser.observe(raw))


def _browser_process_controls() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-browser-controls-") as temporary:
        executable = Path(temporary) / "browser.exe"
        executable.write_bytes(b"selected existing browser")
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        _refuses(lambda: trace_browser.browser_identity(executable, "bad"))
        _refuses(lambda: trace_browser.browser_identity(executable, "a" * 64))
        with patch.object(trace_browser, "MAX_EXECUTABLE_BYTES", 1):
            _refuses(lambda: trace_browser.browser_identity(executable, digest))
        observed = ('<pre id="vela-browser-observation">' +
                    html.escape(json.dumps(trace_browser.EXPECTED)) + "</pre>").encode()
        completed = subprocess.CompletedProcess([], 0, observed, b"")
        with patch.object(trace_browser.subprocess, "run", return_value=completed) as process:
            report = trace_browser.qualify(executable, digest)
            ensure(report["accepted"] is True and report["browser_sha256"] == digest,
                   "qualification lost browser identity")
            arguments = process.call_args.args[0]
            ensure("--headless" in arguments and "--disable-background-networking" in arguments
                   and arguments[-1].startswith("file:"), "browser handoff is not local and headless")
            trace_browser.check_current(executable, digest, report)
            changed = dict(report, viewer_sha256="a" * 64)
            _refuses(lambda: trace_browser.check_current(executable, digest, changed))
        for result in (subprocess.CompletedProcess([], 1, observed, b"failed"),
                       subprocess.CompletedProcess([], 0, b"<html></html>", b""),
                       subprocess.CompletedProcess([], 0, observed, b"x" * (trace_browser.MAX_OUTPUT_BYTES + 1))):
            with patch.object(trace_browser.subprocess, "run", return_value=result):
                _refuses(lambda: trace_browser.qualify(executable, digest))
        with patch.object(trace_browser.subprocess, "run", side_effect=subprocess.TimeoutExpired("browser", 30)):
            _refuses(lambda: trace_browser.qualify(executable, digest))
        def changed_during_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
            executable.write_bytes(b"changed browser")
            return completed
        with patch.object(trace_browser.subprocess, "run", side_effect=changed_during_run):
            _refuses(lambda: trace_browser.qualify(executable, digest))


def _publication_controls() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-trace-html-") as temporary:
        root = Path(temporary)
        source, trace, output = root / "source.vela", root / "trace.json", root / "timeline.html"
        source.write_bytes(trace_viewer.SOURCE)
        trace.write_text(json.dumps(_fixture()), encoding="utf-8")
        def run(*args: str) -> int:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return cli.main(list(args))
        arguments = ("trace-render", str(trace), "--source", str(source), "--output", str(output))
        with patch.object(compiler_trace, "producer_identity", return_value=trace_viewer.FIXTURE_PRODUCER):
            ensure(run(*arguments) == 0, "offline trace publication failed")
            previous = output.read_bytes()
            ensure(run("trace-render", str(trace), "--source", str(source), "--output", str(source)) == 1,
                   "HTML publication overwrote source")
            ensure(run("trace-render", str(trace), "--source", str(source), "--output", str(trace)) == 1,
                   "HTML publication overwrote recording")
            with patch.object(compiler_trace, "producer_identity",
                              side_effect=[trace_viewer.FIXTURE_PRODUCER, trace_viewer.FIXTURE_PRODUCER, "b" * 64]):
                ensure(run(*arguments) == 1, "late producer change published stale HTML")
            ensure(output.read_bytes() == previous, "late failure replaced the existing timeline")
            source.write_bytes(trace_viewer.SOURCE + b" ")
            ensure(run(*arguments) == 1, "stale source reached browser HTML")
            ensure(output.read_bytes() == previous, "stale-source failure replaced timeline")
            source.write_bytes(trace_viewer.SOURCE)
            trace.write_bytes(b"{}")
            ensure(run(*arguments) == 1, "malformed recording reached browser HTML")
            ensure(output.read_bytes() == previous, "malformed recording replaced timeline")


def _browser_publication() -> None:
    with tempfile.TemporaryDirectory(prefix="vela-browser-publication-") as temporary:
        root = Path(temporary)
        executable, output = root / "browser", root / "receipt.json"
        executable.write_bytes(b"selected browser")
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        report = {"browser_sha256": digest, "viewer_sha256": trace_html.identity(),
                  "harness_sha256": trace_browser.harness_identity(), "accepted": True}
        def run(destination: Path) -> int:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return cli.main(["trace-qualify-browser", "--browser", str(executable),
                                 "--browser-sha256", digest, "--output", str(destination)])
        with patch.object(trace_browser, "qualify", return_value=report):
            ensure(run(output) == 0, "browser receipt publication failed")
            previous = output.read_bytes()
            ensure(run(executable) == 1, "browser receipt overwrote its selected executable")
            with patch.object(trace_browser, "check_current", side_effect=ValueError("late change")):
                ensure(run(output) == 1, "late browser/viewer change published a receipt")
            ensure(output.read_bytes() == previous, "late failure replaced browser receipt")
        for error in (ValueError("bad layout"), KeyboardInterrupt()):
            with patch.object(trace_browser, "qualify", side_effect=error):
                try:
                    status = run(output)
                except KeyboardInterrupt:
                    ensure(isinstance(error, KeyboardInterrupt), "unexpected browser cancellation")
                else:
                    ensure(status == 1, "failed rendering claimed browser qualification")
            ensure(output.read_bytes() == previous, "failure or cancellation replaced browser receipt")


def cases() -> list[Case]:
    return [Case("offline-html-geometry-identities-and-refusals", _html_geometry),
            Case("browser-layout-style-filter-and-source-oracle", _browser_observation),
            Case("browser-executable-process-and-freshness-controls", _browser_process_controls),
            Case("source-bound-atomic-html-publication", _publication_controls),
            Case("browser-receipt-alias-freshness-and-cancellation", _browser_publication)]
