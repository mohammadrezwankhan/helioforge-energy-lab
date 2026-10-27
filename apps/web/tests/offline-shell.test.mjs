import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('standalone shell contains no third-party font or asset link tags', () => {
  const html = fs.readFileSync(new URL('../../../HelioForge-Preview.html', import.meta.url), 'utf8');
  const assetLinks = [...html.matchAll(/<(?:link|script|img)\b[^>]*\b(?:href|src)=["'](https?:\/\/[^"']+)["']/gi)];
  assert.deepEqual(assetLinks.map(match => match[1]), []);
});
