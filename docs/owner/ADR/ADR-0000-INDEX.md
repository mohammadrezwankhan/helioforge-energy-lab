# Recorded architecture observations and proposed ADRs

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

No approval or formal old ADR is inferred from the source inspection. The following are **observations** only:

| Key | Source-backed implemented choice |
| --- | --- |
| HF-OBS-01 | Separate static synthetic samples, browser Terminal, advanced Python and opt-in connectors ([capability contract](../../CAPABILITIES.md)) |
| HF-OBS-02 | Deterministic greedy hourly hybrid policy with explicit initial energy and no terminal SOC equality ([hybrid.py](../../../apps/api/helioforge/engines/hybrid.py)) |
| HF-OBS-03 | Behind-the-meter SciPy MILP with binary flow directions and equal terminal SOC ([storage.py](../../../apps/api/helioforge/engines/storage.py)) |
| HF-OBS-04 | Trusted local API with explicit opt-in external calls ([SECURITY](../../../SECURITY.md), [main.py](../../../apps/api/helioforge/main.py)) |
| HF-OBS-05 | Separate dedicated-domain export and aggregate-app publishing routes ([Cloudflare](../../CLOUDFLARE.md)) |

Proposals needing human approval: external study validation standard, identity/authorization for any hosted service, field-integration safety design, real data/consent/rights policy and deployment-signing policy. Mark only as *proposed* until a decision with author, date and evidence is recorded.
