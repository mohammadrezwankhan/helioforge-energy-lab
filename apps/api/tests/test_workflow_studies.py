"""Contract, hand-case, boundary, and conservation tests for workflow studies."""
from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from helioforge.engines.workflow_studies import STUDIES, run

IDS = {
    "lessons-duck", "lessons-blackstart", "lessons-hydrogen",
    "compare-pareto", "compare-dunkelflaute", "compare-thermal",
    "pilots-photogrammetry", "pilots-dts", "pilots-offgas",
    "council-debate", "council-evidence", "council-consensus",
}


def metric(result: dict, label: str):
    return next(item["value"] for item in result["metrics"] if item["label"] == label)


def catalogue_defaults(study: dict) -> dict:
    return ({field["name"]: field["default"] for field in study["fields"]} |
            {field["name"]: field["default"] for field in study["data_fields"]})


def candidate(run_id: str, *, scenario: str = "s-1", sample_set: str = "sample-1",
              sample_count: int = 20, cost: float = 100, service: float = 99,
              lole: float = 1) -> dict:
    return {"run_id": run_id, "scenario_key": scenario, "sample_set_key": sample_set,
        "horizon_hours": 24, "sample_count": sample_count, "cost_eur": cost,
        "served_load_pct": service, "storage_capacity_kwh": 100,
        "initial_soc_kwh": 50, "terminal_soc_kwh": 45,
        "expected_loss_of_load_hours": lole}


def test_catalogue_has_twelve_studies_three_per_page_with_numeric_fields_and_json_data():
    assert {item["id"] for item in STUDIES} == IDS
    assert {page: sum(item["page"] == page for item in STUDIES)
            for page in {item["page"] for item in STUDIES}} == {
                "lessons": 3, "compare": 3, "pilots": 3, "council": 3,
            }
    for study in STUDIES:
        assert 3 <= len(study["fields"]) <= 6
        assert study["data_fields"]
        assert all(isinstance(item["default"], (dict, list)) for item in study["data_fields"])


@pytest.mark.parametrize("study", STUDIES, ids=lambda item: item["id"])
def test_every_catalogue_default_runs_and_serializes_finitely(study):
    result = run(study["id"], catalogue_defaults(study))
    json.dumps(result, allow_nan=False)
    assert set(result) == {"metrics", "series", "table", "details", "warnings"}
    assert result["metrics"]
    for item in result["metrics"]:
        assert {"label", "value", "unit"} <= set(item)
        assert item["value"] is None or isinstance(item["value"], (float, int, str))
    for series in result["series"]:
        assert len(series["x"]) == len(series["y"])


def test_duck_lesson_hand_calculates_net_load_ramp_and_energy_closure():
    result = run("lessons-duck", {
        "interval_hours": 0.5, "ramp_limit_kw_per_hour": 3,
        "load_kw": [10, 12], "solar_kw": [2, 2], "wind_kw": [3, 3],
    })
    assert metric(result, "Demand energy") == pytest.approx(11)
    assert metric(result, "Renewable energy") == pytest.approx(5)
    assert metric(result, "Net-load energy") == pytest.approx(6)
    assert metric(result, "Energy closure residual") == pytest.approx(0)
    assert metric(result, "Maximum upward ramp") == pytest.approx(4)
    assert metric(result, "Upward ramps above marker") == 1


def test_blackstart_procedure_requires_sequence_and_respects_active_plus_inrush_budgets():
    out_of_order = run("lessons-blackstart", {
        "steps": [{"action": "energize_bus", "label": "attempt bus first",
                   "active_kw": 0, "inrush_kw": 10}],
    })
    assert out_of_order["table"][0]["accepted"] is False
    assert out_of_order["details"]["state_sequence"][-1] == "dark"
    over_budget = run("lessons-blackstart", {
        "gfm_rated_kw": 100, "available_power_fraction": 1, "reserve_fraction": 0.1,
        "inrush_budget_kw": 50,
        "steps": [{"action": "start_gfm", "label": "start", "active_kw": 0, "inrush_kw": 0},
                  {"action": "energize_bus", "label": "oversized", "active_kw": 70, "inrush_kw": 30}],
    })
    assert over_budget["table"][1]["accepted"] is False
    assert over_budget["table"][1]["reason"].startswith("active power plus inrush")
    assert "transient" in over_budget["warnings"][0]


def test_hydrogen_stages_close_electric_and_lhv_energy_ledger():
    result = run("lessons-hydrogen", {
        "electrolyzer_kwh_per_kg": 52, "compression_kwh_per_kg": 2,
        "fuel_cell_electric_efficiency": 0.5,
        "batch": {"hydrogen_kg": 1, "batch_id": "hand-case"},
    })
    assert metric(result, "Electrolyzer electricity") == pytest.approx(52)
    assert metric(result, "Stored hydrogen chemical energy") == pytest.approx(33.3)
    assert metric(result, "Fuel-cell electricity") == pytest.approx(16.65)
    assert result["details"]["total_electricity_input_kwh"] == pytest.approx(
        result["details"]["useful_electricity_output_kwh"] + result["details"]["accounted_losses_kwh"])
    assert result["details"]["energy_closure_residual_kwh"] == pytest.approx(0)
    assert metric(run("lessons-hydrogen", {"batch": {"hydrogen_kg": 0}}),
                  "Electric round-trip efficiency") is None


def test_pareto_dominance_and_recommendation_are_limited_to_comparable_runs():
    result = run("compare-pareto", {"candidates": [
        candidate("a", cost=100, service=99, lole=1),
        candidate("b", cost=120, service=100, lole=0.5),
        candidate("c", cost=200, service=98, lole=2),
        candidate("different-scenario", scenario="s-2", cost=1, service=100, lole=0),
    ]})
    rows = {row["run_id"]: row for row in result["table"]}
    assert rows["a"]["pareto_nondominated"] is True
    assert rows["b"]["pareto_nondominated"] is True
    assert set(rows["c"]["dominated_by"]) == {"a", "b"}
    assert rows["different-scenario"]["comparable"] is False
    assert len(result["details"]["recommendations"]) == 1
    assert result["details"]["recommendations"][0]["recommended_run_id"] in {"a", "b", "c"}


def test_pareto_does_not_rank_different_sample_sets_or_sample_counts():
    result = run("compare-pareto", {"candidates": [
        candidate("a"), candidate("b", sample_set="other"),
    ]})
    assert all(row["comparable"] is False for row in result["table"])
    assert result["details"]["recommendations"] == []
    assert metric(result, "Weighted recommendations") == 0


def test_dunkelflaute_dispatch_has_336_steps_cyclic_soc_and_energy_balance():
    result = run("compare-dunkelflaute", {})
    assert len(result["table"]) == 336
    assert len(result["series"][0]["x"]) == 336
    assert len(result["series"][2]["x"]) == 337
    assert result["details"]["terminal_soc_kwh"] == pytest.approx(result["details"]["initial_soc_kwh"], abs=1e-6)
    assert 0 <= result["details"]["soc_min_kwh"] <= result["details"]["soc_max_kwh"] <= 500 + 1e-6
    assert metric(result, "Electric balance residual") == pytest.approx(0, abs=1e-5)
    assert any("not statistical LOLE" in warning for warning in result["warnings"])
    assert max(result["details"]["soc_min_kwh"], result["details"]["soc_max_kwh"]) <= 500 + 1e-6


def test_dunkelflaute_dispatch_enforces_direction_and_physical_balance():
    power_limit_kw = 100
    efficiency = 0.94
    result = run("compare-dunkelflaute", {
        "energy_capacity_kwh": 100, "power_limit_kw": power_limit_kw,
        "charge_efficiency": efficiency, "discharge_efficiency": efficiency,
        "initial_soc_kwh": 0, "load_kw": [0.0] * 336, "renewable_kw": [10.0] * 336,
    })

    assert result["table"][0]["charge_kw"] * result["table"][0]["discharge_kw"] == pytest.approx(0)
    assert any(row["curtailment_kw"] > 1e-7 for row in result["table"])
    for row in result["table"]:
        charge = row["charge_kw"]
        discharge = row["discharge_kw"]
        assert min(charge, discharge) <= 1e-7
        assert charge + discharge <= power_limit_kw + 1e-6
        assert 0 <= charge <= power_limit_kw + 1e-6
        assert 0 <= discharge <= power_limit_kw + 1e-6
        assert row["curtailment_kw"] >= -1e-7
        assert row["shortfall_kw"] == pytest.approx(0, abs=1e-7)
        assert (row["renewable_kw"] + discharge + row["shortfall_kw"] ==
                pytest.approx(row["load_kw"] + charge + row["curtailment_kw"], abs=1e-6))
        assert row["soc_end_kwh"] == pytest.approx(
            row["soc_start_kwh"] + efficiency * charge - discharge / efficiency, abs=1e-6)
        assert 0 <= row["soc_start_kwh"] <= 100 + 1e-6
        assert 0 <= row["soc_end_kwh"] <= 100 + 1e-6
    assert result["details"]["terminal_soc_kwh"] == pytest.approx(0, abs=1e-6)


def test_photogrammetry_hand_case_empty_cloud_and_mismatch():
    hand = run("pilots-photogrammetry", {
        "design_points_xyz": [[0, 0, 0]] * 3,
        "asbuilt_points_xyz": [[0, 0, 0], [3, 0, 0], [4, 0, 0]],
        "percentile": 50,
    })
    assert metric(hand, "3D RMSE") == pytest.approx(math.sqrt(25/3))
    assert metric(hand, "Maximum paired error") == pytest.approx(4)
    assert metric(hand, "P50 paired error") == pytest.approx(3)
    empty = run("pilots-photogrammetry", {"design_points_xyz": [], "asbuilt_points_xyz": []})
    assert metric(empty, "Paired point count") == 0
    assert metric(empty, "3D RMSE") is None
    assert empty["series"][0]["x"] == []
    with pytest.raises(ValidationError):
        run("pilots-photogrammetry", {"design_points_xyz": [[0, 0, 0]], "asbuilt_points_xyz": []})


def test_dts_reports_stale_missing_and_only_fresh_gradient_data():
    result = run("pilots-dts", {"current_time_hour": 10, "maximum_age_hours": 1,
        "samples": [{"distance_m": 0, "temperature_c": None, "observed_at_hour": 9},
                    {"distance_m": 10, "temperature_c": 90, "observed_at_hour": 7}]})
    assert metric(result, "Fresh samples") == 0
    assert metric(result, "Missing samples") == 1
    assert metric(result, "Stale samples") == 1
    assert metric(result, "Maximum fresh temperature") is None
    assert result["series"][0]["y"] == [None, None]
    gap = run("pilots-dts", {"current_time_hour": 10, "maximum_age_hours": 2,
        "samples": [{"distance_m": 0, "temperature_c": 20, "observed_at_hour": 9},
                    {"distance_m": 10, "temperature_c": None, "observed_at_hour": 9},
                    {"distance_m": 20, "temperature_c": 100, "observed_at_hour": 9}]})
    assert metric(gap, "Maximum adjacent fresh gradient") is None


@pytest.mark.parametrize("samples", [
    [{"distance_m": 0, "temperature_c": 20, "observed_at_hour": 9},
     {"distance_m": 1e-323, "temperature_c": 21, "observed_at_hour": 9}],
    [{"distance_m": 1, "temperature_c": 20, "observed_at_hour": 9},
     {"distance_m": 1.05, "temperature_c": 21, "observed_at_hour": 9}],
])
def test_dts_rejects_spacing_below_minimum_during_validation(samples):
    with pytest.raises(ValidationError):
        run("pilots-dts", {"samples": samples})


@pytest.mark.parametrize("temperature", [-100, 500])
def test_dts_rejects_unphysical_sample_temperature_during_validation(temperature):
    with pytest.raises(ValidationError):
        run("pilots-dts", {"samples": [
            {"distance_m": 0, "temperature_c": temperature, "observed_at_hour": 9},
            {"distance_m": 10, "temperature_c": 20, "observed_at_hour": 9},
        ]})


def test_offgas_warning_is_explicit_hypothetical_sensor_vote():
    result = run("pilots-offgas", {"votes_required": 2, "sensors": [
        {"sensor_id": "a", "temperature_c": 40, "co_ppm": 40, "voc_ppm": None},
        {"sensor_id": "b", "temperature_c": None, "co_ppm": None, "voc_ppm": 8},
    ]})
    assert metric(result, "Sensors voting") == 2
    assert metric(result, "Hypothetical warning state") == "warning"
    assert "not calibrated" in result["warnings"][0]


def test_council_debate_keeps_conflicting_assertions_and_disputes():
    result = run("council-debate", {})
    annual = next(row for row in result["table"] if row["topic"] == "annual_value")
    assert annual["status"] == "disputed"
    assert annual["resolution"].startswith("unresolved")
    assert result["details"]["dispute_status_persists"] is True
    assert any("no LLM" in warning for warning in result["warnings"])
    zero_rate = run("council-debate", {"discount_rate_fraction": 0})
    assert zero_rate["details"]["npv_eur"] == pytest.approx(230_000*15-1_200_000)


def test_manifest_checks_expiry_units_bounds_and_supplied_provenance():
    result = run("council-evidence", {"manifest": {"as_of_date": "2026-10-17", "documents": [
        {"document_id": "bad-tariff", "kind": "tariff", "field_name": "tariff_eur_mwh",
         "unit": "USD/MWh", "value": 90, "issuer": None, "source_reference": None,
         "issued_on": "2025-01-01", "expires_on": "2026-01-01"}]}})
    issues = result["table"][0]["issues"]
    assert {"unit_mismatch", "expired", "provenance_missing"} <= set(issues)
    assert result["details"]["authenticity_checked"] is False
    assert result["details"]["ocr_used"] is False


def test_bayesian_probability_normalization_entropy_and_boundary_cases():
    result = run("council-consensus", {"prior_probability": 0.5,
        "evidence": [{"evidence_id": "lr-two", "likelihood_ratio": 2,
                      "dependency_group": "one", "note": "illustrative"}]})
    assert metric(result, "Posterior hypothesis probability") == pytest.approx(2/3)
    assert result["details"]["probability_sum"] == pytest.approx(1)
    assert metric(result, "Posterior Shannon entropy") == pytest.approx(
        -(2/3)*math.log2(2/3)-(1/3)*math.log2(1/3))
    endpoint = run("council-consensus", {"prior_probability": 0, "evidence": [
        {"evidence_id": "lr-large", "likelihood_ratio": 1e8,
         "dependency_group": "same", "note": "illustrative"}]})
    assert metric(endpoint, "Posterior hypothesis probability") == 0
    assert metric(endpoint, "Posterior Shannon entropy") == 0
    assert endpoint["details"]["probability_sum"] == pytest.approx(1)


def test_strict_inputs_reject_unknown_nonfinite_fractional_integer_and_invalid_physics():
    with pytest.raises(ValidationError):
        run("lessons-duck", {"unexpected": 1})
    with pytest.raises(ValidationError):
        run("lessons-duck", {"interval_hours": float("nan")})
    with pytest.raises(ValidationError):
        run("pilots-offgas", {"votes_required": 1.5})
    with pytest.raises(ValidationError):
        run("compare-dunkelflaute", {"initial_soc_kwh": 501})
    with pytest.raises(ValueError):
        run("not-a-study", {})
