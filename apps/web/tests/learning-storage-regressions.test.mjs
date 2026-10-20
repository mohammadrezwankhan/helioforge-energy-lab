import test from 'node:test';
import assert from 'node:assert/strict';
import {controllerFixture} from './helpers/controller-fixture.mjs';

for (const mode of ['blocked', 'write-blocked']) test(`${mode} storage retains session mastery across repeated navigation refreshes`, () => {
  const x = controllerFixture({mode});
  x.dispatch('submit', new x.Form(x.lesson.quiz.map(question => question.answer)));
  x.dispatch('click', new x.Button('export-progress'));
  const first = x.exports.at(-1).payload.mastery_checks[x.lesson.id];
  assert.equal(first.correct, 2);
  for (let i = 0; i < 4; i++) x.completion.refresh();
  x.dispatch('click', new x.Button('export-progress'));
  assert.deepEqual(x.exports.at(-1).payload.mastery_checks[x.lesson.id], first);
  assert.equal(x.exports.at(-1).payload.passed_self_checks.length, 1);
});

test('a rejected persistent reset retains the session record and reports failure', () => {
  const x = controllerFixture({mode: 'mutation-blocked', saved: true});
  x.dispatch('click', new x.Button('confirm-reset-progress'));
  x.completion.refresh();
  x.dispatch('click', new x.Button('export-progress'));
  assert.equal(x.exports.at(-1).payload.mastery_checks[x.lesson.id].correct, 2);
  assert.equal(x.state.hybrid.progress.length, 1);
  assert.equal(x.toasts.at(-1).error, true);
  assert.match(x.toasts.at(-1).message, /could not confirm|did not confirm/i);
  assert.ok(!x.toasts.some(toast => toast.message === 'Browser learning progress reset.'));
});

test('a confirmed reset clears both records, quiz feedback and every progress display', () => {
  const x = controllerFixture({saved: true});
  x.dispatch('submit', new x.Form(x.lesson.quiz.map(question => question.answer)));
  x.dispatch('click', new x.Button('confirm-reset-progress'));
  x.completion.refresh();
  x.dispatch('click', new x.Button('export-progress'));
  assert.equal(x.memory.has('hf-lessons-v2'), false);
  assert.equal(x.memory.has('hf-learning-mastery-v1'), false);
  assert.equal(x.exports.at(-1).payload.passed_self_checks.length, 0);
  assert.equal(Object.keys(x.exports.at(-1).payload.mastery_checks).length, 0);
  assert.equal(x.feedback.innerHTML, '');
  assert.equal(x.state.hybrid.quizResult, null);
  assert.match(x.hero.innerHTML, /^0<small>/);
  assert.match(x.status.textContent, /Foundation 0\/9/);
  assert.equal(x.toasts.at(-1).message, 'Browser learning progress reset.');
});
