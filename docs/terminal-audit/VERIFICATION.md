# Terminal browser verification

**Status: browser acceptance passed.** This report covers the rebuilt standalone export, not the local Python API or hosted deployment.

## Build and environment

- Recorded audit base: `f0dc0bc3bfcf7e08936acacc8fd7d27b0d25e9e3`. This is not the exact published source identity. A passive verification on 27 October 2026 matched the runtime SHA below to the publication manifest at source revision `c1c67652e0b27c807ddfbcaaa9f987d37ca0f992`.
- Current audit: [Full responsive audit](../FULL_AUDIT_REPORT.md).
- Export runtime SHA-256: `fa69fa49e6d97ca75713334aefffd31ead1ec0861e5a39f2aee98bf5c1527d71`
- Browser: Chromium `156.0.8078.4`
- axe-core: `4.14.0`
- Runner: Python virtual environment with Playwright and Chromium installed
- Report: [browser-terminal.json](browser-terminal.json)

The run served the existing `.cloudflare/site` export from loopback. The browser did not call the Python API.

## Command

```powershell
& 'C:\Users\MRK\Downloads\misC\helioforge-integration-20261020\source\.venv-audit\Scripts\python.exe' -B scripts/browser-terminal.py --report docs/terminal-audit/browser-terminal.json --screenshots --screenshot-dir 'C:\Users\MRK\Downloads\Unclassified\mkgrid-terminal-evidence'
```

## Results

| Check | Result |
|---|---:|
| Browser acceptance checks | **251 passed, 0 failed** |
| Route and viewport layout checks | **96/96 passed** at widths 320, 375, 414, 768, 1024, 1280, 1440 and 1920 px |
| Visible interactive-control clipping checks | **96/96 passed** |
| axe-core route/view scans | **24, with 0 violations** (all 12 routes at 375 and 1440 px) |
| Uncaught page errors / same-origin or external console errors / failed requests / same-origin 4xx–5xx responses | **0** |

The separate body-width diagnostic recorded 41 overhangs: all 12 routes at 320, 375 and 414 px; two at 768 px; and three at 1024 px. The largest body overhang was 85 px at a 320 px viewport. `document.documentElement.scrollWidth` stayed within the viewport in all 96 cases, and no visible controls were clipped outside the viewport. Eleven controls inside `.pilot-board` horizontal scroll areas were logged separately as intentional scroll-area content.

## Exercised interactions

- The architecture atlas `data-system` card selected Hospital islanding, exposed `aria-pressed="true"`, and had a measured 44 px control height. The Architecture preset selector then changed to Remote renewable microgrid and back to Hospital islanding; the bundled baseline loaded.
- Original hybrid controls pinned the bundled reference and outage presets and displayed both in the original Scenario compare table.
- The reduced browser model returned 24 finite hourly rows with zero bus and SOC residuals. Pinning reference A, changing the import tariff from `0.25` to `0.35` EUR/kWh, and running B changed period cost from `15.61` to `21.85` EUR. The A/B delta reported `6.243` EUR (`40.000%`).
- Editing inputs marked the result stale and disabled pin, exports and sweep until the next run.
- The default two-axis sweep rendered all 49 matrix points, and selecting a point exposed its coordinates and metrics. Afterward, submitting lower `18` and upper `2` cleared the previous matrix: one matrix with 49 points before the invalid run, zero matrices and zero points afterward. Out-of-range bounds and non-positive logarithmic bounds also reported validation errors.
- JSON, CSV and Markdown exports passed checks. JSON contained a valid SHA-256 manifest and 24 rows; CSV contained 25 lines and `dataKind`, `status`, `flags` and `warnings` columns; Markdown included its flags, integrity payload and SOC caveat. Tampered manifest import was rejected; valid import reproduced the run after hash validation.
- Ctrl+K commands, the colon command opener, `:preset island`, `:pin`, `:diff`, `:export json`, and query-state reload were exercised.

The harness recorded zero page exceptions, console errors, failed resource requests or same-origin 4xx/5xx responses. External console messages and requests are tracked separately from same-origin failures.

## Visual evidence and limits

Captures were saved outside the repository and visually inspected:

- Desktop compare and Terminal workbench: `C:\Users\MRK\Downloads\Unclassified\mkgrid-terminal-evidence\terminal-desktop.png`
- Mobile compare and Terminal heading (375 px): `C:\Users\MRK\Downloads\Unclassified\mkgrid-terminal-evidence\terminal-mobile.png`
- Sweep matrix and selected case: `C:\Users\MRK\Downloads\Unclassified\mkgrid-terminal-evidence\terminal-sweep-results.png`

The browser matrix covers Chromium only. It does not verify native hosting/CSP behavior, browser file navigation, the Python API, other browsers, assistive-technology behavior or full WCAG conformance.

## Final rebuild and release checks

The final browser report was rerun after semantic selection-row repairs and the direct-child lesson decorator fix:251passed,0failed;24axe scans with0violations. Final typecheck and186frontend tests pass. The full Python suite passes653tests; two upstream TestClient deprecations remain visible. Ruff, source preservation, standalone consistency and58asset/three-page publication checks pass. Hallmark reports0hard failures and0reflex findings with48recorded finish warnings; this is not a fabricated58-gate certification.

## Original API-backed regression suite

After restoring full connection-status wording, the actual local API journeys pass: smoke18, hybrid14, Champion18, roadmap24 and completion10 (84 checks total). The separate API-connected axe run scans all12 routes with zero violations. The dense pilot row native drag test uses its exposed article edge rather than a text descendant; it still asserts the requested unsaved stage and empty fresh evidence note. No numerical API contract was changed.

The Linux CI browser exposed a tariff status/action overlap after the first local run. Tariff help, action and live status now occupy separate grid rows. The real completion journey checks pointer hit testing at all eight requested widths before native recalculation. Terminal acceptance and the full Hallmark render were rerun after this fix.

The final release is2.0.0 at the user’s request. Package/API metadata, citation, public facts, visible version, changelog and release manifest were updated together. The2.0.0 artifact passes186frontend tests,653Python tests, typecheck, Ruff and251browser checks with24zero-violation axe scans. Mathematical model and import schema IDs retain their existingv1identities because the calculations and contracts remain unchanged.

Final rendered-colour regressions cover both toolbar counts, all49Terminal sweep cells and all81original PV sensitivity buttons. Count contrast is14.286:1; PV minimum is9.817:1. The numeric heatmaps retain computed values and ordered colour cues in a readable dark range; the PV selector keeps44px targets in a local horizontal scroller. Rounded visible PV values are included verbatim in accessible names.
