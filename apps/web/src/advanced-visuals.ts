namespace HF {
  type AdvancedRow = Record<string, unknown>;
  type Point2 = { x: number; y: number };
  type Point3 = [number, number, number];

  const ADV_MAX_POINTS = 100;
  const ADV_MAX_TRIANGLES = 20;
  const ADV_MAX_PANELS = 10;
  const ADV_MAX_SUNS = 10;

  function advRecord(value: unknown): AdvancedRow {
    return value && typeof value === 'object' && !Array.isArray(value) ? value as AdvancedRow : {};
  }

  function advRows(value: unknown, maximum = ADV_MAX_POINTS): AdvancedRow[] {
    return Array.isArray(value) ? value.slice(0, maximum).map(advRecord) : [];
  }

  function advArray(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
  }

  function advFinite(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
  }

  function advText(value: unknown): string {
    return typeof value === 'string' && value.length ? value : '';
  }

  function advEscape(value: unknown): string {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[character] ?? character);
  }

  function advSlug(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'study';
  }

  function advFmt(value: number | null, digits = 2): string {
    return value == null || !Number.isFinite(value)
      ? 'Missing'
      : new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(value);
  }

  function advStatus(result: StudyResult): string {
    if (result.data_kind === 'synthetic_or_user_supplied_unverified') return 'Synthetic or user-supplied data · unverified';
    if (result.data_kind === 'synthetic') return 'Synthetic example';
    return `Data label: ${result.data_kind || 'unspecified'}`;
  }

  function advFigure(def: StudyDefinition, result: StudyResult, label: string, description: string, content: string, caption: string, viewBox = '0 0 700 340'): string {
    const id = advSlug(def.id);
    const status = advStatus(result);
    return `<figure class="hf-advanced-visual" data-study="${advEscape(def.id)}"><p class="hfav-status">${advEscape(status)}</p><h3 class="hfav-heading">${advEscape(label)}</h3><svg class="hfav-svg" viewBox="${viewBox}" role="img" aria-labelledby="${id}-advanced-title ${id}-advanced-desc"><title id="${id}-advanced-title">${advEscape(label)}</title><desc id="${id}-advanced-desc">${advEscape(description)}</desc>${content}</svg><figcaption>${caption}</figcaption></figure>`;
  }

  function advMissing(def: StudyDefinition, result: StudyResult, reason: string): string {
    return advFigure(def, result, `${def.title}: visualization unavailable`, reason,
      '<rect x="45" y="35" width="610" height="250" rx="18" fill="none" stroke="var(--color-muted)" stroke-dasharray="8 7"/><text x="350" y="168" text-anchor="middle" class="hfav-svg-note">Required result data missing</text>',
      `<span class="hfav-note">${advEscape(reason)} No values or geometry are filled in.</span>`);
  }

  function advRing(count: number, cx: number, cy: number, radiusX: number, radiusY: number): Point2[] {
    if (count <= 0) return [];
    if (count === 1) return [{ x: cx, y: cy }];
    return Array.from({ length: count }, (_, index) => {
      const angle = -Math.PI / 2 + index * Math.PI * 2 / count;
      return { x: cx + Math.cos(angle) * radiusX, y: cy + Math.sin(angle) * radiusY };
    });
  }

  function advColor(value: number, minimum: number, maximum: number): string {
    const fraction = maximum === minimum ? 0.5 : Math.max(0, Math.min(1, (value - minimum) / (maximum - minimum)));
    return `color-mix(in oklch, var(--color-accent) ${Math.round(fraction*100)}%, var(--color-paper-3))`;
  }

  export interface AdvancedPowerflowProjection {
    buses: Array<{ id: string; voltage: number; x: number; y: number }>;
    branches: Array<{ from: string; to: string; activeMw: number; lossMw: number | null }>;
  }

  export function advancedProjectPowerflow(result: StudyResult): AdvancedPowerflowProjection | null {
    const details = advRecord(result.details);
    const rawBuses = advArray(details.buses).slice(0, 24).map(advRecord);
    const buses = rawBuses.map((bus, index) => ({
      id: advText(bus.bus_id),
      voltage: advFinite(bus.voltage_pu),
      index,
    })).filter((bus): bus is { id: string; voltage: number; index: number } => Boolean(bus.id) && bus.voltage != null);
    if (!buses.length) return null;
    const positions = advRing(buses.length, 350, 163, 142, 111);
    const placed = buses.map((bus, index) => ({ ...bus, ...(positions[index] ?? { x: 350, y: 163 }) }));
    const known = new Set(placed.map(bus => bus.id));
    const branches = advRows(details.branches, 100).flatMap(branch => {
      const from = advText(branch.from_bus), to = advText(branch.to_bus);
      const activeMw = advFinite(branch.from_p_mw);
      if (!known.has(from) || !known.has(to) || activeMw == null) return [];
      return [{ from, to, activeMw, lossMw: advFinite(branch.loss_p_mw) }];
    });
    return { buses: placed.map(({ id, voltage, x, y }) => ({ id, voltage, x, y })), branches };
  }

  function advVoltageGrid(buses: AdvancedPowerflowProjection['buses']): string {
    if (!buses.length) return '';
    const values = buses.map(bus => bus.voltage);
    const minimum = Math.min(...values), maximum = Math.max(...values);
    const columns = 29, rows = 15;
    const left = 37, top = 24, width = 626, height = 278;
    const cellWidth = width / columns, cellHeight = height / rows;
    let cells = '';
    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        const x = left + (column + 0.5) * cellWidth;
        const y = top + (row + 0.5) * cellHeight;
        let weightSum = 0, valueSum = 0;
        for (const bus of buses) {
          const distanceSquared = (x - bus.x) ** 2 + (y - bus.y) ** 2;
          const weight = 1 / Math.max(36, distanceSquared);
          weightSum += weight;
          valueSum += bus.voltage * weight;
        }
        const interpolated = weightSum > 0 ? valueSum / weightSum : null;
        if (interpolated == null || !Number.isFinite(interpolated)) continue;
        cells += `<rect class="hfav-voltage-cell" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(cellWidth + 0.5).toFixed(1)}" height="${(cellHeight + 0.5).toFixed(1)}" fill="${advColor(interpolated, minimum, maximum)}"/>`;
      }
    }
    return cells;
  }

  function powerflowVisual(def: StudyDefinition, result: StudyResult): string {
    const projection = advancedProjectPowerflow(result);
    if (!projection) return advMissing(def, result, 'Solved bus voltage rows with finite voltage_pu values are required.');
    const pointById = new Map(projection.buses.map(bus => [bus.id, bus]));
    const maxFlow = Math.max(0, ...projection.branches.map(branch => Math.abs(branch.activeMw)));
    const markerId = `${advSlug(def.id)}-power-arrow`;
    const edges = projection.branches.map(branch => {
      const source = pointById.get(branch.from), target = pointById.get(branch.to);
      if (!source || !target) return '';
      const forward = branch.activeMw >= 0;
      const start = forward ? source : target, end = forward ? target : source;
      const width = 1.4 + 2.7 * (maxFlow > 0 ? Math.abs(branch.activeMw) / maxFlow : 0);
      const dx = end.x - start.x, dy = end.y - start.y;
      const path = `M 0 0 L ${dx.toFixed(1)} ${dy.toFixed(1)}`;
      const midX = (source.x + target.x) / 2, midY = (source.y + target.y) / 2;
      return `<g class="hfav-power-branch"><line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" stroke-width="${width.toFixed(2)}" marker-end="url(#${markerId})"/><circle class="hfav-flow-particle" cx="${start.x}" cy="${start.y}" r="3.8" style="--hfav-path:path('${path}')"/><text class="hfav-edge-label" x="${midX.toFixed(1)}" y="${(midY - 7).toFixed(1)}">${advEscape(advFmt(branch.activeMw))} MW</text></g>`;
    }).join('');
    const buses = projection.buses.map(bus => `<g class="hfav-bus"><circle cx="${bus.x}" cy="${bus.y}" r="13"/><text class="hfav-node-value" x="${bus.x}" y="${(bus.y + 3.5).toFixed(1)}" text-anchor="middle">${advEscape(advFmt(bus.voltage, 3))}</text><text class="hfav-node-label" x="${bus.x}" y="${(bus.y + 28).toFixed(1)}" text-anchor="middle">${advEscape(bus.id)}</text></g>`).join('');
    const voltages = projection.buses.map(bus => bus.voltage);
    const note = `Schematic bus placement; the ground-contour-style voltage backdrop is inverse-distance interpolation of ${projection.buses.length} solved nodal voltage samples. This is visual interpolation on the topology diagram, not a solved spatial field or geographic map. Branch arrows use signed from_p_mw values; plotted branch count is ${projection.branches.length}.`;
    const content = `<defs><marker id="${markerId}" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0L0 6L7 3Z" fill="var(--color-accent)"/></marker></defs><g class="hfav-voltage-grid">${advVoltageGrid(projection.buses)}</g><g class="hfav-power-edges">${edges}</g>${buses}<text class="hfav-axis-hint" x="350" y="326" text-anchor="middle">Schematic node layout · solved voltage ${advEscape(advFmt(Math.min(...voltages), 3))}–${advEscape(advFmt(Math.max(...voltages), 3))} p.u.</text>`;
    const caption = `<span>${advEscape(note)}</span><span class="hfav-note">Solved values shown at nodes · voltage display range ${advEscape(advFmt(Math.min(...voltages), 3))}–${advEscape(advFmt(Math.max(...voltages), 3))} p.u.</span>`;
    return advFigure(def, result, 'Solved hybrid network: voltage samples and active branch flow', note, content, caption);
  }

  export interface AdvancedMarketProjection {
    zones: Array<{ name: string; x: number; y: number; price: number | null; netImport: number | null }>;
    flows: Array<{ from: string; to: string; flowMw: number; limitMw: number | null }>;
  }

  export function advancedProjectMarketsNetwork(result: StudyResult): AdvancedMarketProjection | null {
    const details = advRecord(result.details);
    const zones = advRows(result.table, 6).map(row => ({
      name: advText(row.zone),
      price: advFinite(row.nodal_price_eur_mwh),
      netImport: advFinite(row.net_import_mw),
    })).filter(zone => zone.name);
    if (!zones.length) return null;
    const positions = advRing(zones.length, 350, 163, 142, 111);
    const placed = zones.map((zone, index) => ({ ...zone, ...(positions[index] ?? { x: 350, y: 163 }) }));
    const known = new Set(placed.map(zone => zone.name));
    const flows = advRows(details.line_flows, 100).flatMap(row => {
      const from = advText(row.from_zone), to = advText(row.to_zone);
      const flowMw = advFinite(row.flow_mw);
      if (!known.has(from) || !known.has(to) || flowMw == null) return [];
      return [{ from, to, flowMw, limitMw: advFinite(row.limit_mw) }];
    });
    return { zones: placed, flows };
  }

  function marketVisual(def: StudyDefinition, result: StudyResult): string {
    const projection = advancedProjectMarketsNetwork(result);
    if (!projection) return advMissing(def, result, 'Six-zone result table rows are required to draw zonal nodes.');
    const byName = new Map(projection.zones.map(zone => [zone.name, zone]));
    const largest = Math.max(0, ...projection.flows.map(flow => Math.abs(flow.flowMw)));
    const markerId = `${advSlug(def.id)}-market-arrow`;
    const edges = projection.flows.map(flow => {
      const from = byName.get(flow.from), to = byName.get(flow.to);
      if (!from || !to) return '';
      const start = flow.flowMw >= 0 ? from : to, end = flow.flowMw >= 0 ? to : from;
      const width = 1.2 + 3 * (largest > 0 ? Math.abs(flow.flowMw) / largest : 0);
      const dx = end.x - start.x, dy = end.y - start.y;
      const labelX = (from.x + to.x) / 2, labelY = (from.y + to.y) / 2 - 7;
      const limit = flow.limitMw == null ? 'limit missing' : `limit ${advFmt(flow.limitMw)} MW`;
      return `<g class="hfav-market-flow"><line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" stroke-width="${width.toFixed(2)}" marker-end="url(#${markerId})"/><circle class="hfav-flow-particle hfav-market-particle" cx="${start.x}" cy="${start.y}" r="3.5" style="--hfav-path:path('M 0 0 L ${dx.toFixed(1)} ${dy.toFixed(1)}')"/><text class="hfav-edge-label" x="${labelX.toFixed(1)}" y="${labelY.toFixed(1)}">${advEscape(advFmt(flow.flowMw))} MW</text><title>${advEscape(flow.from)} to ${advEscape(flow.to)}: ${advEscape(advFmt(flow.flowMw))} MW (${advEscape(limit)})</title></g>`;
    }).join('');
    const zones = projection.zones.map(zone => `<g class="hfav-market-zone"><circle cx="${zone.x}" cy="${zone.y}" r="16"/><text class="hfav-node-label" x="${zone.x}" y="${(zone.y + 30).toFixed(1)}" text-anchor="middle">${advEscape(zone.name)}</text>${zone.price == null ? '' : `<text class="hfav-node-value" x="${zone.x}" y="${(zone.y + 4).toFixed(1)}" text-anchor="middle">${advEscape(advFmt(zone.price))}</text>`}</g>`).join('');
    const note = `Actual six-zone DC-OPF line_flows and zonal table rows. The circular node layout is schematic, not a geographic map; line width and direction reflect supplied signed flow_mw.`;
    const content = `<defs><marker id="${markerId}" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0L0 6L7 3Z" fill="var(--color-accent)"/></marker></defs><g class="hfav-market-edges">${edges}</g>${zones}<text class="hfav-axis-hint" x="350" y="326" text-anchor="middle">Schematic network · nodal prices (EUR/MWh) inside nodes</text>`;
    const missing = projection.flows.length ? '' : ' No line-flow rows were supplied, so only zonal nodes are shown.';
    return advFigure(def, result, 'Six-zone DC network flow and nodal price result', note, content,
      `<span>${advEscape(note)}${advEscape(missing)}</span><span class="hfav-note">${projection.zones.length} supplied zone rows · ${projection.flows.length} supplied line flows</span>`);
  }

  function point3(value: unknown): Point3 | null {
    if (!Array.isArray(value) || value.length < 3) return null;
    const x = advFinite(value[0]), y = advFinite(value[1]), z = advFinite(value[2]);
    return x == null || y == null || z == null ? null : [x, y, z];
  }

  function project3d(point: Point3): Point2 {
    return { x: point[0] + point[1] * 0.45, y: point[2] - point[1] * 0.28 };
  }

  function scaleProjected(points: Point2[], box: { x: number; y: number; width: number; height: number }): Array<Point2 | null> {
    if (!points.length) return [];
    const xs = points.map(point => point.x), ys = points.map(point => point.y);
    let minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    if (maxX === minX) { minX -= 0.5; maxX += 0.5; }
    if (maxY === minY) { minY -= 0.5; maxY += 0.5; }
    const padX = (maxX - minX) * 0.08, padY = (maxY - minY) * 0.08;
    minX -= padX; maxX += padX; minY -= padY; maxY += padY;
    return points.map(point => ({
      x: box.x + (point.x - minX) / (maxX - minX) * box.width,
      y: box.y + box.height - (point.y - minY) / (maxY - minY) * box.height,
    }));
  }

  export interface AdvancedPvProjection {
    panels: Array<{ position: Point3; normal: Point3; shadedSamples: number; observedSamples: number }>;
    triangles: Point3[][];
    rays: Array<{ direction: Point3; sampleIndex: number; shaded: boolean | null; energyWh: number | null }>;
    panelCount: number;
    sunCount: number;
    triangleCount: number;
  }

  export function advancedProjectPvRaytrace(result: StudyResult): AdvancedPvProjection | null {
    const inputs = advRecord(result.inputs);
    const rawPanels = advArray(inputs.panel_samples), rawSuns = advArray(inputs.sun_vectors), rawTriangles = advArray(inputs.occluder_triangles);
    const table = advRows(result.table, 1200);
    const panels = rawPanels.slice(0, ADV_MAX_PANELS).map((item, panelIndex) => {
      const panel = advRecord(item);
      const position = point3(panel.position_m), normal = point3(panel.normal);
      const samples = table.filter(row => row.panel_index === panelIndex && typeof row.shaded === 'boolean').slice(0, ADV_MAX_SUNS);
      return position && normal ? { position, normal, shadedSamples: samples.filter(row => row.shaded === true).length, observedSamples: samples.length } : null;
    }).filter((panel): panel is { position: Point3; normal: Point3; shadedSamples: number; observedSamples: number } => panel != null);
    const triangles = rawTriangles.slice(0, ADV_MAX_TRIANGLES).map(value => {
      if (!Array.isArray(value) || value.length !== 3) return null;
      const vertices = value.map(point3);
      return vertices.every((point): point is Point3 => point != null) ? vertices : null;
    }).filter((triangle): triangle is Point3[] => triangle != null);
    const rays = rawSuns.slice(0, ADV_MAX_SUNS).map((value, sampleIndex) => {
      const sun = advRecord(value), direction = point3(sun.direction);
      const row = table.find(item => item.panel_index === 0 && item.sun_index === sampleIndex);
      return direction ? {
        direction, sampleIndex,
        shaded: typeof row?.shaded === 'boolean' ? row.shaded : null,
        energyWh: advFinite(row?.energy_wh),
      } : null;
    }).filter((ray): ray is { direction: Point3; sampleIndex: number; shaded: boolean | null; energyWh: number | null } => ray != null);
    if (!rawPanels.length || !rawSuns.length || !panels.length) return null;
    return { panels, triangles, rays, panelCount: rawPanels.length, sunCount: rawSuns.length, triangleCount: rawTriangles.length };
  }

  function pvVisual(def: StudyDefinition, result: StudyResult): string {
    const projection = advancedProjectPvRaytrace(result);
    if (!projection) return advMissing(def, result, 'Panel positions/normals and sun direction samples from the study inputs are required.');
    const worldPoints: Point3[] = [];
    projection.triangles.forEach(triangle => triangle.forEach(point => worldPoints.push(point)));
    projection.panels.forEach(panel => worldPoints.push(panel.position));
    if (!worldPoints.length) worldPoints.push(...projection.panels.map(panel => panel.position));
    const span = Math.max(1e-9, ...worldPoints.map(point => Math.max(...point.map(Math.abs))));
    const triangleProjected = projection.triangles.flatMap(triangle => triangle.map(project3d));
    const rayProjected: Array<{ start: Point2; end: Point2 } | null> = [];
    const allProjected: Point2[] = [...triangleProjected];
    projection.panels.forEach(panel => {
      const magnitude = Math.hypot(...panel.normal);
      const length = span * 0.2;
      const end: Point3 = magnitude <= 1e-12 ? panel.position : [panel.position[0] + panel.normal[0] / magnitude * length, panel.position[1] + panel.normal[1] / magnitude * length, panel.position[2] + panel.normal[2] / magnitude * length];
      const position = project3d(panel.position), normalEnd = project3d(end);
      allProjected.push(position, normalEnd);
    });
    projection.rays.forEach(ray => {
      const direction = ray.direction;
      const magnitude = Math.hypot(...direction);
      if (magnitude <= 1e-12) { rayProjected.push(null); return; }
      const start = projection.panels[0]?.position;
      if (!start) { rayProjected.push(null); return; }
      const length = span * 0.42;
      const end: Point3 = [start[0] + direction[0] / magnitude * length, start[1] + direction[1] / magnitude * length, start[2] + direction[2] / magnitude * length];
      const projectedStart = project3d(start), projectedEnd = project3d(end);
      allProjected.push(projectedStart, projectedEnd);
      rayProjected.push({ start: projectedStart, end: projectedEnd });
    });
    const scaled = scaleProjected(allProjected, { x: 58, y: 34, width: 584, height: 248 });
    let cursor = 0;
    const triangles = projection.triangles.map((triangle, index) => {
      const points = triangle.map(() => scaled[cursor++] ?? null).filter((point): point is Point2 => point != null);
      if (points.length !== 3) return '';
      return `<polygon class="hfav-terrain-triangle" points="${points.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ')}"><title>Supplied occluder triangle ${index + 1}</title></polygon>`;
    }).join('');
    const panelPoints = projection.panels.map((panel, index) => {
      const point = scaled[cursor++] ?? { x: 350, y: 190 };
      const end = scaled[cursor++] ?? point;
      const shadeClass = panel.shadedSamples > 0 ? 'hfav-panel-shaded' : '';
      const shadeLabel = panel.observedSamples ? `${panel.shadedSamples}/${panel.observedSamples} shaded` : 'shade result missing';
      return `<g class="hfav-panel ${shadeClass}"><line x1="${point.x.toFixed(1)}" y1="${point.y.toFixed(1)}" x2="${end.x.toFixed(1)}" y2="${end.y.toFixed(1)}"/><circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="5"/><text x="${(point.x + 8).toFixed(1)}" y="${(point.y + 4).toFixed(1)}">P${index + 1}: ${shadeLabel}</text></g>`;
    }).join('');
    const rays = projection.rays.map((ray, index) => {
      const ends = rayProjected[index];
      if (!ends) return '';
      const start = scaled[cursor++], end = scaled[cursor++];
      if (!start || !end) return '';
      const state = ray.shaded == null ? 'missing' : ray.shaded ? 'shaded' : 'clear';
      return `<g class="hfav-sun-ray hfav-ray-${state}"><line x1="${start.x.toFixed(1)}" y1="${start.y.toFixed(1)}" x2="${end.x.toFixed(1)}" y2="${end.y.toFixed(1)}" marker-end="url(#${advSlug(def.id)}-ray-arrow)"/><text x="${(end.x + 3).toFixed(1)}" y="${(end.y - 4).toFixed(1)}">S${ray.sampleIndex + 1}: ${state}</text><title>Sun sample ${ray.sampleIndex + 1}, panel 1: ${state}; result energy ${advEscape(advFmt(ray.energyWh))} Wh</title></g>`;
    }).join('');
    const shownPoints = projection.triangles.length * 3 + projection.panels.length * 2 + projection.rays.length * 2;
    const omitted = projection.triangleCount > projection.triangles.length || projection.panelCount > projection.panels.length || projection.sunCount > projection.rays.length;
    const note = 'Supplied XYZ terrain/obstacle triangles, panel sample positions and normals, and sun direction vectors. The 2.5D projection is relative geometry; normal and ray lengths are scaled for visibility and do not encode a measured distance. Shaded/clear labels come only from the supplied result table.';
    const triangleNotice = projection.triangleCount === 0 ? ' No terrain or obstacle triangles were supplied.' : '';
    const omittedNotice = omitted ? ` Rendering is capped at 100 geometry points: ${shownPoints} point markers/vertices are shown from the bounded input arrays.` : '';
    const content = `<defs><marker id="${advSlug(def.id)}-ray-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0L0 6L7 3Z" fill="var(--color-accent)"/></marker></defs><g class="hfav-triangles">${triangles}</g><g class="hfav-panels">${panelPoints}</g><g class="hfav-rays">${rays}</g><text class="hfav-axis-hint" x="350" y="324" text-anchor="middle">Relative XYZ projection · sun rays originate at the first panel sample</text>`;
    return advFigure(def, result, 'Panel sample, sun direction and supplied occluder geometry', note, content,
      `<span>${advEscape(note)}${advEscape(triangleNotice)}${advEscape(omittedNotice)}</span><span class="hfav-note">${projection.panelCount} panel samples · ${projection.sunCount} sun samples · ${projection.triangleCount} supplied triangles</span>`);
  }

  export interface AdvancedRegistrationProjection {
    design: Point3[];
    alignedSurvey: Point3[];
    matches: Array<{ surveyIndex: number; designIndex: number; inlier: boolean }>;
    designCount: number;
    surveyCount: number;
  }

  export function advancedProjectRegistration(result: StudyResult): AdvancedRegistrationProjection | null {
    const inputs = advRecord(result.inputs), details = advRecord(result.details);
    const designRaw = advArray(inputs.design_points_xyz), surveyRaw = advArray(inputs.survey_points_xyz);
    const design = designRaw.slice(0, 50).map(point3);
    const survey = surveyRaw.slice(0, 50).map(point3);
    const matrix = advArray(details.rotation_matrix).map(row => Array.isArray(row) ? row.map(advFinite) : []);
    const translation = advArray(details.translation_m).map(advFinite);
    if (!designRaw.length || !surveyRaw.length || matrix.length !== 3 || matrix.some(row => row.length !== 3 || row.some(value => value == null)) || translation.length !== 3 || translation.some(value => value == null) || design.some(point => point == null) || survey.some(point => point == null)) return null;
    const aligned = survey.map(point => {
      const source = point as Point3;
      return [0, 1, 2].map(axis => (matrix[axis] ?? []).reduce<number>((sum, coefficient, column) => sum + (coefficient ?? 0) * source[column]!, translation[axis] ?? 0)) as Point3;
    });
    if (aligned.some(point => point.some(coordinate => !Number.isFinite(coordinate)))) return null;
    const matches = advRows(result.table, 50).flatMap(row => {
      const surveyIndex = advFinite(row.survey_point_index), designIndex = advFinite(row.design_point_index);
      if (surveyIndex == null || designIndex == null || !Number.isInteger(surveyIndex) || !Number.isInteger(designIndex)) return [];
      return [{ surveyIndex, designIndex, inlier: row.retained_inlier === true }];
    });
    return { design: design as Point3[], alignedSurvey: aligned, matches, designCount: designRaw.length, surveyCount: surveyRaw.length };
  }

  function registrationVisual(def: StudyDefinition, result: StudyResult): string {
    const projection = advancedProjectRegistration(result);
    if (!projection) return advMissing(def, result, 'Design and survey XYZ inputs plus the finite ICP rotation_matrix and translation_m are required.');
    const designIso = projection.design.map(project3d), surveyIso = projection.alignedSurvey.map(project3d);
    const allCloud = scaleProjected([...designIso, ...surveyIso], { x: 54, y: 32, width: 592, height: 260 });
    const scaledDesign = allCloud.slice(0, designIso.length);
    const scaledSurvey = allCloud.slice(designIso.length);
    const design = scaledDesign.map((point, index) => point ? `<circle class="hfav-design-point" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="5"><title>Design point ${index + 1}</title></circle>` : '').join('');
    const survey = scaledSurvey.map((point, index) => {
      if (!point) return '';
      const match = projection.matches.find(row => row.surveyIndex === index);
      const shape = `<path d="M${point.x.toFixed(1)} ${(point.y - 5).toFixed(1)}L${(point.x + 5).toFixed(1)} ${point.y.toFixed(1)}L${point.x.toFixed(1)} ${(point.y + 5).toFixed(1)}L${(point.x - 5).toFixed(1)} ${point.y.toFixed(1)}Z" class="${match?.inlier ? 'hfav-survey-inlier' : match ? 'hfav-survey-outlier' : 'hfav-survey-unpaired'}"><title>Aligned survey point ${index + 1}: ${match ? match.inlier ? 'retained inlier' : 'not retained as an inlier' : 'no result correspondence row'}</title></path>`;
      return shape;
    }).join('');
    const bySurvey = new Map(projection.matches.map(match => [match.surveyIndex, match]));
    const connectors = projection.alignedSurvey.flatMap((_point, index) => {
      const match = bySurvey.get(index), start = scaledSurvey[index], end = scaledDesign[match?.designIndex ?? -1];
      if (!match || !start || !end) return [];
      return [`<line class="${match.inlier ? 'hfav-match-inlier' : 'hfav-match-excluded'}" x1="${start.x.toFixed(1)}" y1="${start.y.toFixed(1)}" x2="${end.x.toFixed(1)}" y2="${end.y.toFixed(1)}"><title>Survey ${index + 1} to design ${match.designIndex + 1}: ${match.inlier ? 'retained inlier' : 'excluded correspondence'}</title></line>`];
    }).join('');
    const omitted = projection.designCount > projection.design.length || projection.surveyCount > projection.alignedSurvey.length;
    const details = advRecord(result.details);
    const photoNote = details.photos_used === false && details.photo_reconstruction === false ? ' No photos or image reconstruction were used in this result.' : '';
    const note = `Design points and survey points transformed by the supplied rigid ICP rotation_matrix and translation_m. Point placement is a relative XYZ projection with no georeferencing; connector status follows actual retained_inlier correspondence rows.${photoNote}`;
    const cap = omitted ? ' Display limited to the first 50 design and 50 survey points.' : '';
    const content = `${connectors}<g class="hfav-design-cloud">${design}</g><g class="hfav-survey-cloud">${survey}</g><g class="hfav-legend"><circle cx="75" cy="314" r="4" class="hfav-design-point"/><text x="85" y="318">Design</text><path d="M165 310L169 314L165 318L161 314Z" class="hfav-survey-inlier"/><text x="175" y="318">Aligned survey · retained</text><path d="M360 310L364 314L360 318L356 314Z" class="hfav-survey-outlier"/><text x="370" y="318">Survey · excluded/unknown</text></g>`;
    return advFigure(def, result, 'Aligned survey point cloud compared with design points', note, content,
      `<span>${advEscape(note)}${advEscape(cap)}</span><span class="hfav-note">${projection.designCount} design points · ${projection.surveyCount} survey points · ${projection.matches.length} supplied correspondence rows</span>`);
  }

  /** Return a source-backed visual for the four studies with structured geometry; null leaves other studies to studyVisual's existing renderer. */
  export function advancedStudyVisual(def: StudyDefinition, result: StudyResult, _slice: number): string | null {
    if (def.id === 'hybrid-powerflow') return powerflowVisual(def, result);
    if (def.id === 'markets-network') return marketVisual(def, result);
    if (def.id === 'pv-raytrace') return pvVisual(def, result);
    if (def.id === 'pilots-registration') return registrationVisual(def, result);
    return null;
  }
}
