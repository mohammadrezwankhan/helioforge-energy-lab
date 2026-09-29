# Change report — Champion 0.3.0

Base: the uploaded `HelioForge-Hybrid-Lab-v0.2.0.zip`. The original upload was not overwritten. `SOURCE_CHANGES.patch` is the reviewable source/test/configuration patch against the isolated local baseline; the full ZIP also includes generated browser assets and documentation. Apply a patch only to a separate matching baseline and rebuild the frontend. The complete packaged app does not need patch application.

| Area | Changed / added files | Purpose |
|---|---|---|
| Main browser controller | `apps/web/src/app.ts` | Nonsensitive in-tab drafts; same-market reconnection preservation; busy-state restoration; navigation/focus; truthful interrupted-response handling |
| Hybrid input/result state | `hybrid-controller.ts`, `hybrid-core.ts`, `hybrid-types.ts`, `hybrid-views.ts` | Immediate invalid/stale gating; raw-draft retention; stable configuration comparison; duplicate blur-event guard; pending-operation locks |
| New workspace functions | `champion-core.ts`, `champion-controller.ts`, `champion-views.ts` | Bounded/validated cache, 20 named setups, missing/damaged-cache recovery, real run reopening, keyboard palette, quick-start guide |
| Visual integration | `champion.css`, `views.ts`, `index.html`, `tsconfig.json`, `scripts/build-web.mjs` | Shared workbench controls, dialog and narrow-screen layouts, motion/focus states, compiled stylesheet integration |
| API boundary | `apps/api/helioforge/main.py` | Explicit Host allow-list; API no-store and permissions headers; preserve Origin validation |
| Local start / recovery | `launch.py`, `start-windows.cmd`, `start-linux.sh`, `start-macos.command`, `scripts/check-launcher.py` | Preflight, loopback launch, explicit external-AI disablement, port collision handling, synthetic restart/restore checks |
| Tests | `apps/api/tests/test_champion.py`, `apps/web/tests/champion.test.mjs`, `scripts/browser-champion.py` | 13 API, 33 frontend, 21 grouped browser regressions |
| Existing tests / CI | TestClient base URL in API fixtures; history selector in `browser-smoke.py`; `.github/workflows/ci.yml` | Match intentional host boundary/new history markup; retain original assertions and add direct-mode Champion workflow |
| Metadata / generated assets | App versions, dashboard snapshot, package lock, `apps/web/dist/*`, `HelioForge-Preview.html` | Version 0.3.0 and rebuilt interface; catalogue version intentionally unchanged |
| Documentation | `START_HERE.md`, README/changelog/security/citation updates; `docs/champion/*` | Actual evidence, scopes, known limits, source patch, human UAT and controlled-release preparation |

No numerical-engine file, hybrid validation module, SQLite store implementation or canonical catalogue was changed. Hash evidence is in `unchanged-model-files.json`. No database migration, sign-in system, cloud synchronization, new provider integration or production deployment is included.

The Windows batch file uses CRLF line endings; shell starters retain executable permissions. Native Windows/macOS execution is still pending. Generated result/screenshot evidence is not independent scientific validation or human UAT.
