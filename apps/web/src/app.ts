namespace HF {
  /** Single application controller. Numerical work remains on the typed Python API. */
  export function boot(): void {
    const root=document.getElementById('app');
    if(!root)throw new Error('Missing application root.');
    const media=window.matchMedia('(prefers-reduced-motion: reduce)');
    let savedMotion=false;
    try { savedMotion=localStorage.getItem('hf-motion-off')==='true'; } catch { /* Storage can be blocked. */ }
    const initial=location.hash.slice(1);
    const state: ViewState={hybrid:initialHybridState(),page:PAGES.some(p=>p.id===initial)?initial as Page:'hybrid',connected:false,busy:false,data:structuredClone(SNAPSHOT),marketFilter:'ALL',search:'',chartMode:'dispatch',forecastYears:20,runs:[],motionOff:media.matches||savedMotion};
    state.champion=initialChampionState(state.hybrid);
    const modelDrafts=new Map<string,Record<string,string>>();
    let champion:ChampionController;
    let hasConnected=false;
    let connectionEpoch=0, toastTimer=0, modalReturn:HTMLElement|null=null;
    let sceneCleanup:(()=>void)|undefined;
    function render(): void {
      sceneCleanup?.();
      root!.innerHTML=shell(state);
      document.documentElement.dataset.motion=state.motionOff?'off':'on';
      for(const form of document.querySelectorAll<HTMLFormElement>('form[data-model]')){
        const draft=modelDrafts.get(form.dataset.model!);
        if(draft){
          for(const field of form.querySelectorAll<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>('input[name],select[name],textarea[name]')){
            if(draft[field.name]!==undefined)field.value=draft[field.name]!;
          }
          const note=document.createElement('p');note.className='draft-note';note.setAttribute('role','status');
          note.textContent='Unsaved input edits. Displayed results still belong to the last completed calculation.';form.append(note);
        }
      }
      if(state.hybrid.draft)for(const field of document.querySelectorAll<HTMLInputElement|HTMLSelectElement>('#hybrid-config input[name],#hybrid-config select[name]')){
        if(state.hybrid.draft[field.name]!==undefined)field.value=state.hybrid.draft[field.name]!;
      }
      applyBusyState();
      const sidebar=document.getElementById('sidebar');if(sidebar)sidebar.inert=window.matchMedia('(max-width:800px)').matches;
      const canvas=document.getElementById('energy-scene') as HTMLCanvasElement|null;
      if(canvas)sceneCleanup=mountEnergyScene(canvas,systemById(state.hybrid.inputs.system_id),state.motionOff,id=>{state.hybrid.objectId=id;const el=document.getElementById('asset-inspector');if(el)el.innerHTML=assetInspector(state.hybrid);document.querySelectorAll<HTMLButtonElement>('[data-asset]').forEach(b=>{b.classList.toggle('selected',b.dataset.asset===id);b.setAttribute('aria-pressed',String(b.dataset.asset===id));});});
      document.title=`${PAGES.find(p=>p.id===state.page)!.title} · HelioForge`;
    }
    function applyBusyState():void {
      document.querySelectorAll<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>('form[data-model] input,form[data-model] select,form[data-model] textarea').forEach(e=>e.disabled=state.busy);
      document.querySelectorAll<HTMLInputElement|HTMLSelectElement>('#hybrid-config input,#hybrid-config select').forEach(e=>e.disabled=state.hybrid.busy);
      document.querySelectorAll<HTMLButtonElement>('[data-system],[data-scenario],[data-hybrid-action="reset"],[data-hybrid-action="import"],[data-hybrid-action="launch-lesson"]').forEach(e=>e.disabled=state.hybrid.busy);
    }
    function setMobileMenu(open:boolean):void {
      const sidebar=document.getElementById('sidebar'),main=document.querySelector<HTMLElement>('.app-main'),toggle=document.querySelector<HTMLElement>('[data-action="menu"]');
      const mobile=window.matchMedia('(max-width:800px)').matches;
      if(!sidebar||!main)return;
      sidebar.classList.toggle('mobile-open',open&&mobile);sidebar.inert=mobile&&!open;main.inert=mobile&&open;
      toggle?.setAttribute('aria-expanded',String(mobile&&open));document.getElementById('nav-backdrop')?.remove();
      if(open&&mobile){
        const shade=document.createElement('button');shade.id='nav-backdrop';shade.className='nav-backdrop';shade.setAttribute('aria-label','Close navigation');shade.onclick=()=>setMobileMenu(false);root!.append(shade);
        sidebar.querySelector<HTMLElement>('[aria-current="page"]')?.focus();
      }else if(mobile)toggle?.focus();
    }
    function rememberDraft(event:Event):void {
      const el=event.target as HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement;
      const form=el.closest<HTMLFormElement>('form[data-model]');
      // Passwords, external execution mode and consent are deliberately never retained.
      if(!form||!el.name||el.type==='password'||['admin_key','consent','mode'].includes(el.name)||state.busy)return;
      const model=form.dataset.model!,draft=modelDrafts.get(model)??{};draft[el.name]=el.value;modelDrafts.set(model,draft);
      if(!form.querySelector('.draft-note')){const note=document.createElement('p');note.className='draft-note';note.setAttribute('role','status');note.textContent='Unsaved input edits. Displayed results still belong to the last completed calculation.';form.append(note);}
    }
    document.addEventListener('input',rememberDraft);document.addEventListener('change',rememberDraft);
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!(document.getElementById('modal') as HTMLDialogElement|null)?.open)setMobileMenu(false);});
    window.matchMedia('(max-width:800px)').addEventListener('change',()=>setMobileMenu(false));
    function toast(message:string,error=false):void {
      const el=document.getElementById('toast'); if(!el)return;
      clearTimeout(toastTimer); el.textContent=message; el.className=`toast show ${error?'toast-error':''}`;
      toastTimer=window.setTimeout(()=>el.classList.remove('show'),6000);
    }
    async function api<T>(path:string,body?:unknown,method='POST',adminKey?:string):Promise<T> {
      if(location.protocol==='file:')throw new Error('Open the local Python application to run calculations. This file is a read-only snapshot.');
      const headers:Record<string,string>={}; if(body!==undefined)headers['Content-Type']='application/json';
      if(adminKey)headers['X-API-Key']=adminKey;
      let response:Response;
      try { response=await fetch(`/api/${path}`,{method:body===undefined?'GET':method,headers,body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(path.startsWith('council')?125000:30000)}); }
      catch { throw new Error(body===undefined?'The local API could not be reached. Start the Python app, then reconnect.':'The response was interrupted. The operation may have completed. Your inputs are retained. Check Analysis history before trying again.'); }
      let data:unknown;
      try { data=await response.json(); }
      catch { throw new Error(body===undefined?'The local API returned an unreadable response. Reconnect and try again.':'The API response could not be read. Check Analysis history before retrying; the operation may already be saved.'); }
      if(!response.ok){
        const detail=(data as {detail?:unknown}).detail;
        const message=typeof detail==='string'?detail:Array.isArray(detail)?detail.map((x:{msg?:string;loc?:unknown[]})=>`${x.loc?.slice(1).join('.')??'Input'}: ${x.msg??'Invalid input'}`).join('; '):`Request failed (${response.status}).`;
        throw new Error(message);
      }
      return data as T;
    }
    async function connect(market:MarketCode=state.data.market,announce=false):Promise<void> {
      const epoch=++connectionEpoch;
      if(location.protocol==='file:'){ if(announce)toast('Snapshot preview: run the Python server for new calculations.'); return; }
      try {
        const d=await api<Dashboard>(`overview?market=${encodeURIComponent(market)}`);
        if(epoch!==connectionEpoch)return;
        if(d.version!=='0.3.0'||d.data_kind!=='synthetic'||!Array.isArray(d.dispatch?.schedule))throw new Error('Unexpected dashboard response.');
        if(!hasConnected)state.data=d;
        else if(state.data.market!==market){state.data=d;modelDrafts.clear();}
        else state.data.pilots=d.pilots;
        hasConnected=true;state.connected=true;render();
        await champion.restore();
        if(announce)toast(`Connected. ${market} illustrative scenario loaded. Completed calculations retained when the market is unchanged.`);
      }catch(error){
        if(epoch!==connectionEpoch)return;
        state.connected=false;render(); if(announce)toast(error instanceof Error?error.message:'API unavailable.',true);
      }
    }
    function navigate(page:Page):void {
      state.page=page;if(location.hash!==`#${page}`)history.pushState(null,'',`#${page}`);render();window.scrollTo({top:0,behavior:'instant'});
      document.getElementById('main-content')?.focus({preventScroll:true});
    }
    function openModal(title:string,body:string):void {
      const m=document.getElementById('modal') as HTMLDialogElement;
      modalReturn=document.activeElement instanceof HTMLElement?document.activeElement:null;
      m.innerHTML=`<div class="modal-heading"><h2 id="modal-title">${escapeHTML(title)}</h2><button class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close',22)}</button></div>${body}`;
      m.addEventListener('close',()=>modalReturn?.focus(),{once:true});m.showModal();
    }
    function celebrate():void {
      if(state.motionOff)return;
      const c=document.getElementById('celebration');if(!c)return;
      c.innerHTML=`<div class="success-medal">${icon('trophy',36)}<span>Milestone complete</span></div>${Array.from({length:14},(_,i)=>`<i style="--angle:${i*360/14}deg;--distance:${90+i%3*25}px;--delay:${i%4*20}ms"></i>`).join('')}`;
      c.classList.add('active');setTimeout(()=>{c.classList.remove('active');c.innerHTML='';},1800);
    }
    const stringify=(data:unknown):string=>JSON.stringify(data,null,2);
    const evidence=():Record<string,unknown>=>({exported_at:new Date().toISOString(),data_kind:'synthetic',view:state.page,hybrid:{inputs:state.hybrid.inputs,result:hybridDirty(state.hybrid)?null:state.hybrid.result,result_is_current:!hybridDirty(state.hybrid),comparisons:state.hybrid.compare},learning:{passed_self_checks:state.hybrid.progress,notice:'Browser-local practice, not verified credentials'},assumptions:state.data.defaults,results:{drift:state.data.drift,dispatch:state.data.dispatch,finance:state.data.finance,pv:state.data.pv,forecast:state.data.forecast,acquisition:state.data.acquisition,reliability:state.data.reliability,sustainability:state.data.sustainability},council:state.data.council,pilots:state.data.pilots,sources:state.data.sources,market_registry:state.data.markets,notice:'Screening scenarios only. No live market feeds. No investment, legal, safety or plant-control approval.'});
    function councilMarkdown():string {
      const c=state.data.council;
      return `# HelioForge council review\n\nMode: ${c.mode} (${c.execution})\nMarket: ${c.market}\n\n## Brief\n${c.reviewed_brief}\n\n## Recommendation\n${c.decision.recommendation}\n\n${c.reviews.map(r=>`## ${r.agent}\n${r.summary}\n\nRisks:\n${r.risks.map(x=>`- ${x}`).join('\n')}\n\nRequired evidence:\n${r.required_evidence.map(x=>`- ${x}`).join('\n')}\n`).join('\n')}\n## Boundaries\n${c.warnings.join('\n')}\n`;
    }
    async function action(name:string):Promise<void> {
      if(name==='export-evidence')download('helioforge-evidence.json',stringify(evidence()));
      else if(name==='export-portfolio')download('helioforge-fictional-portfolio.csv',toCSV(filterProjects(state.data.portfolio,state.marketFilter,state.search).map(p=>({...p}))), 'text/csv');
      else if(name==='export-dispatch')download('helioforge-dispatch.csv',toCSV(state.data.dispatch.schedule.map(p=>({...p}))),'text/csv');
      else if(name==='export-pilots')download('helioforge-pilot-register.json',stringify(state.data.pilots));
      else if(name==='export-council')download('helioforge-council-review.md',councilMarkdown(),'text/markdown');
      else if(name==='export-checklist')download('helioforge-regulatory-review-checklist.md',`# Regulatory evidence checklist\n\nNo current rules have been approved in this demo.\n\n${state.data.markets.map(m=>`## ${m.name}\nSource: ${m.url}\nCustomer segment: ${m.segment}\nValue hypothesis: ${m.hypothesis}\n\n- [ ] Site meter and tariff evidence\n- [ ] Exact legal instrument and provision\n- [ ] Publication and effective dates\n- [ ] Geography, voltage and customer eligibility\n- [ ] Import/export charges, taxes and exemptions\n- [ ] Metering, aggregator and settlement rules\n- [ ] Stacking compatibility and availability obligations\n- [ ] Local currency and explicit FX basis\n- [ ] Independent reviewer, review date and expiry date\n`).join('\n')}`,'text/markdown');
      else if(name==='reconnect')await connect(state.data.market,true);
      else if(name==='menu')setMobileMenu(!document.getElementById('sidebar')?.classList.contains('mobile-open'));
      else if(name==='motion'){
        state.motionOff=!state.motionOff;try{localStorage.setItem('hf-motion-off',String(state.motionOff));}catch{/* Optional preference only. */}render();toast(state.motionOff?'Animations reduced.':'Animations enabled.');
      }else if(name==='close-modal')(document.getElementById('modal') as HTMLDialogElement).close();
      else if(name==='methodology')openModal('Visible assumptions. Verifiable work.',`<div class="modal-copy"><p>HelioForge is a local-first research and investment-screening application. All included sites, prices, portfolios and pilot records are synthetic.</p><h3>What the models do</h3><p>Storage: mixed-integer cost optimization with energy balance, state-of-charge limits and no simultaneous charging/discharging or importing/exporting. The no-storage comparator is optimized under the same constraints.</p><p>Finance: pre-tax nominal cash flows, a conservative augmentation-year debt-service screen and a level-payment debt-capacity estimate. PV: discounted lifecycle costs divided by discounted generation.</p><p>Forecasting: seeded, uncalibrated annual-price scenarios. Reliability: user-specified Weibull assumptions. Carbon: a screening inventory, not a certified life-cycle assessment.</p><h3>What this release does not claim</h3><p>No live regulatory monitoring, bankable price forecast, calibrated fault diagnosis, certified biodiversity result, production authentication or operational equipment control. The country registry provides official starting points, not approved rules.</p><p>The full repository includes methodology, limitations, tests, a multi-agent build prompt and a production-hardening roadmap.</p><button class="btn primary" data-action="export-evidence">${icon('download',16)} Download current evidence</button></div>`);
      else if(name==='history')await champion.history();
    }
    document.addEventListener('click',event=>{
      const el=(event.target as Element).closest<HTMLElement>('button,a');if(!el)return;
      if(el.dataset.nav){navigate(el.dataset.nav as Page);return;}
      if(el.dataset.action){void action(el.dataset.action).catch(e=>toast(e instanceof Error?e.message:'Action failed.',true));return;}
      if(el.dataset.chart){state.chartMode=el.dataset.chart as 'dispatch'|'prices';render();return;}
      if(el.dataset.horizon){state.forecastYears=Number(el.dataset.horizon);render();return;}
      if(el.dataset.run){void api<unknown>(`runs/${encodeURIComponent(el.dataset.run)}`).then(r=>download(`helioforge-run-${el.dataset.run}.json`,stringify(r))).catch(e=>toast(String(e),true));return;}
      if(el.dataset.project){const p=state.data.portfolio.find(x=>x.id===el.dataset.project);if(p)openModal(p.name,`<div class="modal-copy"><span class="tag muted">FICTIONAL PROJECT</span><p>${escapeHTML(p.id)} · ${escapeHTML(p.market)} · ${escapeHTML(p.technology)}</p><div class="result-stats"><div><span>PV capacity</span><strong>${fmt(p.pv_mwp)} MWp</strong></div><div><span>Storage energy</span><strong>${fmt(p.bess_mwh)} MWh</strong></div></div><p>Stage: ${escapeHTML(p.stage)}. Review progress: ${p.progress}%. Screening CAPEX: €${fmt(p.capex_meur,1)}m.</p><p>This is a demonstration record, not a real company asset. Open a modeling workspace to explore an independent scenario.</p><button class="btn primary" data-nav="${p.technology==='PV'?'pv':'storage'}">Open modeling workspace ${icon('arrow',16)}</button></div>`);return;}
      if(el.dataset.pilot){const p=state.data.pilots.find(x=>x.id===el.dataset.pilot);if(p)openModal(p.title,`<form id="pilot-form" data-pilot-id="${escapeHTML(p.id)}" class="modal-copy"><p>${escapeHTML(p.instrument)}</p><p><strong>Hypothesis:</strong> ${escapeHTML(p.target)}</p><label class="field"><span>Evidence gate</span><select name="status">${['planned','instrumenting','running','validated'].map(x=>`<option ${x===p.status?'selected':''}>${x}</option>`).join('')}</select></label><label class="field"><span>Evidence note (required)</span><textarea name="evidence_note" rows="5" minlength="8" maxlength="1200" required>${escapeHTML(p.evidence_note)}</textarea></label><button class="btn primary" type="submit" ${!state.connected?'disabled':''}>${icon('check',16)} Save evidence update</button>${!state.connected?'<p>Snapshot mode is read-only. Start the API to persist changes.</p>':''}</form>`);}
    });
    document.addEventListener('input',event=>{
      const el=event.target as HTMLInputElement;
      if(el.id==='project-search'){state.search=el.value;updateProjectTable(state);}
    });
    document.addEventListener('change',event=>{
      const el=event.target as HTMLInputElement;
      if(el.id==='portfolio-market'){state.marketFilter=el.value;updateProjectTable(state);}
      if(el.id==='context-market'){
        if(!state.connected){el.value=state.data.market;toast('Connect the API to load another market scenario. Snapshot remains France.');return;}
        if(state.busy){el.value=state.data.market;return;}
        void connect(el.value as MarketCode,true);
      }
      if(el.id==='council-mode'){const box=document.getElementById('external-consent');if(box)box.hidden=el.value!=='openai';}
    });
    document.addEventListener('submit',event=>{
      const form=event.target as HTMLFormElement;event.preventDefault();
      if(form.id==='pilot-form'){
        const fd=new FormData(form),id=form.dataset.pilotId!;
        const button=form.querySelector('button[type=submit]') as HTMLButtonElement;button.disabled=true;
        void api<Pilot>(`pilots/${encodeURIComponent(id)}`,{status:fd.get('status'),evidence_note:fd.get('evidence_note')},'PATCH').then(p=>{
          state.data.pilots=state.data.pilots.map(x=>x.id===p.id?p:x);render();toast('Pilot evidence updated and recorded.');
        }).catch(e=>{button.disabled=false;toast(e instanceof Error?e.message:'Update failed.',true);});return;
      }
      if(!form.dataset.model||!state.connected||state.busy)return;
      void runModel(form);
    });
    async function runModel(form:HTMLFormElement):Promise<void> {
      const model=form.dataset.model!,fd=new FormData(form),n=(name:string):number=>finiteInput(fd.get(name),name);
      let inputs:Inputs={},path='',adminKey:string|undefined;
      try{
        if(model==='storage'){
          inputs={...state.data.defaults.storage,market:state.data.market,capacity_kwh:n('capacity_mwh')*1000,power_kw:n('power_mw')*1000,round_trip_efficiency:n('efficiency_pct')/100,wear_eur_per_kwh:n('wear'),min_soc_fraction:n('soc_min')/100,max_soc_fraction:n('soc_max')/100,peak_charge_eur_per_kw_period:n('peak_charge'),grid_import_limit_kw:n('grid_limit')*1000};path='storage/optimize';
        }else if(model==='pv'){
          inputs={...state.data.defaults.pv,capacity_kwp:n('capacity_mwp')*1000,specific_yield_kwh_kwp:n('yield'),capex_eur_kwp:n('capex'),opex_eur_kwp_year:n('opex'),discount_rate:n('discount')/100,capture_price_eur_mwh:n('capture'),curtailment_fraction:n('curtailment')/100,ground_coverage_ratio:n('gcr')/100};path='pv/evaluate';
        }else if(model==='forecast'){
          inputs={...state.data.defaults.forecast,market:state.data.market,base_price_eur_mwh:n('base'),long_run_price_eur_mwh:n('target'),annual_shock_eur_mwh:n('shock'),mean_reversion:n('reversion'),trend_eur_mwh_year:n('trend'),seed:n('seed')};path='forecast/simulate';
        }else if(model==='finance'){
          inputs={...state.data.defaults.finance,capex_eur:n('capex')*1e6,annual_gross_margin_eur:n('margin')*1000,annual_opex_eur:n('opex')*1000,discount_rate:n('discount')/100,debt_fraction:n('debt')/100,debt_interest_rate:n('interest')/100,merchant_margin_factor:n('merchant')/100,contracted_fraction:n('contracted')/100,augmentation_cost_eur:n('augmentation')*1000,augmentation_year:n('aug_year')};path='finance/evaluate';
        }else if(model==='acquisition'){
          inputs={...state.data.defaults.acquisition,enterprise_value_eur:n('ev')*1e6,annual_ebitda_eur:n('ebitda')*1e6,net_debt_eur:n('net_debt')*1e6,annual_maintenance_capex_eur:n('maintenance')*1000};path='acquisitions/screen';
        }else if(model==='reliability'){
          inputs={...state.data.defaults.reliability,shape:n('shape'),scale_hours:n('scale'),age_hours:n('age'),horizon_hours:n('horizon')};path='research/reliability';
        }else if(model==='sustainability'){
          inputs={...state.data.defaults.sustainability,annual_generation_kwh:n('generation')*1e6,embodied_kgco2e:n('embodied')*1000,counterfactual_kgco2e_kwh:n('counterfactual')/1000,annual_operational_kgco2e:n('operational')*1000};path='research/carbon';
        }else if(model==='council'){
          inputs={hybrid_run_id:String(fd.get('hybrid_run_id')??'')||null,market:state.data.market,brief:String(fd.get('brief')??''),mode:String(fd.get('mode')??'local'),consent_to_external_processing:fd.get('consent')==='on'};path='council/review';adminKey=String(fd.get('admin_key')??'')||undefined;
        }else throw new Error('Unknown model.');
        state.busy=true;applyBusyState();
        // Keep entered values and focus while pending; no whole-form rerender.
        document.querySelectorAll<HTMLButtonElement>('form[data-model] button[type=submit]').forEach(b=>b.disabled=true);
        const submitButton=form.querySelector<HTMLButtonElement>('button[type=submit]');
        if(submitButton)submitButton.innerHTML=`${icon('clock',16)} ${model==='council'?'Reviewing…':'Calculating…'}`;
        const result=await api<Dispatch|Finance|PV|Forecast|Acquisition|Reliability|Sustainability|Council>(path,inputs,'POST',adminKey);
        // Inputs and results are committed together only after a successful server response.
        if(model==='storage'){state.data.dispatch=result as Dispatch;state.data.defaults.storage=inputs;}
        else if(model==='pv'){state.data.pv=result as PV;state.data.defaults.pv=inputs;}
        else if(model==='forecast'){state.data.forecast=result as Forecast;state.data.defaults.forecast=inputs;}
        else if(model==='finance'){state.data.finance=result as Finance;state.data.defaults.finance=inputs;}
        else if(model==='acquisition'){state.data.acquisition=result as Acquisition;state.data.defaults.acquisition=inputs;}
        else if(model==='reliability'){state.data.reliability=result as Reliability;state.data.defaults.reliability=inputs;}
        else if(model==='sustainability'){state.data.sustainability=result as Sustainability;state.data.defaults.sustainability=inputs;}
        else state.data.council=result as Council;
        state.busy=false;modelDrafts.delete(model);render();toast(`${model==='council'?'Review':'Calculation'} complete. Inputs and result saved to the local audit store.`);if(model==='storage')celebrate();
      }catch(error){
        state.busy=false;applyBusyState();
        // Preserve the user's invalid inputs so they can correct them.
        document.querySelectorAll<HTMLButtonElement>('form[data-model] button[type=submit]').forEach(b=>b.disabled=!state.connected);
        const currentForm=document.querySelector<HTMLFormElement>(`form[data-model="${model}"]`);
        const b=currentForm?.querySelector<HTMLButtonElement>('button[type=submit]');if(b)b.innerHTML=`${icon('play',16)} Try again`;
        toast(error instanceof Error?error.message:'The model could not be evaluated.',true);
      }
    }
    function syncNavigation():void {const p=location.hash.slice(1);if(PAGES.some(x=>x.id===p)&&state.page!==p){state.page=p as Page;render();document.getElementById('main-content')?.focus({preventScroll:true});}}
    window.addEventListener('hashchange',syncNavigation);window.addEventListener('popstate',syncNavigation);
    media.addEventListener('change',()=>{if(media.matches){state.motionOff=true;render();}});
    champion=installChampionController(state,{render,toast,navigate,api,celebrate,openModal});
    installHybridController(state,{render,toast,navigate,api,celebrate,openModal,persist:champion.persist});
    render();void connect();
  }
  if(typeof document!=='undefined'){
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  }
}
