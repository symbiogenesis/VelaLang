# SPDX-License-Identifier: Apache-2.0
"""Source-bound offline HTML timelines for complete pure compiler recordings."""

import base64
import hashlib
import html
from pathlib import Path
from typing import cast

from toolchain import compiler_trace

MAX_HTML_BYTES = 4_194_304
WIDTH = 1000
DEPTH = {"compile": 0, "parse": 1, "checked-parse": 2, "syntax-decode": 2,
         "elaborate-and-emit": 1, "declaration": 2}
_STYLE = """
body{font:16px system-ui,sans-serif;margin:2rem;color:#172132;background:#f4f7fb}
main{max-width:1200px;margin:auto}h1{margin-bottom:.4rem}p{line-height:1.5}
.panel{background:white;border:1px solid #c5d0de;border-radius:8px;padding:1rem;margin:1rem 0}
.scroll{overflow:auto}svg{display:block;width:1000px;height:160px}
rect{fill:#3569a8;stroke:white;stroke-width:1}g[data-depth="1"] rect{fill:#32796d}
g[data-depth="2"] rect{fill:#805ca6}text{fill:white;font-size:12px;pointer-events:none}
g:focus rect,g:hover rect{stroke:#101a29;stroke-width:3}table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:.55rem;border-bottom:1px solid #dce3ed;vertical-align:top}
code{overflow-wrap:anywhere}summary{cursor:pointer}input{padding:.4rem}small{color:#455771}
@media print{body{margin:0;background:white}.scroll{overflow:visible}input{display:none}}
"""
_SCRIPT = """
const query = document.getElementById('filter');
query.addEventListener('input', () => {
  const needle = query.value.toLowerCase();
  document.querySelectorAll('[data-search]').forEach(row => {
    row.hidden = !row.dataset.search.includes(needle);
  });
});
"""


def identity() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def render(document: object, source: bytes, producer: str) -> str:
    """Validate freshness and completeness before creating a portable, network-free view."""
    manifest = compiler_trace.validate(document, source, producer)
    data = cast("compiler_trace.Object", document)
    events = cast("list[compiler_trace.Object]", data["traceEvents"])
    spans = [event for event in events if event["ph"] == "X"]
    duration = cast("int", spans[0]["dur"])
    scale = max(duration, 1)
    figures: list[str] = []
    rows: list[str] = []
    for index, event in enumerate(spans):
        name = cast("str", event["name"])
        depth = DEPTH[name]
        start, elapsed = cast("int", event["ts"]), cast("int", event["dur"])
        details = cast("compiler_trace.Object", event.get("args", {}))
        site = (f"{details['kind']} {details['name']} at {details['line']}:{details['column']}"
                if details else "synchronous host worker 1:1")
        label = html.escape(f"{name}: {site}")
        # Exact times remain visible even when a subpixel duration needs a minimum hit target.
        x, width = start * WIDTH / scale, elapsed * WIDTH / scale
        title = html.escape(f"{name} | {start} us + {elapsed} us | {site}")
        figures.append(
            f'<g tabindex="0" data-name="{name}" data-start="{start}" data-duration="{elapsed}" '
            f'data-depth="{depth}" aria-label="{title}"><title>{title}</title>'
            f'<rect x="{x:.6f}" y="{depth * 44}" width="{max(width, 0.5):.6f}" height="36" />'
            f'<text x="{x + 5:.6f}" y="{depth * 44 + 23}">{html.escape(name)}</text></g>')
        rows.append(f'<tr data-search="{label.lower()}"><td>{index + 1}</td><td>{label}</td>'
                    f'<td>{depth}</td><td>{start}</td><td>{elapsed}</td></tr>')
    counters = [event for event in events if event["ph"] == "C"]
    counter_rows = "".join(
        f'<tr data-counter="{event["name"]}"><td>{event["name"]}</td><td>{event["ts"]}</td>'
        f'<td>{cast("compiler_trace.Object", event["args"])["bytes"]}</td></tr>' for event in counters)
    style_hash = hashlib.sha256(_STYLE.encode()).digest()
    script_hash = hashlib.sha256(_SCRIPT.encode()).digest()
    csp = ("default-src 'none'; style-src 'sha256-" + base64.b64encode(style_hash).decode() +
           "'; script-src 'sha256-" + base64.b64encode(script_hash).decode() +
           "'; base-uri 'none'; form-action 'none'; connect-src 'none'")
    result = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}"><title>Vela compiler timeline</title>
<style>{_STYLE}</style></head><body><main>
<h1>Vela compiler timeline</h1><p>Complete pure compiler recording · {duration} microseconds · worker 1:1</p>
<div class="panel"><p>Focus or hover a span for its exact time and source site. Each row shows a nesting depth.
Zero and subpixel spans retain a minimum half-pixel hit target; the table preserves exact durations.</p>
<div class="scroll"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 160" role="img"
aria-label="Compiler phase timeline">{''.join(figures)}</svg></div></div>
<section class="panel"><h2>Phases and declarations</h2><label>Filter rows <input id="filter" type="search"></label>
<table id="spans"><thead><tr><th>Order</th><th>Work and source</th><th>Depth</th><th>Start (us)</th><th>Duration (us)</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></section>
<section class="panel"><h2>Byte counters</h2><table id="counters"><thead><tr><th>Counter</th><th>Time (us)</th><th>Bytes</th></tr></thead>
<tbody>{counter_rows}</tbody></table></section>
<details class="panel"><summary>Recording identities</summary><p>Source SHA-256 <code>{manifest['source_sha256']}</code></p>
<p>Producer SHA-256 <code>{producer}</code></p><p>Recording SHA-256 <code>{manifest['binding_sha256']}</code></p>
<p>Viewer SHA-256 <code>{identity()}</code></p></details>
<p><small>Times include checked-parser wait. Hashes detect changed data and authenticate no measurement.
This compiler recording supplies no emitted-program timing or proof verdict.</small></p>
</main><script>{_SCRIPT}</script></body></html>
"""
    if len(result.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("trace HTML exceeds byte limit")
    return result
