/**
 * Construct the application's small HTML/SVG view vocabulary without HTML sinks.
 * Callers still escape interpolated text. This is deliberately not a general HTML
 * parser: executable elements, event attributes and resource-loading CSS fail
 * closed, before the existing view is replaced.
 */
namespace HF { // eslint-disable-line @typescript-eslint/no-namespace, @typescript-eslint/no-unused-vars -- HF is the ordered global-script bundle namespace; modules change its shared runtime contract.
  const viewHTMLTags = new Set(
    'a article aside b br button canvas caption code col colgroup dd details dialog div dl dt em fieldset figcaption figure footer form h1 h2 h3 h4 h5 header hr i input kbd label legend li main nav ol optgroup option output p pre progress section select small span strong summary sup table tbody td textarea th thead time tr ul'.split(
      ' ',
    ),
  );
  const viewSVGTags = new Set(
    'svg circle clipPath defs desc ellipse g line linearGradient marker mask path pattern polygon polyline radialGradient rect stop text title tspan'
      .toLowerCase()
      .split(' '),
  );
  const viewVoidTags = new Set(['br', 'col', 'hr', 'input']);
  const viewSVGResourceAttributes = new Set([
    'clip-path',
    'color-profile',
    'cursor',
    'fill',
    'filter',
    'marker',
    'marker-start',
    'marker-mid',
    'marker-end',
    'mask',
    'stroke',
  ]);
  const svgNames: Record<string, string> = {
    clippath: 'clipPath',
    lineargradient: 'linearGradient',
    radialgradient: 'radialGradient',
  };
  const viewEntities: Record<string, string> = {
    amp: '&',
    lt: '<',
    gt: '>',
    quot: '"',
    apos: "'",
    nbsp: '\u00a0',
    ndash: '\u2013',
    mdash: '\u2014',
    times: '\u00d7',
    minus: '\u2212',
    hellip: '\u2026',
    middot: '\u00b7',
    copy: '\u00a9',
    deg: '\u00b0',
  };
  function viewText(text: string): string {
    return text.replace(/&(#x[\da-f]+|#\d+|[a-z]+);/gi, (entity: string, code: string): string => {
      if (code[0] !== '#') return viewEntities[code] ?? entity;
      const value =
        code[1]?.toLowerCase() === 'x'
          ? Number.parseInt(code.slice(2), 16)
          : Number.parseInt(code.slice(1), 10);
      return value > 0 && value <= 0x10ffff && !(value >= 0xd800 && value <= 0xdfff)
        ? String.fromCodePoint(value)
        : '\ufffd';
    });
  }
  function setViewAttribute(element: Element, name: string, value: string): void {
    const key = name.toLowerCase();
    if (
      /^on/i.test(key) ||
      [
        'srcdoc',
        'is',
        'src',
        'srcset',
        'action',
        'formaction',
        'ping',
        'background',
        'xmlns:xlink',
        'xlink:href',
      ].includes(key)
    ) {
      throw new Error(`Unsupported view attribute: ${name}`);
    }
    if (key === 'style') {
      // CSSOM assignments are compatible with style-src-attr 'none'. None of our
      // numeric chart/animation styles need URL, escaped or executable CSS.
      if (
        /url\s*\(|image-set\s*\(|expression\s*\(|@import|behavior\s*:|-moz-binding|\\|\/\*/i.test(
          value,
        )
      )
        throw new Error('Unsupported view style');
      const style = (element as HTMLElement | SVGElement).style;
      for (const declaration of value.split(';')) {
        if (!declaration.trim()) continue;
        const separator = declaration.indexOf(':');
        if (separator < 1) throw new Error('Invalid view style');
        const property = declaration.slice(0, separator).trim();
        if (!/^(?:--[\w-]+|[a-z][a-z-]*)$/i.test(property))
          throw new Error('Invalid view style property');
        const raw = declaration.slice(separator + 1).trim();
        const important = /\s*!important$/i.test(raw);
        style.setProperty(
          property,
          raw.replace(/\s*!important$/i, ''),
          important ? 'important' : '',
        );
      }
      return;
    }
    if (key === 'href') {
      if (element.namespaceURI === 'http://www.w3.org/2000/svg') {
        if (!/^#[A-Za-z][\w:.-]*$/.test(value)) throw new Error('Unsupported SVG reference');
      } else {
        const url = new URL(value, element.ownerDocument.baseURI);
        if (
          !['http:', 'https:', 'mailto:', 'file:'].includes(url.protocol) ||
          /[\u0000-\u001f\u007f]/.test(value)
        )
          throw new Error('Unsupported view link');
      }
    }
    // SVG presentation attributes are CSS too. Reject escapes and comments before
    // looking for URLs so CSS token normalization cannot hide a resource load.
    // Labels/data attributes keep their literal values; only resource attributes
    // need this CSS restriction. Canonical local fragments remain supported.
    if (
      element.namespaceURI === 'http://www.w3.org/2000/svg' &&
      viewSVGResourceAttributes.has(key) &&
      /\\|\/\*|\*\/|image-set\s*\(|expression\s*\(|@import/i.test(value)
    )
      throw new Error('Unsupported view resource');
    if (/url\s*\(/i.test(value) && !/^url\(#[A-Za-z][\w:.-]*\)$/.test(value))
      throw new Error('Unsupported view resource');
    element.setAttribute(name, value);
  }
  export function viewFragment(markup: string, doc: Document = document): DocumentFragment {
    const fragment = doc.createDocumentFragment();
    const stack: (Element | DocumentFragment)[] = [fragment];
    const names: string[] = [];
    const appendText = (text: string): void => {
      HF.requiredPresent(stack[stack.length - 1], 'stack[stack.length-1]').appendChild(
        doc.createTextNode(viewText(text)),
      );
    };
    let offset = 0;
    while (offset < markup.length) {
      if (markup[offset] !== '<') {
        const next = markup.indexOf('<', offset);
        const end = next < 0 ? markup.length : next;
        appendText(markup.slice(offset, end));
        offset = end;
        continue;
      }
      if (markup.startsWith('<!--', offset)) {
        const end = markup.indexOf('-->', offset + 4);
        if (end < 0) throw new Error('Unclosed view comment');
        offset = end + 3;
        continue;
      }
      const closing = /^<\/\s*([A-Za-z][\w-]*)\s*>/.exec(markup.slice(offset));
      if (closing) {
        const tag = HF.requiredPresent(closing[1], 'closing[1]').toLowerCase();
        if (names[names.length - 1] !== tag) throw new Error(`Unbalanced view element: ${tag}`);
        names.pop();
        stack.pop();
        offset += closing[0].length;
        continue;
      }
      const opening = /^<([A-Za-z][\w-]*)/.exec(markup.slice(offset));
      if (!opening) {
        appendText('<');
        offset++;
        continue;
      }
      const tag = HF.requiredPresent(opening[1], 'opening[1]').toLowerCase();
      const parent = HF.requiredPresent(stack[stack.length - 1], 'stack[stack.length-1]');
      const svg =
        tag === 'svg' ||
        ('namespaceURI' in parent && parent.namespaceURI === 'http://www.w3.org/2000/svg');
      if (!(svg ? viewSVGTags : viewHTMLTags).has(tag))
        throw new Error(`Unsupported view element: ${tag}`);
      const element = svg
        ? doc.createElementNS('http://www.w3.org/2000/svg', svgNames[tag] ?? tag)
        : doc.createElement(tag);
      offset += opening[0].length;
      let selfClosing = false;
      while (offset < markup.length) {
        const whitespace = /^\s+/.exec(markup.slice(offset));
        if (whitespace) offset += whitespace[0].length;
        if (markup.startsWith('/>', offset)) {
          offset += 2;
          selfClosing = true;
          break;
        }
        if (markup[offset] === '>') {
          offset++;
          break;
        }
        const attribute = /^([^\s=<>/"'`]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s<>`]+)))?/.exec(
          markup.slice(offset),
        );
        if (!attribute) throw new Error('Invalid view attribute');
        setViewAttribute(
          element,
          HF.requiredPresent(attribute[1], 'attribute[1]'),
          viewText(attribute[2] ?? attribute[3] ?? attribute[4] ?? ''),
        );
        offset += attribute[0].length;
      }
      if (offset >= markup.length && !markup.endsWith('>'))
        throw new Error('Unclosed view element');
      parent.appendChild(element);
      if (!selfClosing && !viewVoidTags.has(tag)) {
        stack.push(element);
        names.push(tag);
      }
    }
    if (names.length) throw new Error(`Unclosed view element: ${String(names[names.length - 1])}`);
    return fragment;
  }
  export function renderView(target: Element | null | undefined, markup: string): void {
    if (target) target.replaceChildren(viewFragment(markup, target.ownerDocument));
  }
  export function appendView(target: Element | null | undefined, markup: string): void {
    if (target) target.append(viewFragment(markup, target.ownerDocument));
  }
  export function prependView(target: Element | null | undefined, markup: string): void {
    if (target) target.prepend(viewFragment(markup, target.ownerDocument));
  }
  export function replaceViewElement(target: Element | null | undefined, markup: string): void {
    if (target) target.replaceWith(viewFragment(markup, target.ownerDocument));
  }
}
