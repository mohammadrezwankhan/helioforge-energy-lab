"""Reference arithmetic and boundary tests for the independent terminal screen."""
from __future__ import annotations

import math

import pytest

from helioforge.engines.terminal import (
    TerminalModelError,
    terminal_defaults,
    terminal_diff,
    terminal_sensitivity,
    terminal_solve,
    terminal_sweep,
    terminal_validate_inputs,
)


def inputs(**changes):
    return {**terminal_defaults(), **changes}


# Fixed cross-runtime reference summaries. Every hourly row is also checked against
# the analytical recurrence below, with 1e-10 absolute tolerance.
PARITY_FIXTURES = [
    ("default", {}, {
        "periodCost": 15.606424009489949, "unservedKwh": 0.0, "renewableKwh": 60.7660329018012,
        "curtailmentKwh": 0.0, "peakImportKw": 6.0, "finalSocKwh": 2.0, "initialSocKwh": 10.0,
        "terminalSocDeltaKwh": -8.0, "maxBusResidualKw": 0.0, "maxSocResidualKwh": 0.0,
        "servedFraction": 1.0, "totalLoadKwh": 129.6, "servedKwh": 129.6,
    }),
    ("island_no_grid", {"gridKw": 0}, {
        "periodCost": 0.0, "unservedKwh": 62.425696037959796, "renewableKwh": 60.7660329018012,
        "curtailmentKwh": 0.0, "peakImportKw": 0.0, "finalSocKwh": 2.0, "initialSocKwh": 10.0,
        "terminalSocDeltaKwh": -8.0, "maxBusResidualKw": 0.0, "maxSocResidualKwh": 0.0,
        "servedFraction": 0.5183202466206805, "totalLoadKwh": 129.6, "servedKwh": 67.1743039620402,
    }),
    ("negative_export", {
        "pvKw": 20, "batteryKwh": 0, "batteryKw": 0, "loadKw": 0, "gridKw": 100,
        "importPrice": 0.2, "exportPrice": -0.1,
    }, {
        "periodCost": 0.0, "unservedKwh": 0.0, "renewableKwh": 151.915082254503,
        "curtailmentKwh": 151.915082254503, "peakImportKw": 0.0, "finalSocKwh": 0.0,
        "initialSocKwh": 0.0, "terminalSocDeltaKwh": 0.0, "maxBusResidualKw": 0.0,
        "maxSocResidualKwh": 0.0, "servedFraction": 1.0, "totalLoadKwh": 0.0, "servedKwh": 0.0,
    }),
    ("zero_load", {"pvKw": 0, "batteryKwh": 0, "batteryKw": 0, "loadKw": 0, "gridKw": 0}, {
        "periodCost": 0.0, "unservedKwh": 0.0, "renewableKwh": 0.0, "curtailmentKwh": 0.0,
        "peakImportKw": 0.0, "finalSocKwh": 0.0, "initialSocKwh": 0.0, "terminalSocDeltaKwh": 0.0,
        "maxBusResidualKw": 0.0, "maxSocResidualKwh": 0.0, "servedFraction": 1.0,
        "totalLoadKwh": 0.0, "servedKwh": 0.0,
    }),
    ("efficiency_one", {
        "pvKw": 20, "batteryKwh": 40, "batteryKw": 10, "loadKw": 5, "gridKw": 0,
        "roundtripEfficiency": 1, "initialSocFraction": 0, "minSocFraction": 0, "maxSocFraction": 1,
    }, {
        "periodCost": 0.0, "unservedKwh": 29.980470994369973, "renewableKwh": 151.915082254503,
        "curtailmentKwh": 63.39804516764754, "peakImportKw": 0.0, "finalSocKwh": 10.49750808122544,
        "initialSocKwh": 0.0, "terminalSocDeltaKwh": 10.49750808122544, "maxBusResidualKw": 0.0,
        "maxSocResidualKwh": 0.0, "servedFraction": 0.7224030463484262,
        "totalLoadKwh": 108.0, "servedKwh": 78.01952900563003,
    }),
]


def reference_rows(p):
    """Independently evaluate every row from the stated profile and dispatch equations."""
    eta = math.sqrt(p["roundtripEfficiency"])
    minimum, maximum = p["batteryKwh"] * p["minSocFraction"], p["batteryKwh"] * p["maxSocFraction"]
    soc = p["batteryKwh"] * p["initialSocFraction"]
    expected = []
    for hour in range(24):
        load_shape = 0.8 + 0.2 * (0.5 + 0.5 * math.cos((hour - 19) * 2 * math.pi / 24))
        load = p["loadKw"] * load_shape
        pv = 0 if hour <= 6 or hour >= 18 else p["pvKw"] * max(0, math.sin(math.pi * (hour - 6) / 12))
        direct = min(pv, load)
        surplus, deficit = max(0, pv - direct), max(0, load - direct)
        before = soc
        charge = min(surplus, p["batteryKw"], max(0, maximum - soc) / eta)
        soc += charge * eta
        surplus -= charge
        discharge = min(deficit, p["batteryKw"], max(0, soc - minimum) * eta)
        soc -= discharge / eta
        deficit -= discharge
        imported = min(deficit, p["gridKw"])
        unserved = deficit - imported
        exported = min(surplus, p["gridKw"]) if p["exportPrice"] >= 0 else 0
        curtailment = surplus - exported
        expected.append({
            "hour": hour, "loadKw": load, "pvKw": pv, "chargeKw": charge, "dischargeKw": discharge,
            "gridImportKw": imported, "gridExportKw": exported, "curtailmentKw": curtailment,
            "unservedKw": unserved, "socKwh": soc,
            "busResidualKw": pv + imported + discharge + unserved - load - charge - exported - curtailment,
            "socResidualKwh": soc - (before + charge * eta - discharge / eta),
        })
    return expected


@pytest.mark.parametrize("name,changes,expected_metrics", PARITY_FIXTURES, ids=[fixture[0] for fixture in PARITY_FIXTURES])
def test_fixed_cross_runtime_fixtures_match_all_metrics_and_hourly_rows(name, changes, expected_metrics):
    result = terminal_solve(inputs(**changes))
    for metric, expected in expected_metrics.items():
        assert result["metrics"][metric] == pytest.approx(expected, abs=1e-10, rel=0), (name, metric)
    expected_rows = reference_rows(result["inputs"])
    assert len(result["rows"]) == len(expected_rows) == 24
    for actual, expected in zip(result["rows"], expected_rows, strict=True):
        for key, value in expected.items():
            assert actual[key] == pytest.approx(value, abs=1e-10, rel=0), (name, actual["hour"], key)


def test_default_run_has_24_explicit_rows_and_balanced_recurrences():
    result = terminal_solve(terminal_defaults())
    assert result["modelVersion"] == "terminal-greedy-hourly-v1"
    assert result["dataKind"] == "synthetic-deterministic"
    assert result["status"] == "CONVERGED"
    assert result["steps"] == 24
    assert result["iterations"] is None
    assert len(result["rows"]) == 24
    previous_soc = result["metrics"]["initialSocKwh"]
    eta = math.sqrt(result["inputs"]["roundtripEfficiency"])
    for hour, row in enumerate(result["rows"]):
        assert row["hour"] == hour
        assert row["busResidualKw"] == pytest.approx(0, abs=1e-9)
        assert row["socKwh"] == pytest.approx(
            previous_soc + row["chargeKw"] * eta - row["dischargeKw"] / eta,
            abs=1e-9,
        )
        assert 0 <= row["socKwh"] <= result["inputs"]["batteryKwh"]
        assert min(row[key] for key in (
            "chargeKw", "dischargeKw", "gridImportKw", "gridExportKw", "curtailmentKw", "unservedKw"
        )) >= 0
        previous_soc = row["socKwh"]
    assert result["metrics"]["totalLoadKwh"] == pytest.approx(129.6, abs=1e-10)
    assert result["metrics"]["renewableKwh"] == pytest.approx(
        sum(8 * max(0, math.sin(math.pi * (hour - 6) / 12)) for hour in range(24)), abs=1e-10
    )
    assert result["metrics"]["terminalSocDeltaKwh"] == pytest.approx(
        result["metrics"]["finalSocKwh"] - result["metrics"]["initialSocKwh"]
    )
    assert result["metrics"]["maxBusResidualKw"] < 1e-9
    assert result["metrics"]["maxSocResidualKwh"] < 1e-9


def test_zero_battery_grid_only_reference_arithmetic():
    result = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=4))
    assert result["metrics"]["totalLoadKwh"] == pytest.approx(216.0, abs=1e-10)
    assert result["metrics"]["servedKwh"] == pytest.approx(96.0, abs=1e-10)
    assert result["metrics"]["unservedKwh"] == pytest.approx(120.0, abs=1e-10)
    assert result["metrics"]["periodCost"] == pytest.approx(24.0, abs=1e-10)
    assert result["metrics"]["finalSocKwh"] == 0
    assert all(row["gridImportKw"] == 4 for row in result["rows"])
    assert max(row["busResidualKw"] for row in result["rows"]) < 1e-9


def test_charge_and_discharge_use_efficiency_in_opposite_directions():
    result = terminal_solve(inputs(
        pvKw=20, batteryKwh=40, batteryKw=10, loadKw=5, gridKw=0,
        roundtripEfficiency=0.81, initialSocFraction=0, minSocFraction=0, maxSocFraction=1,
    ))
    eta = 0.9
    charge = next(row for row in result["rows"] if row["chargeKw"] > 0)
    discharge = next(row for row in result["rows"] if row["dischargeKw"] > 0)
    before_charge = result["metrics"]["initialSocKwh"] if charge["hour"] == 0 else result["rows"][int(charge["hour"]) - 1]["socKwh"]
    assert charge["socKwh"] - before_charge == pytest.approx(charge["chargeKw"] * eta, abs=1e-9)
    before_discharge = result["rows"][int(discharge["hour"]) - 1]["socKwh"]
    assert before_discharge - discharge["socKwh"] == pytest.approx(discharge["dischargeKw"] / eta, abs=1e-9)
    assert charge["chargeKw"] > charge["chargeKw"] * eta
    assert discharge["dischargeKw"] / eta > discharge["dischargeKw"]


def test_negative_export_price_curtails_surplus_instead_of_exporting_it():
    result = terminal_solve(inputs(
        pvKw=20, batteryKwh=0, batteryKw=0, loadKw=0, gridKw=100,
        importPrice=0.2, exportPrice=-0.1,
    ))
    assert sum(row["gridExportKw"] for row in result["rows"]) == 0
    assert result["metrics"]["curtailmentKwh"] == pytest.approx(result["metrics"]["renewableKwh"])
    assert result["metrics"]["periodCost"] == 0


@pytest.mark.parametrize("field,value", [
    ("pvKw", math.nan), ("batteryKwh", math.inf), ("batteryKw", -1),
    ("loadKw", 100_001), ("gridKw", -0.01), ("roundtripEfficiency", 0),
    ("roundtripEfficiency", 1.01), ("importPrice", -10.01), ("exportPrice", 10.01),
])
def test_rejects_nonfinite_negative_and_out_of_bound_inputs(field, value):
    with pytest.raises(TerminalModelError, match=field):
        terminal_validate_inputs(inputs(**{field: value}))


def test_input_schema_rejects_unknown_fields_and_storage_mismatch():
    with pytest.raises(TerminalModelError, match="unknown fields: extra"):
        terminal_validate_inputs({**terminal_defaults(), "extra": 1})
    with pytest.raises(TerminalModelError, match="batteryKwh and batteryKw"):
        terminal_validate_inputs(inputs(batteryKwh=0))
    with pytest.raises(TerminalModelError, match="initialSocFraction"):
        terminal_validate_inputs(inputs(initialSocFraction=0.95))
    with pytest.raises(TerminalModelError, match="must be a finite number"):
        terminal_validate_inputs(inputs(pvKw=10**10000))


def test_upper_bound_extremes_remain_finite_and_within_sensible_limits():
    boundary = inputs(
        pvKw=100_000, batteryKwh=500_000, batteryKw=100_000,
        loadKw=100_000, gridKw=100_000, roundtripEfficiency=1,
        initialSocFraction=1, minSocFraction=1, maxSocFraction=1,
        importPrice=10, exportPrice=10,
    )
    validated = terminal_validate_inputs(boundary)
    assert validated == boundary
    result = terminal_solve(boundary)
    assert all(math.isfinite(value) for value in result["metrics"].values())
    assert result["metrics"]["maxBusResidualKw"] < 1e-8
    assert all(0 <= row["socKwh"] <= 500_000 for row in result["rows"])


def test_zero_load_has_defined_service_fraction_and_zero_cost():
    result = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=0, gridKw=0))
    assert result["metrics"]["servedFraction"] == 1
    assert result["metrics"]["periodCost"] == 0
    assert result["metrics"]["unservedKwh"] == 0
    tiny = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=1e-10, gridKw=0))
    unserved_flag = next(flag for flag in tiny["flags"] if flag["key"] == "unserved-demand")
    assert unserved_flag["active"]
    assert "e-" in unserved_flag["explanation"]


def test_log_and_matrix_sweeps_rank_with_service_priority_and_find_pareto():
    base = inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=4, importPrice=0.1)
    result = terminal_sweep(
        base, "importPrice", 0.01, 1.0, 3, "log",
        second={"parameter": "gridKw", "lower": 2, "upper": 4, "steps": 2, "scale": "linear"},
    )
    assert [axis["parameter"] for axis in result["axes"]] == ["importPrice", "gridKw"]
    assert result["axes"][0]["values"] == pytest.approx([0.01, 0.1, 1.0])
    assert len(result["points"]) == 6
    assert result["rankedPointIndices"] == [3, 4, 5, 0, 1, 2]
    assert result["paretoPointIndices"] == [0, 3]
    assert all(point["status"] == "CONVERGED" for point in result["points"])


def test_sweep_preserves_invalid_point_status_instead_of_nonfinite_metrics():
    result = terminal_sweep(inputs(), "batteryKw", 0, 5, 2, "linear")
    assert result["points"][0]["status"] == "ERR_VALIDATION"
    assert result["points"][0]["metrics"] is None
    assert "either both be zero or both be greater" in result["points"][0]["error"]
    assert result["points"][1]["status"] == "CONVERGED"
    with pytest.raises(TerminalModelError, match="positive lower and upper"):
        terminal_sweep(inputs(), "pvKw", 0, 5, 2, "log")


def test_service_equivalent_pareto_guard_matches_total_and_served_demand():
    result = terminal_sweep(
        inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=0),
        "loadKw", 2, 10, 3, "linear",
    )
    assert result["paretoPointIndices"] == [0, 1, 2]
    assert "conditional sampled service-equivalent frontier" in result["warnings"][1]
    assert "not a global optimum" in result["warnings"][1]


def test_two_axis_sweep_is_bounded_at_441_points():
    result = terminal_sweep(
        inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=4),
        "importPrice", 0.01, 1, 21, "linear",
        second={"parameter": "gridKw", "lower": 0, "upper": 20, "steps": 21, "scale": "linear"},
    )
    assert len(result["points"]) == 441
    assert len(result["rankedPointIndices"]) == 441


def test_sweep_bounds_are_bounded_and_integer():
    with pytest.raises(TerminalModelError, match="2 through 21"):
        terminal_sweep(inputs(), "pvKw", 0, 10, 22, "linear")
    with pytest.raises(TerminalModelError, match="at most 100000"):
        terminal_sweep(inputs(), "pvKw", 1, 100_001, 2, "linear")


def test_sensitivity_is_one_at_a_time_and_zero_metrics_have_null_elasticity():
    result = terminal_sensitivity(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=4, importPrice=0))
    assert len(result["rows"]) == 11
    cost = next(row for row in result["rows"] if row["parameter"] == "importPrice")
    assert cost["method"] == "central"
    assert cost["periodCostElasticity"] is None
    grid = next(row for row in result["rows"] if row["parameter"] == "gridKw")
    assert grid["unservedKwhElasticity"] is not None
    zero_input = next(row for row in result["rows"] if row["parameter"] == "pvKw")
    assert zero_input["periodCostElasticity"] is None
    assert "not Sobol" in result["warnings"][0]


def test_diff_returns_null_percent_when_reference_metric_is_zero():
    a = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=4, importPrice=0))
    b = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=4, importPrice=0.25))
    result = terminal_diff(a, b)
    cost = next(row for row in result["rows"] if row["metric"] == "periodCost")
    assert cost["a"] == 0
    assert cost["b"] == pytest.approx(24)
    assert cost["deltaAbsolute"] == pytest.approx(24)
    assert cost["deltaPercent"] is None
    assert next(row for row in result["rows"] if row["metric"] == "servedFraction")["deltaPercent"] == 0


def test_diff_reports_run_specific_regime_shifts_from_operating_flags():
    unserved = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=0))
    served = terminal_solve(inputs(pvKw=0, batteryKwh=0, batteryKw=0, loadKw=10, gridKw=100))
    warnings = terminal_diff(unserved, served)["warnings"]
    shift = next(message for message in warnings if message.startswith("Regime shift for unserved-demand"))
    assert "run a was active" in shift
    assert "run b was inactive" in shift
