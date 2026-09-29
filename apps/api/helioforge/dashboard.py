from __future__ import annotations

from functools import lru_cache

import numpy as np

from helioforge.catalog import MARKETS, PILOTS, PROJECTS, SOURCES
from helioforge.council import local_council
from helioforge.engines.finance import calculate_finance, calculate_pv, screen_acquisition
from helioforge.engines.forecast import forecast_prices
from helioforge.engines.research import detect_drift, reliability, sustainability
from helioforge.engines.storage import optimize_storage
from helioforge.schemas import (
    CouncilRequest,
    DriftRequest,
    FinanceRequest,
    ForecastRequest,
    MARequest,
    PVRequest,
    ReliabilityRequest,
    StorageRequest,
    SustainabilityRequest,
)


@lru_cache(maxsize=6)
def dashboard(market: str = "FR") -> dict:
    rng = np.random.default_rng(11)
    expected = np.full(36, 1000.)
    observed = expected*(1+rng.normal(0, .009, 36))
    observed[26:] *= .94
    dispatch = optimize_storage(StorageRequest(market=market))
    finance = calculate_finance(FinanceRequest())
    result = {"version": "0.3.0", "data_kind": "synthetic", "as_of": "Illustrative scenario · not live",
              "market": market, "portfolio": PROJECTS, "markets": MARKETS, "sources": SOURCES,
              "pilots": PILOTS, "dispatch": dispatch, "finance": finance, "pv": calculate_pv(PVRequest()),
              "acquisition": screen_acquisition(MARequest()), "forecast": forecast_prices(ForecastRequest(market=market)),
              "drift": detect_drift(DriftRequest(expected=expected.tolist(), observed=observed.tolist())),
              "reliability": reliability(ReliabilityRequest()), "sustainability": sustainability(SustainabilityRequest()),
              "defaults": {"storage": StorageRequest(market=market).model_dump(), "finance": FinanceRequest().model_dump(),
                           "pv": PVRequest().model_dump(), "forecast": ForecastRequest(market=market).model_dump(),
                           "acquisition": MARequest().model_dump(), "reliability": ReliabilityRequest().model_dump(),
                           "sustainability": SustainabilityRequest().model_dump()},
              "professional_context": {"user_reported_pv_pipeline_gwp": "not included", "as_of": "not applicable",
                    "note": "Private professional context is excluded from the public synthetic demonstration."}}
    result["council"] = local_council(CouncilRequest(market=market), {"dispatch": dispatch, "finance": finance})
    return result
