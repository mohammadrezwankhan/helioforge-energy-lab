"""Verify saved fresh deployed observations; no new network requests."""
import base64
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/remediation-20261028'
DEP = OUT / 'deployed'
obs = json.loads((DEP / 'observation.json').read_text())
browser = obs['browser']
rows = {r['path']: r for r in browser['routes']}
report = {'schema': 'helioforge.deployed-contract.v1', 'observed_at': obs['observed_at'],
          'scope': 'Saved fresh permitted-browser responses; one edge/session, not global cache propagation.',
          'checks': []}
def check(name, condition, actual):
    report['checks'].append({'name': name, 'status': 'PASS' if condition else 'FAIL', 'actual': actual})
check('deployed manifest and exact decoded runtime bytes', browser['digest_matches_manifest'], browser['runtime_response_sha256'])
for route, label in [('', 'overview'), ('about/', 'about'), ('methodology/', 'methodology')]:
    row = rows[route]
    body = (DEP / f'browser-{label}.body').read_bytes()
    text = body.decode('utf-8')
    check(f'{route or "/"} status and body identity', row['status'] == 200 and hashlib.sha256(body).hexdigest() == row['sha256'], row['sha256'])
    canonical = 'https://mkgrid.co.technology/' + route
    check(f'{route or "/"} canonical', bool(re.search(r'<link[^>]+rel="canonical"[^>]+href="' + re.escape(canonical) + '"', text)), canonical)
    structured = [json.loads(m) for m in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script\s*>', text, re.S | re.I)]
    check(f'{route or "/"} parseable structured data', bool(structured), {'blocks': len(structured)})
    policy = row['headers']['content-security-policy']
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'"
              for s in re.findall(r'<script\b[^>]*>(.*?)</script\s*>', text, re.S | re.I) if s.strip()]
    check(f'{route or "/"} inline scripts covered by effective CSP', all(h in policy for h in hashes), {'script_hashes': hashes})
robots = (DEP / 'browser-robots.txt.body').read_text()
sitemap = ElementTree.fromstring((DEP / 'browser-sitemap.xml.body').read_bytes())
urls = [x.text for x in sitemap.iter() if x.tag.endswith('loc')]
check('published three-page sitemap', set(urls) == {'https://mkgrid.co.technology/', 'https://mkgrid.co.technology/about/', 'https://mkgrid.co.technology/methodology/'}, urls)
check('runtime crawl permitted to observe noindex', not re.search(r'Disallow:\s*/run', robots, re.I) and 'noindex' in browser['headers'].get('x-robots-tag', ''), {'robots': robots, 'runtime_header': browser['headers'].get('x-robots-tag')})
redirect = rows['about?acceptance=20261028']
check('query preserved in redirect', redirect['status'] in {301, 308} and 'acceptance=20261028' in redirect['headers'].get('location', ''), redirect['headers'].get('location'))
missing = rows['missing-acceptance-20261028']
check('real missing-route HTTP 404', missing['status'] == 404, missing['status'])
runtime = (DEP / 'browser-runtime.body').read_bytes().decode('utf-8')
policy = browser['headers']['content-security-policy']
hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'" for s in re.findall(r'<script\b[^>]*>(.*?)</script\s*>', runtime, re.S | re.I) if s.strip()]
check('runtime inline scripts covered by effective CSP', all(h in policy for h in hashes), hashes)
report['summary'] = {status: sum(r['status'] == status for r in report['checks']) for status in ['PASS', 'FAIL']}
(OUT / 'deployed-contract-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report['summary']))
raise SystemExit(int(report['summary']['FAIL'] > 0))
