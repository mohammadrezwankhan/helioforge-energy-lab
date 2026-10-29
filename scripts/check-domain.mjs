import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {domainSecurityPolicy} from './domain-security.mjs';
import {buildModelRegistry,buildPublicCapabilityFacts,CAPABILITY_COPY,TASK_STARTS,validateCloudflareCopy,sourceEvidenceMismatches} from './capability-contract.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),outputRoot=process.env.CLOUDFLARE_OUTPUT_ROOT===undefined?path.join(root,'.cloudflare'):path.resolve(root,process.env.CLOUDFLARE_OUTPUT_ROOT),out=path.join(outputRoot,'site');
const site=JSON.parse(fs.readFileSync(path.join(root,'cloudflare-domain.json'),'utf8'));
const cloudflare=JSON.parse(fs.readFileSync(path.join(root,'cloudflare.json'),'utf8'));
validateCloudflareCopy(cloudflare);
const modelRegistry=buildModelRegistry(root),capabilityFacts=buildPublicCapabilityFacts(modelRegistry,{origin:new URL(site.canonical).origin});
const origin=new URL(site.canonical).origin,read=p=>fs.readFileSync(path.join(out,p),'utf8');
const files=[];function scan(dir){for(const ent of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(ent.isSymbolicLink(),false);const file=path.join(dir,ent.name);if(ent.isDirectory())scan(file);else{const rel=path.relative(out,file).replaceAll('\\','/');assert.ok(!/(^|\/)(\.git|\.env|node_modules|server|package(?:-lock)?\.json)(\/|$)/.test(rel),rel);assert.ok(!/\.(?:map|sqlite|db)$/.test(rel),rel);assert.ok(fs.statSync(file).size<=25*1024*1024);files.push(rel);}}}scan(out);
const indexablePages=[['index.html',site.canonical],['methodology/index.html',origin+'/methodology/'],['about/index.html',origin+'/about/'],['help/index.html',origin+'/help/'],['learning/index.html',origin+'/learning/'],['learning/terminal-balance/index.html',origin+'/learning/terminal-balance/'],['learning/model-glossary/index.html',origin+'/learning/model-glossary/'],['learning/capability-modes/index.html',origin+'/learning/capability-modes/'],['models/index.html',origin+'/models/']];
for(const [file,url] of indexablePages){
 const html=read(file);assert.equal((html.match(/<h1>/g)||[]).length,1);assert.equal((html.match(/rel="canonical"/g)||[]).length,1);assert.ok(html.includes(`rel="canonical" href="${url}"`));assert.ok(html.includes('name="robots" content="index,follow'));assert.ok(html.includes('property="og:url" content="'+url+'"'));
 const description=html.match(/name="description" content="([^"]+)"/)[1];assert.ok(description.length>=70&&description.length<=170);
 const graph=JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1])['@graph'];assert.ok(graph.some(x=>x['@type']==='WebPage'&&x.url===url));
 for(const m of html.matchAll(/(?:href|src)="(\/[^"#?]*)"/g)){const ref=m[1].endsWith('/')?m[1]+'index.html':m[1];assert.ok(fs.existsSync(path.join(out,ref)),`${file}: missing ${ref}`);}
}
const overviewGraph=JSON.parse(read('index.html').match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1])['@graph'];
const appSchema=overviewGraph.find(entity=>entity['@type']==='SoftwareApplication');assert.ok(appSchema);for(const phrase of Object.values(CAPABILITY_COPY))assert.ok(appSchema.featureList.includes(phrase),'overview structured facts missing '+phrase);
const overview=read('index.html'),headers=read('_headers'),heroDirectory='assets/engineering-hero/v1';
const expectedPolicy=domainSecurityPolicy([...indexablePages.map(([file])=>file),'run/index.html'].map(read));
assert.ok(headers.includes(`/*\n  Content-Security-Policy: ${expectedPolicy}\n`),'Global CSP must match this exact release');
if(site.engineeringHero===true){
 assert.ok(overview.includes('<h1>Explore the system.<br>Understand its limits.</h1>'));
 assert.ok(overview.includes('href="/run/">Open HelioForge preview'));
 assert.ok(overview.includes('src="/preview.png"'));
 assert.ok(overview.includes('<khan-grid-hero site="mkgrid" mode="video"'));
 assert.ok(overview.includes('A short visual introduction to the engineering context sits alongside'));
 assert.ok(overview.includes('src="/assets/engineering-hero/v1/poster.png"'));
 assert.ok(overview.includes('/assets/engineering-hero/v1/integration/vanilla/host.css'));
 assert.ok(overview.includes('/assets/engineering-hero/v1/integration/vanilla/khan-grid-hero.js'));
 assert.ok(read('domain.css').includes('.engineering-hero{display:grid;'));
 for(const file of ['index.html','release-media.json','hero-1080p60.mp4','poster.png','csp.json','integration/vanilla/host.css','integration/vanilla/khan-grid-hero.js'])assert.ok(files.includes(heroDirectory+'/'+file),`missing published engineering media ${file}`);
 const policy=JSON.parse(read(heroDirectory+'/csp.json')).suggestedContentSecurityPolicy;
 for(const route of ['/assets/engineering-hero/v1/index.html','/assets/engineering-hero/v1/']){
  const start=headers.indexOf(route+'\n');
  assert.notEqual(start,-1,`missing scoped frame route ${route}`);
  const nextRoute=headers.indexOf('\n/assets/engineering-hero/v1/',start+route.length);
  const block=headers.slice(start,nextRoute<0?headers.length:nextRoute);
  assert.ok(block.includes('\n  ! Content-Security-Policy\n'));
  assert.ok(block.includes('\n  Content-Security-Policy: '+policy+'\n'));
  assert.ok(block.includes('\n  ! X-Frame-Options\n'));
 }
 const globalHeaders=headers.slice(0,headers.indexOf('/assets/engineering-hero/v1/index.html'));
 assert.ok(globalHeaders.includes('X-Frame-Options: DENY'));
 assert.ok(globalHeaders.includes('Content-Security-Policy: '+expectedPolicy));
}else{
 assert.ok(!overview.includes('khan-grid-hero'));
 assert.ok(!overview.includes('/assets/engineering-hero/v1/'));
 assert.ok(!headers.includes('/assets/engineering-hero/v1/index.html'));
 assert.ok(!headers.includes('/assets/engineering-hero/v1/\n'));
 assert.ok(!files.some(file=>file.startsWith(heroDirectory+'/')));
}
const facts=JSON.parse(read('app.json')),runtime=read('run/index.html');assert.equal(facts.url,site.canonical);assert.equal(facts.applicationUrl,origin+'/run/');assert.equal(facts.runtimeSha256,createHash('sha256').update(runtime).digest('hex'));assert.match(runtime,/name="robots" content="noindex,follow"/);assert.ok(runtime.includes(`rel="canonical" href="${facts.applicationUrl}"`));assert.ok(!runtime.includes("location.protocol === 'file:'"));
assert.ok(!/<script\b[^>]*\bsrc=/i.test(runtime),'Hosted runtime must embed its compiled script');
assert.ok(!runtime.includes('location.protocol==="file:"'),'Hosted API mode patch must be applied');
const staleStudyEvidence=modelRegistry.studies.flatMap(study=>sourceEvidenceMismatches(study.acceptance.executionEvidence?.record,root).map(mismatch=>({study_id:study.id,...mismatch})));
if(staleStudyEvidence.length)throw new Error(`Refusing to compare/publish a model registry with stale source-bound study evidence: ${JSON.stringify(staleStudyEvidence)}. Refresh the bounded acceptance record and regenerate its registry artifact; do not treat a stale PASS as current.`);
assert.deepEqual(facts.capabilityContract,capabilityFacts);assert.equal(facts.helpUrl,origin+'/help/');assert.equal(facts.modelRegistryUrl,origin+'/models/');assert.equal(facts.capabilitiesUrl,origin+'/learning/capability-modes/');assert.equal(facts.capabilities.workspaceCount,12);assert.equal(facts.capabilities.studyCount,59);
assert.deepEqual(facts.capabilityContract.modes.map(mode=>mode.description),Object.values(CAPABILITY_COPY));
assert.ok(facts.sourceTreeDirty===null||typeof facts.sourceTreeDirty==='boolean');assert.equal(typeof facts.sourceIdentityStatus,'string');
assert.deepEqual(JSON.parse(read('models/registry.json')),JSON.parse(fs.readFileSync(path.join(root,'docs/MODEL_REGISTRY.json'),'utf8')));
for(const modeCopy of Object.values(CAPABILITY_COPY)){
 for(const file of ['index.html','about/index.html','methodology/index.html','help/index.html'])assert.ok(read(file).includes(modeCopy),`${file}: shared capability copy mismatch`);
 assert.ok(read('app.json').includes(modeCopy),`app.json: missing shared capability copy`);
 assert.ok(fs.readFileSync(path.join(root,'README.md'),'utf8').includes(modeCopy),`README.md: missing shared capability copy`);
}
for(const start of TASK_STARTS){
 for(const file of ['index.html','help/index.html'])assert.ok(read(file).includes(start.label)&&read(file).includes(start.description),`${file}: missing task-led start ${start.id}`);
 const fact=facts.capabilityContract.taskStarts.find(item=>item.id===start.id);assert.ok(fact);assert.equal(fact.label,start.label);assert.equal(fact.description,start.description);
}
assert.equal(modelRegistry.workspaces.length,12);assert.equal(modelRegistry.studies.length,59);assert.equal(modelRegistry.identities.catalogue.studies.declaredVersion,null);assert.equal(modelRegistry.identities.schemas.studyResultVersion,null);
for(const study of modelRegistry.studies){
 assert.ok(fs.existsSync(path.join(root,study.acceptance.modelReferences.code)),study.id+': source link missing');
 for(const testFile of study.acceptance.modelReferences.tests)assert.ok(fs.existsSync(path.join(root,testFile)),study.id+': test link missing '+testFile);
 assert.equal(study.acceptance.fixture.handCheck.status,'SOFTWARE_ORACLE_PASS');assert.equal(study.acceptance.status,'SOFTWARE_CHECKS_PASS');assert.equal(study.acceptance.executionEvidence.sourceMatches,true);
}
const hybridBundle=JSON.parse(fs.readFileSync(path.join(root,'examples/hybrid-bundle.json'),'utf8'));
assert.equal(facts.bundledHybrid.cases,285);assert.equal(facts.bundledHybrid.version,hybridBundle.version);assert.equal(facts.bundledHybrid.datasetSha256,hybridBundle.dataset_sha256);
assert.equal((read('sitemap.xml').match(/<loc>/g)||[]).length,9);for(const [,url] of indexablePages)assert.ok(read('sitemap.xml').includes(`<loc>${url}</loc>`),`sitemap missing ${url}`);assert.ok(!read('sitemap.xml').includes('/run/'));assert.ok(read('robots.txt').includes(origin+'/sitemap.xml'));assert.ok(read('llms.txt').includes('59 study IDs across 12 workspaces'));assert.ok(read('_headers').includes(site.project+'.pages.dev/*'));
const personUrl='https://mrkhan.co.technology/#person',profileUrl='https://mrkhan.co.technology/';
const findPeople=value=>{
 const found=[];
 const visit=node=>{
  if(Array.isArray(node)){node.forEach(visit);return;}
  if(!node||typeof node!=='object')return;
  if(node['@type']==='Person')found.push(node);
  Object.values(node).forEach(visit);
 };
 visit(value);
 return found;
};
for(const [file] of indexablePages){
 const html=read(file);
 const schemaMarker='<script type="application/ld+json">';
 const schemaStart=html.indexOf(schemaMarker)+schemaMarker.length;
 const schemaEnd=html.indexOf('</script>',schemaStart);
 const graph=JSON.parse(html.slice(schemaStart,schemaEnd));
 const people=findPeople(graph);
 assert.ok(people.length>0,file+': expected a Person entity');
 for(const person of people){assert.equal(person['@id'],personUrl);assert.equal(person.url,profileUrl);}
 assert.ok(html.includes('<meta name="google-site-verification" content="wZk3bMiBHxDWxN4EmERLH9sBza2QlvsTaxbOSBncrvw">'));
}
assert.ok(read('index.html').includes('href="'+profileUrl+'">Mohammad Rezwan Khan</a>'));
assert.ok(read('about/index.html').includes('href="'+profileUrl+'">Mohammad Rezwan Khan’s profile</a>'));
assert.ok(read('methodology/index.html').includes('https://mktrade.co.business/methodology/'));
assert.ok(read('methodology/index.html').includes('separate synthetic wind-market model'));
const robots=read('robots.txt');
for(const bot of ['Googlebot','Bingbot','OAI-SearchBot','GPTBot','PerplexityBot','Claude-SearchBot'])assert.ok(robots.includes(['User-agent: '+bot,'Allow: /'].join(String.fromCharCode(10))));
const full=read('llms-full.txt');
for(const phrase of ['Explore the system.','Privacy and local state','Catalogue coverage','https://mktrade.co.business/methodology/','Check one synthetic noon balance by hand.','Use version words precisely.','One contract for each named study.'])assert.ok(full.includes(phrase),'llms-full.txt missing '+phrase);
assert.ok(read('llms.txt').includes('https://mrkhan.co.technology/'));
const tokenFile='d73dcd8fd6c59242d9d6f9998bf756f5.txt';
assert.ok(tokenFile.endsWith('.txt')); assert.match(tokenFile.slice(0,-4),/^[a-f0-9]{32}$/);
assert.match(read(tokenFile),/^[a-f0-9]{32}$/);
console.log(JSON.stringify({status:'passed',project:site.project,pages:indexablePages.length,workspaces:modelRegistry.workspaces.length,studies:modelRegistry.studies.length,files:files.length,runtimeSha256:facts.runtimeSha256}));
