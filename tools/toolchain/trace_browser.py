# SPDX-License-Identifier: Apache-2.0
"""Explicitly selected Chromium browser qualification of the offline trace viewer."""

import base64
import hashlib
import json
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import cast, override

from toolchain import compiler_trace, trace_html, trace_viewer
from toolchain.jsonutil import unique_object

MAX_EXECUTABLE_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_BYTES = 2_097_152
TIMEOUT_SECONDS = 30
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
type Object = dict[str, object]
_PROBE = """
const svg = document.querySelector('svg');
const bounds = svg.getBoundingClientRect();
const round = n => Math.round(n * 1000) / 1000;
const spans = [...svg.querySelectorAll('g')].map(g => {
  const r = g.querySelector('rect'), b = r.getBoundingClientRect();
  return [g.dataset.name, Number(g.dataset.start), Number(g.dataset.duration),
    Number(g.dataset.depth), round(b.x-bounds.x), round(b.y-bounds.y),
    round(b.width), round(b.height), getComputedStyle(r).fill, g.tabIndex];
});
const counters = [...document.querySelectorAll('#counters tbody tr')].map(
  r => [...r.cells].map(c => c.textContent));
const filter = document.getElementById('filter');
filter.value = 'twice'; filter.dispatchEvent(new Event('input'));
const visible = [...document.querySelectorAll('#spans tbody tr')].filter(r => !r.hidden);
const result = {width: round(bounds.width), spans, counters,
  visible: visible.map(r => r.cells[1].textContent),
  titles: [...svg.querySelectorAll('title')].map(t => t.textContent)};
const pre = document.createElement('pre'); pre.id = 'vela-browser-observation';
pre.textContent = JSON.stringify(result); document.body.append(pre);
"""
EXPECTED: Object = {
    "width": 1000,
    "spans": [
        ["compile", 0, 13, 0, 0, 0, 1000, 36, "rgb(53, 105, 168)", 0],
        ["parse", 2, 5, 1, 153.846, 44, 384.615, 36, "rgb(50, 121, 109)", 0],
        ["checked-parse", 3, 1, 2, 230.769, 88, 76.923, 36, "rgb(128, 92, 166)", 0],
        ["syntax-decode", 5, 1, 2, 384.615, 88, 76.923, 36, "rgb(128, 92, 166)", 0],
        ["elaborate-and-emit", 8, 3, 1, 615.385, 44, 230.769, 36, "rgb(50, 121, 109)", 0],
        ["declaration", 9, 1, 2, 692.308, 88, 76.923, 36, "rgb(128, 92, 166)", 0],
    ],
    "counters": [["source_bytes", "1", "47"], ["gallina_bytes", "12", "48"]],
    "visible": ["declaration: function Twice at 1:26"],
    "titles": [
        "compile | 0 us + 13 us | synchronous host worker 1:1",
        "parse | 2 us + 5 us | synchronous host worker 1:1",
        "checked-parse | 3 us + 1 us | synchronous host worker 1:1",
        "syntax-decode | 5 us + 1 us | synchronous host worker 1:1",
        "elaborate-and-emit | 8 us + 3 us | synchronous host worker 1:1",
        "declaration | 9 us + 1 us | function Twice at 1:26",
    ],
}


def browser_identity(executable: Path, expected: str) -> str:
    if not isinstance(expected, str) or _SHA256.fullmatch(expected) is None:
        raise ValueError("browser SHA-256 must be explicitly selected")
    digest = hashlib.sha256()
    size = 0
    with executable.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_EXECUTABLE_BYTES:
                raise ValueError("browser executable exceeds byte limit")
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("browser executable differs from selected SHA-256")
    return expected


class _Observation(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts: list[str] = []
        self.count = 0

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre" and ("id", "vela-browser-observation") in attrs:
            self.count += 1
            self.active = True

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self.active = False

    @override
    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)


def observe(raw: bytes) -> Object:
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError("browser DOM exceeds byte limit")
    parser = _Observation()
    parser.feed(raw.decode("utf-8", errors="strict"))
    if parser.count != 1:
        raise ValueError("browser did not render the qualification probe")
    result = json.loads("".join(parser.parts), object_pairs_hook=unique_object)
    if json.dumps(result, sort_keys=True, allow_nan=False) != json.dumps(EXPECTED, sort_keys=True):
        raise ValueError("browser layout, styles, filter, source details or counters disagree")
    return cast("Object", result)


def _fixture() -> str:
    artifact = trace_html.render(trace_viewer._fixture(), trace_viewer.SOURCE,
                                 trace_viewer.FIXTURE_PRODUCER)
    probe_hash = base64.b64encode(hashlib.sha256(_PROBE.encode()).digest()).decode()
    artifact = artifact.replace("'; base-uri", f"' 'sha256-{probe_hash}'; base-uri")
    return artifact.replace("</body>", f"<script>{_PROBE}</script></body>")


def harness_identity() -> str:
    modules = (Path(__file__), Path(trace_html.__file__), Path(trace_viewer.__file__),
               Path(compiler_trace.__file__), Path(__file__).parent / "cli" / "vela.py")
    return hashlib.sha256(json.dumps({path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in modules}, sort_keys=True).encode()).hexdigest()


def check_current(executable: Path, expected: str, report: Object) -> None:
    browser_identity(executable, expected)
    if (report["browser_sha256"] != expected or report["viewer_sha256"] != trace_html.identity()
            or report["harness_sha256"] != harness_identity()):
        raise ValueError("browser, viewer or qualification harness changed before publication")


def qualify(executable: Path, expected: str) -> Object:
    """Run a caller-pinned existing Chromium browser; never download or install one."""
    executable = executable.resolve(strict=True)
    browser_identity(executable, expected)
    harness = harness_identity()
    viewer = trace_html.identity()
    artifact = _fixture()
    with tempfile.TemporaryDirectory(prefix="vela-trace-browser-") as temporary:
        root = Path(temporary)
        fixture = root / "timeline.html"
        fixture.write_text(artifact, encoding="utf-8", newline="")
        try:
            completed = subprocess.run([
                str(executable), "--headless", "--disable-gpu", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking", "--disable-extensions",
                "--dump-dom", "--virtual-time-budget=1000", "--window-size=1280,800",
                f"--user-data-dir={root / 'profile'}", fixture.as_uri(),
            ], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=TIMEOUT_SECONDS)
        except subprocess.SubprocessError as error:
            raise ValueError("browser qualification did not finish within its bound") from error
        if (completed.returncode or len(completed.stdout) > MAX_OUTPUT_BYTES
                or len(completed.stderr) > MAX_OUTPUT_BYTES):
            raise ValueError("browser failed or exceeded output bounds")
        observations = observe(completed.stdout)
    browser_identity(executable, expected)
    if harness != harness_identity() or viewer != trace_html.identity():
        raise ValueError("browser harness or viewer changed during qualification")
    report: Object = {
        "schema": 1, "scope": "pure-trace-offline-browser-rendering", "accepted": True,
        "browser_sha256": expected, "harness_sha256": harness, "viewer_sha256": viewer,
        "fixture_sha256": hashlib.sha256(artifact.encode()).hexdigest(),
        "observations": observations,
        "browser_stderr": completed.stderr.decode("utf-8", errors="replace"),
    }
    report["binding_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return report
