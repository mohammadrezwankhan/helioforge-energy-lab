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


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RUNS = 12
EXPECTED_INTERACTIONS = 96
LCP_BUDGET_MS = 2500
MAIN_THREAD_METRICS = (
    "ScriptDuration",
    "TaskDuration",
    "LayoutDuration",
    "RecalcStyleDuration",
)


def is_http_200(status):
    return status == 200


def runtime_response_evidence(status, url, body, expected_sha256):
    actual_sha256 = hashlib.sha256(body).hexdigest() if body is not None else None
    return {
        "target_http_status": status,
        "runtime_response_url": url,
        "runtime_response_sha256": actual_sha256,
        "runtime_sha256_matches_site": (
            is_http_200(status) and actual_sha256 is not None and actual_sha256 == expected_sha256
        ),
    }


def current_document_main_thread_metrics(metrics):
    """Convert the current document's CDP duration snapshot to milliseconds."""
    values = {metric["name"]: metric["value"] for metric in metrics}
    return {
        name: values[name] * 1000 if name in values else None
        for name in MAIN_THREAD_METRICS
    }


def functional_evidence_passes(run):
    return (
        is_http_200(run.get("target_http_status"))
        and run.get("runtime_sha256_matches_site") is True
        and not run.get("page_errors")
        and not run.get("actual")
        and all(interaction.get("status") == "PASS" for interaction in run.get("interactions", []))
    )


def summarize_runs(runs, expected_runs=EXPECTED_RUNS, expected_interactions=EXPECTED_INTERACTIONS):
    functional_failures = sum(
        run.get("status") != "PASS" or not functional_evidence_passes(run) for run in runs
    )
    lcp_budget_failures = sum(run.get("lab_lcp_budget_status") != "PASS" for run in runs)
    failed_runs = sum(
        run.get("status") != "PASS"
        or not functional_evidence_passes(run)
        or run.get("lab_lcp_budget_status") != "PASS"
        for run in runs
    )
    interaction_count = sum(len(run.get("interactions", [])) for run in runs)
    run_count_complete = len(runs) == expected_runs
    interaction_count_complete = interaction_count == expected_interactions
    acceptance_passes = (
        bool(runs)
        and failed_runs == 0
        and run_count_complete
        and interaction_count_complete
    )
    return {
        "executed": len(runs),
        "expected_runs": expected_runs,
        "run_count_complete": run_count_complete,
        "interactions_executed": interaction_count,
        "expected_interactions": expected_interactions,
        "interaction_count_complete": interaction_count_complete,
        "passed": len(runs) - failed_runs,
        "failed": failed_runs,
        "functional_failures": functional_failures,
        "lcp_budget_failures": lcp_budget_failures,
        "acceptance_status": "PASS" if acceptance_passes else "FAIL",
        "real_device_acceptance": "BLOCKED",
        "field_metrics": "BLOCKED",
    }


def acceptance_exit_code(summary):
    return 0 if summary.get("acceptance_status") == "PASS" else 1


def build_report(url, site, started_at=None):
    artifact_path = site / "run" / "index.html"
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    local_target = urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"}
    return {
        "schema": "helioforge.performance.lab.v1",
        "started_at": started_at or datetime.now(timezone.utc).isoformat(),
        "environment": platform.platform(),
        "artifact_sha256": artifact_sha256,
        "site_runtime_path": str(artifact_path.resolve()),
        "physical_device": False,
        "field_p75": None,
        "field_INP": None,
        "target_url": url,
        "scope": (
            ("Local gzip server" if local_target else "Public HTTPS target over the host's network")
            + ", desktop CPU; new browser context for cold, same-context reload for warm. "
            + "CDP Performance.getMetrics current-value snapshots are taken after each document load; "
            + "navigation resets these duration counters, so the current document snapshot is converted "
            + "to milliseconds without subtracting the previous document. Other host workloads were not "
            + "controlled. No field metrics or real-device claim."
        ),
        "runs": [],
    }


def write_report(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "performance-results.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


def register_page_error_listener(page, run):
    def handle_page_error(error):
        run["page_errors"].append(repr(error))

    page.on("pageerror", handle_page_error)
    return handle_page_error


def remove_page_error_listener(page, handler):
    page.remove_listener("pageerror", handler)


INIT_SCRIPT = """window.audit={lcp:null,lcp_element:null,cls:0,longTasks:[],frames:0};
for(const type of ['largest-contentful-paint','layout-shift','longtask'])try{
new PerformanceObserver(list=>{for(const e of list.getEntries()){
if(type==='largest-contentful-paint'){
audit.lcp=e.startTime;
const element=e.element;
const classes=element?(element.getAttribute('class')||'').split(/\\s+/).filter(Boolean):[];
audit.lcp_element=element?{tag:element.localName||null,id:element.id||null,classes,
selector:(element.localName||'')+(element.id?'#'+element.id:'')+classes.map(c=>'.'+c).join(''),
url:e.url||null,size:e.size,renderTime:e.renderTime,loadTime:e.loadTime}:null;
}
if(type==='layout-shift'&&!e.hadRecentInput)audit.cls+=e.value;
if(type==='longtask')audit.longTasks.push({start:e.startTime,duration:e.duration});
}}).observe({type,buffered:true});}catch{}
const raf=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=cb=>raf(t=>{audit.frames++;cb(t)});
"""


def main():
    from playwright.sync_api import sync_playwright

    url = os.environ.get("HELIOFORGE_ACCEPTANCE_URL", "http://127.0.0.1:4189/run/")
    site = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site"))
    output_dir = Path(
        os.environ.get(
            "HELIOFORGE_EVIDENCE_DIR",
            ROOT / ".cloudflare/performance-evidence",
        )
    )
    report = build_report(url, site)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        report["browser_version"] = browser.version
        for profile in ["desktop", "phone_viewport_constrained_emulation"]:
            for repetition in range(1, 4):
                context = browser.new_context(
                    ignore_https_errors=url.startswith("https://127.0.0.1:"),
                    viewport={
                        "width": 1440 if profile == "desktop" else 390,
                        "height": 1000 if profile == "desktop" else 844,
                    },
                    reduced_motion="no-preference",
                )
                context.add_init_script(INIT_SCRIPT)
                page = context.new_page()
                cdp = context.new_cdp_session(page)
                cdp.send("Network.enable")
                cdp.send("Performance.enable")
                if profile != "desktop":
                    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                    cdp.send(
                        "Network.emulateNetworkConditions",
                        {
                            "offline": False,
                            "latency": 150,
                            "downloadThroughput": 1_600_000 / 8,
                            "uploadThroughput": 750_000 / 8,
                        },
                    )
                for cache in ["cold", "warm"]:
                    run = {
                        "profile": profile,
                        "cache": cache,
                        "repetition": repetition,
                        "status": "FAIL",
                        "acceptance_status": "FAIL",
                        "cpu_multiplier": 1 if profile == "desktop" else 4,
                        "network": (
                            ("loopback" if urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"} else "unthrottled host network")
                            if profile == "desktop"
                            else "CDP 150 ms latency, 1.6 Mbps down, 0.75 Mbps up"
                        ),
                        "page_errors": [],
                        "interactions": [],
                        "lab_lcp_budget_ms": LCP_BUDGET_MS,
                        "lab_lcp_budget_status": "FAIL",
                        "runtime_sha256_matches_site": False,
                    }
                    page_error_handler = register_page_error_listener(page, run)
                    try:
                        if cache == "cold":
                            cdp.send("Network.clearBrowserCache")
                        start = time.perf_counter()
                        if cache == "cold":
                            response = page.goto(url + "#hybrid", wait_until="load", timeout=120000)
                        else:
                            # A hash-only goto has no network response or new navigation timing.
                            page.evaluate("history.replaceState(null,'','#hybrid')")
                            response = page.reload(wait_until="load", timeout=120000)
                        page.locator("#main-content h1").wait_for()
                        page.wait_for_timeout(1200)
                        run["wall_load_ms"] = (time.perf_counter() - start) * 1000
                        run.update(
                            runtime_response_evidence(
                                response.status if response else None,
                                response.url if response else None,
                                response.body() if response else None,
                                report["artifact_sha256"],
                            )
                        )
                        run["metrics"] = page.evaluate(
                            """()=>({ ...audit,navigation:performance.getEntriesByType('navigation').map(n=>({
                                type:n.type,nextHopProtocol:n.nextHopProtocol,
                                startTime:n.startTime,duration:n.duration,
                                redirectStart:n.redirectStart,redirectEnd:n.redirectEnd,
                                fetchStart:n.fetchStart,domainLookupStart:n.domainLookupStart,
                                domainLookupEnd:n.domainLookupEnd,connectStart:n.connectStart,
                                secureConnectionStart:n.secureConnectionStart,connectEnd:n.connectEnd,
                                requestStart:n.requestStart,responseStart:n.responseStart,
                                responseEnd:n.responseEnd,domInteractive:n.domInteractive,
                                domContentLoaded:n.domContentLoadedEventEnd,domComplete:n.domComplete,
                                load:n.loadEventEnd,encodedBodySize:n.encodedBodySize,
                                decodedBodySize:n.decodedBodySize,transferSize:n.transferSize
                            })),heap:performance.memory?{used:performance.memory.usedJSHeapSize,
                                total:performance.memory.totalJSHeapSize}:null})"""
                        )
                        cdp_metrics = cdp.send("Performance.getMetrics")["metrics"]
                        run["main_thread"] = current_document_main_thread_metrics(cdp_metrics)
                        run["main_thread"]["scope"] = (
                            "CDP Performance.getMetrics current-value snapshot in milliseconds after this document's load; "
                            "the navigation reset means no prior-document subtraction is applied. ScriptDuration is "
                            "JavaScript execution, not parser-only work or field INP."
                        )
                        lcp = run["metrics"].get("lcp")
                        run["lab_lcp_budget_status"] = (
                            "PASS" if lcp is not None and lcp <= LCP_BUDGET_MS else "FAIL"
                        )
                        before = page.evaluate("audit.frames")
                        page.wait_for_timeout(1000)
                        run["idle_animation_callbacks_1s"] = page.evaluate("audit.frames") - before

                        interactions = run["interactions"]

                        def measure(label, operation):
                            interaction_start = time.perf_counter()
                            try:
                                operation()
                                page.evaluate(
                                    "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
                                )
                                interactions.append(
                                    {
                                        "name": label,
                                        "status": "PASS",
                                        "automation_wall_ms": (time.perf_counter() - interaction_start) * 1000,
                                        "scope": "automation-to-two-frames latency; includes scrolling and Playwright waits, not INP",
                                    }
                                )
                            except Exception as exc:
                                interactions.append(
                                    {"name": label, "status": "FAIL", "actual": repr(exc)}
                                )

                        measure("architecture search", lambda: page.locator("#hybrid-search").fill("hospital"))
                        measure(
                            "architecture change",
                            lambda: page.locator("#hybrid-system").select_option(index=1),
                        )
                        page.evaluate("location.hash='compare'")
                        page.locator("#terminal-run-form").wait_for()
                        measure(
                            "pin baseline",
                            lambda: page.locator('[data-terminal-action="pin"]').click(),
                        )
                        measure(
                            "Terminal input edit",
                            lambda: page.locator('#terminal-run-form input[name="loadKw"]').fill("9"),
                        )
                        measure(
                            "candidate calculation",
                            lambda: page.locator('#terminal-run-form button[type="submit"]').click(),
                        )

                        def sweep():
                            page.locator('#terminal-sweep-form button[type="submit"]').click()
                            page.locator(".terminal-matrix").wait_for()

                        measure("49-case sweep", sweep)
                        measure(
                            "comparison",
                            lambda: page.locator('[data-terminal-action="diff"]').click(),
                        )

                        def export():
                            with page.expect_download() as download:
                                page.locator('[data-terminal-export="json"]').click()
                            assert download.value.failure() is None

                        measure("manifest export", export)
                        run["status"] = "PASS" if functional_evidence_passes(run) else "FAIL"
                        run["acceptance_status"] = (
                            "PASS"
                            if run["status"] == "PASS" and run["lab_lcp_budget_status"] == "PASS"
                            else "FAIL"
                        )
                    except Exception as exc:
                        run["actual"] = repr(exc)
                        run["status"] = "FAIL"
                        run["acceptance_status"] = "FAIL"
                    finally:
                        remove_page_error_listener(page, page_error_handler)
                    report["runs"].append(run)
                    report["summary"] = summarize_runs(report["runs"])
                    write_report(report, output_dir)
                    print(profile, cache, repetition, run["acceptance_status"], flush=True)
                context.close()
        browser.close()

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = summarize_runs(report["runs"])
    write_report(report, output_dir)
    print(json.dumps(report["summary"]))
    return acceptance_exit_code(report["summary"])


if __name__ == "__main__":
    raise SystemExit(main())
