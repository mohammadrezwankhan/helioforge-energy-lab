import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8');

test('all 59 studies disable comparison and exports immediately on numeric or JSON edits, then restore them on reset', () => {
  const events = new Map(), nodes = new Map();
  class Node {
    constructor() { this.dataset = {}; this.disabled = false; this.hidden = false; this.classList = {toggle() {}}; }
    closest() { return this; }
    hasAttribute(name) { return name === 'data-study-json' && this.json === true; }
    querySelector(selector) { return selector === '[data-study-jump]' ? this : null; }
    before(node) { nodes.set(node.id, node); }
    append(node) { nodes.set(node.id, node); }
  }
  const document = {
    getElementById(id) { return nodes.get(id) ?? null; },
    createElement() { return new Node(); },
    querySelector() { return null; },
    querySelectorAll(selector) { return [selector.includes('[data-study-export]') ? nodes.get('export') : null, selector.includes('[data-study-action="pin"]') ? nodes.get('pin') : null].filter(Boolean); },
    addEventListener(type, callback) { const list = events.get(type) ?? []; list.push(callback); events.set(type, list); },
  };
  const box = vm.createContext({URL, Intl, structuredClone, CSS: {escape: value => value}});
  vm.runInContext(code, box);
  box.document = document;
  const hf = box.HF;
  hf.studyVisual = () => '';
  hf.bindStudyVisuals = () => () => {};
  const state = {page: 'overview', connected: false};
  for (const id of ['page-content', 'study-workbench', 'study-status', 'study-output', 'export', 'pin']) nodes.set(id, new Node());
  const controller = hf.createStudyController(() => state);
  const fire = (type, target) => { for (const callback of events.get(type) ?? []) callback({target, preventDefault() {}}); };
  for (const def of hf.STUDY_BUNDLE.catalogue) {
    state.page = def.page;
    const select = new Node(); select.dataset.studySelect = def.id; fire('click', select);
    assert.equal(nodes.get('pin').disabled, false, `${def.id} initial pin`);
    for (const field of [def.fields[0], def.data_fields?.[0]].filter(Boolean)) {
      const input = new Node(); input.name = field.name; input.json = !('min' in field);
      input.value = input.json ? JSON.stringify(field.default) + ' ' : String(field.default === field.max ? field.min : Math.min(field.max, field.default + field.step));
      fire('input', input);
      assert.equal(nodes.get('study-output').hidden, true, `${def.id}/${field.name} stale result`);
      assert.equal(nodes.get('export').disabled, true, `${def.id}/${field.name} export`);
      assert.equal(nodes.get('pin').disabled, true, `${def.id}/${field.name} pin`);
      const reset = new Node(); reset.dataset.studyAction = 'reset'; fire('click', reset);
      assert.equal(nodes.get('study-output').hidden, false, `${def.id} reset result`);
      assert.equal(nodes.get('pin').disabled, false, `${def.id} reset pin`);
      assert.equal(nodes.get('export').disabled, false, `${def.id} reset export`);
    }
  }
  assert.equal(hf.STUDY_BUNDLE.catalogue.length, 59);
  controller.refresh();
});
