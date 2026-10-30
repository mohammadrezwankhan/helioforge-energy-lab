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
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-study-visuals-'));
const out = path.join(temp, 'study-visuals.js');
try {
  compileScripts([
    path.join(root, 'src/provenance-types.ts'),
    path.join(root, 'src/roadmap-types.ts'),
    path.join(root, 'src/roadmap-data.ts'),
    path.join(root, 'src/advanced-visuals.ts'),
    path.join(root, 'src/study-visuals.ts'),
  ], out);
} catch (error) {
  throw new Error(`Could not compile study visual sources: ${error.stderr?.toString() ?? error.message}`);
}
const context = vm.createContext({
  URL, Intl, Number, String, Math, Array, Object, JSON, Set, Map,
  structuredClone, console,
});
vm.runInContext(fs.readFileSync(out, 'utf8'), context);
const hf = context.HF;

const definition = (id, page, data_fields = []) => ({
  id, page, title: 'Example study', summary: 'Actual supplied records', fields: [],
  data_fields, equations: [], limitations: [], sources: [],
});
const result = (study, table = [], extra = {}) => ({
  study, model_version: 'roadmap-screen-v1', inputs: {}, data_kind: 'synthetic_or_user_supplied_unverified',
  metrics: [], series: [], table, warnings: [], equations: [], limitations: [], sources: [],
  evidence_sha256: 'abc', ...extra,
});

test('PV sensitivity renders all 81 actual Python LCOE cells as titled accessible controls', () => {
  const def = hf.STUDY_BUNDLE.catalogue.find((entry) => entry.id === 'pv-sensitivity');
  const actual = hf.STUDY_BUNDLE.results['pv-sensitivity'];
  const html = hf.studyVisual(def, actual, 0);
  assert.equal((html.match(/data-pv-cell=/g) ?? []).length, 81);
  assert.match(html, /role="img"/);
  assert.match(html, /74\.971/);
  assert.match(html, /33\.944/);
  assert.match(html, /CAPEX/);
});

test('all default roadmap study results produce accessible finite visual markup', () => {
  const { catalogue, results } = hf.STUDY_BUNDLE;
  assert.equal(catalogue.length, 59);
  for (const def of catalogue) {
    const html = hf.studyVisual(def, results[def.id], 0);
    assert.match(html, /role="img"/, def.id);
    assert.doesNotMatch(html, /NaN|Infinity/, def.id);
  }
});

test('forecast tunnel and investment covenant use actual table values and keep null DSCR gaps', () => {
  const forecastDef = definition('forecast-regimes', 'forecast');
  const forecast = result('forecast-regimes', [
    { year: 1, p10_eur_mwh: 10, p50_eur_mwh: 20, p90_eur_mwh: 30 },
    { year: 2, p10_eur_mwh: 11, p50_eur_mwh: 21, p90_eur_mwh: 31 },
  ]);
  const tunnel = hf.studyVisual(forecastDef, forecast, 1);
  assert.match(tunnel, /Selected year 2: P10 11 EUR\/MWh, P50 21 EUR\/MWh, P90 31 EUR\/MWh/);

  const financeDef = definition('investment-sculpt', 'investment');
  const finance = result('investment-sculpt', [
    { year: 1, cfads_eur: 100, debt_service_eur: 70, dscr: 1.429 },
    { year: 2, cfads_eur: 0, debt_service_eur: 50, dscr: null },
  ], { metrics: [{ label: 'Minimum DSCR', value: 1.3, unit: 'ratio' }] });
  const plane = hf.studyVisual(financeDef, finance, 0);
  assert.match(plane, /Actual covenant: 1\.3 DSCR/);
  assert.match(plane, /Year 2: DSCR Missing/);
  assert.match(plane, /CFADS minus debt service, derived/);
  assert.match(plane, /shared scale · zero baseline/);
  assert.match(plane, /y="36" width="5" height="102"/);
  assert.match(plane, /y="138" width="5" height="51"/);
  assert.match(plane, /CFADS minus debt service \(derived\) -?50 EUR/);
});

test('interconnection price pillars preserve negative prices on a shared zero-baseline scale', () => {
  const def = definition('markets-interconnection', 'markets');
  const actual = result('markets-interconnection', [
    { interval: 1, flow_a_to_b_mw: 2, zone_a_marginal_price_eur_mwh: 100, zone_b_marginal_price_eur_mwh: -50 },
    { interval: 2, flow_a_to_b_mw: -1, zone_a_marginal_price_eur_mwh: 200, zone_b_marginal_price_eur_mwh: -100 },
  ], { inputs: { capacity_mw: 5 } });
  const html = hf.studyVisual(def, actual, 0);
  assert.match(html, /zero baseline and a scale spanning all recorded prices/);
  assert.match(html, /Zone B: -50 EUR\/MWh/);
  assert.match(html, /y="150" width="68" height="21"/);
  assert.match(html, /viewBox="0 0 640 280"/);
});

test('a polygon with a null vertex is marked missing instead of silently redrawn without that vertex', () => {
  const def = definition('pv-agrivoltaic', 'pv', [{ name: 'land_polygon_m', default: [[0, 0], [100, 0], [100, 50], [0, 50]] }]);
  const actual = result('pv-agrivoltaic', [], { inputs: { land_polygon_m: [[0, 0], [100, 0], null, [0, 50]] } });
  const html = hf.studyVisual(def, actual, 0);
  assert.match(html, /data-state="missing"/);
  assert.match(html, /null or malformed vertex/);
  assert.doesNotMatch(html, /<polygon data-land-polygon/);
});

test('missing values stay visible as missing and untrusted labels are escaped', () => {
  const def = definition('pv-sensitivity', 'pv');
  def.title = '<ScRiPt>bad()</ScRiPt>';
  const html = hf.studyVisual(def, result('pv-sensitivity', [
    { capex_eur_kwp: 650, yield_kwh_kwp: 1350, lcoe_eur_mwh: null },
  ]), 0);
  assert.doesNotMatch(html, /<script(?:\s|>)/i);
  assert.match(html, /&lt;ScRiPt&gt;bad\(\)&lt;\/ScRiPt&gt;/);
  assert.match(html, /Missing/);
  assert.match(html, /data-state="missing"/);
});

test('polygon clicks convert SVG coordinates to local metres and undo restores vertices', () => {
  const input = [[0, 0], [100, 0], [100, 50], [0, 50]];
  const listeners = new Map();
  const attributes = {};
  const map = {
    getBoundingClientRect: () => ({ left: 10, top: 20, width: 500, height: 260 }),
    addEventListener: (name, listener) => listeners.set(`map:${name}`, listener),
    removeEventListener: (name) => listeners.delete(`map:${name}`),
  };
  const polygon = { setAttribute: (name, value) => { attributes[name] = value; } };
  const button = (action) => ({
    dataset: { polygonAction: action },
    addEventListener: (name, listener) => listeners.set(`${action}:${name}`, listener),
    removeEventListener: (name) => listeners.delete(`${action}:${name}`),
  });
  const undo = button('undo');
  const reset = button('reset');
  const host = {
    querySelector: (selector) => selector === '[data-land-map]' ? map
      : selector === '[data-land-polygon]' ? polygon : null,
    querySelectorAll: (selector) => selector === '[data-polygon-action]' ? [undo, reset] : [],
  };
  const def = definition('pv-agrivoltaic', 'pv', [{ name: 'land_polygon_m', default: input }]);
  const draft = { id: def.id, values: {}, result: result(def.id), dirty: false, busy: false, error: '', slice: 0, selectedSeries: 0 };
  const emitted = [];
  const dispose = hf.bindStudyVisuals(host, def, draft, (name, value) => emitted.push([name, value]));
  listeners.get('map:click')({ clientX: 260, clientY: 147.5 });
  const added = JSON.parse(emitted.at(-1)[1]);
  assert.deepEqual(added.at(-1), [50, 25]);
  assert.equal(added.length, 5);
  listeners.get('undo:click')({ preventDefault() {} });
  assert.deepEqual(JSON.parse(emitted.at(-1)[1]), input);
  assert.ok(attributes.points);
  dispose();
});

test('annual tariff sliders emit the existing tariff data field as a JSON array', () => {
  const listeners = new Map();
  const tariff = Array(24).fill(0.1);
  const sliders = tariff.map((value, hour) => ({
    value: String(value), dataset: { tariffHour: String(hour) },
    addEventListener: (name, listener) => listeners.set(`${hour}:${name}`, listener),
    removeEventListener: (name) => listeners.delete(`${hour}:${name}`),
  }));
  const host = { querySelectorAll: (selector) => selector === '[data-tariff-hour]' ? sliders : [], querySelector: () => null };
  const def = definition('storage-annual', 'storage', [{ name: 'tariff', default: tariff }]);
  const draft = { id: def.id, values: {}, result: result(def.id), dirty: false, busy: false, error: '', slice: 0, selectedSeries: 0 };
  const emitted = [];
  const dispose = hf.bindStudyVisuals(host, def, draft, (name, value) => emitted.push([name, value]));
  sliders[16].value = '0.37';
  listeners.get('16:input')({ currentTarget: sliders[16] });
  assert.equal(emitted.at(-1)[0], 'tariff');
  const parsed = JSON.parse(emitted.at(-1)[1]);
  assert.equal(parsed.length, 24);
  assert.equal(parsed[16], 0.37);
  dispose();
});
