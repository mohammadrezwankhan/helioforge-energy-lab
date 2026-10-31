"""Verify the dated 59-study acceptance artifact is complete and evidence-backed."""
from __future__ import annotations

import json
from pathlib import Path

from helioforge.engines.workflow_studies import run as run_workflow_study
from helioforge.studies import catalogue

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "remediation-20261029" / "study-contracts.json"
CHECKS = {"default_contract", "boundary_case", "invalid_input", "repeatability", "json_export", "solver_feasibility"}


def test_thermal_comparison_matches_single_regime_hand_calculation():
    result = run_workflow_study("compare-thermal", {
        "reference_temperature_c": 20,
        "temperature_factor_per_c": 0,
        "screening_loss_fraction_per_1000_efc": 0.1,
        "years": 1,
        "regimes": [{
            "regime": "hand case",
            "utilization_fraction": 1,
            "cycles_per_day_at_full_utilization": 1,
            "depth_of_discharge_fraction": 1,
            "ambient_temperature_c": 20,
        }],
    })
    row = result["table"][0]
    assert row["equivalent_full_cycles"] == 365
    assert row["thermal_multiplier"] == 1
    assert row["screening_wear_index_pct"] == 3.65


def test_study_acceptance_artifact_has_per_id_oracles_and_actual_outcomes():
    assert REPORT.is_file(), "generate the numerical acceptance artifact with scripts/acceptance-study-contracts.py"
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    expected_ids = {item["id"] for item in catalogue()}
    records = report["studies"]

    assert report["study_count"] == 59
    assert len(records) == len(expected_ids) == 59
    assert {record["study_id"] for record in records} == expected_ids
    assert report["status_counts"] == {"PASS": 59, "FAIL": 0}

    for record in records:
        assert record["status"] in {"PASS", "FAIL"}
        assert record["test_ids"]
        assert all(test["status"] == "PASS" for test in record["test_ids"])
        assert record["oracle"]["expected"]
        assert record["oracle"]["actual"] is not None
        assert record["oracle"]["actual"]["observed_cases"], "capture actual results from the linked acceptance case"
        assert record["oracle"]["units"]
        assert record["oracle"]["evidence_class"] in {
            "independent_software_oracle"
        }
        assert record["source_hashes"]["engine_sha256"]
        assert record["source_hashes"]["test_sha256"]
        assert CHECKS <= set(record["checks"])
        for check_name in CHECKS:
            check = record["checks"][check_name]
            assert check["status"] in {"PASS", "FAIL", "NOT_APPLICABLE"}
            if check["status"] == "NOT_APPLICABLE":
                assert check["reason"]
        assert record["uncovered_conditions"], "state the scientific/operational limit for each study"

