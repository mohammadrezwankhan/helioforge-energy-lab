"""Independent hourly HiGHS reference for three committed HelioForge dispatch scenarios.

Run with scipy installed. The boundary conditions are the committed hourly
load and gross source availability. No production dispatch functions are imported.
"""

import argparse
import json
import math
import sys
from pathlib import Path
from scipy.optimize import linprog

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path, help="JSON output path for reference results")
args = parser.parse_args()
examples = Path(__file__).resolve().parents[1] / "examples"
catalog = json.loads((examples / "hybrid-catalog.json").read_text())
cases = json.loads((examples / "hybrid-bundle.json").read_text())["cases"]
chosen = ["remote-triad/baseline", "hospital-island/outage-24h", "utility-pv-ac/outage-4h"]
results = []
for suffix in chosen:
    case = next(x for x in cases if x["id"].endswith("/" + suffix))
    cfg = case["inputs"]
    topology = next(v["topology"] for v in catalog["systems"] if v["id"] == cfg["system_id"])
    mod = next(v["modifiers"] for v in catalog["scenarios"] if v["id"] == cfg["scenario_id"])
    cap = cfg["battery_kwh"] * mod.get("capacity_factor", 1)
    power = cfg["battery_kw"] * mod.get("battery_factor", 1)
    eta = math.sqrt(cfg["round_trip_efficiency"])
    soc = cfg["initial_soc"] * cap
    low = max(cfg["min_soc"], mod.get("reserve_floor", 0)) * cap
    high = cfg["max_soc"] * cap
    evidence = []
    for row in case["result"]["schedule"]:
        h = row["hour"]
        first = mod.get("outage_start", -1)
        outage = first <= h < first + mod.get("outage_hours", 0)
        grid = topology != "Off-grid" and not outage
        island = (
            topology in ("Off-grid", "Islandable")
            and cfg["control"] in ("Dual", "GFM")
            and power > 0
            and cap > 0
        )
        target = row["load_kw"] * (cfg["critical_fraction"] if outage else 1)
        availability = sum(row[x] for x in ("hydro_kw", "pv_kw", "wind_kw"))
        surplus = availability >= target
        # Mutually exclusive supply/demand branches. One equality enforces AC bus balance.
        energized = grid or island
        bounds = [
            (0, target if energized else 0),
            (0, min(power, max(0, (high - soc) / eta)) if surplus and energized else 0),
            (0, min(power, max(0, (soc - low) * eta)) if not surplus and energized else 0),
            (0, cfg["grid_import_kw"] * mod.get("import_factor", 1) if grid and not surplus else 0),
            (
                0,
                cfg["grid_export_kw"] * mod.get("export_factor", 1)
                if grid and surplus and cfg["export_eur_kwh"] >= 0
                else 0,
            ),
            (0, cfg["generator_kw"] * mod.get("generator_factor", 1) if energized and not surplus else 0),
            (0, availability),
        ]
        opt = linprog(
            [-100, -3, 1, 2, -1, 3, 0],
            A_eq=[[1, 1, -1, -1, 1, -1, 1]],
            b_eq=[availability],
            bounds=bounds,
            method="highs",
        )
        if not opt.success:
            raise RuntimeError(opt.message)
        served, charge, discharge, imp, exp, gen, spill = map(float, opt.x)
        soc += charge * eta - discharge / eta
        cost = imp * row["import_eur_kwh"] - exp * cfg["export_eur_kwh"] + gen * cfg["generator_eur_kwh"]
        ref = dict(
            served_kw=served,
            charge_kw=charge,
            discharge_kw=discharge,
            grid_import_kw=imp,
            grid_export_kw=exp,
            generator_kw=gen,
            curtailed_kw=spill,
            soc_end_kwh=soc,
            variable_cost_eur=cost,
            critical_unserved_kw=max(0, row["load_kw"] * cfg["critical_fraction"] - served),
        )
        errors = {k: abs(row[k] - v) for k, v in ref.items()}
        evidence.append(
            dict(
                hour=h,
                reference=ref,
                absolute_errors=errors,
                bus_residual=availability + discharge + imp + gen - served - charge - exp - spill,
            )
        )
    worst = max(max(i["absolute_errors"].values()) for i in evidence)
    results.append(
        dict(id=case["id"], inputs=cfg, max_absolute_error=worst, passed=worst <= 1e-8, intervals=evidence)
    )
args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print([(x["id"], len(x["intervals"]), x["max_absolute_error"], x["passed"]) for x in results])

if not all(case_result["passed"] for case_result in results):
    sys.exit("Reference comparison exceeded 1e-8 in the reported physical units")
