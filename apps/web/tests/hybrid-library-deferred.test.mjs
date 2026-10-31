import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {transform} from 'esbuild';

const viewSource=fs.readFileSync(new URL('../src/hybrid-views.ts',import.meta.url),'utf8');
const controllerSource=fs.readFileSync(new URL('../src/hybrid-controller.ts',import.meta.url),'utf8');
const viewScript=(await transform(viewSource,{loader:'ts',target:'es2022'})).code;
const controllerScript=(await transform(controllerSource,{loader:'ts',target:'es2022'})).code;

function fixture({intersectionObserver=true}={}){
  const systems=[
    {id:'hospital-island',name:'Hospital island',family:'Microgrids',topology:'Off-grid',coupling:'AC',control:'GFM',technologies:['battery'],description:'Hospital backup microgrid',learning_focus:'Hospital resilience',evidence:'Site load evidence',mode:'screening'},
    {id:'solar-farm',name:'Solar farm',family:'Solar',topology:'Grid-tied',coupling:'DC',control:'GFL',technologies:['solar'],description:'Utility solar generation',learning_focus:'Solar generation',evidence:'Solar evidence',mode:'screening'},
    ...Array.from({length:34},(_,index)=>({id:`test-system-${index+1}`,name:`Test system ${index+1}`,family:'Advanced',topology:'Grid-tied',coupling:'AC',control:'GFM',technologies:['solar'],description:`Controlled architecture ${index+1}`,learning_focus:'Controlled study',evidence:'Controlled evidence',mode:'screening'})),
  ];
  const scenarios=[{id:'baseline',name:'Baseline',category:'Normal',description:'Reference conditions',modifiers:{},mode:'screening'}];
  const observers=[],listeners=new Map(),elements={
    'architecture-library':{scrollIntoView(){}},
    'hybrid-library-results':{innerHTML:'deferred placeholder'},
  };
  class FakeIntersectionObserver{
    constructor(callback,options){this.callback=callback;this.options=options;this.targets=[];this.disconnected=false;observers.push(this);}
    observe(target){this.targets.push(target);}
    disconnect(){this.disconnected=true;}
    trigger(target,isIntersecting=true){this.callback([{target,isIntersecting}],this);}
  }
  const document={
    addEventListener(type,callback){const rows=listeners.get(type)??[];rows.push(callback);listeners.set(type,rows);},
    getElementById(id){return elements[id]??null;},
    querySelectorAll(){return [];},
  };
  const box=vm.createContext({document,window:{scrollTo(){}},escapeHTML:value=>String(value??''),fmt:value=>String(value??''),money:value=>String(value??''),icon:()=>'<svg aria-hidden="true"></svg>',
    filterSystems:(search,family,topology)=>systems.filter(system=>(family==='All'||system.family===family)&&(topology==='All'||system.topology===topology)&&
      (!search||`${system.name} ${system.description} ${system.topology} ${system.family}`.toLowerCase().includes(search.toLowerCase()))),
    techById:id=>({id,name:id,color:'#123456',icon:'layers'}),systemById:id=>systems.find(system=>system.id===id),
    scenarioById:id=>scenarios.find(scenario=>scenario.id===id),applicable:()=>true,hybridTags:()=>[],assetInspector:()=>'<p>Asset</p>',hybridResults:()=>'<p>Result</p>',
    HYBRID_CATALOG:{systems,scenarios},
  });
  if(intersectionObserver)box.IntersectionObserver=FakeIntersectionObserver;
  vm.runInContext(viewScript,box);
  box.hybridLibrary=box.HF.hybridLibrary;
  vm.runInContext(controllerScript,box);
  const state={page:'hybrid',connected:false,busy:false,hybrid:{
    inputs:{system_id:'hospital-island',scenario_id:'baseline',hours:24,control:'GFM',solar_kw:0,wind_kw:0,hydro_kw:0,generator_kw:0,battery_kwh:100,battery_kw:50,load_kw:25,grid_import_kw:0,grid_export_kw:0,critical_fraction:.5,initial_soc:.5,min_soc:.1,max_soc:.9,round_trip_efficiency:.9,import_eur_kwh:.1,export_eur_kwh:0,generator_eur_kwh:.2},
    result:null,resultInputs:null,search:'',family:'All',topology:'All',lessonId:'lesson-hospital-island',progress:[],quizResult:null,objectId:'battery',hour:12,compare:[],busy:false,inputError:null,draft:null,libraryReady:false,
  }};
  const calls={renders:0,navigations:[],toasts:[],onRender:null};
  const callbacks={render(){calls.renders++;calls.onRender?.();},toast(message,error){calls.toasts.push({message,error});},navigate(page){calls.navigations.push(page);},api:async()=>{throw new Error('Unexpected API call');},celebrate(){},openModal(){}};
  const hf=box.HF;
  const handle=hf.installHybridController(state,callbacks);
  function dispatch(type,target){for(const callback of listeners.get(type)??[])callback({target,preventDefault(){},stopImmediatePropagation(){}});}
  return {box,hf,state,elements,observers,listeners,calls,handle,dispatch,FakeIntersectionObserver,systems};
}

test('initial hybrid markup keeps atlas controls and select but defers the 36-card result grid',()=>{
  const x=fixture(),markup=x.hf.hybridView(x.state);

  assert.match(markup,/id="hybrid-search"/);
  assert.match(markup,/id="hybrid-family"/);
  assert.match(markup,/id="hybrid-topology"/);
  assert.match(markup,/id="hybrid-system"/);
  assert.match(markup,/data-library-deferred/);
  assert.doesNotMatch(markup,/data-system="hospital-island"/);

  x.state.hybrid.libraryReady=true;
  const hydrated=x.hf.hybridView(x.state);
  assert.match(hydrated,/data-system="hospital-island"/);
  assert.equal((hydrated.match(/data-system="/g)??[]).length,36);
});

test('nearby atlas hydration fills the existing results node and ignores non-intersecting entries',()=>{
  const x=fixture();

  assert.equal(typeof x.handle?.refreshLibraryObserver,'function');
  x.handle.refreshLibraryObserver();
  assert.equal(x.observers.length,1);
  assert.equal(x.observers[0].options.rootMargin,'400px 0px');
  x.observers[0].trigger(x.elements['architecture-library'],false);
  assert.equal(x.state.hybrid.libraryReady,false);
  assert.equal(x.elements['hybrid-library-results'].innerHTML,'deferred placeholder');

  x.observers[0].trigger(x.elements['architecture-library'],true);

  assert.equal(x.state.hybrid.libraryReady,true);
  assert.match(x.elements['hybrid-library-results'].innerHTML,/data-system="hospital-island"/);
  assert.equal(x.observers[0].disconnected,true);
});

test('focus and search input eagerly render cards for keyboard and filter users',()=>{
  const focused=fixture();
  focused.handle.refreshLibraryObserver();
  const focusTarget={closest(selector){return selector==='#architecture-library'?{}:null;}};
  focused.dispatch('focusin',focusTarget);
  assert.equal(focused.state.hybrid.libraryReady,true);
  assert.match(focused.elements['hybrid-library-results'].innerHTML,/data-system="hospital-island"/);

  const searched=fixture();
  searched.handle.refreshLibraryObserver();
  const search={id:'hybrid-search',value:'hospital',closest(){return null;}};
  searched.dispatch('input',search);
  assert.equal(searched.state.hybrid.search,'hospital');
  assert.match(searched.elements['hybrid-library-results'].innerHTML,/data-system="hospital-island"/);
  assert.doesNotMatch(searched.elements['hybrid-library-results'].innerHTML,/data-system="solar-farm"/);
});

test('family and topology changes eagerly render the filtered result set',()=>{
  const byFamily=fixture();
  byFamily.dispatch('change',{id:'hybrid-family',value:'Solar',closest(){return null;}});
  assert.equal(byFamily.state.hybrid.libraryReady,true);
  assert.match(byFamily.elements['hybrid-library-results'].innerHTML,/data-system="solar-farm"/);
  assert.doesNotMatch(byFamily.elements['hybrid-library-results'].innerHTML,/data-system="hospital-island"/);

  const byTopology=fixture();
  byTopology.dispatch('change',{id:'hybrid-topology',value:'Off-grid',closest(){return null;}});
  assert.equal(byTopology.state.hybrid.libraryReady,true);
  assert.match(byTopology.elements['hybrid-library-results'].innerHTML,/data-system="hospital-island"/);
  assert.doesNotMatch(byTopology.elements['hybrid-library-results'].innerHTML,/data-system="solar-farm"/);
});

test('clear filters rerenders then eagerly fills the new result container',()=>{
  const x=fixture(),newRoot={scrollIntoView(){newRoot.scrolled=true;}},newResults={innerHTML:'new placeholder'};
  x.state.hybrid.search='hospital';x.state.hybrid.family='Microgrids';x.state.hybrid.topology='Off-grid';
  x.calls.onRender=()=>{x.elements['architecture-library']=newRoot;x.elements['hybrid-library-results']=newResults;};
  const button={dataset:{hybridAction:'clear-filters'},closest(selector){return selector==='button'?this:null;}};

  x.dispatch('click',button);

  assert.equal(x.state.hybrid.search,'');
  assert.equal(x.state.hybrid.family,'All');
  assert.equal(x.state.hybrid.topology,'All');
  assert.equal(x.state.hybrid.libraryReady,true);
  assert.equal((newResults.innerHTML.match(/data-system="/g)??[]).length,36);
  assert.equal(newRoot.scrolled,true);
});

test('observer rebind disconnects removed roots and ignores a stale callback',()=>{
  const x=fixture();
  x.handle.refreshLibraryObserver();
  const stale=x.observers[0],oldResults=x.elements['hybrid-library-results'];
  const newRoot={scrollIntoView(){}};
  const newResults={innerHTML:'new placeholder'};
  x.elements['architecture-library']=newRoot;
  x.elements['hybrid-library-results']=newResults;
  x.handle.refreshLibraryObserver();

  assert.equal(stale.disconnected,true);
  assert.equal(x.observers.length,2);
  stale.trigger(x.observers[0].targets[0],true);
  assert.equal(x.state.hybrid.libraryReady,false);
  assert.equal(newResults.innerHTML,'new placeholder');
  x.observers[1].trigger(newRoot,true);
  assert.equal(newResults.innerHTML.includes('data-system="hospital-island"'),true);
  assert.equal(oldResults.innerHTML,'deferred placeholder');
  x.handle.destroy();
  assert.equal(x.observers[1].disconnected,true);
});

test('browsers without IntersectionObserver render immediately after mount',()=>{
  const x=fixture({intersectionObserver:false});

  x.handle.refreshLibraryObserver();

  assert.equal(x.state.hybrid.libraryReady,true);
  assert.match(x.elements['hybrid-library-results'].innerHTML,/data-system="hospital-island"/);
});

test('hydrated card buttons remain disabled while busy and delegated selection is guarded',()=>{
  const x=fixture();
  x.state.hybrid.busy=true;
  const markup=x.hf.hybridLibrary(x.state.hybrid);
  assert.match(markup,/button type="button"[^>]*disabled[^>]*data-system="hospital-island"/);

  const button={dataset:{system:'solar-farm'},closest(selector){return selector==='button'?this:null;}};
  x.dispatch('click',button);

  assert.deepEqual(x.calls.navigations,[]);
});
