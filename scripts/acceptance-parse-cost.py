#!/usr/bin/env python3
"""Measure only parser/compiler/execution intervals visible in a local Chrome trace.

This diagnostic adds tracing overhead and is deliberately separate from the
primary page-load benchmark. It does not infer parser time from ScriptDuration.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import platform
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = ROOT / ".cloudflare" / "acceptance-20261029-g" / "site"
DEFAULT_URL = "https://127.0.0.1:4200/run/"
DEFAULT_OUTPUT = ROOT / "docs" / "remediation-20261029" / "parse-cost"
EXPECTED_RUNTIME_SHA256 = "8ef56f4df539590392696552c2b10651faf953790d8018c982a949b21e0ccb00"
TRACE_CATEGORIES = [
    "devtools.timeline",
    "v8",
    "v8.compile",
    "disabled-by-default-v8.compile",
    "blink.user_timing",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def union_duration_us(intervals: list[tuple[float, float]]) -> float:
    """Return the union length in microseconds, collapsing nested/overlapping work."""
    valid = sorted((start, end) for start, end in intervals if end > start)
    if not valid:
        return 0.0
    total = 0.0
    start, end = valid[0]
    for next_start, next_end in valid[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


def trace_intervals(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[int, int], str]]:
    """Normalize complete and begin/end events without summing nested intervals."""
    intervals: list[dict[str, Any]] = []
    thread_names: dict[tuple[int, int], str] = {}
    stacks: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        pid, tid = int(event.get("pid", -1)), int(event.get("tid", -1))
        key = (pid, tid)
        phase = event.get("ph")
        name = str(event.get("name", ""))
        if phase == "M" and name == "thread_name":
            args = event.get("args") or {}
            thread_names[key] = str(args.get("name", "unknown"))
            continue
        ts = event.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        if phase == "X":
            dur = event.get("dur")
            if isinstance(dur, (int, float)) and dur > 0:
                intervals.append({"pid": pid, "tid": tid, "name": name, "cat": str(event.get("cat", "")),
                                  "start_us": float(ts), "end_us": float(ts + dur), "phase": "X"})
        elif phase == "B":
            stacks[key].append({"pid": pid, "tid": tid, "name": name, "cat": str(event.get("cat", "")),
                                "start_us": float(ts)})
        elif phase == "E" and stacks[key]:
            stack = stacks[key]
            match = next((i for i in range(len(stack) - 1, -1, -1) if stack[i]["name"] == name), len(stack) - 1)
            begin = stack.pop(match)
            if ts > begin["start_us"]:
                intervals.append({**begin, "end_us": float(ts), "phase": "B/E"})
    return intervals, thread_names


def event_kind(name: str, category: str) -> str | None:
    """Classify explicit V8 parsing/compilation and keep HTML parsing separate."""
    lower, category_lower = name.lower(), category.lower()
    if lower == "parsehtml" and "devtools.timeline" in category_lower:
        return "html_parse"
    if "v8" in category_lower:
        if "parse" in lower or "preparse" in lower:
            return "javascript_parse"
        if "compile" in lower or "compiler" in lower:
            return "javascript_compile"
        if "execute" in lower:
            return "javascript_execution"
    if "devtools.timeline" in category_lower and lower in {"evaluatescript", "functioncall", "runscript", "runmicrotasks"}:
        return "javascript_execution"
    return None


def frame_id_from_trace_event(event: dict[str, Any]) -> str | None:
    args = event.get("args") or {}
    for key in ("data", "beginData", "endData"):
        value = args.get(key)
        if isinstance(value, dict) and value.get("frame"):
            return str(value["frame"])
    return None


def summarize_trace(document: dict[str, Any], target_url: str,
                    target_frame_id: str | None = None, frame_count: int | None = None) -> dict[str, Any]:
    events = document.get("traceEvents")
    if not isinstance(events, list):
        raise ValueError("Trace JSON has no traceEvents array")
    intervals, thread_names = trace_intervals(events)
    durations = [event for event in intervals if event_kind(event["name"], event["cat"])]
    main_candidates = [(key, name) for key, name in thread_names.items()
                       if re.search(r"renderer.*main|main.*renderer", name, flags=re.I)]
    if not main_candidates:
        raise ValueError("Trace contains no renderer main-thread metadata; refusing to guess the main thread")
    counts_by_thread = Counter((e["pid"], e["tid"]) for e in durations)
    target_frames_seen: Counter[str] = Counter()
    for event in events:
        frame_id = frame_id_from_trace_event(event)
        args = event.get("args") or {}
        data = args.get("data") or args.get("beginData") or {}
        event_url = str(data.get("url", "")) if isinstance(data, dict) else ""
        if frame_id and event_url and (event_url == target_url or event_url.startswith(target_url + "#")):
            target_frames_seen[frame_id] += 1
    if target_frame_id is None and target_frames_seen:
        target_frame_id = target_frames_seen.most_common(1)[0][0]
    frame_thread_counts: Counter[tuple[int, int]] = Counter()
    if target_frame_id:
        for event in events:
            if frame_id_from_trace_event(event) == target_frame_id:
                frame_thread_counts[(int(event.get("pid", -1)), int(event.get("tid", -1)))] += 1
    matching = [(key, name) for key, name in main_candidates if frame_thread_counts.get(key, 0)]
    if matching:
        main_key, main_name = max(matching, key=lambda item: frame_thread_counts[item[0]])
        main_thread_basis = "RendererMain metadata and events tagged with the navigated page's main frame"
    else:
        main_key, main_name = max(main_candidates, key=lambda item: counts_by_thread[item[0]])
        main_thread_basis = "RendererMain metadata; selected by relevant event count because no target-frame-tagged event matched"
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_thread_intervals: dict[str, dict[tuple[int, int], list[tuple[float, float]]]] = {
        kind: defaultdict(list) for kind in ("javascript_parse", "javascript_compile", "javascript_parse_compile",
                                             "javascript_execution", "html_parse")
    }
    for event in durations:
        kind = event_kind(event["name"], event["cat"])
        assert kind is not None
        groups[kind].append(event)
        all_thread_intervals[kind][(event["pid"], event["tid"])].append((event["start_us"], event["end_us"]))
        if kind in ("javascript_parse", "javascript_compile"):
            all_thread_intervals["javascript_parse_compile"][(event["pid"], event["tid"])].append((event["start_us"], event["end_us"]))

    def group_result(kind: str, thread: tuple[int, int] | None = None) -> dict[str, Any]:
        selected = [e for e in groups[kind] if thread is None or (e["pid"], e["tid"]) == thread]
        intervals_for_group = [(e["start_us"], e["end_us"]) for e in selected]
        union = union_duration_us(intervals_for_group) / 1000 if intervals_for_group else None
        details = []
        by_name: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
        for event in selected:
            by_name[(event["name"], event["cat"], event["phase"])].append((event["start_us"], event["end_us"]))
        for (name, category, phase), spans in sorted(by_name.items()):
            details.append({"name": name, "category": category, "phase": phase, "event_count": len(spans),
                            "duration_sum_ms": round(sum(end - start for start, end in spans) / 1000, 3),
                            "union_ms": round(union_duration_us(spans) / 1000, 3)})
        return {"union_ms": round(union, 3) if union is not None else None,
                "event_count": len(selected), "event_types": details}

    main = {kind: group_result(kind, main_key) for kind in ("javascript_parse", "javascript_compile", "javascript_execution", "html_parse")}
    main_parse_compile_events = [e for kind in ("javascript_parse", "javascript_compile") for e in groups[kind]
                                 if (e["pid"], e["tid"]) == main_key]
    main["javascript_parse_compile_union"] = {
        "union_ms": round(union_duration_us([(e["start_us"], e["end_us"]) for e in main_parse_compile_events]) / 1000, 3)
        if main_parse_compile_events else None,
        "event_count": len(main_parse_compile_events),
    }
    per_thread = {}
    for kind in ("javascript_parse", "javascript_compile", "javascript_parse_compile", "javascript_execution", "html_parse"):
        thread_unions = {key: union_duration_us(spans) / 1000 for key, spans in all_thread_intervals[kind].items()}
        per_thread[kind] = {
            "sum_of_per_thread_unions_ms": round(sum(thread_unions.values()), 3) if thread_unions else None,
            "thread_count": len(thread_unions),
            "includes_main_thread": main_key in thread_unions,
        }
    observed = [event for kind in ("javascript_parse", "javascript_compile", "javascript_execution", "html_parse")
                for event in groups[kind]]
    return {
        "trace_event_count": len(events),
        "renderer_main_thread": {"pid": main_key[0], "tid": main_key[1], "name": main_name,
                                  "identification": main_thread_basis, "target_frame_id": target_frame_id,
                                  "target_frame_event_count_on_selected_thread": frame_thread_counts.get(main_key, 0),
                                  "trace_target_frames_seen": dict(target_frames_seen), "page_frame_count": frame_count},
        "other_renderer_main_candidates": [{"pid": key[0], "tid": key[1], "name": name} for key, name in main_candidates if key != main_key],
        "main_thread_union_metrics": main,
        "all_thread_union_metrics": per_thread,
        "javascript_event_scope": "V8 parse/compile requires a v8 trace category and a parse/compile event name. ParseHTML in devtools.timeline is reported separately and excluded from JavaScript parse cost. Execution is reported separately from parser/compiler intervals.",
        "parser_only_separation": "Only explicit V8 parse-named event intervals count as JavaScript parser cost. Compile-named events may include parse work; do not add the groups. javascript_parse_compile_union_ms deduplicates overlapping intervals.",
        "observed_event_names": sorted({(event["name"], event["cat"]) for event in observed}),
        "events_on_main_thread": len([e for e in durations if (e["pid"], e["tid"]) == main_key]),
    }


def read_trace_stream(cdp: Any, stream: str) -> bytes:
    chunks: list[bytes] = []
    while True:
        part = cdp.send("IO.read", {"handle": stream, "size": 1024 * 1024})
        data = part.get("data", "")
        chunks.append(__import__("base64").b64decode(data) if part.get("base64Encoded") else data.encode("utf-8"))
        if part.get("eof"):
            break
    cdp.send("IO.close", {"handle": stream})
    return b"".join(chunks)


def capture_profile(browser: Any, profile: str, site: Path, url: str, output: Path) -> dict[str, Any]:
    is_phone = profile == "constrained_phone"
    viewport = {"width": 390 if is_phone else 1440, "height": 844 if is_phone else 1000}
    context = browser.new_context(ignore_https_errors=True, viewport=viewport, device_scale_factor=1,
                                  reduced_motion="no-preference")
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    if is_phone:
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
            "downloadThroughput": 1_600_000 / 8, "uploadThroughput": 750_000 / 8})
    cdp.send("Network.enable")
    cdp.send("Network.clearBrowserCache")
    completion: dict[str, Any] = {}
    tracing_done = __import__("threading").Event()
    cdp.on("Tracing.tracingComplete", lambda params: (completion.update(params), tracing_done.set()))
    started = datetime.now(timezone.utc).isoformat()
    cdp.send("Tracing.start", {
        "traceConfig": {"includedCategories": TRACE_CATEGORIES, "recordMode": "recordUntilFull", "traceBufferSizeInKb": 131072},
        "transferMode": "ReturnAsStream", "streamFormat": "json", "streamCompression": "none",
    })
    navigation_status = None
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    started_perf = time.perf_counter()
    try:
        response = page.goto(url + "#hybrid", wait_until="load", timeout=120000)
        navigation_status = response.status if response else None
        page.locator("#main-content h1").wait_for(timeout=30000)
        page.wait_for_function("""() => Boolean(window.HF && document.querySelector('#hybrid-output') &&
          document.querySelector('#hybrid-output').innerText.length > 80 &&
          !document.querySelector('[data-example-retry]'))""", timeout=60000)
        ready_wall_ms = (time.perf_counter() - started_perf) * 1000
        # A bounded settle makes delayed bundled-example parsing visible without turning
        # this diagnostic into the primary load benchmark.
        page.wait_for_timeout(300)
        frame_tree = cdp.send("Page.getFrameTree")["frameTree"]
        target_frame_id = str(frame_tree["frame"]["id"])
        def count_frames(node: dict[str, Any]) -> int:
            return 1 + sum(count_frames(child) for child in node.get("childFrames", []))
        page_frame_count = count_frames(frame_tree)
    finally:
        cdp.send("Tracing.end")
        deadline = time.time() + 120
        while not tracing_done.is_set() and time.time() < deadline:
            page.wait_for_timeout(25)
        if not tracing_done.is_set():
            context.close()
            raise TimeoutError("Tracing.tracingComplete did not arrive within 120 seconds")
    stream = completion.get("stream")
    if not stream:
        context.close()
        raise RuntimeError("Tracing completed without a stream handle")
    raw = read_trace_stream(cdp, stream)
    trace_path = output / f"{profile}.trace.json"
    trace_path.write_bytes(raw)
    trace_document = json.loads(raw)
    summary = summarize_trace(trace_document, url, target_frame_id, page_frame_count)
    categories_observed = sorted({str(event.get("cat", "")) for event in trace_document.get("traceEvents", [])})
    context.close()
    return {
        "profile": profile,
        "viewport_css_px": viewport,
        "cpu_throttling_rate": 4 if is_phone else 1,
        "network_emulation": {"latency_ms": 150, "download_mbps": 1.6, "upload_mbps": 0.75, "offline": False} if is_phone else None,
        "navigation_status": navigation_status,
        "app_ready_wall_ms_diagnostic_only": round(ready_wall_ms, 3),
        "page_errors": page_errors,
        "target_main_frame": {"id": target_frame_id, "frame_count": page_frame_count},
        "trace_started_at_utc": started,
        "trace_data_loss_occurred": completion.get("dataLossOccurred"),
        "trace_categories_requested": TRACE_CATEGORIES,
        "trace_categories_observed": categories_observed,
        "trace_file": trace_path.name,
        "trace_bytes": len(raw),
        "trace_sha256": sha256(raw),
        **summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.site = args.site.resolve()
    args.output = args.output.resolve()
    parsed = urlparse(args.url)
    try:
        loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if parsed.scheme != "https" or not loopback or parsed.path != "/run/":
        raise SystemExit("Refusing to trace: URL must be HTTPS on a loopback IP at /run/.")
    runtime = args.site / "run" / "index.html"
    if not runtime.is_file():
        raise SystemExit(f"Candidate runtime not found: {runtime}")
    runtime_bytes = runtime.read_bytes()
    runtime_hash = sha256(runtime_bytes)
    if runtime_hash != EXPECTED_RUNTIME_SHA256:
        raise SystemExit(f"Candidate G runtime hash mismatch: expected {EXPECTED_RUNTIME_SHA256}, observed {runtime_hash}")
    args.output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "helioforge.parser-cost-trace.v1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": {"python_executable": sys.executable,
                    "argv": ["scripts/acceptance-parse-cost.py", "--site", str(args.site), "--url", args.url, "--output", str(args.output)]},
        "candidate": {"site": str(args.site), "url": args.url, "runtime_sha256": runtime_hash},
        "host": {"platform": platform.platform(), "python": platform.python_version()},
        "instrumentation": {
            "protocol": "Chrome DevTools Protocol Tracing domain via Playwright CDPSession",
            "transfer_mode": "ReturnAsStream; JSON, uncompressed; original bytes retained as trace files",
            "requested_categories": TRACE_CATEGORIES,
            "duration_units": "Trace event timestamps and durations are microseconds; reported intervals are milliseconds.",
            "aggregation": "Union of overlapping/nested intervals; parse/compile overlap is reported and not added twice in combined union.",
            "ScriptDuration_policy": "Not used as parser cost; it includes JavaScript execution.",
            "profiles": "One instrumented cold navigation per profile; trace overhead makes this supplemental diagnostic, not the primary load benchmark.",
        },
        "runs": [],
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        report["browser"] = {"name": "Chromium", "version": browser.version}
        for profile in ("desktop", "constrained_phone"):
            run = capture_profile(browser, profile, args.site, args.url, args.output)
            run["status"] = "PASS" if run["navigation_status"] == 200 and not run["trace_data_loss_occurred"] and not run["page_errors"] else "FAIL"
            report["runs"].append(run)
            (args.output / "parse-cost-results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            metrics = run["main_thread_union_metrics"]
            print(f"{profile}: {run['status']} trace={run['trace_bytes']} bytes; V8 parse={metrics['javascript_parse']['union_ms']} ms; V8 compile={metrics['javascript_compile']['union_ms']} ms; JS execution={metrics['javascript_execution']['union_ms']} ms", flush=True)
        browser.close()
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = {
        "runs": len(report["runs"]),
        "passed": sum(run["status"] == "PASS" for run in report["runs"]),
        "failed": sum(run["status"] == "FAIL" for run in report["runs"]),
        "parser_only_measurable_runs": sum(run["main_thread_union_metrics"]["javascript_parse"]["union_ms"] is not None for run in report["runs"]),
        "limits": "Trace names/categories are reported verbatim. Missing explicit parse events are null/unmeasured, not zero. Compile-named events may include parse work; no split is inferred.",
    }
    (args.output / "parse-cost-results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
