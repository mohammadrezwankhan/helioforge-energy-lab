# Toolchain and dependency matrix

| Layer | Declared source contract | Actual local observation,2026-11-19 |
|---|---|---|
| Python package | `requires-python >=3.11`; packaged launcher accepts 3.11–3.13; CI tests 3.11/3.12/3.13 | Python 3.12.14 used locally; no local claim for the other matrix interpreters |
| Node | Web package Node >=22; CI Node 24 | Node 24.22.3, npm 11.9.0 |
| TypeScript compile/typecheck |7.0.2, exact web lock | Actual no-emit check/build PASS with 7.0.2 |
| Static JS/TS inventory | Operational parser, not runtime dependency |5.9.3 parser; 131files,0 parse diagnostics. This is separate from locked compilation |
| Web build/parser/accessibility test packages | esbuild 0.28.2, parse5 8.1.1, axe-core 4.14.0 | npm ci with ignored lifecycle scripts; 273 existing Node tests PASS |
| Development Python | Optional ranges plus exact dependency-group versions | pytest 9.2.0, pytest-cov 7.1.0, Ruff 0.17.4; no full local mypy/hypothesis/coverage-matrix claim |
| Optional external council | openai-agents 0.24.0 | No live provider call; native/mocked tests and source inspection only |
| Native document extraction | Poppler/Tesseract when installed | No new supplied-document OCR acceptance run |
| Chromium | Real-browser workflow capability | Local capability FAIL(socket EPERM); new visual interaction NOT_RUN |
| Documentation renderer | Python standard library plus local Pandoc; deterministic local assets | Separate new documentation checks; no application dependency added |

Sources: [apps/api/pyproject.toml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/pyproject.toml), [apps/web/package.json](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/package.json), [apps/web/package-lock.json](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/package-lock.json), [launch.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/launch.py), [.github/workflows/ci.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/ci.yml).

## Exact API runtime pins

- `fastapi==0.162.4`
- `starlette==1.10.0`
- `uvicorn==0.54.0`
- `pydantic==2.14.3`
- `numpy==2.4.6`
- `scipy==1.17.1`
- `shapely==2.2.0`
- `httpx==0.28.1`


These exact packages were installed in the isolated local execution target before the main API suite, numerical asset checks and worked labs. The first narrow annual-comparator probe and independent IRR endpoint reproduction used pre-existing differing numerical versions; their original evidence remains unchanged. The pinned annual repeat is a separately dated result. The package installer’s success alone is not a compatibility test.

## Build and asset boundaries

The strict browser compile combines 35 ordered namespace source files. Generated full/hosted/standalone bundles and numerical JSON are preserved from source in the documentation candidate; local build work took place in a separate cache copy. All 819 canonical tracked files matched again after the fresh build, and the existing preview check confirmed exact source/runtime/style correspondence. Hosted deferred datasets are byte-counted and SHA-256 checked before installation into the browser catalogue. [apps/web/tsconfig.json](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/tsconfig.json), [scripts/compile-web.mjs](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/compile-web.mjs), [scripts/build-web.mjs](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/build-web.mjs), [apps/web/src/deferred-data.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/deferred-data.ts).

## Upgrade policy

Use the existing lockfiles and dependency groups. For a numerical upgrade, retain before/after inputs, solver status, objective/endpoint/conservation differences, all 59 study cases and intentional tolerance rationale. For a TypeScript/build upgrade, retain typecheck, complete Node tests, preview equality, hosted asset hashes and actual multi-browser acceptance. A tool upgrade must not rewrite numerical artifacts solely to make a mismatch disappear. Security/quality workflows remain unchanged; candidate PR checks determine current merge eligibility.
