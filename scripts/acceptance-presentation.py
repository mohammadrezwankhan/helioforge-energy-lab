"""Execute supplied pairwise contexts with a bounded presentation/state oracle.

No physical-device, screen-reader, scientific, or whole-workspace acceptance claim.
Constrained here means a reproducible 150 ms request delay, not bandwidth emulation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("HELIOFORGE_EVIDENCE_DIR", ROOT / "docs/remediation-20261028"))
URL = os.environ.get("HELIOFORGE_ACCEPTANCE_URL", "http://127.0.0.1:4189/run/")
SITE = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site"))
plan = list(csv.DictReader((ROOT / "docs/remediation-20261028/source-plan/pairwise_test_design.csv").open(encoding="utf-8-sig")))
requested_ids = set(filter(None, os.environ.get("HELIOFORGE_ACCEPTANCE_CASE_IDS", "").split(',')))
if requested_ids:
    assert requested_ids <= {r['test_id'] for r in plan}, 'Unknown requested presentation test'
    plan = [r for r in plan if r['test_id'] in requested_ids]
report_name = 'presentation-retest-results.json' if requested_ids else 'presentation-results.json'
catalogue = json.loads((ROOT / "examples/hybrid-catalog.json").read_text())
default = json.loads((ROOT / "examples/hybrid-default.json").read_text())
valid = {"schema": "helioforge.workspace.v1", "saved_at": "2026-10-28T20:00:00Z", "inputs": default,
         "lesson_id": catalogue["lessons"][0]["id"], "last_run_id": None, "pinned_run_ids": [], "saved_setups": []}
fixtures = {"fresh": None, "valid_saved": json.dumps(valid), "old_schema": json.dumps({**valid, "schema": "helioforge.workspace.v0"}),
            "corrupt": '{"schema":broken'}
report = {"schema": "helioforge.presentation.execution.v1", "started_at": datetime.now(timezone.utc).isoformat(),
          "artifact_sha256": hashlib.sha256((SITE / "run/index.html").read_bytes()).hexdigest(),
          "environment": platform.platform(), "url": URL, "physical_devices": False,
          "oracle": "Deep link; input-mode navigation away/back; reload or cached offline navigation; draft-cache preservation; root/body overflow; no uncaught errors. Not full task behavior.",
          "constrained_profile": "150 ms delay per routed request; no bandwidth limit; desktop hardware",
          "old_schema_scope": "Unsupported v0 synthetic fixture; rejection/recovery, not a claimed historical migration.", "cases": []}


def action(page, locator, interaction):
    if interaction == "keyboard":
        locator.focus()
        page.keyboard.press("Enter")
    elif interaction == "touch":
        locator.tap()
    else:
        locator.click()


def navigate(page, route, interaction):
    if page.evaluate("location.hash") == "#" + route:
        return
    menu = page.locator('[data-action="menu"]')
    if menu.is_visible() and menu.get_attribute("aria-expanded") != "true":
        action(page, menu, interaction)
    action(page, page.locator(f'#sidebar [data-nav="{route}"]'), interaction)
    page.wait_for_function("r=>location.hash==='#'+r", arg=route)


with sync_playwright() as pw:
    for name in ["Chromium", "Firefox", "WebKit"]:
        try:
            browser = getattr(pw, name.lower()).launch()
        except Exception as exc:
            report["cases"].extend({**row, "status": "BLOCKED", "actual": str(exc)} for row in plan if row["engine"] == name)
            continue
        for row in [r for r in plan if r["engine"] == name]:
            start = time.perf_counter()
            item = {**row, "status": "FAIL", "owner": "integration", "browser_version": browser.version,
                    "expected": "Workspace navigation and reflow remain usable and recovery fixtures are preserved.",
                    "height": 568 if int(row["test_id"].split("-")[1]) % 3 == 0 else 1000 if int(row["viewport_px"]) >= 768 else 844,
                    "zoom": 1, "device": "desktop engine with emulated viewport/input"}
            context = None
            try:
                context = browser.new_context(ignore_https_errors=URL.startswith('https://127.0.0.1:'), viewport={"width": int(row["viewport_px"]), "height": item["height"]},
                    has_touch=row["interaction"] == "touch", reduced_motion="reduce" if row["motion"] == "reduced" else "no-preference")
                raw = fixtures[row["local_state"]]
                if raw is not None:
                    context.add_init_script("if(!sessionStorage.getItem('acceptance-seeded')){localStorage.setItem('hf-workspace-v3'," + json.dumps(raw) + ");sessionStorage.setItem('acceptance-seeded','yes')}")
                if row["load_condition"] == "constrained":
                    def delayed(route):
                        time.sleep(0.150)
                        route.continue_()
                    context.route("**/*", delayed)
                page = context.new_page()
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                response = page.goto(URL + "#" + row["workspace"], wait_until="load", timeout=45000)
                assert response and response.ok
                page.locator("#main-content h1").wait_for()
                assert page.locator('#sidebar [aria-current="page"]').get_attribute("data-nav") == row["workspace"]
                if row["load_condition"] == "offline_after_cached_load":
                    context.set_offline(True)
                other = "overview" if row["workspace"] != "overview" else "hybrid"
                navigate(page, other, row["interaction"])
                navigate(page, row["workspace"], row["interaction"])
                if row["load_condition"] != "offline_after_cached_load":
                    page.reload(wait_until="load")
                    page.locator("#main-content h1").wait_for()
                overflow = page.evaluate("({root:document.documentElement.scrollWidth-innerWidth,body:document.body.scrollWidth-innerWidth})")
                assert max(overflow.values()) <= 1, overflow
                assert not errors, errors
                if row["local_state"] in {"old_schema", "corrupt"}:
                    assert page.evaluate("localStorage.getItem('hf-workspace-v3')") == raw
                    assert "could not be read" in page.locator("#champion-toolbar").inner_text() or "not been overwritten" in page.locator("body").inner_text()
                if row["local_state"] == "valid_saved":
                    stored = json.loads(page.evaluate("localStorage.getItem('hf-workspace-v3')"))
                    assert stored["inputs"] == valid["inputs"]
                item.update(status="PASS", actual={"overflow": overflow, "uncaught_errors": errors, "hash": page.evaluate("location.hash")})
            except Exception as exc:
                item["actual"] = repr(exc)
                if context:
                    try:
                        folder = OUT / "presentation-failures"
                        folder.mkdir(exist_ok=True)
                        page.screenshot(path=str(folder / (row["test_id"] + ".png")), full_page=True)
                    except Exception:
                        pass
            finally:
                if context:
                    context.close()
            item["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
            report["cases"].append(item)
            report["summary"] = dict(Counter(r["status"] for r in report["cases"]))
            (OUT / report_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(row["test_id"], item["status"], flush=True)
        browser.close()
report["finished_at"] = datetime.now(timezone.utc).isoformat()
(OUT / report_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report["summary"]))
raise SystemExit(int(any(r["status"] != "PASS" for r in report["cases"])))
