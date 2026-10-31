# Council execution protocol

**Protocol ID:** `helioforge-council/v1`
**Source of execution limits:** `apps/api/helioforge/council_protocol.py` and `apps/api/helioforge/council.py`

This document describes the active council orchestration. `docs/AI_SETUP.md` covers installation; the Agent council UI and its result/export repeat the protocol ID, execution status, consent, invocation limits, cost boundary, cancellation state, and authority limits.

## Modes and lifecycle

| Mode | External execution status | Behavior |
|---|---|---|
| `local` | `not_requested` | Returns a fixed deterministic checklist. No LLM/Agents SDK runner is called; provider consent is false and provider charges do not apply. |
| `openai` | `completed` | After the configured API feature, server key, model credential and explicit consent gates pass, sends the brief, calculated evidence, and selected saved evidence/imports to the configured OpenAI model. A completed result is stored locally. |
| `openai` | `not_started`, `failed`, or `timed_out` | The error response includes protocol metadata and `result_recorded: false`. A deterministic local result is never substituted. Invocation completion can be unknown when execution started. |

The execution status describes the request lifecycle only. It does not describe evidence quality, scientific validation, reviewer authority or approval.

Local-mode metadata reports zero configured/executed external specialists and critics, zero runner invocations, and eight local checklist sections. External-mode metadata distinguishes configured roles from execution: `configured_specialist_count` is eight, while `executed_specialist_count` is eight on completion, zero when execution did not start, and unknown after a failed or timed-out workflow. `configured_critic_count` and `executed_critic_count` follow the same distinction. The legacy `specialist_count` field remains an alias for configured external roles; it is zero in local mode and does not imply that anyone executed.

Local mode also runs bounded checks over attached saved-record metadata and known result shapes. It checks required result keys and finite numeric fields for the supported result kinds, compares declared units when present, checks a digest against canonical inputs only when those inputs are attached, compares explicitly declared expected model/horizon/data-kind metadata, checks an explicit validity expiry, and reports supplied sensitivity or provider-failure labels. It adds sanitized findings and role-scoped follow-up evidence to the fixed checklist. It does not parse raw evidence text as fact, determine privacy classifications, infer staleness from age without an expiry policy, convert units, or validate scientific assumptions. A digest match is content consistency only, not source or signer authentication. The current API omits original inputs from ordinary attached `evidence_run_ids` records, so their digests are reported as unverifiable; the saved hybrid path does include inputs and can be compared.

The local checklist still does not execute independent reviewer roles or a critic. Eight displayed sections are fixed checklist sections. The bounded checks do not create role-specific scientific analysis or critic dissent. The public static preview has no evidence-state injection interface; its bundled synthetic snapshot can be checked for disclosures but cannot exercise tampered, stale, contradictory, sensitive or failed-evidence cases.

## External orchestration limits

- Eight named specialists run concurrently for the initial review.
- The request allows one or two cross-examination rounds, with eight specialist invocations in each round.
- One critic invocation follows the specialist rounds.
- Planned Agents SDK `Runner.run` invocations are `8 × (1 + cross-examination rounds) + 1`: 17 for one round and 25 for two.
- Each specialist invocation has at most two turns and 1,800 output tokens; the critic has at most two turns and 2,200 output tokens.
- The whole workflow has a 300-second timeout. One external workflow at a time is allowed per API process.
- SDK tracing is disabled, and agents have no external tools.

The 17/25 counts are orchestration invocations. `Runner.run` can use up to two turns, so those counts do not establish provider HTTP request count, token use, or money charged. The response keeps the older `model_calls` field as a compatibility alias; `runner_invocations` and `protocol_metadata.limits` state the accurate meaning.

## Consent, cost and cancellation

The external mode sends the research brief, calculated evidence and explicitly selected saved evidence/imports to the configured provider. The server-side API credential is not sent to the browser. External processing requires the user to explicitly consent and requires a configured local admin key. The UI shows this scope and planned invocation count before submission.

Provider cost cannot be estimated by this application. A call/turn limit is not a monetary limit, and no application spending budget is enforced. Configure a provider-side project limit before using non-confidential data. Even a failed or timed-out request may have generated billable provider usage.

When one task fails, times out or is cancelled, outstanding local asyncio sibling tasks are sent cancellation requests and awaited. Metadata reports `best_effort_requested` and `provider_stop_confirmed: false`; it does not claim the provider stopped work already accepted. Completed runner invocation count is `null` on an error when the wrapper cannot establish it. Failed/timed-out requests do not persist a council result.

## Integrity and authority

- The API persistence layer attaches `input_sha256` as a digest of serialized request inputs. It identifies content; it does not verify source origin, authorship, a signer, truth, calibration or approval.
- External `task_id` is a truncated SHA-256-derived correlation identifier for the serialized review payload. It is not a digital signature or identity credential.
- `critic_signoff`, `reviewer_identity_verified`, `evidence_authenticity_verified`, `signature_verified`, and `human_approval_recorded` are false. No cryptographic signature or independent signer check runs in this protocol.
- Consensus counts summarize correlated reviewer opinions. Neither vote agreement nor entropy establishes correctness, accreditation, approval or fitness for operation.

Exports carry digest, identity, signature, critic signoff and human approval fields separately. A hash value must not be interpreted as authentication, and a successful external execution must not be interpreted as human approval.

For local evidence warnings, the `evidence_review` object reports only result-shape and explicit-metadata findings. Its `records` entries use one-based record indexes and kind labels rather than echoing source text. A `matches_supplied_inputs` digest status means the canonical JSON inputs supplied with the record match its digest; it does not prove those inputs were original or unchanged before import. `unverifiable_missing_inputs` is the expected ordinary route status while the API attaches a saved result without its original inputs. A fixture label such as `sensitive_fixture` or `provider_status=failed` is treated as unverified metadata and only triggers a warning.

## Validation boundary

Automated tests use a fake Agents SDK to exercise one-round and two-round counts, timeout/failure states and best-effort sibling cancellation. No live provider, API key, spend, deployment or real-world approval was used to validate this protocol. Live provider compatibility, provider-side usage and actual charges remain unverified.

The council role/evidence follow-up is recorded in [council-followup.md](remediation-20261029/council-followup.md); its row-level expected/actual ledger and source hashes are in [council-results.json](remediation-20261029/council-results.json). Public-preview rows are static-contract partial checks, local-deterministic rows execute the fixed checklist plus bounded metadata rules, and all external live-provider rows remain blocked.
