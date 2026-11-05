import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {installFixtureViews} from './helpers/fixture-views.mjs';

const context = vm.createContext({URL, Intl, structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8'), context);
const {viewFragment, renderView, appendView, prependView, replaceViewElement} = context.HF;

// A DOM operation recorder, not an HTML parser. HTML sink setters throw so a
// regression cannot silently restore the old insertion path in these tests.
function documentFixture() {
  class Node {
    constructor(nodeType, text = '') { this.nodeType = nodeType; this.data = text; this.childNodes = []; this.ownerDocument = document; }
    appendChild(node) { this.childNodes.push(...(node.nodeType === 11 ? node.childNodes.splice(0) : [node])); return node; }
    append(...nodes) { nodes.forEach(node => this.appendChild(node)); }
    prepend(node) { this.childNodes.unshift(...(node.nodeType === 11 ? node.childNodes.splice(0) : [node])); }
    replaceChildren(...nodes) { this.childNodes = []; this.append(...nodes); }
    replaceWith(node) { this.replacement = node; }
    get textContent() { return this.nodeType === 3 ? this.data : this.childNodes.map(node => node.textContent).join(''); }
    set innerHTML(_) { throw new Error('HTML sink called'); }
    set outerHTML(_) { throw new Error('HTML sink called'); }
    insertAdjacentHTML() { throw new Error('HTML sink called'); }
  }
  class Element extends Node {
    constructor(tagName, namespaceURI = 'http://www.w3.org/1999/xhtml') {
      super(1); this.tagName = tagName; this.namespaceURI = namespaceURI; this.attributes = new Map(); this.styles = new Map();
      this.style = {setProperty: (name, value, priority) => this.styles.set(name, {value, priority})};
    }
    setAttribute(name, value) { this.attributes.set(name, value); }
  }
  const document = {
    baseURI: 'https://local.example/run/',
    createDocumentFragment: () => new Node(11),
    createTextNode: text => new Node(3, text),
    createElement: tag => new Element(tag),
    createElementNS: (namespace, tag) => new Element(tag, namespace),
  };
  return document;
}

test('view boundary preserves nested text, entities, boolean attributes and local links', () => {
  const doc = documentFixture();
  const fragment = viewFragment('<section class="card"><h2>A &amp; B</h2><p>&lt;script&gt; &#x1f50b; &#177;</p><input disabled value="42"><a href="../method#units">Method</a></section>', doc);
  const section = fragment.childNodes[0];
  assert.equal(section.tagName, 'section');
  assert.equal(section.attributes.get('class'), 'card');
  assert.equal(section.textContent, 'A & B<script> 🔋 ±Method');
  assert.equal(section.childNodes[2].attributes.get('disabled'), '');
  assert.equal(section.childNodes[2].attributes.get('value'), '42');
  assert.equal(section.childNodes[3].attributes.get('href'), '../method#units');
});

test('view boundary builds namespaced chart nodes and assigns numeric styles through CSSOM', () => {
  const doc = documentFixture();
  const fragment = viewFragment('<svg viewBox="0 0 100 100"><defs><linearGradient id="power"><stop offset="0" stop-color="#fff"/></linearGradient></defs><path fill="url(#power)" d="M0 0L10 10" style="opacity: .8; --bar: 42%; stroke-width: 2 !important"/></svg>', doc);
  const svg = fragment.childNodes[0], path = svg.childNodes[1];
  assert.equal(svg.namespaceURI, 'http://www.w3.org/2000/svg');
  assert.equal(svg.childNodes[0].childNodes[0].tagName, 'linearGradient');
  assert.equal(path.attributes.get('fill'), 'url(#power)');
  assert.equal(path.attributes.has('style'), false);
  assert.deepEqual(path.styles.get('--bar'), {value: '42%', priority: ''});
  assert.deepEqual(path.styles.get('stroke-width'), {value: '2', priority: 'important'});
});

test('all view operations use fragments and invalid templates leave the existing target untouched', () => {
  const doc = documentFixture(), target = doc.createElement('main');
  renderView(target, '<p>Existing</p>');
  const existing = target.childNodes[0];
  for (const markup of [
    '<script>alert(1)</script>', '<img src="https://external.invalid/pixel">',
    '<p onclick="run()">bad</p>', '<a href="javascript:run()">bad</a>',
    '<a href="jav&#x61;script:run()">bad</a>', '<a href="data:text/html,bad">bad</a>',
    '<div srcdoc="bad"></div>', '<div style="background:url(https://external.invalid)"></div>',
    '<div style="background:u\\72l(https://external.invalid)"></div>',
    '<svg><path fill="url(https://external.invalid)"/></svg>',
    '<svg><text href="https://external.invalid">bad</text></svg>',
    '<p><strong>Unbalanced</p>', '<div title="unclosed',
  ]) {
    assert.throws(() => renderView(target, markup), /Unsupported|Invalid|Unbalanced|Unclosed/);
    assert.equal(target.childNodes[0], existing);
    assert.equal(target.textContent, 'Existing');
  }
  appendView(target, '<p>After</p>');
  prependView(target, '<p>Before</p>');
  assert.equal(target.textContent, 'BeforeExistingAfter');
  replaceViewElement(target, '<section>Replacement</section>');
  assert.equal(target.replacement.nodeType, 11);
  assert.equal(target.replacement.textContent, 'Replacement');
  for (const operation of [renderView, appendView, prependView, replaceViewElement]) assert.doesNotThrow(() => operation(null, '<script>not used</script>'));
});

test('controller presentation spies refuse DOM nodes', () => {
  const views = installFixtureViews({});
  const node = documentFixture().createElement('p');
  assert.throws(() => views.renderView(node, 'not a fixture'), /plain fixture object/);
});


test('SVG resource attributes reject escaped and commented CSS before view replacement', () => {
  const doc = documentFixture(), target = doc.createElement('main');
  renderView(target, '<p>Existing</p>');
  const existing = target.childNodes[0];
  const attributes = ['clip-path', 'color-profile', 'cursor', 'fill', 'filter', 'marker', 'marker-start', 'marker-mid', 'marker-end', 'mask', 'stroke'];
  const resources = [
    'u\\72l(https://outside.invalid/paint.svg#paint)',
    '\\75rl(https://outside.invalid/paint.svg#paint)',
    'u&#92;72l(https://outside.invalid/paint.svg#paint)',
    'u/**/rl(https://outside.invalid/paint.svg#paint)',
    'url/**/(https://outside.invalid/paint.svg#paint)',
    'image-set(&quot;https://outside.invalid/paint.png&quot; 1x)',
  ];
  for (const attribute of attributes) {
    for (const resource of resources) {
      assert.throws(() => renderView(target, `<svg><rect ${attribute}="${resource}"/></svg>`), /Unsupported view resource/, `${attribute}: ${resource}`);
      assert.equal(target.childNodes[0], existing);
    }
    const fragment = viewFragment(`<svg><rect ${attribute}="url(#asset)"/></svg>`, doc);
    assert.equal(fragment.childNodes[0].childNodes[0].attributes.get(attribute), 'url(#asset)');
  }
  const fragment = viewFragment('<svg data-label="path\\series"><text aria-label="a /* label */">Normal label</text></svg>', doc);
  assert.equal(fragment.childNodes[0].attributes.get('data-label'), 'path\\series');
  assert.equal(fragment.childNodes[0].childNodes[0].attributes.get('aria-label'), 'a /* label */');
});
