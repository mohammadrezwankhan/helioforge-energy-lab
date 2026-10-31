import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
import {compileScripts} from '../../../scripts/compile-web.mjs';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const config = JSON.parse(fs.readFileSync(path.join(root, 'tsconfig.json'), 'utf8'));
const workflowIndex = config.files.indexOf('src/workflows.ts');
assert.notEqual(workflowIndex, -1, 'workflow source must remain in the declared bundle order');
const sourceFiles = [
  ...config.files.slice(0, workflowIndex + 1).map(file => path.join(root, file)),
  path.join(root, 'src/completion-ui.ts'),
];
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-workflow-readiness-'));
const bundle = path.join(temp, 'workflows.js');
try {
  compileScripts(sourceFiles, bundle);
} catch (error) {
  throw new Error(`Could not compile workflow source: ${error.stderr?.toString() || error.stdout?.toString() || error.message}`);
}

const downloads = [];
class CapturingURL extends URL {
  static createObjectURL(blob) {
    downloads.push(blob);
    return `blob:workflow-test-${downloads.length}`;
  }
  static revokeObjectURL() {}
}
class TestElement {
  constructor(action) { this.dataset = {workflowAction: action}; }
  closest() { return this; }
}

const listeners = new Map();
const status = {textContent: ''};
const toast = {textContent: '', className: 'toast', classList: {remove() {}}};
const host = {
  markup: '',
  insertAdjacentHTML(_position, markup) { this.markup = markup; },
};
const document = {
  addEventListener(type, listener) { listeners.set(type, listener); },
  getElementById(id) {
    if (id === 'page-content') return host;
    if (id === 'workflow-research-status') return status;
    if (id === 'toast') return toast;
    return null;
  },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  createElement() { return {click() {}}; },
};
const context = vm.createContext({
  URL: CapturingURL, Blob, Intl, Number, String, Math, Array, Object, JSON, Set, Map, Date,
  structuredClone, crypto: webcrypto, TextEncoder, Uint8Array, btoa, atob,
  document, Element: TestElement, setTimeout() { return 0; },
});
vm.runInContext(fs.readFileSync(bundle, 'utf8'), context);
const hf = context.HF;

test('research dossier waits for every bundled research result, then exports complete evidence', async () => {
  downloads.length = 0;
  const researchIds = hf.STUDY_BUNDLE.catalogue.filter(def => def.page === 'research').map(def => def.id);
  assert.ok(researchIds.length > 0);
  const pendingId = researchIds[0];
  const pendingResult = hf.STUDY_BUNDLE.results[pendingId];
  delete hf.STUDY_BUNDLE.results[pendingId];

  try {
    const state = {
      hybrid: hf.initialHybridState(), page: 'research', connected: false, busy: false,
      data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch',
      forecastYears: 20, runs: [], motionOff: false,
    };
    const controller = hf.createWorkflowController(() => state, () => {});
    controller.refresh();

    assert.match(host.markup, /Research study results are loading/);
    assert.match(host.markup, /<button[^>]*data-workflow-action="research-dossier"[^>]*disabled/);
    const click = listeners.get('click');
    click({target: new TestElement('research-dossier'), preventDefault() {}});
    assert.equal(downloads.length, 0, 'a stale click cannot create a dossier while any research result is absent');
    assert.match(status.textContent, /still loading/);
    assert.match(toast.textContent, /still loading/);

    hf.STUDY_BUNDLE.results[pendingId] = pendingResult;
    controller.refresh();
    assert.doesNotMatch(host.markup, /Research study results are loading/);
    assert.doesNotMatch(host.markup, /data-workflow-action="research-dossier"[^>]*disabled/);
    click({target: new TestElement('research-dossier'), preventDefault() {}});
    assert.equal(downloads.length, 1, 'a dossier is created after every research result is available');

    const markdown = await downloads[0].text();
    const start = markdown.indexOf('## Bundled study evidence\n```json\n') + '## Bundled study evidence\n```json\n'.length;
    const end = markdown.indexOf('\n```', start);
    const studies = JSON.parse(markdown.slice(start, end));
    assert.equal(studies.length, researchIds.length);
    assert.ok(studies.every(study => study.result !== null), 'the dossier contains no null research study placeholders');
  } finally {
    hf.STUDY_BUNDLE.results[pendingId] = pendingResult;
  }
});
