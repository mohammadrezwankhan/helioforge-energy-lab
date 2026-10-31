# Result and local-state integrity slice

Date: 2026-10-28  
Scope: F05 result/export boundaries and F11 workspace state handling, limited to the assigned frontend source files and dedicated regression tests. This report does not close either appraisal item globally.

## Evidence classes

- **O — observed:** The appraisal on PDF pages 30 and 32 says result model limits were not persistently exercised, and that local-state migration, quota failure, malformed imports, and recovery were not tested. The new regression harness reproduced stale-result races, permissive Terminal envelope parsing, missing workspace import protection, and missing comparison-contract behavior before the corresponding source changes.
- **R — reported:** The first-party README calls the workspace workflow local-first and describes the browser Terminal as a synthetic, bounded calculation. These are product documentation claims, not independent proof that browser storage or model fidelity was accepted; `docs/VALIDATION.md` explicitly says cross-reload storage persistence was not exercised.
- **P — proposed:** F05 calls for model/data identity, applicability, horizon, units, SOC policy, limitations, and source revision to remain attached to results and exports. F11 calls for schema checks, preview, recoverable backup, explicit replacement confirmation, and failure without silent data loss.
- **I — inference:** A missing source or dataset revision cannot safely be inferred from a catalog label, content hash, or release note. The comparison contract therefore reports those gaps and prevents a “directly comparable” classification until the calculation records carry them.
- **U — unknown/open:** Manual browser/device acceptance, cross-origin migration behavior, explicit migration between workspace schema versions, real storage quota conditions, and provenance availability on all deployed/API result types remain unverified here.

## Status

| Item | Bounded status | Evidence and remaining condition |
| --- | --- | --- |
| F05 | **Implemented; targeted source regressions verified; broader acceptance open.** | Hybrid hourly CSV repeats engine/data/horizon/unit/SOC/endpoints/hash/revision/limitations/warning fields. Comparison JSON embeds a compatibility contract; the view marks incompatible or provenance-incomplete totals as descriptive only. Delayed hybrid/Terminal operations, stale sweep results, stale successful imports, and stale rejected imports are covered. Bundled calculation records currently lack application source revision, so the contract correctly treats them as provenance-incomplete. Terminal exports still do not carry an independently supplied application source revision or applicability contract. |
| F11 | **Implemented; targeted source regressions verified; broader acceptance open.** | Workspace imports require the supported v1 schema, are size-bounded and previewed before explicit replacement, and preserve the prior raw cache as a backup before writing the imported cache. Corrupt/unsupported input and backup/main-cache write failures are tested to leave active state intact; a backup can be previewed and restored. A stale in-memory restore now resets its retry flag so pinned references can be fetched again. Cross-origin transfer and schema migration/receipt behavior remain open. |

## Changes in scope

- `apps/web/src/hybrid-core.ts`: per-state revision epochs and a comparison contract that classifies model/data/horizon/applicability/provenance compatibility and separately lists provenance gaps.
- `apps/web/src/hybrid-controller.ts`: stale async configuration/result guards and per-row CSV provenance; comparison JSON includes the compatibility contract.
- `apps/web/src/hybrid-views.ts`: comparison warning and visible engine/data/input-hash/source/dataset metadata.
- `apps/web/src/champion-core.ts`, `champion-controller.ts`, `champion-views.ts`: strict workspace parsing, async guards, preview/confirm, recoverable local backup, backup preview/restore/export, and storage failure handling.
- `apps/web/src/terminal-ui.ts`, `terminal-manifest.ts`: stale import/export/sweep guards (including rejection-path guards) and strict manifest envelope/payload/solver-contract validation.
- `apps/web/tests/result-state-regressions.test.mjs`: focused race, compatibility, CSV provenance, malformed/unsupported import, confirmation, backup, and quota regressions.

No numerical algorithms or tolerances were changed. This slice does not modify shared app/bootstrap, roadmap/integration pages, shared schemas, generated build logic, or deployment configuration.

## Verification actually run

| Command | Expected | Actual |
| --- | --- | --- |
| Initial red run of `node --test tests/result-state-regressions.test.mjs` from `apps/web` (before fixes) | New regression cases expose the identified gaps | Failed on stale hybrid/Terminal state, stale export, permissive envelope, absent workspace import/backup, absent comparison contract, and missing CSV metadata. This was intentional TDD baseline evidence. |
| `npm run build` from `apps/web` | TypeScript bundle builds | Passed once; dashboard and standalone preview were generated (13,306.1 KiB). This build preceded the last comparison-provenance refinements. |
| `node --test tests/result-state-regressions.test.mjs tests/champion.test.mjs tests/hybrid.test.mjs tests/hybrid-bundle-regressions.test.mjs tests/terminal-engine.test.mjs tests/terminal-manifest.test.mjs` from `apps/web` | Relevant existing built-bundle and dedicated tests pass | Passed 111/111 at that intermediate source point. |
| Initial red run after adding the rejected-stale-import regression: `node --test tests/result-state-regressions.test.mjs` from `apps/web` | A stale rejection leaves the new sweep busy state and notice intact | Failed at that new assertion: the import catch called unconditional `fail()`, changed the notice and reset busy. |
| Final `node --test tests/result-state-regressions.test.mjs` from `apps/web` | Source-compiled focused regressions pass after sweep/import race refinements | Passed 17/17. The test harness compiles the TypeScript source list into a temporary file, so this checks final source independently of generated `dist`. |

The final source changes after the one authorized build need to be included in the parent’s integration build and browser verification. No provider, hardware, publish, or deploy path was invoked.

## Limits and risks

- Strict comparison classification is intentionally unavailable when API/bundled records omit source or dataset revision or input digest. The frontend does not fabricate provenance. Confirm the actual source revision fields supplied by each result-producing path before calling direct comparison available.
- The workspace implementation accepts v1 only; it does not migrate older/newer schemas or issue a durable migration receipt. It retains one raw same-origin browser backup, not a cross-origin or cloud backup.
- Storage failures were simulated with the test harness, not induced in a browser with actual quota exhaustion. Manual preview, keyboard, download, and recovery behavior is not covered by this report.
- A source-compiled regression pass and an intermediate generated-bundle pass are not a deployed release receipt or proof of all F05/F11 close criteria.
- **Observed but not changed in this slice:** `syncHybridInput` advances the hybrid revision, marks the edited configuration dirty, and persists a workspace cache whose `last_run_id` is null, but it does not clear `ChampionState.lastRunId` in memory. System/scenario selection and explicit setup loading do clear it. The stale ID does not make a mismatched result eligible for restore because restore compares saved inputs with the current configuration, but a later retry may perform an unnecessary lookup; this was inspected from source, not independently exercised, and remains outside this bounded change.
