import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {domainSecurityPolicy} from './domain-security.mjs';

test('policy authorizes exact inline bytes and same-origin external scripts only', () => {
  const body = 'window.example = 1;\n';
  const hash = createHash('sha256').update(body).digest('base64');
  const policy = domainSecurityPolicy([`<script>${body}</script><script src="/x.js"></script>`]);
  assert.ok(policy.includes(`'sha256-${hash}'`));
  assert.equal((policy.match(/sha256-/g) || []).length, 2);
  assert.match(policy, /connect-src 'self';/);
  assert.doesNotMatch(policy, /https:|unsafe-eval|script-src[^;]*unsafe-inline/);
  assert.notEqual(policy, domainSecurityPolicy([`<script>${body} </script>`]));
});

test('shared policy deduplicates scripts and covers static structured data', () => {
  const script = '<script type="application/ld+json">{"name":"HelioForge"}</script>';
  assert.equal(domainSecurityPolicy([script, script]), domainSecurityPolicy([script]));
  assert.equal((domainSecurityPolicy([script]).match(/sha256-/g) || []).length, 2);
});

test('hash extraction follows browser script end-tag boundaries', () => {
  const body = 'window.example = "</script-like>";';
  const expected = domainSecurityPolicy([`<script>${body}</script>`]);
  for (const ending of ['</script >', '</ScRiPt\t>', '</script foo="bar">', '</script/>']) {
    assert.equal(domainSecurityPolicy([`<script>${body}${ending}`]), expected);
  }
});
