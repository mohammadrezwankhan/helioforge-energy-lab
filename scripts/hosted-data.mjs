// The downloadable edition remains self-contained; hosted results load by exact content digest.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {inlineDashboard} from './inline-html.mjs';
const {transform}=createRequire(new URL('../apps/web/package.json',import.meta.url))('esbuild');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const prototypeSensitiveStudyIds=new Set([...Object.getOwnPropertyNames(Object.prototype),'prototype']);
export function generatedJSON(text,name){
  const marker=text.indexOf('export const '+name);if(marker<0)throw Error('Missing generated constant '+name);
  const start=text.indexOf('=',marker)+1;let depth=0,quoted=false,escaped=false,begun=false;
  for(let i=start;i<text.length;i++){
    const c=text[i];
    if(quoted){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;continue;}
    if(c==='"'){quoted=true;continue;}
    if(c==='{'||c==='['){depth++;begun=true;}
    if(c==='}'||c===']')depth--;
    if(begun&&depth===0)return JSON.parse(text.slice(start,i+1));
  }
  throw Error('Incomplete generated constant '+name);
}
export function planHostedData(catalogue,bundle,studies){
  const assets=new Map(),index={schema:'helioforge.hosted-data.v1',hybrid:{},workspaces:{},dataset_sha256:bundle.dataset_sha256};
  const add=value=>{const bytes=JSON.stringify(value),sha256=hash(bytes),file=`data/${sha256}.json`;assets.set(file,bytes);return {path:file,sha256,bytes:Buffer.byteLength(bytes)};};
  if(!Array.isArray(studies.catalogue)||!studies.results||typeof studies.results!=='object'||Array.isArray(studies.results))throw Error('Invalid study bundle.');
  const studyIds=new Set();
  for(const study of studies.catalogue){
    if(!study||typeof study!=='object'||typeof study.id!=='string'||!study.id||typeof study.page!=='string'||!study.page||typeof study.title!=='string'||!study.title)throw Error('Invalid study definition.');
    if(prototypeSensitiveStudyIds.has(study.id))throw Error('Prototype-sensitive study id '+study.id+'.');
    if(studyIds.has(study.id))throw Error('Duplicate study id '+study.id+'.');
    studyIds.add(study.id);
  }
  const resultIds=Object.keys(studies.results);
  if(resultIds.length!==studyIds.size||resultIds.some(id=>!studyIds.has(id)))throw Error('Study result set does not match the catalogue.');
  for(const id of studyIds){
    const result=studies.results[id];
    if(!result||typeof result!=='object'||result.study!==id)throw Error('Study result does not match '+id+'.');
  }
  for(const entry of bundle.cases)index.hybrid[`${entry.inputs.system_id}/${entry.inputs.scenario_id}`]=add(entry);
  for(const page of new Set(studies.catalogue.map(s=>s.page))){
    const catalogue=studies.catalogue.filter(s=>s.page===page);
    const results=Object.fromEntries(catalogue.map(s=>[s.id,studies.results[s.id]]));
    index.workspaces[page]=add({catalogue,results});
  }
  const bootstrapCatalogue=studies.catalogue.map(({id,page,title})=>({id,page,title}));
  return {index,assets,catalogue,bootstrapHybrid:{...bundle,cases:[bundle.cases[0]]},bootstrapStudies:{catalogue:bootstrapCatalogue,results:{}}};
}
export async function buildHostedEdition({root,parts,html,css,favicon}){
  const source=await fs.readFile(path.join(root,'apps/web/src/hybrid-data.ts'),'utf8'),studies=await fs.readFile(path.join(root,'apps/web/src/roadmap-data.ts'),'utf8');
  const plan=planHostedData(generatedJSON(source,'HYBRID_CATALOG'),generatedJSON(source,'HYBRID_BUNDLE'),generatedJSON(studies,'STUDY_BUNDLE'));
  const safe=value=>JSON.stringify(value).replace(/</g,'\\u003c');
  const js=parts.map(part=>{
    if(path.basename(part.file)==='hybrid-data.ts')return `var HF; (function(HF){HF.HYBRID_CATALOG=${safe(plan.catalogue)};HF.HYBRID_BUNDLE=${safe(plan.bootstrapHybrid)};HF.HYBRID_EXAMPLE=HF.HYBRID_BUNDLE.cases[0].result;})(HF||(HF={}));globalThis.__HF_DATA_INDEX__=${safe(plan.index)};`;
    if(path.basename(part.file)==='roadmap-data.ts')return `var HF; (function(HF){HF.STUDY_BUNDLE=${safe(plan.bootstrapStudies)};})(HF||(HF={}));`;
    return part.script;
  }).join('\n;\n');
  const compactJS=(await transform(js,{loader:'js',target:'es2022',minify:true,keepNames:true,legalComments:'inline'})).code;
  const compactCSS=(await transform(css,{loader:'css',minify:true,legalComments:'inline'})).code;
  const document=inlineDashboard(html,{css:compactCSS,js:compactJS,favicon});
  const output=path.join(root,'apps/web/dist/hosted');await fs.mkdir(path.join(output,'data'),{recursive:true});
  await fs.writeFile(path.join(output,'index.html'),document);
  // Content-addressed remnants are harmless but the deployment copies only the current manifest's assets.
  for(const [name,bytes] of plan.assets)await fs.writeFile(path.join(output,name),bytes);
  await fs.writeFile(path.join(output,'data-index.json'),JSON.stringify(plan.index,null,2)+'\n');
  console.log(JSON.stringify({hostedShellBytes:Buffer.byteLength(document),hybridCases:Object.keys(plan.index.hybrid).length,studyWorkspaces:Object.keys(plan.index.workspaces).length,dataAssets:plan.assets.size}));
  return plan;
}
