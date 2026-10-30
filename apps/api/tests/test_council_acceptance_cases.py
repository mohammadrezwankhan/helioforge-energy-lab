"""Focused acceptance regressions for deterministic council evidence checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from helioforge.council import local_council
from helioforge.schemas import CouncilRequest


def _digest(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _record(*, result: dict | None = None, metadata: dict | None = None) -> dict:
    inputs = {"market": "FR", "capacity_kwh": 10000.0}
    return {
        "run_id": "synthetic-run-01",
        "kind": "storage",
        "created_at": "2026-10-28T12:00:00+00:00",
        "input_sha256": _digest(inputs),
        "inputs": inputs,
        "result": {
            "model": "btm-milp-v1",
            "duration_hours": 24.0,
            "capacity_kwh": 10000.0,
            "power_kw": 5000.0,
            "terminal_soc_kwh": 5000.0,
            **(result or {}),
        },
        "metadata": {"as_of": "2026-10-29T12:00:00+00:00", **(metadata or {})},
    }


def _review(record: dict | None = None) -> dict:
    evidence = {
        "dispatch": {
            "duration_hours": 24.0,
            "solver_status": "optimal",
            "terminal_soc_kwh": 5000.0,
        },
        "finance": {
            "npv_eur": 1000.0,
            "irr_pct": None,
            "minimum_dscr": None,
        },
        "sustainability": {"model": "carbon-screen-v1"},
        "supplied_records": [] if record is None else [record],
    }
    return local_council(CouncilRequest(), evidence)


def test_local_council_marks_no_evidence_and_does_not_claim_a_critic():
    result = _review()

    assert result["protocol_metadata"]["limits"]["executed_specialist_count"] == 0
    assert result["protocol_metadata"]["limits"]["executed_critic_count"] == 0
    assert result["protocol_metadata"]["integrity"]["critic_signoff"] is False
    assert result["protocol_metadata"]["integrity"]["human_approval_recorded"] is False
    assert result["evidence_review"]["status"] == "checklist_only"
    assert "no_attached_evidence" in {x["code"] for x in result["evidence_review"]["findings"]}
    assert "not investment approval" in result["decision"]["recommendation"].lower()


def test_digest_mismatch_is_reported_as_integrity_warning_not_authenticity_judgment():
    record = _record()
    record["inputs"]["capacity_kwh"] = 12000.0
    result = _review(record)

    checked = result["evidence_review"]["records"][0]
    assert checked["digest_status"] == "mismatch"
    assert "digest_mismatch" in checked["finding_codes"]
    assert result["protocol_metadata"]["integrity"]["evidence_authenticity_verified"] is False
    reproducibility = next(x for x in result["reviews"] if x["agent"] == "Reproducibility reviewer")
    assert any("sha-256" in item.lower() for item in reproducibility["risks"])


def test_missing_schema_fields_and_declared_invalid_units_are_role_scoped():
    record = _record(
        result={"duration_hours": None, "capacity_kwh": None, "power_kw": None},
        metadata={"units": {"capacity_kwh": "MWh", "power_kw": "kW"}},
    )
    result = _review(record)

    findings = result["evidence_review"]["records"][0]["finding_codes"]
    assert "missing_or_invalid_result_fields" in findings
    assert "invalid_declared_unit" in findings
    storage = next(x for x in result["reviews"] if x["agent"] == "Storage engineer")
    assert any("unit labels" in item.lower() for item in storage["required_evidence"])


def test_explicit_version_expiry_and_horizon_conflicts_are_reported():
    record = _record(metadata={
        "expected_model": "btm-milp-v2",
        "valid_until": "2026-10-01T00:00:00+00:00",
        "expected_horizon_hours": 48.0,
    })
    result = _review(record)

    codes = set(result["evidence_review"]["records"][0]["finding_codes"])
    assert {"model_version_mismatch", "expired_validity", "horizon_mismatch"} <= codes


def test_old_timestamp_is_not_called_stale_without_an_explicit_expiry():
    record = _record(metadata={"as_of": "2026-10-29T12:00:00+00:00"})
    record["created_at"] = "2000-01-01T00:00:00+00:00"
    result = _review(record)

    codes = set(result["evidence_review"]["records"][0]["finding_codes"])
    assert "expired_validity" not in codes
    assert "model_version_mismatch" not in codes


def test_malformed_record_and_unavailable_raw_inputs_are_not_called_verified():
    malformed = {"run_id": "synthetic-malformed", "kind": "storage", "input_sha256": "bad", "result": "not-an-object"}
    result = _review(malformed)

    checked = result["evidence_review"]["records"][0]
    assert {"malformed_result", "missing_or_invalid_result_fields", "malformed_input_digest"} <= set(checked["finding_codes"])
    ordinary_route_record = _record()
    ordinary_route_record.pop("inputs")
    route_result = _review(ordinary_route_record)
    route_checked = route_result["evidence_review"]["records"][0]
    assert route_checked["digest_status"] == "unverifiable_missing_inputs"
    assert "digest_unverifiable_without_inputs" in route_checked["finding_codes"]


def test_sensitive_label_and_provider_failure_are_not_echoed_or_promoted():
    marker = "SYNTHETIC_SENSITIVE_MARKER_DO_NOT_ECHO"
    record = _record(result={"notes": marker}, metadata={
        "classification": "sensitive_fixture",
        "provider_status": "failed",
    })
    result = _review(record)
    serialized = json.dumps(result)

    assert marker not in serialized
    codes = set(result["evidence_review"]["records"][0]["finding_codes"])
    assert {"sensitivity_label_present", "provider_failure_recorded"} <= codes
    assert result["execution"] == "deterministic_rule_based"
    assert result["protocol_metadata"]["limits"]["expected_runner_invocations"] == 0
    assert "critic" not in " ".join(x["agent"].lower() for x in result["reviews"])


def test_reproducibility_and_undefined_metrics_are_stated_without_overclaim():
    result = _review()
    investment = next(x for x in result["reviews"] if x["agent"] == "Investment analyst")
    reproducibility = next(x for x in result["reviews"] if x["agent"] == "Reproducibility reviewer")

    assert "IRR is not defined (null)" in investment["summary"]
    assert "minimum DSCR is not applicable (null)" in investment["summary"]
    assert "not established" in reproducibility["summary"].lower()
    assert "does not authenticate" in reproducibility["summary"].lower()


def test_acceptance_runner_accounts_for_all_126_requested_and_63_external_rows():
    repo_root = Path(__file__).resolve().parents[3]
    runner_path = repo_root / "scripts" / "acceptance-council-cases.py"
    spec = importlib.util.spec_from_file_location("acceptance_council_cases", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    report = runner.build_acceptance_results(repo_root)

    assert report["case_counts"] == {
        "total_design_rows": 189,
        "public_preview": 63,
        "local_deterministic": 63,
        "local_external_opt_in": 63,
        "requested_public_and_local": 126,
    }
    assert report["requested_case_status_counts"] == {
        "NOT_APPLICABLE_ABSENT_CRITIC": 14,
        "PASS_FIXED_CHECKLIST_AND_METADATA_CHECKS": 56,
        "PARTIAL_STATIC_CONTRACT_ONLY": 56,
    }
    assert report["all_case_status_counts"]["BLOCKED_LIVE_PROVIDER_ACCEPTANCE"] == 63
    assert report["environment"]["live_provider_calls"] == 0
    local_tampered = next(x for x in report["cases"] if x["test_id"] == "ROLE-010")
    assert local_tampered["evidence_class"] == "O"
    assert local_tampered["actual"]["evidence_state_check_ok"] is True
    assert local_tampered["actual"]["evidence_state_codes"] == ["digest_mismatch"]
    local_critic = next(x for x in report["cases"] if x["role"] == "Independent critic" and x["mode"] == "local_deterministic")
    assert local_critic["status"] == "NOT_APPLICABLE_ABSENT_CRITIC"
    external = next(x for x in report["cases"] if x["mode"] == "local_external_opt_in")
    assert external["actual"]["live_provider_call"] is False
    assert external["evidence_class"] == "P"
    public = next(x for x in report["cases"] if x["mode"] == "public_preview")
    assert public["evidence_class"] == "R"
