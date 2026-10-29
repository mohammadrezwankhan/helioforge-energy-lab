# Independent follow-up review

Read-only review of hosted data partitioning/loading and champion workspace v1-to-v2 migration. No implementation files were changed.

## Findings

### P2 — Offline v1 migration can drop the saved-run reference

**Files:** `apps/web/src/champion-core.ts:86,97`; `apps/web/src/champion-controller.ts:97-101,77-80`; `apps/web/src/hybrid-core.ts:86`.

When a v1 cache is loaded, `initialChampionState` retains its `last_run_id` in `c.lastRunId`. But `workspaceCache()` emits that ID only when `!hybridDirty(h)`. In the hosted edition, only the bootstrap hybrid result is initially present. A restored custom configuration, or a bundled preset that has not finished lazy loading, has `h.resultInputs === null`; `hybridDirty` therefore returns true even though the user has not edited the restored configuration. If the user confirms migration while offline or before API restoration completes, `migrate-workspace` builds the v2 record from `workspaceCache(state)`, so `last_run_id` becomes null. Commit then replaces `c.lastRunId` with that null. The migration receipt still reports no losses, and its changes do not identify the dropped reference. The exact raw v1 cache remains in the recovery backup, so the run can be recovered manually, but the active v2 workspace no longer links to it.

Preserve the v1 run reference when the migrated inputs still match the stored configuration, even if the result is not hydrated. Clear the reference only when the configuration actually changes; add a regression case for a custom v1 workspace with a run ID migrated offline.

### P3 — Local migration refreshes `saved_at` without recording that change

**Files:** `apps/web/src/champion-core.ts:94-98`; `apps/web/src/champion-controller.ts:97-101`.

The local migration path constructs its target via `workspaceCache(state)`, which assigns a new `saved_at`. Its comparison intentionally omits `saved_at`, so no change is added to the migration receipt. The default receipt says existing workspace fields were retained. This is reasonable if `saved_at` means “last saved,” but the migration receipt and preview should say that timestamp was refreshed; alternatively, retain the source timestamp.

## Reviewed hosted-data path

The hosted builder partitions the 285 hybrid cases by system/scenario and the study results by catalogue page, checking for each catalogue study before writing its workspace asset. Browser loads require the content-addressed path, expected byte count and SHA-256 to match before parsing; hybrid result attachment is guarded by the selected state revision. Study workspaces show loading/error/retry states and install results only after all study IDs for the page match. `build-web.mjs` still creates the standalone preview from the complete compiled sources before producing the reduced hosted shell, so the offline standalone retains the full bundles.

The existing local hosted-data snapshot I inspected had 285 hybrid manifest keys, 12 workspace keys, and 297 data files. Its largest asset was 4,473,903 bytes, below the loader's 12,000,000-byte declared limit. The study builder maps every catalogue entry into its page asset and fails on a missing result; the current generated registry lists 59 studies. These are source and existing-artifact checks, not a newly built release or deployment verification.

## Commands and limits

Read `AGENTS.md`, `README.md`, `docs/METHODOLOGY.md`, `SECURITY.md`, and `docs/VALIDATION.md`; inspected the scoped TypeScript and build scripts, `cloudflare.json`, and the migration regression-test source. Read-only queries included `git status --short`, scoped `rg`/`type`/`more`, and Node queries against the existing local data index and model registry. No tests or builds were run, and no external or live deployment was contacted.

## Follow-up re-review — 2026-10-29

### Resolved — offline v1 migration can retain a valid saved-run pointer

The earlier P2 finding above is fixed in the current source. `champion-controller.ts:99-105` now restores the source `last_run_id` only when the normalized inputs and current in-memory pointer still match; when the pointer is stale or the inputs changed, the receipt explicitly records the loss. `workspace-migration.test.mjs` now covers the custom v1 workspace with no hydrated result and the edited-input case. The parent reports five focused tests passing; I did not rerun them.

### P2 — Storage provenance hashes the submitted request, not all inputs consumed by the solver

**Files:** `apps/api/helioforge/main.py:208-213,217-218`; `apps/api/helioforge/engines/storage.py:32-38`; `apps/api/helioforge/provenance.py:204`.

For the supported default storage request, all four time-series arrays are empty. The route calls `optimize_storage(p)`, where the engine creates `raw` and fills it with `demo_profile(request.market)` before constructing and solving with `p`. But `record()` calls `attach_result_provenance(..., inputs=inputs.model_dump())` using the original request and labels that digest scope `effective_model_inputs`. Thus the digest omits the generated load, PV and price arrays actually consumed by the solver. The source digest includes the profile-generation code, so this is not an untraceable output, but the input-hash label overstates what is hashed. Hash the materialized model input object, or describe this as a request-input digest and separately record the generated-profile identity/digest.

### P3 — Hybrid CSV `model_id` contains the version string

**File:** `apps/web/src/result-provenance.ts:94-103`.

The flattened export metadata chooses `record.model` before `provenance.model.id`. For hybrid records these are `hybrid-greedy-hourly-v1` and `hybrid`, respectively: the former is the model version, not the registered ID. This makes the `model_id` column inconsistent with the provenance envelope and awkward for consumers grouping by stable model ID. Prefer `model.id` for `model_id` and add a separate `model_version` column.

### P3 — Local v1 migration still refreshes `saved_at` without reporting it

**Files:** `apps/web/src/champion-core.ts:63,96`; `apps/web/src/champion-controller.ts:97,106`.

The local migration still builds the target using `workspaceCache(state)`, which assigns a new `saved_at`. Its comparison omits `saved_at`, so it adds no change receipt for the refresh; the base v1 receipt still says all existing workspace fields were retained. Preserve the source timestamp or add a specific change such as “Refreshed saved_at during migration.” This is a receipt-accuracy issue rather than loss of the recoverable raw record.

### Hosted minification review

`apps/web/package.json` pins `esbuild` at `0.28.2` under `devDependencies`; `scripts/hosted-data.mjs` applies it to the hosted JavaScript and CSS after the hosted data partition replaces the large generated bundles. `build-web.mjs` still forms `HelioForge-Preview.html` from the complete, unminified compiled source before producing the hosted edition. `cloudflare.json`’s adapted `location.protocol==="file:"` patch is guarded by an exact two-occurrence check in `build-cloudflare.mjs`. The current hosted artifact is a single minified inline script; I did not rebuild it or independently exercise the Cloudflare packaging guard in this follow-up.

## Follow-up commands and limits

Read-only inspection included `git status --short`, `type`/`more` of current migration, provenance, type and hosted-build sources, and targeted `rg` queries. I inspected the current hosted output and its directory listing. I did not run a build or tests, edit implementation files, contact a deployment/provider, or mutate a user account. Findings above are source review; the parent-reported focused migration result is not independently rerun.

## Final source re-review — 2026-10-29

All three follow-up findings above are resolved in the current source:

- **Storage effective-input identity:** `main.py:208-218` now computes provenance inputs through `storage_provenance_inputs()` while continuing to store the submitted request unchanged. The helper uses the solver's `demo_profile()` for the default profile and hashes canonical effective dataset inputs (market plus the four series) separately. The storage model contract lists `engines/storage.py`; `attach_result_provenance()` also adds `provenance.py` for the package-root call. Consequently both the profile implementation and the helper that materializes/hashes it are included in `source_revision`.
- **CSV identity and empty exports:** `result-provenance.ts:96-105,118` now prefers the stable `provenance.model.id`, exports the version separately, and includes the full `result_json` when the scientific rows list is empty. Regression-test source covers stable ID/version, collision preservation, and empty export payload. I did not run it.
- **Migration timestamp receipt:** `champion-controller.ts:106-107` now appends an explicit `saved_at` refresh change when migration changes the timestamp; the workspace migration test asserts the disclosure. I did not run it.

The earlier saved-run pointer fix remains present: it preserves the pointer only when inputs and the in-memory reference match, otherwise reporting the loss. No consequential issue remains from these three findings by source review. This re-review was read-only; no build or tests were run while the parent regenerated assets.
