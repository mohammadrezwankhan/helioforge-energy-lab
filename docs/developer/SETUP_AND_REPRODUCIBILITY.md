# Local setup and reproducibility

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

## Python and optional browser-development toolchain

The package declares Python 3.11+; the [launcher guide](../../START_HERE.md) supports Python 3.11–3.13 for the packaged local app. The API project is under `apps/api` and its [manifest](../../apps/api/pyproject.toml) has pinned FastAPI 0.162.4, Pydantic 2.14.3, NumPy 2.4.6 and SciPy 1.17.1. These are *declarations*, not observations of installed versions.

```sh
python -m venv .venv
python -m pip install -e "apps/api[dev]"
python launch.py --check
python -m pytest apps/api/tests
python -m ruff check apps/api
python launch.py --no-browser
```

Launch the API only on its default loopback address (typically `http://127.0.0.1:8000`). The local app is not authenticated for multi-user hosting; do not expose it on a network. The supplied portable [HelioForge-Preview.html](../../HelioForge-Preview.html) is available without an installed API, but most new calculations are not.

For source/UI changes, use Node.js 22+ where needed, `npm --prefix apps/web ci`, `npm --prefix apps/web run build`, and project-specific tests defined by [original CI](../../.github/workflows/ci.yml). The dedicated public export uses Node.js 24 per [Cloudflare instructions](../CLOUDFLARE.md).

## Evidence for a genuine reproduction

Record full Git SHA, Python/Node versions, installed pins, command and exit code, synthetic case ID, input hash, output hash and local execution date. Generated example outputs, browser bundle hashes, dated history and published Cloudflare receipts are distinct. Avoid changing original source fixtures or old evidence to force a result to match.
