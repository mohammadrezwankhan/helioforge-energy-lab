# Local evidence and connector setup

The static public preview displays bundled examples. Imports, new calculations and upstream/device connections run only through the local Python API. Settings below are environment variables; neither `.env.example` nor the development launcher automatically loads a private `.env` file. Keep the server on loopback. `launch.py` deliberately disables external AI; an operator enabling it must start the API with the intended environment.

## Imports

Every view has an evidence panel. CSV expects the exact columns `timestamp,value`, a declared unit and ordered, unique timestamps with UTC offsets. It accepts up to 20,000 observations and 700,000 text characters, never invents missing observations and records a SHA-256 digest. Choose a returned numeric column and a compatible study array field to apply it; this invalidates the previous result.

Overview accepts WGS84 GeoJSON FeatureCollection Point features (longitude, latitude), at most 200. No coordinates are inferred. The resulting map and GeoJSON export preserve supplied coordinates; this is not a cadastral survey.

Document ingestion accepts text/CSV/JSON/Markdown/XML directly, PDF through `pdftotext` (Poppler, first 20 pages), and supported images through `tesseract`, with a 700 KB decoded limit and bounded extraction time. Extracted tariff, warranty, diagram, EPD and regulation candidates remain unverified. Scanned PDFs need a separately supplied OCR image. No remote URL is fetched from an uploaded document. The audit stores metadata/hash and extraction, not the base64 file. Review storage/privacy before supplying confidential records.

Telemetry JSON supplies source, timestamp and readings containing channel/value/unit and optional warning/critical thresholds. Staleness, threshold state and operational alarm approval are distinct. Importing data never commissions a safety alarm.

## Provider configuration

| Feature | Required settings | Execution boundary |
|---|---|---|
| Open-Meteo weather | No key for the public endpoint; optional `OPEN_METEO_API_KEY` uses the customer endpoint | Explicit browser consent; coordinates and requested hours are sent. Service terms and data licensing still apply. Null provider values stay null. |
| ENTSO-E prices | `ENTSOE_API_TOKEN` | Explicit consent; one UTC day and a supported market EIC. EUR/MWh and 15/30/60-minute periods are retained; unsupported currency, missing intervals and malformed XML fail closed. |
| Official regulatory publications | `HELIOFORGE_REGULATORY_FEEDS` JSON mapping FR/DE/ES/IT/NL/GB to an actual official regulator HTTPS RSS/Atom URL | Explicit consent; no redirects or arbitrary browser-supplied endpoint. Changed hashes compare publications; publication timestamps are not verified effective dates. |
| Modbus TCP | `ADMIN_API_KEY`, `HELIOFORGE_MODBUS_DEVICES` JSON mapping an alias to host/port/unit/address/count/function | The operator configures reachable devices. Browser submits only the alias and admin key; functions 3/4 read uint16 registers. No write command is implemented. Scaling/units/calibration belong to the instrument configuration and engineering review. |
| External council | Install `apps/api[ai]`; `ENABLE_OPENAI=true`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ADMIN_API_KEY` | Protocol `helioforge-council/v1`: explicit consent transmits the brief/calculated evidence/selected saved evidence or imports. Eight specialists + one or two paired rounds + critic plan 17 or 25 Agents SDK `Runner.run` invocations. Each invocation permits up to two turns, so this is not a provider HTTP request, token or cost count. Workflow timeout is 300 seconds. Sibling cancellation is best effort and does not confirm provider work stopped; usage may still be billed. Cost is not estimated and no application monetary budget is enforced. Tracing is disabled. See [the versioned protocol](../COUNCIL_PROTOCOL.md). |

Copy configuration shapes from `.env.example`, replacing documentation-only addresses with actual operator-approved settings. Status reports indicate configuration presence, not a successful authenticated connection. Secret values are not returned to the browser. Provider responses are bounded to 2 MB with a 15-second timeout and no redirects.

The application does not schedule polling or imply a background regulatory monitor. Fetches occur only when requested. Official-source review must determine applicability and legal dates.

## Survey reconstruction

Install COLMAP separately and put its executable on PATH. Supply 3–200 overlapping original JPG/PNG photos, each at most 30 MB, and calibrated PINHOLE intrinsics `fx,fy,cx,cy`. Run:

```sh
python scripts/reconstruct-pilot.py --images /path/to/photos --output /path/to/new-reconstruction --camera-params fx,fy,cx,cy
```

The output must be a new directory outside the photo directory. The adapter runs feature extraction, exhaustive matching, sparse mapping and text model conversion. Reconstruction has arbitrary scale until independently tied to surveyed control; use the registration study only with compatible coordinate systems. This release has no supplied real photos and therefore does not claim a successful real reconstruction.

## Observed validation

Local import, parsing, authorization, transport and council orchestration tests use controlled fixtures. One consented public Open-Meteo request returned 24 actual hourly rows for Paris on 17 October 2026 UTC. ENTSO-E, paid AI, official feeds, Modbus instruments, Poppler/Tesseract and COLMAP were not validated against real credentials/documents/devices in this release. Their prerequisites remain visible in the UI.
