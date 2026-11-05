"""Local-first application entry point; analytics are not operational plant control."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from helioforge.council import local_council, openai_council
from helioforge.council_protocol import external_failure_detail
from helioforge.dashboard import dashboard
from helioforge.engines.finance import calculate_finance, calculate_pv, screen_acquisition
from helioforge.engines.forecast import forecast_prices
from helioforge.engines.hybrid import simulate_hybrid
from helioforge.engines.research import detect_drift, reliability, sustainability
from helioforge.engines.storage import optimize_storage
from helioforge.engines.study_types import StudyDefinition
from helioforge.hybrid import HybridRequest, catalog, validate_configuration
from helioforge.hybrid_types import ConfigurationResult, HybridCatalog
from helioforge.integration_types import ConnectorStatus
from helioforge.integrations import (
    DocumentImport,
    GeoImport,
    MarketRequest,
    ModbusRequest,
    RegulatoryRequest,
    SeriesImport,
    TelemetryImport,
    WeatherRequest,
    connector_status,
    extract_document,
    import_geography,
    import_series,
    inspect_telemetry,
    market_prices,
    modbus_read,
    regulatory_feed,
    weather,
)
from helioforge.provenance import attach_result_provenance, storage_provenance_inputs
from helioforge.schemas import (
    CouncilRequest,
    DriftRequest,
    FinanceRequest,
    ForecastRequest,
    MARequest,
    Market,
    PilotUpdate,
    PVRequest,
    ReliabilityRequest,
    StorageRequest,
    SustainabilityRequest,
)
from helioforge.store import PilotEvent, RunSummary, SavedRun, Store
from helioforge.studies import StudyRequest
from helioforge.studies import catalogue as study_catalogue
from helioforge.studies import evaluate as evaluate_study

logger = logging.getLogger("helioforge")


class ProvenanceOptions(TypedDict, total=False):
    dataset_inputs: Mapping[str, object]
    data_identity: Mapping[str, object]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.store = Store()
    app.state.ai_lock = asyncio.Lock()
    yield


def _store(request: Request) -> Store:
    """Use the store installed by the application's lifespan before request dispatch."""
    store: Store = request.app.state.store
    return store


app = FastAPI(
    title="HelioForge API",
    version="0.3.0",
    lifespan=lifespan,
    description="Synthetic-first energy screening. Not investment advice or real-time plant control.",
)
origins = [
    x.strip()
    for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if x.strip()
]
# Loopback is the default trust boundary. An explicit allow-list is not authentication.
hosts = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",") if x.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts, www_redirect=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_guard(request: Request, call_next: RequestResponseEndpoint) -> Response:
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return JSONResponse(status_code=403, content={"detail": "Origin is not allowed."})
        # Bound request memory including chunked bodies, not only Content-Length.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1_000_000:
                return JSONResponse(status_code=413, content={"detail": "Maximum request body is 1 MB."})
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(uuid4())
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Scientific records are private local data; updated assets must revalidate after an upgrade.
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    # Inline script/style are used only in the downloadable standalone preview, not the served app.
    if request.url.path == "/" or request.url.path.endswith(".html"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'"
            " 'unsafe-inline'; img-src 'self' data:; connect-src 'self';"
            " object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
    return response


@app.exception_handler(ValueError)
async def bad_model_input(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health", response_model=None)
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "version": "0.3.0",
        "data_kind": "synthetic",
        "live_market_feeds": False,
        "openai_enabled": os.getenv("ENABLE_OPENAI", "false").lower() == "true",
    }


@app.get("/api/studies", response_model=None)
def studies_catalogue() -> list[StudyDefinition]:
    return study_catalogue()


@app.get("/api/connectors/status", response_model=None)
def connectors_status() -> ConnectorStatus:
    return connector_status()


@app.post("/api/evidence/series", response_model=None)
def evidence_series(p: SeriesImport, request: Request) -> dict[str, object]:
    return record(request, "series_import", p, import_series(p))


@app.post("/api/evidence/geography", response_model=None)
def evidence_geography(p: GeoImport, request: Request) -> dict[str, object]:
    return record(request, "geography_import", p, import_geography(p))


@app.post("/api/evidence/document", response_model=None)
def evidence_document(p: DocumentImport, request: Request) -> dict[str, object]:
    result = extract_document(p)
    return _store(request).save(
        "document_import",
        {**p.model_dump(exclude={"content_base64"}), "file_sha256": result["sha256"]},
        result,
    )


@app.post("/api/evidence/telemetry", response_model=None)
def evidence_telemetry(p: TelemetryImport, request: Request) -> dict[str, object]:
    return record(request, "telemetry_import", p, inspect_telemetry(p))


@app.post("/api/connectors/weather", response_model=None)
async def connector_weather(p: WeatherRequest, request: Request) -> dict[str, object]:
    if not p.consent:
        raise HTTPException(403, "Confirm sending these coordinates to Open-Meteo.")
    return record(request, "weather_feed", p, await weather(p))


@app.post("/api/connectors/market", response_model=None)
async def connector_market(p: MarketRequest, request: Request) -> dict[str, object]:
    if not p.consent:
        raise HTTPException(403, "Confirm the ENTSO-E request using server credentials.")
    return record(request, "market_feed", p, await market_prices(p))


@app.post("/api/connectors/regulatory", response_model=None)
async def connector_regulatory(p: RegulatoryRequest, request: Request) -> dict[str, object]:
    if not p.consent:
        raise HTTPException(403, "Confirm the official regulator feed request.")
    return record(request, "regulatory_feed", p, await regulatory_feed(p))


@app.post("/api/connectors/modbus", response_model=None)
def connector_modbus(
    p: ModbusRequest, request: Request, x_api_key: str | None = Header(default=None)
) -> dict[str, object]:
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key or "", expected):
        raise HTTPException(401, "A configured server ADMIN_API_KEY is required for device reads.")
    return record(request, "modbus_read", p, modbus_read(p))


@app.post("/api/studies/evaluate", response_model=None)
def study_evaluate(p: StudyRequest, request: Request) -> dict[str, object]:
    return record(request, "study", p, evaluate_study(p))


@app.get("/api/overview", response_model=None)
def overview(request: Request, market: Market = "FR") -> dict[str, object]:
    result = dict(dashboard(market))
    result["pilots"] = _store(request).pilots()
    return result


def record(request: Request, kind: str, inputs: BaseModel, result: Mapping[str, object]) -> dict[str, object]:
    model_id = {
        "storage": "storage",
        "finance": "finance",
        "pv": "pv",
        "forecast": "forecast",
        "drift": "drift",
        "reliability": "reliability",
        "carbon": "sustainability",
        "acquisition": "acquisition",
    }.get(kind)
    request_inputs = inputs.model_dump(mode="json")
    effective_inputs = request_inputs
    provenance_options: ProvenanceOptions = {}
    if model_id == "storage":
        effective_inputs, dataset_inputs, data_identity = storage_provenance_inputs(request_inputs)
        provenance_options = {"dataset_inputs": dataset_inputs, "data_identity": data_identity}
    # Old saved records are not routed through record(); only newly calculated
    # numerical results receive the source-bound envelope.
    if model_id and not result.get("provenance"):
        result = attach_result_provenance(
            result, model_id=model_id, inputs=effective_inputs, **provenance_options
        )
    return _store(request).save(kind, request_inputs, result)


@app.post("/api/storage/optimize", response_model=None)
def storage(p: StorageRequest, request: Request) -> dict[str, object]:
    return record(request, "storage", p, optimize_storage(p))


@app.post("/api/finance/evaluate", response_model=None)
def finance(p: FinanceRequest, request: Request) -> dict[str, object]:
    return record(request, "finance", p, calculate_finance(p))


@app.post("/api/pv/evaluate", response_model=None)
def pv(p: PVRequest, request: Request) -> dict[str, object]:
    return record(request, "pv", p, calculate_pv(p))


@app.post("/api/forecast/simulate", response_model=None)
def forecast(p: ForecastRequest, request: Request) -> dict[str, object]:
    return record(request, "forecast", p, forecast_prices(p))


@app.post("/api/research/drift", response_model=None)
def drift(p: DriftRequest, request: Request) -> dict[str, object]:
    return record(request, "drift", p, detect_drift(p))


@app.post("/api/research/reliability", response_model=None)
def predict_reliability(p: ReliabilityRequest, request: Request) -> dict[str, object]:
    return record(request, "reliability", p, reliability(p))


@app.post("/api/research/carbon", response_model=None)
def carbon(p: SustainabilityRequest, request: Request) -> dict[str, object]:
    return record(request, "carbon", p, sustainability(p))


@app.post("/api/acquisitions/screen", response_model=None)
def acquisition(p: MARequest, request: Request) -> dict[str, object]:
    return record(request, "acquisition", p, screen_acquisition(p))


@app.post("/api/council/review", response_model=None)
async def council(
    p: CouncilRequest, request: Request, x_api_key: str | None = Header(default=None)
) -> dict[str, object]:
    evidence_dashboard = await run_in_threadpool(dashboard, p.market)
    evidence = {k: evidence_dashboard[k] for k in ["dispatch", "finance", "sustainability"]}
    supplied_records: list[dict[str, object]] = []
    evidence["supplied_records"] = supplied_records
    for run_id in p.evidence_run_ids:
        saved = _store(request).get_run(run_id)
        if saved is None:
            raise HTTPException(404, "An evidence run was not found.")
        item: dict[str, object] = {
            "run_id": saved["run_id"],
            "kind": saved["kind"],
            "created_at": saved["created_at"],
            "input_sha256": saved["input_sha256"],
            "inputs": saved["inputs"],
            "result": saved["result"],
        }
        if len(json.dumps(item)) > 30000:
            raise HTTPException(
                422,
                (
                    "Each council evidence record must be at most 30 KB. Supply a"
                    " bounded summary with the source digest."
                ),
            )
        supplied_records.append(item)
    if p.hybrid_run_id:
        saved = _store(request).get_run(p.hybrid_run_id)
        if saved is None or saved["kind"] != "hybrid":
            raise HTTPException(404, "Saved hybrid run not found. Select an actual completed hybrid run.")
        evidence["hybrid"] = {
            "run_id": saved["run_id"],
            "input_sha256": saved["input_sha256"],
            "inputs": saved["inputs"],
            "summary": {k: v for k, v in saved["result"].items() if k != "schedule"},
        }
    result: Mapping[str, object]
    if p.mode == "local":
        result = local_council(p, evidence)
    else:

        def external_not_started(status_code: int, message: str) -> HTTPException:
            return HTTPException(
                status_code,
                detail=external_failure_detail(
                    status="not_started",
                    cross_examination_rounds=p.cross_examination_rounds,
                    model=os.getenv("OPENAI_MODEL"),
                    consent_to_external_processing=p.consent_to_external_processing,
                    message=f"{message} No external council execution started.",
                ),
            )

        if os.getenv("ENABLE_OPENAI", "false").lower() != "true":
            raise external_not_started(403, "OpenAI mode is disabled; local mode requires no API key.")
        expected = os.getenv("ADMIN_API_KEY", "")
        if not expected or not secrets.compare_digest(x_api_key or "", expected):
            raise external_not_started(401, "A valid server ADMIN_API_KEY is required in X-API-Key.")
        if not p.consent_to_external_processing:
            raise external_not_started(
                422, "Explicit consent to send the brief and evidence to OpenAI is required."
            )
        if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
            raise external_not_started(503, "Set server-side OPENAI_API_KEY and OPENAI_MODEL.")
        ai_lock: asyncio.Lock = request.app.state.ai_lock
        if ai_lock.locked():
            raise external_not_started(
                429, "An external council review is already running. Retry after it completes."
            )
        async with ai_lock:
            try:
                result = await openai_council(p, evidence)
            except ImportError:
                raise HTTPException(
                    503,
                    detail=external_failure_detail(
                        status="not_started",
                        cross_examination_rounds=p.cross_examination_rounds,
                        model=os.getenv("OPENAI_MODEL"),
                        message="Install the API ai optional dependency. No provider execution started.",
                    ),
                ) from None
            except TimeoutError:
                raise HTTPException(
                    504,
                    detail=external_failure_detail(
                        status="timed_out",
                        cross_examination_rounds=p.cross_examination_rounds,
                        model=os.getenv("OPENAI_MODEL"),
                        message=(
                            "External review timed out under helioforge-council/v1. No result was recorded. "
                            "Sibling cancellation was requested on a best-effort basis; "
                            "provider work may continue "
                            "and charges may remain."
                        ),
                    ),
                ) from None
            except Exception:
                # Never leak provider payloads or credentials via errors/logs.
                logger.warning("External council failed; inspect provider diagnostics securely.")
                raise HTTPException(
                    502,
                    detail=external_failure_detail(
                        status="failed",
                        cross_examination_rounds=p.cross_examination_rounds,
                        model=os.getenv("OPENAI_MODEL"),
                        message=(
                            "External review failed under helioforge-council/v1. "
                            "No result was recorded or local "
                            "review substituted. Sibling cancellation was requested on a best-effort basis; "
                            "provider work may continue and charges may remain."
                        ),
                    ),
                ) from None
    return record(request, "council", p, result)


@app.get("/api/runs", response_model=None)
def runs(request: Request) -> list[RunSummary]:
    return _store(request).list_runs()


@app.get("/api/runs/{run_id}", response_model=None)
def run(run_id: str, request: Request) -> SavedRun:
    result = _store(request).get_run(run_id)
    if result is None:
        raise HTTPException(404, "Analysis run not found.")
    return result


@app.get("/api/pilots", response_model=None)
def pilots(request: Request) -> list[dict[str, object]]:
    return _store(request).pilots()


@app.get("/api/pilots/events", response_model=None)
def pilot_events(request: Request) -> list[PilotEvent]:
    return _store(request).pilot_events()


@app.patch("/api/pilots/{pilot_id}", response_model=None)
def update_pilot(pilot_id: str, p: PilotUpdate, request: Request) -> dict[str, object]:
    result = _store(request).update_pilot(pilot_id, p.model_dump())
    if result is None:
        raise HTTPException(404, "Pilot not found.")
    return result


@app.get("/api/hybrid/catalog", response_model=None)
def hybrid_catalog() -> HybridCatalog:
    return catalog()


@app.post("/api/hybrid/validate", response_model=None)
def hybrid_validate(p: HybridRequest) -> ConfigurationResult:
    return validate_configuration(p)


@app.post("/api/hybrid/simulate", response_model=None)
def hybrid_simulate(p: HybridRequest, request: Request) -> dict[str, object]:
    return record(request, "hybrid", p, simulate_hybrid(p))


# Build frontend first. Missing frontend does not prevent API-only use or testing.
web_dist = Path(os.getenv("WEB_DIST", Path(__file__).resolve().parents[2] / "web" / "dist"))
if web_dist.is_dir():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="dashboard")
