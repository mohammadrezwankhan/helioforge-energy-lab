namespace HF {
  interface DataAsset {path:string;sha256:string;bytes:number}
  interface HostedDataIndex {schema:string;hybrid:Record<string,DataAsset>;workspaces:Record<string,DataAsset>}
  const hostedIndex=(globalThis as unknown as {__HF_DATA_INDEX__?:HostedDataIndex}).__HF_DATA_INDEX__;
  const pendingExamples=new Map<string,Promise<unknown>>();
  const prototypeSensitiveStudyIds=new Set([...Object.getOwnPropertyNames(Object.prototype),'prototype']);
  function isRecord(value:unknown):value is Record<string,unknown> {return typeof value==='object'&&value!==null&&!Array.isArray(value)}
  function isSafeStudyId(value:unknown):value is string {return typeof value==='string'&&value.length>0&&!prototypeSensitiveStudyIds.has(value)}
  /** Only the exact build-manifest bytes may become a displayed example. Failed loads can retry. */
  export async function loadExampleAsset(ref:DataAsset):Promise<unknown> {
    if(!/^data\/[a-f0-9]{64}\.json$/.test(ref.path)||ref.path!==`data/${ref.sha256}.json`||!Number.isSafeInteger(ref.bytes)||ref.bytes<1||ref.bytes>12_000_000)throw Error('Invalid example manifest.');
    if(!pendingExamples.has(ref.path))pendingExamples.set(ref.path,(async()=>{
      const response=await fetch(new URL(ref.path,location.href),{credentials:'omit',cache:'force-cache',signal:AbortSignal.timeout(30000)});
      if(!response.ok)throw Error('Example download failed. Your inputs are retained.');
      const bytes=await response.arrayBuffer();
      if(bytes.byteLength!==ref.bytes)throw Error('Example size does not match this release.');
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
      if(digest!==ref.sha256)throw Error('Example integrity check failed. No result was loaded.');
      return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)) as unknown;
    })().catch(error=>{pendingExamples.delete(ref.path);throw error;}));
    return pendingExamples.get(ref.path)!;
  }
  export function deferredHybridAvailable(inputs:HybridInputs):boolean {
    return Boolean(hostedIndex?.hybrid[`${inputs.system_id}/${inputs.scenario_id}`])&&configurationKey(inputs)===configurationKey(presetInputs(inputs.system_id,inputs.scenario_id));
  }
  export async function loadHybridExample(inputs:HybridInputs):Promise<void> {
    const ref=hostedIndex?.hybrid[`${inputs.system_id}/${inputs.scenario_id}`];if(!ref||bundledHybridCase(inputs))return;
    const value=await loadExampleAsset(ref) as HybridBundledCase;
    if(configurationKey(value.inputs)!==configurationKey(inputs))throw Error('Example inputs do not match this selection.');
    registerBundledHybridCase(value);
  }
  export async function loadStudyExamples(page:string):Promise<void> {
    const ref=hostedIndex?.workspaces[page];if(!ref)throw Error('Examples are unavailable in this edition.');
    const value=await loadExampleAsset(ref);
    if(!isRecord(value)||!Array.isArray(value.catalogue)||!isRecord(value.results))throw Error('Example workspace does not match this release.');
    const index=STUDY_BUNDLE.catalogue as unknown[];
    const expected:StudyDefinition[]=[];
    const allIds=new Set<string>();
    for(const candidate of index){
      if(!isRecord(candidate)||typeof candidate.page!=='string'||!candidate.page||typeof candidate.title!=='string'||!candidate.title)throw Error('Example workspace index does not match this release.');
      if(!isSafeStudyId(candidate.id))throw Error('Prototype-sensitive or invalid study id in workspace index.');
      if(allIds.has(candidate.id))throw Error('Duplicate study id in the workspace index.');
      allIds.add(candidate.id);
      if(candidate.page===page)expected.push(candidate as unknown as StudyDefinition);
    }
    if(expected.length===0)throw Error('Example workspace does not match this release.');
    const expectedById=new Map(expected.map(definition=>[definition.id,definition]));
    if(value.catalogue.length!==expected.length)throw Error('Example workspace definitions do not match this release.');
    const definitionsById=new Map<string,StudyDefinition>();
    for(const candidate of value.catalogue){
      if(!isRecord(candidate)||typeof candidate.page!=='string'||typeof candidate.title!=='string'||typeof candidate.summary!=='string'||!Array.isArray(candidate.fields)||!Array.isArray(candidate.equations)||!Array.isArray(candidate.limitations)||!Array.isArray(candidate.sources)||(candidate.kind!==undefined&&typeof candidate.kind!=='string')||(candidate.data_fields!==undefined&&!Array.isArray(candidate.data_fields))||Object.keys(candidate).some(key=>key==='__proto__'||key==='constructor'||key==='prototype'))throw Error('Example workspace definition is invalid.');
      if(!isSafeStudyId(candidate.id))throw Error('Prototype-sensitive or invalid study id in workspace definition.');
      const stub=expectedById.get(candidate.id);
      if(!stub||stub.page!==candidate.page||stub.title!==candidate.title||definitionsById.has(candidate.id))throw Error('Example workspace definitions do not match this release.');
      definitionsById.set(candidate.id,candidate as unknown as StudyDefinition);
    }
    const resultIds=Object.keys(value.results);
    if(resultIds.length!==expected.length||resultIds.some(id=>!expectedById.has(id)))throw Error('Example workspace results do not match this release.');
    for(const id of expectedById.keys()){
      const result=value.results[id];
      if(!isRecord(result)||result.study!==id)throw Error('Example workspace result does not match this release.');
    }
    if(!isRecord(STUDY_BUNDLE.results))throw Error('Example workspace results cannot be loaded in this edition.');
    // Validate the complete payload before mutating these bootstrap objects: callers may hold references to them.
    for(const stub of expected)Object.assign(stub,definitionsById.get(stub.id)!);
    for(const id of expectedById.keys())STUDY_BUNDLE.results[id]=value.results[id] as StudyResult;
    document.dispatchEvent(new CustomEvent('hf:examples-loaded',{detail:{page}}));
  }
}
