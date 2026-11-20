# Governance and scope

## Product purpose

HelioForge is an educational and research workbench for energy systems, finance and evidence-aware comparisons. Its synthetic examples support reproducible questions; they are not certified plant controls, validated safety systems, current market forecasts, legal determinations or investment recommendations. The original README, methodology, security policy, MIT license and known CFF authorship/release remain authoritative context. [README.md](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/README.md), [docs/METHODOLOGY.md](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/METHODOLOGY.md), [LICENSE](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/LICENSE), [CITATION.cff](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/CITATION.cff), [SECURITY.md](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/SECURITY.md).

## Responsibilities to assign

| Role | Accountable decision |
|---|---|
|Repository owner|Priorities, scope, data rights, external processing and actual releases |
|Numerical maintainer|Equations, units, baselines, solver status, regressions and calibrated-versus-synthetic claims |
|API/browser maintainer|Schemas, state consistency, imports/exports, local persistence and accessible controls |
|Build/security maintainer|Pinned toolchains, existing checks, artifact identity and effective deployment controls |
|Documentation maintainer|Current canonical prose, source locators, handbook freshness and historical scope notices |
|Independent reviewer|Review the exact frozen candidate and report disagreements without inheriting author conclusions |
|Integration owner|Current policy/head/base/checks, guarded merge and separately observed publication |

These are responsibility categories, not a claim that distinct named people currently staff them. The same owner may coordinate several roles, but independent review must remain independent of the relevant authorship.

## Change boundaries

Documentation can clarify an implemented limitation and propose a repair without altering the calculation. A numerical change requires a reproducible failing case, a source-located rationale, meaningful negative controls and independent review of changed results. A schema or persistence change requires migration/recovery and stale-operation evidence. A hosting/dependency/workflow change needs a concrete separately scoped implementation; this package makes none.

Keep the 19 runnable/17 study-only architecture distinction and 59 bounded-study meanings visible. No count, model label or comparison rank is a certification claim. Preserve free versus fixed terminal SOC and project versus equity/CFADS distinctions in public summaries. [apps/api/helioforge/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/hybrid.py), [apps/api/helioforge/studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/studies.py), [apps/api/helioforge/engines/finance.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/finance.py).

## Data, privacy and external authority

Use synthetic/nonconfidential examples for public reproducibility. A digest identifies content; ephemeral browser signatures do not identify a person or institution. Do not put provider secrets, private measurements or unrelated repository findings in the public package. External council/provider/device experiments require their actual stated scope and consent; the default local app remains usable without them. Configured status and mock tests cannot be promoted to successful live integration. [apps/web/src/evidence.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/evidence.ts), [apps/api/helioforge/council_protocol.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/council_protocol.py), [apps/api/helioforge/integrations.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/integrations.py).

## Ownership cadence

Review the [roadmap](../../ROADMAP.md) at its twelve dated checkpoints, the [debt register](../maintainer/FAILURE_MODES_AND_TECH_DEBT.md) before stronger result claims, and the [recovery runbook](BUS_FACTOR_RECOVERY_RUNBOOK.md) before a release. Close items only with their acceptance evidence. Preserve blocked/deferred decisions and failed runs; do not equate author completion with merge or publication.
