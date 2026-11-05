import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { browserPolicy } from '../../scripts/browser-csp.mjs';

test('deployment meta CSP authorizes final hosted script bytes after runtime patches', () => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  execFileSync(process.execPath, ['scripts/build-web.mjs'], { cwd: root, stdio: 'pipe' });
  const parent = path.join(root, '.cloudflare');
  fs.mkdirSync(parent, { recursive: true });
  const staging = fs.mkdtempSync(path.join(parent, 'csp-regression-'));
  const output = path.join(staging, 'export');
  try {
    execFileSync(process.execPath, ['scripts/build-cloudflare.mjs'], {
      cwd: root,
      env: { ...process.env, CLOUDFLARE_OUTPUT_ROOT: output },
      stdio: 'pipe',
    });
    const html = fs.readFileSync(path.join(output, 'app/run/index.html'), 'utf8');
    const policy = /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i.exec(html)?.[1];
    assert.ok(policy, 'deployed runtime keeps its document CSP');
    const expected = browserPolicy(html);
    assert.equal(policy, expected, 'CSP must authorize the final delivered executable bytes');
    const original = fs.readFileSync(path.join(root, 'apps/web/dist/hosted/index.html'), 'utf8');
    assert.notEqual(expected, browserPolicy(original), 'browser-only runtime patches change executable bytes');
    assert.match(html, /<head\b[^>]*>\s*<meta\s+http-equiv="Content-Security-Policy"/i);
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
});
