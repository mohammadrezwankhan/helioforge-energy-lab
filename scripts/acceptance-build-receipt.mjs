// Exact release bytes and source state; a build receipt is not deployment proof.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const site=path.join(process.env.CLOUDFLARE_OUTPUT_ROOT?path.resolve(root,process.env.CLOUDFLARE_OUTPUT_ROOT):path.join(root,'.cloudflare'),'site');
const sha=data=>createHash('sha256').update(data).digest('hex');
const git=(...args)=>execFileSync('git',args,{cwd:root,encoding:'utf8',windowsHide:true}).trim();
const facts=JSON.parse(fs.readFileSync(path.join(site,'app.json'),'utf8'));
const runtime=fs.readFileSync(path.join(site,'run/index.html'));
if(sha(runtime)!==facts.runtimeSha256)throw Error('Manifest/runtime mismatch; receipt refused');
const fileNames=[];
function inventory(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const file=path.join(dir,entry.name);if(entry.isSymbolicLink())throw Error('Symlink distribution refused');if(entry.isDirectory())inventory(file);else fileNames.push(path.relative(site,file).replaceAll('\\','/'));}}
inventory(site);fileNames.sort();
const files=fileNames.map(name=>{const bytes=fs.readFileSync(path.join(site,name));return {path:name,bytes:bytes.length,sha256:sha(bytes)};});
const receipt={schema:'helioforge.build-receipt.v1',source_base_commit:git('rev-parse','HEAD'),
  working_tree_dirty:git('status','--porcelain','--untracked-files=normal')!=='',
  environment:process.env.GITHUB_ACTIONS==='true'?'CI':'local',created_at:new Date().toISOString(),
  hash_representation:'SHA-256 of exact file bytes; UTF-8 as generated, no newline normalization; HTTP content encodings are decoded before comparison.',
  runtime_sha256:sha(runtime),dataset:facts.bundledHybrid,capabilities:facts.capabilities,
  ci_run_id:process.env.GITHUB_RUN_ID??null,ci_attempt:process.env.GITHUB_RUN_ATTEMPT??null,
  deployment_id:null,deployment_status:'UNVERIFIED',test_status:'Consult attached execution reports; this receipt proves build byte identity only.',files};
const encoded=JSON.stringify(receipt,null,2)+'\n';
const dir=path.join(process.env.HELIOFORGE_EVIDENCE_DIR?path.resolve(root,process.env.HELIOFORGE_EVIDENCE_DIR):path.join(root,'docs/remediation-20261029'),'receipts');fs.mkdirSync(dir,{recursive:true});
const name=`build-${sha(encoded)}.json`;
fs.writeFileSync(path.join(dir,name),encoded,{flag:'wx'});
console.log(JSON.stringify({receipt:path.relative(root,path.join(dir,name)),runtime_sha256:receipt.runtime_sha256,environment:receipt.environment}));
