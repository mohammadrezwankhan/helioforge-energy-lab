import test from 'node:test';
import assert from 'node:assert/strict';
import {controllerFixture} from './helpers/controller-fixture.mjs';

test('the final correct quiz updates every progress presentation without losing its feedback', () => {
  const x = controllerFixture();
  const lessons = x.hf.HYBRID_CATALOG.lessons;
  x.state.hybrid.progress = lessons.slice(0, -1).map(lesson => lesson.id);
  const last = lessons.at(-1); x.state.hybrid.lessonId = last.id;
  x.completion.refresh();
  x.dispatch('submit', new x.Form(last.quiz.map(question => question.answer)));
  assert.equal(x.hero.textContent, '36 / 36');
  assert.match(x.status.textContent, /Advanced 17\/17/);
  assert.match(x.note.textContent, /Passed 36 of 36/);
  const button = x.buttons.find(item => item.dataset.lesson === last.id);
  assert.equal(button.classList.contains('done'), true);
  assert.doesNotMatch(button.getAttribute('aria-label'), /not passed/);
  assert.match(x.feedback.textContent, /2 \/ 2 correct/);
});
