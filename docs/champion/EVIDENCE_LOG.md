# Evidence index

Exact execution metadata: `BASELINE_RESULTS.csv` and `evidence/commands.jsonl`. Status is based on actual exit results; blocked tools and failed attempts are retained. The interrupted invocation is separately described in `evidence/interrupted-attempt.md`.

| Command | Exit | Log |
|---|---:|---|
| baseline-python | 0 | [log](evidence/baseline-python.log) |
| baseline-web | 0 | [log](evidence/baseline-web.log) |
| baseline-browser | 1 | [log](evidence/baseline-browser.log) |
| baseline-browser-bridge | 0 | [log](evidence/baseline-browser-bridge.log) |
| baseline-targeted | 0 | [log](evidence/baseline-targeted.log) |
| champion-build-1 | 0 | [log](evidence/champion-build-1.log) |
| champion-python-1 | 0 | [log](evidence/champion-python-1.log) |
| champion-browser-existing | 1 | [log](evidence/champion-browser-existing.log) |
| champion-regression-1 | 1 | [log](evidence/champion-regression-1.log) |
| champion-browser-existing-3 | 1 | [log](evidence/champion-browser-existing-3.log) |
| champion-new-browser-1 | 1 | [log](evidence/champion-new-browser-1.log) |
| champion-launch-check | 0 | [log](evidence/champion-launch-check.log) |
| champion-new-browser-2 | 1 | [log](evidence/champion-new-browser-2.log) |
| champion-launch-integration | 0 | [log](evidence/champion-launch-integration.log) |
| champion-new-browser-3 | 1 | [log](evidence/champion-new-browser-3.log) |
| champion-final-suite | 1 | [log](evidence/champion-final-suite.log) |
| champion-toolbar-reproduction | 0 | [log](evidence/champion-toolbar-reproduction.log) |
| champion-lint-availability | 1 | [log](evidence/champion-lint-availability.log) |
| champion-final-suite-2 | 0 | [log](evidence/champion-final-suite-2.log) |
| champion-syntax | 0 | [log](evidence/champion-syntax.log) |

Final browser results: `browser-champion.json`, `../browser-validation.json`, `../hybrid-browser-validation.json`. Backend counts: `python-tests.xml`. Local process and synthetic database recovery: `launcher-validation.json`. Read `VERIFICATION.md` for what these checks do and do not establish.
