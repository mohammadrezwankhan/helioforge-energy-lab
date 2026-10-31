# Remaining acceptance and release procedure

This is a runbook, not executed evidence. Use the immutable receipt and record exact artifact, OS, device, browser/version, viewport, native zoom, input, network, fixture, expected/actual result, operator, date, and attachments for each case. Preserve PASS, FAIL, BLOCKED, NOT_RUN and NOT_APPLICABLE separately. Unknown is not a pass.

## Unavailable acceptance

- Windows NVDA with Firefox or Chromium: no installed NVDA session was available. Run the journeys below with speech/braille output recorded, including labels, units, errors, busy/live messages, tables, charts, alternatives to canvas, dialog focus trapping and restoration to the real opener.
- Physical iPhone/iPad with Safari and VoiceOver, Android phone/tablet with Chrome and TalkBack, and native macOS Safari were unavailable. Desktop Playwright WebKit and touch emulation do not satisfy these checks.
- Test native 200% and 400% desktop zoom, OS text scaling, small landscape screens, browser bars, safe areas, on-screen keyboard, file selection, downloads, background interruptions, and tablet split screen. Verify the primary action remains reachable and drafts survive rotation/resize. The automated 63-check resize/capture suite uses desktop CSS viewports only.
- Recruit representative participants for the eight personas below. Observe uncoached mode identification and first valid task; ask where each number came from, what an edit invalidates, and what a hash proves. Record errors and recovery. No observed usability sessions were conducted here. A collapsible tablet-rail prototype and comparative usability test remain NOT_RUN; layout automation cannot select the better design.
- Real mid-range phone performance and field mobile/desktop p75 LCP/INP/CLS remain BLOCKED. No telemetry was added. Use at least three cold and three warm runs per actual device/network condition, retain every slow/failed observation, and distinguish lab interaction wall time from INP. Targets from the appraisal are LCP <=2.5 s, INP <=200 ms, CLS <=0.1; these are targets, not universal acceptance claims from this run.
- External-provider execution requires explicit processing/cost authorization, credentials, spending controls, and a selected provider. None were used. The 63 external council specifications remain BLOCKED, and the 126 public/local role/evidence specifications remain NOT_RUN as complete specifications. Unit tests and protocol mocks are separate evidence.

## Eight persona journeys (all full usability sessions NOT_RUN)

1. First-time visitor: choose each of the three starts; distinguish bundled examples, a new browser Terminal calculation, and advanced local Python. Explain synthetic data and operational limits.
2. Learner: complete one lesson experiment, explain the model limits, and distinguish a local quiz score from accreditation.
3. Educator: check prerequisites, save progress, export inputs and teaching evidence, and restore them on the same origin without silent loss.
4. Energy engineer: compare applicable cases; reconcile model/horizon, served load, initial/final SOC, units and source revision. A missing source revision currently forces descriptive-only comparison.
5. Researcher: reproduce a versioned input/seed, inspect uncertainty and solver feasibility, export full data, and explain which evidence has independent validation.
6. Market/finance analyst: distinguish synthetic from measured values, reconcile cash flows/units, exercise zero debt, undefined ratios and non-conventional cash flows, and avoid treating output as investment approval.
7. Reviewer/decision-maker: inspect conflicts, absent evidence, tampering, signatures and identity; require explicit human approval independently of a hash or council output.
8. Developer/maintainer: rebuild frozen assets, run CI, independently fetch deployed bytes, reconcile receipt/CSP/manifest/deployment, and update capability/model documentation together.

## Stateful tasks

Run the following in browser preview and local API mode where supported, on every available input/device family. Use controlled fixtures; do not reset personal storage.

| Sequence | Required result | Current automated evidence / remaining scope |
|---|---|---|
| Valid run -> edit -> invalid value -> compare/export | Stale result cannot become a current success | Source regressions and Terminal browser checks; full 12-workspace sequence remains NOT_RUN |
| Architecture A -> study-only B -> A | No incompatible hidden values or numeric study-only success | Catalogue gates and existing frontend tests; complete native-device journey NOT_RUN |
| Pin A -> other horizon/model B -> compare | Explicit incompatibility, no recommendation from mismatched totals | Comparison contract unit tests; missing historical result source revision remains open |
| Saved setup -> reload -> old schema -> recovery | Raw record preserved, explicit reversible migration | v1 import/backup tests and corrupt/unsupported v0 recovery; supported historical migration and migration receipt NOT_RUN |
| Valid sweep -> reversed bounds -> rerun | Old matrix/Pareto cleared | Targeted source regression and browser Terminal checks |
| Valid import -> tampered import -> valid retry | No partial replacement; retry works | Existing manifest tests/browser checks; native file-picker session NOT_RUN |
| Dialog -> Tab/Shift+Tab -> Escape | Focus stays inside and returns to opener | Automated keyboard coverage; spoken output/native AT NOT_RUN |
| External consent -> failure -> retry/cancel | No fabricated completion or implied provider stop | Mocked API protocol failures/timeouts; real provider task BLOCKED |
| Pending work -> edit/new work -> old response/error | New state retained | Source-compiled async regressions, including stale manifest rejection during a new sweep |
| Resize/connectivity interruption while editing/importing/exporting | Draft retained, incomplete action disclosed | CSS resize and limited offline navigation only; full interrupted native task NOT_RUN |

## Numerical and model acceptance still required

The registry has all 12 workspaces and 59 study cards. Default executions and original tests are useful evidence, but the acceptance fields intentionally retain NOT_RUN for independent hand checks and unexecuted per-study boundary/transfer checks. For each study, identify the authoritative equations and units, produce a tiny independently calculated fixture, test invalid/boundary inputs and finite outputs, repeat seeded results, inspect solver feasibility/convergence, and round-trip JSON/CSV/memo/cross-workspace transfer. Treat null metrics as undefined, not zero. The two newly sourced finance studies cite first-party implementation and do not claim independent validation.

## Publication and rollback

Production was not changed. The local candidate must not be described as deployed. Do not invoke provider calls or publish as an incidental acceptance step.

1. Review the branch/patch and unresolved F01–F14 gates. Obtain explicit publication authorization with the exact candidate digest.
2. Commit the reviewed source and frozen generated assets, run CI on that commit, and attach matching immutable build/runtime/header artifacts and test reports. The local receipt has a base commit plus dirty-source hashes; it is not a new commit or a successful remote CI run.
3. Publish the verified output directory as one unit. Do not regenerate studies, alter line endings, minify, or mix CSP/manifest/runtime from another build after hashing.
4. Independently fetch canonical production runtime and manifest through a permitted browser; hash exact decoded response bytes without newline normalization. Check effective CSP inline hashes, cache propagation with repeated fresh retrieval, redirects/query preservation, real 404, canonicals, robots, structured data, and all nine intended indexable pages. Keep `/run/` noindex and crawlable.
5. Confirm published preview/social images against capture metadata and the same runtime receipt. Current captures are local candidates.
6. Record the new deployment ID and CI run in a new immutable release receipt. Retain the current deployed baseline as the immediate rollback target: deployment `777ff5d5-be6d-4018-a0a4-392167601a7e`, source `74d6730e38323b69c180d7f4b4945d11010203f3`, runtime `a12384067a75ab7a3449c9b49936e923058bd7e92585f5a08f9c00ae735b203e`. The historical earlier deployment `662d8a2b-9c03-4a20-b7e8-e43ed19d4ae7` is a secondary reference, not the preferred undo target for this candidate. No rollback was executed.

## Local fixture and persistence

Local HTTP was altered by host AdGuard injection. Retained HTTP evidence is labeled accordingly. Final static acceptance uses HTTPS on loopback with a temporary self-signed certificate and exact generated CSP; only the automated loopback context ignores certificate trust errors. No system certificate store, AdGuard setting, production policy, or CSP directive was relaxed. Exact response bytes matched the built runtime. Local API browser tasks ran via HTTP and may include host injection; they are functional evidence, not exact static-distribution byte proof.

Workspace imports accept schema v1, show preview, require an explicit replacement action, and preserve a backup before commit. Unsupported v0 is rejected and raw recovery data remains available. There is no claimed historical v0-to-v1 migrator. Storage and API origins remain distinct; exported run IDs are references and may not resolve on a different installation. Existing user storage/databases were not used: browser contexts and API fixture databases were isolated. The original repository remains separate from the remediation worktree.
