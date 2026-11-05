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
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import Error, Locator, Page, Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("HELIOFORGE_EVIDENCE_DIR", ROOT / "docs/remediation-20261028"))
URL = os.environ.get("HELIOFORGE_ACCEPTANCE_URL", "http://127.0.0.1:4189/run/")
SITE = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/site"))
with (ROOT / "docs/remediation-20261028/source-plan/pairwise_test_design.csv").open(
    encoding="utf-8-sig"
) as source:
    plan = list(csv.DictReader(source))
requested_ids = set(filter(None, os.environ.get("HELIOFORGE_ACCEPTANCE_CASE_IDS", "").split(",")))
if requested_ids:
    if not (requested_ids <= {r["test_id"] for r in plan}):
        raise AssertionError("Unknown requested presentation test")
    plan = [r for r in plan if r["test_id"] in requested_ids]
report_name = "presentation-retest-results.json" if requested_ids else "presentation-results.json"
catalogue = json.loads((ROOT / "examples/hybrid-catalog.json").read_text())
default = json.loads((ROOT / "examples/hybrid-default.json").read_text())
valid = {
    "schema": "helioforge.workspace.v1",
    "saved_at": "2026-10-28T20:00:00Z",
    "inputs": default,
    "lesson_id": catalogue["lessons"][0]["id"],
    "last_run_id": None,
    "pinned_run_ids": [],
    "saved_setups": [],
}
fixtures = {
    "fresh": None,
    "valid_saved": json.dumps(valid),
    "old_schema": json.dumps({**valid, "schema": "helioforge.workspace.v0"}),
    "corrupt": '{"schema":broken',
}
cases: list[dict[str, object]] = []
report: dict[str, object] = {
    "schema": "helioforge.presentation.execution.v1",
    "started_at": datetime.now(UTC).isoformat(),
    "artifact_sha256": hashlib.sha256((SITE / "run/index.html").read_bytes()).hexdigest(),
    "environment": platform.platform(),
    "url": URL,
    "physical_devices": False,
    "oracle": (
        "Deep link; input-mode navigation away/back; reload or cached"
        " offline navigation; draft-cache preservation; root/body"
        " overflow; no uncaught errors. Not full task behavior."
    ),
    "constrained_profile": "150 ms delay per routed request; no bandwidth limit; desktop hardware",
    "old_schema_scope": (
        "Unsupported v0 synthetic fixture; rejection/recovery, not a claimed historical migration."
    ),
    "cases": cases,
}


def collect_page_errors(target: list[str]) -> Callable[[Error], None]:
    def record(error: Error) -> None:
        target.append(str(error))

    return record


def action(page: Page, locator: Locator, interaction: str) -> None:
    if interaction == "keyboard":
        locator.focus()
        page.keyboard.press("Enter")
    elif interaction == "touch":
        locator.tap()
    else:
        locator.click()


def navigate(page: Page, route: str, interaction: str) -> None:
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
            cases.extend(
                {**row, "status": "BLOCKED", "actual": str(exc)} for row in plan if row["engine"] == name
            )
            continue
        for row in [r for r in plan if r["engine"] == name]:
            start = time.perf_counter()
            item: dict[str, object] = {
                **row,
                "status": "FAIL",
                "owner": "integration",
                "browser_version": browser.version,
                "expected": (
                    "Workspace navigation and reflow remain usable and recovery fixtures are preserved."
                ),
                "height": 568
                if int(row["test_id"].split("-")[1]) % 3 == 0
                else 1000
                if int(row["viewport_px"]) >= 768
                else 844,
                "zoom": 1,
                "device": "desktop engine with emulated viewport/input",
            }
            context = None
            page: Page | None = None
            try:
                context = browser.new_context(
                    ignore_https_errors=URL.startswith("https://127.0.0.1:"),
                    viewport={"width": int(row["viewport_px"]), "height": item["height"]},
                    has_touch=row["interaction"] == "touch",
                    reduced_motion="reduce" if row["motion"] == "reduced" else "no-preference",
                )
                raw = fixtures[row["local_state"]]
                if raw is not None:
                    context.add_init_script(
                        (
                            "if(!sessionStorage.getItem('acceptance-seeded')){localStorag"
                            "e.setItem('hf-workspace-v3',"
                        )
                        + json.dumps(raw)
                        + ");sessionStorage.setItem('acceptance-seeded','yes')}"
                    )
                if row["load_condition"] == "constrained":

                    def delayed(route: Route) -> None:
                        time.sleep(0.150)
                        route.continue_()

                    context.route("**/*", delayed)
                page = context.new_page()
                page.set_default_timeout(10000)
                errors: list[str] = []
                page.on("pageerror", collect_page_errors(errors))
                response = page.goto(URL + "#" + row["workspace"], wait_until="load", timeout=45000)
                if not (response and response.ok):
                    raise AssertionError
                page.locator("#main-content h1").wait_for()
                if not (
                    page.locator('#sidebar [aria-current="page"]').get_attribute("data-nav")
                    == row["workspace"]
                ):
                    raise AssertionError
                if row["load_condition"] == "offline_after_cached_load":
                    context.set_offline(True)
                other = "overview" if row["workspace"] != "overview" else "hybrid"
                navigate(page, other, row["interaction"])
                navigate(page, row["workspace"], row["interaction"])
                if row["load_condition"] != "offline_after_cached_load":
                    page.reload(wait_until="load")
                    page.locator("#main-content h1").wait_for()
                overflow = page.evaluate(
                    "({root:document.documentElement.scrollWidth-innerWidth,body:"
                    "document.body.scrollWidth-innerWidth})"
                )
                if not (max(overflow.values()) <= 1):
                    raise AssertionError(overflow)
                if errors:
                    raise AssertionError(errors)
                if row["local_state"] in {"old_schema", "corrupt"}:
                    if not (page.evaluate("localStorage.getItem('hf-workspace-v3')") == raw):
                        raise AssertionError
                    if not (
                        "could not be read" in page.locator("#champion-toolbar").inner_text()
                        or "not been overwritten" in page.locator("body").inner_text()
                    ):
                        raise AssertionError
                if row["local_state"] == "valid_saved":
                    stored = json.loads(page.evaluate("localStorage.getItem('hf-workspace-v3')"))
                    if not (stored["inputs"] == valid["inputs"]):
                        raise AssertionError
                item.update(
                    status="PASS",
                    actual={
                        "overflow": overflow,
                        "uncaught_errors": errors,
                        "hash": page.evaluate("location.hash"),
                    },
                )
            except Exception as exc:
                item["actual"] = repr(exc)
                if context and page is not None:
                    try:
                        folder = OUT / "presentation-failures"
                        folder.mkdir(exist_ok=True)
                        page.screenshot(path=str(folder / (row["test_id"] + ".png")), full_page=True)
                    except Exception as capture_error:
                        item["capture_error"] = repr(capture_error)
            finally:
                if context:
                    context.close()
            item["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
            cases.append(item)
            report["summary"] = dict(Counter(r["status"] for r in cases))
            (OUT / report_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(row["test_id"], item["status"], flush=True)  # noqa: T201 -- CLI report output.
        browser.close()
report["finished_at"] = datetime.now(UTC).isoformat()
(OUT / report_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report["summary"]))  # noqa: T201 -- CLI report output.
raise SystemExit(int(any(r["status"] != "PASS" for r in cases)))
