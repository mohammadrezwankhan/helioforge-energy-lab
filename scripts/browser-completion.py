"""Proof of remaining-roadmap UI using real local API, with no paid/device calls."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8017')
parser.add_argument('--output',default='docs/roadmap/completion-browser')
args=parser.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def passed(message):
    checks.append(message)
    print('PASS',message,flush=True)

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1050},reduced_motion='reduce')
    page.set_default_timeout(20000)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.url,wait_until='networkidle')
    expect(page.locator('.connection-chip')).to_have_text('API connected')
    def nav(name):
        menu=page.locator('[data-action="menu"]')
        if menu.is_visible():menu.click()
        page.locator(f'.nav-item[data-nav="{name}"]').click()
        expect(page.locator('#integration-panel')).to_have_count(1)
    def open_form(op):
        form=page.locator(f'form[data-integration="{op}"]')
        form.evaluate('(f)=>f.closest("details").open=true')
        return form
    for name in ['overview','hybrid','lessons','compare','storage','pv','research','markets','forecast','investment','pilots','council']:
        nav(name)
        expect(page.locator('#integration-panel')).to_contain_text('EXTERNAL REQUIREMENTS')
    passed('Every view exposes its specific real-data and external-validation requirements without navigation starvation')

    for name,study in [('hybrid','hybrid-powerflow'),('markets','markets-network'),('pv','pv-raytrace'),('pilots','pilots-registration')]:
        nav(name);page.locator(f'[data-study-select="{study}"]').click()
        expect(page.locator('.hf-advanced-visual')).to_have_count(1)
        expect(page.locator('.hf-advanced-visual')).not_to_contain_text('Required result data missing')
        page.locator('#study-visual').screenshot(path=str(out/f'{study}.png'),animations='disabled')
    passed('Solved voltage/branch flows, six-zone flows, ray geometry and aligned point clouds render actual study data')

    nav('storage');page.locator('[data-study-select="storage-annual"]').click()
    chart=page.locator('[data-hf-tariff-profile]');expect(chart).to_have_count(1)
    before=json.loads(page.locator('#study-form [name="tariff"]').input_value())
    # A cached page is frozen, not disposed; its event handlers must survive restoration.
    page.evaluate('window.dispatchEvent(new PageTransitionEvent("pagehide", {persisted:true}))')
    chart.focus();chart.press('ArrowUp')
    after=json.loads(page.locator('#study-form [name="tariff"]').input_value())
    assert after[0]>before[0]
    expect(page.locator('#study-output')).to_be_hidden()
    # Status prose must never cover the action when fonts or viewport change.
    for width in [320,375,414,768,1024,1280,1440,1920]:
        page.set_viewport_size({'width':width,'height':1050})
        apply=page.locator('[data-hf-tariff-apply]')
        apply.evaluate('b=>b.scrollIntoView({block:"center",inline:"nearest"})')
        assert apply.evaluate('b=>{const r=b.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest("[data-hf-tariff-apply]")===b}'), width
    page.set_viewport_size({'width':1600,'height':1050})
    page.locator('[data-hf-tariff-apply]').click()
    expect(page.locator('#study-output')).to_be_visible(timeout=30000)
    passed('Keyboard tariff edit changes the actual input, hides stale output, and recalculates successfully')

    form=open_form('series')
    form.locator('[name="csv"]').set_input_files({'name':'meter.csv','mimeType':'text/csv','buffer':b'timestamp,value\n2026-01-01T00:00:00Z,100\n2026-01-01T01:00:00Z,120'})
    form.locator('button[type="submit"]').click()
    expect(page.locator('#integration-result')).to_contain_text('user_supplied_unverified')
    page.locator('#integration-result details').evaluate('(e)=>e.open=true')
    page.locator('#integration-target').fill('hourly_load_kw')
    page.locator('[data-integration-apply]').click()
    assert json.loads(page.locator('#study-form [name="hourly_load_kw"]').input_value())==[100,120]
    expect(page.locator('#study-output')).to_be_hidden()
    passed('Measured CSV import retains observations, unit and provenance and invalidates edited study results')

    nav('overview');form=open_form('geography')
    geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'name':'Supplied location'},'geometry':{'type':'Point','coordinates':[2.3,48.8]}}]}
    form.locator('[name="geography"]').set_input_files({'name':'assets.geojson','mimeType':'application/json','buffer':json.dumps(geo).encode()})
    form.locator('button[type="submit"]').click()
    expect(page.locator('.evidence-geography circle')).to_have_count(1)
    with page.expect_download() as dl:page.locator('[data-integration-export="json"]').click()
    assert json.loads(Path(dl.value.path()).read_text(encoding='utf-8'))==geo
    passed('Geographic assets use supplied WGS84 coordinates and export the same GeoJSON')

    nav('council');form=open_form('document')
    form.locator('[name="document"]').set_input_files({'name':'warranty.txt','mimeType':'text/plain','buffer':b'Warranty: 6000 cycles at 80% remaining capacity. Valid until 2030-01-01.'})
    form.locator('[name="purpose"]').select_option('warranty')
    form.locator('button[type="submit"]').click()
    expect(page.locator('#integration-result')).to_contain_text('6000 cycles')
    page.locator('[data-integration-attach]').click()
    assert page.locator('[name="evidence_run_ids"]').input_value()
    passed('Document extraction is auditable and its saved run can be attached to a council review')

    nav('pilots');form=open_form('telemetry')
    record={'source':'Test fixture only','timestamp':datetime.now(timezone.utc).isoformat(),'readings':[{'channel':'temperature','value':90,'unit':'degC','warning':50,'critical':80}]}
    form.locator('[name="telemetry"]').fill(json.dumps(record));form.locator('button[type="submit"]').click()
    expect(page.locator('#integration-result')).to_contain_text('critical')
    expect(page.locator('#integration-result')).to_contain_text('Read-only diagnostic thresholds')
    passed('Supplied telemetry shows threshold severity while retaining the external safety-validation boundary')

    nav('lessons')
    lessons=page.evaluate('HF.HYBRID_CATALOG.lessons')
    advanced=next(l for l in lessons if l['level']=='Advanced')
    expect(page.locator(f'[data-lesson="{advanced["id"]}"]').first).to_have_attribute('aria-disabled','true')
    for lesson in [l for l in lessons if l['level']=='Foundation']:
        page.locator(f'.lesson-list [data-lesson="{lesson["id"]}"]').click()
        for i,q in enumerate(lesson['quiz']):page.locator(f'#lesson-quiz [name="q{i}"][value="{q["answer"]}"]').check()
        page.locator('#lesson-quiz button[type="submit"]').click()
        expect(page.locator('#quiz-feedback')).to_contain_text('2 / 2')
    applied=next(l for l in lessons if l['level']=='Applied')
    expect(page.locator(f'.lesson-list [data-lesson="{applied["id"]}"]')).to_have_attribute('aria-disabled','false')
    expect(page.locator(f'.lesson-list [data-lesson="{advanced["id"]}"]')).to_have_attribute('aria-disabled','true')
    stored=page.evaluate('JSON.parse(localStorage.getItem("hf-learning-mastery-v1"))')
    assert len(stored['mastery_checks'])==9
    passed('All nine actual Foundation quizzes unlock Applied while Advanced stays gated; exact local scores persist')

    nav('hybrid')
    page.locator('#run-hybrid').click();expect(page.locator('#toast')).to_contain_text('Hybrid energy screen complete',timeout=30000)
    page.locator('[data-hybrid-action="pin"]').click()
    other=page.evaluate('HF.HYBRID_CATALOG.systems.find(s=>s.mode==="screening"&&s.id!==HF.HYBRID_CATALOG.systems[0].id).id')
    page.locator('#architecture-library').scroll_into_view_if_needed()
    page.locator(f'[data-system="{other}"]').first.click()
    page.locator('#run-hybrid').click();expect(page.locator('#toast')).to_contain_text('Hybrid energy screen complete',timeout=30000)
    page.locator('[data-hybrid-action="pin"]').click();nav('compare')
    expect(page.locator('[data-hf-scene-canvas]')).to_have_count(2)
    page.locator('[data-hf-sync-hour]').fill('18')
    expect(page.locator('[data-hf-scene-evidence]')).to_contain_text('Hour 18')
    page.locator('[data-hf-camera="left"][data-camera-preset="top-down"]').click()
    expect(page.locator('[data-hf-camera="left"][data-camera-preset="top-down"]')).to_have_attribute('aria-pressed','true')
    page.locator('[data-hf-completion-scenes]').screenshot(path=str(out/'dual-scenes.png'),animations='disabled')
    nav('overview');nav('compare');expect(page.locator('[data-hf-scene-canvas]')).to_have_count(2)
    passed('Two real saved runs drive synchronized scenes, independent camera controls and clean remounts')
    page.set_viewport_size({'width':390,'height':844})
    for name in ['overview','hybrid','lessons','compare','storage','pv','research','markets','forecast','investment','pilots','council']:
        nav(name)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), name
    page.screenshot(path=str(out/'mobile-council.png'),full_page=True,animations='disabled')
    passed('New evidence panels and comparison scenes fit every view at 390px')
    assert not errors,errors
    browser.close()
(out/'report.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'errors':errors},indent=2),encoding='utf-8')
print(json.dumps({'passed':len(checks),'errors':errors}))
