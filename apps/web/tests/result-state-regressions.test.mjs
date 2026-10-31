import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {compileScripts} from '../../../scripts/compile-web.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-result-state-'));
const out = path.join(temp, 'app.js');
const files = JSON.parse(fs.readFileSync(path.join(web, 'tsconfig.json'), 'utf8')).files.map(file => path.join(web, file));
compileScripts(files, out);
const code = fs.readFileSync(out, 'utf8');
process.on('exit', () => fs.rmSync(temp, {recursive: true, force: true}));

function runtime({digest = webcrypto.subtle} = {}) {
  const memory = new Map(), listeners = new Map(), pickers = [], nodes = new Map(), downloads = [], toasts = [];
  class FakeFormData {
    constructor(form) { this.form = form; }
    *[Symbol.iterator]() { yield* this.form.fields ?? []; }
    entries() { return this[Symbol.iterator](); }
    get(key) { return (this.form.fields ?? []).find(([name]) => name === key)?.[1] ?? null; }
  }
  const localStorage = {
    getItem(key) { return memory.get(key) ?? null; },
    setItem(key, value) { memory.set(key, String(value)); },
    removeItem(key) { memory.delete(key); },
  };
  const document = {
    readyState: 'loading',
    addEventListener(type, callback) { const callbacks = listeners.get(type) ?? []; callbacks.push(callback); listeners.set(type, callbacks); },
    createElement(tag) {
      if (tag === 'input') {
        const picker = {files: [], addEventListener(type, callback) { this[`on${type}`] = callback; }, click() {}};
        pickers.push(picker);
        return picker;
      }
      return {click() {}, remove() {}, setAttribute() {}, style: {}, href: '', download: ''};
    },
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, {set outerHTML(value) { this.html = value; }, scrollIntoView() {}});
      return nodes.get(id);
    },
    querySelectorAll() { return []; },
    querySelector() { return null; },
  };
  const box = vm.createContext({
    URL, URLSearchParams, Intl, Number, String, Math, Array, Object, JSON, Set, Map, Date,
    structuredClone, localStorage, document, FormData: FakeFormData, crypto: {subtle: digest, randomUUID: webcrypto.randomUUID.bind(webcrypto)},
    TextEncoder, performance, history: {replaceState() {}}, location: {href: 'http://localhost/run/'},
    navigator: {clipboard: {writeText: async () => {}}}, window: {scrollTo() {}},
    setTimeout(callback) { callback(); return 1; }, clearTimeout() {},
  });
  vm.runInContext(code, box);
  box.HF.download = (filename, payload) => downloads.push({filename, payload});
  function dispatch(type, target, extra = {}) {
    const event = {target, preventDefault() {}, ...extra};
    for (const callback of listeners.get(type) ?? []) callback(event);
    return event;
  }
  return {hf: box.HF, box, memory, localStorage, listeners, pickers, nodes, downloads, toasts, dispatch};
}

const clickTarget = dataset => ({dataset, closest() { return this; }});
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
};
const flush = async () => { for (let i = 0; i < 20; i++) await new Promise(resolve => setTimeout(resolve, 5)); };

test('a delayed hybrid configuration import cannot replace an edit made after file selection', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: true, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  let picker;
  const fileText = deferred();
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 400, text: () => fileText.promise}], click() {}};
    return picker;
  };
  hf.installHybridController(state, {render() {}, toast: (message, error) => x.toasts.push({message, error}), navigate() {}, api: async () => { throw new Error('Unexpected API call'); }, celebrate() {}, openModal() {}});
  x.dispatch('click', clickTarget({hybridAction: 'import'}));
  const imported = {...state.hybrid.inputs};
  const edited = {...imported, load_kw: imported.load_kw + 1};
  const fields = Object.entries(edited).filter(([name]) => !['system_id', 'scenario_id'].includes(name)).map(([name, value]) => [name, String(value)]);
  const controls = fields.map(([name, value]) => ({name, value, removeAttribute() {}}));
  const form = {fields, querySelectorAll() { return controls; }};
  const input = {name: 'load_kw', closest(selector) { return selector === '#hybrid-config' ? form : null; }, setAttribute() {}};
  x.dispatch('input', input);
  fileText.resolve(JSON.stringify({schema: 'helioforge.hybrid.v1', inputs: imported}));
  await picker.onchange();
  assert.equal(state.hybrid.inputs.load_kw, edited.load_kw, 'the newer draft must remain current');
  assert.equal(state.hybrid.inputError, null);
});

test('a delayed Terminal manifest import cannot replace a newer completed candidate', async () => {
  const x = runtime(), hf = x.hf;
  const defaults = hf.terminalDefaults();
  const importedRun = hf.terminalSolve({...defaults, pvKw: 0, batteryKwh: 0, batteryKw: 0, gridKw: 0, loadKw: 5});
  const manifest = JSON.stringify(await hf.terminalCreateManifest(importedRun));
  let picker;
  const fileText = deferred();
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: manifest.length, text: () => fileText.promise}], addEventListener(type, callback) { this[`on${type}`] = callback; }, click() {}};
    return picker;
  };
  hf.installTerminalController({navigate() {}, toast(message, error) { x.toasts.push({message, error}); }});
  x.dispatch('click', clickTarget({terminalAction: 'import'}));
  picker.onchange();

  const newer = {...defaults, pvKw: 0, batteryKwh: 0, batteryKw: 0, gridKw: 0, loadKw: 1};
  const form = {id: 'terminal-run-form', fields: Object.entries(newer).map(([key, value]) => [key, String(value)])};
  x.dispatch('submit', form);
  fileText.resolve(manifest);
  await flush();
  assert.match(hf.terminalView(), /name="loadKw" type="number" step="any" value="1"/, 'the newer candidate must remain visible');
});

test('Terminal export drops a digest response when its run became stale while hashing', async () => {
  const digest = deferred();
  const x = runtime({digest: {digest: () => digest.promise}}), hf = x.hf;
  const defaults = hf.terminalDefaults();
  hf.installTerminalController({navigate() {}, toast(message, error) { x.toasts.push({message, error}); }});
  x.dispatch('click', clickTarget({terminalExport: 'json'}));
  const newer = {...defaults, pvKw: 0, batteryKwh: 0, batteryKw: 0, gridKw: 0, loadKw: 1};
  x.dispatch('submit', {id: 'terminal-run-form', fields: Object.entries(newer).map(([key, value]) => [key, String(value)])});
  digest.resolve(new Uint8Array(32).buffer);
  await flush();
  assert.equal(x.downloads.length, 0, 'no old run may be exported after a newer run completes');
});

test('editing Terminal sweep controls clears the old heatmap and invalidates a queued sweep', () => {
  const x = runtime(), hf = x.hf;
  hf.installTerminalController({navigate() {}, toast(message, error) { x.toasts.push({message, error}); }});
  const fields = [['x', 'pvKw'], ['lower', '2'], ['upper', '18'], ['y', 'batteryKwh'], ['yLower', '5'], ['yUpper', '40'], ['steps', '3'], ['scale', 'linear'], ['matrix', '2']];
  x.dispatch('submit', {id: 'terminal-sweep-form', fields});
  const initialView = hf.terminalView();
  const candidateSnapshot = view => ({
    load: view.match(/name="loadKw" type="number" step="any" value="([^"]+)"/)?.[1],
    periodCost: view.match(/<dt>Period cost \[EUR\]<\/dt><dd>([^<]+)<\/dd>/)?.[1],
    served: view.match(/<dt>Demand served<\/dt><dd>([^<]+)<\/dd>/)?.[1],
    unserved: view.match(/<dt>Unserved \[kWh\]<\/dt><dd>([^<]+)<\/dd>/)?.[1],
    storedDelta: view.match(/<dt>Stored energy delta \[kWh\]<\/dt><dd>([^<]+)<\/dd>/)?.[1],
  });
  assert.match(initialView, /class="terminal-matrix"/, 'a completed initial sweep should show its heatmap');

  const sweepForm = {id: 'terminal-sweep-form', fields};
  const lowerInput = {name: 'lower', closest(selector) { return selector === '#terminal-sweep-form' ? sweepForm : null; }};
  x.dispatch('input', lowerInput);
  const clearedView = hf.terminalView();
  assert.doesNotMatch(clearedView, /terminal-matrix|terminal-pareto/, 'edited bounds must not leave the old sweep visible');
  assert.match(clearedView, /sweep controls changed/i, 'the user should be told to rerun the sweep');
  assert.deepEqual(candidateSnapshot(clearedView), candidateSnapshot(initialView), 'editing sweep controls must preserve the current candidate result and inputs');

  const queued = [];
  x.box.setTimeout = callback => { queued.push(callback); return queued.length; };
  const pendingFields = fields.map(([key, value]) => [key, key === 'lower' ? '3' : value]);
  x.dispatch('submit', {id: 'terminal-sweep-form', fields: pendingFields});
  assert.equal(queued.length, 1, 'the new sweep should be pending');
  const changedForm = {id: 'terminal-sweep-form', fields: [...fields]};
  const upperChange = {name: 'upper', closest(selector) { return selector === '#terminal-sweep-form' ? changedForm : null; }};
  x.dispatch('change', upperChange);
  assert.doesNotMatch(hf.terminalView(), /terminal-matrix|terminal-pareto/, 'editing while a sweep is pending must keep the heatmap clear');
  queued[0]();
  assert.doesNotMatch(hf.terminalView(), /terminal-matrix|terminal-pareto/, 'the obsolete queued sweep must not repopulate results');
  const rerunFields = pendingFields.map(([key, value]) => [key, key === 'upper' ? '17' : value]);
  x.dispatch('submit', {id: 'terminal-sweep-form', fields: rerunFields});
  queued[1]();
  assert.match(hf.terminalView(), /class="terminal-matrix"/, 'a deliberate rerun should compute and display the changed sweep');
  assert.deepEqual(candidateSnapshot(hf.terminalView()), candidateSnapshot(initialView), 'rerunning the sweep must continue to preserve the candidate result');
});

test('a delayed Terminal manifest cannot overwrite a newer sweep-control edit', async () => {
  const source = runtime(), run = source.hf.terminalSolve({...source.hf.terminalDefaults(), loadKw: 5});
  const manifest = JSON.stringify(await source.hf.terminalCreateManifest(run));
  const digest = deferred();
  let digestCalls = 0;
  const x = runtime({digest: {digest(...args) { return digestCalls++ === 0 ? digest.promise : webcrypto.subtle.digest(...args); }}}), hf = x.hf;
  let picker;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: manifest.length, text: async () => manifest}], addEventListener(type, callback) { this[`on${type}`] = callback; }, click() {}};
    return picker;
  };
  hf.installTerminalController({navigate() {}, toast(message, error) { x.toasts.push({message, error}); }});
  x.dispatch('click', clickTarget({terminalAction: 'import'}));
  picker.onchange();
  await new Promise(resolve => setTimeout(resolve, 5));
  const fields = [['x', 'pvKw'], ['lower', '4'], ['upper', '18'], ['y', 'batteryKwh'], ['yLower', '5'], ['yUpper', '40'], ['steps', '3'], ['scale', 'linear'], ['matrix', '2']];
  const form = {id: 'terminal-sweep-form', fields};
  const lowerInput = {name: 'lower', closest(selector) { return selector === '#terminal-sweep-form' ? form : null; }};
  x.dispatch('input', lowerInput);
  digest.resolve(await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(hf.terminalCanonical(JSON.parse(manifest).payload))));
  await flush();
  assert.match(hf.terminalView(), /name="loadKw" type="number" step="any" value="6"/, 'the delayed import must leave the current candidate and newer sweep edit in place');
  assert.doesNotMatch(hf.terminalView(), /class="terminal-matrix"|class="terminal-pareto"/, 'the import must not restore an obsolete sweep heatmap');
});

test('a rejected stale Terminal import cannot clear a newer pending sweep state', async () => {
  const source = runtime(), run = source.hf.terminalSolve({...source.hf.terminalDefaults(), loadKw: 5});
  const tampered = await source.hf.terminalCreateManifest(run);
  tampered.payload.run.inputs.loadKw = 4;
  const manifest = JSON.stringify(tampered);
  const digest = deferred();
  const payloadDigest = await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(source.hf.terminalCanonical(tampered.payload)));
  let digestCalls = 0;
  const x = runtime({digest: {digest(...args) { return digestCalls++ === 0 ? digest.promise : webcrypto.subtle.digest(...args); }}}), hf = x.hf;
  let picker;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: manifest.length, text: async () => manifest}], addEventListener(type, callback) { this[`on${type}`] = callback; }, click() {}};
    return picker;
  };
  const queued = [];
  x.box.setTimeout = callback => { queued.push(callback); return queued.length; };
  hf.installTerminalController({navigate() {}, toast(message, error) { x.toasts.push({message, error}); }});
  x.dispatch('click', clickTarget({terminalAction: 'import'}));
  picker.onchange();
  await new Promise(resolve => setTimeout(resolve, 5));

  const fields = [['x', 'pvKw'], ['lower', '4'], ['upper', '18'], ['y', 'batteryKwh'], ['yLower', '5'], ['yUpper', '40'], ['steps', '3'], ['scale', 'linear'], ['matrix', '2']];
  const form = {id: 'terminal-sweep-form', fields};
  x.dispatch('input', {name: 'lower', closest(selector) { return selector === '#terminal-sweep-form' ? form : null; }});
  x.dispatch('submit', {id: 'terminal-sweep-form', fields});
  const pendingSweepView = hf.terminalView();
  assert.match(pendingSweepView, /<output id="terminal-status"[^>]*>SOLVING<\/output>/);
  assert.match(pendingSweepView, /Sweep controls changed; rerun the sweep/);
  assert.match(pendingSweepView, /name="lower" type="number" step="any" value="4"/);

  digest.resolve(payloadDigest);
  await flush();
  const afterRejectedImport = hf.terminalView();
  assert.match(afterRejectedImport, /<output id="terminal-status"[^>]*>SOLVING<\/output>/, 'a stale rejection must not clear the newer sweep busy state');
  assert.match(afterRejectedImport, /Sweep controls changed; rerun the sweep/, 'a stale rejection must not replace the newer notice');
  assert.match(afterRejectedImport, /name="lower" type="number" step="any" value="4"/, 'a stale rejection must preserve the newer sweep draft');
  assert.equal(x.toasts.length, 0, 'a rejection from an obsolete import must not surface as the current action failure');
  queued[0]();
  assert.match(hf.terminalView(), /class="terminal-matrix"/);
});

test('Terminal manifests reject unrecognized envelope fields', async () => {
  const x = runtime(), run = x.hf.terminalSolve(x.hf.terminalDefaults());
  const manifest = await x.hf.terminalCreateManifest(run);
  await assert.rejects(x.hf.terminalReadManifest({...manifest, source_revision: 'untrusted'}), /unknown|unexpected/i);
});

test('workspace import previews replacement, backs up the old cache, and applies only after confirmation', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  hf.persistWorkspace(state);
  const previous = x.memory.get(hf.WORKSPACE_KEY);
  const imported = {...hf.workspaceCache(state), saved_at: '2026-10-28T12:00:00.000Z', inputs: hf.presetInputs('hospital-island'), saved_setups: []};
  let picker, opened = null;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 500, text: async () => JSON.stringify(imported)}], click() {}};
    return picker;
  };
  hf.installChampionController(state, {render() {}, toast() {}, navigate() {}, openModal(title, body) { opened = {title, body}; }, celebrate() {}, api: async () => { throw new Error('Unexpected API call'); }});
  x.dispatch('click', clickTarget({championAction: 'import-workspace'}));
  assert.ok(picker, 'workspace import must be available from the controller');
  await picker.onchange();
  assert.match(opened.title, /preview/i);
  assert.match(opened.body, /hospital/i);
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), previous, 'preview must not overwrite the active cache');
  x.dispatch('click', clickTarget({championAction: 'confirm-workspace-import'}));
  assert.equal(state.hybrid.inputs.system_id, 'hospital-island');
  assert.equal(x.memory.get('hf-workspace-import-backup-v1'), previous, 'the replaced cache must remain recoverable');
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).inputs.system_id, 'hospital-island');
  x.dispatch('click', clickTarget({championAction: 'restore-workspace-backup'}));
  assert.match(opened.title, /preview workspace backup/i);
  x.dispatch('click', clickTarget({championAction: 'confirm-workspace-import'}));
  assert.equal(state.hybrid.inputs.system_id, 'remote-triad', 'a saved backup can be restored after preview');
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_KEY)).inputs.system_id, 'remote-triad');
  assert.equal(JSON.parse(x.memory.get(hf.WORKSPACE_BACKUP_KEY)).inputs.system_id, 'hospital-island', 'the replaced workspace becomes the next recovery backup');
});

test('a v1 workspace import previews a lossless v2 migration receipt before replacing the current cache', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  hf.persistWorkspace(state);
  const oldRaw = x.memory.get(hf.WORKSPACE_KEY);
  const oldRecord = {...hf.workspaceCache(state), schema: hf.WORKSPACE_SCHEMA_V1, inputs: hf.presetInputs('hospital-island')};
  delete oldRecord.migration;
  let picker, preview = '';
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 1000, text: async () => JSON.stringify(oldRecord)}], click() {}};
    return picker;
  };
  hf.installChampionController(state, {render() {}, toast() {}, navigate() {}, openModal(title, body) { preview = `${title}\n${body}`; }, celebrate() {}, api: async () => { throw new Error('Unexpected API call'); }});
  x.dispatch('click', clickTarget({championAction: 'import-workspace'}));
  await picker.onchange();
  assert.match(preview, /Source schema: helioforge\.workspace\.v1/);
  assert.match(preview, /Target schema: helioforge\.workspace\.v2/);
  assert.match(preview, /Losses:[\s\S]*None/);
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), oldRaw, 'migration preview cannot overwrite current storage');
  x.dispatch('click', clickTarget({championAction: 'export-workspace-migration-receipt'}));
  const receipt = JSON.parse(x.downloads[0].payload);
  assert.equal(receipt.source_schema, 'helioforge.workspace.v1');
  assert.equal(receipt.target_schema, 'helioforge.workspace.v2');
  assert.deepEqual(JSON.parse(JSON.stringify(receipt.losses)), []);
  x.dispatch('click', clickTarget({championAction: 'confirm-workspace-import'}));
  const current = JSON.parse(x.memory.get(hf.WORKSPACE_KEY));
  assert.equal(current.schema, 'helioforge.workspace.v2');
  assert.equal(current.inputs.system_id, 'hospital-island');
  assert.equal(current.migration.source_schema, 'helioforge.workspace.v1');
  assert.equal(x.memory.get(hf.WORKSPACE_BACKUP_KEY), oldRaw, 'the exact replaced workspace bytes remain recoverable');
});

test('unsupported workspace imports leave both current state and cache untouched', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  hf.persistWorkspace(state);
  const previous = x.memory.get(hf.WORKSPACE_KEY), inputKey = hf.configurationKey(state.hybrid.inputs);
  let picker;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 200, text: async () => JSON.stringify({schema: 'helioforge.workspace.v0'})}], click() {}};
    return picker;
  };
  hf.installChampionController(state, {render() {}, toast(message, error) { x.toasts.push({message, error}); }, navigate() {}, openModal() {}, celebrate() {}, api: async () => { throw new Error('Unexpected API call'); }});
  x.dispatch('click', clickTarget({championAction: 'import-workspace'}));
  await picker.onchange();
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), previous);
  assert.equal(hf.configurationKey(state.hybrid.inputs), inputKey);
  assert.ok(x.toasts.some(toast => toast.error));
});

test('corrupt workspace files fail before the current cache or inputs are replaced', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  hf.persistWorkspace(state);
  const previous = x.memory.get(hf.WORKSPACE_KEY), inputKey = hf.configurationKey(state.hybrid.inputs);
  let picker;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 10, text: async () => '{broken'}], click() {}};
    return picker;
  };
  hf.installChampionController(state, {render() {}, toast(message, error) { x.toasts.push({message, error}); }, navigate() {}, openModal() {}, celebrate() {}, api: async () => { throw new Error('Unexpected API call'); }});
  x.dispatch('click', clickTarget({championAction: 'import-workspace'}));
  await picker.onchange();
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), previous);
  assert.equal(hf.configurationKey(state.hybrid.inputs), inputKey);
  assert.equal(x.memory.has(hf.WORKSPACE_BACKUP_KEY), false);
  assert.ok(x.toasts.some(toast => toast.error));
});

test('workspace import aborts when its recovery backup cannot be written', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  hf.persistWorkspace(state);
  const previous = x.memory.get(hf.WORKSPACE_KEY), inputKey = hf.configurationKey(state.hybrid.inputs);
  const imported = {...hf.workspaceCache(state), inputs: hf.presetInputs('hospital-island')};
  let picker;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 500, text: async () => JSON.stringify(imported)}], click() {}};
    return picker;
  };
  const setItem = x.localStorage.setItem.bind(x.localStorage);
  x.localStorage.setItem = (key, value) => { if (key === hf.WORKSPACE_BACKUP_KEY) throw new Error('QuotaExceededError'); setItem(key, value); };
  hf.installChampionController(state, {render() {}, toast(message, error) { x.toasts.push({message, error}); }, navigate() {}, openModal() {}, celebrate() {}, api: async () => { throw new Error('Unexpected API call'); }});
  x.dispatch('click', clickTarget({championAction: 'import-workspace'}));
  await picker.onchange();
  x.dispatch('click', clickTarget({championAction: 'confirm-workspace-import'}));
  await flush();
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), previous);
  assert.equal(hf.configurationKey(state.hybrid.inputs), inputKey);
  assert.equal(x.memory.has(hf.WORKSPACE_BACKUP_KEY), false);
  assert.ok(x.toasts.some(toast => toast.error && /backup|quota/i.test(toast.message)));
});

test('workspace write quota failure keeps the prior cache and leaves a recovery backup', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  hf.persistWorkspace(state);
  const previous = x.memory.get(hf.WORKSPACE_KEY), inputKey = hf.configurationKey(state.hybrid.inputs);
  const imported = {...hf.workspaceCache(state), inputs: hf.presetInputs('hospital-island')};
  let picker;
  x.box.document.createElement = tag => {
    if (tag !== 'input') return {};
    picker = {files: [{size: 500, text: async () => JSON.stringify(imported)}], click() {}};
    return picker;
  };
  const setItem = x.localStorage.setItem.bind(x.localStorage);
  x.localStorage.setItem = (key, value) => { if (key === hf.WORKSPACE_KEY && String(value).includes('hospital-island')) throw new Error('QuotaExceededError'); setItem(key, value); };
  hf.installChampionController(state, {render() {}, toast(message, error) { x.toasts.push({message, error}); }, navigate() {}, openModal() {}, celebrate() {}, api: async () => { throw new Error('Unexpected API call'); }});
  x.dispatch('click', clickTarget({championAction: 'import-workspace'}));
  await picker.onchange();
  x.dispatch('click', clickTarget({championAction: 'confirm-workspace-import'}));
  await flush();
  assert.equal(x.memory.get(hf.WORKSPACE_KEY), previous);
  assert.equal(x.memory.get(hf.WORKSPACE_BACKUP_KEY), previous);
  assert.equal(state.champion.importBackupRaw, previous);
  assert.equal(hf.configurationKey(state.hybrid.inputs), inputKey);
  assert.ok(x.toasts.some(toast => toast.error && /could not be stored|quota/i.test(toast.message)));
});

test('a delayed saved-run response cannot replace a newer same-input setup selection', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: true, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  const id = 'd85c1ad4-98b3-46e1-af53-23a202435683', inputs = structuredClone(state.hybrid.inputs);
  const saved = {kind: 'hybrid', run_id: id, created_at: '2026-10-28T12:00:00.000Z', input_sha256: 'a'.repeat(64), inputs, result: structuredClone(state.hybrid.result)};
  state.champion.saved = [{id: `setup-${id}`, name: 'Newer setup selection', created_at: saved.created_at, inputs}];
  const response = deferred();
  hf.installChampionController(state, {render() {}, toast() {}, navigate() {}, openModal() {}, celebrate() {}, api: async () => response.promise});
  x.dispatch('click', clickTarget({restoreRun: id}));
  x.dispatch('click', clickTarget({loadSetup: `setup-${id}`}));
  response.resolve(saved);
  await flush();
  assert.equal(state.hybrid.result.run_id, undefined, 'the later setup selection should keep its bundled result');
  assert.equal(hf.configurationKey(state.hybrid.inputs), hf.configurationKey(inputs));
});

test('a stale workspace restore can retry pinned-run recovery after the setup changes', async () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: true, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  state.champion = hf.initialChampionState(state.hybrid);
  const id = 'f85c1ad4-98b3-46e1-af53-23a202435683', inputs = structuredClone(state.hybrid.inputs);
  const createdAt = '2026-10-28T12:00:00.000Z';
  const saved = {kind: 'hybrid', run_id: id, created_at: createdAt, input_sha256: 'b'.repeat(64), inputs, result: structuredClone(state.hybrid.result)};
  state.champion.pendingPins = [id];
  const nextInputs = {...inputs, load_kw: inputs.load_kw + 1};
  state.champion.saved = [{id: `setup-${id}`, name: 'Newer setup', created_at: createdAt, inputs: nextInputs}];
  const response = deferred();
  let calls = 0;
  const controller = hf.installChampionController(state, {render() {}, toast() {}, navigate() {}, openModal() {}, celebrate() {}, api: async () => calls++ === 0 ? response.promise : saved});
  const restoring = controller.restore();
  x.dispatch('click', clickTarget({loadSetup: `setup-${id}`}));
  response.resolve(saved);
  await restoring;
  assert.equal(state.champion.restored, false, 'a state-changed response should leave recovery retryable');
  assert.deepEqual(state.champion.pendingPins, [id], 'the stale request must keep the unresolved pin reference');
  await controller.restore();
  assert.equal(calls, 2, 'a later reconnect/recovery attempt should fetch the preserved pin again');
  assert.equal(state.champion.pendingPins.length, 0);
  assert.ok(state.hybrid.compare.some(run => run.id === id));
});

test('comparison compatibility identifies mismatched model horizons and names their limits', () => {
  const x = runtime(), hf = x.hf;
  const makeRun = (id, system, scenario) => {
    const inputs = hf.presetInputs(system, scenario), entry = hf.bundledHybridCase(inputs);
    return {id, name: `${system}/${scenario}`, inputs, result: structuredClone(entry.result)};
  };
  const runs = [makeRun('a', 'utility-pv-dc', 'baseline'), makeRun('b', 'hospital-island', 'outage-72h')];
  const contract = hf.hybridComparisonContract(runs);
  assert.equal(contract.comparable, false);
  assert.ok(contract.reasons.some(reason => /horizon/i.test(reason)));
  const markup = hf.compareView({hybrid: {compare: runs}});
  assert.match(markup, /not directly comparable|horizon mismatch/i);
  assert.match(markup, /hybrid-greedy-hourly-v1/);
});

test('comparison contract requires matching source and dataset provenance before period totals are comparable', () => {
  const x = runtime(), hf = x.hf;
  const makeRun = (id, system) => {
    const inputs = hf.presetInputs(system, 'baseline'), entry = hf.bundledHybridCase(inputs);
    const result = {...structuredClone(entry.result), source_revision: 'a'.repeat(40), dataset_revision: 'hybrid-presets-v1'};
    return {id, name: system, inputs, result};
  };
  const matching = hf.hybridComparisonContract([makeRun('a', 'utility-pv-dc'), makeRun('b', 'hospital-island')]);
  assert.equal(matching.comparable, true);
  assert.equal(matching.provenance_complete, true);
  const runs = [makeRun('a', 'utility-pv-dc'), makeRun('b', 'hospital-island')];
  runs[1].result.source_revision = 'b'.repeat(40);
  const changed = hf.hybridComparisonContract(runs);
  assert.equal(changed.comparable, false);
  assert.ok(changed.reasons.some(reason => /source revisions differ/i.test(reason)));
});

test('hybrid dispatch CSV carries the result model and input provenance on every row', () => {
  const x = runtime(), hf = x.hf;
  const state = {hybrid: hf.initialHybridState(), page: 'hybrid', connected: true, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
  hf.installHybridController(state, {render() {}, toast() {}, navigate() {}, api: async () => { throw new Error('Unexpected API call'); }, celebrate() {}, openModal() {}});
  x.dispatch('click', clickTarget({hybridAction: 'csv'}));
  assert.equal(x.downloads.length, 1);
  const csv = x.downloads[0].payload;
  for (const field of ['engine_id', 'data_kind', 'horizon_hours', 'units', 'input_sha256', 'initial_energy_kwh', 'terminal_energy_kwh', 'source_revision']) assert.ok(csv.includes(field), field);
});
