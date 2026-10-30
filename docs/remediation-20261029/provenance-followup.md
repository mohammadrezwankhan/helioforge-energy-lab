# Source-bound result provenance follow-up

## Status and scope

Implemented a versioned `helioforge.result-provenance.v1` envelope for newly computed numerical API results, the hybrid hourly calculation, experimental study results, and synthetic dashboard snapshots. Existing rows returned by the store are not migrated or stamped; the frontend view reports missing envelopes as **Legacy/unknown**. Local digest metadata does not indicate scientific validation, digital signature, human approval, or operational readiness.

The API attaches provenance before `Store.save`, so new stored JSON and exports include the envelope. The study evaluator adds it before calculating `evidence_sha256`, so that evidence digest covers the provenance fields. Council, imports, and external connector records do not receive numerical-model provenance.

## Envelope contract

The envelope records:

- `schema`, `status`, model identifier/version, a 64-character source SHA-256, and its implementation file list.
- Canonical effective-model-input SHA-256 and its explicit scope. Store request hashes remain separate when request inputs differ from the effective study inputs.
- Data kind, declared data identity, and an optional dataset revision. Only the hybrid packaged catalogue receives a dataset revision in this change; it is the raw SHA-256 of `apps/api/helioforge/data/hybrid_catalog.json`, not a digest of the calculated result.
- Units, declared horizon, and the hybrid initial/terminal energy endpoints with the unconstrained terminal policy.
- A model contract reference, existing equations, model sources, and limitations/warnings.
- Integrity scope and explicit `signature_verified: false`, `human_approval_recorded: false`, `approval_status: "not_assessed"`.

The production source revision is SHA-256 over `helioforge.source-revision.v1\0` followed by each sorted unique relative source path, NUL, exact file bytes, and NUL. All production source sets include `provenance.py`, so changes to the envelope semantics change the revision as well. The isolated helper tests can pass a temporary source root to prove deterministic hashing and byte sensitivity. Input hashes are SHA-256 over UTF-8 JSON with sorted keys, compact separators, and non-finite values rejected. The source contract URL is a human-readable repository reference; it is explicitly not asserted to match the locally hashed bytes. The digest itself identifies the local runtime source set.

Source file sets include `provenance.py`, each numerical engine, and `schemas.py`; hybrid also includes `hybrid.py`, and study records include `studies.py`, the selected study module, schemas, and `finance.py` when that selected module calls the shared finance engine. Import review across the seven study modules found no other application-internal dependencies. Hybrid `dataset_revision` is based on the exact packaged catalogue file bytes. Study source references, equations, units, limitations, and inputs are copied from the existing catalogue/evaluation contract; no external data identity is invented.

## Frontend and integration hooks

`HF.ResultProvenance` is optional on `BaseResult` and `StudyResult`; `HybridResult` inherits it through `BaseResult`. `HF.resultProvenanceView(result)` validates the version and source digest before presenting a result as source-bound. Missing or malformed envelopes are reported as legacy/unknown. It links only HTTPS contracts/sources through the existing `safeURL` helper and renders equations, inputs, units, horizons, endpoints, warnings, and approval state as escaped text.

`HF.resultExportRows(result, rows)` preserves every scientific row and existing cell, repeats schema/model/run/input/source/dataset identifiers on each row, and adds an untruncated original-result JSON plus provenance/warnings metadata on the first row. If there are no data rows it emits one metadata-only row; metadata columns use collision-safe preservation if a caller already has the same column names. The parent now wires this helper to the dispatch CSV export; other legacy CSV call sites still require review.

Saved-run evidence sent to council review now includes the original stored `inputs` next to the saved result and input digest. The existing 30 KB per-record limit applies to the expanded evidence object; no other record retrieval boundary was changed.

Parent integration status at handoff (these files were parent-owned and are not part of my changed-file list):

1. `src/result-provenance.ts` is inserted in `apps/web/tsconfig.json` after `src/roadmap-types.ts`.
2. `HF.resultProvenanceView(result)` is wired to the Hybrid, study, and baseline result panels.
3. `hybridComparisonContract` reads actual `source_revision` and `dataset_revision` digest fields; the earlier `bundle_version` and `application_revision` fallbacks are removed so legacy bundled records without actual digests remain provenance-incomplete.

These parent edits typecheck in the shared tree. Full app build, browser behavior, and additional CSV call sites remain parent integration verification.

## Verification

Test-first regression evidence:

- Before implementation, `apps/api/tests/test_result_provenance.py` failed collection with `ModuleNotFoundError: No module named 'helioforge.provenance'` (the expected red for the missing helper).
- The saved-council-input regression failed first with `KeyError: 'inputs'`, then passed after adding inputs to the bounded saved evidence item.
- The existing hybrid bundle contract failed first because the direct engine result had acquired a bundle-level `input_sha256`; that wrapper field is now left to the API store/bundle generator, while the effective-input digest remains inside provenance.
- A hybrid assertion for including `provenance.py` in the production source set failed before the source set was updated.
- After implementation, the focused provenance and hybrid-bundle tests passed **8/8**. The provenance tests emitted the installed Starlette deprecation notice for its `httpx` TestClient integration.

Exact successful command:

```cmd
set PYTHONPATH=apps/api&& C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe -m pytest apps/api/tests/test_result_provenance.py apps/api/tests/test_hybrid_bundle.py -q
node --test apps/web/tests/workspace-migration.test.mjs
npm --prefix apps/web run typecheck
```

The eight Python tests cover stable/order-independent source hashing, source-byte invalidation, input-digest sensitivity without source-revision changes, no approval claim, the hybrid catalogue SHA-256 and endpoints, study evidence hash coverage, dashboard snapshots, legacy store records remaining unknown, API persistence without stamping council results, saved council input visibility, and deterministic generated hybrid bundle parity. The five workspace migration tests pass after adding regressions for retaining an unchanged v1 run ID and declaring its loss when inputs changed.

No TypeScript build, global frontend suite, full API suite, browser run, external provider, hardware, publication, or deployment was run in this bounded task. The source typecheck passed; parent integration still owns the complete build/browser verification.

## Changed files

- `apps/api/helioforge/provenance.py` (new)
- `apps/api/helioforge/main.py`
- `apps/api/helioforge/studies.py`
- `apps/api/helioforge/dashboard.py`
- `apps/api/helioforge/engines/hybrid.py`
- `apps/api/tests/test_result_provenance.py` (new)
- `apps/web/src/types.ts`
- `apps/web/src/roadmap-types.ts`
- `apps/web/src/result-provenance.ts` (new)
- `apps/web/src/champion-controller.ts` (follow-up saved-run migration preservation)
- `apps/web/tests/workspace-migration.test.mjs` (follow-up preservation/loss regressions)
- `apps/web/src/types.ts` also extends optional council protocol snapshot metadata types.
- `docs/remediation-20261029/state-followup.md` records the migration follow-up.

## Risks and limits

The envelope uses local hashes, not a signature or tamper-evident store. Third-party numerical library source bytes are not included; the hashed source set covers application model code, schema contracts, the envelope helper, and explicitly listed internal model dependencies. The documentation URLs point to the repository's `main` branch and can move; they are explanatory links rather than revision pins. Existing bundled browser records were not regenerated in this task and remain unknown unless generated through the source path that emits this envelope. Parent-owned view wiring and hybrid comparison fallback removal are present in the shared working tree but still need integration build/browser verification. The metadata helper wraps dispatch CSV now; other CSV export paths remain open until they use the helper or report why raw columns suffice.
