"""Portable worked examples: run from repository root with API dependencies installed.

PYTHONPATH=apps/api python docs/examples/worked_labs.py OUTPUT_DIRECTORY
No network, persistence store, provider or browser operations are invoked.
"""

import importlib.metadata
import json
import math
import sys
from pathlib import Path

from helioforge.engines.finance import calculate_finance, calculate_pv
from helioforge.engines.hybrid import simulate_hybrid
from helioforge.engines.storage import optimize_storage
from helioforge.engines.terminal import terminal_defaults, terminal_diff, terminal_solve
from helioforge.hybrid import HybridRequest
from helioforge.schemas import FinanceRequest, PVRequest, StorageRequest
from helioforge.studies import StudyRequest, catalogue, evaluate

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def save(name, value):
    (output / (name + ".json")).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


storage_inputs = {
    "capacity_kwh": 2,
    "power_kw": 1,
    "round_trip_efficiency": 1,
    "min_soc_fraction": 0,
    "max_soc_fraction": 1,
    "initial_soc_fraction": 0.5,
    "wear_eur_per_kwh": 0,
    "grid_import_limit_kw": 10,
    "grid_export_limit_kw": 10,
    "load_kw": [1, 1],
    "pv_kw": [0, 0],
    "import_eur_per_kwh": [0.1, 0.3],
    "export_eur_per_kwh": [0, 0],
}
storage = optimize_storage(StorageRequest(**storage_inputs))
require(
    math.isclose(storage["baseline_cost_eur"], 0.4, abs_tol=1e-09),
    "Storage baseline cost differs from 0.4 EUR.",
)
require(
    math.isclose(storage["optimized_cost_eur"], 0.2, abs_tol=1e-09),
    "Storage optimized cost differs from 0.2 EUR.",
)
require(
    math.isclose(storage["terminal_soc_kwh"], 1, abs_tol=1e-09), "Storage terminal SOC differs from 1 kWh."
)
save("storage-two-interval", {"inputs": storage_inputs, "result": storage})
reference = terminal_solve(terminal_defaults())
island_inputs = {**terminal_defaults(), "gridKw": 0.0}
island = terminal_solve(island_inputs)
for run in (reference, island):
    require(len(run["rows"]) == 24, "Terminal run must contain 24 rows.")
    require(run["metrics"]["maxBusResidualKw"] < 1e-10, "Terminal bus residual exceeds the example limit.")
    require(run["metrics"]["maxSocResidualKwh"] < 1e-10, "Terminal SOC residual exceeds the example limit.")
save(
    "terminal-reference-and-island",
    {"reference": reference, "island": island, "difference": terminal_diff(reference, island)},
)
finance_inputs = {
    "capex_eur": 100,
    "annual_gross_margin_eur": 60,
    "annual_opex_eur": 0,
    "years": 2,
    "discount_rate": 0,
    "annual_margin_degradation": 0,
    "escalation_rate": 0,
    "debt_fraction": 0,
    "debt_tenor_years": 2,
    "augmentation_year": None,
    "augmentation_cost_eur": 0,
    "contracted_fraction": 1,
    "contract_years": 2,
}
finance = calculate_finance(FinanceRequest(**finance_inputs))
require(finance["npv_eur"] == 20, "Debt-free finance NPV differs from 20 EUR.")
require(
    finance["minimum_dscr"] is None and finance["covenant_pass"] is None,
    "Debt-free finance must have null DSCR and covenant status.",
)
save("finance-debt-free", {"inputs": finance_inputs, "result": finance})
pv = calculate_pv(PVRequest())
save("pv-default", {"inputs": PVRequest().model_dump(), "result": pv})
hybrid_inputs = HybridRequest()
hybrid = simulate_hybrid(hybrid_inputs)
require(abs(hybrid["max_balance_residual_kw"]) < 1e-07, "Hybrid balance residual exceeds the example limit.")
save("hybrid-default", {"inputs": hybrid_inputs.model_dump(), "result": hybrid})
control = evaluate(StudyRequest(study="hybrid-controls"))
save("hybrid-controls-default", control)
save("study-catalogue", catalogue())
summary = {
    "versions": {k: importlib.metadata.version(k) for k in ["numpy", "scipy", "pydantic"]},
    "storage": {
        k: storage[k]
        for k in [
            "duration_hours",
            "baseline_cost_eur",
            "optimized_cost_eur",
            "savings_eur",
            "terminal_soc_kwh",
        ]
    },
    "terminal": {"reference": reference["metrics"], "island": island["metrics"]},
    "finance": {k: finance[k] for k in ["npv_eur", "irr_pct", "minimum_dscr", "covenant_pass"]},
    "pv": {
        k: pv[k]
        for k in [
            "capex_eur",
            "lcoe_eur_mwh",
            "first_year_generation_mwh",
            "panel_count",
            "indicative_land_ha",
        ]
    },
    "hybrid": {
        k: hybrid[k]
        for k in [
            "duration_hours",
            "total_load_kwh",
            "served_kwh",
            "unserved_kwh",
            "initial_energy_kwh",
            "terminal_energy_kwh",
            "variable_cost_eur",
            "max_balance_residual_kw",
        ]
    },
    "controls": {"metrics": control["metrics"], "warnings": control["warnings"]},
    "scope": (
        "Direct native Python functions with declared pins, not HTTP/browser/provider/field validation; "
        "numerical examples use synthetic assumptions."
    ),
}
save("summary", summary)
sys.stdout.write(json.dumps(summary, indent=2, allow_nan=False) + "\n")
