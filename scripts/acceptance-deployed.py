"""Read-only publication evidence. Do not bypass denied access or mutate hosting."""
import hashlib
import json
import platform
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/remediation-20261028/deployed"
OUT.mkdir(parents=True, exist_ok=True)
report = {"observed_at": datetime.now(timezone.utc).isoformat(), "environment": platform.platform(),
          "production_changed": False, "requests": [], "browser": {}}
for path in ["app.json", "run/", "robots.txt", "sitemap.xml", "about/", "methodology/", ""]:
    url = "https://mkgrid.co.technology/" + path
    item = {"url": url}
    try:
        try:
            response = urllib.request.urlopen(url, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        data = response.read()
        item.update(http_status=response.status, headers=dict(response.headers), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                    status="PASS" if response.status == 200 else "BLOCKED")
        name = (path.strip("/") or "overview").replace("/", "-")
        (OUT / (name + ".body")).write_bytes(data)
        if response.status == 403:
            item["actual"] = data[:200].decode(errors="replace")
            report["requests"].append(item)
            report["remaining_routes"] = "BLOCKED: stopped scripted HTTP requests after access denial; this does not prove an outage."
            break
    except Exception as exc:
        item.update(status="BLOCKED", actual=repr(exc))
    report["requests"].append(item)
# One ordinary browser navigation, no changed fingerprint, credentials or alternate host.
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    try:
        response = page.goto("https://mkgrid.co.technology/run/", wait_until="domcontentloaded", timeout=45000)
        report["browser"] = {"engine": "Chromium", "version": browser.version, "physical_device": False,
                             "http_status": response.status, "headers": response.all_headers(), "title": page.title(),
                             "status": "PASS" if response.ok and page.locator("#main-content").count() else "BLOCKED"}
        page.screenshot(path=str(OUT / "browser-navigation.png"), full_page=True)
        # Large inline HTML can be evicted from Chromium's inspector body cache.
        # Use the ordinary browser request context and preserve that separate request.
        captured = page.request.get("https://mkgrid.co.technology/run/", timeout=45000)
        report["browser"]["capture_http_status"] = captured.status
        if not captured.ok:
            raise RuntimeError("Browser request context could not retrieve runtime bytes")
        data = captured.body()
        report["browser"]["runtime_response_sha256"] = hashlib.sha256(data).hexdigest()
        report["browser"]["digest_representation"] = "exact decoded HTTP response body bytes; no newline normalization"
        (OUT / "browser-runtime.body").write_bytes(data)
        if report["browser"]["status"] == "PASS":
            manifest_response = page.request.get("https://mkgrid.co.technology/app.json")
            report["browser"]["manifest_status"] = manifest_response.status
            if manifest_response.ok:
                manifest = manifest_response.json()
                report["browser"]["manifest"] = manifest
                report["browser"]["digest_matches_manifest"] = manifest.get("runtimeSha256") == hashlib.sha256(data).hexdigest()
            report["browser"]["routes"] = []
            for route in ["", "about/", "methodology/", "robots.txt", "sitemap.xml", "llms.txt", "missing-acceptance-20261028", "about?acceptance=20261028"]:
                result = page.request.get("https://mkgrid.co.technology/" + route, max_redirects=0)
                name = (route.replace("?", "-").replace("=", "-").strip("/") or "overview").replace("/", "-")
                body = result.body()
                (OUT / ("browser-" + name + ".body")).write_bytes(body)
                report["browser"]["routes"].append({"path": route, "status": result.status, "headers": result.headers,
                    "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
    except Exception as exc:
        report["browser"].update(status="BLOCKED", actual=repr(exc))
    finally:
        browser.close()
report["conclusion"] = "No deployment or live-provider invocation; identity remains unverified unless response bytes and manifest match."
(OUT / "observation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
