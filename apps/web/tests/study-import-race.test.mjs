import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
test('a delayed study JSON file cannot replace a later numeric edit',async()=>{
  const events=new Map(),nodes=new Map();
  class Node{
    constructor(){this.dataset={};this.classList={toggle(){}};}
    closest(){return this;} hasAttribute(){return false;}
    append(n){nodes.set(n.id,n);} before(n){nodes.set(n.id,n);}
    querySelector(){return null;}
  }
  const document={getElementById:id=>nodes.get(id)??null,createElement:()=>new Node(),querySelector:()=>null,querySelectorAll:()=>[],
    addEventListener:(type,callback)=>{const list=events.get(type)??[];list.push(callback);events.set(type,list);}};
  const box=vm.createContext({URL,Intl,structuredClone,CSS:{escape:value=>value}});
  vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),box);
  box.document=document;
  const hf=box.HF;hf.studyVisual=()=>'';hf.bindStudyVisuals=()=>()=>{};
  for(const id of ['page-content','study-workbench','study-status','study-output'])nodes.set(id,new Node());
  const controller=hf.createStudyController(()=>({page:'storage',connected:false}));
  const fire=(type,target)=>{for(const callback of events.get(type)??[])callback({target,preventDefault(){}});};
  const select=new Node();select.dataset.studySelect='storage-annual';fire('click',select);
  let resolveFile;const file=new Node();file.dataset.studyFile='tariff';file.files=[{size:3,text:()=>new Promise(resolve=>{resolveFile=resolve;})}];
  fire('change',file);
  const edit=new Node();edit.name='battery_kwh';edit.value='123';fire('input',edit);
  resolveFile('[9]');await new Promise(resolve=>setImmediate(resolve));
  controller.refresh();
  assert.doesNotMatch(nodes.get('study-workbench').innerHTML,/>\[\s*9\s*\]</);
  assert.equal(nodes.get('study-output').hidden,true);
});
