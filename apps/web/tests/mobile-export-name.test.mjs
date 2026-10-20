import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const box = vm.createContext({URL, Intl, structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8'), box);
const hf = box.HF;

for (const page of ['hybrid', 'lessons', 'compare', 'overview', 'storage', 'pv', 'research', 'markets', 'forecast', 'investment', 'pilots', 'council']) {
  test(`${page}: Export evidence retains its accessible name when its visible text span is hidden`, () => {
    const state = {page, hybrid: hf.initialHybridState(), connected: false, busy: false, data: structuredClone(hf.SNAPSHOT), marketFilter: 'ALL', search: '', chartMode: 'dispatch', forecastYears: 20, runs: [], motionOff: true};
    state.champion = hf.initialChampionState(state.hybrid);
    const button = hf.shell(state).match(/<button\b[^>]*data-action="export-evidence"[^>]*>[\s\S]*?<\/button>/)?.[0];
    assert.ok(button);
    const mobileButton = button.replace(/<span>Export evidence<\/span>/, '');
    assert.match(mobileButton, /aria-label="Export evidence"/);
    assert.match(mobileButton, /<svg[^>]*aria-hidden="true"/);
  });
}
