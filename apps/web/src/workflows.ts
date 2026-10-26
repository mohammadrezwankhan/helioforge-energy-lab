namespace HF {
  export interface WorkflowDelta { key: keyof HybridResult; label: string; unit: string; before: number | null; after: number | null; delta: number | null; digits: number; direction:'higher'|'lower'|'context'; tone:'improved'|'worse'|'neutral' }
  export interface WorkflowGeoJSON { type: 'FeatureCollection'; features: { type: 'Feature'; geometry: null; properties: Project }[] }

  const workflowMetrics: { key: keyof HybridResult; label: string; unit: string; digits: number; direction:'higher'|'lower'|'context' }[] = [
    {key:'load_served_pct',label:'Total load served',unit:'%',digits:1,direction:'higher'},
    {key:'critical_unserved_kwh',label:'Critical shortfall',unit:'kWh',digits:1,direction:'lower'},
    {key:'grid_import_kwh',label:'Grid imports',unit:'kWh',digits:1,direction:'context'},
    {key:'curtailed_kwh',label:'Renewable curtailment',unit:'kWh',digits:1,direction:'lower'},
    {key:'terminal_energy_kwh',label:'Terminal battery energy',unit:'kWh',digits:1,direction:'context'},
  ];

  /** Serializations preserve the synthetic portfolio and never infer project coordinates. */
  export function portfolioJSONLD(projects: Project[]): Record<string, unknown> {
    return {'@context':'https://schema.org','@type':'Dataset',name:'HelioForge synthetic portfolio',description:'Illustrative fictional project records; no geographic coordinates are supplied.',distribution:{'@type':'DataDownload',encodingFormat:'application/json'},mainEntity:{'@type':'ItemList',itemListElement:projects.map((project,position)=>({'@type':'ListItem',position:position+1,item:{'@type':'Project',...project}}))},dataKind:'synthetic'};
  }
  export function portfolioGeoJSON(projects: Project[]): WorkflowGeoJSON {
    return {type:'FeatureCollection',features:projects.map(properties=>({type:'Feature',geometry:null,properties}))};
  }
  export function portfolioCSV(projects: Project[]): string {
    return toCSV(projects.map(p=>({id:p.id,name:p.name,market:p.market,technology:p.technology,stage:p.stage,pv_mwp:p.pv_mwp,wind_mw:p.wind_mw??null,bess_mwh:p.bess_mwh,capex_meur:p.capex_meur,progress:p.progress})));
  }
  export function compareWorkflowMetrics(a: HybridResult, b: HybridResult): WorkflowDelta[] {
    return workflowMetrics.map(metric=>{
      const rawA=a[metric.key],rawB=b[metric.key];
      const before=typeof rawA==='number'&&Number.isFinite(rawA)?rawA:null;
      const after=typeof rawB==='number'&&Number.isFinite(rawB)?rawB:null;
      const delta=before===null||after===null?null:after-before;
      const tone=delta===null||delta===0||metric.direction==='context'?'neutral':(metric.direction==='higher'?delta>0:delta<0)?'improved':'worse';
      return {...metric,before,after,delta,tone};
    });
  }

  const isRecord=(value:unknown):value is Record<string,unknown>=>Boolean(value)&&typeof value==='object'&&!Array.isArray(value);
  function assertEvidenceEnvelope(value:unknown):asserts value is EvidenceEnvelope {
    if(!isRecord(value)||value.format!=='helioforge-evidence-v1'||typeof value.sha256!=='string'||!(/^[a-f0-9]{64}$/i).test(value.sha256)||!Array.isArray(value.signatures))throw new Error('This is not a HelioForge signed evidence envelope.');
    if(value.signatures.length<1||value.signatures.length>20)throw new Error('An evidence envelope must have 1–20 signatures.');
    for(const signer of value.signatures){
      if(!isRecord(signer)||signer.algorithm!=='ECDSA-P256-SHA256'||!isRecord(signer.public_key)||typeof signer.signature!=='string'||typeof signer.identity!=='string')throw new Error('Evidence signature metadata is incomplete.');
    }
    try{canonicalEvidence(value.payload);}catch{throw new Error('Evidence payload must contain JSON values.');}
  }
  export async function verifyImportedEvidence(value:unknown):Promise<EvidenceEnvelope> {
    assertEvidenceEnvelope(value);
    const result=await verifyEvidence(value);
    if(!result.valid)throw new Error('Evidence signature or payload digest is invalid.');
    return value;
  }
  /** Independently signed envelopes merge only when their exact payload and digest match. */
  export async function mergeEvidenceEnvelopes(values:unknown[]):Promise<EvidenceEnvelope> {
    if(values.length<1||values.length>20)throw new Error('Select 1–20 evidence files to verify.');
    const envelopes:EvidenceEnvelope[]=[];
    for(const value of values)envelopes.push(await verifyImportedEvidence(value));
    const first=envelopes[0]!;
    const canonical=canonicalEvidence(first.payload),keys=new Set<string>(),signatures:EvidenceEnvelope['signatures']=[];
    for(const envelope of envelopes){
      if(envelope.sha256!==first.sha256||canonicalEvidence(envelope.payload)!==canonical)throw new Error('Signatures can merge only when every file contains the same payload and SHA-256 digest.');
      for(const signature of envelope.signatures){
        const key=`${String(signature.public_key.x)}:${String(signature.public_key.y)}`;
        if(keys.has(key))throw new Error('Cannot merge duplicate signer keys.');
        keys.add(key);signatures.push(signature);
        if(signatures.length>20)throw new Error('A merged evidence envelope supports at most 20 signers.');
      }
    }
    return {...first,signatures};
  }

  interface PilotStudyInfo { id:string; label:string; register:string; sampleInterval:string }
  const pilotStudyInfo:PilotStudyInfo[]=[
    {id:'pilots-photogrammetry',label:'Paired as-built geometry',register:'Paired design/as-built XYZ points and coordinate residuals',sampleInterval:'One paired point per row; no time cadence is specified.'},
    {id:'pilots-dts',label:'Distributed temperature profile',register:'Fibre distance, temperature and observation time',sampleInterval:'Bundled positions are illustrative 10 m steps; no live polling cadence.'},
    {id:'pilots-offgas',label:'Hypothetical multisensor vote',register:'Sensor identifier, temperature, CO and VOC channels',sampleInterval:'No timestamps or acquisition interval are supplied.'},
  ];
  const study=(id:string):StudyResult|undefined=>STUDY_BUNDLE.results[id];
  const val=(value:unknown):string=>value===null||value===undefined?'—':typeof value==='number'?(Number.isFinite(value)?fmt(value,3):'—'):String(value);
  const workflowPanel=(title:string,subtitle:string,body:string):string=>`<section id="workflow-panel" class="panel workflow-panel"><div class="section-heading"><div><span class="eyebrow">LOCAL WORKFLOW / EVIDENCE CONTROLS</span><h2>${escapeHTML(title)}</h2><p>${escapeHTML(subtitle)}</p></div></div>${body}</section>`;
  const downloadText=(name:string,value:unknown,mime='application/json'):void=>download(name,typeof value==='string'?value:JSON.stringify(value,null,2),mime);

  function overviewPanel():string {
    return workflowPanel('Evidence and portfolio exports','Expandable, source-backed exports for the portfolio currently loaded in this browser.',
      `<details class="workflow-drawer"><summary>Open portfolio export drawer</summary><p>Every portfolio entry is a fictional screening record. GeoJSON features have <code>geometry: null</code> because no coordinates are available.</p><div class="workflow-actions"><button class="btn secondary small" data-workflow-action="portfolio-jsonld">Download JSON-LD</button><button class="btn secondary small" data-workflow-action="portfolio-geojson">Download GeoJSON</button><button class="btn secondary small" data-workflow-action="portfolio-csv">Download portfolio CSV</button></div><div class="workflow-import"><label class="field"><span>Verify signed evidence files (up to 1 MB each)</span><input type="file" accept=".json,application/json" multiple data-workflow-import></label><p id="workflow-import-status" class="workflow-status" role="status" aria-live="polite">Imported signers are cryptographically checked, but their people and authority remain unverified.</p></div></details>`);
  }
  function lessonsPanel(state:ViewState):string {
    const lessons=HYBRID_CATALOG.lessons,lessonIds=new Set(lessons.map(lesson=>lesson.id)),done=new Set(state.hybrid.progress.filter(id=>lessonIds.has(id)));
    const guidance=(level:string):string=>level==='Intermediate'?'Suggested preparation: complete Foundation lessons first. This is guidance, not an accreditation gate.':level==='Advanced'?'Suggested preparation: work through Foundation and Intermediate lessons first. This is guidance, not an accreditation gate.':'Foundation tier; no earlier tier is assumed.';
    return workflowPanel('Learning skill tree','Hexagonal shortcuts to all catalogue lessons. Progress reflects local self-checks only.',
      `${lessons.length?`<div class="skill-tree" role="group" aria-label="Lesson skill tree">${lessons.map((lesson,index)=>{const ordinal=String(index+1).padStart(2,'0');return `<button type="button" data-lesson="${escapeHTML(lesson.id)}" class="${done.has(lesson.id)?'done ':''}${state.hybrid.lessonId===lesson.id?'selected':''}" aria-pressed="${state.hybrid.lessonId===lesson.id}" aria-label="${ordinal} ${escapeHTML(lesson.level)}: ${escapeHTML(lesson.title)}; ${done.has(lesson.id)?'self-check passed':'not passed'}" title="${escapeHTML(guidance(lesson.level))}"><span>${ordinal}</span><small>${escapeHTML(lesson.level)}</small></button>`;}).join('')}</div>`:'<p class="notice">The lesson catalogue is unavailable.</p>'}<p class="workflow-note" data-learning-progress-note>${lessonProgressNote(state.hybrid.progress)}</p><button class="btn secondary small" data-workflow-action="sign-progress">Sign local completion record</button><p id="workflow-learning-status" class="workflow-status" role="status" aria-live="polite">The signed record will include only saved completion IDs and the matching lesson titles, tiers and source references.</p>`);
  }
  function comparePanel(state:ViewState,overlay:boolean):string {
    const runs=state.hybrid.compare;
    if(runs.length<2)return workflowPanel('Isometric run comparison','Pin at least two actual hybrid results to inspect paired metrics.',`<p class="notice">This view uses only runs already pinned in Scenario compare. It does not create a missing run.</p>`);
    const a=runs[0]!,b=runs[1]!,deltas=compareWorkflowMetrics(a.result,b.result);
    return workflowPanel('Isometric run comparison','Pinned run A and B are displayed with deltas calculated from their saved results.',
      `<p class="notice warn">Review horizon, served demand and initial/terminal SOC before interpreting a delta. Cost or service differences do not establish a winner.</p><div class="comparison-stages ${overlay?'overlay':''}"><article><span class="tag muted">RUN A</span><h3>${escapeHTML(a.name)}</h3><p>${escapeHTML(a.result.run_id??a.id)} · ${a.result.duration_hours} modeled hours</p><strong>${fmt(a.result.load_served_pct,1)}% load served</strong><small>Initial ${fmt(a.result.initial_energy_kwh,1)} kWh · terminal ${fmt(a.result.terminal_energy_kwh,1)} kWh</small></article><article><span class="tag muted">RUN B</span><h3>${escapeHTML(b.name)}</h3><p>${escapeHTML(b.result.run_id??b.id)} · ${b.result.duration_hours} modeled hours</p><strong>${fmt(b.result.load_served_pct,1)}% load served</strong><small>Initial ${fmt(b.result.initial_energy_kwh,1)} kWh · terminal ${fmt(b.result.terminal_energy_kwh,1)} kWh</small></article></div><button class="btn secondary small" data-workflow-action="toggle-overlay" aria-pressed="${overlay}">${overlay?'Show side by side':'Overlay run cards'}</button><div class="table-scroll"><table class="workflow-delta-table"><thead><tr><th>Metric</th><th>A</th><th>B</th><th>Δ B − A</th></tr></thead><tbody>${deltas.map(item=>`<tr><th>${item.label}</th><td>${item.before===null?'—':`${fmt(item.before,item.digits)} ${item.unit}`}</td><td>${item.after===null?'—':`${fmt(item.after,item.digits)} ${item.unit}`}</td><td class="delta-${item.tone}">${item.delta===null?'—':`${item.delta>0?'+':''}${fmt(item.delta,item.digits)} ${item.unit}`}</td></tr>`).join('')}</tbody></table></div>`);
  }
  function pilotPanel(selected:string):string {
    const options=pilotStudyInfo.map(item=>`<option value="${item.id}" ${selected===item.id?'selected':''}>${escapeHTML(item.label)}</option>`).join('');
    const info=pilotStudyInfo.find(item=>item.id===selected)??pilotStudyInfo[0]!;
    const result=study(info.id);
    return workflowPanel('Synthetic pilot telemetry inspector','Three bundled study examples, with their supplied tables and limitations; no sensor is connected.',
      `<div class="workflow-inline"><label class="field"><span>Study example</span><select data-workflow-sensor>${options}</select></label><span class="tag muted">SYNTHETIC · NOT CONNECTED</span></div><div class="telemetry-hud"><strong>Illustrative register mapping</strong><p>${escapeHTML(info.register)}</p><strong>Illustrative sample interval</strong><p>${escapeHTML(info.sampleInterval)}</p><small>These are study metadata only. No Modbus device, live telemetry, alarm or field result is read.</small></div>${result?`<div class="result-stats">${result.metrics.map(metric=>`<div><span>${escapeHTML(metric.label)}</span><strong>${escapeHTML(val(metric.value))} <small>${escapeHTML(metric.unit)}</small></strong></div>`).join('')}</div><details class="method-details"><summary>Supplied synthetic study rows</summary>${studyTable(result.table??[])}</details><details class="method-details"><summary>Study limits</summary>${[...(result.limitations??[]),...(result.warnings??[])].map(line=>`<p>${escapeHTML(line)}</p>`).join('')}</details>`:'<p class="notice">No bundled result is available for this study in the current browser catalogue.</p>'}<p id="workflow-pilot-status" class="workflow-status" role="status" aria-live="polite">Drag a connected pilot card to a stage to open its existing evidence form. Keyboard users can open Review evidence and choose a stage. Add a new human note and submit to save.</p><button class="btn secondary small" data-workflow-action="sign-pilot-registry">Sign local pilot registry</button>`);
  }
  function researchPanel():string {
    return workflowPanel('Research dossier','Compile existing research outputs and study evidence without recalculating or changing any values.',
      `<p>This export reuses the currently loaded drift, reliability, sustainability and source records. Results remain screening evidence with their existing warnings.</p><button class="btn secondary small" data-workflow-action="research-dossier">Download research dossier</button>`);
  }
  function investmentPanel():string {
    return workflowPanel('Investment committee memo','Compile current finance, PV and acquisition screens with their existing assumptions and limits.',
      `<p>The memo preserves current state values and does not add a recommendation, recompute a cash flow or imply approval. The experimental study memo remains available in its study panel.</p><button class="btn secondary small" data-workflow-action="investment-memo">Download current-state IC memo</button>`);
  }
  function councilTranscriptHTML(filter:string,cursor:number):string {
    const result=study('council-debate'),rows=result?.table??[];
    const relevant=rows.filter(row=>filter==='finance'?row.proposer!==null&&row.proposer!==undefined:filter==='storage'?row.challenger!==null&&row.challenger!==undefined:filter==='risk'?row.status!=='convergent_within_declared_tolerance':true);
    const through=relevant.filter(row=>typeof row.round==='number'&&row.round<=cursor);
    return through.length?`<ol class="workflow-transcript">${through.map(row=>`<li><span>Round ${escapeHTML(row.round)}</span><strong>${escapeHTML(row.topic)}</strong><span class="tag muted">${escapeHTML(row.status)}</span><p>${row.proposer?`Finance: ${escapeHTML((row.proposer as Record<string,unknown>).statement)}`:'Finance: no assertion supplied.'}</p><p>${row.challenger?`Storage: ${escapeHTML((row.challenger as Record<string,unknown>).statement)}`:'Storage: no assertion supplied.'}</p><p>${escapeHTML(row.resolution)}</p></li>`).join('')}</ol>`:'<p class="notice">No debate rows match this filter and replay position.</p>';
  }
  function councilPanel(state:ViewState,filter:string,cursor:number):string {
    const rows=study('council-debate')?.table??[],lastRound=rows.reduce((max,row)=>typeof row.round==='number'?Math.max(max,row.round):max,0);
    const mode=state.data.council.mode==='local'?'Local deterministic checklist; no external agent executed.':`Recorded council mode: ${state.data.council.mode} · ${state.data.council.execution}.`;
    return workflowPanel('Council transcript and determination','Replay the bundled structured finance/storage study and seal the current council record.',
      `<p class="notice">${escapeHTML(mode)} The study transcript contains deterministic evidence comparisons, not a live debate.</p>${lastRound?`<div class="workflow-replay"><label class="field"><span>Transcript perspective</span><select data-workflow-council-filter><option value="all" ${filter==='all'?'selected':''}>All rounds</option><option value="finance" ${filter==='finance'?'selected':''}>Finance assertions</option><option value="storage" ${filter==='storage'?'selected':''}>Storage assertions</option><option value="risk" ${filter==='risk'?'selected':''}>Unresolved / risk</option></select></label><label class="field"><span>Replay through round <output id="workflow-round-value">${cursor}</output> of ${lastRound}</span><input type="range" min="1" max="${lastRound}" value="${cursor}" data-workflow-council-round aria-label="Council transcript round"></label><div id="workflow-council-transcript">${councilTranscriptHTML(filter,cursor)}</div></div>`:'<p class="notice">No council-debate study rows are bundled.</p>'}<button class="btn secondary small" data-workflow-action="sign-council">Sign council determination envelope</button><p id="workflow-council-status" class="workflow-status" role="status" aria-live="polite">Signatures use ephemeral local browser keys. The key does not verify a person, office or authority.</p>`);
  }
  function valueList(data:Record<string,unknown>):string {
    return Object.entries(data).map(([key,value])=>`- ${key}: ${value===null?'not applicable':typeof value==='object'?JSON.stringify(value):String(value)}`).join('\n');
  }
  function researchDossier(state:ViewState):string {
    const s=state.data;
    const studies=STUDY_BUNDLE.catalogue.filter(def=>def.page==='research').map(def=>({study:def.title,result:STUDY_BUNDLE.results[def.id]??null}));
    return ['# HelioForge research dossier','',`Generated from current browser state: ${new Date().toISOString()}`,'','## Existing research results',...['drift','reliability','sustainability'].map(key=>`### ${key}\n\n\`\`\`json\n${JSON.stringify(s[key as 'drift'|'reliability'|'sustainability'],null,2)}\n\`\`\``),'','## Bundled study evidence','```json',JSON.stringify(studies,null,2),'```','','## Source register','```json',JSON.stringify(s.sources,null,2),'```','','## Boundaries','All bundled cases are synthetic screening examples. The export does not validate source facts or recalculate results.'].join('\n');
  }
  function investmentMemo(state:ViewState):string {
    const d=state.data;
    return ['# Investment committee screening memo','',`Compiled: ${new Date().toISOString()}`,'','## Current finance result',...valueList(d.finance as unknown as Record<string,unknown>).split('\n'),'','## Existing assumptions','```json',JSON.stringify({finance:d.defaults.finance,pv:d.defaults.pv,acquisition:d.defaults.acquisition},null,2),'```','','## Related screens','```json',JSON.stringify({pv:d.pv,acquisition:d.acquisition},null,2),'```','','## Review limits',...d.finance.warnings.map(w=>`- ${w}`),...d.pv.warnings.map(w=>`- ${w}`),...d.acquisition.warnings.map(w=>`- ${w}`),'- These independent screening cases are not reconciled into an investment model.','- This memo is not an investment recommendation or approval.'].join('\n');
  }
  function referencedRun(state:ViewState):Record<string,unknown>|null {
    const id=state.data.council.hybrid_run_id;if(!id)return null;
    const saved=state.runs.find(run=>run.id===id);
    if(saved)return {id:saved.id,input_sha256:saved.input_hash,created_at:saved.created_at};
    const pinned=state.hybrid.compare.find(run=>run.id===id||run.result.run_id===id);
    if(pinned)return {id:pinned.result.run_id??pinned.id,input_sha256:pinned.result.input_sha256??null,created_at:pinned.result.created_at??null};
    const current=state.hybrid.result?.run_id===id?state.hybrid.result:null;
    return current?{id:current.run_id,input_sha256:current.input_sha256??null,created_at:current.created_at??null}:null;
  }
  function setStatus(id:string,message:string):void {const el=document.getElementById(id);if(el)el.textContent=message;}

  export function createWorkflowController(getState:()=>ViewState,render:()=>void):{refresh:()=>void} {
    let overlay=false,selectedPilotStudy='pilots-photogrammetry',councilFilter='all',councilRound=1;
    let importedEnvelope:EvidenceEnvelope|null=null;
    function refresh():void {
      const state=getState(),host=document.getElementById('page-content');
      document.getElementById('workflow-panel')?.remove();
      if(!host)return;
      let html='';
      if(state.page==='overview')html=overviewPanel();
      else if(state.page==='lessons')html=lessonsPanel(state);
      else if(state.page==='compare')html=comparePanel(state,overlay);
      else if(state.page==='pilots')html=pilotPanel(selectedPilotStudy);
      else if(state.page==='research')html=researchPanel();
      else if(state.page==='investment')html=investmentPanel();
      else if(state.page==='council')html=councilPanel(state,councilFilter,councilRound);
      if(html)host.insertAdjacentHTML('beforeend',html);
      if(state.page==='overview')document.querySelector('.workflow-import')?.insertAdjacentHTML('beforeend',`<button class="btn secondary small" data-workflow-action="cosign-import" ${importedEnvelope?'':'disabled'}>Add local co-signature and export</button><p>Review the payload before signing. Co-signatures prove possession of distinct keys, not independent people or institutional approval.</p><details><summary>Imported payload for review</summary><pre id="workflow-import-payload">${importedEnvelope?escapeHTML(JSON.stringify(importedEnvelope.payload,null,2)):'No verified payload imported.'}</pre></details>`);
    }
    async function signedDownload(statusId:string,name:string,payload:unknown):Promise<void> {
      const envelope=await signEvidence(payload);downloadText(name,envelope);setStatus(statusId,`Signed with ${envelope.signatures.length} ephemeral local key. Signer identity and authority are unverified.`);
    }
    async function act(action:string):Promise<void> {
      const state=getState();
      if(action==='portfolio-jsonld')downloadText('helioforge-portfolio.jsonld',portfolioJSONLD(state.data.portfolio),'application/ld+json');
      else if(action==='cosign-import'&&importedEnvelope){
        const additional=await signEvidence(importedEnvelope.payload);
        const combined=await mergeEvidenceEnvelopes([importedEnvelope,additional]);
        downloadText('helioforge-cosigned-evidence.json',combined);
        setStatus('workflow-import-status',`Exported ${combined.signatures.length} distinct valid signatures. People and authority remain unverified.`);
      }
      else if(action==='portfolio-geojson')downloadText('helioforge-portfolio.geojson',portfolioGeoJSON(state.data.portfolio),'application/geo+json');
      else if(action==='portfolio-csv')downloadText('helioforge-portfolio.csv',portfolioCSV(state.data.portfolio),'text/csv');
      else if(action==='sign-progress'){
        const progress=state.hybrid.progress.map(id=>HYBRID_CATALOG.lessons.find(lesson=>lesson.id===id)).filter((lesson):lesson is Lesson=>Boolean(lesson));
        await signedDownload('workflow-learning-status','helioforge-local-learning-evidence.json',{schema:'helioforge-learning-evidence-v1',created_at:new Date().toISOString(),passed_self_check_ids:progress.map(lesson=>lesson.id),lesson_evidence:progress.map(lesson=>({id:lesson.id,title:lesson.title,level:lesson.level,objectives:lesson.objectives,source_ids:lesson.source_ids})),notice:'Browser-local self-check progress; not verified mastery, accreditation or a credential.'});
      }else if(action==='toggle-overlay'){overlay=!overlay;render();}
      else if(action==='sign-pilot-registry')await signedDownload('workflow-pilot-status','helioforge-pilot-registry-signed.json',{schema:'helioforge-pilot-registry-v1',created_at:new Date().toISOString(),data_kind:'synthetic',pilots:state.data.pilots,notice:'Fictional workflow records; signature does not establish field evidence or signer identity.'});
      else if(action==='research-dossier')downloadText('helioforge-research-dossier.md',researchDossier(state),'text/markdown');
      else if(action==='investment-memo')downloadText('helioforge-investment-committee-screen.md',investmentMemo(state),'text/markdown');
      else if(action==='sign-council'){
        const c=state.data.council;
        await signedDownload('workflow-council-status','helioforge-council-determination.json',{schema:'helioforge-council-determination-v1',created_at:new Date().toISOString(),council:c,referenced_run:referencedRun(state),notice:c.mode==='local'?'Deterministic local checklist. No external agent execution is implied.':'Council mode and execution are copied from the current saved state; the envelope does not validate agent identity or authority.'});
      }
    }
    document.addEventListener('click',event=>{
      const target=event.target;
      if(!(target instanceof Element))return;
      const button=target.closest<HTMLButtonElement>('[data-workflow-action]');if(!button)return;
      const action=button.dataset.workflowAction;if(!action)return;
      event.preventDefault();
      void act(action).catch(error=>setStatus(action==='cosign-import'?'workflow-import-status':action==='sign-progress'?'workflow-learning-status':action==='sign-council'?'workflow-council-status':'workflow-pilot-status',error instanceof Error?error.message:'The workflow action failed.'));
    });
    document.addEventListener('change',event=>{
      const target=event.target;if(!(target instanceof HTMLInputElement||target instanceof HTMLSelectElement))return;
      if(target.matches('[data-workflow-sensor]')){selectedPilotStudy=target.value;render();}
      else if(target.matches('[data-workflow-council-filter]')){councilFilter=target.value;render();}
      else if(target.matches('[data-workflow-import]')){
        const input=target as HTMLInputElement;void(async()=>{
          try{
            const files=[...(input.files??[])];if(!files.length)return;
            if(files.length>20||files.some(file=>file.size>1_000_000))throw new Error('Choose at most 20 files, each no larger than 1 MB.');
            const values:unknown[]=[];
            for(const file of files)values.push(JSON.parse(await file.text()) as unknown);
            const envelope=await mergeEvidenceEnvelopes(values);
            importedEnvelope=envelope;
            const button=document.querySelector<HTMLButtonElement>('[data-workflow-action="cosign-import"]');if(button)button.disabled=false;
            const payload=document.getElementById('workflow-import-payload');if(payload)payload.textContent=JSON.stringify(envelope.payload,null,2);
            setStatus('workflow-import-status',`Verified ${envelope.signatures.length} unique cryptographic signer key(s) for one payload. All signer identities and authority remain unverified.`);
          }catch(error){importedEnvelope=null;const button=document.querySelector<HTMLButtonElement>('[data-workflow-action="cosign-import"]');if(button)button.disabled=true;const payload=document.getElementById('workflow-import-payload');if(payload)payload.textContent='No verified payload imported.';setStatus('workflow-import-status',error instanceof Error?error.message:'Evidence import failed.');}
          finally{input.value='';}
        })();
      }
    });
    document.addEventListener('input',event=>{
      const target=event.target;if(!(target instanceof HTMLInputElement))return;
      if(!target.matches('[data-workflow-council-round]'))return;
      councilRound=Number(target.value);
      const output=document.getElementById('workflow-round-value');if(output)output.textContent=String(councilRound);
      const transcript=document.getElementById('workflow-council-transcript');if(transcript)transcript.innerHTML=councilTranscriptHTML(councilFilter,councilRound);
    });
    let draggedPilot:string|null=null;
    document.addEventListener('dragstart',event=>{
      const card=(event.target as Element|null)?.closest<HTMLElement>('article[data-pilot-card]');if(!card||getState().page!=='pilots'||!getState().connected)return;
      draggedPilot=card.dataset.pilotCard??null;
      if(!draggedPilot)return;
      card.classList.add('dragging');
      if(event instanceof DragEvent&&event.dataTransfer){event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedPilot);}
    });
    document.addEventListener('dragover',event=>{
      const stage=(event.target as Element|null)?.closest<HTMLElement>('div[data-pilot-stage]');if(!stage||getState().page!=='pilots'||!getState().connected)return;
      event.preventDefault();stage.classList.add('drag-target');
      if(event instanceof DragEvent&&event.dataTransfer)event.dataTransfer.dropEffect='move';
    });
    document.addEventListener('dragleave',event=>{
      const stage=(event.target as Element|null)?.closest<HTMLElement>('div[data-pilot-stage]');if(stage&&!stage.contains(event.relatedTarget as Node|null))stage.classList.remove('drag-target');
    });
    document.addEventListener('dragend',event=>{
      (event.target as Element|null)?.closest('article[data-pilot-card]')?.classList.remove('dragging');
      document.querySelectorAll('[data-pilot-stage].drag-target').forEach(stage=>stage.classList.remove('drag-target'));draggedPilot=null;
    });
    document.addEventListener('drop',event=>{
      const stage=(event.target as Element|null)?.closest<HTMLElement>('div[data-pilot-stage]');if(!stage||getState().page!=='pilots'||!getState().connected)return;
      event.preventDefault();stage.classList.remove('drag-target');
      const id=(event instanceof DragEvent?event.dataTransfer?.getData('text/plain'):undefined)||draggedPilot;
      const targetStage=stage.dataset.pilotStage;
      if(!id||!targetStage||!['planned','instrumenting','running','validated'].includes(targetStage))return;
      const pilot=getState().data.pilots.find(item=>item.id===id);if(!pilot)return;
      if(pilot.status===targetStage){setStatus('workflow-pilot-status','The pilot is already in that stage. No update was made.');return;}
      const review=document.querySelector<HTMLButtonElement>(`article[data-pilot-card="${CSS.escape(id)}"] button[data-pilot]`);
      if(!review){setStatus('workflow-pilot-status','Open the pilot review form to record a stage change.');return;}
      review.click();
      const form=document.querySelector<HTMLFormElement>('#modal #pilot-form');
      const select=form?.querySelector<HTMLSelectElement>('select[name="status"]');
      const note=form?.querySelector<HTMLTextAreaElement>('textarea[name="evidence_note"]');
      if(!form||!select||!note){setStatus('workflow-pilot-status','The existing evidence form could not be opened.');return;}
      select.value=targetStage;select.dispatchEvent(new Event('change',{bubbles:true}));
      note.value='';note.focus();
      setStatus('workflow-pilot-status',`Requested stage: ${targetStage}. Add a new evidence note and submit the existing form to save; no change has been sent yet.`);
    });
    return {refresh};
  }
}
