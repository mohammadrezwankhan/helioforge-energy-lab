"""Transparent research baselines; not a trained fault classifier or certified LCA."""
from __future__ import annotations

import math

import numpy as np

from helioforge.schemas import DriftRequest, ReliabilityRequest, SustainabilityRequest


def detect_drift(p: DriftRequest) -> dict:
    residual = (np.asarray(p.observed)-np.asarray(p.expected))/np.asarray(p.expected)
    baseline = residual[:max(5, len(residual)//3)]
    center = float(np.median(baseline))
    # Robust normal-sigma estimate with 0.5% noise floor for flat baselines.
    sigma = max(float(np.median(np.abs(baseline-center)))*1.4826, 0.005)
    z = (residual-center)/sigma
    alerts = [int(i) for i in np.flatnonzero(np.abs(z) > p.threshold_sigma)]
    return {"model": "robust-residual-v1", "baseline_fraction": 1/3, "sigma_fraction": round(sigma, 6),
            "drift_pct": round(float(np.mean(residual[-5:]))*100, 3), "alert_count": len(alerts),
            "alert_indices": alerts, "series": [{"index": i, "residual_pct": round(float(v)*100, 3),
            "z_score": round(float(z[i]), 3)} for i, v in enumerate(residual)],
            "warnings": ["The first third must represent healthy operation; thresholds are not validated field alarms.",
                         "Pointwise robust residual screening, not causal diagnosis or an RUL model."]}


def reliability(p: ReliabilityRequest) -> dict:
    cumulative_hazard = (p.age_hours/p.scale_hours)**p.shape
    future_hazard = ((p.age_hours+p.horizon_hours)/p.scale_hours)**p.shape
    # Conditional probability avoids underflow from dividing two tiny survival probabilities.
    failure_probability = -math.expm1(-(future_hazard-cumulative_hazard))
    survival = math.exp(-cumulative_hazard)
    # Median remaining lifetime conditional on survival to current age.
    conditional_median = p.scale_hours*(cumulative_hazard+math.log(2))**(1/p.shape)-p.age_hours
    return {"model": "conditional-weibull-v1", "survival_pct": round(survival*100, 3),
            "conditional_failure_pct": round(failure_probability*100, 3),
            "conditional_median_remaining_hours": round(conditional_median, 2),
            "warnings": ["User-specified Weibull parameters; no fit to censored field data or calibrated prognostics."]}


def sustainability(p: SustainabilityRequest) -> dict:
    generation = sum(p.annual_generation_kwh*(1-p.degradation_fraction)**y for y in range(p.years))
    project_emissions = p.embodied_kgco2e + p.annual_operational_kgco2e*p.years + p.end_of_life_kgco2e
    avoided = generation*p.counterfactual_kgco2e_kwh-project_emissions
    return {"model": "carbon-screen-v1", "lifetime_generation_mwh": round(generation/1000, 2),
            "intensity_gco2e_kwh": round(project_emissions/generation*1000, 3),
            "net_counterfactual_avoided_tco2e": round(avoided/1000, 2),
            "project_lifecycle_tco2e": round(project_emissions/1000, 2),
            "warnings": ["Screening inventory, not an ISO-conformant or independently verified life-cycle assessment.",
                         "Avoided emissions depend on the assumed counterfactual; they are not carbon credits.",
                         "Biodiversity requires a separate ecological baseline and field survey; no automatic biodiversity score."]}
