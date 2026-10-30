namespace HF {
  export const systemById=(id:string):HybridSystem=>{const s=HYBRID_CATALOG.systems.find(s=>s.id===id);if(!s)throw new Error('Unknown architecture.');return s;};
  export const scenarioById=(id:string):HybridScenario=>{const s=HYBRID_CATALOG.scenarios.find(s=>s.id===id);if(!s)throw new Error('Unknown scenario.');return s;};
  export const techById=(id:string):HybridTechnology=>{const t=HYBRID_CATALOG.technologies.find(t=>t.id===id);return t?{...t,color:'var(--color-accent)'}:{id,name:id==='load'?'Site demand':'Grid connection',icon:'grid',color:'var(--color-ink-2)',boundary:id==='load'?'Synthetic site demand; not a measured load profile.':'Utility connection; no power flow, fault or protection model.'};};
  export function applicable(s:HybridSystem,c:HybridScenario):boolean {
    const required:Record<string,string>={'cloud-cover':'solar','wind-lull':'wind','low-river':'hydro','generator-outage':'generator','battery-trip':'battery','aged-battery':'battery','reserve-floor':'battery'};
    const asset=required[c.id];if(asset&&!s.technologies.includes(asset))return false;
    if(['outage-4h','outage-24h','outage-72h','zero-export','export-cap','import-cap','negative-prices','price-spike','reconnection','weak-grid'].includes(c.id))return s.topology!=='Off-grid';
    if(c.id==='renewable-drought')return s.technologies.some(t=>t==='solar'||t==='wind');
    if(c.id==='black-start')return ['Off-grid','Islandable','Networked'].includes(s.topology);
    return true;
  }
  export function hybridTags(p:HybridInputs):HybridTag[] {
    const s=systemById(p.system_id);
    const tags:HybridTag[]=[{label:s.topology,reason:'Derived from the architecture interconnection.'},{label:s.coupling,reason:'Coupling shown conceptually. Electrical calculations are AC-equivalent.'},{label:p.control,reason:'Declared reference/control assumption, not a validated dynamic model.'},{label:s.mode==='study'?'Study only':'Energy screen',reason:'The numerical capability, not a safety or engineering approval.'}];
    if(p.battery_kw>0)tags.push({label:`${fmt(p.battery_kwh/p.battery_kw,1)} h storage`,reason:'Nameplate kWh / AC kW; excludes usable SOC window and losses.'});
    if(s.topology==='Off-grid')tags.push({label:'No grid support',reason:'The off-grid connection has zero import and export capacity.'});
    return tags;
  }
  export function filterSystems(search:string,family:string,topology:string):HybridSystem[] {
    const synonyms:Record<string,string>={pv:'solar',bess:'battery',h2:'hydrogen',standalone:'off-grid',backup:'island',gfm:'gfm',gfl:'gfl'};
    const terms=search.toLowerCase().trim().split(/\s+/).filter(Boolean).map(t=>synonyms[t]??t);
    return HYBRID_CATALOG.systems.filter(s=>(family==='All'||s.family===family)&&(topology==='All'||s.topology===topology)&&terms.every(t=>`${s.name} ${s.topology} ${s.family} ${s.control} ${s.coupling} ${s.technologies.join(' ')} ${s.description}`.toLowerCase().includes(t)));
  }
  export function presetInputs(systemId:string,scenarioId='baseline'):HybridInputs {
    const s=systemById(systemId),c=scenarioById(scenarioId);
    if(!applicable(s,c))throw new Error('This scenario does not apply to the selected architecture.');
    return {...s.preset,scenario_id:scenarioId,hours:Math.max(s.preset.hours,Number(c.modifiers.hours??0))};
  }
  export function parseConfiguration(raw:unknown):HybridInputs {
    if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('Configuration must be a JSON object.');
    const envelope=raw as Record<string,unknown>;
    const value=(envelope.schema==='helioforge.hybrid.v1'?envelope.inputs:raw) as Record<string,unknown>;
    if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('Missing configuration inputs.');
    if(typeof value.system_id!=='string'||typeof value.scenario_id!=='string')throw new Error('System and scenario IDs are required.');
    const base=presetInputs(value.system_id,value.scenario_id);
    const keys=Object.keys(base);
    if(Object.keys(value).some(k=>!keys.includes(k)))throw new Error('Unknown configuration field.');
    if(keys.some(k=>!(k in value)))throw new Error('Configuration has missing fields.');
    const limits:Record<string,[number,number]>={hours:[2,168],solar_kw:[0,1e6],wind_kw:[0,1e6],hydro_kw:[0,1e6],generator_kw:[0,1e6],battery_kwh:[0,1e7],battery_kw:[0,1e6],load_kw:[.000001,1e6],grid_import_kw:[0,1e6],grid_export_kw:[0,1e6],critical_fraction:[.000001,1],initial_soc:[0,1],min_soc:[0,.999999],max_soc:[.000001,1],round_trip_efficiency:[.000001,1],import_eur_kwh:[-2,5],export_eur_kwh:[-2,5],generator_eur_kwh:[0,5]};
    for(const [key,[lo,hi]] of Object.entries(limits)){const n=value[key];if(typeof n!=='number'||!Number.isFinite(n)||n<lo||n>hi)throw new Error(`${key} must be a finite number between ${lo} and ${hi}.`);}
    if(!Number.isInteger(value.hours))throw new Error('Hours must be an integer.');
    if(!['GFL','GFM','Dual','Synchronous'].includes(String(value.control)))throw new Error('Invalid control assumption.');
    const p=value as unknown as HybridInputs;
    if(p.min_soc>=p.max_soc||p.initial_soc<p.min_soc||p.initial_soc>p.max_soc)throw new Error('SOC must satisfy minimum <= initial <= maximum.');
    if((p.battery_kw===0)!==(p.battery_kwh===0))throw new Error('Battery power and energy must both be zero or both positive.');
    const s=systemById(p.system_id),c=scenarioById(p.scenario_id);
    const assetFields:{key:keyof HybridInputs;tech:string}[]=[{key:'solar_kw',tech:'solar'},{key:'wind_kw',tech:'wind'},{key:'hydro_kw',tech:'hydro'},{key:'generator_kw',tech:'generator'},{key:'battery_kwh',tech:'battery'}];
    if(assetFields.some(({key,tech})=>Number(p[key])>0&&!s.technologies.includes(tech)))throw new Error('A configured asset is absent from this architecture.');
    if(s.topology==='Off-grid'&&(p.grid_import_kw||p.grid_export_kw))throw new Error('Off-grid systems cannot import or export.');
    if(p.hours<Number(c.modifiers.hours??0))throw new Error('This scenario needs a longer horizon.');
    const floor=Number(c.modifiers.reserve_floor??p.min_soc);if(floor>p.initial_soc||floor>=p.max_soc)throw new Error('Reserve floor exceeds the initial SOC or usable window.');
    return {...p};
  }
  export function gradeLesson(lesson:Lesson,answers:number[]):{passed:boolean;correct:number;total:number} {
    const correct=lesson.quiz.filter((q,i)=>answers[i]===q.answer).length;
    return {passed:correct===lesson.quiz.length,correct,total:lesson.quiz.length};
  }
  const hybridPresets=new Map(HYBRID_BUNDLE.cases.map(entry=>[`${entry.inputs.system_id}/${entry.inputs.scenario_id}`,entry]));
  export function registerBundledHybridCase(entry:HybridBundledCase):void {
    const key=`${entry.inputs.system_id}/${entry.inputs.scenario_id}`;
    if(!hybridPresets.has(key)){hybridPresets.set(key,entry);HYBRID_BUNDLE.cases.push(entry);}
  }
  /** Only an exact frozen input record can display a build-time Python result. */
  export function bundledHybridCase(inputs:HybridInputs):HybridBundledCase|null {
    const entry=hybridPresets.get(`${inputs.system_id}/${inputs.scenario_id}`);
    return HYBRID_BUNDLE.catalogue_version===HYBRID_CATALOG.version&&entry&&configurationKey(entry.inputs)===configurationKey(inputs)?entry:null;
  }
  export function attachBundledHybridResult(h:HybridState):boolean {
    h.result=null;h.resultInputs=null;
    const entry=h.inputError?null:bundledHybridCase(h.inputs);
    if(!entry)return false;
    h.result=structuredClone(entry.result);h.resultInputs={...entry.inputs};h.hour=clamp(h.hour,0,h.result.schedule.length-1);
    return true;
  }
  export function initialHybridState():HybridState {
    let progress:string[]=[];
    try{const raw:unknown=JSON.parse(localStorage.getItem('hf-lessons-v2')??'[]');if(Array.isArray(raw))progress=[...new Set(raw.filter((x):x is string=>typeof x==='string'&&HYBRID_CATALOG.lessons.some(l=>l.id===x)))];}catch{/* Local persistence is optional. */}
    return {inputs:presetInputs('remote-triad'),result:structuredClone(HYBRID_EXAMPLE),resultInputs:presetInputs('remote-triad'),search:'',family:'All',topology:'All',lessonId:'lesson-remote-triad',progress,quizResult:null,objectId:'battery',hour:12,compare:[],busy:false,inputError:null,draft:null};
  }
  /** Canonical input equality is independent of JSON property order. Invalid drafts are never current. */
  export function configurationKey(inputs:HybridInputs|null):string {
    if(!inputs)return '';
    return JSON.stringify(Object.keys(inputs).sort().map(k=>[k,inputs[k as keyof HybridInputs]]));
  }
  export const hybridDirty=(h:HybridState):boolean=>Boolean(h.inputError)||configurationKey(h.inputs)!==configurationKey(h.resultInputs);

  const hybridRevisions=new WeakMap<HybridState,number>();
  export function hybridStateRevision(h:HybridState):number{return hybridRevisions.get(h)??0;}
  export function advanceHybridStateRevision(h:HybridState):number{
    const next=hybridStateRevision(h)+1;hybridRevisions.set(h,next);return next;
  }

  export interface HybridComparisonContract {
    comparable:boolean; provenance_complete:boolean; engine_id:string|null; data_kind:string|null;
    horizon_hours:number|null; dataset_revision:string|null; source_revision:string|null;
    units:'kW, kWh, EUR'; reasons:string[]; provenance_gaps:string[];
  }
  /** Describe whether period totals share one model/data/horizon contract before interpreting them. */
  export function hybridComparisonContract(runs:ComparedRun[]):HybridComparisonContract {
    const reasons:string[]=[],provenanceGaps:string[]=[];
    if(runs.length<2)reasons.push('At least two completed runs are needed for comparison.');
    const models=new Set<string>(),dataKinds=new Set<string>(),horizons=new Set<number>(),datasetRevisions=new Set<string>(),sourceRevisions=new Set<string>();
    for(const run of runs){
      const result=run.result as HybridResult&Record<string,unknown>;
      if(typeof result.model==='string'&&result.model)models.add(result.model);
      else reasons.push(`${run.name} has no engine identifier.`);
      if(typeof result.data_kind==='string'&&result.data_kind)dataKinds.add(result.data_kind);
      else reasons.push(`${run.name} has no data-origin label.`);
      const datasetRevision=result.dataset_revision;
      if(typeof datasetRevision==='string'&&datasetRevision)datasetRevisions.add(datasetRevision);
      else provenanceGaps.push(`${run.name} has no dataset revision.`);
      const sourceRevision=result.source_revision;
      if(typeof sourceRevision==='string'&&sourceRevision.trim())sourceRevisions.add(sourceRevision);
      else provenanceGaps.push(`${run.name} has no application source revision.`);
      if(Number.isInteger(result.duration_hours)&&result.duration_hours>0){
        horizons.add(result.duration_hours);
        if(result.duration_hours!==run.inputs.hours||!Array.isArray(result.schedule)||result.schedule.length!==result.duration_hours)
          reasons.push(`${run.name} does not match its declared input horizon.`);
      }else reasons.push(`${run.name} has no valid model horizon.`);
      if(!/^[a-f0-9]{64}$/i.test(String(result.input_sha256??'')))provenanceGaps.push(`${run.name} has no valid input SHA-256.`);
      if(systemById(run.inputs.system_id).mode!=='screening'||scenarioById(run.inputs.scenario_id).mode!=='screening')
        reasons.push(`${run.name} is outside the runnable screening applicability boundary.`);
    }
    if(models.size>1)reasons.push(`Engine versions differ (${[...models].join(', ')}).`);
    if(dataKinds.size>1)reasons.push(`Data origins differ (${[...dataKinds].join(', ')}).`);
    if(datasetRevisions.size>1)reasons.push(`Dataset revisions differ (${[...datasetRevisions].join(', ')}).`);
    if(sourceRevisions.size>1)reasons.push('Application source revisions differ.');
    if(horizons.size>1)reasons.push(`Model horizons differ (${[...horizons].sort((a,b)=>a-b).join(' h, ')} h); period totals are not directly comparable.`);
    const uniqueReasons=[...new Set(reasons)],uniqueGaps=[...new Set(provenanceGaps)];
    return {comparable:uniqueReasons.length===0&&uniqueGaps.length===0,provenance_complete:uniqueGaps.length===0,
      engine_id:models.size===1?[...models][0]!:null,data_kind:dataKinds.size===1?[...dataKinds][0]!:null,
      horizon_hours:horizons.size===1?[...horizons][0]!:null,dataset_revision:datasetRevisions.size===1?[...datasetRevisions][0]!:null,
      source_revision:sourceRevisions.size===1?[...sourceRevisions][0]!:null,units:'kW, kWh, EUR',reasons:uniqueReasons,provenance_gaps:uniqueGaps};
  }
}
