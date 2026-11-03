const namedEntities = {amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:' '};

export const decodeHtmlEntities = value => value.replace(/&(?:#x([\da-f]+)|#(\d+)|(amp|lt|gt|quot|apos|nbsp));/gi,
  (_, hex, decimal, named) => {
    if (hex) return String.fromCodePoint(parseInt(hex, 16));
    if (decimal) return String.fromCodePoint(Number(decimal));
    return namedEntities[named.toLowerCase()];
  });
