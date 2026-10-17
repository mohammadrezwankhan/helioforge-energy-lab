import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const sandbox = vm.createContext({ URL, Intl, Number, String, Math, Array, Object, JSON, Set, structuredClone });
const bundlePath = process.env.HELIOFORGE_SCENE_TEST_BUNDLE ?? new URL('../dist/app.js', import.meta.url);
vm.runInContext(fs.readFileSync(bundlePath, 'utf8'), sandbox);
const h = sandbox.HF;
test('asset telemetry preserves power direction and absent data',()=>{
 const p={pv_kw:10,wind_kw:3,hydro_kw:0,generator_kw:1,charge_kw:4,discharge_kw:0,grid_import_kw:0,grid_export_kw:2,served_kw:8};
 assert.equal(h.sceneAssetPower(p,'battery'),-4);assert.equal(h.sceneAssetPower(p,'load'),-8);
 assert.equal(h.sceneAssetPower(p,'grid'),-2);assert.equal(h.sceneAssetPower(p,'solar'),10);
 assert.equal(h.sceneAssetPower(null,'solar'),null);assert.equal(h.sceneAssetPower(p,'electrolyzer'),null);
});

test('camera presets use distinct, defined orthographic views', () => {
  const iso = h.scenePresetState('isometric');
  const top = h.scenePresetState('top-down');
  const oblique = h.scenePresetState('oblique');
  const wireframe = h.scenePresetState('wireframe');

  assert.equal(iso.preset, 'isometric');
  assert.equal(iso.yaw, -Math.PI / 4);
  assert.equal(iso.pitch, 35 * Math.PI / 180);
  assert.equal(iso.zoom, 1);
  assert.equal(iso.wireframe, false);

  assert.equal(top.preset, 'top-down');
  assert.equal(top.pitch, Math.PI / 2);
  assert.equal(top.wireframe, false);

  assert.equal(oblique.preset, 'oblique');
  assert.ok(oblique.pitch > 0 && oblique.pitch < iso.pitch);
  assert.notEqual(oblique.yaw, iso.yaw);
  assert.equal(oblique.wireframe, false);

  assert.equal(wireframe.preset, 'wireframe');
  assert.equal(wireframe.wireframe, true);
  assert.equal(wireframe.pitch, iso.pitch);
  assert.equal(h.scenePresetState('unknown'), null);
});

test('hybrid scene exposes four keyboard accessible camera preset buttons', () => {
  const state = {
    hybrid: h.initialHybridState(), page: 'hybrid', connected: true, busy: false,
    data: h.SNAPSHOT, marketFilter: 'ALL', search: '', chartMode: 'dispatch',
    forecastYears: 20, runs: [], motionOff: false,
  };
  const html = h.hybridView(state);
  for (const preset of ['isometric', 'top-down', 'oblique', 'wireframe']) {
    assert.match(html, new RegExp(`data-camera-preset="${preset}"`));
    assert.match(html, new RegExp(`data-scene-command="${preset}"`));
  }
  assert.match(html, /data-camera-preset="isometric"[^>]*aria-pressed="true"/);
});

test('scene mount returns a safe disposer when Canvas2D is unavailable', () => {
  const dispose = h.mountEnergyScene({ getContext: () => null }, h.systemById('remote-triad'), false, () => {});
  assert.equal(typeof dispose, 'function');
  assert.doesNotThrow(() => dispose());
});
