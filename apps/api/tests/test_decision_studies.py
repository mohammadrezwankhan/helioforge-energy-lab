import copy
import json
import math

import pytest
from pydantic import ValidationError

from helioforge.engines.decision_studies import STUDIES, run


def metric(result, label):
    return next(item["value"] for item in result["metrics"] if item["label"] == label)


def test_all_twelve_catalogue_defaults_run_and_serialize_as_finite_contract_results():
    assert len(STUDIES) == 12
    assert {study["page"] for study in STUDIES} == {"overview", "markets", "forecast", "investment"}
    assert all(sum(study["page"] == page for study in STUDIES) == 3
               for page in ("overview", "markets", "forecast", "investment"))

    for study in STUDIES:
        assert all(isinstance(field["default"], (list, dict)) for field in study["data_fields"])
        inputs = {field["name"]: field["default"] for field in study["fields"]}
        inputs.update({field["name"]: copy.deepcopy(field["default"]) for field in study["data_fields"]})
        result = run(study["id"], inputs)
        assert set(result) == {"metrics", "series", "table", "details", "warnings"}
        assert all(set(item) == {"label", "value", "unit"} for item in result["metrics"])
        assert all(len(series["x"]) == len(series["y"]) for series in result["series"])
        json.dumps(result, allow_nan=False)


def test_unknown_study_and_extra_or_nonfinite_inputs_are_rejected():
    with pytest.raises(ValueError, match="Unknown study"):
        run("unknown", {})
    with pytest.raises(ValidationError):
        run("overview-weather", {"horizon_years": 5, "unknown": 1})
    with pytest.raises(ValidationError):
        run("overview-weather", {"horizon_years": float("inf")})
    with pytest.raises(ValidationError):
        run("forecast-regimes", {"years": 1.5})
    with pytest.raises(ValidationError):
        run("markets-negative", {"prices_eur_mwh": [1e100]})


def test_run_does_not_mutate_user_input():
    inputs = {"horizon_years": 3, "seed": 11, "common_shock_fraction": 0.7}
    before = copy.deepcopy(inputs)
    run("overview-weather", inputs)
    assert inputs == before


def test_weather_stress_exposes_the_common_factor_correlation():
    result = run("overview-weather", {"horizon_years": 3, "common_shock_fraction": 0.5, "seed": 2})
    corr = result["details"]["theoretical_standardized_shock_correlation"]
    assert len(result["table"]) == 6
    assert all(row["stress_index_pct"] >= 0 for row in result["details"]["annual_stress"])
    assert corr[0][0] == 1
    assert corr[0][1] == pytest.approx(0.5)


def test_merit_matrix_compares_value_routes_to_variable_cost():
    result = run("overview-merit", {
        "balancing_weight": 0.25,
        "bilateral_weight": 0.5,
        "spot_weight": 0.25,
        "assets": [{
            "name": "hand case", "variable_cost_eur_mwh": 40,
            "bilateral_value_eur_mwh": 70, "spot_value_eur_mwh": 90,
            "balancing_value_eur_mwh": 110,
        }],
    })
    row = result["table"][0]
    assert row["net_bilateral_eur_mwh"] == 30
    assert row["net_spot_eur_mwh"] == 50
    assert row["net_balancing_eur_mwh"] == 70
    assert row["weighted_net_value_eur_mwh"] == 45


def test_carbon_uses_hourly_marginal_factors_without_credits_or_day_annualization():
    result = run("overview-carbon", {
        "static_factor_kgco2e_mwh": 500,
        "sample_hours": 2,
        "generation_scale": 1,
        "generation_mwh": [1, 3],
        "marginal_factors_kgco2e_mwh": [100, 900],
    })
    assert metric(result, "Hourly marginal emissions") == 2_800
    assert metric(result, "Static-factor emissions") == 2_000
    assert metric(result, "Difference (hourly minus static)") == 800
    assert "credit" in " ".join(result["warnings"]).lower()


def test_capture_price_zero_generation_has_null_not_fabricated_value():
    result = run("markets-capture", {
        "penetration_fraction": 0.5,
        "reference_penetration_fraction": 0.2,
        "cannibalization_slope_eur_mwh": 100,
        "intervals": [{"generation_mwh": 0, "spot_price_eur_mwh": 80}],
    })
    assert metric(result, "Capture price") is None


def test_negative_price_suspension_uses_15_minute_runs_and_warns_about_hypotheses():
    result = run("markets-negative", {
        "interval_minutes": 15,
        "suspension_duration_minutes": 30,
        "negative_threshold_eur_mwh": 0,
        "prices_eur_mwh": [10, -1, -2, 4, -5, -6, -7, 8],
        "country_scenario": {"country_code": "DE"},
    })
    assert metric(result, "Negative settlement intervals") == 5
    assert metric(result, "Suspension-triggering runs") == 2
    assert any("UNVERIFIED" in warning for warning in result["warnings"])


def test_interconnection_zero_capacity_cannot_create_flow():
    result = run("markets-interconnection", {
        "capacity_mw": 0,
        "supply_slope_a_eur_mwh_mw": 1,
        "supply_slope_b_eur_mwh_mw": 1,
        "intervals": [{
            "demand_a_mw": 10, "demand_b_mw": 10,
            "supply_intercept_a_eur_mwh": 20, "supply_intercept_b_eur_mwh": 80,
        }],
    })
    assert result["table"][0]["flow_a_to_b_mw"] == 0


def test_markov_paths_are_seeded_and_quantiles_are_ordered():
    inputs = {"years": 5, "paths": 80, "seed": 13}
    first = run("forecast-regimes", inputs)
    assert first == run("forecast-regimes", inputs)
    assert first != run("forecast-regimes", {**inputs, "seed": 14})
    for row in first["table"]:
        assert row["p10_eur_mwh"] <= row["p50_eur_mwh"] <= row["p90_eur_mwh"]


def test_commodity_correlation_matrix_must_be_positive_semidefinite():
    bad = [[1, 0.9, -0.9], [0.9, 1, 0.9], [-0.9, 0.9, 1]]
    with pytest.raises(ValidationError):
        run("forecast-commodities", {"years": 3, "paths": 20, "seed": 1,
                                      "correlation_matrix": bad})


def test_tail_metrics_use_losses_and_cvar_is_not_below_var():
    result = run("forecast-tail", {"strike_eur_mwh": 80, "volume_mwh": 100,
                                    "years": 3, "paths": 200, "seed": 19,
                                    "annual_volatility": 0.3,
                                    "histogram_year": {"year": 2, "bins": 8}})
    assert metric(result, "95% loss VaR") <= metric(result, "95% loss CVaR")
    assert metric(result, "99% loss VaR") <= metric(result, "99% loss CVaR")
    assert result["details"]["seed"] == 19
    assert len(result["details"]["raw_paths"]) == 200
    assert len(result["details"]["histogram"]["counts"]) == 8
    for path in result["details"]["raw_paths"]:
        for price, loss in zip(path["prices_eur_mwh"], path["losses_eur"]):
            assert loss == pytest.approx((price - 80) * 100)


def test_zero_is_not_counted_as_a_negative_market_price():
    result = run("markets-negative", {"prices_eur_mwh": [0, -1, 1],
                                      "country_scenario": {"country_code": "FR"}})
    assert metric(result, "Negative settlement intervals") == 1


def test_sculpting_reconciles_amortization_and_handles_zero_rate_and_zero_debt():
    base = {
        "target_dscr": 1.25,
        "requested_debt_eur": 50_000,
        "discount_rate": 0,
        "finance_request": {
            "capex_eur": 100_000, "annual_gross_margin_eur": 50_000,
            "annual_opex_eur": 0, "years": 2, "discount_rate": 0,
            "annual_margin_degradation": 0, "escalation_rate": 0,
            "debt_fraction": 0, "debt_interest_rate": 0,
            "debt_tenor_years": 2, "augmentation_year": None,
            "augmentation_cost_eur": 0, "contract_years": 0,
            "merchant_margin_factor": 1,
        },
    }
    result = run("investment-sculpt", base)
    schedule = result["details"]["sculpt_schedule"]
    assert schedule[0]["opening_balance_eur"] == 50_000
    assert schedule[-1]["closing_balance_eur"] == pytest.approx(0)
    for row in schedule:
        assert row["opening_balance_eur"] + row["interest_eur"] - row["debt_service_eur"] == pytest.approx(row["closing_balance_eur"])
        assert row["principal_eur"] >= 0

    positive_rate = copy.deepcopy(base)
    positive_rate["finance_request"]["debt_interest_rate"] = 0.1
    interest_result = run("investment-sculpt", positive_rate)
    interest_schedule = interest_result["details"]["sculpt_schedule"]
    for row in interest_schedule:
        assert row["interest_eur"] == pytest.approx(row["opening_balance_eur"] * 0.1)
        assert row["opening_balance_eur"] + row["interest_eur"] - row["debt_service_eur"] == pytest.approx(row["closing_balance_eur"])

    debt_free = run("investment-sculpt", {**base, "requested_debt_eur": 0})
    assert metric(debt_free, "Minimum DSCR") is None
    assert all(row["dscr"] is None for row in debt_free["details"]["sculpt_schedule"])


def test_sculpting_exposes_negative_cfads_as_infeasible_without_hiding_it():
    result = run("investment-sculpt", {
        "target_dscr": 1.3, "requested_debt_eur": 50_000, "discount_rate": 0.08,
        "finance_request": {
            "capex_eur": 100_000, "annual_gross_margin_eur": 0,
            "annual_opex_eur": 1_000, "years": 2, "debt_fraction": 0,
            "debt_tenor_years": 2, "augmentation_year": None,
            "contract_years": 0,
        },
    })
    assert result["details"]["requested_debt_feasible"] is False
    assert metric(result, "Sculpted debt capacity") == 0
    assert all(row["cfads_eur"] < 0 for row in result["details"]["project_rows"])


def test_tranche_haircut_changes_merchant_debt_capacity_monotonically():
    base = {"target_dscr": 1.3, "merchant_haircut_fraction": 0.5,
            "interest_rate": 0.05, "tenor_years": 3, "contract_years": 2,
            "annual_rows": [
                {"year": 1, "contracted_mwh": 100, "floor_eur_mwh": 90,
                 "merchant_mwh": 100, "merchant_price_eur_mwh": 80, "opex_eur": 1_000},
                {"year": 2, "contracted_mwh": 100, "floor_eur_mwh": 90,
                 "merchant_mwh": 100, "merchant_price_eur_mwh": 80, "opex_eur": 1_000},
                {"year": 3, "contracted_mwh": 0, "floor_eur_mwh": 90,
                 "merchant_mwh": 100, "merchant_price_eur_mwh": 80, "opex_eur": 1_000},
            ]}
    low = run("investment-tranches", base)
    high = run("investment-tranches", {**base, "merchant_haircut_fraction": 1})
    assert metric(low, "Haircut merchant debt capacity") <= metric(high, "Haircut merchant debt capacity")
    assert any("floor" in warning.lower() for warning in low["warnings"])


def test_tranche_capacity_uses_cash_flow_bound_above_one_trillion_euros():
    result = run("investment-tranches", {
        "target_dscr": 1,
        "merchant_haircut_fraction": 1,
        "interest_rate": 0,
        "tenor_years": 40,
        "contract_years": 40,
        "annual_rows": [
            {"year": year, "contracted_mwh": 10_000_000,
             "floor_eur_mwh": 10_000, "merchant_mwh": 10_000_000,
             "merchant_price_eur_mwh": 10_000, "opex_eur": 0}
            for year in range(1, 41)
        ],
    })

    assert metric(result, "Contracted-floor debt capacity") == pytest.approx(4_000_000_000_000)
    assert metric(result, "Haircut merchant debt capacity") == pytest.approx(8_000_000_000_000)
    assert metric(result, "Full merchant debt capacity") == pytest.approx(8_000_000_000_000)
    json.dumps(result, allow_nan=False)


def test_waterfall_conserves_distribution_and_applies_catchup_then_promote():
    result = run("investment-waterfall", {
        "capital_eur": 100, "distribution_pool_eur": 200,
        "years": 2, "preferred_return_rate": 0.08,
        "catchup_share": 0.5, "sponsor_promote_share": 0.2,
    })
    allocations = result["details"]["allocations"]
    assert math.fsum(row["amount_eur"] for row in allocations) == pytest.approx(200)
    assert result["details"]["unallocated_distribution_eur"] == pytest.approx(0)
    assert result["details"]["lp_capital_return_eur"] == pytest.approx(100)
    assert result["details"]["lp_preferred_return_eur"] > 0
    assert result["details"]["sponsor_catchup_eur"] > 0
    assert result["details"]["sponsor_promote_eur"] > 0
