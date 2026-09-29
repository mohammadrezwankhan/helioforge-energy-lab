import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8');
function setup(){
 const memory=new Map();
 const sandbox=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,Map,Date,structuredClone,
  localStorage:{getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v),removeItem:k=>memory.delete(k)}});
 vm.runInContext(code,sandbox);const h=sandbox.HF;
 const state={hybrid:h.initialHybridState(),page:'hybrid',connected:true,busy:false,data:structuredClone(h.SNAPSHOT),marketFilter:'ALL',search:'',chartMode:'dispatch',forecastYears:20,runs:[],motionOff:true};
 state.champion=h.initialChampionState(state.hybrid);
 return {h,state,memory,sandbox};
}
const uuid='d85c1ad4-98b3-46e1-af53-23a202435683';
const clone=x=>JSON.parse(JSON.stringify(x));
test('a workspace serializes inputs and run IDs, not result payloads',()=>{const {h,state}=setup();const c=h.workspaceCache(state);assert.equal(c.schema,'helioforge.workspace.v1');assert.ok(c.inputs.system_id);assert.equal('result' in c,false);assert.equal(c.last_run_id,null);});
test('valid workspace round trip',()=>{const {h,state}=setup();const original=h.workspaceCache(state);assert.deepEqual(clone(h.parseWorkspace(original)),clone(original));});
test('browser storage restores a valid setup without fabricating a result',()=>{const {h,state,memory}=setup();state.hybrid.inputs.battery_kwh=321;assert.equal(h.persistWorkspace(state),true);const next=h.initialHybridState(),c=h.initialChampionState(next);assert.equal(next.inputs.battery_kwh,321);assert.equal(next.result,null);assert.equal(c.storage,'available');});
test('corrupt JSON is retained, with no silent overwrite',()=>{const {h,state,memory}=setup();memory.set(h.WORKSPACE_KEY,'{broken');state.champion=h.initialChampionState(state.hybrid);assert.equal(state.champion.recoveryRaw,'{broken');assert.equal(h.persistWorkspace(state),false);assert.equal(memory.get(h.WORKSPACE_KEY),'{broken');});
test('oversized cache is retained for recovery',()=>{const {h,state,memory}=setup();memory.set(h.WORKSPACE_KEY,'x'.repeat(100001));assert.ok(h.initialChampionState(state.hybrid).recoveryRaw);});
test('storage denied is reported as memory-only',()=>{const {h,state,sandbox}=setup();sandbox.localStorage.setItem=()=>{throw new Error('denied')};assert.equal(h.persistWorkspace(state),false);assert.equal(state.champion.storage,'unavailable');});
test('invalid draft cannot overwrite last valid cache',()=>{const {h,state,memory}=setup();h.persistWorkspace(state);const before=memory.get(h.WORKSPACE_KEY);state.hybrid.inputError='Check battery';assert.equal(h.persistWorkspace(state),false);assert.equal(memory.get(h.WORKSPACE_KEY),before);});
for(const [name,mutate] of [
 ['unknown schema',x=>x.schema='unknown'],['extra key',x=>x.inject='x'],['unknown lesson',x=>x.lesson_id='missing'],
 ['bad timestamp',x=>x.saved_at='invalid'],['bad reference',x=>x.last_run_id='../bad'],
 ['duplicate pins',x=>x.pinned_run_ids=[uuid,uuid]],['too many pins',x=>x.pinned_run_ids=[uuid,uuid,uuid,uuid]],
 ['out-of-range inputs',x=>x.inputs.battery_kwh=-1],['bad setup name',x=>x.saved_setups=[{id:'setup-'+uuid,name:' ',created_at:x.saved_at,inputs:x.inputs}]],
 ['duplicate setups',x=>{const s={id:'setup-'+uuid,name:'Test',created_at:x.saved_at,inputs:x.inputs};x.saved_setups=[s,s]}]
])test('workspace rejects '+name,()=>{const {h,state}=setup();const c=clone(h.workspaceCache(state));mutate(c);assert.throws(()=>h.parseWorkspace(c));});
test('named setups are escaped in rendered markup',()=>{const {h,state}=setup();state.champion.saved=[{id:'setup-'+uuid,name:'<img src=x onerror=alert(1)>',created_at:new Date().toISOString(),inputs:state.hybrid.inputs}];const html=h.workspaceDialog(state);assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img src=x'));});
test('configuration comparison ignores JSON key order',()=>{const {h,state}=setup();const reversed=Object.fromEntries(Object.entries(state.hybrid.inputs).reverse());assert.equal(h.configurationKey(reversed),h.configurationKey(state.hybrid.inputs));});
test('invalid in-progress input invalidates the result immediately',()=>{const {h,state}=setup();state.hybrid.inputError='Battery energy must be a number';assert.equal(h.hybridDirty(state.hybrid),true);const html=h.hybridResults(state);assert.match(html,/Battery energy must be a number/);assert.ok(!html.includes('98.9%'));});
test('palette finds battery screens with BESS alias',()=>{const {h}=setup();const rows=h.commandEntries('bess');assert.ok(rows.length>0);assert.ok(rows.some(r=>(r.label+r.detail).toLowerCase().includes('battery')));});
test('palette is bounded and handles no results',()=>{const {h}=setup();assert.ok(h.commandEntries('').length<=10);assert.equal(h.commandEntries('no-match-zzzz').length,0);});
test('history empty state is actionable',()=>{const {h}=setup();assert.match(h.historyRows([],''),/No matching runs/);});
function savedFixture(h,state){return {run_id:uuid,kind:'hybrid',created_at:new Date().toISOString(),input_sha256:'a'.repeat(64),inputs:clone(state.hybrid.inputs),result:clone(state.hybrid.result)};}
test('saved API result is reopened with exact inputs and metadata',()=>{const {h,state}=setup();const f=savedFixture(h,state);const saved=h.parseSavedHybrid(f);assert.equal(saved.run_id,uuid);assert.equal(saved.result.run_id,uuid);assert.deepEqual(clone(saved.inputs),f.inputs);});
for(const [name,mutate] of [
 ['wrong model',f=>f.result.model='made-up'],['mismatched system',f=>f.result.system_id='missing'],
 ['wrong horizon',f=>f.result.duration_hours=1],['missing schedule',f=>f.result.schedule=[]],
 ['nonfinite summary',f=>f.result.served_kwh=Infinity],['nonfinite hour',f=>f.result.schedule[0].load_kw=NaN],
 ['wrong row order',f=>f.result.schedule[0].hour=7],['unknown run kind',f=>f.kind='storage'],['malformed hash',f=>f.input_sha256='bad']
])test('saved result rejects '+name,()=>{const {h,state}=setup();const f=savedFixture(h,state);mutate(f);assert.throws(()=>h.parseSavedHybrid(f));});
