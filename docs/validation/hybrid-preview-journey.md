# Hybrid run and restore at the local preview origin

On 9 November 2026, the preview and a separate local Python API were run on
Windows with external AI disabled and an isolated local test database. The
preview was built from source `b9fac68` plus the opt-in bridge in this change.
Use only synthetic inputs. This records a bounded software test, not system,
engineering, safety or general browser certification.

The default `node scripts/preview-demo.mjs` remains a read-only snapshot. To
exercise new hybrid calculations at its origin, install the local API as
specified in [its README](../../apps/api/README.md), then use two terminals.
For example, from the repository root in PowerShell, choose a **new** database
path and start the API:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'apps/api')
$env:HELIOFORGE_DB = (Join-Path $env:TEMP 'helioforge-example.sqlite3')
$env:ENABLE_OPENAI = 'false'
$env:ALLOWED_ORIGINS = 'http://127.0.0.1:4173'
python -m uvicorn helioforge.main:app --host 127.0.0.1 --port 8765
```

In a second terminal, set `$env:HELIOFORGE_PREVIEW_API_PORT = '8765'`, run
`node scripts/preview-demo.mjs`, and open `http://127.0.0.1:4173/`. The opt-in
bridge connects only to a loopback port and permits the overview, run history,
individual saved runs and hybrid simulation routes. It rejects other API
routes, non-loopback host headers, cross-origin writes and request bodies over
1 MB. It is not an authentication mechanism and should only be used with a
trusted local API and a disposable database. Other connected application
features are not supplied by this narrow bridge. Stop both processes with
Ctrl+C; existing database files are not deleted by the preview.

## Observed journey

Playwright 1.64.1 ran Firefox 157.0 and WebKit 27.2 at 1440 × 900, in fresh
browser contexts. For each browser:

1. Select **Hospital islanding microgrid**, retain its reference-day preset,
   set **Solar PV** to 777 kW, and choose **Run energy screen**. Both displayed
   100.0% critical and total load served, 0.0 kWh shortfall, 7.11 MWh grid
   energy imported over 24 modeled hours, and 0.45 MWh terminal battery
   energy from 1.80 MWh initial energy. The two result texts matched.
2. Change Solar PV to 999 kW; the stale result is hidden. Open **Analysis
   history** and choose **Open run** for the exact run ID just returned by the
   API. The form returns to 777 kW and the saved result reappears.
3. Reload at the same origin. The form still shows 777 kW and the saved result
   is restored. This depends on that browser workspace and the same local
   database. It is not cloud durability; clearing storage, switching origin or
   removing the database is outside this observation.

There were no uncaught page errors or page-level horizontal overflow in either
browser. Firefox logged no console errors; WebKit logged 63 CSP inline-style
refusals and two 404 messages over the full run and reload. Both browsers
received two 404 responses for the optional `/api/connectors/status` endpoint,
which the hybrid-only bridge deliberately does not expose. The earlier
[partial browser note](hybrid-cross-browser-partial.md) records a minimal
native-select CSP reproduction; the visual impact remains unknown and CSP was
not weakened. The baseline `python -m pytest apps/api/tests/test_hybrid.py`
passed 328 tests with one Starlette deprecation warning.
