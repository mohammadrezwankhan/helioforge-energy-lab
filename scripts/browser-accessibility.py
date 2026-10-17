"""Automated accessibility checks, including enhanced contrast; not a WCAG certification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8017')
parser.add_argument('--output',default='docs/roadmap/accessibility-report.json')
args=parser.parse_args()
report=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    page=browser.new_page(viewport={'width':1600,'height':1050},reduced_motion='reduce')
    page.goto(args.url,wait_until='networkidle')
    expect(page.locator('.connection-chip')).to_have_text('API connected')
    page.evaluate((ROOT/'apps/web/node_modules/axe-core/axe.min.js').read_text(encoding='utf-8'))
    for name in ['overview','hybrid','lessons','compare','storage','pv','research','markets','forecast','investment','pilots','council']:
        page.locator(f'.nav-item[data-nav="{name}"]').click()
        result=page.evaluate('async()=>await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag2aaa","wcag21aa","wcag22aa"]}})')
        item={'page':name,'violations':result['violations'],'incomplete':result['incomplete'],'passes':len(result['passes'])}
        report.append(item)
        print(name,json.dumps([{'id':v['id'],'nodes':len(v['nodes'])} for v in result['violations']]),flush=True)
    browser.close()
path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps({'tool':'axe-core 4.14.0','scope':'Default desktop states; incomplete checks and assistive-technology review remain external.','pages':report},indent=2),encoding='utf-8')
raise SystemExit(1 if any(item['violations'] for item in report) else 0)
