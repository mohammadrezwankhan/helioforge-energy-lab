# Verification evidence ledger

**Scope date: 2026-11-19.** Source commit `fb42eb4d9b0c87e692710e8e867ab5190ea831a7`, canonical Git tree `63c94b36fee39030b87065495d6151111d916969`. All 819 source blobs and 927 canonical entries were accounted for with Git identity, byte size, SHA-256 and mode. Runtime copies were reconciled against those source files both before and after each command below. The newly authored documentation has a separate complete candidate fingerprint and later independent QA/CI requirements; no future commit or deployment identity is invented here.

## Current local observations

Receipt IDs below identify retained raw commands, timestamps, logs and source manifests. PASS is scoped to the executed command; a successful probe that demonstrates a source defect is not evidence that the defect is fixed.

| Receipt | Actual UTC start → finish, 2026-11-19 | Result and scope |
|---|---|---|
| `01-dependency-install` | 22:30:11.312546 → 22:30:27.587900 | PASS — scoped preliminary pytest/Shapely installation; not a source test. |
| `02-annual-negative-export-comparator` | 22:30:43.773280 → 22:30:46.226300 | PASS reproduction — differing pre-existing numerical versions expose zero-storage baseline defect; retained unchanged. |
| `03-pinned-api-dependencies` | 22:31:13.685311 → 22:31:35.947661 | PASS — declared runtime pins installed in isolated execution target; optional development tools recorded separately. |
| `04-browser-dependencies` | 22:31:15.140999 → 22:31:19.877307 | PASS — locked npm ci, lifecycle scripts disabled; no manifest or lock change. |
| `05-api-pytest` | 22:31:55.483863 → 22:32:17.485096 | PASS — 1067 passing pytest progress items, no failure/skip symbols; double quiet suppresses final aggregate/subtest count. One Starlette TestClient deprecation warning. |
| `06-browser-typecheck` | 22:32:39.952130 → 22:32:42.602538 | PASS — locked TypeScript 7.0.2 no-emit typecheck. |
| `07-browser-unit-tests` | 22:32:54.381422 → 22:33:04.816556 | PASS —273 Node tests,0 failures/skips/cancel/todo. DOM/VM tests are not real-browser visual execution. |
| `08-publication-script-tests` | 22:34:05.714231 → 22:34:12.598142 | PASS — 39 tests and 75 subtests across four existing publication/asset-check test modules; Python 3.12. |
| `09-api-ruff` | 22:34:32.712252 → 22:34:32.762286 | PASS — Ruff 0.17.4 check, without fixes. |
| `10-hybrid-assets` | 22:34:32.721385 → 22:34:34.026647 | PASS — 285 cases; 1315 accepted roundoff values, maximum 9.094947017729282e−13; no stored artifact rewrite. |
| `11-study-assets` | 22:35:21.082897 → 22:35:24.532072 | PASS — 59 cases; 2473 accepted numeric differences, maximum 1.3280659914016724e−6; runtime duration separately observational; no rewrite. |
| `12-annual-comparator-exact-pins` | 22:44:27.116050 → 22:44:29.094162 | PASS reproduction — declared NumPy 2.4.6/SciPy 1.17.1/Pydantic 2.14.3 repeat the zero-storage EUR 876 comparator difference; no scientific fix. |
| `13-web-build` | 22:44:59.240973 → 22:45:03.059256 | PASS — locked web build in separate cache copy; all 819 tracked bytes/modes remain exactly source-identical after build. |
| `14-worked-numerical-labs` | 22:45:35.395310 → 22:45:36.772155 | PASS —six direct native examples; cost/SOC/conservation/DSCR assertions plus retained full outputs and actual catalogue. |
| `15-preview-structure` | 22:45:52.815122 → 22:45:53.225069 | PASS —fresh standalone runtime and stylesheet exactly match canonical compiled sources; structural only. |
| `16-launcher-preflight` | 22:45:52.796466 → 22:45:52.926094 | PASS —launch.py --check with declared pins; no server/browser/database launch. |
| `17-chromium-capability` | 22:45:52.825710 → 22:45:53.021900 | FAIL capability —about:blank process exits−6: socket Operation not permitted. Actual browser interaction/visual checks NOT_RUN. |


The complete two-interval, Terminal, finance, PV, hybrid and control results are described in [worked labs](../developer/WORKED_EXAMPLES_AND_LABS.md). The exact source-bound asset tests deliberately permit their recorded numerical tolerances; they do not demonstrate bit-for-bit numerical equivalence for every floating-point field or arbitrary input.

An independent source-only reviewer also reproduced the finance endpoint guard on 2026-11-19 22:30:17.758–22:30:18.225 UTC, using pre-existing NumPy 2.3.5/SciPy 1.17.0/Pydantic 2.13.4. It observed null at roots 1/2, approximately 0.5 for the interior control, and null debt-free DSCR/covenant for the valid request. This is a narrowly scoped function reproduction, not a supported-version matrix or final candidate QA. Receipt SHA-256: `d75abba34a56a62d237e397298495089a133d530af03c629c2c2719a6fbcbfa2`.

## Historical source CI

The GitHub provider read at **2026-11-19 22:23:30 UTC** returned the default latest set of **24 completed successful check runs** for the pinned source, with event times on **2026-11-18**. Six source workflow runs in the bounded query were successful. These are historical source observations, not candidate CI or proof that every current effective merge requirement is known.

The retained [Python 3.12 job](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/44412057369/job/135182534585) log explicitly reported **1067 passed, 1 warning, 28 subtests passed** on November 18. The raw job log identity is `57431c08e1158c1641ed4e789b41c206ee8c995f8167ebb1c296bcf691c15656`. The [browser job](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/44412057369/job/135182534147) log is retained separately with SHA-256 `259c05a52c390d4deef9887fd450e422e8e6b4d4c62d2493a562379a6d1c498f`. Provider event times remain original; the exact retrieval time of each later job-log request was not captured and is not replaced by its later persistence time. The exact job/run URLs are retained in the provider receipts.

Classic branch-protection lookup returned 403. Active ruleset metadata was visible, but that list alone does not resolve the entire effective PR policy. The Pages metadata connector returned an unsupported-endpoint 400; that does not establish that no site exists. Existing publication configuration is documented in the [release playbook](CI_CD_AND_RELEASE_PLAYBOOK.md).

## What remains separate

| Boundary | Review status / next evidence |
|---|---|
| Static scientific/source review | Core numerical engines, every registered study handler/schema, public control/transport contracts and source-specific limitations linked in the canonical chapters |
| Indexed/generated/media material | Complete file identity and explicit narrower disposition; parsing or hashes do not imply visual or semantic review of all payloads |
| Documentation quality | Final artifact/schema/link/renderer/source-preservation checks are retained in the exact candidate handoff; author checks are separate from independent QA |
| Real-browser execution | NOT_RUN after the scoped Chromium permission failure; structural/Node evidence remains valid within scope |
| Docker clean build | NOT_RUN; missing sibling build-script copies are a static risk |
| External council, weather/market feeds, Modbus, OCR on supplied documents | No live external/provider/device acceptance claimed; native/import unit tests do not establish successful service access |
| Scientific calibration / professional validation | Not supplied by this review; bundled data and numerical tests do not substitute for independent observations |
| Candidate CI / merge | Pending integration-owner verification on the actual documentation head/base and effective policy |
| Existing-site publication | Requires merge/build/deployment identity and distinctive live content; local HTML generation is insufficient |

## Evidence maintenance

Keep original failures, skipped/unavailable operations, version differences and log hashes. A later successful rerun gets a new receipt and its own source/candidate binding. Once a candidate changes, re-evaluate affected checks; never reuse a frozen QA decision for altered content. Keep final commit/deployment receipts outside the commit that introduces the documentation to avoid a self-referential identity. Source and workflow details: [.github/workflows/ci.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/ci.yml), [.github/workflows/hardened-ci.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/hardened-ci.yml), [.github/workflows/codeql.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/codeql.yml).

## Documentation repair round 1 observations

The initial independent candidate review identified six required documentation/helper repairs and two precision notes. The revised prose distinguishes the inclusive negative-price threshold, engineering-only FFT endpoint halving, the built-in ephemeral signer from generic key verification, and sign-count filtering from complete-cash-flow NPV evaluation. Source interface accounting includes 27 inherited help groups; catalogue metadata comprises **296 scalar controls plus 84 structured fields**, or 380 input records. No numerical/application implementation changed.

| Bounded repair check | Actual UTC observation on 2026-11-19 | Scope |
|---|---|---|
| Missing-index renderer control | 23:52:31.394455–23:52:31.852515 | Expected failure on the old helper; the published-directory control and ten original renderer tests passed. |
| Repaired renderer controls | 23:53:20.965830–23:53:21.652844 | All 12 focused tests passed, including missing/present directory indexes, unsafe schemes, traversal, image fallbacks, escaping and chapter behavior. Static helper execution, not a browser or live-site result. |
| Pinned helper lint | 23:54:25.523516–23:54:25.898425 | Both new documentation helpers passed unchanged Ruff 0.17.4 configuration. The earlier 17 diagnostics and original source lint receipt remain preserved; this is not full repository CI. |
| Repaired six worked examples | 23:56:23.857682–23:56:26.691022 | Same source/pins/inputs; nine explicit predicates retain their tolerances. All eight JSON outputs reproduce the original bytes, and all 819 cached source payloads/modes remain unchanged. |

The nine replacement checks also accepted their synthetic passing values and rejected nine corresponding failing values when compiled with Python optimization. This verifies guard effectiveness, not additional scientific cases. The actual output-directory nonoverwrite rejection has its own receipt. Original source receipts 01–17, the retained independent threshold/spectrum probes and launcher-help observation retain their original identities and times; no broad scientific suite, browser, provider or publication check was repeated.

The original candidate manifest used Python Path/component array ordering. Repair history preserves that manifest and fingerprint; the revised external manifest sorts record paths as strings to match integration consumers. This metadata-order reconciliation does not change the pinned source or retime execution evidence. Final candidate/commit/merge/deployment identities remain separate in the external handoff. Independent repair QA and current platform/publication gates remain pending.
