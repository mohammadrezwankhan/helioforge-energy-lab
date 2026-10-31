# Registry CI source-binding repair

## Failure and exact cause

The first Cloudflare job reached `node scripts/check-domain.mjs` and failed its deep equality between the freshly generated capability facts and the committed model registry. The first substantive difference was `compare-thermal`: its generated acceptance card had `sourceMatches: false` and `STALE_SOURCE_EVIDENCE`, while the committed registry retained `SOFTWARE_CHECKS_PASS`. The other 17 reported leaf differences were consequences of that one status change; no catalogue, model-version, equation, or fixture difference was found.

The pinned record in `docs/remediation-20261029/study-contracts.json` expected SHA-256 `62a64ad856c68d521f0468066f4a1d642e2b5324faa7848c22e0e509fd123f42` for `apps/api/tests/test_study_acceptance_contracts.py`. Before repair, the checked-out file hashed to `e52b36802637e1e4cb4bd4374abaeb4ca0d534f148b06904efd04299ec5af714`. The orchestrator traced the one-byte difference to whitespace cleanup removing the final blank line. This was not a Windows/Linux line-ending conversion: other files in the same source-hash record matched their recorded hashes, and the test file’s committed and working bytes matched each other before restoration.

The Python study implementation and numerical calculations were not changed. Because this test file is explicitly part of the acceptance record’s source binding, the generator correctly refused to carry its old PASS forward across the byte change.

The orchestrator restored the test file from the verified delivery archive. It now hashes to the pinned value `62a64ad856c68d521f0468066f4a1d642e2b5324faa7848c22e0e509fd123f42`. The generated registry again equals the committed registry without modifying `docs/MODEL_REGISTRY.*` or `docs/remediation-20261029/study-contracts.json`.

## Checker diagnostics

`sourceEvidenceMismatches()` in `scripts/capability-contract.mjs` centralizes exact-byte source-hash checks and returns file, expected hash, and observed hash for any mismatch. It does not normalize line endings or weaken the existing source binding. An absent optional evidence record returns no mismatch; an existing record with missing, non-object, or empty `source_hashes`, unpaired file/hash entries, malformed digests, missing files, or byte mismatches fails closed. `scripts/check-domain.mjs` reports precise mismatches before its generated-versus-committed registry comparison; `scripts/capability-contract.test.mjs` exercises valid, absent, empty, malformed, mismatched, and missing-file bindings before deep equality.

If a future mismatch occurs, CI still fails until the source-bound record and registry are correctly refreshed or the accidental source change is restored. The diagnostic does not treat stale evidence as current.

## Verification

After restoration, the following focused commands passed:

```text
node scripts/capability-contract.test.mjs
{"status":"passed", ..., "workspaces":12,"studies":59}

$env:CLOUDFLARE_OUTPUT_ROOT='.cloudflare/acceptance-20261029-g'; node scripts/check-domain.mjs
{"status":"passed","project":"mkgrid-helioforge","pages":9,"workspaces":12,"studies":59,"files":364,"runtimeSha256":"8ef56f4df539590392696552c2b10651faf953790d8018c982a949b21e0ccb00"}
```

The runtime SHA-256 remains the approved Candidate G value. No build, publication, deployment, provider call, or registry-artifact regeneration was performed for this repair.
