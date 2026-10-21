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
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-experiences-'));
const stub = path.join(temp, 'experience-types.ts');
const out = path.join(temp, 'experiences.js');
fs.writeFileSync(stub, `namespace HF {
  export type Page = string;
  export type MarketCode = string;
  export interface Market { code: MarketCode; name: string; currency: string }
  export interface Drift { series: { index: number; residual_pct: number; z_score: number }[]; alert_indices: number[] }
  export interface ViewState { page: Page; motionOff: boolean; connected: boolean; hybrid: { lessonId: string; quizResult: { passed: boolean; correct: number; total: number } | null }; data: { markets: Market[]; drift: Drift; portfolio: { id: string; capex_meur: number }[] } }
}`);
try {
  compileScripts([
    stub,
    path.join(root, 'src/experiences.ts'),
  ], out);
} catch (error) {
  throw new Error(`Could not compile experiences sources: ${error.stderr?.toString() || error.stdout?.toString() || error.message}`);
}
const context = vm.createContext({ URL, URLSearchParams, Intl, Date, Math, Number, String, Array, Object, Map, Set, JSON, RegExp, console });
vm.runInContext(fs.readFileSync(out, 'utf8'), context);
const hf = context.HF;
const markets = [
  { code: 'FR', name: 'France', currency: 'EUR' },
  { code: 'DE', name: 'Germany', currency: 'EUR' },
  { code: 'GB', name: 'Great Britain', currency: 'GBP' },
];

test('tariff stack reports complete totals only when every component is supplied', () => {
  assert.deepEqual(JSON.parse(JSON.stringify(hf.sumTariffStack({ energy: 30, network: 4, levies: null, other: 1 }))), {
    total: null, supplied: 3, complete: false,
  });
  assert.deepEqual(JSON.parse(JSON.stringify(hf.sumTariffStack({ energy: 30, network: 4, levies: -2, other: 1 }))), {
    total: 33, supplied: 4, complete: true,
  });
});

test('ENTSO-E query builder includes the selected verified EIC and rejects unknown countries', () => {
  const expected = {
    FR: '10YFR-RTE------C', DE: '10Y1001A1001A82H', ES: '10YES-REE------0',
    IT: '10YIT-GRTN-----B', NL: '10YNL----------L', GB: '10YGB----------A',
  };
  for (const [country, eic] of Object.entries(expected)) {
    const url = new URL(hf.buildEntsoeLoadUrl(country));
    assert.equal(url.hostname, 'transparency.entsoe.eu');
    assert.equal(url.searchParams.get('areaType'), 'CTA');
    assert.equal(url.searchParams.get('biddingZone.values'), `CTY|${eic}!CTA|${eic}`);
  }
  assert.equal(hf.buildEntsoeLoadUrl('XX'), null);
});

test('review timeline includes only valid user-supplied date and HTTP(S) document pairs', () => {
  const items = hf.reviewTimeline({
    FR: { effectiveDate: '2027-01-02', documentUrl: 'https://example.test/fr.pdf' },
    DE: { effectiveDate: '2026-06-30', documentUrl: 'https://example.test/de.pdf' },
    GB: { effectiveDate: '2025-02-30', documentUrl: 'https://example.test/invalid-date.pdf' },
    ES: { effectiveDate: '2026-01-01', documentUrl: 'javascript:alert(1)' },
  }, markets);
  assert.deepEqual(JSON.parse(JSON.stringify(items)), [
    { code: 'DE', country: 'Germany', effectiveDate: '2026-06-30', documentUrl: 'https://example.test/de.pdf' },
    { code: 'FR', country: 'France', effectiveDate: '2027-01-02', documentUrl: 'https://example.test/fr.pdf' },
  ]);
});

test('trailing mean uses observed residuals and keeps empty windows missing', () => {
  assert.deepEqual(JSON.parse(JSON.stringify(hf.trailingMean([null, 2, 4, -2, null], 2))), [null, null, 3, 1, null]);
});

test.after(() => fs.rmSync(temp, { recursive: true, force: true }));
