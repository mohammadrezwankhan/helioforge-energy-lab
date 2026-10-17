import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from helioforge.main import app
from helioforge.studies import StudyRequest, catalogue, evaluate


def test_catalogue_is_complete_unique_and_examples_are_finite():
    definitions=catalogue()
    assert len(definitions)==59
    assert len({s['id'] for s in definitions})==59
    assert {s['page'] for s in definitions}=={'overview','hybrid','lessons','compare','storage','pv','research','markets','forecast','investment','pilots','council'}
    for study in definitions:
        r=evaluate(StudyRequest(study=study['id']))
        digest=r.pop('evidence_sha256')
        raw=json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)
        assert hashlib.sha256(raw.encode()).hexdigest()==digest


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('HELIOFORGE_DB',str(tmp_path/'studies.sqlite3'))
    with TestClient(app,base_url='http://127.0.0.1') as c:
        yield c


def test_study_api_persists_inputs_and_evidence(client):
    assert len(client.get('/api/studies').json())==59
    response=client.post('/api/studies/evaluate',json={'study':'pv-reserve','inputs':{'cost_eur':1000,'inflation':0,'fund_return':0,'years':10}})
    assert response.status_code==200,response.text
    r=response.json()
    assert r['metrics'][1]['value']==100
    stored=client.get('/api/runs/'+r['run_id']).json()
    assert stored['result']['evidence_sha256']==r['evidence_sha256']
    assert stored['inputs']['study']=='pv-reserve'


@pytest.mark.parametrize('body',[
    {'study':'missing-study','inputs':{}},
    {'study':'pv-reserve','inputs':{'years':1.5}},
    {'study':'pv-reserve','inputs':{'unknown':1}},
    {'study':'../secret','inputs':{}},
])
def test_study_api_rejects_invalid_requests(client,body):
    assert client.post('/api/studies/evaluate',json=body).status_code==422
