# Terminal greedy hourly screen — analytical model

**Model:** `terminal-greedy-hourly-v1` · **data:** deterministic synthetic · **horizon:** 24 one-hour steps.

This is a new single-bus PV, battery, and grid adequacy screen. It is deliberately separate from the retained hybrid engine and storage MILP. It implements a fixed greedy dispatch recurrence. It does not solve an optimization problem, and `iterations` is null because there is no iterative solver.

## Inputs and limits

All powers are kW, battery energy is kWh, prices are EUR/kWh, and time steps are one hour. Defaults are PV 8 kW, battery 20 kWh / 5 kW, load 6 kW, grid 10 kW, round-trip efficiency 0.90, initial/minimum/maximum SOC fractions 0.50/0.10/0.90, import price 0.25 EUR/kWh, and export price 0.05 EUR/kWh.

| Input | Accepted range |
|---|---:|
| `pvKw`, `batteryKw`, `loadKw`, `gridKw` | 0–100,000 kW |
| `batteryKwh` | 0–500,000 kWh |
| `roundtripEfficiency` | greater than 0 through 1 |
| SOC fractions | 0–1, with minimum ≤ initial ≤ maximum |
| `importPrice`, `exportPrice` | −10 to +10 EUR/kWh |

Every value must be finite. Unknown and missing input fields are errors. Battery energy and power must either both be zero or both be positive. Values are rejected with a field-specific message rather than clamped.

## Synthetic hourly profiles

For hour `h` from 0 through 23, the fixed load and PV availability are:

```text
load[h] = loadKw × (0.8 + 0.2 × (0.5 + 0.5 × cos((h − 19) × 2π / 24)))
pv[h]   = pvKw × max(0, sin(π × (h − 6) / 12))
```

The load varies between 80% and 100% of its configured level with an evening peak. The PV profile is zero overnight, peaks at hour 12 at `pvKw`, then returns to zero. These equations generate a repeatable demonstration shape; they are not weather, metered demand, or a probabilistic resource model.

## Dispatch and balances

The policy serves direct PV first, uses PV surplus to charge the battery, discharges the battery to serve remaining load, imports from the grid up to `gridKw`, and records any remaining demand as unserved. It exports leftover PV only if `exportPrice` is nonnegative; exports share the same grid power limit. Remaining surplus is curtailed. It never imports extra power to charge, deliberately arbitrages prices, or discharges for export.

For round-trip efficiency `ηrt`, charge and discharge efficiencies are both `η = √ηrt`. The one-hour state transition is:

```text
SOC[h] = SOC[h−1] + η × charge[h] − discharge[h] / η
battery energy limits = batteryKwh × [minSocFraction, maxSocFraction]
charge[h], discharge[h] ≤ batteryKw
```

The bus residual checks each interval using:

```text
PV + grid import + discharge + unserved
  − load − charge − grid export − curtailment = 0
```

`busResidualKw` and `socResidualKwh` are reported per row. The output reports `initialSocKwh`, `finalSocKwh`, and `terminalSocDeltaKwh = final − initial`. There is no cyclic or terminal-SOC constraint. Storage energy can increase or decrease over the period, so a lower-cost run is not automatically energy-neutral or directly comparable with a run that ends at a different SOC.

## Outputs

Each of 24 rows contains hour, load, PV, charge, discharge, grid import/export, curtailment, unserved demand, end-of-hour SOC, and bus/SOC residuals. Summary metrics include period cost, unserved and served energy, renewable availability, curtailment, peak grid import, initial/final SOC, terminal energy change, served fraction, and maximum absolute residuals.

```text
periodCost = Σ (gridImportKw × importPrice − gridExportKw × exportPrice) × 1 hour
servedFraction = servedKwh / totalLoadKwh   (1 when total load is zero)
```

`periodCost` is only for this synthetic 24-hour interval. It excludes CAPEX, OPEX, battery wear, demand charges, taxes, financing, and lost-load valuation. It is not annualized.

Operating flags report the configured PV nameplate bound, any unserved demand, any battery power/SOC limit reached, and initial-to-final stored-energy drift. Each flag includes a plain-language explanation of what the result showed.

## Sweeps, sensitivity, and differences

One- and two-axis sweeps use linear or logarithmic values, require 2–21 points per axis, and cap the matrix at 441 runs. Log endpoints must be positive. An invalid combination is preserved as an `ERR_BOUND` or `ERR_VALIDATION` point with an error string and null metrics; a sweep does not silently omit failed configurations.

Sweep ordering sorts valid runs by lower unserved energy, then lower period cost, then smaller absolute terminal SOC change. This is a presentation order, not an optimized winner. The **conditional sampled service-equivalent frontier** compares Pareto dominance only among points with matching total load and served kWh. It minimizes period cost and unserved energy within each matched group; it is not a global optimum. Initial and terminal SOC are not constrained to match, so endpoint energy differences can bias cost comparisons. Inspect terminal SOC deltas before drawing a conclusion.

Sensitivity is one-at-a-time finite-difference elasticity for cost and unserved energy. It uses a central difference when both perturbations validate and a one-sided difference at a boundary. The perturbation is 0.1% of the current input with a `1e-8` parameter-range floor. Elasticity is null if the input or baseline metric is zero, or if neither perturbation is valid. This is not Sobol analysis and is not a probabilistic attribution.

Run differences give `b − a` absolute changes and percent changes relative to `abs(a)`. Percent change is null for a zero baseline. The diff also reports a regime-shift warning when an operating flag changes between runs, with both run-specific explanations. Run differences retain changes in service and endpoint SOC; they do not create a terminal-neutral comparison.

## Exclusions and use boundary

This screen is not a mixed-integer linear program, economic dispatch optimizer, controller, reliability forecast, measured-data study, calibrated digital twin, investment model, or field design. It contains no wind, generator, hydrogen, thermal, frequency, voltage, reactive-power, protection, transient, degradation, reserve, or network model. No weather uncertainty or annual billing model is present. Do not infer annual energy/cost by multiplying this result by 365. Do not treat the result as operating advice.

The repository's existing 19 runnable / 17 study-only architecture boundary and retained numerical engines are unaffected by this independent demonstration model.
