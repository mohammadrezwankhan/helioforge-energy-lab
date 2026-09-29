"""Browser regression checks. Start API first. --bridge supports restricted CI browsers.

Normal mode exercises HTTP directly. Bridge mode renders the shipped standalone HTML
and forwards fetch through a host-side HTTP client to the SAME running API. It does
not mock calculations. It does not test browser network policy/CSP or file:// navigation.
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
args = p.parse_args()
checks: list[str] = []

def passed(name: str) -> None:
    checks.append(name)
    print('PASS', name)

with sync_playwright() as pw, httpx.Client(base_url=args.url, timeout=40) as client:
    browser = pw.chromium.launch(executable_path=args.executable, headless=True,
                                 args=['--no-sandbox'] if args.executable else [])
    page = browser.new_page(viewport={'width':1600, 'height':1080}, device_scale_factor=1)
    errors: list[str] = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    def bridge(path: str, options: dict | None = None) -> dict:
        if not path.startswith('/api/'):
            raise ValueError('The test bridge permits only local API paths.')
        options = options or {}
        r = client.request(options.get('method','GET'), path,
                           headers=options.get('headers',{}), content=options.get('body'))
        return {'status':r.status_code, 'body':r.text,
                'headers':{'content-type':r.headers.get('content-type','application/json')}}

    if args.bridge:
        page.expose_function('hfTestTransport', bridge)
        page.evaluate('''() => { window.fetch = async (path, options) => {
            const r = await window.hfTestTransport(String(path), options || {});
            return new Response(r.body, {status:r.status, headers:r.headers});
        }; }''')
        page.set_content((ROOT/'HelioForge-Preview.html').read_text(), wait_until='load')
    else:
        page.goto(args.url+'/#overview', wait_until='networkidle')
    expect(page.locator('.connection-chip')).to_have_text('API connected')
    page.locator('.nav-item[data-nav="overview"]').click()
    expect(page.locator('h1')).to_contain_text('Command centre')
    passed('API-connected overview')
    if args.screenshots:
        page.screenshot(path=str(ROOT/'docs/dashboard-desktop.png'),full_page=True,animations='disabled')

    page.locator('#project-search').fill('no-such-project')
    expect(page.locator('#project-table')).to_contain_text('No projects match')
    page.locator('#project-search').fill('')
    page.locator('#portfolio-market').select_option('FR')
    expect(page.locator('.project-table tbody tr')).to_have_count(1)
    page.locator('#portfolio-market').select_option('ALL')
    passed('Portfolio search and country filter')
    with page.expect_download() as download:
        page.locator('[data-action="export-evidence"]').first.click()
    assert download.value.suggested_filename == 'helioforge-evidence.json'
    passed('Evidence JSON download')

    def nav(name: str) -> None:
        page.locator(f'.nav-item[data-nav="{name}"]').click()
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), name

    def run(model: str, values: dict[str,str]) -> None:
        form = page.locator(f'form[data-model="{model}"]')
        for name, value in values.items():
            form.locator(f'[name="{name}"]').fill(value)
        form.locator('button[type="submit"]').click()
        expect(page.locator('#toast')).to_contain_text('complete', timeout=30000)
        expect(page.locator(f'form[data-model="{model}"] button[type="submit"]')).to_be_enabled()

    nav('storage')
    run('storage', {'capacity_mwh':'12'})
    expect(page.locator('form[data-model="storage"] [name="capacity_mwh"]')).to_have_value('12')
    passed('Storage calculation, input commit and solver completion')
    if args.screenshots:
        page.screenshot(path=str(ROOT/'docs/storage-desktop.png'),full_page=True,animations='disabled')
    with page.expect_download() as download:
        page.locator('[data-action="export-dispatch"]').click()
    assert download.value.suggested_filename.endswith('.csv')
    passed('Dispatch CSV download')
    nav('pv'); run('pv', {'capacity_mwp':'60'})
    passed('PV economics recalculation')
    nav('research'); run('reliability', {'horizon':'4000'})
    expect(page.locator('form[data-model="reliability"]')).to_contain_text('4,000 h')
    run('sustainability', {'counterfactual':'200'})
    passed('Reliability and carbon recalculation')
    nav('markets')
    assert page.locator('a[href^="https://"]').count() >= 6
    passed('Market registry and primary-source links')
    nav('forecast'); run('forecast', {'seed':'57'})
    passed('Seeded price simulation')
    nav('investment'); run('finance', {'debt':'0'})
    expect(page.locator('.metrics-grid')).to_contain_text('No debt service')
    expect(page.locator('.plot-panel').first).to_contain_text('No applicable observations')
    passed('Debt-free finance case has no fabricated DSCR')
    run('finance', {'debt':'55'})
    run('acquisition', {'ev':'40'})
    passed('Leveraged finance and acquisition screen')
    nav('pilots')
    page.locator('[data-pilot]').first.click()
    expect(page.locator('dialog')).to_be_visible()
    page.locator('#pilot-form [name="status"]').select_option('running')
    page.locator('#pilot-form [name="evidence_note"]').fill('Browser test: synthetic instrumentation evidence reviewed; not a real field result.')
    page.locator('#pilot-form button[type="submit"]').click()
    expect(page.locator('#toast')).to_contain_text('Pilot evidence updated')
    assert client.get('/api/pilots/events').json()
    passed('Pilot evidence update and persisted audit event')
    nav('council')
    run('council', {'brief':'Review the synthetic storage case and highlight evidence gaps.'})
    expect(page.locator('.council-decision')).to_contain_text('LOCAL MODE')
    expect(page.locator('.review-card')).to_have_count(8)
    page.locator('#council-mode').select_option('openai')
    expect(page.locator('#external-consent')).to_be_visible()
    page.locator('#council-mode').select_option('local')
    passed('Local council review and external-processing consent UI')
    if args.screenshots:
        page.screenshot(path=str(ROOT/'docs/council-desktop.png'),full_page=True,animations='disabled')
    page.locator('[data-action="history"]').click()
    # History now exposes explicit per-record export controls, rather than whole-row buttons.
    expect(page.locator('#run-results [data-run]')).not_to_have_count(0)
    expect(page.locator('#run-results')).to_contain_text('saved')
    page.locator('[data-action="close-modal"]').click()
    passed('Saved model runs visible in history')
    page.locator('[data-action="motion"]').click()
    assert page.evaluate('document.documentElement.dataset.motion') == 'off'
    passed('Reduced-motion user control')
    page.emulate_media(reduced_motion='reduce')
    page.set_viewport_size({'width':390,'height':844})
    for name in ['overview','storage','pv','research','markets','forecast','investment','pilots','council']:
        page.locator('[data-action="menu"]').click()
        nav(name)
    passed('All nine workspaces fit 390px mobile viewport')
    page.locator('[data-action="menu"]').click(); nav('overview')
    if args.screenshots:
        page.screenshot(path=str(ROOT/'docs/dashboard-mobile.png'),full_page=True,animations='disabled')
    # Disconnected snapshot: verify no calculation pretends to have run.
    preview=browser.new_page(viewport={'width':1440,'height':900})
    preview.evaluate("() => { window.fetch = async () => { throw new Error('Offline test'); }; }")
    preview.set_content((ROOT/'HelioForge-Preview.html').read_text(), wait_until='load')
    expect(preview.locator('.connection-chip')).to_have_text('Snapshot preview')
    preview.locator('.nav-item[data-nav="storage"]').click()
    expect(preview.locator('button[type="submit"]')).to_be_disabled()
    passed('Standalone snapshot renders with calculations explicitly disabled')
    assert not errors, errors
    passed('No uncaught JavaScript errors')
    browser.close()
report={'checks_passed':len(checks),'checks':checks,'transport':'host HTTP bridge' if args.bridge else 'direct browser HTTP',
        'notes':'Bridge mode does not validate direct browser network, CSP enforcement, or file:// navigation.' if args.bridge else 'Browser HTTP tested.'}
(ROOT/'docs/browser-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'\n{len(checks)} browser checks passed.')
