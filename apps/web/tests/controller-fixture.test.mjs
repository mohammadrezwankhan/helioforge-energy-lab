import test from 'node:test';
import assert from 'node:assert/strict';
import {controllerFixture} from './helpers/controller-fixture.mjs';

test('fixture text extraction omits complete and unfinished tag fragments', () => {
  const {hero} = controllerFixture();
  hero.innerHTML = '36<small> / 36</small>';
  assert.equal(hero.textContent, '36 / 36');
  hero.innerHTML = '<strong>example</strong><script';
  assert.equal(hero.textContent, 'example');
  assert.equal(hero.innerHTML, '<strong>example</strong><script');
  hero.innerHTML = '36 > 35';
  assert.equal(hero.textContent, '36 > 35');
});
