/* Progressive enhancement only: model contracts remain visible without JavaScript. */
(() => {
  'use strict';
  const input=document.getElementById('registry-search');
  const workspace=document.getElementById('registry-workspace');
  const clear=document.getElementById('registry-clear');
  const count=document.getElementById('registry-count');
  const empty=document.getElementById('registry-empty');
  const directory=document.getElementById('registry-workspaces');
  const cards=[...document.querySelectorAll('#registry-results .model-card')];
  if(!input||!workspace||!clear||!count||!empty||!directory||!cards.length)return;
  function apply(){
    const term=input.value.trim().toLocaleLowerCase(), chosen=workspace.value;
    let visible=0;
    for(const card of cards){
      const matches=(!chosen||card.dataset.workspace===chosen)&&(!term||(card.dataset.search||'').includes(term));
      card.hidden=!matches;
      if(matches)visible++;
    }
    count.textContent='Showing '+visible+' of '+cards.length+' models.';
    empty.hidden=visible!==0;
  }
  function revealWorkspace(){if(location.hash.startsWith('#workspace-'))directory.open=true;}
  input.addEventListener('input',apply);
  workspace.addEventListener('change',apply);
  clear.addEventListener('click',()=>{input.value='';workspace.value='';apply();input.focus();});
  window.addEventListener('hashchange',revealWorkspace);
  revealWorkspace();apply();
})();
