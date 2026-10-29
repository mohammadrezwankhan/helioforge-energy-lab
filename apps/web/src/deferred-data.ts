namespace HF {
  interface DataAsset {path:string;sha256:string;bytes:number}
  interface HostedDataIndex {schema:string;hybrid:Record<string,DataAsset>;workspaces:Record<string,DataAsset>}
  const hostedIndex=(globalThis as unknown as {__HF_DATA_INDEX__?:HostedDataIndex}).__HF_DATA_INDEX__;
  const pendingExamples=new Map<string,Promise<unknown>>();
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
    const value=await loadExampleAsset(ref) as {results:Record<string,StudyResult>};
    const definitions=STUDY_BUNDLE.catalogue.filter(s=>s.page===page);
    if(!value.results||definitions.some(d=>value.results[d.id]?.study!==d.id))throw Error('Example workspace does not match this release.');
    for(const def of definitions)STUDY_BUNDLE.results[def.id]=value.results[def.id]!;
    document.dispatchEvent(new CustomEvent('hf:examples-loaded',{detail:{page}}));
  }
}
