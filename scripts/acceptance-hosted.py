#!/usr/bin/env python3
"""Targeted acceptance for the hosted, split-data HelioForge browser edition.

This runner inspects the exact built site named by HELIOFORGE_ACCEPTANCE_SITE,
then optionally exercises that site and the self-contained file preview with
Playwright. It does not build, deploy, call providers, or edit application code.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "remediation-20261029"
DEFAULT_SITE = ROOT / ".cloudflare" / "acceptance-20261029-a" / "site"
DEFAULT_URL = "https://127.0.0.1:4193/run/"
STUDY_LEDGER = ROOT / "docs" / "remediation-20261028" / "source-plan" / "study_inventory_59.csv"
COUNCIL_LEDGER = ROOT / "docs" / "remediation-20261028" / "source-plan" / "council_role_test_design.csv"
REQUIRED_STUDY_KEYS = {"study", "model_version", "inputs", "metrics", "series", "table", "data_kind"}


class ScriptSourceCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "script":
            src = dict(attrs).get("src")
            if src:
                self.sources.append(src)


class HostedAppStartupError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json_strict(path: Path) -> Any:
    def reject(value: str) -> None:
        raise ValueError(f"non-JSON numeric constant {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def read_json_bytes(data: bytes) -> Any:
    def reject(value: str) -> None:
        raise ValueError(f"non-JSON numeric constant {value}")
    return json.loads(data.decode("utf-8", errors="strict"), parse_constant=reject)


def outcome(name: str, expected: Any, actual: Any, passed: bool, *, evidence_class: str = "O", detail: str = "") -> dict[str, Any]:
    item = {"check": name, "status": "PASS" if passed else "FAIL", "evidence_class": evidence_class,
            "expected": expected, "actual": actual}
    if detail:
        item["detail"] = detail
    return item


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check_site(site: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    facts_path = site / "app.json"
    runtime_path = site / "run" / "index.html"
    data_index_path = site / "run" / "data-index.json"
    manifest_error: str | None = None
    facts: dict[str, Any] = {}
    index: dict[str, Any] = {}
    runtime_html = ""
    try:
        facts = read_json_strict(facts_path)
        index = read_json_strict(data_index_path)
        runtime_html = runtime_path.read_text(encoding="utf-8")
    except Exception as exc:  # retained as an explicit result, not silently skipped
        manifest_error = f"{type(exc).__name__}: {exc}"

    checks.append(outcome(
        "site_inputs_present_and_parseable",
        {"app_json": True, "runtime_html": True, "data_index": True},
        {"app_json": facts_path.exists(), "runtime_html": runtime_path.exists(), "data_index": data_index_path.exists(), "error": manifest_error},
        manifest_error is None,
    ))
    if manifest_error is not None:
        return checks, {"site": str(site), "site_status": "unreadable"}, {}

    runtime_manifest = facts.get("runtimeDataManifest") or {}
    manifest_bytes = data_index_path.read_bytes()
    hybrid = index.get("hybrid") or {}
    workspaces = index.get("workspaces") or {}
    assets = runtime_manifest.get("assets") or []
    by_path = {asset.get("path"): asset for asset in assets if isinstance(asset, dict)}
    index_refs = {asset.get("path"): asset for section in (hybrid, workspaces) for asset in section.values() if isinstance(asset, dict)}
    index_assignment_present = "globalThis.__HF_DATA_INDEX__" in runtime_html
    collector = ScriptSourceCollector()
    collector.feed(runtime_html)
    runtime_script_sources = collector.sources
    missing_runtime_scripts = []
    for src in runtime_script_sources:
        parsed = urllib.parse.urlparse(src)
        if parsed.scheme or parsed.netloc or parsed.scheme == "data":
            continue
        local_path = urllib.parse.unquote(parsed.path)
        target = (site / local_path.lstrip("/")) if local_path.startswith("/") else (site / "run" / local_path)
        if not target.exists():
            missing_runtime_scripts.append({"src": src, "expected_path": str(target)})
    source_studies = load_csv(STUDY_LEDGER)
    frozen_source = (ROOT / "apps/web/src/roadmap-data.ts").read_text(encoding="utf-8")
    frozen_studies = read_json_bytes(frozen_source.split("STUDY_BUNDLE: StudyBundle = ", 1)[1].rsplit("; }", 1)[0].encode("utf-8"))
    studies_by_page: dict[str, set[str]] = {}
    for row in source_studies:
        studies_by_page.setdefault(row["workspace"], set()).add(row["study_id"])

    checks.append(outcome("runtime_data_schema", "helioforge.hosted-data.v1", index.get("schema"), index.get("schema") == "helioforge.hosted-data.v1"))
    checks.append(outcome("runtime_manifest_sha256", sha256(manifest_bytes), runtime_manifest.get("manifestSha256"), runtime_manifest.get("manifestSha256") == sha256(manifest_bytes)))
    runtime_digest = sha256(runtime_path.read_bytes())
    checks.append(outcome("app_facts_runtime_sha256_matches_exact_runtime", runtime_digest, facts.get("runtimeSha256"), facts.get("runtimeSha256") == runtime_digest))
    counts = {"hybrid_cases": len(hybrid), "workspaces": len(workspaces), "distinct_assets": len(assets), "study_ids_in_source_ledger": len(source_studies)}
    expected_counts = {"hybrid_cases": 285, "workspaces": 12, "distinct_assets": 297, "study_ids_in_source_ledger": 59}
    checks.append(outcome("indexed_hybrid_workspace_study_counts", expected_counts, counts, counts == expected_counts))
    checks.append(outcome("runtime_html_contains_embedded_data_index", True, index_assignment_present, index_assignment_present))
    checks.append(outcome("all_external_runtime_script_files_exist", [], missing_runtime_scripts, not missing_runtime_scripts,
                          detail=f"script src references: {runtime_script_sources}"))
    checks.append(outcome("manifest_asset_set_matches_data_index", sorted(index_refs), sorted(by_path), sorted(index_refs) == sorted(by_path)))
    checks.append(outcome("workspace_keys_match_source_study_inventory",
                          sorted(studies_by_page), sorted(workspaces),
                          sorted(studies_by_page) == sorted(workspaces)))

    bad: list[dict[str, Any]] = []
    checked_refs: set[str] = set()
    for label, mapping, kind in (("hybrid", hybrid, "hybrid"), ("workspace", workspaces, "workspace")):
        for key, ref in mapping.items():
            path_value = ref.get("path", "")
            if path_value in checked_refs:
                continue
            checked_refs.add(path_value)
            target = site / "run" / Path(path_value)
            row = {"kind": kind, "key": key, "path": path_value}
            try:
                data = target.read_bytes()
                value = read_json_bytes(data)
                row.update({"actual_bytes": len(data), "expected_bytes": ref.get("bytes"), "actual_sha256": sha256(data), "expected_sha256": ref.get("sha256")})
                valid = (len(data) == ref.get("bytes") and sha256(data) == ref.get("sha256") and path_value == f"data/{ref.get('sha256')}.json")
                if kind == "hybrid":
                    expected_entry_keys = {"id", "inputs", "result"}
                    valid = valid and isinstance(value, dict) and set(value) == expected_entry_keys
                    inputs = value.get("inputs") if isinstance(value, dict) else None
                    result = value.get("result") if isinstance(value, dict) else None
                    valid = valid and isinstance(value.get("id"), str) and bool(value.get("id"))
                    valid = valid and isinstance(inputs, dict) and f"{inputs.get('system_id')}/{inputs.get('scenario_id')}" == key
                    valid = valid and isinstance(result, dict) and isinstance(result.get("schedule"), list) and bool(result.get("schedule"))
                    row["expected_top_level_keys"] = sorted(expected_entry_keys)
                    row["actual_top_level_keys"] = sorted(value) if isinstance(value, dict) else None
                    row["schedule_rows"] = len(result.get("schedule", [])) if isinstance(result, dict) else None
                else:
                    expected_result_ids = studies_by_page.get(key, set())
                    results = value.get("results") if isinstance(value, dict) else None
                    catalogue = value.get("catalogue") if isinstance(value, dict) else None
                    expected_catalogue = [study for study in frozen_studies["catalogue"] if study["page"] == key]
                    expected_results = {study_id: frozen_studies["results"][study_id] for study_id in expected_result_ids}
                    valid = valid and isinstance(value, dict) and set(value) == {"catalogue", "results"}
                    valid = valid and isinstance(results, dict) and set(results) == expected_result_ids
                    valid = valid and catalogue == expected_catalogue and results == expected_results
                    result_shape_errors = []
                    for study_id, result in (results or {}).items() if isinstance(results, dict) else []:
                        if not isinstance(result, dict) or not REQUIRED_STUDY_KEYS.issubset(result) or result.get("study") != study_id:
                            result_shape_errors.append(study_id)
                        if isinstance(result, dict):
                            for series in result.get("series", []) if isinstance(result.get("series"), list) else []:
                                if not isinstance(series, dict) or not isinstance(series.get("x"), list) or not isinstance(series.get("y"), list) or len(series["x"]) != len(series["y"]):
                                    result_shape_errors.append(study_id + ":series")
                    valid = valid and not result_shape_errors
                    row["expected_result_ids"] = len(expected_result_ids)
                    row["actual_result_ids"] = len(results) if isinstance(results, dict) else None
                    row["catalogue_exactly_matches_frozen_source"] = catalogue == expected_catalogue
                    row["results_exactly_match_frozen_source"] = results == expected_results
                    row["result_shape_errors"] = result_shape_errors
                if not valid:
                    row["error"] = "integrity or expected JSON structure mismatch"
                row["status"] = "PASS" if valid else "FAIL"
            except Exception as exc:
                row.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
            if row["status"] != "PASS":
                bad.append(row)

    chunk_summary = {
        "hybrid_case_entries_checked": len(hybrid), "workspace_entries_checked": len(workspaces),
        "unique_assets_checked": len(checked_refs), "asset_failures": bad,
        "asset_check_status": "PASS" if not bad and len(checked_refs) == len(assets) else "FAIL",
    }
    checks.append(outcome("all_indexed_chunks_byte_hash_and_schema", {"assets": len(assets), "hybrid_cases": 285, "workspaces": 12, "failures": 0},
                          {"assets_checked": len(checked_refs), "hybrid_cases": len(hybrid), "workspaces": len(workspaces), "failures": len(bad)},
                          chunk_summary["asset_check_status"] == "PASS"))

    initial_case = None
    for key, ref in hybrid.items():
        if key.startswith("remote-triad/"):
            try:
                value = read_json_strict(site / "run" / Path(ref["path"]))
                initial_case = {"key": key, "inputs": value.get("inputs"), "path": ref["path"]}
                break
            except Exception:
                pass
    runtime_hash = runtime_digest
    result = {"site": str(site), "site_runtime_sha256": runtime_hash, "data_index_sha256": sha256(manifest_bytes),
              "app_facts_source_revision": facts.get("sourceRevision"), "app_facts_source_tree_dirty": facts.get("sourceTreeDirty"),
              "app_facts_runtime_sha256": facts.get("runtimeSha256"), "counts": counts, "initial_remote_triad_asset": initial_case,
              "asset_summary": chunk_summary}
    return checks, result, index


def check_council_ledger() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, str]]]:
    rows = load_csv(COUNCIL_LEDGER)
    public_rows = [row for row in rows if row.get("mode") == "public_preview"]
    roles = sorted({row.get("role", "") for row in public_rows})
    fixtures = sorted({row.get("evidence_state", "") for row in public_rows})
    counts = {"total_design_rows": len(rows), "public_preview_rows": len(public_rows), "public_roles": len(roles), "public_evidence_states": len(fixtures)}
    checks = [outcome("public_council_source_matrix", {"public_preview_rows": 63, "roles": 9, "evidence_states": 7},
                      {"public_preview_rows": len(public_rows), "roles": len(roles), "evidence_states": len(fixtures)},
                      len(public_rows) == 63 and len(roles) == 9 and len(fixtures) == 7, evidence_class="R",
                      detail="Source design rows are used as read-only matrix labels; they are not treated as injected evidence payloads.")]
    return checks, counts, public_rows


def parse_csv_export(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def outcome_status(checks: list[dict[str, Any]]) -> str:
    return "PASS" if checks and all(item.get("status") == "PASS" for item in checks) else "FAIL"


def run_browser(url: str, offline_file: Path, public_rows: list[dict[str, str]], studies: list[dict[str, str]], expected_index: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    checks: list[dict[str, Any]] = []
    actual: dict[str, Any] = {"url": url, "offline_file": str(offline_file)}
    page_errors: list[str] = []
    browser_console: list[dict[str, str]] = []
    api_requests: list[str] = []
    remote_origin_requests: list[str] = []
    data_responses: list[dict[str, Any]] = []
    script_responses: list[dict[str, Any]] = []
    study_seen: list[str] = []
    workspaces_seen: list[str] = []
    export_hashes: list[str] = []
    offline_http_requests: list[str] = []
    stage = "launch"
    download_dir = tempfile.TemporaryDirectory(prefix="helioforge-hosted-acceptance-")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        local_tls_fixture = urllib.parse.urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"}
        context = browser.new_context(ignore_https_errors=local_tls_fixture, accept_downloads=True, viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("console", lambda msg: browser_console.append({"type": msg.type, "text": msg.text}) if msg.type in {"error", "warning"} else None)
        page.on("request", lambda req: api_requests.append(req.url) if "/api/" in req.url else None)
        local_origin = urllib.parse.urlparse(url).scheme + "://" + urllib.parse.urlparse(url).netloc
        page.on("request", lambda req: remote_origin_requests.append(req.url) if req.url.startswith(("http://", "https://")) and urllib.parse.urlparse(req.url).scheme + "://" + urllib.parse.urlparse(req.url).netloc != local_origin else None)
        page.on("response", lambda response: data_responses.append({"url": response.url, "status": response.status}) if "/run/data/" in response.url else None)
        page.on("response", lambda response: script_responses.append({"url": response.url, "status": response.status}) if response.request.resource_type == "script" else None)

        last_export_at = 0.0

        def paced_download_click(selector: str) -> None:
            nonlocal last_export_at
            # Respect Chromium's ten-downloads-per-second burst limit while retaining
            # real clicks and downloaded bytes. This is a correctness check, not a burst benchmark.
            time.sleep(max(0.0, 0.25 - (time.monotonic() - last_export_at)))
            page.locator(selector).click()
            last_export_at = time.monotonic()

        def click_export(kind: str) -> None:
            nonlocal stage
            stage = f"study {study_id}: {kind} export"
            paced_download_click(f'[data-study-export="{kind}"]')

        actual["export_minimum_interval_seconds"] = 0.25

        def result_labels(key: str) -> dict[str, str | None]:
            return page.evaluate("""key => ({
              system:window.HF.HYBRID_CATALOG.systems.find(x=>x.id===key.split('/')[0])?.name,
              scenario:window.HF.HYBRID_CATALOG.scenarios.find(x=>x.id===key.split('/')[1])?.name
            })""", key)

        def wait_for_exact_example(labels: dict[str, str | None], timeout: int = 60000) -> None:
            page.wait_for_function("""expected => {
              const output=document.querySelector('#hybrid-output')?.innerText||'';
              const loading=[...document.querySelectorAll('.notice')].some(n=>n.innerText.includes('Loading verified example records'));
              return Boolean(expected.system&&expected.scenario&&output.includes(expected.system)&&output.includes(expected.scenario)&&
                !loading&&!document.querySelector('[data-example-retry]'));
            }""", arg=labels, timeout=timeout)

        def hold_example_fetch(path: str) -> None:
            page.evaluate("""path => {
              const original=window.fetch.bind(window);
              const state={started:false,finished:false,response:null,release:null,original};
              window.__hfAcceptanceHeldAsset=state;
              window.fetch=(input,init)=>{
                const raw=typeof input==='string'?input:(input instanceof URL?input.href:input.url);
                const requestUrl=new URL(raw,location.href);
                if(requestUrl.pathname.endsWith(path)&&!state.started){
                  state.started=true;
                  return new Promise((resolve,reject)=>{state.release=()=>original(input,init).then(async response=>{
                    try{
                      const bytes=await response.clone().arrayBuffer();
                      const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
                      state.response={status:response.status,bytes:bytes.byteLength,sha256};state.finished=true;resolve(response);
                    }catch(error){reject(error);}
                  },reject);});
                }
                return original(input,init);
              };
            }""", path)

        def release_example_fetch() -> dict[str, Any] | None:
            page.evaluate("() => window.__hfAcceptanceHeldAsset?.release?.()")
            page.wait_for_function("() => window.__hfAcceptanceHeldAsset?.finished===true", timeout=30000)
            return page.evaluate("() => window.__hfAcceptanceHeldAsset?.response??null")

        def restore_example_fetch() -> None:
            page.evaluate("""() => {
              const state=window.__hfAcceptanceHeldAsset;
              if(state?.original)window.fetch=state.original;
              delete window.__hfAcceptanceHeldAsset;
            }""")

        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=120000)
            stage = "hosted startup"
            page.locator("#app").wait_for(state="attached", timeout=30000)
            startup = page.evaluate("""() => ({namespace_available:Boolean(window.HF&&window.HF.HYBRID_BUNDLE&&window.HF.PAGES),
              scripts:[...document.scripts].map(s=>({src:s.getAttribute('src'),inline_bytes:s.textContent.length})),title:document.title})""")
            if not startup["namespace_available"]:
                actual["hosted_bootstrap_diagnostics"] = {**startup, "script_responses": script_responses, "page_errors": page_errors}
                checks.append(outcome("hosted_application_script_and_namespace_loaded", True, actual["hosted_bootstrap_diagnostics"], False))
                raise HostedAppStartupError("#app exists but the compiled hosted application namespace did not initialize")
            checks.append(outcome("hosted_application_script_and_namespace_loaded", True, startup, True))
            page.wait_for_function("() => Boolean(window.HF && window.HF.HYBRID_BUNDLE && window.HF.PAGES)", timeout=5000)
            checks.append(outcome("hosted_app_navigation", 200, response.status if response else None, bool(response and response.status == 200)))
            embedded_index = page.evaluate("() => window.__HF_DATA_INDEX__")
            checks.append(outcome("browser_embedded_data_index_matches_exact_site_manifest", expected_index,
                                  embedded_index, embedded_index == expected_index))
            bootstrap = page.evaluate("""() => {
              const bundled=window.HF.HYBRID_BUNDLE.cases?.[0];
              const initial=window.HF.initialHybridState();
              return {bundleInputs:bundled?.inputs,initialInputs:initial.inputs,initialResult:initial.result,bootstrapResult:window.HF.HYBRID_EXAMPLE,
                pageCount:window.HF.PAGES.length,studyCount:window.HF.STUDY_BUNDLE.catalogue.length};
            }""")
            bootstrap_match = (bootstrap.get("bundleInputs") == bootstrap.get("initialInputs") and
                               bootstrap.get("initialInputs", {}).get("system_id") == "remote-triad" and
                               bootstrap.get("initialResult") == bootstrap.get("bootstrapResult"))
            checks.append(outcome("bootstrap_remote_triad_matches_initial_inputs_and_result", "remote-triad input and exact bundled result", bootstrap, bootstrap_match))

            initial_cards = page.locator('#hybrid-library-results [data-system]').count()
            atlas_controls = all(page.locator(selector).is_enabled() for selector in
                                 ('#hybrid-search', '#hybrid-family', '#hybrid-topology', '#hybrid-system'))
            page.locator('#architecture-library').scroll_into_view_if_needed()
            page.locator('#hybrid-library-results [data-system]').first.wait_for(state="attached")
            loaded_cards = page.locator('#hybrid-library-results [data-system]').count()
            checks.append(outcome("deferred_architecture_atlas_loads_on_approach",
                                  {"initial_cards": 0, "loaded_cards": 36, "controls_enabled": True},
                                  {"initial_cards": initial_cards, "loaded_cards": loaded_cards, "controls_enabled": atlas_controls},
                                  initial_cards == 0 and loaded_cards == 36 and atlas_controls))

            # Retry a deliberately failed non-bootstrap hybrid case. Interception is local to this exact data URL.
            keys = page.evaluate("() => Object.keys(window.__HF_DATA_INDEX__.hybrid)")
            target_a = next((key for key in keys if not key.startswith("remote-triad/")), None)
            remaining = [key for key in keys if key != target_a and not key.startswith("remote-triad/")]
            target_b = next((key for key in remaining if key.split("/", 1)[0] != target_a.split("/", 1)[0]), None) if target_a else None
            target_c = next((key for key in remaining if key != target_b), None)
            target_d = next((key for key in remaining if key not in {target_b, target_c}), None)
            actual["hybrid_sample_pairs"] = [target_a, target_b, target_c, target_d]
            if not target_a:
                checks.append(outcome("hybrid_nonbootstrap_retry_and_stale_cases", "at least four non-bootstrap pairs", keys[:4], False))
            else:
                ref_a = page.evaluate("key => window.__HF_DATA_INDEX__.hybrid[key]", target_a)
                failed = {"count": 0}
                target_a_url = urllib.parse.urljoin(url, ref_a["path"])
                expected_a = result_labels(target_a)
                def fail_first(route: Any) -> None:
                    failed["count"] += 1
                    if failed["count"] == 1:
                        route.fulfill(status=503, content_type="text/plain", body="controlled acceptance fetch failure")
                    else:
                        route.continue_()
                page.route(target_a_url, fail_first)
                for system, scenario in [target_a.split("/", 1)]:
                    if page.locator(f'[data-system="{system}"]').count():
                        page.locator(f'[data-system="{system}"]').first.click()
                    page.locator(f'[data-scenario="{scenario}"]').first.click()
                page.wait_for_function("() => document.querySelector('[data-example-retry]') !== null", timeout=30000)
                stage = "controlled fetch failure visible"
                retry_before = failed["count"]
                page.locator("[data-example-retry]").click()
                wait_for_exact_example(expected_a)
                stage = "retry recovered"
                target_a_statuses = [response["status"] for response in data_responses if response["url"] == target_a_url]
                target_a_visible = page.locator("#hybrid-output").inner_text()
                checks.append(outcome("controlled_data_failure_retries_and_recovers", {"first_attempt": 503, "retry": 200, "retry_button_removed": True},
                                      {"pair": target_a, "intercepted_requests": failed["count"], "retry_count_after_first": retry_before,
                                       "responses": target_a_statuses, "expected": expected_a,
                                       "result_matches": bool(expected_a["system"] and expected_a["scenario"] and
                                           expected_a["system"] in target_a_visible and expected_a["scenario"] in target_a_visible),
                                       "retry_button_removed": page.locator("[data-example-retry]").count() == 0},
                                      failed["count"] >= 2 and retry_before == 1 and 503 in target_a_statuses and 200 in target_a_statuses and
                                      bool(expected_a["system"] and expected_a["scenario"] and expected_a["system"] in target_a_visible and
                                           expected_a["scenario"] in target_a_visible) and page.locator("[data-example-retry]").count() == 0))
                page.unroute(target_a_url)

                # Delay a second architecture's immutable example across both visible clicks. The scenario is already
                # baseline, so this proves that a same-configuration selection revision cannot strand hydration.
                if target_b and target_c and target_d:
                    ref_b = page.evaluate("key => window.__HF_DATA_INDEX__.hybrid[key]", target_b)
                    expected_b = result_labels(target_b)
                    hold_example_fetch(ref_b["path"])
                    for system, scenario in [target_b.split("/", 1)]:
                        if page.locator(f'[data-system="{system}"]').count():
                            page.locator(f'[data-system="{system}"]').first.click()
                        page.locator(f'[data-scenario="{scenario}"]').first.click()
                    stage = "waiting for delayed same-configuration example"
                    page.wait_for_function("() => window.__hfAcceptanceHeldAsset?.started===true", timeout=30000)
                    selected_before_release = page.evaluate("""() => ({
                      system:document.querySelector('[data-system][aria-pressed="true"]')?.dataset.system,
                      scenario:document.querySelector('[data-scenario][aria-pressed="true"]')?.dataset.scenario
                    })""")
                    held_started = selected_before_release == {"system": target_b.split("/", 1)[0], "scenario": target_b.split("/", 1)[1]}
                    checks.append(outcome("delayed_example_is_held_after_same_configuration_clicks",
                                          {"pair": target_b, "system": target_b.split("/", 1)[0], "scenario": target_b.split("/", 1)[1]},
                                          {"selected_before_release": selected_before_release, "held_started": True}, held_started))
                    stage = "releasing delayed same-configuration example"
                    held_b = release_example_fetch()
                    stage = "waiting for delayed same-configuration result"
                    wait_for_exact_example(expected_b)
                    restore_example_fetch()
                    stage = "nonbootstrap sample loaded"
                    visible_b = page.locator("#hybrid-output").inner_text()
                    checks.append(outcome("nonbootstrap_architecture_and_scenario_result",
                                          {"pair": target_b, "expected": expected_b,
                                           "asset_bytes": ref_b["bytes"], "asset_sha256": ref_b["sha256"]},
                                          {"selected": selected_before_release, "response": held_b,
                                           "result_matches": bool(expected_b["system"] and expected_b["scenario"] and
                                               expected_b["system"] in visible_b and expected_b["scenario"] in visible_b),
                                           "retry_removed": page.locator("[data-example-retry]").count() == 0},
                                          bool(held_b and held_b.get("status") == 200 and held_b.get("bytes") == ref_b["bytes"] and
                                               held_b.get("sha256") == ref_b["sha256"] and expected_b["system"] and expected_b["scenario"] and
                                               expected_b["system"] in visible_b and expected_b["scenario"] in visible_b and
                                               page.locator("[data-example-retry]").count() == 0)))

                    # Reselect the same architecture while a different, exact preset load is held.
                    target_same = page.evaluate("""() => {
                      const bundled=new Set((window.HF.HYBRID_BUNDLE.cases||[]).map(c=>`${c.inputs.system_id}/${c.inputs.scenario_id}`));
                      return Object.keys(window.__HF_DATA_INDEX__.hybrid).find(k=>k.split('/')[1]==='baseline'&&
                        !['remote-triad','utility-pv-ac','utility-pv-dc'].includes(k.split('/')[0])&&!bundled.has(k))||null;
                    }""")
                    if not target_same:
                        checks.append(outcome("same_architecture_reselection_keeps_pending_hydration", "an unbundled baseline case", target_same, False))
                    else:
                        system_same, scenario_same = target_same.split("/", 1)
                        ref_same = page.evaluate("key => window.__HF_DATA_INDEX__.hybrid[key]", target_same)
                        expected_same = result_labels(target_same)
                        hold_example_fetch(ref_same["path"])
                        stage = "selecting same architecture for delayed hydration"
                        if page.locator(f'[data-system="{system_same}"]').count():
                            page.locator(f'[data-system="{system_same}"]').first.click()
                        page.wait_for_function("() => window.__hfAcceptanceHeldAsset?.started===true", timeout=30000)
                        page.locator(f'[data-system="{system_same}"]').first.click()
                        selected_same = page.evaluate("""() => ({
                          system:document.querySelector('[data-system][aria-pressed="true"]')?.dataset.system,
                          scenario:document.querySelector('[data-scenario][aria-pressed="true"]')?.dataset.scenario
                        })""")
                        held_same = release_example_fetch()
                        stage = "waiting for same-architecture delayed result"
                        wait_for_exact_example(expected_same)
                        restore_example_fetch()
                        visible_same = page.locator("#hybrid-output").inner_text()
                        same_visible = bool(expected_same["system"] and expected_same["scenario"] and
                                            expected_same["system"] in visible_same and expected_same["scenario"] in visible_same)
                        checks.append(outcome("same_architecture_reselection_keeps_pending_hydration",
                                              {"pair": target_same, "result": expected_same,
                                               "asset_bytes": ref_same["bytes"], "asset_sha256": ref_same["sha256"]},
                                              {"selected_after_reselection": selected_same, "response": held_same,
                                               "result_matches": same_visible},
                                              bool(held_same and held_same.get("status") == 200 and held_same.get("bytes") == ref_same["bytes"] and
                                                   held_same.get("sha256") == ref_same["sha256"] and same_visible)))

                    # A real number-field edit while a verified example is held must still prevent stale attachment.
                    target_edit = page.evaluate("""same => {
                      const bundled=new Set((window.HF.HYBRID_BUNDLE.cases||[]).map(c=>`${c.inputs.system_id}/${c.inputs.scenario_id}`));
                      return Object.keys(window.__HF_DATA_INDEX__.hybrid).find(k=>k.split('/')[1]==='baseline'&&
                        !['remote-triad','utility-pv-ac','utility-pv-dc'].includes(k.split('/')[0])&&
                        !bundled.has(k)&&k!==same)||null;
                    }""", target_same)
                    if not target_edit:
                        checks.append(outcome("edited_inputs_reject_pending_example", "a second unbundled baseline case", target_edit, False))
                    else:
                        system_edit, scenario_edit = target_edit.split("/", 1)
                        ref_edit = page.evaluate("key => window.__HF_DATA_INDEX__.hybrid[key]", target_edit)
                        expected_edit = result_labels(target_edit)
                        hold_example_fetch(ref_edit["path"])
                        stage = "selecting architecture before real input edit"
                        if page.locator(f'[data-system="{system_edit}"]').count():
                            page.locator(f'[data-system="{system_edit}"]').first.click()
                        page.wait_for_function("() => window.__hfAcceptanceHeldAsset?.started===true", timeout=30000)
                        field = page.locator('#hybrid-config input[type="number"]').first
                        field_before = field.input_value()
                        field_after = str(float(field_before) + 1.0)
                        field.fill(field_after)
                        stage = "releasing example after real input edit"
                        held_edit = release_example_fetch()
                        page.wait_for_function("""key => {
                          const [system,scenario]=key.split('/');
                          return Boolean(window.HF.bundledHybridCase(window.HF.presetInputs(system,scenario)));
                        }""", arg=target_edit, timeout=30000)
                        restore_example_fetch()
                        edited_output = page.locator("#hybrid-output").inner_text()
                        input_retained = field.input_value() == field_after
                        stale_result_visible = bool(expected_edit["system"] and expected_edit["system"] in edited_output)
                        checks.append(outcome("edited_inputs_reject_pending_example",
                                              {"pair": target_edit, "edited_input_value": field_after,
                                               "asset_bytes": ref_edit["bytes"], "asset_sha256": ref_edit["sha256"]},
                                              {"input_value_retained": input_retained, "response": held_edit,
                                               "stale_result_visible": stale_result_visible,
                                               "output_length": len(edited_output)},
                                              bool(input_retained and not stale_result_visible and held_edit and
                                                   held_edit.get("status") == 200 and held_edit.get("bytes") == ref_edit["bytes"] and
                                                   held_edit.get("sha256") == ref_edit["sha256"])))

                    # Hold a fourth, previously unrequested pair so browser cache cannot satisfy it early.
                    ref_d = page.evaluate("key => window.__HF_DATA_INDEX__.hybrid[key]", target_d)
                    hold_path = ref_d["path"]
                    page.evaluate("""path => {
                      const native=window.fetch.bind(window); window.__hfNativeFetch=native;
                      window.__hfHeldStarted=false; window.__hfHeldDone=false; window.__hfRelease=null;
                      window.__hfFetchCalls=[];
                      window.fetch=(input,init)=>{
                        const raw=typeof input==='string'?input:(input instanceof URL?input.href:input.url);
                        const u=new URL(raw,location.href);
                        window.__hfFetchCalls.push(u.pathname);
                        if(u.pathname.endsWith(path) && !window.__hfHeldStarted){
                          window.__hfHeldStarted=true;
                          return new Promise((resolve,reject)=>{window.__hfRelease=()=>native(input,init).then(r=>{window.__hfHeldDone=true;resolve(r);},reject);});
                        }
                        return native(input,init);
                      };
                    }""", hold_path)
                    system_d, scenario_d = target_d.split("/", 1)
                    stage = "selecting stale-response architecture"
                    if page.locator(f'[data-system="{system_d}"]').count():
                        page.locator(f'[data-system="{system_d}"]').first.click()
                    stage = "selecting stale-response scenario"
                    page.locator(f'[data-scenario="{scenario_d}"]').first.click()
                    stage = "waiting for stale-response fetch to hold"
                    page.wait_for_function("() => window.__hfHeldStarted === true", timeout=30000)
                    stage = "late response held"
                    system_c, scenario_c = target_c.split("/", 1)
                    stage = "selecting current scenario after hold"
                    if page.locator(f'[data-system="{system_c}"]').count():
                        page.locator(f'[data-system="{system_c}"]').first.click()
                    page.locator(f'[data-scenario="{scenario_c}"]').first.click()
                    stage = "waiting for current result while old response held"
                    expected_c = page.evaluate("key => window.HF.HYBRID_CATALOG.systems.find(x=>x.id===key.split('/')[0])?.name", target_c)
                    page.wait_for_function("expected => document.querySelector('#hybrid-output')?.innerText.includes(expected)", arg=expected_c, timeout=60000)
                    stage = "new selection loaded while old request held"
                    page.evaluate("() => window.__hfRelease && window.__hfRelease()")
                    page.wait_for_function("() => window.__hfHeldDone === true", timeout=60000)
                    stage = "late response released"
                    page.wait_for_load_state("networkidle", timeout=15000)
                    visible_after_stale = page.locator("#hybrid-output").inner_text()
                    result_labels = page.evaluate("""pairs => {
                      const text=document.querySelector('#hybrid-output')?.innerText||'';
                      const current=window.HF.scenarioById(pairs[0].split('/')[1]).name;
                      const stale=window.HF.scenarioById(pairs[1].split('/')[1]).name;
                      return {current_scenario:current,stale_scenario:stale,current_visible:text.includes(current),stale_visible:text.includes(stale)};
                    }""", [target_c, target_d])
                    checks.append(outcome("late_hybrid_response_does_not_replace_new_selection",
                                          {"current_pair": target_c, "current_scenario_visible": True, "stale_scenario_visible": False},
                                          {**result_labels, "current_pair": target_c, "stale_pair": target_d},
                                          result_labels.get("current_visible") is True and result_labels.get("stale_visible") is False))
                else:
                    checks.append(outcome("nonbootstrap_architecture_and_scenario_result", "second, third, and uncached fourth distinct pairs", [target_b, target_c, target_d], False))

            # All 12 workspaces and all 59 study IDs, loading the deferred panel only after scrolling it into view.
            by_page: dict[str, list[dict[str, str]]] = {}
            for item in studies:
                by_page.setdefault(item["workspace"], []).append(item)
            export_checks: list[dict[str, Any]] = []
            export_status: dict[str, list[str]] = {kind: [] for kind in ("json", "table_csv", "series_csv", "memo")}
            empty_table_ids: list[str] = []
            series_8760: list[dict[str, Any]] = []
            heading_failures: list[dict[str, str]] = []
            for workspace, entries in by_page.items():
                stage = f"workspace {workspace}"
                page.locator(f'[data-nav="{workspace}"]').first.click()
                workbench = page.locator("#study-workbench")
                workbench.wait_for(state="attached", timeout=30000)
                workbench.scroll_into_view_if_needed(timeout=30000)
                workbench.locator("[data-study-select]").first.wait_for(state="visible", timeout=30000)
                for item in entries:
                    study_id = item["study_id"]
                    selector = f'[data-study-select="{study_id}"]'
                    page.locator(selector).first.click()
                    form = page.locator(f'#study-form[data-study-id="{study_id}"]')
                    form.wait_for(state="attached", timeout=30000)
                    page.wait_for_function("id => { const s=document.querySelector('#study-status'); const o=document.querySelector('#study-output'); return Boolean(s && o && !o.hidden && s.innerText.includes('Completed example')); }", arg=study_id, timeout=30000)
                    study_seen.append(study_id)
                    expected = page.evaluate("""async id => {
                      const r=window.HF.STUDY_BUNDLE.results[id];
                      const def=window.HF.STUDY_BUNDLE.catalogue.find(x=>x.id===id);
                      const selected=Number(document.querySelector('#study-workbench [data-study-series]')?.value ?? 0);
                      const series=Array.isArray(r?.series)?r.series:[];
                      const s=series[selected];
                      const csvText=v=>{let text=String(v??'');if(typeof v!=='number'&&/^[=+\\-@\\t\\r]/.test(text))text="'"+text;return text;};
                      const provenance={schema:'helioforge.study-export.v1',study:r.study,model_version:r.model_version,
                        data_kind:r.data_kind,inputs:r.inputs,provenance:r.provenance,equations:r.equations,limitations:r.limitations,warnings:r.warnings,
                        sources:r.sources,evidence_sha256:r.evidence_sha256,
                        units:{metrics:(r.metrics||[]).map(m=>({label:m.label,unit:m.unit})),series:series.map(x=>({name:x.name,x_label:x.x_label,y_unit:x.y_unit}))},
                        integrity_scope:'Evidence digest identifies the original result JSON, not this CSV encoding; no scientific or human approval.'};
                      const provenanceText=JSON.stringify(provenance);
                      const csvCell=value=>{let text=String(value??'');if(typeof value!=='number'&&/^[=+\\-@\\t\\r]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';};
                      const addMetadata=rows=>(rows.length?rows:[{}]).map((row,i)=>({...row,hf_record_kind:rows.length?'observation':'metadata_only',
                        hf_study:r.study,hf_model_version:r.model_version,hf_data_kind:r.data_kind,hf_evidence_sha256:r.evidence_sha256,
                        hf_provenance_json:i===0?provenanceText:''}));
                      const toCsv=rows=>{const keys=Object.keys(rows[0]||{});return [keys.map(k=>csvCell(k)).join(','),...rows.map(row=>keys.map(k=>csvCell(row[k])).join(','))].join('\\r\\n');};
                      const digestText=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),x=>x.toString(16).padStart(2,'0')).join('');
                      const tableCsvSha256=await digestText(toCsv(addMetadata(Array.isArray(r.table)?r.table:[])));
                      const seriesRows=s?s.x.map((x,i)=>({observation:x,value:s.y[i],unit:s.y_unit})):[];
                      const seriesCsvSha256=s?await digestText(toCsv(addMetadata(seriesRows))):null;
                      const textValue=v=>typeof v==='number'?window.HF.fmt(v,3):v==null?'—':typeof v==='object'?JSON.stringify(v):String(v);
                      const memoLines=[`# ${def?.title??id}`,'',def?.summary??'','','## Result provenance','```json',String(provenanceText),'```','','## Results',...(r.metrics||[]).map(m=>`- ${m.label}: ${textValue(m.value)} ${m.unit}`),'','## Assumptions','```json',JSON.stringify(r.inputs,null,2),'```','','## Boundaries',...(def?.limitations||[]).map(x=>'- '+x),...(r.warnings||[]).map(x=>'- '+x),'','Evidence SHA-256: '+r.evidence_sha256,'No investment, engineering, regulatory or operational approval is implied.'];
                      const memoSha256=await digestText(memoLines.join('\\n'));
                      const jsonText=JSON.stringify(r,null,2);
                      const jsonSha256=await digestText(jsonText);
                      return {jsonSha256,tableCsvSha256,seriesCsvSha256,memoSha256,tableCount:Array.isArray(r.table)?r.table.length:0,tablePresent:Array.isArray(r.table),
                        seriesCount:series.length,selectedSeriesIndex:s?selected:null,selectedSeriesName:s?.name??null,
                        seriesXText:s?.x?.map(csvText)??[],seriesYText:s?.y?.map(csvText)??[],
                        seriesUnit:s?.y_unit??null,seriesLength:s?.x?.length??0,seriesYLength:s?.y?.length??0,
                        provenance:JSON.parse(JSON.stringify(provenance)),studyTitle:def?.title??id,studySummary:def?.summary??'',
                        definitionLimitations:def?.limitations??[],
                        limitations:r.limitations||[],warnings:r.warnings||[],metrics:r.metrics||[],inputs:r.inputs,
                        study:r.study,modelVersion:r.model_version,dataKind:r.data_kind,evidenceSha256:r.evidence_sha256??''};
                    }""", study_id)
                    actual_heading = page.locator("#study-workbench .section-heading h2").inner_text()
                    heading_ok = actual_heading == expected["studyTitle"]
                    if not heading_ok:
                        heading_failures.append({"study_id": study_id, "expected": expected["studyTitle"], "actual": actual_heading})
                    valid_export: dict[str, Any] = {"study_id": study_id, "workspace": workspace, "heading_expected": expected["studyTitle"],
                                                   "heading_actual": actual_heading, "heading_matches_result": heading_ok,
                                                   "table_rows_expected": expected["tableCount"],
                                                   "table_metadata_only_expected": expected["tableCount"] == 0,
                                                   "selected_series_index": expected["selectedSeriesIndex"], "selected_series_expected": expected["seriesLength"]}

                    stage = f"study {study_id}: JSON export"
                    # Full JSON must be byte-for-byte the current workspace result object.
                    with page.expect_download(timeout=30000) as download_info:
                        click_export("json")
                    json_download = download_info.value
                    json_target = Path(download_dir.name) / f"{study_id}.json"
                    json_download.save_as(str(json_target))
                    json_bytes = json_target.read_bytes()
                    json_value = read_json_strict(json_target)
                    json_ok = (sha256(json_bytes) == expected["jsonSha256"] and isinstance(json_value, dict) and
                               json_value.get("study") == study_id and REQUIRED_STUDY_KEYS.issubset(json_value))
                    export_status["json"].append("PASS" if json_ok else "FAIL")
                    valid_export["json"] = {"status": "PASS" if json_ok else "FAIL", "filename": json_download.suggested_filename,
                                             "sha256_expected": expected["jsonSha256"], "sha256_actual": sha256(json_bytes),
                                             "study_id": json_value.get("study") if isinstance(json_value, dict) else None}

                    stage = f"study {study_id}: table CSV export"
                    # Table CSV is lossless with respect to row count and carries provenance on row one.
                    with page.expect_download(timeout=30000) as download_info:
                        click_export("csv")
                    table_download = download_info.value
                    table_target = Path(download_dir.name) / f"{study_id}-table.csv"
                    table_download.save_as(str(table_target))
                    table_header, table_rows = parse_csv_export(table_target)
                    expected_data_rows = expected["tableCount"] or 1
                    obs_count = sum(row.get("hf_record_kind") == "observation" for row in table_rows)
                    metadata_only_count = sum(row.get("hf_record_kind") == "metadata_only" for row in table_rows)
                    table_provenance = None
                    try:
                        table_provenance = json.loads(table_rows[0]["hf_provenance_json"]) if table_rows else None
                    except Exception:
                        pass
                    metadata_columns = {"hf_record_kind", "hf_study", "hf_model_version", "hf_data_kind", "hf_evidence_sha256", "hf_provenance_json"}
                    table_metadata_ok = bool(table_rows) and all(metadata_columns.issubset(row) for row in table_rows)
                    table_metadata_ok = table_metadata_ok and all(row.get("hf_study") == study_id and row.get("hf_model_version") == expected["modelVersion"] and
                                                                  row.get("hf_data_kind") == expected["dataKind"] and row.get("hf_evidence_sha256") == expected["evidenceSha256"] for row in table_rows)
                    table_metadata_ok = table_metadata_ok and table_provenance == expected["provenance"] and all(not row.get("hf_provenance_json") for row in table_rows[1:])
                    table_kind_ok = (obs_count == expected["tableCount"] and metadata_only_count == (1 if expected["tableCount"] == 0 else 0) and len(table_rows) == expected_data_rows)
                    table_hash = sha256(table_target.read_bytes())
                    table_ok = (table_kind_ok and table_metadata_ok and bool(metadata_columns.issubset(table_header)) and
                                table_hash == expected["tableCsvSha256"])
                    export_status["table_csv"].append("PASS" if table_ok else "FAIL")
                    if expected["tableCount"] == 0 and metadata_only_count == 1:
                        empty_table_ids.append(study_id)
                    valid_export["table_csv"] = {"status": "PASS" if table_ok else "FAIL", "filename": table_download.suggested_filename,
                                                  "expected_data_rows": expected_data_rows, "actual_data_rows": len(table_rows),
                                                  "observation_rows": obs_count, "metadata_only_rows": metadata_only_count,
                                                  "sha256_matches_current_bundle_rows": table_hash == expected["tableCsvSha256"],
                                                  "provenance_matches_current_bundle": table_provenance == expected["provenance"],
                                                  "record_metadata_matches_current_bundle": table_metadata_ok}

                    # A selected series is an exact x/y export, including null gaps and long 8760-step series.
                    if expected["selectedSeriesIndex"] is None:
                        series_button = page.locator('[data-study-export="series"]')
                        no_series_export = not series_button.is_disabled()
                        series_status = "FAIL" if no_series_export else "NOT_APPLICABLE_NO_SERIES"
                        export_status["series_csv"].append(series_status)
                        valid_export["series_csv"] = {"status": series_status, "series_available": False, "button_disabled": not no_series_export,
                                                       "download_emitted": False, "detail": "No selected series exists; series export is disabled."}
                    else:
                        with page.expect_download(timeout=30000) as download_info:
                            click_export("series")
                        series_download = download_info.value
                        series_target = Path(download_dir.name) / f"{study_id}-series.csv"
                        series_download.save_as(str(series_target))
                        series_header, series_rows = parse_csv_export(series_target)
                        x_match = len(series_rows) == len(expected["seriesXText"]) and [row.get("observation", "") for row in series_rows] == expected["seriesXText"]
                        y_match = len(series_rows) == len(expected["seriesYText"]) and [row.get("value", "") for row in series_rows] == expected["seriesYText"]
                        units_match = bool(series_rows) and all(row.get("unit") == expected["seriesUnit"] for row in series_rows)
                        series_provenance = None
                        try:
                            series_provenance = json.loads(series_rows[0]["hf_provenance_json"]) if series_rows else None
                        except Exception:
                            pass
                        series_metadata_ok = bool(series_rows) and all(row.get("hf_study") == study_id and row.get("hf_model_version") == expected["modelVersion"] and
                                                                     row.get("hf_data_kind") == expected["dataKind"] and row.get("hf_evidence_sha256") == expected["evidenceSha256"] for row in series_rows)
                        series_metadata_ok = series_metadata_ok and series_provenance == expected["provenance"] and all(not row.get("hf_provenance_json") for row in series_rows[1:])
                        series_hash = sha256(series_target.read_bytes())
                        series_ok = (len(series_rows) == expected["seriesLength"] and x_match and y_match and units_match and series_metadata_ok and
                                     series_hash == expected["seriesCsvSha256"] and
                                     {"observation", "value", "unit", "hf_record_kind"}.issubset(series_header) and all(row.get("hf_record_kind") == "observation" for row in series_rows))
                        export_status["series_csv"].append("PASS" if series_ok else "FAIL")
                        if expected["seriesLength"] >= 8000:
                            series_8760.append({"study_id": study_id, "expected_rows": expected["seriesLength"], "actual_rows": len(series_rows), "status": "PASS" if series_ok else "FAIL"})
                        valid_export["series_csv"] = {"status": "PASS" if series_ok else "FAIL", "filename": series_download.suggested_filename,
                                                       "expected_data_rows": expected["seriesLength"], "actual_data_rows": len(series_rows),
                                                       "x_matches_current_bundle": x_match, "y_matches_current_bundle": y_match,
                                                       "sha256_matches_current_bundle_rows": series_hash == expected["seriesCsvSha256"],
                                                       "unit_matches_current_bundle": units_match, "provenance_matches_current_bundle": series_provenance == expected["provenance"],
                                                       "record_metadata_matches_current_bundle": series_metadata_ok}

                    # Memo provenance, assumptions, boundaries and non-approval language must match the result.
                    with page.expect_download(timeout=30000) as download_info:
                        click_export("memo")
                    memo_download = download_info.value
                    memo_target = Path(download_dir.name) / f"{study_id}-memo.md"
                    memo_download.save_as(str(memo_target))
                    memo = memo_target.read_text(encoding="utf-8")
                    prov_match = re.search(r"## Result provenance\s*```json\s*(.*?)\s*```", memo, flags=re.DOTALL)
                    assumptions_match = re.search(r"## Assumptions\s*```json\s*(.*?)\s*```", memo, flags=re.DOTALL)
                    try:
                        memo_provenance = json.loads(prov_match.group(1)) if prov_match else None
                    except Exception:
                        memo_provenance = None
                    try:
                        memo_inputs = json.loads(assumptions_match.group(1)) if assumptions_match else None
                    except Exception:
                        memo_inputs = None
                    boundaries_ok = all(text in memo for text in expected["definitionLimitations"] + expected["warnings"])
                    no_fake_approval = ("No investment, engineering, regulatory or operational approval is implied." in memo and
                                        "no scientific or human approval" in expected["provenance"].get("integrity_scope", ""))
                    memo_hash = sha256(memo_target.read_bytes())
                    memo_ok = (memo_hash == expected["memoSha256"] and memo.startswith("# " + expected["studyTitle"] + "\n") and memo_provenance == expected["provenance"] and
                               memo_inputs == expected["inputs"] and boundaries_ok and no_fake_approval)
                    export_status["memo"].append("PASS" if memo_ok else "FAIL")
                    valid_export["memo"] = {"status": "PASS" if memo_ok else "FAIL", "filename": memo_download.suggested_filename,
                                             "sha256_matches_current_bundle_value": memo_hash == expected["memoSha256"],
                                             "provenance_matches_current_bundle": memo_provenance == expected["provenance"],
                                             "assumptions_match_current_bundle": memo_inputs == expected["inputs"],
                                             "limitations_and_warnings_present": boundaries_ok, "non_approval_disclosure_present": no_fake_approval}
                    valid_export["series_metadata"] = {"available": expected["selectedSeriesIndex"] is not None, "selected_index": expected["selectedSeriesIndex"],
                                                        "length": expected["seriesLength"], "selected_name": expected["selectedSeriesName"]}
                    export_checks.append(valid_export)

            workspaces_seen = list(by_page.keys())
            json_pass = sum(value == "PASS" for value in export_status["json"])
            table_pass = sum(value == "PASS" for value in export_status["table_csv"])
            series_pass = sum(value == "PASS" for value in export_status["series_csv"])
            series_na = sum(value == "NOT_APPLICABLE_NO_SERIES" for value in export_status["series_csv"])
            memo_pass = sum(value == "PASS" for value in export_status["memo"])
            export_summary = {"studies": len(export_checks), "json_pass": json_pass, "table_csv_pass": table_pass,
                              "series_csv_pass": series_pass, "series_csv_not_applicable_no_series": series_na,
                              "memo_pass": memo_pass, "empty_table_metadata_only_expected": len(empty_table_ids),
                              "empty_table_metadata_only_actual": empty_table_ids, "long_series": series_8760}
            checks.append(outcome("study_all_59_json_exports_match_current_bundle", {"study_ids": 59, "exports": 59},
                                  {"study_ids": len(export_checks), "valid_exports": json_pass, "failures": [x["study_id"] for x in export_checks if x["json"]["status"] != "PASS"]},
                                  len(export_checks) == 59 and json_pass == 59))
            checks.append(outcome("study_all_59_table_csv_rows_and_provenance", {"study_ids": 59, "exports": 59, "empty_tables_metadata_only": 10},
                                  {"study_ids": len(export_checks), "valid_exports": table_pass, "empty_tables_metadata_only": len(empty_table_ids),
                                   "empty_table_ids": empty_table_ids, "failures": [x["study_id"] for x in export_checks if x["table_csv"]["status"] != "PASS"]},
                                  len(export_checks) == 59 and table_pass == 59 and len(empty_table_ids) == 10))
            checks.append(outcome("selected_series_csv_matches_bundle_or_has_no_series", {"studies": 59, "downloaded": 45, "not_applicable_no_series": 14},
                                  {"studies": len(export_checks), "downloaded_and_verified": series_pass, "not_applicable_no_series": series_na,
                                   "long_series_8000_or_more": series_8760, "failures": [x["study_id"] for x in export_checks if x["series_csv"]["status"] == "FAIL"]},
                                  len(export_checks) == 59 and series_pass == 45 and series_na == 14 and not any(x["status"] != "PASS" for x in series_8760)))
            checks.append(outcome("study_all_59_memos_provenance_boundaries_and_nonapproval", {"study_ids": 59, "exports": 59, "scientific_validation_claims": 0},
                                  {"study_ids": len(export_checks), "valid_memos": memo_pass, "failures": [x["study_id"] for x in export_checks if x["memo"]["status"] != "PASS"]},
                                  len(export_checks) == 59 and memo_pass == 59))
            actual["study_export_records"] = export_checks
            actual["study_export_summary"] = export_summary
            actual["loaded_workspaces"] = workspaces_seen
            actual["selected_studies"] = study_seen
            checks.append(outcome("all_workspaces_load_and_all_studies_select", {"workspaces": 12, "studies": 59, "expected_results_and_enabled_exports": True},
                                  {"workspaces": len(workspaces_seen), "workspace_ids": workspaces_seen, "study_ids": len(study_seen), "heading_failures": heading_failures,
                                   "study_ids_unique": len(set(study_seen)) == 59},
                                  len(workspaces_seen) == 12 and len(study_seen) == 59 and len(set(study_seen)) == 59 and not heading_failures))
            actual["browser_data_responses"] = data_responses

            # The browser model starts at Compare. Run a fresh candidate and verify new output.
            page.locator('[data-nav="compare"]').first.click()
            stage = "hosted terminal"
            run_form = page.locator("#terminal-run-form")
            run_form.wait_for(state="visible", timeout=30000)
            input_pv = run_form.locator('[name="pvKw"]')
            old_pv = input_pv.input_value()
            input_pv.fill(str(float(old_pv) + 1.0))
            run_form.get_by_role("button", name=re.compile("Run candidate")).click()
            page.get_by_text("Candidate B completed. All displayed numbers belong to these exact inputs.", exact=True).wait_for(state="visible", timeout=30000)
            checks.append(outcome("hosted_terminal_fresh_run", "candidate B completed after changing inputs", {"initial_pv_kw": old_pv, "updated_pv_kw": input_pv.input_value(), "notice": page.locator("#terminal-notice").inner_text()},
                                  page.locator("#terminal-notice").inner_text() == "Candidate B completed. All displayed numbers belong to these exact inputs."))

            # Resize/keyboard checks for the drawer at requested tablet boundaries.
            drawer_results = []
            for width in (820, 1024, 1100, 1101):
                stage = f"tablet drawer {width}"
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_function("width => document.querySelector('#sidebar')?.inert === (width <= 1100)", arg=width, timeout=10000)
                toggle = page.locator('[data-action="menu"]')
                if width <= 1100:
                    menu_style = toggle.evaluate("el => ({display:getComputedStyle(el).display,rect:el.getBoundingClientRect().toJSON()})")
                    if menu_style["display"] == "none" or menu_style["rect"]["width"] <= 0:
                        drawer_results.append({"width": width, "status": "FAIL", "error": "menu button is not visible", "button": menu_style,
                                               "media_query_matches": page.evaluate("() => matchMedia('(max-width:1100px)').matches")})
                        continue
                    toggle.click()
                    page.wait_for_function("() => document.querySelector('#sidebar')?.classList.contains('mobile-open') && document.querySelector('.app-main')?.inert", timeout=10000)
                    opened = {"expanded": toggle.get_attribute("aria-expanded"), "sidebar_inert": page.locator("#sidebar").evaluate("el => el.inert"), "main_inert": page.locator(".app-main").evaluate("el => el.inert")}
                    page.keyboard.press("Escape")
                    page.wait_for_function("() => !document.querySelector('#sidebar')?.classList.contains('mobile-open') && !document.querySelector('.app-main')?.inert", timeout=10000)
                    closed = {"expanded": toggle.get_attribute("aria-expanded"), "toggle_restored_focus": page.evaluate("el => document.activeElement === el", toggle.element_handle()), "sidebar_inert": page.locator("#sidebar").evaluate("el => el.inert")}
                    passed = opened == {"expanded": "true", "sidebar_inert": False, "main_inert": True} and closed == {"expanded": "false", "toggle_restored_focus": True, "sidebar_inert": True}
                    drawer_results.append({"width": width, "opened": opened, "closed": closed, "status": "PASS" if passed else "FAIL"})
                else:
                    state = {"sidebar_inert": page.locator("#sidebar").evaluate("el => el.inert"), "closed": not page.locator("#sidebar").evaluate("el => el.classList.contains('mobile-open')"), "toggle_expanded": toggle.get_attribute("aria-expanded")}
                    drawer_results.append({"width": width, **state, "status": "PASS" if state == {"sidebar_inert": False, "closed": True, "toggle_expanded": "false"} else "FAIL"})
            checks.append(outcome("tablet_drawer_820_1024_1100_1101", "open/escape/restore at <=1100; desktop inert=false at 1101", drawer_results, all(row["status"] == "PASS" for row in drawer_results)))
            actual["tablet_drawer_checks"] = drawer_results

            # Long hashes in expanded provenance details must remain readable on narrow screens.
            provenance_layout = []
            for width in (390, 820):
                page.set_viewport_size({"width": width, "height": 900})
                page.locator('[data-action="menu"]').click()
                page.wait_for_function("() => document.querySelector('#sidebar')?.classList.contains('mobile-open')", timeout=10000)
                page.locator('[data-nav="hybrid"]').first.click()
                page.wait_for_function("() => !document.querySelector('#sidebar')?.classList.contains('mobile-open')", timeout=10000)
                hybrid_detail = page.locator('#hybrid-output details.method-details').filter(has_text=re.compile(r"Read assumptions, provenance & model limits", re.I)).first
                hybrid_detail.wait_for(state="attached", timeout=30000)
                hybrid_detail.locator("summary").click()
                page.wait_for_function("() => document.querySelector('#hybrid-output details[open]')?.innerText.includes('provenance')", timeout=10000)
                hybrid_layout = hybrid_detail.evaluate("""d => {
                  const root=document.documentElement,body=document.body;
                  const longText=[...d.querySelectorAll('p')].filter(x=>/SHA-256/i.test(x.innerText));
                  return {open:d.open,summary:d.querySelector('summary')?.innerText,
                    viewportWidth:innerWidth,rootScrollWidth:root.scrollWidth,bodyScrollWidth:body.scrollWidth,
                    longText:longText.map(x=>({text:x.innerText,clientWidth:x.clientWidth,scrollWidth:x.scrollWidth,
                      overflowWrap:getComputedStyle(x).overflowWrap,wordBreak:getComputedStyle(x).wordBreak,whiteSpace:getComputedStyle(x).whiteSpace}))};
                }""")
                hybrid_layout["pair"] = page.evaluate("() => `${document.querySelector('[data-system][aria-pressed=\"true\"]')?.dataset.system ?? 'unknown'}/${document.querySelector('[data-scenario][aria-pressed=\"true\"]')?.dataset.scenario ?? 'unknown'}`")
                hybrid_layout.update({"width": width, "view": "hybrid"})
                hybrid_layout["status"] = "PASS" if hybrid_layout["open"] and hybrid_layout["rootScrollWidth"] <= width and hybrid_layout["bodyScrollWidth"] <= width and all(x["scrollWidth"] <= x["clientWidth"] for x in hybrid_layout["longText"]) else "FAIL"
                provenance_layout.append(hybrid_layout)

                page.locator('[data-action="menu"]').click()
                page.wait_for_function("() => document.querySelector('#sidebar')?.classList.contains('mobile-open')", timeout=10000)
                page.locator('[data-nav="storage"]').first.click()
                page.wait_for_function("() => !document.querySelector('#sidebar')?.classList.contains('mobile-open')", timeout=10000)
                workbench = page.locator("#study-workbench")
                workbench.wait_for(state="attached", timeout=30000)
                workbench.scroll_into_view_if_needed(timeout=30000)
                page.locator('[data-study-select="storage-annualopt"]').first.click()
                page.wait_for_function("() => {const s=document.querySelector('#study-status'),o=document.querySelector('#study-output');return Boolean(s&&o&&!o.hidden&&s.innerText.includes('Completed example'));}", timeout=30000)
                annual_detail = page.locator('#study-output details.method-details').filter(has_text=re.compile(r"Equations, sources and model boundaries", re.I)).first
                annual_detail.wait_for(state="attached", timeout=30000)
                annual_detail.locator("summary").click()
                page.wait_for_function("() => [...document.querySelectorAll('#study-output details[open]')].some(d=>d.innerText.includes('Evidence SHA-256'))", timeout=10000)
                annual_layout = annual_detail.evaluate("""d => {
                  const root=document.documentElement,body=document.body;
                  const longText=[...d.querySelectorAll('p')].filter(x=>/SHA-256/i.test(x.innerText));
                  return {open:d.open,summary:d.querySelector('summary')?.innerText,
                    viewportWidth:innerWidth,rootScrollWidth:root.scrollWidth,bodyScrollWidth:body.scrollWidth,
                    longText:longText.map(x=>({text:x.innerText,clientWidth:x.clientWidth,scrollWidth:x.scrollWidth,
                      overflowWrap:getComputedStyle(x).overflowWrap,wordBreak:getComputedStyle(x).wordBreak,whiteSpace:getComputedStyle(x).whiteSpace}))};
                }""")
                annual_layout.update({"width": width, "view": "study", "study_id": "storage-annualopt"})
                annual_layout["status"] = "PASS" if annual_layout["open"] and annual_layout["rootScrollWidth"] <= width and annual_layout["bodyScrollWidth"] <= width and all(x["scrollWidth"] <= x["clientWidth"] for x in annual_layout["longText"]) else "FAIL"
                provenance_layout.append(annual_layout)
            checks.append(outcome("expanded_hybrid_and_annual_provenance_has_no_horizontal_overflow_at_390_820",
                                  {"widths": [390, 820], "views": ["hybrid", "study"], "root_overflow": False, "long_hash_overflow": False},
                                  provenance_layout, len(provenance_layout) == 4 and all(x["status"] == "PASS" for x in provenance_layout)))
            actual["expanded_provenance_responsive_checks"] = provenance_layout

            # Frozen council: every source-ledger row is a label for a rejected, read-only fixture attempt.
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.locator('[data-nav="council"]').click()
            stage = "frozen council"
            council_form = page.locator('form[data-model="council"]')
            council_form.wait_for(state="visible", timeout=30000)
            notice = page.locator("[data-frozen-council]")
            notice.wait_for(state="visible", timeout=10000)
            council_geometry = page.evaluate("""() => {
              const form=document.querySelector('form[data-model="council"]');
              const inputs=[...form.querySelectorAll('input,select,textarea')];
              const nodes=[...document.querySelectorAll('.council-topology .council-node')];
              const critic=document.querySelector('.council-topology .critic');
              return {notice:document.querySelector('[data-frozen-council]')?.innerText,
                disabledFields:inputs.length>0&&inputs.every(x=>x.disabled),fieldCount:inputs.length,
                disabledSubmit:form.querySelector('[type="submit"]')?.disabled,
                fixedSections:document.querySelectorAll('.council-topology .council-node:not(.critic)').length,
                criticText:critic?.innerText,criticStatus:critic?.querySelector('small')?.innerText,
                exportButton:document.querySelector('[data-action="export-council"]')!==null};
            }""")
            api_before = len(api_requests)
            # Submit event is forced directly, even though the visible control is disabled.
            page.evaluate("""() => {const f=document.querySelector('form[data-model="council"]'); f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}""")
            page.wait_for_timeout(100)
            api_after = len(api_requests)
            static_fixed = council_geometry.get("fixedSections") == 8 and "no critic invocation" in (council_geometry.get("criticStatus") or "").lower()
            checks.append(outcome("frozen_council_fixed_eight_no_critic_disabled_and_forced_submit_inert",
                                  {"fixed_sections": 8, "critic_invocation": False, "all_fields_disabled": True, "submit_disabled": True, "forced_api_calls": 0, "notice": "Frozen synthetic council example"},
                                  {**council_geometry, "forced_api_calls": api_after - api_before},
                                  static_fixed and council_geometry.get("disabledFields") is True and council_geometry.get("disabledSubmit") is True and api_after == api_before and "Frozen synthetic council example" in (council_geometry.get("notice") or "")))
            matrix_row_results = []
            for row in public_rows:
                stage = f"council row {row.get('test_id')}"
                # Fixture rejection is what this public edition can prove; no evidence payload is injected.
                fields_still_disabled = page.locator('form[data-model="council"] input,form[data-model="council"] select,form[data-model="council"] textarea').evaluate_all("xs => xs.length > 0 && xs.every(x => x.disabled)")
                with page.expect_download(timeout=30000) as download_info:
                    paced_download_click('[data-action="export-council"]')
                download = download_info.value
                target = Path(download_dir.name) / f"council-{row.get('test_id','row')}.md"
                download.save_as(str(target))
                raw = target.read_bytes()
                body = raw.decode("utf-8", errors="strict")
                digest = sha256(raw)
                required_caveats = ["Frozen synthetic council example.", "no specialist or critic is executed", "does not verify source, signer, scientific validity, or approval"]
                caveats_present = all(phrase.lower() in body.lower() for phrase in required_caveats)
                export_hashes.append(digest)
                row_ok = fields_still_disabled and caveats_present and "evidence-state submissions" in (notice.inner_text()).lower()
                matrix_row_results.append({"test_id": row.get("test_id"), "role": row.get("role"), "evidence_state": row.get("evidence_state"),
                                           "status": "FIXTURE_REJECTED_READ_ONLY" if row_ok else "FAIL", "evidence_injected": False,
                                           "disabled_fields": fields_still_disabled, "export_sha256": digest, "disclosures_present": caveats_present,
                                           "source_expected": row.get("expected")})
            checks.append(outcome("council_public_fixture_matrix_read_only_and_export_disclosures_invariant",
                                  {"rows": 63, "unique_roles": 9, "unique_evidence_states": 7, "all_exports_identical": True, "evidence_payloads_injected": False},
                                  {"rows": len(matrix_row_results), "roles": len({r.get("role") for r in matrix_row_results}), "evidence_states": len({r.get("evidence_state") for r in matrix_row_results}),
                                   "all_exports_identical": len(set(export_hashes)) == 1, "evidence_payloads_injected": False,
                                   "row_failures": [r for r in matrix_row_results if r["status"] == "FAIL"],
                                   "status_note": "Each ledger row exercises the same frozen public state; it does not claim evidence-state processing."},
                                  len(matrix_row_results) == 63 and len({r.get("role") for r in matrix_row_results}) == 9 and len({r.get("evidence_state") for r in matrix_row_results}) == 7 and len(set(export_hashes)) == 1 and all(r["status"] != "FAIL" for r in matrix_row_results)))
            actual["council_matrix_rows"] = matrix_row_results
            actual["council_export_sha256_set"] = sorted(set(export_hashes))

            checks.append(outcome("browser_page_errors_and_provider_api_calls", {"page_errors": 0, "api_requests": 0, "remote_origin_requests": 0},
                                  {"page_errors": page_errors, "api_requests": api_requests, "remote_origin_requests": remote_origin_requests},
                                  not page_errors and not api_requests and not remote_origin_requests))
            actual["browser_data_responses"] = data_responses
        except HostedAppStartupError as exc:
            actual["browser_error"] = f"{type(exc).__name__}: {exc}"
            actual["browser_stage"] = stage
            actual["browser_console"] = browser_console
            actual["study_dom"] = page.locator("#study-workbench").inner_text(timeout=2000)[-3000:] if page.locator("#study-workbench").count() else "absent"
            actual["remote_origin_requests"] = remote_origin_requests
            actual["page_errors"] = page_errors
            actual["api_requests"] = api_requests
            actual["browser_script_responses"] = script_responses
            actual["browser_data_responses"] = data_responses
        except Exception as exc:
            checks.append(outcome("browser_run_completed", "all requested browser checks executed", f"{type(exc).__name__}: {exc}", False))
            actual["browser_error"] = f"{type(exc).__name__}: {exc}"
            actual["browser_stage"] = stage
            actual["browser_console"] = browser_console
            actual["remote_origin_requests"] = remote_origin_requests
            try:
                actual["current_page_text_excerpt"] = page.locator("body").inner_text(timeout=2000)[:1800]
                actual["selected_architecture"] = page.locator('[data-system][aria-pressed="true"]').first.get_attribute("data-system")
                actual["selected_scenario"] = page.locator('[data-scenario][aria-pressed="true"]').first.get_attribute("data-scenario")
                actual["scenario_choices"] = page.locator("[data-scenario]").evaluate_all("xs => xs.map(x=>x.dataset.scenario)")
                actual["held_fetch_state"] = page.evaluate("() => ({started:window.__hfHeldStarted,done:window.__hfHeldDone,calls:window.__hfFetchCalls})")
            except Exception:
                pass
            actual["page_errors"] = page_errors
            actual["api_requests"] = api_requests
            actual["remote_origin_requests"] = remote_origin_requests
            actual["browser_script_responses"] = script_responses
            actual["browser_data_responses"] = data_responses

        # Full standalone HTML is intentionally a separate offline context.
        try:
            if not offline_file.exists():
                checks.append(outcome("offline_full_html_all_studies_and_terminal", str(offline_file), "file is absent", False))
            else:
                offline_context = browser.new_context(offline=True, accept_downloads=True, viewport={"width": 1440, "height": 1000})
                offline = offline_context.new_page()
                offline.on("request", lambda req: offline_http_requests.append(req.url) if req.url.startswith(("http://", "https://")) else None)
                offline.on("pageerror", lambda exc: page_errors.append("offline: " + str(exc)))
                offline.goto(offline_file.resolve().as_uri(), wait_until="domcontentloaded", timeout=120000)
                offline.locator("#app").wait_for(state="attached", timeout=30000)
                offline.wait_for_function("() => Boolean(window.HF && window.HF.STUDY_BUNDLE)", timeout=30000)
                embedded = offline.evaluate("""() => ({catalogue:window.HF.STUDY_BUNDLE.catalogue.map(x=>({id:x.id,page:x.page})),results:Object.keys(window.HF.STUDY_BUNDLE.results||{})})""")
                catalogue_ids = {item["id"] for item in embedded.get("catalogue", [])}
                result_ids = set(embedded.get("results", []))
                offline_study_results = []
                offline_by_page: dict[str, list[dict[str, str]]] = {}
                for item in studies:
                    offline_by_page.setdefault(item["workspace"], []).append(item)
                for workspace, entries in offline_by_page.items():
                    offline.locator(f'[data-nav="{workspace}"]').first.click()
                    offline.locator("#study-workbench").wait_for(state="attached", timeout=30000)
                    offline.locator("#study-workbench").scroll_into_view_if_needed(timeout=30000)
                    for item in entries:
                        offline.locator(f'[data-study-select="{item["study_id"]}"]').first.click()
                        offline.locator(f'#study-form[data-study-id="{item["study_id"]}"]').wait_for(state="attached", timeout=10000)
                        offline.wait_for_function("() => {const s=document.querySelector('#study-status');return Boolean(s && s.innerText.includes('Completed example'));}", timeout=10000)
                        offline_study_results.append(item["study_id"])
                offline.locator('[data-nav="compare"]').first.click()
                offline.locator("#terminal-run-form").wait_for(state="visible", timeout=10000)
                offline_pv = offline.locator('#terminal-run-form [name="pvKw"]')
                old_value = offline_pv.input_value()
                offline_pv.fill(str(float(old_value) + 1.0))
                offline.locator('#terminal-run-form button[type="submit"]').click()
                offline.get_by_text("Candidate B completed. All displayed numbers belong to these exact inputs.", exact=True).wait_for(state="visible", timeout=30000)
                offline_counts = {"catalogue_studies": len(catalogue_ids), "results": len(result_ids), "selected_studies": len(offline_study_results), "selected_unique": len(set(offline_study_results)), "http_requests": len(offline_http_requests)}
                passed_offline = len(catalogue_ids) == 59 and len(result_ids) == 59 and len(offline_study_results) == 59 and len(set(offline_study_results)) == 59 and not offline_http_requests
                checks.append(outcome("offline_full_html_all_studies_and_terminal", {"catalogue_studies": 59, "results": 59, "selected_studies": 59, "http_requests": 0, "terminal_candidate_b": "completed"},
                                      {**offline_counts, "terminal_notice": offline.locator("#terminal-notice").inner_text()}, passed_offline))
                actual["offline_html_sha256"] = sha256(offline_file.read_bytes())
                actual["offline_embedded_studies"] = sorted(catalogue_ids)
                actual["offline_http_requests"] = offline_http_requests
                offline_context.close()
        except Exception as exc:
            checks.append(outcome("offline_run_completed", "all 59 studies and Terminal tested", f"{type(exc).__name__}: {exc}", False))
            actual["offline_error"] = f"{type(exc).__name__}: {exc}"

        context.close()
        browser.close()
    download_dir.cleanup()
    return checks, actual


def save_run(phase: str, site_info: dict[str, Any], checks: list[dict[str, Any]], browser_info: dict[str, Any] | None,
             ledger_counts: dict[str, Any], output_path: Path, command: list[str]) -> dict[str, Any]:
    run = {"phase": phase, "generated_at_utc": datetime.now(timezone.utc).isoformat(), "site": site_info,
           "command": {"python_executable": sys.executable, "python_version": sys.version.split()[0], "argv": command},
           "source_ledgers": {"study_inventory": str(STUDY_LEDGER.relative_to(ROOT)), "council_matrix": str(COUNCIL_LEDGER.relative_to(ROOT)), "council_matrix_counts": ledger_counts},
           "checks": checks, "status": outcome_status(checks)}
    if browser_info is not None:
        run["browser"] = browser_info
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {"title": "HelioForge hosted browser acceptance", "executions": []}
    if output_path.exists():
        try:
            existing = read_json_strict(output_path)
        except Exception:
            existing = {"title": "HelioForge hosted browser acceptance", "executions": [], "prior_output_read_error": "Existing evidence file could not be parsed; preserved as unavailable."}
    existing.setdefault("executions", []).append(run)
    output_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return run


def write_followup(results: dict[str, Any], output: Path) -> None:
    lines = ["# Hosted browser acceptance follow-up", "", "Generated by `scripts/acceptance-hosted.py`. This records local build and browser checks; it is not deployment, scientific validation, evidence authentication, or publication approval.", ""]
    omitted = results.get("runner_development_iterations_excluded")
    if omitted:
        lines += [f"Acceptance-runner note: {omitted.get('count')} development iterations were excluded from candidate evidence because they exposed runner expectation/selector defects that were corrected before the retained candidate runs. {omitted.get('reason')}", ""]
    for index, run in enumerate(results.get("executions", []), start=1):
        command = run.get("command") or {}
        command_argv = command.get("argv", [])
        lines += [f"## Execution {index}: {run.get('phase')} — {run.get('status')}", "", f"- Run time: `{run.get('generated_at_utc')}`", f"- Site: `{run.get('site', {}).get('site')}`", f"- Runtime SHA-256: `{run.get('site', {}).get('site_runtime_sha256')}`", f"- Data-index SHA-256: `{run.get('site', {}).get('data_index_sha256')}`", f"- Browser URL: `{(run.get('browser') or {}).get('url', 'not run')}`", f"- Python: `{command.get('python_executable', 'not recorded')}` ({command.get('python_version', 'unknown')})", f"- Arguments: `{json.dumps(command_argv, ensure_ascii=False)}`", "", "| Check | Status | Evidence class | Expected | Actual |", "|---|---|---|---|---|"]
        for item in run.get("checks", []):
            def compact(value: Any) -> Any:
                if isinstance(value, list) and len(value) > 8:
                    return {"count": len(value), "sample": value[:3], "last": value[-1]}
                if isinstance(value, dict):
                    return {key: compact(child) for key, child in value.items()}
                if isinstance(value, list):
                    return [compact(child) for child in value]
                return value
            expected = json.dumps(compact(item.get("expected")), ensure_ascii=False, separators=(",", ":"))
            actual = json.dumps(compact(item.get("actual")), ensure_ascii=False, separators=(",", ":"))
            lines.append(f"| `{item.get('check')}` | **{item.get('status')}** | {item.get('evidence_class')} | `{expected[:220]}` | `{actual[:320]}` |")
        lines += ["", "Run data and per-study/council row details are in [`hosted-browser-results.json`](hosted-browser-results.json).", ""]
    export_correction = any(
        run.get("browser", {}).get("study_export_summary", {}).get("table_csv_pass") == 59
        and run.get("browser", {}).get("study_export_summary", {}).get("series_csv_pass") == 45
        and run.get("browser", {}).get("study_export_summary", {}).get("memo_pass") == 59
        for run in results.get("executions", [])
    )
    if export_correction:
        lines += ["## Export-oracle correction", "", "An earlier retained candidate run reported CSV and memorandum provenance mismatches because the acceptance runner's expected provenance object omitted the app's `provenance` field. The runner expectation was corrected to include `r.provenance`, and the later run records the downloaded exports matching the result bundle for all 59 studies (59 JSON, 59 table CSV, 45 available series CSV, and 59 memoranda). The earlier run remains in the JSON history as an observed runner false negative.", ""]
    responsive_provenance_pass = any(
        item.get("check") == "expanded_hybrid_and_annual_provenance_has_no_horizontal_overflow_at_390_820" and item.get("status") == "PASS"
        for run in results.get("executions", []) for item in run.get("checks", [])
    )
    if responsive_provenance_pass:
        lines += ["## Responsive provenance check", "", "The first focused runner attempt did not reach the overflow assertions because it tried to click navigation while the mobile drawer was closed. The runner now opens the drawer before navigating. The passing execution records expanded hybrid and annual-study provenance at 390 px and 820 px, including root/body widths and long-hash element scroll widths.", ""]
    lines += ["## Interpretation", "", "The public council matrix uses the 63 `public_preview` rows in the historical source ledger as fixture labels. The hosted browser edition has no evidence-state injection interface; each row is therefore reported as a fixture-rejected, read-only check against the same frozen synthetic example. Matching export digests show the disclosure did not vary across those labels; they do not show that new evidence was processed.", "", "No test contacts a provider or submits evidence. Browser HTTPS certificate bypass is limited to the explicitly configured local test URL. See each run's `checks` entries for exact expected and observed values.", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-only", action="store_true", help="check the built app facts, exact manifest and every hosted JSON chunk without opening a browser")
    parser.add_argument("--url", default=os.environ.get("HELIOFORGE_ACCEPTANCE_URL", DEFAULT_URL))
    parser.add_argument("--site", default=os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", str(DEFAULT_SITE)))
    parser.add_argument("--offline-file", default=os.environ.get("HELIOFORGE_ACCEPTANCE_OFFLINE_FILE", str(ROOT / "HelioForge-Preview.html")))
    parser.add_argument("--evidence-dir", default=os.environ.get("HELIOFORGE_ACCEPTANCE_EVIDENCE_DIR", str(DOCS)))
    args = parser.parse_args()
    site = Path(args.site).resolve()
    output_dir = Path(args.evidence_dir).resolve()
    checks, site_info, expected_index = check_site(site)
    council_checks, council_counts, public_rows = check_council_ledger()
    checks.extend(council_checks)
    browser_info = None
    phase = "data-only" if args.data_only else "hosted-browser-and-offline"
    if not args.data_only:
        studies = load_csv(STUDY_LEDGER)
        browser_checks, browser_info = run_browser(args.url, Path(args.offline_file), public_rows, studies, expected_index)
        checks.extend(browser_checks)
    output_path = output_dir / "hosted-browser-results.json"
    command = [Path(sys.argv[0]).resolve().relative_to(ROOT).as_posix(), "--site", args.site, "--url", args.url,
               "--offline-file", args.offline_file, "--evidence-dir", args.evidence_dir]
    run = save_run(phase, site_info, checks, browser_info, council_counts, output_path, command)
    output = read_json_strict(output_path)
    write_followup(output, output_dir / "hosted-followup.md")
    print(json.dumps({"phase": phase, "status": run["status"], "checks": {status: sum(item["status"] == status for item in checks) for status in ("PASS", "FAIL")},
                      "runtime_sha256": site_info.get("site_runtime_sha256"), "data_index_sha256": site_info.get("data_index_sha256"),
                      "results": str(output_path)}, indent=2))
    return 0 if run["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
