/**
 * Presentation spies for controller tests whose elements are plain objects.
 * These fixtures assert controller state and emitted markup; view-dom.test.mjs
 * and the browser parity suite exercise the actual DOM construction boundary.
 * Never install this adapter in an actual DOM or the application bundle.
 */
export function installFixtureViews(hf) {
  function fixture(target) {
    if (target && ('nodeType' in target || target.ownerDocument)) throw new Error('Presentation spy requires a plain fixture object');
    return target;
  }
  const views = {
    renderView(target, markup) { if (fixture(target)) target.markup = markup; },
    replaceViewElement(target, markup) { if (fixture(target)) target.replacementMarkup = markup; },
    appendView(target, markup) {
      if (!fixture(target)) return;
      if (typeof target.insertMarkup === 'function') target.insertMarkup('beforeend', markup);
      else target.markup = (target.markup ?? '') + markup;
    },
    prependView(target, markup) {
      if (!fixture(target)) return;
      if (typeof target.insertMarkup === 'function') target.insertMarkup('afterbegin', markup);
      else target.markup = markup + (target.markup ?? '');
    },
  };
  Object.assign(hf, views);
  return views;
}
