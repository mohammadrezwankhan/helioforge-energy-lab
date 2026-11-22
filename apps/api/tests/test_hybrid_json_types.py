"""Reject hybrid API coercions that disagree with the browser JSON-number contract."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from helioforge.hybrid import HybridRequest
from helioforge.main import app

COERCIVE_INPUTS: tuple[dict[str, object], ...] = (
    {"hours": 24.0},
    {"hours": "24"},
    {"hours": True},
    {"solar_kw": "1200"},
    {"battery_kw": True},
    {"critical_fraction": True},
    {"initial_soc": "0.6"},
    {"initial_soc": True},
    {"round_trip_efficiency": "0.9"},
    {"import_eur_kwh": "0.2"},
    {"export_eur_kwh": False},
)


@pytest.mark.parametrize("invalid", COERCIVE_INPUTS)
def test_hybrid_request_rejects_coercive_types(invalid: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HybridRequest.model_validate(invalid)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "hybrid-coercion.sqlite3"))
    monkeypatch.setenv("ENABLE_OPENAI", "false")
    with TestClient(app, base_url="http://127.0.0.1") as api:
        yield api


def test_hybrid_api_rejects_coercive_json_types(client: TestClient) -> None:
    for invalid in COERCIVE_INPUTS:
        response = client.post("/api/hybrid/simulate", json=invalid)
        assert response.status_code == 422, (invalid, response.text)


def test_valid_json_numbers_still_accept_integer_ratings() -> None:
    request = HybridRequest.model_validate({"hours": 24, "solar_kw": 1200, "battery_kw": 750})
    assert request.hours == 24
    assert request.solar_kw == 1200.0
    assert request.battery_kw == 750.0
