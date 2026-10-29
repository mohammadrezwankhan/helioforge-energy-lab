import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {compileScripts} from '../../../scripts/compile-web.mjs';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-advanced-visuals-'));
const out = path.join(temp, 'advanced-visuals.js');
try {
  compileScripts([
    path.join(root, 'src/provenance-types.ts'),
    path.join(root, 'src/roadmap-types.ts'),
    path.join(root, 'src/roadmap-data.ts'),
    path.join(root, 'src/advanced-visuals.ts'),
  ], out);
} catch (error) {
  throw new Error(`Could not compile advanced visual sources: ${error.stderr?.toString() || error.stdout?.toString() || error.message}`);
}
const context = vm.createContext({
  URL, Intl, Number, String, Math, Array, Object, JSON, Set, Map,
  structuredClone, console,
});
vm.runInContext(fs.readFileSync(out, 'utf8'), context);
const hf = context.HF;
const { catalogue, results } = hf.STUDY_BUNDLE;
const definition = (id, page = 'test') => catalogue.find((entry) => entry.id === id)
  ?? { id, page, title: id, summary: '', fields: [], equations: [], limitations: [], sources: [] };

test('four geometry-specific studies render from the bundled Python result contract', () => {
  for (const id of ['hybrid-powerflow', 'markets-network', 'pv-raytrace', 'pilots-registration']) {
    const html = hf.advancedStudyVisual(definition(id), results[id], 0);
    assert.equal(typeof html, 'string', `${id} must own a specialized view`);
    assert.match(html, /role="img"/, id);
    assert.match(html, /aria-labelledby=/, id);
    assert.match(html, /Synthetic or user-supplied data · unverified/, id);
    assert.doesNotMatch(html, /NaN|Infinity|undefined/, id);
  }
  assert.equal(hf.advancedStudyVisual(definition('not-specialized'), results['hybrid-powerflow'], 0), null);
});

test('power-flow visual projects actual solved voltage_pu and signed from_p_mw rows', () => {
  const result = results['hybrid-powerflow'];
  const projected = hf.advancedProjectPowerflow(result);
  assert.ok(projected);
  assert.equal(projected.buses.length, result.details.buses.length);
  assert.equal(projected.buses[0].voltage, result.details.buses[0].voltage_pu);
  assert.equal(projected.branches[0].activeMw, result.details.branches[0].from_p_mw);
  const html = hf.advancedStudyVisual(definition('hybrid-powerflow'), result, 0);
  assert.match(html, /inverse-distance interpolation/);
  assert.match(html, /not a solved spatial field/);
  assert.match(html, /Schematic node layout/);
  assert.match(html, /hfav-flow-particle/);
  assert.match(html, /from_p_mw/);
});

test('six-zone network shows actual signed line flows and does not imply a real map', () => {
  const result = structuredClone(results['markets-network']);
  result.details.line_flows = [{ from_zone: 'North', to_zone: 'South', flow_mw: -12.5, limit_mw: 20 }];
  const projected = hf.advancedProjectMarketsNetwork(result);
  assert.ok(projected);
  assert.equal(projected.zones.length, 6);
  assert.deepEqual(JSON.parse(JSON.stringify(projected.flows)), [{ from: 'North', to: 'South', flowMw: -12.5, limitMw: 20 }]);
  const html = hf.advancedStudyVisual(definition('markets-network'), result, 0);
  assert.match(html, /-12\.5 MW/);
  assert.match(html, /not a geographic map/);
  assert.match(html, /nodal price/);
});

test('PV projection uses submitted geometry and result shading rows; default missing triangles stay missing', () => {
  const bundled = results['pv-raytrace'];
  const defaultHtml = hf.advancedStudyVisual(definition('pv-raytrace'), bundled, 0);
  assert.match(defaultHtml, /No terrain or obstacle triangles were supplied/);
  const result = structuredClone(bundled);
  result.inputs.panel_samples = [{ position_m: [1, 2, 0], normal: [0, 0, 1], area_m2: 2 }];
  result.inputs.sun_vectors = [{ direction: [0, 0, 1], dni_w_m2: 700, duration_h: 1 }];
  result.inputs.occluder_triangles = [[[1, 2, 1], [3, 2, 1], [1, 4, 1]]];
  result.table = [{ panel_index: 0, sun_index: 0, shaded: true, energy_wh: 0 }];
  const projected = hf.advancedProjectPvRaytrace(result);
  assert.ok(projected);
  assert.deepEqual(JSON.parse(JSON.stringify(projected.triangles)), [[[1, 2, 1], [3, 2, 1], [1, 4, 1]]]);
  assert.equal(projected.rays[0].shaded, true);
  const html = hf.advancedStudyVisual(definition('pv-raytrace'), result, 0);
  assert.match(html, /hfav-terrain-triangle/);
  assert.match(html, /S1: shaded/);
  assert.match(html, /relative geometry/);
  assert.match(html, /do not encode a measured distance/);
});

test('ICP aligned survey points use supplied rigid transform and correspondence membership', () => {
  const result = results['pilots-registration'];
  const projected = hf.advancedProjectRegistration(result);
  assert.ok(projected);
  assert.equal(projected.design.length, result.inputs.design_points_xyz.length);
  assert.equal(projected.alignedSurvey.length, result.inputs.survey_points_xyz.length);
  assert.equal(projected.matches.filter((match) => match.inlier).length, result.details.inlier_count);
  const first = projected.alignedSurvey[0];
  const target = projected.design[projected.matches.find((match) => match.surveyIndex === 0).designIndex];
  assert.ok(Math.hypot(...first.map((coordinate, i) => coordinate - target[i])) < 1e-8);
  const html = hf.advancedStudyVisual(definition('pilots-registration'), result, 0);
  assert.match(html, /hfav-match-inlier/);
  assert.match(html, /no georeferencing/);
  assert.match(html, /photosUsed|photo/);
  const connector = html.match(/class="hfav-match-inlier" x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"/);
  assert.ok(connector, 'an actual retained correspondence should be drawn');
  assert.equal(connector[1], connector[3], 'aligned inlier and design point share an x projection');
  assert.equal(connector[2], connector[4], 'aligned inlier and design point share a y projection');
});

test('visual input bounds stay finite at 100 geometry points and malformed result states are explicit', () => {
  const pv = structuredClone(results['pv-raytrace']);
  pv.inputs.panel_samples = Array.from({ length: 25 }, () => ({ position_m: [0, 0, 0], normal: [0, 0, 1], area_m2: 1 }));
  pv.inputs.sun_vectors = Array.from({ length: 48 }, () => ({ direction: [0, 0, 1], dni_w_m2: 500, duration_h: 1 }));
  pv.inputs.occluder_triangles = Array.from({ length: 50 }, () => [[0, 0, 1], [1, 0, 1], [0, 1, 1]]);
  pv.table = [];
  const bounded = hf.advancedProjectPvRaytrace(pv);
  assert.equal(bounded.triangles.length, 20);
  assert.equal(bounded.panels.length, 10);
  assert.equal(bounded.rays.length, 10);
  assert.ok(bounded.triangles.length * 3 + bounded.panels.length * 2 + bounded.rays.length * 2 <= 100);
  const html = hf.advancedStudyVisual(definition('pv-raytrace'), pv, 0);
  assert.match(html, /capped at 100 geometry points/);
  assert.doesNotMatch(html, /NaN|Infinity/);

  const registration = structuredClone(results['pilots-registration']);
  registration.inputs.design_points_xyz = Array.from({ length: 120 }, (_, index) => [index, index % 7, index % 11]);
  registration.inputs.survey_points_xyz = Array.from({ length: 120 }, (_, index) => [index, index % 7, index % 11]);
  registration.details.rotation_matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  registration.details.translation_m = [0, 0, 0];
  registration.table = [];
  const boundedCloud = hf.advancedProjectRegistration(registration);
  assert.equal(boundedCloud.design.length, 50);
  assert.equal(boundedCloud.alignedSurvey.length, 50);
  assert.equal(boundedCloud.designCount, 120);
  assert.match(hf.advancedStudyVisual(definition('pilots-registration'), registration, 0), /Display limited to the first 50/);

  const missing = structuredClone(results['hybrid-powerflow']);
  missing.details.buses = [{ bus_id: 'missing-voltage', voltage_pu: Number.NaN }];
  missing.details.branches = [];
  assert.equal(hf.advancedProjectPowerflow(missing), null);
  assert.match(hf.advancedStudyVisual(definition('hybrid-powerflow'), missing, 0), /Required result data missing/);
});

test('untrusted labels are escaped and missing point-cloud fields do not create coordinates', () => {
  const powerflow = structuredClone(results['hybrid-powerflow']);
  powerflow.details.buses = [{ bus_id: '<img src=x>', voltage_pu: 1 }];
  powerflow.details.branches = [];
  const html = hf.advancedStudyVisual(definition('hybrid-powerflow'), powerflow, 0);
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img src=x&gt;/);
  const registration = structuredClone(results['pilots-registration']);
  delete registration.inputs.design_points_xyz;
  assert.equal(hf.advancedProjectRegistration(registration), null);
  assert.match(hf.advancedStudyVisual(definition('pilots-registration'), registration, 0), /Required result data missing/);
});

test.after(() => fs.rmSync(temp, { recursive: true, force: true }));
