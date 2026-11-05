"""Independent failure and boundary contracts for physical study families.

Malformed user data must fail before solving. Failed numerical backends must not
produce an apparently usable result. The hand cases below also cover charging,
geometry, excluded inventory stages, and complete supplied annual observations.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from pydantic import ValidationError

from helioforge.engines import control_studies as control
from helioforge.engines import engineering_studies as engineering
from helioforge.engines import physical_studies as physical
from helioforge.engines import toolkit_studies as toolkit
from helioforge.engines.study_types import StudyResult
from tests.study_contract_assertions import numbers

RUNNERS: dict[str, Callable[[str, object], StudyResult]] = {
    "physical": physical.run,
    "engineering": engineering.run,
    "control": control.run,
    "toolkit": toolkit.run,
}


def buses(*kinds: str) -> list[dict[str, object]]:
    return [{"bus_id": f"b{index}", "kind": kind} for index, kind in enumerate(kinds)]


def branch(start: str, end: str) -> dict[str, object]:
    return {"from_bus": start, "to_bus": end, "r_pu": 0.1, "x_pu": 0}


def observations(
    count: int, *, flat_cycles: bool = False, flat_temperature: bool = False
) -> list[dict[str, float]]:
    return [
        {
            "cycle_count": 1000 if flat_cycles else 100 * (index + 1),
            "temperature_c": 25 if flat_temperature else 20 + index,
            "capacity_fraction": 0.98,
        }
        for index in range(count)
    ]


def vibration_records(*, mismatched: bool = False, duplicate: bool = False) -> dict[str, object]:
    return {
        "training_records": [{"record_id": f"train-{index}", "signal": [0.0] * 64} for index in range(3)],
        "heldout_records": [
            {"record_id": "train-0" if duplicate else "heldout", "signal": [0.0] * (65 if mismatched else 64)}
        ],
    }


@pytest.mark.parametrize(
    "family,study,inputs,message",
    [
        ("physical", "hybrid-powerflow", {"branches": [branch("grid", "grid")]}, "two different buses"),
        (
            "physical",
            "hybrid-powerflow",
            {"buses": [{"bus_id": "same", "kind": "slack"}, {"bus_id": "same", "kind": "pq"}]},
            "Bus IDs must be unique",
        ),
        ("physical", "hybrid-powerflow", {"buses": buses("pq", "pq")}, "exactly one slack bus"),
        ("physical", "hybrid-powerflow", {"buses": buses("slack", "slack")}, "exactly one slack bus"),
        (
            "physical",
            "hybrid-powerflow",
            {"buses": buses("slack", "pq"), "branches": [branch("b0", "missing")]},
            "Every branch endpoint",
        ),
        (
            "physical",
            "hybrid-powerflow",
            {"buses": buses("slack", "pq", "pq"), "branches": [branch("b0", "b1")]},
            "All buses must be connected",
        ),
        ("physical", "hybrid-switching", {"time_step_s": 0.000001}, "Simulation is too long"),
        ("physical", "lessons-energization", {"breaker_close_s": 0.1}, "inside the simulated window"),
        ("physical", "lessons-energization", {"time_step_s": 0.000001}, "Simulation is too long"),
        (
            "physical",
            "storage-response",
            {"minimum_soc_fraction": 0.8, "maximum_soc_fraction": 0.2},
            "Minimum SOC must be less",
        ),
        (
            "physical",
            "storage-response",
            {"minimum_soc_fraction": 0.2, "initial_soc_fraction": 0.1},
            "Initial SOC must be between",
        ),
        ("physical", "storage-response", {"frequency_hz": [44.0, 50.0]}, "between 45 and 65 Hz"),
        (
            "physical",
            "storage-agingfit",
            {"observations": observations(8)},
            "six training and two held-out observations",
        ),
        (
            "physical",
            "storage-agingfit",
            {"observations": observations(10, flat_cycles=True)},
            "range of cycle counts",
        ),
        (
            "physical",
            "storage-agingfit",
            {"observations": observations(10, flat_temperature=True)},
            "range of temperatures",
        ),
        (
            "physical",
            "compare-thermalphysics",
            {"initial_temperature_c": 100, "termination_temperature_c": 100},
            "below the termination threshold",
        ),
        (
            "physical",
            "compare-thermalphysics",
            {"duration_s": 120, "time_step_s": 0.01},
            "Thermal run is too long",
        ),
        (
            "physical",
            "pv-raytrace",
            {"panel_samples": [{"position_m": [0, 0, 0], "normal": [0, 0, 0], "area_m2": 1}]},
            "normal vectors must be non-zero",
        ),
        (
            "physical",
            "pv-setbacks",
            {"parcels": [{"exterior_m": [[0, 0], [2, 2], [0, 2], [2, 0]]}]},
            "valid, non-empty polygon",
        ),
        (
            "physical",
            "pv-setbacks",
            {
                "parcels": [
                    {"exterior_m": [[0, 0], [2, 0], [2, 2], [0, 2]]},
                    {"exterior_m": [[1, 0], [3, 0], [3, 2], [1, 2]]},
                ]
            },
            "must not overlap",
        ),
        (
            "physical",
            "research-bearing",
            {"training_records": vibration_records()["training_records"]},
            "Supply both training and held-out records",
        ),
        ("physical", "research-bearing", vibration_records(mismatched=True), "same sample count"),
        ("physical", "research-bearing", vibration_records(duplicate=True), "record IDs must be unique"),
        (
            "engineering",
            "hybrid-clipping",
            {"battery_initial_kwh": 501, "battery_capacity_kwh": 500},
            "Initial battery energy cannot exceed capacity",
        ),
        ("engineering", "storage-stacking", {"price_eur_mwh": [10, 20]}, "must have equal lengths"),
        ("engineering", "storage-stacking", {"initial_soc_fraction": 0}, "Initial SOC must be inside"),
        ("engineering", "pv-backtracking", {"sun_elevation_deg": [1]}, "must have equal lengths"),
        (
            "engineering",
            "pv-backtracking",
            {"sun_elevation_deg": [-1], "sun_azimuth_deg": [90]},
            "Solar elevation must be between",
        ),
        (
            "engineering",
            "pv-backtracking",
            {"module_width_m": 3, "row_pitch_m": 2},
            "Module width cannot exceed",
        ),
        (
            "engineering",
            "pv-agrivoltaic",
            {"land_polygon_m": [[0, 0], [2, 0], [2, 2], [0, 0]]},
            "vertices must be distinct",
        ),
        (
            "engineering",
            "pv-agrivoltaic",
            {"land_polygon_m": [[0, 0], [100001, 0], [0, 1]]},
            "coordinates must stay within",
        ),
        ("engineering", "pv-agrivoltaic", {"land_polygon_m": [[0, 0], [1, 0], [2, 0]]}, "non-zero area"),
        (
            "engineering",
            "research-vibration",
            {"synthetic_frequency_hz": 128},
            "frequencies must be below Nyquist",
        ),
        (
            "engineering",
            "research-vibration",
            {"synthetic_drift_hz": 120},
            "spectral drift magnitude must remain below Nyquist",
        ),
        ("engineering", "research-vibration", {"signal": [0.0] * 63}, "at least 64 samples"),
        (
            "engineering",
            "research-scr",
            {"plant_mw": 10, "active_power_mw": 11},
            "cannot exceed the stated plant rating",
        ),
        (
            "control",
            "hybrid-controls",
            {"duration_s": 0.12, "time_step_s": 0.00001},
            "bounded to 6,000 time steps",
        ),
        ("control", "hybrid-controls", {"load_step_time_s": 0.04}, "before the end of duration_s"),
        ("control", "hybrid-controls", {"current_kp_v_per_a": -1.0}, "PI gains must be positive"),
        ("control", "hybrid-controls", {"current_limit_a": 1.0}, "equilibrium capacitor q-axis current"),
        ("control", "research-eigenmodes", {"current_ki_v_per_as": -1.0}, "Current PI gains"),
        ("control", "research-eigenmodes", {"current_limit_a": 1.0}, "equilibrium inside the current limit"),
        (
            "toolkit",
            "storage-annual",
            {"export_price": 0.2},
            "import prices at least as high as export prices",
        ),
        (
            "toolkit",
            "storage-annual",
            {"hourly_load_kw": [1.0] * 24},
            "both complete 8760-hour load and PV arrays",
        ),
    ],
)
def test_cross_field_constraints_reject_unsafe_or_ill_defined_studies(
    family: str, study: str, inputs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=re.escape(message)):
        RUNNERS[family](study, inputs)


@pytest.mark.parametrize(
    "family,study",
    [("physical", "hybrid-powerflow"), ("engineering", "hybrid-inertia"), ("control", "hybrid-controls")],
)
def test_nonobject_study_requests_are_rejected(family: str, study: str) -> None:
    with pytest.raises(TypeError, match="JSON object"):
        RUNNERS[family](study, [])


def test_bearing_model_does_not_turn_nonobject_input_into_synthetic_evidence() -> None:
    with pytest.raises(ValidationError):
        physical.BearingInput.model_validate([{"record_id": "unexpected"}])


def test_overfrequency_absorbs_energy_with_charge_efficiency_and_ramp_limits() -> None:
    result = physical.run(
        "storage-response",
        {
            "capacity_kwh": 100,
            "initial_soc_fraction": 0.5,
            "power_limit_kw": 100,
            "droop_kw_per_hz": 1000,
            "ramp_kw_per_s": 100,
            "interval_s": 0.1,
            "round_trip_efficiency": 0.81,
            "frequency_hz": [50.1, 50.1],
        },
    )
    assert [row["response_kw"] for row in result["table"]] == [-10, -20]
    assert result["table"][-1]["soc_end_kwh"] == pytest.approx(50 + 30 * 0.1 / 3600 * 0.9, abs=1e-12)
    metrics = {item["label"]: item["value"] for item in result["metrics"]}
    assert metrics["Absorbed response energy"] == pytest.approx(30 * 0.1 / 3600, abs=1e-12)
    assert metrics["Delivered response energy"] == 0


@pytest.mark.parametrize(
    "success,coefficients,message",
    [
        (False, [0.018, 0.008], "did not converge"),
        (True, [math.nan, 0.008], "did not converge"),
        (True, [0.2, 0.1], "leaves the bounded"),
    ],
)
def test_failed_or_unphysical_aging_fit_never_returns_capacity_predictions(
    success: bool, coefficients: list[float], message: str
) -> None:
    fit = SimpleNamespace(success=success, x=np.asarray(coefficients))
    with patch.object(physical, "least_squares", return_value=fit), pytest.raises(ValueError, match=message):
        physical.run("storage-agingfit", {})


@pytest.mark.parametrize("failure", ["unsuccessful", "nonfinite", "missing-events"])
def test_thermal_backend_failures_do_not_return_a_successful_trajectory(failure: str) -> None:
    solution = SimpleNamespace(
        success=failure != "unsuccessful",
        y=np.asarray([[math.nan if failure == "nonfinite" else 25.0], [0.0]]),
        t_events=None,
        y_events=None,
    )
    expected = (
        "omitted configured event results" if failure == "missing-events" else "failed or returned non-finite"
    )
    with (
        patch.object(physical, "solve_ivp", return_value=solution),
        pytest.raises(ValueError, match=expected),
    ):
        physical.run("compare-thermalphysics", {})


def test_reaction_trip_stops_thermal_run_at_analytically_known_event() -> None:
    result = physical.run(
        "compare-thermalphysics",
        {
            "reaction_energy_j": 0,
            "cooling_w_per_k": 0,
            "activation_energy_kj_mol": 0,
            "reaction_rate_ref_per_s": 0.005,
            "reaction_fraction_trip": 0.01,
            "duration_s": 4,
        },
    )
    assert result["details"]["termination_reason"] == "reaction fraction threshold reached"
    assert result["details"]["final_reaction_fraction"] == pytest.approx(0.01, abs=1e-10)
    # For constant k and zero initial conversion, alpha(t) = 1 - exp(-k*t).
    assert numbers(result["series"][0]["x"])[-1] == pytest.approx(-math.log(0.99) / 0.005, abs=1e-7)
    assert result["details"]["final_temperature_c"] == pytest.approx(25, abs=1e-12)


@pytest.mark.parametrize(
    "origin,direction,expected",
    [
        ([0.25, 0.25, 0.0], [0.0, 0.0, 1.0], True),
        ([0.25, 0.25, 0.0], [1.0, 0.0, 0.0], False),
        ([-1.0, 0.25, 0.0], [0.0, 0.0, 1.0], False),
        ([0.25, -1.0, 0.0], [0.0, 0.0, 1.0], False),
        ([0.8, 0.8, 0.0], [0.0, 0.0, 1.0], False),
        ([0.25, 0.25, 2.0], [0.0, 0.0, 1.0], False),
    ],
)
def test_ray_triangle_intersection_respects_plane_barycentric_bounds_and_forward_distance(
    origin: list[float], direction: list[float], expected: bool
) -> None:
    triangle: tuple[physical.Point3, physical.Point3, physical.Point3] = (
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 1.0),
    )
    assert physical._ray_triangle_hit(np.asarray(origin), np.asarray(direction), triangle) is expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_engineering_metrics_fail_closed(value: float) -> None:
    with pytest.raises(ValueError, match="Non-finite result for injected metric"):
        engineering._m("injected metric", value, "kWh")


@pytest.mark.parametrize(
    "solution", [SimpleNamespace(success=False, x=None), SimpleNamespace(success=True, x=None)]
)
def test_storage_service_optimizer_failure_does_not_emit_a_schedule(solution: object) -> None:
    with (
        patch.object(engineering, "milp", return_value=solution),
        pytest.raises(ValueError, match="No feasible storage"),
    ):
        engineering.run("storage-stacking", {})


def test_zero_synthetic_inertia_headroom_is_identical_to_no_support() -> None:
    capped = engineering.run("hybrid-inertia", {"synthetic_inertia_limit_mw": 0})
    no_support = engineering.run("hybrid-inertia", {"synthetic_inertia_mw_s_per_hz": 0})
    assert capped["series"] == no_support["series"]
    assert set(numbers(capped["details"]["synthetic_inertia_mw"])) == {0}


def test_sun_below_sloping_ground_does_not_create_tracker_angle_or_shadow() -> None:
    result = engineering.run(
        "pv-backtracking",
        {"terrain_slope_deg": 5, "sun_elevation_deg": [0], "sun_azimuth_deg": [90]},
    )
    assert [series["y"] for series in result["series"]] == [[0], [0], [0]]


def test_odd_sample_noise_free_vibration_retains_supplied_data_and_seed_label() -> None:
    signal = [math.sin(2 * math.pi * 10 * index / 255) for index in range(255)]
    result = engineering.run("research-vibration", {"sample_rate_hz": 255, "signal": signal})
    assert result["details"]["seed"] is None
    assert result["metrics"][0]["value"] == pytest.approx(10, abs=1e-12)
    synthetic = engineering.run("research-vibration", {"noise_std": 0})
    assert synthetic["details"]["seed"] == 42
    assert synthetic == engineering.run("research-vibration", {"noise_std": 0})


def test_excluded_emissions_and_repeated_duplicate_ids_remain_auditable_without_double_counting() -> None:
    supplied = {
        "record_id": "source-a",
        "supplier": "Illustrative",
        "stage": "materials",
        "quantity": 2,
        "unit": "kg",
        "emission_factor_kgco2e_per_unit": 3,
        "evidence_id": "SYNTHETIC-a",
    }
    result = engineering.run(
        "research-epd", {"include_materials": 0, "records": [supplied, supplied, supplied]}
    )
    assert result["details"]["duplicate_record_ids"] == ["source-a"]
    assert [row["status"] for row in result["table"]] == [
        "excluded_by_stage_boundary",
        "duplicate_skipped",
        "duplicate_skipped",
    ]
    assert next(item["value"] for item in result["metrics"] if item["label"] == "Included emissions") == 0
    assert result["table"][0]["emissions_kgco2e"] == 6


def test_control_refinement_shape_mismatch_fails_before_reporting_convergence() -> None:
    with (
        patch.object(control, "_integrate", side_effect=[np.zeros((3, 10)), np.zeros((2, 10))]),
        pytest.raises(ArithmeticError, match="did not align"),
    ):
        control.run("hybrid-controls", {})


def test_control_rhs_rejects_nonfinite_state_before_computing_derivatives() -> None:
    with pytest.raises(ArithmeticError, match="state became non-finite"):
        control._rhs(np.full(10, math.nan), control.HybridControlsInput(), np.zeros(2))


def test_control_integrator_bounds_refinement_work_and_rejects_divergence() -> None:
    parameters = control.HybridControlsInput()
    initial = control._equilibrium(parameters)
    with pytest.raises(ValueError, match="bounded to 12,000 integration steps"):
        control._integrate(parameters, initial, parameters.duration_s / 12001)
    with (
        patch.object(control, "_rhs", return_value=np.full(10, 1e16)),
        pytest.raises(ArithmeticError, match="diverged or exceeded"),
    ):
        control._integrate(parameters, initial, parameters.time_step_s)


def test_control_linearization_rejects_nonfinite_derivatives() -> None:
    parameters = control.EigenmodesInput()
    with (
        patch.object(control, "_rhs", return_value=np.full(10, math.nan)),
        pytest.raises(ArithmeticError, match="non-finite coefficients"),
    ):
        control._linearize(parameters, control._equilibrium(parameters))


def test_control_eigenvalue_backend_cannot_emit_nonfinite_modes() -> None:
    with (
        patch.object(np.linalg, "eigvals", return_value=np.asarray([complex(math.nan, 0)])),
        pytest.raises(ArithmeticError, match="non-finite state matrix or mode"),
    ):
        control.run("research-eigenmodes", {})


def test_supplied_full_year_observations_are_used_without_synthetic_replacement() -> None:
    result = toolkit.run(
        "storage-annual",
        {
            "hourly_load_kw": [4.0] * 8760,
            "hourly_pv_kw": [4.0] * 8760,
            "tariff": [0.1] * 24,
            "export_price": 0.1,
            "efficiency": 1,
            "wear": 0,
        },
    )
    rows = result["table"]
    assert len(rows) == 8760
    assert all(row["load_kw"] == 4 and row["pv_kw"] == 4 for row in rows)
    assert rows[0]["timestamp"] == "2025-01-01T00:00:00"
    assert rows[-1]["timestamp"] == "2025-12-31T23:00:00"
    assert len({row["timestamp"] for row in rows}) == 8760


def test_unknown_toolkit_study_cannot_fall_through_to_an_unrelated_calculation() -> None:
    with pytest.raises(ValueError, match="Unknown supporting study"):
        toolkit.run("unsupported", {})
