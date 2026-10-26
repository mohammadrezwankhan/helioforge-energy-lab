import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'helioforge-terminal-'));
const compiler = fileURLToPath(new URL('../node_modules/typescript/bin/tsc', import.meta.url));
const source = fileURLToPath(new URL('../src/terminal-engine.ts', import.meta.url));
execFileSync(process.execPath, [compiler, '--target', 'ES2022', '--module', 'commonjs', '--lib', 'ES2022,DOM',
  '--strict', '--noUnusedLocals', '--noUnusedParameters', '--outDir', scratch, source], {stdio: 'pipe', cwd: scratch});
process.on('exit', () => fs.rmSync(scratch, {recursive: true, force: true}));
const output = path.join(scratch, 'terminal-engine.js');
const sandbox = vm.createContext({URL, Intl, Number, String, Math, Array, Object, JSON, Set, Map, structuredClone});
vm.runInContext(fs.readFileSync(output, 'utf8'), sandbox);
const hf = sandbox.HF;
const defaults = () => hf.terminalDefaults();
const close = (a, b, tolerance = 1e-9) => Math.abs(a - b) <= tolerance;

// Fixed summaries are shared with the Python parity tests; hourly rows are also
// checked independently against the documented recurrence at 1e-10 tolerance.
const parityFixtures = [
  ['default', {}, {
    periodCost: 15.606424009489949, unservedKwh: 0, renewableKwh: 60.7660329018012,
    curtailmentKwh: 0, peakImportKw: 6, finalSocKwh: 2, initialSocKwh: 10,
    terminalSocDeltaKwh: -8, maxBusResidualKw: 0, maxSocResidualKwh: 0,
    servedFraction: 1, totalLoadKwh: 129.6, servedKwh: 129.6,
  }],
  ['island_no_grid', {gridKw: 0}, {
    periodCost: 0, unservedKwh: 62.425696037959796, renewableKwh: 60.7660329018012,
    curtailmentKwh: 0, peakImportKw: 0, finalSocKwh: 2, initialSocKwh: 10,
    terminalSocDeltaKwh: -8, maxBusResidualKw: 0, maxSocResidualKwh: 0,
    servedFraction: 0.5183202466206805, totalLoadKwh: 129.6, servedKwh: 67.1743039620402,
  }],
  ['negative_export', {pvKw: 20, batteryKwh: 0, batteryKw: 0, loadKw: 0, gridKw: 100, importPrice: 0.2, exportPrice: -0.1}, {
    periodCost: 0, unservedKwh: 0, renewableKwh: 151.915082254503,
    curtailmentKwh: 151.915082254503, peakImportKw: 0, finalSocKwh: 0, initialSocKwh: 0,
    terminalSocDeltaKwh: 0, maxBusResidualKw: 0, maxSocResidualKwh: 0,
    servedFraction: 1, totalLoadKwh: 0, servedKwh: 0,
  }],
  ['zero_load', {pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 0, gridKw: 0}, {
    periodCost: 0, unservedKwh: 0, renewableKwh: 0, curtailmentKwh: 0, peakImportKw: 0,
    finalSocKwh: 0, initialSocKwh: 0, terminalSocDeltaKwh: 0, maxBusResidualKw: 0,
    maxSocResidualKwh: 0, servedFraction: 1, totalLoadKwh: 0, servedKwh: 0,
  }],
  ['efficiency_one', {
    pvKw: 20, batteryKwh: 40, batteryKw: 10, loadKw: 5, gridKw: 0,
    roundtripEfficiency: 1, initialSocFraction: 0, minSocFraction: 0, maxSocFraction: 1,
  }, {
    periodCost: 0, unservedKwh: 29.980470994369973, renewableKwh: 151.915082254503,
    curtailmentKwh: 63.39804516764754, peakImportKw: 0, finalSocKwh: 10.49750808122544,
    initialSocKwh: 0, terminalSocDeltaKwh: 10.49750808122544, maxBusResidualKw: 0,
    maxSocResidualKwh: 0, servedFraction: 0.7224030463484262,
    totalLoadKwh: 108, servedKwh: 78.01952900563003,
  }],
];

function referenceRows(p) {
  const eta = Math.sqrt(p.roundtripEfficiency);
  const minimum = p.batteryKwh * p.minSocFraction;
  const maximum = p.batteryKwh * p.maxSocFraction;
  let soc = p.batteryKwh * p.initialSocFraction;
  return Array.from({length: 24}, (_, hour) => {
    const load = p.loadKw * (0.8 + 0.2 * (0.5 + 0.5 * Math.cos((hour - 19) * 2 * Math.PI / 24)));
    const pv = hour <= 6 || hour >= 18 ? 0 : p.pvKw * Math.max(0, Math.sin(Math.PI * (hour - 6) / 12));
    const direct = Math.min(pv, load);
    let surplus = Math.max(0, pv - direct);
    let deficit = Math.max(0, load - direct);
    const before = soc;
    const charge = Math.min(surplus, p.batteryKw, Math.max(0, maximum - soc) / eta);
    soc += charge * eta;
    surplus -= charge;
    const discharge = Math.min(deficit, p.batteryKw, Math.max(0, soc - minimum) * eta);
    soc -= discharge / eta;
    deficit -= discharge;
    const gridImport = Math.min(deficit, p.gridKw);
    const unserved = deficit - gridImport;
    const gridExport = p.exportPrice >= 0 ? Math.min(surplus, p.gridKw) : 0;
    const curtailment = surplus - gridExport;
    return {
      hour, loadKw: load, pvKw: pv, chargeKw: charge, dischargeKw: discharge,
      gridImportKw: gridImport, gridExportKw: gridExport, curtailmentKw: curtailment,
      unservedKw: unserved, socKwh: soc,
      busResidualKw: pv + gridImport + discharge + unserved - load - charge - gridExport - curtailment,
      socResidualKwh: soc - (before + charge * eta - discharge / eta),
    };
  });
}

test('fixed cross-runtime fixtures match all metrics and 24 hourly reference rows', () => {
  for (const [name, changes, expectedMetrics] of parityFixtures) {
    const p = {...defaults(), ...changes};
    const result = hf.terminalSolve(p);
    for (const [metric, expected] of Object.entries(expectedMetrics)) {
      assert.ok(close(result.metrics[metric], expected, 1e-10), `${name}.${metric}: ${result.metrics[metric]} != ${expected}`);
    }
    const expectedRows = referenceRows(result.inputs);
    assert.equal(result.rows.length, expectedRows.length);
    for (let index = 0; index < 24; index += 1) {
      for (const [key, expected] of Object.entries(expectedRows[index])) {
        assert.ok(close(result.rows[index][key], expected, 1e-10), `${name}.hour${index}.${key}`);
      }
    }
  }
});

test('default run exposes 24 synthetic rows, explicit endpoints, and balanced recurrences', () => {
  const result = hf.terminalSolve(defaults());
  assert.equal(result.modelVersion, 'terminal-greedy-hourly-v1');
  assert.equal(result.dataKind, 'synthetic-deterministic');
  assert.equal(result.status, 'CONVERGED');
  assert.equal(result.steps, 24);
  assert.equal(result.iterations, null);
  assert.equal(result.rows.length, 24);
  let previousSoc = result.metrics.initialSocKwh;
  const eta = Math.sqrt(result.inputs.roundtripEfficiency);
  for (const [hour, row] of result.rows.entries()) {
    assert.equal(row.hour, hour);
    assert.ok(Math.abs(row.busResidualKw) < 1e-9);
    assert.ok(Math.abs(row.socKwh - (previousSoc + row.chargeKw * eta - row.dischargeKw / eta)) < 1e-9);
    assert.ok(row.socKwh >= 0 && row.socKwh <= result.inputs.batteryKwh);
    for (const key of ['chargeKw', 'dischargeKw', 'gridImportKw', 'gridExportKw', 'curtailmentKw', 'unservedKw']) assert.ok(row[key] >= 0);
    previousSoc = row.socKwh;
  }
  assert.ok(Math.abs(result.metrics.totalLoadKwh - 129.6) < 1e-10);
  assert.ok(Math.abs(result.metrics.terminalSocDeltaKwh - (result.metrics.finalSocKwh - result.metrics.initialSocKwh)) < 1e-12);
  assert.ok(result.metrics.maxBusResidualKw < 1e-9);
  assert.ok(result.metrics.maxSocResidualKwh < 1e-9);
});

test('zero-capacity battery reference balance gives bounded imports and unserved demand', () => {
  const result = hf.terminalSolve({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 4});
  assert.ok(close(result.metrics.totalLoadKwh, 216));
  assert.ok(close(result.metrics.servedKwh, 96));
  assert.ok(close(result.metrics.unservedKwh, 120));
  assert.equal(result.metrics.periodCost, 24);
  assert.equal(result.metrics.finalSocKwh, 0);
  assert.ok(result.rows.every(row => row.gridImportKw === 4));
  const tiny = hf.terminalSolve({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 1e-10, gridKw: 0});
  const unservedFlag = tiny.flags.find(flag => flag.key === 'unserved-demand');
  assert.equal(unservedFlag.active, true);
  assert.match(unservedFlag.explanation, /e-9 kWh/);
});

test('charge and discharge apply efficiency losses in opposite directions', () => {
  const result = hf.terminalSolve({...defaults(), pvKw: 20, batteryKwh: 40, batteryKw: 10, loadKw: 5, gridKw: 0,
    roundtripEfficiency: 0.81, initialSocFraction: 0, minSocFraction: 0, maxSocFraction: 1});
  const charge = result.rows.find(row => row.chargeKw > 0);
  const discharge = result.rows.find(row => row.dischargeKw > 0);
  const eta = 0.9;
  const beforeCharge = charge.hour === 0 ? result.metrics.initialSocKwh : result.rows[charge.hour - 1].socKwh;
  assert.ok(Math.abs(charge.socKwh - beforeCharge - charge.chargeKw * eta) < 1e-9);
  const beforeDischarge = result.rows[discharge.hour - 1].socKwh;
  assert.ok(Math.abs(beforeDischarge - discharge.socKwh - discharge.dischargeKw / eta) < 1e-9);
  assert.ok(charge.chargeKw > charge.chargeKw * eta);
  assert.ok(discharge.dischargeKw / eta > discharge.dischargeKw);
});

test('negative export prices curtail unused PV rather than creating paid exports', () => {
  const result = hf.terminalSolve({...defaults(), pvKw: 20, batteryKwh: 0, batteryKw: 0, loadKw: 0,
    gridKw: 100, importPrice: 0.2, exportPrice: -0.1});
  assert.equal(result.metrics.curtailmentKwh, result.metrics.renewableKwh);
  assert.equal(result.metrics.periodCost, 0);
  assert.ok(result.rows.every(row => row.gridExportKw === 0));
});

test('input contract rejects extras, invalid capacity pairing, nonfinite values, and range errors', () => {
  const p = defaults();
  for (const value of [null, [], {...p, extra: 1}, {...p, batteryKw: 0}, {...p, pvKw: NaN},
    {...p, batteryKwh: Infinity}, {...p, loadKw: -1}, {...p, gridKw: 100_001},
    {...p, pvKw: 1n}, {...p, roundtripEfficiency: 0}, {...p, importPrice: -10.01}, {...p, exportPrice: 10.01},
    {...p, initialSocFraction: 0.95}]) assert.throws(() => hf.terminalValidateInputs(value));
  const maximum = {...p, pvKw: 100_000, batteryKwh: 500_000, batteryKw: 100_000,
    loadKw: 100_000, gridKw: 100_000, roundtripEfficiency: 1,
    initialSocFraction: 1, minSocFraction: 1, maxSocFraction: 1, importPrice: 10, exportPrice: 10};
  assert.equal(hf.terminalSolve(maximum).steps, 24);
});

test('linear and logarithmic sweeps form bounded matrices, rank service first, and preserve invalid points', () => {
  const p = {...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 4, importPrice: 0.1};
  const matrix = hf.terminalSweep(p, 'importPrice', 0.01, 1, 3, 'log',
    {parameter: 'gridKw', lower: 2, upper: 4, steps: 2, scale: 'linear'});
  assert.equal(matrix.points.length, 6);
  assert.ok(Array.from(matrix.axes[0].values).every((value, index) => close(value, [0.01, 0.1, 1][index])));
  assert.deepEqual(Array.from(matrix.rankedPointIndices), [3, 4, 5, 0, 1, 2]);
  assert.deepEqual(Array.from(matrix.paretoPointIndices), [0, 3]);
  const partial = hf.terminalSweep(defaults(), 'batteryKw', 0, 5, 2, 'linear');
  assert.equal(partial.points[0].status, 'ERR_VALIDATION');
  assert.equal(partial.points[0].metrics, null);
  assert.match(partial.points[0].error, /either both be zero or both be greater/);
  assert.equal(partial.points[1].status, 'CONVERGED');
  assert.throws(() => hf.terminalSweep(defaults(), 'pvKw', 0, 5, 2, 'log'));
  assert.throws(() => hf.terminalSweep(defaults(), 'pvKw', 0, 5, 22, 'linear'));
});

test('Pareto groups match total and served demand, and a two-axis matrix stops at 441 points', () => {
  const varyingDemand = hf.terminalSweep({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 0},
    'loadKw', 2, 10, 3, 'linear');
  assert.deepEqual(Array.from(varyingDemand.paretoPointIndices), [0, 1, 2]);
  assert.match(varyingDemand.warnings[1], /conditional sampled service-equivalent frontier/);
  assert.match(varyingDemand.warnings[1], /not a global optimum/);
  const maximum = hf.terminalSweep({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 4},
    'importPrice', 0.01, 1, 21, 'linear',
    {parameter: 'gridKw', lower: 0, upper: 20, steps: 21, scale: 'linear'});
  assert.equal(maximum.points.length, 441);
  assert.equal(maximum.rankedPointIndices.length, 441);
});

test('finite-difference sensitivity marks undefined zero-baseline elasticities null', () => {
  const result = hf.terminalSensitivity({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0,
    loadKw: 10, gridKw: 4, importPrice: 0});
  assert.equal(result.rows.length, 11);
  assert.equal(result.rows.find(row => row.parameter === 'importPrice').periodCostElasticity, null);
  assert.equal(result.rows.find(row => row.parameter === 'pvKw').periodCostElasticity, null);
  assert.notEqual(result.rows.find(row => row.parameter === 'gridKw').unservedKwhElasticity, null);
  assert.match(result.warnings[0], /not Sobol/);
});

test('run diff reports absolute changes and null percentage for a zero baseline', () => {
  const a = hf.terminalSolve({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 4, importPrice: 0});
  const b = hf.terminalSolve({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 4, importPrice: 0.25});
  const diff = hf.terminalDiff(a, b);
  const cost = diff.rows.find(row => row.metric === 'periodCost');
  assert.equal(cost.a, 0);
  assert.equal(cost.b, 24);
  assert.equal(cost.deltaAbsolute, 24);
  assert.equal(cost.deltaPercent, null);
  assert.equal(diff.rows.find(row => row.metric === 'servedFraction').deltaPercent, 0);
  const served = hf.terminalSolve({...defaults(), pvKw: 0, batteryKwh: 0, batteryKw: 0, loadKw: 10, gridKw: 100, importPrice: 0.25});
  const shift = hf.terminalDiff(a, served).warnings.find(message => message.startsWith('Regime shift for unserved-demand'));
  assert.match(shift, /run a was active/);
  assert.match(shift, /run b was inactive/);
});
