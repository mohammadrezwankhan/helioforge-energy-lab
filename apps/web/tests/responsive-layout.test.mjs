import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const css = fs.readFileSync(new URL('../src/terminal.css', import.meta.url), 'utf8');

function blockAt(source, start) {
  const open = source.indexOf('{', start);
  if (open < 0) return '';
  let depth = 1;
  for (let i = open + 1; i < source.length; i++) {
    if (source[i] === '{') depth++;
    if (source[i] === '}' && --depth === 0) return source.slice(open + 1, i);
  }
  return '';
}

function mediaBlock(query) {
  const needle = `@media (max-width: ${query}px)`;
  const start = css.lastIndexOf(needle);
  return start < 0 ? '' : blockAt(css, start);
}

function ruleBlock(source, selector) {
  const needle = `${selector} {`;
  const blocks = [];
  let start = source.indexOf(needle);
  while (start >= 0) {
    blocks.push(blockAt(source, start));
    start = source.indexOf(needle, start + needle.length);
  }
  return blocks.join('\n');
}

test('tablet hybrid hero stacks its title and architecture counts', () => {
  const tablet = mediaBlock(1120);
  assert.match(ruleBlock(tablet, '.forge-heading'), /grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  assert.match(ruleBlock(tablet, '.forge-heading'), /align-items:\s*start/);
});

test('phone hybrid counts retain readable columns without clipping labels', () => {
  const phone = mediaBlock(600);
  assert.match(ruleBlock(phone, '.forge-counts'), /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(ruleBlock(phone, '.forge-counts div:nth-child(3)'), /grid-column:\s*1\s*\/\s*-1/);
  assert.match(ruleBlock(phone, '.forge-counts span'), /overflow-wrap:\s*anywhere/);
});

test('the first hybrid count label can use the full unruled stat cell', () => {
  assert.match(ruleBlock(css, '.forge-counts div:first-child'), /padding-left:\s*0/);
  assert.match(ruleBlock(css, '.forge-counts div:first-child'), /padding-right:\s*0/);
});

test('narrow section headings stack metadata badges beneath their text', () => {
  const phone = mediaBlock(600);
  const tablet = mediaBlock(1120);
  assert.match(ruleBlock(phone, '.section-heading'), /flex-direction:\s*column/);
  assert.match(ruleBlock(phone, '.section-heading > div'), /min-width:\s*0/);
  assert.match(ruleBlock(tablet, '.section-heading > .tag'), /white-space:\s*normal/);
  assert.match(ruleBlock(tablet, '.section-heading > .tag'), /max-width:\s*100%/);
});

test('market metadata can wrap before the card grid forces page overflow', () => {
  const tablet = mediaBlock(1120);
  assert.match(ruleBlock(tablet, '.market-meta > div'), /flex-wrap:\s*wrap/);
  assert.match(ruleBlock(tablet, '.market-meta > div > strong'), /overflow-wrap:\s*anywhere/);
});

test('compact research panels and experience actions stack before they become cramped', () => {
  const compact = mediaBlock(900);
  assert.match(ruleBlock(compact, '.two-columns'), /grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  assert.match(ruleBlock(compact, '.hf-experience-heading'), /flex-direction:\s*column/);
  assert.match(ruleBlock(compact, '.hf-experience-heading > div'), /min-width:\s*0/);
});

test('wide data tables keep their local horizontal scroll region', () => {
  assert.match(css, /\.table-scroll\s*\{[^}]*overflow-x:\s*auto/s);
});
