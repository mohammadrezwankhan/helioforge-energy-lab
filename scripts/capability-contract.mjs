import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export const CAPABILITY_CONTRACT_VERSION = '1.0.0';
export const CONTENT_REVISION_DATE = '2026-10-29';
export const APPLICATION_VERSION = '2.0.0';

export const CAPABILITY_COPY = Object.freeze({
  bundled: 'Bundled synthetic examples are precomputed outputs; the public browser edition does not calculate new study-model results from edited inputs.',
  terminal: 'The Terminal runs new deterministic, bounded 24-hour energy-balance cases in the browser; it uses a greedy policy and is not an optimizer.',
  python: 'The separate local Python application runs new calculations for the advanced study models and optimization.',
  external: 'Optional local external providers are separate, opt-in integrations; credentials and explicit consent are required where applicable. The public static preview makes no provider calls.',
});

export const TASK_STARTS = Object.freeze([
  {id:'examples', label:'Explore a bundled example', description:'Open the public preview and inspect a labeled synthetic result.', href:'/run/#hybrid', mode:'bundled'},
  {id:'terminal', label:'Calculate a bounded Terminal case', description:'Open Scenario compare and use the Parametric energy workbench.', href:'/run/#compare', mode:'terminal'},
  {id:'local-python', label:'Set up advanced local calculations', description:'Use the source setup guide to run the Python application on your machine.', href:'https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/main/START_HERE.md', mode:'python'},
]);

export const WORKSPACES = Object.freeze({
  hybrid:{name:'Hybrid systems lab',route:'#hybrid'},
  lessons:{name:'Learning studio',route:'#lessons'},
  compare:{name:'Scenario compare',route:'#compare'},
  overview:{name:'Command centre',route:'#overview'},
  storage:{name:'Storage & flexibility',route:'#storage'},
  pv:{name:'PV economics',route:'#pv'},
  research:{name:'Research pillars',route:'#research'},
  markets:{name:'Market intelligence',route:'#markets'},
  forecast:{name:'Forecast studio',route:'#forecast'},
  investment:{name:'Investment desk',route:'#investment'},
  pilots:{name:'Construction & pilots',route:'#pilots'},
  council:{name:'Agent council',route:'#council'},
});

export const MODELS = Object.freeze({
  terminal:{version:'terminal-greedy-hourly-v1',code:'apps/api/helioforge/engines/terminal.py',contract:'docs/terminal-audit/ANALYTICAL_MODEL.md'},
  hybrid:{version:'hybrid-greedy-hourly-v1',code:'apps/api/helioforge/engines/hybrid.py',contract:'docs/HYBRID_METHODOLOGY.md'},
  storage:{version:'btm-milp-v1',code:'apps/api/helioforge/engines/storage.py',contract:'docs/METHODOLOGY.md'},
  studies:{version:'roadmap-screen-v1',code:'apps/api/helioforge/studies.py',contract:'docs/roadmap/CONTRACT.md'},
});

const stable = value => {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])]));
  return value;
};
const canonical = value => JSON.stringify(stable(value));
const digest = value => createHash('sha256').update(typeof value === 'string' ? value : canonical(value)).digest('hex');
const escapeRegExp = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function loadStudyBundle(repoRoot=root) {
  const source = fs.readFileSync(path.join(repoRoot, 'apps/web/src/roadmap-data.ts'), 'utf8');
  const marker = 'const STUDY_BUNDLE: StudyBundle = ';
  const start = source.indexOf(marker);
  if (start < 0) throw new Error('Generated Python study catalogue is missing from roadmap-data.ts');
  const jsonStart = start + marker.length;
  const end = source.indexOf('; }', jsonStart);
  if (end < 0) throw new Error('Generated Python study catalogue has an unexpected wrapper');
  return JSON.parse(source.slice(jsonStart, end));
}

function findStudySource(repoRoot, id) {
  const engines = path.join(repoRoot, 'apps/api/helioforge/engines');
  const files = fs.readdirSync(engines).filter(name => name.endsWith('_studies.py'));
  const escaped = escapeRegExp(id);
  const definition = new RegExp(`(?:\\b["']?id["']?\\s*[:=]\\s*["']${escaped}["']|\\b_entry\\(\\s*["']${escaped}["'])`);
  const matches = files.filter(name => definition.test(fs.readFileSync(path.join(engines, name), 'utf8')));
  if (matches.length !== 1) throw new Error(`Expected one Python study implementation for ${id}; found ${matches.join(', ') || 'none'}`);
  const module = matches[0];
  const testFile = `apps/api/tests/test_${module.replace(/_studies\.py$/, '_studies.py')}`;
  return {module:`apps/api/helioforge/engines/${module}`, tests:[testFile, 'apps/api/tests/test_studies_api.py']};
}

export function sourceEvidenceMismatches(evidence, repoRoot=root) {
  if (evidence===undefined||evidence===null) return [];
  const invalid=(reason,actual)=>[{file:null,expected:'non-empty source_hashes object with paired file/SHA-256 fields',actual,reason}];
  if (typeof evidence!=='object'||Array.isArray(evidence)) return invalid('evidence_record_not_object',typeof evidence);
  const sourceHashes=evidence.source_hashes;
  if (!sourceHashes||typeof sourceHashes!=='object'||Array.isArray(sourceHashes)) return invalid('source_hashes_not_object',sourceHashes??null);
  const entries=Object.entries(sourceHashes),fileEntries=entries.filter(([key])=>key.endsWith('_file'));
  if (!fileEntries.length) return invalid('no_source_file_bindings',Object.keys(sourceHashes));
  const hashKeys=new Set(entries.filter(([key])=>key.endsWith('_sha256')).map(([key])=>key));
  const fileKeys=new Set(fileEntries.map(([key])=>key.replace(/_file$/,'_sha256')));
  const unpaired=[...hashKeys].filter(key=>!fileKeys.has(key));
  const mismatches=unpaired.map(key=>({file:sourceHashes[key.replace(/_sha256$/,'_file')]??null,
    expected:sourceHashes[key]??null,actual:null,reason:'unpaired_file_or_hash_field'}));
  for (const [key,file] of fileEntries) {
    const expectedKey=key.replace(/_file$/,'_sha256'),expected=sourceHashes[expectedKey];
    if (typeof file!=='string'||!file.trim()) {
      mismatches.push({file:file??null,expected:expected??null,actual:null,reason:'source_file_path_missing_or_invalid'});
      continue;
    }
    if (typeof expected!=='string'||!/^[a-f0-9]{64}$/.test(expected)) {
      mismatches.push({file,expected:expected??null,actual:null,reason:'expected_sha256_missing_or_invalid'});
      continue;
    }
    const source=path.join(repoRoot,file);
    const actual=fs.existsSync(source)?createHash('sha256').update(fs.readFileSync(source)).digest('hex'):null;
    if (actual===null||actual!==expected) mismatches.push({file,expected,actual,reason:actual===null?'source_file_missing':'sha256_mismatch'});
  }
  return mismatches;
}

const summarizeDefault = value => {
  if (Array.isArray(value)) return {type:'array',items:value.length,itemTypes:[...new Set(value.map(item => item === null ? 'null' : Array.isArray(item) ? 'array' : typeof item))].sort(),sha256:digest(value)};
  if (value && typeof value === 'object') return {type:'object',keys:Object.keys(value).sort(),sha256:digest(value)};
  return {type:value === null ? 'null' : typeof value,value};
};

function acceptanceCard(study, example, code, repoRoot, evidence) {
  const numericBounds = (study.fields || []).map(field => ({field:field.name,unit:field.unit || null,minimum:field.min,maximum:field.max,boundSemantics:'U — catalogue bounds are recorded; consult the Pydantic field for inclusive/exclusive semantics.'}));
  const seedFields = [...(study.fields || []), ...(study.data_fields || [])].filter(field => /^(seed|random_seed)$/i.test(field.name)).map(field => field.name);
  const details = example.details && typeof example.details === 'object' ? example.details : {};
  const convergenceFacts = Object.fromEntries(Object.entries(details).filter(([key, value]) => /converg|feasib|solver_status|solverStatus|status/i.test(key) && ['string','boolean','number'].includes(typeof value)));
  const api = `apps/api/helioforge/engines/${path.basename(code.module)}`;
  const card={
    status:'NOT_RUN_IN_THIS_REMEDIATION',
    schema:{
      declaredVersion:null,
      versionStatus:'U — study result envelope has no separate schema_version in the current shared result contract.',
      numericFields:numericBounds,
      jsonDataFields:(study.data_fields || []).map(field => ({name:field.name,label:field.label,default:summarizeDefault(field.default),unit:null,unitStatus:'U — JSON data-field units are not declared in the catalogue metadata.'})),
      strictValidationReference:api,
    },
    fixture:{
      type:'bundled default-input example; generated by scripts/generate-studies.py from the Python study implementation',
      dataKind:example.data_kind,
      inputSha256:digest(example.inputs),
      evidenceSha256:example.evidence_sha256,
      inputReference:`apps/web/src/roadmap-data.ts — STUDY_BUNDLE.results["${study.id}"].inputs`,
      resultReference:`apps/web/src/roadmap-data.ts — STUDY_BUNDLE.results["${study.id}"]`,
      handCheck:{status:'NOT_RUN',note:'Bundled output is a reproducibility example, not an independent hand calculation or scientific reference.'},
    },
    invalidBoundary:{
      suggestedCases:numericBounds.length ? [
        `${numericBounds[0].field} below declared minimum ${numericBounds[0].minimum}`,
        `${numericBounds[0].field} above declared maximum ${numericBounds[0].maximum}`,
        'unknown input field and non-finite numeric input',
      ] : ['unknown input field, non-finite numeric input, and malformed/oversized JSON data'],
      sourceAndTests:code.tests.map(file => path.relative(repoRoot, path.join(repoRoot, file)).replaceAll('\\','/')),
      status:'NOT_RUN_IN_THIS_REMEDIATION',
      crossFieldConstraints:'Consult the linked Pydantic model and study-specific tests; not inferred from the catalogue bounds alone.',
    },
    deterministicOrSeeded:{
      contract:'docs/roadmap/CONTRACT.md states study runs must not use global random state; stochastic studies use a per-run seeded generator.',
      seedFields,
      status:'NOT_RERUN_IN_THIS_REMEDIATION',
    },
    feasibilityOrConvergence:{
      defaultExampleSignals:convergenceFacts,
      applicability:'Model-specific; the common result envelope does not require a solver-status field.',
      status:'NOT_RUN_IN_THIS_REMEDIATION',
    },
    export:{
      expected:['JSON inputs and full result','full result table CSV','selected series CSV','study memorandum'],
      implementation:'apps/web/src/roadmap.ts',
      status:'NOT_RUN_IN_THIS_REMEDIATION',
    },
    limitations:study.limitations || [],
    modelReferences:{code:code.module,tests:code.tests,sharedContract:'docs/roadmap/CONTRACT.md'},
  };
  if(evidence){
    const bound=sourceEvidenceMismatches(evidence,repoRoot).length===0;
    card.executionEvidence={reference:'docs/remediation-20261029/study-contracts.json',sourceMatches:bound,record:evidence};
    if(bound&&evidence.status==='PASS'){
      card.status='SOFTWARE_CHECKS_PASS';
      card.fixture.handCheck={status:'SOFTWARE_ORACLE_PASS',note:evidence.oracle.expected,testIds:evidence.test_ids,scope:'Independent arithmetic/invariant/software checks; scientific and field validation remain unestablished.'};
      card.invalidBoundary={...card.invalidBoundary,status:'PASS',executed:[evidence.checks.boundary_case,evidence.checks.invalid_input]};
      card.deterministicOrSeeded={...card.deterministicOrSeeded,...evidence.checks.repeatability};
      card.feasibilityOrConvergence={...card.feasibilityOrConvergence,...evidence.checks.solver_feasibility};
      card.export={...card.export,json:evidence.checks.json_export,status:'JSON_PASS; BROWSER_EXPORTS_SEPARATE'};
    } else card.status=bound?'SOFTWARE_CHECKS_FAILED':'STALE_SOURCE_EVIDENCE';
  }
  return card;
}

export function buildModelRegistry(repoRoot=root) {
  const bundle = loadStudyBundle(repoRoot);
  const evidencePath=path.join(repoRoot,'docs/remediation-20261029/study-contracts.json');
  // Registry wire JSON represents negative zero as zero; retain raw numerical evidence in its own artifact.
  const evidence=fs.existsSync(evidencePath)?JSON.parse(JSON.stringify(JSON.parse(fs.readFileSync(evidencePath,'utf8')).studies)):[];
  const ids = new Set();
  const studies = bundle.catalogue.map(definition => {
    if (ids.has(definition.id)) throw new Error(`Duplicate study id ${definition.id}`);
    ids.add(definition.id);
    const result = bundle.results[definition.id];
    if (!result || result.study !== definition.id || !result.model_version) throw new Error(`Missing generated result or model version for ${definition.id}`);
    const workspace = WORKSPACES[definition.page];
    if (!workspace) throw new Error(`Unknown workspace ${definition.page} for ${definition.id}`);
    const code = findStudySource(repoRoot, definition.id);
    const acceptance = acceptanceCard(definition, result, code, repoRoot,evidence.find(record=>record.study_id===definition.id));
    return {
      id:definition.id,
      title:definition.title,
      summary:definition.summary,
      workspace:{id:definition.page,name:workspace.name,appRoute:workspace.route},
      delivery:{publicBrowser:'bundled synthetic example only',newCalculations:'separate local Python application',boundedTerminal:false},
      model:{version:result.model_version,kind:definition.kind || null,equations:definition.equations || [],limitations:definition.limitations || [],sources:definition.sources || []},
      inputs:{numericFields:definition.fields || [],jsonDataFields:(definition.data_fields || []).map(field=>({name:field.name,label:field.label,default:summarizeDefault(field.default)}))},
      fixture:acceptance.fixture,
      acceptance,
      documentationUrl:`/models/#study-${definition.id}`,
    };
  });
  const workspaces = Object.entries(WORKSPACES).map(([id, workspace]) => ({
    id,name:workspace.name,appRoute:workspace.route,
    studies:studies.filter(study=>study.workspace.id===id).map(study=>study.id),
    delivery:{publicBrowser:'bundled synthetic examples',newCalculations:'local Python application',boundedTerminal:false},
    contractUrl:'/models/#workspace-'+id,
  }));
  if (studies.length !== 59 || workspaces.length !== 12 || workspaces.some(workspace=>workspace.studies.length===0)) {
    throw new Error(`Study coverage changed: ${studies.length} studies across ${workspaces.length} workspaces`);
  }
  const studyCatalogueDigest = digest(bundle.catalogue);
  const studyFixtureDigest = digest(Object.fromEntries(studies.map(study=>[study.id,study.fixture.evidenceSha256])));
  const hybridBundle = JSON.parse(fs.readFileSync(path.join(repoRoot,'examples/hybrid-bundle.json'),'utf8'));
  const packageText=fs.readFileSync(path.join(repoRoot,'apps/api/pyproject.toml'),'utf8');
  const packageVersion=packageText.match(/^version\s*=\s*"([^"]+)"/m)?.[1] || null;
  if(!packageVersion)throw new Error('Python API package version is not declared in pyproject.toml');
  return {
    registryVersion:'1.0.0',
    generatedFrom:'apps/web/src/roadmap-data.ts (generated by scripts/generate-studies.py from apps/api/helioforge/studies.py)',
    generatedAtSourceRevisionDate:CONTENT_REVISION_DATE,
    status:'source inventory; not a deployment receipt or independent scientific validation',
    identities:{
      application:{browserReleaseVersion:APPLICATION_VERSION,source:'scripts/build-domain.mjs sets the browser release version on the generated app.json; this source identity does not prove deployment.'},
      apiPackage:{name:'helioforge-api',version:packageVersion,source:'apps/api/pyproject.toml'},
      catalogue:{
        hybrid:{version:'0.2.0',source:'apps/api/helioforge/data/hybrid_catalog.json',architectureCount:36,scenarioCount:24,lessonCount:36},
        studies:{declaredVersion:null,versionStatus:'U — no independent semantic study-catalogue version is declared; content digest below identifies this catalogue snapshot.',studyCount:studies.length,workspaceCount:workspaces.length,sha256:studyCatalogueDigest},
      },
      data:{
        hybridPresets:{schema:hybridBundle.schema,version:hybridBundle.version,catalogueVersion:hybridBundle.catalogue_version,caseCount:hybridBundle.cases.length,sha256:hybridBundle.dataset_sha256},
        studyExamples:{kind:'synthetic_or_user_supplied_unverified',version:null,versionStatus:'U — examples have no named dataset version; the fixture digest identifies their current generated evidence hashes.',sha256:studyFixtureDigest},
      },
      models:{...Object.fromEntries(Object.entries(MODELS).map(([key,value])=>[key,value.version])),studyCatalogue:[...new Set(studies.map(study=>study.model.version))]},
      schemas:{terminal:'helioforge.terminal.v1',hybridPresets:hybridBundle.schema,studyResultVersion:null,studyResultVersionStatus:'U — studies.py currently adds study/model_version/input provenance but no standalone result schema_version.'},
    },
    deliveryModes:[
      {id:'bundled',name:'Bundled synthetic examples',description:CAPABILITY_COPY.bundled,newCalculations:false},
      {id:'terminal',name:'Bounded browser Terminal',description:CAPABILITY_COPY.terminal,newCalculations:true,modelVersion:MODELS.terminal.version,horizon:'24 one-hour steps'},
      {id:'python',name:'Advanced local Python',description:CAPABILITY_COPY.python,newCalculations:true,studyCount:studies.length,workspaceCount:workspaces.length,modelVersion:'roadmap-screen-v1'},
      {id:'external',name:'Opt-in local external providers',description:CAPABILITY_COPY.external,newCalculations:null,providerExecutionStatus:'not verified by this documentation change'},
    ],
    taskStarts:TASK_STARTS,
    workspaces,
    studies,
  };
}

export function buildPublicCapabilityFacts(registry, options={}) {
  const {origin='https://mkgrid.co.technology',applicationBase=`${origin}/`} = options;
  const documentation = options.documentation || {
    help:`${origin}/help/`,modelRegistry:`${origin}/models/`,capabilities:`${origin}/learning/capability-modes/`,
  };
  return {
    contractVersion:CAPABILITY_CONTRACT_VERSION,
    revisionDate:CONTENT_REVISION_DATE,
    applicationVersion:registry.identities.application.browserReleaseVersion,
    application:{version:registry.identities.application.browserReleaseVersion,apiPackageVersion:registry.identities.apiPackage.version,source:'source release manifest; not a deployment identity'},
    catalogue:registry.identities.catalogue,
    data:registry.identities.data,
    modelVersions:registry.identities.models,
    schemaVersions:registry.identities.schemas,
    modes:registry.deliveryModes,
    taskStarts:TASK_STARTS.map(start=>({...start,href:start.href.startsWith('/')?applicationBase+start.href.slice(1):start.href})),
    workspaceCount:registry.workspaces.length,
    studyCount:registry.studies.length,
    modelRegistryUrl:documentation.modelRegistry,
    helpUrl:documentation.help,
    capabilitiesUrl:documentation.capabilities,
    evidenceBoundary:'Published source inventory only. No deployment, independent model validation or external-provider execution is asserted.',
  };
}

export function validateCloudflareCopy(config) {
  const fullText = JSON.stringify(config);
  for (const [mode, phrase] of Object.entries(CAPABILITY_COPY)) {
    if (!fullText.includes(phrase)) throw new Error(`cloudflare.json capability copy is out of sync for ${mode}`);
  }
  for (const start of TASK_STARTS) if (!fullText.includes(start.label) || !fullText.includes(start.description)) {
    throw new Error(`cloudflare.json is missing the ${start.id} task-led entry`);
  }
}

export function capabilityMarkdown(registry) {
  const lines = [
    '# Capability contract',
    '',
    `Contract version: \`${CAPABILITY_CONTRACT_VERSION}\` · Content revision: ${CONTENT_REVISION_DATE}.`,
    '',
    'This is the shared product-copy and evidence contract used by the generated public overview, About, Methodology, Help and app facts. Application version, catalogue identity, data identity and model versions are recorded separately in [the model registry](MODEL_REGISTRY.md).',
    '',
    '## Delivery modes',
    '',
    '| Mode | Capability | New calculations |',
    '|---|---|---:|',
    ...registry.deliveryModes.map(mode=>`| ${mode.name} | ${mode.description} | ${mode.newCalculations===true?'Yes':mode.newCalculations===false?'No':'Provider-specific'} |`),
    '',
    '## Task-led starts',
    '',
    ...TASK_STARTS.map(start=>`- **${start.label}.** ${start.description} [Open](${start.href}).`),
    '',
    '## Public copy (shared verbatim)',
    '',
    ...Object.values(CAPABILITY_COPY).map(text=>`> ${text}`),
    '',
    'The external-provider description is a scope boundary, not a claim that any paid, live or device provider was exercised. External integrations remain provider-specific and consent-gated.',
    '',
    '## Scope',
    '',
    `The current source inventory has **${registry.workspaces.length} workspaces** and **${registry.studies.length} study IDs**. The Terminal is a separate browser energy-balance model. The 59 study models use the local Python API for new calculations; the public preview carries their generated sample outputs.`,
    '',
    'This implementation does not establish publication, deployment state, calibration, independent scientific validation, professional approval, or production readiness.',
    '',
  ];
  return lines.join('\n');
}

export function modelRegistryMarkdown(registry) {
  const lines = [
    '# Model registry',
    '',
    `Registry version: \`${registry.registryVersion}\` · Content revision: ${registry.generatedAtSourceRevisionDate}.`,
    '',
    'This registry is generated from the Python-backed study catalogue embedded in `apps/web/src/roadmap-data.ts`. It inventories source contracts and default fixtures; the per-study acceptance cards distinguish packaged evidence from checks not run during this documentation change.',
    '',
    '## Version identities',
    '',
    '| Layer | Identity | Evidence |',
    '|---|---|---|',
    `| Browser application release | ${registry.identities.application.browserReleaseVersion} | ${registry.identities.application.source} |`,
    `| Python API package | ${registry.identities.apiPackage.version} | ${registry.identities.apiPackage.source} |`,
    `| Hybrid catalogue | ${registry.identities.catalogue.hybrid.version} | ${registry.identities.catalogue.hybrid.architectureCount} architectures, ${registry.identities.catalogue.hybrid.scenarioCount} scenarios, ${registry.identities.catalogue.hybrid.lessonCount} lessons |`,
    `| Study catalogue | No declared semantic version; SHA-256 \`${registry.identities.catalogue.studies.sha256}\` | ${registry.identities.catalogue.studies.studyCount} IDs / ${registry.identities.catalogue.studies.workspaceCount} workspaces |`,
    `| Hybrid example data | ${registry.identities.data.hybridPresets.version} / ${registry.identities.data.hybridPresets.schema} | ${registry.identities.data.hybridPresets.caseCount} bundled cases; dataset digest in JSON |`,
    `| Study example data | No declared dataset version; digest \`${registry.identities.data.studyExamples.sha256}\` | Synthetic or user-supplied-unverified examples |`,
    `| Study model | \`${[...new Set(registry.studies.map(study=>study.model.version))].join('`, `')}\` | Per-study association is listed below |`,
    `| Study result schema | U — no standalone schema_version in current envelope | See \`docs/roadmap/CONTRACT.md\` and individual source module |`,
    '',
    'A version or digest identifies a source object. It does not prove its scientific accuracy or deployment state.',
    '',
    '## Workspaces and linked study contracts',
    '',
  ];
  for (const workspace of registry.workspaces) {
    lines.push(`### ${workspace.name} · \`${workspace.id}\` {#workspace-${workspace.id}}`, '');
    lines.push(`Route: \`${workspace.appRoute}\` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*`, '');
    for (const id of workspace.studies) {
      const study = registry.studies.find(item=>item.id===id);
      lines.push(`#### ${study.title} · \`${study.id}\` {#study-${study.id}}`, '');
      lines.push(`Model: \`${study.model.version}\`. Python: [${path.basename(study.acceptance.modelReferences.code)}](../${study.acceptance.modelReferences.code}) · Tests: ${study.acceptance.modelReferences.tests.map(file=>`[${path.basename(file)}](../${file})`).join(', ')}.`, '');
      lines.push(`Input schema: ${study.acceptance.schema.numericFields.length} bounded numeric field(s), ${study.acceptance.schema.jsonDataFields.length} JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.`, '');
      lines.push(`Default fixture: \`${study.fixture.dataKind}\`, input SHA-256 \`${study.fixture.inputSha256}\`, evidence SHA-256 \`${study.fixture.evidenceSha256}\`. Independent hand check: **NOT RUN**.`, '');
      lines.push('Equations:', ...study.model.equations.map(equation=>`- \`${equation.replaceAll('`','\\`')}\``), '');
      lines.push('Model limits:', ...study.model.limitations.map(limit=>`- ${limit}`), '');
      lines.push(`Acceptance status: **${study.acceptance.status}**. ${study.acceptance.executionEvidence?.sourceMatches?'Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation.':'Linked checks lack current source-bound execution evidence.'} [Open the full acceptance card](MODEL_REGISTRY.json#${study.id}).`, '');
    }
  }
  lines.push('## Registry data', '', '[Machine-readable per-study records and acceptance cards](MODEL_REGISTRY.json). Each card includes input names, declared units and bounds, equation strings, source links, bundled fixture digests, model limits, validation-status unknowns, and exact test-module paths.', '');
  return lines.join('\n');
}

export function writeModelRegistry(repoRoot=root) {
  const registry = buildModelRegistry(repoRoot);
  fs.writeFileSync(path.join(repoRoot,'docs/MODEL_REGISTRY.json'),JSON.stringify(registry,null,2)+'\n');
  fs.writeFileSync(path.join(repoRoot,'docs/CAPABILITIES.md'),capabilityMarkdown(registry));
  fs.writeFileSync(path.join(repoRoot,'docs/MODEL_REGISTRY.md'),modelRegistryMarkdown(registry));
  return registry;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const registry = writeModelRegistry(root);
  console.log(JSON.stringify({registry:'docs/MODEL_REGISTRY.json',workspaces:registry.workspaces.length,studies:registry.studies.length,studyCatalogueSha256:registry.identities.catalogue.studies.sha256}));
}
