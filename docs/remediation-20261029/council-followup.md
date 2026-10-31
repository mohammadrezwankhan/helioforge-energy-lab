# Council acceptance follow-up — 29 October 2026

This follow-up uses the role/evidence matrix at [council_role_test_design.csv](../remediation-20261028/source-plan/council_role_test_design.csv). The CSV has **189 rows**, not 126: 63 each for `public_preview`, `local_deterministic`, and `local_external_opt_in`. The requested public/local subset is exactly 126 rows. Each row’s original expected text, observed behavior, status, evidence class, and source hashes are in [council-results.json](council-results.json).

## Row status

| Mode | Rows | Status | Evidence class | Interpretation |
|---|---:|---|---|---|
| `local_deterministic` | 56 | `PASS_FIXED_CHECKLIST_AND_METADATA_CHECKS` | O | The real `local_council` function was exercised per row with a controlled fixture. This demonstrates fixed checklist text and bounded metadata checks, not eight executing evidence analysts. |
| `local_deterministic` | 7 | `NOT_APPLICABLE_ABSENT_CRITIC` | O | No critic runs in local mode. No critic review, dissent analysis, or signoff is claimed. |
| `public_preview` | 56 | `PARTIAL_STATIC_CONTRACT_ONLY` | R | The shipped bundle and UI source disclose local/checklist behavior and authority limits. The static snapshot has no evidence-state injection path, so these rows do not exercise their selected fixture states. |
| `public_preview` | 7 | `NOT_APPLICABLE_ABSENT_CRITIC` | R | The public snapshot shows no critic execution. |
| `local_external_opt_in` | 63 | `BLOCKED_LIVE_PROVIDER_ACCEPTANCE` | P | No live provider, API key, paid request, or deployment was used. The required local gate and fake-SDK failure/orchestration tests were run separately. |

Evidence classes and statuses are separate. `O` means observed controlled local-code execution, `R` read-only source and shipped-bundle review, `P` blocked live-provider scope, and `U` unverified claims such as scientific validity, source authenticity, human approval, and actual provider billing.

## Deterministic checks added

Local mode now emits an `evidence_review` object and sanitized warnings for the following bounded checks:

- Missing required output fields and non-finite or invalid numeric values for known saved-result kinds.
- Declared unit labels that conflict with the known result-field contract. Values are never converted based on a guess.
- SHA-256 consistency against canonical inputs only when those inputs are present. A match is a content-consistency check, not authentication.
- Explicit expected model, horizon, and data-kind metadata that contradict the attached result.
- Explicit validity expiry. Old `created_at` alone is not called stale; there is no arbitrary age threshold.
- Supplied sensitivity and provider-failure labels. These labels are unverified metadata and trigger generic warnings only.

The checks attach generic risks and follow-up evidence to the corresponding fixed checklist section. They do not echo attached result text, classify arbitrary content as sensitive, infer facts from natural-language evidence, decide scientific validity, or execute a critic. A malformed record is reported without turning it into an AI review.

The API currently strips original inputs from ordinary `evidence_run_ids` records before the local checker receives them. Those digests are therefore reported as `unverifiable_missing_inputs`; the checker compares the hybrid evidence path when its inputs are included. No change was made to the parent-owned `main.py` route.

Undefined IRR and DSCR values remain null and appear as `not defined (null)` / `not applicable (null)` in the fixed investment summary. The local reproducibility section no longer says that hashes establish reproducibility.

## Negative fixtures observed

Representative local rows in the JSON ledger show:

- `ROLE-008`: no attached evidence produces `no_attached_evidence` and an explicit request for the saved run/source.
- `ROLE-009`: a valid synthetic fixture’s digest matches the canonical supplied inputs; authenticity and scientific validity remain unverified.
- `ROLE-010`: post-hash input mutation produces `digest_mismatch`.
- `ROLE-011`: an explicitly incompatible expected model and expired validity date produce `model_version_mismatch` and `expired_validity`.
- `ROLE-012`: an explicitly inconsistent expected horizon produces `horizon_mismatch`.
- `ROLE-013`: the supplied `sensitive_fixture` label produces a generic warning; the controlled sentinel text is absent from the returned review.
- `ROLE-014`: declared provider failure is reported as failure; local mode returns zero runner calls and no critic.

Additional focused regressions cover malformed records, missing required result fields, invalid declared units, an old timestamp without an explicit expiry, ordinary route records with no raw inputs, and null finance metrics.

## Remaining public-preview requirement

The static public snapshot has no role selector or evidence-state upload/injection field. It cannot behaviorally run the seven fixture variants. The **minimal parent-owned product change** for this acceptance plan is to show a clear frozen-example state in the actual council view: identify the displayed evidence and results as bundled synthetic examples, identify the eight entries as checklist sections, state that case-specific evidence upload/review is unavailable in public preview, reject or disable attempts to submit fixture states, and keep the critic labeled “not executed.” Include the same boundary in the public export.

Then run the browser acceptance matrix for all 9 role rows × 7 evidence states in public-preview mode. Each case should verify that the attempted fixture is rejected or left unapplied, the bundled synthetic example remains unchanged, no reviewer or critic execution is shown, and the relevant disclosure survives export. Until that browser-visible rejection/disclosure exists and has been exercised, the 56 public non-critic rows remain `PARTIAL_STATIC_CONTRACT_ONLY`.

For the new local `evidence_review` result, the parent-owned view/export should render each record’s kind, digest status, sanitized finding message, and role-scoped follow-up evidence. It should preserve “content consistency only” language, label the local roles as checklist sections, and not show a digest match as authentication or a test result as reviewer execution.

For ordinary saved-record digest checks, parent-owned `main.py` can either pass a bounded digest-consistency status computed while it still has `saved["inputs"]`, or leave the current transparent `unverifiable_missing_inputs` warning. Passing full inputs into the council payload is unnecessary if the route computes that status before projection. This agent did not edit `main.py`.

## Commands and observed verification

Environment: Python 3.12.14 from `C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe`; `PYTHONPATH` was set to this checkout’s `apps/api`. No full suite, frontend build, generated UI output, live provider, or deployment was run.

```powershell
$env:PYTHONPATH='C:\Users\MRK\Downloads\misC\helioforge-remediation-20261028\source\apps\api'
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' scripts/acceptance-council-cases.py
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m pytest apps/api/tests/test_council_acceptance_cases.py apps/api/tests/test_council.py -q
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m pytest apps/api/tests/test_api.py -k 'local_council_honest_mode or external_mode or external_provider_error or external_timeout' -q
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m ruff check --no-cache apps/api/helioforge/council.py apps/api/helioforge/council_protocol.py apps/api/tests/test_council_acceptance_cases.py apps/api/tests/test_council.py scripts/acceptance-council-cases.py
```

Observed results: the acceptance ledger command exited 0 with 189 accounted-for rows, 56 local checklist/metadata passes, 56 static-preview partials, 14 absent-critic N/A rows, 63 blocked live-provider rows, and zero live provider calls. The selected API gate/failure set exited 0 with 6 tests. Ruff exited 0 (`All checks passed!`). The final council/acceptance pytest attempt printed 14 dots and `[100%]`, but the host exec wrapper did not expose its exit summary; an earlier run before adding the final old-timestamp regression printed 13 dots and `[100%]`. Treat the final 14-test command’s shell exit status as unconfirmed. Initial red runs exposed the missing evidence metadata behavior and malformed-record handling; those defects were corrected before the ledger was generated.

The selected API tests include default-disabled execution, missing admin/consent/credentials gates, provider failure without a fake local result, timeout reporting, and local protocol disclosure. Fake-SDK council tests cover 17/25 `Runner.run` counts and best-effort sibling cancellation. These mocked tests do not establish provider-side stopping or cost.

## Source hashes

SHA-256 values captured by the acceptance runner are in full in `council-results.json`. The core input and implementation hashes are:

| File | SHA-256 |
|---|---|
| `docs/remediation-20261028/source-plan/council_role_test_design.csv` | `5587c387611884ae25a68e40f1f20f1876762be7c5286c218f6ceb2df1a9fa94` |
| `apps/api/helioforge/council.py` | `bbd0bdf467ffb7e06f735a797e00692b58bbce3cfc989ee274fa0575b5d614ba` |
| `apps/api/helioforge/council_protocol.py` | `46a6490168f9bb4b1ca7ce654da3f9eb511e150a5292a7663538482cfe567828` |
| `apps/api/tests/test_council_acceptance_cases.py` | `b36cf3cbee712c6b3cb12df17b380e2286c6c3c3066dec7a10d7c7c94bb8c213` |
| `apps/api/tests/test_council.py` | `bb81578979ff518d77250996bbfc018412710ebdefe643e7e2f9b74351cb1093` |
| `apps/api/tests/test_api.py` | `b178c6fd9c8d6de334a73d4efd3c257e6e9cf49bd639dba447c76e84db4e6bc2` |
| `scripts/acceptance-council-cases.py` | `e2dc32343c44fdefbb348a5c9546eca86f9dbe75e650060ca65a19da6e209039` |
| `docs/COUNCIL_PROTOCOL.md` | `7a45c892eb3a04fe188b0e46d0332cb58afefaece724b6d1e78eed2dcffe62d3` |
| `apps/web/src/app.ts` | `dde9e533bc7d340901ae69e1a4cb77dcef1bc58121db52f1e996e08c60cae42f` |
| `apps/web/src/views.ts` | `110506fc35b14e7927c5455ad57283e816f5333ac42b272685c402dcab34cb01` |
| `apps/web/src/integrations-ui.ts` | `5ae39d8748578487bbc0a8884d0dab4b94e4e61b5dc463031d92bac7ff856d35` |
| `apps/web/dist/app.js` | `86f9c9d4d71b86fa95c7308aa71f5115224789aaa9cb82fe5ad4f96da9aeef21` |

## Acceptance condition

Accept the local deterministic subset when the 56 checklist/metadata rows pass, preserve the 7 critic rows as absent/not applicable, and retain the documented limitations on digest consistency, explicit timestamps, and role execution. Accept public-preview evidence-state behavior only when the frozen synthetic example and unsupported upload/review behavior are visible in the actual browser and all 63 public rows have browser evidence; otherwise retain their partial status. Keep all 63 live-provider rows blocked until a separately authorized, consented, budgeted provider acceptance run is reviewed. Scientific validation and human approval remain separate.
