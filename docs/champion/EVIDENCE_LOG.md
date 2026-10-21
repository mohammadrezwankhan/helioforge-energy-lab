# Evidence index

> Historical release inventory. The log paths in the table below are not included in this source checkout. The recorded exit codes are retained as historical claims, not independently reproducible log evidence. Use the current workflow runs and `VERIFICATION.md` for their stated scope; do not infer that missing logs passed a new audit.

Exact execution metadata: `BASELINE_RESULTS.csv` and `evidence/commands.jsonl`. Status is based on actual exit results; blocked tools and failed attempts are retained. The interrupted invocation is separately described in `evidence/interrupted-attempt.md`.

| Command | Exit | Log |
|---|---:|---|
| baseline-python | 0 | `evidence/baseline-python.log` (not shipped) |
| baseline-web | 0 | `evidence/baseline-web.log` (not shipped) |
| baseline-browser | 1 | `evidence/baseline-browser.log` (not shipped) |
| baseline-browser-bridge | 0 | `evidence/baseline-browser-bridge.log` (not shipped) |
| baseline-targeted | 0 | `evidence/baseline-targeted.log` (not shipped) |
| champion-build-1 | 0 | `evidence/champion-build-1.log` (not shipped) |
| champion-python-1 | 0 | `evidence/champion-python-1.log` (not shipped) |
| champion-browser-existing | 1 | `evidence/champion-browser-existing.log` (not shipped) |
| champion-regression-1 | 1 | `evidence/champion-regression-1.log` (not shipped) |
| champion-browser-existing-3 | 1 | `evidence/champion-browser-existing-3.log` (not shipped) |
| champion-new-browser-1 | 1 | `evidence/champion-new-browser-1.log` (not shipped) |
| champion-launch-check | 0 | `evidence/champion-launch-check.log` (not shipped) |
| champion-new-browser-2 | 1 | `evidence/champion-new-browser-2.log` (not shipped) |
| champion-launch-integration | 0 | `evidence/champion-launch-integration.log` (not shipped) |
| champion-new-browser-3 | 1 | `evidence/champion-new-browser-3.log` (not shipped) |
| champion-final-suite | 1 | `evidence/champion-final-suite.log` (not shipped) |
| champion-toolbar-reproduction | 0 | `evidence/champion-toolbar-reproduction.log` (not shipped) |
| champion-lint-availability | 1 | `evidence/champion-lint-availability.log` (not shipped) |
| champion-final-suite-2 | 0 | `evidence/champion-final-suite-2.log` (not shipped) |
| champion-syntax | 0 | `evidence/champion-syntax.log` (not shipped) |

Final browser results: `browser-champion.json`, `../browser-validation.json`, `../hybrid-browser-validation.json`. Backend counts: `python-tests.xml`. Local process and synthetic database recovery: `launcher-validation.json`. Read `VERIFICATION.md` for what these checks do and do not establish.
