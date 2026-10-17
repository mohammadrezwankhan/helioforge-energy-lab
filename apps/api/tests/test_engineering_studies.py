"""Contract and hand-check tests for the engineering experimental studies."""
from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from helioforge.engines.engineering_studies import INPUT_MODELS, STUDIES, run

EXPECTED_IDS = {
    "hybrid-resonance", "hybrid-clipping", "hybrid-inertia",
    "storage-degradation", "storage-stacking", "storage-synergy",
    "pv-backtracking", "pv-agrivoltaic", "pv-albedo",
    "research-vibration", "research-epd", "research-scr",
}


def metric(result: dict, label: str):
    return next(item["value"] for item in result["metrics"] if item["label"] == label)


def test_catalogue_has_three_distinct_studies_per_engineering_page():
    assert {study["id"] for study in STUDIES} == EXPECTED_IDS
    assert {page: sum(s["page"] == page for s in STUDIES)
            for page in {s["page"] for s in STUDIES}} == {
                "hybrid": 3, "storage": 3, "pv": 3, "research": 3,
            }
    for study in STUDIES:
        model = INPUT_MODELS[study["id"]]
        assert 3 <= len(study["fields"]) <= 6
        for control in study["fields"]:
            assert control["name"] in model.model_fields
            assert control["min"] <= control["default"] <= control["max"]
            assert control["step"] > 0
        for data_field in study["data_fields"]:
            assert data_field["name"] in model.model_fields
            default = json.loads(json.dumps(data_field["default"]))
            assert default == model().model_dump(mode="json")[data_field["name"]]


def test_catalogue_defaults_run_through_renderer_result_contract():
    for study in STUDIES:
        inputs = {field["name"]: field["default"] for field in study["fields"]}
        inputs.update({field["name"]: field["default"] for field in study["data_fields"]})
        result = run(study["id"], inputs)
        json.dumps(result, allow_nan=False)
        for item in result["series"]:
            assert set(item) == {"name", "x_label", "y_unit", "x", "y"}
            assert isinstance(item["name"], str)
            assert isinstance(item["x_label"], str)
            assert isinstance(item["y_unit"], str)
            assert len(item["x"]) == len(item["y"])
            assert all(isinstance(value, (int, float, str)) for value in item["x"])
            assert all(value is None or (isinstance(value, (int, float)) and math.isfinite(value))
                       for value in item["y"])


@pytest.mark.parametrize("study_id", sorted(EXPECTED_IDS))
def test_each_study_default_is_finite_and_matches_result_contract(study_id):
    result = run(study_id, {})
    json.dumps(result, allow_nan=False)
    assert set(result) >= {"metrics", "series", "table", "details", "warnings"}
    assert all({"label", "value", "unit"} <= set(item) for item in result["metrics"])
    for series in result["series"]:
        assert len(series["x"]) == len(series["y"])


def test_study_inputs_reject_unknown_nonfinite_and_unknown_ids():
    with pytest.raises(ValidationError):
        run("hybrid-inertia", {"extra": 1})
    with pytest.raises(ValidationError):
        run("hybrid-inertia", {"inertia_seconds": float("nan")})
    with pytest.raises(ValueError):
        run("not-a-study", {})


def test_resonance_zero_coupling_retains_two_uncoupled_natural_modes():
    result = run("hybrid-resonance", {"coupling_fraction": 0})
    modes = result["details"]["modes"]
    natural = sorted(round(mode["frequency_hz"], 2) for mode in modes)
    assert natural == sorted([round(result["details"]["mode_1_hz"], 2),
                              round(result["details"]["mode_2_hz"], 2)])
    assert all(mode["stable"] for mode in modes)


def test_clipping_recovery_is_limited_by_power_and_soc_headroom():
    result = run("hybrid-clipping", {
        "pv_dc_kw": 1200, "inverter_ac_kw": 800, "inverter_efficiency": 1,
        "battery_capacity_kwh": 100, "battery_initial_kwh": 98,
        "battery_charge_limit_kw": 1000,
    })
    assert metric(result, "Clipped DC energy recovered") == pytest.approx(2)
    assert metric(result, "Unrecovered clipped DC energy") == pytest.approx(400 - 2 / 0.96)
    assert result["details"]["dc_balance_residual_kwh"] == pytest.approx(0)


def test_clipping_without_excess_pv_does_not_add_battery_energy():
    result = run("hybrid-clipping", {"pv_dc_kw": 500, "battery_initial_kwh": 100})
    assert metric(result, "Clipped DC energy available") == pytest.approx(0)
    assert metric(result, "Ending battery energy") == pytest.approx(100)


def test_synthetic_inertia_reduces_initial_rocof_and_stays_bounded():
    baseline = run("hybrid-inertia", {"synthetic_inertia_mw_s_per_hz": 0})
    supported = run("hybrid-inertia", {})
    assert metric(supported, "Initial RoCoF") > metric(baseline, "Initial RoCoF")
    assert metric(supported, "Minimum frequency") >= 40
    assert metric(supported, "Maximum absolute RoCoF") < 10
    assert all(math.isfinite(v) for v in supported["details"]["frequency_hz"])


def test_degradation_contributions_are_separate_and_increase_with_stress():
    mild = run("storage-degradation", {"temperature_c": 25, "charge_c_rate": 0.5})
    cold_fast = run("storage-degradation", {"temperature_c": 5, "charge_c_rate": 2})
    hot = run("storage-degradation", {"temperature_c": 35, "charge_c_rate": 0.5})
    cycled = run("storage-degradation", {"equivalent_full_cycles": 4800})
    assert set(mild["details"]["loss_fraction_by_mechanism"]) == {"sei", "plating", "fatigue"}
    assert cold_fast["details"]["loss_fraction_by_mechanism"]["plating"] > mild["details"]["loss_fraction_by_mechanism"]["plating"]
    assert hot["details"]["loss_fraction_by_mechanism"]["sei"] > mild["details"]["loss_fraction_by_mechanism"]["sei"]
    assert cycled["details"]["loss_fraction_by_mechanism"]["fatigue"] > mild["details"]["loss_fraction_by_mechanism"]["fatigue"]


def test_storage_stacking_obeys_energy_power_and_terminal_soc():
    result = run("storage-stacking", {
        "capacity_kwh": 2, "power_kw": 1, "initial_soc_fraction": 0.1,
        "round_trip_efficiency": 1,
        "price_eur_mwh": [100, 300], "reserve_up_price_eur_mw_h": [0, 0],
        "reserve_down_price_eur_mw_h": [0, 0], "reserve_up_request_mw": [0, 0],
        "reserve_down_request_mw": [0, 0],
    })
    assert result["details"]["terminal_soc_kwh"] == pytest.approx(0.2)
    assert metric(result, "Optimized arbitrage revenue") == pytest.approx(0.2)
    for row in result["table"]:
        assert row["charge_kw"] + row["discharge_kw"] + row["up_reserve_mw"] + row["down_reserve_mw"] <= 1 + 1e-6


def test_storage_stacking_flat_zero_service_is_a_no_op():
    result = run("storage-stacking", {
        "price_eur_mwh": [100, 100], "reserve_up_price_eur_mw_h": [0, 0],
        "reserve_down_price_eur_mw_h": [0, 0], "reserve_up_request_mw": [0, 0],
        "reserve_down_request_mw": [0, 0],
    })
    assert metric(result, "Total modeled gross value") == pytest.approx(0)
    assert all(row["charge_kw"] == pytest.approx(0) and row["discharge_kw"] == pytest.approx(0)
               for row in result["table"])


def test_hybrid_storage_split_conserves_energy_and_reports_unmet_power():
    result = run("storage-synergy", {
        "interval_seconds": 1, "flywheel_energy_kwh": 0.1,
        "flywheel_power_kw": 100, "battery_energy_kwh": 1,
        "battery_power_kw": 100, "disturbance_kw": [100, 100, 0, -100],
    })
    assert result["details"]["maximum_power_balance_residual_kw"] == pytest.approx(0, abs=1e-8)
    assert metric(result, "Unmet power energy") == pytest.approx(0)
    assert result["details"]["flywheel_energy_kwh"][-1] == pytest.approx(0.5 * 0.1, abs=0.1)


def test_hybrid_storage_zero_power_reports_requested_power_as_unmet():
    result = run("storage-synergy", {"flywheel_power_kw": 0, "battery_power_kw": 0,
                                     "disturbance_kw": [10, -10]})
    assert metric(result, "Unmet power energy") == pytest.approx(20 / 3600)
    assert result["details"]["flywheel_energy_kwh"] == pytest.approx([10, 10, 10])


@pytest.mark.parametrize("disturbance", [1_000_001, -1_000_001, 1e308, -1e308])
def test_storage_synergy_rejects_disturbances_outside_one_gigawatt_bound(disturbance):
    with pytest.raises(ValidationError):
        run("storage-synergy", {"disturbance_kw": [0, disturbance]})


def test_backtracking_reduces_or_preserves_planar_row_shading():
    raw = {"backtracking": 0}
    no_backtracking = run("pv-backtracking", raw)
    with_backtracking = run("pv-backtracking", {"backtracking": 1})
    assert metric(with_backtracking, "Mean row-shaded fraction") <= metric(no_backtracking, "Mean row-shaded fraction") + 1e-9


def test_agrivoltaic_polygon_area_and_par_tradeoff_hand_case():
    polygon = [[0, 0], [100, 0], [100, 50], [0, 50]]
    result = run("pv-agrivoltaic", {"land_polygon_m": polygon, "setback_m": 1, "ground_coverage_ratio": 0.4})
    assert metric(result, "Land polygon area") == pytest.approx(5000)
    assert metric(result, "Conservative usable area") == pytest.approx(4700)
    less_coverage = run("pv-agrivoltaic", {"land_polygon_m": polygon, "setback_m": 1, "ground_coverage_ratio": 0.2})
    assert metric(less_coverage, "Estimated crop PAR") > metric(result, "Estimated crop PAR")


def test_agrivoltaic_rejects_nonadjacent_polygon_edges_that_touch():
    touching = [[0, 0], [2, 0], [2, 2], [1, 0], [0, 2]]
    with pytest.raises(ValidationError):
        run("pv-agrivoltaic", {"land_polygon_m": touching})


def test_bifacial_albedo_gain_and_monthly_annual_reconciliation():
    low = run("pv-albedo", {"albedo": 0.1})
    high = run("pv-albedo", {"albedo": 0.8})
    assert metric(high, "Annual energy with rear response") > metric(low, "Annual energy with rear response")
    assert metric(high, "Annual energy with rear response") == pytest.approx(
        sum(row["energy_with_rear_kwh"] for row in high["table"])
    )
    zero = run("pv-albedo", {"albedo": 0})
    assert metric(zero, "Annual rear-side contribution") == pytest.approx(0)


def test_vibration_fft_recovers_known_sine_peak_and_seed_is_reproducible():
    count = 1024
    signal = [math.sin(2 * math.pi * 64 * i / 1024) for i in range(count)]
    result = run("research-vibration", {"sample_rate_hz": 1024, "signal": signal})
    assert metric(result, "Dominant frequency") == pytest.approx(64)
    assert run("research-vibration", {}) == run("research-vibration", {})


def test_epd_sum_skips_duplicate_and_makes_missing_records_visible():
    result = run("research-epd", {"records": [
        {"record_id": "a", "supplier": "S1", "stage": "materials", "quantity": 2,
         "unit": "kg", "emission_factor_kgco2e_per_unit": 3, "evidence_id": "EPD-1",
         "data_quality": "supplier_primary"},
        {"record_id": "a", "supplier": "S1", "stage": "materials", "quantity": 2,
         "unit": "kg", "emission_factor_kgco2e_per_unit": 3, "evidence_id": "EPD-1",
         "data_quality": "supplier_primary"},
        {"record_id": "b", "supplier": "S2", "stage": "transport", "quantity": 1,
         "unit": "t_km", "emission_factor_kgco2e_per_unit": None, "evidence_id": None,
         "data_quality": "secondary"},
    ]})
    assert metric(result, "Included emissions") == pytest.approx(6)
    assert result["details"]["duplicate_record_ids"] == ["a"]
    assert result["details"]["missing_record_ids"] == ["b"]


def test_epd_empty_inventory_has_null_like_zero_completeness_without_imputation():
    result = run("research-epd", {"records": []})
    assert metric(result, "Included emissions") == pytest.approx(0)
    assert metric(result, "Evidence completeness") == pytest.approx(0)
    assert result["details"]["missing_record_ids"] == []


@pytest.mark.parametrize("record", [
    {"record_id": "huge-quantity", "stage": "materials", "quantity": 1e200,
     "emission_factor_kgco2e_per_unit": 1},
    {"record_id": "huge-factor", "stage": "materials", "quantity": 1,
     "emission_factor_kgco2e_per_unit": 1e200},
])
def test_epd_rejects_extreme_quantity_and_factor_before_multiplication(record):
    with pytest.raises(ValidationError):
        run("research-epd", {"records": [record]})


def test_epd_maximum_bounded_quantity_and_factor_remain_json_finite():
    result = run("research-epd", {"records": [{
        "record_id": "bounded-maximum", "stage": "materials", "quantity": 1_000_000_000_000,
        "unit": "kg", "emission_factor_kgco2e_per_unit": 1_000_000,
        "supplier": "Illustrative supplier", "evidence_id": "SYNTHETIC-1",
    }]})

    assert metric(result, "Included emissions") == 1_000_000_000_000_000_000
    json.dumps(result, allow_nan=False)


def test_scr_and_voltage_drop_hand_case_is_labeled_as_screening():
    result = run("research-scr", {
        "short_circuit_mva": 600, "plant_mw": 100,
        "active_power_mw": 80, "reactive_power_mvar": 30,
        "voltage_kv": 20, "line_r_ohm": 0.1,
    })
    assert metric(result, "SCR at plant rating") == pytest.approx(6)
    assert metric(result, "Approximate voltage-drop magnitude") == pytest.approx(4.25)
    assert any("not a stability" in warning.lower() for warning in result["warnings"])


def test_numeric_switch_and_bounded_array_validation_reject_fractional_or_extreme_inputs():
    with pytest.raises(ValidationError):
        run("pv-backtracking", {"backtracking": 0.5})
    with pytest.raises(ValidationError):
        run("storage-synergy", {"disturbance_kw": [0.0] * 3601})
