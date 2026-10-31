import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {compileScripts} from '../../../scripts/compile-web.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-workspace-migration-'));
const out = path.join(temp, 'app.js');
const sources = JSON.parse(fs.readFileSync(path.join(web, 'tsconfig.json'), 'utf8')).files.map(file => path.join(web, file));
compileScripts(sources, out);
const code = fs.readFileSync(out, 'utf8');
process.on('exit', () => fs.rmSync(temp, {recursive: true, force: true}));

function runtime() {
  const memory = new Map(), listeners = new Map(), nodes = new Map(), downloads = [], toasts = [];
  const localStorage = {
    getItem(key) { return memory.get(key) ?? null; },
    setItem(key, value) { memory.set(key, String(value)); },
    removeItem(key) { memory.delete(key); },
  };
  const document = {
    readyState: 'loading',
    addEventListener(type, callback) { const callbacks = listeners.get(type) ?? []; callbacks.push(callback); listeners.set(type, callbacks); },
    createElement() { return {}; },
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, {set outerHTML(value) { this.html = value; }, textContent: '', innerHTML: ''});
      return nodes.get(id);
    },
    querySelectorAll() { return []; },
  };
  const box = vm.createContext({URL, Intl, Number, String, Math, Array, Object, JSON, Set, Map, Date, structuredClone, localStorage, document, FormData: class {}, window: {scrollTo() {}}});
  vm.runInContext(code, box);
  box.HF.download = (filename, payload, type = 'application/json') => downloads.push({filename, payload, type});
  function dispatch(type, target) {
    const event = {target, preventDefault() {}};
    for (const callback of listeners.get(type) ?? []) callback(event);
  }
  return {hf: box.HF, box, memory, localStorage, document, nodes, downloads, toasts, dispatch};
}

const target = dataset => ({dataset, closest() { return this; }});
const flush = async () => { for (let i = 0; i < 20; i++) await new Promise(resolve => setTimeout(resolve, 5)); };
function makeState(hf, connected = false) {
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  return state;
}
function install(x, state, modal = {title: '', body: ''}) {
  const controller = x.hf.installChampionController(state, {
    render() {}, toast(message, error) { x.toasts.push({message, error}); }, navigate() {},
    openModal(title, body) { modal.title = title; modal.body = body; }, celebrate() {},
    api: async () => { throw new Error('Unexpected API call'); },
  });
  return {controller, modal};
}
function workspaceV1(hf, state, patch = {}) {
  const record = {...hf.workspaceCache(state), ...patch, schema: hf.WORKSPACE_SCHEMA_V1};
  delete record.migration;
  return record;
}
function pickerFor(x, file) {
  let picker;
  x.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [file], click() {}};
    return picker;
  };
  return () => picker;
}

test('v1 is the historical source schema and parses to v2 without losing workspace fields', () => {
  const x = runtime(), hf = x.hf, state = makeState(hf);
  state.champion.saved = [{id: 'setup-d85c1ad4-98b3-46e1-af53-23a202435683', name: 'Original setup', created_at: '2026-10-28T12:00:00.000Z', inputs: structuredClone(state.hybrid.inputs)}];
  const v2 = hf.workspaceCache(state), v1 = workspaceV1(hf, state, {saved_setups: structuredClone(state.champion.saved)});
  const migrated = hf.parseWorkspace(v1);
  assert.equal(v2.schema, 'helioforge.workspace.v2');
  assert.equal(v2.migration, null);
  assert.equal(migrated.schema, 'helioforge.workspace.v2');
  assert.equal(migrated.migration.schema, 'helioforge.workspace-migration.v1');
  assert.equal(migrated.migration.source_schema, 'helioforge.workspace.v1');
  assert.equal(migrated.migration.target_schema, 'helioforge.workspace.v2');
  assert.deepEqual(JSON.parse(JSON.stringify(migrated.migration.losses)), []);
  for (const key of ['saved_at', 'inputs', 'lesson_id', 'last_run_id', 'pinned_run_ids', 'saved_setups']) assert.deepEqual(JSON.parse(JSON.stringify(migrated[key])), JSON.parse(JSON.stringify(v1[key])));
  assert.deepEqual(JSON.parse(JSON.stringify(hf.parseWorkspace(v2))), JSON.parse(JSON.stringify(v2)), 'current v2 round trips without changing its receipt');
  assert.throws(() => hf.parseWorkspace({...v1, saved_setups: [{id: 'setup-d85c1ad4-98b3-46e1-af53-23a202435683', name: 'Unsupported field', created_at: v1.saved_at, inputs: v1.inputs, future_value: true}]}), /unknown saved setup field/i);
  assert.throws(() => hf.prepareWorkspaceImport({schema: 'helioforge.workspace.v0'}), /unsupported/i, 'no historical v0 schema is fabricated');
});

test('an existing local v1 cache waits for migration preview and confirmation, retaining its raw backup', async () => {
  const x = runtime(), hf = x.hf, state = makeState(hf);
  const savedRunId = 'f6b50c62-95a4-4aa4-a3da-1a4af7709966';
  const savedInputs = {...hf.presetInputs('hospital-island'), load_kw: 651};
  const rawV1 = JSON.stringify({...workspaceV1(hf, state, {inputs: savedInputs, last_run_id: savedRunId}), saved_at: '2026-10-28T12:00:00.000Z'});
  x.memory.set(hf.WORKSPACE_KEY, rawV1);
  state.champion = hf.initialChampionState(state.hybrid);
  assert.equal(state.hybrid.inputs.system_id, 'hospital-island');
  assert.equal(state.hybrid.result, null, 'the custom saved inputs have no bundled result attached');
  assert.equal(state.champion.migrationPendingRaw, rawV1);
  assert.equal(state.champion.lastRunId, savedRunId);
  assert.equal(hf.persistWorkspace(state), false);
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), rawV1, 'ordinary persistence cannot silently migrate the local record');
  const {modal} = install(x, state);
  x.dispatch('click', target({championAction: 'migrate-workspace'}));
  assert.match(modal.title, /migration/i);
  assert.match(modal.body, /Source schema: helioforge\.workspace\.v1/);
  assert.match(modal.body, /Target schema: helioforge\.workspace\.v2/);
  assert.match(modal.body, /Refreshed the workspace saved_at timestamp during migration\./);
  assert.match(modal.body, /Losses:[\s\S]*None/);
  x.dispatch('click', target({championAction: 'export-workspace-migration-receipt'}));
  assert.equal(x.downloads.length, 1);
  const exported = JSON.parse(x.downloads[0].payload);
  assert.equal(exported.source_schema, 'helioforge.workspace.v1');
  assert.equal(exported.target_schema, 'helioforge.workspace.v2');
  x.dispatch('click', target({championAction: 'confirm-workspace-import'}));
  assert.equal(x.memory.get(hf.WORKSPACE_BACKUP_KEY), rawV1, 'migration preserves the exact old workspace bytes');
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).schema, 'helioforge.workspace.v2');
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).last_run_id, savedRunId, 'an unchanged v1 workspace retains its validated saved-run reference');
  assert.notEqual(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).saved_at, '2026-10-28T12:00:00.000Z');
  assert.equal(state.champion.migrationPendingRaw, null);
});

test('migration declares when an edited workspace drops its now-stale saved-run pointer', () => {
  const x = runtime(), hf = x.hf, state = makeState(hf);
  const savedRunId = 'e8107071-3a8b-4c0a-b28b-93558cf90788';
  const savedInputs = {...hf.presetInputs('hospital-island'), load_kw: 651};
  const rawV1 = JSON.stringify(workspaceV1(hf, state, {inputs: savedInputs, last_run_id: savedRunId}));
  x.memory.set(hf.WORKSPACE_KEY, rawV1);
  state.champion = hf.initialChampionState(state.hybrid);
  state.hybrid.inputs = {...state.hybrid.inputs, load_kw: 652};
  state.champion.lastRunId = null;
  const {modal} = install(x, state);

  x.dispatch('click', target({championAction: 'migrate-workspace'}));
  assert.match(modal.body, /Cleared the saved last-run ID because current inputs differ from the v1 workspace inputs\./);
  x.dispatch('click', target({championAction: 'confirm-workspace-import'}));
  const migrated = JSON.parse(x.memory.get(hf.WORKSPACE_KEY));
  assert.equal(migrated.last_run_id, null);
  assert.deepEqual(migrated.migration.losses, [
    'Cleared the saved last-run ID because current inputs differ from the v1 workspace inputs.',
  ]);
});

test('v1 and v2 imports preview their receipt, preserve the replaced bytes, and round trip', async () => {
  const x = runtime(), hf = x.hf, state = makeState(hf), modal = {title: '', body: ''};
  hf.persistWorkspace(state);
  const originalRaw = x.memory.get(hf.WORKSPACE_KEY);
  const {modal: opened} = install(x, state, modal);
  const v1 = workspaceV1(hf, state, {inputs: hf.presetInputs('hospital-island'), saved_setups: []});
  const getPicker = pickerFor(x, {size: 1000, text: async () => JSON.stringify(v1)});
  x.dispatch('click', target({championAction: 'import-workspace'}));
  await getPicker().onchange();
  assert.match(opened.body, /Source schema: helioforge\.workspace\.v1/);
  assert.match(opened.body, /Target schema: helioforge\.workspace\.v2/);
  assert.ok(opened.body.includes('retained'));
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), originalRaw, 'preview alone does not replace the local workspace');
  x.dispatch('click', target({championAction: 'export-workspace-migration-receipt'}));
  assert.equal(JSON.parse(x.downloads.at(-1).payload).source_schema, 'helioforge.workspace.v1');
  x.dispatch('click', target({championAction: 'confirm-workspace-import'}));
  assert.equal(x.memory.get(hf.WORKSPACE_BACKUP_KEY), originalRaw);
  const firstImport = JSON.parse(x.memory.get(hf.WORKSPACE_KEY));
  assert.equal(firstImport.schema, 'helioforge.workspace.v2');
  assert.equal(firstImport.inputs.system_id, 'hospital-island');
  assert.equal(firstImport.migration.source_schema, 'helioforge.workspace.v1');
  assert.deepEqual(firstImport.migration.losses, []);

  const v2 = {...firstImport, saved_at: '2026-10-29T09:00:00.000Z', inputs: hf.presetInputs('remote-triad')};
  const currentPicker = pickerFor(x, {size: 1200, text: async () => JSON.stringify(v2)});
  x.dispatch('click', target({championAction: 'import-workspace'}));
  await currentPicker().onchange();
  assert.match(opened.body, /Source schema: helioforge\.workspace\.v2/);
  assert.match(opened.body, /Target schema: helioforge\.workspace\.v2/);
  assert.match(opened.body, /Changes:[\s\S]*None/);
  x.dispatch('click', target({championAction: 'export-workspace-migration-receipt'}));
  const currentReceipt = JSON.parse(x.downloads.at(-1).payload);
  assert.equal(currentReceipt.source_schema, 'helioforge.workspace.v2');
  assert.equal(currentReceipt.target_schema, 'helioforge.workspace.v2');
  x.dispatch('click', target({championAction: 'confirm-workspace-import'}));
  const roundTrip = JSON.parse(x.memory.get(hf.WORKSPACE_KEY));
  assert.equal(roundTrip.inputs.system_id, 'remote-triad');
  assert.equal(roundTrip.schema, 'helioforge.workspace.v2');
  assert.equal(roundTrip.migration.source_schema, 'helioforge.workspace.v1', 'a v2 import keeps its existing migration history');
  assert.equal(state.champion.lastMigrationReceipt.source_schema, 'helioforge.workspace.v2', 'the current import receipt remains available in memory');
  assert.equal(state.champion.lastMigrationReceipt.target_schema, 'helioforge.workspace.v2');
  assert.deepEqual(JSON.parse(JSON.stringify(hf.parseWorkspace(roundTrip))), roundTrip);
});

test('interrupted v1 import and storage denial retain data and permit retry', async () => {
  const x = runtime(), hf = x.hf, state = makeState(hf), modal = {title: '', body: ''};
  hf.persistWorkspace(state);
  const originalRaw = x.memory.get(hf.WORKSPACE_KEY), originalInputs = hf.configurationKey(state.hybrid.inputs);
  const v1 = workspaceV1(hf, state, {inputs: hf.presetInputs('hospital-island')});
  let resolveText;
  const delayedPicker = pickerFor(x, {size: 1000, text: () => new Promise(resolve => { resolveText = resolve; })});
  const {modal: opened} = install(x, state, modal);
  x.dispatch('click', target({championAction: 'import-workspace'}));
  const interrupted = delayedPicker().onchange();
  hf.advanceHybridStateRevision(state.hybrid);
  resolveText(JSON.stringify(v1));
  await interrupted;
  assert.equal(opened.title, '', 'an import interrupted by newer work must not show a stale preview');
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), originalRaw);
  assert.equal(hf.configurationKey(state.hybrid.inputs), originalInputs);

  const retryPicker = pickerFor(x, {size: 1000, text: async () => JSON.stringify(v1)});
  x.dispatch('click', target({championAction: 'import-workspace'}));
  await retryPicker().onchange();
  const setItem = x.localStorage.setItem.bind(x.localStorage);
  x.localStorage.setItem = (key, value) => { if (key === hf.WORKSPACE_KEY && String(value).includes('hospital-island')) throw new Error('QuotaExceededError'); setItem(key, value); };
  x.dispatch('click', target({championAction: 'confirm-workspace-import'}));
  await flush();
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), originalRaw, 'storage denial leaves the active workspace unchanged');
  assert.equal(x.memory.get(hf.WORKSPACE_BACKUP_KEY), originalRaw, 'the exact prior workspace remains recoverable after a denied v2 write');
  assert.equal(hf.configurationKey(state.hybrid.inputs), originalInputs);
  assert.ok(x.toasts.some(toast => toast.error && /could not be stored|quota/i.test(toast.message)));

  x.localStorage.setItem = setItem;
  x.dispatch('click', target({championAction: 'confirm-workspace-import'}));
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).schema, 'helioforge.workspace.v2');
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).inputs.system_id, 'hospital-island');
});
