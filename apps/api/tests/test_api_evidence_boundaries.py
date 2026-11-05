"""Consent, bounded evidence, and truthful API failure states without live I/O."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from helioforge import main
from helioforge.council import inspect_supplied_evidence
from helioforge.schemas import PVRequest, StorageRequest
from helioforge.store import Store


@pytest.fixture
def boundary_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "boundaries.sqlite3"))
    monkeypatch.setenv("ENABLE_OPENAI", "false")
    with TestClient(main.app, base_url="http://127.0.0.1") as client:
        yield client


@pytest.mark.parametrize(
    ("endpoint", "provider_name", "payload"),
    [
        ("weather", "weather", {}),
        ("market", "market_prices", {"date": "2026-01-01"}),
        ("regulatory", "regulatory_feed", {}),
    ],
)
def test_external_connector_requires_consent_before_provider_call_or_storage(
    boundary_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    provider_name: str,
    payload: dict[str, object],
) -> None:
    provider = AsyncMock(return_value={"fixture": "no network request", "data_kind": "test_fixture"})
    monkeypatch.setattr(main, provider_name, provider)

    denied = boundary_client.post(f"/api/connectors/{endpoint}", json=payload)
    assert denied.status_code == 403
    provider.assert_not_awaited()
    assert boundary_client.get("/api/runs").json() == []

    allowed = boundary_client.post(f"/api/connectors/{endpoint}", json={**payload, "consent": True})
    assert allowed.status_code == 200
    assert allowed.json()["fixture"] == "no network request"
    provider.assert_awaited_once()
    assert len(boundary_client.get("/api/runs").json()) == 1
    saved = boundary_client.get(f"/api/runs/{allowed.json()['run_id']}").json()
    assert saved["inputs"]["consent"] is True
    for key, value in payload.items():
        assert saved["inputs"][key] == value


def test_device_read_requires_matching_configured_admin_key(
    boundary_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-only-admin-key")
    read = Mock(return_value={"fixture": "no device read", "data_kind": "test_fixture"})
    monkeypatch.setattr(main, "modbus_read", read)

    denied = boundary_client.post("/api/connectors/modbus", json={"device": "fixture"})
    assert denied.status_code == 401
    read.assert_not_called()
    allowed = boundary_client.post(
        "/api/connectors/modbus",
        json={"device": "fixture"},
        headers={"X-API-Key": "test-only-admin-key"},
    )
    assert allowed.status_code == 200
    read.assert_called_once()
    assert allowed.json()["fixture"] == "no device read"


def test_missing_evidence_run_is_rejected_without_recording_a_council_result(
    boundary_client: TestClient,
) -> None:
    response = boundary_client.post("/api/council/review", json={"evidence_run_ids": ["missing"]})
    assert response.status_code == 404
    assert response.json()["detail"] == "An evidence run was not found."
    assert boundary_client.get("/api/runs").json() == []


def test_oversized_saved_evidence_requires_a_bounded_summary(boundary_client: TestClient) -> None:
    store: Store = main.app.state.store
    saved = store.save("series_import", {}, {"fixture": "x" * 31_000})
    response = boundary_client.post("/api/council/review", json={"evidence_run_ids": [saved["run_id"]]})
    assert response.status_code == 422
    assert "at most 30 KB" in response.json()["detail"]
    assert len(boundary_client.get("/api/runs").json()) == 1


def configure_external_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OPENAI", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "test-only-admin-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-not-a-real-secret")
    monkeypatch.setenv("OPENAI_MODEL", "test-fixture-model")


def test_busy_external_council_fails_before_starting_another_provider_execution(
    boundary_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_external_fixture(monkeypatch)
    provider = AsyncMock()
    monkeypatch.setattr(main, "openai_council", provider)
    lock: asyncio.Lock = main.app.state.ai_lock
    assert boundary_client.portal is not None
    boundary_client.portal.call(lock.acquire)
    try:
        response = boundary_client.post(
            "/api/council/review",
            json={"mode": "openai", "consent_to_external_processing": True},
            headers={"X-API-Key": "test-only-admin-key"},
        )
    finally:
        boundary_client.portal.call(lock.release)
    assert response.status_code == 429
    assert response.json()["detail"]["protocol"]["external_execution_status"] == "not_started"
    provider.assert_not_awaited()
    assert boundary_client.get("/api/runs").json() == []


def test_missing_optional_external_dependency_is_not_reported_as_a_completed_review(
    boundary_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure_external_fixture(monkeypatch)
    monkeypatch.setattr(main, "openai_council", AsyncMock(side_effect=ImportError("missing SDK")))
    response = boundary_client.post(
        "/api/council/review",
        json={"mode": "openai", "consent_to_external_processing": True},
        headers={"X-API-Key": "test-only-admin-key"},
    )
    assert response.status_code == 503
    failure = response.json()["detail"]
    assert failure["protocol"]["external_execution_status"] == "not_started"
    assert failure["result_recorded"] is False
    assert boundary_client.get("/api/runs").json() == []


def test_html_responses_have_the_served_application_csp(boundary_client: TestClient) -> None:
    response = boundary_client.get("/")
    assert response.status_code == 200
    assert "script-src 'self';" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-cache"


@pytest.mark.parametrize(
    ("model", "payload", "reason"),
    [
        (
            StorageRequest,
            {"min_soc_fraction": 0.5, "max_soc_fraction": 0.5, "initial_soc_fraction": 0.5},
            "Minimum SOC must be less",
        ),
        (
            StorageRequest,
            {"load_kw": [1], "pv_kw": [0], "import_eur_per_kwh": [0.2], "export_eur_per_kwh": [0.1]},
            "At least two intervals",
        ),
        (PVRequest, {"years": 2, "inverter_replacement_year": 3}, "within project life"),
    ],
)
def test_impossible_model_horizons_are_rejected(
    model: type[BaseModel], payload: dict[str, object], reason: str
) -> None:
    with pytest.raises(ValidationError, match=reason):
        model.model_validate(payload)


def test_malformed_council_record_list_is_flagged_without_interpreting_its_contents() -> None:
    review = inspect_supplied_evidence({"supplied_records": {"untrusted": "object"}})
    assert review["records_checked"] == 0
    assert "malformed_record_list" in {finding["code"] for finding in review["findings"]}
    assert review["critic_execution"] == "not_configured_in_local_mode"


@pytest.mark.parametrize(
    ("record", "finding"),
    [
        (
            {"kind": "finance", "result": {"model": "", "npv_eur": 1, "irr_pct": None, "minimum_dscr": None}},
            "missing_or_invalid_result_fields",
        ),
        (
            {"kind": "forecast", "result": {"model": "fixture", "rows": {}}},
            "missing_or_invalid_result_fields",
        ),
        (
            {"result": {}, "input_sha256": "a" * 64, "inputs": {"value": float("nan")}},
            "uncanonical_input_payload",
        ),
        (
            {"result": {"data_kind": "synthetic"}, "metadata": {"expected_data_kind": "measured"}},
            "data_kind_mismatch",
        ),
        ({"result": {}, "metadata": {"valid_until": "not-a-date"}}, "invalid_validity_timestamp"),
    ],
)
def test_council_evidence_findings_preserve_unverified_status(
    record: dict[str, object], finding: str
) -> None:
    review = inspect_supplied_evidence({"supplied_records": [record]})
    assert finding in review["records"][0]["finding_codes"]
    assert review["status"] == "checklist_only"
    assert "source authenticity" in review["semantics"]


def test_nullable_finance_metrics_and_unexpired_validity_are_not_fabricated_as_numbers() -> None:
    result = {"model": "fixture", "npv_eur": 1, "irr_pct": None, "minimum_dscr": None}
    review = inspect_supplied_evidence(
        {
            "supplied_records": [
                {
                    "kind": "finance",
                    "result": result,
                    "metadata": {"as_of": "2026-01-01", "valid_until": "2027-01-01T00:00:00Z"},
                }
            ]
        }
    )
    codes = review["records"][0]["finding_codes"]
    assert "missing_or_invalid_result_fields" not in codes
    assert "expired_validity" not in codes
    assert result["irr_pct"] is None
    assert result["minimum_dscr"] is None
