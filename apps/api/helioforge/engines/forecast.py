"""Seeded scenario generator, deliberately not described as a validated price forecast."""
from __future__ import annotations

import numpy as np

from helioforge.schemas import ForecastRequest


def forecast_prices(p: ForecastRequest) -> dict:
    rng = np.random.default_rng(p.seed)
    values = np.full(p.paths, p.base_price_eur_mwh, dtype=float)
    rows = []
    for t in range(p.years):
        target = p.long_run_price_eur_mwh + p.trend_eur_mwh_year*t
        values = values + p.mean_reversion*(target-values) + rng.normal(0, p.annual_shock_eur_mwh, p.paths)
        low, median, high = np.quantile(values, [.1, .5, .9])
        rows.append({"year": p.start_year+t, "p10_eur_mwh": round(float(low), 2),
                     "p50_eur_mwh": round(float(median), 2), "p90_eur_mwh": round(float(high), 2),
                     "negative_price_probability": round(float(np.mean(values < 0)), 4)})
    return {"model": "mean-reverting-scenario-v1", "market": p.market, "seed": p.seed,
            "paths": p.paths, "data_kind": "synthetic", "rows": rows,
            "warnings": ["Uncalibrated annual-price scenarios, not market forecasts or backtested confidence intervals.",
                         "P10/P50/P90 are numerical quantiles, not exceedance-probability energy-yield labels.",
                         "Negative annual outcomes are allowed, not clipped. Currency is constant EUR, including GB demo.",
                         "Market code is metadata; geography changes require user-specified scenario parameters."]}
