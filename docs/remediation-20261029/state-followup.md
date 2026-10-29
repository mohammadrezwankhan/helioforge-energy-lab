# Workspace migration and recovery follow-up

Date: 2026-10-29  
Scope: historical workspace schema support, migration receipts, and reversible import/recovery. The earlier `docs/remediation-20261028/state-agent.md` remains unchanged.

## Evidence classes

- **O — observed:** Git history and source show a workspace record at commit `87b1c2c` and the later audit-fix commit `e3e788c` using `helioforge.workspace.v1` with local-storage key `hf-workspace-v3`. `git log --all -S'helioforge.workspace.v0'` returns no matching commit. The `workspace-migration` source tests exercised v1/v2 records, raw backup, preview/confirm, interruption, and quota-denial retry.
- **R — reported:** The first-party README describes the workspace as local-first. `docs/VALIDATION.md` says cross-reload storage persistence was not exercised; neither statement is runtime proof of migration behavior.
- **I — inference:** With no earlier schema in repository history, v1 is the oldest supported migration source. V1 and v2 share all seven workspace data fields; the migration adds a versioned receipt and changes the envelope. Unknown v1/v2 fields are rejected, so this migration reports no silently dropped fields.
- **P — proposed:** The appraisal recommends schema validation, import preview, recoverable backups, explicit replacement confirmation, and failure without silent data loss.
- **U — unknown/open:** Manual browser/device behavior, actual browser quota behavior, cross-origin migration, and migration receipts after deployment remain unverified. The older generated-bundle `champion.test.mjs` was updated but not run because this task forbids a build.

## Implemented status

**V1 to v2 migration is implemented and source-tested.** New workspace records use `helioforge.workspace.v2` and carry a `migration` field. The parser accepts v1 and v2, validates the same workspace content fields, and normalizes v1 into v2 with a `helioforge.workspace-migration.v1` receipt containing source schema, target schema, time, changes, and losses.

An existing local v1 cache remains byte-for-byte unchanged until the user reviews and confirms migration. Ordinary persistence is blocked while that migration is pending. Confirmation first saves the exact current raw record to the one-slot recovery backup, then writes v2. A denied backup or v2 write leaves the active raw workspace intact and leaves the confirmation available for retry.

V1 and v2 file imports show source/target schemas, changes, and losses before confirmation. Users can download the operation receipt during preview and after confirmation. A v2 import keeps its existing persisted migration receipt while exposing the separate v2-to-v2 operation receipt in the current session. Unknown or unsupported fields fail validation instead of being dropped. Current and migrated records preserve their input/setup/run-reference fields on export/import round trips.

## Historical scope and changed files

- `apps/web/src/champion-core.ts`: v2 workspace contract, strict v1 migration, receipt validation, pending-local-migration protection, and receipt preservation.
- `apps/web/src/champion-controller.ts`: explicit preview/confirm for local v1 migration and file imports; exact raw backup; receipt download; retry-safe write behavior.
- `apps/web/src/champion-views.ts`: migration preview with source/target schemas, listed changes/losses, explicit confirmation, and one-slot backup replacement disclosure.
- `apps/web/tests/workspace-migration.test.mjs`: five source-compiled migration, round-trip, backup, interruption, retry, and saved-run-reference cases.
- `apps/web/tests/result-state-regressions.test.mjs`: v1 migration preview/receipt/backup regression.
- `apps/web/tests/champion.test.mjs`: updates the supported current-schema assertion and adds a v1 preservation assertion. This test reads `dist/app.js`, so integration must run it after the parent build.

Repository history does not support a v0 reader or earlier storage-key migration. No v0 shape was invented. The existing `hf-workspace-v3` key remains in place so the actual v1 cache is discoverable.

## Verification actually run

| Command | Result |
| --- | --- |
| `git log --all -S'helioforge.workspace.v0' --oneline -- apps/web/src apps/web/tests` | No matching historical v0 record. |
| `node --test apps/web/tests/workspace-migration.test.mjs` from the repository root | Passed 5/5, including custom inputs without a bundled result. |
| `node --test tests/result-state-regressions.test.mjs` from `apps/web` | Passed 18/18. |
| `npm --prefix apps/web run typecheck` from the repository root | Passed (`tsc -p tsconfig.json --noEmit`) after the follow-up and snapshot protocol type additions. |

No global test command, build, or generated asset step was run.

## Open review note

Subsequent review found that an unchanged v1 cache with custom inputs and no attached bundled result could lose its saved run ID during migration: `workspaceCache()` correctly clears a dirty result pointer, but the local migration then treated that as current v2 data. The controller now retains the validated v1 run ID only when normalized inputs are unchanged and the in-memory pointer still matches the v1 value. If inputs changed or the pointer was invalidated, the migration clears it and records the specific loss in the receipt. The source-compiled regression covers both paths. Parent integration also clears `ChampionState.lastRunId` on actual Hybrid input edits, so a changed-and-restored configuration cannot revive a stale pointer.

The backup slot holds one raw prior workspace; confirmation discloses that a new replacement overwrites an older backup. Download an older backup before confirming if it must also be retained.
