namespace HF {
  type StudyRow = Record<string, unknown>;
  type StudyPoint = [number, number];

  const visualPalette = ['#8ee0c2', '#86c8f0', '#dfbd80', '#d99bc7', '#f28d7a'];
  const plot = { left: 54, right: 620, top: 26, bottom: 206 };

  function visualEscape(value: unknown): string {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[character] ?? character);
  }

  function visualId(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'study';
  }

  function finiteValue(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
  }

  function visualNumber(value: unknown, digits = 2): string {
    const numeric = finiteValue(value);
    return numeric == null ? 'Missing' : new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(numeric);
  }

  function heatColor(tone: number): string {
    const fraction = Math.max(0, Math.min(1, tone));
    const low = [48, 130, 121], high = [211, 137, 96];
    const rgb = low.map((channel, index) => Math.round(channel + ((high[index] ?? channel) - channel) * fraction));
    return `rgb(${rgb[0] ?? 48} ${rgb[1] ?? 130} ${rgb[2] ?? 121})`;
  }

  function visualRows(result: StudyResult): StudyRow[] {
    return Array.isArray(result.table) ? result.table : [];
  }

  function visualDetails(result: StudyResult): StudyRow {
    return result.details && typeof result.details === 'object' ? result.details : {};
  }

  function svgImage(def: StudyDefinition, label: string, description: string, content: string, viewBox = '0 0 640 250'): string {
    const id = visualId(def.id);
    return `<svg class="hf-visual-svg" viewBox="${viewBox}" role="img" aria-labelledby="${id}-visual-title ${id}-visual-desc"><title id="${id}-visual-title">${visualEscape(label)}</title><desc id="${id}-visual-desc">${visualEscape(description)}</desc>${content}</svg>`;
  }

  function noData(def: StudyDefinition, reason: string): string {
    return `<figure class="hf-study-visual hf-no-data" data-state="missing">${svgImage(def, `${def.title}: data unavailable`, reason, '<path d="M80 54H560V196H80Z" fill="none" stroke="#657783" stroke-dasharray="7 6"/><path d="M100 174L224 132L330 162L462 82L540 116" fill="none" stroke="#657783" stroke-dasharray="4 7"/>')}<figcaption>${visualEscape(reason)} <strong>Missing</strong> values remain unplotted.</figcaption></figure>`;
  }

  function range(values: Array<number | null>): { min: number; max: number } | null {
    const finite = values.filter((value): value is number => value != null && Number.isFinite(value));
    if (!finite.length) return null;
    let min = Math.min(...finite), max = Math.max(...finite);
    if (min === max) {
      const pad = Math.abs(min) > 1 ? Math.abs(min) * 0.08 : 1;
      min -= pad;
      max += pad;
    }
    return { min, max };
  }

  function linePath(points: Array<StudyPoint | null>): string {
    let path = '', open = false;
    for (const point of points) {
      if (!point) { open = false; continue; }
      path += `${open ? 'L' : 'M'}${point[0].toFixed(2)} ${point[1].toFixed(2)} `;
      open = true;
    }
    return path.trim();
  }

  function lineVisual(def: StudyDefinition, series: StudyResult['series'], slice: number, caption?: string): string {
    const usable = series.filter(item => Array.isArray(item.x) && Array.isArray(item.y) && item.x.length === item.y.length && item.y.length > 0);
    if (!usable.length) return noData(def, 'No finite result series were supplied for this view.');
    const allValues = usable.flatMap(item => item.y.map(finiteValue));
    const bounds = range(allValues);
    if (!bounds) return noData(def, 'The supplied series contains no finite observations.');
    const xAt = (index: number, count: number) => plot.left + (count <= 1 ? 0 : index / (count - 1)) * (plot.right - plot.left);
    const yAt = (value: number) => plot.bottom - (value - bounds.min) / (bounds.max - bounds.min) * (plot.bottom - plot.top);
    const paths: string[] = [];
    const labels: string[] = [];
    const first = usable[0];
    let sliceMarks = '';
    usable.forEach((item, seriesIndex) => {
      const color = visualPalette[seriesIndex % visualPalette.length];
      const points = item.y.map((value, index): StudyPoint | null => {
        const numeric = finiteValue(value);
        return numeric == null ? null : [xAt(index, item.y.length), yAt(numeric)];
      });
      const path = linePath(points);
      if (path) paths.push(`<path d="${path}" fill="none" stroke="${color}" stroke-width="2.2" vector-effect="non-scaling-stroke"/>`);
      const selected = Math.max(0, Math.min(item.y.length - 1, Math.floor(slice)));
      const selectedValue = finiteValue(item.y[selected]);
      if (seriesIndex === 0) sliceMarks = `<line x1="${xAt(selected, item.y.length)}" y1="${plot.top}" x2="${xAt(selected, item.y.length)}" y2="${plot.bottom}" stroke="#dfbd80" stroke-dasharray="4 4"/>${selectedValue == null ? '' : `<circle cx="${xAt(selected, item.y.length)}" cy="${yAt(selectedValue)}" r="4.5" fill="#dfbd80"/>`}`;
      labels.push(`<span><i style="--visual-color:${color}"></i>${visualEscape(item.name)}</span>`);
    });
    const tickText = `<g class="hf-axis-label"><text x="${plot.left}" y="231">${visualEscape(first?.x[0] ?? '')}</text><text x="${plot.right}" y="231" text-anchor="end">${visualEscape(first?.x[first.x.length - 1] ?? '')}</text><text x="6" y="${plot.top + 4}">${visualEscape(visualNumber(bounds.max, 2))}</text><text x="6" y="${plot.bottom}">${visualEscape(visualNumber(bounds.min, 2))}</text></g>`;
    return `<figure class="hf-study-visual">${svgImage(def, `${def.title} result series`, `Actual supplied result series. The vertical marker shows observation ${Math.max(0, Math.floor(slice)) + 1}; null observations are gaps.`, `<path d="M${plot.left} ${plot.top}V${plot.bottom}H${plot.right}" fill="none" stroke="#607483"/>${tickText}${paths.join('')}${sliceMarks}`)}<figcaption>${caption ? `${visualEscape(caption)} ` : ''}${labels.join('')}<span class="hf-visual-note">Actual result values; gaps are preserved.</span></figcaption></figure>`;
  }

  function rowBars(def: StudyDefinition, rows: StudyRow[], labelKey: string, valueKeys: string[], names?: string[], caption?: string): string {
    if (!rows.length || !valueKeys.length) return noData(def, 'No source records are available for this comparison.');
    const seriesValues = valueKeys.flatMap(key => rows.map(row => finiteValue(row[key])));
    const bounds = range([0, ...seriesValues]);
    if (!bounds) return noData(def, 'The source records contain no finite values for this comparison.');
    const x0 = plot.left + (0 - bounds.min) / (bounds.max - bounds.min) * (plot.right - plot.left);
    const rowHeight = 26;
    const top = 30;
    const height = Math.max(190, top + rows.length * rowHeight + 26);
    const content: string[] = [`<line x1="${x0}" y1="18" x2="${x0}" y2="${height - 26}" stroke="#718796"/>`];
    const swatches: string[] = [];
    rows.forEach((row, rowIndex) => {
      const label = visualEscape(row[labelKey] ?? `Record ${rowIndex + 1}`);
      const y = top + rowIndex * rowHeight;
      content.push(`<text class="hf-row-label" x="4" y="${y + 12}">${label}</text>`);
      valueKeys.forEach((key, valueIndex) => {
        const value = finiteValue(row[key]);
        const color = visualPalette[valueIndex % visualPalette.length];
        const barY = y + valueIndex * 6;
        if (value == null) {
          content.push(`<rect x="${plot.left}" y="${barY}" width="5" height="5" fill="none" stroke="#84929b" stroke-dasharray="2 2"><title>${label}: ${visualEscape(names?.[valueIndex] ?? key)} — Missing</title></rect>`);
        } else {
          const end = plot.left + (value - bounds.min) / (bounds.max - bounds.min) * (plot.right - plot.left);
          content.push(`<rect x="${Math.min(x0, end)}" y="${barY}" width="${Math.max(1, Math.abs(end - x0))}" height="5" rx="2" fill="${color}"><title>${label}: ${visualEscape(names?.[valueIndex] ?? key)} ${visualEscape(visualNumber(value, 3))}</title></rect>`);
        }
      });
    });
    valueKeys.forEach((key, index) => swatches.push(`<span><i style="--visual-color:${visualPalette[index % visualPalette.length]}"></i>${visualEscape(names?.[index] ?? key.replaceAll('_', ' '))}</span>`));
    return `<figure class="hf-study-visual">${svgImage(def, `${def.title} record comparison`, `Bars use the supplied record values for ${valueKeys.join(', ')}. Missing values are marked and not imputed.`, content.join(''), `0 0 640 ${height}`)}<figcaption>${caption ? `${visualEscape(caption)} ` : ''}${swatches.join('')}<span class="hf-visual-note">Source records only; Missing values are not imputed.</span></figcaption></figure>`;
  }

  function pvSensitivity(def: StudyDefinition, result: StudyResult, slice: number): string {
    const rows = visualRows(result);
    const capex = [...new Set(rows.map(row => finiteValue(row.capex_eur_kwp)).filter((value): value is number => value != null))].sort((a, b) => a - b);
    const yields = [...new Set(rows.map(row => finiteValue(row.yield_kwh_kwp)).filter((value): value is number => value != null))].sort((a, b) => a - b);
    if (capex.length !== 9 || yields.length !== 9 || rows.length !== 81) return noData(def, `The supplied sensitivity table has ${rows.length} records; a complete 9 by 9 LCOE grid is required to render the heatmap.`);
    const values = rows.map(row => finiteValue(row.lcoe_eur_mwh));
    const extent = range(values);
    if (!extent) return noData(def, 'The 9 by 9 sensitivity table has no finite LCOE values.');
    const selected = Math.max(0, Math.min(rows.length - 1, Math.floor(slice)));
    const cellWidth = 36, cellHeight = 23, left = 94, top = 38;
    const cells = rows.map(row => {
      const rowIndex = capex.indexOf(Number(row.capex_eur_kwp));
      const columnIndex = yields.indexOf(Number(row.yield_kwh_kwp));
      const value = finiteValue(row.lcoe_eur_mwh);
      const x = left + columnIndex * cellWidth;
      const y = top + rowIndex * cellHeight;
      const state = value == null ? 'missing' : 'value';
      const tone = value == null ? 0 : (value - extent.min) / (extent.max - extent.min);
      const title = value == null
        ? 'CAPEX and yield record supplied; LCOE Missing'
        : `CAPEX ${visualNumber(row.capex_eur_kwp, 2)} EUR/kWp; yield ${visualNumber(row.yield_kwh_kwp, 2)} kWh/kWp; LCOE ${visualNumber(value, 3)} EUR/MWh`;
      return `<rect x="${x}" y="${y}" width="${cellWidth - 2}" height="${cellHeight - 2}" rx="3" class="hf-heat-rect" data-state="${state}" style="--cell-color:${heatColor(tone)}"><title>${visualEscape(title)}</title></rect>`;
    }).join('');
    const rowLabels = capex.map((value, index) => `<text x="${left - 7}" y="${top + index * cellHeight + 15}" text-anchor="end">${visualEscape(visualNumber(value, 0))}</text>`).join('');
    const colLabels = yields.map((value, index) => index % 2 === 0 || index === 8 ? `<text x="${left + index * cellWidth + 16}" y="${top + 9 * cellHeight + 14}" text-anchor="middle">${visualEscape(visualNumber(value, 0))}</text>` : '').join('');
    const selection = rows[selected];
    const buttons = rows.map((row, index) => {
      const value = finiteValue(row.lcoe_eur_mwh);
      const tone = value == null ? 0 : (value - extent.min) / (extent.max - extent.min);
      const cellState = value == null ? 'missing' : 'value';
      return `<button type="button" class="hf-heat-button" data-pv-cell="${index}" data-state="${cellState}" style="--cell-color:${heatColor(tone)}" aria-pressed="${index === selected}" title="CAPEX ${visualEscape(visualNumber(row.capex_eur_kwp, 2))} EUR/kWp · yield ${visualEscape(visualNumber(row.yield_kwh_kwp, 2))} kWh/kWp · ${value == null ? 'LCOE Missing' : `${visualEscape(visualNumber(value, 3))} EUR/MWh`}" aria-label="CAPEX ${visualEscape(visualNumber(row.capex_eur_kwp, 2))} euros per kWp, yield ${visualEscape(visualNumber(row.yield_kwh_kwp, 2))} kilowatt-hours per kWp, LCOE ${value == null ? 'Missing' : `${visualEscape(visualNumber(value, 3))} euros per megawatt-hour`}">${value == null ? '—' : visualEscape(visualNumber(value, 1))}</button>`;
    }).join('');
    return `<figure class="hf-study-visual hf-sensitivity" data-state="complete"><div class="hf-heatmap-heading"><span>CAPEX · EUR/kWp</span><span>Specific yield · kWh/kWp</span></div>${svgImage(def, 'PV LCOE sensitivity heatmap', `Nine CAPEX values by nine specific-yield values from the Python result table. Low ${visualNumber(extent.min, 3)} and high ${visualNumber(extent.max, 3)} EUR/MWh; null cells remain missing.`, `<g class="hf-heat-cells">${cells}</g><g class="hf-axis-label">${rowLabels}${colLabels}</g>`, '0 0 450 285')}<div class="hf-heat-button-grid" role="group" aria-label="Select one of the 81 CAPEX and yield result cells">${buttons}</div><p class="hf-heat-selected" data-pv-selection aria-live="polite">${selection ? `Selected: ${visualNumber(selection.capex_eur_kwp, 2)} EUR/kWp · ${visualNumber(selection.yield_kwh_kwp, 2)} kWh/kWp · ${visualNumber(selection.lcoe_eur_mwh, 3)} EUR/MWh` : 'Selected record unavailable.'}</p><figcaption>Each cell is an actual Python result-table record. The parent page retains the complete accessible data table.</figcaption></figure>`;
  }

  function polygonPoints(value: unknown): Array<[number, number]> {
    if (!Array.isArray(value)) return [];
    const points: Array<[number, number]> = [];
    for (const point of value) {
      if (!Array.isArray(point) || point.length !== 2) return [];
      const x = finiteValue(point[0]), y = finiteValue(point[1]);
      if (x == null || y == null) return [];
      points.push([x, y]);
    }
    return points;
  }

  function currentPolygon(def: StudyDefinition, result: StudyResult): Array<[number, number]> {
    const value = result.inputs.land_polygon_m ?? def.data_fields?.find(field => field.name === 'land_polygon_m')?.default;
    return polygonPoints(value);
  }

  function polygonGeometry(points: Array<[number, number]>): { points: string; bounds: [number, number, number, number] } | null {
    if (points.length < 3) return null;
    const xs = points.map(point => point[0]), ys = points.map(point => point[1]);
    let minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    if (minX === maxX) { minX -= 1; maxX += 1; }
    if (minY === maxY) { minY -= 1; maxY += 1; }
    const x = (v: number) => 30 + (v - minX) / (maxX - minX) * 440;
    const y = (v: number) => 220 - (v - minY) / (maxY - minY) * 185;
    return { points: points.map(point => `${x(point[0]).toFixed(2)},${y(point[1]).toFixed(2)}`).join(' '), bounds: [minX, maxX, minY, maxY] };
  }

  function agrivoltaic(def: StudyDefinition, result: StudyResult): string {
    const points = currentPolygon(def, result);
    const geometry = polygonGeometry(points);
    if (!geometry) return noData(def, 'The boundary contains a null or malformed vertex, or fewer than three finite local-metre points; it is not simplified for display. The JSON editor remains available.');
    const vertices = points.map((point, index) => {
      const mapped = geometry.points.split(' ')[index]?.split(',').map(Number) ?? [0, 0];
      const x = mapped[0] ?? 0, y = mapped[1] ?? 0;
      return `<circle cx="${x}" cy="${y}" r="4" fill="#dfbd80"><title>Vertex ${index + 1}: (${visualEscape(visualNumber(point[0], 1))} m, ${visualEscape(visualNumber(point[1], 1))} m)</title></circle>`;
    }).join('');
    return `<figure class="hf-study-visual hf-polygon-editor"><p class="hf-editor-hint">Click inside the field to add a vertex. Coordinates are local metres; the JSON input remains available above.</p><svg class="hf-visual-svg hf-land-map" data-land-map viewBox="0 0 500 260" role="img" aria-labelledby="pv-agrivoltaic-land-title pv-agrivoltaic-land-desc" tabindex="0"><title id="pv-agrivoltaic-land-title">Editable agrivoltaic land boundary</title><desc id="pv-agrivoltaic-land-desc">Current local-metre polygon with click-to-add vertices, displayed on an auto-scaled plan. This is a boundary editor, not a terrain or crop simulation.</desc><path d="M30 35H470M30 220H470" stroke="#425b61" stroke-dasharray="4 7"/><polygon data-land-polygon points="${visualEscape(geometry.points)}" fill="rgba(118,206,154,.20)" stroke="#8ee0c2" stroke-width="3"/><g data-land-vertices>${vertices}</g><text x="32" y="250" class="hf-axis-label">${visualEscape(visualNumber(geometry.bounds[0], 1))} m</text><text x="468" y="250" text-anchor="end" class="hf-axis-label">${visualEscape(visualNumber(geometry.bounds[1], 1))} m</text><text x="8" y="24" class="hf-axis-label">${visualEscape(visualNumber(geometry.bounds[3], 1))} m</text><text x="8" y="222" class="hf-axis-label">${visualEscape(visualNumber(geometry.bounds[2], 1))} m</text></svg><div class="hf-editor-controls"><button type="button" class="btn secondary small" data-polygon-action="undo">Undo vertex</button><button type="button" class="btn secondary small" data-polygon-action="reset">Reset boundary</button><span data-land-status aria-live="polite">${points.length} vertices · local metres</span></div><figcaption>Current source polygon is drawn to scale within its own coordinate bounds. The parent retains the exact JSON vertices.</figcaption></figure>`;
  }

  function trackerHeliodon(def: StudyDefinition, result: StudyResult, slice: number): string {
    const rows = visualRows(result);
    if (!rows.length) return noData(def, 'No sun-position rows were supplied; tracker angles are not fabricated.');
    const index = Math.max(0, Math.min(rows.length - 1, Math.floor(slice)));
    const row = rows[index];
    if (!row) return noData(def, `Tracker row ${index + 1} is unavailable.`);
    const elevation = finiteValue(row.solar_elevation_deg);
    const azimuth = finiteValue(row.solar_azimuth_deg);
    const ideal = finiteValue(row.ideal_angle_deg);
    const corrected = finiteValue(row.tracker_angle_deg);
    const shade = finiteValue(row.shaded_fraction);
    if (elevation == null || azimuth == null || corrected == null) return noData(def, `Tracker row ${index + 1} has missing sun or corrected-angle values.`);
    const sunX = 245 + Math.cos((azimuth - 90) * Math.PI / 180) * (60 + elevation * 1.8);
    const sunY = 118 - Math.sin(elevation * Math.PI / 180) * 78;
    const angle = corrected * Math.PI / 180;
    const panelX = 450 * Math.cos(angle), panelY = -450 * Math.sin(angle);
    const panelStart: [number, number] = [320 - panelX / 2, 190 - panelY / 2];
    const panelEnd: [number, number] = [320 + panelX / 2, 190 + panelY / 2];
    const selectedValues = `<dl class="hf-visual-values"><div><dt>Sun elevation</dt><dd>${visualNumber(elevation, 1)}°</dd></div><div><dt>Sun azimuth</dt><dd>${visualNumber(azimuth, 1)}°</dd></div><div><dt>Ideal tracker</dt><dd>${visualNumber(ideal, 2)}°</dd></div><div><dt>Backtracked tracker</dt><dd>${visualNumber(corrected, 2)}°</dd></div><div><dt>Row-shaded fraction</dt><dd>${visualNumber(shade, 5)}</dd></div></dl>`;
    return `<figure class="hf-study-visual hf-heliodon">${svgImage(def, 'Tracker heliodon at selected sun sample', `Sun position and tracker rotation use actual result row ${index + 1}: elevation ${visualNumber(elevation, 1)} degrees, azimuth ${visualNumber(azimuth, 1)} degrees, corrected tracker angle ${visualNumber(corrected, 2)} degrees. Lines are a geometric orientation sketch, not ray tracing.`, `<path d="M82 193A238 148 0 0 1 558 193" fill="none" stroke="#425e70" stroke-dasharray="4 6"/><path d="M90 194H550" stroke="#657783"/><circle cx="${sunX.toFixed(2)}" cy="${sunY.toFixed(2)}" r="12" fill="#dfbd80"><title>Sun position from the selected result row</title></circle><line x1="${sunX.toFixed(2)}" y1="${(sunY + 14).toFixed(2)}" x2="320" y2="190" stroke="#dfbd80" stroke-width="1.5" stroke-dasharray="5 5"/><circle cx="320" cy="190" r="7" fill="#8ee0c2"/><line x1="${panelStart[0].toFixed(2)}" y1="${panelStart[1].toFixed(2)}" x2="${panelEnd[0].toFixed(2)}" y2="${panelEnd[1].toFixed(2)}" stroke="#8ee0c2" stroke-width="13" stroke-linecap="round"><title>Actual corrected tracker angle: ${visualEscape(visualNumber(corrected, 2))} degrees</title></line><text x="48" y="232" class="hf-axis-label">Sample ${index + 1} of ${rows.length}</text><text x="592" y="232" text-anchor="end" class="hf-axis-label">${visualEscape(visualNumber(elevation, 1))}° elevation · ${visualEscape(visualNumber(azimuth, 1))}° azimuth</text>`)}${selectedValues}<figcaption>Angles and shaded fraction come from the selected Python table row. The geometry shows orientation only; it does not ray-trace shadows.</figcaption></figure>`;
  }

  function quantileTunnel(def: StudyDefinition, rows: StudyRow[], keys: [string, string, string], label: string, slice: number, unit: string): string {
    if (!rows.length) return noData(def, 'No quantile records are available for this tunnel.');
    const low = rows.map(row => finiteValue(row[keys[0]]));
    const median = rows.map(row => finiteValue(row[keys[1]]));
    const high = rows.map(row => finiteValue(row[keys[2]]));
    const bounds = range([...low, ...median, ...high]);
    if (!bounds || rows.length < 2) return noData(def, 'At least two complete quantile records are required for a tunnel.');
    const x = (i: number) => plot.left + i / (rows.length - 1) * (plot.right - plot.left);
    const y = (v: number) => plot.bottom - (v - bounds.min) / (bounds.max - bounds.min) * (plot.bottom - plot.top);
    const segments: number[][] = [];
    let segment: number[] = [];
    for (let i = 0; i < rows.length; i++) {
      if (low[i] == null || high[i] == null || median[i] == null) {
        if (segment.length) segments.push(segment);
        segment = [];
      } else segment.push(i);
    }
    if (segment.length) segments.push(segment);
    const bands = segments.filter(indexes => indexes.length >= 2).map(indexes => {
      const outline = [...indexes.map(i => `${x(i).toFixed(2)},${y(high[i]!).toFixed(2)}`), ...indexes.slice().reverse().map(i => `${x(i).toFixed(2)},${y(low[i]!).toFixed(2)}`)].join(' ');
      return `<polygon points="${outline}" fill="rgba(118,206,154,.20)" stroke="#8ee0c2" stroke-width="1"><title>P10 to P90 supplied quantile band</title></polygon>`;
    }).join('');
    const medPath = linePath(median.map((value, i) => value == null ? null : [x(i), y(value)]));
    const selected = Math.max(0, Math.min(rows.length - 1, Math.floor(slice)));
    const row = rows[selected];
    if (!row) return noData(def, 'The selected quantile year has no table record.');
    const year = row.year ?? selected + 1;
    const lowValue = finiteValue(row[keys[0]]), medValue = finiteValue(row[keys[1]]), highValue = finiteValue(row[keys[2]]);
    const selection = `<line x1="${x(selected)}" y1="${plot.top}" x2="${x(selected)}" y2="${plot.bottom}" stroke="#dfbd80" stroke-dasharray="4 4"/>`;
    const rowsLabels = `<g class="hf-axis-label"><text x="${plot.left}" y="231">${visualEscape(rows[0]?.year ?? 1)}</text><text x="${plot.right}" y="231" text-anchor="end">${visualEscape(rows[rows.length - 1]?.year ?? rows.length)}</text><text x="4" y="${plot.top + 3}">${visualEscape(visualNumber(bounds.max))}</text><text x="4" y="${plot.bottom}">${visualEscape(visualNumber(bounds.min))}</text></g>`;
    return `<figure class="hf-study-visual hf-quantile-tunnel">${svgImage(def, `${label} P10 to P90 quantile tunnel`, `A shaded P10 to P90 band and P50 median from actual result records. Selected year ${year}: P10 ${visualNumber(lowValue)} ${unit}, P50 ${visualNumber(medValue)} ${unit}, P90 ${visualNumber(highValue)} ${unit}. Null records are gaps.`, `<path d="M${plot.left} ${plot.top}V${plot.bottom}H${plot.right}" fill="none" stroke="#607483"/>${rowsLabels}${bands}<path d="${medPath}" fill="none" stroke="#dfbd80" stroke-width="2.5"/>${selection}`)}<div class="hf-quantile-values"><strong>${visualEscape(label)} · year ${visualEscape(year)}</strong><span>P10 ${visualEscape(visualNumber(lowValue))}</span><span>P50 ${visualEscape(visualNumber(medValue))}</span><span>P90 ${visualEscape(visualNumber(highValue))}</span><small>${visualEscape(unit)}</small></div><figcaption>All quantiles are copied from the supplied Python result table; bands do not imply calibration.</figcaption></figure>`;
  }

  function forecastTail(def: StudyDefinition, result: StudyResult): string {
    const histogram = visualDetails(result).histogram;
    if (!histogram || typeof histogram !== 'object') return noData(def, 'No selected-year histogram was included in result details.');
    const record = histogram as StudyRow;
    const edges = Array.isArray(record.edges_eur_mwh) ? record.edges_eur_mwh.map(finiteValue) : [];
    const counts = Array.isArray(record.counts) ? record.counts.map(finiteValue) : [];
    if (!counts.length || edges.length !== counts.length + 1 || counts.some(value => value == null) || edges.some(value => value == null)) return noData(def, 'The selected-year histogram edges and counts are incomplete; no bins were inferred.');
    const maxCount = Math.max(...counts as number[]);
    if (!Number.isFinite(maxCount) || maxCount <= 0) return noData(def, 'The selected-year histogram has no positive observed counts.');
    const left = 56, top = 24, width = 560, height = 182, binWidth = width / counts.length;
    const cleanCounts = counts as number[];
    const cleanEdges = edges as number[];
    const bars = cleanCounts.map((value, index) => {
      const barHeight = value / maxCount * height;
      return `<rect x="${left + index * binWidth + 2}" y="${top + height - barHeight}" width="${Math.max(1, binWidth - 4)}" height="${barHeight}" rx="2" fill="#86c8f0"><title>${visualEscape(visualNumber(cleanEdges[index], 2))} to ${visualEscape(visualNumber(cleanEdges[index + 1], 2))} EUR/MWh · ${visualEscape(value)} paths</title></rect>`;
    }).join('');
    const year = record.year ?? 'Missing';
    return `<figure class="hf-study-visual hf-histogram">${svgImage(def, `Selected-year price histogram, year ${year}`, `Actual histogram detail with ${cleanCounts.length} bins for year ${year}. Counts sum to ${cleanCounts.reduce((sum, value) => sum + value, 0)} paths.`, `<path d="M${left} ${top}V${top + height}H${left + width}" fill="none" stroke="#607483"/>${bars}<g class="hf-axis-label"><text x="${left}" y="232">${visualEscape(visualNumber(cleanEdges[0], 2))}</text><text x="${left + width}" y="232" text-anchor="end">${visualEscape(visualNumber(cleanEdges[cleanEdges.length - 1], 2))}</text><text x="8" y="${top + 3}">${visualEscape(maxCount)}</text><text x="8" y="${top + height}">0</text></g>`)}<figcaption>Year ${visualEscape(year)} histogram from result details; counts and price edges are retained as supplied. ${visualEscape(String(visualDetails(result).loss_convention ?? ''))}</figcaption></figure>`;
  }

  function sculptVisual(def: StudyDefinition, result: StudyResult): string {
    const rows = visualRows(result);
    if (!rows.length) return noData(def, 'No annual debt schedule records were supplied.');
    const covenant = finiteValue(result.metrics.find(metric => metric.label.toLowerCase().includes('minimum dscr'))?.value);
    const dscrs = rows.map(row => finiteValue(row.dscr));
    const dscrBounds = range([...dscrs, covenant]);
    if (!dscrBounds || covenant == null) return noData(def, 'The debt schedule or minimum DSCR covenant is missing.');
    const x = (index: number) => plot.left + index / Math.max(1, rows.length - 1) * (plot.right - plot.left);
    const y = (value: number) => 186 - (value - dscrBounds.min) / (dscrBounds.max - dscrBounds.min) * 132;
    const line = linePath(dscrs.map((value, index) => value == null ? null : [x(index), y(value)]));
    const covenantY = y(covenant);
    const dscrArea = `<rect x="${plot.left}" y="${covenantY}" width="${plot.right - plot.left}" height="${Math.max(0, 186 - covenantY)}" fill="rgba(214,111,98,.10)"/><line x1="${plot.left}" y1="${covenantY}" x2="${plot.right}" y2="${covenantY}" stroke="#f28d7a" stroke-width="2" stroke-dasharray="6 5"><title>Actual covenant: ${visualEscape(visualNumber(covenant, 3))} DSCR</title></line><path d="${line}" fill="none" stroke="#8ee0c2" stroke-width="2.5"/>`;
    const dscrDots = dscrs.map((value, index) => {
      const year = rows[index]?.year ?? index + 1;
      return value == null
        ? `<circle cx="${x(index)}" cy="184" r="3" fill="none" stroke="#85949d" stroke-dasharray="2 2"><title>Year ${visualEscape(year)}: DSCR Missing</title></circle>`
        : `<circle cx="${x(index)}" cy="${y(value)}" r="3" fill="${value < covenant ? '#f28d7a' : '#8ee0c2'}"><title>Year ${visualEscape(year)}: DSCR ${visualEscape(visualNumber(value, 3))}</title></circle>`;
    }).join('');
    const dscrSvg = svgImage(def, 'Actual debt schedule DSCR against the configured covenant', `DSCR values come from the source annual debt schedule. The red horizontal plane is the actual ${visualNumber(covenant, 3)} target; null DSCR values are shown as missing markers.`, `<path d="M${plot.left} ${plot.top}V186H${plot.right}" fill="none" stroke="#607483"/>${dscrArea}${dscrDots}<g class="hf-axis-label"><text x="${plot.left}" y="216">Year ${visualEscape(rows[0]?.year ?? 1)}</text><text x="${plot.right}" y="216" text-anchor="end">Year ${visualEscape(rows[rows.length - 1]?.year ?? rows.length)}</text><text x="8" y="${plot.top + 4}">${visualEscape(visualNumber(dscrBounds.max, 2))}</text><text x="8" y="186">${visualEscape(visualNumber(dscrBounds.min, 2))}</text></g>`);
    const cashflowRows = rows.slice(0, 20);
    const cashflowValues = cashflowRows.flatMap(row => {
      const cfads = finiteValue(row.cfads_eur), service = finiteValue(row.debt_service_eur);
      return [cfads, service, cfads == null || service == null ? null : cfads - service];
    });
    const cashflowMax = Math.max(1, ...cashflowValues.filter((value): value is number => value != null).map(Math.abs));
    const cashflowScale = 102 / cashflowMax;
    const cashflowBaseline = 138;
    const cashBars = cashflowRows.map((row, index) => {
      const cfads = finiteValue(row.cfads_eur), service = finiteValue(row.debt_service_eur);
      const afterService = cfads == null || service == null ? null : cfads - service;
      const entries = [cfads, service, afterService];
      const x0 = 42 + index * 28;
      return entries.map((value, valueIndex) => value == null
        ? `<rect x="${x0 + valueIndex * 7}" y="${cashflowBaseline - 1}" width="5" height="2" fill="none" stroke="#85949d" stroke-dasharray="2 2"><title>Year ${visualEscape(row.year ?? index + 1)}: ${['CFADS', 'Debt service', 'CFADS minus debt service (derived)'][valueIndex]} Missing</title></rect>`
        : `<rect x="${x0 + valueIndex * 7}" y="${value >= 0 ? cashflowBaseline - Math.max(1, Math.abs(value) * cashflowScale) : cashflowBaseline}" width="5" height="${Math.max(1, Math.abs(value) * cashflowScale)}" fill="${visualPalette[valueIndex]}"><title>Year ${visualEscape(row.year ?? index + 1)}: ${['CFADS', 'Debt service', 'CFADS minus debt service (derived)'][valueIndex]} ${visualEscape(visualNumber(value, 0))} EUR</title></rect>`).join('');
    }).join('');
    const barSvg = svgImage(def, 'Financial cashflow by year', 'Bars show actual CFADS, actual scheduled debt service, and CFADS minus scheduled debt service derived from those two table columns. All years share one scale; positive and negative values extend from zero in opposite directions. No revenue or cashflow stages are added.', `<path d="M34 ${cashflowBaseline}H610" stroke="#607483"/>${cashBars}<text x="40" y="24" class="hf-axis-label">Annual EUR amounts · shared scale · zero baseline</text><g class="hf-axis-label"><text x="6" y="40">+${visualEscape(visualNumber(cashflowMax, 0))}</text><text x="6" y="${cashflowBaseline + 4}">0</text><text x="6" y="248">−${visualEscape(visualNumber(cashflowMax, 0))}</text></g>`);
    return `<section class="hf-study-visual hf-sculpt"><figure>${dscrSvg}<figcaption><span><i style="--visual-color:#8ee0c2"></i>Actual DSCR</span><span><i style="--visual-color:#f28d7a"></i>Configured covenant ${visualEscape(visualNumber(covenant, 3))}</span><span>Null debt-free DSCR remains missing.</span></figcaption></figure><figure>${barSvg}<figcaption><span><i style="--visual-color:#8ee0c2"></i>CFADS</span><span><i style="--visual-color:#86c8f0"></i>Scheduled debt service</span><span><i style="--visual-color:#dfbd80"></i>CFADS minus debt service, derived</span></figcaption></figure><p class="hf-visual-note">All source values come from the actual debt schedule. The covenant plane shows the configured result metric.</p></section>`;
  }

  function investmentWaterfall(def: StudyDefinition, result: StudyResult): string {
    const rows = visualRows(result);
    if (!rows.length) return noData(def, 'No LP/sponsor allocation rows were supplied.');
    const max = Math.max(0, ...rows.flatMap(row => [finiteValue(row.lp_eur), finiteValue(row.sponsor_eur)]).filter((value): value is number => value != null));
    if (!Number.isFinite(max) || max <= 0) return noData(def, 'The supplied waterfall has no positive LP or sponsor allocation values.');
    const left = 164, width = 440, rowHeight = 40;
    const bars = rows.map((row, index) => {
      const lp = finiteValue(row.lp_eur), sponsor = finiteValue(row.sponsor_eur);
      const y = 30 + index * rowHeight;
      const lpWidth = lp == null ? 0 : lp / max * width;
      const sponsorWidth = sponsor == null ? 0 : sponsor / max * width;
      const stage = visualEscape(row.stage ?? `Stage ${index + 1}`);
      return `<text x="4" y="${y + 15}" class="hf-row-label">${stage}</text>${lp == null ? `<rect x="${left}" y="${y}" width="5" height="8" fill="none" stroke="#84929b" stroke-dasharray="2 2"><title>LP allocation Missing</title></rect>` : `<rect x="${left}" y="${y}" width="${lpWidth}" height="10" rx="2" fill="#86c8f0"><title>${stage}: LP ${visualEscape(visualNumber(lp, 0))} EUR</title></rect>`}${sponsor == null ? `<rect x="${left}" y="${y + 12}" width="5" height="8" fill="none" stroke="#84929b" stroke-dasharray="2 2"><title>Sponsor allocation Missing</title></rect>` : `<rect x="${left}" y="${y + 12}" width="${sponsorWidth}" height="10" rx="2" fill="#dfbd80"><title>${stage}: sponsor ${visualEscape(visualNumber(sponsor, 0))} EUR</title></rect>`}`;
    }).join('');
    return `<figure class="hf-study-visual">${svgImage(def, 'LP and sponsor distribution by actual waterfall stage', 'Stack components are the supplied LP and sponsor allocation values for each waterfall stage.', `<g class="hf-axis-label"><text x="4" y="18">Stage</text><text x="${left}" y="18">LP (top bar) · Sponsor (lower bar)</text></g>${bars}`, `0 0 640 ${Math.max(210, 42 + rows.length * rowHeight)}`)}<figcaption>Allocation bars use the source result table; no distribution tiers are inferred.</figcaption></figure>`;
  }

  function marketInterconnection(def: StudyDefinition, result: StudyResult, slice: number): string {
    const rows = visualRows(result);
    if (!rows.length) return noData(def, 'No interconnection records are available.');
    const index = Math.max(0, Math.min(rows.length - 1, Math.floor(slice)));
    const row = rows[index];
    if (!row) return noData(def, `Interconnection record ${index + 1} is unavailable.`);
    const flow = finiteValue(row.flow_a_to_b_mw);
    const priceA = finiteValue(row.zone_a_marginal_price_eur_mwh);
    const priceB = finiteValue(row.zone_b_marginal_price_eur_mwh);
    const cap = finiteValue(result.inputs.capacity_mw);
    if (flow == null) return noData(def, `Interconnection record ${index + 1} has no finite A-to-B flow value.`);
    const allPrices = rows.flatMap(record => [finiteValue(record.zone_a_marginal_price_eur_mwh), finiteValue(record.zone_b_marginal_price_eur_mwh)]).filter((value): value is number => value != null);
    const maxAbsPrice = Math.max(1, ...allPrices.map(Math.abs));
    const pillarHeight = (value: number | null) => value == null ? null : Math.abs(value) / maxAbsPrice * 84;
    const levelA = pillarHeight(priceA);
    const levelB = pillarHeight(priceB);
    const pillar = (zone: string, value: number | null, height: number | null, x: number, color: string) => {
      if (height == null || value == null) return `<text x="${x + 34}" y="112" text-anchor="middle" class="hf-axis-label">Price Missing</text>`;
      const baseline = 150;
      const y = value >= 0 ? baseline - height : baseline;
      const labelY = value >= 0 ? y - 7 : y + height + 14;
      return `<rect x="${x}" y="${y}" width="68" height="${Math.max(1, height)}" fill="${color}" rx="3"><title>${zone}: ${visualEscape(visualNumber(value, 2))} EUR/MWh</title></rect><text x="${x + 34}" y="${labelY}" text-anchor="middle" class="hf-axis-label">${visualEscape(visualNumber(value, 1))}</text>`;
    };
    const direction = flow >= 0 ? 'A exports to B' : 'B exports to A';
    return `<figure class="hf-study-visual hf-market-map">${svgImage(def, 'Two-zone interconnection price pillars and recorded flow', `Study records show ${direction}, ${visualNumber(Math.abs(flow), 2)} MW on interval ${row.interval ?? index + 1}. Zone A price ${visualNumber(priceA, 2)} EUR/MWh; zone B price ${visualNumber(priceB, 2)} EUR/MWh. Pillars share a zero baseline and a scale spanning all recorded prices. This is a modeled two-zone case, not a six-country price map.`, `<path d="M98 188L160 126L235 144L258 194Z" fill="rgba(134,200,240,.08)" stroke="#86c8f0" stroke-width="2"/><path d="M382 188L430 132L534 144L564 194Z" fill="rgba(223,189,128,.08)" stroke="#dfbd80" stroke-width="2"/><line x1="120" y1="150" x2="532" y2="150" stroke="#718796" stroke-dasharray="3 4"/><text x="120" y="141" class="hf-axis-label">0</text>${pillar('Zone A', priceA, levelA, 142, '#86c8f0')}${pillar('Zone B', priceB, levelB, 441, '#dfbd80')}<text x="176" y="266" text-anchor="middle" class="hf-row-label">Zone A</text><text x="475" y="266" text-anchor="middle" class="hf-row-label">Zone B</text><path d="M260 104H380" stroke="#8ee0c2" stroke-width="${2 + Math.min(9, Math.abs(flow) / Math.max(1, cap ?? Math.abs(flow)) * 8)}" marker-end="url(#${visualId(def.id)}-arrow)"/><defs><marker id="${visualId(def.id)}-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#8ee0c2"/></marker></defs><text x="320" y="86" text-anchor="middle" class="hf-axis-label">${visualEscape(visualNumber(flow, 1))} MW · interval ${visualEscape(row.interval ?? index + 1)}</text>`, '0 0 640 280')}<figcaption>Actual two-zone study row. The line is shown only for this interconnection study; no solved flow is inferred for other market pages.</figcaption></figure>`;
  }

  function marketVisual(def: StudyDefinition, result: StudyResult, slice: number): string {
    if (def.id === 'markets-interconnection') return marketInterconnection(def, result, slice);
    const rows = visualRows(result);
    if (def.id === 'markets-negative' && rows.length) {
      const points = rows.map(row => ({ x: row.interval, y: row.price_eur_mwh }));
      const line = lineVisual(def, [{ name: 'Settlement price', x_label: '15-minute interval', y_unit: 'EUR/MWh', x: points.map(row => row.x as string | number), y: points.map(row => finiteValue(row.y)) }], slice, `Scenario ${String(visualDetails(result).country_code_scenario_label ?? 'country missing')} · user-supplied threshold results`);
      return line.replace('</figure>', `<p class="hf-visual-note">${visualEscape(visualDetails(result).hypothetical_country_rule_status ?? 'No country rule supplied')}</p></figure>`);
    }
    return lineVisual(def, result.series, slice, 'Single-scenario price records only; no six-zone prices were supplied.');
  }

  function weatherStress(def: StudyDefinition, result: StudyResult): string {
    const rows = visualRows(result);
    if (!rows.length) return noData(def, 'No asset-stress records were supplied.');
    return rowBars(def, rows, 'asset', ['mean_stress_loss_pct', 'p95_stress_loss_pct'], ['Mean stress loss', 'P95 stress loss'], `Seed ${visualNumber(visualDetails(result).seed, 0)} · percentage values from the generated asset records.`);
  }

  function studyRadar(def: StudyDefinition, result: StudyResult): string {
    const details = visualDetails(result);
    const axes = Array.isArray(details.radar_axes) ? details.radar_axes.filter((value): value is string => typeof value === 'string') : [];
    const entries = Array.isArray(details.radar_series) ? details.radar_series.filter(value => value && typeof value === 'object') as StudyRow[] : [];
    if (axes.length < 3 || !entries.length) return noData(def, 'The source result does not contain complete radar_axes and radar_series records.');
    const series = entries.map(entry => {
      const vals = Array.isArray(entry.values) ? entry.values.map(finiteValue) : [];
      return { name: String(entry.name ?? 'Series'), vals };
    });
    if (series.some(entry => entry.vals.length !== axes.length)) return noData(def, 'Radar axis and value lengths do not match.');
    const maxima = axes.map((_, axisIndex) => Math.max(1e-9, ...series.map(entry => Math.abs(entry.vals[axisIndex] ?? 0))));
    const cx = 320, cy = 132, radius = 80;
    const pointAt = (axisIndex: number, fraction: number) => {
      const angle = (-90 + axisIndex * 360 / axes.length) * Math.PI / 180;
      return [cx + Math.cos(angle) * radius * fraction, cy + Math.sin(angle) * radius * fraction];
    };
    const grid = [0.25, 0.5, 0.75, 1].map(fraction => `<polygon points="${axes.map((_, index) => pointAt(index, fraction).map(value => value.toFixed(2)).join(',')).join(' ')}" fill="none" stroke="#425b61"/>`).join('');
    const axisLines = axes.map((axis, index) => {
      const end = pointAt(index, 1.22);
      const label = axis.replaceAll('_', ' ');
      return `<line x1="${cx}" y1="${cy}" x2="${pointAt(index, 1)[0]}" y2="${pointAt(index, 1)[1]}" stroke="#718796"/><text x="${end[0]}" y="${end[1]}" text-anchor="middle" class="hf-axis-label">${visualEscape(label)}</text>`;
    }).join('');
    const polygons = series.map((entry, seriesIndex) => {
      const color = visualPalette[seriesIndex % visualPalette.length];
      const coords = entry.vals.map((value, index) => pointAt(index, value == null ? 0 : Math.abs(value) / (maxima[index] ?? 1))).map(point => point.map(v => v.toFixed(2)).join(',')).join(' ');
      const alt = axes.map((axis, i) => `${axis} ${visualNumber(entry.vals[i], 3)}`).join('; ');
      return `<polygon points="${coords}" fill="${color}" fill-opacity=".12" stroke="${color}" stroke-width="2"><title>${visualEscape(entry.name)}: ${visualEscape(alt)}</title></polygon>`;
    }).join('');
    const controls = `<div class="hf-radar-controls"><button type="button" class="btn secondary small" data-radar-step="-1" aria-label="Rotate radar left">Rotate left</button><button type="button" class="btn secondary small" data-radar-step="1" aria-label="Rotate radar right">Rotate right</button><span data-radar-angle aria-live="polite">View angle 0°</span></div>`;
    const legend = series.map((entry, index) => `<span><i style="--visual-color:${visualPalette[index % visualPalette.length]}"></i>${visualEscape(entry.name)}</span>`).join('');
    return `<section class="hf-study-visual hf-radar"><div class="hf-radar-stage" data-radar-stage tabindex="0" role="group" aria-label="Interactive radar. Use left and right arrow keys to rotate the chart." data-radar-angle-deg="0">${svgImage(def, 'Battery screening wear radar by actual regime', 'Radar axes and series values come directly from result details. Values are normalized independently to each axis maximum for display; source values are listed in the visual caption.', `${grid}${axisLines}${polygons}`)}</div>${controls}<div class="hf-radar-legend">${legend}</div><p class="hf-visual-note">Axis radius is normalized per measured result axis for display; inspect the result table for raw values. This is a screening index, not a degradation forecast.</p></section>`;
  }

  function tetraSelector(def: StudyDefinition): string {
    const nodes = [
      { id: 'research-vibration', label: 'Reliability · vibration' },
      { id: 'research-epd', label: 'Sustainability · EPD records' },
      { id: 'research-scr', label: 'Grid integration · SCR' },
    ];
    const active = nodes.findIndex(node => node.id === def.id);
    const state = active >= 0 ? active : 0;
    return `<section class="hf-study-visual hf-tetra"><div class="hf-tetra-stage" data-tetra-stage data-active-pillar="${state}">${svgImage(def, 'Research pillar tetrahedron', 'A navigation diagram for the three current research studies. The fourth conceptual vertex, operational efficiency, has no study selector in the current catalogue.', '<path d="M320 36L206 187L442 187Z M320 36L321 120L206 187 M320 36L321 120L442 187 M206 187L321 120L442 187" fill="rgba(134,200,240,.08)" stroke="#86c8f0" stroke-width="2"/><circle cx="320" cy="36" r="9" fill="#8ee0c2"/><circle cx="206" cy="187" r="9" fill="#dfbd80"/><circle cx="442" cy="187" r="9" fill="#d99bc7"/><circle cx="321" cy="120" r="9" fill="#86c8f0"/><text x="320" y="22" text-anchor="middle" class="hf-axis-label">Reliability</text><text x="194" y="214" text-anchor="middle" class="hf-axis-label">Sustainability</text><text x="450" y="214" text-anchor="middle" class="hf-axis-label">Grid integration</text><text x="321" y="145" text-anchor="middle" class="hf-axis-label">Operational</text>')}</div><div class="hf-tetra-buttons">${nodes.map(node => `<button type="button" class="btn secondary small" data-study-select="${node.id}" aria-pressed="${node.id === def.id}">${visualEscape(node.label)}${node.id === def.id ? ' · selected' : ''}</button>`).join('')}</div><p class="hf-visual-note">Selectors use existing study IDs. The operational-efficiency concept has no separate study in this catalogue.</p></section>`;
  }

  function tariffValues(def: StudyDefinition, result: StudyResult): number[] {
    const fromResult = result.inputs.tariff;
    if (Array.isArray(fromResult) && fromResult.length === 24) return fromResult.map(value => finiteValue(value) ?? 0);
    const fromDefinition = def.data_fields?.find(field => field.name === 'tariff')?.default;
    return Array.isArray(fromDefinition) && fromDefinition.length === 24 ? fromDefinition.map(value => finiteValue(value) ?? 0) : [];
  }

  function annualStorage(def: StudyDefinition, result: StudyResult): string {
    const tariff = tariffValues(def, result);
    if (tariff.length !== 24) return noData(def, 'The annual tariff editor requires the existing 24-hour tariff array. Its JSON input remains available.');
    const max = Math.max(0.1, ...tariff, 3);
    const bars = tariff.map((value, index) => `<rect x="${56 + index * 23}" y="${192 - value / max * 142}" width="16" height="${value / max * 142}" rx="2" fill="#dfbd80" data-tariff-bar="${index}"><title>Hour ${index}: ${visualEscape(visualNumber(value, 3))} EUR/kWh</title></rect>`).join('');
    const sliders = tariff.map((value, hour) => `<label class="hf-tariff-hour"><span>${String(hour).padStart(2, '0')}</span><input type="range" min="0" max="3" step="0.01" value="${value}" data-tariff-hour="${hour}" aria-label="Hour ${hour} tariff in EUR per kWh"><output data-tariff-value="${hour}">${visualEscape(visualNumber(value, 2))}</output></label>`).join('');
    const svg = svgImage(def, 'Current 24-hour tariff schedule', 'Bars are the current 24 tariff entries in EUR per kWh. Sliders edit the existing tariff array and submit it through the study input callback.', `<path d="M50 192H620" stroke="#607483"/>${bars}<g class="hf-axis-label"><text x="56" y="220">00:00</text><text x="596" y="220" text-anchor="end">23:00</text></g>`);
    return `<section class="hf-study-visual hf-annual-tariff"><figure>${svg}<figcaption>Editable import tariff · EUR/kWh. Use each hourly slider or retain the JSON editor above.</figcaption></figure><div class="hf-tariff-grid" role="group" aria-label="24-hour tariff schedule">${sliders}</div><p class="hf-visual-note">Slider edits emit the existing <code>tariff</code> input field as a 24-value JSON array. No annual result is multiplied from a demonstration day.</p></section>`;
  }

  function researchVisual(def: StudyDefinition, result: StudyResult, slice: number): string {
    let visual: string;
    if (def.id === 'research-epd') visual = rowBars(def, visualRows(result), 'stage', ['emissions_kgco2e'], ['Included emissions · kgCO2e'], 'Only factor-complete included records contribute; missing factors remain missing.');
    else visual = lineVisual(def, result.series, slice);
    return `${tetraSelector(def)}${visual}`;
  }

  function overviewVisual(def: StudyDefinition, result: StudyResult, slice: number): string {
    if (def.id === 'overview-weather') return weatherStress(def, result);
    if (def.id === 'overview-merit') return rowBars(def, visualRows(result), 'asset', ['net_bilateral_eur_mwh', 'net_spot_eur_mwh', 'net_balancing_eur_mwh', 'weighted_net_value_eur_mwh'], ['Bilateral', 'Spot', 'Balancing', 'Weighted net value'], 'Values are the synthetic record assumptions for the selected comparison.');
    return lineVisual(def, result.series, slice, 'Hourly source-result series; no emissions factors are inferred.');
  }

  function storageVisual(def: StudyDefinition, result: StudyResult, slice: number): string {
    if (def.id === 'storage-annual') return annualStorage(def, result);
    if (def.id === 'storage-degradation') return rowBars(def, visualRows(result), 'mechanism', ['loss_pct'], ['Modeled capacity loss · %'], 'Component contributions are the actual uncalibrated screening terms.');
    if (def.id === 'storage-stacking') return rowBars(def, visualRows(result).slice(0, 24), 'interval', ['charge_kw', 'discharge_kw', 'up_reserve_mw', 'down_reserve_mw'], ['Charge kW', 'Discharge kW', 'Up reserve MW', 'Down reserve MW'], 'Intervals use the actual MILP schedule; power and reserve units remain separate.');
    return lineVisual(def, result.series, slice, 'Actual disturbance and device dispatch result series.');
  }

  function investmentVisual(def: StudyDefinition, result: StudyResult): string {
    if (def.id === 'investment-sculpt') return sculptVisual(def, result);
    if (def.id === 'investment-waterfall') return investmentWaterfall(def, result);
    return rowBars(def, visualRows(result), 'year', ['contracted_only_cfads_eur', 'haircut_merchant_cfads_eur', 'full_merchant_cfads_eur'], ['Contracted floor CFADS', 'Haircut merchant CFADS', 'Full merchant CFADS'], 'All bars are source schedule values; the haircut is a scenario input.');
  }

  function genericVisual(def: StudyDefinition, result: StudyResult, slice: number): string {
    if (result.series.some(series => Array.isArray(series.y) && series.y.some(value => finiteValue(value) != null))) return lineVisual(def, result.series, slice);
    const rows = visualRows(result);
    const first = rows[0];
    const numericKey = first ? Object.keys(first).find(key => rows.some(row => finiteValue(row[key]) != null)) : undefined;
    if (first && numericKey) return rowBars(def, rows.slice(0, 20), Object.keys(first)[0] ?? 'record', [numericKey]);
    if (rows.length) {
      const values = rows.map((row, index) => {
        const key = Object.keys(row)[0] ?? '';
        return `<li><strong>${visualEscape(row[key] ?? `Record ${index + 1}`)}</strong><span>${Object.keys(row).length} supplied fields</span></li>`;
      }).join('');
      return `<section class="hf-study-visual hf-record-list"><p class="hf-visual-note">This study returns records but no numeric series to plot. The values below are record labels only.</p><ul>${values}</ul></section>`;
    }
    return noData(def, 'This result has no numeric series or records for a visualization. Metrics and assumptions remain available above.');
  }

  /** Return an accessible, page-specific visual built only from the supplied study contract values. */
  export function studyVisual(def: StudyDefinition, result: StudyResult, slice: number): string {
    if (def.id === 'pv-sensitivity') return pvSensitivity(def, result, slice);
    if (def.id === 'pv-agrivoltaic') return agrivoltaic(def, result);
    if (def.id === 'pv-backtracking') return trackerHeliodon(def, result, slice);
    if (def.id === 'forecast-regimes') return quantileTunnel(def, visualRows(result), ['p10_eur_mwh', 'p50_eur_mwh', 'p90_eur_mwh'], 'Power price', slice, 'EUR/MWh');
    if (def.id === 'forecast-commodities') {
      const rows = visualRows(result);
      const commodities: Array<[string, string, string, string]> = [
        ['Gas', 'gas_p10', 'gas_p50', 'gas_p90'],
        ['Carbon', 'carbon_p10', 'carbon_p50', 'carbon_p90'],
        ['Power', 'power_p10', 'power_p50', 'power_p90'],
      ];
      return `<section class="hf-study-visual hf-commodity-tunnels">${commodities.map(([label, p10, p50, p90]) => quantileTunnel(def, rows, [p10, p50, p90], label, slice, 'scenario currency/unit')).join('')}</section>`;
    }
    if (def.id === 'forecast-tail') return forecastTail(def, result);
    if (def.id === 'investment-sculpt' || def.id === 'investment-tranches' || def.id === 'investment-waterfall') return investmentVisual(def, result);
    if (def.page === 'markets') return marketVisual(def, result, slice);
    if (def.id === 'compare-thermal') return studyRadar(def, result);
    if (def.page === 'research') return researchVisual(def, result, slice);
    if (def.page === 'overview') return overviewVisual(def, result, slice);
    if (def.page === 'storage') return storageVisual(def, result, slice);
    if (def.id === 'pv-albedo') return rowBars(def, visualRows(result), 'month', ['front_energy_kwh', 'rear_energy_kwh'], ['Front energy', 'Rear contribution'], 'Monthly energy uses actual front and rear rows.');
    if (def.id === 'pv-reserve') return lineVisual(def, result.series, slice, 'Reserve balance uses actual year records.');
    if (def.id === 'hybrid-clipping') return rowBars(def, visualRows(result), 'flow', ['energy_kwh'], ['Energy · kWh'], 'Energy-flow components come from the source result table.');
    if (def.page === 'hybrid') return lineVisual(def, result.series, slice, 'Reduced-order study output; see the source limitations above.');
    return genericVisual(def, result, slice);
  }

  function parseInputArray(value: string | undefined, fallback: unknown): number[] {
    let parsed: unknown = fallback;
    if (value != null) {
      try { parsed = JSON.parse(value); } catch { parsed = fallback; }
    }
    return Array.isArray(parsed) ? parsed.map(value => finiteValue(value) ?? 0) : [];
  }

  function setAriaPressed(elements: NodeListOf<HTMLButtonElement> | HTMLButtonElement[], selected: HTMLButtonElement): void {
    elements.forEach(element => element.setAttribute('aria-pressed', String(element === selected)));
  }

  /** Bind direct-manipulation controls contained by a rendered study visual and return a disposer. */
  export function bindStudyVisuals(host: HTMLElement, def: StudyDefinition, draft: StudyDraft, onInput: (name: string, value: string) => void): () => void {
    const cleanups: Array<() => void> = [];
    const listen = (element: Element, name: string, handler: EventListener) => {
      element.addEventListener(name, handler);
      cleanups.push(() => element.removeEventListener(name, handler));
    };

    if (def.id === 'pv-sensitivity') {
      const buttons = Array.from(host.querySelectorAll<HTMLButtonElement>('[data-pv-cell]'));
      const status = host.querySelector<HTMLElement>('[data-pv-selection]');
      buttons.forEach(button => listen(button, 'click', () => {
        setAriaPressed(buttons, button);
        const row = visualRows(draft.result)[Number(button.dataset.pvCell)];
        if (row && status) status.textContent = `Selected: ${visualNumber(row.capex_eur_kwp, 2)} EUR/kWp · ${visualNumber(row.yield_kwh_kwp, 2)} kWh/kWp · ${visualNumber(row.lcoe_eur_mwh, 3)} EUR/MWh`;
      }));
    }

    if (def.id === 'pv-agrivoltaic') {
      const field = def.data_fields?.find(item => item.name === 'land_polygon_m');
      const fallback = draft.result.inputs.land_polygon_m ?? field?.default;
      let vertices = parseInputArrayVertices(draft.values.land_polygon_m, fallback);
      const map = host.querySelector<SVGSVGElement>('[data-land-map]');
      const polygon = host.querySelector<SVGPolygonElement>('[data-land-polygon]');
      const markerGroup = host.querySelector<SVGGElement>('[data-land-vertices]');
      const status = host.querySelector<HTMLElement>('[data-land-status]');
      const draw = () => {
        if (polygon) polygon.setAttribute('points', polygonGeometry(vertices)?.points ?? '');
        if (markerGroup && polygon) {
          markerGroup.replaceChildren();
          const geometry = polygonGeometry(vertices);
          if (geometry) vertices.forEach((point, index) => {
            const mapped = geometry.points.split(' ')[index]?.split(',').map(Number) ?? [0, 0];
            const marker = polygon.ownerDocument.createElementNS('http://www.w3.org/2000/svg', 'circle');
            marker.setAttribute('cx', String(mapped[0] ?? 0));
            marker.setAttribute('cy', String(mapped[1] ?? 0));
            marker.setAttribute('r', '4');
            marker.setAttribute('fill', '#dfbd80');
            const title = polygon.ownerDocument.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = `Vertex ${index + 1}: (${visualNumber(point[0], 1)} m, ${visualNumber(point[1], 1)} m)`;
            marker.appendChild(title);
            markerGroup.appendChild(marker);
          });
        }
        if (status) status.textContent = `${vertices.length} vertices · local metres`;
      };
      const update = () => {
        draw();
        onInput('land_polygon_m', JSON.stringify(vertices));
      };
      draw();
      if (map) {
        const click = (event: Event) => {
          const pointer = event as MouseEvent;
          const rect = map.getBoundingClientRect();
          if (!rect.width || !rect.height || vertices.length >= 128) return;
          const bounds = polygonGeometry(vertices)?.bounds ?? [0, 100, 0, 50];
          const sx = pointer.clientX - rect.left;
          const sy = pointer.clientY - rect.top;
          const viewX = sx / rect.width * 500;
          const viewY = sy / rect.height * 260;
          const x = Math.max(30, Math.min(470, viewX));
          const y = Math.max(35, Math.min(220, viewY));
          const metricX = bounds[0] + (x - 30) / 440 * (bounds[1] - bounds[0]);
          const metricY = bounds[2] + (220 - y) / 185 * (bounds[3] - bounds[2]);
          vertices = [...vertices, [Number(metricX.toFixed(1)), Number(metricY.toFixed(1))]];
          update();
        };
        listen(map, 'click', click);
      }
      host.querySelectorAll<HTMLButtonElement>('[data-polygon-action]').forEach(button => listen(button, 'click', event => {
        event.preventDefault();
        if (button.dataset.polygonAction === 'undo') {
          if (vertices.length > 3) vertices = vertices.slice(0, -1);
        } else if (button.dataset.polygonAction === 'reset') {
          vertices = parseInputArrayVertices(undefined, field?.default ?? fallback);
        }
        update();
      }));
    }

    if (def.id === 'storage-annual') {
      const field = def.data_fields?.find(item => item.name === 'tariff');
      let values = parseInputArray(draft.values.tariff, draft.result.inputs.tariff ?? field?.default);
      const syncTariffControls = () => {
        host.querySelectorAll<HTMLInputElement>('[data-tariff-hour]').forEach(input => {
          const hour = Number(input.dataset.tariffHour);
          if (!Number.isInteger(hour) || hour < 0 || hour >= 24) return;
          input.value = String(values[hour] ?? 0);
          const output = host.querySelector<HTMLOutputElement>(`[data-tariff-value="${hour}"]`);
          if (output) output.value = visualNumber(values[hour], 2);
          const bar = host.querySelector<SVGRectElement>(`[data-tariff-bar="${hour}"]`);
          if (bar) {
            const height = (values[hour] ?? 0) / 3 * 142;
            bar.setAttribute('y', String(192 - height));
            bar.setAttribute('height', String(height));
          }
        });
      };
      syncTariffControls();
      host.querySelectorAll<HTMLInputElement>('[data-tariff-hour]').forEach(input => listen(input, 'input', event => {
        const target = event.currentTarget as HTMLInputElement;
        const hour = Number(target.dataset.tariffHour);
        const value = Number(target.value);
        if (!Number.isInteger(hour) || hour < 0 || hour >= 24 || !Number.isFinite(value)) return;
        values[hour] = Math.max(0, Math.min(3, value));
        const output = host.querySelector<HTMLOutputElement>(`[data-tariff-value="${hour}"]`);
        if (output) output.value = visualNumber(values[hour], 2);
        const bar = host.querySelector<SVGRectElement>(`[data-tariff-bar="${hour}"]`);
        if (bar) {
          const height = values[hour] / 3 * 142;
          bar.setAttribute('y', String(192 - height));
          bar.setAttribute('height', String(height));
          const title = bar.querySelector('title');
          if (title) title.textContent = `Hour ${hour}: ${visualNumber(values[hour], 3)} EUR/kWh`;
        }
        onInput('tariff', JSON.stringify(values));
      }));
    }

    if (def.id === 'compare-thermal') {
      const stage = host.querySelector<HTMLElement>('[data-radar-stage]');
      if (stage) {
        let angle = 0;
        const renderAngle = () => {
          stage.dataset.radarAngleDeg = String(angle);
          stage.style.transform = `perspective(850px) rotateY(${angle}deg)`;
          const status = host.querySelector<HTMLElement>('[data-radar-angle]');
          if (status) status.textContent = `View angle ${angle}°`;
        };
        const rotate = (step: number) => { angle = ((angle + step + 360) % 360); renderAngle(); };
        host.querySelectorAll<HTMLButtonElement>('[data-radar-step]').forEach(button => listen(button, 'click', () => rotate(Number(button.dataset.radarStep) * 12)));
        listen(stage, 'keydown', event => {
          const key = (event as KeyboardEvent).key;
          if (key === 'ArrowLeft') { rotate(-12); (event as KeyboardEvent).preventDefault(); }
          if (key === 'ArrowRight') { rotate(12); (event as KeyboardEvent).preventDefault(); }
        });
      }
    }

    return () => cleanups.splice(0).forEach(cleanup => cleanup());
  }

  function parseInputArrayVertices(raw: string | undefined, fallback: unknown): Array<[number, number]> {
    let value: unknown = fallback;
    if (raw != null) {
      try { value = JSON.parse(raw); } catch { value = fallback; }
    }
    return polygonPoints(value);
  }
}
