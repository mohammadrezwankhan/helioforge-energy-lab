#!/usr/bin/env python3
"""Audit the generated public static pages and two workbench entry states.

Run on loopback after build-domain.mjs; existing full-audit suites still test
scientific workflow interactions separately.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

STATIC_ROUTES = (
    "/", "/models/", "/learning/", "/learning/capability-modes/",
    "/learning/model-glossary/", "/learning/terminal-balance/",
    "/help/", "/methodology/", "/about/",
)
WORKBENCH_ROUTES = ("/run/#hybrid", "/run/#compare")
VIEWPORTS = ((1440, 900), (820, 1180), (390, 844))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Loopback URL for generated static site")
    parser.add_argument("--report", help="Optional JSON evidence file")
    args = parser.parse_args()
    base = args.url.rstrip("/") + "/"
    observations, failures, console_errors = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda exc: console_errors.append("pageerror: " + str(exc)))
        def record_console(message: object) -> None:
            if getattr(message, "type") == "error":
                console_errors.append("console: " + str(getattr(message, "text")))

        page.on("console", record_console)

        def inspect(route: str, width: int, height: int) -> None:
            page.set_viewport_size({"width": width, "height": height})
            metrics = page.evaluate("""() => ({
                documentWidth: document.documentElement.clientWidth,
                scrollWidth: document.documentElement.scrollWidth,
                bodyScrollWidth: document.body.scrollWidth,
                hasContent: !!document.querySelector('main, #app .topbar'),
                clippedControls: [...document.querySelectorAll('button, input, select, a')]
                  .filter(el => {
                    const rect = el.getBoundingClientRect();
                    if (!rect.width || !rect.height) return false;
                    if (el.closest('.table-scroll, [aria-hidden="true"]')) return false;
                    return rect.left < -2 || rect.right > innerWidth + 2;
                  }).slice(0, 5).map(el =>
                    (el.textContent || el.getAttribute('aria-label') || el.tagName)
                      .trim().slice(0, 60))
            })""")
            observations.append({"route": route, "viewport": [width, height], **metrics})
            document_width = metrics["documentWidth"]
            if (
                metrics["scrollWidth"] > document_width + 1
                or metrics["bodyScrollWidth"] > document_width + 1
            ):
                failures.append(f"{route} at {width}px: horizontal overflow")
            if metrics["clippedControls"]:
                failures.append(f"{route} at {width}px: clipped controls {metrics['clippedControls']}")
            if not metrics["hasContent"]:
                failures.append(f"{route} at {width}px: empty application")

        for route in STATIC_ROUTES:
            response = page.goto(
                urljoin(base, route.lstrip("/")), wait_until="domcontentloaded", timeout=60000
            )
            if not response or response.status != 200:
                failures.append(f"{route}: HTTP {response.status if response else 'no response'}")
                continue
            page.locator("main#main").wait_for(state="visible")
            for width, height in VIEWPORTS:
                inspect(route, width, height)
            if route == "/" and page.locator(".boundary ul").count() != 1:
                failures.append("Landing capability boundary must contain one list")
            if route == "/models/":
                cards = page.locator("#registry-results .model-card")
                if cards.count() != 59:
                    failures.append(f"Registry has {cards.count()} models; expected 59")
                query = page.locator("#registry-search")
                query.fill("no-such-helioforge-study-identifier")
                if page.locator("#registry-results .model-card:visible").count() != 0:
                    failures.append("Search failed to hide nonmatching models")
                if not page.locator("#registry-empty").is_visible():
                    failures.append("Empty state did not appear")
                page.locator("#registry-clear").click()
                if page.locator("#registry-results .model-card:visible").count() != 59:
                    failures.append("Reset did not restore 59 models")
                first = page.locator("#registry-workspace option").nth(1).get_attribute("value")
                page.locator("#registry-workspace").select_option(first)
                filtered = page.locator("#registry-results .model-card:visible").count()
                if not 0 < filtered < 59:
                    failures.append("Workspace filter did not narrow models")
                page.locator("#registry-clear").click()

        for route in WORKBENCH_ROUTES:
            response = page.goto(
                urljoin(base, route.lstrip("/")), wait_until="domcontentloaded", timeout=120000
            )
            if not response or response.status != 200:
                failures.append(f"{route}: HTTP {response.status if response else 'no response'}")
                continue
            page.locator("#app .topbar").wait_for(state="visible", timeout=45000)
            for width, height in VIEWPORTS:
                inspect(route, width, height)

        browser.close()
    failures.extend(console_errors[:30])
    result = {
        "status": "passed" if not failures else "failed",
        "routes": len(STATIC_ROUTES) + len(WORKBENCH_ROUTES),
        "viewportChecks": len(observations),
        "observations": observations, "consoleErrors": console_errors, "failures": failures
    }
    if args.report:
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": result["status"],
        "routes": result["routes"],
        "viewportChecks": result["viewportChecks"],
        "failures": failures[:20],
    }
    sys.stdout.write(json.dumps(summary) + "\n")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
