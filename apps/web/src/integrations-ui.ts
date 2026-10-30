namespace HF {
  const evidenceRequirements:Record<Page,string[]>={
    overview:['Portfolio coordinates, metered generation and marginal emissions','Licensed weather and price feeds; reviewed asset thresholds'],
    hybrid:['As-built impedances and controller parameters','Independent EMT, protection and grid-code validation'],
    lessons:['Instructor-reviewed assessments and learner identity','Institutional approval for externally recognized certificates'],
    compare:['Representative weather/outage histories and failure rates','Cell abuse-test calibration and an independent safety review'],
    storage:['8760 interval load/PV, tariff and warranty data','Cell aging observations, reserve qualification and grid connection limits'],
    pv:['Surveyed terrain/obstacles, site irradiance and legal parcel boundaries','Crop calibration, approved setbacks and supplier prices'],
    research:['Calibrated sensor baseline and held-out failure observations','Original EPDs, verifier credentials and validated grid models'],
    markets:['ENTSO-E access, exact bidding zones and dated contracts','Current legal instruments, eligibility and accountable local review'],
    forecast:['Licensed chronological power/gas/carbon history','Out-of-sample calibration review and forecast-use approval'],
    investment:['Executed contracts, tax jurisdiction and lender covenants','Accountant/legal review of tax, DSRA and distribution assumptions'],
    pilots:['Surveyed reference and as-built point clouds','Device/register allow-list, sensor calibration and commissioned safety alarms'],
    council:['Explicit provider model, server credentials and processing consent','Trusted signer identity, document authenticity and human determination']
  };
  const escI=escapeHTML;
  export function evidenceReadiness(page:Page):string[]{return [...evidenceRequirements[page]];}
  export function importedArray(result:Record<string,unknown>,column:string):number[]{
    const rows=result.rows;
    if(!Array.isArray(rows)||!rows.length)throw Error('No imported rows are available.');
    const values=rows.map(row=>(row as Record<string,unknown>)[column]);
    if(!values.every((value):value is number=>typeof value==='number'&&Number.isFinite(value)))throw Error('The selected column has missing or non-numeric observations.');
    return values;
  }
  function geographicEvidenceMap(result:Record<string,unknown>):string{
    const rows=Array.isArray(result.rows)?result.rows as {asset:string;longitude:number;latitude:number}[]:[];
    if(!rows.length)return '';
    return `<figure class="evidence-geography"><svg viewBox="0 0 720 360" role="img" aria-label="User-supplied WGS84 assets on a longitude-latitude grid"><path d="M0 180H720M360 0V360" stroke="var(--color-rule-2)"/>${rows.map(r=>`<g><circle cx="${(r.longitude+180)*2}" cy="${(90-r.latitude)*2}" r="5" fill="var(--color-accent)"><title>${escI(r.asset)} (${r.latitude}, ${r.longitude})</title></circle><text x="${(r.longitude+180)*2+7}" y="${(90-r.latitude)*2}" fill="var(--color-ink)" font-size="10">${escI(r.asset)}</text></g>`).join('')}</svg><figcaption>Supplied geographic points · equirectangular WGS84 grid, not a cadastral survey. Exact coordinates appear in the table.</figcaption></figure>`;
  }
  export function createIntegrationController(getState:()=>ViewState):{refresh:()=>void}{
    let result:Record<string,unknown>|null=null,error='',busy=false,status:Record<string,unknown>|null=null,checking=false,round=0;
    const field=(name:string,label:string,value:string,type='text')=>`<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${escI(value)}" required></label>`;
    const submit=(label:string)=>`<button class="btn primary small" type="submit" ${!getState().connected||busy?'disabled':''}>${label}</button>`;
    const consent='<label class="check-row"><input type="checkbox" name="consent" required> Send this request to the named provider</label>';
    const form=(op:string,body:string)=>`<form data-integration="${op}">${body}</form>`;
    function renderResult():void {
      const host=document.getElementById('integration-result');if(!host)return;
      host.innerHTML=error?`<p class="notice warn" role="alert">${escI(error)}</p>`:busy?'<p role="status">Processing evidence…</p>':result?`<p class="notice">${escI(result.data_kind)} · ${escI(result.source??result.filename??result.device??'Local import')} · authenticity: ${escI(result.authenticity??'unverified')}</p><p>${escI(result.notice??'Inspect the source and units before using these observations.')}</p><p class="mono">Run: ${escI(result.run_id)}<br>SHA-256: ${escI(result.sha256)}</p>${result.geojson?geographicEvidenceMap(result):''}${Array.isArray(result.rows)?studyTable(result.rows as Record<string,unknown>[],20):Array.isArray(result.readings)?studyTable(result.readings as Record<string,unknown>[],20):typeof result.text==='string'?`<details open><summary>Extracted text · review against original</summary><pre>${escI(result.text)}</pre></details>`:''}<div class="study-actions"><button type="button" data-integration-export="json" class="btn secondary small">Export complete evidence JSON</button>${Array.isArray(result.rows)?'<button type="button" data-integration-export="csv" class="btn secondary small">Export all rows CSV</button>':''}${getState().page==='council'?'<button type="button" data-integration-attach class="btn secondary small">Attach run to council review</button>':''}</div>${Array.isArray(result.rows)?'<details><summary>Use numeric observations in the current study</summary><p>Copy a column into a JSON array field. Confirm matching units, cadence and length; this invalidates the previous result.</p><label class="field"><span>Source column</span><input id="integration-column" value="value"></label><label class="field"><span>Study JSON field name</span><input id="integration-target" placeholder="hourly_load_kw"></label><button type="button" class="btn secondary small" data-integration-apply>Apply values to study inputs</button></details>':''}`:'<p class="notice">No source has been imported or fetched in this session. Included model examples remain synthetic.</p>';
    }
    function refresh():void {
      const state=getState(),host=document.getElementById('page-content');document.getElementById('integration-panel')?.remove();if(!host)return;
      const series=form('series',`<p>Upload chronological UTF-8 CSV with the columns <code>timestamp,value</code>. Timestamps need Z or an offset; no missing values are invented.</p><label class="field"><span>CSV file</span><input type="file" name="csv" accept=".csv,text/csv" required></label><label class="field"><span>Unit</span><select name="unit">${['kW','kWh','EUR/MWh','EUR/kWh','gCO2e/kWh','degC','ppm','m/s','W/m2'].map(x=>`<option>${x}</option>`).join('')}</select></label>${field('source','Source / provenance','User supplied measurements')}${submit('Validate and save series')}`);
      const documents=form('document',`<p>Local extraction: text/CSV/JSON/XML, PDF text via Poppler, image OCR via Tesseract. Maximum 700 KB; PDFs use the first 20 pages. Matches need human review.</p><label class="field"><span>Source document</span><input type="file" name="document" accept=".txt,.csv,.json,.md,.xml,.pdf,.png,.jpg,.jpeg,.tif,.tiff" required></label><label class="field"><span>Purpose</span><select name="purpose">${['diagram','tariff','warranty','epd','regulation','other'].map(x=>`<option>${x}</option>`).join('')}</select></label>${field('source_url','Original source URL (metadata only)','https://example.org/source','url')}${submit('Extract and seal evidence')}`);
      const feed=state.page==='overview'||state.page==='pv'?`<details><summary>Fetch weather forecast for real coordinates</summary>${form('weather',`${field('latitude','Latitude','48.8566','number')}${field('longitude','Longitude','2.3522','number')}${field('days','Forecast days (1–7)','2','number')}<p>Open-Meteo numerical weather prediction. Verify commercial licence; this is not measured site irradiance.</p>${consent}${submit('Fetch weather')}`)}</details>`:state.page==='markets'?`<details><summary>Fetch ENTSO-E day-ahead prices</summary>${form('market',`<label class="field"><span>Bidding zone</span><select name="market">${['FR','DE','ES','IT','NL','GB'].map(x=>`<option>${x}</option>`).join('')}</select></label>${field('date','UTC date',new Date().toISOString().slice(0,10),'date')}<p>Uses the server ENTSOE_API_TOKEN. Italy = North zone; availability and EUR currency are checked.</p>${consent}${submit('Fetch market prices')}`)}</details>`:'';
      const regulatory=state.page==='markets'?`<details><summary>Refresh official regulatory publications</summary>${form('regulatory',`<label class="field"><span>Regulator</span><select name="market">${['FR','DE','ES','IT','NL','GB'].map(x=>`<option>${x}</option>`).join('')}</select></label><p>Uses the operator-configured official RSS/Atom feed. Extracted publication dates and text date candidates need legal review before they become an effective-date timeline.</p>${consent}${submit('Fetch official publications')}`)}</details>`:'';
      const geography=state.page==='overview'?`<details><summary>Import actual portfolio coordinates</summary>${form('geography',`<label class="field"><span>GeoJSON Point FeatureCollection</span><input type="file" name="geography" accept=".geojson,.json" required></label><p>WGS84 longitude/latitude. No coordinates are invented for fictional portfolio rows.</p>${submit('Validate geographic assets')}`)}</details>`:'';
      const telemetry=state.page==='pilots'?`<details><summary>Read-only telemetry and device access</summary>${form('telemetry',`<label class="field"><span>Timestamped readings JSON</span><textarea name="telemetry" rows="8" required spellcheck="false">${escI(JSON.stringify({source:'Replace with calibrated instrument',timestamp:new Date().toISOString(),readings:[{channel:'temperature',value:25,unit:'degC',warning:50,critical:80}],stale_after_seconds:60},null,2))}</textarea></label><p>The shown record is an editable example. Thresholds are diagnostic, not commissioned safety alarms.</p>${submit('Inspect supplied telemetry')}`)}${form('modbus',`${field('device','Configured device name','pilot')}${field('admin_key','Local server access credential','','password')}<p>Only server-allowlisted function 03/04 register reads. Addresses, scaling and host are controlled by the operator.</p>${submit('Read configured device')}`)}</details>`:'';
      host.insertAdjacentHTML('beforeend',`<section id="integration-panel" class="panel integration-panel"><div class="section-heading"><div><span class="eyebrow">SOURCE EVIDENCE / READINESS</span><h2>Connect this view to reviewed evidence</h2></div><span class="tag muted">EXTERNAL REQUIREMENTS</span></div><ul>${evidenceReadiness(state.page).map(x=>`<li>${escI(x)}</li>`).join('')}</ul><p>Implemented calculations can be run locally. These real-world prerequisites remain unverified until evidence is supplied and reviewed.</p><details><summary>Import measured data</summary>${series}</details><details><summary>Extract source documents and EPD evidence</summary>${documents}</details>${feed}${regulatory}${geography}${telemetry}<details><summary>Connector configuration status</summary><pre id="integration-config-status">${escI(status?JSON.stringify(status,null,2):state.connected?'Checking local service…':'Static preview. Start the local Python API to import evidence or use connectors.')}</pre></details><div id="integration-result" aria-live="polite"></div></section>`);
      host.querySelectorAll<HTMLInputElement>('#integration-panel input[type="number"]').forEach(input=>input.step='any');
      renderResult();
      if(state.page==='council')installCouncil();
      if(state.connected&&!status&&!checking){checking=true;void fetch('/api/connectors/status').then(async r=>{if(!r.ok)throw Error();status=await r.json();}).catch(()=>{status={notice:'Connector status unavailable.'};}).finally(()=>{checking=false;const el=document.getElementById('integration-config-status');if(el)el.textContent=JSON.stringify(status,null,2);});}
    }
    function installCouncil():void {
      const target=document.querySelector<HTMLFormElement>('form[data-model="council"]');
      if(target&&!target.querySelector('[name="cross_examination_rounds"]'))target.insertAdjacentHTML('beforeend',`<label class="field"><span>Cross-examination rounds (external mode)</span><select name="cross_examination_rounds"><option value="1">1 round · 17 Runner.run invocations</option><option value="2">2 rounds · 25 Runner.run invocations</option></select></label><label class="field"><span>Saved evidence run IDs (comma separated, at most six)</span><input name="evidence_run_ids" placeholder="Import a source below, then attach its run"></label>`);
      updateCouncilPreflight();
      document.getElementById('integration-council-rounds')?.remove();
      const council=getState().data.council as Council&{rounds?:{round:number;phase:string;reviews:Review[];consensus:Record<string,unknown>}[]};
      const rounds=council.mode==='openai'&&council.protocol_metadata?.external_execution_status==='completed'?council.rounds:undefined;
      if(!rounds?.length)return;
      round=clamp(round,0,rounds.length-1);const current=rounds[round]!;
      document.getElementById('integration-panel')?.insertAdjacentHTML('beforeend',`<section id="integration-council-rounds"><h3>Recorded external cross-examination</h3><label class="field"><span>Review round ${round}</span><input type="range" data-integration-round min="0" max="${rounds.length-1}" value="${round}" aria-label="External council replay round"></label><p>${escI(current.phase)} · vote entropy ${escI(current.consensus.entropy_bits)} bits</p>${current.reviews.map(r=>`<article><h4>${escI(r.agent)}</h4><p>${escI(r.summary)}</p><ul>${r.risks.map(x=>`<li>${escI(x)}</li>`).join('')}</ul>${'response_to_challenge' in r?`<p>${escI(r.response_to_challenge)}</p>`:''}</article>`).join('')}</section>`);
    }
    function updateCouncilPreflight():void {
      const mode=(document.getElementById('council-mode') as HTMLSelectElement|null)?.value??'local';
      const rounds=Number(document.querySelector<HTMLSelectElement>('[name="cross_examination_rounds"]')?.value??1);
      const summary=document.getElementById('council-preflight');if(!summary)return;
      if(mode==='local'){
        summary.textContent='helioforge-council/v1 · Local deterministic checklist · 0 external Runner.run invocations · no brief or evidence is sent to a provider and no provider charge applies.';
        return;
      }
      const invocations=8*(1+rounds)+1;
      summary.textContent=`helioforge-council/v1 · OpenAI external mode plans ${invocations} Agents SDK Runner.run invocations (8 specialists, ${rounds} cross-examination round${rounds===1?'':'s'}, 1 critic), with a 300-second workflow timeout. Each invocation can use up to 2 turns, so this count does not predict provider requests, tokens, or cost. After explicit consent, the brief, calculated evidence, and selected saved evidence/imports are sent externally; provider usage may be billed, cost is not estimated, and the application enforces no monetary budget. Cancellation is best effort; provider work already accepted may continue and charges may remain after failure.`;
    }
    async function request(op:string,inputs:unknown,key?:string):Promise<void>{
      busy=true;error='';result=null;renderResult();
      try{
        const response=await fetch(`/api/${['series','document','telemetry','geography'].includes(op)?'evidence':'connectors'}/${op}`,{method:'POST',headers:{'Content-Type':'application/json',...(key?{'X-API-Key':key}:{})},body:JSON.stringify(inputs),signal:AbortSignal.timeout(40000)});
        const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Input rejected. Check values, size and format.');result=body;
      }catch(e){error=e instanceof Error?e.message:'Evidence operation failed.';}finally{busy=false;renderResult();}
    }
    document.addEventListener('submit',event=>{
      const target=event.target;if(!(target instanceof HTMLFormElement)||!target.dataset.integration)return;event.preventDefault();if(busy||!getState().connected)return;
      const op=target.dataset.integration,fd=new FormData(target);
      void(async()=>{try{
        if(op==='series'){const file=fd.get('csv') as File;if(!file?.size||file.size>700000)throw Error('Choose a CSV file up to 700 KB.');await request(op,{text:await file.text(),unit:fd.get('unit'),source:fd.get('source')});}
        else if(op==='document'){const file=fd.get('document') as File;if(!file?.size||file.size>700000)throw Error('Choose a source file up to 700 KB.');let raw='';for(const byte of new Uint8Array(await file.arrayBuffer()))raw+=String.fromCharCode(byte);await request(op,{filename:file.name,content_base64:btoa(raw),source_url:fd.get('source_url'),purpose:fd.get('purpose')});}
        else if(op==='geography'){const file=fd.get('geography') as File;if(!file?.size||file.size>700000)throw Error('Choose GeoJSON up to 700 KB.');await request(op,{geojson:JSON.parse(await file.text())});}
        else if(op==='telemetry')await request(op,JSON.parse(String(fd.get('telemetry'))));
        else if(op==='weather')await request(op,{latitude:finiteInput(fd.get('latitude'),'Latitude'),longitude:finiteInput(fd.get('longitude'),'Longitude'),days:finiteInput(fd.get('days'),'Days'),consent:fd.get('consent')==='on'});
        else if(op==='regulatory')await request(op,{market:fd.get('market'),consent:fd.get('consent')==='on'});
        else if(op==='market')await request(op,{market:fd.get('market'),date:fd.get('date'),consent:fd.get('consent')==='on'});
        else if(op==='modbus')await request(op,{device:fd.get('device')},String(fd.get('admin_key')??''));
      }catch(e){error=e instanceof Error?e.message:'Invalid import.';renderResult();}})();
    });
    document.addEventListener('click',event=>{
      const button=(event.target as Element).closest<HTMLElement>('button');if(!button?.closest('#integration-panel')||!result)return;
      if(button.dataset.integrationExport==='json')download(result.geojson?'helioforge-portfolio.geojson':'helioforge-source-evidence.json',JSON.stringify(result.geojson??result,null,2));
      if(button.dataset.integrationExport==='csv'&&Array.isArray(result.rows))download('helioforge-source-rows.csv',toCSV(result.rows as Record<string,unknown>[]),'text/csv');
      if(button.hasAttribute('data-integration-attach')){const input=document.querySelector<HTMLInputElement>('[name="evidence_run_ids"]');if(input){const ids=input.value.split(',').map(x=>x.trim()).filter(Boolean);if(!ids.includes(String(result.run_id)))ids.push(String(result.run_id));input.value=ids.slice(0,6).join(', ');input.dispatchEvent(new Event('input',{bubbles:true}));input.focus();}}
      if(button.hasAttribute('data-integration-apply'))try{
        const column=(document.getElementById('integration-column') as HTMLInputElement).value;
        const name=(document.getElementById('integration-target') as HTMLInputElement).value;
        const input=document.querySelector<HTMLTextAreaElement>(`#study-form textarea[name="${CSS.escape(name)}"]`);if(!input)throw Error('Choose a JSON array field in the currently selected study.');
        input.value=JSON.stringify(importedArray(result,column));input.dispatchEvent(new Event('input',{bubbles:true}));input.closest('details')?.setAttribute('open','');input.focus();
      }catch(e){error=e instanceof Error?e.message:'Could not apply values.';renderResult();}
    });
    document.addEventListener('input',event=>{const el=event.target;if(el instanceof HTMLInputElement&&el.hasAttribute('data-integration-round')){round=Number(el.value);installCouncil();}});
    document.addEventListener('change',event=>{const el=event.target;if(el instanceof HTMLSelectElement&&(el.id==='council-mode'||el.name==='cross_examination_rounds'))updateCouncilPreflight();});
    return {refresh};
  }
}
