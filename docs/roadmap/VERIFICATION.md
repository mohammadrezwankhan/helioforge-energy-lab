# Verification — 17 October 2026

The following checks ran on the local full-spectrum branch. They are software evidence, not scientific, regulatory or accessibility certification. The five independent-review counterexamples and their repairs are recorded in [DELIVERY.md](DELIVERY.md).

| Check | Result |
|---|---|
| `python -m ruff check apps/api` | Passed |
| `python -m pytest apps/api/tests -q` | 521 passed; 0 failures/errors/skips, confirmed from JUnit XML |
| `python scripts/generate-studies.py` | 39 finite examples, all 12 actual navigation IDs; 3,635,648-byte JSON payload |
| `npm --prefix apps/web run typecheck` | Passed strict TypeScript |
| `npm --prefix apps/web run build` | Source JS/CSS and standalone preview built, no runtime package dependencies |
| `npm --prefix apps/web test` | 130 passed; 0 failed/skipped |
| `python scripts/browser-smoke.py --url http://127.0.0.1:8017` | 18 passed against real loopback API |
| `python scripts/browser-hybrid.py --url http://127.0.0.1:8017` | 14 passed; includes 320/390px, cameras, saved runs, lessons, offline boundaries |
| `python scripts/browser-champion.py --url http://127.0.0.1:8017` | 18 passed; native browser storage, 320/390/768/1440px, workspace recovery and keyboard navigation |
| `python scripts/browser-roadmap.py --url http://127.0.0.1:8017` | 24 passed; all 39 Python experiments through real browser forms, 8,760 CSV records, stale/error states, actual signing/tamper rejection/co-signing, tariff dialog, pilot dragging, raw paths, all 12 mobile views and file preview |
| Research display control check | Moving window changed to 8, cutoff changed to 0; displayed values updated |
| `node scripts/check-preview.mjs` | Exact source-built JS/CSS parity with standalone HTML |
| `node scripts/build-cloudflare.mjs` | Passed; snapshot-only runtime patches applied |
| `node scripts/build-domain.mjs` | Passed; dedicated MKGrid artifact generated |
| `node scripts/check-domain.mjs` | Passed; 3 content pages, 20 files, canonical/schema/runtime digest assertions |
| `git diff --check` | Passed |

Browser reports are `docs/browser-validation.json`, `docs/hybrid-browser-validation.json`, `docs/champion/browser-champion.json` and `docs/roadmap/browser-validation.json`. Screenshots of PV sensitivity, interval storage, hybrid scene, markets, investment and mobile council were captured in the delivery output directory and visually inspected. There were no uncaught JavaScript errors in the checked journeys.

Local versions: Windows, Python 3.12.14, Node 24.20.0, TypeScript 5.8.3, NumPy 2.3.5, SciPy 1.17.0, FastAPI 0.142.0, Pydantic 2.13.4. The Python suite emitted two dependency deprecation notices concerning TestClient/httpx and the AnyIO BlockingPortal alias; neither was a test failure. CI independently exercises its Python matrix. Floating-point/solver schedules can vary by platform, so CI regenerates study examples and validates mathematical invariants rather than promising identical floating-point bytes across environments.

The visible hybrid scene's 120-sample headless Chromium requestAnimationFrame cadence measured a 16.7 ms median and 16.7 ms p95. This measures scheduling in one environment, not rendering latency, a physical device or a universal 60 FPS guarantee. See `frame-cadence.json`.

No public deployment, Git push, paid provider call, live market connection, assistive-technology session, physical-device session, independent calibration, field alarm validation, or production Astra execution was performed. The prepared archive and signed receipt identify the exact local commit and build hashes. The public site was read successfully during the audit and remains separate from this local implementation.
