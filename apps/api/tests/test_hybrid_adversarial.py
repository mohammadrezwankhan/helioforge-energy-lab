"""Adversarial, independent checks for the versioned greedy adequacy policy."""

from __future__ import annotations

import pytest

from helioforge.engines.hybrid import simulate_hybrid
from helioforge.hybrid import HybridRequest, get_system

POWER_FIELDS = (
    "load_kw",
    "target_load_kw",
    "served_kw",
    "pv_kw",
    "wind_kw",
    "hydro_kw",
    "generator_kw",
    "charge_kw",
    "discharge_kw",
    "grid_import_kw",
    "grid_export_kw",
    "curtailed_kw",
    "soc_start_kwh",
    "soc_end_kwh",
    "unserved_kw",
    "critical_unserved_kw",
)


def _request(system_id: str, scenario_id: str, **changes: object) -> HybridRequest:
    return HybridRequest.model_validate(
        {**get_system(system_id)["preset"], "scenario_id": scenario_id, **changes}
    )


def test_negative_midday_prices_cannot_change_dispatch_or_enable_grid_charging() -> None:
    settings = {"solar_kw": 0, "battery_kwh": 0, "battery_kw": 0, "load_kw": 500}
    baseline = simulate_hybrid(_request("industrial-btm", "baseline", **settings))
    negative = simulate_hybrid(_request("industrial-btm", "negative-prices", **settings))
    for ordinary, negative_price in zip(baseline["schedule"], negative["schedule"], strict=True):
        for field in POWER_FIELDS:
            assert ordinary[field] == pytest.approx(negative_price[field])
    assert baseline["grid_import_kwh"] == pytest.approx(negative["grid_import_kwh"])
    assert negative["schedule"][12]["import_eur_kwh"] == -0.05
    assert baseline["variable_cost_eur"] > negative["variable_cost_eur"]
    assert all(row["charge_kw"] == 0 for row in negative["schedule"])


def test_battery_trip_preserves_energy_without_converter_flows() -> None:
    result = simulate_hybrid(_request("remote-triad", "battery-trip"))
    initial = result["initial_energy_kwh"]
    assert initial > 0
    assert result["terminal_energy_kwh"] == pytest.approx(initial)
    assert result["battery_energy_delta_kwh"] == pytest.approx(0)
    for row in result["schedule"]:
        assert row["charge_kw"] == row["discharge_kw"] == 0
        assert row["soc_start_kwh"] == pytest.approx(initial)
        assert row["soc_end_kwh"] == pytest.approx(initial)
        assert row["grid_import_kw"] == row["grid_export_kw"] == 0


def test_outage_shortfall_separates_deliberate_noncritical_shedding() -> None:
    request = _request("hospital-island", "outage-4h")
    result = simulate_hybrid(request)
    outage_rows = [row for row in result["schedule"] if not row["grid_connected"]]
    assert len(outage_rows) == 4
    for row in outage_rows:
        assert row["target_load_kw"] == pytest.approx(row["load_kw"] * request.critical_fraction)
        assert row["scheduled_shed_kw"] == pytest.approx(row["load_kw"] - row["target_load_kw"])
        assert row["critical_unserved_kw"] == pytest.approx(
            max(row["critical_load_kw"] - row["served_kw"], 0)
        )
        assert row["unserved_kw"] == pytest.approx(
            row["scheduled_shed_kw"] + row["target_load_kw"] - row["served_kw"]
        )
        assert row["grid_import_kw"] == row["grid_export_kw"] == 0


@pytest.mark.parametrize("scenario_id", ["baseline", "negative-prices", "outage-4h"])
def test_interval_cost_is_independently_recalculated(scenario_id: str) -> None:
    request = _request("hospital-island", scenario_id)
    result = simulate_hybrid(request)
    independently_recalculated = 0.0
    for row in result["schedule"]:
        expected = (
            row["grid_import_kw"] * row["import_eur_kwh"]
            - row["grid_export_kw"] * request.export_eur_kwh
            + row["generator_kw"] * request.generator_eur_kwh
        )
        assert row["variable_cost_eur"] == pytest.approx(expected)
        independently_recalculated += expected
    assert result["variable_cost_eur"] == pytest.approx(independently_recalculated)
