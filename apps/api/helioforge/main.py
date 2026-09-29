"""Local-first application entry point; analytics are not operational plant control."""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from helioforge.council import local_council, openai_council
from helioforge.dashboard import dashboard
from helioforge.engines.finance import calculate_finance, calculate_pv, screen_acquisition
from helioforge.engines.forecast import forecast_prices
from helioforge.engines.research import detect_drift, reliability, sustainability
from helioforge.engines.storage import optimize_storage
from helioforge.engines.hybrid import simulate_hybrid
from helioforge.hybrid import HybridRequest, catalog, validate_configuration
from helioforge.schemas import (CouncilRequest, DriftRequest, FinanceRequest, ForecastRequest,
                               MARequest, Market, PilotUpdate, PVRequest, ReliabilityRequest,
                               StorageRequest, SustainabilityRequest)
from helioforge.store import Store

logger = logging.getLogger("helioforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = Store()
    app.state.ai_lock = asyncio.Lock()
    yield


app = FastAPI(title="HelioForge API", version="0.3.0", lifespan=lifespan,
              description="Synthetic-first energy screening. Not investment advice or real-time plant control.")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if x.strip()]
# Loopback is the default trust boundary. An explicit allow-list is not authentication.
hosts = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",") if x.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts, www_redirect=False)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "X-API-Key"])


@app.middleware("http")
async def request_guard(request: Request, call_next):
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
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.exception_handler(ValueError)
async def bad_model_input(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0", "data_kind": "synthetic", "live_market_feeds": False,
            "openai_enabled": os.getenv("ENABLE_OPENAI", "false").lower() == "true"}


@app.get("/api/overview")
def overview(request: Request, market: Market = "FR"):
    result = dict(dashboard(market))
    result["pilots"] = request.app.state.store.pilots()
    return result


def record(request: Request, kind: str, inputs, result):
    return request.app.state.store.save(kind, inputs.model_dump(), result)


@app.post("/api/storage/optimize")
def storage(p: StorageRequest, request: Request):
    return record(request, "storage", p, optimize_storage(p))


@app.post("/api/finance/evaluate")
def finance(p: FinanceRequest, request: Request):
    return record(request, "finance", p, calculate_finance(p))


@app.post("/api/pv/evaluate")
def pv(p: PVRequest, request: Request):
    return record(request, "pv", p, calculate_pv(p))


@app.post("/api/forecast/simulate")
def forecast(p: ForecastRequest, request: Request):
    return record(request, "forecast", p, forecast_prices(p))


@app.post("/api/research/drift")
def drift(p: DriftRequest, request: Request):
    return record(request, "drift", p, detect_drift(p))


@app.post("/api/research/reliability")
def predict_reliability(p: ReliabilityRequest, request: Request):
    return record(request, "reliability", p, reliability(p))


@app.post("/api/research/carbon")
def carbon(p: SustainabilityRequest, request: Request):
    return record(request, "carbon", p, sustainability(p))


@app.post("/api/acquisitions/screen")
def acquisition(p: MARequest, request: Request):
    return record(request, "acquisition", p, screen_acquisition(p))


@app.post("/api/council/review")
async def council(p: CouncilRequest, request: Request, x_api_key: str | None = Header(default=None)):
    evidence_dashboard = await run_in_threadpool(dashboard, p.market)
    evidence = {k: evidence_dashboard[k] for k in ["dispatch", "finance", "sustainability"]}
    if p.hybrid_run_id:
        saved = request.app.state.store.get_run(p.hybrid_run_id)
        if saved is None or saved["kind"] != "hybrid":
            raise HTTPException(404, "Saved hybrid run not found. Select an actual completed hybrid run.")
        evidence["hybrid"] = {"run_id": saved["run_id"], "input_sha256": saved["input_sha256"],
                              "inputs": saved["inputs"],
                              "summary": {k:v for k,v in saved["result"].items() if k != "schedule"}}
    if p.mode == "local":
        result = local_council(p, evidence)
    else:
        if os.getenv("ENABLE_OPENAI", "false").lower() != "true":
            raise HTTPException(403, "OpenAI mode is disabled; local mode requires no API key.")
        expected = os.getenv("ADMIN_API_KEY", "")
        if not expected or not secrets.compare_digest(x_api_key or "", expected):
            raise HTTPException(401, "A valid server ADMIN_API_KEY is required in X-API-Key.")
        if not p.consent_to_external_processing:
            raise HTTPException(422, "Explicit consent to send the brief and demo evidence to OpenAI is required.")
        if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
            raise HTTPException(503, "Set server-side OPENAI_API_KEY and OPENAI_MODEL.")
        if request.app.state.ai_lock.locked():
            raise HTTPException(429, "An external council review is already running. Retry after it completes.")
        async with request.app.state.ai_lock:
            try:
                result = await openai_council(p, evidence)
            except ImportError:
                raise HTTPException(503, "Install the API ai optional dependency.") from None
            except TimeoutError:
                raise HTTPException(504, "External review timed out; no approval or result was recorded.") from None
            except Exception:
                # Never leak provider payloads or credentials via errors/logs.
                logger.warning("External council failed; inspect provider diagnostics securely.")
                raise HTTPException(502, "External review failed. No local result has been substituted.") from None
    return record(request, "council", p, result)


@app.get("/api/runs")
def runs(request: Request):
    return request.app.state.store.list_runs()


@app.get("/api/runs/{run_id}")
def run(run_id: str, request: Request):
    result = request.app.state.store.get_run(run_id)
    if result is None:
        raise HTTPException(404, "Analysis run not found.")
    return result


@app.get("/api/pilots")
def pilots(request: Request):
    return request.app.state.store.pilots()


@app.get("/api/pilots/events")
def pilot_events(request: Request):
    return request.app.state.store.pilot_events()


@app.patch("/api/pilots/{pilot_id}")
def update_pilot(pilot_id: str, p: PilotUpdate, request: Request):
    result = request.app.state.store.update_pilot(pilot_id, p.model_dump())
    if result is None:
        raise HTTPException(404, "Pilot not found.")
    return result


@app.get("/api/hybrid/catalog")
def hybrid_catalog():
    return catalog()


@app.post("/api/hybrid/validate")
def hybrid_validate(p: HybridRequest):
    return validate_configuration(p)


@app.post("/api/hybrid/simulate")
def hybrid_simulate(p: HybridRequest, request: Request):
    return record(request, "hybrid", p, simulate_hybrid(p))


# Build frontend first. Missing frontend does not prevent API-only use or testing.
web_dist = Path(os.getenv("WEB_DIST", Path(__file__).resolve().parents[2] / "web" / "dist"))
if web_dist.is_dir():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="dashboard")
