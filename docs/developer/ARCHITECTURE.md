# Architecture and runtime boundaries

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

## Four distinct execution modes

1. **Bundled examples:** precomputed source-generated research outputs. Editing inputs in the static site does not re-run the 59 Python study engines.
2. **Browser Terminal:** a bounded 24-hour energy-balance calculation running locally in browser JavaScript, using a deterministic greedy policy rather than an optimizer.
3. **Local Python application:** FastAPI plus Pydantic schemas, SQLite research history, the hourly hybrid model, SciPy storage MILP and research modules for new advanced calculations.
4. **Opt-in connectors:** local external-provider/device functions are separate, credential/consent-gated services; the static preview does not call them.

The authoritative [capability contract](../CAPABILITIES.md) and [model registry](../MODEL_REGISTRY.md) define these boundaries.

## Important source entry points

| Area | Inspect |
| --- | --- |
| Server API and trust controls | [apps/api/helioforge/main.py](../../apps/api/helioforge/main.py), [SECURITY.md](../../SECURITY.md) |
| Hourly adequacy | [hybrid.py](../../apps/api/helioforge/engines/hybrid.py), [methodology](../HYBRID_METHODOLOGY.md) |
| Behind-the-meter optimization | [storage.py](../../apps/api/helioforge/engines/storage.py) |
| Data/synthetic scenario validation | [helioforge/hybrid.py](../../apps/api/helioforge/hybrid.py) and [schemas.py](../../apps/api/helioforge/schemas.py) |
| Provenance | [provenance.py](../../apps/api/helioforge/provenance.py) and stored local history |
| Cross-workspace study catalogue | [studies.py](../../apps/api/helioforge/studies.py), [model registry](../MODEL_REGISTRY.md) |
| Development/browser | [apps/web](../../apps/web/package.json), [Cloudflare source](../CLOUDFLARE.md) |

The hybrid greedy simulation, local storage cost MILP, Terminal JavaScript and illustrative precomputed scenarios have different objectives. Do not add their outputs as if one jointly validated plant simulator.
