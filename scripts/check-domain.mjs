import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=path.join(root,'.cloudflare/site');
const site=JSON.parse(fs.readFileSync(path.join(root,'cloudflare-domain.json'),'utf8'));
const origin=new URL(site.canonical).origin,read=p=>fs.readFileSync(path.join(out,p),'utf8');
const files=[];function scan(dir){for(const ent of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(ent.isSymbolicLink(),false);const file=path.join(dir,ent.name);if(ent.isDirectory())scan(file);else{const rel=path.relative(out,file).replaceAll('\\','/');assert.ok(!/(^|\/)(\.git|\.env|node_modules|server|package(?:-lock)?\.json)(\/|$)/.test(rel),rel);assert.ok(!/\.(?:map|sqlite|db)$/.test(rel),rel);assert.ok(fs.statSync(file).size<=25*1024*1024);files.push(rel);}}}scan(out);
for(const [file,url] of [['index.html',site.canonical],['methodology/index.html',origin+'/methodology/'],['about/index.html',origin+'/about/']]){
 const html=read(file);assert.equal((html.match(/<h1>/g)||[]).length,1);assert.equal((html.match(/rel="canonical"/g)||[]).length,1);assert.ok(html.includes(`rel="canonical" href="${url}"`));assert.ok(html.includes('name="robots" content="index,follow'));assert.ok(html.includes('property="og:url" content="'+url+'"'));
 const description=html.match(/name="description" content="([^"]+)"/)[1];assert.ok(description.length>=70&&description.length<=170);
 const graph=JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1])['@graph'];assert.ok(graph.some(x=>x['@type']==='WebPage'&&x.url===url));
 for(const m of html.matchAll(/(?:href|src)="(\/[^"#?]*)"/g)){const ref=m[1].endsWith('/')?m[1]+'index.html':m[1];assert.ok(fs.existsSync(path.join(out,ref)),`${file}: missing ${ref}`);}
}
const facts=JSON.parse(read('app.json')),runtime=read('run/index.html');assert.equal(facts.url,site.canonical);assert.equal(facts.applicationUrl,origin+'/run/');assert.equal(facts.runtimeSha256,createHash('sha256').update(runtime).digest('hex'));assert.match(runtime,/name="robots" content="noindex,follow"/);assert.ok(runtime.includes(`rel="canonical" href="${site.canonical}"`));assert.ok(!runtime.includes("location.protocol === 'file:'"));
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
