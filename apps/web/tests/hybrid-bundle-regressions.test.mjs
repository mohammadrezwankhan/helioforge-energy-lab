import test from 'node:test';
import assert from 'node:assert/strict';
import {controllerFixture} from './helpers/controller-fixture.mjs';

const action = (x, dataset) => { const button = new x.Button(''); Object.assign(button.dataset, dataset); x.dispatch('click', button); };

test('the frozen archive covers exactly all 285 numerical presets and excludes 349 study and 230 inapplicable pairs', () => {
  const {hf} = controllerFixture();
  assert.equal(hf.HYBRID_BUNDLE.schema, 'helioforge.hybrid-bundle.v1');
  assert.equal(hf.HYBRID_BUNDLE.catalogue_version, hf.HYBRID_CATALOG.version);
  assert.match(hf.HYBRID_BUNDLE.dataset_sha256, /^[a-f0-9]{64}$/);
  assert.equal(hf.HYBRID_BUNDLE.cases.length, 285);
  let numerical = 0, study = 0, inapplicable = 0;
  for (const system of hf.HYBRID_CATALOG.systems) for (const scenario of hf.HYBRID_CATALOG.scenarios) {
    const eligible = hf.applicable(system, scenario);
    if (!eligible) { inapplicable++; assert.equal(hf.bundledHybridCase({...system.preset, scenario_id: scenario.id}), null); continue; }
    const inputs = hf.presetInputs(system.id, scenario.id), entry = hf.bundledHybridCase(inputs);
    if (system.mode === 'study' || scenario.mode === 'study') { study++; assert.equal(entry, null); continue; }
    numerical++;
    assert.ok(entry, `${system.id}/${scenario.id}`);
    assert.equal(hf.configurationKey(entry.inputs), hf.configurationKey(inputs));
    assert.equal(entry.result.schedule.length, inputs.hours);
    assert.equal(entry.result.bundle_case_id, entry.id);
    assert.equal(entry.result.run_id, undefined);
    assert.match(entry.result.input_sha256, /^[a-f0-9]{64}$/);
    assert.equal(hf.bundledHybridCase({...inputs, load_kw: inputs.load_kw + 1}), null);
    assert.equal(hf.bundledHybridCase(Object.fromEntries(Object.entries(inputs).reverse())), entry);
  }
  assert.deepEqual([numerical, study, inapplicable], [285, 349, 230]);
});

test('every architecture and applicable scenario selects its exact bundled result or explicit study boundary without an API call', () => {
  const x = controllerFixture();
  for (const system of x.hf.HYBRID_CATALOG.systems) {
    action(x, {system: system.id});
    for (const scenario of x.hf.HYBRID_CATALOG.scenarios.filter(s => x.hf.applicable(system, s))) {
      action(x, {scenario: scenario.id});
      const h = x.state.hybrid;
      assert.equal(x.hf.configurationKey(h.inputs), x.hf.configurationKey(x.hf.presetInputs(system.id, scenario.id)));
      const html = x.hf.hybridResults(x.state);
      if (system.mode === 'screening' && scenario.mode === 'screening') {
        assert.equal(h.result?.system_id, system.id);
        assert.equal(h.result?.scenario_id, scenario.id);
        assert.equal(x.hf.hybridDirty(h), false);
        assert.match(html, /hybrid-metrics/);
        assert.match(html, /Bundled Python preset/);
      } else {
        assert.equal(h.result, null);
        assert.match(html, /STUDY-ONLY/);
        assert.ok(!html.includes('hybrid-metrics'));
      }
    }
  }
});

test('edits hide results, reset restores the baseline, and all 36 lesson loads use exact preset identity', () => {
  const x = controllerFixture(), h = x.state.hybrid;
  for (const lesson of x.hf.HYBRID_CATALOG.lessons) {
    h.lessonId = lesson.id;
    action(x, {hybridAction: 'launch-lesson'});
    assert.equal(x.hf.configurationKey(h.inputs), x.hf.configurationKey(x.hf.presetInputs(lesson.system_id, lesson.scenario_id)));
    assert.equal(Boolean(h.result), Boolean(x.hf.bundledHybridCase(h.inputs)));
  }
  action(x, {system: 'hospital-island'});
  h.inputs.load_kw += 1;
  assert.ok(!x.hf.hybridResults(x.state).includes('hybrid-metrics'));
  action(x, {scenario: 'outage-72h'});
  assert.equal(h.result, null, 'a scenario change must not relabel custom inputs as a preset');
  action(x, {hybridAction: 'reset'});
  assert.equal(h.result.scenario_id, 'baseline');
  assert.equal(h.inputs.hours, 24);
});

test('three distinct bundled cases can be pinned and compared without fabricated API run IDs', () => {
  const x = controllerFixture();
  action(x, {system: 'hospital-island'});
  for (const scenario of ['baseline', 'outage-4h', 'outage-72h']) {
    action(x, {scenario}); action(x, {hybridAction: 'pin'});
  }
  assert.equal(x.state.hybrid.compare.length, 3);
  assert.equal(new Set(x.state.hybrid.compare.map(run => run.id)).size, 3);
  assert.ok(x.state.hybrid.compare.every(run => !run.result.run_id));
  assert.match(x.hf.compareView(x.state), /3 pinned runs/);
});

test('a restored exact workspace shows a bundled preset while changed inputs retain an empty result', () => {
  const x = controllerFixture(), hf = x.hf;
  x.state.hybrid.inputs = hf.presetInputs('utility-pv-dc', 'baseline');
  hf.persistWorkspace(x.state);
  const next = hf.initialHybridState(); hf.initialChampionState(next);
  assert.equal(next.result.system_id, 'utility-pv-dc');
  assert.equal(next.result.run_id, undefined);
  next.inputs.load_kw += 1;
  x.state.hybrid = next; hf.persistWorkspace(x.state);
  const edited = hf.initialHybridState(); hf.initialChampionState(edited);
  assert.equal(edited.result, null);
});

test('imported exact configurations attach a preset; modified imports do not', async () => {
  const x = controllerFixture();
  for (const changed of [false, true]) {
    const inputs = x.hf.presetInputs('hospital-island', 'outage-4h');
    if (changed) inputs.load_kw += 1;
    let imported;
    const file = new x.Button('');
    file.files = [{size: 2000, text: async () => JSON.stringify({schema: 'helioforge.hybrid.v1', inputs})}];
    file.click = () => { imported = file.onchange(); };
    x.document.createElement = () => file;
    action(x, {hybridAction: 'import'});
    await imported;
    assert.equal(Boolean(x.state.hybrid.result), !changed);
    assert.equal(x.hf.configurationKey(x.state.hybrid.inputs), x.hf.configurationKey(inputs));
  }
});

test('named setups, command selection and the guided hospital start restore matching bundled presets', () => {
  const x = controllerFixture();
  x.hf.installChampionController(x.state, {render() {}, toast() {}, navigate() {}, openModal() {}, celebrate() {}, api: async () => { throw new Error('Unexpected API request'); }});
  const id = 'setup-d85c1ad4-98b3-46e1-af53-23a202435683';
  x.state.champion.saved = [{id, name: 'Example', created_at: '2026-10-20T12:00:00Z', inputs: x.hf.presetInputs('utility-pv-dc')}];
  action(x, {loadSetup: id});
  assert.equal(x.state.hybrid.result.system_id, 'utility-pv-dc');
  action(x, {commandKind: 'system', commandTarget: 'industrial-btm'});
  assert.equal(x.state.hybrid.result.system_id, 'industrial-btm');
  action(x, {championAction: 'start-hospital'});
  assert.equal(x.state.hybrid.result.system_id, 'hospital-island');
  x.state.champion.saved[0].inputs.load_kw += 1;
  action(x, {loadSetup: id});
  assert.equal(x.state.hybrid.result, null);
});
