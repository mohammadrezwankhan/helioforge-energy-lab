# Verification — 18 October 2026

Software evidence for the 59-study release; see the [completion ledger](COMPLETION.md) for all twelve views and external prerequisites. This does not establish scientific, regulatory, identity or accessibility certification.

| Check | Observed result |
|---|---|
| Ruff on apps/api | Passed |
| Python full unit/API suite | **579 passed**, 0 failures/errors/skips, confirmed from JUnit XML |
| Generated Python examples | **59** finite study envelopes across 12 navigation IDs |
| Strict TypeScript and build | Passed; no browser runtime package dependencies |
| Frontend tests | **141 passed**, 0 failures/skips |
| npm audit, moderate threshold | 0 known vulnerabilities at check time |
| Existing Playwright suites | **74 passed**: smoke 18, hybrid 14, Champion 18, roadmap 24 |
| Remaining-roadmap browser suite | **10 passed**: requirements panels, four geometry visuals, tariff editing/staleness, real CSV/GeoJSON/document/telemetry import journeys, nine Foundation quiz gates, saved-run scenes, all views at 390px |
| axe-core 4.14.0 | **0 automated violations** across 12 default desktop views, including enhanced contrast; incomplete/manual checks remain |
| Standalone parity | Exact compiled JavaScript/CSS equality with generated HTML |
| Cloudflare export checks | Public facts, canonical, schema, digest, assets and source-file exclusions pass |
| Dedicated MKGrid export | 3 content pages, 20 files; canonical/schema/runtime digest checks pass |
| Independent completion review | Rare-event confidence interval, bearing-envelope score and ICP-retention findings independently rechecked after repairs; no remaining blocker within the review scope |
| Live Open-Meteo request | 24 Paris hourly rows retrieved 2026-10-17T22:07:44.275184Z |
| Frame scheduling | 120 headless Chromium samples, median/p95 16.7 ms; not rendering latency or a device FPS guarantee |

Reports: [original browser](../browser-validation.json), [hybrid](../hybrid-browser-validation.json), [Champion](../champion/browser-champion.json), [59 studies](browser-validation.json), [new interactions](completion-browser-report.json), [accessibility summary](accessibility-summary.json), [frame cadence](frame-cadence.json). Full logs, JUnit XML, axe incomplete-node output and screenshots are retained in the local delivery output. CI uploads its independently generated browser evidence.

No uncaught JavaScript exceptions were observed in the checked journeys. Browser proof includes actual P-256 signing, tamper rejection and co-signature verification, full annual CSV export and snapshot-only boundaries. Screenshots of advanced graphics, synchronized scenes and mobile layouts were captured; selected images were visually inspected. Integration repairs include MutationObserver feedback starvation, synchronous lesson-score persistence and cached-page lifecycle handling. The export checker now compares complete configured public features/steps instead of an obsolete fixed count.

Environment: Windows, Python 3.12.14, Node 24.20.0, TypeScript 5.8.3, NumPy 2.3.5, SciPy 1.17.0, Shapely 2.1.2. Python emitted two dependency deprecation notices (TestClient/httpx and AnyIO BlockingPortal alias). CI separately exercises Python 3.11/3.12/3.13 and browser flows. A local pass does not claim remote CI completion. Floating-point schedules may vary across solver/BLAS environments; CI regenerates examples and tests mathematical invariants.

Public publication follows these gates. The live app.json source revision/runtime digest, Git merge and signed release receipt identify the delivered build. Paid AI, ENTSO-E credentials, live Modbus, real survey reconstruction, authenticated document provenance, independent calibration, assistive-technology sessions and physical-device performance were not exercised. They remain explicit external requirements.
