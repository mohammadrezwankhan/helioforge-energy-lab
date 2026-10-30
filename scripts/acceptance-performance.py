"""Retained desktop-lab runs, including viewport/CPU/network emulation.

These are not physical phone measurements, field INP, or field p75 evidence.
"""
import hashlib
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("HELIOFORGE_EVIDENCE_DIR", ROOT / "docs/remediation-20261028"))
OUT.mkdir(parents=True, exist_ok=True)
URL = os.environ.get("HELIOFORGE_ACCEPTANCE_URL", "http://127.0.0.1:4189/run/")
SITE = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site"))
LOCAL_TARGET = urlsplit(URL).hostname in {"127.0.0.1", "localhost", "::1"}
report = {"schema": "helioforge.performance.lab.v1", "started_at": datetime.now(timezone.utc).isoformat(),
          "environment": platform.platform(), "artifact_sha256": hashlib.sha256((SITE / "run/index.html").read_bytes()).hexdigest(),
          "physical_device": False, "field_p75": None, "field_INP": None,
          "target_url": URL,
          "scope": ("Local gzip server" if LOCAL_TARGET else "Public HTTPS target over the host's network") + ", desktop CPU; new browser context for cold, same-context reload for warm. Other host workloads were not controlled. No field metrics or real-device claim.",
          "runs": []}
init = """window.audit={lcp:null,cls:0,longTasks:[],frames:0};
for(const type of ['largest-contentful-paint','layout-shift','longtask'])try{
new PerformanceObserver(list=>{for(const e of list.getEntries()){
if(type==='largest-contentful-paint')audit.lcp=e.startTime;
if(type==='layout-shift'&&!e.hadRecentInput)audit.cls+=e.value;
if(type==='longtask')audit.longTasks.push({start:e.startTime,duration:e.duration});
}}).observe({type,buffered:true});}catch{}
const raf=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=cb=>raf(t=>{audit.frames++;cb(t)});
"""

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    report["browser_version"] = browser.version
    for profile in ["desktop", "phone_viewport_constrained_emulation"]:
        for repetition in range(1, 4):
            context = browser.new_context(ignore_https_errors=URL.startswith('https://127.0.0.1:'), viewport={"width": 1440 if profile == "desktop" else 390, "height": 1000 if profile == "desktop" else 844},
                                          reduced_motion="no-preference")
            context.add_init_script(init)
            page = context.new_page()
            cdp = context.new_cdp_session(page)
            cdp.send("Network.enable")
            cdp.send("Performance.enable")
            if profile != "desktop":
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
                    "downloadThroughput": 1_600_000 / 8, "uploadThroughput": 750_000 / 8})
            for cache in ["cold", "warm"]:
                run = {"profile": profile, "cache": cache, "repetition": repetition, "status": "FAIL",
                       "cpu_multiplier": 1 if profile == "desktop" else 4, "network": ("loopback" if LOCAL_TARGET else "unthrottled host network") if profile == "desktop" else "CDP 150 ms latency, 1.6 Mbps down, 0.75 Mbps up"}
                try:
                    before_metrics = {m['name']: m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
                    if cache == "cold":
                        cdp.send("Network.clearBrowserCache")
                    start = time.perf_counter()
                    if cache == "cold":
                        response = page.goto(URL + "#hybrid", wait_until="load", timeout=120000)
                    else:
                        # A hash-only goto has no network response or new navigation timing.
                        page.evaluate("history.replaceState(null,'','#hybrid')")
                        response = page.reload(wait_until="load", timeout=120000)
                    page.locator("#main-content h1").wait_for()
                    page.wait_for_timeout(1200)
                    run["wall_load_ms"] = (time.perf_counter() - start) * 1000
                    run["metrics"] = page.evaluate("""()=>({ ...audit,navigation:performance.getEntriesByType('navigation').map(n=>({domInteractive:n.domInteractive,domContentLoaded:n.domContentLoadedEventEnd,load:n.loadEventEnd,encodedBodySize:n.encodedBodySize,decodedBodySize:n.decodedBodySize,transferSize:n.transferSize})),heap:performance.memory?{used:performance.memory.usedJSHeapSize,total:performance.memory.totalJSHeapSize}:null})""")
                    after_metrics = {m['name']: m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
                    run['main_thread'] = {name: max(0, after_metrics.get(name, 0)-before_metrics.get(name, 0))*1000
                        for name in ['ScriptDuration', 'TaskDuration', 'LayoutDuration', 'RecalcStyleDuration']}
                    run['main_thread']['scope'] = 'CDP cumulative-duration deltas in milliseconds; ScriptDuration is execution, not a separate parser-only or field INP measurement.'
                    run['lab_lcp_budget_ms'] = 2500
                    run['lab_lcp_budget_status'] = 'PASS' if run['metrics']['lcp'] is not None and run['metrics']['lcp'] <= 2500 else 'FAIL'
                    run["status"] = "PASS" if response and response.ok else "FAIL"
                    before = page.evaluate("audit.frames")
                    page.wait_for_timeout(1000)
                    run["idle_animation_callbacks_1s"] = page.evaluate("audit.frames") - before
                    interactions = []
                    def measure(label, operation):
                        start = time.perf_counter()
                        try:
                            operation()
                            page.evaluate("()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
                            interactions.append({"name": label, "status": "PASS", "automation_wall_ms": (time.perf_counter()-start)*1000,
                                                 "scope": "automation-to-two-frames latency; includes scrolling and Playwright waits, not INP"})
                        except Exception as exc:
                            interactions.append({"name": label, "status": "FAIL", "actual": repr(exc)})
                    measure("architecture search", lambda: page.locator('#hybrid-search').fill('hospital'))
                    measure("architecture change", lambda: page.locator('#hybrid-system').select_option(index=1))
                    page.evaluate("location.hash='compare'")
                    page.locator('#terminal-run-form').wait_for()
                    measure("pin baseline", lambda: page.locator('[data-terminal-action="pin"]').click())
                    measure("Terminal input edit", lambda: page.locator('#terminal-run-form input[name="loadKw"]').fill('9'))
                    measure("candidate calculation", lambda: page.locator('#terminal-run-form button[type="submit"]').click())
                    def sweep():
                        page.locator('#terminal-sweep-form button[type="submit"]').click()
                        page.locator('.terminal-matrix').wait_for()
                    measure("49-case sweep", sweep)
                    measure("comparison", lambda: page.locator('[data-terminal-action="diff"]').click())
                    def export():
                        with page.expect_download() as download:
                            page.locator('[data-terminal-export="json"]').click()
                        assert download.value.failure() is None
                    measure("manifest export", export)
                    run["interactions"] = interactions
                except Exception as exc:
                    run["actual"] = repr(exc)
                report["runs"].append(run)
                (OUT / "performance-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(profile, cache, repetition, run["status"], flush=True)
            context.close()
    browser.close()
report["finished_at"] = datetime.now(timezone.utc).isoformat()
report["summary"] = {"executed": len(report["runs"]), "passed": sum(r["status"] == "PASS" for r in report["runs"]),
                     "failed": sum(r["status"] == "FAIL" for r in report["runs"]), "real_device_acceptance": "BLOCKED", "field_metrics": "BLOCKED"}
(OUT / "performance-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report["summary"]))
