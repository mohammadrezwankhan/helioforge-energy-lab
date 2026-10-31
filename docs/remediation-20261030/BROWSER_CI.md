# Browser CI assertions reconciled with the repaired contracts

## Terminal replacement-node timing

A subsequent isolated preflight produced 250 passing Terminal checks and one failure: the architecture card reported a zero height after selection. The app's `selectSystem()` calls `cb.navigate('hybrid')`, rebuilding the view and detaching the original card. Waiting only for the selector value was insufficient because it could already equal the requested system. A focused 375-by-844 reproduction observed the original node disconnect and its visible replacement measure 44 pixels.

The harness now waits for the connected, selected replacement card before measuring it. The existing minimum-height assertion remains 44 pixels; application code and release bytes are unchanged. The focused journey passed both checks and the full Terminal suite passed 251 checks, with 24 axe runs and zero violations or execution errors. `browser-terminal-recovery.json` preserves the report; its screenshot paths identify retained local temporary evidence. The main CI artifact now also includes its executed Terminal report.

Remote CI passed frozen study replay, build, frontend tests, 18 smoke checks and 14 hybrid checks, then failed at `browser-champion.py:175`: its reset assertion still expected workspace v1. The product's reviewed current schema is v2, with v1 handled separately by explicit migration. The test now asserts the literal v2 schema. A subsequent isolated full run exposed another stale expectation, `local API`, where the rendered guide says `local Python API`; the assertion now matches that disclosure. Application code and frozen artifacts were unchanged.

The hybrid suite's success label now describes eight deterministic checklist sections and explicitly states that no agents or critic execute. Its assertions still require eight cards and the exact selected saved run.

The isolated full Champion journey passed 18 checks using Windows, Python 3.12.14 and installed Chromium `chromium-1248/chrome-win64/chrome.exe`, direct browser HTTP and native localStorage. `browser-champion-recovery.json` retains the executed checks. The worker used `PYTHONPATH=apps/api`, `PYTHONUTF8=1`, `HELIOFORGE_DB` pointing to its named synthetic temporary SQLite file, `ENABLE_OPENAI=false`, `ALLOWED_ORIGINS=http://127.0.0.1:18167`, and `ALLOWED_HOSTS=127.0.0.1`.

Commands were `python -m uvicorn helioforge.main:app --host 127.0.0.1 --port 18167` and `scripts/browser-champion.py --url http://127.0.0.1:18167 --executable <installed Chromium path>`. The browser command ran through `runpy.run_path(..., run_name='__main__')`; a `Path.write_text` wrapper redirected only the fixed `docs/champion/browser-champion.json` output to a temporary report. No assertions or browser interactions were replaced. The owned Uvicorn process was stopped. No historical report, user database or provider was used. Remote CI will execute the ordinary script directly.
