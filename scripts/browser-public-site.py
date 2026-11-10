"""Audit public HelioForge routes at representative desktop, tablet and phone viewports.

Run against the built, locally served .cloudflare/site export. These results are
browser-emulation evidence only, not field Core Web Vitals or physical-device UAT.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ROUTES = (
    "/",
    "/run/",
    "/run/#hybrid",
    "/run/#compare",
    "/models/",
    "/learning/",
    "/learning/terminal-balance/",
    "/learning/model-glossary/",
    "/learning/capability-modes/",
    "/help/",
    "/methodology/",
    "/about/",
)
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 820, "height": 1180},
    {"width": 390, "height": 844},
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:4190/")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--screenshots-dir", type=Path)
    parser.add_argument("--no-axe", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {
        "scope": "Locally served static domain export; no external provider execution",
        "baseUrl": args.base_url,
        "engine": "chromium",
        "devices": "Emulated viewports with DPR 1; not physical devices",
        "routes": list(ROUTES),
        "viewports": list(VIEWPORTS),
        "checks": [],
        "a11yIncomplete": [],
    }
    checks: list[dict[str, object]] = report["checks"]  # type: ignore[assignment]
    incomplete: list[dict[str, object]] = report["a11yIncomplete"]  # type: ignore[assignment]

    def check(route: str, viewport: int, name: str, condition: bool, detail: object) -> None:
        checks.append({
            "route": route,
            "width": viewport,
            "name": name,
            "status": "passed" if condition else "failed",
            "detail": detail,
        })
        if not condition:
            print(f"FAIL {viewport}px {route} {name}: {str(detail)[:400]}", flush=True)  # noqa: T201 -- CLI audit

    axe_js = None
    if not args.no_axe:
        axe_js = (ROOT / "apps/web/node_modules/axe-core/axe.min.js").read_text(encoding="utf-8")
    if args.screenshots_dir:
        args.screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        report["browserVersion"] = browser.version
        context = browser.new_context(reduced_motion="reduce", device_scale_factor=1)
        page = context.new_page()
        events: list[dict[str, str]] = []
        page.on(
            "console",
            lambda message: events.append({"kind": "console", "text": message.text})
            if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: events.append({"kind": "pageerror", "text": str(error)}))

        for viewport in VIEWPORTS:
            page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
            width = viewport["width"]
            for route in ROUTES:
                events.clear()
                url = urljoin(args.base_url.rstrip("/") + "/", route.lstrip("/"))
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # A hash-only SPA transition is a same-document navigation; Playwright
                    # correctly returns no HTTP response. Validate its URL/state instead.
                    hash_transition = response is None and route.startswith("/run/#")
                    hash_matches = (
                        page.evaluate(
                            "(expected) => location.pathname === '/run/' && location.hash === expected",
                            "#" + route.split("#", 1)[1],
                        )
                        if hash_transition
                        else False
                    )
                    check(route, width, "HTTP response or same-document hash transition",
                          (response is not None and response.status == 200) or hash_matches,
                          response.status if response is not None else {"hashNavigation": hash_matches})
                    if route.startswith("/run/"):
                        page.locator("#main-content").wait_for(state="visible", timeout=30000)
                    else:
                        page.locator("main#main h1").first.wait_for(state="visible", timeout=30000)
                    page.evaluate("document.fonts.ready")
                    dimensions = page.evaluate("""() => {
                      const root = document.documentElement, body = document.body;
                      return {
                        rootScroll: root.scrollWidth, rootClient: root.clientWidth,
                        bodyScroll: body.scrollWidth, bodyClient: body.clientWidth,
                        main: !!document.querySelector('main')
                      };
                    }""")
                    check(route, width, "no document horizontal overflow",
                          dimensions["rootScroll"] <= dimensions["rootClient"] + 1
                          and dimensions["bodyScroll"] <= dimensions["bodyClient"] + 1,
                          dimensions)
                    if not route.startswith("/run/"):
                        navigation = page.locator('nav[aria-label="Main"] a')
                        check(route, width, "main navigation exists", navigation.count() >= 6,
                              navigation.count())
                        if width == 390:
                            targets = navigation.evaluate_all("""links => links.map(a => ({
                              text: a.textContent.trim(),
                              height: Math.round(a.getBoundingClientRect().height),
                              offscreen: a.getBoundingClientRect().right > innerWidth + 1
                            }))""")
                            check(route, width, "mobile navigation fits and is touch sized",
                                  all(item["height"] >= 44 and not item["offscreen"] for item in targets),
                                  targets)
                    if route == "/":
                        boundaries = page.locator(".boundary ul")
                        check(route, width, "capability boundary has one list",
                              boundaries.count() == 1, boundaries.count())
                    if route == "/run/":
                        icon = page.locator('link[rel="icon"]').first.get_attribute("href")
                        check(route, width, "root favicon asset", icon == "/favicon.svg", icon)
                    if axe_js:
                        page.evaluate(axe_js)
                        result = page.evaluate("""async () => {
                          const r = await axe.run(document, {
                            runOnly: {type: 'tag',
                              values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa']}
                          });
                          return {
                            violations: r.violations.map(v => ({
                              id: v.id, impact: v.impact,
                              elements: v.nodes.map(n => n.target)
                            })),
                            incomplete: r.incomplete.map(v => v.id),
                            passes: r.passes.length
                          };
                        }""")
                        check(route, width, "axe WCAG 2.2 AA", not result["violations"],
                              {"violations": result["violations"], "passes": result["passes"]})
                        if result["incomplete"]:
                            incomplete.append({"route": route, "width": width, "rules": result["incomplete"]})
                    if args.screenshots_dir and route in ("/", "/run/", "/models/"):
                        filename = route.strip("/").replace("/", "-") or "home"
                        page.screenshot(path=str(args.screenshots_dir / f"{filename}-{width}.png"),
                                        animations="disabled", full_page=False)
                    check(route, width, "no console or page exceptions", not events, list(events))
                except Exception as error:
                    check(route, width, "route completed", False, str(error))
        context.close()
        browser.close()

    failures = sum(item["status"] == "failed" for item in checks)
    report["summary"] = {
        "passed": sum(item["status"] == "passed" for item in checks),
        "failed": failures,
        "axeIncomplete": len(incomplete),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]), flush=True)  # noqa: T201 -- CLI audit
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
