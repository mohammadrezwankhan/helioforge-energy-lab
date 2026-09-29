> Historical report supplied with the earlier release. For current v0.3.0 evidence, see [Champion verification](champion/VERIFICATION.md). Old counts and readiness claims are not the current release gate.

# Validation record — 0.2.0

**Date:** 23 September 2026. These are observed checks in the build environment, not declarations that every deployment or scientific use is safe.

| Check | Result | Evidence |
|---|---|---|
| Python unit/API suite | **404 passed** | [python-tests.txt](python-tests.txt) |
| Python statement coverage | **98.49%** (785 / 797 statements) | [coverage.json](coverage.json) |
| Strict TypeScript compilation | Passed | `npm run typecheck`; `npm run build` |
| Frontend logic/render suite | **65 passed** | [frontend-tests.txt](frontend-tests.txt) |
| Original workspace browser flows | **18 passed** | [browser-tests.txt](browser-tests.txt), [browser-validation.json](browser-validation.json) |
| Hybrid/lesson/comparison browser flows | **14 passed** | [hybrid-browser-tests.txt](hybrid-browser-tests.txt), [hybrid-browser-validation.json](hybrid-browser-validation.json) |
| Architecture/scenario matrix | **285 runnable combinations tested** | `apps/api/tests/test_hybrid.py` |
| Parameter perturbations | **100 seeded cases**, invariants preserved | `test_seeded_input_fuzz_preserves_invariants` |
| Packaged API catalogue and calculation | Wheel build/import/simulation passed | [package-validation.txt](package-validation.txt) |
| Desktop and mobile | Actual screenshots inspected; all twelve views fit 390px and 320px | Screenshots in this directory and browser report |
| Live OpenAI / Docker / remote CI / publication | **Not run** | No credentials, paid calls, deployment or repository publication used |

## Environment and commands

Python 3.13.5; Node v22.16.0; Version 5.8.3; Chromium at `/usr/bin/chromium`. Exact Python package versions are in [release-validation.json](release-validation.json). TypeScript used the installed compiler. Clean dependency downloads and supported-version matrix execution were not repeated here.

```bash
PYTHONPATH=apps/api python -m pytest apps/api/tests -o addopts='' \
  --cov=helioforge --cov-report=json:docs/coverage.json --cov-report=term-missing
cd apps/web && npm run typecheck && npm run build && npm test
cd ../..
# Start the API in another terminal first.
python scripts/browser-smoke.py --bridge --executable /usr/bin/chromium --screenshots
python scripts/browser-hybrid.py --bridge --executable /usr/bin/chromium --screenshots
```

For an unrestricted local/CI browser, omit `--bridge` and optionally omit `--executable` after `python -m playwright install chromium`. Direct mode is the repository CI target, not a test that ran successfully in this restricted build environment.

## Browser boundary

The browser rendered the actual shipped HTML, executed its TypeScript output, drew the 3D canvas and exercised real DOM events. A host-side HTTP bridge forwarded API fetches to the running local server. Numerical results were not mocks. Direct browser localhost access was blocked by environment policy.

This validates the exercised UI and API workflows, not browser networking policy, direct CSP enforcement, file:// navigation, cross-reload storage persistence, Safari/Firefox compatibility, a full screen-reader audit or WCAG certification. Opaque-origin storage failure was handled visibly, and progress export still worked. The standalone build is self-contained; its direct file-launch path still needs a normal-machine acceptance test.

## Release acceptance interpretation

The release is suitable for local educational/research evaluation under documented limits. Internal conservation and regression tests are not independent scientific validation. A coverage percentage is not a benchmark or a security guarantee. The external agent adapter's structured concurrency and error paths were tested with a fake SDK, not a live paid model. Read [FINAL_AUDIT.md](FINAL_AUDIT.md) before wider release.
