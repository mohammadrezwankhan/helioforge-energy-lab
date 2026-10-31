"""Bind the follow-up's actual local evidence without claiming external acceptance."""
import hashlib
import json
import os
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/remediation-20261029'
SITE = Path(os.environ['HELIOFORGE_ACCEPTANCE_SITE'])
def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
def write(name, value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').strip()

runtime = sha(SITE/'run/index.html')
facts = json.loads((SITE/'app.json').read_text(encoding='utf-8'))
assert runtime == facts['runtimeSha256']
responsive, terminal = read('final-responsive.json'), read('final-terminal.json')
presentation, capture = read('presentation-results.json'), read('capture-results.json')
presentation_retest = read('presentation-retest-results.json') if (OUT/'presentation-retest-results.json').is_file() else None
presentation_final = {case['test_id']:case for case in presentation['cases']}
if presentation_retest:
    assert presentation_retest['artifact_sha256'] == runtime
    for case in presentation_retest['cases']:
        assert case['test_id'] in presentation_final
        presentation_final[case['test_id']] = case
presentation_summary = dict(Counter(case['status'] for case in presentation_final.values()))
studies, inventory = read('study-contracts.json'), read('inventory-results.json')
hosted = read('hosted-browser-results.json')['executions'][-1]
workspace = read('workspace-browser-results.json')
performance = read('performance-final/performance-results.json')
parse_cost = read('parse-cost/parse-cost-results.json')
assert parse_cost['candidate']['runtime_sha256'] == runtime
assert parse_cost['summary']['runs'] == parse_cost['summary']['passed'] == 2 and parse_cost['summary']['failed'] == 0
python = ElementTree.parse(OUT/'python-verified.xml').getroot()[0].attrib
frontend = (OUT/'frontend-final.log').read_text(encoding='utf-8-sig')
node_pass = int(re.findall(r'(?:ℹ|#) pass (\d+)',frontend)[-1])
node_fail = int(re.findall(r'(?:ℹ|#) fail (\d+)',frontend)[-1])
assert int(python['failures']) == int(python['errors']) == node_fail == 0
assert responsive['summary']['failed'] == terminal['summary']['failed'] == 0
assert capture['summary']['FAIL'] == 0
assert int(python['tests']) == 679 and int(python['skipped']) == 0 and node_pass == 225
assert responsive['summary']['passed'] == 654 and responsive['summary']['unavailable'] == 0
assert terminal['summary']['passed'] == 251 and terminal['summary']['axeViolations'] == 0
assert presentation_summary == {'PASS':157} and capture['summary']['PASS'] == 63
assert presentation['artifact_sha256'] == capture['artifact_sha256'] == performance['artifact_sha256'] == runtime
assert len(studies['studies']) == 59 and all(row['status']=='PASS' for row in studies['studies'])
assert hosted['status'] == workspace['status'] == 'PASS'
assert all(row['status'] == 'PASS' for row in hosted['checks'])
assert len(hosted['checks']) == 30 and workspace['summary']['pass'] == 18
assert next(row['actual'] for row in hosted['checks'] if row['check']=='app_facts_runtime_sha256_matches_exact_runtime') == runtime
assert workspace['summary']['fail'] == 0 and workspace['summary']['runtime_sha256'] == runtime
assert performance['summary']['executed'] == 12 and performance['summary']['failed'] == 0
interactions = [item for run in performance['runs'] for item in run['interactions']]
assert len(interactions) == 96 and all(item['status']=='PASS' for item in interactions)
budget_failed = sum(run['lab_lcp_budget_status']=='FAIL' for run in performance['runs'])
api = json.loads((ROOT/'docs/roadmap/browser-validation.json').read_text(encoding='utf-8-sig'))
assert len(api['checks']) == 24 and not api['browser_errors']

suite = {
    'runtime_sha256':runtime,'source_base_commit':git('rev-parse','HEAD'),'production_changed':False,
    'runtime_binding':'Browser suites used the unchanged loopback candidate at port 4200; hosted/capture/migration independently hashed response bytes. artifact-equivalence.json verifies all 364 candidate and delivery files match.',
    'python':{k:int(python[k]) for k in ['tests','failures','errors','skipped']},
    'frontend':{'passed':node_pass,'failed':node_fail},
    'responsive':responsive['summary'],'terminal':terminal['summary'],
    'catalogue_and_default_studies':inventory['summary'],
    'independent_study_cases':studies['targeted_test_run'],
    'presentation':{'first_attempts':presentation['summary'],'retest':presentation_retest['summary'] if presentation_retest else None,'final_unique_cases':presentation_summary},'capture':capture['summary'],
    'hosted_latest':hosted,'workspace_browser':workspace,
    'council_local':read('council-results.json')['all_case_status_counts'],
    'reproducible_site':read('artifact-equivalence.json'),
    'performance':performance['summary'],
    'parse_cost':{'summary':parse_cost['summary'],'evidence':'docs/remediation-20261029/parse-cost/parse-cost-results.json'},
    'performance_load_budget':{'executed':12,'passed':12-budget_failed,'failed':budget_failed,'target_lcp_ms':2500},
    'performance_interactions':{'executed':len(interactions),'passed':len(interactions),'failed':0,'field_INP':None},
    'hosted_check_counts':{'passed':len(hosted['checks']),'failed':0},
    'api_browser':{'passed':len(api['checks']),'failed':0,'evidence':'docs/roadmap/browser-validation.json'},
    'external_provider':{'blocked':63,'executed':0},
    'human_personas':{'not_run':8,'executed':0},
    'native_zoom':'BLOCKED: Computer Use stopped for unsupported browser URL-policy enforcement.',
    'physical_devices_native_AT_and_field_metrics':'BLOCKED: unavailable; no substitution by emulation.',
}
write('suite-ledger.json',suite)

updates = {
 'F01':('Deterministic LF build, frozen replay, content-addressed hosted assets and whole-site byte receipts.','Candidate remote CI, deployment and independently retrieved production identity still require authorized publication.'),
 'F02':('Shared four-mode contract and nine public content pages; on-demand hosted data and complete offline edition are documented.','Candidate content is not published or production-cache verified.'),
 'F03':('Local evidence metadata checks executed; frozen public council explicitly rejects new submissions; protocol discloses roles, costs and cancellation uncertainty.','63 actual provider cases remain blocked; public read-only checks do not execute specialists.'),
 'F04':('New genuine desktop/tablet/mobile/social captures are bound to the tested runtime.','Publication and physical-device appearance remain unverified.'),
 'F05':('Source-bound numerical provenance, effective storage input identity, direct result contracts, complete CSV/JSON/memo data and stale-result gates are integrated.','Verified for the recorded software paths; historical unknown records remain unknown. Candidate production transfer/export paths remain unverified.'),
 'F06':('Task-led starts and a collapsible tablet drawer pass automated navigation, focus and resize checks.','Eight uncoached persona sessions and participant comparison against the prior rail remain unexecuted.'),
 'F07':('Hosted shell separated from 297 exact-data chunks; offline edition preserved; cold/warm lab runs and separate V8 parsing/compilation traces retained.',f'{budget_failed}/12 final lab LCP measurements exceed 2500 ms. Physical phone measurements, field p75 and field INP remain unavailable.'),
 'F08':('654 desktop-engine responsive/accessibility checks, 251 Terminal checks and expanded provenance reflow checks are recorded.','Native AT, physical devices and native zoom remain blocked; automated scans are not full accessibility acceptance.'),
 'F09':('Nine-page local crawl/header/CSP contract and artifact checks pass; prior production evidence remains dated baseline evidence.','New deployed pages, effective production headers, global cache and account-specific discovery evidence require authorized publication/access.'),
 'F10':('All 59 source-bound software acceptance records are linked into the model registry; direct result contracts and full study exports are available.','Candidate published links remain unverified. Software checks do not establish model-specific scientific/field validation or explicitly unknown solver optimality.'),
 'F11':('Actual historical v1-to-v2 migration includes preview, exact backup, source/target receipt, loss disclosure and preservation of unchanged offline run references.','Recorded desktop-engine round trips and negative recovery paths pass. Required physical/native picker and cross-device journeys remain unexecuted; no historical v0 schema was invented.'),
 'F12':('Content integrity, data origin, source identity and human authority remain distinct; local metadata and public rejection cases are executed.','Provider failure/cancellation authority and real human sign-off remain untested/unrecorded.'),
 'F13':('Reviewed learning, glossary, mode, help and model content is included in the complete local candidate.','Publication, cache propagation and discovery outcomes remain unverified.'),
 'F14':('Catalogue, studies, pairwise contexts, exports, races, migration and public/local council evidence are recorded separately with failures retained.','External, native-device and uncoached human acceptance cases remain open; planned cases are not passes.'),
}
ledger=json.loads((ROOT/'docs/remediation-20261028/issue-ledger.json').read_text(encoding='utf-8'))
file_groups = {
 'F01':['.gitattributes','.github/workflows/ci.yml','scripts/compile-web.mjs','scripts/build-web.mjs','scripts/acceptance-build-receipt.mjs'],
 'F02':['scripts/capability-contract.mjs','scripts/build-domain.mjs','README.md'],
 'F03':['apps/api/helioforge/council.py','apps/api/helioforge/main.py','apps/web/src/integrations-ui.ts','apps/web/src/app.ts'],
 'F04':['cloudflare.json','scripts/acceptance-capture.py','scripts/build-cloudflare.mjs'],
 'F05':['apps/api/helioforge/provenance.py','apps/api/helioforge/studies.py','apps/api/helioforge/main.py','apps/web/src/result-provenance.ts','apps/web/src/provenance-types.ts','apps/web/src/roadmap.ts'],
 'F06':['apps/web/src/app.ts','apps/web/src/terminal.css'],
 'F07':['scripts/hosted-data.mjs','scripts/inline-html.mjs','apps/web/src/deferred-data.ts','apps/web/src/hybrid-core.ts','apps/web/src/roadmap.ts','scripts/acceptance-performance.py'],
 'F08':['apps/web/src/result-provenance.ts','apps/web/src/terminal.css','scripts/browser-full-audit.py'],
 'F09':['scripts/build-domain.mjs','scripts/check-domain.mjs'],
 'F10':['scripts/acceptance-study-contracts.py','scripts/capability-contract.mjs','docs/MODEL_REGISTRY.json'],
 'F11':['apps/web/src/champion-core.ts','apps/web/src/champion-controller.ts','apps/web/src/champion-views.ts','apps/web/tests/workspace-migration.test.mjs','scripts/acceptance-workspace-migration.py'],
 'F12':['apps/api/helioforge/council.py','apps/web/src/result-provenance.ts'],
 'F13':['scripts/build-domain.mjs','docs/CAPABILITIES.md'],
 'F14':['scripts/acceptance-hosted.py','scripts/acceptance-presentation.py','scripts/finalize-followup.py','scripts/package-acceptance.py'],
}
for row in ledger:
    observation, blocker=updates[row['issue_id']]
    row['historical_observation_20261028']=row['current_observation']
    row['historical_evidence_base']='docs/remediation-20261028/'
    row['changed_files']=sorted(set(row['changed_files']+file_groups[row['issue_id']]))
    row.update(current_observation=observation,actual_behavior=observation,remaining_blocker=blocker,
        implementation_status='VERIFIED_LOCAL in the explicitly recorded scope',deployed_status='Candidate NOT_DEPLOYED',
        status='OPEN_EXTERNAL_OR_HUMAN_ACCEPTANCE',acceptance_complete=False,
        artifact_identity={'runtime_sha256':runtime,'source_base_commit':suite['source_base_commit'],'source_dirty':True,'production_changed':False},
        followup_evidence=['docs/remediation-20261029/suite-ledger.json','docs/remediation-20261029/ACCEPTANCE_REPORT.md'],
        disposition={'verified_fixed':'Recorded local implementation and executed regression scope; see suite ledger.',
          'already_resolved':'Historical baseline observations are preserved separately; no historical repair was reintroduced.',
          'implemented_unverified':'Candidate deployment/remote CI and unavailable human/native journeys.',
          'blocked':blocker,'not_applicable':'Only explicitly justified rows in the individual suite reports.'})
write('issue-ledger.json',ledger)
lines=['# F01–F14 follow-up disposition','','Local implementation/verification and full appraisal closure are distinct. Every original applicable acceptance condition remains binding.','', '| ID | Verified local work | Remaining gate |','|---|---|---|']
for row in ledger:lines.append(f"| {row['issue_id']} | {row['current_observation']} | {row['remaining_blocker']} |")
(OUT/'ISSUE_LEDGER.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')

perf=[]
for profile in sorted({r['profile'] for r in performance['runs']}):
    for cache in ['cold','warm']:
        runs=[r for r in performance['runs'] if r['profile']==profile and r['cache']==cache]
        values=[r['metrics']['lcp'] for r in runs]
        perf.append(f"| {profile} | {cache} | {len(runs)} | {statistics.median(values):.0f} | {min(values):.0f}–{max(values):.0f} | {sum(v>2500 for v in values)} |")
parse_rows=[]
for run in parse_cost['runs']:
    metrics=run['main_thread_union_metrics']
    parse_rows.append('| '+run['profile']+' | '+' | '.join(str(metrics[key]['union_ms']) for key in ['javascript_parse','javascript_compile','javascript_parse_compile_union','html_parse','javascript_execution'])+' |')
(OUT/'PERFORMANCE.md').write_text('\n'.join(['# Retained laboratory performance','','Final runtime: `'+runtime+'`. No physical-device or field claim.','',
 '| Profile | Cache | Runs | Median LCP ms | LCP range ms | Runs over 2500 ms |','|---|---|---:|---:|---:|---:|',*perf,'',
 'The prior monolithic phone emulation measured approximately 10–12.3 seconds. Earlier split/minified attempts, including candidate F with one LCP target miss, remain retained. The final untraced load results include CDP main-thread execution/layout deltas, long tasks, heap observations and interaction measurements. Those measurements are not field INP.',
 '', 'Two separate instrumented cold traces measure the observed V8 parser/compiler intervals on the frame-linked renderer main thread. They are diagnostics, not additional load-budget or field samples; tracing and other host activity affect cost. Compile intervals include overlapping parser work; the union column deduplicates overlap. Do not add the parse and compile columns.', '',
 '| Trace profile | JS parse ms | JS compile ms | Parse/compile union ms | HTML parse ms | JS execution ms |','|---|---:|---:|---:|---:|---:|',*parse_rows,'',
 'The complete offline HTML remains self-contained. The hosted entry loads selected exact-data JSON chunks only as needed; hashes and byte counts must match before display. esbuild 0.28.2 is a pinned build-only dependency ([official transform/minification API](https://esbuild.github.io/api/#minify)). No analytics or runtime dependency was added.','']),encoding='utf-8',newline='\n')

report=f"""# HelioForge repair follow-up — 2026-10-29

The local repair implementation and functional verification are complete in the remediation worktree. The final performance run has {budget_failed}/12 LCP target misses, retained as failures against the 2500 ms target. Full appraisal acceptance remains open for authorized publication/CI, live providers, physical devices, native assistive technology, field measurements and uncoached participants. Production was not changed.

Tested hosted runtime SHA-256: `{runtime}`. Source base: `{suite['source_base_commit']}` with uncommitted changes. The hosted shell is {len((SITE/'run/index.html').read_bytes()):,} bytes, with 297 separately verified data assets covering 285 hybrid presets and all 59 studies. The separate offline edition retains every example and the browser Terminal.

## Completed local changes

- On-demand, integrity-checked hosted data, literal-safe HTML embedding, pinned build-only minification and deterministic LF output; complete offline download retained.
- Source-bound numerical provenance and direct model contracts. Storage identity uses effective solver inputs; request identity remains separate. Legacy unknown records are not upgraded by inference.
- Full JSON, CSV, series and memorandum exports, including empty-table metadata and 8,760-point data; model ID/version remain distinct.
- Explicit historical v1-to-v2 migration, exact backup, receipt, retry and unchanged offline run-pointer preservation.
- Tablet drawer and public frozen-council controls, with genuine release-bound captures. Local evidence metadata checks execute without claiming specialist or critic execution.
- All 59 model software acceptance records are linked into a registry that checks their source hashes. Independent review findings were corrected and re-reviewed.

## Executed evidence

| Suite | Result |
|---|---|
| Python unit/API | {python['tests']} passed; zero failures/errors |
| Frontend unit/controller | {node_pass} passed; zero failures |
| Catalogue matrix | 864 passed (numerical, study-only and inapplicable gates remain distinct) |
| Study software acceptance | 59 IDs; 61 executed targeted cases passed |
| Responsive/accessibility | {responsive['summary']['passed']} passed across Chromium, Firefox and WebKit; no native-device claim |
| Terminal journeys | {terminal['summary']['passed']} passed; 24 axe view runs, zero violations |
| Presentation pairwise | {presentation_summary.get('PASS',0)} unique cases passed finally; first attempts: {presentation['summary']}; targeted retry: {presentation_retest['summary'] if presentation_retest else 'none'} |
| Capture/onboarding/breakpoints | {capture['summary']['PASS']} passed |
| Hosted exports, lazy loads and public council | {len(hosted['checks'])} checks passed; all 59 study export bundles checked |
| Workspace migration browser | {workspace['summary']['pass']} passed; zero failures |
| API-backed browser | 24 checks passed; isolated synthetic TLS loopback fixture |
| Performance | 12 completed load measurements; {budget_failed} LCP target misses; 96/96 interactions completed; details in `PERFORMANCE.md` |
| Parse/compile diagnostics | 2 instrumented cold traces retained; explicit V8 parsing separated from HTML parsing and execution |

The council ledger retains 56 local evidence-state passes, 14 non-applicable local/public critic execution cases, and 63 blocked live-provider rows. The separate 63 public browser checks verify frozen/read-only behavior and invariant disclosures, not processing of new evidence. Eight human persona sessions remain not run. Native zoom was blocked when Computer Use stopped because this browser lacked URL-policy enforcement support.

Failed intermediate candidates and harness failures are retained and distinguished in logs and `NEW_FINDINGS.md`; their tests are not silently counted as final passes. The final presentation run's Firefox focus timeout occurred during host stalls and passed a single unchanged-artifact retry; its root cause is not established. The final unit suite retains one upstream Starlette/httpx deprecation warning. No tolerances were loosened and no failed scientific condition was relabeled as validated.

## Delivery and remaining actions

`ISSUE_LEDGER.md` and `issue-ledger.json` preserve F01–F14, source IDs and remaining acceptance conditions. `MANUAL_ACCEPTANCE.md` contains provider, device, participant, publication and rollback steps. `RELEASE_RECEIPT.json` points to an immutable local receipt with exact source/evidence/site hashes; remote CI and deployment identity remain explicitly unverified. `DELIVERY_MANIFEST.json` and the separate archive receipt bind the packaged review files and exact candidate site.

Git publication, production deployment and paid provider calls require explicit user authorization under the repository's `AGENTS.md`. No such action was taken. The original checkout and the prior 2026-10-28 delivery were preserved.
"""
(OUT/'ACCEPTANCE_REPORT.md').write_text(report,encoding='utf-8',newline='\n')

source_names=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))
source_names.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))
sources=[{'path':name,'sha256':sha(ROOT/name),'bytes':(ROOT/name).stat().st_size} for name in sorted(source_names)
    if name and name!='x.bytes)))' and (ROOT/name).is_file() and not name.startswith('docs/remediation-')]
evidence=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*'))
    if p.is_file() and 'receipts' not in p.parts and p.name not in {'RELEASE_RECEIPT.json','DELIVERY_MANIFEST.json','review.patch','package.log','finalize.log','receipt-verification.json'}]
site_files=[{'path':p.relative_to(SITE).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(SITE.rglob('*')) if p.is_file()]
receipt={'schema':'helioforge.followup-release.v1','created_at':datetime.now(timezone.utc).isoformat(),
 'source_base_commit':suite['source_base_commit'],'working_tree_dirty':True,'runtime_sha256':runtime,
 'environment':'VERIFIED_LOCAL','production_changed':False,'ci_run_id':None,'deployment_id':None,
 'external_and_human_gates':'OPEN; see issue ledger','sources':sources,'evidence':evidence,'site_files':site_files}
encoded=(json.dumps(receipt,indent=2)+'\n').encode()
digest=hashlib.sha256(encoded).hexdigest()
directory=OUT/'receipts';directory.mkdir(exist_ok=True)
target=directory/f'release-{digest}.json'
with target.open('xb') as handle:
    handle.write(encoded)
write('RELEASE_RECEIPT.json',{'receipt':target.relative_to(ROOT).as_posix(),'sha256':digest,'runtime_sha256':runtime,'production_changed':False})
print(json.dumps({'runtime':runtime,'receipt':str(target),'source_files':len(sources),'evidence_files':len(evidence),'site_files':len(site_files)}))
