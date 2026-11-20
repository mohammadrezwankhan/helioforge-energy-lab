# Troubleshooting by affected boundary

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

| Symptom | Diagnostic | Correct boundary |
| --- | --- | --- |
| `launch.py --check` fails | Check Python 3.11–3.13, pinned package installation and extracted directory layout | [START_HERE](../../START_HERE.md) |
| Preview says Python is disconnected | Static HTML is not the full local app | Run local launcher and use its loopback address |
| Browser inputs changed but study result is unchanged | Static bundle is precomputed and requires exact preset identity | For new advanced studies use local Python API |
| Hybrid outage reports de-energized | Island-capable topology and GFM/synchronous reference assumptions | [Hybrid methodology](../HYBRID_METHODOLOGY.md) |
| Hybrid and storage cost disagree | Greedy service-first screen versus terminal-SOC-constrained MILP | [Equations](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md) |
| Bad or stale local saved result | Re-check input hash, run ID and SQLite history | [Launcher recovery](../../START_HERE.md); never invent recovered numbers |
| 403 from local API | Host/Origin/consent guard | Keep trust checks; don't disable to force request |
| Public site and source disagree | Compare `.cloudflare/site` build, source SHA and CSP with provider receipt | [Cloudflare playbook](../CLOUDFLARE.md) |
| Original CI queued | Inspect exact head/merge-queue checks and runner labels | [Release playbook](../maintainer/CI_CD_AND_RELEASE_PLAYBOOK.md) |

Start with a fictional input and exact error output. Preserve security boundaries; do not post logs containing secrets, external-provider credentials or stored local research history.
