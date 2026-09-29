import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const sandbox=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),sandbox);
const h=sandbox.HF;
const state=()=>({hybrid:h.initialHybridState(),page:'hybrid',connected:true,busy:false,data:h.SNAPSHOT,marketFilter:'ALL',search:'',chartMode:'dispatch',forecastYears:20,runs:[],motionOff:false});
test('catalogue has 36 explicit capability declarations',()=>{
 assert.equal(h.HYBRID_CATALOG.systems.length,36);
 assert.equal(h.HYBRID_CATALOG.systems.filter(s=>s.mode==='screening').length,19);
 assert.equal(h.HYBRID_CATALOG.scenarios.length,24);
});
for(const s of h.HYBRID_CATALOG.systems){
 test(`configuration roundtrip: ${s.id}`,()=>{
  const p=h.presetInputs(s.id);const parsed=h.parseConfiguration({schema:'helioforge.hybrid.v1',inputs:p});
  assert.equal(JSON.stringify(p),JSON.stringify(parsed));
 });
}
test('rejects unknown, absent, incompatible, nonfinite and unsafe fields',()=>{
 const p=h.presetInputs('remote-triad');
 for(const v of [null,[],{}, {...p,load_kw:0},{...p,wind_kw:Infinity},{...p,hours:2.5},{...p,grid_import_kw:50},{...p,solar_kw:-1},{...p,unknown:'<script>'},{...p,control:'<img onerror=alert(1)>'},{...p,battery_kwh:0},{...p,initial_soc:.1},{...p,hydro_kw:10}])assert.throws(()=>h.parseConfiguration(v));
 const missing={...p};delete missing.hours;assert.throws(()=>h.parseConfiguration(missing));
});
test('search combines synonyms and topology without duplicating cards',()=>{
 assert.ok(h.filterSystems('PV BESS','All','All').length>0);
 assert.ok(h.filterSystems('H2','All','All').every(s=>s.technologies.includes('hydrogen')));
 assert.equal(h.filterSystems('not_a_system','All','All').length,0);
 assert.ok(h.filterSystems('','Solar','FTM').every(s=>s.family==='Solar'&&s.topology==='FTM'));
});
test('scenario applicability and long-horizon preset agree',()=>{
 assert.equal(h.applicable(h.systemById('remote-triad'),h.scenarioById('outage-4h')),false);
 assert.equal(h.presetInputs('hospital-island','outage-72h').hours,72);
 assert.throws(()=>h.presetInputs('remote-triad','low-river'));
});
test('all 36 lessons grade exactly and do not reward incorrect answers',()=>{
 for(const l of h.HYBRID_CATALOG.lessons){
  assert.equal(h.gradeLesson(l,l.quiz.map(q=>q.answer)).passed,true);
  assert.equal(h.gradeLesson(l,[-1,-1]).passed,false);
  assert.equal(h.gradeLesson(l,l.quiz.map(q=>(q.answer+1)%q.options.length)).correct,0);
 }
});
test('smart tags expose reasons and storage units',()=>{
 const tags=h.hybridTags(h.presetInputs('remote-triad'));
 assert.ok(tags.every(t=>t.reason.length>10));
 assert.ok(tags.some(t=>t.label==='4.0 h storage'));
});
test('stale results hidden and not relabelled with new inputs',()=>{
 const s=state();assert.equal(h.hybridDirty(s.hybrid),false);
 s.hybrid.inputs.solar_kw+=1;assert.equal(h.hybridDirty(s.hybrid),true);
 const html=h.hybridResults(s);assert.ok(!html.includes('hybrid-metrics'));
});
test('study architecture and scenario render no invented numeric result',()=>{
 for(const [id,scenario] of [['solar-hydrogen','baseline'],['hospital-island','black-start']]){
  const s=state();s.hybrid.inputs=h.presetInputs(id,scenario);
  assert.ok(h.hybridResults(s).includes('study'));
  assert.ok(!h.hybridResults(s).includes('hybrid-metrics'));
 }
});
test('no inapplicable market selector on hybrid, lesson and compare screens',()=>{
 for(const page of ['hybrid','lessons','compare']){const s=state();s.page=page;assert.ok(!h.shell(s).includes('id="context-market"'));}
});
