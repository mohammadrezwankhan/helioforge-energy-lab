# Hybrid run restoration (partial)

On 9 November 2026, Chromium 151.0.7922.34 on Windows at 1440 × 900
exercised the local API-backed application from source commit
`e7e1f0c5373b8d35a397d6f61f016e69fcbda1d8`. The example is synthetic and
uses a separate local test database. External AI was disabled.

The requested `node scripts/preview-demo.mjs` origin serves a read-only
standalone preview: after an input edit, its **Run** control is disabled.
The following observed new-run journey therefore used the local Python API
at `http://127.0.0.1:8765`, with that exact origin allowed. For example, after
installing the API, set `ENABLE_OPENAI=false`, point `HELIOFORGE_DB` to a new
test database, set `ALLOWED_ORIGINS=http://127.0.0.1:8765`, and run
`python -m uvicorn helioforge.main:app --host 127.0.0.1 --port 8765`.

1. Select **Hospital islanding microgrid**, retain its reference-day preset,
   change solar capacity to **777 kW**, and run. The result displayed 100.0%
   critical and total load served, 7.11 MWh imported and 0.45 MWh terminal
   battery energy from 1.80 MWh initial energy. The API saved a run with an
   ID and inputs in the local database.
2. Change solar capacity to **999 kW**. The old numerical result is hidden as
   stale. Open **Analysis history** and choose **Open run** for the saved
   hybrid result. Solar capacity returns to **777 kW** and the saved result
   is displayed without a new simulation.
3. Reload the page in the same browser with the same local database available.
   The **777 kW** input and saved result were restored. This depends on the
   browser workspace and local database; it is not cloud durability. Clearing
   browser storage, removing the database or switching origin is outside this
   observed sequence.

The preview-origin edited-input run requested by the issue remains unverified
because the preview is deliberately read-only. No persistence feature was
added, and these results do not establish engineering or safety validation.

A subsequent [preview-origin run and restoration](hybrid-preview-journey.md)
uses an explicitly enabled local hybrid bridge; the default preview remains
read-only.
