"""Operational failure and evidence-state contracts for decision workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import Mock

import numpy as np
import pytest

from helioforge.engines import decision_studies as decision
from helioforge.engines import planning_studies as planning
from helioforge.engines import workflow_studies as workflow

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass(frozen=True)
class SolverOutcome:
    """Explicit external optimizer response fixture for failure-contract tests."""

    success: bool = False
    status: int = 0
    x: NDArray[np.float64] | None = None
    fun: float | None = None
    mip_gap: float = 0.0
    message: str = "fixture solver failure"


@pytest.mark.parametrize(
    ("payload", "reason", "state"),
    [
        (
            {"steps": [{"action": "start_gfm", "label": "too much power", "active_kw": 1000}]},
            "active power plus inrush exceeds post-reserve budget",
            "dark",
        ),
        (
            {"inrush_budget_kw": 1, "steps": [{"action": "start_gfm", "label": "inrush", "inrush_kw": 2}]},
            "inrush exceeds configured exercise budget",
            "dark",
        ),
        (
            {
                "steps": [
                    {"action": "start_gfm", "label": "start"},
                    {"action": "start_gfm", "label": "repeat"},
                ]
            },
            "source can start only from dark state",
            "grid_forming_ready",
        ),
        (
            {"steps": [{"action": "connect_load", "label": "load before energization"}]},
            "load connection requires an energized bus",
            "dark",
        ),
    ],
)
def test_rejected_blackstart_step_preserves_the_preceding_safe_state(
    payload: dict[str, object], reason: str, state: str
) -> None:
    result = workflow.run("lessons-blackstart", payload)
    rejected = result["table"][-1]
    assert rejected["accepted"] is False
    assert rejected["reason"] == reason
    assert rejected["state_after"] == state


def test_debate_keeps_unpaired_and_unit_conflicting_evidence_unresolved() -> None:
    claim = {"statement": "Supplied claim", "value": 10, "unit": "EUR", "source_ref": "test"}
    result = workflow.run(
        "council-debate",
        {
            "capex_eur": 100,
            "annual_net_value_eur": 10,
            "life_years": 5,
            "discount_rate_fraction": 0,
            "finance_evidence": [
                {**claim, "topic": "finance_only"},
                {**claim, "topic": "units"},
                {**claim, "topic": "agreed"},
            ],
            "storage_evidence": [
                {**claim, "topic": "storage_only"},
                {**claim, "topic": "units", "unit": "kWh"},
                {**claim, "topic": "agreed"},
            ],
        },
    )
    assert result["metrics"][0]["value"] == -50
    statuses = {row["topic"]: row["status"] for row in result["table"]}
    assert statuses == {
        "finance_only": "unpaired",
        "units": "unit_mismatch_disputed",
        "agreed": "convergent_within_declared_tolerance",
        "storage_only": "unpaired",
    }
    assert all(
        row["resolution"] == "unresolved; evidence persists for human review" for row in result["table"]
    )


@pytest.mark.parametrize(
    ("overrides", "expected_issue"),
    [
        ({"field_name": "wrong_field"}, "field_name_mismatch"),
        ({"unit": "kWh"}, "unit_mismatch"),
        ({"issued_on": "2027-01-01"}, "issued_in_future"),
        ({"issued_on": "2000-01-01"}, "manifest_too_old"),
        ({"expires_on": "2026-02-01"}, "expired"),
        ({"issuer": None}, "provenance_missing"),
        ({"source_reference": None}, "provenance_missing"),
        ({"value": 2001}, "value_out_of_bounds"),
        (
            {"kind": "warranty", "field_name": "warranty_years", "unit": "year", "value": 51},
            "value_out_of_bounds",
        ),
        (
            {"kind": "single_line", "field_name": "node_count", "unit": "count", "value": 10.5},
            "value_out_of_bounds_or_non_integer",
        ),
    ],
)
def test_document_metadata_findings_require_review_without_authenticating_content(
    overrides: dict[str, object], expected_issue: str
) -> None:
    document = {
        "document_id": "review-me",
        "kind": "tariff",
        "field_name": "tariff_eur_mwh",
        "unit": "EUR/MWh",
        "value": 10,
        "issued_on": "2026-01-01",
        "issuer": "Example issuer",
        "source_reference": "test:record",
        **overrides,
    }
    result = workflow.run("council-evidence", {"manifest": {"documents": [document]}})
    assert result["table"][0]["status"] == "review"
    assert result["table"][0]["issues"] == [expected_issue]
    assert result["details"]["authenticity_checked"] is False
    assert result["details"]["ocr_used"] is False


def test_adverse_evidence_lowers_bayesian_probability_without_changing_total_mass() -> None:
    result = workflow.run(
        "council-consensus",
        {
            "prior_probability": 0.1,
            "evidence": [
                {
                    "evidence_id": "negative",
                    "likelihood_ratio": 0.5,
                    "dependency_group": "one",
                    "note": "test",
                }
            ],
        },
    )
    assert result["details"]["hypothesis_probability"] == pytest.approx(1 / 19, rel=1e-12, abs=1e-15)
    assert result["details"]["probability_sum"] == 1


@pytest.mark.parametrize("stage", [1, 2])
def test_dunkelflaute_solver_failure_never_emits_a_dispatch_result(
    monkeypatch: pytest.MonkeyPatch, stage: int
) -> None:
    failed = SolverOutcome(success=False, message="solver unavailable")
    # A zero-load/zero-SOC first-stage solution is physically feasible. It lets
    # the second-stage failure be tested without claiming an optimal dispatch.
    feasible_zero_load = SolverOutcome(success=True, x=np.zeros(6 * 336 + 1))
    solver = Mock(side_effect=[failed] if stage == 1 else [feasible_zero_load, failed])
    monkeypatch.setattr(workflow, "milp", solver)
    reason = "336-hour dispatch MILP failed" if stage == 1 else "336-hour dispatch tie-break MILP failed"
    with pytest.raises(RuntimeError, match=reason):
        workflow.run(
            "compare-dunkelflaute",
            {"load_kw": [0] * 336, "renewable_kw": [0] * 336, "initial_soc_kwh": 0},
        )
    assert solver.call_count == stage


@pytest.mark.parametrize(
    ("result", "reason"),
    [
        (
            SolverOutcome(status=1, x=None, fun=None, message="time limit"),
            "did not prove an optimal schedule",
        ),
        (
            SolverOutcome(status=0, x=np.zeros(1), fun=0, mip_gap=0.1),
            "no requested optimality proof",
        ),
        (
            SolverOutcome(status=0, x=np.zeros(1), fun=0, mip_gap=float("nan")),
            "no requested optimality proof",
        ),
    ],
)
def test_annual_dispatch_requires_an_actual_finite_zero_gap_optimality_proof(
    monkeypatch: pytest.MonkeyPatch, result: SolverOutcome, reason: str
) -> None:
    monkeypatch.setattr(planning, "milp", Mock(return_value=result))
    with pytest.raises(ValueError, match=reason):
        planning.run("storage-annualopt", {})


def test_network_with_insufficient_generation_reports_infeasibility() -> None:
    with pytest.raises(ValueError, match="Six-zone DC-OPF failed"):
        planning.run("markets-network", {"generator_capacity_mw": [0] * 6})


def test_constant_price_histories_do_not_claim_an_identified_cointegration_model() -> None:
    with pytest.raises(ValueError, match="do not identify a stable rank-one"):
        planning.run(
            "forecast-cointegration",
            {
                "gas_price_eur_mwh": [1] * 100,
                "carbon_price_eur_t": [1] * 100,
                "power_price_eur_mwh": [1] * 100,
            },
        )


def test_missing_spatial_correspondences_do_not_report_a_registration_transform() -> None:
    with pytest.raises(ValueError, match="Fewer than three point pairs"):
        planning.run(
            "pilots-registration",
            {
                "design_points_xyz": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                "survey_points_xyz": [[0, 0, 0], [100, 0, 0], [0, 100, 0]],
                "maximum_correspondence_distance_m": 0.001,
            },
        )


def test_debt_request_above_capex_is_reported_as_capped() -> None:
    result = decision.run("investment-sculpt", {"requested_debt_eur": 100_000_000})
    assert "Requested debt was capped at project CAPEX." in result["warnings"]
