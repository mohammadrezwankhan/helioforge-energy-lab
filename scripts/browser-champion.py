"""Champion UI regressions against the real local Python API.

Default: direct browser HTTP and native localStorage. --bridge: host HTTP transport;
localStorage and randomUUID are test adapters on about:blank. The adapter validates
save/restore logic, NOT native browser storage or direct networking/CSP.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8000');p.add_argument('--bridge',action='store_true');p.add_argument('--executable',default=os.getenv('CHROMIUM_EXECUTABLE'));p.add_argument('--screenshots',action='store_true');a=p.parse_args()
checks=[];errors=[]
out=ROOT/'docs/champion';out.mkdir(parents=True,exist_ok=True)
def passed(text):
    checks.append(text);print('PASS',text,flush=True)

with sync_playwright() as pw,httpx.Client(base_url=a.url,timeout=40) as client:
    browser=pw.chromium.launch(executable_path=a.executable,headless=True,args=['--no-sandbox'] if a.executable else [])
    def bridge(path,options=None):
        if not path.startswith('/api/'):raise ValueError('Only local API requests are permitted.')
        o=options or {};r=client.request(o.get('method','GET'),path,headers=o.get('headers',{}),content=o.get('body'))
        return {'status':r.status_code,'body':r.text,'headers':{'content-type':r.headers.get('content-type','application/json')}}
    def new_page(cache=None,offline=False):
        page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(8000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        if a.bridge:
            page.expose_function('hfChampionTransport',bridge)
            page.evaluate('''({cache,offline})=>{
              window.__testCache=cache||{};
              Object.defineProperty(window,'localStorage',{configurable:true,value:{
                getItem:k=>window.__testCache[k]??null,setItem:(k,v)=>{if(window.__denyStorage)throw new Error('Test storage denied');window.__testCache[k]=String(v)},
                removeItem:k=>{delete window.__testCache[k]}
              }});
              if(!crypto.randomUUID)crypto.randomUUID=()=> '10000000-1000-4000-8000-100000000000'.replace(/[018]/g,c=>(+c^crypto.getRandomValues(new Uint8Array(1))[0]&15>>+c/4).toString(16));
              window.fetch=async(path,options)=>{
                if(offline)throw new Error('Offline test');
                if(window.__holdPath===path)await new Promise(resolve=>window.__release=resolve);
                const r=await window.hfChampionTransport(String(path),options||{});
                if(window.__failAfterSave===path){window.__failAfterSave=null;throw new Error('Injected response loss after API save');}
                return new Response(r.body,{status:r.status,headers:r.headers});
              };
            }''',{'cache':cache or {},'offline':offline})
            page.set_content((ROOT/'HelioForge-Preview.html').read_text(),wait_until='load')
        else:
            if offline:page.route('**/api/**',lambda r:r.abort())
            page.goto(a.url,wait_until='networkidle')
            if cache:
                page.evaluate('(cache)=>{for(const [k,v] of Object.entries(cache))localStorage.setItem(k,v)}',cache);page.reload(wait_until='networkidle')
        expect(page.locator('.connection-chip')).to_have_text('Snapshot preview' if offline else 'API connected')
        return page
    page=new_page()
    def nav(name):
        if page.locator('[data-action="menu"]').is_visible():page.locator('[data-action="menu"]').click()
        page.locator(f'.nav-item[data-nav="{name}"]').click()
    def run():
        page.locator('#run-hybrid').click();expect(page.locator('#toast')).to_contain_text('Hybrid energy screen complete',timeout=30000)
        expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(1)
    def cache():return page.evaluate("({[HF.WORKSPACE_KEY]:localStorage.getItem(HF.WORKSPACE_KEY)})")
    def close():page.locator('[data-action="close-modal"]').click()

    page.locator('#hybrid-config [name="battery_kwh"]').fill('')
    expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(0)
    expect(page.locator('#hybrid-output')).to_contain_text('Check')
    nav('lessons');nav('hybrid')
    expect(page.locator('#hybrid-config [name="battery_kwh"]')).to_have_value('')
    page.locator('#hybrid-config [name="battery_kwh"]').fill('1300')
    assert page.evaluate('''()=>{const b=document.querySelector('#champion-toolbar [data-champion-action="workspace"]');document.querySelector('[name="battery_kwh"]').dispatchEvent(new Event('change',{bubbles:true}));return b.isConnected}''')
    passed('Unchanged blur preserves toolbar button identity instead of consuming the next click')
    run();passed('HF-001: invalid in-progress hybrid input hides results immediately; raw input survives navigation and recovers')
    page.locator('[data-hybrid-action="pin"]').click()
    first_cache=cache();first_id=json.loads(first_cache['hf-workspace-v3'])['last_run_id'];assert first_id
    before=client.get('/api/runs/'+first_id).json();assert before['inputs']['battery_kwh']==1300

    nav('storage');page.locator('[name="capacity_mwh"]').fill('23');nav('pv');nav('storage')
    expect(page.locator('[name="capacity_mwh"]')).to_have_value('23')
    expect(page.locator('.draft-note')).to_contain_text('Unsaved input edits')
    passed('HF-002: unsubmitted model inputs survive workspace navigation and are labelled as uncalculated')
    page.locator('[name="capacity_mwh"]').fill('12');page.locator('form[data-model="storage"] button[type="submit"]').click()
    expect(page.locator('#toast')).to_contain_text('Calculation complete',timeout=30000)
    page.locator('[data-action="reconnect"]').click()
    expect(page.locator('#toast')).to_contain_text('Completed calculations retained')
    expect(page.locator('[name="capacity_mwh"]')).to_have_value('12')
    passed('HF-003: reconnect preserves a completed 12 MWh calculation instead of resetting it to 10 MWh')

    nav('hybrid');page.locator('#champion-toolbar [data-champion-action="workspace"]').click()
    name='Hospital reference <study>'
    page.locator('#save-setup-form [name="setup_name"]').fill(name);page.locator('#save-setup-form button[type="submit"]').click()
    expect(page.locator('.setup-row')).to_have_count(1);expect(page.locator('.setup-copy')).to_contain_text(name)
    saved_cache=cache();assert json.loads(saved_cache['hf-workspace-v3'])['saved_setups'][0]['name']==name
    assert page.locator('study').count()==0
    with page.expect_download() as dl:page.locator('[data-export-setup]').click()
    assert json.loads(Path(dl.value.path()).read_text())['schema']=='helioforge.hybrid.v1'
    passed('Named setup saves validated inputs, escapes its name and exports an import-compatible file')
    if a.screenshots:page.screenshot(path=str(out/'saved-setups-desktop.png'),animations='disabled')
    close();page.locator('#hybrid-config [name="battery_kwh"]').fill('1500')
    page.locator('#champion-toolbar [data-champion-action="workspace"]').click();page.locator('[data-load-setup]').click()
    expect(page.locator('[name="battery_kwh"]')).to_have_value('1300');expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(0)
    passed('Opening a saved setup restores exact inputs without pretending to calculate')
    page.locator('[data-action="history"]').click();page.locator('#run-search').fill(first_id)
    expect(page.locator('[data-restore-run]')).to_have_count(1);page.locator('[data-restore-run]').click()
    expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(1);expect(page.locator('[name="battery_kwh"]')).to_have_value('1300')
    assert client.get('/api/runs/'+first_id).json()==before
    passed('History filtering and run reopening preserve stored inputs/results without rewriting the API record')

    page.keyboard.press('Control+k');expect(page.locator('#command-search')).to_be_focused()
    page.locator('#command-search').fill('solar hydrogen');expect(page.locator('#command-results')).to_contain_text('Study only')
    page.keyboard.press('Enter');expect(page.locator('#hybrid-system')).to_have_value('solar-hydrogen');expect(page.locator('#run-hybrid')).to_be_disabled()
    page.keyboard.press('Control+k');page.locator('#command-search').fill('saved setups');page.keyboard.press('ArrowDown');page.keyboard.press('Enter')
    expect(page.locator('#save-setup-form')).to_be_visible();close()
    passed('Keyboard command palette finds study-only systems, navigates by Enter, and opens actions')
    page.locator('[data-champion-action="guide"]').click();page.locator('[data-champion-action="start-hospital"]').click()
    expect(page.locator('#hybrid-system')).to_have_value('hospital-island');run();page.locator('[data-hybrid-action="pin"]').click()
    current_cache=cache();parsed=json.loads(current_cache['hf-workspace-v3']);assert parsed['last_run_id'];assert len(parsed['pinned_run_ids'])==2
    page.close();page=new_page(current_cache)
    expect(page.locator('#hybrid-output .hybrid-metrics')).to_have_count(1)
    nav('compare');expect(page.locator('.compare-panel')).to_contain_text('2 pinned runs')
    passed('Workspace reconstruction restores named setups and verifies last result plus comparison IDs against the real API')
    nav('hybrid')
    if a.screenshots:page.screenshot(path=str(out/'champion-desktop.png'),animations='disabled')

    if a.bridge:
        ids_before={r['id'] for r in client.get('/api/runs').json()}
        page.evaluate("()=>{window.__holdPath='/api/hybrid/simulate'}")
        page.locator('#run-hybrid').click();expect(page.locator('#run-hybrid')).to_be_disabled()
        page.evaluate("()=>document.getElementById('run-hybrid').click()")
        nav('compare');nav('hybrid');expect(page.locator('#run-hybrid')).to_be_disabled();expect(page.locator('[name="battery_kwh"]')).to_be_disabled()
        page.evaluate('()=>{window.__holdPath=null;window.__release()}')
        expect(page.locator('#toast')).to_contain_text('Hybrid energy screen complete',timeout=30000)
        assert len({r['id'] for r in client.get('/api/runs').json()}-ids_before)==1
        passed('Pending-request navigation keeps inputs locked; repeated submit creates only one run')
        page.evaluate("()=>{window.__failAfterSave='/api/hybrid/simulate'}")
        ids_before={r['id'] for r in client.get('/api/runs').json()};page.locator('#run-hybrid').click()
        expect(page.locator('#toast')).to_contain_text('may have completed',timeout=30000)
        expect(page.locator('#run-hybrid')).to_be_enabled();assert len({r['id'] for r in client.get('/api/runs').json()}-ids_before)==1
        expect(page.locator('#toast')).to_contain_text('Check Analysis history')
        passed('Injected response loss after a real API save is reported as ambiguous, with recovery through history')

    page.locator('#champion-toolbar [data-champion-action="workspace"]').click();page.locator('[data-delete-setup]').click()
    expect(page.locator('#modal-title')).to_contain_text('Delete');page.locator('#modal [data-champion-action="workspace"]').click()
    expect(page.locator('.setup-row')).to_have_count(1)
    page.locator('[data-delete-setup]').click();page.locator('[data-confirm-delete]').click();expect(page.locator('.setup-row')).to_have_count(0);close()
    assert client.get('/api/runs/'+first_id).status_code==200
    passed('Deleting a setup requires confirmation and does not delete historical calculations')

    page.emulate_media(reduced_motion='reduce')
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        for view in ['hybrid','lessons','compare','overview','storage','pv','research','markets','forecast','investment','pilots','council']:
            nav(view)
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,view)
        passed(f'All 12 workspaces fit {width}px without document overflow')
    page.set_viewport_size({'width':390,'height':844});nav('hybrid')
    page.locator('[data-action="menu"]').click()
    assert page.locator('.app-main').evaluate('(e)=>e.inert')
    page.keyboard.press('Escape');expect(page.locator('[data-action="menu"]')).to_be_focused()
    assert page.locator('#sidebar').evaluate('(e)=>e.inert')
    passed('Mobile navigation uses inert background/hidden menu and restores focus on Escape')
    if a.screenshots:page.screenshot(path=str(out/'champion-mobile.png'),full_page=True,animations='disabled')
    page.locator('#champion-toolbar [data-champion-action="workspace"]').click()
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    if a.screenshots:page.screenshot(path=str(out/'saved-setups-mobile.png'),animations='disabled')
    close()

    bad=new_page({'hf-workspace-v3':'{broken-workspace'})
    expect(bad.locator('.workspace-notice')).to_contain_text('not been overwritten')
    bad.locator('[data-champion-action="workspace"]').first.click()
    with bad.expect_download() as dl:bad.locator('[data-champion-action="recovery-export"]').click()
    assert Path(dl.value.path()).read_text()=='{broken-workspace'
    bad.locator('[data-champion-action="recovery-reset"]').click();bad.locator('[data-champion-action="confirm-recovery-reset"]').click()
    assert json.loads(bad.evaluate('localStorage.getItem(HF.WORKSPACE_KEY)'))['schema']=='helioforge.workspace.v1'
    passed('Damaged workspace is retained, downloadable, and reset only after explicit confirmation')
    bad.close()
    if a.bridge:
        page.set_viewport_size({'width':1440,'height':900});page.evaluate('()=>{window.__denyStorage=true}')
        page.locator('#champion-toolbar [data-champion-action="workspace"]').click();page.locator('#save-setup-form [name="setup_name"]').fill('Memory only')
        page.locator('#save-setup-form button[type="submit"]').click();expect(page.locator('#toast')).to_contain_text('memory only')
        expect(page.locator('.workspace-dialog')).to_contain_text('in memory only');close()
        passed('Storage write failure retains setup in memory and never claims it was durably saved')
    offline=new_page(offline=True);expect(offline.locator('#run-hybrid')).to_be_disabled()
    offline.locator('[data-champion-action="guide"]').click();expect(offline.locator('.quick-start')).to_contain_text('local API')
    passed('Offline preview keeps new calculations disabled and states the local API prerequisite')
    assert not errors,errors;passed('No uncaught JavaScript exceptions in the checked journeys')
    browser.close()
report={'checks_passed':len(checks),'checks':checks,'transport':'host HTTP bridge' if a.bridge else 'direct browser HTTP','storage':'test adapter on about:blank' if a.bridge else 'native browser localStorage','limitations':['No physical-device, assistive-technology or human UAT sessions.']+(['No direct browser networking, CSP, file launch, or native storage durability verified.'] if a.bridge else [])}
(out/'browser-champion.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(checks)} Champion checks passed.',flush=True)
