# Toolchain and dependency evidence matrix

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

| Tool/stack | Declared or documented | Evidence boundary |
| --- | --- | --- |
| Python | 3.11+ package; 3.11–3.13 packaged local launcher | [START_HERE](../../START_HERE.md), [pyproject](../../apps/api/pyproject.toml) |
| FastAPI / Starlette / Pydantic | 0.162.4 / 1.10.0 / 2.14.3 pinned | Local API transport and bounded schemas |
| NumPy / SciPy | 2.4.6 / 1.17.1 pinned | Storage SciPy MILP, numerical engines |
| HTTPX / Uvicorn / Shapely | 0.28.1 / 0.54.0 / 2.2.0 pinned | Service, requests and geometry |
| Python dev | pytest, Ruff, coverage; optional OpenAI Agents extra | Installed with `apps/api[dev]`; AI functionality not enabled by install alone |
| Browser source | `apps/web`, locked Node ecosystem | `npm --prefix apps/web ci`, test/build and browser checks |
| Site build | Node 24 per Cloudflare guide | Build entire `.cloudflare/site`, check CSP and hash output |
| CI | Original GitHub Actions matrix | Exact SHA and provider-run status, not a generic badge |

All installed-version observations, dependency audits and verification claims must be measured on the relevant candidate. The [2026-10-31 historical run](../../QUALITY_REPORT.md) applies only to its named revision, not automatically to this PR.
