"""Behind-the-meter MILP with explicit battery and grid direction binaries.

The objective is interval electricity cost + period peak charge + discharged-energy wear.
No ancillary-service or capacity revenue is invented or added to the dispatch result.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from helioforge.schemas import StorageRequest

# Illustrative retail scenarios ONLY. Not current tariffs, legal advice or market data.
PRICE_MULTIPLIERS = {"FR": 1.0, "DE": 1.18, "ES": 0.84, "IT": 1.13, "NL": 1.06, "GB": 1.15}


def demo_profile(market: str = "FR") -> dict:
    hours = np.arange(24)
    load = 2450 + 1850 * np.exp(-((hours - 13) / 5) ** 2) + 900 * np.exp(-((hours - 19) / 2.5) ** 2)
    pv = np.maximum(0, 5900 * np.sin(np.pi * (hours - 6) / 12))
    prices = np.array([.105, .092, .088, .085, .09, .105, .14, .20, .23, .18, .13, .10,
                       .08, .07, .075, .11, .18, .28, .35, .32, .27, .205, .16, .125])
    prices *= PRICE_MULTIPLIERS[market]
    export = np.maximum(0.025, prices * 0.40)
    return {"load_kw": load.tolist(), "pv_kw": pv.tolist(), "import_eur_per_kwh": prices.tolist(),
            "export_eur_per_kwh": export.tolist()}


def optimize_storage(request: StorageRequest) -> dict:
    raw = request.model_dump()
    is_demo = not request.load_kw
    if is_demo:
        raw.update(demo_profile(request.market))
    p = StorageRequest(**raw)
    n, dt = len(p.load_kw), p.interval_hours
    load, pv = np.asarray(p.load_kw), np.asarray(p.pv_kw)
    buy, sell = np.asarray(p.import_eur_per_kwh), np.asarray(p.export_eur_per_kwh)
    eta = math.sqrt(p.round_trip_efficiency)
    # c,d,i,e,curtailment,SOC(n+1),battery_mode,grid_mode,peak
    c, d, imp, exp, cur = [np.arange(k*n, (k+1)*n) for k in range(5)]
    soc = np.arange(5*n, 6*n+1)
    battery_mode = np.arange(6*n+1, 7*n+1)
    grid_mode = np.arange(7*n+1, 8*n+1)
    peak, size = 8*n+1, 8*n+2
    objective = np.zeros(size)
    objective[imp], objective[exp], objective[d] = buy*dt, -sell*dt, p.wear_eur_per_kwh*dt
    objective[peak] = p.peak_charge_eur_per_kw_period
    lower, upper = np.zeros(size), np.full(size, np.inf)
    upper[c], upper[d], upper[imp], upper[exp], upper[cur] = (
        p.power_kw, p.power_kw, p.grid_import_limit_kw, p.grid_export_limit_kw, pv)
    lower[soc], upper[soc] = p.capacity_kwh*p.min_soc_fraction, p.capacity_kwh*p.max_soc_fraction
    # Equal terminal SOC: no free energy from emptying the battery at the horizon end.
    lower[soc[0]] = upper[soc[0]] = p.capacity_kwh*p.initial_soc_fraction
    lower[soc[-1]] = upper[soc[-1]] = p.capacity_kwh*p.initial_soc_fraction
    upper[battery_mode] = upper[grid_mode] = 1
    upper[peak] = p.grid_import_limit_kw
    integrality = np.zeros(size, dtype=int)
    integrality[battery_mode] = integrality[grid_mode] = 1
    a = lil_matrix((7*n, size), dtype=float)
    lo, hi = np.full(7*n, -np.inf), np.zeros(7*n)
    row = 0
    for t in range(n):
        # PV - curtailment + import + discharge = load + charge + export.
        a[row, [imp[t], exp[t], d[t], c[t], cur[t]]] = [1, -1, 1, -1, -1]
        lo[row] = hi[row] = load[t] - pv[t]
        row += 1
        a[row, [soc[t+1], soc[t], c[t], d[t]]] = [1, -1, -eta*dt, dt/eta]
        lo[row] = hi[row] = 0
        row += 1
        a[row, [c[t], battery_mode[t]]] = [1, -p.power_kw]
        row += 1
        a[row, [d[t], battery_mode[t]]] = [1, p.power_kw]
        hi[row] = p.power_kw
        row += 1
        a[row, [imp[t], grid_mode[t]]] = [1, -p.grid_import_limit_kw]
        row += 1
        a[row, [exp[t], grid_mode[t]]] = [1, p.grid_export_limit_kw]
        hi[row] = p.grid_export_limit_kw
        row += 1
        a[row, [imp[t], peak]] = [1, -1]
        row += 1
    result = milp(objective, integrality=integrality, bounds=Bounds(lower, upper),
                  constraints=LinearConstraint(a.tocsr(), lo, hi),
                  options={"time_limit": 10.0, "mip_rel_gap": 1e-7})
    if not result.success or result.x is None:
        raise ValueError("No proven optimal dispatch within limits. Check grid capacity and site demand.")
    x = result.x
    # Solve the no-battery comparator with the same grid/curtailment freedoms.
    # This remains valid for negative import/export prices, unlike a simple net-load baseline.
    baseline_upper = upper.copy()
    baseline_upper[c] = baseline_upper[d] = 0
    base_result = milp(objective, integrality=integrality, bounds=Bounds(lower, baseline_upper),
                       constraints=LinearConstraint(a.tocsr(), lo, hi),
                       options={"time_limit": 10.0, "mip_rel_gap": 1e-7})
    if not base_result.success or base_result.x is None:
        raise ValueError("No feasible no-storage baseline within grid limits; savings comparison is invalid.")
    base_import, base_export = base_result.x[imp], base_result.x[exp]
    base_energy = float(np.dot(base_import, buy)*dt - np.dot(base_export, sell)*dt)
    optimized_energy = float(np.dot(x[imp], buy)*dt - np.dot(x[exp], sell)*dt)
    base_peak = float(np.max(base_import))
    optimized_peak = float(np.max(x[imp]))
    wear_cost = float(np.sum(x[d])*dt*p.wear_eur_per_kwh)
    base_cost = base_energy + base_peak*p.peak_charge_eur_per_kw_period
    opt_cost = optimized_energy + optimized_peak*p.peak_charge_eur_per_kw_period + wear_cost
    schedule = []
    for t in range(n):
        schedule.append({"hour": round(t*dt, 2), "label": f"{int(t*dt):02d}:{int((t*dt%1)*60):02d}",
                         "load_kw": round(float(load[t]), 3), "pv_kw": round(float(pv[t]), 3),
                         "charge_kw": round(float(x[c[t]]), 3), "discharge_kw": round(float(x[d[t]]), 3),
                         "grid_import_kw": round(float(x[imp[t]]), 3), "grid_export_kw": round(float(x[exp[t]]), 3),
                         "curtailed_kw": round(float(x[cur[t]]), 3), "soc_start_kwh": round(float(x[soc[t]]), 3),
                         "soc_end_kwh": round(float(x[soc[t+1]]), 3),
                         "soc_pct": round(float(x[soc[t+1]])/p.capacity_kwh*100, 3),
                         "import_eur_mwh": round(float(buy[t])*1000, 2)})
    savings = base_cost-opt_cost
    return {"model": "btm-milp-v1", "data_kind": "synthetic" if is_demo else "user_supplied",
            "market": p.market, "duration_hours": n*dt, "capacity_kwh": p.capacity_kwh,
            "power_kw": p.power_kw, "baseline_cost_eur": round(base_cost, 2),
            "optimized_cost_eur": round(opt_cost, 2), "savings_eur": round(savings, 2),
            "savings_pct": round(savings/base_cost*100, 2) if base_cost > 0 else None,
            "energy_savings_eur": round(base_energy-optimized_energy, 2),
            "peak_savings_eur": round((base_peak-optimized_peak)*p.peak_charge_eur_per_kw_period, 2),
            "wear_cost_eur": round(wear_cost, 2), "baseline_peak_kw": round(base_peak, 3),
            "optimized_peak_kw": round(optimized_peak, 3),
            "discharged_kwh": round(float(np.sum(x[d]))*dt, 3),
            "equivalent_discharge_cycles": round(float(np.sum(x[d]))*dt/p.capacity_kwh, 4),
            "terminal_soc_kwh": round(float(x[soc[-1]]), 3),
            "solver": "SciPy / HiGHS MILP", "solver_status": "optimal", "schedule": schedule,
            "warnings": ["Synthetic daily profile is not an annual revenue forecast." if is_demo else
                         "User time series have not been independently validated.",
                         "Peak tariff applies once to this modeled period, not automatically to a month.",
                         "Perfect foresight; no ancillary services, taxes, fixed fees or availability reserve."]}
