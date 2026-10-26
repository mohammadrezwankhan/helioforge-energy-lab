/** Browser-native deterministic screening model. This is a greedy policy, not an optimizer. */
namespace HF {
  export type TerminalInputs = {
    pvKw: number;
    batteryKwh: number;
    batteryKw: number;
    loadKw: number;
    gridKw: number;
    roundtripEfficiency: number;
    initialSocFraction: number;
    minSocFraction: number;
    maxSocFraction: number;
    importPrice: number;
    exportPrice: number;
  };

  export type TerminalRunStatus = 'CONVERGED';
  export type TerminalPointStatus = 'CONVERGED' | 'ERR_BOUND' | 'ERR_VALIDATION';
  export type TerminalScale = 'linear' | 'log';
  export type TerminalMetricName =
    | 'periodCost' | 'unservedKwh' | 'renewableKwh' | 'curtailmentKwh'
    | 'peakImportKw' | 'finalSocKwh' | 'initialSocKwh' | 'terminalSocDeltaKwh'
    | 'maxBusResidualKw' | 'maxSocResidualKwh' | 'servedFraction'
    | 'totalLoadKwh' | 'servedKwh';

  export type TerminalRow = {
    hour: number;
    loadKw: number;
    pvKw: number;
    chargeKw: number;
    dischargeKw: number;
    gridImportKw: number;
    gridExportKw: number;
    curtailmentKw: number;
    unservedKw: number;
    socKwh: number;
    busResidualKw: number;
    socResidualKwh: number;
  };

  export type TerminalMetrics = {
    periodCost: number;
    unservedKwh: number;
    renewableKwh: number;
    curtailmentKwh: number;
    peakImportKw: number;
    finalSocKwh: number;
    initialSocKwh: number;
    terminalSocDeltaKwh: number;
    maxBusResidualKw: number;
    maxSocResidualKwh: number;
    servedFraction: number;
    totalLoadKwh: number;
    servedKwh: number;
  };

  export type TerminalOperatingFlag = {
    key: 'resource-bound' | 'unserved-demand' | 'soc-or-power-limit' | 'energy-drift';
    active: boolean;
    explanation: string;
  };

  export type TerminalRun = {
    modelVersion: 'terminal-greedy-hourly-v1';
    dataKind: 'synthetic-deterministic';
    status: TerminalRunStatus;
    steps: 24;
    iterations: null;
    inputs: TerminalInputs;
    rows: TerminalRow[];
    metrics: TerminalMetrics;
    flags: TerminalOperatingFlag[];
    warnings: string[];
  };

  export type TerminalSweepAxis = {
    parameter: keyof TerminalInputs;
    values: number[];
    scale: TerminalScale;
  };

  export type TerminalSweepPoint = {
    index: number;
    coordinates: Partial<Record<keyof TerminalInputs, number>>;
    status: TerminalPointStatus;
    error: string | null;
    metrics: TerminalMetrics | null;
  };

  export type TerminalSweep = {
    modelVersion: 'terminal-greedy-hourly-v1';
    axes: TerminalSweepAxis[];
    points: TerminalSweepPoint[];
    rankedPointIndices: number[];
    paretoPointIndices: number[];
    warnings: string[];
  };

  export type TerminalSensitivityRow = {
    parameter: keyof TerminalInputs;
    baseValue: number;
    step: number;
    method: 'central' | 'forward' | 'backward' | 'unavailable';
    periodCostElasticity: number | null;
    unservedKwhElasticity: number | null;
    error: string | null;
  };

  export type TerminalSensitivity = {
    modelVersion: 'terminal-greedy-hourly-v1';
    baseline: TerminalRun;
    rows: TerminalSensitivityRow[];
    warnings: string[];
  };

  export type TerminalDiffRow = {
    metric: TerminalMetricName;
    a: number;
    b: number;
    deltaAbsolute: number;
    deltaPercent: number | null;
  };

  export type TerminalDiff = {
    modelVersion: 'terminal-greedy-hourly-v1';
    rows: TerminalDiffRow[];
    warnings: string[];
  };

  type TerminalBounds = { min: number; max: number; minExclusive?: boolean };
  const terminalInputKeys: (keyof TerminalInputs)[] = [
    'pvKw', 'batteryKwh', 'batteryKw', 'loadKw', 'gridKw',
    'roundtripEfficiency', 'initialSocFraction', 'minSocFraction',
    'maxSocFraction', 'importPrice', 'exportPrice',
  ];
  const terminalBounds: Record<keyof TerminalInputs, TerminalBounds> = {
    pvKw: { min: 0, max: 100_000 },
    batteryKwh: { min: 0, max: 500_000 },
    batteryKw: { min: 0, max: 100_000 },
    loadKw: { min: 0, max: 100_000 },
    gridKw: { min: 0, max: 100_000 },
    roundtripEfficiency: { min: 0, max: 1, minExclusive: true },
    initialSocFraction: { min: 0, max: 1 },
    minSocFraction: { min: 0, max: 1 },
    maxSocFraction: { min: 0, max: 1 },
    importPrice: { min: -10, max: 10 },
    exportPrice: { min: -10, max: 10 },
  };
  const terminalTolerance = 1e-9;
  const terminalMaxSweepPoints = 441;
  const terminalWarnings = [
    'PV and load use deterministic synthetic 24-hour shapes; they are not measured weather or demand data.',
    'Dispatch is greedy: PV serves load, renewable surplus charges storage, storage serves remaining load before grid import, then remaining load is unserved. It is not cost optimization.',
    'Surplus is exported only when exportPrice is nonnegative and grid capacity is available; remaining surplus is curtailed.',
    'Charging and discharging each use the square root of roundtripEfficiency. Terminal SOC is unconstrained; initial-to-final stored-energy change is reported explicitly.',
    'periodCost covers this 24-hour synthetic period only. It excludes fixed costs, degradation, demand charges, taxes, finance, and annualization.',
    'No thermal, frequency, voltage, protection, dynamic-control, or field-calibration model is included.',
  ];

  export function terminalDefaults(): TerminalInputs {
    return {
      pvKw: 8,
      batteryKwh: 20,
      batteryKw: 5,
      loadKw: 6,
      gridKw: 10,
      roundtripEfficiency: 0.9,
      initialSocFraction: 0.5,
      minSocFraction: 0.1,
      maxSocFraction: 0.9,
      importPrice: 0.25,
      exportPrice: 0.05,
    };
  }

  function terminalError(message: string, code: 'ERR_BOUND' | 'ERR_VALIDATION'): Error & { code: string } {
    return Object.assign(new Error(message), { code });
  }

  function terminalRecord(value: unknown): Record<string, unknown> {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      throw terminalError('Inputs must be an object with exactly the documented fields.', 'ERR_VALIDATION');
    }
    return value as Record<string, unknown>;
  }

  export function terminalValidateInputs(value: unknown): TerminalInputs {
    const input = terminalRecord(value);
    const actualKeys = Object.keys(input);
    const unknown = actualKeys.filter(key => !terminalInputKeys.includes(key as keyof TerminalInputs));
    const missing = terminalInputKeys.filter(key => !Object.prototype.hasOwnProperty.call(input, key));
    if (unknown.length || missing.length) {
      const parts: string[] = [];
      if (missing.length) parts.push(`missing fields: ${missing.join(', ')}`);
      if (unknown.length) parts.push(`unknown fields: ${unknown.join(', ')}`);
      throw terminalError(`Inputs have ${parts.join('; ')}.`, 'ERR_VALIDATION');
    }
    const result = {} as TerminalInputs;
    for (const key of terminalInputKeys) {
      const valueForKey = input[key];
      if (typeof valueForKey !== 'number' || !Number.isFinite(valueForKey)) {
        throw terminalError(`${key} must be a finite number.`, 'ERR_VALIDATION');
      }
      const bound = terminalBounds[key];
      if ((bound.minExclusive && valueForKey <= bound.min) || valueForKey < bound.min || valueForKey > bound.max) {
        const lower = bound.minExclusive ? `greater than ${bound.min}` : `at least ${bound.min}`;
        throw terminalError(`${key} must be ${lower} and at most ${bound.max}; received ${valueForKey}.`, 'ERR_BOUND');
      }
      result[key] = valueForKey;
    }
    if (result.minSocFraction > result.maxSocFraction) {
      throw terminalError('minSocFraction must be less than or equal to maxSocFraction.', 'ERR_VALIDATION');
    }
    if (result.initialSocFraction < result.minSocFraction || result.initialSocFraction > result.maxSocFraction) {
      throw terminalError('initialSocFraction must be within the inclusive minSocFraction to maxSocFraction range.', 'ERR_VALIDATION');
    }
    if ((result.batteryKwh === 0) !== (result.batteryKw === 0)) {
      throw terminalError('batteryKwh and batteryKw must either both be zero or both be greater than zero.', 'ERR_VALIDATION');
    }
    return result;
  }

  function terminalSyntheticLoad(inputs: TerminalInputs, hour: number): number {
    const shape = 0.8 + 0.2 * (0.5 + 0.5 * Math.cos((hour - 19) * 2 * Math.PI / 24));
    return inputs.loadKw * shape;
  }

  function terminalSyntheticPv(inputs: TerminalInputs, hour: number): number {
    if (hour <= 6 || hour >= 18) return 0;
    return inputs.pvKw * Math.max(0, Math.sin(Math.PI * (hour - 6) / 12));
  }

  function terminalExplainNumber(value: number): string {
    return Number(value.toPrecision(12)).toString();
  }

  function terminalFlags(inputs: TerminalInputs, rows: TerminalRow[], metrics: TerminalMetrics): TerminalOperatingFlag[] {
    const resourceBound = inputs.pvKw > 0;
    const unserved = metrics.unservedKwh > terminalTolerance;
    const limits: string[] = [];
    if (inputs.batteryKw > 0) {
      if (rows.some(row => (row.chargeKw > 0 && row.chargeKw >= inputs.batteryKw - terminalTolerance)
        || (row.dischargeKw > 0 && row.dischargeKw >= inputs.batteryKw - terminalTolerance))) {
        limits.push(`battery power reached the configured ${inputs.batteryKw} kW limit`);
      }
      const minimum = inputs.batteryKwh * inputs.minSocFraction;
      const maximum = inputs.batteryKwh * inputs.maxSocFraction;
      if (rows.some(row => row.socKwh <= minimum + terminalTolerance || row.socKwh >= maximum - terminalTolerance)) {
        limits.push('stored energy reached an SOC boundary');
      }
    }
    const drift = metrics.terminalSocDeltaKwh;
    return [
      {
        key: 'resource-bound', active: resourceBound,
        explanation: resourceBound
          ? `The synthetic PV profile reaches the configured ${inputs.pvKw} kW nameplate at hour 12; this is an input ceiling, not an optimized or measured capacity.`
          : 'PV capacity is zero, so no PV resource is available in this scenario.',
      },
      {
        key: 'unserved-demand', active: unserved,
        explanation: unserved
          ? `${terminalExplainNumber(metrics.unservedKwh)} kWh of demand is unserved over the 24-hour synthetic period.`
          : 'All modeled demand is served over the 24-hour synthetic period.',
      },
      {
        key: 'soc-or-power-limit', active: limits.length > 0,
        explanation: limits.length ? `Storage limit observed: ${limits.join('; ')}.` : 'No configured battery power or SOC boundary was reached during dispatch.',
      },
      {
        key: 'energy-drift', active: Math.abs(drift) > terminalTolerance,
        explanation: Math.abs(drift) > terminalTolerance
          ? `Terminal stored energy changed by ${drift >= 0 ? '+' : ''}${terminalExplainNumber(drift)} kWh from its initial value; terminal SOC is unconstrained.`
          : 'Terminal stored energy matches its initial value within the 1e-9 kWh reporting tolerance.',
      },
    ];
  }

  export function terminalSolve(rawInputs: TerminalInputs): TerminalRun {
    const inputs = terminalValidateInputs(rawInputs);
    const eta = Math.sqrt(inputs.roundtripEfficiency);
    const initialSocKwh = inputs.batteryKwh * inputs.initialSocFraction;
    const minSocKwh = inputs.batteryKwh * inputs.minSocFraction;
    const maxSocKwh = inputs.batteryKwh * inputs.maxSocFraction;
    let socKwh = initialSocKwh;
    const rows: TerminalRow[] = [];
    for (let hour = 0; hour < 24; hour += 1) {
      const loadKw = terminalSyntheticLoad(inputs, hour);
      const pvKw = terminalSyntheticPv(inputs, hour);
      const directPvKw = Math.min(pvKw, loadKw);
      let renewableSurplusKw = Math.max(0, pvKw - directPvKw);
      let remainingLoadKw = Math.max(0, loadKw - directPvKw);
      const socBeforeKwh = socKwh;
      const chargeKw = Math.min(renewableSurplusKw, inputs.batteryKw, Math.max(0, maxSocKwh - socKwh) / eta);
      socKwh += chargeKw * eta;
      renewableSurplusKw -= chargeKw;
      const dischargeKw = Math.min(remainingLoadKw, inputs.batteryKw, Math.max(0, socKwh - minSocKwh) * eta);
      socKwh -= dischargeKw / eta;
      remainingLoadKw -= dischargeKw;
      const gridImportKw = Math.min(remainingLoadKw, inputs.gridKw);
      remainingLoadKw -= gridImportKw;
      const unservedKw = remainingLoadKw;
      const gridExportKw = inputs.exportPrice >= 0 ? Math.min(renewableSurplusKw, inputs.gridKw) : 0;
      const curtailmentKw = renewableSurplusKw - gridExportKw;
      const busResidualKw = pvKw + gridImportKw + dischargeKw + unservedKw
        - loadKw - chargeKw - gridExportKw - curtailmentKw;
      const socResidualKwh = socKwh - (socBeforeKwh + chargeKw * eta - dischargeKw / eta);
      rows.push({ hour, loadKw, pvKw, chargeKw, dischargeKw, gridImportKw, gridExportKw,
        curtailmentKw, unservedKw, socKwh, busResidualKw, socResidualKwh });
    }
    const sum = (select: (row: TerminalRow) => number): number => rows.reduce((total, row) => total + select(row), 0);
    const totalLoadKwh = sum(row => row.loadKw);
    const unservedKwh = sum(row => row.unservedKw);
    const servedKwh = totalLoadKwh - unservedKwh;
    const metrics: TerminalMetrics = {
      periodCost: sum(row => row.gridImportKw * inputs.importPrice - row.gridExportKw * inputs.exportPrice),
      unservedKwh,
      renewableKwh: sum(row => row.pvKw),
      curtailmentKwh: sum(row => row.curtailmentKw),
      peakImportKw: Math.max(...rows.map(row => row.gridImportKw)),
      finalSocKwh: socKwh,
      initialSocKwh,
      terminalSocDeltaKwh: socKwh - initialSocKwh,
      maxBusResidualKw: Math.max(...rows.map(row => Math.abs(row.busResidualKw))),
      maxSocResidualKwh: Math.max(...rows.map(row => Math.abs(row.socResidualKwh))),
      servedFraction: totalLoadKwh === 0 ? 1 : servedKwh / totalLoadKwh,
      totalLoadKwh,
      servedKwh,
    };
    return {
      modelVersion: 'terminal-greedy-hourly-v1',
      dataKind: 'synthetic-deterministic',
      status: 'CONVERGED',
      steps: 24,
      iterations: null,
      inputs,
      rows,
      metrics,
      flags: terminalFlags(inputs, rows, metrics),
      warnings: [...terminalWarnings],
    };
  }

  function terminalAxisValues(parameter: keyof TerminalInputs, lower: number, upper: number, steps: number, scale: TerminalScale): number[] {
    if (!terminalInputKeys.includes(parameter)) throw terminalError(`Unknown sweep parameter: ${String(parameter)}.`, 'ERR_VALIDATION');
    if (!Number.isFinite(lower) || !Number.isFinite(upper)) throw terminalError('Sweep lower and upper bounds must be finite numbers.', 'ERR_VALIDATION');
    if (lower >= upper) throw terminalError('Sweep lower bound must be less than upper bound.', 'ERR_VALIDATION');
    if (!Number.isInteger(steps) || steps < 2 || steps > 21) throw terminalError('Sweep steps must be an integer from 2 through 21.', 'ERR_BOUND');
    if (scale !== 'linear' && scale !== 'log') throw terminalError('Sweep scale must be linear or log.', 'ERR_VALIDATION');
    const bound = terminalBounds[parameter];
    if ((bound.minExclusive && lower <= bound.min) || lower < bound.min || upper > bound.max) {
      throw terminalError(`${parameter} sweep bounds must stay within ${bound.minExclusive ? 'greater than' : 'at least'} ${bound.min} and at most ${bound.max}.`, 'ERR_BOUND');
    }
    if (scale === 'log' && lower <= 0) throw terminalError('Log sweeps require positive lower and upper bounds.', 'ERR_BOUND');
    const values = [];
    for (let index = 0; index < steps; index += 1) {
      const fraction = index / (steps - 1);
      values.push(scale === 'linear'
        ? lower + (upper - lower) * fraction
        : Math.exp(Math.log(lower) + (Math.log(upper) - Math.log(lower)) * fraction));
    }
    values[0] = lower;
    values[values.length - 1] = upper;
    return values;
  }

  function terminalErrorCode(error: unknown): TerminalPointStatus {
    return typeof error === 'object' && error !== null && 'code' in error && error.code === 'ERR_BOUND'
      ? 'ERR_BOUND' : 'ERR_VALIDATION';
  }

  function terminalMetricsSameService(a: TerminalMetrics, b: TerminalMetrics): boolean {
    const sameDemand = Math.abs(a.totalLoadKwh - b.totalLoadKwh)
      <= terminalTolerance * Math.max(1, Math.abs(a.totalLoadKwh), Math.abs(b.totalLoadKwh));
    const sameServedEnergy = Math.abs(a.servedKwh - b.servedKwh)
      <= terminalTolerance * Math.max(1, Math.abs(a.servedKwh), Math.abs(b.servedKwh));
    return sameDemand && sameServedEnergy;
  }

  export function terminalSweep(
    rawInputs: TerminalInputs,
    parameter: keyof TerminalInputs,
    lower: number,
    upper: number,
    steps: number,
    scale: TerminalScale,
    second?: { parameter: keyof TerminalInputs; lower: number; upper: number; steps: number; scale: TerminalScale },
  ): TerminalSweep {
    const inputs = terminalValidateInputs(rawInputs);
    const axes: TerminalSweepAxis[] = [{ parameter, values: terminalAxisValues(parameter, lower, upper, steps, scale), scale }];
    if (second) {
      if (second.parameter === parameter) throw terminalError('A two-axis sweep must use two different parameters.', 'ERR_VALIDATION');
      axes.push({ parameter: second.parameter, values: terminalAxisValues(second.parameter, second.lower, second.upper, second.steps, second.scale), scale: second.scale });
    }
    const pointCount = axes.reduce((total, axis) => total * axis.values.length, 1);
    if (pointCount > terminalMaxSweepPoints) throw terminalError(`Sweep matrix cannot exceed ${terminalMaxSweepPoints} points.`, 'ERR_BOUND');
    const firstAxis = axes[0];
    if (!firstAxis) throw terminalError('A sweep requires at least one axis.', 'ERR_VALIDATION');
    const points: TerminalSweepPoint[] = [];
    for (let row = 0; row < (axes[1]?.values.length ?? 1); row += 1) {
      for (let column = 0; column < firstAxis.values.length; column += 1) {
        const coordinates: Partial<Record<keyof TerminalInputs, number>> = { [firstAxis.parameter]: firstAxis.values[column] };
        if (axes[1]) coordinates[axes[1].parameter] = axes[1].values[row];
        const index = points.length;
        try {
          const run = terminalSolve({ ...inputs, ...coordinates });
          points.push({ index, coordinates, status: 'CONVERGED', error: null, metrics: run.metrics });
        } catch (error) {
          points.push({ index, coordinates, status: terminalErrorCode(error), error: error instanceof Error ? error.message : String(error), metrics: null });
        }
      }
    }
    const valid = points.filter(point => point.metrics !== null);
    const rankedPointIndices = [...valid].sort((a, b) => {
      const left = a.metrics as TerminalMetrics;
      const right = b.metrics as TerminalMetrics;
      return left.unservedKwh - right.unservedKwh || left.periodCost - right.periodCost
        || Math.abs(left.terminalSocDeltaKwh) - Math.abs(right.terminalSocDeltaKwh) || a.index - b.index;
    }).map(point => point.index);
    const paretoPointIndices = valid.filter(candidate => {
      const value = candidate.metrics as TerminalMetrics;
      return !valid.some(other => {
        if (other.index === candidate.index || !terminalMetricsSameService(value, other.metrics as TerminalMetrics)) return false;
        const comparison = other.metrics as TerminalMetrics;
        return comparison.periodCost <= value.periodCost + terminalTolerance
          && comparison.unservedKwh <= value.unservedKwh + terminalTolerance
          && (comparison.periodCost < value.periodCost - terminalTolerance
            || comparison.unservedKwh < value.unservedKwh - terminalTolerance);
      });
    }).map(point => point.index);
    return {
      modelVersion: 'terminal-greedy-hourly-v1', axes, points, rankedPointIndices, paretoPointIndices,
      warnings: [
        'Sweep ranking sorts by unserved energy, then period cost, then absolute terminal SOC change; it is not an optimization result.',
        'This is a conditional sampled service-equivalent frontier: Pareto dominance compares only points with matching totalLoadKwh and servedKwh, minimizing period cost and unserved kWh; it is not a global optimum.',
        'Initial and terminal SOC are not constrained to match. Endpoint energy changes can bias cost comparisons, so inspect terminal SOC deltas before interpreting the sampled frontier.',
        ...terminalWarnings,
      ],
    };
  }

  export function terminalSensitivity(rawInputs: TerminalInputs): TerminalSensitivity {
    const inputs = terminalValidateInputs(rawInputs);
    const baseline = terminalSolve(inputs);
    const rows: TerminalSensitivityRow[] = terminalInputKeys.map(parameter => {
      const baseValue = inputs[parameter];
      const bounds = terminalBounds[parameter];
      const step = Math.max(Math.abs(baseValue) * 1e-3, (bounds.max - bounds.min) * 1e-8);
      let plus: TerminalRun | null = null;
      let minus: TerminalRun | null = null;
      let plusValue = baseValue + step;
      let minusValue = baseValue - step;
      let plusError: string | null = null;
      let minusError: string | null = null;
      try { plus = terminalSolve({ ...inputs, [parameter]: plusValue }); }
      catch (error) { plusError = error instanceof Error ? error.message : String(error); }
      try { minus = terminalSolve({ ...inputs, [parameter]: minusValue }); }
      catch (error) { minusError = error instanceof Error ? error.message : String(error); }
      let method: TerminalSensitivityRow['method'] = 'unavailable';
      if (plus && minus) method = 'central';
      else if (plus) method = 'forward';
      else if (minus) method = 'backward';
      const elasticity = (metric: 'periodCost' | 'unservedKwh'): number | null => {
        const baseMetric = baseline.metrics[metric];
        if (baseValue === 0 || baseMetric === 0 || method === 'unavailable') return null;
        let derivative: number;
        if (method === 'central') derivative = ((plus as TerminalRun).metrics[metric] - (minus as TerminalRun).metrics[metric]) / (plusValue - minusValue);
        else if (method === 'forward') derivative = ((plus as TerminalRun).metrics[metric] - baseMetric) / (plusValue - baseValue);
        else derivative = (baseMetric - (minus as TerminalRun).metrics[metric]) / (baseValue - minusValue);
        return derivative * baseValue / baseMetric;
      };
      return {
        parameter, baseValue, step, method,
        periodCostElasticity: elasticity('periodCost'),
        unservedKwhElasticity: elasticity('unservedKwh'),
        error: method === 'unavailable' ? `Both perturbations failed. Increase/decrease errors: ${minusError ?? 'none'}; ${plusError ?? 'none'}` : null,
      };
    });
    return {
      modelVersion: 'terminal-greedy-hourly-v1', baseline, rows,
      warnings: [
        'This is a one-at-a-time finite-difference elasticity screen, not Sobol analysis or probabilistic sensitivity.',
        'The perturbation is 0.1% of the current value, with a 1e-8 parameter-range floor; a valid one-sided difference is used at input boundaries.',
        'Elasticity is null when its baseline metric or input is zero, or when neither perturbation is valid.',
        ...terminalWarnings,
      ],
    };
  }

  export function terminalDiff(a: TerminalRun, b: TerminalRun): TerminalDiff {
    const metricNames: TerminalMetricName[] = [
      'periodCost', 'unservedKwh', 'renewableKwh', 'curtailmentKwh', 'peakImportKw',
      'finalSocKwh', 'initialSocKwh', 'terminalSocDeltaKwh', 'maxBusResidualKw',
      'maxSocResidualKwh', 'servedFraction', 'totalLoadKwh', 'servedKwh',
    ];
    const regimeShifts = a.flags.flatMap(flagA => {
      const flagB = b.flags.find(candidate => candidate.key === flagA.key);
      return flagB && flagA.active !== flagB.active
        ? [`Regime shift for ${flagA.key}: run a was ${flagA.active ? 'active' : 'inactive'} (${flagA.explanation}); run b was ${flagB.active ? 'active' : 'inactive'} (${flagB.explanation}).`]
        : [];
    });
    return {
      modelVersion: 'terminal-greedy-hourly-v1',
      rows: metricNames.map(metric => {
        const left = a.metrics[metric];
        const right = b.metrics[metric];
        const deltaAbsolute = right - left;
        return { metric, a: left, b: right, deltaAbsolute, deltaPercent: left === 0 ? null : 100 * deltaAbsolute / Math.abs(left) };
      }),
      warnings: [
        'Diff percentage is relative to the absolute value of run a; it is null when the baseline metric is zero.',
        'Runs can differ in unserved demand and terminal battery energy; neither cost nor SOC endpoints are neutralized.',
        ...regimeShifts,
        ...terminalWarnings,
      ],
    };
  }
}
