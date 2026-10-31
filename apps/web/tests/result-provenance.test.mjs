import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const box=vm.createContext({URL,Intl,structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),box);
const hf=box.HF;
test('export retains model identity separately from version and original colliding data',()=>{
  const result={...hf.HYBRID_EXAMPLE,inputs:hf.HYBRID_BUNDLE.cases[0].inputs};
  const rows=hf.resultExportRows(result,[{model_id:'observation',value:0},{value:2}]);
  assert.equal(rows.length,2);assert.equal(rows[0].model_id,'hybrid');
  assert.equal(rows[0].model_version,result.model);assert.equal(rows[0].original_model_id,'observation');
  assert.equal(rows[1].source_revision,result.source_revision);
  assert.deepEqual(JSON.parse(rows[0].result_json).inputs,JSON.parse(JSON.stringify(result.inputs)));
  assert.equal(rows[1].result_json,undefined);
});
test('empty export carries the entire original record; legacy results remain explicitly unknown',()=>{
  const result={model:'legacy',warnings:['Unverified'],inputs:{x:3}};
  const rows=hf.resultExportRows(result,[]);
  assert.equal(rows.length,1);assert.deepEqual(JSON.parse(rows[0].result_json),result);
  assert.equal(rows[0].source_revision,'legacy/unknown');
  assert.match(hf.resultProvenanceView(result),/Legacy\/unknown source provenance/);
  assert.doesNotMatch(hf.resultProvenanceView(result),/Source-bound record/);
});
test('new result disclosure includes units, horizon and endpoint assumptions without claiming approval',()=>{
  const html=hf.resultProvenanceView(hf.HYBRID_EXAMPLE);
  for(const phrase of ['Model provenance','kWh','duration_hours','terminal_soc_policy','not_assessed'])assert.ok(html.includes(phrase),phrase);
});
