namespace HF {
  export interface CompletionMasteryCheck {
    correct: number;
    total: number;
    passed_at: string;
  }
  export interface CompletionRecord {
    schema: 'helioforge.local-learning.v1';
    passed_self_checks: string[];
    mastery_checks: Record<string, CompletionMasteryCheck>;
  }
  export interface LessonGate {
    unlocked: boolean;
    required: string[];
    missing: string[];
  }

  const completionSchema = 'helioforge.local-learning.v1' as const;
  const lessonLevels: Record<string, number> = {Foundation: 0, Applied: 1, Advanced: 2};
  const tariffHours = 24;

  /** Validate the exact tariff shape consumed by the existing storage-annual study. */
  export function normalizeHourlyTariff(raw: unknown): number[] | null {
    if (!Array.isArray(raw) || raw.length !== tariffHours) return null;
    const values: number[] = [];
    for (const value of raw) {
      if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 3) return null;
      values.push(value);
    }
    return values;
  }

  /** Only hours present as finite observations in both saved runs can be scrubbed together. */
  export function sharedScheduleHours(a: HybridResult | null, b: HybridResult | null): number[] {
    const hours = (run: HybridResult | null): Set<number> => {
      const schedule: unknown = run?.schedule;
      if (!Array.isArray(schedule)) return new Set<number>();
      return new Set(schedule.flatMap(point => point && typeof point === 'object' && typeof point.hour === 'number' && Number.isFinite(point.hour) ? [point.hour] : []));
    };
    const first = hours(a);
    return [...hours(b)].filter(hour => first.has(hour)).sort((x, y) => x - y);
  }

  export function lessonPrerequisiteIds(lesson: Lesson, lessons: Lesson[] = HYBRID_CATALOG.lessons): string[] {
    const level = lessonLevels[lesson.level];
    if (level === undefined || level === 0) return [];
    return lessons.filter(candidate => {
      const candidateLevel = lessonLevels[candidate.level];
      return candidateLevel !== undefined && candidateLevel < level;
    }).map(candidate => candidate.id);
  }

  export function lessonGate(lesson: Lesson, completed: readonly string[], lessons: Lesson[] = HYBRID_CATALOG.lessons): LessonGate {
    const done = new Set(completed);
    const required = lessonPrerequisiteIds(lesson, lessons);
    const missing = required.filter(id => !done.has(id));
    return {unlocked: missing.length === 0, required, missing};
  }

  /** Parse local records defensively; browser-local progress is editable self-report. */
  export function parseCompletionRecord(raw: unknown, lessons: Lesson[] = HYBRID_CATALOG.lessons): CompletionRecord {
    const validIds = new Set(lessons.map(lesson => lesson.id));
    const source = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw as Record<string, unknown> : {};
    const passed = Array.isArray(source.passed_self_checks)
      ? [...new Set(source.passed_self_checks.filter((id): id is string => typeof id === 'string' && validIds.has(id)))]
      : [];
    const checks: Record<string, CompletionMasteryCheck> = {};
    const inputChecks = source.mastery_checks && typeof source.mastery_checks === 'object' && !Array.isArray(source.mastery_checks)
      ? source.mastery_checks as Record<string, unknown> : {};
    for (const [id, value] of Object.entries(inputChecks)) {
      const lesson = lessons.find(candidate => candidate.id === id);
      if (!lesson || !value || typeof value !== 'object' || Array.isArray(value)) continue;
      const check = value as Record<string, unknown>;
      const total = lesson.quiz.length;
      if (check.total !== total || check.correct !== total || typeof check.passed_at !== 'string' || !Number.isFinite(Date.parse(check.passed_at))) continue;
      checks[id] = {correct: total, total, passed_at: check.passed_at};
      if (!passed.includes(id)) passed.push(id);
    }
    return {schema: completionSchema, passed_self_checks: passed, mastery_checks: checks};
  }

  export function lessonProgressNote(progress: readonly string[]): string {
    const passed = new Set(HYBRID_CATALOG.lessons.filter(lesson => progress.includes(lesson.id)).map(lesson => lesson.id));
    return `Passed ${passed.size} of ${HYBRID_CATALOG.lessons.length} local self-checks. Tiers provide suggested study order; completion is not a qualification, credential or verified mastery.`;
  }

  export function syncLessonProgressDisplays(progress: readonly string[]): void {
    const lessons = HYBRID_CATALOG.lessons;
    const passed = new Set(lessons.filter(lesson => progress.includes(lesson.id)).map(lesson => lesson.id));
    const hero = document.querySelector<HTMLElement>('.achievement-orb strong');
    if (hero) hero.innerHTML = `${passed.size}<small> / ${lessons.length}</small>`;
    for (const button of document.querySelectorAll<HTMLElement>('.skill-tree [data-lesson]')) button.classList.toggle('done', passed.has(button.dataset.lesson ?? ''));
    for (const button of document.querySelectorAll<HTMLElement>('.lesson-list [data-lesson]')) {
      const number = button.querySelector<HTMLElement>('.lesson-number');
      if (number) {
        const done = passed.has(button.dataset.lesson ?? '');
        number.classList.toggle('done', done);
        number.textContent = done ? '✓' : String(lessons.findIndex(lesson => lesson.id === button.dataset.lesson) + 1).padStart(2, '0');
      }
    }
    const note = document.querySelector<HTMLElement>('[data-learning-progress-note]');
    if (note) note.textContent = lessonProgressNote(progress);
    const status = document.querySelector<HTMLElement>('[data-hf-completion-status]');
    if (status) {
      const counts = ['Foundation', 'Applied', 'Advanced'].map(level => {
        const tier = lessons.filter(lesson => lesson.level === level);
        return `${level} ${tier.filter(lesson => passed.has(lesson.id)).length}/${tier.length}`;
      });
      status.textContent = `Local self-check progress: ${counts.join(' · ')}. A lesson counts as passed only after every quiz answer is correct.`;
    }
  }

  export function createCompletionController(getState: () => ViewState, notify?: (message: string, error?: boolean) => void): {refresh: () => void; destroy: () => void} {
    let record = parseCompletionRecord(null);
    let sceneCleanups: Array<() => void> = [];
    let sceneKey = '';
    let leftRunId = '';
    let rightRunId = '';
    let selectedHour: number | null = null;
    let pauseLeft = false;
    let pauseRight = false;
    let activeDrag: {svg: SVGSVGElement; pointerId: number; hour: number} | null = null;
    let observer: MutationObserver | undefined;
    let observeRoot: HTMLElement | null = null;
    let updateQueued = false;
    let disposed = false;

    function readStored(): void {
      try {
        const raw = localStorage.getItem('hf-learning-mastery-v1');
        const stored = parseCompletionRecord(raw ? JSON.parse(raw) : null);
        record = parseCompletionRecord({
          passed_self_checks: [...stored.passed_self_checks, ...record.passed_self_checks],
          mastery_checks: {...stored.mastery_checks, ...record.mastery_checks},
        });
      } catch {
        // Navigation must retain checks earned in this session when storage fails.
      }
    }
    function validLessonIds(values: readonly string[]): string[] {
      const valid = new Set(HYBRID_CATALOG.lessons.map(lesson => lesson.id));
      return [...new Set(values.filter(id => valid.has(id)))];
    }
    function hydrateProgress(): void {
      const h = getState().hybrid;
      const ids = [...h.progress, ...record.passed_self_checks];
      try {
        const legacy: unknown = JSON.parse(localStorage.getItem('hf-lessons-v2') ?? '[]');
        if (Array.isArray(legacy)) ids.push(...legacy.filter((id): id is string => typeof id === 'string'));
      } catch { /* Progress can still be used in this session when storage is unavailable. */ }
      h.progress = validLessonIds(ids);
    }
    function persistRecord(): boolean {
      record = parseCompletionRecord({
        schema: completionSchema,
        passed_self_checks: [...getState().hybrid.progress, ...record.passed_self_checks],
        mastery_checks: record.mastery_checks,
      });
      try {
        localStorage.setItem('hf-learning-mastery-v1', JSON.stringify(record));
        localStorage.setItem('hf-lessons-v2', JSON.stringify(record.passed_self_checks));
        return true;
      } catch {
        return false;
      }
    }
    function announce(message: string): void {
      const host = document.getElementById('page-content');
      if (!host) return;
      let status = host.querySelector<HTMLElement>('[data-hf-completion-notice]');
      if (!status) {
        status = document.createElement('p');
        status.className = 'hf-completion-status';
        status.dataset.hfCompletionNotice = 'true';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        host.prepend(status);
      }
      status.textContent = message;
    }
    function gateMessage(lesson: Lesson, gate: LessonGate): string {
      if (gate.unlocked) return '';
      const missingLessons = gate.missing.map(id => HYBRID_CATALOG.lessons.find(candidate => candidate.id === id)?.title ?? id);
      return `${lesson.level} lessons are locked until every lower-tier self-check is passed (${missingLessons.length} remaining).`;
    }
    function decorateLessons(): void {
      const h = getState().hybrid;
      const completed = validLessonIds(h.progress);
      const passed = new Set(completed);
      for (const button of document.querySelectorAll<HTMLButtonElement>('[data-lesson]')) {
        const lesson = HYBRID_CATALOG.lessons.find(candidate => candidate.id === button.dataset.lesson);
        if (!lesson) continue;
        const gate = lessonGate(lesson, completed);
        button.classList.toggle('hf-lesson-gated', !gate.unlocked);
        button.setAttribute('aria-disabled', String(!gate.unlocked));
        const note = gate.unlocked ? `${lesson.level} lesson. ${passed.has(lesson.id) ? 'Self-check passed in this browser.' : 'Self-check not yet passed.'}` : gateMessage(lesson, gate);
        button.title = note;
        if (button.hasAttribute('aria-label')) {
          button.setAttribute('aria-label', `${lesson.title}; ${lesson.level}; ${passed.has(lesson.id) ? 'self-check passed' : 'not passed'}; ${note}`);
        }
      }
      const list = document.querySelector<HTMLElement>('.lesson-list');
      if (list) {
        let path = list.querySelector<HTMLElement>('[data-hf-completion-path]');
        if (!path) {
          path = document.createElement('div');
          path.className = 'hf-completion-path';
          path.dataset.hfCompletionPath = 'true';
          path.setAttribute('aria-label', 'Mastery unlock requirements');
          list.insertBefore(path, list.querySelector('[data-lesson]') ?? null);
        }
        const levels = ['Foundation', 'Applied', 'Advanced'];
        const markup = levels.map(level => {
          const tier = HYBRID_CATALOG.lessons.filter(lesson => lesson.level === level);
          const done = tier.filter(lesson => passed.has(lesson.id)).length;
          const gate = tier.length ? lessonGate(tier[0]!, completed) : {unlocked: false};
          return `<span class="${gate.unlocked ? 'unlocked' : 'locked'}"><strong>${escapeHTML(level)}</strong><small>${done}/${tier.length} passed${gate.unlocked ? ' · open' : ' · locked'}</small></span>`;
        }).join('');
        if (path.dataset.hfMarkup !== markup) {
          path.innerHTML = markup;
          path.dataset.hfMarkup = markup;
        }
      }
      const lesson = HYBRID_CATALOG.lessons.find(candidate => candidate.id === h.lessonId);
      const content = document.querySelector<HTMLElement>('.lesson-content');
      let lock = document.querySelector<HTMLElement>('[data-hf-lesson-lock]');
      if (lesson && content) {
        const gate = lessonGate(lesson, completed);
        if (!gate.unlocked) {
          if (!lock) {
            lock = document.createElement('section');
            lock.className = 'panel hf-lesson-lock';
            lock.dataset.hfLessonLock = 'true';
            lock.setAttribute('role', 'status');
            content.before(lock);
          }
          const next = HYBRID_CATALOG.lessons.find(candidate => lessonGate(candidate, completed).unlocked && !passed.has(candidate.id));
          const markup = `<span class="eyebrow">MASTERY GATE</span><h2>${escapeHTML(lesson.level)} lessons are locked</h2><p>Pass each lower-tier lesson’s full self-check to unlock this activity. This is an in-browser learning gate, not a credential or independent assessment.</p><p><strong>${gate.missing.length} prerequisite checks remain.</strong></p>${next ? `<button type="button" class="btn primary" data-lesson="${escapeHTML(next.id)}">Continue with ${escapeHTML(next.title)}</button>` : ''}`;
          if (lock.dataset.hfMarkup !== markup) {
            lock.innerHTML = markup;
            lock.dataset.hfMarkup = markup;
          }
          content.hidden = true;
        } else {
          lock?.remove();
          content.hidden = false;
        }
      } else {
        lock?.remove();
        if (content) content.hidden = false;
      }
      const footer = document.querySelector<HTMLElement>('.learning-footer');
      if (footer) {
        const caveat = footer.querySelector<HTMLElement>('[data-hf-record-caveat]') ?? document.createElement('p');
        caveat.dataset.hfRecordCaveat = 'true';
        caveat.className = 'hf-record-caveat';
        caveat.textContent = 'This export is a local record of browser self-checks. It does not verify identity, independent mastery, a qualification, accreditation or certification.';
        if (!caveat.isConnected) footer.prepend(caveat);
      }
      const sign = document.querySelector<HTMLButtonElement>('[data-workflow-action="sign-progress"]');
      if (sign && !sign.parentElement?.querySelector('[data-hf-sign-caveat]')) {
        const caveat = document.createElement('p');
        caveat.dataset.hfSignCaveat = 'true';
        caveat.className = 'hf-record-caveat';
        caveat.textContent = 'The browser-generated signature seals the local payload only. It does not establish signer identity, authority, mastery or certification.';
        sign.after(caveat);
      }
      syncLessonProgressDisplays(completed);
    }
    function clearScenes(): void {
      for (const cleanup of sceneCleanups.splice(0)) cleanup();
      sceneKey = '';
    }
    function selectedRuns(): [ComparedRun, ComparedRun] | null {
      const runs = getState().hybrid.compare;
      if (runs.length < 2) return null;
      const left = runs.find(run => run.id === leftRunId) ?? runs[0]!;
      const right = runs.find(run => run.id === rightRunId) ?? runs.find(run => run.id !== left.id) ?? runs[1]!;
      leftRunId = left.id;
      rightRunId = right.id;
      return [left, right];
    }
    function sceneMarkup(runs: [ComparedRun, ComparedRun], hours: number[]): string {
      const state = getState();
      const choices = state.hybrid.compare.map((run, index) => {
        const system = HYBRID_CATALOG.systems.find(item => item.id === run.inputs.system_id);
        return `<option value="${escapeHTML(run.id)}">${String.fromCharCode(65 + index)} · ${escapeHTML(run.name)} · ${escapeHTML(system?.name ?? 'Unknown architecture')}</option>`;
      }).join('');
      const currentHour = hours.includes(selectedHour ?? -1) ? selectedHour! : hours[0] ?? null;
      return `<section class="hf-completion-scenes" data-hf-completion-scenes aria-labelledby="hf-completion-scenes-title"><header class="hf-completion-heading"><div><span class="eyebrow">SAVED RUNS / ACTUAL HOURLY POINTS</span><h2 id="hf-completion-scenes-title">Compare two hybrid architecture scenes</h2><p>Choose two pinned runs. Each viewport uses its saved architecture and hourly telemetry; camera presets are independent and the scrubber uses only hours present in both schedules.</p></div><span class="tag muted">SOFTWARE 3D · CONCEPTUAL CONNECTIONS</span></header><div class="hf-completion-selectors"><label class="field"><span>Run A · architecture</span><select data-hf-run-select="left">${choices}</select></label><label class="field"><span>Run B · architecture</span><select data-hf-run-select="right">${choices}</select></label></div><div class="hf-scene-viewport-grid">${runs.map((run, index) => {
        const slot = index === 0 ? 'left' : 'right';
        const system = HYBRID_CATALOG.systems.find(item => item.id === run.inputs.system_id);
        const label = system?.name ?? 'Unknown architecture';
        const scenario = HYBRID_CATALOG.scenarios.find(item => item.id === run.inputs.scenario_id);
        return `<article class="hf-scene-viewport" data-hf-scene-slot="${slot}"><header><span class="tag muted">RUN ${slot === 'left' ? 'A' : 'B'}</span><h3>${escapeHTML(label)}</h3><p>${escapeHTML(run.name)} · ${escapeHTML(scenario?.name ?? 'Unknown scenario')}</p></header><canvas data-hf-scene-canvas="${slot}" role="img" tabindex="0" aria-label="Conceptual software 3D scene for ${escapeHTML(label)}. Use pointer or arrow keys to inspect; camera presets are below.">Conceptual energy architecture. View the saved run summary above.</canvas><div class="hf-scene-controls"><div class="hf-scene-presets" role="group" aria-label="Run ${slot === 'left' ? 'A' : 'B'} camera presets">${[['isometric','Isometric'],['top-down','Top-down'],['oblique','Oblique'],['wireframe','Wireframe']].map(([preset, name]) => `<button type="button" data-hf-camera="${slot}" data-camera-preset="${preset}" data-preset="${preset}" aria-pressed="${preset === 'isometric'}">${name}</button>`).join('')}</div><label class="hf-scene-pause"><input type="checkbox" data-hf-pause="${slot}" ${state.motionOff || (slot === 'left' ? pauseLeft : pauseRight) ? 'checked' : ''} ${state.motionOff ? 'disabled' : ''}><span>Pause animation</span></label></div><p class="hf-scene-status" data-hf-scene-status="${slot}" role="status" aria-live="polite">Select an asset in the scene to inspect its name.</p></article>`;
      }).join('')}</div><label class="hf-sync-control"><span>Shared saved-run hour</span><input type="range" data-hf-sync-hour min="0" max="${Math.max(0, hours.length - 1)}" step="1" value="${Math.max(0, hours.indexOf(currentHour ?? -1))}" ${hours.length ? '' : 'disabled'}><output data-hf-sync-label>${currentHour === null ? 'No shared hourly points' : `Hour ${currentHour}`}</output></label><p class="hf-scene-evidence" data-hf-scene-evidence role="status" aria-live="polite">${hours.length ? `Scrubbing ${hours.length} common saved hour${hours.length === 1 ? '' : 's'}. Values come from the two selected run schedules.` : 'The selected runs do not contain a common finite hour; no telemetry point is shown.'} Geographic coordinates and voltage measurements are absent from these energy-balance results, so no geographic or voltage contours are drawn.</p></section>`;
    }
    function mountCompareScenes(): void {
      const host = document.querySelector<HTMLElement>('.workflow-panel');
      const state = getState();
      if (state.page !== 'compare' || !host || state.hybrid.compare.length < 2) return;
      let container = host.querySelector<HTMLElement>('[data-hf-completion-host]');
      if (!container) {
        container = document.createElement('div');
        container.dataset.hfCompletionHost = 'true';
        host.append(container);
      }
      const selected = selectedRuns();
      if (!selected) return;
      const [a, b] = selected;
      const hours = sharedScheduleHours(a.result, b.result);
      if (selectedHour !== null && !hours.includes(selectedHour)) selectedHour = null;
      if (selectedHour === null && hours.length) selectedHour = hours[0]!;
      const key = `${state.motionOff}|${pauseLeft}|${pauseRight}|${a.id}|${b.id}|${hours.join(',')}`;
      if (sceneKey === key && container.querySelectorAll('canvas[data-hf-scene-canvas]').length === 2) return;
      clearScenes();
      container.innerHTML = sceneMarkup(selected, hours);
      const runChoices = container.querySelectorAll<HTMLSelectElement>('[data-hf-run-select]');
      runChoices[0]!.value = a.id;
      runChoices[1]!.value = b.id;
      const hourIndex = selectedHour === null ? 0 : hours.indexOf(selectedHour);
      const range = container.querySelector<HTMLInputElement>('[data-hf-sync-hour]');
      if (range) range.value = String(Math.max(0, hourIndex));
      for (const [slot, run, paused] of [['left', a, pauseLeft], ['right', b, pauseRight]] as const) {
        const canvas = container.querySelector<HTMLCanvasElement>(`canvas[data-hf-scene-canvas="${slot}"]`);
        const system = HYBRID_CATALOG.systems.find(item => item.id === run.inputs.system_id);
        if (!canvas || !system) continue;
        const schedule = Array.isArray(run.result.schedule) ? run.result.schedule : [];
        const getPoint = (): HybridPoint | null => selectedHour === null ? null : schedule.find(point => point.hour === selectedHour) ?? null;
        const status = container.querySelector<HTMLElement>(`[data-hf-scene-status="${slot}"]`);
        sceneCleanups.push(mountEnergyScene(canvas, system, state.motionOff || paused, id => {
          if (status) status.textContent = `Selected ${techById(id).name}${getPoint() ? ` at ${getPoint()!.label}` : ''}. Scene links are conceptual; the selected interval values are saved run evidence.`;
        }, getPoint));
      }
      sceneKey = key;
    }
    function updateScenesAtHour(): void {
      const container = document.querySelector<HTMLElement>('[data-hf-completion-scenes]');
      const runs = selectedRuns();
      if (!container || !runs) return;
      const hours = sharedScheduleHours(runs[0].result, runs[1].result);
      const range = container.querySelector<HTMLInputElement>('[data-hf-sync-hour]');
      if (!range || !hours.length) return;
      selectedHour = hours[clamp(Math.round(Number(range.value)), 0, hours.length - 1)] ?? null;
      const pointA = runs[0].result.schedule.find(point => point.hour === selectedHour);
      const pointB = runs[1].result.schedule.find(point => point.hour === selectedHour);
      const label = container.querySelector<HTMLOutputElement>('[data-hf-sync-label]');
      if (label) label.value = selectedHour === null ? 'No shared hourly points' : `Hour ${selectedHour}${pointA?.label ? ` · ${pointA.label}` : ''}`;
      const evidence = container.querySelector<HTMLElement>('[data-hf-scene-evidence]');
      if (evidence && pointA && pointB) evidence.textContent = `Hour ${selectedHour}: Run A ${pointA.label}, ${fmt(pointA.served_kw, 2)} kW served, ${fmt(pointA.soc_end_kwh, 2)} kWh battery energy; Run B ${pointB.label}, ${fmt(pointB.served_kw, 2)} kW served, ${fmt(pointB.soc_end_kwh, 2)} kWh battery energy. These are actual stored schedule points. Geographic coordinates and voltage measurements are absent, so no geographic or voltage contours are drawn.`;
      for (const canvas of container.querySelectorAll<HTMLCanvasElement>('canvas[data-hf-scene-canvas]')) canvas.dispatchEvent(new Event('scene-telemetry'));
    }
    function decorateTariffProfile(): void {
      const form = document.querySelector<HTMLFormElement>('#study-form[data-study-id="storage-annual"]');
      const host = document.getElementById('study-visual');
      if (!form || !host || host.hidden) return;
      const profile = host.querySelector<SVGSVGElement>('.hf-annual-tariff svg');
      if (!profile) return;
      profile.dataset.hfTariffProfile = 'true';
      profile.setAttribute('role', 'group');
      profile.setAttribute('tabindex', '0');
      profile.setAttribute('aria-label', 'Draggable hourly import tariff profile. Use left and right arrows to choose an hour; up and down arrows adjust by 0.01 EUR per kWh; Home sets zero and End sets three.');
      profile.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight ArrowUp ArrowDown Home End');
      profile.setAttribute('aria-describedby', 'hf-tariff-profile-help');
      let controls = host.querySelector<HTMLElement>('[data-hf-tariff-actions]');
      if (!controls) {
        controls = document.createElement('div');
        controls.className = 'hf-tariff-profile-actions';
        controls.dataset.hfTariffActions = 'true';
        controls.innerHTML = `<p id="hf-tariff-profile-help">Drag across the bars to edit the existing 24-value tariff input. With this chart focused, use ←/→ to choose an hour, ↑/↓ to adjust it, Home for 0 and End for 3 EUR/kWh. The hourly sliders remain available below.</p><button type="button" class="btn primary" data-hf-tariff-apply ${getState().connected ? '' : 'disabled'} ${getState().connected ? '' : 'aria-disabled="true"'}>Apply profile &amp; recalculate</button><p data-hf-tariff-live role="status" aria-live="polite">Changes update the study’s actual <code>tariff</code> JSON input. Prior results become stale and are hidden until a connected local API calculation succeeds.</p>`;
        host.append(controls);
      }
      const apply = controls.querySelector<HTMLButtonElement>('[data-hf-tariff-apply]');
      if (apply) {
        apply.disabled = !getState().connected;
        apply.setAttribute('aria-disabled', String(!getState().connected));
        apply.title = getState().connected ? 'Submit the current 24-value tariff input to the local study API.' : 'Start and connect the local Python app before recalculating edited inputs.';
      }
    }
    function tariffAtPointer(svg: SVGSVGElement, event: PointerEvent): {hour: number; value: number} | null {
      const rect = svg.getBoundingClientRect();
      if (!rect.width || !rect.height) return null;
      const x = (event.clientX - rect.left) / rect.width * 640;
      const y = (event.clientY - rect.top) / rect.height * 260;
      const hour = clamp(Math.floor((x - 52) / 23), 0, 23);
      const value = Math.round(clamp((192 - y) / 142 * 3, 0, 3) * 100) / 100;
      return {hour, value};
    }
    function setTariffValue(svg: SVGSVGElement, hour: number, value: number): void {
      const boundedHour = clamp(Math.trunc(hour), 0, 23);
      const boundedValue = Math.round(clamp(value, 0, 3) * 100) / 100;
      const json = document.querySelector<HTMLTextAreaElement>('#study-form textarea[name="tariff"]')?.value;
      let currentTariff: unknown;
      try { currentTariff = json ? JSON.parse(json) : null; } catch { currentTariff = null; }
      if (!normalizeHourlyTariff(currentTariff)) return;
      const slider = document.querySelector<HTMLInputElement>(`#study-workbench [data-tariff-hour="${boundedHour}"]`);
      if (!slider) return;
      selectTariffHour(svg, boundedHour);
      if (Number(slider.value) === boundedValue) return;
      slider.value = String(boundedValue);
      slider.dispatchEvent(new Event('input', {bubbles: true}));
      const live = document.querySelector<HTMLElement>('[data-hf-tariff-live]');
      if (live) live.textContent = `Hour ${String(boundedHour).padStart(2, '0')}: ${boundedValue.toFixed(2)} EUR/kWh. The study input is changed; previous results remain stale until recalculation succeeds.`;
      svg.setAttribute('aria-label', `Hourly import tariff profile. Selected hour ${boundedHour}, ${boundedValue.toFixed(2)} EUR per kWh. Use left and right arrows to choose an hour; up and down arrows adjust it.`);
    }
    function selectTariffHour(svg: SVGSVGElement, hour: number): void {
      const boundedHour = clamp(Math.trunc(hour), 0, 23);
      const bar = svg.querySelector<SVGRectElement>(`[data-tariff-bar="${boundedHour}"]`);
      svg.querySelectorAll<SVGRectElement>('[data-tariff-bar]').forEach(item => item.removeAttribute('data-hf-active'));
      bar?.setAttribute('data-hf-active', 'true');
      const value = Number(document.querySelector<HTMLInputElement>(`#study-workbench [data-tariff-hour="${boundedHour}"]`)?.value ?? 0);
      svg.setAttribute('aria-label', `Hourly import tariff profile. Selected hour ${boundedHour}, ${fmt(value, 2)} EUR per kWh. Use left and right arrows to choose an hour; up and down arrows adjust it.`);
      const live = document.querySelector<HTMLElement>('[data-hf-tariff-live]');
      if (live) live.textContent = `Hour ${String(boundedHour).padStart(2, '0')} selected · ${fmt(value, 2)} EUR/kWh. Use the hourly sliders or arrow keys to adjust the tariff.`;
    }
    function decorateLearningStatus(): void {
      const host = document.getElementById('page-content');
      if (!host) return;
      let status = host.querySelector<HTMLElement>('[data-hf-completion-status]');
      if (!status && getState().page === 'lessons') {
        status = document.createElement('p');
        status.className = 'hf-completion-status';
        status.dataset.hfCompletionStatus = 'true';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        host.prepend(status);
      }
      syncLessonProgressDisplays(getState().hybrid.progress);
    }
    function decorateWorkflow(): void {
      const sign = document.querySelector<HTMLButtonElement>('[data-workflow-action="sign-progress"]');
      if (sign && !sign.parentElement?.querySelector('[data-hf-sign-caveat]')) {
        const note = document.createElement('p');
        note.dataset.hfSignCaveat = 'true';
        note.className = 'hf-record-caveat';
        note.textContent = 'This seals a local self-check payload with an ephemeral browser key. It does not verify identity, authority, independent mastery or certification.';
        sign.after(note);
      }
    }
    function syncDecorations(): void {
      if (disposed) return;
      // Own DOM writes must not recursively trigger the observer and starve input.
      observer?.disconnect();
      try {
        decorateLessons();
        decorateLearningStatus();
        decorateWorkflow();
        decorateTariffProfile();
        mountCompareScenes();
      } finally {
        if (observeRoot && !disposed) observer?.observe(observeRoot, {childList:true, subtree:true});
      }
    }
    function scheduleDecorations(): void {
      if (updateQueued || disposed) return;
      updateQueued = true;
      queueMicrotask(() => { updateQueued = false; syncDecorations(); });
    }
    function bindObserver(): void {
      const next = document.getElementById('page-content');
      if (!next || next === observeRoot) return;
      observer?.disconnect();
      observeRoot = next;
      observer = new MutationObserver(scheduleDecorations);
      observer.observe(next, {childList: true, subtree: true});
    }
    function onClick(event: Event): void {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const button = target.closest<HTMLButtonElement>('button');
      if (!button) return;
      const action = button.dataset.hybridAction;
      if (action === 'export-progress') {
        event.preventDefault();
        event.stopImmediatePropagation();
        const h = getState().hybrid;
        const all = parseCompletionRecord({schema: completionSchema, passed_self_checks: h.progress, mastery_checks: record.mastery_checks});
        download('helioforge-learning-progress.json', JSON.stringify({
          schema: completionSchema,
          exported_at: new Date().toISOString(),
          data_kind: 'browser_local_self_reported',
          passed_self_checks: all.passed_self_checks,
          mastery_checks: all.mastery_checks,
          notice: 'Local browser self-check progress. The record does not verify identity, independent mastery, qualification, accreditation, certification or engineering competence.',
          identity_verification: 'none',
        }, null, 2));
        announce('Exported local self-check IDs and exact quiz scores. The file does not verify identity or certification.');
        return;
      }
      if (action === 'confirm-reset-progress') {
        event.preventDefault();
        event.stopImmediatePropagation();
        const keys = ['hf-learning-mastery-v1', 'hf-lessons-v2'];
        let removed = true;
        for (const key of keys) {
          try { localStorage.removeItem(key); } catch { removed = false; }
        }
        for (const key of keys) {
          try { if (localStorage.getItem(key) !== null) removed = false; } catch { removed = false; }
        }
        if (!removed) {
          const message = 'Browser storage did not confirm removal. Your current progress is retained. Retry the reset or clear this site’s data in your browser settings.';
          const status = document.getElementById('learning-reset-status');
          if (status) status.textContent = message;
          announce(message);
          notify?.(message, true);
          return;
        }
        record = parseCompletionRecord(null);
        const h = getState().hybrid;
        h.progress = [];
        h.quizResult = null;
        const feedback = document.getElementById('quiz-feedback');
        if (feedback) feedback.innerHTML = '';
        const dialog = document.querySelector<HTMLDialogElement>('dialog[open]');
        dialog?.close();
        syncDecorations();
        announce('Browser learning progress reset.');
        notify?.('Browser learning progress reset.');
        return;
      }
      const lessonId = button.dataset.lesson;
      if (lessonId) {
        const lesson = HYBRID_CATALOG.lessons.find(candidate => candidate.id === lessonId);
        if (lesson) {
          const gate = lessonGate(lesson, getState().hybrid.progress);
          if (!gate.unlocked) {
            event.preventDefault();
            event.stopImmediatePropagation();
            announce(gateMessage(lesson, gate));
            return;
          }
        }
      }
      if (button.hasAttribute('data-hf-tariff-apply')) {
        event.preventDefault();
        const form = document.querySelector<HTMLFormElement>('#study-form[data-study-id="storage-annual"]');
        if (!getState().connected || !form) {
          const live = document.querySelector<HTMLElement>('[data-hf-tariff-live]');
          if (live) live.textContent = 'The tariff is in the study input, but edited values cannot be recalculated in disconnected preview mode. Start the local Python app and reconnect.';
          return;
        }
        form.requestSubmit();
        return;
      }
      if (button.dataset.hfCamera) {
        const canvas = document.querySelector<HTMLCanvasElement>(`canvas[data-hf-scene-canvas="${button.dataset.hfCamera}"]`);
        if (canvas && button.dataset.preset) canvas.dispatchEvent(new CustomEvent('scene-command', {detail: button.dataset.preset}));
        return;
      }
      if (button.dataset.hfRunSelect) return;
      if (button.dataset.studySelect) queueMicrotask(scheduleDecorations);
    }
    function onSubmit(event: Event): void {
      const form = event.target;
      if (!(form instanceof HTMLFormElement) || form.id !== 'lesson-quiz') return;
      const lesson = HYBRID_CATALOG.lessons.find(candidate => candidate.id === getState().hybrid.lessonId);
      if (!lesson || !lessonGate(lesson, getState().hybrid.progress).unlocked) {
        event.preventDefault();
        event.stopImmediatePropagation();
        announce('This lesson remains locked until all lower-tier mastery checks are passed.');
        return;
      }
      const data=new FormData(form);
      const answers=lesson.quiz.map((_,i)=>{const value=data.get(`q${i}`);return value===null?-1:Number(value);});
      const result=gradeLesson(lesson,answers);
      if(result.passed&&result.correct===lesson.quiz.length&&result.total===lesson.quiz.length){
        record.mastery_checks[lesson.id] ??= {correct:result.correct,total:result.total,passed_at:new Date().toISOString()};
        const saved=persistRecord();
        queueMicrotask(()=>{syncDecorations();if(!saved)announce('Self-check passed for this session, but browser storage is unavailable. Export the progress record before leaving.');});
      }
    }
    function onChange(event: Event): void {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement || target instanceof HTMLInputElement)) return;
      if (target.dataset.hfRunSelect) {
        if (target.dataset.hfRunSelect === 'left') leftRunId = target.value;
        else rightRunId = target.value;
        clearScenes();
        mountCompareScenes();
      } else if (target instanceof HTMLInputElement && target.dataset.hfPause) {
        if (target.dataset.hfPause === 'left') pauseLeft = target.checked;
        else pauseRight = target.checked;
        clearScenes();
        mountCompareScenes();
      }
    }
    function onInput(event: Event): void {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) return;
      if (target.hasAttribute('data-hf-sync-hour')) updateScenesAtHour();
    }
    function onPointerDown(event: Event): void {
      const pointer = event as PointerEvent;
      const target = pointer.target;
      if (!(target instanceof Element)) return;
      const svg = target.closest<SVGSVGElement>('[data-hf-tariff-profile]');
      if (!svg || pointer.button !== 0) return;
      const mapped = tariffAtPointer(svg, pointer);
      if (!mapped) return;
      event.preventDefault();
      activeDrag = {svg, pointerId: pointer.pointerId, hour: mapped.hour};
      try { svg.setPointerCapture(pointer.pointerId); } catch { /* Pointer capture is optional on SVG implementations. */ }
      svg.focus({preventScroll: true});
      setTariffValue(svg, mapped.hour, mapped.value);
    }
    function onPointerMove(event: Event): void {
      const pointer = event as PointerEvent;
      if (!activeDrag || activeDrag.pointerId !== pointer.pointerId) return;
      const mapped = tariffAtPointer(activeDrag.svg, pointer);
      if (!mapped) return;
      activeDrag.hour = mapped.hour;
      setTariffValue(activeDrag.svg, mapped.hour, mapped.value);
    }
    function onPointerEnd(event: Event): void {
      const pointer = event as PointerEvent;
      if (!activeDrag || activeDrag.pointerId !== pointer.pointerId) return;
      try { activeDrag.svg.releasePointerCapture(pointer.pointerId); } catch { /* Pointer capture may already be released. */ }
      activeDrag = null;
    }
    function onKeyDown(event: Event): void {
      const keyEvent = event as KeyboardEvent;
      const target = keyEvent.target;
      if (!(target instanceof Element)) return;
      const svg = target.closest<SVGSVGElement>('[data-hf-tariff-profile]');
      if (!svg) return;
      const bars = [...svg.querySelectorAll<SVGRectElement>('[data-tariff-bar]')];
      if (!bars.length) return;
      const active = bars.findIndex(bar => bar.hasAttribute('data-hf-active'));
      let hour = active < 0 ? 0 : active;
      const slider = (index: number): HTMLInputElement | null => document.querySelector<HTMLInputElement>(`#study-workbench [data-tariff-hour="${index}"]`);
      if (keyEvent.key === 'ArrowLeft' || keyEvent.key === 'ArrowRight') {
        hour = clamp(hour + (keyEvent.key === 'ArrowRight' ? 1 : -1), 0, 23);
        selectTariffHour(svg, hour);
      } else if (keyEvent.key === 'ArrowUp' || keyEvent.key === 'ArrowDown' || keyEvent.key === 'Home' || keyEvent.key === 'End') {
        const current = Number(slider(hour)?.value ?? 0);
        const step = keyEvent.shiftKey ? .1 : .01;
        const value = keyEvent.key === 'Home' ? 0 : keyEvent.key === 'End' ? 3 : current + (keyEvent.key === 'ArrowUp' ? step : -step);
        setTariffValue(svg, hour, value);
      } else return;
      keyEvent.preventDefault();
    }
    function refresh(): void {
      if (disposed) return;
      clearScenes();
      readStored();
      hydrateProgress();
      bindObserver();
      syncDecorations();
    }
    function destroy(): void {
      disposed = true;
      clearScenes();
      observer?.disconnect();
      observer = undefined;
      observeRoot = null;
      activeDrag = null;
      document.removeEventListener('click', onClick, true);
      document.removeEventListener('submit', onSubmit, true);
      document.removeEventListener('change', onChange);
      document.removeEventListener('input', onInput);
      document.removeEventListener('pointerdown', onPointerDown, true);
      document.removeEventListener('pointermove', onPointerMove, true);
      document.removeEventListener('pointerup', onPointerEnd, true);
      document.removeEventListener('pointercancel', onPointerEnd, true);
      document.removeEventListener('keydown', onKeyDown, true);
    }
    readStored();
    document.addEventListener('click', onClick, true);
    document.addEventListener('submit', onSubmit, true);
    document.addEventListener('change', onChange);
    document.addEventListener('input', onInput);
    document.addEventListener('pointerdown', onPointerDown, true);
    document.addEventListener('pointermove', onPointerMove, true);
    document.addEventListener('pointerup', onPointerEnd, true);
    document.addEventListener('pointercancel', onPointerEnd, true);
    document.addEventListener('keydown', onKeyDown, true);
    return {refresh, destroy};
  }
}
