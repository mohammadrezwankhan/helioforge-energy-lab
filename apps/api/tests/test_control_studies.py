"""Numerical invariants for the averaged converter controller and eigenmodes."""
from __future__ import annotations

import json

import numpy as np
import pytest
from pydantic import ValidationError

from helioforge.engines import control_studies as studies


def test_catalogue_defaults_execute_and_serialize_as_finite_json() -> None:
    assert {study["id"] for study in studies.STUDIES} == {
        "hybrid-controls",
        "research-eigenmodes",
    }
    for study in studies.STUDIES:
        result = studies.run(study["id"], {})
        encoded = json.dumps(result, allow_nan=False)
        assert encoded
        assert {"metrics", "series", "table", "details", "warnings"} <= result.keys()
        assert result["details"]


def test_no_load_case_holds_grid_voltage_and_zero_current() -> None:
    result = studies.run("hybrid-controls", {"load_step_a": 0.0})
    details = result["details"]
    voltage_d = _series(result, "capacitor_voltage_d")
    voltage_q = _series(result, "capacitor_voltage_q")
    filter_current_d = _series(result, "filter_current_d")
    filter_current_q = _series(result, "filter_current_q")
    grid_current_d = _series(result, "grid_current_d")
    grid_current_q = _series(result, "grid_current_q")

    assert details["converged"] is True
    assert max(abs(value - details["grid_voltage_peak_v"]) for value in voltage_d["y"]) < 1e-8
    assert max(abs(value) for value in voltage_q["y"]) < 1e-8
    assert max(abs(value) for value in filter_current_d["y"]) < 1e-8
    expected_capacitor_q_current = (
        studies.HybridControlsInput().grid_angular_frequency_rad_s
        * studies.HybridControlsInput().filter_capacitance_f
        * details["grid_voltage_peak_v"]
    )
    assert max(abs(value - expected_capacitor_q_current) for value in filter_current_q["y"]) < 1e-8
    assert max(abs(value) for value in grid_current_d["y"]) < 1e-8
    assert max(abs(value) for value in grid_current_q["y"]) < 1e-8


def test_load_step_is_tracked_and_refined_trajectories_agree() -> None:
    result = studies.run(
        "hybrid-controls",
        {"duration_s": 0.05, "load_step_a": 8.0},
    )
    details = result["details"]
    voltage = _series(result, "capacitor_voltage_d")
    filter_current = _series(result, "filter_current_d")
    reference = _series(result, "current_reference_d")

    assert details["converged"] is True
    assert details["load_step_a"] == 8.0
    assert details["maximum_abs_voltage_refinement_error_v"] < 0.1
    assert details["maximum_abs_current_refinement_error_a"] < 0.02
    assert max(abs(value - details["grid_voltage_peak_v"]) for value in voltage["y"]) > 1e-4
    assert abs(filter_current["y"][-1] - reference["y"][-1]) < 0.1
    assert len(voltage["x"]) <= 500


def test_vector_limit_is_enforced_during_large_load_step() -> None:
    result = studies.run(
        "hybrid-controls",
        {
            "duration_s": 0.02,
            "load_step_time_s": 0.004,
            "load_step_a": 100.0,
            "current_limit_a": 5.0,
        },
    )
    details = result["details"]
    current_ref = _series(result, "current_reference_d")
    inverter_voltage = _series(result, "inverter_voltage_d")

    assert details["current_reference_limit_hit_count"] > 0
    assert max(abs(value) for value in current_ref["y"]) <= 5.0 + 1e-8
    assert details["inverter_voltage_limit_v"] < details["dc_bus_v"]
    assert max(abs(value) for value in inverter_voltage["y"]) <= details["inverter_voltage_limit_v"] + 1e-7

    no_antiwindup = studies.run(
        "hybrid-controls",
        {
            "duration_s": 0.02,
            "load_step_time_s": 0.004,
            "load_step_a": 100.0,
            "current_limit_a": 5.0,
            "voltage_antiwindup_per_s": 0.0,
        },
    )
    antiwindup_integral = _series(result, "voltage_integrator_q")["y"]
    unwound_integral = _series(no_antiwindup, "voltage_integrator_q")["y"]
    assert max(abs(value) for value in antiwindup_integral) < max(abs(value) for value in unwound_integral)


def test_invalid_limits_events_and_unknown_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        studies.run("hybrid-controls", {"load_step_time_s": 0.004123})
    with pytest.raises(ValidationError):
        studies.run("hybrid-controls", {"unexpected": 1})
    with pytest.raises(ValidationError):
        studies.run("hybrid-controls", {"time_step_s": 1e-7})
    with pytest.raises(ValidationError):
        studies.run("hybrid-controls", {"dc_bus_v": float("inf")})


def test_eigenmodes_report_actual_matrix_eigenvalues_and_stable_default() -> None:
    result = studies.run("research-eigenmodes", {})
    matrix = np.asarray(result["details"]["state_matrix_per_s"], dtype=float)
    reported = np.asarray(
        [complex(row["real_per_s"], row["imaginary_per_s"]) for row in result["table"]]
    )
    independently_computed = np.linalg.eigvals(matrix)
    model = studies.EigenmodesInput.model_validate({})
    equilibrium = np.asarray(result["details"]["equilibrium_state"], dtype=float)
    equilibrium_derivative = studies._rhs(equilibrium, model, np.zeros(2))

    assert matrix.shape == (10, 10)
    assert np.max(np.abs(equilibrium_derivative)) < 1e-8
    assert result["details"]["stability"] == "locally_asymptotically_stable"
    assert max(value.real for value in independently_computed) < 0
    assert np.allclose(np.sort_complex(reported), np.sort_complex(independently_computed), atol=1e-7)
    # With i_f,d as state 0, the d-axis inductor self term includes plant R and
    # the proportional current feedback. This is an independent hand coefficient.
    assert matrix[0, 0] == pytest.approx(
        -(result["details"]["filter_resistance_ohm"]
          + result["details"]["current_kp_v_per_a"])
        / result["details"]["filter_inductance_h"],
        rel=1e-8,
    )


def test_wrong_sign_outer_integral_gain_exposes_unstable_mode() -> None:
    result = studies.run(
        "research-eigenmodes",
        {"voltage_ki_a_per_vs": -80.0},
    )
    eigenvalues = [complex(row["real_per_s"], row["imaginary_per_s"]) for row in result["table"]]

    assert result["details"]["stability"] == "unstable"
    assert result["details"]["maximum_real_part_per_s"] > 0
    assert max(value.real for value in eigenvalues) == pytest.approx(
        result["details"]["maximum_real_part_per_s"], abs=1e-7
    )
    assert "wrong-sign" in " ".join(result["warnings"]).lower()


def test_eigenmode_input_validation_and_unknown_study() -> None:
    with pytest.raises(ValidationError):
        studies.run("research-eigenmodes", {"filter_inductance_h": 1e-9})
    with pytest.raises(ValidationError):
        studies.run("research-eigenmodes", {"dc_bus_v": 120.0})
    with pytest.raises(ValidationError):
        studies.run("research-eigenmodes", {"voltage_ki_a_per_vs": 0.0})
    with pytest.raises(ValidationError):
        studies.run(
            "research-eigenmodes",
            {
                "filter_inductance_h": 0.02,
                "filter_capacitance_f": 0.001,
                "grid_angular_frequency_rad_s": 400.0,
                "grid_voltage_peak_v": 800.0,
            },
        )
    with pytest.raises(ValidationError):
        studies.run("hybrid-controls", {"filter_capacitance_f": 0.001})
    with pytest.raises(ValueError, match="Unknown control study"):
        studies.run("not-a-study", {})


def _series(result: dict, prefix: str) -> dict:
    return next(row for row in result["series"] if row["name"] == prefix)
