# HelioForge remediation and acceptance

Completed local work on `repair/appraisal-20261028` from baseline `74d6730e38323b69c180d7f4b4945d11010203f3`. **Production was not changed. Full appraisal acceptance remains open.**

Tested static runtime: `9f54ad506e6dcfa6ae2534c39531bcf7847549398f9e72a4db5f9a797f718d52` (13,630,124 exact bytes). [Immutable release receipt](receipts/release-f0bd3cbc8ce01f34c782ae2ff53d752294856b529136d91d666ed86f4b713038.json). Source remains a reviewable dirty worktree with a full file-hash manifest; no candidate CI run, commit publication or deployment was performed.

## What changed

- Versioned capability, 59-study model registry and council protocol; accurate local/external invocation counts and failure metadata.
- Study CSV/memo provenance, sources for two finance studies, stale async response guards, sweep invalidation, guarded comparison and preview/backup workspace imports.
- Frozen-data replay checks and content-addressed build receipts, genuine local release captures, three task starts, nine-page local documentation/content distribution.

## Executed evidence

| Suite | Executed | Pass | Fail | Blocked | Not run |
|---|---:|---:|---:|---:|---:|
| Python final | 659 | 659 | 0 | 0 | 0 |
| Frontend final | 212 | 212 | 0 | 0 | 0 |
| Catalogue gates/invariants | 864 | 864 | 0 | 0 | 0 |
| Study defaults/digests | 59 | 59 | 0 | 0 | 0 |
| Responsive/axe/keyboard | 654 | 654 | 0 | 0 | 0 |
| Terminal journeys | 251 | 251 | 0 | 0 | 0 |
| Presentation contexts | 157 | 156 | 1 | 0 | 0 |
| Presentation targeted retest | 1 | 1 | 0 | 0 | 0 |
| Capture/onboarding/breakpoint | 63 | 63 | 0 | 0 | 0 |
| Deployed crawler contract | 18 | 18 | 0 | 0 | 0 |
| API study/browser journeys | 24 | 24 | 0 | 0 | 0 |
| API integration journeys | 10 | 10 | 0 | 0 | 0 |
| Performance lab loads | 12 | 12 | 0 | 0 | 0 |
| Performance interaction measurements | 96 | 96 | 0 | 0 | 0 |
| Council role/evidence specifications | 0 | 0 | 0 | 63 | 126 |
| Independent per-study hand checks | 0 | 0 | 0 | 0 | 59 |
| Persona usability sessions | 0 | 0 | 0 | 0 | 8 |
| Build/domain/security contract tests | 7 | 7 | 0 | 0 | 0 |

Counts are per suite and non-additive. [Machine-readable scopes and evidence](suite-ledger.json). Presentation design covers 620 pair values in 33,696 declared contexts; 157 executed contexts establish only the stated presentation/state oracle. Catalogue checks cover 285 applicable numerical cases, 349 study-only gates and 230 not-applicable gates. Per-study default runs do not prove hand benchmarks or complete boundary/export acceptance.

## Dispositions and limitations

**Verified fixed locally:** provenance omission in study exports; stale study/Hybrid/Terminal continuations including rejected import during a newer sweep; workspace preview/backup safeguards; misleading local council invocation metadata; empty source references in two study defaults. [Separate engineering review](INDEPENDENT_REVIEW.md).

**Already resolved with deployed evidence:** the old About browser-versus-Python discrepancy. Existing production runtime/manifest identity and three-page crawler controls were observed successfully, but the same-commit CI artifact does not match the deployment.

**Implemented but not accepted in full:** capability/model contracts, new public content, screenshots, onboarding and CI controls. [F01–F14 ledger](ISSUE_LEDGER.md) preserves all original priorities and complete remaining conditions; no F item is labeled fully closed merely because code exists.

**Open code/product work:** complete source-revision provenance for normal Hybrid records and remaining legacy export/transfer paths; supported historical state migration with receipts; direct applicable-contract links for every retained result; measured hosted-shell/data-splitting optimization; comparative tablet-rail usability experiment. These are not hidden behind hardware blockers.

**Blocked or not run:** native/physical device and screen-reader tasks, uncoached usability, real-phone/field performance, 189 complete council role/evidence specifications, independent hand checks for each of 59 studies, exhaustive higher-order task states across all workspaces, and candidate remote CI/deployment reconciliation. [Manual acceptance and rollback runbook](MANUAL_ACCEPTANCE.md).

## Measurement and failure integrity

All original failure logs are retained. The initial metadata inventory failed two studies; source-reference corrections pass on rerun. Test-fixture expectation errors, the Terminal harness URL error, a Windows output-directory lock, and an interrupted provider-mock test are distinguished from application regressions. Local HTTP AdGuard injection changed response bytes/CSP; those runs are retained but are not exact static artifact acceptance. Final static suites use HTTPS loopback and verify the original bytes without changing host security settings. API UI tasks remain HTTP functional evidence. An initial warm-performance harness used fragment navigation rather than reload; those measurements are invalid and retained separately.

Lab measurement completion is not a pass against LCP/INP/CLS targets. Field INP and p75 remain null. Real-world cache propagation, native downloads, user profile behavior and provider spend were not claimed.

## Artifacts

- [Issue ledger](issue-ledger.json), [suite ledger](suite-ledger.json), [workspace results](workspace-results.json), [study cards/results](study-acceptance-results.json), [council specifications/results](council-results.json).
- [Screenshots and capture metadata](capture-results.json), [desktop](screenshots/desktop.png), [tablet](screenshots/tablet.png), [mobile](screenshots/mobile.png), [trace](onboarding-resize-trace.zip).
- [Performance raw runs](performance-results.json), [deployed observations](deployed/observation.json), [source file hashes](source-file-hashes.json), and retained logs in `logs/`.
- Reviewable source branch and `review.patch`; delivery archive contains changed/new files and evidence, with a separate file manifest. No production publication or paid provider calls.

The first exact-byte presentation run had 156 PASS and one loopback TLS failure before app load (PAIR-141); the separate targeted retest passed. All 157 case IDs consequently have a passing execution, across 158 attempts with one retained failed attempt. This is bounded presentation acceptance, not exhaustive behavior coverage.
