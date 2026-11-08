import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {compileScripts} from '../../../scripts/compile-web.mjs';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-dialog-focus-'));
const output = path.join(temp, 'app.js');
const files = JSON.parse(fs.readFileSync(path.join(web, 'tsconfig.json'), 'utf8')).files;
compileScripts(files.map(file => path.join(web, file)), output);
const code = fs.readFileSync(output, 'utf8');
process.on('exit', () => fs.rmSync(temp, {recursive: true, force: true}));

function fixture() {
  const closeTasks = [];
  let openModal;
  let activeDialog;
  const document = {
    readyState: 'loading',
    documentElement: {dataset: {}},
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
  };
  class Element {
    constructor(name) { this.name = name; }
    focus() {
      if (!activeDialog || this === activeDialog) document.activeElement = this;
    }
    contains(element) { return element === this; }
  }
  class Dialog extends Element {
    listeners = [];
    open = false;
    addEventListener(type, callback, options) {
      assert.equal(type, 'close');
      this.listeners.push({callback, once: options?.once === true});
    }
    showModal() {
      this.previousFocus = document.activeElement;
      this.open = true;
      activeDialog = this;
      this.focus();
    }
    close() {
      this.open = false;
      activeDialog = null;
      this.previousFocus?.focus();
      // HTML's close steps restore focus now, then queue the close event.
      // https://html.spec.whatwg.org/multipage/interactive-elements.html#close-the-dialog
      closeTasks.push(() => {
        for (const listener of [...this.listeners]) {
          if (listener.once) this.listeners.splice(this.listeners.indexOf(listener), 1);
          listener.callback();
        }
      });
    }
  }
  const root = new Element('root'), dialog = new Dialog('dialog');
  const command = new Element('command'), field = new Element('field');
  document.body = new Element('body');
  document.activeElement = document.body;
  document.getElementById = id => id === 'app' ? root : id === 'modal' ? dialog : null;
  const box = vm.createContext({
    URL, Intl, structuredClone, document, HTMLElement: Element,
    location: {hash: '#hybrid', protocol: 'file:'},
    localStorage: {getItem() { return null; }, setItem() {}},
    window: {matchMedia() { return {matches: false, addEventListener() {}}; }, addEventListener() {}},
  });
  vm.runInContext(code, box);
  const controller = () => ({refresh() {}, destroy() {}});
  Object.assign(box.HF, {
    createStudyController: controller,
    createWorkflowController: controller,
    createExperienceController: controller,
    createCompletionController: controller,
    createIntegrationController: controller,
    shell() { return ''; },
    renderView() {},
    deferredHybridAvailable() { return false; },
    async refreshReleaseProvenance() {},
    installChampionController(_state, callbacks) {
      openModal = callbacks.openModal;
      return {persist() {}, async restore() {}};
    },
    installHybridController() { return {refreshLibraryObserver() {}, destroy() {}}; },
    installTerminalController() {},
  });
  box.HF.boot();
  return {document, dialog, command, field, openModal, flushClose: () => closeTasks.shift()()};
}

test('the application restores the opener when a closed dialog leaves no active control', () => {
  const x = fixture();
  x.command.focus();
  x.openModal('Commands', '');
  x.dialog.close();
  x.document.body.focus();
  x.flushClose();
  assert.equal(x.document.activeElement, x.command);
});

test('a queued dialog close cannot steal focus moved to an input after native restoration', () => {
  const x = fixture();
  x.command.focus();
  x.openModal('Commands', '');
  x.dialog.close();
  assert.equal(x.document.activeElement, x.command, 'native restoration happens before close dispatch');
  x.field.focus();
  x.flushClose();
  assert.equal(x.document.activeElement, x.field, 'the later explicit focus must remain current');
});

test('a stale close event preserves the reopened dialog and its later focus fallback', () => {
  const x = fixture();
  x.command.focus();
  x.openModal('Commands', '');
  x.dialog.close();
  x.field.focus();
  x.openModal('New command', '');
  x.flushClose();
  assert.equal(x.dialog.open, true);
  assert.equal(x.document.activeElement, x.dialog, 'the new modal interaction keeps focus');
  x.dialog.close();
  assert.equal(x.document.activeElement, x.field);
  x.document.body.focus();
  x.flushClose();
  assert.equal(x.document.activeElement, x.field, 'the new opening still has a focus-restoration handler');
});
