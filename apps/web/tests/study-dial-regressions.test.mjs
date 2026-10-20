import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const box = vm.createContext({URL, Intl, structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8'), box);
const hf = box.HF;

test('every numeric study input preserves its exact default in its paired range', () => {
  let fields = 0;
  for (const def of hf.STUDY_BUNDLE.catalogue) {
    const markup = hf.studyForm(def, {values: {}, busy: false}, false);
    for (const field of def.fields) {
      const input = markup.match(new RegExp(`<input type="number" name="${field.name}"[^>]+>`))?.[0];
      const dial = markup.match(new RegExp(`<input type="range" data-study-dial="${field.name}"[^>]+>`))?.[0];
      assert.ok(input && dial, `${def.id}/${field.name}`);
      assert.match(dial, /step="any"/);
      assert.equal(Number(input.match(/value="([^"]+)"/)[1]), field.default);
      assert.equal(Number(dial.match(/value="([^"]+)"/)[1]), field.default);
      assert.ok(dial.includes(`data-study-step="${field.step}"`));
      fields++;
    }
  }
  assert.equal(fields, 296);
});

test('range keyboard increments preserve scientific defaults and respect endpoints', () => {
  assert.equal(hf.studyDialNextValue(0.08, 0.001, 1, 0.01, 'ArrowRight'), 0.09);
  assert.equal(hf.studyDialNextValue(1e-9, 0, 1e-6, 1e-9, 'ArrowUp'), 2e-9);
  assert.equal(hf.studyDialNextValue(Math.PI * 100, 1, 500, 1, 'ArrowLeft'), Math.PI * 100 - 1);
  assert.equal(hf.studyDialNextValue(0.99, 0.001, 1, 0.1, 'ArrowRight'), 1);
  assert.equal(hf.studyDialNextValue(0.02, 0.001, 1, 0.1, 'ArrowDown'), 0.001);
  assert.equal(hf.studyDialNextValue(0.08, 0.001, 1, 0.01, 'Home'), 0.001);
  assert.equal(hf.studyDialNextValue(0.08, 0.001, 1, 0.01, 'End'), 1);
  assert.equal(hf.studyDialNextValue(0.08, 0.001, 1, 0.01, 'Tab'), null);
});
