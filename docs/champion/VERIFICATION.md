# HelioForge Champion 0.3.0 — verification and handoff

**Assessment date:** 28 September 2026. **Deliverable:** implemented local-evaluation app, compiled interface, source, starter scripts and evidence. **Production status:** not deployed; production approval is blocked pending the checks and decisions below. “Champion” is an edition name, not an award or certification.

## 1. Outcome

The supplied archive contains several generations. The implementation used `HelioForge-Hybrid-Lab-v0.2.0.zip`, the newer hybrid lab, rather than replacing it with the older repository. The original uploaded archive and diagnostic baseline were preserved. Local modifications were made in a separate candidate folder/repair branch. No remote repository was pushed, external AI called, customer data accessed, or production service changed.

Four baseline defects were reproduced: stale hybrid results during invalid input, lost model drafts on navigation, completed calculations reset by reconnection, and unexpected Host headers accepted. Repairs were implemented and regression-tested. Modernization added saved setups, validated workspace recovery, actual hybrid-run reopening, searchable history, keyboard commands, first-experiment guidance, clearer status and responsive controls. Two regressions introduced during this work—320px overflow and a blur-time toolbar replacement—were identified and repaired rather than concealed.

Engineering, design, security and verification were sequential role-based passes and self-review, not independently delegated agents or independent human assurance. The built-in local council is deterministic application logic; its role labels do not establish independent agent execution.

## 2. Actual tested results

| Check | Outcome | Evidence / boundary |
|---|---|---|
| Backend pytest suite | **PASS: 417 tests**, no failures/errors | `python-tests.xml`; includes original 404 plus 13 host/cache regressions |
| Strict TypeScript checking | **PASS** | `evidence/champion-final-suite-2.log` |
| Compiled production assets and single-file preview | **PASS** | Same integrated build log; prebuilt assets included |
| Frontend Node tests | **PASS: 98 tests**, no failures/skips | Original 65 plus 33 new validation/state tests |
| Existing browser journeys | **PASS: 18 general + 14 hybrid groups** | `../browser-validation.json`, `../hybrid-browser-validation.json` |
| Champion browser regressions | **PASS: 21 groups** | `browser-champion.json` |
| Total browser groups | **53 passed** | Actual Python API calculations; host transport adapter, not native networking |
| Local launcher / recovery | **PASS: 8 groups** | `launcher-validation.json`, `evidence/champion-launch-integration.log` |
| Layout checks | **PASS in emulation** | All 12 views at 320, 390, 768 and 1440 pixels; additional desktop captures |
| Uncaught browser exceptions | None observed in exercised journeys | Not a claim of universal crash freedom |
| Python lint | **BLOCKED** | Ruff was unavailable: `evidence/champion-lint-availability.log` |
| Native browser localhost navigation / CSP enforcement | **BLOCKED** | Browser returned `ERR_BLOCKED_BY_ADMINISTRATOR`; HTTP serving/headers checked separately |
| Native browser storage durability | **NOT VERIFIED** | About-blank tests use a storage adapter; real cache parsing/recovery code is exercised |
| Windows/macOS execution, physical devices, human UAT, assistive technology | **NOT RUN** | Scripts and task-based UAT procedure supplied |
| Real external AI integration, Docker, hosted CI and production monitoring | **NOT RUN** | No live provider call, container release, hosted workflow or rollout was claimed |

Counts identify different test layers and grouped browser journeys; they are not combined into a quality score or independent-user sample. These checks do not establish scientific calibration, investment-grade results, WCAG conformance, absence of vulnerabilities or production reliability.

The final integrated suite ran at `2026-09-28T21:04:31.460358+00:00` and exited **0** after **123.127 seconds** on the recorded container. This is test-suite duration, not an app startup benchmark. Runtime: Python 3.13.5, Node v22.16.0, Chromium 144.0.7559.96 built on Debian GNU/Linux 13 (trixie). Full versions are in `environment.json`. Hardware quotas and representative user-device performance were not measured.

## 3. Reproduction and exact command record

`BASELINE_RESULTS.csv` records actual commands, UTC timestamps, exit codes, durations and log locations. `evidence/commands.jsonl` is the machine-readable execution index. The final integrated command was:

```sh
python -m pytest apps/api/tests -q --junitxml=docs/champion/python-tests.xml
cd apps/web
npm run typecheck
npm run build
npm test
cd ../..
python scripts/browser-smoke.py --bridge --executable /usr/bin/chromium --screenshots
python scripts/browser-hybrid.py --bridge --executable /usr/bin/chromium --screenshots
python scripts/browser-champion.py --bridge --executable /usr/bin/chromium --screenshots
```

The actual invocation chained those steps with `&&`; a failed step stopped the invocation. The local Python API was started separately against an explicitly synthetic, isolated SQLite database. Browser scripts use the shipped standalone HTML and a host HTTP transport to that same API: **energy calculations are not mocked**. The new browser harness additionally adapts `localStorage`/UUID generation on `about:blank`; it tests the app's storage/recovery logic, not the browser's native persistence implementation. Fault injection waits on requests and drops a response only after the real API has saved the run.

For normal local validation, install development dependencies and Playwright's browser, start the API, and run the same scripts **without `--bridge` or the environment-specific Chromium path**. Direct-mode checks are supplied, not claimed as executed here. The updated GitHub workflow includes them; it was not submitted or run in a hosted account.

## 4. Findings, causes and preservation

`ISSUE_REGISTER.csv` is the canonical register. Each entry distinguishes baseline defects, introduced regressions and improvements, with supported cause, changed paths, evidence and remaining limits. Baseline targeted evidence is retained in `evidence/baseline-targeted.log` and `evidence/baseline-findings.json`; the original stale-result screen is in `evidence/baseline-stale-input.png`.

The toolbar failure received a discriminating reproduction: after typing, an unchanged blur event detached the intended button from the DOM. `evidence/champion-toolbar-reproduction.log` records both identity checks as false before repair. The final browser test asserts the original button remains connected after the same event and then exercises the workflow. This was a production-code repair, not a click-forcing workaround.

Other failed attempts are retained. One test compared two newly generated timestamps and was corrected to test a single captured record. Old history selectors were updated for explicit export buttons. New browser selectors were scoped to the visible toolbar or active modal instead of a hidden mobile-sidebar control. No assertions were disabled or changed to always pass. An interrupted wrapper attempt is described in `evidence/interrupted-attempt.md`; it is not counted as a success. Subsequent test failures led to a stated diagnosis or selector correction before the final integrated pass.

**Preserved models:** the numerical-engine files, hybrid input validation, SQLite store and canonical catalogue are byte-identical to the chosen baseline. `unchanged-model-files.json` records their SHA-256 hashes. There is **no database schema migration**. Existing storage optimization, PV/finance/acquisition, forecast/reliability/carbon, pilot evidence, export, lesson and deterministic council journeys remain in the app and were exercised where shown in the test matrix.

## 5. Architecture and feature contracts

The TypeScript namespace application compiles to one local JavaScript file, with no runtime JavaScript dependency or remote font required. It renders the original software-3D Canvas scene and data views. A validated `HybridInputs` configuration flows through `/api/hybrid/simulate`, Python validation, the existing hourly model, and `Store.save`; only a completed response is committed as a new displayed result. Comparisons retain the original inputs and battery endpoint context.

Named setups and the last valid hybrid workspace use a bounded, versioned browser cache. The cache stores inputs and API run IDs, not manufactured numerical records, passwords or API keys. Reopening a run retrieves its actual API record and checks structure/input alignment. Missing or damaged records are reported without a fake replacement. Clearing a shortcut does not delete a calculation. Generic model drafts are memory-only within a tab; user consent and credentials are excluded. Multiple tabs use last-writer-wins storage; no collaborative synchronization is implemented.

The API remains a **single-user local research service**. The launcher binds to loopback, sets explicit Host/Origin allow-lists, and disables external AI. Host validation is defense in depth, not user authentication. Existing write-Origin checks remain active. API responses are marked no-store; response headers were tested. Application records are not cryptographically signed or tamper evident. UI duplicate-submit guards and no automatic write retries do **not** create distributed exactly-once semantics; repeating an experiment through the API can create another valid record.

## 6. Screens, accessibility and performance limits

Actual candidate screenshots are included: `champion-desktop.png`, `champion-mobile.png`, `saved-setups-desktop.png`, and `saved-setups-mobile.png`. They depict the implemented interface in the declared bridged environment, not design mockups. Desktop and mobile captures were visually inspected alongside automated viewport-overflow checks. Keyboard commands, scene keyboard controls, mobile background/hidden-menu inertness, Escape focus return and reduced-motion behaviour were exercised.

These are **not** a complete accessibility audit. Screen-reader sessions, text zoom/translation coverage, every contrast pair, all dialogs on all devices, and physical touchscreen testing remain pending. WCAG 2.2 AA is a proposed target, not achieved conformance.

Compiled asset sizes are recorded in `asset-sizes.json` against the original local build. The preview grew from 369,757 to 423,849 bytes due to the added functionality. No speedup, memory-leak resolution, production latency percentile, universal FPS claim or historical customer-performance improvement is asserted. Performance budgets require agreement and representative-device measurements.

## 7. Crash, feedback and external-evidence coverage

No production telemetry, crash-service account, support tickets, app-store review dataset, real user sessions or field measurements were supplied or accessed. Crash incidence, affected-user counts, task-completion rates and production impact remain **unknown**. Browser exception listeners observed no uncaught exceptions only in the executed journeys. No customer quotations, ratings, sentiment totals or third-party assurances were invented. All model test data and saved-run fixtures are synthetic.

## 8. Recovery and release gates

The local launcher passed preflight, custom-port startup, HTML/asset serving, disabled external AI, Host rejection, occupied-port handling, process restart and small synthetic SQLite backup/restore checks. Restored inputs/results matched the original saved record; integrity checking passed. Automatic opening of a real user's browser, Windows/macOS native execution and large-database recovery were not tested.

| Phase / requested scope | Gate |
|---|---|
| Focused evidence-based diagnosis | **PASS**, within the supplied source and local evidence scope |
| Scoped local repairs | **PASS**, under the recorded API + bridged-browser verification conditions |
| Full supported-platform redesign sign-off | **BLOCKED**, native/device/assistive checks and approved performance budgets remain |
| Full validation / human beta sign-off | **BLOCKED**, genuine human UAT and native-browser coverage are pending |
| Release-preparation documents | **PASS as preparation only**; `RELEASE_PLAN.md` and `UAT.md` supplied |
| Public/production release or staged promotion | **BLOCKED / not authorized**; no rollout has occurred |

This is a useful **local evaluation build**, not a blanket production-ready declaration. The next human action is to run the included direct-browser UAT on the intended computer, confirm saved-work recovery and the modelling limits, and decide whether a separately secured staging environment is required. See the release plan for ownership, monitoring and approval requirements. No ongoing background monitoring is configured or promised.

## 9. Source and identity

Uploaded archive SHA-256: `ae9d7903c47ac07b93b48dc0086dda94a53dff0be6e4d328a3179985e6395bfc`.
Selected inner archive SHA-256: `add80834016aee6f8663292541b5bd5522a91b928b42b2f97273766cca729e7f`.

An upstream Git revision was not supplied with that archive. The working copy's local baseline branch is a diagnostic convenience, not an asserted upstream release commit. The delivered `RELEASE_MANIFEST.json` pins packaged file hashes; `scripts/verify-release.py` checks them. Hashes detect file drift but are not signatures or an independent security audit. Source changes and the change report accompany the full runnable source.

Technical guidance consulted: FastAPI advanced middleware (`https://fastapi.tiangolo.com/advanced/middleware/`), Starlette middleware (`https://starlette.dev/middleware/`) and Playwright BrowserType documentation (`https://playwright.dev/python/docs/api/class-browsertype`). Test claims above come from the supplied code and actual local logs, not those documentation pages.
