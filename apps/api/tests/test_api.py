import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from helioforge.main import app


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('HELIOFORGE_DB',str(tmp_path/'test.sqlite3'))
    monkeypatch.setenv('ENABLE_OPENAI','false')
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


def test_health_and_overview(client):
    assert client.get('/api/health').json()['status'] == 'ok'
    d=client.get('/api/overview').json()
    assert d['data_kind'] == 'synthetic'
    assert len(d['markets']) == 6
    assert len(d['portfolio']) == 6
    assert client.get('/api/overview?market=ZZ').status_code == 422


@pytest.mark.parametrize('path', ['storage/optimize','finance/evaluate','pv/evaluate','forecast/simulate',
                                   'research/reliability','research/carbon','acquisitions/screen'])
def test_default_model_endpoints_persist(path,client):
    response=client.post(f'/api/{path}',json={})
    assert response.status_code == 200,response.text
    data=response.json()
    assert data['run_id']
    assert len(data['input_sha256']) == 64
    stored=client.get(f"/api/runs/{data['run_id']}").json()
    assert stored['result']['model'] == data['model']
    canonical=json.dumps(stored['inputs'],sort_keys=True,separators=(',',':'))
    assert hashlib.sha256(canonical.encode()).hexdigest() == data['input_sha256']
    assert len(client.get('/api/runs').json()) == 1


def test_drift_endpoint(client):
    response=client.post('/api/research/drift',json={'expected':[100]*30,'observed':[100]*20+[90]*10})
    assert response.status_code == 200
    assert response.json()['alert_count'] == 10


def test_invalid_input_is_actionable_and_not_saved(client):
    response=client.post('/api/storage/optimize',json={'capacity_kwh':-1})
    assert response.status_code == 422
    assert client.get('/api/runs').json() == []


def test_pilot_update_is_persistent_and_audited(client):
    response=client.patch('/api/pilots/P-01',json={'status':'validated','evidence_note':'Synthetic acceptance evidence recorded.'})
    assert response.status_code == 200
    assert client.get('/api/pilots').json()[0]['status'] == 'validated'
    assert client.get('/api/overview').json()['pilots'][0]['status'] == 'validated'
    events=client.get('/api/pilots/events').json()
    assert len(events) == 1
    assert json.loads(events[0]['old_json'])['status'] == 'running'


def test_pilot_note_required(client):
    assert client.patch('/api/pilots/P-01',json={'status':'validated','evidence_note':'OK'}).status_code == 422


def test_missing_run_and_pilot(client):
    assert client.get('/api/runs/missing').status_code == 404
    assert client.patch('/api/pilots/unknown',json={'status':'planned','evidence_note':'Enough evidence length.'}).status_code == 404


def test_local_council_honest_mode(client):
    r=client.post('/api/council/review',json={})
    assert r.status_code == 200,r.text
    assert r.json()['execution'] == 'deterministic_rule_based'
    assert len(r.json()['reviews']) == 8
    assert 'No LLM' in r.json()['warnings'][0]


def test_external_mode_disabled_by_default(client):
    r=client.post('/api/council/review',json={'mode':'openai','consent_to_external_processing':True})
    assert r.status_code == 403


def test_external_mode_requires_admin_and_consent(client,monkeypatch):
    monkeypatch.setenv('ENABLE_OPENAI','true')
    monkeypatch.setenv('ADMIN_API_KEY','test-admin-key')
    assert client.post('/api/council/review',json={'mode':'openai'}).status_code == 401
    assert client.post('/api/council/review',json={'mode':'openai'},headers={'X-API-Key':'test-admin-key'}).status_code == 422


def test_external_mode_requires_server_credentials(client,monkeypatch):
    monkeypatch.setenv('ENABLE_OPENAI','true')
    monkeypatch.setenv('ADMIN_API_KEY','test-admin-key')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    r=client.post('/api/council/review',json={'mode':'openai','consent_to_external_processing':True},headers={'X-API-Key':'test-admin-key'})
    assert r.status_code == 503


def test_external_provider_error_is_not_a_fake_local_success(client,monkeypatch):
    monkeypatch.setenv('ENABLE_OPENAI','true')
    monkeypatch.setenv('ADMIN_API_KEY','test-admin-key')
    monkeypatch.setenv('OPENAI_API_KEY','fake-not-a-real-secret')
    monkeypatch.setenv('OPENAI_MODEL','configured-model')
    async def fail(*args):
        raise RuntimeError('provider payload should never be exposed')
    monkeypatch.setattr('helioforge.main.openai_council',fail)
    r=client.post('/api/council/review',json={'mode':'openai','consent_to_external_processing':True},headers={'X-API-Key':'test-admin-key'})
    assert r.status_code == 502
    assert 'provider payload' not in r.text
    assert client.get('/api/runs').json() == []


def test_untrusted_browser_origin_blocked(client):
    r=client.post('/api/finance/evaluate',json={},headers={'Origin':'https://untrusted.example'})
    assert r.status_code == 403


def test_request_size_bounded(client):
    assert client.post('/api/finance/evaluate',content='x'*1_000_001).status_code == 413


def test_security_headers(client):
    r=client.get('/api/health')
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert r.headers['x-request-id']


def test_openapi_lists_all_analysis_routes(client):
    paths=client.get('/openapi.json').json()['paths']
    assert '/api/storage/optimize' in paths
    assert '/api/council/review' in paths
