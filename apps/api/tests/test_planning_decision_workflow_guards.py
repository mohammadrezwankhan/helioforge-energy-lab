"""Reject inconsistent study inputs before numerical work or evidence claims."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel, ValidationError

from helioforge.engines import decision_studies as decision
from helioforge.engines import planning_studies as planning
from helioforge.engines import workflow_studies as workflow

if TYPE_CHECKING:
    from helioforge.engines.study_types import StudyModule


WEATHER_ASSET = {"name": "duplicate", "generation_mwh": 1, "weather_sensitivity": 0.5}
MERIT_ASSET = {
    "name": "duplicate",
    "variable_cost_eur_mwh": 1,
    "bilateral_value_eur_mwh": 2,
    "spot_value_eur_mwh": 2,
    "balancing_value_eur_mwh": 2,
}
TRANCHE_ROW = {
    "year": 1,
    "contracted_mwh": 1,
    "floor_eur_mwh": 10,
    "merchant_mwh": 1,
    "merchant_price_eur_mwh": 10,
    "opex_eur": 1,
}
OPERATING_YEAR = {"year": 2027, "generation_mwh": 1, "merchant_price_eur_mwh": 10, "opex_eur": 1}
CONTRACT = {"start_year": 2027, "end_year": 2029, "annual_volume_mwh": 1, "floor_price_eur_mwh": 10}
LINE = {"from_zone": 0, "to_zone": 1, "susceptance_mw_per_rad": 1, "limit_mw": 1}
PARETO = {
    "run_id": "duplicate",
    "scenario_key": "case",
    "sample_set_key": "samples",
    "horizon_hours": 24,
    "cost_eur": 1,
    "served_load_pct": 100,
    "storage_capacity_kwh": 10,
    "initial_soc_kwh": 5,
    "terminal_soc_kwh": 5,
    "expected_loss_of_load_hours": 0,
    "sample_count": 20,
}
ASSERTION = {"topic": "value", "statement": "Supplied value", "value": 1, "unit": "EUR", "source_ref": "test"}
DOCUMENT = {
    "document_id": "document-1",
    "kind": "tariff",
    "field_name": "tariff_eur_mwh",
    "unit": "EUR/MWh",
    "value": 10,
    "issued_on": "2026-01-01",
}
EVIDENCE = {"evidence_id": "duplicate", "likelihood_ratio": 2, "dependency_group": "meter", "note": "test"}


@pytest.mark.parametrize(
    ("model", "payload", "reason"),
    [
        (planning.AnnualStorageInput, {"import_price_eur_kwh": [1] * 25}, "Tariffs must contain"),
        (
            planning.AnnualStorageInput,
            {"import_price_eur_kwh": [0.04] * 24},
            "Import price must exceed export price",
        ),
        (
            planning.AnnualStorageInput,
            {"import_price_eur_kwh": [0.04] * 8760},
            "Import price must exceed export price",
        ),
        (planning.AnnualStorageInput, {"initial_soc_kwh": 0}, "Initial SOC must fall inside"),
        (planning.AnnualStorageInput, {"power_kw": 601}, "Battery power may not exceed"),
        (planning.AnnualStorageInput, {"grid_import_limit_kw": 0}, "No-battery baseline must be able"),
        (
            planning.ReliabilityInput,
            {"load_kw": [1] * 24, "renewable_kw": [1] * 25},
            "same horizon length",
        ),
        (planning.ReliabilityInput, {"initial_soc_kwh": 81}, "Initial SOC must fall inside"),
        (
            planning.ReliabilityInput,
            {"trials": 5000, "load_kw": [1] * 8760, "renewable_kw": [1] * 8760},
            "two million trial-hours",
        ),
        (planning.ReliabilityInput, {"annualization_hours": 8761}, "non-leap or leap calendar year"),
        (
            planning.CointegrationInput,
            {"gas_price_eur_mwh": [1] * 40, "carbon_price_eur_t": [1] * 40, "power_price_eur_mwh": [1] * 41},
            "aligned and equal length",
        ),
        (
            planning.CointegrationInput,
            {
                "gas_price_eur_mwh": [1] * 40,
                "carbon_price_eur_t": [1] * 40,
                "power_price_eur_mwh": [1] * 40,
                "training_fraction": 0.9,
            },
            "train/holdout split is too short",
        ),
        (
            planning.BacktestInput,
            {"gas_price_eur_mwh": [1] * 36, "carbon_price_eur_t": [1] * 36, "target_price_eur_mwh": [1] * 37},
            "aligned and equal length",
        ),
        (
            planning.BacktestInput,
            {
                "gas_price_eur_mwh": [1] * 36,
                "carbon_price_eur_t": [1] * 36,
                "target_price_eur_mwh": [1] * 36,
                "training_fraction": 0.5,
            },
            "training segment must contain at least 24",
        ),
        (planning.NetworkInput, {"zone_names": ["same"] * 6}, "Six unique zone names"),
        (
            planning.NetworkInput,
            {"lines": [{**LINE, "to_zone": 0}] * 5},
            "Network lines must connect distinct zones",
        ),
        (planning.NetworkInput, {"lines": [LINE] * 5}, "Parallel duplicate lines"),
        (
            planning.NetworkInput,
            {"lines": [{**LINE, "from_zone": i, "to_zone": (i + 1) % 5} for i in range(5)]},
            "six-zone network must be connected",
        ),
        (
            planning.ContractInput,
            {"operating_years": [OPERATING_YEAR] * 2, "debt_tenor_years": 1},
            "unique, consecutive calendar years",
        ),
        (planning.ContractInput, {"debt_tenor_years": 6}, "Debt tenor cannot exceed"),
        (
            planning.ContractInput,
            {"contracts": [{**CONTRACT, "end_year": 2026}]},
            "start year must be on or before",
        ),
        (planning.ContractInput, {"contracts": [CONTRACT, CONTRACT]}, "Overlapping contract terms"),
        (
            planning.ContractInput,
            {"contracts": [{**CONTRACT, "start_year": 2026}]},
            "Contract years must fall inside",
        ),
        (
            planning.RiskObservation,
            {
                "asset": "site",
                "metric": "load",
                "value": 1,
                "threshold": 1,
                "direction": "max",
                "unit": "kW",
                "observed_on": "2026-02-30",
            },
            "observed_on must be an ISO calendar date",
        ),
        (decision.WeatherInput, {"assets": [WEATHER_ASSET] * 6}, "Asset names must be unique"),
        (decision.MeritInput, {"bilateral_weight": 0.5}, "weights must sum to one"),
        (decision.MeritInput, {"assets": [MERIT_ASSET] * 2}, "Asset names must be unique"),
        (
            decision.CarbonInput,
            {"generation_mwh": [1], "marginal_factors_kgco2e_mwh": [1, 2], "sample_hours": 1},
            "arrays must have equal lengths",
        ),
        (
            decision.CarbonInput,
            {"generation_mwh": [1], "marginal_factors_kgco2e_mwh": [1]},
            "Sample hours cannot exceed",
        ),
        (decision.NegativeInput, {"suspension_duration_minutes": 16}, "whole number of 15-minute"),
        (
            decision.RegimesInput,
            {"initial_state_probabilities": [0.5, 0.5, 0.5]},
            "three probabilities summing to one",
        ),
        (
            decision.RegimesInput,
            {"transition_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 0]]},
            "Each transition-matrix row",
        ),
        (
            decision.CommoditiesInput,
            {"correlation_matrix": [[1, 0.1, 0], [0, 1, 0], [0, 0, 1]]},
            "symmetric and 3 by 3",
        ),
        (
            decision.CommoditiesInput,
            {"correlation_matrix": [[0.5, 0, 0], [0, 1, 0], [0, 0, 1]]},
            "diagonal entries must equal one",
        ),
        (
            decision.CommoditiesInput,
            {"correlation_matrix": [[1, 2, 0], [2, 1, 0], [0, 0, 1]]},
            "positive semidefinite",
        ),
        (
            decision.CommoditiesInput,
            {"correlation_matrix": [[1 + 1e-11, 0, 0], [0, 1, 0], [0, 0, 1]]},
            "between -1 and 1",
        ),
        (decision.TailInput, {"years": 1, "histogram_year": {"year": 2}}, "Histogram year cannot exceed"),
        (decision.SculptInput, {"finance_request": {"capex_eur": 1e12 + 1}}, "amounts are bounded at 1e12"),
        (decision.TranchesInput, {"contract_years": 11}, "Contract years cannot exceed debt tenor"),
        (decision.TranchesInput, {"annual_rows": [TRANCHE_ROW]}, "Provide annual cash-flow rows"),
        (
            decision.TranchesInput,
            {"annual_rows": [TRANCHE_ROW] * 2, "tenor_years": 2, "contract_years": 2},
            "unique consecutive years starting at one",
        ),
        (
            decision.WaterfallInput,
            {"catchup_share": 0.2, "sponsor_promote_share": 0.2},
            "Catch-up sponsor share must exceed",
        ),
        (
            workflow.DuckInput,
            {"load_kw": [1, 1], "solar_kw": [0, 0], "wind_kw": [0, 0, 0]},
            "arrays must have equal lengths",
        ),
        (
            workflow.DuckInput,
            {"load_kw": [100001, 1], "solar_kw": [0, 0], "wind_kw": [0, 0]},
            "bounded to 100,000 kW",
        ),
        (workflow.BlackstartInput, {"available_power_fraction": 0.1}, "at least the reserve fraction"),
        (workflow.ParetoCandidate, {**PARETO, "initial_soc_kwh": 11}, "SOC must be within storage capacity"),
        (
            workflow.ParetoCandidate,
            {**PARETO, "expected_loss_of_load_hours": 25},
            "cannot exceed the horizon",
        ),
        (workflow.ParetoInput, {"cost_weight": 0.5}, "weights must sum to one"),
        (workflow.ParetoInput, {"candidates": [PARETO] * 2}, "Candidate run IDs must be unique"),
        (workflow.DunkelflauteInput, {"load_kw": [100001] * 336}, "bounded to 100,000 kW"),
        (
            workflow.PhotogrammetryInput,
            {"design_points_xyz": [[1000001, 0, 0]], "asbuilt_points_xyz": [[0, 0, 0]]},
            "Coordinates are bounded",
        ),
        (
            workflow.DtsInput,
            {"samples": [{"distance_m": 1, "observed_at_hour": 1}, {"distance_m": 1, "observed_at_hour": 1}]},
            "distances must be strictly increasing",
        ),
        (
            workflow.DtsInput,
            {"samples": [{"distance_m": 1, "observed_at_hour": 11}]},
            "cannot be in the future",
        ),
        (workflow.OffgasInput, {"votes_required": 4}, "votes cannot exceed sensor count"),
        (
            workflow.OffgasInput,
            {"sensors": [{"sensor_id": "same", "co_ppm": 1}] * 2},
            "Sensor IDs must be unique",
        ),
        (
            workflow.OffgasInput,
            {"sensors": [{"sensor_id": "empty"}], "votes_required": 1},
            "at least one reading",
        ),
        (workflow.DebateInput, {"finance_evidence": [ASSERTION] * 2}, "assert a topic once"),
        (workflow.ManifestDocument, {**DOCUMENT, "issued_on": "2026-02-30"}, "valid ISO calendar dates"),
        (workflow.ManifestDocument, {**DOCUMENT, "expires_on": "2025-12-31"}, "Expiry cannot precede"),
        (workflow.ManifestPayload, {"as_of_date": "2026-02-30"}, "As-of date must be valid"),
        (workflow.ManifestPayload, {"documents": [DOCUMENT] * 2}, "document IDs must be unique"),
        (workflow.ConsensusInput, {"evidence": [EVIDENCE] * 2}, "Evidence IDs must be unique"),
    ],
)
def test_inconsistent_input_is_rejected_with_a_specific_contract_reason(
    model: type[BaseModel], payload: dict[str, object], reason: str
) -> None:
    with pytest.raises(ValidationError, match=reason):
        model.model_validate(payload)


@pytest.mark.parametrize(("import_hours", "export_hours"), [(24, 24), (24, 8760), (8760, 24), (8760, 8760)])
def test_daily_and_annual_tariff_inputs_preserve_the_declared_time_resolution(
    import_hours: int, export_hours: int
) -> None:
    payload = {
        "import_price_eur_kwh": [0.2] * import_hours,
        "export_price_eur_kwh": [0.1] * export_hours,
    }
    model = planning.AnnualStorageInput.model_validate(payload)
    assert model.import_price_eur_kwh == payload["import_price_eur_kwh"]
    assert model.export_price_eur_kwh == payload["export_price_eur_kwh"]


@pytest.mark.parametrize("module", [planning, decision, workflow])
def test_unknown_study_never_falls_through_to_a_default_solver(module: StudyModule) -> None:
    with pytest.raises(ValueError, match="Unknown"):
        module.run("unknown-study", {})


@pytest.mark.parametrize(("module", "study"), [(planning, "overview-risk"), (decision, "overview-carbon")])
def test_non_object_study_inputs_are_rejected(module: StudyModule, study: str) -> None:
    with pytest.raises(TypeError, match="JSON object"):
        module.run(study, [])
