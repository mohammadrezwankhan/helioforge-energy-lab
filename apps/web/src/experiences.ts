namespace HF {
  export type TariffLayer = 'energy' | 'network' | 'levies' | 'other';
  export interface TariffStack { energy: number | null; network: number | null; levies: number | null; other: number | null }
  export interface TariffStackSummary { total: number | null; supplied: number; complete: boolean }
  export interface ReviewInput { effectiveDate: string; documentUrl: string }
  export interface ReviewTimelineItem { code: string; country: string; effectiveDate: string; documentUrl: string }

  export const TARIFF_LAYERS: TariffLayer[] = ['energy', 'network', 'levies', 'other'];
  const TARIFF_LABELS: Record<TariffLayer, string> = { energy: 'Energy', network: 'Network', levies: 'Taxes & levies', other: 'Other charges' };

  /** Only complete user-entered stacks are summed; missing components never become zero. */
  export function sumTariffStack(stack: Partial<TariffStack>): TariffStackSummary {
    const values = TARIFF_LAYERS.map(layer => stack[layer]);
    const supplied = values.filter(value => typeof value === 'number' && Number.isFinite(value)).length;
    const complete = supplied === TARIFF_LAYERS.length;
    return { total: complete ? values.reduce<number>((sum, value) => sum + (value as number), 0) : null, supplied, complete };
  }

  export const ENTSOE_AREA_CODES: Record<string, { eic: string; source: string; note: string }> = {
    FR: { eic: '10YFR-RTE------C', source: 'https://eepublicdownloads.entsoe.eu/clean-documents/nc-tasks/Day-ahead_Annex3-MRC%20cost%20coefficients_NEMOS_update.pdf', note: 'France area EIC; confirm the area type offered for the selected data series.' },
    DE: { eic: '10Y1001A1001A82H', source: 'https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2FImportant_Changes_for_SFTP_Extracts.pdf', note: 'ENTSO-E lists this as the Germany–Luxembourg (DE-LU) bidding zone; it is not Germany-only.' },
    ES: { eic: '10YES-REE------0', source: 'https://eepublicdownloads.entsoe.eu/clean-documents/nc-tasks/Day-ahead_Annex3-MRC%20cost%20coefficients_NEMOS_update.pdf', note: 'Spain area EIC; confirm the area type offered for the selected data series.' },
    IT: { eic: '10YIT-GRTN-----B', source: 'https://www.entsoe.eu/fileadmin/user_upload/edi/library/downloads/Market_Areas_v2.0.pdf', note: 'Italy control-area EIC. The Italian day-ahead market has multiple bidding zones.' },
    NL: { eic: '10YNL----------L', source: 'https://eepublicdownloads.entsoe.eu/clean-documents/nc-tasks/Day-ahead_Annex3-MRC%20cost%20coefficients_NEMOS_update.pdf', note: 'Netherlands area EIC; confirm the area type offered for the selected data series.' },
    GB: { eic: '10YGB----------A', source: 'https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2FImportant_Changes_for_SFTP_Extracts.pdf', note: 'Great Britain EIC is listed for BZN and CTA areas; portal series availability can differ.' },
  };

  /** Build a Transparency Platform total-load starting link with the chosen EIC. */
  export function buildEntsoeLoadUrl(countryCode: string): string | null {
    const area = ENTSOE_AREA_CODES[countryCode];
    if (!area) return null;
    const query = new URLSearchParams({
      areaType: 'CTA',
      atch: 'false',
      'biddingZone.values': `CTY|${area.eic}!CTA|${area.eic}`,
      defaultValue: 'false',
      viewType: 'GRAPH',
    });
    return `https://transparency.entsoe.eu/load-domain/r2/totalLoadR2/show?${query.toString()}`;
  }

  export function isHttpDocumentUrl(value: string): boolean {
    try {
      const parsed = new URL(value.trim());
      return parsed.protocol === 'https:' || parsed.protocol === 'http:';
    } catch { return false; }
  }

  /** Return only dated rows backed by both user-supplied fields and sort chronologically. */
  export function reviewTimeline(inputs: Record<string, ReviewInput>, markets: Market[]): ReviewTimelineItem[] {
    return Object.entries(inputs).flatMap(([code, input]) => {
      const market = markets.find(item => item.code === code);
      if (!market || !/^\d{4}-\d{2}-\d{2}$/.test(input.effectiveDate) || !isHttpDocumentUrl(input.documentUrl)) return [];
      const timestamp = Date.parse(`${input.effectiveDate}T00:00:00Z`);
      if (!Number.isFinite(timestamp) || new Date(timestamp).toISOString().slice(0, 10) !== input.effectiveDate) return [];
      return [{ code, country: market.name, effectiveDate: input.effectiveDate, documentUrl: input.documentUrl.trim() }];
    }).sort((a, b) => a.effectiveDate.localeCompare(b.effectiveDate) || a.code.localeCompare(b.code));
  }

  /** Trailing arithmetic mean for display; absent residuals remain absent. */
  export function trailingMean(values: Array<number | null>, windowSize: number): Array<number | null> {
    const size = Math.max(1, Math.floor(windowSize));
    return values.map((_, index) => {
      if (index + 1 < size) return null;
      const window = values.slice(index - size + 1, index + 1);
      if (window.length !== size || window.some(value => value === null || !Number.isFinite(value))) return null;
      return window.reduce<number>((sum, value) => sum + (value as number), 0) / size;
    });
  }

  const esc = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character] ?? character));
  const numberText = (value: number | null | undefined, digits = 2): string => value == null || !Number.isFinite(value) ? '—' : new Intl.NumberFormat(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
  const BLANK_STACK = (): TariffStack => ({ energy: null, network: null, levies: null, other: null });
  const layerNames = TARIFF_LAYERS;

  export function createExperienceController(getState: () => ViewState): { refresh: () => void } {
    const tariffs = new Map<string, TariffStack>();
    const reviews: Record<string, ReviewInput> = {};
    let selectedEntsoe = 'FR';
    let threshold: number | null = null;
    let movingWindow = 5;
    let wireStates: Record<string, boolean> = { sourceBus: true, busLoad: true, loadReturn: true };
    let activeLesson = '';
    let tiltX = 0, tiltY = 0;

    const ensureMarketState = (markets: Market[]): void => {
      for (const market of markets) {
        if (!tariffs.has(market.code)) tariffs.set(market.code, BLANK_STACK());
        if (!reviews[market.code]) reviews[market.code] = { effectiveDate: '', documentUrl: '' };
      }
    };
    const tariffTotalText = (market: Market): string => {
      const summary = sumTariffStack(tariffs.get(market.code) ?? BLANK_STACK());
      return summary.complete ? `${numberText(summary.total)} ${market.currency}/MWh` : `Incomplete · ${summary.supplied}/4 inputs`;
    };
    const escapeAttr = (value: string): string => esc(value);

    function marketPanel(state: ViewState): string {
      const markets = state.data.markets;
      ensureMarketState(markets);
      const cards = markets.map(market => {
        const stack = tariffs.get(market.code) ?? BLANK_STACK();
        return `<article class="hf-experience-tariff-card"><header><span class="hf-experience-country">${esc(market.code)}</span><div><h3>${esc(market.name)}</h3><p>${esc(market.currency)} per MWh · user-entered</p></div></header><div class="hf-experience-stack">${layerNames.map(layer => `<label><span>${TARIFF_LABELS[layer]}</span><div class="hf-experience-input-unit"><input type="number" min="-100000" max="100000" step="any" inputmode="decimal" value="${stack[layer] ?? ''}" data-tariff-code="${escapeAttr(market.code)}" data-tariff-layer="${layer}" aria-label="${TARIFF_LABELS[layer]} tariff component for ${esc(market.name)} (${esc(market.currency)}/MWh)"><small>${esc(market.currency)}/MWh</small></div></label>`).join('')}</div><div class="hf-experience-total"><span>Stack total</span><output data-tariff-total="${escapeAttr(market.code)}">${esc(tariffTotalText(market))}</output></div></article>`;
      }).join('');
      const timeline = reviewTimeline(reviews, markets);
      return `<section class="hf-experiences hf-market-experiences" data-hf-experiences="markets" aria-labelledby="hf-market-experiences-title"><div class="hf-experience-heading"><div><span class="eyebrow">USER-ENTERED SCENARIO INPUTS</span><h2 id="hf-market-experiences-title">Tariff stacks and evidence dates</h2><p>Enter each tariff component in that market’s currency. No defaults or live rates are supplied; totals are local-currency sums and are not directly comparable across currencies.</p></div><button type="button" class="btn secondary" data-experience-action="compare-tariffs">Compare entered stacks</button></div><div class="hf-experience-tariff-grid">${cards}</div><p class="hf-experience-note">Blank fields are missing information, not zero. Negative values are permitted for user-supplied energy-price assumptions.</p><section class="hf-experience-subpanel" aria-labelledby="hf-entsoe-title"><div><span class="eyebrow">OFFICIAL DATA PORTAL</span><h3 id="hf-entsoe-title">Open an ENTSO-E area query</h3><p>Select a market to build a Transparency Platform total-load link using its published EIC area code. The portal may require a different area type or series; the link is a starting point, not a data connector.</p></div><div class="hf-entsoe-controls"><label><span>Country</span><select data-entsoe-country aria-label="Choose country for ENTSO-E query">${markets.map(market => `<option value="${escapeAttr(market.code)}" ${selectedEntsoe === market.code ? 'selected' : ''}>${esc(market.name)} (${esc(market.code)})</option>`).join('')}</select></label><div class="hf-entsoe-linkbox"><code data-entsoe-eic>${ENTSOE_AREA_CODES[selectedEntsoe]?.eic ?? 'No verified EIC'}</code><a class="btn secondary small" data-entsoe-link href="${buildEntsoeLoadUrl(selectedEntsoe) ?? 'https://transparency.entsoe.eu/'}" target="_blank" rel="noopener noreferrer">Open Transparency Platform ↗</a></div><p data-entsoe-note>${esc(ENTSOE_AREA_CODES[selectedEntsoe]?.note ?? 'No verified area code is available for this market.')}</p></div><p class="hf-experience-source">EIC references: <a href="https://eepublicdownloads.entsoe.eu/clean-documents/nc-tasks/Day-ahead_Annex3-MRC%20cost%20coefficients_NEMOS_update.pdf" target="_blank" rel="noopener noreferrer">ENTSO-E Day-Ahead Bidding Area Settings</a>, <a href="https://www.entsoe.eu/fileadmin/user_upload/edi/library/downloads/Market_Areas_v2.0.pdf" target="_blank" rel="noopener noreferrer">ENTSO-E Market Areas v2.0</a> and <a href="https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2FImportant_Changes_for_SFTP_Extracts.pdf" target="_blank" rel="noopener noreferrer">Transparency Platform area-code changes</a>.</p></section><section class="hf-experience-subpanel" aria-labelledby="hf-reg-review-title"><div><span class="eyebrow">NO AUTOMATIC LAW CLAIMS</span><h3 id="hf-reg-review-title">Add review dates supplied by your team</h3><p>Every date and document link below is user-supplied and marked <strong>UNVERIFIED</strong>. Nothing is populated from regulator homepages or inferred as upcoming law.</p></div><div class="hf-reg-review-grid">${markets.map(market => {
        const input = reviews[market.code] ?? { effectiveDate: '', documentUrl: '' };
        return `<div class="hf-reg-review-row"><strong>${esc(market.name)}</strong><label><span>Effective date supplied by reviewer</span><input type="date" value="${escapeAttr(input.effectiveDate)}" data-review-date="${escapeAttr(market.code)}" aria-label="User-supplied effective date for ${esc(market.name)}"></label><label><span>Instrument or document URL supplied by reviewer</span><input type="url" value="${escapeAttr(input.documentUrl)}" placeholder="https://…" data-review-url="${escapeAttr(market.code)}" aria-label="User-supplied legal document URL for ${esc(market.name)}"></label></div>`;
      }).join('')}</div><p class="hf-review-validation" data-review-validation role="status"></p><div class="hf-review-timeline" id="hf-regulatory-timeline">${timelineMarkup(timeline)}</div></section><dialog class="hf-tariff-dialog" data-tariff-dialog aria-labelledby="hf-tariff-dialog-title"><div class="hf-dialog-heading"><div><span class="eyebrow">USER-ENTERED INPUTS</span><h2 id="hf-tariff-dialog-title">Tariff stack comparison</h2></div><button type="button" class="btn quiet" data-experience-action="close-tariffs">Close</button></div><p>Each sum uses one country’s four entered components. Currency conversion, taxes, meter configuration, eligibility and contract terms are not modeled, so totals across currencies are not ranked.</p><div class="hf-table-scroll"><table><thead><tr><th>Market</th>${layerNames.map(layer => `<th>${TARIFF_LABELS[layer]}</th>`).join('')}<th>Total</th><th>Input status</th></tr></thead><tbody data-comparison-body>${comparisonRows(markets)}</tbody></table></div></dialog></section>`;
    }

    function timelineMarkup(items: ReviewTimelineItem[]): string {
      if (!items.length) return '<p class="hf-empty-timeline">No complete date-and-document entries have been supplied.</p>';
      return `<ol>${items.map(item => `<li><time datetime="${escapeAttr(item.effectiveDate)}">${esc(item.effectiveDate)}</time><div><strong>${esc(item.country)}</strong><span class="hf-unverified">UNVERIFIED · user supplied</span></div><a href="${esc(item.documentUrl)}" target="_blank" rel="noopener noreferrer">Open supplied document ↗</a></li>`).join('')}</ol>`;
    }

    function comparisonRows(markets: Market[]): string {
      return markets.map(market => {
        const stack = tariffs.get(market.code) ?? BLANK_STACK();
        const summary = sumTariffStack(stack);
        return `<tr><th scope="row">${esc(market.name)} <small>${esc(market.currency)}/MWh</small></th>${layerNames.map(layer => `<td>${stack[layer] == null ? '—' : numberText(stack[layer])}</td>`).join('')}<td>${summary.complete ? `${numberText(summary.total)} ${esc(market.currency)}` : '—'}</td><td>${summary.complete ? 'Complete' : `Incomplete · ${summary.supplied}/4`}</td></tr>`;
      }).join('');
    }

    function refreshTariffOutputs(): void {
      const state = getState();
      state.data.markets.forEach(market => {
        const output = document.querySelector<HTMLOutputElement>(`[data-tariff-total="${market.code}"]`);
        if (output) output.value = tariffTotalText(market);
      });
      const body = document.querySelector<HTMLElement>('[data-comparison-body]');
      if (body) body.innerHTML = comparisonRows(state.data.markets);
    }

    function entsoeMarkup(): void {
      const area = ENTSOE_AREA_CODES[selectedEntsoe];
      const link = document.querySelector<HTMLAnchorElement>('[data-entsoe-link]');
      const code = document.querySelector<HTMLElement>('[data-entsoe-eic]');
      const note = document.querySelector<HTMLElement>('[data-entsoe-note]');
      if (link) link.href = buildEntsoeLoadUrl(selectedEntsoe) ?? 'https://transparency.entsoe.eu/';
      if (code) code.textContent = area?.eic ?? 'No verified EIC';
      if (note) note.textContent = area?.note ?? 'No verified area code is available for this market.';
    }

    function reviewMarkup(): void {
      const state = getState();
      const timeline = document.getElementById('hf-regulatory-timeline');
      const validation = document.querySelector<HTMLElement>('[data-review-validation]');
      const items = reviewTimeline(reviews, state.data.markets);
      if (timeline) timeline.innerHTML = timelineMarkup(items);
      if (validation) {
        const current = Object.values(reviews).some(row => (row.effectiveDate || row.documentUrl) && !(row.effectiveDate && isHttpDocumentUrl(row.documentUrl)));
        validation.textContent = current ? 'Timeline entries need both a valid date and an HTTP(S) document URL. All accepted entries remain UNVERIFIED.' : '';
      }
    }

    function marketsView(state: ViewState, host: HTMLElement): void {
      if (host.querySelector('[data-hf-experiences="markets"]')) return;
      host.insertAdjacentHTML('beforeend', marketPanel(state));
    }

    function breadboardMarkup(state: ViewState): string {
      const result = state.hybrid.quizResult;
      const checkState = result ? (result.passed ? 'passed' : 'retry') : 'idle';
      const checkText = result ? `${result.correct} / ${result.total} correct · ${result.passed ? 'Self-check passed' : 'Review and try again'}` : 'Use the self-check above to test your understanding. This diagram is a conceptual continuity exercise.';
      const connections: Array<[string, string]> = [
        ['sourceBus', 'Source to bus'], ['busLoad', 'Bus to critical load'], ['loadReturn', 'Load return path'],
      ];
      return `<section class="hf-experiences hf-learning-experiences" data-hf-experiences="lessons" aria-labelledby="hf-breadboard-title"><div class="hf-experience-heading"><div><span class="eyebrow">CONCEPTUAL CONTINUITY</span><h2 id="hf-breadboard-title">Build a path to the critical load</h2><p>Toggle each connection with keyboard or pointer. Continuity is a teaching diagram; it does not simulate electrical arcs, transients, protection or equipment behavior.</p></div><span class="hf-concept-tag">NOT AN ELECTRICAL SIMULATION</span></div><div class="hf-breadboard" data-check-state="${checkState}"><svg class="hf-circuit-svg" viewBox="0 0 760 230" role="img" aria-labelledby="hf-circuit-title hf-circuit-desc"><title id="hf-circuit-title">Source, bus and critical-load continuity loop</title><desc id="hf-circuit-desc">Three switchable wires form a conceptual path from a source through a bus and critical load and back to the source.</desc><path class="hf-circuit-wire" data-circuit-path="sourceBus" d="M160 72 H294"></path><path class="hf-circuit-wire" data-circuit-path="busLoad" d="M466 72 H602"></path><path class="hf-circuit-wire" data-circuit-path="loadReturn" d="M602 158 H160 V112"></path><circle class="hf-circuit-source" cx="112" cy="92" r="30"><title>Conceptual energy source</title></circle><text x="112" y="98" text-anchor="middle">SOURCE</text><rect class="hf-circuit-node" x="294" y="38" width="172" height="68" rx="12"></rect><text x="380" y="79" text-anchor="middle">BUS</text><rect class="hf-circuit-load" data-circuit-load x="602" y="40" width="126" height="126" rx="16"></rect><text x="665" y="91" text-anchor="middle">CRITICAL</text><text x="665" y="112" text-anchor="middle">LOAD</text><circle class="hf-circuit-ripple" data-circuit-ripple cx="665" cy="103" r="35"></circle><text class="hf-circuit-return" x="378" y="194" text-anchor="middle">RETURN PATH</text></svg><div class="hf-circuit-switches" role="group" aria-label="Switch conceptual circuit connections">${connections.map(([id, label]) => `<button type="button" class="hf-wire-switch" data-wire-toggle="${id}" data-wire-label="${label}" aria-pressed="${wireStates[id] !== false}" aria-label="${label}, ${wireStates[id] === false ? 'open' : 'closed'}">${label}<span>${wireStates[id] === false ? 'Open' : 'Closed'}</span></button>`).join('')}</div><p class="hf-circuit-status" data-circuit-status role="status" aria-live="polite"></p><div class="hf-check-result ${checkState}" data-lesson-check>${result?.passed ? '<span class="hf-check-medal" aria-label="Self-check passed">✓</span>' : ''}<span>${esc(checkText)}</span></div></div><details class="hf-formula-inspector"><summary>Inspect formulas and units</summary><div class="hf-formula-grid"><article><h3>AC power balance</h3><code>g⁺ + PV − q + d = load + c + g⁻</code><p><strong>Terms:</strong> grid import, photovoltaic output, curtailment, discharge, site load, charge and grid export.</p><small>Power in kW. Source: repository numerical methodology, storage dispatch.</small></article><article><h3>Battery energy transition</h3><code>s[t+1] = s[t] + ηc·c[t]·Δt − d[t]·Δt/ηd</code><p>Charge/discharge power is integrated over the interval using charge and discharge efficiency.</p><small>Energy in kWh; power in kW; Δt in hours. Source: repository numerical methodology, storage dispatch.</small></article><article><h3>Conditional reliability</h3><code>S(t) = exp(−(t/scale)<sup>shape</sup>)</code><p>The existing reliability screen evaluates the user-specified Weibull survival model.</p><small>t and scale in hours; shape is dimensionless; S(t) is a fraction. Not a fitted field model.</small></article><article><h3>Discounted PV levelized cost</h3><code>LCOE = discounted lifecycle costs / discounted lifetime MWh</code><p>The PV screen keeps its constant-money discounting and generation assumptions explicit.</p><small>Output in EUR/MWh. This formula is a screening summary, not a tariff or bid.</small></article></div></details></section>`;
    }

    function syncCircuit(): void {
      const complete = Object.values(wireStates).every(Boolean);
      document.querySelectorAll<SVGPathElement>('[data-circuit-path]').forEach(path => {
        const open = wireStates[path.dataset.circuitPath ?? ''] === false;
        path.classList.toggle('open', open);
        path.classList.toggle('closed', !open);
      });
      document.querySelectorAll<HTMLButtonElement>('[data-wire-toggle]').forEach(button => {
        const isClosed = wireStates[button.dataset.wireToggle ?? ''] !== false;
        button.setAttribute('aria-pressed', String(isClosed));
        button.setAttribute('aria-label', `${button.dataset.wireLabel ?? 'Connection'}, ${isClosed ? 'closed' : 'open'}`);
        const status = button.querySelector('span');
        if (status) status.textContent = isClosed ? 'Closed' : 'Open';
      });
      document.querySelector('[data-circuit-load]')?.classList.toggle('illuminated', complete);
      const ripple = document.querySelector('[data-circuit-ripple]');
      ripple?.classList.toggle('active', !complete);
      const openNames = Object.entries(wireStates).filter(([, isClosed]) => !isClosed).map(([key]) => ({ sourceBus: 'source-to-bus link', busLoad: 'bus-to-critical-load link', loadReturn: 'return path' }[key] ?? key));
      const status = document.querySelector<HTMLElement>('[data-circuit-status]');
      if (status) status.textContent = complete ? 'Continuity shown: the conceptual source, bus and critical load form a closed loop.' : `Continuity interrupted at ${openNames.join(' and ')}. The load illumination is off; the ripple marks an open connection conceptually.`;
    }

    function decorateLessonCheck(): void {
      const board = document.querySelector<HTMLElement>('[data-hf-experiences="lessons"] .hf-breadboard');
      if (!board) return;
      const result = getState().hybrid.quizResult;
      const check = board.querySelector<HTMLElement>('[data-lesson-check]');
      board.dataset.checkState = result ? (result.passed ? 'passed' : 'retry') : 'idle';
      if (check) {
        check.className = `hf-check-result ${result ? (result.passed ? 'passed' : 'retry') : 'idle'}`;
        check.innerHTML = `${result?.passed ? '<span class="hf-check-medal" aria-label="Self-check passed">✓</span>' : ''}<span>${result ? `${result.correct} / ${result.total} correct · ${result.passed ? 'Self-check passed' : 'Review and try again'}` : 'Use the self-check above to test your understanding. This diagram is a conceptual continuity exercise.'}</span>`;
      }
      syncCircuit();
    }

    function lessonsView(state: ViewState, host: HTMLElement): void {
      if (activeLesson !== state.hybrid.lessonId) {
        activeLesson = state.hybrid.lessonId;
        wireStates = { sourceBus: true, busLoad: true, loadReturn: true };
      }
      if (host.querySelector('[data-hf-experiences="lessons"]')) return;
      host.insertAdjacentHTML('beforeend', breadboardMarkup(state));
      syncCircuit();
    }

    function driftChart(series: Drift['series'], alertIndices: number[], windowSize: number, cutoff: number): string {
      if (!series.length) return '<p class="hf-experience-empty">No residual observations are available. No points are synthesized.</p>';
      const width = 760, height = 270, left = 56, right = 18, top = 18, bottom = 42;
      const values = series.map(row => Number.isFinite(row.residual_pct) ? row.residual_pct : null);
      const means = trailingMean(values, windowSize);
      const maxAbs = Math.max(cutoff, ...values.map(value => Math.abs(value ?? 0)), 0.25) * 1.15;
      const x = (index: number): number => left + (series.length <= 1 ? 0 : index / (series.length - 1) * (width - left - right));
      const y = (value: number): number => top + (maxAbs - value) / (2 * maxAbs) * (height - top - bottom);
      const pointLine = values.flatMap((value, index) => value == null ? [] : [`${x(index).toFixed(1)},${y(value).toFixed(1)}`]).join(' ');
      const meanLine = means.flatMap((value, index) => value == null ? [] : [`${x(index).toFixed(1)},${y(value).toFixed(1)}`]).join(' ');
      const zeroY = y(0), hiY = y(cutoff), loY = y(-cutoff);
      const alertSet = new Set(alertIndices);
      const ticks = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs].map(value => `<g><line x1="${left}" x2="${width - right}" y1="${y(value)}" y2="${y(value)}" class="hf-drift-grid"/><text x="${left - 8}" y="${y(value) + 4}" text-anchor="end">${numberText(value, 1)}%</text></g>`).join('');
      const circles = series.map((row, index) => `<circle class="hf-drift-point ${alertSet.has(row.index) ? 'server-flagged' : ''} ${Math.abs(row.residual_pct) >= cutoff ? 'over-cutoff' : ''}" cx="${x(index).toFixed(1)}" cy="${y(row.residual_pct).toFixed(1)}" r="${alertSet.has(row.index) ? 4.5 : 3.5}"><title>Source residual ${row.index + 1}: ${numberText(row.residual_pct, 3)}%; model z-score ${numberText(row.z_score, 2)}${alertSet.has(row.index) ? '; flagged by backend screen' : ''}</title></circle>`).join('');
      const table = series.map(row => `<tr><th scope="row">${row.index + 1}</th><td>${numberText(row.residual_pct, 3)}%</td><td>${numberText(row.z_score, 2)}</td><td>${alertSet.has(row.index) ? 'Backend screen flagged' : 'Not flagged by backend screen'}</td><td>${Math.abs(row.residual_pct) >= cutoff ? 'At / beyond UI cutoff' : 'Within UI cutoff'}</td></tr>`).join('');
      return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Source performance residual observations, trailing moving mean, user-selected review cutoff and backend alert points">${ticks}<rect class="hf-drift-cutoff-band" x="${left}" y="${hiY}" width="${width - left - right}" height="${Math.max(0, loY - hiY)}"/><line class="hf-drift-zero" x1="${left}" x2="${width - right}" y1="${zeroY}" y2="${zeroY}"/><line class="hf-drift-threshold" x1="${left}" x2="${width - right}" y1="${hiY}" y2="${hiY}"/><line class="hf-drift-threshold" x1="${left}" x2="${width - right}" y1="${loY}" y2="${loY}"/><polyline class="hf-drift-source-line" points="${pointLine}"/><polyline class="hf-drift-mean-line" points="${meanLine}"/>${circles}<text x="${left}" y="${height - 13}">Observation 1</text><text x="${width - right}" y="${height - 13}" text-anchor="end">Observation ${series.length}</text></svg><div class="hf-drift-legend"><span><i class="source"></i>Source residual points</span><span><i class="mean"></i>Trailing moving mean (${windowSize} points)</span><span><i class="flagged"></i>Backend alert</span><span><i class="cutoff"></i>User review cutoff ±${numberText(cutoff, 2)}%</span></div><details class="hf-drift-data"><summary>Inspect source residual values (${series.length})</summary><div class="hf-table-scroll"><table><thead><tr><th>Observation</th><th>Residual</th><th>Model z-score</th><th>Backend flag</th><th>UI cutoff</th></tr></thead><tbody>${table}</tbody></table></div></details>`;
    }

    function researchPanel(state: ViewState): string {
      const series = state.data.drift.series;
      const maximum = Math.max(0.25, ...series.map(row => Math.abs(row.residual_pct)));
      if (threshold == null) threshold = maximum / 2;
      movingWindow = Math.max(1, Math.min(Math.max(1, series.length), movingWindow));
      return `<section class="hf-experiences hf-research-experiences" data-hf-experiences="research" aria-labelledby="hf-drift-inspector-title"><div class="hf-experience-heading"><div><span class="eyebrow">SOURCE RESIDUALS · DISPLAY CONTROLS</span><h2 id="hf-drift-inspector-title">Inspect the supplied drift observations</h2><p>Points and backend flags come from the current synthetic or user-supplied residual series. The moving mean and cutoff are display aids, not a new diagnostic model.</p></div></div><div class="hf-drift-controls"><label><span>Trailing window <output data-window-output>${movingWindow}</output> observations</span><input type="range" min="1" max="${Math.max(1, series.length)}" step="1" value="${movingWindow}" data-drift-window aria-label="Trailing moving mean window size"></label><label><span>User review cutoff <output data-cutoff-output>${numberText(threshold, 2)}%</output></span><input type="range" min="0" max="${maximum}" step="${Math.max(0.01, maximum / 100)}" value="${threshold}" data-drift-cutoff aria-label="User-selected absolute residual review cutoff in percent"></label></div><p class="hf-experience-note">The existing backend’s flagged observation indices remain separately marked. Moving-window values are arithmetic display summaries of actual residual points; no values are generated for missing observations.</p><div class="hf-drift-chart" data-drift-chart>${driftChart(series, state.data.drift.alert_indices, movingWindow, threshold)}</div></section>`;
    }

    function refreshDrift(): void {
      const state = getState();
      const chart = document.querySelector<HTMLElement>('[data-drift-chart]');
      if (!chart) return;
      const maximum = Math.max(0.25, ...state.data.drift.series.map(row => Math.abs(row.residual_pct)));
      threshold = Math.max(0, Math.min(maximum, threshold ?? maximum / 2));
      movingWindow = Math.max(1, Math.min(Math.max(1, state.data.drift.series.length), movingWindow));
      chart.innerHTML = driftChart(state.data.drift.series, state.data.drift.alert_indices, movingWindow, threshold);
      const windowOutput = document.querySelector<HTMLOutputElement>('[data-window-output]');
      if (windowOutput) windowOutput.value = String(movingWindow);
      const cutoffOutput = document.querySelector<HTMLOutputElement>('[data-cutoff-output]');
      if (cutoffOutput) cutoffOutput.value = `${numberText(threshold, 2)}%`;
    }

    function medianCapex(state: ViewState): number {
      const ordered = state.data.portfolio.map(project => project.capex_meur).filter(Number.isFinite).sort((a, b) => a - b);
      if (!ordered.length) return 0;
      return ordered[Math.floor((ordered.length - 1) / 2)] ?? 0;
    }

    function applyCapexHighlight(state: ViewState): void {
      const table = document.getElementById('project-table');
      const rows = table?.querySelectorAll<HTMLTableRowElement>('tbody tr');
      if (!rows) return;
      const cutoff = capexThreshold ?? medianCapex(state);
      let count = 0;
      rows.forEach(row => {
        const id = row.querySelector<HTMLElement>('[data-project]')?.dataset.project;
        const project = state.data.portfolio.find(item => item.id === id);
        const highlighted = Boolean(project && project.capex_meur <= cutoff);
        row.classList.toggle('hf-capex-highlight', highlighted);
        if (highlighted) count++;
      });
      const status = document.querySelector<HTMLElement>('[data-capex-status]');
      if (status) status.textContent = `${count} currently visible fictional project${count === 1 ? '' : 's'} are at or below €${numberText(cutoff, 1)}m screening CAPEX.`;
    }

    let capexThreshold: number | null = null;
    function overviewPanel(state: ViewState): string {
      const maximum = Math.max(0.1, ...state.data.portfolio.map(project => project.capex_meur));
      capexThreshold = Math.min(maximum, capexThreshold ?? medianCapex(state));
      return `<section class="hf-experiences hf-overview-experiences" data-hf-experiences="overview" aria-labelledby="hf-overview-control-title"><div class="hf-experience-heading"><div><span class="eyebrow">INTERACTIVE PORTFOLIO EXPLORATION</span><h2 id="hf-overview-control-title">Explore the actual synthetic portfolio</h2><p>Move the pointer or use arrow keys on the overview hero for a small 3D tilt. The slider highlights real rows by their supplied screening CAPEX field.</p></div></div><label class="hf-capex-control"><span>Highlight projects at or below <output data-capex-value>€${numberText(capexThreshold, 1)}m</output> screening CAPEX</span><input type="range" min="0" max="${maximum}" step="0.1" value="${capexThreshold}" data-capex-threshold aria-label="Highlight projects by screening CAPEX threshold in millions of euros"><span data-capex-status role="status"></span></label></section>`;
    }

    function bindHeroTilt(state: ViewState): void {
      const hero = document.querySelector<HTMLElement>('.hero');
      if (!hero || hero.dataset.experienceTiltBound === 'true') return;
      hero.dataset.experienceTiltBound = 'true';
      hero.tabIndex = 0;
      hero.setAttribute('aria-label', 'Overview hero. Move pointer or use arrow keys to tilt the panel up to six degrees.');
      const reduced = (): boolean => state.motionOff || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
      const draw = (): void => {
        if (reduced()) { tiltX = 0; tiltY = 0; hero.style.transform = ''; return; }
        hero.style.transform = `perspective(1200px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
      };
      hero.addEventListener('pointermove', event => {
        if (reduced()) return;
        const rect = hero.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        const pointer = event as PointerEvent;
        tiltY = Math.max(-6, Math.min(6, ((pointer.clientX - rect.left) / rect.width - 0.5) * 12));
        tiltX = Math.max(-6, Math.min(6, (0.5 - (pointer.clientY - rect.top) / rect.height) * 12));
        draw();
      });
      hero.addEventListener('pointerleave', () => { tiltX = 0; tiltY = 0; draw(); });
      hero.addEventListener('keydown', event => {
        const keyEvent = event as KeyboardEvent;
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home'].includes(keyEvent.key) && !(keyEvent.target instanceof HTMLButtonElement)) {
          keyEvent.preventDefault();
          if (keyEvent.key === 'Home') { tiltX = 0; tiltY = 0; }
          if (keyEvent.key === 'ArrowUp') tiltX = Math.min(6, tiltX + 1.5);
          if (keyEvent.key === 'ArrowDown') tiltX = Math.max(-6, tiltX - 1.5);
          if (keyEvent.key === 'ArrowLeft') tiltY = Math.max(-6, tiltY - 1.5);
          if (keyEvent.key === 'ArrowRight') tiltY = Math.min(6, tiltY + 1.5);
          draw();
        }
      });
      draw();
    }

    function refresh(): void {
      const state = getState();
      const host = document.getElementById('page-content');
      if (!host) return;
      if (state.page === 'markets') marketsView(state, host);
      else if (state.page === 'lessons') lessonsView(state, host);
      else if (state.page === 'research') {
        if (!host.querySelector('[data-hf-experiences="research"]')) host.insertAdjacentHTML('beforeend', researchPanel(state));
      } else if (state.page === 'overview') {
        if (!host.querySelector('[data-hf-experiences="overview"]')) {
          host.insertAdjacentHTML('beforeend', overviewPanel(state));
          const controls = host.querySelector<HTMLElement>('[data-hf-experiences="overview"]');
          const portfolio = host.querySelector<HTMLElement>('.portfolio-panel');
          if (controls && portfolio) host.insertBefore(controls, portfolio);
        }
        bindHeroTilt(state);
        applyCapexHighlight(state);
      }
    }

    document.addEventListener('input', event => {
      const input = event.target as HTMLInputElement;
      if (input.dataset.tariffCode && input.dataset.tariffLayer) {
        const code = input.dataset.tariffCode;
        const layer = input.dataset.tariffLayer as TariffLayer;
        const stack = tariffs.get(code) ?? BLANK_STACK();
        const parsed = input.value.trim() === '' ? null : Number(input.value);
        if (parsed == null || (Number.isFinite(parsed) && Math.abs(parsed) <= 100000)) stack[layer] = parsed;
        tariffs.set(code, stack);
        refreshTariffOutputs();
      }
      if (input.dataset.reviewDate) {
        const code = input.dataset.reviewDate;
        reviews[code] = { ...(reviews[code] ?? { effectiveDate: '', documentUrl: '' }), effectiveDate: input.value };
        reviewMarkup();
      }
      if (input.dataset.reviewUrl) {
        const code = input.dataset.reviewUrl;
        reviews[code] = { ...(reviews[code] ?? { effectiveDate: '', documentUrl: '' }), documentUrl: input.value };
        reviewMarkup();
      }
      if (input.hasAttribute('data-drift-window')) {
        movingWindow = Number(input.value);
        refreshDrift();
      }
      if (input.hasAttribute('data-drift-cutoff')) {
        threshold = Number(input.value);
        refreshDrift();
      }
      if (input.hasAttribute('data-capex-threshold')) {
        capexThreshold = Number(input.value);
        const output = document.querySelector<HTMLOutputElement>('[data-capex-value]');
        if (output) output.value = `€${numberText(capexThreshold, 1)}m`;
        applyCapexHighlight(getState());
      }
      if (input.id === 'project-search') window.setTimeout(() => applyCapexHighlight(getState()), 0);
    });

    document.addEventListener('change', event => {
      const input = event.target as HTMLInputElement;
      if (input.id === 'portfolio-market') window.setTimeout(() => applyCapexHighlight(getState()), 0);
    });

    document.addEventListener('change', event => {
      const select = event.target as HTMLSelectElement;
      if (select.matches('[data-entsoe-country]')) { selectedEntsoe = select.value; entsoeMarkup(); }
    });

    document.addEventListener('click', event => {
      const target = event.target as Element;
      const action = target.closest<HTMLElement>('[data-experience-action]')?.dataset.experienceAction;
      if (action === 'compare-tariffs') {
        const dialog = document.querySelector<HTMLDialogElement>('[data-tariff-dialog]');
        if (dialog && !dialog.open) dialog.showModal();
      } else if (action === 'close-tariffs') {
        document.querySelector<HTMLDialogElement>('[data-tariff-dialog]')?.close();
      }
      const wire = target.closest<HTMLButtonElement>('[data-wire-toggle]');
      if (wire) {
        const key = wire.dataset.wireToggle;
        if (key) wireStates[key] = wireStates[key] === false;
        syncCircuit();
      }
    });

    document.addEventListener('keydown', event => {
      const button = event.target as HTMLButtonElement;
      if (!button.matches('[data-wire-toggle]')) return;
      const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('[data-wire-toggle]'));
      const index = buttons.indexOf(button);
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown' || event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        const offset = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : -1;
        buttons[(index + offset + buttons.length) % buttons.length]?.focus();
      }
    });

    document.addEventListener('submit', event => {
      const form = event.target as HTMLFormElement;
      if (form.id !== 'lesson-quiz') return;
      window.setTimeout(decorateLessonCheck, 0);
    }, true);

    return { refresh };
  }
}
