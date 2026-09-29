namespace HF {
  // Original simple line glyphs: no external image, font or icon runtime required.
  const glyphs: Record<string, string> = {
    grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    battery:'<rect x="2" y="6" width="18" height="12" rx="3"/><path d="M23 10v4M11 8l-3 5h5l-2 4"/>',
    sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    atom:'<ellipse cx="12" cy="12" rx="10" ry="4"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/><circle cx="12" cy="12" r="1"/>',
    globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 7h14M5 17h14"/>',
    chart:'<path d="M3 3v18h18M6 16l4-6 4 3 6-8"/><path d="M16 5h4v4"/>',
    briefcase:'<rect x="3" y="7" width="18" height="14" rx="3"/><path d="M8 7V4h8v3M3 12c6 3 12 3 18 0M10 13v3h4v-3"/>',
    layers:'<path d="M12 3L2 8l10 5 10-5-10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
    sparkles:'<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v5M17.5 4.5h5"/>',
    arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    diagonal:'<path d="M5 19L19 5M5 5h14v14"/>',
    down:'<path d="m6 9 6 6 6-6"/>',
    download:'<path d="M12 3v12m-5-5 5 5 5-5M3 16v5h18v-5"/>',
    search:'<circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/>',
    leaf:'<path d="M20 3C8 2 2 7 4 15c6 8 16 4 16-12ZM4 20L15 9M10 14v-4M10 14h5"/>',
    shield:'<path d="M12 2L3 6v6c0 6 9 10 9 10s9-4 9-10V6l-9-4Z"/><path d="m7 12 3 3 7-7"/>',
    activity:'<path d="M2 12h5l3-8 4 16 3-8h5"/>',
    bolt:'<path d="M13 2L4 14h7l-1 8 10-13h-8l1-7Z"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    check:'<path d="m4 12 5 5L20 6"/>',
    alert:'<path d="M12 3L2 21h20L12 3ZM12 9v5M12 17v1"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',
    close:'<path d="m5 5 14 14M5 19 19 5"/>',
    menu:'<path d="M3 6h18M3 12h18M3 18h18"/>',
    play:'<path d="m8 4 12 8-12 8V4Z"/>',
    pause:'<path d="M8 4v16M16 4v16"/>',
    code:'<path d="m8 6-6 6 6 6M16 6l6 6-6 6M14 3l-4 18"/>',
    document:'<path d="M5 2h10l4 4v16H5V2ZM14 2v5h5M8 11h8M8 15h8M8 19h5"/>',
    flask:'<path d="M9 2h6M10 2v7L3 20c0 2 18 2 18 0L14 9V2M7 14h10"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    trophy:'<path d="M7 3h10v6c0 7-10 7-10 0V3ZM7 5H3v3c0 3 2 4 5 4M17 5h4v3c0 3-2 4-5 4M12 14v6M7 21h10"/>',
    database:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
    wind:'<path d="M2 8h13c6 0 5-7 1-5M2 12h18c4 0 3 6-1 5M2 16h8c5 0 4 6 0 5"/>',
  };
  export function icon(name: string, size = 20): string {
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${glyphs[name] ?? glyphs['grid']}</svg>`;
  }
  export function brandMark(): string {
    return '<svg class="brand-mark" width="38" height="38" viewBox="0 0 38 38" fill="none" aria-hidden="true"><rect x="1" y="1" width="36" height="36" rx="12" fill="#d7ff84"/><path d="M11 10v18m16-18v18M11 19h16" stroke="#111916" stroke-width="4"/><path d="m23 7-9 14h6l-5 10 12-15h-7l3-9Z" fill="#d7ff84" stroke="#111916" stroke-width="1.5"/></svg>';
  }
}
