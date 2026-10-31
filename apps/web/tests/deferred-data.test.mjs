import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash,webcrypto} from 'node:crypto';
import {transform} from 'esbuild';
const source=fs.readFileSync(new URL('../src/deferred-data.ts',import.meta.url),'utf8');
const script=(await transform(source,{loader:'ts',target:'es2022'})).code;
function fixture(value,fetcher,{catalogue=[],workspace=null}={}){
  const bytes=Buffer.from(JSON.stringify(value)),sha256=createHash('sha256').update(bytes).digest('hex');
  const ref={path:`data/${sha256}.json`,sha256,bytes:bytes.length};
  const studyBundle={catalogue,results:{}};
  const events=[];
  const document={dispatchEvent:event=>{events.push({type:event.type,detail:event.detail,definitions:JSON.stringify(studyBundle.catalogue),results:JSON.stringify(studyBundle.results)});return true;}};
  class CustomEvent {constructor(type,options={}){this.type=type;this.detail=options.detail;}}
  const box=vm.createContext({URL,Intl,structuredClone,TextDecoder,Uint8Array,crypto:webcrypto,AbortSignal,location:{href:'https://example.test/run/#hybrid'},fetch:fetcher,document,CustomEvent});
  box.__HF_DATA_INDEX__={schema:'helioforge.hosted-data.v1',hybrid:{},workspaces:workspace?{[workspace]:ref}:{}};
  box.HF={STUDY_BUNDLE:studyBundle};
  box.STUDY_BUNDLE=studyBundle;
  vm.runInContext(script,box);return {hf:box.HF,ref,bytes,box,events,studyBundle};
}
const bodyResponse=bytes=>({ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)});
const fullDefinition=(id,title,page='research')=>({id,page,title,summary:`Summary for ${id}`,fields:[],equations:[],limitations:[],sources:[]});
const definitionIndex=definitions=>definitions.map(({id,page,title})=>({id,page,title}));
test('verified example requests coalesce and preserve exact decoded data',async()=>{
  let calls=0;const f=fixture({x:[1,null,3]},async()=>{calls++;return {ok:true,arrayBuffer:async()=>f.bytes.buffer.slice(f.bytes.byteOffset,f.bytes.byteOffset+f.bytes.byteLength)};});
  const [a,b]=await Promise.all([f.hf.loadExampleAsset(f.ref),f.hf.loadExampleAsset(f.ref)]);
  assert.equal(JSON.stringify(a),'{"x":[1,null,3]}');assert.equal(a,b);assert.equal(calls,1);
});
test('network failure retries; same-size corruption cannot be cached as an example',async()=>{
  let calls=0;const f=fixture({x:1},async()=>{calls++;if(calls===1)throw Error('offline');const bytes=Buffer.from(calls===2?'{"x":2}':'{"x":1}');return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};});
  await assert.rejects(f.hf.loadExampleAsset(f.ref),/offline/);
  await assert.rejects(f.hf.loadExampleAsset(f.ref),/integrity/);
  assert.equal(JSON.stringify(await f.hf.loadExampleAsset(f.ref)),'{"x":1}');assert.equal(calls,3);
});
test('manifest paths and sizes cannot escape the content-addressed local data directory',async()=>{
  const f=fixture({},()=>{throw Error('must not fetch');});
  await assert.rejects(f.hf.loadExampleAsset({...f.ref,path:'https://external.test/data.json'}),/manifest/);
  await assert.rejects(f.hf.loadExampleAsset({...f.ref,bytes:Infinity}),/manifest/);
});

test('study workspace fetch hydrates bootstrap definitions in place before exposing results',async()=>{
  const definitions=[fullDefinition('study-a','Study A'),fullDefinition('study-b','Study B')];
  const results={
    'study-a':{study:'study-a',series:[{name:'A',value:1.25}]},
    'study-b':{study:'study-b',series:[{name:'B',value:2.5}]},
  };
  const payload={catalogue:definitions,results};
  const bytes=Buffer.from(JSON.stringify(payload));
  const stubs=definitionIndex(definitions);
  const f=fixture(payload,async()=>bodyResponse(bytes),{catalogue:stubs,workspace:'research'});
  const originalArray=f.hf.STUDY_BUNDLE.catalogue;
  const originalDefinitions=[...originalArray];

  await f.hf.loadStudyExamples('research');

  assert.equal(f.hf.STUDY_BUNDLE.catalogue,originalArray);
  assert.equal(f.hf.STUDY_BUNDLE.catalogue[0],originalDefinitions[0]);
  assert.equal(f.hf.STUDY_BUNDLE.catalogue[1],originalDefinitions[1]);
  assert.equal(f.hf.STUDY_BUNDLE.catalogue[0].summary,'Summary for study-a');
  assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.results),JSON.stringify(results));
  assert.equal(f.events.length,1);
  assert.equal(f.events[0].type,'hf:examples-loaded');
  assert.equal(f.events[0].detail.page,'research');
  assert.equal(f.events[0].definitions,JSON.stringify(definitions));
  assert.equal(f.events[0].results,JSON.stringify(results));
});

test('invalid workspace definitions or results are rejected without partial hydration',async()=>{
  const definitions=[fullDefinition('study-a','Study A'),fullDefinition('study-b','Study B')];
  const results={
    'study-a':{study:'study-a',series:[1]},
    'study-b':{study:'study-b',series:[2]},
  };
  const invalidCatalogues=[
    {name:'missing definition',catalogue:[definitions[0]]},
    {name:'extra definition',catalogue:[...definitions,fullDefinition('study-c','Study C')]},
    {name:'duplicate definition',catalogue:[definitions[0],definitions[0]]},
    {name:'id mismatch',catalogue:[{...definitions[0],id:'other'},definitions[1]]},
    {name:'page mismatch',catalogue:[{...definitions[0],page:'storage'},definitions[1]]},
    {name:'title mismatch',catalogue:[{...definitions[0],title:'Different title'},definitions[1]]},
  ];

  for(const invalid of invalidCatalogues){
    const payload={catalogue:invalid.catalogue,results};
    const bytes=Buffer.from(JSON.stringify(payload));
    const stubs=definitionIndex(definitions);
    const f=fixture(payload,async()=>bodyResponse(bytes),{catalogue:stubs,workspace:'research'});
    const before=JSON.stringify(f.hf.STUDY_BUNDLE.catalogue);

    await assert.rejects(f.hf.loadStudyExamples('research'),/workspace|catalogue|definition|study/i,invalid.name);

    assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.catalogue),before,invalid.name);
    assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.results),'{}',invalid.name);
    assert.equal(f.events.length,0,invalid.name);
  }

  for(const invalidResults of [
    {'study-a':results['study-a']},
    {...results,'study-extra':{study:'study-extra'}},
    {...results,'study-a':{study:'wrong-study'}},
  ]){
    const payload={catalogue:definitions,results:invalidResults};
    const bytes=Buffer.from(JSON.stringify(payload));
    const stubs=definitionIndex(definitions);
    const f=fixture(payload,async()=>bodyResponse(bytes),{catalogue:stubs,workspace:'research'});
    const before=JSON.stringify(f.hf.STUDY_BUNDLE.catalogue);

    await assert.rejects(f.hf.loadStudyExamples('research'),/workspace|result|study/i);

    assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.catalogue),before);
    assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.results),'{}');
    assert.equal(f.events.length,0);
  }
});

test('network failure leaves bootstrap definitions intact and a retry hydrates the workspace',async()=>{
  const definitions=[fullDefinition('study-a','Study A')];
  const results={'study-a':{study:'study-a',series:[1.25]}};
  const payload={catalogue:definitions,results};
  const bytes=Buffer.from(JSON.stringify(payload));
  const stubs=definitionIndex(definitions);
  let calls=0;
  const f=fixture(payload,async()=>{
    calls++;
    if(calls===1)throw Error('offline');
    return bodyResponse(bytes);
  },{catalogue:stubs,workspace:'research'});
  const before=JSON.stringify(f.hf.STUDY_BUNDLE.catalogue);

  await assert.rejects(f.hf.loadStudyExamples('research'),/offline/);
  assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.catalogue),before);
  assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.results),'{}');
  assert.equal(f.events.length,0);

  await f.hf.loadStudyExamples('research');

  assert.equal(calls,2);
  assert.equal(f.hf.STUDY_BUNDLE.catalogue[0].summary,'Summary for study-a');
  assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.results),JSON.stringify(results));
  assert.equal(f.events.length,1);
});

test('study workspace loader rejects Object prototype-sensitive IDs before mutating result state',async()=>{
  for(const id of ['constructor','toString','__proto__','prototype','hasOwnProperty']){
    const definitions=[fullDefinition(id,'Study')];
    const results=Object.fromEntries([[id,{study:id,series:[1.25]}]]);
    const payload={catalogue:definitions,results};
    const bytes=Buffer.from(JSON.stringify(payload));
    const f=fixture(payload,async()=>bodyResponse(bytes),{catalogue:definitionIndex(definitions),workspace:'research'});
    const before=JSON.stringify(f.hf.STUDY_BUNDLE.catalogue);
    const resultsObject=f.hf.STUDY_BUNDLE.results;

    await assert.rejects(f.hf.loadStudyExamples('research'),/prototype-sensitive/i,id);

    assert.equal(JSON.stringify(f.hf.STUDY_BUNDLE.catalogue),before,id);
    assert.equal(Object.getPrototypeOf(resultsObject),Object.prototype,id);
    assert.equal(Object.hasOwn(resultsObject,id),false,id);
    assert.equal(f.events.length,0,id);
  }
});
