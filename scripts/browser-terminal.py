# ruff: noqa: BLE001
# Test-harness boundaries record every exception as a failed check, then continue independent journeys.
"""Headless browser acceptance for the standalone Terminal release.

By default this serves the already-built .cloudflare/site export on a random
loopback port, so the browser can exercise the shipped artifact without
starting or exposing the Python API. Pass --url to audit an existing server.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ROUTES = [
    "hybrid", "lessons", "compare", "overview", "storage", "pv",
    "research", "markets", "forecast", "investment", "pilots", "council",
]
VIEWPORTS = [320, 375, 414, 768, 1024, 1280, 1440, 1920]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Existing exported site URL (default: serve .cloudflare/site locally).")
    parser.add_argument("--site-dir", type=Path, default=ROOT / ".cloudflare" / "site")
    parser.add_argument("--executable", default=os.getenv("CHROMIUM_EXECUTABLE"))
    parser.add_argument("--report", type=Path, default=ROOT / "docs" / "terminal-audit" / "browser-validation.json")
    parser.add_argument("--screenshot-dir", type=Path,
                        help="Optional output directory outside the repository for visual captures.")
    parser.add_argument("--screenshots", action="store_true", help="Save desktop and mobile preview captures beside the report.")
    return parser.parse_args()


def check(state: dict, name: str, ok: bool, detail: str = "") -> None:
    state["checks"].append({"name": name, "status": "passed" if ok else "failed", "detail": detail})
    print(("PASS" if ok else "FAIL"), name, detail)


def fail(state: dict, name: str, detail: str) -> None:
    check(state, name, False, detail)


def expect_selector(page: Page, selector: str, timeout: int = 10_000) -> None:
    page.locator(selector).first.wait_for(state="visible", timeout=timeout)


def navigate(page: Page, route: str, width: int) -> None:
    if page.evaluate("location.hash.slice(1)") == route:
        return
    if page.locator('[data-action="menu"]').is_visible():
        toggle = page.locator('[data-action="menu"]')
        if toggle.get_attribute("aria-expanded") != "true":
            toggle.click()
    page.locator(f'#sidebar .nav-item[data-nav="{route}"]').click()
    page.wait_for_function("route => location.hash.slice(1) === route", arg=route, timeout=5_000)
    page.wait_for_function(
        "route => document.querySelector('#sidebar .nav-item[aria-current=page]')?.dataset.nav === route",
        arg=route,
        timeout=5_000,
    )


def page_overflow(page: Page) -> dict:
    return page.evaluate("""() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
      rootDelta: document.documentElement.scrollWidth - innerWidth,
      bodyDelta: document.body.scrollWidth - innerWidth
    })""")


def offscreen_controls(page: Page) -> dict:
    return page.evaluate("""() => {
      const clipped = [], scrollArea = [];
      for (const el of document.querySelectorAll('a[href],button,input:not([type="file"]),label:has(input[type="file"]),select,textarea,[tabindex]:not([tabindex="-1"])')) {
        if (!el.getClientRects().length || !el.checkVisibility() || el.closest('dialog:not([open])')) continue;
        const sidebar = el.closest('#sidebar');
        if (sidebar && !sidebar.classList.contains('mobile-open')) continue;
        if (el.closest('[aria-hidden="true"]')) continue;
        const box = el.getBoundingClientRect();
        if (box.width <= 0 || (box.left >= -1 && box.right <= innerWidth + 1)) continue;
        let parent = el.parentElement, scrollHost = null;
        while (parent && parent !== document.documentElement) {
          const style = getComputedStyle(parent);
          if (parent.scrollWidth > parent.clientWidth + 1 && ['auto', 'scroll'].includes(style.overflowX)) {
            scrollHost = parent.id ? `#${parent.id}` : `.${String(parent.className || parent.tagName).trim().split(/\\s+/).join('.')}`;
            break;
          }
          parent = parent.parentElement;
        }
        const item = {tag: el.matches('label:has(input[type="file"])') ? 'label-file-picker' : el.tagName.toLowerCase(), id: el.id || null,
          label: (el.getAttribute('aria-label') || el.innerText || el.getAttribute('name') || el.title || '').trim().slice(0, 100),
          left: Math.round(box.left), right: Math.round(box.right), scrollHost};
        (scrollHost ? scrollArea : clipped).push(item);
      }
      return {clipped, scrollArea};
    }""")


def rendered_text_contrasts(page: Page, selector: str) -> list[float]:
    return page.evaluate("""selector => {
              const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
              const ctx = canvas.getContext('2d', {willReadFrequently:true});
              const luminance = colour => {
                ctx.clearRect(0,0,1,1); ctx.fillStyle = colour; ctx.fillRect(0,0,1,1);
                const rgb = [...ctx.getImageData(0,0,1,1).data].slice(0,3).map(c => {
                  const v=c/255; return v<=0.04045 ? v/12.92 : ((v+0.055)/1.055)**2.4;
                });
                return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
              };
              return [...document.querySelectorAll(selector)].map(b => {
                const style=getComputedStyle(b), ink=luminance(style.color), paper=luminance(style.backgroundColor);
                return (Math.max(ink,paper)+0.05)/(Math.min(ink,paper)+0.05);
              });
            }""", selector)


def metrics_are_finite(page: Page) -> tuple[bool, str]:
    result = page.evaluate("""() => {
      const run = HF.terminalSolve(HF.terminalDefaults());
      const numbers = [...Object.values(run.metrics), ...run.rows.flatMap(row => Object.values(row))];
      return {finite: numbers.every(Number.isFinite), rows: run.rows.length,
        busResidual: run.metrics.maxBusResidualKw, socResidual: run.metrics.maxSocResidualKwh};
    }""")
    return result["finite"] and result["rows"] == 24 and max(result["busResidual"], result["socResidual"]) <= 1e-9, json.dumps(result)


def current_cost(page: Page) -> float:
    text = page.locator("#terminal-root .terminal-stats dd").nth(0).inner_text().strip()
    return float(text.replace(",", ""))


def download_text(page: Page, selector: str, destination: Path) -> tuple[str, str]:
    with page.expect_download(timeout=15_000) as result:
        page.locator(selector).click()
    download = result.value
    download.save_as(str(destination))
    return download.suggested_filename, destination.read_text(encoding="utf-8")


def open_command_palette(page: Page, prefix: str) -> None:
    page.keyboard.press("Control+k")
    page.locator("#modal[open]").wait_for(timeout=5_000)
    search = page.locator("#command-search")
    search.fill(prefix)


def select_command(page: Page, command: str) -> None:
    page.locator(f'[data-terminal-command="{command}"]').click()
    page.locator("#modal[open]").wait_for(state="hidden", timeout=5_000)
    page.locator("#terminal-root").wait_for(timeout=5_000)


def audit_accessibility(page: Page, axe_path: Path, route: str, width: int, state: dict) -> None:
    try:
        if not page.evaluate("Boolean(window.axe)"):
            # Run audit instrumentation through automation, without adding an
            # inline script element that the production CSP correctly blocks.
            page.evaluate(axe_path.read_text(encoding="utf-8"))
        result = page.evaluate("""async () => {
          const report = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}});
          return {violations: report.violations.map(v => ({id: v.id, impact: v.impact,
            description: v.help, nodes: v.nodes.length,
            examples: v.nodes.slice(0, 3).map(n => ({target: n.target, summary: n.failureSummary?.slice(0, 500)}))})),
            passes: report.passes.length, incomplete: report.incomplete.length};
        }""")
        state["accessibility"].append({"route": route, "width": width, **result})
        summary = [{"id": violation["id"], "impact": violation["impact"], "nodes": violation["nodes"]}
                   for violation in result["violations"]]
        check(state, f"{route} axe-core check at {width}px", not summary, json.dumps(summary))
    except Exception as exc:  # Keep the rest of the acceptance journeys independent.
        state["accessibilityErrors"].append({"route": route, "width": width, "error": str(exc)})
        fail(state, f"{route} axe-core check at {width}px", str(exc))


def exercise_terminal(page: Page, state: dict, scratch: Path, screenshot_dir: Path | None) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    navigate(page, "compare", 1440)
    page.locator("#terminal-root").wait_for(state="visible")
    check(state, "terminal workbench is integrated into Scenario compare",
          page.locator("#terminal-heading").inner_text().strip() == "Parametric energy workbench"
          and page.locator(".page-intro").count() == 1,
          "new workbench and original comparison view coexist")

    finite, detail = metrics_are_finite(page)
    check(state, "default 24-step browser calculation is finite and conservative", finite, detail)

    baseline = current_cost(page)
    page.locator('[data-terminal-action="pin"]').click()
    check(state, "completed reference can be pinned as run A",
          "pinned as baseline A" in page.locator("#terminal-notice").inner_text())

    page.locator('#terminal-run-form [name="importPrice"]').fill("0.35")
    dirty_state = page.evaluate("""() => ({
      status: document.querySelector('#terminal-status')?.textContent,
      pinDisabled: document.querySelector('[data-terminal-action="pin"]')?.disabled,
      exportDisabled: [...document.querySelectorAll('[data-terminal-export]')].every(b => b.disabled),
      sweepDisabled: document.querySelector('#terminal-sweep-form button')?.disabled
    })""")
    check(state, "input edits mark the displayed result stale and disable pin/export/sweep",
          dirty_state["pinDisabled"] and dirty_state["exportDisabled"] and dirty_state["sweepDisabled"]
          and "inputs changed" in dirty_state["status"].lower(), json.dumps(dirty_state))

    page.locator('#terminal-run-form button[type="submit"]').click()
    page.wait_for_function("document.querySelector('#terminal-status')?.textContent === 'CONVERGED'", timeout=5_000)
    candidate = current_cost(page)
    check(state, "candidate B reruns against changed import tariff",
          abs(candidate - baseline) > 0.01, f"A={baseline}; B={candidate}")

    page.locator('[data-terminal-action="diff"]').click()
    page.locator("#terminal-delta .terminal-diff").wait_for(timeout=5_000)
    diff = page.locator("#terminal-delta table tbody tr").filter(has_text="Period cost [EUR]")
    diff_values = diff.locator("td").all_inner_texts() if diff.count() == 1 else []
    check(state, "run A versus B diff includes the changed period cost", len(diff_values) == 4
          and abs(float(diff_values[2].replace(",", ""))) > 0.01
          and abs(float(diff_values[1].replace(",", "")) - candidate) < 0.02,
          " | ".join(diff_values))

    page.locator('#terminal-sweep-form button[type="submit"]').click()
    page.locator("#terminal-sweep-results .terminal-matrix").wait_for(timeout=10_000)
    count = page.locator("#terminal-sweep-results [data-terminal-point]").count()
    check(state, "default two-axis sweep renders all 49 selectable matrix points", count == 49, f"points={count}")
    sweep_contrast = rendered_text_contrasts(page, "#terminal-sweep-results [data-terminal-point]")
    check(state, "all 49 Terminal matrix values clear 4.5:1 rendered contrast",
          len(sweep_contrast) == 49 and min(sweep_contrast) >= 4.5,
          f"cells={len(sweep_contrast)}; min={min(sweep_contrast) if sweep_contrast else None}")
    if count:
        page.locator('#terminal-sweep-results [data-terminal-point="0"]').click()
        selected = page.locator("#terminal-sweep-results [role=status]").inner_text()
        check(state, "matrix point selection exposes exact coordinates and metrics",
              "Selected case 1" in selected and "terminal SOC" in selected, selected[:300])
        if screenshot_dir:
            page.locator("#terminal-sweep-results").scroll_into_view_if_needed()
            image_path = screenshot_dir / "terminal-sweep-results.png"
            page.screenshot(path=str(image_path), full_page=False, animations="disabled")
            state["screenshots"].append(str(image_path))

    prior_matrix_count = page.locator("#terminal-sweep-results .terminal-matrix").count()
    page.locator('#terminal-sweep-form [name="lower"]').fill("18")
    page.locator('#terminal-sweep-form [name="upper"]').fill("2")
    page.locator('#terminal-sweep-form button[type="submit"]').click()
    page.locator("#terminal-notice").get_by_text("lower bound must be less than upper bound", exact=False).wait_for(timeout=5_000)
    page.wait_for_function("!document.querySelector('#terminal-sweep-results .terminal-matrix')", timeout=5_000)
    remaining_matrix_count = page.locator("#terminal-sweep-results .terminal-matrix").count()
    remaining_point_count = page.locator("#terminal-sweep-results [data-terminal-point]").count()
    check(state, "invalid lower-greater-than-upper sweep clears the previous valid matrix",
          prior_matrix_count == 1 and count == 49 and remaining_matrix_count == 0 and remaining_point_count == 0,
          f"before={prior_matrix_count} matrix/{count} points; after={remaining_matrix_count} matrix/{remaining_point_count} points")

    page.locator('#terminal-sweep-form [name="lower"]').fill("100001")
    page.locator('#terminal-sweep-form [name="upper"]').fill("100002")
    page.locator('#terminal-sweep-form button[type="submit"]').click()
    page.locator("#terminal-notice").get_by_text("pvKw sweep bounds", exact=False).wait_for(timeout=5_000)
    check(state, "out-of-range sweep bounds are rejected visibly",
          "at most 100000" in page.locator("#terminal-notice").inner_text(),
          page.locator("#terminal-notice").inner_text())

    page.locator('#terminal-sweep-form [name="lower"]').fill("0")
    page.locator('#terminal-sweep-form [name="upper"]').fill("10")
    page.locator('#terminal-sweep-form [name="scale"]').select_option("log")
    page.locator('#terminal-sweep-form button[type="submit"]').click()
    page.locator("#terminal-notice").get_by_text("positive lower and upper bounds", exact=False).wait_for(timeout=5_000)
    check(state, "invalid logarithmic sweep reports positive-bound constraint",
          "Log sweeps require positive" in page.locator("#terminal-notice").inner_text(),
          page.locator("#terminal-notice").inner_text())

    page.locator('#terminal-sweep-form [name="lower"]').fill("2")
    page.locator('#terminal-sweep-form [name="upper"]').fill("18")
    page.locator('#terminal-sweep-form [name="scale"]').select_option("linear")

    export_records = {}
    for kind, suffix in (("json", ".json"), ("csv", ".csv"), ("md", ".md")):
        filename, content = download_text(page, f'[data-terminal-export="{kind}"]', scratch / f"run{suffix}")
        export_records[kind] = {"filename": filename, "bytes": len(content.encode("utf-8"))}
        if kind == "json":
            manifest = json.loads(content)
            check(state, "JSON run export contains a SHA-256 manifest and 24 rows",
                  bool(re.fullmatch(r"[a-f0-9]{64}", manifest.get("stateSha256", "")))
                  and len(manifest["payload"]["run"]["rows"]) == 24,
                  f"hash={manifest.get('stateSha256')}; rows={len(manifest['payload']['run']['rows'])}")
        elif kind == "csv":
            columns = set(next(csv.reader(content.splitlines()[:1]))) if content.splitlines() else set()
            metadata_columns = {"dataKind", "status", "flags", "warnings"}
            check(state, "CSV run export contains inputs, residuals, and 24 hourly records",
                  "stateSha256" in columns and "busResidualKw" in columns and metadata_columns <= columns
                  and "synthetic" in content and "CONVERGED" in content and len(content.splitlines()) == 25,
                  f"bytes={len(content.encode('utf-8'))}; lines={len(content.splitlines())}; metadata={sorted(metadata_columns & columns)}")
        else:
            check(state, "Markdown run export includes model limits, metrics, and integrity payload",
                  "SHA-256:" in content and "## Flags and limits" in content and "Complete integrity payload" in content
                  and "may differ" in content,
                  f"bytes={len(content.encode('utf-8'))}")
    state["exports"] = export_records

    corrupt = json.loads((scratch / "run.json").read_text(encoding="utf-8"))
    corrupt["payload"]["run"]["rows"][0]["loadKw"] += 1
    corrupt_path = scratch / "corrupt.json"
    corrupt_path.write_text(json.dumps(corrupt), encoding="utf-8")
    with page.expect_file_chooser() as chooser_event:
        page.locator('[data-terminal-action="import"]').click()
    chooser_event.value.set_files(str(corrupt_path))
    page.locator("#toast").get_by_text("Manifest hash does not match", exact=False).wait_for(timeout=5_000)
    check(state, "manifest import rejects output tampering", "Manifest hash does not match" in page.locator("#toast").inner_text())

    with page.expect_file_chooser() as chooser_event:
        page.locator('[data-terminal-action="import"]').click()
    chooser_event.value.set_files(str(scratch / "run.json"))
    page.locator("#terminal-notice").get_by_text("Manifest integrity verified", exact=False).wait_for(timeout=5_000)
    imported_notice = page.locator("#terminal-notice").inner_text()
    exported_inputs = json.loads((scratch / "run.json").read_text(encoding="utf-8"))["payload"]["run"]["inputs"]
    imported_inputs = page.locator('#terminal-run-form [name]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.name,Number(e.value)]))")
    check(state, "valid JSON manifest imports after digest check and deterministic rerun",
          "all 24 steps reproduced locally" in imported_notice and "does not establish authorship or scientific validity" in imported_notice
          and imported_inputs == exported_inputs, imported_notice)

    open_command_palette(page, ":")
    check(state, "Ctrl+K palette lists terminal commands", page.locator('[data-terminal-command=":preset island"]').count() == 1)
    select_command(page, ":preset island")
    grid_value = page.locator('#terminal-run-form [name="gridKw"]').input_value()
    check(state, "palette preset island performs a real zero-grid calculation", grid_value == "0", f"gridKw={grid_value}")

    open_command_palette(page, ":pin")
    select_command(page, ":pin")
    check(state, "palette :pin pins the completed preset", "pinned as baseline A" in page.locator("#terminal-notice").inner_text())

    open_command_palette(page, ":diff")
    select_command(page, ":diff")
    check(state, "palette :diff opens the existing compare view", page.locator("#terminal-delta").is_visible())

    page.evaluate("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:':',bubbles:true}))")
    page.locator("#command-search").wait_for(timeout=5_000)
    check(state, "colon opener opens command palette with command filtering", page.locator("#command-search").input_value() == ":")
    page.locator("#command-search").fill(":export json")
    with page.expect_download(timeout=15_000) as download_event:
        page.locator('[data-terminal-command=":export json"]').click()
    download_event.value.save_as(str(scratch / "palette.json"))
    palette_manifest = json.loads((scratch / "palette.json").read_text(encoding="utf-8"))
    check(state, "colon-opened command palette exports a verifiable JSON manifest",
          bool(re.fullmatch(r"[a-f0-9]{64}", palette_manifest.get("stateSha256", ""))))

    share_url = page.locator('[data-terminal-action="share"]')
    share_url.click()
    page.wait_for_url(re.compile(r'.*[?&]terminal=.*#compare$'), wait_until='commit', timeout=10_000)
    shared = page.url
    parsed = urlparse(shared)
    check(state, "share action writes exact terminal inputs to query state", "terminal=" in parsed.query and parsed.fragment == "compare", shared[:500])
    query_page = page.context.new_page()
    query_errors: list[str] = []
    query_page.on("pageerror", lambda error: query_errors.append(str(error)))
    query_page.goto(shared, wait_until="load")
    query_page.locator("#terminal-root").wait_for(timeout=10_000)
    query_grid = query_page.locator('#terminal-run-form [name="gridKw"]').input_value()
    query_state_ok = query_grid == "0" and "query inputs reproduced" in query_page.locator("#terminal-notice").inner_text()
    check(state, "shared query reload reproduces candidate inputs in a new browser tab", query_state_ok, f"gridKw={query_grid}")
    query_page.close()
    check(state, "query-state reload has no page exceptions", not query_errors, "; ".join(query_errors[:3]))


def exercise_legacy_compare(page: Page, state: dict) -> None:
    page.goto(page.url.split("?")[0].split("#")[0] + "#hybrid", wait_until="load")
    page.locator("#hybrid-config").wait_for()
    page.locator('#architecture-library button[data-system="hospital-island"]').click()
    page.wait_for_function("document.querySelector('#hybrid-system')?.value === 'hospital-island'", timeout=5_000)
    system_card = page.locator('#architecture-library button[data-system="hospital-island"]')
    card_state = system_card.evaluate("el => ({pressed: el.getAttribute('aria-pressed'), height: el.getBoundingClientRect().height})")
    page.locator("#hybrid-system").select_option("remote-triad")
    page.wait_for_function("document.querySelector('#hybrid-system')?.value === 'remote-triad'", timeout=5_000)
    selector_changed = page.locator("#hybrid-system").input_value() == "remote-triad"
    page.locator("#hybrid-system").select_option("hospital-island")
    page.locator('#hybrid-output .hybrid-metrics').wait_for(timeout=5_000)
    check(state, "architecture card and preset selector restore the bundled baseline",
          card_state["pressed"] == "true" and card_state["height"] >= 44 and selector_changed
          and page.locator("#run-hybrid").is_disabled() and "Bundled Python preset" in page.locator("#hybrid-output").inner_text(),
          json.dumps({**card_state, "presetSelectorChanged": selector_changed}))
    page.locator('[data-hybrid-action="pin"]').click()
    page.locator('[data-scenario="outage-4h"]').click()
    page.locator('#hybrid-output .hybrid-metrics').wait_for(timeout=5_000)
    page.locator('[data-hybrid-action="pin"]').click()
    navigate(page, "compare", page.viewport_size["width"])
    page.locator(".comparison-table").wait_for(timeout=5_000)
    check(state, "original hybrid comparison still pins and shows two bundled cases",
          "2 pinned runs" in page.locator(".compare-panel").inner_text()
          and page.locator(".comparison-table thead th").count() == 3,
          page.locator(".compare-panel").inner_text()[:350])
    page.locator('[data-hybrid-action="clear-compare"]').click()
    page.locator(".comparison-empty").wait_for(timeout=5_000)


def main() -> int:
    args = parse_args()
    report_path: Path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    state: dict = {
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "site": args.url or "local .cloudflare/site export",
        "routes": ROUTES,
        "viewports": VIEWPORTS,
        "checks": [],
        "accessibility": [],
        "accessibilityErrors": [],
        "pageErrors": [],
        "consoleErrors": [],
        "sameOriginConsoleErrors": [],
        "externalConsoleErrors": [],
        "failedRequests": [],
        "sameOriginFailedRequests": [],
        "externalFailedRequests": [],
        "badResponses": [],
        "bodyContentOverhangs": [],
        "clippedControls": [],
        "scrollAreaControls": [],
        "screenshots": [],
        "limits": [
            "Accessibility results are automated axe-core findings, not WCAG certification or a screen-reader audit.",
            "The export is a static snapshot: new API calculations and native hosting/CSP behavior are not exercised.",
            "Only the Chromium build supplied by the audit environment is exercised.",
        ],
    }

    server: ThreadingHTTPServer | None = None
    if args.url:
        base_url = args.url.rstrip("/")
        if base_url.endswith('/run'):
            base_url = base_url[:-4]
    else:
        site_dir = args.site_dir.resolve()
        if not site_dir.is_dir():
            raise SystemExit(f"Static export not found: {site_dir}. Build it before running this browser audit.")
        handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base_url = f"http://127.0.0.1:{server.server_port}"
    page_url = base_url + "/run/"

    axe_path = ROOT / "apps" / "web" / "node_modules" / "axe-core" / "axe.min.js"
    if not axe_path.is_file():
        state["accessibilityErrors"].append({"error": f"axe-core not found: {axe_path}"})
    output_dir = report_path.parent
    screenshot_dir = args.screenshot_dir.resolve() if args.screenshot_dir else output_dir
    if args.screenshots:
        screenshot_dir.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser: Browser = pw.chromium.launch(
                executable_path=args.executable,
                headless=True,
                args=["--no-sandbox"] if args.executable else [],
            )
            context = browser.new_context(ignore_https_errors=page_url.startswith('https://127.0.0.1:'), viewport={"width": 1440, "height": 1000}, accept_downloads=True,
                                          reduced_motion="reduce")
            page = context.new_page()
            origin = urlparse(page_url).netloc
            page.on("pageerror", lambda error: state["pageErrors"].append(str(error)))
            def record_console_error(message: Any) -> None:
                if message.type != "error":
                    return
                location = message.location or {}
                error_origin = urlparse(location.get("url", "")).netloc
                entry = {"type": message.type, "text": message.text[:500],
                         "url": location.get("url", ""), "origin": error_origin,
                         "line": location.get("lineNumber", 0), "column": location.get("columnNumber", 0)}
                state["consoleErrors"].append(entry)
                destination = "sameOriginConsoleErrors" if error_origin == origin else "externalConsoleErrors"
                state[destination].append(entry)

            def record_failed_request(request: Any) -> None:
                request_origin = urlparse(request.url).netloc
                entry = {"url": request.url, "origin": request_origin, "failure": request.failure,
                         "sameOrigin": request_origin == origin}
                state["failedRequests"].append(entry)
                destination = "sameOriginFailedRequests" if request_origin == origin else "externalFailedRequests"
                state[destination].append(entry)

            page.on("console", record_console_error)
            page.on("requestfailed", record_failed_request)
            page.on("response", lambda response: state["badResponses"].append({"url": response.url, "status": response.status})
                    if urlparse(response.url).netloc == origin and response.status >= 400 else None)
            page.goto(page_url + "#compare", wait_until="load", timeout=30_000)
            page.locator("#terminal-root").wait_for(timeout=15_000)
            check(state, "export route loads the browser app and integrated workbench", page.locator("#terminal-root").count() == 1)

            # Rasterize computed colours to sRGB so OKLCH inherits are measured,
            # including count text that an automated accessibility scan can miss.
            count_contrast = rendered_text_contrasts(page, "#champion-toolbar .workbench-actions b")
            check(state, "toolbar count readouts clear 4.5:1 rendered contrast",
                  len(count_contrast) == 2 and min(count_contrast) >= 4.5, json.dumps(count_contrast))

            navigate(page, "pv", 1440)
            page.locator('[data-study-select="pv-sensitivity"]').click()
            page.locator('[data-pv-cell="80"]').wait_for()
            pv_contrast = rendered_text_contrasts(page, "[data-pv-cell]")
            check(state, "all 81 original PV matrix values clear 4.5:1 rendered contrast",
                  len(pv_contrast) == 81 and min(pv_contrast) >= 4.5,
                  f"cells={len(pv_contrast)}; min={min(pv_contrast) if pv_contrast else None}")
            navigate(page, "compare", 1440)

            # Exercise actual navigation in every view at every requested width.
            for width in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": 900})
                for route in ROUTES:
                    try:
                        navigate(page, route, width)
                        overflow = page_overflow(page)
                        ok = overflow["document"] <= width
                        if overflow["body"] > width and ok:
                            state["bodyContentOverhangs"].append({"route": route, **overflow})
                        check(state, f"{route} has no page-level horizontal overflow at {width}px", ok,
                              "" if ok else json.dumps(overflow))
                        offscreen = offscreen_controls(page)
                        state["clippedControls"].extend({"route": route, "width": width, **item}
                                                       for item in offscreen["clipped"])
                        state["scrollAreaControls"].extend({"route": route, "width": width, **item}
                                                           for item in offscreen["scrollArea"])
                        check(state, f"{route} has no clipped interactive controls at {width}px",
                              not offscreen["clipped"], json.dumps(offscreen["clipped"][:5]))
                    except Exception as exc:
                        fail(state, f"{route} navigation at {width}px", str(exc))
                if width in (375, 1440):
                    for route in ROUTES:
                        try:
                            navigate(page, route, width)
                            if axe_path.is_file():
                                audit_accessibility(page, axe_path, route, width, state)
                        except Exception as exc:
                            state["accessibilityErrors"].append({"route": route, "width": width, "error": str(exc)})

            if args.screenshots:
                page.set_viewport_size({"width": 1440, "height": 1000})
                navigate(page, "compare", 1440)
                desktop = screenshot_dir / "terminal-desktop.png"
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=str(desktop), full_page=False, animations="disabled")
                state["screenshots"].append(str(desktop))
                page.set_viewport_size({"width": 375, "height": 844})
                navigate(page, "compare", 375)
                page.screenshot(path=str(screenshot_dir / "terminal-mobile.png"), full_page=False, animations="disabled")
                state["screenshots"].append(str(screenshot_dir / "terminal-mobile.png"))

            with TemporaryDirectory(prefix="helioforge-terminal-audit-") as tmp:
                scratch = Path(tmp)
                exercise_legacy_compare(page, state)
                exercise_terminal(page, state, scratch, screenshot_dir if args.screenshots else None)

            check(state, "no uncaught page exceptions", not state["pageErrors"], "; ".join(state["pageErrors"][:5]))
            check(state, "no same-origin console errors", not state["sameOriginConsoleErrors"],
                  json.dumps(state["sameOriginConsoleErrors"][:5]))
            check(state, "no failed same-origin resource requests", not state["sameOriginFailedRequests"],
                  json.dumps(state["sameOriginFailedRequests"][:5]))
            check(state, "no same-origin 4xx/5xx responses", not state["badResponses"], json.dumps(state["badResponses"][:5]))

            browser_version = browser.version
            state["browser"] = {"name": "Chromium", "version": browser_version}
            context.close()
            browser.close()
    except Exception as exc:
        fail(state, "browser harness completed all independent journeys", f"{type(exc).__name__}: {exc}")
    finally:
        if server:
            server.shutdown()
            server.server_close()

    state["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["summary"] = {
        "passed": sum(item["status"] == "passed" for item in state["checks"]),
        "failed": sum(item["status"] == "failed" for item in state["checks"]),
        "axeViewRuns": len(state["accessibility"]),
        "axeViolations": sum(len(item["violations"]) for item in state["accessibility"]),
        "axeExecutionErrors": len(state["accessibilityErrors"]),
    }
    report_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(state["summary"], indent=2))
    print(f"Report: {report_path}")
    return 1 if state["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
