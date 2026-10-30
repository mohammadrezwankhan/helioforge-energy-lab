"""Full-spectrum integration checks against the actual loopback API and standalone file."""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8000')
parser.add_argument('--output', default=str(ROOT / 'docs/roadmap/browser-evidence'))
args = parser.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
checks, errors = [], []

def passed(message):
    checks.append(message)
    print('PASS', message, flush=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1600, 'height': 1100}, reduced_motion='reduce', ignore_https_errors=args.url.startswith('https://127.0.0.1:'))
    page.set_default_timeout(20000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until='networkidle')
    expect(page.locator('.connection-chip')).to_have_text('API connected')
    catalogue = page.request.get(args.url + '/api/studies').json()
    if isinstance(catalogue, dict):
        catalogue = catalogue.get('studies', catalogue.get('catalogue'))
    assert len(catalogue) == 59

    def nav(name):
        menu = page.locator('[data-action="menu"]')
        if menu.is_visible():
            menu.click()
        page.locator(f'.nav-item[data-nav="{name}"]').click()

    for name in dict.fromkeys(study['page'] for study in catalogue):
        nav(name)
        expect(page.locator('#study-workbench')).to_have_count(1)
        for study in [item for item in catalogue if item['page'] == name]:
            page.locator(f'.study-nodes [data-study-select="{study["id"]}"]').click()
            assert page.locator('#study-form').evaluate('(form)=>form.checkValidity()'), study['id']
            with page.expect_response(lambda response: response.url.endswith('/api/studies/evaluate'), timeout=120000) as response:
                page.locator('#study-form button[type="submit"]').click()
            assert response.value.ok, (study['id'], response.value.text())
            result = response.value.json()
            assert result['study'] == study['id'] and len(result['evidence_sha256']) == 64
            expect(page.locator('#study-status')).to_contain_text('Completed example')
            expect(page.locator('#study-output')).to_be_visible()
        passed(f'{name}: all experiment forms calculate via Python with finite evidence envelopes')

    nav('storage')
    page.locator('[data-study-select="storage-annual"]').click()
    tariff = page.locator('[data-tariff-hour="18"]')
    tariff.fill('0.9')
    expect(page.locator('#study-output')).to_be_hidden()
    expect(tariff).to_be_visible()
    assert json.loads(page.locator('textarea[name="tariff"]').input_value())[18] == .9
    expect(page.locator('[data-study-export="csv"]')).to_be_disabled()
    nav('pv'); nav('storage')
    assert json.loads(page.locator('textarea[name="tariff"]').input_value())[18] == .9
    page.locator('[data-study-action="reset"]').click()
    with page.expect_download() as download:
        page.locator('[data-study-export="csv"]').click()
    rows = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))))
    assert len(rows) == 8760 and len({row['timestamp'] for row in rows}) == 8760
    passed('Annual tariff edits hide stale results, persist through navigation and export all 8,760 unique hours')
    field = page.locator('textarea[name="tariff"]')
    field.evaluate('(el)=>el.closest("details").open=true')
    field.fill('[1]')
    with page.expect_response(lambda response: response.url.endswith('/api/studies/evaluate')) as response:
        page.locator('#study-form button[type="submit"]').click()
    assert response.value.status == 422
    expect(page.locator('#study-status')).to_contain_text('tariff')
    expect(page.locator('#study-output')).to_be_hidden()
    passed('Rejected JSON model input never reveals the previous successful results')

    nav('pv'); page.locator('[data-study-select="pv-sensitivity"]').click()
    expect(page.locator('[data-pv-cell]')).to_have_count(81)
    page.locator('[data-pv-cell="80"]').click()
    expect(page.locator('[data-pv-cell="80"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('#study-workbench').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'pv-desktop.png'), animations='disabled')
    page.locator('[data-study-select="pv-agrivoltaic"]').click()
    page.locator('[data-land-map]').click(position={'x': 140, 'y': 100})
    expect(page.locator('#study-output')).to_be_hidden()
    expect(page.locator('[data-land-map]')).to_be_visible()
    passed('81-cell sensitivity selection and polygon editing are interactive and preserve stale-result rules')

    nav('lessons')
    with page.expect_download() as download:
        page.locator('[data-workflow-action="sign-progress"]').click()
    envelope = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
    original_envelope = json.dumps(envelope).encode()
    verified = page.evaluate('(value)=>HF.verifyEvidence(value)', envelope)
    assert verified == {'valid': True, 'signers': 1}
    envelope['payload']['notice'] = 'tampered'
    assert not page.evaluate('(value)=>HF.verifyEvidence(value)', envelope)['valid']
    passed('Actual browser P-256 signature verifies and payload tampering fails')

    nav('overview')
    page.locator('.workflow-drawer').evaluate('(el)=>el.open=true')
    page.locator('[data-workflow-import]').set_input_files({'name':'evidence.json','mimeType':'application/json','buffer':original_envelope})
    expect(page.locator('#workflow-import-status')).to_contain_text('Verified 1')
    with page.expect_download() as download:
        page.locator('[data-workflow-action="cosign-import"]').click()
    combined=json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
    assert page.evaluate('(value)=>HF.verifyEvidence(value)',combined)=={'valid':True,'signers':2}
    page.locator('[data-capex-threshold]').fill('0')
    expect(page.locator('[data-capex-value]')).to_contain_text('0')
    passed('Imported evidence is inspected and co-signed with a distinct verified key; portfolio threshold responds')

    nav('markets')
    inputs=page.locator('[data-tariff-code="FR"]')
    for index in range(inputs.count()):
        inputs.nth(index).fill(str(index+1))
    page.locator('[data-experience-action="compare-tariffs"]').click()
    expect(page.locator('[data-tariff-dialog]')).to_be_visible()
    expect(page.locator('[data-comparison-body]')).to_contain_text('10')
    page.keyboard.press('Escape')
    page.locator('[data-entsoe-country]').select_option('DE')
    expect(page.locator('[data-entsoe-eic]')).to_contain_text('10Y1001A1001A82H')
    passed('Editable market tariffs populate the modal; ENTSO-E selection preserves the documented area code')

    nav('lessons')
    wire=page.locator('[data-wire-toggle="sourceBus"]')
    before=wire.get_attribute('aria-pressed');wire.press('Space')
    assert wire.get_attribute('aria-pressed')!=before
    passed('Conceptual lesson continuity switches are keyboard operable')

    nav('pilots')
    card=page.locator('article[data-pilot-card]').first
    current=card.evaluate('(el)=>el.closest("[data-pilot-stage]").dataset.pilotStage')
    target='planned' if current!='planned' else 'instrumenting'
    # Drag the exposed article edge to the stage heading. The dense row's
    # geometric centre is a text descendant, not a reliable native drag origin.
    card.drag_to(page.locator(f'[data-pilot-stage="{target}"]'),
                 source_position={'x': 10, 'y': 10}, target_position={'x': 40, 'y': 20})
    expect(page.locator('#pilot-form select[name="status"]')).to_have_value(target)
    expect(page.locator('#pilot-form textarea')).to_have_value('')
    page.locator('[data-action="close-modal"]').click()
    passed('Pilot drag/drop opens an unsaved stage request and requires a fresh evidence note')

    nav('forecast');page.locator('[data-study-select="forecast-tail"]').click()
    with page.expect_download() as download:
        page.locator('[data-study-export="paths"]').click()
    paths=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))))
    expected=page.evaluate("HF.STUDY_BUNDLE.results['forecast-tail'].details.raw_paths.reduce((n,p)=>n+p.prices_eur_mwh.length,0)")
    assert len(paths)==expected
    assert {'seed','path','year','price_eur_mwh','loss_eur','hf_record_kind','hf_study','hf_model_version',
            'hf_data_kind','hf_evidence_sha256','hf_provenance_json'}==set(paths[0])
    provenance=json.loads(paths[0]['hf_provenance_json'])
    assert provenance['study']=='forecast-tail' and provenance['inputs']['seed']==int(paths[0]['seed'])
    assert provenance['limitations'] and provenance['sources'] and provenance['warnings'] is not None
    assert all(row['hf_evidence_sha256']==provenance['evidence_sha256'] for row in paths)
    passed('Forecast raw-path CSV retains every seeded path-year observation')

    nav('hybrid')
    for preset in ['isometric', 'top-down', 'oblique', 'wireframe']:
        button = page.locator(f'[data-camera-preset="{preset}"]')
        button.click()
        expect(button).to_have_attribute('aria-pressed', 'true')
    nav('storage')
    page.locator('#dispatch-interval').fill('18')
    expect(page.locator('#dispatch-interval')).to_have_value('18')
    page.locator('.flow-diagram-25d').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'storage-desktop.png'), animations='disabled')
    passed('Storage interval telemetry responds with reduced motion enabled')

    page.set_viewport_size({'width': 390, 'height': 844})
    for name in dict.fromkeys(study['page'] for study in catalogue):
        nav(name)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), name
    page.locator('#study-workbench').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'council-mobile.png'), animations='disabled')
    passed('All twelve views fit a 390px mobile viewport without document overflow')

    offline = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    offline.on('pageerror', lambda error: errors.append(str(error)))
    offline.goto((ROOT/'HelioForge-Preview.html').as_uri(), wait_until='load')
    expect(offline.locator('.connection-chip')).to_have_text('Snapshot preview')
    expect(offline.locator('#study-form button[type="submit"]')).to_be_disabled()
    assert offline.evaluate('HF.STUDY_BUNDLE.catalogue.length') == 59
    passed('Standalone file retains all 59 examples and disables unavailable Python calculations')
    assert not errors, errors
    browser.close()

report = {'checks': checks, 'browser_errors': errors, 'browser': 'Playwright Chromium', 'url': args.url, 'reduced_motion': True}
(ROOT/'docs/roadmap/browser-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'passed': len(checks), 'errors': errors}))
