const namedEntities = {amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:' '};

const decodeHtmlEntities = value => value.replace(/&(?:#x([\da-f]+)|#(\d+)|(amp|lt|gt|quot|apos|nbsp));/gi,
  (_, hex, decimal, named) => {
    if (hex) return String.fromCodePoint(parseInt(hex, 16));
    if (decimal) return String.fromCodePoint(Number(decimal));
    return namedEntities[named.toLowerCase()];
  });

export const extractStaticPageText = (html, origin, route, file) => {
  const main = html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i);
  if (!main) throw Error('Static text page has no main element: ' + file);
  return decodeHtmlEntities(main[1]
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<a\b[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi, (_, href, label) => {
      const text = label.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
      return text ? text + ' (' + new URL(href, origin + route).href + ') ' : '';
    })
    .replace(/<img\b[^>]*\balt="([^"]*)"[^>]*>/gi, (_, alt) => alt + '\n')
    .replace(/<(?:h[1-6]|p|li|summary|figcaption|section|article|div|br|hr|ol|ul)\b[^>]*>/gi, '\n')
    .replace(/<\/(?:h[1-6]|p|li|summary|figcaption|section|article|div|br|hr|ol|ul)\s*>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t\f\v]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim());
};
