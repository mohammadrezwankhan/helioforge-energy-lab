"""Genuine local candidate captures and bounded onboarding/resize checks."""
import hashlib
import os
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("HELIOFORGE_EVIDENCE_DIR", ROOT / "docs/remediation-20261028"))
IMAGES = OUT / "screenshots"
IMAGES.mkdir(exist_ok=True)
URL = os.environ.get("HELIOFORGE_ACCEPTANCE_URL", "https://127.0.0.1:4191/run/")
SITE = Path(os.environ.get("HELIOFORGE_ACCEPTANCE_SITE", ROOT / ".cloudflare/acceptance-v2/site"))
digest = hashlib.sha256((SITE / "run/index.html").read_bytes()).hexdigest()
report = {"schema": "helioforge.capture.v1", "captured_at": datetime.now(timezone.utc).isoformat(),
          "artifact_sha256": digest, "environment": platform.platform(), "production": False,
          "physical_device": False, "zoom": "100% desktop browser; native zoom not tested",
          "checks": [], "captures": []}

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    report["browser_version"] = browser.version
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce", device_scale_factor=1, ignore_https_errors=True)
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    page = context.new_page()
    page.goto(URL + "#hybrid", wait_until="load")
    actual = hashlib.sha256(page.request.get(URL).body()).hexdigest()
    assert actual == digest, (actual, digest)
    # The action must reach the real browser model and dismiss the dialog.
    page.locator('[data-champion-action="guide"]').click()
    page.get_by_role("button", name="Calculate a browser Terminal case", exact=True).click()
    page.locator('#terminal-run-form').wait_for(state="visible")
    assert page.locator('dialog[open]').count() == 0
    report["checks"].append({"name": "task-led Terminal entry", "status": "PASS", "actual": "Dialog dismissed; real candidate form visible at #compare."})
    for label, width, height in [("desktop", 1440, 1000), ("tablet", 820, 1180), ("mobile", 390, 844), ("social", 1200, 630)]:
        page.set_viewport_size({"width": width, "height": height})
        page.locator('#terminal-root').scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0,-80)")
        page.screenshot(path=str(IMAGES / f"{label}.png"), full_page=False, animations="disabled")
        report["captures"].append({"path": f"screenshots/{label}.png", "viewport": {"width": width, "height": height},
                                   "DPR": 1, "route": "#compare", "scope": "Desktop Chromium viewport emulation; genuine local candidate screenshot."})
    # Discover actual CSS width breakpoints, then check adjacent widths.
    widths = set()
    for css in (ROOT / "apps/web/src").glob('*.css'):
        for query in re.findall(r'@media[^\{]+', css.read_text()):
            widths.update(int(v) for v in re.findall(r'(?:min|max)-width\s*:\s*(\d+)px', query))
    report["width_breakpoints_px"] = sorted(widths)
    for width in sorted({max(320, n + offset) for n in widths for offset in [-1, 0, 1]}):
        page.set_viewport_size({"width": width, "height": 568})
        overflow = page.evaluate("Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-innerWidth")
        report["checks"].append({"name": f"Terminal breakpoint {width}px x 568px", "status": "PASS" if overflow <= 1 else "FAIL", "overflow_px": overflow})
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('#terminal-run-form [name="loadKw"]').fill('9.5')
    for width, height in [(844, 390), (390, 568), (390, 1000)]:
        page.set_viewport_size({"width": width, "height": height})
        assert page.locator('#terminal-run-form [name="loadKw"]').input_value() == '9.5'
    report["checks"].append({"name": "portrait/landscape/short/tall draft preservation", "status": "PASS", "actual": "9.5 input retained across three viewport changes; no native rotation claim."})
    context.tracing.stop(path=str(OUT / "onboarding-resize-trace.zip"))
    browser.close()
report["summary"] = {"PASS": sum(c["status"] == "PASS" for c in report["checks"]), "FAIL": sum(c["status"] == "FAIL" for c in report["checks"])}
(OUT / "capture-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report["summary"]))
raise SystemExit(int(report["summary"]["FAIL"] > 0))
