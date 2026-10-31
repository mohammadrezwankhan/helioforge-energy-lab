import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {planHostedData} from './hosted-data.mjs';

test('hosted data separates every frozen result without altering its bytes or numbers',()=>{
  const catalogue={version:'fixture',systems:[],lessons:[],scenarios:[]};
  const cases=[0,1,2].map(i=>({id:'case-'+i,inputs:{system_id:'system-'+i,scenario_id:'baseline'},result:{model:'test',schedule:[{x:i/3}]}}));
  const bundle={version:'fixture',schema:'helioforge.hybrid-bundle.v1',catalogue_version:'fixture',dataset_sha256:'a'.repeat(64),cases};
  const studyA={id:'hybrid-a',page:'hybrid',title:'Hybrid example',summary:'Hybrid summary',fields:[],equations:[],limitations:[],sources:[]};
  const studyB={id:'storage-b',page:'storage',title:'Storage example',summary:'Storage summary',fields:[],equations:[],limitations:[],sources:[]};
  const studies={catalogue:[studyA,studyB],results:{'hybrid-a':{study:'hybrid-a',series:[1.25]},'storage-b':{study:'storage-b',series:[2.5]}}};
  const result=planHostedData(catalogue,bundle,studies);
  assert.equal(Object.keys(result.index.hybrid).length,3);
  assert.equal(Object.keys(result.index.workspaces).length,2);
  assert.deepEqual(result.bootstrapHybrid.cases,[cases[0]]);
  assert.deepEqual(result.bootstrapStudies.catalogue,[
    {id:'hybrid-a',page:'hybrid',title:'Hybrid example'},
    {id:'storage-b',page:'storage',title:'Storage example'},
  ]);
  assert.deepEqual(result.bootstrapStudies.results,{});
  for(const [key,ref] of Object.entries(result.index.hybrid)){
    const bytes=result.assets.get(ref.path);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),ref.sha256);
    assert.deepEqual(JSON.parse(bytes),cases.find(c=>`${c.inputs.system_id}/${c.inputs.scenario_id}`===key));
  }
  assert.deepEqual(JSON.parse(result.assets.get(result.index.workspaces.storage.path)),{
    catalogue:[studyB],results:{'storage-b':studies.results['storage-b']},
  });
  assert.deepEqual(bundle.cases,cases);
});

test('hosted planner rejects duplicate study ids and results outside the catalogue',()=>{
  const catalogue={version:'fixture',systems:[],lessons:[],scenarios:[]};
  const bundle={version:'fixture',schema:'helioforge.hybrid-bundle.v1',catalogue_version:'fixture',dataset_sha256:'a'.repeat(64),cases:[]};
  const study={id:'study-a',page:'research',title:'Study A',summary:'A',fields:[],equations:[],limitations:[],sources:[]};
  const duplicate={catalogue:[study,{...study,title:'Duplicate'}],results:{'study-a':{study:'study-a'}}};
  const extraResult={catalogue:[study],results:{'study-a':{study:'study-a'},'study-extra':{study:'study-extra'}}};

  assert.throws(()=>planHostedData(catalogue,bundle,duplicate),/duplicate study id/i);
  assert.throws(()=>planHostedData(catalogue,bundle,extraResult),/study result set/i);
});

test('hosted planner rejects Object prototype-sensitive study ids',()=>{
  const catalogue={version:'fixture',systems:[],lessons:[],scenarios:[]};
  const bundle={version:'fixture',schema:'helioforge.hybrid-bundle.v1',catalogue_version:'fixture',dataset_sha256:'a'.repeat(64),cases:[]};
  for(const id of ['constructor','toString','__proto__','prototype','hasOwnProperty']){
    const study={id,page:'research',title:'Study',summary:'A',fields:[],equations:[],limitations:[],sources:[]};
    const studies={catalogue:[study],results:Object.fromEntries([[id,{study:id}]])};
    assert.throws(()=>planHostedData(catalogue,bundle,studies),/prototype-sensitive study id/i,id);
  }
});
