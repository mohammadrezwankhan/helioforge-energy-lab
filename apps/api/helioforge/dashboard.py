from __future__ import annotations

from functools import lru_cache

import numpy as np

from helioforge.catalog import MARKETS, PILOTS, PROJECTS, SOURCES
from helioforge.council import local_council
from helioforge.engines.finance import calculate_finance, calculate_pv, screen_acquisition
from helioforge.engines.forecast import forecast_prices
from helioforge.engines.research import detect_drift, reliability, sustainability
from helioforge.engines.storage import optimize_storage
from helioforge.provenance import attach_result_provenance, storage_provenance_inputs
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
    storage_inputs = StorageRequest(market=market)
    finance_inputs = FinanceRequest()
    pv_inputs = PVRequest()
    acquisition_inputs = MARequest()
    forecast_inputs = ForecastRequest(market=market)
    drift_inputs = DriftRequest(expected=expected.tolist(), observed=observed.tolist())
    reliability_inputs = ReliabilityRequest()
    sustainability_inputs = SustainabilityRequest()
    dispatch_raw = optimize_storage(storage_inputs)
    finance_raw = calculate_finance(finance_inputs)
    storage_effective_inputs, storage_dataset_inputs, storage_data_identity = storage_provenance_inputs(storage_inputs.model_dump())
    # Keep the local council's evidence payload byte-for-byte equivalent in
    # shape to the pre-envelope snapshot; provenance decorates public results.
    dispatch = attach_result_provenance(
        dispatch_raw, model_id="storage", inputs=storage_effective_inputs,
        dataset_inputs=storage_dataset_inputs, data_identity=storage_data_identity,
    )
    finance = attach_result_provenance(finance_raw, model_id="finance", inputs=finance_inputs.model_dump())
    result = {"version": "0.3.0", "data_kind": "synthetic", "as_of": "Illustrative scenario · not live",
              "market": market, "portfolio": PROJECTS, "markets": MARKETS, "sources": SOURCES,
              "pilots": PILOTS, "dispatch": dispatch, "finance": finance,
              "pv": attach_result_provenance(calculate_pv(pv_inputs), model_id="pv", inputs=pv_inputs.model_dump()),
              "acquisition": attach_result_provenance(screen_acquisition(acquisition_inputs), model_id="acquisition", inputs=acquisition_inputs.model_dump()),
              "forecast": attach_result_provenance(forecast_prices(forecast_inputs), model_id="forecast", inputs=forecast_inputs.model_dump()),
              "drift": attach_result_provenance(detect_drift(drift_inputs), model_id="drift", inputs=drift_inputs.model_dump()),
              "reliability": attach_result_provenance(reliability(reliability_inputs), model_id="reliability", inputs=reliability_inputs.model_dump()),
              "sustainability": attach_result_provenance(sustainability(sustainability_inputs), model_id="sustainability", inputs=sustainability_inputs.model_dump()),
              "defaults": {"storage": storage_inputs.model_dump(), "finance": finance_inputs.model_dump(),
                           "pv": pv_inputs.model_dump(), "forecast": forecast_inputs.model_dump(),
                           "acquisition": acquisition_inputs.model_dump(), "reliability": reliability_inputs.model_dump(),
                           "sustainability": sustainability_inputs.model_dump()},
              "professional_context": {"user_reported_pv_pipeline_gwp": "not included", "as_of": "not applicable",
                    "note": "Private professional context is excluded from the public synthetic demonstration."}}
    result["council"] = local_council(CouncilRequest(market=market), {"dispatch": dispatch_raw, "finance": finance_raw})
    return result
