import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

const receiptScript = new URL('../../scripts/acceptance-build-receipt.mjs', import.meta.url);

function releaseFixture(t) {
  const root = mkdtempSync(path.join(tmpdir(), 'helioforge-receipt-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
  const script = path.join('scripts', 'acceptance-build-receipt.mjs');
  const receipts = path.join(root, 'evidence', 'receipts');
  const site = path.join(root, '.cloudflare', 'site');
  const runtime = 'A small release runtime\n';
  mkdirSync(path.join(root, 'scripts'));
  mkdirSync(path.join(site, 'run'), { recursive: true });
  copyFileSync(receiptScript, path.join(root, script));
  writeFileSync(path.join(root, '.gitignore'), '/.cloudflare/\n/evidence/\n');
  writeFileSync(path.join(site, 'run', 'index.html'), runtime);
  git('init', '--quiet');
  git('add', '.gitignore', script);
  git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Fixture source');
  const sourceRevision = git('rev-parse', 'HEAD');
  const runtimeSha256 = createHash('sha256').update(runtime).digest('hex');
  const writeManifest = (changes = {}) => writeFileSync(path.join(site, 'app.json'), JSON.stringify({
    sourceRevision, sourceTreeDirty: false, runtimeSha256, ...changes,
  }));
  writeManifest();
  const run = (ci = true) => spawnSync(process.execPath, [script], {
    cwd: root,
    encoding: 'utf8',
    env: {
      ...process.env,
      CLOUDFLARE_OUTPUT_ROOT: '.cloudflare',
      HELIOFORGE_EVIDENCE_DIR: 'evidence',
      GITHUB_ACTIONS: String(ci),
      GITHUB_RUN_ID: ci ? '17' : '',
      GITHUB_RUN_ATTEMPT: ci ? '1' : '',
    },
  });
  const readReceipt = (output) => JSON.parse(readFileSync(path.join(root, JSON.parse(output).receipt), 'utf8'));
  return { root, receipts, run, writeManifest, sourceRevision, readReceipt };
}

test('CI writes a receipt for the exact clean checkout with ignored build outputs', (t) => {
  const fixture = releaseFixture(t);
  const result = fixture.run();
  assert.equal(result.status, 0, result.stderr);
  const receipt = fixture.readReceipt(result.stdout);
  assert.equal(receipt.source_base_commit, fixture.sourceRevision);
  assert.equal(receipt.working_tree_dirty, false);
  assert.deepEqual(receipt.files.map(({ path }) => path), ['app.json', 'run/index.html']);
});

test('CI rejects a dirty checkout and identifies the changed path', (t) => {
  const fixture = releaseFixture(t);
  writeFileSync(path.join(fixture.root, '.gitignore'), '/.cloudflare/\n/evidence/\n/new-output/\n');
  const result = fixture.run();
  assert.equal(result.status, 1);
  assert.match(result.stderr, /clean source tree/);
  assert.match(result.stderr, /\.gitignore/);
  assert.equal(existsSync(fixture.receipts), false);
});

test('CI rejects a manifest from a different Git revision', (t) => {
  const fixture = releaseFixture(t);
  fixture.writeManifest({ sourceRevision: 'a'.repeat(40) });
  const result = fixture.run();
  assert.equal(result.status, 1);
  assert.match(result.stderr, /manifest.*clean checkout/i);
  assert.equal(existsSync(fixture.receipts), false);
});

test('CI rejects a manifest reporting an unclean source tree', (t) => {
  const fixture = releaseFixture(t);
  fixture.writeManifest({ sourceTreeDirty: true });
  const result = fixture.run();
  assert.equal(result.status, 1);
  assert.match(result.stderr, /manifest.*clean checkout/i);
  assert.equal(existsSync(fixture.receipts), false);
});

test('local receipts preserve the actual dirty state for diagnostics', (t) => {
  const fixture = releaseFixture(t);
  writeFileSync(path.join(fixture.root, 'local-edit.txt'), 'Untracked local work\n');
  fixture.writeManifest({ sourceTreeDirty: true });
  const result = fixture.run(false);
  assert.equal(result.status, 0, result.stderr);
  const receipt = fixture.readReceipt(result.stdout);
  assert.equal(receipt.environment, 'local');
  assert.equal(receipt.working_tree_dirty, true);
});
