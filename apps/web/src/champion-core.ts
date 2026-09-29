namespace HF {
  export const WORKSPACE_KEY = 'hf-workspace-v3';
  export interface SavedSetup { id:string; name:string; created_at:string; inputs:HybridInputs }
  export interface WorkspaceCache {
    schema:'helioforge.workspace.v1'; saved_at:string; inputs:HybridInputs; lesson_id:string;
    last_run_id:string|null; pinned_run_ids:string[]; saved_setups:SavedSetup[];
  }
  export interface ChampionState {
    saved:SavedSetup[]; storage:'available'|'unavailable'; notice:string;
    lastRunId:string|null; pendingPins:string[]; restored:boolean; lastSavedAt:string|null;
    recoveryRaw:string|null;
  }
  export interface SavedHybrid { run_id:string; kind:'hybrid'; created_at:string; input_sha256:string; inputs:HybridInputs; result:HybridResult }
  export interface CommandEntry { id:string; label:string; detail:string; icon:string; kind:'page'|'system'|'lesson'|'action'; target:string }
  const isRecord=(x:unknown):x is Record<string,unknown>=>Boolean(x)&&typeof x==='object'&&!Array.isArray(x);
  const isRunId=(x:unknown):x is string=>typeof x==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(x);
  function timestamp(x:unknown):string {
    if(typeof x!=='string'||x.length>40||!Number.isFinite(Date.parse(x)))throw new Error('Invalid saved timestamp.');
    return x;
  }
  /** Read only the documented schema, bound resource use, and validate every configuration. */
  export function parseWorkspace(raw:unknown):WorkspaceCache {
    if(!isRecord(raw)||raw.schema!=='helioforge.workspace.v1')throw new Error('Unsupported workspace record.');
    const allowed=['schema','saved_at','inputs','lesson_id','last_run_id','pinned_run_ids','saved_setups'];
    if(Object.keys(raw).some(k=>!allowed.includes(k)))throw new Error('Unknown workspace field.');
    const inputs=parseConfiguration(raw.inputs);
    if(typeof raw.lesson_id!=='string'||!HYBRID_CATALOG.lessons.some(l=>l.id===raw.lesson_id))throw new Error('Unknown saved lesson.');
    if(raw.last_run_id!==null&&!isRunId(raw.last_run_id))throw new Error('Invalid saved run reference.');
    if(!Array.isArray(raw.pinned_run_ids)||raw.pinned_run_ids.length>3||!raw.pinned_run_ids.every(isRunId))throw new Error('Invalid comparison references.');
    if(new Set(raw.pinned_run_ids).size!==raw.pinned_run_ids.length)throw new Error('Duplicate comparison references.');
    if(!Array.isArray(raw.saved_setups)||raw.saved_setups.length>20)throw new Error('A workspace supports up to 20 saved setups.');
    const saved=raw.saved_setups.map((s:unknown):SavedSetup=>{
      if(!isRecord(s)||typeof s.id!=='string'||!/^setup-[a-f0-9-]{36}$/i.test(s.id))throw new Error('Invalid setup identifier.');
      if(typeof s.name!=='string'||!s.name.trim()||s.name.length>80)throw new Error('A setup name must contain 1–80 characters.');
      return {id:s.id,name:s.name.trim(),created_at:timestamp(s.created_at),inputs:parseConfiguration(s.inputs)};
    });
    if(new Set(saved.map(s=>s.id)).size!==saved.length)throw new Error('Duplicate setup identifiers.');
    return {schema:'helioforge.workspace.v1',saved_at:timestamp(raw.saved_at),inputs,lesson_id:raw.lesson_id,
      last_run_id:raw.last_run_id,pinned_run_ids:[...raw.pinned_run_ids],saved_setups:saved};
  }
  export function initialChampionState(h:HybridState):ChampionState {
    const c:ChampionState={saved:[],storage:'available',notice:'',lastRunId:null,pendingPins:[],restored:false,lastSavedAt:null,recoveryRaw:null};
    let raw:string|null=null;
    try { raw=localStorage.getItem(WORKSPACE_KEY); }
    catch { c.storage='unavailable';c.notice='Browser storage is unavailable. Keep this tab open and export your work.';return c; }
    if(!raw)return c;
    try {
      if(raw.length>100_000)throw new Error('Workspace record is too large.');
      const saved=parseWorkspace(JSON.parse(raw));
      h.inputs=saved.inputs;h.result=null;h.resultInputs=null;h.lessonId=saved.lesson_id;
      h.objectId=systemById(h.inputs.system_id).technologies[0]!;
      c.saved=saved.saved_setups;c.lastRunId=saved.last_run_id;c.pendingPins=saved.pinned_run_ids;c.lastSavedAt=saved.saved_at;
      c.notice='Your last valid setup is restored. Saved results are verified against the local API before display.';
    } catch {
      c.recoveryRaw=raw;c.notice='The saved workspace could not be read. It has not been overwritten. Open Saved setups to download or reset it.';
    }
    return c;
  }
  export function workspaceCache(state:ViewState):WorkspaceCache {
    const h=state.hybrid,c=state.champion;
    return {schema:'helioforge.workspace.v1',saved_at:new Date().toISOString(),inputs:parseConfiguration(h.inputs),
      lesson_id:h.lessonId,last_run_id:!hybridDirty(h)?h.result?.run_id??c?.lastRunId??null:null,
      pinned_run_ids:[...new Set([...h.compare.flatMap(r=>r.result.run_id?[r.result.run_id]:[]),...(c?.pendingPins??[])])].slice(0,3),
      saved_setups:c?.saved??[]};
  }
  /** A browser cache stores configurations and server IDs, never manufactured result objects or keys. */
  export function persistWorkspace(state:ViewState):boolean {
    const c=state.champion;if(!c||c.recoveryRaw||state.hybrid.inputError)return false;
    try {
      const record=workspaceCache(state),serialized=JSON.stringify(record);
      if(serialized.length>100_000)throw new Error('Workspace is too large. Export a setup and remove it from the shelf.');
      localStorage.setItem(WORKSPACE_KEY,serialized);c.storage='available';c.lastSavedAt=record.saved_at;
      return true;
    } catch { c.storage='unavailable';c.notice='Work is available in this tab but could not be stored. Export before closing.';return false; }
  }
  /** This validates an API response, not an arbitrary user-uploaded result. */
  export function parseSavedHybrid(raw:unknown):SavedHybrid {
    if(!isRecord(raw)||raw.kind!=='hybrid'||!isRunId(raw.run_id)||typeof raw.input_sha256!=='string'||!/^[a-f0-9]{64}$/i.test(raw.input_sha256))throw new Error('This is not a saved hybrid run.');
    const inputs=parseConfiguration(raw.inputs),r=raw.result;
    if(!isRecord(r)||r.model!=='hybrid-greedy-hourly-v1'||r.system_id!==inputs.system_id||r.scenario_id!==inputs.scenario_id||r.duration_hours!==inputs.hours||!Array.isArray(r.schedule)||r.schedule.length!==inputs.hours)throw new Error('The saved model result does not match its inputs.');
    if(!Array.isArray(r.warnings)||!r.warnings.every(v=>typeof v==='string')||!Array.isArray(r.tags)||!r.tags.every(t=>isRecord(t)&&typeof t.label==='string'&&typeof t.reason==='string'))throw new Error('Saved result metadata is incomplete.');
    const summaries=['total_load_kwh','served_kwh','unserved_kwh','critical_unserved_kwh','critical_served_pct','load_served_pct','renewable_available_kwh','grid_import_kwh','grid_export_kwh','generator_kwh','curtailed_kwh','charged_kwh','discharged_kwh','initial_energy_kwh','terminal_energy_kwh','battery_energy_delta_kwh','effective_capacity_kwh','effective_power_kw','variable_cost_eur','max_balance_residual_kw'];
    if(summaries.some(k=>typeof r[k]!=='number'||!Number.isFinite(r[k])))throw new Error('Saved summary contains invalid numbers.');
    const numeric=['hour','load_kw','target_load_kw','served_kw','critical_load_kw','pv_kw','wind_kw','hydro_kw','generator_kw','charge_kw','discharge_kw','grid_import_kw','grid_export_kw','curtailed_kw','unserved_kw','critical_unserved_kw','scheduled_shed_kw','soc_start_kwh','soc_end_kwh','soc_pct','import_eur_kwh','variable_cost_eur','balance_residual_kw'];
    if(r.schedule.some((p:unknown,i:number)=>!isRecord(p)||p.hour!==i||numeric.some(k=>typeof p[k]!=='number'||!Number.isFinite(p[k]))||typeof p.label!=='string'||typeof p.state!=='string'||typeof p.grid_connected!=='boolean'))throw new Error('Saved schedule is incomplete.');
    if(systemById(inputs.system_id).mode==='study'||scenarioById(inputs.scenario_id).mode==='study')throw new Error('Study-only configurations cannot have solved results.');
    const created=timestamp(raw.created_at);
    return {kind:'hybrid',run_id:raw.run_id,created_at:created,input_sha256:raw.input_sha256,inputs,
      result:{...r,run_id:raw.run_id,created_at:created,input_sha256:raw.input_sha256} as unknown as HybridResult};
  }
  export function commandEntries(query:string):CommandEntry[] {
    const actions:CommandEntry[]=[
      {id:'a-workspace',label:'Saved setups',detail:'Save, reopen and export your configurations',icon:'layers',kind:'action',target:'workspace'},
      {id:'a-guide',label:'Start a guided experiment',detail:'A baseline-to-outage walkthrough',icon:'play',kind:'action',target:'guide'},
      {id:'a-history',label:'Analysis history',detail:'Reopen or export a saved calculation',icon:'clock',kind:'action',target:'history'},
    ];
    const entries:CommandEntry[]=[...actions,...PAGES.map(p=>({id:`p-${p.id}`,label:p.title,detail:'Workspace',icon:p.icon,kind:'page' as const,target:p.id})),
      ...HYBRID_CATALOG.systems.map(s=>({id:`s-${s.id}`,label:s.name,detail:`${s.topology} · ${s.mode==='study'?'Study only':'Runnable screen'} · ${s.technologies.join(' ')}`,icon:'layers',kind:'system' as const,target:s.id})),
      ...HYBRID_CATALOG.lessons.map(l=>({id:`l-${l.id}`,label:l.title,detail:`Guided lesson · ${l.level}`,icon:'document',kind:'lesson' as const,target:l.id}))];
    const aliases:Record<string,string>={pv:'solar',bess:'battery',h2:'hydrogen'};
    const terms=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const matches=entries.filter(e=>terms.every(t=>{const hay=`${e.label} ${e.detail}`.toLowerCase();return hay.includes(t)||hay.includes(aliases[t]??t);}));
    return matches.slice(0,10);
  }
}
