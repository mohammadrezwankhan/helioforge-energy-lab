"""Deterministic synthetic 24-hour greedy PV/battery/grid adequacy screen.

This is a fixed dispatch policy, not cost optimization, a forecast, or a calibrated
plant model. It is intentionally independent of the retained hybrid and storage
engines. See ``docs/terminal-audit/ANALYTICAL_MODEL.md`` for equations and limits.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Literal

MODEL_VERSION = "terminal-greedy-hourly-v1"
STEPS = 24
TOLERANCE = 1e-9
MAX_SWEEP_POINTS = 441

INPUT_BOUNDS: dict[str, tuple[float, float, bool]] = {
    "pvKw": (0.0, 100_000.0, False),
    "batteryKwh": (0.0, 500_000.0, False),
    "batteryKw": (0.0, 100_000.0, False),
    "loadKw": (0.0, 100_000.0, False),
    "gridKw": (0.0, 100_000.0, False),
    "roundtripEfficiency": (0.0, 1.0, True),
    "initialSocFraction": (0.0, 1.0, False),
    "minSocFraction": (0.0, 1.0, False),
    "maxSocFraction": (0.0, 1.0, False),
    "importPrice": (-10.0, 10.0, False),
    "exportPrice": (-10.0, 10.0, False),
}
INPUT_KEYS = tuple(INPUT_BOUNDS)
WARNINGS = [
    "PV and load use deterministic synthetic 24-hour shapes; they are not measured weather or demand data.",
    "Dispatch is greedy: PV serves load, renewable surplus charges storage, storage serves remaining load before grid import, then remaining load is unserved. It is not cost optimization.",
    "Surplus is exported only when exportPrice is nonnegative and grid capacity is available; remaining surplus is curtailed.",
    "Charging and discharging each use the square root of roundtripEfficiency. Terminal SOC is unconstrained; initial-to-final stored-energy change is reported explicitly.",
    "periodCost covers this 24-hour synthetic period only. It excludes fixed costs, degradation, demand charges, taxes, finance, and annualization.",
    "No thermal, frequency, voltage, protection, dynamic-control, or field-calibration model is included.",
]


class TerminalModelError(ValueError):
    """Bounded input or sweep error with a stable machine-readable code."""

    def __init__(self, message: str, code: Literal["ERR_BOUND", "ERR_VALIDATION"]):
        super().__init__(message)
        self.code = code


def terminal_defaults() -> dict[str, float]:
    """Return a new copy of the explicit synthetic teaching scenario defaults."""
    return {
        "pvKw": 8.0,
        "batteryKwh": 20.0,
        "batteryKw": 5.0,
        "loadKw": 6.0,
        "gridKw": 10.0,
        "roundtripEfficiency": 0.9,
        "initialSocFraction": 0.5,
        "minSocFraction": 0.1,
        "maxSocFraction": 0.9,
        "importPrice": 0.25,
        "exportPrice": 0.05,
    }


def terminal_validate_inputs(value: object) -> dict[str, float]:
    """Validate all finite values and cross-field constraints; never clamp input."""
    if not isinstance(value, Mapping):
        raise TerminalModelError("Inputs must be an object with exactly the documented fields.", "ERR_VALIDATION")
    actual_keys = set(value)
    unknown = sorted(str(key) for key in actual_keys - set(INPUT_KEYS))
    missing = sorted(set(INPUT_KEYS) - actual_keys)
    if unknown or missing:
        parts = []
        if missing:
            parts.append(f"missing fields: {', '.join(missing)}")
        if unknown:
            parts.append(f"unknown fields: {', '.join(unknown)}")
        raise TerminalModelError(f"Inputs have {'; '.join(parts)}.", "ERR_VALIDATION")
    result: dict[str, float] = {}
    for key in INPUT_KEYS:
        number = value[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise TerminalModelError(f"{key} must be a finite number.", "ERR_VALIDATION")
        try:
            finite_number = float(number)
        except (OverflowError, ValueError):
            finite_number = math.inf
        if not math.isfinite(finite_number):
            raise TerminalModelError(f"{key} must be a finite number.", "ERR_VALIDATION")
        low, high, minimum_exclusive = INPUT_BOUNDS[key]
        if (minimum_exclusive and finite_number <= low) or finite_number < low or finite_number > high:
            lower = f"greater than {low}" if minimum_exclusive else f"at least {low}"
            raise TerminalModelError(f"{key} must be {lower} and at most {high}; received {finite_number}.", "ERR_BOUND")
        result[key] = finite_number
    if result["minSocFraction"] > result["maxSocFraction"]:
        raise TerminalModelError("minSocFraction must be less than or equal to maxSocFraction.", "ERR_VALIDATION")
    if not result["minSocFraction"] <= result["initialSocFraction"] <= result["maxSocFraction"]:
        raise TerminalModelError(
            "initialSocFraction must be within the inclusive minSocFraction to maxSocFraction range.",
            "ERR_VALIDATION",
        )
    if (result["batteryKwh"] == 0.0) != (result["batteryKw"] == 0.0):
        raise TerminalModelError(
            "batteryKwh and batteryKw must either both be zero or both be greater than zero.",
            "ERR_VALIDATION",
        )
    return result


def _synthetic_load(inputs: Mapping[str, float], hour: int) -> float:
    shape = 0.8 + 0.2 * (0.5 + 0.5 * math.cos((hour - 19) * 2 * math.pi / 24))
    return inputs["loadKw"] * shape


def _synthetic_pv(inputs: Mapping[str, float], hour: int) -> float:
    if hour <= 6 or hour >= 18:
        return 0.0
    return inputs["pvKw"] * max(0.0, math.sin(math.pi * (hour - 6) / 12))


def _explain_number(value: float) -> str:
    return format(value, ".12g")


def _operating_flags(
    inputs: Mapping[str, float], rows: list[dict[str, float]], metrics: Mapping[str, float]
) -> list[dict[str, Any]]:
    resource_bound = inputs["pvKw"] > 0
    unserved = metrics["unservedKwh"] > TOLERANCE
    limits: list[str] = []
    if inputs["batteryKw"] > 0:
        if any(
            row["chargeKw"] >= inputs["batteryKw"] - TOLERANCE
            or row["dischargeKw"] >= inputs["batteryKw"] - TOLERANCE
            for row in rows
        ):
            limits.append(f"battery power reached the configured {inputs['batteryKw']} kW limit")
        minimum = inputs["batteryKwh"] * inputs["minSocFraction"]
        maximum = inputs["batteryKwh"] * inputs["maxSocFraction"]
        if any(row["socKwh"] <= minimum + TOLERANCE or row["socKwh"] >= maximum - TOLERANCE for row in rows):
            limits.append("stored energy reached an SOC boundary")
    drift = metrics["terminalSocDeltaKwh"]
    return [
        {
            "key": "resource-bound",
            "active": resource_bound,
            "explanation": (
                f"The synthetic PV profile reaches the configured {inputs['pvKw']} kW nameplate at hour 12; "
                "this is an input ceiling, not an optimized or measured capacity."
                if resource_bound else "PV capacity is zero, so no PV resource is available in this scenario."
            ),
        },
        {
            "key": "unserved-demand",
            "active": unserved,
            "explanation": (
                f"{_explain_number(metrics['unservedKwh'])} kWh of demand is unserved over the 24-hour synthetic period."
                if unserved else "All modeled demand is served over the 24-hour synthetic period."
            ),
        },
        {
            "key": "soc-or-power-limit",
            "active": bool(limits),
            "explanation": (
                f"Storage limit observed: {'; '.join(limits)}."
                if limits else "No configured battery power or SOC boundary was reached during dispatch."
            ),
        },
        {
            "key": "energy-drift",
            "active": abs(drift) > TOLERANCE,
            "explanation": (
                f"Terminal stored energy changed by {'+' if drift >= 0 else ''}{_explain_number(drift)} kWh from its initial value; "
                "terminal SOC is unconstrained."
                if abs(drift) > TOLERANCE else
                "Terminal stored energy matches its initial value within the 1e-9 kWh reporting tolerance."
            ),
        },
    ]


def terminal_solve(raw_inputs: object) -> dict[str, Any]:
    """Run 24 explicit hourly recurrences using the fixed greedy dispatch order."""
    inputs = terminal_validate_inputs(raw_inputs)
    eta = math.sqrt(inputs["roundtripEfficiency"])
    initial_soc = inputs["batteryKwh"] * inputs["initialSocFraction"]
    min_soc = inputs["batteryKwh"] * inputs["minSocFraction"]
    max_soc = inputs["batteryKwh"] * inputs["maxSocFraction"]
    soc = initial_soc
    rows: list[dict[str, float]] = []
    for hour in range(STEPS):
        load = _synthetic_load(inputs, hour)
        pv = _synthetic_pv(inputs, hour)
        direct_pv = min(pv, load)
        surplus = max(0.0, pv - direct_pv)
        remaining_load = max(0.0, load - direct_pv)
        soc_before = soc
        charge = min(surplus, inputs["batteryKw"], max(0.0, max_soc - soc) / eta)
        soc += charge * eta
        surplus -= charge
        discharge = min(remaining_load, inputs["batteryKw"], max(0.0, soc - min_soc) * eta)
        soc -= discharge / eta
        remaining_load -= discharge
        grid_import = min(remaining_load, inputs["gridKw"])
        remaining_load -= grid_import
        unserved = remaining_load
        grid_export = min(surplus, inputs["gridKw"]) if inputs["exportPrice"] >= 0 else 0.0
        curtailment = surplus - grid_export
        bus_residual = pv + grid_import + discharge + unserved - load - charge - grid_export - curtailment
        soc_residual = soc - (soc_before + charge * eta - discharge / eta)
        rows.append({
            "hour": hour, "loadKw": load, "pvKw": pv,
            "chargeKw": charge, "dischargeKw": discharge,
            "gridImportKw": grid_import, "gridExportKw": grid_export,
            "curtailmentKw": curtailment, "unservedKw": unserved,
            "socKwh": soc, "busResidualKw": bus_residual, "socResidualKwh": soc_residual,
        })
    total_load = sum(row["loadKw"] for row in rows)
    unserved_kwh = sum(row["unservedKw"] for row in rows)
    served_kwh = total_load - unserved_kwh
    metrics = {
        "periodCost": sum(
            row["gridImportKw"] * inputs["importPrice"] - row["gridExportKw"] * inputs["exportPrice"]
            for row in rows
        ),
        "unservedKwh": unserved_kwh,
        "renewableKwh": sum(row["pvKw"] for row in rows),
        "curtailmentKwh": sum(row["curtailmentKw"] for row in rows),
        "peakImportKw": max(row["gridImportKw"] for row in rows),
        "finalSocKwh": soc,
        "initialSocKwh": initial_soc,
        "terminalSocDeltaKwh": soc - initial_soc,
        "maxBusResidualKw": max(abs(row["busResidualKw"]) for row in rows),
        "maxSocResidualKwh": max(abs(row["socResidualKwh"]) for row in rows),
        "servedFraction": 1.0 if total_load == 0 else served_kwh / total_load,
        "totalLoadKwh": total_load,
        "servedKwh": served_kwh,
    }
    return {
        "modelVersion": MODEL_VERSION,
        "dataKind": "synthetic-deterministic",
        "status": "CONVERGED",
        "steps": STEPS,
        "iterations": None,
        "inputs": inputs,
        "rows": rows,
        "metrics": metrics,
        "flags": _operating_flags(inputs, rows, metrics),
        "warnings": list(WARNINGS),
    }


def _axis_values(
    parameter: str, lower: float, upper: float, steps: int, scale: str
) -> list[float]:
    if parameter not in INPUT_BOUNDS:
        raise TerminalModelError(f"Unknown sweep parameter: {parameter}.", "ERR_VALIDATION")
    if isinstance(lower, bool) or not isinstance(lower, (int, float)):
        raise TerminalModelError("Sweep lower and upper bounds must be finite numbers.", "ERR_VALIDATION")
    if isinstance(upper, bool) or not isinstance(upper, (int, float)):
        raise TerminalModelError("Sweep lower and upper bounds must be finite numbers.", "ERR_VALIDATION")
    try:
        lower = float(lower)
        upper = float(upper)
    except (OverflowError, ValueError):
        raise TerminalModelError("Sweep lower and upper bounds must be finite numbers.", "ERR_VALIDATION") from None
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise TerminalModelError("Sweep lower and upper bounds must be finite numbers.", "ERR_VALIDATION")
    if lower >= upper:
        raise TerminalModelError("Sweep lower bound must be less than upper bound.", "ERR_VALIDATION")
    if isinstance(steps, bool) or not isinstance(steps, int) or not 2 <= steps <= 21:
        raise TerminalModelError("Sweep steps must be an integer from 2 through 21.", "ERR_BOUND")
    if scale not in {"linear", "log"}:
        raise TerminalModelError("Sweep scale must be linear or log.", "ERR_VALIDATION")
    minimum, maximum, min_exclusive = INPUT_BOUNDS[parameter]
    if (min_exclusive and lower <= minimum) or lower < minimum or upper > maximum:
        phrase = "greater than" if min_exclusive else "at least"
        raise TerminalModelError(
            f"{parameter} sweep bounds must stay within {phrase} {minimum} and at most {maximum}.", "ERR_BOUND"
        )
    if scale == "log" and lower <= 0:
        raise TerminalModelError("Log sweeps require positive lower and upper bounds.", "ERR_BOUND")
    values = []
    for index in range(steps):
        fraction = index / (steps - 1)
        if scale == "linear":
            values.append(float(lower + (upper - lower) * fraction))
        else:
            values.append(math.exp(math.log(lower) + (math.log(upper) - math.log(lower)) * fraction))
    values[0], values[-1] = float(lower), float(upper)
    return values


def _same_service(a: Mapping[str, float], b: Mapping[str, float]) -> bool:
    same_load = abs(a["totalLoadKwh"] - b["totalLoadKwh"]) <= TOLERANCE * max(
        1.0, abs(a["totalLoadKwh"]), abs(b["totalLoadKwh"])
    )
    same_served = abs(a["servedKwh"] - b["servedKwh"]) <= TOLERANCE * max(
        1.0, abs(a["servedKwh"]), abs(b["servedKwh"])
    )
    return same_load and same_served


def _error_status(error: Exception) -> str:
    return error.code if isinstance(error, TerminalModelError) else "ERR_VALIDATION"


def terminal_sweep(
    raw_inputs: object,
    parameter: str,
    lower: float,
    upper: float,
    steps: int,
    scale: Literal["linear", "log"],
    second: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a bounded one- or two-parameter cartesian sweep."""
    inputs = terminal_validate_inputs(raw_inputs)
    axes = [{"parameter": parameter, "values": _axis_values(parameter, lower, upper, steps, scale), "scale": scale}]
    if second is not None:
        second_parameter = second.get("parameter")
        if second_parameter == parameter:
            raise TerminalModelError("A two-axis sweep must use two different parameters.", "ERR_VALIDATION")
        axes.append({
            "parameter": second_parameter,
            "values": _axis_values(
                second_parameter, second.get("lower"), second.get("upper"),
                second.get("steps"), second.get("scale"),
            ),
            "scale": second.get("scale"),
        })
    point_count = math.prod(len(axis["values"]) for axis in axes)
    if point_count > MAX_SWEEP_POINTS:
        raise TerminalModelError(f"Sweep matrix cannot exceed {MAX_SWEEP_POINTS} points.", "ERR_BOUND")
    points: list[dict[str, Any]] = []
    outer_values = axes[1]["values"] if len(axes) == 2 else [None]
    for outer in outer_values:
        for inner in axes[0]["values"]:
            coordinates: dict[str, float] = {parameter: inner}
            if len(axes) == 2:
                coordinates[axes[1]["parameter"]] = outer
            index = len(points)
            try:
                run = terminal_solve({**inputs, **coordinates})
                points.append({
                    "index": index, "coordinates": coordinates,
                    "status": "CONVERGED", "error": None, "metrics": run["metrics"],
                })
            except (TerminalModelError, ValueError, TypeError) as error:
                points.append({
                    "index": index, "coordinates": coordinates,
                    "status": _error_status(error), "error": str(error), "metrics": None,
                })
    valid = [point for point in points if point["metrics"] is not None]
    ranked = sorted(valid, key=lambda point: (
        point["metrics"]["unservedKwh"], point["metrics"]["periodCost"],
        abs(point["metrics"]["terminalSocDeltaKwh"]), point["index"],
    ))
    pareto = []
    for candidate in valid:
        value = candidate["metrics"]
        dominated = any(
            other["index"] != candidate["index"]
            and _same_service(value, other["metrics"])
            and other["metrics"]["periodCost"] <= value["periodCost"] + TOLERANCE
            and other["metrics"]["unservedKwh"] <= value["unservedKwh"] + TOLERANCE
            and (
                other["metrics"]["periodCost"] < value["periodCost"] - TOLERANCE
                or other["metrics"]["unservedKwh"] < value["unservedKwh"] - TOLERANCE
            )
            for other in valid
        )
        if not dominated:
            pareto.append(candidate["index"])
    return {
        "modelVersion": MODEL_VERSION,
        "axes": axes,
        "points": points,
        "rankedPointIndices": [point["index"] for point in ranked],
        "paretoPointIndices": pareto,
        "warnings": [
            "Sweep ranking sorts by unserved energy, then period cost, then absolute terminal SOC change; it is not an optimization result.",
            "This is a conditional sampled service-equivalent frontier: Pareto dominance compares only points with matching totalLoadKwh and servedKwh, minimizing period cost and unserved kWh; it is not a global optimum.",
            "Initial and terminal SOC are not constrained to match. Endpoint energy changes can bias cost comparisons, so inspect terminal SOC deltas before interpreting the sampled frontier.",
            *WARNINGS,
        ],
    }


def terminal_sensitivity(raw_inputs: object) -> dict[str, Any]:
    """Calculate one-at-a-time finite-difference elasticities (not Sobol indices)."""
    inputs = terminal_validate_inputs(raw_inputs)
    baseline = terminal_solve(inputs)
    output_rows = []
    for parameter in INPUT_KEYS:
        base_value = inputs[parameter]
        minimum, maximum, _ = INPUT_BOUNDS[parameter]
        step = max(abs(base_value) * 1e-3, (maximum - minimum) * 1e-8)
        plus_value, minus_value = base_value + step, base_value - step
        plus = minus = None
        plus_error = minus_error = None
        try:
            plus = terminal_solve({**inputs, parameter: plus_value})
        except (TerminalModelError, ValueError, TypeError) as error:
            plus_error = str(error)
        try:
            minus = terminal_solve({**inputs, parameter: minus_value})
        except (TerminalModelError, ValueError, TypeError) as error:
            minus_error = str(error)
        method = "central" if plus is not None and minus is not None else (
            "forward" if plus is not None else "backward" if minus is not None else "unavailable"
        )

        def elasticity(metric: str) -> float | None:
            base_metric = baseline["metrics"][metric]
            if base_value == 0 or base_metric == 0 or method == "unavailable":
                return None
            if method == "central":
                derivative = (plus["metrics"][metric] - minus["metrics"][metric]) / (plus_value - minus_value)
            elif method == "forward":
                derivative = (plus["metrics"][metric] - base_metric) / (plus_value - base_value)
            else:
                derivative = (base_metric - minus["metrics"][metric]) / (base_value - minus_value)
            return derivative * base_value / base_metric

        output_rows.append({
            "parameter": parameter,
            "baseValue": base_value,
            "step": step,
            "method": method,
            "periodCostElasticity": elasticity("periodCost"),
            "unservedKwhElasticity": elasticity("unservedKwh"),
            "error": (
                f"Both perturbations failed. Increase/decrease errors: {minus_error or 'none'}; {plus_error or 'none'}"
                if method == "unavailable" else None
            ),
        })
    return {
        "modelVersion": MODEL_VERSION,
        "baseline": baseline,
        "rows": output_rows,
        "warnings": [
            "This is a one-at-a-time finite-difference elasticity screen, not Sobol analysis or probabilistic sensitivity.",
            "The perturbation is 0.1% of the current value, with a 1e-8 parameter-range floor; a valid one-sided difference is used at input boundaries.",
            "Elasticity is null when its baseline metric or input is zero, or when neither perturbation is valid.",
            *WARNINGS,
        ],
    }


def terminal_diff(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    """Return absolute and baseline-relative changes for numerical run metrics."""
    metric_names = (
        "periodCost", "unservedKwh", "renewableKwh", "curtailmentKwh", "peakImportKw",
        "finalSocKwh", "initialSocKwh", "terminalSocDeltaKwh", "maxBusResidualKw",
        "maxSocResidualKwh", "servedFraction", "totalLoadKwh", "servedKwh",
    )
    rows = []
    for metric in metric_names:
        left, right = a["metrics"][metric], b["metrics"][metric]
        delta = right - left
        rows.append({
            "metric": metric, "a": left, "b": right, "deltaAbsolute": delta,
            "deltaPercent": None if left == 0 else 100 * delta / abs(left),
        })
    b_flags = {flag["key"]: flag for flag in b.get("flags", [])}
    regime_shifts = [
        f"Regime shift for {flag_a['key']}: run a was {'active' if flag_a['active'] else 'inactive'} "
        f"({flag_a['explanation']}); run b was {'active' if flag_b['active'] else 'inactive'} "
        f"({flag_b['explanation']})."
        for flag_a in a.get("flags", [])
        if (flag_b := b_flags.get(flag_a["key"])) is not None and flag_a["active"] != flag_b["active"]
    ]
    return {
        "modelVersion": MODEL_VERSION,
        "rows": rows,
        "warnings": [
            "Diff percentage is relative to the absolute value of run a; it is null when the baseline metric is zero.",
            "Runs can differ in unserved demand and terminal battery energy; neither cost nor SOC endpoints are neutralized.",
            *regime_shifts,
            *WARNINGS,
        ],
    }
