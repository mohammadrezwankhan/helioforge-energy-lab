namespace HF {
  export interface ChampionController { persist:()=>boolean; restore:()=>Promise<void>; history:()=>Promise<void> }
  export function installChampionController(state:ViewState,cb:HybridCallbacks):ChampionController {
    const h=state.hybrid,c=state.champion!;
    let selectionEpoch=0;
    let pendingWorkspaceImport:{record:WorkspaceCache;receipt:WorkspaceMigrationReceipt;revision:number;restoreBackup:boolean;migrateCurrent:boolean}|null=null;
    const refreshToolbar=():void=>{const el=document.getElementById('champion-toolbar');if(el)el.innerHTML=championToolbar(state);};
    const persist=():boolean=>{const ok=persistWorkspace(state);refreshToolbar();return ok;};
    function setInputs(inputs:HybridInputs):void {
      advanceHybridStateRevision(h);
      h.inputs=parseConfiguration(inputs);h.result=null;h.resultInputs=null;h.inputError=null;h.draft=null;
      h.objectId=systemById(h.inputs.system_id).technologies[0]!;h.hour=Math.min(12,h.inputs.hours-1);c.lastRunId=null;
      attachBundledHybridResult(h);
    }
    function showWorkspace():void {cb.openModal('Saved setups',workspaceDialog(state));}
    async function history():Promise<void> {
      if(!state.connected){cb.toast('Run the local Python application to access saved calculations.');return;}
      state.runs=await cb.api<RunRecord[]>('runs');cb.openModal('Analysis history',historyDialog(state.runs));
    }
    function setResult(saved:SavedHybrid):void {
      setInputs(saved.inputs);h.result=saved.result;h.resultInputs={...saved.inputs};c.lastRunId=saved.run_id;
    }
    async function restore():Promise<void> {
      if(c.restored||!state.connected)return;
      c.restored=true;
      let revision=hybridStateRevision(h);
      const expected=configurationKey(h.inputs),runId=c.lastRunId,ids=[...c.pendingPins];
      const failures:string[]=[];
      if(runId){
        try {
          const saved=parseSavedHybrid(await cb.api<unknown>(`runs/${encodeURIComponent(runId)}`));
          if(revision!==hybridStateRevision(h)){c.restored=false;return;}
          if(configurationKey(saved.inputs)===expected&&configurationKey(h.inputs)===expected&&!h.busy&&!h.inputError)setResult(saved);
          else if(configurationKey(saved.inputs)!==expected)failures.push('The saved result does not match the restored setup.');
          revision=hybridStateRevision(h);
        } catch { if(revision!==hybridStateRevision(h)){c.restored=false;return;}failures.push('The previous result is unavailable in this API database. Your configuration is still retained.');c.restored=false; }
      }
      for(const id of ids){
        try {
          const saved=parseSavedHybrid(await cb.api<unknown>(`runs/${encodeURIComponent(id)}`));
          if(revision!==hybridStateRevision(h)){c.restored=false;return;}
          if(c.pendingPins.includes(id)&&h.compare.length<3&&!h.compare.some(r=>r.id===id))h.compare.push({id,name:`${systemById(saved.inputs.system_id).name} / ${scenarioById(saved.inputs.scenario_id).name}`,inputs:saved.inputs,result:saved.result});
          c.pendingPins=c.pendingPins.filter(x=>x!==id);
        } catch { if(revision!==hybridStateRevision(h)){c.restored=false;return;}failures.push('A pinned run is unavailable. Its reference is retained for reconnection.');c.restored=false; }
      }
      if(failures.length)c.notice=[...new Set(failures)].join(' ');
      else if(runId||ids.length)c.notice='Workspace recovered. Displayed results were loaded from actual saved API records.';
      if(!failures.length&&!c.recoveryRaw)persist();
      cb.render();
    }
    async function openRun(id:string):Promise<void> {
      if(h.busy)throw new Error('Wait for the current energy screen before reopening another run.');
      const epoch=++selectionEpoch;advanceHybridStateRevision(h);const revision=hybridStateRevision(h),expected=configurationKey(h.inputs),page=state.page;
      const saved=parseSavedHybrid(await cb.api<unknown>(`runs/${encodeURIComponent(id)}`));
      if(epoch!==selectionEpoch||revision!==hybridStateRevision(h)||h.busy||h.inputError||configurationKey(h.inputs)!==expected){cb.toast('The workspace changed while the run was loading. Your newer selection was retained.');return;}
      setResult(saved);persist();
      if(state.page===page)cb.navigate('hybrid');else cb.render();
      cb.toast('Saved calculation reopened with its exact inputs. No new simulation was performed.');
    }
    function previewWorkspaceImport(record:WorkspaceCache,receipt:WorkspaceMigrationReceipt,restoreBackup:boolean,revision:number,migrateCurrent=false):void {
      pendingWorkspaceImport={record,receipt,revision,restoreBackup,migrateCurrent};
      cb.openModal(migrateCurrent?'Preview workspace migration':restoreBackup?'Preview workspace backup':'Preview workspace import',workspaceImportPreview(record,restoreBackup,receipt,migrateCurrent));
    }
    function commitWorkspaceImport():void {
      const pending=pendingWorkspaceImport;if(!pending)throw new Error('There is no validated workspace import to confirm.');
      if(h.busy||pending.revision!==hybridStateRevision(h)){pendingWorkspaceImport=null;throw new Error('Workspace import cancelled because the current work changed after preview. Open the import again to review it.');}
      const record=parseWorkspace(pending.record);
      const serialized=JSON.stringify(record);
      if(serialized.length>100_000)throw new Error('Workspace record is too large to store safely.');
      let previous:string|null;
      try{previous=localStorage.getItem(WORKSPACE_KEY);}catch{throw new Error('Workspace import cancelled because browser storage cannot be read. The current setup was retained.');}
      if(previous!==null){
        try{localStorage.setItem(WORKSPACE_BACKUP_KEY,previous);}catch{throw new Error('Workspace import cancelled because a recovery backup could not be written (storage quota or permission). The current setup was retained.');}
        c.importBackupRaw=previous;
      }
      try{localStorage.setItem(WORKSPACE_KEY,serialized);}catch{throw new Error('Workspace import cancelled because the imported record could not be stored (storage quota or permission). The current setup was retained; any previous cache remains recoverable.');}
      advanceHybridStateRevision(h);h.inputs=parseConfiguration(record.inputs);h.result=null;h.resultInputs=null;h.inputError=null;h.draft=null;h.lessonId=record.lesson_id;h.quizResult=null;h.objectId=systemById(h.inputs.system_id).technologies[0]!;h.hour=Math.min(12,h.inputs.hours-1);attachBundledHybridResult(h);h.compare=[];
      c.saved=record.saved_setups;c.lastRunId=record.last_run_id;c.pendingPins=[...record.pinned_run_ids];c.restored=false;c.lastSavedAt=record.saved_at;c.recoveryRaw=null;c.migrationReceipt=record.migration;c.lastMigrationReceipt=pending.receipt;c.migrationPendingRaw=null;if(previous!==null)c.importBackupRaw=previous;
      c.storage='available';c.notice=pending.migrateCurrent?'Workspace migration to v2 completed. The exact v1 record is available in the recovery backup.':pending.restoreBackup?'Workspace backup restored. The workspace it replaced is now the recovery backup.':`Workspace imported as ${record.schema}. The replaced browser cache is available as a recovery backup.`;pendingWorkspaceImport=null;
      cb.render();cb.toast(pending.migrateCurrent?'Workspace migration complete. Original raw v1 data remains in the recovery backup.':'Workspace imported. Saved API run references require the same local database.');
      if(state.connected)void restore().catch(fail);
    }
    async function action(name:string):Promise<void> {
      if(name==='workspace')showWorkspace();
      else if(name==='cancel-workspace-import'){pendingWorkspaceImport=null;showWorkspace();}
      else if(name==='guide')cb.openModal('A baseline. A stress. A better question.',quickStartDialog());
      else if(name==='commands'){
        cb.openModal('Find anything',commandDialog());
        const el=document.getElementById('command-search') as HTMLInputElement|null;el?.focus();el?.setAttribute('aria-activedescendant','command-option-0');
      }else if(name==='history')await history();
      else if(name==='dismiss-notice'){c.notice='';refreshToolbar();}
      else if(name==='migrate-workspace'){
        if(h.busy)throw new Error('Wait for the current calculation before migrating a workspace.');
        if(!c.migrationPendingRaw)throw new Error('There is no pending v1 workspace migration.');
        const source=prepareWorkspaceImport(JSON.parse(c.migrationPendingRaw));
        if(source.receipt.source_schema!==WORKSPACE_SCHEMA_V1)throw new Error('The pending local record is not a supported v1 workspace.');
        const record=workspaceCache(state),content=(value:WorkspaceCache)=>JSON.stringify({inputs:value.inputs,lesson_id:value.lesson_id,last_run_id:value.last_run_id,pinned_run_ids:value.pinned_run_ids,saved_setups:value.saved_setups});
        const receipt={...source.receipt,changes:[...source.receipt.changes],losses:[...source.receipt.losses]};
        const inputsUnchanged=JSON.stringify(record.inputs)===JSON.stringify(source.record.inputs);
        if(record.last_run_id===null&&inputsUnchanged&&c.lastRunId===source.record.last_run_id)
          record.last_run_id=source.record.last_run_id;
        if(source.record.last_run_id&&record.last_run_id===null)
          receipt.losses.push(inputsUnchanged
            ?'Cleared the saved last-run ID because the current in-memory run reference no longer matches the v1 record.'
            :'Cleared the saved last-run ID because current inputs differ from the v1 workspace inputs.');
        if(record.saved_at!==source.record.saved_at)
          receipt.changes.push('Refreshed the workspace saved_at timestamp during migration.');
        if(content(record)!==content(source.record))receipt.changes.push('Included current in-memory workspace fields after loading the v1 record.');
        record.migration=receipt;
        previewWorkspaceImport(record,receipt,false,hybridStateRevision(h),true);
      }else if(name==='export-workspace-migration-receipt'){
        const receipt=pendingWorkspaceImport?.receipt??c.lastMigrationReceipt??c.migrationReceipt;if(!receipt)throw new Error('There is no workspace migration receipt to export.');
        download('helioforge-workspace-migration-receipt.json',JSON.stringify(receipt,null,2),'application/json');
      }
      else if(name==='import-workspace'){
        if(h.busy)throw new Error('Wait for the current calculation before importing a workspace.');
        const revision=advanceHybridStateRevision(h),file=document.createElement('input');file.type='file';file.accept='.json,application/json';
        file.onchange=async()=>{try{const selected=file.files?.[0];if(!selected)return;if(selected.size>100_000)throw new Error('Workspace file must be at most 100 KB.');const prepared=prepareWorkspaceImport(JSON.parse(await selected.text()));if(revision!==hybridStateRevision(h)||h.busy)throw new Error('Workspace import cancelled because newer work started while the file was being read.');previewWorkspaceImport(prepared.record,prepared.receipt,false,revision);}catch(error){cb.toast(error instanceof Error?error.message:'Invalid workspace file.',true);}};file.click();
      }else if(name==='restore-workspace-backup'){
        if(h.busy)throw new Error('Wait for the current calculation before restoring a workspace backup.');
        if(!c.importBackupRaw)throw new Error('There is no workspace backup to restore.');
        const revision=advanceHybridStateRevision(h),prepared=prepareWorkspaceImport(JSON.parse(c.importBackupRaw));previewWorkspaceImport(prepared.record,prepared.receipt,true,revision);
      }else if(name==='confirm-workspace-import')commitWorkspaceImport();
      else if(name==='start-hospital'){
        if(h.busy)throw new Error('Wait for the current energy screen.');
        setInputs(presetInputs('hospital-island'));persist();cb.navigate('hybrid');cb.toast('Hospital bundled reference loaded. Pin it, then select Four-hour outage to compare the bundled stress case. Edited inputs require the local Python API.');
      }else if(name==='export-workspace')download('helioforge-workspace.json',JSON.stringify(workspaceCache(state),null,2));
      else if(name==='recovery-export')download('helioforge-workspace-recovery.txt',c.recoveryRaw??'No damaged cache is present.','text/plain');
      else if(name==='backup-export')download('helioforge-workspace-backup.txt',c.importBackupRaw??'No workspace backup is present.','text/plain');
      else if(name==='recovery-reset')cb.openModal('Reset the damaged workspace cache?',`<div class="modal-copy"><p>This removes the unreadable browser cache. It does not delete your API runs, lesson progress or exported files. Download the recovery record first to keep a copy.</p><div class="h-actions"><button class="btn secondary" data-champion-action="workspace">Keep it</button><button class="btn primary" data-champion-action="confirm-recovery-reset">Reset browser cache</button></div></div>`);
      else if(name==='confirm-recovery-reset'){
        localStorage.removeItem(WORKSPACE_KEY);c.recoveryRaw=null;c.notice='Browser workspace cache reset. Existing API runs were not changed.';persist();showWorkspace();
      }
    }
    function fail(error:unknown):void {cb.toast(error instanceof Error?error.message:'The workspace action could not complete.',true);}
    document.addEventListener('click',event=>{
      const el=(event.target as Element).closest<HTMLElement>('button');if(!el)return;
      try {
        if(el.dataset.championAction)void action(el.dataset.championAction).catch(fail);
        if(el.dataset.restoreRun)void openRun(el.dataset.restoreRun).catch(fail);
        const setupId=el.dataset.loadSetup??el.dataset.exportSetup??el.dataset.deleteSetup??el.dataset.confirmDelete;
        if(setupId){
          const s=c.saved.find(x=>x.id===setupId);if(!s)throw new Error('The saved setup is no longer available.');
          if(el.dataset.loadSetup){if(h.busy)throw new Error('Wait for the current energy screen.');setInputs(s.inputs);persist();cb.navigate('hybrid');cb.toast(h.result?'Saved preset loaded with its bundled Python result.':'Saved setup loaded. Start the local Python API to calculate these edited inputs.');}
          if(el.dataset.exportSetup)download('helioforge-saved-setup.json',JSON.stringify({schema:'helioforge.hybrid.v1',inputs:s.inputs},null,2));
          if(el.dataset.deleteSetup)cb.openModal('Delete this saved setup?',`<div class="modal-copy"><p>Remove <strong>${escapeHTML(s.name)}</strong> from this browser? The current configuration and API runs will not be deleted.</p><div class="h-actions"><button class="btn secondary" data-champion-action="workspace">Keep setup</button><button class="btn primary" data-confirm-delete="${s.id}">Delete saved setup</button></div></div>`);
          if(el.dataset.confirmDelete){c.saved=c.saved.filter(x=>x.id!==setupId);const ok=persist();showWorkspace();cb.toast(ok?'Saved setup removed from this browser.':'Removed in this tab only; browser storage could not be updated.',!ok);}
        }
        if(el.dataset.commandKind){
          const target=el.dataset.commandTarget!;
          if(el.dataset.commandKind==='action')void action(target).catch(fail);
          else if(el.dataset.commandKind==='page')cb.navigate(target as Page);
          else if(el.dataset.commandKind==='system'){if(h.busy)throw new Error('Wait for the current energy screen.');setInputs(presetInputs(target));persist();cb.navigate('hybrid');}
          else if(el.dataset.commandKind==='lesson'){h.lessonId=target;h.quizResult=null;persist();cb.navigate('lessons');}
        }
      } catch(e){fail(e);}
    });
    document.addEventListener('input',event=>{
      const el=event.target as HTMLInputElement;
      if(el.id==='run-search'){const target=document.getElementById('run-results');if(target)target.innerHTML=historyRows(state.runs,el.value);}
      if(el.id==='command-search'){
        const list=document.getElementById('command-results');if(list)list.innerHTML=commandResults(el.value);
        if(list?.querySelector('button'))el.setAttribute('aria-activedescendant','command-option-0');else el.removeAttribute('aria-activedescendant');
      }
    });
    document.addEventListener('keydown',event=>{
      if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();void action('commands').catch(fail);return;}
      if(event.key===':'&&!(event.target as Element).closest('input,textarea,select,[contenteditable="true"]')){
        event.preventDefault();void action('commands').then(()=>{const input=document.getElementById('command-search') as HTMLInputElement|null;if(input){input.value=':';input.dispatchEvent(new Event('input',{bubbles:true}));}}).catch(fail);return;
      }
      const el=event.target as HTMLInputElement;if(el.id!=='command-search')return;
      if(event.key==='Enter'&&el.value.trim().startsWith(':')){event.preventDefault();document.dispatchEvent(new CustomEvent('terminal-command',{detail:el.value}));return;}
      const buttons=[...document.querySelectorAll<HTMLButtonElement>('#command-results button')];if(!buttons.length)return;
      let selected=Math.max(0,buttons.findIndex(b=>b.classList.contains('active')));
      if(event.key==='ArrowDown'||event.key==='ArrowUp'){
        event.preventDefault();selected=(selected+(event.key==='ArrowDown'?1:buttons.length-1))%buttons.length;
        buttons.forEach((b,i)=>{b.classList.toggle('active',i===selected);b.setAttribute('aria-selected',String(i===selected));});
        el.setAttribute('aria-activedescendant',buttons[selected]!.id);buttons[selected]!.scrollIntoView({block:'nearest'});
      } else if(event.key==='Enter'){event.preventDefault();buttons[selected]!.click();}
    });
    document.addEventListener('submit',event=>{
      const form=event.target as HTMLFormElement;if(form.id!=='save-setup-form')return;
      event.preventDefault();
      try {
        if(h.busy||h.inputError||c.recoveryRaw)throw new Error('Resolve the current operation or workspace recovery before saving.');
        const name=String(new FormData(form).get('setup_name')??'').trim();
        if(!name||name.length>80)throw new Error('Use a setup name of 1–80 characters.');
        if(c.saved.length>=20)throw new Error('The shelf holds 20 setups. Export and remove one before adding another.');
        c.saved.push({id:`setup-${crypto.randomUUID()}`,name,created_at:new Date().toISOString(),inputs:parseConfiguration(h.inputs)});
        const ok=persist();showWorkspace();cb.toast(ok?'Setup saved in this browser.':'Setup added to memory only. Export it before closing this tab.',!ok);
      }catch(e){fail(e);}
    });
    return {persist,restore,history};
  }
}
