# Controlled release preparation — not a deployment

## Candidate and allowed next use

HelioForge Champion 0.3.0 is delivered for local evaluation. The full source, built frontend, starter scripts, verification records and file-hash manifest are included. The standard launcher uses this computer's loopback interface and disables external AI. No service was published, repository pushed, billable integration called or staged rollout started.

**Release entry is blocked** for any public/shared deployment until an accountable owner approves a target platform, authentication/authorization and privacy design, native-browser/device results, real human UAT, operational recovery and monitoring. The app currently has no multi-user security layer. Hosting the static preview is not equivalent to hosting the API; preview calculations remain disabled.

## Required decisions and owners

| Decision | Proposed accountable role | Current status |
|---|---|---|
| Scientific scope and acceptance of synthetic-model limits | Product / research owner | Person and acceptance not supplied |
| Target browsers, operating systems and accessibility criteria | Product / accessibility owner | Not approved; local emulation evidence only |
| Secured hosting, identity and data retention | Security / platform owner | No production platform selected |
| Backup/restore and local data support | Operations owner | Small synthetic rehearsal passed; real ownership pending |
| Deployment, promotion and rollback approval | Release owner | No authorization supplied |
| Monitoring and incident response | Operations / support owner | No production telemetry or accepted rota |

Role names are proposed responsibilities, not evidence that real people accepted them.

## Staged exposure plan (proposed)

Use **1% → 10% → 50% → 100%**, with a separate recorded decision before each promotion. Do not substitute an immediate full rollout. No deployment platform was selected, so its percentage-rollout capability has not been verified and no configuration has been applied. For a desktop/local pilot, cohorts could be explicitly invited evaluators; this is a proposal, not enrolled participants.

Before entry, define eligible users/installations, stable cohort assignment, exclusions, minimum observation time **and** minimum completed-journey samples. Numeric thresholds are **TBD pending owner agreement and baseline measurement**, not chosen after seeing a favourable result. All mandatory evidence must pass; low traffic or no complaints is not proof of safety. Missing telemetry, unresolved P0/P1 risk or a failed preservation obligation blocks promotion.

Monitor candidate/cohort-specific startup failures, request failures with denominators, saved-work recovery, baseline/outage/compare completion, invalid-input handling and serious data-integrity incidents. Define response budgets, error categories and privacy-aware retention. No production dashboard, alerts or external tracking have been configured. Current request IDs and local logs are not a replacement for an accepted monitoring plan.

Each stage decision should record candidate manifest hash, cohort definition, observation period, sample counts, acceptance outcomes, unresolved risks, decision, named approver and rollback authority. Do not simulate elapsed observation or treat automated personas as human users.

## Stop and recovery

Stop promotion on data loss, materially misleading results, access-control failure, inability to recover saved work, or a failed approved essential journey. Stop changes first; retain sanitised evidence. Application rollback uses the preserved previous app package in a separate environment. No schema migration was introduced, but never overwrite the only database copy while the service is running.

A small synthetic SQLite backup/restore was actually tested. This does not establish restoration for a large production dataset, external side effects, concurrent writers or offline clients. Preserve current data before choosing a backup and validate exact saved inputs/results after recovery. The standard launcher does not enable a live provider, and no queue/external transaction recovery is applicable to the tested local mode.

## Draft release notes and communications

DRAFT: “Champion adds saved hybrid setups, validated workspace recovery, run reopening and keyboard search. It repairs stale hybrid input presentation, lost navigation drafts and same-market reconnect resets. Existing numerical engines and clear study-only boundaries are preserved. Run the local app for new calculations; the standalone HTML remains a preview.”

No app-store submission, public announcement, support reply or customer email was sent. There is no supplied review dataset from which to draft genuine complaint-specific responses.

## Post-release review (proposal only)

A named owner should review evidence before each exposure increase, after the first full-release observation window, and after material model or storage changes. Include reopened defects, recovery failures, actual task completion and support themes. These are proposed reviews, not scheduled events or configured background monitoring. This chat will not continue observing a rollout after handoff.
