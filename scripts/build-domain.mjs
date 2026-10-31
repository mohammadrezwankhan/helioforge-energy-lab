// Dedicated static publication. The collection export remains a separate output.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {addEngineeringHeroFramePolicy, insertEngineeringHeroSection, prepareEngineeringHero} from './engineering-hero.mjs';
import {domainSecurityPolicy} from './domain-security.mjs';
import {buildModelRegistry,buildPublicCapabilityFacts,CAPABILITY_COPY,CONTENT_REVISION_DATE,TASK_STARTS,WORKSPACES} from './capability-contract.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const config=JSON.parse(fs.readFileSync(path.join(root,'cloudflare.json'),'utf8'));
const site=JSON.parse(fs.readFileSync(path.join(root,'cloudflare-domain.json'),'utf8'));
const origin=new URL(site.canonical).origin;
if(site.canonical!==origin+'/'||!site.canonical.startsWith('https://'))throw Error('Expected an HTTPS apex canonical');
if(!/^[a-z0-9-]+$/.test(site.project))throw Error('Invalid Pages project');
const outputRootOverride=process.env.CLOUDFLARE_OUTPUT_ROOT;
const outputRoot=outputRootOverride===undefined?path.join(root,'.cloudflare'):path.resolve(root,outputRootOverride);
const freshOutput=outputRootOverride!==undefined;
const outputRelative=path.relative(path.join(root,'.cloudflare'),outputRoot);
if(outputRelative==='..'||outputRelative.startsWith('..'+path.sep)||path.isAbsolute(outputRelative))throw Error('CLOUDFLARE_OUTPUT_ROOT must stay beneath .cloudflare');
const out=path.join(outputRoot,'site'),appOut=path.join(outputRoot,'app');
if(!path.relative(root,out).startsWith('.cloudflare'+path.sep))throw Error('Unsafe output');
for(const dir of [path.dirname(outputRoot),outputRoot,out])if(fs.existsSync(dir)&&fs.lstatSync(dir).isSymbolicLink())throw Error('Symlink output');
if(freshOutput&&fs.existsSync(outputRoot))throw Error('CLOUDFLARE_OUTPUT_ROOT must be a fresh, nonexistent directory');
execFileSync(process.execPath,['scripts/build-cloudflare.mjs'],{cwd:root,stdio:'inherit',windowsHide:true});
if(freshOutput){if(fs.existsSync(out))throw Error('Fresh site output already exists');}
else fs.rmSync(out,{recursive:true,force:true});
fs.cpSync(appOut,out,{recursive:true});
const engineeringHero=prepareEngineeringHero({
 enabled:site.engineeringHero===true,
 sourceRoot:path.join(root,'assets','engineering-hero','v1'),
 siteOutput:out,
 siteId:site.engineeringHeroSite
});
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json=v=>JSON.stringify(v).replace(/</g,'\\u003c');
const sha=v=>createHash('sha256').update(v).digest('hex');
const write=(file,content)=>{fs.mkdirSync(path.dirname(path.join(out,file)),{recursive:true});fs.writeFileSync(path.join(out,file),content);};
const facts=JSON.parse(fs.readFileSync(path.join(out,'app.json'),'utf8'));
const modelRegistry=buildModelRegistry(root);
const capabilityFacts=buildPublicCapabilityFacts(modelRegistry,{origin});
let runtime=fs.readFileSync(path.join(out,'run/index.html'),'utf8');
if(runtime.split(config.canonical).length-1!==1)throw Error('Runtime canonical anchor changed');
runtime=runtime.replace(config.canonical,origin+'/run/');
write('run/index.html',runtime);
facts.version='2.0.0';facts.url=site.canonical;facts.applicationUrl=origin+'/run/';facts.runtimeSha256=sha(runtime);
facts.methodologyUrl=origin+'/methodology/';facts.authorUrl='https://mrkhan.co.technology/';
facts.capabilityContract=capabilityFacts;
facts.capabilities={architectures:36,lessons:36,localApiRunnableArchitectures:19,studyOnlyArchitectures:17,workspaceCount:modelRegistry.workspaces.length,studyCount:modelRegistry.studies.length,browserMode:'bundled synthetic examples plus a separate bounded browser Terminal',terminalModel:'terminal-greedy-hourly-v1',advancedStudyModel:'roadmap-screen-v1',externalProviderMode:'opt-in local only; provider execution not verified',contractVersion:'1.0.0'};
facts.helpUrl=origin+'/help/';facts.modelRegistryUrl=origin+'/models/';facts.capabilitiesUrl=origin+'/learning/capability-modes/';
const hybridBundle=JSON.parse(fs.readFileSync(path.join(root,'examples/hybrid-bundle.json'),'utf8'));
if(hybridBundle.schema!=='helioforge.hybrid-bundle.v1'||hybridBundle.cases.length!==285)throw Error('Regenerate the complete hybrid preset archive before publication');
facts.bundledHybrid={schema:hybridBundle.schema,version:hybridBundle.version,catalogueVersion:hybridBundle.catalogue_version,cases:hybridBundle.cases.length,datasetSha256:hybridBundle.dataset_sha256};
const offline=fs.readFileSync(path.join(root,config.demoArtifact));
write('downloads/HelioForge-Offline.html',offline);
facts.offlineEdition={url:origin+'/downloads/HelioForge-Offline.html',sha256:sha(offline),bytes:offline.length,scope:'Self-contained frozen examples and browser Terminal. Advanced edited studies require the local Python API.'};
write('app.json',JSON.stringify(facts,null,2)+'\n');
const author={'@type':'Person','@id':'https://mrkhan.co.technology/#person',name:'Mohammad Rezwan Khan',url:'https://mrkhan.co.technology/',sameAs:['https://github.com/mohammadrezwankhan']};
const nav=`<header class="masthead"><a class="wordmark" href="/">H<span>↗</span> HelioForge</a><nav aria-label="Main"><a href="/run/">Open app</a><a href="/models/">Model registry</a><a href="/learning/">Learning pages</a><a href="/help/">Help</a><a href="/methodology/">Methodology</a><a href="/about/">About</a></nav></header>`;
const footer=`<footer><a class="wordmark" href="/">HelioForge</a><p>Explore energy systems. Inspect their assumptions.</p><a href="/downloads/HelioForge-Offline.html" download>Download complete offline edition</a><a href="https://mklab.co.technology/">Explore MKLab apps →</a></footer>`;
const page=(url,title,description,content,extra=[])=>{
 const graph=[{'@type':'WebSite','@id':origin+'/#website',name:'HelioForge',url:site.canonical,publisher:author,inLanguage:'en'},author,{'@type':'WebPage','@id':url+'#page',name:title,url,description,inLanguage:'en',dateModified:CONTENT_REVISION_DATE,isPartOf:{'@id':origin+'/#website'},author},...extra];
 return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><meta name="description" content="${esc(description)}"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="google-site-verification" content="wZk3bMiBHxDWxN4EmERLH9sBza2QlvsTaxbOSBncrvw"><meta name="author" content="Mohammad Rezwan Khan"><meta name="theme-color" content="#132923"><link rel="canonical" href="${url}"><link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/site.css"><link rel="stylesheet" href="/domain.css"><meta property="og:type" content="website"><meta property="og:site_name" content="HelioForge"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="${url}"><meta property="og:image" content="${origin}/social-preview.png"><meta property="og:image:alt" content="HelioForge hybrid-energy research preview"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${esc(title)}"><meta name="twitter:description" content="${esc(description)}"><meta name="twitter:image" content="${origin}/social-preview.png"><script type="application/ld+json">${json({'@context':'https://schema.org','@graph':graph})}</script></head><body><a class="skip" href="#main">Skip to content</a>${nav}<main id="main">${content}</main>${footer}</body></html>`;
};
const list=items=>items.map(item=>`<li>${esc(item)}</li>`).join('');
const starts=`<section class="content-grid task-starts" aria-labelledby="task-start-heading"><div><p class="eyebrow">START WITH A QUESTION</p><h2 id="task-start-heading">Choose what you need to do</h2><p>Each path opens a different delivery mode.</p></div><div class="steps">${TASK_STARTS.map(start=>`<article><h3><a href="${esc(start.href)}">${esc(start.label)} →</a></h3><p>${esc(start.description)}</p></article>`).join('')}</div></section>`;
const modeCopy=Object.values(CAPABILITY_COPY).map(text=>`<li>${esc(text)}</li>`).join('');
const home=`<section class="app-hero"><div><p class="eyebrow">HYBRID ENERGY / RESEARCH / LEARNING</p><h1>Explore the system.<br>Understand its limits.</h1><p class="lead">${esc(config.summary)}</p><div class="actions"><a class="button primary" href="/run/">Open HelioForge preview ↗</a><a href="/methodology/">Read the model boundaries</a></div><p class="micro">Free browser preview · No sign-in · Bundled synthetic examples</p></div><figure class="app-preview"><img src="/preview.png" alt="HelioForge’s actual hybrid-energy learning interface" width="1440" height="1000" fetchpriority="high"><figcaption>Actual interface. The Terminal calculates bounded cases in the browser; advanced study models use the separate local Python application.</figcaption></figure></section>${starts}<section class="content-grid"><div><p class="eyebrow">EXPLORE</p><h2>Follow the energy and the assumptions</h2><ul class="feature-list">${list(config.features)}</ul></div><div id="how-to-use"><p class="eyebrow">START HERE</p><h2>Try it in three steps</h2><ol class="steps">${list(config.steps)}</ol></div></section><section class="boundary"><div><p class="eyebrow">CAPABILITY &amp; LIMITS</p><h2>A research preview with a visible boundary</h2></div><div><p>The catalogue contains <strong>36 architectures</strong> and <strong>36 linked lessons</strong>. In the separate local Python application, 19 architectures have electricity-balance screens and 17 remain study-only. The 59 advanced study models are listed in the <a href="/models/">versioned model registry</a>.</p><ul class="capability-copy">${modeCopy}</ul><ul>${list(config.limitations)}</ul><p><a href="/methodology/">Read what is implemented and what remains a study →</a></p></div></section><section class="faq"><p class="eyebrow">COMMON QUESTIONS</p><h2>Before you explore</h2>${config.faqs.map(f=>`<details><summary>${esc(f.question)}</summary><p>${esc(f.answer)}</p></details>`).join('')}<details><summary>Does local progress transfer from MKLab?</summary><p>No. Browser storage belongs to the current origin and device. Local progress saved on another domain is not automatically transferred.</p></details></section><section class="release"><h2>Source, methods and evidence</h2><p>Maintained by <a href="https://mrkhan.co.technology/">Mohammad Rezwan Khan</a>. Updated <time datetime="${CONTENT_REVISION_DATE}">${CONTENT_REVISION_DATE}</time>.</p><p><a href="${config.publicSource}">Public source and verification</a> · <a href="/app.json">App facts</a> · <a href="/llms.txt">Plain-text guide</a> · <a href="/models/">Model registry</a> · <a href="/learning/">Learning pages</a></p><p class="micro">Base revision ${facts.sourceRevision.slice(0,12)} · Source tree ${facts.sourceTreeDirty===null?'unknown':facts.sourceTreeDirty?'dirty; local changes included':'clean'} · Browser runtime SHA-256 ${facts.runtimeSha256.slice(0,16)}</p></section>`;
const application={'@type':'SoftwareApplication','@id':origin+'/#app',name:'HelioForge',url:site.canonical,description:site.description,applicationCategory:'EducationalApplication',operatingSystem:'Web browser',isAccessibleForFree:true,author,featureList:[...config.features,...Object.values(CAPABILITY_COPY)],softwareHelp:{'@id':origin+'/help/#page'},sameAs:[config.publicSource]};
const overviewHome=insertEngineeringHeroSection(home,engineeringHero.section);
const overviewHtml=page(site.canonical,site.title,site.description,overviewHome,[application]);
write('index.html',engineeringHero.headMarkup?overviewHtml.replace('</head>',`${engineeringHero.headMarkup}</head>`):overviewHtml);
const methodology=`<article class="document"><p class="eyebrow">HELIOFORGE / METHODOLOGY</p><h1>Know what the model represents.</h1><p class="lead">Hybrid-energy learning activities and research screens with explicit capability boundaries.</p><h2>Hosted preview and local calculations</h2><ul class="capability-copy">${modeCopy}</ul><p>The <a href="${config.publicSource}/blob/main/START_HERE.md">local setup guide</a> explains how to run the separate research application on your own machine. See the <a href="/learning/capability-modes/">mode guide</a> and <a href="/models/">versioned model registry</a> for model-specific contracts.</p><h2>Catalogue coverage</h2><p>The source catalogue includes 36 architectures, 24 scenarios and 36 architecture-linked lessons. In the local application, 19 architectures have runnable electricity-balance screens and 17 advanced architectures are study-only. There are 20 numerical scenario presets and four dynamic/control study presets. A displayed architecture is not evidence that all of its specialized physics have been implemented. The study catalogue covers ${modelRegistry.studies.length} named experiments across ${modelRegistry.workspaces.length} workspaces.</p><p>Browse original system layouts, read assumptions and follow the lessons’ experiment prompts and self-check questions. The separate Terminal panel labels newly calculated reduced-model outcomes explicitly.</p><h2>Energy-model boundaries</h2><p>The hybrid hourly screen and the battery dispatch optimization are separate models. Their state-of-charge conditions, grid limits, units and energy-balance assumptions must be read in context. The <a href="${config.publicSource}/blob/main/docs/HYBRID_METHODOLOGY.md">hybrid methodology</a> and <a href="${config.publicSource}/blob/main/docs/METHODOLOGY.md">numerical methodology</a> are the detailed source references.</p><p>A demonstration day must not be multiplied into an annual business case without a reviewed annual model. A cheaper case that serves less demand is not automatically a better case. The interface’s geometry is explanatory; animated links are not solved electrical branch flows.</p><h2>Finance, forecasts and evidence</h2><p>Storage, project finance, PV, carbon and forecast examples are separate screening cases. No hidden automated revenue bridge connects them. Project and equity cash flows, nominal and real assumptions, and null or undefined metrics remain distinct. Synthetic examples are not calibrated forecasts, plant controls, investment recommendations or regulatory approvals.</p><h2>AI and review roles</h2><p>The public preview makes no external AI calls. The local application’s deterministic review mode is a checklist, not independently executed agents. Its optional external adapter requires explicit configuration and consent; it is not part of this hosted website.</p><h2>Separate synthetic wind-market model</h2><p><a href="https://mktrade.co.business/methodology/">MKTrade methodology</a> documents a separate synthetic wind-market model. Its illustrative market assumptions and results belong to a different project; they do not feed HelioForge’s bundled examples or models.</p><h2>Verification and reproducibility</h2><p>Read the <a href="${config.publicSource}/blob/main/QUALITY_REPORT.md">quality report</a> and <a href="${config.publicSource}/blob/main/docs/champion/VERIFICATION.md">release verification</a>, and inspect <a href="${config.publicSource}/actions">CI runs</a>. The website’s source revision and runtime SHA-256 are in <a href="/app.json">app.json</a>. Software checks do not establish independent scientific calibration or operational approval.</p><p><a class="button primary" href="/run/">Explore the preview ↗</a></p></article>`;
write('methodology/index.html',page(origin+'/methodology/','HelioForge Methodology | Model Coverage & Research Limits','Understand HelioForge’s architecture coverage, bundled preview, local Python models, evidence boundaries and energy-research limitations.',methodology));
const about=`<article class="document"><p class="eyebrow">HELIOFORGE / ABOUT</p><h1>Energy research you can inspect.</h1><p class="lead">HelioForge Energy Lab is maintained by Mohammad Rezwan Khan as a hybrid-energy research and learning workbench.</p><h2>Author and public source</h2><p><a href="https://mrkhan.co.technology/">Mohammad Rezwan Khan’s profile</a> identifies the maintainer. The <a href="${config.publicSource}">public repository</a> contains source, numerical methodology, lessons, validation records and contribution guidance. First-party source is available under the MIT license; bundled material retains its applicable notices.</p><h2>Delivery modes</h2><ul class="capability-copy">${modeCopy}</ul><p>Open the <a href="/help/">Help and getting-started page</a>, the <a href="/models/">model registry</a>, or the <a href="/learning/">source-linked learning guides</a> for more detail.</p><h2>Privacy and local state</h2><p>Supported browser progress remains local to this origin and device. The application has no external analytics scripts. The public static preview does not call an external provider. Cloudflare delivers the website and processes normal web requests. Browser saves from MKLab or another domain do not automatically transfer here. Export supported local records before clearing browser storage.</p><h2>Questions and corrections</h2><p>Follow the repository’s <a href="${config.publicSource}/blob/main/SUPPORT.md">support guide</a> for questions and <a href="${config.publicSource}/blob/main/SECURITY.md">security reporting instructions</a> for vulnerabilities. The <a href="/methodology/">methodology page</a> explains the scope of the hosted preview.</p><p>Explore the wider <a href="https://mklab.co.technology/">MKLab browser collection</a> or the separate <a href="https://khanlab.co.technology/">Datacenter Twin Lab course</a>.</p></article>`;
write('about/index.html',page(origin+'/about/','About HelioForge Energy Lab | Author, Source & Privacy','Learn who maintains HelioForge Energy Lab, where its source and methods live, and how the free MKGrid browser preview handles local progress.',about));
const help=`<article class="document"><p class="eyebrow">HELIOFORGE / HELP</p><h1>Choose a useful first step.</h1><p class="lead">Pick a task, then follow the model and evidence links attached to the result.</p><p class="learning-byline">Capability contract ${capabilityFacts.contractVersion} · Revised ${capabilityFacts.revisionDate} · Maintained by Mohammad Rezwan Khan.</p><h2>Start with one of these tasks</h2><ol class="task-starts">${TASK_STARTS.map(start=>`<li><h3><a href="${esc(start.href)}">${esc(start.label)} →</a></h3><p>${esc(start.description)}</p></li>`).join('')}</ol><h2>What each mode provides</h2><ul class="capability-copy">${modeCopy}</ul><h2>Where to find model details</h2><p>The <a href="/models/">model registry</a> links all ${modelRegistry.studies.length} study IDs across ${modelRegistry.workspaces.length} workspaces to their Python code, test files, declared inputs, units, equations, bundled defaults and limits. The <a href="/learning/">learning pages</a> include an arithmetic example and glossary.</p><p>For command-line installation use <a href="${config.publicSource}/blob/main/START_HERE.md">START_HERE.md</a>. For setup and provider requirements use <a href="${config.publicSource}/blob/main/docs/roadmap/CONNECTORS.md">the connector guide</a>. This page does not claim live provider execution or scientific validation.</p></article>`;
write('help/index.html',page(origin+'/help/','HelioForge Help | Choose a Calculation Mode','Start with a bundled example, bounded browser Terminal calculation, advanced local Python study, or a separate opt-in provider.',help));

const contentPage=(file,title,description,route)=>{
 const content=fs.readFileSync(path.join(root,'docs/learning-pages',file),'utf8');
 return page(origin+route,title,description,content);
};
write('learning/index.html',contentPage('index.html','HelioForge Learning Guides | Model and Evidence','Source-linked lessons for following one energy model result, reading the model registry and choosing a calculation mode.','/learning/'));
write('learning/terminal-balance/index.html',contentPage('terminal-balance.html','Worked Example | One Terminal Energy Balance','Hand-check one synthetic Terminal hour using the documented load shape, PV shape, export limit and bus balance.','/learning/terminal-balance/'));
write('learning/model-glossary/index.html',contentPage('glossary.html','HelioForge Model and Evidence Glossary','Definitions for application versions, catalogues, datasets, model versions, schemas, fixtures, evidence digests and validation tiers.','/learning/model-glossary/'));
write('learning/capability-modes/index.html',contentPage('capability-modes.html','HelioForge Capability Guide | Four Delivery Modes','Compare bundled synthetic examples, browser Terminal, advanced local Python, and opt-in external-provider delivery.','/learning/capability-modes/'));

const repoFile=file=>config.publicSource+'/blob/main/'+file;
const modelCard=study=>{
 const fields=study.acceptance.schema.numericFields.map(field=>`<tr><th scope="row">${esc(field.field)}</th><td>${esc(field.unit||'U')}</td><td>${esc(field.minimum)}</td><td>${esc(field.maximum)}</td><td>Default ${esc(study.inputs.numericFields.find(item=>item.name===field.field)?.default)}</td></tr>`).join('');
 const dataFields=study.acceptance.schema.jsonDataFields.map(field=>`<li><code>${esc(field.name)}</code> — ${esc(field.label)}; JSON ${esc(field.default.type)}, units U; default SHA-256 ${esc(field.default.sha256||'not available')}.</li>`).join('');
 const equations=study.model.equations.map(equation=>`<li><code>${esc(equation)}</code></li>`).join('');
 const limitations=study.model.limitations.map(limit=>`<li>${esc(limit)}</li>`).join('');
 const sources=study.model.sources.map(source=>`<li><a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.title)}</a></li>`).join('');
 const tests=study.acceptance.modelReferences.tests.map(file=>`<a href="${esc(repoFile(file))}">${esc(path.basename(file))}</a>`).join(' · ');
 return `<article class="model-card" id="study-${esc(study.id)}"><p class="eyebrow">${esc(study.workspace.name)} / ${esc(study.workspace.id)}</p><h3><code>${esc(study.id)}</code> · ${esc(study.title)}</h3><p>${esc(study.summary)}</p><p>Delivery: public preview = bundled example; new calculation = local Python. Model version: <code>${esc(study.model.version)}</code>. <a href="/run/${esc(study.workspace.appRoute)}">Open workspace</a> · <a href="#workspace-${esc(study.workspace.id)}">Workspace card</a>.</p><details><summary>Input schema, units and bounds (${study.acceptance.schema.numericFields.length} numeric; ${study.acceptance.schema.jsonDataFields.length} JSON)</summary><div class="table-scroll"><table><thead><tr><th>Field</th><th>Unit</th><th>Minimum</th><th>Maximum</th><th>Default</th></tr></thead><tbody>${fields||'<tr><td colspan="5">No scalar numeric fields declared; inspect JSON fields and the linked input model.</td></tr>'}</tbody></table></div>${dataFields?`<ul>${dataFields}</ul>`:''}<p>Study result schema version: <strong>U</strong>. Units not declared by the catalogue remain U; consult the linked model source for full Pydantic validation.</p></details><details><summary>Equations, references and limits</summary><h4>Declared equations</h4><ul>${equations}</ul><h4>Model limits</h4><ul>${limitations}</ul><h4>References</h4><ul>${sources||'<li>No source references declared in this catalogue entry.</li>'}</ul></details><details><summary>Fixture and per-study acceptance card</summary><p>Bundled default input/output fixture: <code>${esc(study.fixture.dataKind)}</code>. Input digest <code>${esc(study.fixture.inputSha256)}</code>; result evidence digest <code>${esc(study.fixture.evidenceSha256)}</code>. Both identify content; neither establishes validity.</p><ul><li>Hand-checkable independent reference: <strong>NOT RUN</strong>.</li><li>Invalid boundaries and additional cross-field restrictions: <strong>NOT RUN in this documentation change</strong>.</li><li>Seed/determinism and solver feasibility/convergence acceptance: <strong>NOT RUN in this documentation change</strong>.</li><li>JSON, CSV and memorandum export path: <strong>NOT RUN in this documentation change</strong>.</li></ul><p>Implementation: <a href="${esc(repoFile(study.acceptance.modelReferences.code))}">${esc(path.basename(study.acceptance.modelReferences.code))}</a>. Tests: ${tests}. <a href="${esc(repoFile(study.acceptance.sharedContract))}">Shared study result contract</a>.</p></details></article>`;
};
const workspaceCards=modelRegistry.workspaces.map(workspace=>`<section class="workspace-card" id="workspace-${esc(workspace.id)}"><h2>${esc(workspace.name)} <code>${esc(workspace.id)}</code></h2><p>Local app route <code>${esc(workspace.appRoute)}</code> · ${workspace.studies.length} registered study ID(s) · new study calculations use the separate local Python application.</p><ul>${workspace.studies.map(id=>{const study=modelRegistry.studies.find(item=>item.id===id);return `<li><a href="#study-${esc(id)}"><code>${esc(id)}</code> — ${esc(study.title)}</a> · model <code>${esc(study.model.version)}</code></li>`;}).join('')}</ul></section>`).join('');
const registryCards=modelRegistry.studies.map(modelCard).join('');
const modelRegistryPage=`<article class="document model-registry"><p class="eyebrow">MODEL REGISTRY / ${modelRegistry.registryVersion}</p><h1>One contract for each named study.</h1><p class="lead">Browse all ${modelRegistry.studies.length} current study IDs by workspace. Each card shows its model version, input names and declared bounds/units, equations, fixture digest, source, test file and limits.</p><p class="learning-byline">Registry revision ${CONTENT_REVISION_DATE} · Catalogue SHA-256 <code>${modelRegistry.identities.catalogue.studies.sha256}</code>. Independent validation and deployment are not asserted.</p><h2>How to read this registry</h2><p>The application, catalogue, sample data and numerical model have separate identities. No semantic study-catalogue version or separate study-result schema_version is declared by this source; both are marked U where appropriate. The default result is generated example evidence, not an independent reference fixture.</p><p><a href="/models/registry.json">Download machine-readable registry JSON</a> · <a href="/learning/model-glossary/">Read the model/evidence glossary</a> · <a href="/learning/capability-modes/">Compare delivery modes</a>.</p>${workspaceCards}<h2>Per-study cards</h2>${registryCards}<p>Source snapshot: <a href="${esc(repoFile('docs/MODEL_REGISTRY.md'))}">human-readable registry</a> · <a href="${esc(repoFile('docs/MODEL_REGISTRY.json'))}">machine-readable registry</a> · <a href="${esc(repoFile('docs/roadmap/VERIFICATION.md'))}">historical software verification record</a>. Historical verification does not prove that this page’s app deployment is current.</p></article>`;
write('models/index.html',page(origin+'/models/','HelioForge Model Registry | 59 Studies in 12 Workspaces','Source-linked registry for each HelioForge study: equations, schemas, units, fixtures, software tests and explicit model limits.',modelRegistryPage));
write('models/registry.json',JSON.stringify(modelRegistry,null,2)+'\n');
write('domain.css','.document{max-width:860px;padding:64px 0 72px}.document h1{font-size:clamp(40px,6vw,68px)}.document h2{font-size:30px;margin-top:40px}.document p{max-width:75ch}.masthead nav{flex-wrap:wrap}.masthead .wordmark{white-space:normal}@media(max-width:700px){.document{padding-top:36px}.masthead{flex-wrap:wrap}.masthead nav{justify-content:flex-start}.app-hero h1{font-size:43px}}\n');
fs.appendFileSync(path.join(out,'domain.css'),'.learning-byline{font-size:.9rem;color:var(--muted,#56665e)}.learning-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:16px}.learning-cards article,.model-card,.workspace-card{min-width:0;padding:18px;border:1px solid var(--line,#cad2ca);border-radius:12px}.learning-cards h3{margin-top:0}.task-starts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:18px}.capability-copy{padding-left:1.3rem}.model-card{margin:22px 0;scroll-margin-top:20px}.workspace-card{margin:28px 0;scroll-margin-top:20px}.model-card code,.model-registry code{overflow-wrap:anywhere}.model-card details{margin:12px 0;padding:10px 0;border-top:1px solid var(--line,#cad2ca)}.model-card summary{cursor:pointer;font-weight:650}.model-card h4{margin-bottom:6px}.table-scroll{overflow-x:auto;max-width:100%}.table-scroll table{min-width:620px;border-collapse:collapse}.table-scroll th,.table-scroll td{padding:8px;text-align:left;border-bottom:1px solid var(--line,#cad2ca)}.model-registry .lead{max-width:78ch}\n');
if(engineeringHero.enabled)fs.appendFileSync(path.join(out,'domain.css'),'.engineering-hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:44px;align-items:center;padding:54px 0 60px;border-top:1px solid var(--line)}.engineering-hero>div,.engineering-hero khan-grid-hero{min-width:0}.engineering-hero h2{margin:0 0 18px}.engineering-hero .lead{margin:0}.engineering-hero khan-grid-hero{width:100%}@media(max-width:700px){.engineering-hero{grid-template-columns:1fr;gap:22px;padding:35px 0 42px}}');
write('favicon.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#132923"/><path d="M17 16h8v12h14V16h8v32h-8V36H25v12h-8z" fill="#c9ee8b"/></svg>');
write('robots.txt',[
'User-agent: *',
'Allow: /',
'',
'Sitemap: '+origin+'/sitemap.xml',
'',
'# Explicit public crawler permissions. A crawl rule does not grant reuse rights.',
'User-agent: Googlebot','Allow: /','',
'User-agent: Bingbot','Allow: /','',
'User-agent: OAI-SearchBot','Allow: /','',
'User-agent: GPTBot','Allow: /','',
'User-agent: PerplexityBot','Allow: /','',
'User-agent: Claude-SearchBot','Allow: /',''
].join('\n'));

const publicRoutes=['/','/methodology/','/about/','/help/','/learning/','/learning/terminal-balance/','/learning/model-glossary/','/learning/capability-modes/','/models/'];
write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+publicRoutes.map(route=>`<url><loc>${origin+route}</loc><lastmod>${CONTENT_REVISION_DATE}</lastmod></url>`).join('')+'</urlset>\n');
const decodeEntities=value=>value.replace(/&#x([a-f0-9]+);/gi,(_,code)=>String.fromCodePoint(parseInt(code,16))).replace(/&#(\d+);/g,(_,code)=>String.fromCodePoint(Number(code))).replace(/&nbsp;/gi,' ').replace(/&amp;/gi,'&').replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&quot;/gi,'"').replace(/&#39;|&apos;/gi,"'");
const staticPageText=(file,route)=>{
 const html=fs.readFileSync(path.join(out,file),'utf8');
 const main=html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i);
 if(!main)throw Error('Static text page has no main element: '+file);
 return decodeEntities(main[1]
  .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,' ')
  .replace(/<a\b[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi,(_,href,label)=>{
   const text=decodeEntities(label.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim());
   return text?text+' ('+new URL(href,origin+route).href+') ':'';
  })
  .replace(/<img\b[^>]*\balt="([^"]*)"[^>]*>/gi,(_,alt)=>alt+'\n')
  .replace(/<(?:h[1-6]|p|li|summary|figcaption|section|article|div|br|hr|ol|ul)\b[^>]*>/gi,'\n')
  .replace(/<\/(?:h[1-6]|p|li|summary|figcaption|section|article|div|br|hr|ol|ul)\s*>/gi,'\n')
  .replace(/<[^>]+>/g,' ')
  .replace(/[ \t\f\v]+/g,' ')
  .replace(/ *\n */g,'\n')
  .replace(/\n{3,}/g,'\n\n')
  .trim());
};
const publicTextPages=[
 ['Overview','index.html','/'],['About','about/index.html','/about/'],['Methodology','methodology/index.html','/methodology/'],['Help','help/index.html','/help/'],
 ['Learning guides','learning/index.html','/learning/'],['Terminal worked example','learning/terminal-balance/index.html','/learning/terminal-balance/'],
 ['Model glossary','learning/model-glossary/index.html','/learning/model-glossary/'],['Capability modes','learning/capability-modes/index.html','/learning/capability-modes/'],['Model registry','models/index.html','/models/'],
];
write('llms.txt',[
 '# HelioForge Energy Lab','',
 'A free hybrid-energy research and learning preview maintained by Mohammad Rezwan Khan. The capability modes, task starts and model identities below are shared with the public app facts.','',
 '- [Overview]('+origin+'/)',
 '- [Browser preview]('+origin+'/run/)',
 '- [Methodology and model limits]('+origin+'/methodology/)',
 '- [Author, source and privacy]('+origin+'/about/)',
 '- [Help and task-led starts]('+origin+'/help/)',
 '- [Learning guides]('+origin+'/learning/)',
 '- [Model registry]('+origin+'/models/)',
 '- [Maintainer profile](https://mrkhan.co.technology/)',
 '- [Full static page text]('+origin+'/llms-full.txt)',
 '- [Machine-readable app facts]('+origin+'/app.json)',
 '- [Public source]('+config.publicSource+')','',
 '## Scope',
 ...Object.values(CAPABILITY_COPY),'',
 `The source registry currently lists ${modelRegistry.studies.length} study IDs across ${modelRegistry.workspaces.length} workspaces.`, '',
 ...TASK_STARTS.map(start=>`${start.label}: ${start.description} ${start.href}`),'',
 '## Boundaries',
 'Educational research examples, not calibrated forecasts, plant controls, investment advice or operational approval. Browser storage is origin-specific and does not automatically transfer from another domain.','',
 '## Separate project',
 '[MKTrade methodology](https://mktrade.co.business/methodology/) describes a separate synthetic wind-market model. It is not a HelioForge model or validation source.','',
 'This optional text supplements the visible pages; it does not guarantee search rankings or AI citations.',''
].join('\n'));
write('llms-full.txt',[
 '# HelioForge Energy Lab — full static page text','',
 'Generated from the visible main content of the nine indexable static HTML pages during this build. Interactive app states and external source repositories are not included. These are published site claims, not independent certification.','',
 ...publicTextPages.map(([label,file,route])=>['## '+label,'','Source: '+origin+route,'',staticPageText(file,route)].join('\n')),''
].join('\n'));

const indexNowFile='d73dcd8fd6c59242d9d6f9998bf756f5.txt';
const indexNowToken=fs.readFileSync(path.join(root,'static',indexNowFile),'utf8');
if(!/^[a-f0-9]{32}$/.test(indexNowToken))throw Error('Invalid IndexNow verification token');
write(indexNowFile,indexNowToken);
write('404.html',`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex"><title>Page not found | HelioForge</title><h1>Page not found</h1><p><a href="/">Return to HelioForge</a></p></html>`);
const securityPolicy=domainSecurityPolicy(['index.html','methodology/index.html','about/index.html','help/index.html','learning/index.html','learning/terminal-balance/index.html','learning/model-glossary/index.html','learning/capability-modes/index.html','models/index.html','run/index.html'].map(file=>fs.readFileSync(path.join(out,file),'utf8')));
write('_headers',addEngineeringHeroFramePolicy(`/*\n  Content-Security-Policy: ${securityPolicy}\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n/run/*\n  X-Robots-Tag: noindex, follow\n/run/data/*\n  Cache-Control: public, max-age=31536000, immutable\n/downloads/*\n  Content-Disposition: attachment\n  X-Robots-Tag: noindex, nofollow\nhttps://${site.project}.pages.dev/*\n  X-Robots-Tag: noindex, follow\nhttps://:preview.${site.project}.pages.dev/*\n  X-Robots-Tag: noindex, follow\n`,engineeringHero.contentSecurityPolicy));
write('_redirects','# Domain aliases use Cloudflare zone Redirect Rules.\n/index.html / 301\n/run /run/ 301\n/methodology /methodology/ 301\n/about /about/ 301\n/help /help/ 301\n/learning /learning/ 301\n/models /models/ 301\n/apps/helioforge-energy-lab/ / 301\n/apps/helioforge-energy-lab/run/ /run/ 301\n');
console.log(JSON.stringify({project:site.project,output:out,canonical:site.canonical,sourceRevision:facts.sourceRevision,runtimeSha256:facts.runtimeSha256}));
