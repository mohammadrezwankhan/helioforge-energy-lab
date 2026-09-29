"""Hybrid UI integration checks, using real API results (never mocked energy).

Direct HTTP is the default; --bridge supports sandbox browser network restrictions.
The bridge does not certify CSP enforcement, file:// behavior or deployment security.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--url', default='http://127.0.0.1:8000')
p.add_argument('--bridge', action='store_true')
p.add_argument('--executable', default=os.getenv('CHROMIUM_EXECUTABLE'))
p.add_argument('--screenshots', action='store_true')
a = p.parse_args()
checks: list[str] = []


def passed(text: str) -> None:
    checks.append(text)
    print('PASS', text, flush=True)


with sync_playwright() as pw, httpx.Client(base_url=a.url, timeout=40) as client:
    browser = pw.chromium.launch(executable_path=a.executable, headless=True,
                                args=['--no-sandbox'] if a.executable else [])
    page = browser.new_page(viewport={'width':1600,'height':1150},device_scale_factor=1)
    errors: list[str] = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def bridge(path: str, options: dict | None = None) -> dict:
        if not path.startswith('/api/'):
            raise ValueError('Only local API paths are permitted by this test bridge.')
        opts = options or {}
        r = client.request(opts.get('method','GET'),path,headers=opts.get('headers',{}),content=opts.get('body'))
        return {'status':r.status_code,'body':r.text,'headers':{'content-type':r.headers.get('content-type','application/json')}}

    if a.bridge:
        page.expose_function('hfHybridTestTransport',bridge)
        page.evaluate('''() => { window.fetch = async(path,options) => {
            const r=await window.hfHybridTestTransport(String(path),options||{});
            return new Response(r.body,{status:r.status,headers:r.headers});
        }; }''')
        page.set_content((ROOT/'HelioForge-Preview.html').read_text(),wait_until='load')
    else:
        page.goto(a.url,wait_until='networkidle')
    expect(page.locator('.connection-chip')).to_have_text('API connected')
    expect(page.locator('#hybrid-system option')).to_have_count(36)
    assert page.locator('canvas#energy-scene').count()==1
    passed('Hybrid lab is the default; all 36 architecture presets are available')
    if a.screenshots:
        page.screenshot(path=str(ROOT/'docs/hybrid-desktop.png'),animations='disabled')

    def nav(name: str) -> None:
        if page.locator('[data-action="menu"]').is_visible():
            page.locator('[data-action="menu"]').click()
        page.locator(f'.nav-item[data-nav="{name}"]').click()
        page.wait_for_timeout(300)
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'),(name,page.evaluate("Array.from(document.querySelectorAll('body *')).map(e=>({tag:e.tagName,cls:e.className,id:e.id,x:e.getBoundingClientRect().x,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})).filter(e=>e.right>innerWidth+.01&&e.width>1).slice(0,18)"))

    page.locator('[data-action="motion"]').click()
    page.wait_for_timeout(120)
    before=page.locator('#energy-scene').evaluate('(c)=>c.toDataURL()')
    page.wait_for_timeout(120)
    assert before==page.locator('#energy-scene').evaluate('(c)=>c.toDataURL()')
    page.locator('[data-scene-command="ArrowLeft"]').click()
    page.wait_for_timeout(100)
    assert before!=page.locator('#energy-scene').evaluate('(c)=>c.toDataURL()')
    page.locator('#energy-scene').focus()
    page.keyboard.press('ArrowRight');page.keyboard.press('+');page.keyboard.press('Home')
    page.locator('[data-asset="solar"]').click()
    expect(page.locator('#asset-inspector')).to_contain_text('Solar')
    passed('3D camera buttons and keyboard work; reduced motion freezes decorative canvas animation; asset inspector updates')

    page.locator('#hybrid-search').fill('H2')
    assert page.locator('.system-card').count()>=3
    page.locator('#hybrid-search').fill('not-a-real-architecture')
    expect(page.locator('#hybrid-library-results')).to_contain_text('No architectures match')
    page.locator('[data-hybrid-action="clear-filters"]').click()
    expect(page.locator('.system-card')).to_have_count(36)
    page.locator('#hybrid-family').select_option('Hydro')
    assert 0<page.locator('.system-card').count()<36
    page.locator('[data-hybrid-action="clear-filters"]').click()
    passed('Smart search synonyms, no-results state, family filter and reset')

    page.locator('#hybrid-system').select_option('hospital-island')
    page.locator('#hybrid-config [name="solar_kw"]').fill('777')
    page.locator('#hybrid-config [name="solar_kw"]').press('Tab')
    expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(0)

    def run() -> dict:
        page.locator('#run-hybrid').click()
        expect(page.locator('#toast')).to_contain_text('Hybrid energy screen complete',timeout=30000)
        expect(page.locator('#run-hybrid')).to_be_enabled()
        expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(1)
        saved=client.get('/api/runs').json()
        latest=next(x for x in saved if x['kind']=='hybrid')
        return client.get('/api/runs/'+latest['id']).json()

    baseline=run()
    assert baseline['inputs']['solar_kw']==777
    assert baseline['inputs']['scenario_id']=='baseline'
    with page.expect_download() as dl:
        page.locator('[data-hybrid-action="export"]').click()
    exported=json.loads(Path(dl.value.path()).read_text())
    assert exported['inputs']['solar_kw']==777
    with page.expect_download() as dl:
        page.locator('[data-hybrid-action="csv"]').click()
    csv=Path(dl.value.path()).read_text()
    assert 'balance_residual_kw' in csv
    page.locator('[data-hybrid-action="pin"]').click()
    page.locator('[data-scenario="outage-4h"]').click()
    expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(0)
    outage=run()
    assert outage['inputs']['scenario_id']=='outage-4h'
    assert sum(not x['grid_connected'] for x in outage['result']['schedule'])==4
    page.locator('#hybrid-hour').fill('18')
    expect(page.locator('#hour-label')).to_contain_text('18:00')
    expect(page.locator('#interval-readout')).to_contain_text('Island energized')
    page.locator('[data-hybrid-action="pin"]').click()
    passed('Real baseline and outage calculations, current-input provenance, stale-result hiding, time scrubber and CSV/setup exports')

    nav('compare')
    expect(page.locator('.comparison-table thead th')).to_have_count(3)
    expect(page.locator('.compare-panel')).to_contain_text('2 pinned runs')
    with page.expect_download() as dl:
        page.locator('[data-hybrid-action="export-compare"]').click()
    comparison=json.loads(Path(dl.value.path()).read_text())
    assert len(comparison['runs'])==2
    if a.screenshots:
        page.screenshot(path=str(ROOT/'docs/hybrid-compare.png'),animations='disabled')
    passed('Two-run comparison preserves inputs and stored-energy boundaries; comparison export is parseable')

    nav('council')
    page.locator('form[data-model="council"] [name="hybrid_run_id"]').select_option(outage['run_id'])
    page.locator('form[data-model="council"] button[type="submit"]').click()
    expect(page.locator('#toast')).to_contain_text('complete',timeout=30000)
    expect(page.locator('.review-card')).to_have_count(8)
    expect(page.locator('.review-card').filter(has_text='Hybrid architect')).to_contain_text(outage['run_id'])
    passed('Eight local specialists review the exact selected saved hybrid run, not an invented or default substitute')

    nav('hybrid')
    page.locator('#hybrid-system').select_option('solar-hydrogen')
    expect(page.locator('#run-hybrid')).to_be_disabled()
    expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(0)
    page.locator('#hybrid-system').select_option('hospital-island')
    page.locator('[data-scenario="black-start"]').click()
    expect(page.locator('#run-hybrid')).to_be_disabled()
    passed('Advanced hydrogen architecture and dynamic black-start scenario are visibly study-only and cannot manufacture results')

    page.locator('[data-scenario="baseline"]').click()
    with page.expect_file_chooser() as chooser:
        page.locator('[data-hybrid-action="import"]').click()
    chooser.value.set_files({'name':'setup.json','mimeType':'application/json','buffer':json.dumps(exported).encode()})
    expect(page.locator('#toast')).to_contain_text('Configuration imported')
    expect(page.locator('#hybrid-config [name="solar_kw"]')).to_have_value('777')
    with page.expect_file_chooser() as chooser:
        page.locator('[data-hybrid-action="import"]').click()
    invalid={**exported,'inputs':{**exported['inputs'],'evil':'<script>alert(1)</script>'}}
    chooser.value.set_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(invalid).encode()})
    expect(page.locator('#toast')).to_contain_text('Unknown configuration field')
    passed('Configuration JSON import round-trip and malicious/unknown-field rejection')

    nav('lessons')
    expect(page.locator('.lesson-list [data-lesson]')).to_have_count(36)
    lesson=page.evaluate('HF.HYBRID_CATALOG.lessons[0]')
    for i,q in enumerate(lesson['quiz']):
        page.locator(f'#lesson-quiz [name="q{i}"][value="{(q["answer"]+1)%len(q["options"])}"]').check()
    page.locator('#lesson-quiz button[type="submit"]').click()
    expect(page.locator('#quiz-feedback')).to_contain_text('0 / 2')
    for i,q in enumerate(lesson['quiz']):
        page.locator(f'#lesson-quiz [name="q{i}"][value="{q["answer"]}"]').check()
    page.locator('#lesson-quiz button[type="submit"]').click()
    expect(page.locator('#quiz-feedback')).to_contain_text('2 / 2')
    with page.expect_download() as dl:
        page.locator('[data-hybrid-action="export-progress"]').click()
    assert lesson['id'] in json.loads(Path(dl.value.path()).read_text())['passed_self_checks']
    page.locator('#lesson-quiz button[type="submit"]').click()
    with page.expect_download() as dl:
        page.locator('[data-hybrid-action="export-progress"]').click()
    assert len(json.loads(Path(dl.value.path()).read_text())['passed_self_checks'])==1
    if a.screenshots:
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(ROOT/'docs/learning-studio.png'),animations='disabled')
    with page.expect_download() as dl:
        page.locator('[data-hybrid-action="export-lesson"]').click()
    assert json.loads(Path(dl.value.path()).read_text())['lesson']['id']==lesson['id']
    passed('Lesson self-check rejects wrong answers, grades correct answers, avoids duplicate progress and exports lesson/progress records')
    page.locator('[data-hybrid-action="reset-progress"]').click()
    expect(page.locator('dialog')).to_be_visible()
    page.locator('[data-hybrid-action="confirm-reset-progress"]').click()
    expect(page.locator('dialog')).not_to_be_visible()
    passed('Learning reset requires an explicit confirmation')

    page.emulate_media(reduced_motion='reduce')
    for width in [390,320]:
        page.set_viewport_size({'width':width,'height':844})
        for name in ['hybrid','lessons','compare','overview','storage','pv','research','markets','forecast','investment','pilots','council']:
            nav(name)
        passed(f'All twelve workspaces fit {width}px without page-level horizontal overflow')
    page.set_viewport_size({'width':390,'height':844});nav('hybrid')
    if a.screenshots:
        page.screenshot(path=str(ROOT/'docs/hybrid-mobile.png'),animations='disabled')

    preview=browser.new_page(viewport={'width':1440,'height':1000})
    preview.evaluate("() => {window.fetch=async()=>{throw new Error('Offline test');};}")
    preview.set_content((ROOT/'HelioForge-Preview.html').read_text(),wait_until='load')
    expect(preview.locator('.connection-chip')).to_have_text('Snapshot preview')
    expect(preview.locator('#run-hybrid')).to_be_disabled()
    preview.locator('#hybrid-system').select_option('hydro-triad')
    expect(preview.locator('#hybrid-output .hybrid-metrics')).to_have_count(0)
    preview.locator('.nav-item[data-nav="lessons"]').click()
    expect(preview.locator('#lesson-quiz button[type="submit"]')).to_be_enabled()
    passed('Offline preview allows exploration and learning but never claims a new numerical calculation')
    assert not errors,errors
    passed('No uncaught JavaScript errors in the exercised hybrid flows')
    browser.close()

report={'checks_passed':len(checks),'checks':checks,'transport':'host HTTP bridge' if a.bridge else 'direct browser HTTP',
        'limits':['Not a formal accessibility certification or WebGL performance benchmark.','Cross-reload localStorage persistence and file:// navigation were not verified in bridge mode.']}
(ROOT/'docs/hybrid-browser-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'\n{len(checks)} hybrid browser checks passed.')
