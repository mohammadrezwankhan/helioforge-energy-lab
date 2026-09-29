"""Regression coverage for the explicit local-only host and cache boundary."""
import pytest
from fastapi.testclient import TestClient
from helioforge.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "champion.sqlite3"))
    monkeypatch.setenv("ENABLE_OPENAI", "false")
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c

@pytest.mark.parametrize("host", ["evil.example", "localhost.evil.example", "127.0.0.1.evil.example", "untrusted.test:8000"])
def test_unexpected_host_is_rejected(client, host):
    r=client.get("/api/health",headers={"host":host})
    assert r.status_code==400
    assert "Invalid host" in r.text

@pytest.mark.parametrize("host", ["localhost", "localhost:8000", "127.0.0.1", "127.0.0.1:8765"])
def test_local_hosts_are_accepted(client, host):
    r=client.get("/api/health", headers={"host":host})
    assert r.status_code==200
    assert r.json()["version"]=="0.3.0"

@pytest.mark.parametrize("path", ["/api/health", "/api/runs", "/api/hybrid/catalog"])
def test_local_api_results_are_not_cached(client,path):
    r=client.get(path)
    assert r.status_code==200
    assert r.headers["cache-control"]=="no-store"
    assert "camera=()" in r.headers["permissions-policy"]
    assert r.headers["x-content-type-options"]=="nosniff"

def test_host_restriction_does_not_weaken_origin_checks(client):
    r=client.post("/api/hybrid/simulate", json={}, headers={"host":"localhost:8000","origin":"https://evil.example"})
    assert r.status_code==403
    assert client.get("/api/runs").json()==[]

def test_rejected_host_does_not_write_a_run(client):
    r=client.post("/api/storage/optimize", json={}, headers={"host":"rebinding.example"})
    assert r.status_code==400
    assert client.get("/api/runs").json()==[]
