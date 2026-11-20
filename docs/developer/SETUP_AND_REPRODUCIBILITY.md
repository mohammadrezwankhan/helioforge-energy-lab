# Setup and reproducibility

## Use the packaged local app

Extract the complete repository/release package. The launcher checks Python **3.11–3.13**, exact runtime dependency versions from `apps/api/pyproject.toml`, and the packaged frontend files. It does not install dependencies itself. The existing `start-windows.cmd`, `start-macos.command` and `start-linux.sh` scripts provide the documented first-use path. Read [START_HERE](../../START_HERE.md) with its dated scope notice. [launch.py:24–105](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/launch.py#L24-L105), [apps/api/pyproject.toml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/pyproject.toml).

From the repository root on a POSIX shell:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e './apps/api[dev]'
python launch.py --check
python launch.py --no-browser
```

Open `http://127.0.0.1:8000` after the server reports readiness. `--port 8001` changes the port; allowed values are 1024–65535. On Windows use `.venv\Scripts\python.exe` for the Python commands. Stopping with Ctrl+C retains saved runs. The launcher sets `ENABLE_OPENAI=false`, loopback host binding and matching Host/Origin allow-lists. It does not terminate a process occupying a port. [launch.py:68–196](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/launch.py#L68-L196).

The packaged app uses `data/helioforge.sqlite3` by default. Set `HELIOFORGE_DB` to an explicit absolute path to separate experiments, and retain that path with the experiment record. `HF_DATA_DIR` is not the launcher's database setting. [launch.py:119–130](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/launch.py#L119-L130), [apps/api/helioforge/store.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/store.py).

## Rebuild the browser runtime

Node **22 or later** is declared; the source CI uses Node 24. Build tools are locked in the web package lock. No runtime npm packages are needed by the generated standalone application.

```sh
cd apps/web
npm ci --ignore-scripts
npm run typecheck
npm test
npm run build
cd ../..
node scripts/check-preview.mjs
```

The build compiles the ordered `HF` namespace files, assembles ten stylesheets, writes `apps/web/dist`, creates `HelioForge-Preview.html` and emits hashed deferred hosted data. Keep `scripts/build-web.mjs` together with its imported sibling helpers. A fresh local build on 2026-11-19 reproduced every canonical tracked byte and mode; the preview check confirmed exact runtime/style equality. This says nothing about a remotely deployed revision. [apps/web/package.json](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/package.json), [apps/web/tsconfig.json](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/tsconfig.json), [scripts/build-web.mjs](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/build-web.mjs). See the [dated evidence ledger](../maintainer/VERIFICATION_EVIDENCE_LEDGER.md).

The existing Dockerfile copies only the build entry script before invoking this build, while that script imports three sibling modules. This is a source-inspected clean-build risk; Docker was not executed in this review. Use the supported source/packaged paths above pending the roadmap's focused packaging repair. [Dockerfile](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/Dockerfile), [scripts/build-web.mjs:1–3](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/build-web.mjs#L1-L3).

## Verify numerical source and bundled examples

```sh
python -m ruff check apps/api
python -m pytest apps/api/tests
python scripts/check-hybrid-assets.py
python scripts/check-study-assets.py
```

The asset checks regenerate values in memory and compare the established numerical contracts; they do not require accepting newly generated fixture bytes. The source CI additionally runs publication, dependency, security and real-browser checks. Running the four commands above is not equivalent to that whole matrix. [.github/workflows/ci.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/ci.yml), [scripts/check-hybrid-assets.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/check-hybrid-assets.py), [scripts/check-study-assets.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/check-study-assets.py).

## Reproducibility record

Retain the Git commit, exact command, Python/Node and package versions, inputs with units, seed, interval count, timezone/calendar convention, source/data/input digests, solver status and residuals, start/end UTC times and raw log. Keep failures and differing-version observations alongside successful reruns. For comparison, state whether final SOC is constrained and whether demand served is equal. Scientific reproducibility also needs provenance and calibration of real input data, which bundled synthetic cases do not provide.

The 2026-11-19 local API suite used Python 3.12.14 and the declared pinned numerical/runtime packages. The first small annual-comparator probe used pre-existing differing package versions; a separately dated exact-pin repeat reproduced it. The JS/TS **AST inventory** used parser 5.9.3, while the actual typecheck and build used locked TypeScript **7.0.2**. Parsing and compilation are separate observations. A local Chromium capability probe failed at `socket()` with `Operation not permitted`; browser interaction, screenshots and visual accessibility were not observed in this review. Existing Node/DOM tests and structural checks remain useful within their narrower scopes.

## Optional external capabilities

Do not enable a provider to reproduce the native labs. External council mode requires server configuration, an access credential and explicit processing consent; it can incur provider usage. Weather, market and regulatory collectors require their own configured/consented paths. PDF text/OCR use local optional executables when installed. Modbus permits configured read-only registers; a status response does not prove device connectivity. Consult [interfaces](API_CLI_AND_INTERFACES.md), the preserved [security policy](../../SECURITY.md) and [.env.example](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.env.example) before an independently authorized external experiment.
