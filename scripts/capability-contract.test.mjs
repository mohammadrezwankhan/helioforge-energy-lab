import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {
  CAPABILITY_COPY,
  TASK_STARTS,
  WORKSPACES,
  buildModelRegistry,
  validateCloudflareCopy,
} from './capability-contract.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=relative=>fs.readFileSync(path.join(root,relative),'utf8');
const cloudflare=JSON.parse(read('cloudflare.json'));
validateCloudflareCopy(cloudflare);

const registry=buildModelRegistry(root);
const committed=JSON.parse(read('docs/MODEL_REGISTRY.json'));
assert.deepEqual(committed,registry,'committed model registry must be regenerated from Python-backed study bundle');
assert.equal(registry.registryVersion,'1.0.0');
assert.equal(registry.workspaces.length,12);
assert.equal(registry.studies.length,59);
assert.equal(new Set(registry.studies.map(study=>study.id)).size,59);
assert.equal(registry.identities.catalogue.studies.declaredVersion,null);
assert.equal(registry.identities.data.studyExamples.version,null);
assert.equal(registry.identities.schemas.studyResultVersion,null);
assert.equal(registry.identities.models.studies,'roadmap-screen-v1');
assert.equal(registry.identities.models.terminal,'terminal-greedy-hourly-v1');
assert.equal(registry.identities.models.hybrid,'hybrid-greedy-hourly-v1');
assert.equal(registry.identities.models.storage,'btm-milp-v1');
assert.deepEqual(Object.keys(WORKSPACES).sort(),registry.workspaces.map(workspace=>workspace.id).sort());

for(const [mode,copy] of Object.entries(CAPABILITY_COPY)){
  assert.ok(JSON.stringify(cloudflare).includes(copy),`cloudflare.json lacks the shared ${mode} copy`);
  assert.ok(read('README.md').includes(copy),`README lacks the shared ${mode} copy`);
  assert.ok(read('docs/CAPABILITIES.md').includes(copy),`CAPABILITIES.md lacks the shared ${mode} copy`);
}
for(const start of TASK_STARTS){
  const configText=JSON.stringify(cloudflare);
  assert.ok(configText.includes(start.label),`cloudflare.json lacks ${start.label}`);
  assert.ok(configText.includes(start.description),`cloudflare.json lacks ${start.description}`);
  assert.ok(read('README.md').includes(start.label),`README lacks ${start.label}`);
  assert.ok(read('README.md').includes(start.description),`README lacks ${start.description}`);
}

for(const study of registry.studies){
  assert.ok(WORKSPACES[study.workspace.id],`${study.id}: unknown workspace`);
  assert.equal(study.model.version,'roadmap-screen-v1',`${study.id}: model version must come from its bundled Python result`);
  assert.ok(study.model.equations.length,`${study.id}: no equation contract`);
  assert.ok(study.model.limitations.length,`${study.id}: no stated limitations`);
  assert.ok(fs.existsSync(path.join(root,study.acceptance.modelReferences.code)),`${study.id}: missing Python source link`);
  for(const testFile of study.acceptance.modelReferences.tests)assert.ok(fs.existsSync(path.join(root,testFile)),`${study.id}: missing test link ${testFile}`);
  assert.ok(study.fixture.evidenceSha256 && study.fixture.inputSha256,`${study.id}: default fixture lacks digests`);
  assert.equal(study.acceptance.executionEvidence.sourceMatches,true,`${study.id}: stale acceptance evidence`);
  assert.equal(study.fixture.handCheck.status,'SOFTWARE_ORACLE_PASS');
  assert.equal(study.acceptance.invalidBoundary.status,'PASS');
  assert.equal(study.acceptance.deterministicOrSeeded.status,'PASS');
  assert.notEqual(study.acceptance.feasibilityOrConvergence.status,'FAIL');
  assert.equal(study.acceptance.export.status,'JSON_PASS; BROWSER_EXPORTS_SEPARATE');
  assert.ok(study.inputs.numericFields.every(field=>Number.isFinite(field.min)&&Number.isFinite(field.max)&&field.min<=field.max));
}

console.log(JSON.stringify({status:'passed',checks:['four delivery modes','shared overview copy source','task-led starts','version-layer separation','all workspace/study mappings','per-study source/test/fixture/limit links','unknown and not-run evidence labels'],workspaces:registry.workspaces.length,studies:registry.studies.length}));
