namespace HF {
  const esc=escapeHTML;
  const textValue=(v:unknown):string=>typeof v==='number'?fmt(v,3):v==null?'—':typeof v==='object'?JSON.stringify(v):String(v);
  /** Keep full provenance once in a CSV; repeat its digest on every observation. */
  export function studyExportRows(r:StudyResult,rows:Record<string,unknown>[]):Record<string,unknown>[] {
    const provenance={schema:'helioforge.study-export.v1',study:r.study,model_version:r.model_version,
      data_kind:r.data_kind,inputs:r.inputs,provenance:r.provenance,equations:r.equations,limitations:r.limitations,warnings:r.warnings,
      sources:r.sources,evidence_sha256:r.evidence_sha256,
      units:{metrics:r.metrics.map(m=>({label:m.label,unit:m.unit})),series:r.series.map(s=>({name:s.name,x_label:s.x_label,y_unit:s.y_unit}))},
      integrity_scope:'Evidence digest identifies the original result JSON, not this CSV encoding; no scientific or human approval.'};
    return (rows.length?rows:[{}]).map((row,i)=>({...row,hf_record_kind:rows.length?'observation':'metadata_only',
      hf_study:r.study,hf_model_version:r.model_version,hf_data_kind:r.data_kind,hf_evidence_sha256:r.evidence_sha256,
      hf_provenance_json:i===0?JSON.stringify(provenance):''}));
  }
  export function studyChart(s:StudyResult['series'][number],slice=0):string {
    const values=s.y.filter((v):v is number=>typeof v==='number'&&Number.isFinite(v));
    if(!values.length)return '<p class="notice">No finite observations in this series.</p>';
    const lo=Math.min(...values),hi=Math.max(...values),span=hi-lo||1;
    const x=(i:number)=>50+i*600/Math.max(1,s.y.length-1),y=(v:number)=>210-(v-lo)*160/span;
    let path='',open=false;
    s.y.forEach((v,i)=>{if(v===null||!Number.isFinite(v)){open=false;return;}path+=`${open?'L':'M'}${x(i).toFixed(2)},${y(v).toFixed(2)} `;open=true;});
    const j=clamp(Math.floor(slice),0,Math.max(0,s.y.length-1)),v=s.y[j];
    return `<div class="study-chart"><svg viewBox="0 0 700 260" role="img" aria-label="${esc(s.name)}; ${esc(s.y_unit)}. Missing observations are gaps."><path d="M50 40V210H650" fill="none" stroke="var(--color-rule-2)"/><path d="${path}" fill="none" stroke="var(--color-accent)" stroke-width="2.4"/><path d="${path}" fill="none" stroke="var(--color-accent)" stroke-width="8" opacity=".08" transform="translate(0 6)"/><path d="M${x(j)} 40V210" stroke="var(--color-accent)" stroke-dasharray="4 4"/>${v!=null&&Number.isFinite(v)?`<circle cx="${x(j)}" cy="${y(v)}" r="5" fill="var(--color-accent)"/>`:''}<g fill="var(--color-ink)" font-size="11"><text x="8" y="45">${esc(fmt(hi,2))}</text><text x="8" y="212">${esc(fmt(lo,2))}</text><text x="50" y="240">${esc(s.x[0])}</text><text x="650" y="240" text-anchor="end">${esc(s.x[s.x.length-1])}</text></g></svg><p class="study-slice"><strong>${esc(s.x_label)} ${esc(s.x[j])}</strong><span>${v==null?'Missing':esc(fmt(v,3))} ${esc(s.y_unit)}</span></p></div>`;
  }
  export function studyTable(rows:Record<string,unknown>[],limit=100):string {
    if(!rows.length)return '<p class="notice">No tabular observations returned.</p>';
    const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];
    return `<div class="table-scroll"><table><thead><tr>${keys.map(k=>`<th>${esc(k.replaceAll('_',' '))}</th>`).join('')}</tr></thead><tbody>${rows.slice(0,limit).map(row=>`<tr>${keys.map(k=>`<td>${esc(textValue(row[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${rows.length>limit?`<p class="form-note">Showing ${limit} of ${rows.length} records. CSV and JSON contain all records.</p>`:''}`;
  }
  function studySchematic(def:StudyDefinition):string {
    const peers=STUDY_BUNDLE.catalogue.filter(s=>s.page===def.page),icons:Record<string,string>={overview:'globe',hybrid:'bolt',lessons:'document',compare:'activity',storage:'battery',pv:'sun',research:'atom',markets:'globe',forecast:'chart',investment:'briefcase',pilots:'layers',council:'sparkles'};
    return `<nav class="study-schematic schematic-${esc(def.page)}" aria-label="${esc(def.page)} study navigation"><div class="study-orbit" aria-hidden="true"><i></i><i></i><i></i><span>${icon(icons[def.page]??'atom',40)}</span></div><div class="study-nodes">${peers.map((s,i)=>`<button type="button" data-study-select="${esc(s.id)}" aria-pressed="${s.id===def.id}"><span>0${i+1}</span><strong>${esc(s.title)}</strong></button>`).join('')}</div></nav>`;
  }
  export function studyResultView(def:StudyDefinition,r:StudyResult,slice=0,seriesIndex=0):string {
    const series=r.series??[],si=clamp(seriesIndex,0,Math.max(0,series.length-1)),selected=series[si];
    return `<div class="study-results">${resultProvenanceView(r)}<div class="result-stats">${r.metrics.map(m=>`<div><span>${esc(m.label)}</span><strong>${esc(textValue(m.value))} <small>${esc(m.unit)}</small></strong></div>`).join('')}</div>${selected?`<label class="field"><span>Inspect a result series</span><select data-study-series>${series.map((s,i)=>`<option value="${i}" ${i===si?'selected':''}>${esc(s.name)} · ${esc(s.y_unit)}</option>`).join('')}</select></label><div id="study-chart">${studyChart(selected,slice)}</div><label class="field"><span>Scrub ${esc(selected.x_label)} · ${selected.x.length} observations</span><input data-study-slice type="range" min="0" max="${Math.max(0,selected.x.length-1)}" step="1" value="${clamp(slice,0,Math.max(0,selected.x.length-1))}" aria-label="Result observation" aria-controls="study-chart"></label>`:''}<details class="method-details"><summary>Result records and accessible data table</summary>${studyTable(r.table??[])}</details><details class="method-details"><summary>Equations, sources and model boundaries</summary><div>${(def.equations??[]).map(e=>`<p class="formula"><code>${esc(e)}</code></p>`).join('')}${[...(def.limitations??[]),...(r.warnings??[])].map(e=>`<p>${esc(e)}</p>`).join('')}<ul>${(def.sources??[]).map(s=>`<li><a href="${safeURL(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a></li>`).join('')}</ul><p class="mono">Evidence SHA-256: ${esc(r.evidence_sha256??'Not available')}</p><p>A digest detects content changes; it does not establish factual accuracy, signer identity or approval.</p></div></details></div>`;
  }
  export function studyDialNextValue(value:number,min:number,max:number,step:number,key:string):number|null {
    if(![value,min,max,step].every(Number.isFinite)||step<=0||min>max)return null;
    if(key==='Home')return min;
    if(key==='End')return max;
    const direction=key==='ArrowRight'||key==='ArrowUp'?1:key==='ArrowLeft'||key==='ArrowDown'?-1:0;
    return direction?clamp(value+direction*step,min,max):null;
  }
  export function studyForm(def:StudyDefinition,draft:StudyDraft,connected:boolean):string {
    return `<form id="study-form" data-study-id="${esc(def.id)}" class="study-form"><div class="form-grid">${def.fields.map(f=>`<label class="field"><span>${esc(f.label)} ${f.unit?`(${esc(f.unit)})`:''}</span><input type="number" name="${esc(f.name)}" min="${f.min}" max="${f.max}" step="any" value="${esc(draft.values[f.name]??f.default)}" required ${draft.busy?'disabled':''}><input type="range" data-study-dial="${esc(f.name)}" min="${f.min}" max="${f.max}" step="any" data-study-step="${f.step}" data-study-unit="${esc(f.unit??'')}" value="${esc(draft.values[f.name]??f.default)}" aria-valuetext="${esc(draft.values[f.name]??f.default)} ${esc(f.unit??'')}" aria-label="${esc(f.label)} slider" ${draft.busy?'disabled':''}></label>`).join('')}</div>${(def.data_fields??[]).map(f=>`<details class="method-details"><summary>${esc(f.label)} · JSON inputs</summary><label class="field"><span>${esc(f.label)}</span><textarea name="${esc(f.name)}" data-study-json rows="7" spellcheck="false" ${draft.busy?'disabled':''}>${esc(draft.values[f.name]??JSON.stringify(f.default,null,2))}</textarea></label><label class="btn secondary small">Load JSON file<input type="file" accept=".json,application/json" data-study-file="${esc(f.name)}" ${draft.busy?'disabled':''}></label></details>`).join('')}<div class="study-actions"><button type="submit" class="btn primary" ${!connected||draft.busy?'disabled':''}>${icon(draft.busy?'clock':'play',16)}${draft.busy?'Calculating…':def.id==='investment-sculpt'?'Run covenant solver':'Run experiment'}</button><button type="button" class="btn secondary" data-study-action="reset" ${draft.busy?'disabled':''}>Reset inputs</button></div><p class="form-note">${connected?'Local Python calculation. Imported evidence is unverified.':'Bundled Python example. Start the local Python app to calculate edited inputs.'}</p></form>`;
  }
  export function createStudyController(getState:()=>ViewState):{refresh:()=>void} {
    const drafts=new Map<string,StudyDraft>(),chosen=new Map<string,string>(),pins:StudyResult[]=[];
    let importGeneration=0;
    const loadingPages=new Set<string>(),loadErrors=new Map<string,string>();
    let exampleObserver:IntersectionObserver|undefined;
    let visualCleanup:(()=>void)|undefined;
    function renderVisual():void {
      visualCleanup?.();visualCleanup=undefined;
      const c=current(),host=document.getElementById('study-visual');if(!c||!host)return;
      host.innerHTML=studyVisual(c.def,c.draft.result,c.draft.slice);
      visualCleanup=bindStudyVisuals(host,c.def,c.draft,(name,value)=>{
        importGeneration++;c.draft.values[name]=value;c.draft.dirty=true;c.draft.error='';
        const input=document.querySelector<HTMLInputElement|HTMLTextAreaElement>(`#study-form [name="${CSS.escape(name)}"]`);
        if(input)input.value=value;
        status();
      });
    }
    function current():{def:StudyDefinition;draft:StudyDraft}|null {
      const page=getState().page,def=STUDY_BUNDLE.catalogue.find(s=>s.id===chosen.get(page))??STUDY_BUNDLE.catalogue.find(s=>s.page===page);
      if(!def||!STUDY_BUNDLE.results[def.id])return null;
      if(!drafts.has(def.id))drafts.set(def.id,{id:def.id,values:{},result:structuredClone(STUDY_BUNDLE.results[def.id]!),dirty:false,busy:false,error:'',slice:0,selectedSeries:0});
      return {def,draft:drafts.get(def.id)!};
    }
    function status():void {
      const c=current(),el=document.getElementById('study-status');if(!c||!el)return;
      el.textContent=c.draft.error||(c.draft.dirty?'Inputs changed. Previous results are hidden until this experiment succeeds.':'Completed example · synthetic or user-supplied inputs, not independently verified.');
      el.className=`notice ${c.draft.error?'warn':''}`;
      const result=document.getElementById('study-output');if(result)result.hidden=c.draft.dirty;
      const visual=document.getElementById('study-visual');
      if(visual){
        let editable=['pv-agrivoltaic','storage-annual'].includes(c.def.id);
        if(editable){const name=c.def.id==='storage-annual'?'tariff':'land_polygon_m',raw=c.draft.values[name];if(raw!==undefined)try{const value:unknown=JSON.parse(raw);editable=Array.isArray(value)&&(name==='tariff'?value.length===24&&value.every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=3):value.length>=3&&value.every(v=>Array.isArray(v)&&v.length===2&&v.every(n=>typeof n==='number'&&Number.isFinite(n))));}catch{editable=false;}}
        visual.hidden=c.draft.dirty&&!editable;visual.classList.toggle('inputs-dirty',c.draft.dirty);
      }
      document.querySelectorAll<HTMLButtonElement>('[data-study-export],[data-study-action="pin"]').forEach(b=>b.disabled=c.draft.dirty||c.draft.busy||(b.dataset.studyExport==='series'&&!c.draft.result.series.length));
    }
    function refresh():void {
      exampleObserver?.disconnect();exampleObserver=undefined;
      visualCleanup?.();visualCleanup=undefined;
      const c=current(),host=document.getElementById('page-content');if(!host)return;
      if(!c){
        const page=getState().page,def=STUDY_BUNDLE.catalogue.find(s=>s.id===chosen.get(page))??STUDY_BUNDLE.catalogue.find(s=>s.page===page);if(!def)return;
        let panel=document.getElementById('study-workbench');if(!panel){panel=document.createElement('section');panel.id='study-workbench';host.append(panel);}panel.className='panel study-workbench';
        panel.innerHTML=`<h2>${esc(def.title)}</h2>${studySchematic(def)}<p role="status">${esc(loadErrors.get(page)??'Loading verified example records…')}</p>${loadErrors.has(page)?'<button class="btn secondary" data-study-retry>Retry example download</button>':''}`;
        if(!loadingPages.has(page)&&!loadErrors.has(page)){
          const load=():void=>{exampleObserver?.disconnect();exampleObserver=undefined;if(loadingPages.has(page))return;
            loadingPages.add(page);void loadStudyExamples(page).catch(e=>loadErrors.set(page,e instanceof Error?e.message:'Example download failed.')).finally(()=>{loadingPages.delete(page);if(getState().page===page)refresh();});};
          if(typeof IntersectionObserver==='undefined')load();
          else {exampleObserver=new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting))load();},{rootMargin:'400px'});exampleObserver.observe(panel);}
        }
        return;
      }
      const {def,draft}=c;
      let panel=document.getElementById('study-workbench');if(!panel){panel=document.createElement('section');panel.id='study-workbench';host.append(panel);}
      panel.className='panel study-workbench';
      if(!host.querySelector('[data-study-jump]'))host.querySelector('.page-intro')?.insertAdjacentHTML('beforeend',`<button type="button" class="btn secondary small" data-study-jump>Open ${STUDY_BUNDLE.catalogue.filter(s=>s.page===def.page).length} experimental studies ↓</button>`);
      panel.innerHTML=`<div class="section-heading"><div><span class="eyebrow">FULL-SPECTRUM / EXPERIMENTAL STUDIES</span><h2>${esc(def.title)}</h2><p>${esc(def.summary)}</p></div><span class="tag muted">BOUNDED RESEARCH MODEL</span></div>${studySchematic(def)}<div class="study-layout">${studyForm(def,draft,getState().connected)}<div><div id="study-status" role="status"></div><div id="study-output">${studyResultView(def,draft.result,draft.slice,draft.selectedSeries)}</div></div></div><div class="study-actions"><button class="btn secondary small" data-study-export="json">${icon('download',15)} Inputs & results</button><button class="btn secondary small" data-study-export="csv">All result records · CSV</button><button class="btn secondary small" data-study-export="series">Selected series · CSV</button><button class="btn secondary small" data-study-export="memo">${def.page==='investment'?'IC briefing':def.page==='research'?'Research dossier':'Study memorandum'}</button><button class="btn secondary small" data-study-action="pin" ${draft.dirty||draft.busy?'disabled':''}>Pin comparison</button></div>${pins.length?`<details class="method-details"><summary>Pinned experiments (${pins.length}) · inspect assumptions before comparison</summary><div class="study-pin-grid">${pins.map(r=>`<article><h3>${esc(STUDY_BUNDLE.catalogue.find(s=>s.id===r.study)?.title??r.study)}</h3>${r.metrics.slice(0,5).map(m=>`<p>${esc(m.label)}: <strong>${esc(textValue(m.value))} ${esc(m.unit)}</strong></p>`).join('')}<button class="btn secondary small" data-study-unpin="${esc(r.study)}">Unpin</button></article>`).join('')}</div></details>`:''}`;
      const output=document.getElementById('study-output');
      if(output){const visual=document.createElement('div');visual.id='study-visual';output.before(visual);renderVisual();}
      if(Array.isArray(draft.result.details?.raw_paths))panel.querySelector('.study-actions:last-of-type')?.insertAdjacentHTML('beforeend','<button type="button" class="btn secondary small" data-study-export="paths">Raw seeded paths · CSV</button>');
      status();
    }
    const mark=(el:HTMLInputElement|HTMLTextAreaElement):void=>{const c=current();if(!c||c.draft.busy)return;importGeneration++;c.draft.values[el.name]=el.value;c.draft.dirty=true;c.draft.error='';status();};
    document.addEventListener('keydown',event=>{
      const el=event.target as HTMLInputElement;
      if(!el.closest('#study-workbench')||!el.dataset.studyDial||el.disabled)return;
      const value=studyDialNextValue(Number(el.value),Number(el.min),Number(el.max),Number(el.dataset.studyStep),event.key);
      if(value===null)return;
      event.preventDefault();el.value=String(value);el.dispatchEvent(new Event('input',{bubbles:true}));
    });
    document.addEventListener('input',event=>{
      const el=event.target as HTMLInputElement;if(!el.closest('#study-workbench'))return;
      const c=current();if(!c)return;
      if(el.hasAttribute('data-study-slice')){c.draft.slice=Number(el.value);const chart=document.getElementById('study-chart'),series=c.draft.result.series[c.draft.selectedSeries];if(chart&&series)chart.innerHTML=studyChart(series,c.draft.slice);renderVisual();return;}
      if(el.dataset.studyDial){el.setAttribute('aria-valuetext',`${el.value} ${el.dataset.studyUnit??''}`.trim());const input=document.querySelector<HTMLInputElement>(`#study-form input[name="${CSS.escape(el.dataset.studyDial)}"]`);if(input){input.value=el.value;mark(input);}return;}
      if(el.name){mark(el);const dial=document.querySelector<HTMLInputElement>(`[data-study-dial="${CSS.escape(el.name)}"]`);if(dial){dial.value=el.value;dial.setAttribute('aria-valuetext',`${dial.value} ${dial.dataset.studyUnit??''}`.trim());}if(el.hasAttribute('data-study-json')&&!document.getElementById('study-visual')?.hidden){renderVisual();status();}}
    });
    document.addEventListener('change',event=>{
      const el=event.target as HTMLInputElement,c=current();if(!c||!el.closest('#study-workbench'))return;
      if(el.hasAttribute('data-study-series')){c.draft.selectedSeries=Number(el.value);c.draft.slice=0;refresh();return;}
      if(el.dataset.studyFile){
        if(c.draft.busy)return;
        const file=el.files?.[0];if(!file)return;
        const generation=++importGeneration,name=el.dataset.studyFile;
        const currentImport=()=>generation===importGeneration&&current()?.draft===c.draft;
        c.draft.dirty=true;status();
        void(async()=>{try{
          if(file.size>800000)throw Error('JSON file must be smaller than 800 KB.');
          const text=await file.text();if(!currentImport())return;
          const parsed=JSON.parse(text);c.draft.values[name]=JSON.stringify(parsed,null,2);c.draft.error='';refresh();
        }catch(e){if(currentImport()){c.draft.error=e instanceof Error?e.message:'JSON import failed.';status();}}})();
      }
    });
    document.addEventListener('submit',event=>{
      const form=event.target as HTMLFormElement;if(form.id!=='study-form')return;event.preventDefault();
      const c=current();if(!c||c.draft.busy||!getState().connected)return;
      importGeneration++;
      void(async()=>{
        try{
          const inputs:Record<string,unknown>={},data=new FormData(form);
          for(const f of c.def.fields)inputs[f.name]=finiteInput(data.get(f.name),f.label);
          for(const f of c.def.data_fields??[])inputs[f.name]=JSON.parse(String(data.get(f.name)));
          c.draft.busy=true;c.draft.error='';c.draft.dirty=true;refresh();
          const response=await fetch('/api/studies/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({study:c.def.id,inputs}),signal:AbortSignal.timeout(120000)});
          const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'The model rejected these inputs. Check bounds and JSON structure.');
          c.draft.result=body as StudyResult;c.draft.dirty=false;c.draft.slice=0;c.draft.selectedSeries=0;
        }catch(e){c.draft.error=e instanceof Error?e.message:'Experiment failed. No new result was recorded.';}
        finally{c.draft.busy=false;refresh();}
      })();
    });
    document.addEventListener('click',event=>{
      const el=(event.target as Element).closest<HTMLElement>('button');
      if(el?.hasAttribute('data-study-jump')){const panel=document.getElementById('study-workbench');if(panel){panel.tabIndex=-1;panel.focus();panel.scrollIntoView({behavior:'instant'});}return;}
      if(!el?.closest('#study-workbench'))return;
      if(el.hasAttribute('data-study-retry')){loadErrors.delete(getState().page);refresh();return;}
      if(el.dataset.studySelect){importGeneration++;chosen.set(getState().page,el.dataset.studySelect);refresh();return;}
      const c=current();if(!c)return;
      if(el.dataset.studyUnpin){const i=pins.findIndex(r=>r.study===el.dataset.studyUnpin);if(i>=0)pins.splice(i,1);refresh();return;}
      if(el.dataset.studyAction==='reset'){importGeneration++;drafts.delete(c.def.id);refresh();return;}
      if(el.dataset.studyAction==='pin'&&!c.draft.dirty&&!c.draft.busy){const old=pins.findIndex(r=>r.study===c.def.id);if(old>=0)pins.splice(old,1);pins.push(structuredClone(c.draft.result));if(pins.length>3)pins.shift();refresh();return;}
      const kind=el.dataset.studyExport;if(!kind||c.draft.dirty||c.draft.busy)return;
      const r=c.draft.result;
      if(kind==='csv')download(`${c.def.id}.csv`,toCSV(studyExportRows(r,r.table)),'text/csv');
      else if(kind==='paths'){
        const paths=r.details?.raw_paths;
        if(Array.isArray(paths))download(`${c.def.id}-raw-paths.csv`,toCSV(studyExportRows(r,paths.flatMap(p=>(p.prices_eur_mwh as number[]).map((price,i)=>({seed:r.inputs.seed,path:p.path,year:i+1,price_eur_mwh:price,loss_eur:p.losses_eur[i]}))))),'text/csv');
      }
      else if(kind==='series'){const s=r.series[c.draft.selectedSeries];if(s)download(`${c.def.id}-series.csv`,toCSV(studyExportRows(r,s.x.map((x,i)=>({observation:x,value:s.y[i],unit:s.y_unit})))),'text/csv');}
      else if(kind==='memo'){const lines=[`# ${c.def.title}`,'',c.def.summary,'','## Result provenance','```json',String(studyExportRows(r,[])[0]!.hf_provenance_json),'```','','## Results',...r.metrics.map(m=>`- ${m.label}: ${textValue(m.value)} ${m.unit}`),'','## Assumptions','```json',JSON.stringify(r.inputs,null,2),'```','','## Boundaries',...c.def.limitations.map(l=>'- '+l),...r.warnings.map(l=>'- '+l),'','Evidence SHA-256: '+r.evidence_sha256,'No investment, engineering, regulatory or operational approval is implied.'];download(`${c.def.id}-memorandum.md`,lines.join('\n'),'text/markdown');}
      else download(`${c.def.id}.json`,JSON.stringify(r,null,2));
    });
    return {refresh};
  }
}
