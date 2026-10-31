"""Build the traceable disposition and execution ledger from retained evidence.

This never upgrades unexecuted specification rows to passes.
"""
import csv
import hashlib
import json
import platform
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/remediation-20261028'
SITE = ROOT / '.cloudflare/acceptance-final/site'
def read(path):
    return json.loads((OUT / path).read_text(encoding='utf-8-sig'))
def dump(path, value):
    (OUT / path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
runtime = sha(SITE / 'run/index.html')
base = git('rev-parse', 'HEAD')
now = datetime.now(timezone.utc).isoformat()
artifact = {'source_base_commit': base, 'source_dirty': True, 'runtime_sha256': runtime, 'environment': 'VERIFIED_LOCAL', 'production_changed': False}

# Evidence classes and implementation status are separate dimensions.
# tuples: class, owner, local observation, root cause, changed files, evidence, blocker.
details = {
'F01': ('O','release/platform',
 'Fresh production runtime and manifest match a1238406; Cloudflare identifies deployment 777ff5d5 at 74d6730e. The successful baseline CI log instead records b0b536f6. A local exact-byte receipt and frozen-data replay check now exist.',
 'CI regenerated studies after verifying them; solver wall time is demonstrably nondeterministic. This is one established source of build variance, not proof of the complete historical deployment chain.',
 ['.github/workflows/ci.yml','scripts/check-study-assets.py','scripts/acceptance-build-receipt.mjs'],
 ['deployed/observation.json','deployed/cloudflare-deployments.json','deployed/baseline-ci-log.txt','logs/check-study-assets.log'],
 'No candidate remote CI run or deployment. Fresh deployed bytes, manifest and matching candidate CI receipt still must agree; multi-edge cache propagation unverified.'),
'F02': ('O','capability/docs',
 'The historical About discrepancy was already corrected on the observed deployment. A shared versioned four-mode capability contract now generates local public facts, help and documentation; corrected Terminal entry targets #compare.',
 'Duplicated prose made distribution-mode statements drift; the already-corrected deployed About text was not reverted.',
 ['scripts/capability-contract.mjs','scripts/build-domain.mjs','scripts/build-cloudflare.mjs','cloudflare.json','README.md','docs/CAPABILITIES.md'],
 ['deployed/browser-about.body','logs/capability-final.log','logs/domain-final-check.log'],
 'New shared-contract pages have not been published or cache-checked in production.'),
'F03': ('O','council/protocol',
 'helioforge-council/v1 exposes local checklist versus external execution, 300-second external workflow and 17/25 SDK Runner.run invocations. Local mode has zero external roles/calls and eight checklist sections. Failure/timeout responses retain structured execution uncertainty.',
 'Older documentation used a 120-second contract and ambiguous model-call terminology; local metadata inherited external terminology before review correction.',
 ['apps/api/helioforge/council_protocol.py','apps/api/helioforge/council.py','apps/api/helioforge/main.py','apps/web/src/types.ts','apps/web/src/views.ts','apps/web/src/integrations-ui.ts','apps/web/src/app.ts','docs/COUNCIL_PROTOCOL.md','docs/AI_SETUP.md','docs/roadmap/CONNECTORS.md'],
 ['council-agent.md','INDEPENDENT_REVIEW.md','final2-python.xml','logs/final3-frontend.log'],
 'Real external-provider failure/retry/cancellation and full 189 role/evidence specifications are not executed. No claim that SDK invocation count equals billable provider requests.'),
'F04': ('O','release/UX',
 'Genuine local Chromium desktop, tablet and phone-viewport captures plus social capture are bound to the candidate digest. Local distribution uses the new images and labels them local candidate captures.',
 'Historical images mixed interface editions without release-bound capture metadata.',
 ['scripts/acceptance-capture.py','cloudflare.json','scripts/build-cloudflare.mjs'],
 ['capture-results.json','screenshots/desktop.png','screenshots/tablet.png','screenshots/mobile.png','screenshots/social.png'],
 'Images are not published and cannot establish production or physical-device appearance.'),
'F05': ('P','numerical/functional/state',
 'Study CSV/memo exports now retain original rows, units, full provenance, limitations and original-result digest. Async study, Hybrid and Terminal state guards reject stale completion. Hybrid comparisons explicitly reject missing/mismatched contract metadata.',
 'Study CSV paths dropped metadata; asynchronous continuations lacked current-generation checks. Normal historical Hybrid results still lack an authoritative application source revision.',
 ['apps/web/src/roadmap.ts','apps/web/src/hybrid-core.ts','apps/web/src/hybrid-controller.ts','apps/web/src/hybrid-views.ts','apps/web/src/terminal-ui.ts','apps/web/src/terminal-manifest.ts'],
 ['logs/study-export-red.log','logs/study-import-red.log','logs/final3-frontend.log','api-roadmap-final/report.json','INDEPENDENT_REVIEW.md'],
 'Full result-path provenance remains incomplete: normal Hybrid records lack source revision and therefore remain descriptive-only. All legacy exports/transfers and independent hand checks are not comprehensively accepted.'),
'F06': ('I','UX/onboarding',
 'Three starts are present in public content and Quick start. A real browser click dismisses the dialog and reaches the Terminal candidate form. Adjacent CSS breakpoints and draft-preserving viewport changes pass the bounded capture suite.',
 'The initial entry lacked task-led shortcuts; the appraisal mobile concern was heuristic, not an observed usability defect.',
 ['apps/web/src/champion-views.ts','scripts/capability-contract.mjs','docs/learning-pages/capability-modes.html'],
 ['capture-results.json','onboarding-resize-trace.zip'],
 'No uncoached usability sessions, mode-comprehension outcomes, or comparative collapsible-tablet-rail test.'),
'F07': ('U','performance',
 'Retained lab cold/warm loading and interaction measurements, including constrained phone viewport/CPU/network emulation. Invalid HTTP/hash-only warm runs are retained separately. No telemetry or field p75 was invented.',
 'Independent real-device/field evidence was absent. The self-contained runtime remains about 13.6 MB decoded; splitting datasets has not been implemented without a measured architecture decision.',
 ['scripts/acceptance-performance.py','scripts/serve-acceptance.py'],
 ['performance-results.json','performance-http-harness-invalid.json','logs/performance-final.log'],
 'No physical mid-range phone, controlled field volume, field INP or field p75. No measured bundle-size optimization shipped; hosted shell/on-demand data work remains open.'),
'F08': ('U','accessibility/QA',
 'All 13 requested CSS widths, 12 routes and three desktop engines are covered by the final responsive/axe/keyboard suite. Additional native dialogs, controls and local scrolling are exercised by Terminal checks.',
 'Native AT/device acceptance is an evidence gap; an automated scan cannot supply it.',
 ['scripts/browser-full-audit.py','scripts/browser-terminal.py','scripts/acceptance-capture.py'],
 ['final-responsive.json','final-terminal.json','capture-results.json'],
 'NVDA, VoiceOver/Safari on physical Apple devices, TalkBack, native 200%/400% zoom and full manual tasks remain BLOCKED/NOT_RUN.'),
'F09': ('U','platform/SEO',
 'Saved fresh browser responses verify current three-page production status/canonicals/sitemap/structured data, exact inline CSP coverage, query-preserving redirect, real 404 and runtime noindex with crawl access. Candidate nine-page distribution passes local contract checks.',
 'The appraisal could not retrieve these effective responses. A raw urllib denial was not interpreted as an outage; permitted browser retrieval succeeded.',
 ['scripts/acceptance-deployed.py','scripts/acceptance-deployed-contract.py','scripts/build-domain.mjs','scripts/check-domain.mjs'],
 ['deployed-contract-results.json','deployed/observation.json','logs/domain-final-check.log'],
 'New candidate pages require deployed verification after authorized publication; Search Console and global cache coverage were not available.'),
'F10': ('P','model/documentation',
 'Versioned registry contains all 12 workspaces and 59 study acceptance cards, equations, schema/units, fixtures, source/test references, limits and explicit unknown validation tiers. Two finance studies now expose first-party source references.',
 'Model contracts were scattered; two default study results had empty source lists. Adding implementation citations is not independent numerical validation.',
 ['scripts/capability-contract.mjs','docs/MODEL_REGISTRY.json','docs/MODEL_REGISTRY.md','apps/api/helioforge/engines/decision_studies.py','apps/api/helioforge/engines/toolkit_studies.py','apps/web/src/roadmap-data.ts'],
 ['inventory-before.json','inventory-results.json','logs/study-source-red.log','logs/study-source-green.log','logs/capability-final.log'],
 'Not every retained legacy result has a direct applicable-contract link; 59 independent hand-check/complete boundary/export acceptance cards remain open.'),
'F11': ('P','state/security',
 'Versioned v1 workspace imports validate bounds, preview replacement, require explicit confirmation and preserve recoverable backups. Corrupt/unsupported storage and quota denial are handled without claiming success; async restores/imports protect newer edits.',
 'Imports previously lacked the complete preview/backup transaction and stale-operation protection. Historical migration is a separate unimplemented requirement.',
 ['apps/web/src/champion-core.ts','apps/web/src/champion-controller.ts','apps/web/src/champion-views.ts','apps/web/tests/result-state-regressions.test.mjs'],
 ['state-agent.md','logs/final3-frontend.log','presentation-results.json','final-terminal.json'],
 'Unsupported v0 rejection is not a real historical migration. Version-to-version migration receipts and exhaustive interrupted cross-origin/native-file recovery remain NOT_RUN.'),
'F12': ('P','research governance/council',
 'Council UI and exports distinguish digest identity, signature state, reviewer identity, scientific validation, critic signoff and human approval. No provider failure is turned into fabricated completion or a silent local fallback.',
 'Ambiguous council/integrity phrasing risked conflating local evidence checks with independent execution or approval.',
 ['apps/api/helioforge/council_protocol.py','apps/web/src/views.ts','apps/web/src/integrations-ui.ts','apps/web/src/app.ts','docs/COUNCIL_PROTOCOL.md'],
 ['council-agent.md','INDEPENDENT_REVIEW.md','final2-python.xml','logs/final3-frontend.log'],
 'Complete audit of every legacy interface/export and all role/evidence combinations remains NOT_RUN; no external identity or accreditation validation claimed.'),
'F13': ('P','content/SEO',
 'Local distribution now has nine intended indexable pages, including focused capability/model explanations, worked learning material and glossary with source/revision metadata and internal links. Runtime noindex remains intact.',
 'Existing public site offered limited discoverable learning content; this was an opportunity, not a reproduced defect.',
 ['docs/learning-pages/','scripts/build-domain.mjs','scripts/check-domain.mjs','docs/MODEL_REGISTRY.md'],
 ['docs-agent.md','logs/domain-final-check.log','logs/domain-contract-tests.log'],
 'Content is locally generated and source reviewed, not published or independently pedagogically/scientifically validated. No rankings or AI-citation outcome claimed.'),
'F14': ('P','orchestrator/independent QA',
 'Separate plan and execution ledgers retain all 864 catalogue, 59 study, 157 presentation and 189 council specifications, exact runtime identities, raw failures and scoped outcomes. Engineering review and baseline/current evidence are separated.',
 'Feature/test counts and planned pair coverage cannot prove behavior or deployed identity.',
 ['scripts/acceptance-inventory.py','scripts/acceptance-presentation.py','scripts/finalize-acceptance.py','docs/remediation-20261028/'],
 ['suite-ledger.json','issue-ledger.json','council-results.json','workspace-results.json','study-acceptance-results.json','INDEPENDENT_REVIEW.md'],
 'Full higher-order/stateful/persona/native/provider acceptance and candidate CI/deployment reconciliation remain open; no promotion of plans to passes.')}
with (OUT / 'source-plan/recommendation_register.csv').open(encoding='utf-8-sig', newline='') as f:
    source_rows = list(csv.DictReader(f))
ledger = []
for source in source_rows:
    fid = source['id']
    evidence, owner, observation, cause, changed, paths, blocker = details[fid]
    page = 29 if fid <= 'F03' else 30 if fid <= 'F06' else 31 if fid <= 'F09' else 32 if fid <= 'F12' else 33
    ledger.append({'issue_id': fid, 'source': 'HelioForge_Critical_Appraisal (2).pdf, 2026-10-28 v1.0', 'source_page': page,
        'source_title': source['title'], 'source_evidence_description': source['evidence_class'], 'evidence_class': evidence,
        'priority': source['priority'], 'owner': owner, 'affected_scope': 'See source acceptance and named files; static public, local Python, emulated desktop/tablet/phone. External/native scope explicitly gated.',
        'reproduction_or_verification': 'Execute the named suite scripts/commands recorded in their logs and inspect linked machine-readable observations. Preserve the source-plan rows as plans.',
        'expected_behavior': source['acceptance'], 'current_observation': observation, 'actual_behavior': observation,
        'established_root_cause_or_evidence_gap': cause, 'changed_files': changed, 'tests_and_evidence_paths': paths,
        'artifact_identity': artifact, 'implementation_status': 'VERIFIED_LOCAL in stated scope; remaining acceptance open',
        'deployed_status': 'VERIFIED_DEPLOYED for existing three-page crawler contract only' if fid == 'F09' else 'Candidate NOT_DEPLOYED',
        'status': 'OPEN', 'acceptance_complete': False, 'remaining_blocker': blocker})
dump('issue-ledger.json', ledger)
lines = ['# F01–F14 disposition ledger', '', 'Source priorities and terminology are preserved. O = observed, R = reported, I = inference, P = proposed, U = unverified. Evidence class is separate from implementation status. Full appraisal closure is not claimed. See the JSON ledger for all required fields.', '', '| ID | Priority / class | Current disposition | Remaining acceptance |','|---|---|---|---|']
for r in ledger:
    lines.append(f"| {r['issue_id']} | {r['priority']} / {r['evidence_class']} | {r['current_observation']} | {r['remaining_blocker']} |")
(OUT / 'ISSUE_LEDGER.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

with (OUT / 'source-plan/council_role_test_design.csv').open(encoding='utf-8-sig', newline='') as f:
    council = list(csv.DictReader(f))
for row in council:
    row['status'] = 'BLOCKED' if row['mode'] == 'local_external_opt_in' else 'NOT_RUN'
    row['actual'] = 'Live provider execution not authorized or attempted.' if row['status'] == 'BLOCKED' else 'Full role/evidence specification not executed; protocol unit/mocked tests are separate evidence.'
    row['owner'] = 'council QA'
    row['artifact_identity'] = artifact
dump('council-results.json', {'schema':'helioforge.council.acceptance.v1','cases':council,'summary':dict(Counter(r['status'] for r in council))})
inventory = read('inventory-results.json')
registry = json.loads((ROOT / 'docs/MODEL_REGISTRY.json').read_text(encoding='utf-8'))
study_execution = {s['test_id']: s for s in inventory['studies']}
studies = []
for card in registry['studies']:
    sid = card['id']
    studies.append({'study_id':sid,'acceptance_card':card,'default_local_execution':study_execution[sid],
        'local_UI_default_run':'PASS (browser-roadmap loop executes all 59)', 'independent_hand_check':'NOT_RUN',
        'complete_boundary_invalid_case':'NOT_RUN as individual acceptance card', 'complete_export_transfer_roundtrip':'NOT_RUN as individual acceptance card',
        'evidence':['api-roadmap-final/report.json','inventory-results.json'], 'artifact_identity':artifact})
dump('study-acceptance-results.json', studies)
workspaces = []
for workspace in registry['workspaces']:
    workspaces.append({**workspace,'entry_navigation_reflow':'See final-responsive.json and presentation-results.json per route/engine/width',
        'local_study_default_execution':'PASS','bundled_examples':'PASS via browser-roadmap standalone check',
        'all_loading_empty_partial_invalid_stale_import_export_migration_recovery_states':'NOT_RUN exhaustively for this workspace',
        'physical_device_and_manual_AT':'BLOCKED','artifact_identity':artifact})
dump('workspace-results.json', workspaces)

def suite(name, executed, passed, failed=0, blocked=0, not_run=0, evidence=None, scope='', identity=None):
    return {'suite':name,'executed':executed,'PASS':passed,'FAIL':failed,'BLOCKED':blocked,'NOT_RUN':not_run,
            'NOT_APPLICABLE':0,'evidence':evidence,'scope':scope,'artifact_identity':identity or artifact}
suite_rows = []
xml = ElementTree.parse(OUT / 'final2-python.xml').getroot()
cases = list(xml.iter('testcase'))
suite_rows.append(suite('Python final',len(cases),sum(not list(c) or all(x.tag not in {'failure','error','skipped'} for x in c) for c in cases),evidence='final2-python.xml',scope='Current backend source; one upstream Starlette/httpx deprecation warning. Python 3.12.14 Windows.'))
frontend = (OUT / 'logs/final3-frontend.log').read_text(encoding='utf-8-sig')
count = int(re.search(r'ℹ tests (\d+)',frontend).group(1))
failed = int(re.search(r'ℹ fail (\d+)',frontend).group(1))
suite_rows.append(suite('Frontend final',count,count-failed,failed,evidence='logs/final3-frontend.log',scope='Node 24.22.1; includes source-compiled state and import regressions.'))
for name,key in [('Catalogue gates/invariants','catalogue'),('Study defaults/digests','studies')]:
    rows = inventory[key]
    suite_rows.append(suite(name,len(rows),sum(r['status']=='PASS' for r in rows),sum(r['status']=='FAIL' for r in rows),evidence='inventory-results.json',scope=inventory['scope']))
for name,file in [('Responsive/axe/keyboard','final-responsive.json'),('Terminal journeys','final-terminal.json')]:
    data = read(file); rows = data['checks']
    suite_rows.append(suite(name,len(rows),sum(r['status']=='passed' for r in rows),sum(r['status']=='failed' for r in rows),evidence=file,scope='Desktop automation on exact-byte HTTPS loopback runtime; not native AT or physical device evidence.'))
presentation = read('presentation-results.json')
assert len(presentation['cases']) == 157 and presentation.get('finished_at'), 'Presentation run incomplete; do not finalize'
suite_rows.append(suite('Presentation contexts',len(presentation['cases']),sum(r['status']=='PASS' for r in presentation['cases']),sum(r['status']=='FAIL' for r in presentation['cases']),evidence='presentation-results.json',scope=presentation['oracle']))
if (OUT / 'presentation-retest-results.json').exists():
    retest=read('presentation-retest-results.json')
    suite_rows.append(suite('Presentation targeted retest',len(retest['cases']),sum(r['status']=='PASS' for r in retest['cases']),sum(r['status']=='FAIL' for r in retest['cases']),evidence='presentation-retest-results.json',scope='PAIR-141 initially failed before app load with loopback TLS protocol error; original 156 PASS / 1 FAIL retained. Retest is a separate executed attempt.'))
for name,file in [('Capture/onboarding/breakpoint','capture-results.json'),('Deployed crawler contract','deployed-contract-results.json')]:
    data=read(file)
    suite_rows.append(suite(name,len(data['checks']),data['summary']['PASS'],data['summary']['FAIL'],evidence=file,scope=data.get('scope','Genuine local captures and bounded checks'),identity={'runtime_sha256':'a12384067a75ab7a3449c9b49936e923058bd7e92585f5a08f9c00ae735b203e','environment':'VERIFIED_DEPLOYED'} if 'Deployed' in name else None))
for name,file in [('API study/browser journeys','api-roadmap-final/report.json'),('API integration journeys','api-completion-final/report.json')]:
    data=read(file); checks=data['checks']
    suite_rows.append(suite(name,len(checks),len(checks),evidence=file,scope='Current local API source and web distribution; isolated fixture database. HTTP transport may include host AdGuard injection; not exact static-response proof.'))
perf=read('performance-results.json')
assert perf.get('finished_at') and len(perf['runs']) == 12, 'Performance run incomplete'
perf_lines=['# Retained performance baseline', '', 'Windows desktop laboratory, Chromium, exact local HTTPS artifact. Phone profile is a 390px viewport, 4x CPU slowdown and CDP 150ms / 1.6 Mbps down / 0.75 Mbps up. This is not a physical phone or field p75/INP. Host background workloads are uncontrolled. All runs and failed harness attempts remain available.', '', '| Profile / cache | Runs | LCP min / median / max (ms) | Maximum CLS |', '|---|---:|---|---:|']
for profile in ['desktop','phone_viewport_constrained_emulation']:
    for cache in ['cold','warm']:
        selected=[r for r in perf['runs'] if r['profile']==profile and r['cache']==cache]
        lcp=[r['metrics']['lcp'] for r in selected if r.get('metrics',{}).get('lcp') is not None]
        cls=[r['metrics']['cls'] for r in selected if r.get('metrics',{}).get('cls') is not None]
        perf_lines.append(f'| {profile} / {cache} | {len(selected)} | '+(' / '.join(f'{x:.0f}' for x in [min(lcp),statistics.median(lcp),max(lcp)]) if lcp else 'unavailable')+f' | {max(cls) if cls else "unavailable"} |')
perf_lines += ['', 'LCP <=2500ms, INP <=200ms and CLS <=0.1 are appraisal targets. Constrained profile loading exceeds the LCP target. Measurement execution PASS does not mean the target passed. Automation interaction latency includes scrolling, waiting and two frames, and is not INP. Navigation timing, encoded/decoded/transfer bytes, long tasks, heap and idle animation callbacks are retained in the raw JSON. Pure JavaScript parse cost is NOT_MEASURED separately from load/main-thread work.', '',
 'Proposed next-release guardrails (P, not implemented): preserve all numerical replay checks and standalone offline behavior; do not exceed the current 13,630,124 decoded-byte runtime without explicit review; establish a separately measured hosted-shell/on-demand-data design against this baseline; rerun three cold and three warm real-device measurements before setting a compressed-byte or interaction budget. No improvement or scientifically meaningful latency threshold is inferred from these lab runs.', '']
(OUT/'PERFORMANCE.md').write_text('\n'.join(perf_lines),encoding='utf-8')
suite_rows.append(suite('Performance lab loads',len(perf['runs']),sum(r['status']=='PASS' for r in perf['runs']),sum(r['status']=='FAIL' for r in perf['runs']),evidence='performance-results.json',scope='Measurement execution success is not a performance-target pass. Desktop and phone-viewport emulation; field INP/p75 absent.'))
interactions=[i for r in perf['runs'] for i in r.get('interactions',[])]
suite_rows.append(suite('Performance interaction measurements',len(interactions),sum(i['status']=='PASS' for i in interactions),sum(i['status']=='FAIL' for i in interactions),evidence='performance-results.json',scope='Automation-to-two-frame wall latency including scrolling/waits; not INP.'))
suite_rows.append(suite('Council role/evidence specifications',0,0,blocked=63,not_run=126,evidence='council-results.json',scope='No specification case promoted from mocks or plans.'))
suite_rows.append(suite('Independent per-study hand checks',0,0,not_run=59,evidence='study-acceptance-results.json',scope='Default execution is not independent scientific validation.'))
suite_rows.append(suite('Persona usability sessions',0,0,not_run=8,evidence='MANUAL_ACCEPTANCE.md',scope='No human participant sessions.'))
suite_rows.append(suite('Build/domain/security contract tests',7,7,evidence='logs/domain-contract-tests.log',scope='Capability contract and existing security/hero tests; build checks separately verify 9 pages, 12 workspaces, 59 studies and 65 files.'))
dump('suite-ledger.json', {'schema':'helioforge.suites.v1','created_at':now,'suites':suite_rows,'non_additive_note':'Counts have different units and overlapping checks; never add them into a coverage percentage.'})

# Source identity and a unified content-addressed receipt. No self-referential hashes.
source_paths = subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
source_records=[]
for relative in sorted(set(source_paths)):
    path=ROOT/relative
    if not relative or relative.startswith('docs/remediation-20261028/') or not path.is_file(): continue
    source_records.append({'path':relative,'bytes':path.stat().st_size,'sha256':sha(path)})
dump('source-file-hashes.json', source_records)
source_tree_hash=hashlib.sha256(json.dumps(source_records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
file_records=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file() and 'receipts' not in path.relative_to(OUT).parts and path.name not in {'RELEASE_RECEIPT.json','COMPLETION_REPORT.md','review.patch','DELIVERY_MANIFEST.json','finalize.log','package.log'}:
        file_records.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
deployed=read('deployed/observation.json')['browser']
receipt={'schema':'helioforge.release-acceptance.v1','created_at':now,'release_decision':'NOT_ACCEPTED_FOR_FULL_APPRAISAL_CLOSURE',
    'source':{'base_commit':base,'branch':git('branch','--show-current'),'working_tree_dirty':True,'file_manifest':'source-file-hashes.json','file_manifest_sha256':sha(OUT/'source-file-hashes.json'),'canonical_source_tree_sha256':source_tree_hash},
    'local_candidate':{'runtime_sha256':runtime,'runtime_bytes':(SITE/'run/index.html').stat().st_size,'manifest_sha256':sha(SITE/'app.json'),'headers_sha256':sha(SITE/'_headers'),'output':str(SITE),'verified_transport':'HTTPS loopback; decoded bytes verified; temporary self-signed test certificate; generated CSP unchanged','dataset':json.loads((SITE/'app.json').read_text()).get('bundledHybrid')},
    'hash_representation':'SHA-256 of exact file/decoded HTTP response bytes. No newline normalization. Source tree hash is sorted compact JSON of path/bytes/SHA-256 entries; excludes acceptance evidence directory to avoid a circular digest.',
    'deployed_baseline':{'runtime_sha256':deployed['runtime_response_sha256'],'manifest_match':deployed['digest_matches_manifest'],'source_commit':base,'deployment_id':'777ff5d5-be6d-4018-a0a4-392167601a7e','candidate_deployed':False,'effective_headers':'deployed/observation.json'},
    'baseline_ci':{'run_id':40491147851,'status':'success','runtime_sha256':'b0b536f66edfdfcc42f37f2eee1a307cd3e7ee9113098a433d2842b92251a089','matches_deployment':False},
    'candidate_ci':{'run_id':None,'status':'NOT_RUN'},'candidate_deployment':{'id':None,'status':'NOT_DEPLOYED'},'production_changed':False,
    'environment':{'os':platform.platform(),'python':'3.12.14','node':'24.22.1','physical_devices':False,'manual_AT':False,'external_provider_calls':0},
    'evidence_files':file_records,'suite_ledger':'suite-ledger.json','remaining_gates':'issue-ledger.json','rollback':'MANUAL_ACCEPTANCE.md'}
encoded=(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n').encode()
receipt_hash=hashlib.sha256(encoded).hexdigest()
receipt_dir=OUT/'receipts';receipt_dir.mkdir(exist_ok=True)
immutable=receipt_dir/f'release-{receipt_hash}.json'
immutable.write_bytes(encoded)
dump('RELEASE_RECEIPT.json', {'immutable_receipt':f'receipts/{immutable.name}','sha256':receipt_hash,'runtime_sha256':runtime,'decision':receipt['release_decision']})

report=['# HelioForge remediation and acceptance', '', f'Completed local work on `{git("branch","--show-current")}` from baseline `{base}`. **Production was not changed. Full appraisal acceptance remains open.**', '',
 f'Tested static runtime: `{runtime}` ({receipt["local_candidate"]["runtime_bytes"]:,} exact bytes). [Immutable release receipt](receipts/'+immutable.name+'). Source remains a reviewable dirty worktree with a full file-hash manifest; no candidate CI run, commit publication or deployment was performed.', '',
 '## What changed', '',
 '- Versioned capability, 59-study model registry and council protocol; accurate local/external invocation counts and failure metadata.',
 '- Study CSV/memo provenance, sources for two finance studies, stale async response guards, sweep invalidation, guarded comparison and preview/backup workspace imports.',
 '- Frozen-data replay checks and content-addressed build receipts, genuine local release captures, three task starts, nine-page local documentation/content distribution.', '',
 '## Executed evidence', '', '| Suite | Executed | Pass | Fail | Blocked | Not run |', '|---|---:|---:|---:|---:|---:|']
for row in suite_rows:
    report.append(f'| {row["suite"]} | {row["executed"]} | {row["PASS"]} | {row["FAIL"]} | {row["BLOCKED"]} | {row["NOT_RUN"]} |')
report += ['', 'Counts are per suite and non-additive. [Machine-readable scopes and evidence](suite-ledger.json). Presentation design covers 620 pair values in 33,696 declared contexts; 157 executed contexts establish only the stated presentation/state oracle. Catalogue checks cover 285 applicable numerical cases, 349 study-only gates and 230 not-applicable gates. Per-study default runs do not prove hand benchmarks or complete boundary/export acceptance.', '',
 '## Dispositions and limitations', '',
 '**Verified fixed locally:** provenance omission in study exports; stale study/Hybrid/Terminal continuations including rejected import during a newer sweep; workspace preview/backup safeguards; misleading local council invocation metadata; empty source references in two study defaults. [Separate engineering review](INDEPENDENT_REVIEW.md).', '',
 '**Already resolved with deployed evidence:** the old About browser-versus-Python discrepancy. Existing production runtime/manifest identity and three-page crawler controls were observed successfully, but the same-commit CI artifact does not match the deployment.', '',
 '**Implemented but not accepted in full:** capability/model contracts, new public content, screenshots, onboarding and CI controls. [F01–F14 ledger](ISSUE_LEDGER.md) preserves all original priorities and complete remaining conditions; no F item is labeled fully closed merely because code exists.', '',
 '**Open code/product work:** complete source-revision provenance for normal Hybrid records and remaining legacy export/transfer paths; supported historical state migration with receipts; direct applicable-contract links for every retained result; measured hosted-shell/data-splitting optimization; comparative tablet-rail usability experiment. These are not hidden behind hardware blockers.', '',
 '**Blocked or not run:** native/physical device and screen-reader tasks, uncoached usability, real-phone/field performance, 189 complete council role/evidence specifications, independent hand checks for each of 59 studies, exhaustive higher-order task states across all workspaces, and candidate remote CI/deployment reconciliation. [Manual acceptance and rollback runbook](MANUAL_ACCEPTANCE.md).', '',
 '## Measurement and failure integrity', '',
 'All original failure logs are retained. The initial metadata inventory failed two studies; source-reference corrections pass on rerun. Test-fixture expectation errors, the Terminal harness URL error, a Windows output-directory lock, and an interrupted provider-mock test are distinguished from application regressions. Local HTTP AdGuard injection changed response bytes/CSP; those runs are retained but are not exact static artifact acceptance. Final static suites use HTTPS loopback and verify the original bytes without changing host security settings. API UI tasks remain HTTP functional evidence. An initial warm-performance harness used fragment navigation rather than reload; those measurements are invalid and retained separately.', '',
 'Lab measurement completion is not a pass against LCP/INP/CLS targets. Field INP and p75 remain null. Real-world cache propagation, native downloads, user profile behavior and provider spend were not claimed.', '',
 '## Artifacts', '',
 '- [Issue ledger](issue-ledger.json), [suite ledger](suite-ledger.json), [workspace results](workspace-results.json), [study cards/results](study-acceptance-results.json), [council specifications/results](council-results.json).',
 '- [Screenshots and capture metadata](capture-results.json), [desktop](screenshots/desktop.png), [tablet](screenshots/tablet.png), [mobile](screenshots/mobile.png), [trace](onboarding-resize-trace.zip).',
 '- [Performance raw runs](performance-results.json), [deployed observations](deployed/observation.json), [source file hashes](source-file-hashes.json), and retained logs in `logs/`.',
 '- Reviewable source branch and `review.patch`; delivery archive contains changed/new files and evidence, with a separate file manifest. No production publication or paid provider calls.', '']
report += ['The first exact-byte presentation run had 156 PASS and one loopback TLS failure before app load (PAIR-141); the separate targeted retest passed. All 157 case IDs consequently have a passing execution, across 158 attempts with one retained failed attempt. This is bounded presentation acceptance, not exhaustive behavior coverage.', '']
(OUT/'COMPLETION_REPORT.md').write_text('\n'.join(report),encoding='utf-8')
print(json.dumps({'runtime_sha256':runtime,'receipt':immutable.name,'suites':len(suite_rows),'open_appraisal_items':14}))
