namespace HF {
  export interface HybridCallbacks {
    render:()=>void; toast:(message:string,error?:boolean)=>void; navigate:(page:Page)=>void;
    api:<T>(path:string,body?:unknown,method?:string,adminKey?:string)=>Promise<T>;
    celebrate:()=>void; openModal:(title:string,body:string)=>void; persist?:()=>boolean;
  }
  export function installHybridController(state:ViewState,cb:HybridCallbacks):void {
    const h=state.hybrid;
    function selectSystem(id:string):void {
      const s=systemById(id);h.inputs=presetInputs(id);h.objectId=s.technologies.includes('battery')?'battery':s.technologies[0]!;
      h.result=null;h.resultInputs=null;h.inputError=null;h.draft=null;h.hour=12;if(state.champion)state.champion.lastRunId=null;cb.persist?.();cb.navigate('hybrid');
    }
    function collect(form:HTMLFormElement):HybridInputs {
      const value:Record<string,unknown>={...h.inputs};
      for(const [name,v] of new FormData(form)){if(name==='control')value[name]=String(v);else value[name]=finiteInput(v,name);}
      return parseConfiguration(value);
    }
    function downloadJSON(name:string,value:unknown):void{download(name,JSON.stringify(value,null,2));}
    async function act(name:string):Promise<void> {
      if(h.busy&&['reset','import','launch-lesson'].includes(name))throw new Error('Complete the current run before changing its configuration.');
      if(name==='export'){const form=document.getElementById('hybrid-config') as HTMLFormElement|null;if(form&&!h.busy)h.inputs=collect(form);downloadJSON('helioforge-configuration.json',{schema:'helioforge.hybrid.v1',data_kind:'synthetic_educational',inputs:h.inputs});}
      else if(name==='reset')selectSystem(h.inputs.system_id);
      else if(name==='clear-filters'){h.search='';h.family='All';h.topology='All';cb.render();document.getElementById('architecture-library')?.scrollIntoView({behavior:'instant'});}
      else if(name==='import'){
        const file=document.createElement('input');file.type='file';file.accept='.json,application/json';
        file.onchange=async()=>{try{if(h.busy)throw new Error('Complete the current run before importing a configuration.');const f=file.files?.[0];if(!f)return;if(f.size>100_000)throw new Error('Configuration file must be under 100 KB.');const p=parseConfiguration(JSON.parse(await f.text()));h.inputs=p;h.result=null;h.resultInputs=null;h.inputError=null;h.draft=null;if(state.champion)state.champion.lastRunId=null;cb.persist?.();h.objectId=systemById(p.system_id).technologies[0]!;cb.render();cb.toast('Configuration imported. Run the API to calculate this setup.');}catch(e){cb.toast(e instanceof Error?e.message:'Invalid configuration file.',true);}};file.click();
      }else if(name==='csv'){if(!h.result||hybridDirty(h))throw new Error('Run this configuration first.');download('helioforge-hybrid-dispatch.csv',toCSV(h.result.schedule.map(x=>({...x}))),'text/csv');}
      else if(name==='pin'){
        if(!h.result||hybridDirty(h)||!h.resultInputs)throw new Error('Only a completed, current result can be compared.');
        if(h.compare.length>=3)throw new Error('The comparison holds three runs. Remove a pinned run first.');
        const id=h.result.run_id??'bundled-example';if(h.compare.some(x=>x.id===id))throw new Error('This exact run is already pinned.');
        h.compare.push({id,name:`${systemById(h.result.system_id).name} / ${scenarioById(h.result.scenario_id).name}`,inputs:structuredClone(h.resultInputs),result:structuredClone(h.result)});
        cb.persist?.();cb.toast(`Pinned ${h.compare.length} of 3 runs. Open Scenario compare to inspect them.`);
      }else if(name==='export-compare')downloadJSON('helioforge-comparison.json',{schema:'helioforge.comparison.v1',note:'Synthetic, different service and SOC endpoints must be reconciled before ranking.',runs:h.compare});
      else if(name==='clear-compare'){h.compare=[];if(state.champion)state.champion.pendingPins=[];cb.persist?.();cb.render();}
      else if(name==='launch-lesson'){
        const l=HYBRID_CATALOG.lessons.find(x=>x.id===h.lessonId)!;
        selectSystem(l.system_id);h.inputs=presetInputs(l.system_id,l.scenario_id);h.draft=null;h.inputError=null;cb.persist?.();cb.render();cb.toast('Lesson configuration loaded. Begin with a reference run, then apply the lesson stress.');
      }else if(name==='export-lesson'){
        const l=HYBRID_CATALOG.lessons.find(x=>x.id===h.lessonId)!;
        downloadJSON(`helioforge-${l.id}.json`,{schema:'helioforge.lesson.v1',lesson:l,configuration:presetInputs(l.system_id,l.scenario_id),notice:'Original local self-study material; not accredited or field-validated.'});
      }else if(name==='export-progress')downloadJSON('helioforge-learning-progress.json',{schema:'helioforge.progress.v1',exported_at:new Date().toISOString(),passed_self_checks:h.progress,notice:'Self-reported browser-local practice. Not verified credentials.'});
      else if(name==='reset-progress')cb.openModal('Reset learning progress?',`<div class="modal-copy"><p>This removes the ${h.progress.length} passed self-checks stored in this browser. It does not delete exported records or API runs.</p><button class="btn secondary" data-hybrid-action="confirm-reset-progress">Reset browser progress</button></div>`);
      else if(name==='confirm-reset-progress'){h.progress=[];try{localStorage.removeItem('hf-lessons-v2');}catch{/* optional */}cb.render();cb.toast('Browser learning progress reset.');}
      else if(name==='review-hybrid'){
        if(!h.result?.run_id||hybridDirty(h))throw new Error('Calculate and save a current hybrid run first.');
        cb.navigate('council');
      }
    }
    document.addEventListener('click',event=>{
      const el=(event.target as Element).closest<HTMLElement>('button');if(!el)return;
      try{
        if(el.dataset.system){if(h.busy)return;selectSystem(el.dataset.system);window.scrollTo({top:0,behavior:'instant'});}
        if(el.dataset.scenario){if(h.busy)return;if(h.inputError)throw new Error('Correct the input error before changing the scenario.');h.draft=null;const c=scenarioById(el.dataset.scenario);h.inputs={...h.inputs,scenario_id:c.id,hours:Math.max(h.inputs.hours,Number(c.modifiers.hours??0))};h.hour=Math.min(h.hour,h.inputs.hours-1);cb.persist?.();cb.render();}
        if(el.dataset.lesson){h.lessonId=el.dataset.lesson;h.quizResult=null;cb.persist?.();cb.navigate('lessons');}
        if(el.dataset.asset){h.objectId=el.dataset.asset;const inspector=document.getElementById('asset-inspector');if(inspector)inspector.innerHTML=assetInspector(h);document.querySelectorAll<HTMLButtonElement>('[data-asset]').forEach(b=>{b.classList.toggle('selected',b.dataset.asset===h.objectId);b.setAttribute('aria-pressed',String(b.dataset.asset===h.objectId));});}
        if(el.dataset.sceneCommand)document.getElementById('energy-scene')?.dispatchEvent(new CustomEvent('scene-command',{detail:el.dataset.sceneCommand}));
        if(el.dataset.hybridAction)void act(el.dataset.hybridAction).catch(e=>cb.toast(e instanceof Error?e.message:'Action failed.',true));
        if(el.dataset.removeCompare){h.compare=h.compare.filter(x=>x.id!==el.dataset.removeCompare);if(state.champion)state.champion.pendingPins=state.champion.pendingPins.filter(x=>x!==el.dataset.removeCompare);cb.persist?.();cb.render();}
      }catch(e){cb.toast(e instanceof Error?e.message:'Invalid selection.',true);}
    });
    function updateLibrary():void{const el=document.getElementById('hybrid-library-results');if(el)el.innerHTML=hybridLibrary(h);}
    function syncHybridInput(el:HTMLInputElement):void {
      const form=el.closest<HTMLFormElement>('#hybrid-config');if(!form||h.busy)return;
      const draft:Record<string,string>={};
      for(const field of form.querySelectorAll<HTMLInputElement|HTMLSelectElement>('input[name],select[name]'))draft[field.name]=field.value;
      // A native change event follows input on blur. Replacing the toolbar here
      // would remove a pointer's target between mousedown and click.
      if(h.draft&&JSON.stringify(draft)===JSON.stringify(h.draft))return;
      h.draft=draft;
      try{
        h.inputs=collect(form);h.inputError=null;
        const tags=document.getElementById('smart-tags');if(tags)tags.innerHTML=hybridTags(h.inputs).map(t=>`<span class="smart-tag" title="${escapeHTML(t.reason)}">${escapeHTML(t.label)}</span>`).join('');
        const inspector=document.getElementById('asset-inspector');if(inspector)inspector.innerHTML=assetInspector(h);
        form.querySelectorAll('[aria-invalid]').forEach(e=>e.removeAttribute('aria-invalid'));cb.persist?.();
      }catch(e){h.inputError=e instanceof Error?e.message:'Invalid input.';el.setAttribute('aria-invalid','true');}
      const output=document.getElementById('hybrid-output');if(output)output.innerHTML=hybridResults(state);
      const toolbar=document.getElementById('champion-toolbar');if(toolbar)toolbar.innerHTML=championToolbar(state);
    }
    document.addEventListener('input',event=>{
      const el=event.target as HTMLInputElement;
      if(el.closest('#hybrid-config')&&el.name)syncHybridInput(el);
      if(el.id==='hybrid-search'){h.search=el.value;updateLibrary();}
      if(el.id==='hybrid-hour'&&h.result){h.hour=Number(el.value);const point=h.result.schedule[h.hour]!;const read=document.getElementById('interval-readout'),label=document.getElementById('hour-label');if(read)read.innerHTML=intervalReadout(point);if(label)label.textContent=point.label;}
    });
    document.addEventListener('change',event=>{
      const el=event.target as HTMLInputElement;
      if(el.id==='hybrid-family'){h.family=el.value;updateLibrary();}
      if(el.id==='hybrid-topology'){h.topology=el.value;updateLibrary();}
      if(el.id==='hybrid-system'){if(!h.busy)selectSystem(el.value);return;}
      if(el.closest('#hybrid-config')&&el.name)syncHybridInput(el);
    });
    document.addEventListener('submit',event=>{
      const form=event.target as HTMLFormElement;
      if(form.id==='hybrid-config'){
        event.preventDefault();if(h.busy||!state.connected)return;
        void (async()=>{
          try{
            const inputs=collect(form);h.inputs=inputs;h.inputError=null;h.busy=true;
            const button=form.querySelector<HTMLButtonElement>('[type=submit]')!;button.disabled=true;button.textContent='Running energy screen…';
            // Snapshot inputs to avoid labeling a pending response with later edits.
            form.querySelectorAll<HTMLInputElement|HTMLSelectElement>('input,select').forEach(e=>e.disabled=true);document.querySelectorAll<HTMLButtonElement>('[data-system],[data-scenario]').forEach(e=>e.disabled=true);
            const result=await cb.api<HybridResult>('hybrid/simulate',inputs);
            h.result=result;h.resultInputs={...inputs};h.inputs={...inputs};h.inputError=null;h.draft=null;h.busy=false;if(state.champion)state.champion.lastRunId=result.run_id??null;cb.persist?.();h.hour=Math.min(h.hour,result.schedule.length-1);cb.render();cb.toast('Hybrid energy screen complete. Inputs and result saved in the local audit store.');
          }catch(e){h.busy=false;cb.render();cb.toast(e instanceof Error?e.message:'Simulation failed. Your inputs were retained.',true);}
        })();
      }
      if(form.id==='lesson-quiz'){
        event.preventDefault();const lesson=HYBRID_CATALOG.lessons.find(x=>x.id===h.lessonId)!;
        const fd=new FormData(form),answers=lesson.quiz.map((_,i)=>{const v=fd.get(`q${i}`);return v===null?-1:Number(v);});
        const result=gradeLesson(lesson,answers);h.quizResult=result;
        const feedback=document.getElementById('quiz-feedback');
        if(feedback)feedback.innerHTML=`<div class="quiz-result ${result.passed?'passed':'retry'}"><strong>${result.correct} / ${result.total} correct · ${result.passed?'Self-check passed':'Review and try again'}</strong>${lesson.quiz.map((q,i)=>`<p><b>${i+1} · ${answers[i]===q.answer?'Correct':'Review'}:</b> ${escapeHTML(q.explanation)}</p>`).join('')}</div>`;
        if(result.passed){
          const first=!h.progress.includes(lesson.id);if(first){h.progress.push(lesson.id);try{localStorage.setItem('hf-lessons-v2',JSON.stringify(h.progress));}catch{cb.toast('Self-check passed. Browser storage is unavailable; export your progress.');}}
          if(first)cb.celebrate();
          const progress=document.querySelector('.achievement-orb strong');if(progress)progress.innerHTML=`${h.progress.length}<small> / 36</small>`;
          const number=document.querySelector(`.lesson-list [data-lesson="${lesson.id}"] .lesson-number`);if(number){number.classList.add('done');number.innerHTML=icon('check',14);}
        }
      }
    });
  }
}
