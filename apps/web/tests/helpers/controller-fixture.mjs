import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync(new URL('../../dist/app.js', import.meta.url), 'utf8');
export function controllerFixture({mode = 'normal', saved = false, progress = []} = {}) {
  const memory = new Map(), events = new Map(), toasts = [], exports = [], microtasks = [];
  class Element {
    constructor() { this.dataset = {}; this.attributes = new Map(); this.textContent = ''; this.classes = new Set(); this.classList = {add: x => this.classes.add(x), remove: x => this.classes.delete(x), contains: x => this.classes.has(x), toggle: (x, on) => on ? this.classes.add(x) : this.classes.delete(x)}; }
    set innerHTML(value) {
      this.markup = value;
      // Minimal text projection for controlled fixture markup, not an HTML sanitizer.
      let text = '', inTag = false;
      for (const character of value) {
        if (inTag) { if (character === '>') inTag = false; }
        else if (character === '<') inTag = true;
        else text += character;
      }
      this.textContent = text;
    }
    get innerHTML() { return this.markup ?? ''; }
    setAttribute(key, value) { this.attributes.set(key, value); }
    getAttribute(key) { return this.attributes.get(key) ?? null; }
    hasAttribute(key) { return this.attributes.has(key); }
    closest(selector) { return selector === 'button' ? this : null; }
    querySelector() { return null; }
  }
  class Form extends Element { constructor(answers) { super(); this.id = 'lesson-quiz'; this.values = new Map(answers.map((value, i) => ['q' + i, String(value)])); } }
  class Button extends Element { constructor(action) { super(); this.dataset.hybridAction = action; } }
  class FormData { constructor(form) { this.form = form; } get(key) { return this.form.values.get(key) ?? null; } }
  const storage = {
    getItem(key) { if (mode === 'blocked') throw new Error('SecurityError'); return memory.get(key) ?? null; },
    setItem(key, value) { if (['blocked', 'write-blocked', 'mutation-blocked'].includes(mode)) throw new Error('QuotaExceededError'); memory.set(key, value); },
    removeItem(key) { if (['blocked', 'mutation-blocked'].includes(mode)) throw new Error('SecurityError'); memory.delete(key); },
  };
  const box = vm.createContext({URL, Intl, structuredClone, localStorage: storage, Element, HTMLFormElement: Form, HTMLInputElement: class extends Element {}, HTMLSelectElement: class extends Element {}, FormData, queueMicrotask: callback => microtasks.push(callback)});
  vm.runInContext(code, box);
  const hf = box.HF, lesson = hf.HYBRID_CATALOG.lessons[0];
  if (saved) {
    memory.set('hf-lessons-v2', JSON.stringify([lesson.id]));
    memory.set('hf-learning-mastery-v1', JSON.stringify({schema: 'helioforge.local-learning.v1', passed_self_checks: [lesson.id], mastery_checks: {[lesson.id]: {correct: 2, total: 2, passed_at: '2026-10-20T12:00:00Z'}}}));
  }
  const hero = new Element(), status = new Element(), note = new Element(), feedback = new Element();
  const buttons = hf.HYBRID_CATALOG.lessons.map(item => {
    const button = new Element(); button.dataset.lesson = item.id;
    button.setAttribute('aria-label', item.title + '; ' + item.level + '; not passed');
    button.number = new Element(); button.querySelector = selector => selector === '.lesson-number' ? button.number : null;
    return button;
  });
  const document = {
    getElementById(id) { return id === 'quiz-feedback' ? feedback : null; },
    querySelector(selector) {
      if (selector === '.achievement-orb strong') return hero;
      if (selector === '[data-hf-completion-status]') return status;
      if (selector === '[data-learning-progress-note]') return note;
      const match = selector.match(/^\.lesson-list \[data-lesson="([^"]+)"\] \.lesson-number$/);
      return match ? buttons.find(button => button.dataset.lesson === match[1])?.number ?? null : null;
    },
    querySelectorAll(selector) { return ['[data-lesson]', '.skill-tree [data-lesson]', '.lesson-list [data-lesson]'].includes(selector) ? buttons : []; },
    addEventListener(type, callback, capture) { const row = events.get(type) ?? []; row.push({callback, capture: capture === true}); events.set(type, row); },
    removeEventListener() {},
  };
  box.document = document; box.window = {scrollTo() {}};
  const state = {hybrid: hf.initialHybridState(), page: 'lessons', connected: false, data: structuredClone(hf.SNAPSHOT), motionOff: true};
  state.hybrid.progress.push(...progress); state.champion = hf.initialChampionState(state.hybrid);
  hf.download = (filename, value) => exports.push({filename, payload: JSON.parse(value)});
  const completion = hf.createCompletionController(() => state, (message, error) => toasts.push({message, error})); completion.refresh();
  hf.installHybridController(state, {render: () => completion.refresh(), toast: (message, error) => toasts.push({message, error}), navigate: () => completion.refresh(), api: async () => { throw new Error('Unexpected API request'); }, celebrate() {}, openModal() {}});
  function dispatch(type, target) {
    const event = {target, stopped: false, preventDefault() {}, stopImmediatePropagation() { this.stopped = true; }};
    for (const row of [...events.get(type) ?? []].sort((a, b) => Number(b.capture) - Number(a.capture))) { row.callback(event); if (event.stopped) break; }
    while (microtasks.length) microtasks.shift()();
  }
  return {hf, state, lesson, memory, toasts, exports, completion, dispatch, Form, Button, hero, status, note, feedback, buttons, document};
}
