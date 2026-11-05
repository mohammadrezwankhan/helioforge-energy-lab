namespace HF { // eslint-disable-line @typescript-eslint/no-namespace, @typescript-eslint/no-unused-vars -- HF is the ordered global-script bundle namespace; modules change its shared runtime contract.
  type Vec3 = [number, number, number];
  interface Face {
    points: Vec3[];
    fill: string;
    stroke?: string;
    depth?: number;
    wireframe?: boolean;
  }
  interface SceneAsset {
    id: string;
    x: number;
    z: number;
    label: string;
  }
  export function sceneAssetPower(point: HybridPoint | null, id: string): number | null {
    if (!point) return null;
    const powers: Record<string, number> = {
      solar: point.pv_kw,
      wind: point.wind_kw,
      hydro: point.hydro_kw,
      generator: point.generator_kw,
      battery: point.discharge_kw - point.charge_kw,
      grid: point.grid_import_kw - point.grid_export_kw,
      load: -point.served_kw,
    };
    return Object.hasOwn(powers, id) && Number.isFinite(powers[id])
      ? HF.requiredPresent(powers[id], 'powers[id]')
      : null;
  }
  export type ScenePreset = 'isometric' | 'top-down' | 'oblique' | 'wireframe';
  export interface ScenePresetState {
    preset: ScenePreset;
    yaw: number;
    pitch: number;
    zoom: number;
    wireframe: boolean;
  }
  /** Camera presets for the orthographic canvas renderer. Top-down uses a 90° pitch. */
  export function scenePresetState(name: string): ScenePresetState | null {
    switch (name) {
      case 'isometric':
        return {
          preset: name,
          yaw: -Math.PI / 4,
          pitch: (35 * Math.PI) / 180,
          zoom: 1,
          wireframe: false,
        };
      case 'top-down':
        return { preset: name, yaw: 0, pitch: Math.PI / 2, zoom: 1, wireframe: false };
      case 'oblique':
        return {
          preset: name,
          yaw: -Math.PI / 6,
          pitch: (22 * Math.PI) / 180,
          zoom: 1,
          wireframe: false,
        };
      case 'wireframe':
        return {
          preset: name,
          yaw: -Math.PI / 4,
          pitch: (35 * Math.PI) / 180,
          zoom: 1,
          wireframe: true,
        };
      default:
        return null;
    }
  }
  /** Small original orthographic software-3D renderer. Real 3D vertices and
   * camera transforms, rendered to Canvas2D; no WebGL/CDN/runtime package.
   * Energy links are conceptual, not solved branch power flows. */
  export function mountEnergyScene(
    canvas: HTMLCanvasElement,
    system: HybridSystem,
    reduced: boolean,
    onSelect: (id: string) => void,
    getPoint: () => HybridPoint | null = () => null,
  ): () => void {
    const ctx = canvas.getContext('2d');
    if (!ctx) return () => {};
    const initial = HF.requiredPresent(scenePresetState('isometric'), "scenePresetState('isometric')");
    let yaw = initial.yaw,
      pitch = initial.pitch,
      zoom = initial.zoom,
      wireframe = initial.wireframe,
      activePreset: ScenePreset | null = initial.preset;
    let frame = 0,
      disposed = false,
      visible = false,
      drag = false,
      moved = false,
      lastX = 0,
      lastY = 0,
      lastTime = 0;
    let width = 0,
      height = 0,
      phase = 0,
      dirty = true;
    const pos: Vec3[] = [
      [-1.7, 0, 1.0],
      [-1.9, 0, -1.15],
      [0.45, 0, 1.25],
      [0.5, 0, -1.15],
      [2.3, 0, 0.8],
      [2.2, 0, -1.35],
      [-0.45, 0, 0.1],
    ];
    const ids = [
      ...system.technologies,
      'load',
      ...(system.topology === 'Off-grid' ? [] : ['grid']),
    ];
    const assets: SceneAsset[] = ids.map((id, i) => ({
      id,
      x: HF.requiredPresent(pos[i % pos.length], 'pos[i%pos.length]')[0],
      z: HF.requiredPresent(pos[i % pos.length], 'pos[i%pos.length]')[2],
      label: techById(id).name,
    }));
    let hit: { id: string; x: number; y: number }[] = [];
    const projection = (v: Vec3): [number, number, number] => {
      const rx = v[0] * Math.cos(yaw) + v[2] * Math.sin(yaw),
        rz = -v[0] * Math.sin(yaw) + v[2] * Math.cos(yaw);
      const scale = Math.min(width / 7.8, height / 6.0) * zoom;
      return [
        width * 0.5 + rx * scale,
        height * 0.62 + (-v[1] * Math.cos(pitch) + rz * Math.sin(pitch)) * scale,
        v[1] * Math.sin(pitch) + rz * Math.cos(pitch),
      ];
    };
    function draw(): void {
      if (disposed || !visible || !width || !height) {
        dirty = true;
        return;
      }
      if (!ctx || width === 0) return;
      const theme = getComputedStyle(canvas);
      const resolveThemeColor = (value: string): string => {
        const match = /^var\((--[a-z0-9-]+)\)$/.exec(value);
        return match ? theme.getPropertyValue(HF.requiredPresent(match[1], 'match[1]')).trim() : value;
      };
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = resolveThemeColor('var(--color-paper-2)');
      ctx.fillRect(0, 0, width, height);
      const faces: Face[] = [];
      const telemetry = getPoint();
      const maxPower = Math.max(
        1,
        ...assets.map((a) => Math.abs(sceneAssetPower(telemetry, a.id) ?? 0)),
      );
      const face = (points: Vec3[], fill: string, stroke?: string, wireframeEdge = true): void => {
        faces.push({
          points,
          fill,
          ...(stroke === undefined ? {} : { stroke }),
          wireframe: wireframeEdge,
        });
      };
      function cube(
        x: number,
        y: number,
        z: number,
        w: number,
        h: number,
        d: number,
        colors: [string, string, string],
      ): void {
        const a: Vec3 = [x - w / 2, y, z - d / 2],
          b: Vec3 = [x + w / 2, y, z - d / 2],
          c: Vec3 = [x + w / 2, y, z + d / 2],
          e: Vec3 = [x - w / 2, y, z + d / 2];
        const up = (v: Vec3): Vec3 => [v[0], v[1] + h, v[2]];
        face([a, b, up(b), up(a)], colors[2]);
        face([b, c, up(c), up(b)], colors[1]);
        face([c, e, up(e), up(c)], colors[2]);
        face([e, a, up(a), up(e)], colors[1]);
        face([up(a), up(b), up(c), up(e)], colors[0]);
      }
      function cylinder(x: number, z: number, h: number, color: string): void {
        const ring: Vec3[] = [];
        for (let i = 0; i < 12; i++) {
          const a = (i * Math.PI) / 6,
            b = ((i + 1) * Math.PI) / 6;
          const p: Vec3 = [x + 0.26 * Math.cos(a), 0.2, z + 0.26 * Math.sin(a)],
            q: Vec3 = [x + 0.26 * Math.cos(b), 0.2, z + 0.26 * Math.sin(b)];
          face(
            [p, q, [q[0], h, q[2]], [p[0], h, p[2]]],
            i % 3 === 0 ? 'var(--color-muted)' : color,
          );
          ring.push([p[0], h, p[2]]);
        }
        face(ring, 'var(--color-accent)');
      }
      // Raised base and ground-plane grid.
      cube(0, -0.15, 0, 6.25, 0.15, 4.45, [
        'var(--color-rule)',
        'var(--color-paper-2)',
        'var(--color-paper-2)',
      ]);
      for (let x = -3; x <= 3; x += 0.5)
        face(
          [
            [x, 0.005, -2.1],
            [x + 0.008, 0.005, -2.1],
            [x + 0.008, 0.005, 2.1],
            [x, 0.005, 2.1],
          ],
          'var(--color-rule)',
          undefined,
          false,
        );
      for (let z = -2; z <= 2; z += 0.5)
        face(
          [
            [-3, 0.005, z],
            [3, 0.005, z],
            [3, 0.005, z + 0.008],
            [-3, 0.005, z + 0.008],
          ],
          'var(--color-rule)',
          undefined,
          false,
        );
      for (const a of assets) {
        const { id, x, z } = a,
          tech = techById(id);
        cube(x, 0.02, z, 1.26, 0.09, 1.02, [
          'var(--color-rule)',
          'var(--color-rule)',
          'var(--color-rule)',
        ]);
        if (id === 'solar' || id === 'csp') {
          for (let row = 0; row < 2; row++)
            for (let col = 0; col < 3; col++) {
              const px = x - 0.49 + col * 0.34,
                pz = z - 0.38 + row * 0.43;
              cube(px + 0.14, 0.12, pz + 0.17, 0.025, 0.22, 0.025, [
                'var(--color-ink)',
                'var(--color-muted)',
                'var(--color-rule-2)',
              ]);
              face(
                [
                  [px, 0.4, pz],
                  [px + 0.3, 0.4, pz],
                  [px + 0.3, 0.23, pz + 0.35],
                  [px, 0.23, pz + 0.35],
                ],
                'var(--color-rule-2)',
                'var(--color-accent)',
              );
              face(
                [
                  [px + 0.145, 0.4, pz],
                  [px + 0.151, 0.4, pz],
                  [px + 0.151, 0.23, pz + 0.35],
                  [px + 0.145, 0.23, pz + 0.35],
                ],
                'var(--color-accent)',
              );
            }
        } else if (id === 'wind') {
          cube(x, 0.1, z, 0.075, 1.9, 0.075, [
            'var(--color-ink)',
            'var(--color-ink-2)',
            'var(--color-muted)',
          ]);
          cube(x, 1.96, z, 0.24, 0.18, 0.19, [
            'var(--color-ink)',
            'var(--color-ink-2)',
            'var(--color-ink-2)',
          ]);
          for (let j = 0; j < 3; j++) {
            const ang =
              phase * (telemetry ? clamp(telemetry.wind_kw / maxPower, 0, 1) : 1) +
              (j * Math.PI * 2) / 3;
            const vx = Math.cos(ang),
              vy = Math.sin(ang);
            face(
              [
                [x - vy * 0.05, 2 + vx * 0.05, z + 0.15],
                [x + vx * 0.94 - vy * 0.028, 2 + vy * 0.94 + vx * 0.028, z + 0.15],
                [x + vx * 0.55 + vy * 0.07, 2 + vy * 0.55 - vx * 0.07, z + 0.15],
              ],
              'var(--color-ink)',
              'var(--color-accent)',
            );
          }
        } else if (id === 'battery') {
          cube(x, 0.12, z, 1.06, 0.58, 0.65, [
            'var(--color-accent)',
            'var(--color-muted)',
            'var(--color-accent)',
          ]);
          for (let k = 0; k < 8; k++)
            cube(x - 0.45 + k * 0.125, 0.16, z + 0.332, 0.025, 0.49, 0.016, [
              'var(--color-accent)',
              'var(--color-rule-2)',
              'var(--color-muted)',
            ]);
          cube(x - 0.52, 0.18, z, 0.013, 0.36, 0.38, [
            'var(--color-paper-2)',
            'var(--color-rule)',
            'var(--color-rule)',
          ]);
          cube(x - 0.529, 0.36, z - 0.08, 0.02, 0.09, 0.12, [
            'var(--color-accent)',
            'var(--color-accent)',
            'var(--color-accent)',
          ]);
        } else if (['hydrogen', 'electrolyzer', 'fuelcell'].includes(id)) {
          cylinder(x - 0.3, z, 0.92, 'var(--color-accent)');
          cylinder(x + 0.3, z, 0.92, 'var(--color-accent)');
          cube(x, 0.11, z + 0.32, 0.92, 0.15, 0.17, [
            'var(--color-accent)',
            'var(--color-rule-2)',
            'var(--color-muted)',
          ]);
        } else if (id === 'load') {
          cube(x, 0.12, z, 0.82, 1.05, 0.68, [
            'var(--color-muted)',
            'var(--color-rule)',
            'var(--color-rule-2)',
          ]);
          cube(x, 0.12, z + 0.32, 1.0, 0.22, 0.2, [
            'var(--color-muted)',
            'var(--color-rule-2)',
            'var(--color-rule-2)',
          ]);
          for (let k = 0; k < 3; k++)
            for (let j = 0; j < 3; j++)
              cube(x - 0.28 + k * 0.25, 0.38 + j * 0.24, z + 0.35, 0.12, 0.12, 0.018, [
                'var(--color-accent)',
                'var(--color-accent)',
                'var(--color-accent)',
              ]);
          cube(x, 1.18, z, 0.38, 0.09, 0.3, [
            'var(--color-ink)',
            'var(--color-muted)',
            'var(--color-muted)',
          ]);
        } else if (id === 'grid' || id === 'network') {
          cube(x - 0.15, 0.1, z, 0.035, 1.25, 0.035, [
            'var(--color-ink)',
            'var(--color-ink-2)',
            'var(--color-muted)',
          ]);
          cube(x + 0.15, 0.1, z, 0.035, 1.25, 0.035, [
            'var(--color-ink)',
            'var(--color-ink-2)',
            'var(--color-muted)',
          ]);
          cube(x, 1.1, z, 0.7, 0.055, 0.055, [
            'var(--color-ink)',
            'var(--color-ink-2)',
            'var(--color-muted)',
          ]);
          cube(x, 0.77, z, 0.53, 0.04, 0.04, [
            'var(--color-ink)',
            'var(--color-ink-2)',
            'var(--color-muted)',
          ]);
          cube(x, 0.12, z, 0.6, 0.4, 0.48, [
            'var(--color-ink-2)',
            'var(--color-muted)',
            'var(--color-muted)',
          ]);
        } else if (['hydro', 'pumpedhydro', 'tidal', 'wave'].includes(id)) {
          cube(x, 0.12, z, 0.99, 0.16, 0.75, [
            'var(--color-muted)',
            'var(--color-rule-2)',
            'var(--color-muted)',
          ]);
          for (let j = 0; j < 3; j++)
            cube(x - 0.33 + j * 0.33, 0.29, z, 0.09, 0.42, 0.56, [
              'var(--color-ink-2)',
              'var(--color-muted)',
              'var(--color-muted)',
            ]);
        } else {
          cube(x, 0.12, z, 0.92, 0.6, 0.68, [
            tech.color,
            'var(--color-rule-2)',
            'var(--color-muted)',
          ]);
          for (let j = 0; j < 3; j++)
            cube(x - 0.29 + j * 0.3, 0.74, z, 0.11, 0.25, 0.12, [
              'var(--color-ink)',
              'var(--color-muted)',
              'var(--color-muted)',
            ]);
        }
      }
      faces.forEach(
        (f) => (f.depth = f.points.reduce((s, v) => s + projection(v)[2], 0) / f.points.length),
      );
      faces.sort((a, b) => (a.depth ?? 0) - (b.depth ?? 0));
      for (const f of faces) {
        ctx.beginPath();
        f.points.forEach((v, i) => {
          const [x, y] = projection(v);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.closePath();
        ctx.fillStyle = resolveThemeColor(f.fill);
        ctx.fill();
        if (f.stroke || (wireframe && f.wireframe !== false)) {
          ctx.strokeStyle = resolveThemeColor(
            wireframe && f.wireframe !== false
              ? 'var(--color-accent)'
              : HF.requiredPresent(f.stroke, 'f.stroke'),
          );
          ctx.lineWidth = wireframe ? 1 : 0.7;
          ctx.stroke();
        }
      }
      // Schematic connector route overlays; these remain conceptual, not solved power flows.
      const hub = projection([0.05, 0.11, 0.05]);
      for (const a of assets) {
        const b = projection([a.x, 0.11, a.z]),
          color = techById(a.id).color;
        ctx.save();
        ctx.strokeStyle = resolveThemeColor(color);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(b[0], b[1]);
        ctx.lineTo(hub[0], hub[1]);
        ctx.stroke();
        ctx.strokeStyle = resolveThemeColor(color);
        ctx.lineWidth = 0.9;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(b[0], b[1]);
        ctx.lineTo(hub[0], hub[1]);
        ctx.stroke();
        ctx.setLineDash([]);
        const power = sceneAssetPower(telemetry, a.id),
          ratio = power === null ? 0.5 : Math.abs(power) / maxPower;
        const count = power === null ? 3 : Math.abs(power) < 0.01 ? 0 : Math.ceil(ratio * 6);
        if (!reduced)
          for (let i = 0; i < count; i++) {
            const progress = (phase * (0.12 + ratio * 0.5) + i / count) % 1,
              k = power !== null && power < 0 ? 1 - progress : progress,
              x = b[0] + (hub[0] - b[0]) * k,
              y = b[1] + (hub[1] - b[1]) * k;
            ctx.fillStyle = resolveThemeColor(color);
            ctx.beginPath();
            ctx.arc(x, y, 2, 0, Math.PI * 2);
            ctx.fill();
          }
        ctx.restore();
      }
      hit = [];
      ctx.font = '500 12px ' + theme.fontFamily;
      ctx.textAlign = 'center';
      for (const a of [...assets].sort(
        (a, b) => projection([a.x, 0, a.z])[2] - projection([b.x, 0, b.z])[2],
      )) {
        const power = sceneAssetPower(telemetry, a.id),
          label =
            a.label +
            (power === null ? '' : ` · ${fmt(power, 0)} kW`) +
            (a.id === 'battery' && telemetry ? ` · ${fmt(telemetry.soc_pct, 0)}%` : ''),
          p = projection([a.x, 0.08, a.z + 0.75]),
          w = ctx.measureText(label).width + 19;
        ctx.fillStyle = resolveThemeColor('var(--color-paper-2)');
        ctx.beginPath();
        ctx.roundRect(p[0] - w / 2, p[1] - 9, w, 24, 0);
        ctx.fill();
        ctx.fillStyle = resolveThemeColor(techById(a.id).color);
        ctx.fillText(label, p[0], p[1] + 5);
        hit.push({ id: a.id, x: p[0], y: p[1] - 20 });
      }
    }
    // Observer dimensions are available after layout; a synchronous bounds read
    // here would force the entire newly rendered page to lay out during boot.
    const resize = (rect: DOMRectReadOnly): void => {
      if (disposed) return;
      width = rect.width;
      height = rect.height;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dirty = true;
      draw();
    };
    const observer = new ResizeObserver((entries) => {
      const entry = entries.find((item) => item.target === canvas);
      if (entry) resize(entry.contentRect);
    });
    observer.observe(canvas);
    const intersection = new IntersectionObserver((e) => {
      if (disposed) return;
      visible = e[0]?.isIntersecting ?? false;
      dirty = true;
      draw();
      syncAnimation();
    });
    intersection.observe(canvas);
    const down = (e: PointerEvent): void => {
      drag = true;
      moved = false;
      lastX = e.clientX;
      lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    };
    const syncPresetButtons = (preset: ScenePreset | null): void => {
      canvas.parentElement
        ?.querySelectorAll<HTMLButtonElement>('[data-camera-preset]')
        .forEach((button) => {
          button.setAttribute('aria-pressed', String(button.dataset.cameraPreset === preset));
        });
    };
    const applyPreset = (preset: ScenePreset): void => {
      const state = HF.requiredPresent(scenePresetState(preset), 'scenePresetState(preset)');
      yaw = state.yaw;
      pitch = state.pitch;
      zoom = state.zoom;
      wireframe = state.wireframe;
      activePreset = preset;
      syncPresetButtons(activePreset);
      dirty = true;
      draw();
    };
    const markCustom = (): void => {
      if (activePreset !== null) {
        activePreset = null;
        syncPresetButtons(null);
      }
    };
    const move = (e: PointerEvent): void => {
      if (!drag) return;
      const dx = e.clientX - lastX,
        dy = e.clientY - lastY;
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      yaw += dx * 0.006;
      pitch = clamp(pitch + dy * 0.002, 0.25, Math.PI / 2);
      lastX = e.clientX;
      lastY = e.clientY;
      markCustom();
      dirty = true;
      draw();
    };
    const up = (e: PointerEvent): void => {
      drag = false;
      if (!moved) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left,
          y = e.clientY - rect.top;
        const nearest = [...hit].sort(
          (a, b) => Math.hypot(a.x - x, a.y - y) - Math.hypot(b.x - x, b.y - y),
        )[0];
        if (nearest && Math.hypot(nearest.x - x, nearest.y - y) < 70) onSelect(nearest.id);
      }
    };
    const key = (e: KeyboardEvent): void => {
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '-', 'Home'].includes(e.key)) {
        e.preventDefault();
        if (e.key === 'Home') {
          applyPreset('isometric');
          return;
        }
        if (e.key === 'ArrowLeft') yaw -= 0.15;
        if (e.key === 'ArrowRight') yaw += 0.15;
        if (e.key === 'ArrowUp') pitch = clamp(pitch + 0.1, 0.25, Math.PI / 2);
        if (e.key === 'ArrowDown') pitch = clamp(pitch - 0.1, 0.25, Math.PI / 2);
        if (e.key === '+') zoom = clamp(zoom + 0.1, 0.7, 1.4);
        if (e.key === '-') zoom = clamp(zoom - 0.1, 0.7, 1.4);
        markCustom();
        dirty = true;
        draw();
      }
    };
    const command = (e: Event): void => {
      const cmd = (e as CustomEvent<string>).detail;
      if (cmd === 'isometric' || cmd === 'top-down' || cmd === 'oblique' || cmd === 'wireframe') {
        applyPreset(cmd);
        return;
      }
      key(new KeyboardEvent('keydown', { key: cmd }));
    };
    canvas.addEventListener('pointerdown', down);
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', up);
    canvas.addEventListener('pointercancel', up);
    canvas.addEventListener('keydown', key);
    canvas.addEventListener('scene-command', command);
    syncPresetButtons(activePreset);
    const telemetryChanged = (): void => {
      dirty = true;
      draw();
    };
    canvas.addEventListener('scene-telemetry', telemetryChanged);
    function syncAnimation(): void {
      if (disposed || reduced || !visible || document.hidden) {
        cancelAnimationFrame(frame);
        frame = 0;
        lastTime = 0;
        return;
      }
      if (!frame) frame = requestAnimationFrame(tick);
    }
    function tick(time: number): void {
      frame = 0;
      if (disposed) return;
      if (visible && !document.hidden && (dirty || !reduced)) {
        phase += reduced ? 0 : Math.min(50, lastTime ? time - lastTime : 0) * 0.000625;
        draw();
        lastTime = time;
        dirty = false;
      }
      syncAnimation();
    }
    document.addEventListener('visibilitychange', syncAnimation);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      intersection.disconnect();
      document.removeEventListener('visibilitychange', syncAnimation);
      canvas.removeEventListener('pointerdown', down);
      canvas.removeEventListener('pointermove', move);
      canvas.removeEventListener('pointerup', up);
      canvas.removeEventListener('pointercancel', up);
      canvas.removeEventListener('keydown', key);
      canvas.removeEventListener('scene-command', command);
      canvas.removeEventListener('scene-telemetry', telemetryChanged);
    };
  }
}
