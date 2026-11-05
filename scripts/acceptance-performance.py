"""Retained desktop-lab runs, including viewport/CPU/network emulation.

These are not physical phone measurements, field INP, or field p75 evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NotRequired, Protocol, TypedDict
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from playwright.sync_api import Page

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


class CDPMetric(TypedDict):
    name: str
    value: float


class RuntimeEvidence(TypedDict):
    target_http_status: int | None
    runtime_response_url: str | None
    runtime_response_sha256: str | None
    runtime_sha256_matches_site: bool


class Interaction(TypedDict):
    name: str
    status: str
    automation_wall_ms: NotRequired[float]
    scope: NotRequired[str]
    actual: NotRequired[str]


class BrowserMetrics(TypedDict, total=False):
    lcp: float | None
    lcp_element: dict[str, object] | None
    cls: float
    longTasks: list[dict[str, float]]
    frames: int
    navigation: list[dict[str, object]]
    heap: dict[str, float] | None


class PageErrorRun(TypedDict):
    page_errors: list[str]


class PerformanceRun(PageErrorRun, total=False):
    profile: str
    cache: str
    repetition: int
    status: str
    acceptance_status: str
    cpu_multiplier: int
    network: str
    interactions: list[Interaction]
    lab_lcp_budget_ms: int
    lab_lcp_budget_status: str
    runtime_sha256_matches_site: bool
    target_http_status: int | None
    runtime_response_url: str | None
    runtime_response_sha256: str | None
    wall_load_ms: float
    metrics: BrowserMetrics
    main_thread: dict[str, float | str | None]
    idle_animation_callbacks_1s: int
    actual: str


class PerformanceSummary(TypedDict):
    executed: int
    expected_runs: int
    run_count_complete: bool
    interactions_executed: int
    expected_interactions: int
    interaction_count_complete: bool
    passed: int
    failed: int
    functional_failures: int
    lcp_budget_failures: int
    acceptance_status: str
    real_device_acceptance: str
    field_metrics: str


class PerformanceReport(TypedDict):
    schema: str
    started_at: str
    environment: str
    artifact_sha256: str
    site_runtime_path: str
    physical_device: bool
    field_p75: None
    field_INP: None
    target_url: str
    scope: str
    runs: list[PerformanceRun]
    browser_version: NotRequired[str]
    summary: NotRequired[PerformanceSummary]
    finished_at: NotRequired[str]


class PageErrorSource(Protocol):
    def on(self, event_name: Literal["pageerror"], handler: Callable[[BaseException], None], /) -> object: ...

    def remove_listener(
        self, event_name: Literal["pageerror"], handler: Callable[[BaseException], None], /
    ) -> object: ...


def is_http_200(status: object) -> bool:
    return status == 200


def runtime_response_evidence(
    status: int | None, url: str | None, body: bytes | None, expected_sha256: str
) -> RuntimeEvidence:
    actual_sha256 = hashlib.sha256(body).hexdigest() if body is not None else None
    return {
        "target_http_status": status,
        "runtime_response_url": url,
        "runtime_response_sha256": actual_sha256,
        "runtime_sha256_matches_site": (
            is_http_200(status) and actual_sha256 is not None and actual_sha256 == expected_sha256
        ),
    }


def current_document_main_thread_metrics(metrics: Sequence[CDPMetric]) -> dict[str, float | None]:
    """Convert the current document's CDP duration snapshot to milliseconds."""
    values = {metric["name"]: metric["value"] for metric in metrics}
    return {name: values[name] * 1000 if name in values else None for name in MAIN_THREAD_METRICS}


def functional_evidence_passes(run: PerformanceRun) -> bool:
    return (
        is_http_200(run.get("target_http_status"))
        and run.get("runtime_sha256_matches_site") is True
        and not run.get("page_errors")
        and not run.get("actual")
        and all(interaction.get("status") == "PASS" for interaction in run.get("interactions", []))
    )


def summarize_runs(
    runs: Sequence[PerformanceRun],
    expected_runs: int = EXPECTED_RUNS,
    expected_interactions: int = EXPECTED_INTERACTIONS,
) -> PerformanceSummary:
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
    acceptance_passes = bool(runs) and failed_runs == 0 and run_count_complete and interaction_count_complete
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


def acceptance_exit_code(summary: PerformanceSummary) -> int:
    return 0 if summary.get("acceptance_status") == "PASS" else 1


def build_report(url: str, site: Path, started_at: str | None = None) -> PerformanceReport:
    artifact_path = site / "run" / "index.html"
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    local_target = urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"}
    return {
        "schema": "helioforge.performance.lab.v1",
        "started_at": started_at or datetime.now(UTC).isoformat(),
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


def write_report(report: PerformanceReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "performance-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def register_page_error_listener(page: PageErrorSource, run: PageErrorRun) -> Callable[[BaseException], None]:
    def handle_page_error(error: BaseException) -> None:
        run["page_errors"].append(repr(error))

    page.on("pageerror", handle_page_error)
    return handle_page_error


def remove_page_error_listener(page: PageErrorSource, handler: Callable[[BaseException], None]) -> None:
    page.remove_listener("pageerror", handler)


INIT_SCRIPT = (
    "window.audit={lcp:null,lcp_element:null,cls:0,longTasks:[],frames:0};\nfor(const type of ['largest-c"
    "ontentful-paint','layout-shift','longtask'])try{\nnew PerformanceObserver(list=>{for(const e of list"
    ".getEntries()){\nif(type==='largest-contentful-paint'){\naudit.lcp=e.startTime;\nconst element=e.ele"
    "ment;\nconst classes=element?(element.getAttribute('class')||'').split(/\\s+/).filter(Boolean):[];\n"
    "audit.lcp_element=element?{tag:element.localName||null,id:element.id||null,classes,\nselector:(eleme"
    "nt.localName||'')+(element.id?'#'+element.id:'')+classes.map(c=>'.'+c).join(''),\nurl:e.url||null,si"
    "ze:e.size,renderTime:e.renderTime,loadTime:e.loadTime}:null;\n}\nif(type==='layout-shift'&&!e.hadRec"
    "entInput)audit.cls+=e.value;\nif(type==='longtask')audit.longTasks.push({start:e.startTime,duration:"
    "e.duration});\n}}).observe({type,buffered:true});}catch{}\nconst raf=window.requestAnimationFrame.bi"
    "nd(window);window.requestAnimationFrame=cb=>raf(t=>{audit.frames++;cb(t)});\n"
)


def main() -> int:
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
                    run: PerformanceRun = {
                        "profile": profile,
                        "cache": cache,
                        "repetition": repetition,
                        "status": "FAIL",
                        "acceptance_status": "FAIL",
                        "cpu_multiplier": 1 if profile == "desktop" else 4,
                        "network": (
                            (
                                "loopback"
                                if urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"}
                                else "unthrottled host network"
                            )
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
                        runtime_evidence = runtime_response_evidence(
                            response.status if response else None,
                            response.url if response else None,
                            response.body() if response else None,
                            report["artifact_sha256"],
                        )
                        run["target_http_status"] = runtime_evidence["target_http_status"]
                        run["runtime_response_url"] = runtime_evidence["runtime_response_url"]
                        run["runtime_response_sha256"] = runtime_evidence["runtime_response_sha256"]
                        run["runtime_sha256_matches_site"] = runtime_evidence["runtime_sha256_matches_site"]
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
                        main_thread: dict[str, float | str | None] = {
                            **current_document_main_thread_metrics(cdp_metrics)
                        }
                        run["main_thread"] = main_thread
                        main_thread["scope"] = (
                            "CDP Performance.getMetrics current-value snapshot in milliseconds afte"
                            "r this document's load; "
                            "the navigation reset means no prior-document subtraction is applied. S"
                            "criptDuration is "
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

                        def measure(
                            label: str,
                            operation: Callable[[], object],
                            page: Page = page,
                            interactions: list[Interaction] = interactions,
                        ) -> None:
                            interaction_start = time.perf_counter()
                            try:
                                operation()
                                page.evaluate(
                                    "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAn"
                                    "imationFrame(resolve)))"
                                )
                                interactions.append(
                                    {
                                        "name": label,
                                        "status": "PASS",
                                        "automation_wall_ms": (time.perf_counter() - interaction_start)
                                        * 1000,
                                        "scope": (
                                            "automation-to-two-frames latency; includes scrolling and"
                                            " Playwright waits, not INP"
                                        ),
                                    }
                                )
                            except Exception as exc:
                                interactions.append({"name": label, "status": "FAIL", "actual": repr(exc)})

                        def search_architecture(page: Page = page) -> None:
                            page.locator("#hybrid-search").fill("hospital")

                        def change_architecture(page: Page = page) -> None:
                            page.locator("#hybrid-system").select_option(index=1)

                        measure("architecture search", search_architecture)
                        measure("architecture change", change_architecture)
                        page.evaluate("location.hash='compare'")
                        page.locator("#terminal-run-form").wait_for()

                        def pin_baseline(page: Page = page) -> None:
                            page.locator('[data-terminal-action="pin"]').click()

                        def edit_terminal_input(page: Page = page) -> None:
                            page.locator('#terminal-run-form input[name="loadKw"]').fill("9")

                        def calculate_candidate(page: Page = page) -> None:
                            page.locator('#terminal-run-form button[type="submit"]').click()

                        measure("pin baseline", pin_baseline)
                        measure("Terminal input edit", edit_terminal_input)
                        measure("candidate calculation", calculate_candidate)

                        def sweep(page: Page = page) -> None:
                            page.locator('#terminal-sweep-form button[type="submit"]').click()
                            page.locator(".terminal-matrix").wait_for()

                        measure("49-case sweep", sweep)

                        def compare(page: Page = page) -> None:
                            page.locator('[data-terminal-action="diff"]').click()

                        measure("comparison", compare)

                        def export(page: Page = page) -> None:
                            with page.expect_download() as download:
                                page.locator('[data-terminal-export="json"]').click()
                            if download.value.failure() is not None:
                                raise AssertionError

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
                    print(profile, cache, repetition, run["acceptance_status"], flush=True)  # noqa: T201 -- CLI report output.
                context.close()
        browser.close()

    report["finished_at"] = datetime.now(UTC).isoformat()
    report["summary"] = summarize_runs(report["runs"])
    write_report(report, output_dir)
    print(json.dumps(report["summary"]))  # noqa: T201 -- CLI report output.
    return acceptance_exit_code(report["summary"])


if __name__ == "__main__":
    raise SystemExit(main())
