"""Execute bounded deterministic council acceptance cases; never calls a provider."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from helioforge.council import local_council
from helioforge.council_protocol import PROTOCOL_ID
from helioforge.dashboard import dashboard
from helioforge.schemas import CouncilRequest

DESIGN_CSV = Path("docs/remediation-20261028/source-plan/council_role_test_design.csv")
EVIDENCE_STATES = (
    "no_evidence", "valid_synthetic", "tampered", "stale_version", "contradictory",
    "sensitive_fixture", "provider_failure",
)
MODES = ("public_preview", "local_deterministic", "local_external_opt_in")
ROLE_NAMES = {
    "Storage engineering": "Storage engineer",
    "Investment analysis": "Investment analyst",
    "Market evidence": "Market reviewer",
    "Sustainability": "Sustainability reviewer",
    "Hybrid architecture": "Hybrid architect",
    "Learning design": "Learning designer",
    "Accessibility": "Accessibility reviewer",
    "Reproducibility": "Reproducibility reviewer",
}
PREVIEW_CONTRACTS = {
    "bundled_local_checklist": "No LLM or independent agent is executed in local mode",
    "local_preflight_zero_calls": "0 external Runner.run invocations",
    "no_critic_execution": "No critic invocation",
    "hash_is_not_authority": "content identifier only",
    "approval_fields_disclosed": "Human approval recorded:",
    "identity_fields_disclosed": "Reviewer identity verified:",
    "source_authenticity_fields_disclosed": "Evidence authenticity verified:",
    "signature_fields_disclosed": "Signature verified:",
}
ROLE_EXPECTATIONS = {
    "Storage engineering": ("synthetic", "terminal soc", "annual value"),
    "Investment analysis": ("npv eur", "not investment approval"),
    "Market evidence": ("source link", "no approved tariff or regulatory determination"),
    "Sustainability": ("separate evidence streams", "no carbon credits"),
    "Hybrid architecture": ("structural illustrations", "not dynamic specialist studies"),
    "Learning design": ("none is an accredited qualification", "not independently verified mastery"),
    "Accessibility": ("assistive-technology testing", "has not inspected a browser"),
    "Reproducibility": ("not established", "does not authenticate source"),
}
MOCKED_EXTERNAL_TESTS = [
    "test_external_mode_disabled_by_default",
    "test_external_mode_requires_admin_and_consent",
    "test_external_mode_requires_server_credentials",
    "test_external_provider_error_is_not_a_fake_local_success",
    "test_external_timeout_is_marked_with_protocol_and_no_record",
    "test_eight_concurrent_specialists_then_cross_examination_then_critic",
    "test_two_cross_examination_rounds_have_twenty_five_runner_invocations",
    "test_provider_failure_cancels_sibling_reviews",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_digest(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _fixture_record(state: str) -> dict | None:
    if state == "no_evidence":
        return None
    inputs = {"market": "FR", "capacity_kwh": 10000.0, "fixture_state": state}
    result = {
        "model": "btm-milp-v1",
        "data_kind": "synthetic",
        "duration_hours": 24.0,
        "capacity_kwh": 10000.0,
        "power_kw": 5000.0,
        "terminal_soc_kwh": 5000.0,
    }
    metadata = {
        "expected_model": "btm-milp-v1",
        "expected_horizon_hours": 24.0,
        "expected_data_kind": "synthetic",
        "units": {"duration_hours": "h", "capacity_kwh": "kWh", "power_kw": "kW",
                  "terminal_soc_kwh": "kWh"},
        "as_of": "2026-10-29T12:00:00+00:00",
    }
    if state == "stale_version":
        metadata["expected_model"] = "btm-milp-v0"
        metadata["valid_until"] = "2026-10-01T00:00:00+00:00"
    elif state == "contradictory":
        metadata["expected_horizon_hours"] = 48.0
    elif state == "sensitive_fixture":
        metadata["classification"] = "sensitive_fixture"
        result["notes"] = "SYNTHETIC_SENSITIVE_FIXTURE_MARKER_DO_NOT_ECHO"
    elif state == "provider_failure":
        metadata["provider_status"] = "failed"

    digest = _canonical_digest(inputs)
    if state == "tampered":
        inputs["capacity_kwh"] = 12000.0  # Controlled mutation after the stored digest was computed.
    return {
        "run_id": f"synthetic-{state}", "kind": "storage",
        "created_at": "2026-10-28T12:00:00+00:00", "input_sha256": digest,
        "inputs": inputs, "result": result, "metadata": metadata,
    }


def _preview_contract(root: Path) -> dict:
    bundle_path = root / "apps" / "web" / "dist" / "app.js"
    bundle = bundle_path.read_text(encoding="utf-8") if bundle_path.exists() else ""
    checks = {name: marker in bundle for name, marker in PREVIEW_CONTRACTS.items()}
    source_checks = {
        "local_mode_label": "Local · deterministic checklist" in (root / "apps/web/src/views.ts").read_text(encoding="utf-8"),
        "preflight_discloses_no_provider": "no brief or evidence is sent to a provider" in (root / "apps/web/src/integrations-ui.ts").read_text(encoding="utf-8"),
        "markdown_export_names_authority_limits": "does not verify source, signer, scientific validity, or approval" in (root / "apps/web/src/app.ts").read_text(encoding="utf-8"),
    }
    return {
        "bundle_path": str(bundle_path.relative_to(root)),
        "bundle_exists": bundle_path.exists(),
        "bundle_checks": checks,
        "source_checks": source_checks,
        "all_static_contract_checks_pass": bool(checks) and all(checks.values()) and all(source_checks.values()),
        "evidence_state_injection_available": False,
        "interpretation": (
            "This is a source and shipped-bundle contract inspection. Public-preview evidence-state variants cannot be injected "
            "through this static snapshot, so those row states are not behaviorally exercised here."
        ),
    }


def _role_result(role: str, result: dict) -> dict:
    if role == "Independent critic":
        has_critic = any("critic" in review["agent"].lower() for review in result["reviews"])
        return {"status": "NOT_APPLICABLE_ABSENT_CRITIC" if not has_critic else "UNEXPECTED_CRITIC",
                "observed": "No critic review is executed in local mode." if not has_critic else "A critic-shaped review was returned.",
                "required_conditions": ["No independent critic execution or signoff is claimed."],
                "conditions_met": not has_critic}

    review_name = ROLE_NAMES[role]
    review = next((item for item in result["reviews"] if item["agent"] == review_name), None)
    if review is None:
        return {"status": "ROLE_SECTION_MISSING", "observed": "No matching fixed checklist section returned.",
                "required_conditions": list(ROLE_EXPECTATIONS[role]), "conditions_met": False}
    corpus = " ".join([review["summary"], *review["risks"], *review["required_evidence"],
                       result["decision"]["recommendation"]]).lower()
    conditions = ROLE_EXPECTATIONS[role]
    met = all(condition in corpus for condition in conditions)
    return {
        "status": "CHECKLIST_CONDITIONS_MET" if met else "CHECKLIST_CONDITIONS_PARTIAL",
        "observed_section": review_name,
        "required_conditions": list(conditions),
        "conditions_met": met,
        "actual_summary": review["summary"],
        "risk_count": len(review["risks"]),
        "required_evidence_count": len(review["required_evidence"]),
    }


def build_acceptance_results(root: Path = ROOT) -> dict:
    csv_path = root / DESIGN_CSV
    with csv_path.open(newline="", encoding="utf-8") as stream:
        specifications = list(csv.DictReader(stream))
    mode_counts = Counter(row["mode"] for row in specifications)
    if len(specifications) != 189 or mode_counts != Counter({mode: 63 for mode in MODES}):
        raise ValueError(f"Unexpected council design matrix: {len(specifications)} rows, {dict(mode_counts)}")
    if len({row["test_id"] for row in specifications}) != len(specifications):
        raise ValueError("Council design matrix contains duplicate test IDs.")

    preview = _preview_contract(root)
    baseline = dashboard("FR")
    local_rows = [row for row in specifications if row["mode"] == "local_deterministic"]
    public_rows = [row for row in specifications if row["mode"] == "public_preview"]
    external_rows = [row for row in specifications if row["mode"] == "local_external_opt_in"]
    results: list[dict] = []

    for row in local_rows:
        case_state = row["evidence_state"]
        evidence = {key: deepcopy(baseline[key]) for key in ("dispatch", "finance", "sustainability")}
        record = _fixture_record(case_state)
        evidence["supplied_records"] = [] if record is None else [record]
        result = local_council(CouncilRequest(mode="local", market="FR"), evidence)
        protocol = result["protocol_metadata"]
        limits = protocol["limits"]
        protocol_ok = (
            protocol["id"] == PROTOCOL_ID and protocol["mode"] == "local" and
            protocol["external_execution_status"] == "not_requested" and
            limits["expected_runner_invocations"] == 0 and
            limits["completed_runner_invocations"] == 0 and
            limits["executed_specialist_count"] == 0 and
            limits["executed_critic_count"] == 0 and
            limits["local_checklist_section_count"] == 8 and
            result["execution"] == "deterministic_rule_based" and len(result["reviews"]) == 8
        )
        evidence_review = result["evidence_review"]
        records = evidence_review["records"]
        codes = {code for checked in records for code in checked["finding_codes"]}
        codes.update(finding["code"] for finding in evidence_review["findings"])
        expected_state_code = {
            "no_evidence": "no_attached_evidence",
            "valid_synthetic": None,
            "tampered": "digest_mismatch",
            "stale_version": "model_version_mismatch",
            "contradictory": "horizon_mismatch",
            "sensitive_fixture": "sensitivity_label_present",
            "provider_failure": "provider_failure_recorded",
        }[case_state]
        state_check_ok = (
            (case_state == "valid_synthetic" and records and records[0]["digest_status"] == "matches_supplied_inputs" and not codes) or
            (case_state != "valid_synthetic" and expected_state_code in codes)
        )
        role_result = _role_result(row["role"], result)
        critic_na = role_result["status"] == "NOT_APPLICABLE_ABSENT_CRITIC"
        status = (
            "NOT_APPLICABLE_ABSENT_CRITIC" if critic_na else
            "PASS_FIXED_CHECKLIST_AND_METADATA_CHECKS"
            if protocol_ok and state_check_ok and role_result["conditions_met"] else
            "PARTIAL_OR_FAILED_EXPECTATION"
        )
        serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
        fixture_not_echoed = "SYNTHETIC_SENSITIVE_FIXTURE_MARKER_DO_NOT_ECHO" not in serialized
        if case_state == "sensitive_fixture" and not fixture_not_echoed:
            status = "FAIL_SENSITIVE_FIXTURE_ECHOED"
        results.append({
            **row,
            "status": status,
            "evidence_class": "O",
            "actual": {
                "mode": "local_deterministic",
                "protocol_ok": protocol_ok,
                "evidence_state_check_ok": state_check_ok,
                "evidence_state_codes": sorted(codes),
                "digest_status": records[0]["digest_status"] if records else "not_applicable_no_record",
                "role_result": role_result,
                "fixed_checklist_only": evidence_review["status"] == "checklist_only",
                "critic_execution": evidence_review["critic_execution"],
                "sensitive_fixture_not_echoed": fixture_not_echoed,
                "claims": "These are deterministic metadata/result-shape checks and fixed checklist text, not evidence-role analysis or scientific validation.",
            },
        })

    for row in public_rows:
        if row["role"] == "Independent critic":
            status = "NOT_APPLICABLE_ABSENT_CRITIC"
        else:
            status = "PARTIAL_STATIC_CONTRACT_ONLY" if preview["all_static_contract_checks_pass"] else "STATIC_CONTRACT_FAILED"
        results.append({
            **row,
            "status": status,
            "evidence_class": "R",
            "actual": {
                "mode": "public_preview_static_bundle",
                "static_contract_checks_pass": preview["all_static_contract_checks_pass"],
                "evidence_state_exercised": False,
                "evidence_state_blocker": "The static public snapshot has no evidence-state injection interface.",
                "role_result": "Eight fixed sections are displayed; no reviewer or critic is executed by this source inspection.",
                "claims": "Public bundle contract only. This does not pass role/evidence behavior for the selected CSV evidence state.",
            },
        })

    for row in external_rows:
        results.append({
            **row,
            "status": "BLOCKED_LIVE_PROVIDER_ACCEPTANCE",
            "evidence_class": "P",
            "actual": {
                "mode": "local_external_opt_in",
                "live_provider_call": False,
                "status": "Not started without provider-enabled config, server credentials and explicit consent.",
                "mocked_provider_tests": MOCKED_EXTERNAL_TESTS,
                "claims": "Mocked orchestration and failure behavior are tested separately; this row does not claim real-provider compatibility, billing, source analysis, critic authority, or human approval.",
            },
        })

    results.sort(key=lambda case: case["test_id"])
    status_counts = Counter(case["status"] for case in results)
    requested = [case for case in results if case["mode"] in {"public_preview", "local_deterministic"}]
    requested_status_counts = Counter(case["status"] for case in requested)
    hash_paths = [
        DESIGN_CSV,
        Path("apps/api/helioforge/council.py"),
        Path("apps/api/helioforge/council_protocol.py"),
        Path("apps/api/tests/test_council_acceptance_cases.py"),
        Path("apps/api/tests/test_council.py"),
        Path("apps/api/tests/test_api.py"),
        Path("scripts/acceptance-council-cases.py"),
        Path("docs/COUNCIL_PROTOCOL.md"),
        Path("apps/web/src/app.ts"),
        Path("apps/web/src/views.ts"),
        Path("apps/web/src/integrations-ui.ts"),
        Path("apps/web/dist/app.js"),
    ]
    source_hashes = {str(path).replace("\\", "/"): _sha256(root / path)
                     for path in hash_paths if (root / path).is_file()}
    return {
        "title": "HelioForge council acceptance follow-up",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "design_source": str(DESIGN_CSV).replace("\\", "/"),
        "design_source_sha256": _sha256(csv_path),
        "case_counts": {"total_design_rows": len(specifications), "public_preview": len(public_rows),
                        "local_deterministic": len(local_rows), "local_external_opt_in": len(external_rows),
                        "requested_public_and_local": len(requested)},
        "requested_case_status_counts": dict(sorted(requested_status_counts.items())),
        "all_case_status_counts": dict(sorted(status_counts.items())),
        "interpretation": {
            "evidence_class_key": {
                "O": "Observed controlled execution of the real local deterministic council code.",
                "R": "Read-only inspection of the public static source and shipped bundle.",
                "P": "Blocked; no live provider call was made.",
                "U": "Unverified: scientific validity, source authenticity, human approval, and actual provider charges.",
            },
            "public_preview": "Static bundle checks are partial and evidence-state specific behavior is not executable without an injection interface.",
            "local_deterministic": "The real local_council function was called once per CSV row with controlled synthetic fixtures; its fixed sections and bounded metadata checks are reported separately.",
            "external": "All 63 live-provider acceptance rows are blocked by design; no API key or provider call was used.",
            "scientific_and_human_review": "Scientific validation, source authentication, legal approval, human approval and provider billing review remain separate and unclaimed.",
        },
        "public_preview_contract": preview,
        "mocked_external_coverage": {
            "live_provider_call": False,
            "tests_to_run_separately": MOCKED_EXTERNAL_TESTS,
            "note": "These named local tests use a fake SDK or API gate and do not establish actual provider behavior.",
        },
        "environment": {
            "python": platform.python_version(),
            "executable": sys.executable,
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "live_provider_calls": 0,
        },
        "source_sha256": source_hashes,
        "cases": results,
    }


def _write_artifacts(report: dict, root: Path) -> Path:
    directory = root / "docs" / "remediation-20261029"
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "council-results.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return json_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--no-write", action="store_true", help="Print a status summary without writing the requested artifacts.")
    args = parser.parse_args()
    report = build_acceptance_results(args.root.resolve())
    if not args.no_write:
        json_path = _write_artifacts(report, args.root.resolve())
        print(f"Wrote {json_path}")
    print(json.dumps({
        "case_counts": report["case_counts"],
        "requested_case_status_counts": report["requested_case_status_counts"],
        "all_case_status_counts": report["all_case_status_counts"],
        "live_provider_calls": 0,
    }, indent=2))
    local_failures = report["all_case_status_counts"].get("PARTIAL_OR_FAILED_EXPECTATION", 0)
    return 0 if report["public_preview_contract"]["all_static_contract_checks_pass"] and not local_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
