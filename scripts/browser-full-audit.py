"""Cross-engine responsive, accessibility and keyboard regression evidence.

Run against a loopback preview or the published static /run/ URL. All actions are
browser-local; this suite never invokes a calculation API or external provider.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("terminal_audit", ROOT / "scripts/browser-terminal.py")
terminal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal)
WIDTHS = [320, 360, 375, 390, 414, 430, 600, 768, 820, 1024, 1280, 1440, 1920]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4180/")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path)
    parser.add_argument("--browsers", default="chromium,firefox,webkit")
    parser.add_argument("--widths", default=",".join(map(str, WIDTHS)))
    parser.add_argument("--no-axe", action="store_true")
    args = parser.parse_args()
    report = {"url": args.url, "profile": "Headless desktop CPU; unthrottled network; DPR 1; reduced motion; emulated viewports, not physical devices", "engines": [], "checks": []}
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    def check(name, ok, detail=None):
        report["checks"].append({"name": name, "status": "passed" if ok else "failed", "detail": detail})
        if not ok:
            print("FAIL", name, json.dumps(detail), flush=True)

    with sync_playwright() as pw:
        for engine_name in args.browsers.split(","):
            engine = {"name": engine_name, "pages": [], "errors": [], "networkFailures": []}
            report["engines"].append(engine)
            try:
                browser = getattr(pw, engine_name).launch()
            except Exception as exc:
                engine["unavailable"] = str(exc)
                print("UNAVAILABLE", engine_name, str(exc).splitlines()[0], flush=True)
                continue
            engine["version"] = browser.version
            context = browser.new_context(ignore_https_errors=args.url.startswith('https://127.0.0.1:'), viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda exc, target=engine: target["errors"].append(str(exc)))
            page.on("requestfailed", lambda req, target=engine: target["networkFailures"].append({"url": req.url, "error": req.failure}))
            page.add_init_script("""window.auditPerf={lcp:null,cls:0};
              try{new PerformanceObserver(l=>{for(const e of l.getEntries()) window.auditPerf.lcp=e.startTime;}).observe({type:'largest-contentful-paint',buffered:true});}catch{}
              try{new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.auditPerf.cls+=e.value;}).observe({type:'layout-shift',buffered:true});}catch{}
            """)
            response = page.goto(args.url, wait_until="networkidle")
            page.locator("#main-content").wait_for()
            engine["load"] = page.evaluate("({ ...window.auditPerf, navigation:performance.getEntriesByType('navigation').map(n=>({duration:n.duration,transferSize:n.transferSize,decodedBodySize:n.decodedBodySize})) })")
            engine["httpStatus"] = response.status if response else None
            if not args.no_axe:
                page.evaluate((ROOT / "apps/web/node_modules/axe-core/axe.min.js").read_text(encoding="utf-8"))
            for width in map(int, args.widths.split(",")):
                page.set_viewport_size({"width": width, "height": 844 if width < 768 else 1000})
                for route in terminal.ROUTES:
                    start = time.perf_counter()
                    terminal.navigate(page, route, width)
                    page.locator("h1").wait_for()
                    page.evaluate("document.fonts.ready")
                    overflow = terminal.page_overflow(page)
                    controls = terminal.offscreen_controls(page)
                    item = {"route": route, "width": width, "navigationMs": round((time.perf_counter()-start)*1000, 2), "overflow": overflow, "controls": controls}
                    check(f"{engine_name} {route} {width}px reflow", overflow["rootDelta"] <= 1 and overflow["bodyDelta"] <= 1 and not controls["clipped"], {"overflow": overflow, "clipped": controls["clipped"]})
                    if route == "hybrid":
                        clipped_labels = page.locator('.forge-counts span').evaluate_all("els=>els.filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)")
                        check(f"{engine_name} hybrid {width}px readable count labels", not clipped_labels, clipped_labels)
                    if width in [390, 820, 1440] and not args.no_axe:
                        axe = page.evaluate("""async()=>{const a=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return {violations:a.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),passes:a.passes.length,incomplete:a.incomplete.length}}""")
                        item["accessibility"] = axe
                        check(f"{engine_name} {route} {width}px WCAG AA", not axe["violations"], axe["violations"])
                    if args.screenshots and engine_name == "chromium" and width in [390, 820, 1440]:
                        page.screenshot(path=str(args.screenshots / f"{route}-{width}.png"), full_page=True, animations="disabled")
                    engine["pages"].append(item)
                print(engine_name, width, "12 workspaces checked", flush=True)

            # Real keyboard interaction: native dialog isolation and restoration.
            page.set_viewport_size({"width": 390, "height": 844})
            terminal.navigate(page, "hybrid", 390)
            menu = page.locator('[data-action="menu"]')
            menu.click()
            check(f"{engine_name} mobile navigation opens", menu.get_attribute("aria-expanded") == "true" and page.locator(".app-main").evaluate("e=>e.inert"))
            page.keyboard.press("Escape")
            check(f"{engine_name} mobile navigation restores focus", menu.evaluate("e=>e===document.activeElement") and menu.get_attribute("aria-expanded") == "false")
            command = page.locator('[data-champion-action="commands"]')
            command.focus()
            page.keyboard.press("Control+k")
            page.locator("#modal[open]").wait_for()
            focus_stayed_inside = True
            for _ in range(25):
                page.keyboard.press("Tab")
                focus_stayed_inside &= page.evaluate("!!document.activeElement.closest('#modal')")
            for _ in range(25):
                page.keyboard.press("Shift+Tab")
                focus_stayed_inside &= page.evaluate("!!document.activeElement.closest('#modal')")
            check(f"{engine_name} command dialog traps focus in both directions", focus_stayed_inside)
            page.keyboard.press("Escape")
            check(f"{engine_name} command dialog restores focus", command.evaluate("e=>e===document.activeElement"))
            field = page.locator('#hybrid-config input[name="solar_kw"]')
            field.focus()
            page.keyboard.press("Escape")
            check(f"{engine_name} Escape preserves field focus when navigation is closed", field.evaluate("e=>e===document.activeElement"))
            terminal.navigate(page, "markets", 390)
            tariff_trigger = page.locator('[data-experience-action="compare-tariffs"]')
            tariff_trigger.click()
            page.locator('[data-tariff-dialog][open]').wait_for()
            tariff_focus = True
            for key in ["Tab"] * 8 + ["Shift+Tab"] * 8:
                page.keyboard.press(key)
                tariff_focus &= page.evaluate("!!document.activeElement.closest('[data-tariff-dialog]')")
            check(f"{engine_name} tariff dialog traps focus in both directions", tariff_focus)
            page.keyboard.press("Escape")
            check(f"{engine_name} tariff dialog restores focus", tariff_trigger.evaluate("e=>e===document.activeElement"))

            # Reflow equivalents for a 1280px window at 200% and 400% zoom.
            # The 320px cases above cover 400%; this is not native browser zoom.
            page.set_viewport_size({"width": 640, "height": 500})
            for route in ["hybrid", "lessons", "compare", "storage", "council"]:
                terminal.navigate(page, route, 640)
                result = terminal.page_overflow(page)
                check(f"{engine_name} {route} 200% zoom-equivalent reflow", result["rootDelta"] <= 1 and result["bodyDelta"] <= 1, result)
            check(f"{engine_name} no uncaught errors", not engine["errors"], engine["errors"])
            context.close()
            browser.close()
    report["summary"] = {"passed": sum(c["status"] == "passed" for c in report["checks"]), "failed": sum(c["status"] == "failed" for c in report["checks"]), "unavailable": sum("unavailable" in e for e in report["engines"])}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"]), flush=True)
    return int(report["summary"]["failed"] > 0 or report["summary"]["unavailable"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
