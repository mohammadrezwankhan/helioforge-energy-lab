"""Independent numerical checks for advanced planning studies."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from helioforge.engines.planning_studies import _RUNNERS, STUDIES, AnnualStorageInput, _fit_vecm, run


def test_every_default_study_returns_finite_contract_result() -> None:
    for study in STUDIES:
        if study["id"] == "storage-annualopt":
            continue
        result = run(study["id"], {})
        assert {"metrics", "series", "table", "details", "warnings"} <= result.keys()
        json.dumps(result, allow_nan=False)


def test_catalogue_field_and_data_defaults_validate_against_strict_models() -> None:
    for study in STUDIES:
        inputs = {field["name"]: field["default"] for field in study["fields"]}
        inputs.update({field["name"]: field["default"] for field in study["data_fields"]})
        model = _RUNNERS[study["id"]][0]
        model.model_validate(inputs)


def test_annual_storage_uses_full_year_and_closes_soc() -> None:
    result = run("storage-annualopt", {})
    details = result["details"]
    assert details["interval_count"] == 8760
    assert details["solver_status"] == "optimal"
    assert details["terminal_soc_kwh"] == pytest.approx(details["initial_soc_kwh"], abs=1e-5)
    assert details["max_balance_residual_kw"] < 1e-5
    assert details["max_simultaneous_charge_discharge_kw"] < 1e-5
    assert details["solver_runtime_seconds"] < 5
    assert len(result["table"]) == 8760


def test_annual_storage_matches_hand_calculated_energy_and_monthly_peak_cost() -> None:
    result = run("storage-annualopt", {"load_kw": [100.0] * 8760, "pv_kw": [20.0] * 8760,
        "import_price_eur_kwh": [0.1] * 24, "export_price_eur_kwh": [0.05] * 24,
        "power_kw": 0, "monthly_demand_charge_eur_kw": 2})
    # 80 kW × 8,760 h × €0.10/kWh + 12 × 80 kW × €2/kW-month.
    assert result["metrics"][0]["value"] == pytest.approx(72_000)
    assert result["metrics"][1]["value"] == pytest.approx(72_000)
    assert result["details"]["monthly_peaks_kw"] == pytest.approx([80] * 12)


@pytest.mark.parametrize("demand_charge", [0.0, 2.0])
def test_annual_monthly_peaks_are_observed_import_maxima_with_and_without_peak_pricing(demand_charge):
    p = AnnualStorageInput(monthly_demand_charge_eur_kw=demand_charge)
    result = run("storage-annualopt", {"monthly_demand_charge_eur_kw": demand_charge})
    expected = [max(row["grid_import_kw"] for row in result["table"] if row["month"] == month)
                for month in range(1, 13)]
    details = result["details"]
    assert details["monthly_peaks_kw"] == pytest.approx(expected)
    assert details["maximum_monthly_peak_import_kw"] == pytest.approx(max(expected))
    assert result["series"][2]["y"] == pytest.approx(expected)
    assert details["annual_demand_charge_eur"] == pytest.approx(sum(expected) * demand_charge)
    energy_cost = sum(row["grid_import_kw"] * p.import_price_eur_kwh[row["hour"] % 24]
                      - row["grid_export_kw"] * p.export_price_eur_kwh[row["hour"] % 24]
                      + row["discharge_kw"] * p.discharge_wear_eur_kwh
                      for row in result["table"])
    assert details["annual_energy_cost_eur"] == pytest.approx(energy_cost)
    assert result["metrics"][0]["value"] == pytest.approx(energy_cost + sum(expected) * demand_charge)


def test_annual_storage_rejects_solver_timeout_without_returning_schedule() -> None:
    timeout = SimpleNamespace(status=1, x=None, fun=None, mip_gap=0.8, message="time limit reached")
    with patch("helioforge.engines.planning_studies.milp", return_value=timeout):
        with pytest.raises(ValueError, match="did not prove an optimal schedule"):
            run("storage-annualopt", {})


def test_annual_storage_enforces_direction_binaries_when_zero_export_and_wear_cost() -> None:
    captured: dict = {}

    def inspect_solver(objective, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status=1, x=None, fun=None, mip_gap=None, message="test stop")

    with patch("helioforge.engines.planning_studies.milp", side_effect=inspect_solver):
        with pytest.raises(ValueError, match="did not prove an optimal schedule"):
            run("storage-annualopt", {"export_price_eur_kwh": [0.0] * 24,
                "discharge_wear_eur_kwh": 0, "power_kw": 0.5, "capacity_kwh": 1,
                "initial_soc_kwh": 0.5, "minimum_soc_fraction": 0.5,
                "maximum_soc_fraction": 0.5})

    n = 8760
    integrality = captured["integrality"]
    assert np.count_nonzero(integrality) == n
    matrix = captured["constraints"].A.tocsr()
    # charge <= P z; discharge <= P (1-z), so the binary direction enforces
    # one-way battery power in each interval, independently of the objective.
    assert matrix[2 * n, 0] == pytest.approx(1)
    assert matrix[2 * n, 6 * n + 1] == pytest.approx(-0.5)
    assert matrix[3 * n, n] == pytest.approx(1)
    assert matrix[3 * n, 6 * n + 1] == pytest.approx(0.5)
    assert captured["constraints"].ub[2 * n] == pytest.approx(0)
    assert captured["constraints"].ub[3 * n] == pytest.approx(0.5)


def test_reliability_is_reproducible_and_preserves_chronological_soc() -> None:
    inputs = {"load_kw": [10.0] * 48, "renewable_kw": [5.0] * 48,
              "weather_cv": 0, "generator_capacity_kw": 0,
              "generator_failure_probability_per_hour": 0,
              "trials": 24, "seed": 7, "battery_capacity_kwh": 6,
              "battery_power_kw": 2, "initial_soc_kwh": 3}
    first = run("compare-reliability", inputs)
    second = run("compare-reliability", inputs)
    assert first == second
    assert first["details"]["soc_resets_within_trial"] is False
    assert first["details"]["horizon_hours"] == 48
    assert first["details"]["annualization_factor"] == pytest.approx(8760 / 48)
    assert first["metrics"][0]["value"] == pytest.approx(8760)
    assert first["details"]["lole_horizon_mean_hours"] == pytest.approx(48)


def test_reliability_zero_observed_events_keeps_analytic_rare_event_inside_ci() -> None:
    failure, repair, load_kw = 1e-6, 0.08, 10.0
    result = run("compare-reliability", {"load_kw": [load_kw] * 24,
        "renewable_kw": [0.0] * 24, "generator_capacity_kw": load_kw,
        "generator_failure_probability_per_hour": failure,
        "generator_repair_probability_per_hour": repair, "weather_cv": 0,
        "battery_capacity_kwh": 0, "battery_power_kw": 0, "initial_soc_kwh": 0,
        "trials": 250, "seed": 42})
    details = result["details"]
    assert sum(result["series"][0]["y"]) == 0
    assert sum(result["series"][1]["y"]) == 0
    stationary_outage = failure / (failure + repair)
    analytic_lole = stationary_outage * details["annualization_hours"]
    analytic_eens = analytic_lole * load_kw
    assert details["lole_annualized_95_ci_hours"][0] <= analytic_lole
    assert details["lole_annualized_95_ci_hours"][1] >= analytic_lole
    assert details["eens_annualized_95_ci_kwh"][0] <= analytic_eens
    assert details["eens_annualized_95_ci_kwh"][1] >= analytic_eens
    assert details["lole_event_trial_count"] == 0
    assert details["low_event_warning_triggered"] is True
    assert any("zero observed" in warning for warning in result["warnings"])


def test_reliability_hoeffding_intervals_use_finite_annual_support_bounds() -> None:
    trials, load_kw = 20, 10.0
    result = run("compare-reliability", {"load_kw": [load_kw] * 24,
        "renewable_kw": [0.0] * 24, "generator_capacity_kw": 0,
        "generator_failure_probability_per_hour": 0, "weather_cv": 0,
        "battery_capacity_kwh": 0, "battery_power_kw": 0, "initial_soc_kwh": 0,
        "trials": trials, "seed": 9})
    details = result["details"]
    lole_bound = float(details["annualization_hours"])
    eens_bound = load_kw * 24 * details["annualization_factor"]
    half_width_fraction = np.sqrt(np.log(2 / 0.05) / (2 * trials))
    lole_ci = details["lole_annualized_95_ci_hours"]
    eens_ci = details["eens_annualized_95_ci_kwh"]
    assert lole_ci == pytest.approx([lole_bound * (1 - half_width_fraction), lole_bound])
    assert eens_ci == pytest.approx([eens_bound * (1 - half_width_fraction), eens_bound])
    assert details["lole_outcome_upper_bound_hours_per_year"] == pytest.approx(lole_bound)
    assert details["eens_outcome_upper_bound_kwh_per_year"] == pytest.approx(eens_bound)
    assert "Hoeffding" in details["confidence_interval"]


def test_cointegration_fit_uses_chronological_holdout_and_assumed_rank() -> None:
    t = np.arange(120, dtype=float)
    gas = 35 + 0.2 * t + 3 * np.sin(t / 7)
    carbon = 70 + 0.08 * t + 2 * np.cos(t / 9)
    power = 14 + 1.2 * gas + 0.35 * carbon + 0.15 * np.sin(t / 3)
    result = run("forecast-cointegration", {"gas_price_eur_mwh": gas.tolist(),
        "carbon_price_eur_t": carbon.tolist(), "power_price_eur_mwh": power.tolist(),
        "training_fraction": 0.75, "lag_count": 1, "forecast_steps": 12})
    details = result["details"]
    assert details["rank_assumption"] == 1
    assert details["training_observations"] == 90
    assert details["holdout_observations"] == 30
    assert details["rank_test_performed"] is False
    assert np.isfinite(details["holdout_rmse_power_eur_mwh"])
    assert len(details["forecast_path"]) == 12


def test_vecm_short_run_fit_uses_only_prior_differences() -> None:
    rng = np.random.default_rng(2026)
    n = 400
    gas = 20 + np.cumsum(rng.normal(0, 0.6, n))
    carbon = 40 + np.cumsum(rng.normal(0, 0.3, n))
    residual = np.empty(n)
    residual[0] = 0
    shocks = rng.normal(0, 0.8, n - 1)
    for i in range(1, n):
        residual[i] = 0.65 * residual[i - 1] + shocks[i - 1]
    power = 3 + 1.1 * gas + 0.4 * carbon + residual
    levels = np.column_stack((gas, carbon, power))
    lag_count = 2

    long_run, short_run, reported_rmse = _fit_vecm(levels, lag_count)

    differences = np.diff(levels, axis=0)
    ect = power - long_run[0] - long_run[1] * gas - long_run[2] * carbon
    design, targets = [], []
    for t in range(lag_count + 1, n):
        prior_changes = [differences[t - 1 - lag] for lag in range(1, lag_count + 1)]
        design.append([1.0, ect[t - 1], *np.asarray(prior_changes).ravel()])
        targets.append(differences[t - 1])
    independent_rmse = float(np.sqrt(np.mean((np.asarray(targets) - np.asarray(design) @ short_run) ** 2)))
    assert independent_rmse > 1e-4
    assert reported_rmse == pytest.approx(independent_rmse, rel=1e-10, abs=1e-12)


def test_forecast_backtest_fits_training_rows_and_reports_holdout_metrics() -> None:
    actual = [100.0] * 48
    result = run("forecast-backtest", {"target_price_eur_mwh": actual,
        "gas_price_eur_mwh": [30.0] * 48, "carbon_price_eur_t": [60.0] * 48,
        "training_fraction": 0.75})
    details = result["details"]
    assert details["training_observations"] == 35
    assert details["holdout_observations"] == 12
    assert details["mae_eur_mwh"] == pytest.approx(0)
    assert details["rmse_eur_mwh"] == pytest.approx(0)
    assert details["prediction_interval_coverage_fraction"] == pytest.approx(1)


def test_six_zone_dcopf_prices_separate_across_congested_cut() -> None:
    zones = ["A", "B", "C", "D", "E", "F"]
    lines = [{"from_zone": i, "to_zone": i + 1,
              "susceptance_mw_per_rad": 100, "limit_mw": 100} for i in range(4)]
    lines.append({"from_zone": 4, "to_zone": 5, "susceptance_mw_per_rad": 100, "limit_mw": 20})
    result = run("markets-network", {"zone_names": zones,
        "demand_mw": [0, 0, 0, 0, 0, 80],
        "generator_capacity_mw": [100, 0, 0, 0, 0, 100],
        "generator_cost_eur_mwh": [10, 10, 10, 10, 10, 100], "lines": lines})
    assert result["details"]["total_generation_mw"] == pytest.approx(80)
    assert result["details"]["nodal_prices_eur_mwh"][0] == pytest.approx(10)
    assert result["details"]["nodal_prices_eur_mwh"][5] == pytest.approx(100)
    assert result["details"]["max_balance_residual_mw"] < 1e-7


def test_contract_model_reconciles_cash_ledgers_and_releases_reserves() -> None:
    result = run("investment-contracts", {})
    details = result["details"]
    assert details["dsra_balance_eur"][-1] == pytest.approx(0)
    assert details["terminal_working_capital_eur"] == pytest.approx(0)
    assert abs(details["project_cashflow_reconciliation_eur"]) < 0.02
    assert details["tax_loss_carryforward_eur"] >= 0
    assert details["project_irr_pct"] is None or np.isfinite(details["project_irr_pct"])
    assert details["equity_irr_pct"] is None or np.isfinite(details["equity_irr_pct"])
    assert result["table"][0]["contract_settled_price_eur_mwh"] == pytest.approx(85)


def test_contract_debt_service_is_continuous_at_tiny_positive_rates() -> None:
    zero_rate = run("investment-contracts", {"debt_interest_rate": 0})
    tiny_rate = run("investment-contracts", {"debt_interest_rate": 1e-20})
    assert np.isfinite(tiny_rate["table"][0]["debt_service_eur"])
    assert tiny_rate["table"][0]["debt_service_eur"] == pytest.approx(
        zero_rate["table"][0]["debt_service_eur"], rel=1e-12, abs=1e-8)


def test_contract_tax_losses_carry_forward_and_zero_investment_irr_stays_null() -> None:
    rows = [
        {"year": 2027, "generation_mwh": 0, "merchant_price_eur_mwh": 100, "opex_eur": 2000},
        {"year": 2028, "generation_mwh": 100, "merchant_price_eur_mwh": 100, "opex_eur": 0},
    ]
    result = run("investment-contracts", {"capex_eur": 1000, "debt_share": 0,
        "debt_interest_rate": 0, "debt_tenor_years": 1, "tax_rate": 0.25,
        "depreciation_years": 1, "dsra_months": 0, "working_capital_fraction_of_revenue": 0,
        "operating_years": rows, "contracts": []})
    assert result["table"][0]["equity_nol_closing_eur"] > 0
    assert result["table"][1]["equity_nol_closing_eur"] == pytest.approx(0)
    assert result["table"][1]["equity_cash_tax_eur"] == pytest.approx(1750)
    no_investment = run("investment-contracts", {"capex_eur": 0, "debt_share": 0,
        "debt_interest_rate": 0, "debt_tenor_years": 1,
        "operating_years": [
            {"year": 2027, "generation_mwh": 0, "merchant_price_eur_mwh": 100, "opex_eur": 0},
            {"year": 2028, "generation_mwh": 0, "merchant_price_eur_mwh": 100, "opex_eur": 0},
        ], "contracts": []})
    assert no_investment["details"]["project_irr_pct"] is None
    assert no_investment["details"]["equity_irr_pct"] is None


def test_hydrogen_ledger_accounts_for_treatment_compression_and_auxiliaries() -> None:
    result = run("lessons-hydrogenaux", {"hydrogen_kg": 10})
    details = result["details"]
    assert details["water_feed_kg"] > details["stoichiometric_water_kg"]
    assert details["compression_pressure_out_bar"] == pytest.approx(350)
    assert details["fuel_cell_auxiliary_kwh"] > 0
    assert details["energy_balance_residual_kwh"] == pytest.approx(0, abs=1e-8)


def test_portfolio_risk_distinguishes_breach_missing_and_unprovenanced_data() -> None:
    result = run("overview-risk", {"evidence": [
        {"asset": "North", "metric": "price", "value": 120, "threshold": 100,
         "direction": "max", "unit": "EUR/MWh", "source_reference": "meter-1", "observed_on": "2026-01-01"},
        {"asset": "South", "metric": "yield", "value": None, "threshold": 900,
         "direction": "min", "unit": "kWh/kWp/year", "source_reference": None, "observed_on": None},
        {"asset": "East", "metric": "DSCR", "value": 1.4, "threshold": 1.2,
         "direction": "min", "unit": "x", "source_reference": None, "observed_on": None},
    ]})
    assert result["details"]["breach_count"] == 1
    assert result["details"]["missing_value_count"] == 1
    assert result["details"]["missing_provenance_count"] == 2
    assert result["table"][1]["status"] == "missing_value"
    assert result["table"][2]["status"] == "within_threshold_unverified"


def test_point_cloud_icp_recovers_rigid_transform_without_photo_inputs() -> None:
    design = [[0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3], [1, 2, 3],
              [2, 1, 0], [1, 0, 2], [0, 3, 1]]
    theta = 0.02
    rotation = [[np.cos(theta), -np.sin(theta), 0],
                [np.sin(theta), np.cos(theta), 0], [0, 0, 1]]
    survey = (np.asarray(design) @ np.asarray(rotation).T + [0.03, -0.02, 0.01]).tolist()
    result = run("pilots-registration", {"design_points_xyz": design,
        "survey_points_xyz": survey, "maximum_correspondence_distance_m": 1.0,
        "trim_fraction": 1.0})
    assert result["details"]["registration_rmse_m"] < 1e-6
    assert result["details"]["converged"] is True
    assert result["details"]["photos_used"] is False
    assert len(result["details"]["rotation_matrix"]) == 3
    assert len(result["table"]) == len(survey)
    assert all(row["retained_inlier"] for row in result["table"])


def test_point_cloud_retention_uses_ceiling_and_reports_actual_fraction() -> None:
    result = run("pilots-registration", {"trim_fraction": 0.8})
    details = result["details"]
    assert details["eligible_correspondence_count"] == 6
    assert details["minimum_retained_count"] == 5
    assert details["inlier_count"] == 5
    assert details["actual_retained_fraction"] == pytest.approx(5 / 6)
    assert details["trim_fraction"] == pytest.approx(0.8)


def test_studies_reject_nonannual_storage_and_disconnected_network() -> None:
    with pytest.raises(ValueError):
        run("storage-annualopt", {"load_kw": [1.0] * 24})
    with pytest.raises(ValueError):
        run("markets-network", {"lines": []})
    with pytest.raises(ValueError):
        run("compare-reliability", {"load_kw": [1.0] * 8760,
            "renewable_kw": [0.0] * 8760, "trials": 5000})
    with pytest.raises(ValueError):
        run("overview-risk", {"evidence": [{"asset": "A", "metric": "price", "value": float("nan"),
            "threshold": 1, "direction": "max", "unit": "EUR/MWh"}]})
    with pytest.raises(ValueError):
        run("not-a-study", {})
