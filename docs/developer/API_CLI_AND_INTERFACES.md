# API, launcher and input contracts

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

## Local entry points

`python launch.py --check` inspects prerequisites/assets; `python launch.py --no-browser` starts the local FastAPI application without opening a browser. Port may be overridden with `--port`. See [START_HERE](../../START_HERE.md). `node scripts/preview-demo.mjs` serves an offline browser illustration; this does not start the Python API.

The [FastAPI entry](../../apps/api/helioforge/main.py) declares `GET /api/health`, `GET /api/studies`, and `GET /api/connectors/status`. It also defines bounded JSON POST routes for evidence-series/geography/document/telemetry and separately consent-gated weather, market, regulator and read-only device functions. Refer directly to current source for the full route and Pydantic schema inventory, especially before any client integration.

## Trust and state

Default allowed hosts are `localhost`, `127.0.0.1` and loopback IPv6. Write requests enforce an origin allowlist when Origin is supplied, and streamed bodies are bounded to 1 MB. CORS, origin and Host checks **do not authenticate clients**. Ordinary local run results are recorded in SQLite by the [store](../../apps/api/helioforge/store.py); that record is not tamper-evident or centrally backed up.

## Scientific interfaces

- [HybridRequest](../../apps/api/helioforge/hybrid.py) is validated before [simulate_hybrid](../../apps/api/helioforge/engines/hybrid.py).
- [StorageRequest](../../apps/api/helioforge/schemas.py) is the Pydantic contract for [optimize_storage](../../apps/api/helioforge/engines/storage.py).
- Study definitions and result provenance belong to [studies](../../apps/api/helioforge/studies.py), [provenance](../../apps/api/helioforge/provenance.py) and the [capability registry](../MODEL_REGISTRY.md).

No new endpoint, live feed or external-provider run is asserted by this document.
