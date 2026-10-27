import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {domainSecurityPolicy} from './domain-security.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),outputRoot=process.env.CLOUDFLARE_OUTPUT_ROOT===undefined?path.join(root,'.cloudflare'):path.resolve(root,process.env.CLOUDFLARE_OUTPUT_ROOT),out=path.join(outputRoot,'site');
const site=JSON.parse(fs.readFileSync(path.join(root,'cloudflare-domain.json'),'utf8'));
const origin=new URL(site.canonical).origin,read=p=>fs.readFileSync(path.join(out,p),'utf8');
const files=[];function scan(dir){for(const ent of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(ent.isSymbolicLink(),false);const file=path.join(dir,ent.name);if(ent.isDirectory())scan(file);else{const rel=path.relative(out,file).replaceAll('\\','/');assert.ok(!/(^|\/)(\.git|\.env|node_modules|server|package(?:-lock)?\.json)(\/|$)/.test(rel),rel);assert.ok(!/\.(?:map|sqlite|db)$/.test(rel),rel);assert.ok(fs.statSync(file).size<=25*1024*1024);files.push(rel);}}}scan(out);
for(const [file,url] of [['index.html',site.canonical],['methodology/index.html',origin+'/methodology/'],['about/index.html',origin+'/about/']]){
 const html=read(file);assert.equal((html.match(/<h1>/g)||[]).length,1);assert.equal((html.match(/rel="canonical"/g)||[]).length,1);assert.ok(html.includes(`rel="canonical" href="${url}"`));assert.ok(html.includes('name="robots" content="index,follow'));assert.ok(html.includes('property="og:url" content="'+url+'"'));
 const description=html.match(/name="description" content="([^"]+)"/)[1];assert.ok(description.length>=70&&description.length<=170);
 const graph=JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1])['@graph'];assert.ok(graph.some(x=>x['@type']==='WebPage'&&x.url===url));
 for(const m of html.matchAll(/(?:href|src)="(\/[^"#?]*)"/g)){const ref=m[1].endsWith('/')?m[1]+'index.html':m[1];assert.ok(fs.existsSync(path.join(out,ref)),`${file}: missing ${ref}`);}
}
const overview=read('index.html'),headers=read('_headers'),heroDirectory='assets/engineering-hero/v1';
const expectedPolicy=domainSecurityPolicy(['index.html','methodology/index.html','about/index.html','run/index.html'].map(read));
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
const hybridBundle=JSON.parse(fs.readFileSync(path.join(root,'examples/hybrid-bundle.json'),'utf8'));
assert.equal(facts.bundledHybrid.cases,285);assert.equal(facts.bundledHybrid.version,hybridBundle.version);assert.equal(facts.bundledHybrid.datasetSha256,hybridBundle.dataset_sha256);
assert.equal((read('sitemap.xml').match(/<loc>/g)||[]).length,3);assert.ok(!read('sitemap.xml').includes('/run/'));assert.ok(read('robots.txt').includes(origin+'/sitemap.xml'));assert.ok(read('llms.txt').includes('36 architectures'));assert.ok(read('_headers').includes(site.project+'.pages.dev/*'));
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
for(const file of ['index.html','methodology/index.html','about/index.html']){
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
for(const phrase of ['Explore the system.','Privacy and local state','Catalogue coverage','https://mktrade.co.business/methodology/'])assert.ok(full.includes(phrase),'llms-full.txt missing '+phrase);
assert.ok(read('llms.txt').includes('https://mrkhan.co.technology/'));
const tokenFile='d73dcd8fd6c59242d9d6f9998bf756f5.txt';
assert.ok(tokenFile.endsWith('.txt')); assert.match(tokenFile.slice(0,-4),/^[a-f0-9]{32}$/);
assert.match(read(tokenFile),/^[a-f0-9]{32}$/);
console.log(JSON.stringify({status:'passed',project:site.project,pages:3,files:files.length,runtimeSha256:facts.runtimeSha256}));
