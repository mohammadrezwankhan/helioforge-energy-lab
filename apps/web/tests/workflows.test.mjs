import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';

const bundle=process.env.HF_WORKFLOW_TEST_BUNDLE??new URL('../dist/app.js',import.meta.url);
const c=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,Map,structuredClone,crypto:webcrypto,TextEncoder,Uint8Array,btoa,atob});
vm.runInContext(fs.readFileSync(bundle,'utf8'),c);
const h=c.HF;

test('portfolio JSON-LD and GeoJSON serialize supplied synthetic records without invented coordinates',()=>{
 const projects=[{id:'p-1',name:'Solstice',market:'FR',technology:'PV',stage:'screening',pv_mwp:12,wind_mw:undefined,bess_mwh:4,capex_meur:9,progress:25}];
 const jsonld=h.portfolioJSONLD(projects),geo=h.portfolioGeoJSON(projects);
 assert.equal(jsonld.dataKind,'synthetic');
 assert.equal(jsonld.mainEntity.itemListElement[0].item.name,'Solstice');
 assert.equal(geo.features.length,1);
 assert.equal(geo.features[0].geometry,null);
 assert.equal(geo.features[0].properties.id,'p-1');
 assert.match(h.portfolioCSV(projects),/'Solstice|"Solstice"/);
});

test('portfolio CSV retains spreadsheet formula protection for text fields',()=>{
 const project={id:'p-2',name:'=IMPORTXML("x")',market:'FR',technology:'PV',stage:'screening',pv_mwp:1,bess_mwh:0,capex_meur:1,progress:0};
 assert.match(h.portfolioCSV([project]),/"'=IMPORTXML\(""x""\)"/);
});

test('paired comparison deltas use B minus A and preserve missing values as null',()=>{
 const a={load_served_pct:90,critical_unserved_kwh:0,grid_import_kwh:100,curtailed_kwh:5,terminal_energy_kwh:40};
 const b={load_served_pct:95,critical_unserved_kwh:2,grid_import_kwh:80,curtailed_kwh:null,terminal_energy_kwh:60};
 const delta=h.compareWorkflowMetrics(a,b);
 assert.deepEqual(JSON.parse(JSON.stringify(delta.map(x=>x.delta))),[5,2,-20,null,20]);
 assert.deepEqual(JSON.parse(JSON.stringify(delta.map(x=>x.tone))),['improved','worse','neutral','neutral','neutral']);
 assert.equal(delta[3].before,5);
 assert.equal(delta[3].after,null);
});

test('evidence merge verifies signatures and rejects changed payloads or duplicate keys',async()=>{
 const first=await h.signEvidence({record:'same',value:4});
 const second=await h.signEvidence({value:4,record:'same'});
 const merged=await h.mergeEvidenceEnvelopes([first,second]);
 assert.equal((await h.verifyEvidence(merged)).signers,2);
 assert.match(merged.signatures[0].identity,/unverified/);
 await assert.rejects(h.mergeEvidenceEnvelopes([first,await h.signEvidence({record:'other',value:4})]),/same payload/);
 await assert.rejects(h.mergeEvidenceEnvelopes([first,first]),/duplicate signer keys/);
 const changed=structuredClone(second);changed.payload.value=99;
 await assert.rejects(h.mergeEvidenceEnvelopes([first,changed]),/invalid/i);
});
