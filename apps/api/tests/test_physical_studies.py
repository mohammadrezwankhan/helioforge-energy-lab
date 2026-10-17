"""Contract, hand-case and boundary tests for the physical experimental studies."""
from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from helioforge.engines.physical_studies import INPUT_MODELS, STUDIES, run

EXPECTED_IDS = {
    "hybrid-powerflow",
    "hybrid-switching",
    "lessons-energization",
    "storage-response",
    "storage-agingfit",
    "compare-thermalphysics",
    "pv-raytrace",
    "pv-setbacks",
    "research-bearing",
}


def metric(result: dict, label: str):
    return next(item["value"] for item in result["metrics"] if item["label"] == label)


def test_catalogue_defaults_are_strict_and_every_study_returns_finite_renderer_data():
    assert {study["id"] for study in STUDIES} == EXPECTED_IDS
    assert {study["page"] for study in STUDIES} == {"hybrid", "lessons", "storage", "compare", "pv", "research"}
    for study in STUDIES:
        model = INPUT_MODELS[study["id"]]
        for field in study["fields"]:
            assert field["name"] in model.model_fields
            assert field["min"] <= field["default"] <= field["max"]
            assert field["step"] > 0
        for data_field in study["data_fields"]:
            assert data_field["name"] in model.model_fields
            assert json.loads(json.dumps(data_field["default"])) == model().model_dump(mode="json")[data_field["name"]]
        result = run(study["id"], {})
        json.dumps(result, allow_nan=False)
        assert set(result) >= {"metrics", "series", "table", "details", "warnings"}
        assert all({"label", "value", "unit"} <= set(item) for item in result["metrics"])
        for series in result["series"]:
            assert set(series) == {"name", "x_label", "y_unit", "x", "y"}
            assert len(series["x"]) == len(series["y"])
            assert len(series["x"]) <= 500
            assert all(value is None or isinstance(value, (int, float)) and math.isfinite(value)
                       for value in series["y"])


def test_unknown_study_extra_fields_and_nonfinite_values_are_rejected():
    with pytest.raises(ValueError):
        run("not-a-study", {})
    with pytest.raises(ValidationError):
        run("storage-response", {"unexpected": 1})
    with pytest.raises(ValidationError):
        run("storage-response", {"nominal_frequency_hz": float("nan")})


def test_extreme_values_and_invalid_network_or_time_resolution_are_rejected():
    with pytest.raises(ValidationError):
        run("hybrid-powerflow", {"max_iterations": 3.5})
    with pytest.raises(ValidationError):
        run("hybrid-powerflow", {"branches": [{"from_bus": "grid", "to_bus": "campus",
                                                   "r_pu": 0, "x_pu": 0}]})
    with pytest.raises(ValidationError):
        run("hybrid-switching", {"switching_hz": 5000, "time_step_s": 0.00005})
    with pytest.raises(ValidationError):
        run("storage-agingfit", {"observations": [{"cycle_count": 1e100,
                                                      "temperature_c": 25,
                                                      "capacity_fraction": 0.9}] * 8})
    with pytest.raises(ValidationError):
        run("pv-raytrace", {"occluder_triangles": [[[0, 0, 0], [0, 0, 0], [0, 0, 0]]]})
    with pytest.raises(ValidationError):
        run("research-bearing", {"training_records": [], "heldout_records": []})


def test_balanced_two_bus_powerflow_matches_resistive_hand_solution_and_branch_loss():
    result = run("hybrid-powerflow", {
        "base_mva": 100,
        "buses": [
            {"bus_id": "grid", "kind": "slack", "p_load_mw": 0, "q_load_mvar": 0,
             "voltage_pu": 1, "angle_deg": 0},
            {"bus_id": "load", "kind": "pq", "p_load_mw": 50, "q_load_mvar": 0,
             "voltage_pu": 1, "angle_deg": 0},
        ],
        "branches": [{"from_bus": "grid", "to_bus": "load", "r_pu": 0.1, "x_pu": 0,
                      "b_pu": 0, "rate_mva": 100}],
    })
    assert result["details"]["converged"] is True
    assert result["details"]["buses"][1]["voltage_pu"] == pytest.approx((1 + math.sqrt(0.8)) / 2, abs=1e-7)
    branch = result["details"]["branches"][0]
    assert branch["from_p_mw"] - 50 == pytest.approx(branch["loss_p_mw"], abs=1e-6)
    assert branch["loss_p_mw"] == pytest.approx(100 * (1 - branch["to_voltage_pu"]) ** 2 / 0.1, abs=1e-5)


def test_powerflow_fails_closed_for_unsolvable_constant_power_load_and_reports_thermal_limit():
    case = {
        "base_mva": 100,
        "buses": [
            {"bus_id": "grid", "kind": "slack", "p_load_mw": 0, "q_load_mvar": 0,
             "voltage_pu": 1, "angle_deg": 0},
            {"bus_id": "load", "kind": "pq", "p_load_mw": 50, "q_load_mvar": 0,
             "voltage_pu": 1, "angle_deg": 0},
        ],
        "branches": [{"from_bus": "grid", "to_bus": "load", "r_pu": 0.1, "x_pu": 0,
                      "b_pu": 0, "rate_mva": 1}],
    }
    solved = run("hybrid-powerflow", case)
    assert solved["details"]["branches"][0]["over_limit"] is True
    case["buses"][1]["p_load_mw"] = 300
    with pytest.raises(ValueError, match="did not converge"):
        run("hybrid-powerflow", case)


def test_switching_and_averaged_inverter_modes_are_distinct_and_numerically_converged():
    switching = run("hybrid-switching", {"switching_enabled": 1})
    averaged = run("hybrid-switching", {"switching_enabled": 0})
    assert switching["details"]["mode"] == "switching"
    assert averaged["details"]["mode"] == "averaged"
    assert switching["details"]["switching_ripple_rms_a"] > averaged["details"]["switching_ripple_rms_a"]
    assert switching["details"]["convergence_relative_error"] < 0.05


def test_energization_trace_starts_at_breaker_step_and_closes_circuit_energy_balance():
    result = run("lessons-energization", {"time_step_s": 0.00002, "simulation_cycles": 2})
    times = result["series"][0]["x"]
    currents = result["series"][0]["y"]
    close_at = result["details"]["breaker_close_s"]
    assert max(abs(value) for t, value in zip(times, currents) if t < close_at) == pytest.approx(0)
    assert max(abs(value) for t, value in zip(times, currents) if t >= close_at) > 0
    assert result["details"]["energy_balance_residual_j"] == pytest.approx(0, abs=0.5)
    assert result["details"]["convergence_relative_error"] < 0.05


def test_frequency_droop_obeys_ramp_soc_power_and_dt_energy_integration():
    result = run("storage-response", {
        "capacity_kwh": 100,
        "initial_soc_fraction": 0.5,
        "power_limit_kw": 100,
        "droop_kw_per_hz": 1000,
        "ramp_kw_per_s": 100,
        "interval_s": 0.1,
        "frequency_hz": [49.9, 49.9],
    })
    power = [row["response_kw"] for row in result["table"]]
    assert power == pytest.approx([10, 20])
    assert metric(result, "Delivered response energy") == pytest.approx(sum(power) * 0.1 / 3600)
    assert max(abs(row["response_kw"]) for row in result["table"]) <= 100
    assert all(0.1 * 100 <= row["soc_end_kwh"] <= 0.9 * 100 for row in result["table"])


def test_frequency_response_is_noop_at_nominal_and_respects_empty_soc_headroom():
    no_op = run("storage-response", {"frequency_hz": [50, 50]})
    at_floor = run("storage-response", {
        "capacity_kwh": 1, "initial_soc_fraction": 0.1, "minimum_soc_fraction": 0.1,
        "maximum_soc_fraction": 0.9, "power_limit_kw": 1000, "ramp_kw_per_s": 10000,
        "frequency_hz": [49, 49],
    })
    assert metric(no_op, "Delivered response energy") == pytest.approx(0)
    assert all(row["response_kw"] == pytest.approx(0) for row in no_op["table"])
    assert all(row["response_kw"] == pytest.approx(0) for row in at_floor["table"])
    assert metric(at_floor, "Terminal state of charge") == pytest.approx(0.1)


def test_agingfit_recovers_synthetic_coefficient_and_reports_heldout_error():
    result = run("storage-agingfit", {})
    assert result["details"]["dataset_label"].startswith("Synthetic fixture")
    assert result["details"]["heldout_count"] >= 2
    assert metric(result, "Fitted cycle loss per 1000 cycles") == pytest.approx(0.018, rel=0.02)
    assert metric(result, "Held-out RMSE") < 0.003
    assert "scientific validation" in " ".join(result["warnings"]).lower()


def test_thermal_model_passively_cools_and_stops_at_configured_threshold_without_alarm_claim():
    cooling = run("compare-thermalphysics", {
        "initial_temperature_c": 70, "ambient_temperature_c": 20, "reaction_energy_j": 0,
        "duration_s": 10, "time_step_s": 0.05,
    })
    assert metric(cooling, "Peak lumped temperature") == pytest.approx(70, abs=1e-6)
    assert cooling["details"]["final_temperature_c"] < 70
    assert cooling["details"]["termination_reason"] == "duration reached"
    assert any("not a validated safety alarm" in warning.lower() for warning in cooling["warnings"])


def test_thermal_arrhenius_source_stops_at_temperature_event():
    result = run("compare-thermalphysics", {
        "initial_temperature_c": 25, "ambient_temperature_c": 25,
        "thermal_mass_j_per_k": 1000, "cooling_w_per_k": 0,
        "activation_energy_kj_mol": 80, "reaction_rate_ref_per_s": 0.005,
        "reaction_energy_j": 10_000_000, "duration_s": 60, "time_step_s": 0.1,
        "termination_temperature_c": 50,
    })
    assert result["details"]["termination_reason"] == "temperature threshold reached"
    assert result["details"]["final_temperature_c"] == pytest.approx(50, abs=1e-7)
    assert 0 < result["details"]["final_reaction_fraction"] < 0.01


def test_ray_triangle_shading_handles_shadow_backface_and_zero_sun():
    clear = run("pv-raytrace", {})
    shadowed = run("pv-raytrace", {
        "panel_samples": [{"position_m": [0, 0, 0], "normal": [0, 0, 1], "area_m2": 10}],
        "sun_vectors": [{"direction": [0, 0, 1], "dni_w_m2": 800, "duration_h": 1}],
        "occluder_triangles": [[[ -1, -1, 1], [1, -1, 1], [0, 1, 1]]],
    })
    backface = run("pv-raytrace", {
        "panel_samples": [{"position_m": [0, 0, 0], "normal": [0, 0, -1], "area_m2": 10}],
        "sun_vectors": [{"direction": [0, 0, 1], "dni_w_m2": 800, "duration_h": 1}],
    })
    zero_sun = run("pv-raytrace", {
        "sun_vectors": [{"direction": [0, 0, 0], "dni_w_m2": 800, "duration_h": 1}],
    })
    hand_case = run("pv-raytrace", {
        "panel_samples": [{"position_m": [0, 0, 0], "normal": [0, 0, 1], "area_m2": 10}],
        "sun_vectors": [{"direction": [0, 0, 1], "dni_w_m2": 800, "duration_h": 1}],
    })
    assert metric(clear, "Incident direct-beam energy") > 0
    assert metric(hand_case, "Incident direct-beam energy") == pytest.approx(8)
    assert metric(shadowed, "Incident direct-beam energy") == pytest.approx(0)
    assert metric(backface, "Incident direct-beam energy") == pytest.approx(0)
    assert metric(zero_sun, "Incident direct-beam energy") == pytest.approx(0)


def test_polygon_setback_preserves_multipolygon_holes_and_crop_light_tradeoff():
    geometry = {
        "parcels": [
            {"exterior_m": [[0, 0], [10, 0], [10, 10], [0, 10]],
             "holes_m": [[[4, 4], [6, 4], [6, 6], [4, 6]]]},
            {"exterior_m": [[20, 0], [25, 0], [25, 5], [20, 5]], "holes_m": []},
        ],
        "setback_m": 1,
    }
    result = run("pv-setbacks", geometry)
    assert metric(result, "Parcel area") == pytest.approx(121)
    assert metric(result, "Usable area after setback") == pytest.approx(57)
    full_light = run("pv-setbacks", {**geometry, "pv_cover_fraction": 0})
    assert metric(full_light, "Estimated crop DLI") > metric(result, "Estimated crop DLI")
    assert "calibrat" in " ".join(result["warnings"]).lower()


def test_bearing_spectrum_envelope_flags_heldout_frequency_outlier_without_diagnosis():
    count = 256
    training = []
    for index in range(6):
        signal = [((1 + index * 0.005) * math.sin(2 * math.pi * 24 * i / count)
                   + 0.01 * math.sin(2 * math.pi * 43 * i / count)) for i in range(count)]
        training.append({"record_id": f"train-{index}", "signal": signal})
    nominal = [math.sin(2 * math.pi * 24 * i / count) + 0.01 * math.sin(2 * math.pi * 43 * i / count)
               for i in range(count)]
    anomalous = [value + 0.4 * math.sin(2 * math.pi * 62 * i / count)
                 for i, value in enumerate(nominal)]
    result = run("research-bearing", {
        "sample_rate_hz": 256,
        "training_records": training,
        "heldout_records": [{"record_id": "nominal", "signal": nominal},
                             {"record_id": "outlier", "signal": anomalous}],
    })
    by_id = {row["record_id"]: row["flagged"] for row in result["table"]}
    assert by_id == {"nominal": False, "outlier": True}
    by_id_exceedance = {row["record_id"]: row["maximum_envelope_exceedance_sigma"] for row in result["table"]}
    assert by_id_exceedance["nominal"] == 0
    assert by_id_exceedance["outlier"] > 0
    assert any("diagnos" in warning.lower() for warning in result["warnings"])


def test_bearing_positive_deviation_below_training_envelope_is_not_exceedance():
    count = 256
    training = []
    for index, amplitude in enumerate((1.0, 1.01, 1.02, 1.03, 1.04)):
        signal = [amplitude * math.sin(2 * math.pi * 24 * sample / count) for sample in range(count)]
        training.append({"record_id": f"train-{index}", "signal": signal})
    heldout = [1.15 * math.sin(2 * math.pi * 24 * sample / count) for sample in range(count)]

    result = run("research-bearing", {
        "sample_rate_hz": 256,
        "threshold_sigma": 4,
        "training_records": training,
        "heldout_records": [{"record_id": "below-envelope", "signal": heldout}],
    })
    row = result["table"][0]

    assert row["flagged"] is False
    assert row["exceedance_bin_count"] == 0
    assert row["maximum_envelope_exceedance_sigma"] == 0
