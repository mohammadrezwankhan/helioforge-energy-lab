import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
const c=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,structuredClone,crypto:webcrypto,TextEncoder});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),c);
const h=c.HF;
test('canonical manifest rejects nonfinite payloads and sorts keys',()=>{
  assert.equal(h.terminalCanonical({b:2,a:1}),'{"a":1,"b":2}');
  assert.throws(()=>h.terminalCanonical({a:Infinity}),/finite/);
});
test('manifest digest covers inputs, solver and every output row, excluding timestamp',async()=>{
  const run=h.terminalSolve(h.terminalDefaults());
  const a=await h.terminalCreateManifest(run),b=await h.terminalCreateManifest(run);
  assert.match(a.stateSha256,/^[a-f0-9]{64}$/);
  assert.equal(a.stateSha256,b.stateSha256);
  const imported=await h.terminalReadManifest(a);
  assert.equal(imported.metrics.periodCost,run.metrics.periodCost);
  const changed=JSON.parse(JSON.stringify(a));changed.payload.run.rows[0].loadKw+=1;
  await assert.rejects(h.terminalReadManifest(changed),/hash/);
});
test('query state round trip is complete and rejects unknown fields',()=>{
  const input=h.terminalDefaults();
  assert.deepEqual(JSON.parse(JSON.stringify(h.terminalDecodeState(h.terminalEncodeState(input)))),JSON.parse(JSON.stringify(input)));
  assert.throws(()=>h.terminalDecodeState(encodeURIComponent('{"unrecognized":1}')));
});
test('exported csv and Markdown include inputs, output series and integrity metadata',async()=>{
  const m=await h.terminalCreateManifest(h.terminalSolve(h.terminalDefaults()));
  const csv=h.terminalManifestCSV(m),md=h.terminalManifestMarkdown(m);
  for(const key of ['stateSha256','pvKw','busResidualKw','dataKind','status','flags','warnings','synthetic-deterministic'])assert.ok(csv.includes(key),key);
  assert.ok(md.includes(m.stateSha256));assert.ok(md.includes('socResidualKwh'));
});
