"""New-model tests: scope contracts, scenario matrix, invariants and API provenance."""
import hashlib
import json
import math
import random

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from helioforge.engines.hybrid import simulate_hybrid
from helioforge.hybrid import (
    HybridRequest,
    applicability,
    catalog,
    get_scenario,
    get_system,
    validate_configuration,
)
from helioforge.main import app

C = catalog()
SYSTEMS = C['systems']
SCENARIOS = C['scenarios']
PAIRS = [(s, c) for s in SYSTEMS if s['mode'] == 'screening'
         for c in SCENARIOS if c['mode'] == 'screening' and applicability(s, c)]


def config(s, c='baseline', **extra):
    scenario = get_scenario(c)
    return HybridRequest(**{**s['preset'], 'scenario_id': c,
                            'hours': max(s['preset']['hours'], scenario['modifiers'].get('hours', 0)), **extra})


def invariant(p, result):
    m = get_scenario(p.scenario_id)['modifiers']
    capacity = result['effective_capacity_kwh']
    lo = capacity * max(p.min_soc, m.get('reserve_floor', p.min_soc))
    hi = capacity * p.max_soc
    eta = math.sqrt(p.round_trip_efficiency)
    assert len(result['schedule']) == p.hours
    assert 0 <= result['load_served_pct'] <= 100 + 1e-8
    assert 0 <= result['critical_served_pct'] <= 100 + 1e-8
    assert result['max_balance_residual_kw'] < 1e-6
    prev = result['initial_energy_kwh']
    for row in result['schedule']:
        assert lo-1e-7 <= row['soc_end_kwh'] <= hi+1e-7
        assert row['soc_start_kwh'] == pytest.approx(prev)
        assert row['soc_end_kwh'] == pytest.approx(prev + row['charge_kw']*eta-row['discharge_kw']/eta)
        assert not(row['charge_kw'] > 1e-8 and row['discharge_kw'] > 1e-8)
        assert not(row['grid_import_kw'] > 1e-8 and row['grid_export_kw'] > 1e-8)
        for key in ['served_kw','unserved_kw','critical_unserved_kw','curtailed_kw','generator_kw','charge_kw','discharge_kw']:
            assert row[key] >= -1e-7
        assert row['served_kw'] + row['unserved_kw'] == pytest.approx(row['load_kw'])
        assert row['grid_import_kw'] <= p.grid_import_kw*m.get('import_factor',1)+1e-7
        assert row['grid_export_kw'] <= p.grid_export_kw*m.get('export_factor',1)+1e-7
        if not row['grid_connected']:
            assert row['grid_import_kw'] == row['grid_export_kw'] == 0
        prev = row['soc_end_kwh']
    assert result['battery_energy_delta_kwh'] == pytest.approx(prev-result['initial_energy_kwh'])
    assert result['unserved_kwh'] == pytest.approx(result['total_load_kwh']-result['served_kwh'])


def test_catalogue_is_cross_referenced_and_scope_explicit():
    assert len(SYSTEMS) == len(C['lessons']) == 36
    assert len(SCENARIOS) == 24
    assert sum(s['mode']=='screening' for s in SYSTEMS) == 19
    assert sum(c['mode']=='study' for c in SCENARIOS) == 4
    for key in ['systems','scenarios','lessons','technologies']:
        assert len({v['id'] for v in C[key]}) == len(C[key])
    techs = {t['id'] for t in C['technologies']}
    for s in SYSTEMS:
        assert set(s['technologies']) <= techs
        assert config(s).system_id == s['id']
    for lesson in C['lessons']:
        assert lesson['system_id'] in {s['id'] for s in SYSTEMS}
        assert applicability(get_system(lesson['system_id']),get_scenario(lesson['scenario_id']))
        for q in lesson['quiz']:
            assert 0 <= q['answer'] < len(q['options'])
            assert len(q['options']) == len(set(q['options']))
            assert q['explanation']


@pytest.mark.parametrize('system,scenario', PAIRS, ids=[f"{s['id']}--{c['id']}" for s,c in PAIRS])
def test_all_applicable_runnable_pairs(system, scenario):
    p=config(system,scenario['id'])
    invariant(p,simulate_hybrid(p))


@pytest.mark.parametrize('system',[s for s in SYSTEMS if s['mode']=='study'],ids=lambda s:s['id'])
def test_study_architectures_never_get_fake_numerical_results(system):
    p=config(system)
    assert not validate_configuration(p)['valid']
    with pytest.raises(ValueError,match='Study-only'):
        simulate_hybrid(p)


@pytest.mark.parametrize('scenario',[c for c in SCENARIOS if c['mode']=='study'],ids=lambda c:c['id'])
def test_control_studies_rejected(scenario):
    with pytest.raises(ValueError,match='Study-only'):
        simulate_hybrid(config(get_system('hospital-island'),scenario['id']))


def test_zero_assets_grid_only_has_hand_verifiable_balance():
    p=config(get_system('industrial-btm'),hours=2,solar_kw=0,battery_kwh=0,battery_kw=0,control='GFL',load_kw=10,grid_import_kw=100,grid_export_kw=0)
    r=simulate_hybrid(p)
    expected=sum(10*(.78+.18*math.sin((h-8)*math.pi/12)**2) for h in range(2))
    assert r['grid_import_kwh']==pytest.approx(expected)
    assert r['variable_cost_eur']==pytest.approx(expected*p.import_eur_kwh)
    assert r['terminal_energy_kwh']==0
    invariant(p,r)


def test_outage_reference_and_scheduled_shedding_not_conflated():
    s=get_system('hospital-island')
    grid_following=simulate_hybrid(config(s,'outage-24h',control='GFL'))
    assert grid_following['served_kwh']==0
    grid_forming=simulate_hybrid(config(s,'outage-24h'))
    assert grid_forming['served_kwh']>0
    assert sum(x['scheduled_shed_kw'] for x in grid_forming['schedule'])>0
    assert grid_forming['unserved_kwh']>=grid_forming['critical_unserved_kwh']
    nonisland=simulate_hybrid(config(get_system('utility-pv-ac'),'outage-24h',control='GFM'))
    assert nonisland['served_kwh']==0


def test_offgrid_gfl_and_unsupported_scenario_rejected():
    with pytest.raises(ValueError,match='grid-following'):
        simulate_hybrid(HybridRequest(control='GFL'))
    with pytest.raises(ValueError,match='does not apply'):
        simulate_hybrid(HybridRequest(scenario_id='outage-24h'))


def test_scenario_capacity_power_and_tariff_effects_are_explicit():
    s=get_system('industrial-btm')
    aged=simulate_hybrid(config(s,'aged-battery'))
    assert aged['effective_capacity_kwh']==s['preset']['battery_kwh']*.7
    tripped=simulate_hybrid(config(s,'battery-trip'))
    assert tripped['charged_kwh']==tripped['discharged_kwh']==0
    assert simulate_hybrid(config(s,'zero-export'))['grid_export_kwh']==0
    negative=simulate_hybrid(config(s,'negative-prices'))
    assert negative['schedule'][12]['import_eur_kwh']==-.05
    noexport=simulate_hybrid(config(s,export_eur_kwh=-.1))
    assert noexport['grid_export_kwh']==0
    dc=simulate_hybrid(config(get_system('utility-pv-dc')))
    assert any('AC-equivalent' in warning for warning in dc['warnings'])


@pytest.mark.parametrize('bad',[{'min_soc':.8},{'hours':169},{'hours':2.5},{'load_kw':0},
    {'solar_kw':float('inf')},{'wind_kw':float('nan')},{'battery_kwh':0},{'extra':1},
    {'grid_import_kw':100},{'system_id':'missing'},{'scenario_id':'missing'},
    {'scenario_id':'outage-72h','hours':24},{'scenario_id':'reserve-floor','initial_soc':.2}])
def test_invalid_inputs_rejected(bad):
    with pytest.raises((ValueError,ValidationError)):
        HybridRequest(**bad)


def test_seeded_input_fuzz_preserves_invariants():
    rng=random.Random(619)
    candidates=[s for s in SYSTEMS if s['mode']=='screening']
    for _ in range(100):
        s=rng.choice(candidates)
        inputs={**s['preset'],'hours':rng.randint(2,168),'load_kw':rng.uniform(1,1500)}
        for key in ['solar_kw','wind_kw','hydro_kw','generator_kw','battery_kw','battery_kwh']:
            if inputs[key]:
                inputs[key]*=rng.uniform(.05,4)
        p=HybridRequest(**inputs)
        invariant(p,simulate_hybrid(p))


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('HELIOFORGE_DB',str(tmp_path/'hybrid.sqlite3'))
    monkeypatch.setenv('ENABLE_OPENAI','false')
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


def test_api_catalogue_validation_run_hash_and_exact_review_attachment(client):
    assert len(client.get('/api/hybrid/catalog').json()['systems'])==36
    payload=config(get_system('hospital-island'),'outage-4h',solar_kw=777).model_dump()
    assert client.post('/api/hybrid/validate',json=payload).json()['valid']
    response=client.post('/api/hybrid/simulate',json=payload)
    assert response.status_code==200,response.text
    run=response.json()
    stored=client.get('/api/runs/'+run['run_id']).json()
    assert stored['inputs']['solar_kw']==777
    canonical=json.dumps(stored['inputs'],sort_keys=True,separators=(',',':'))
    assert hashlib.sha256(canonical.encode()).hexdigest()==run['input_sha256']
    review=client.post('/api/council/review',json={'hybrid_run_id':run['run_id']})
    assert review.status_code==200,review.text
    body=review.json()
    assert body['hybrid_run_id']==run['run_id']
    assert len(body['reviews'])==8
    hybrid=next(x for x in body['reviews'] if x['agent']=='Hybrid architect')
    assert run['run_id'] in str(hybrid)
    assert 'outage-4h' in str(hybrid)


def test_rejected_runs_and_missing_review_evidence_not_recorded(client):
    p=config(get_system('solar-hydrogen')).model_dump()
    assert client.post('/api/hybrid/simulate',json=p).status_code==422
    assert client.get('/api/runs').json()==[]
    assert client.post('/api/council/review',json={'hybrid_run_id':'missing'}).status_code==404
    run=client.post('/api/pv/evaluate',json={}).json()
    assert client.post('/api/council/review',json={'hybrid_run_id':run['run_id']}).status_code==404
