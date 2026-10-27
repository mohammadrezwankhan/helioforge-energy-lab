import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8');
function mount(reduced = false) {
  const frames = new Map(), events = new Map(), canvasEvents = new Map();
  let nextFrame = 0, intersections, styleReads = 0, draws = 0;
  const ctx = new Proxy({measureText: text => ({width: text.length * 7}), clearRect: () => draws++}, {
    get: (target, name) => target[name] ?? (() => {}),
  });
  const document = {hidden: false, documentElement: {}, addEventListener: (name, fn) => events.set(name, fn), removeEventListener: name => events.delete(name)};
  const box = vm.createContext({URL, Intl, structuredClone, devicePixelRatio: 1,
    getComputedStyle: () => {styleReads++; return {getPropertyValue: () => '#bbffbb'};},
    requestAnimationFrame: callback => {frames.set(++nextFrame, callback); return nextFrame;},
    cancelAnimationFrame: id => frames.delete(id),
    ResizeObserver: class {observe() {} disconnect() {}},
    IntersectionObserver: class {constructor(callback) {intersections = callback;} observe() {} disconnect() {}},
  });
  vm.runInContext(code, box);
  box.document = document;
  const canvas = {getContext: () => ctx, getBoundingClientRect: () => ({width: 600, height: 400}), parentElement: {querySelectorAll: () => []},
    addEventListener: (name, fn) => canvasEvents.set(name, fn), removeEventListener: name => canvasEvents.delete(name)};
  const dispose = box.HF.mountEnergyScene(canvas, box.HF.systemById('remote-triad'), reduced, () => {});
  return {frames, events, canvasEvents, document, dispose, setVisible: value => intersections([{isIntersecting: value}]),
    stats: () => ({styleReads, draws}), tick: () => {const [id, callback] = frames.entries().next().value; frames.delete(id); callback(16);}};
}

test('reduced motion renders on demand without a permanent animation callback', () => {
  const scene = mount(true);
  assert.equal(scene.frames.size, 0);
  const before = scene.stats().draws;
  scene.canvasEvents.get('scene-telemetry')();
  assert.ok(scene.stats().draws > before, 'telemetry changes still redraw the diagram');
  scene.dispose();
});

test('animation stops offscreen and in background, resumes once, and disposes all listeners', () => {
  const scene = mount();
  assert.equal(scene.frames.size, 1);
  scene.setVisible(false);
  assert.equal(scene.frames.size, 0, 'offscreen diagrams do not consume frame callbacks');
  scene.setVisible(true);
  scene.setVisible(true);
  assert.equal(scene.frames.size, 1);
  scene.document.hidden = true;
  scene.events.get('visibilitychange')();
  assert.equal(scene.frames.size, 0);
  scene.document.hidden = false;
  scene.events.get('visibilitychange')();
  assert.equal(scene.frames.size, 1);
  scene.tick();
  assert.equal(scene.frames.size, 1);
  scene.dispose();
  assert.equal(scene.frames.size, 0);
  assert.equal(scene.events.size, 0);
  assert.equal(scene.canvasEvents.size, 0);
});

test('canvas resolves the current theme once per draw, rather than once per face', () => {
  const scene = mount();
  assert.equal(scene.stats().styleReads, scene.stats().draws);
  scene.tick();
  assert.equal(scene.stats().styleReads, scene.stats().draws);
  scene.dispose();
});
