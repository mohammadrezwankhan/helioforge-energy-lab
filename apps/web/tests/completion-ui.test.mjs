import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {compileScripts} from '../../../scripts/compile-web.mjs';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-completion-ui-'));
const out = path.join(temp, 'completion-ui.js');
try {
  compileScripts([
    path.join(root, 'src/provenance-types.ts'),
    path.join(root, 'src/types.ts'),
    path.join(root, 'src/hybrid-types.ts'),
    path.join(root, 'src/core.ts'),
    path.join(root, 'src/hybrid-data.ts'),
    path.join(root, 'src/hybrid-core.ts'),
    path.join(root, 'src/champion-core.ts'),
    path.join(root, 'src/roadmap-types.ts'),
    path.join(root, 'src/roadmap-data.ts'),
    path.join(root, 'src/scene.ts'),
    path.join(root, 'src/completion-ui.ts'),
  ], out);
} catch (error) {
  throw new Error(`Could not compile completion UI sources: ${error.stderr?.toString() ?? error.message}`);
}
const context = vm.createContext({URL, Intl, Number, String, Math, Array, Object, JSON, Set, Map, Date, structuredClone});
vm.runInContext(fs.readFileSync(out, 'utf8'), context);
const hf = context.HF;

test('tariff editor accepts exactly 24 finite EUR/kWh values inside model bounds', () => {
  const tariff = Array.from({length: 24}, (_, hour) => hour / 10);
  const normalized = hf.normalizeHourlyTariff(tariff);
  assert.deepEqual(JSON.parse(JSON.stringify(normalized)), tariff);
  assert.notEqual(normalized, tariff);
  for (const invalid of [
    null, {}, Array(23).fill(0), Array(25).fill(0),
    [...Array(23).fill(0), '1'], [...Array(23).fill(0), NaN],
    [...Array(23).fill(0), Infinity], [...Array(23).fill(0), -0.01],
    [...Array(23).fill(0), 3.01],
  ]) assert.equal(hf.normalizeHourlyTariff(invalid), null);
});

test('Applied and Advanced lessons require a complete exact-score mastery path', () => {
  const lessons = hf.HYBRID_CATALOG.lessons;
  const foundation = lessons.filter(lesson => lesson.level === 'Foundation');
  const applied = lessons.filter(lesson => lesson.level === 'Applied');
  const advanced = lessons.find(lesson => lesson.level === 'Advanced');
  const appliedLesson = applied[0];
  assert.ok(advanced && appliedLesson);
  assert.equal(foundation.length, 9);
  assert.equal(hf.lessonGate(appliedLesson, []).unlocked, false);
  assert.equal(hf.lessonGate(appliedLesson, foundation.slice(0, -1).map(lesson => lesson.id)).missing.length, 1);
  assert.equal(hf.lessonGate(appliedLesson, foundation.map(lesson => lesson.id)).unlocked, true);
  const allLower = lessons.filter(lesson => lesson.level !== 'Advanced').map(lesson => lesson.id);
  assert.equal(hf.lessonGate(advanced, allLower.slice(0, -1)).unlocked, false);
  assert.equal(hf.lessonGate(advanced, allLower).unlocked, true);
  assert.equal(hf.lessonPrerequisiteIds(advanced).length, foundation.length + applied.length);
});

test('persisted progress parsing accepts known IDs and exact quiz scores only', () => {
  const lesson = hf.HYBRID_CATALOG.lessons[0];
  const valid = hf.parseCompletionRecord({
    passed_self_checks: [lesson.id, lesson.id, 'unknown'],
    mastery_checks: {
      [lesson.id]: {correct: lesson.quiz.length, total: lesson.quiz.length, passed_at: '2026-10-17T12:00:00.000Z'},
      'unknown': {correct: 2, total: 2, passed_at: '2026-10-17T12:00:00.000Z'},
    },
  });
  assert.deepEqual(JSON.parse(JSON.stringify(valid.passed_self_checks)), [lesson.id]);
  assert.equal(valid.mastery_checks[lesson.id].correct, lesson.quiz.length);
  const invalid = hf.parseCompletionRecord({
    passed_self_checks: ['unknown'],
    mastery_checks: {[lesson.id]: {correct: 1, total: lesson.quiz.length, passed_at: 'not-a-date'}},
  });
  assert.deepEqual(JSON.parse(JSON.stringify(invalid.passed_self_checks)), []);
  assert.deepEqual(JSON.parse(JSON.stringify(invalid.mastery_checks)), {});
});

test('synchronized time choices are the intersection of actual finite run hours', () => {
  const run = hours => ({schedule: hours.map(hour => ({hour}))});
  assert.deepEqual(JSON.parse(JSON.stringify(hf.sharedScheduleHours(run([0, 1, 2, 3]), run([2, 3, 4])))), [2, 3]);
  assert.deepEqual(JSON.parse(JSON.stringify(hf.sharedScheduleHours(run([0, NaN, 2]), run([1, 2])))), [2]);
  assert.deepEqual(JSON.parse(JSON.stringify(hf.sharedScheduleHours(run([0]), run([1])))), []);
  assert.deepEqual(JSON.parse(JSON.stringify(hf.sharedScheduleHours(null, run([0])))), []);
});
