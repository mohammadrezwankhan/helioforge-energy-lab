import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8');
const applicationUrl = 'https://mkgrid.co.technology/run/';
const facts = {applicationUrl, publicSource: 'https://github.com/mohammadrezwankhan/helioforge-energy-lab', sourceRevision: 'a'.repeat(40), runtimeSha256: 'b'.repeat(64)};
function setup(url = applicationUrl, response = facts) {
  const box = vm.createContext({URL, Intl, structuredClone, AbortSignal});
  vm.runInContext(code, box);
  const nodes = Array.from({length: 2}, () => { const identity = {innerHTML: ''}, source = {href: '', textContent: ''}; return {identity, source, querySelector: selector => selector === '[data-release-source]' ? source : identity}; });
  let requests = 0;
  box.location = new URL(url);
  box.document = {querySelectorAll: () => nodes};
  box.fetch = async () => { requests++; if (response instanceof Error) throw response; return {ok: true, json: async () => response}; };
  return {hf: box.HF, nodes, requests: () => requests};
}
test('published identity validates the exact app, repository and full digests', () => {
  const {hf} = setup();
  assert.equal(typeof hf.parsePublishedRuntimeFacts, 'function');
  assert.equal(hf.parsePublishedRuntimeFacts(facts, applicationUrl).sourceRevision, facts.sourceRevision);
  for (const bad of [null, {}, {...facts, applicationUrl: 'https://other.invalid/run/'}, {...facts, publicSource: 'javascript:alert(1)'}, {...facts, sourceRevision: 'short'}, {...facts, runtimeSha256: 'b'.repeat(63)}]) {
    assert.equal(hf.parsePublishedRuntimeFacts(bad, applicationUrl), null);
  }
});
test('one same-origin facts request updates all visible provenance hosts without rerendering the app', async () => {
  const x = setup();
  await Promise.all([x.hf.refreshReleaseProvenance(), x.hf.refreshReleaseProvenance()]);
  assert.equal(x.requests(), 1);
  for (const node of x.nodes) {
    assert.match(node.identity.innerHTML, /Published runtime SHA-256/);
    assert.ok(node.identity.innerHTML.includes(facts.runtimeSha256));
    assert.ok(node.source.href.endsWith('/tree/' + facts.sourceRevision));
  }
});
test('offline and malformed facts retain useful links and an honest unavailable state', async () => {
  for (const x of [setup('file:///tmp/HelioForge-Preview.html'), setup(applicationUrl, {}), setup(applicationUrl, new Error('offline'))]) {
    await x.hf.refreshReleaseProvenance();
    assert.match(x.nodes[0].identity.innerHTML, /Release identity unavailable/);
    assert.equal(x.nodes[0].source.textContent, 'Public source');
    assert.doesNotMatch(x.nodes[0].identity.innerHTML, /Published runtime SHA-256/);
  }
});
