# Council remediation evidence — 2026-10-28

## Scope and evidence convention

Scope: appraisal F03 (versioned council protocol), F12 (digest/signature/approval distinction), and the council-specific F05 boundary. This source review does not validate a published deployment or a live OpenAI provider.

Evidence class and remediation status are separate:

| Class | Meaning |
|---|---|
| O | Observed in inspected source or a directly executed tool outcome. |
| R | Reproduced in a controlled local test. |
| I | Reasoned interpretation from the observed code/test behavior. |
| P | Proposed acceptance condition, not an observed result. |
| U | Unverified because current external/runtime evidence is unavailable. |

## Findings

| Item | Evidence class | Status | Finding and evidence |
|---|---|---|---|
| F03 timeout discrepancy | O | Reconciled in source/docs | `apps/api/helioforge/council.py` wraps the workflow in `asyncio.wait_for(..., timeout=300)`. `docs/AI_SETUP.md` said 120 seconds; `docs/roadmap/CONNECTORS.md` said 300 seconds. The active timeout is 300 seconds. The value now lives in `council_protocol.py` and is covered by tests and exported metadata. |
| F03 call-count discrepancy | O, R | Reconciled in source/docs | The active external workflow has eight specialist `Runner.run` invocations for the initial round, eight for each of one or two cross-examination rounds, then one critic invocation: `8 × (1 + rounds) + 1` gives 17 or 25. Fake-SDK tests exercised both counts. These are orchestration invocations; each may use up to two turns, so they are not a provider HTTP-request, token, or billing count. |
| F03 local-mode display | R | Corrected in source; bundled verification pending | The pre-change browser bundle called the local mode “Eight specialists challenge the evidence,” rendered “Specialist review” nodes and presented a committee critic, although the API returned `execution=deterministic_rule_based` and no Agents SDK calls. `node --test tests/council-protocol.test.mjs` reproduced both missing local-mode disclosure and missing protocol metadata against the pre-build `apps/web/dist/app.js` (2 expected failures). `views.ts` now labels local entries as fixed checklist sections and the summary as deterministic; old OpenAI-labelled data without a versioned completed status is marked unverified. A frontend build is needed to verify the changed browser bundle. The protocol now reports zero configured/executed external specialists and critics in local mode and counts its eight deterministic sections separately. |
| Failed provider result handling | R | Corrected/extended | Before changes, the API provider-error test returned 502, leaked no provider payload and saved no run; it did not substitute local output. The low-level fake-SDK test verified that the seven sibling reviews are sent cancellation requests when one fails. The versioned error body now includes protocol/status, unknown completed call count, `best_effort_requested`, `provider_stop_confirmed=false`, possible remaining charges and `result_recorded=false`. It does not claim provider work stopped. Pre-execution gate errors are marked `not_started` with zero completed invocations. |
| F12 authority/integrity | O, R, P | Preventive control added; no existing false signature/approval claim reproduced | Existing source already reported `identity_verified=false`, `critic_signoff=false`, and no local persisted result after provider failure. No council UI badge or export was found that claimed a SHA-256 digest was a signature or approval. The store hashes canonical serialized request inputs; external `task_id` is a truncated SHA-256 payload correlation value. Both are content identifiers, not source authentication, signer identity, scientific validation or approval. Protocol metadata, the council view and Markdown/JSON exports now show these claims separately and leave reviewer identity, evidence authenticity, signature verification, critic signoff and human approval false. |
| Live provider execution/cost | U | Open | No live credentials, provider call, account usage record or charge was used. Provider compatibility, real token/request counts and actual cost remain unverified. |

## Implementation and verification

The versioned source contract is `helioforge-council/v1` in `apps/api/helioforge/council_protocol.py`. `council.py` uses the shared constants for timeout, turn and output-token limits; result metadata reports mode, external execution status, consent, configured versus executed specialist/critic counts, local checklist-section count, expected/completed `Runner.run` invocations, cost availability, cancellation state and integrity/authority state. `main.py` attaches the same protocol metadata to both pre-execution and post-start external errors. UI preflight discloses the payload, plan and cost boundary before submission; result view and exports repeat the protocol and provenance fields. `AI_SETUP.md`, `CONNECTORS.md` and this protocol document agree on the active limits.

Commands used (PowerShell, source checkout `C:\Users\MRK\Downloads\misC\helioforge-remediation-20261028\source`):

```powershell
$env:PYTHONPATH='C:\Users\MRK\Downloads\misC\helioforge-remediation-20261028\source\apps\api'
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m pytest apps/api/tests/test_council.py apps/api/tests/test_api.py -q
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m ruff check apps/api/helioforge/council.py apps/api/helioforge/council_protocol.py apps/api/helioforge/main.py apps/api/tests/test_council.py apps/api/tests/test_api.py
npm run typecheck   # from apps/web
node --test tests/council-protocol.test.mjs   # from apps/web; reads generated dist/app.js
```

Observed environment: Python 3.12.14, Node v24.22.1, TypeScript 7.0.2. An earlier post-fix focused Python run passed 27 tests. Ruff passed; the tool emitted cache-write access warnings but exited 0. TypeScript typecheck passed. **Final focused Python rerun: BLOCKED/INTERRUPTED.** Exact command: `$env:PYTHONPATH='C:\Users\MRK\Downloads\misC\helioforge-remediation-20261028\source\apps\api'; & 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m pytest apps/api/tests/test_council.py apps/api/tests/test_api.py -q`. Partial output was five progress dots (`.....`), then no output for more than three minutes. The owned session was interrupted with Ctrl+C at the parent request; it exited 1 with no summary or traceback, so this attempt establishes neither pass nor failure. No rerun was started. The frontend regression test currently sees the pre-build bundle and was intentionally not rerun after the source edit; no generated frontend build was performed by this agent. The app's full frontend test suite and visual/browser validation were not run here.

## Proposed acceptance condition

**P — Close F03/F12 for the source release only when** one `helioforge-council/v1` contract is used by code, success/error API responses, preflight UI, result view, exports and setup docs; the 300-second server timeout and 17/25 `Runner.run` invocation plans match the implementation and regression tests; local mode never implies independent agent execution; consent and transmitted evidence scope are shown before an external request; errors distinguish `not_started`, `failed` and `timed_out`, persist no completed result, report cancellation as best effort with provider stop unconfirmed, and disclose possible charges; and every digest/task identifier is explicitly separated from verified identity, signature, critic signoff and human approval. Close live-provider acceptance only after a separately authorized nonconfidential run verifies provider compatibility and dashboard usage. No local code or mock test can satisfy that last condition.
