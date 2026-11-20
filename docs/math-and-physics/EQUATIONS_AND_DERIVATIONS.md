# Implemented equations: hybrid adequacy and storage MILP

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

**Canonical detail:** [hybrid methodology](../HYBRID_METHODOLOGY.md), [hourly simulator](../../apps/api/helioforge/engines/hybrid.py) and [storage MILP](../../apps/api/helioforge/engines/storage.py).

## Hourly adequacy screen

Source uses **1-hour steps** and synthetic profiles; output power is kW, aggregated energy is kWh. For interval `t`:

```text
renewables + generator + battery_discharge + grid_import
 = served_target + battery_charge + grid_export + curtailment
balance_residual_kw = left − right
```

The policy orders renewables -> demand -> surplus battery charge -> battery discharge -> grid import -> dispatchable generator -> unserved. The engine tracks critical demand and noncritical outage shedding separately; island operation requires explicit structural source references. It does **not** solve voltage, frequency, short-circuit, protection, EMT or dynamic black-start physics.

For `eta = sqrt(round_trip_efficiency)`, `E_t` in kWh, power in kW, and step `Δt=1 h`:

```text
E_(t+1) = E_t + eta × charge_kw × Δt
                 − discharge_kw × Δt / eta
E_min ≤ E_(t+1) ≤ E_max
```

No cyclic terminal energy constraint is applied to this hybrid *screen*. Variable cost sums imported energy tariff minus exported energy credit plus generator variable energy cost, without CAPEX or degradation.

## Different behind-the-meter storage optimiser

The [storage model](../../apps/api/helioforge/engines/storage.py) builds a SciPy `milp` with charge/discharge, import/export, curtailment, SOC and peak variables, plus binaries to prevent simultaneous opposing flows. Its objective is

```text
minimise Σ_t Δt × [import × buy_price − export × sell_price
                   + discharge × wear_price]
         + peak_kw × peak_charge_eur_per_kw_period
```

Subject to `PV − curtail + import + discharge = load + charge + export`, SOC propagation and explicit **equal initial/terminal SOC**. It computes a same-limits no-storage baseline by solving another MILP. No ancillary-service revenue, project NPV, capacity payment or external engineering qualification is modeled.

Distinguish these equations from the *browser Terminal*, other specialized studies and fictional sample graphics. An exact internal zero balance is not measured facility performance.
