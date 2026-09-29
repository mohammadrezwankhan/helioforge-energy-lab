# Hybrid electricity screen: numerical contract

Version: `hybrid-greedy-hourly-v1` · catalogue 0.2.0 · synthetic educational data.

## Scope and boundary

The new engine is a deterministic, hourly, single-bus electrical-adequacy screen. It is separate from the repository's existing storage MILP. It is not an economic optimizer, a network power-flow solver, a dynamic inverter model, a weather forecast or a dispatch instruction. All displayed assets share an AC-equivalent balance. DC-coupled architecture labels do not imply a DC-bus, shared-inverter or clipping model.

NLR's REopt provides primary context for hybrid DER screening and outage analysis; it does not validate this implementation. NLR's grid-forming research describes a different, dynamic-control problem. See https://reopt.nlr.gov/tool and https://www.nlr.gov/grid/grid-forming-inverter-controls. No affiliation, equivalence or certification is claimed.

## Units, inputs and profiles

Power is kW; energy is kWh; prices are EUR/kWh. Each step is exactly one hour, so the sum of interval-average power multiplied by one hour yields energy. The horizon is an integer from 2 to 168 hours. The input model rejects unknown fields and nonfinite/out-of-range values. Architecture asset membership, grid topology, SOC ordering and scenario requirements are checked.

For hour-of-day `h = t % 24`, before scenario modifiers:

```text
PV(h)   = solar_kw × max(0, sin((h − 6)π/12))
Wind(h) = wind_kw × (0.38 + 0.16 sin(0.43h + 1))
Hydro   = hydro_kw × 0.60
Load(h) = load_kw × (0.78 + 0.18 sin²((h − 8)π/12)
                    + 0.25 when 17 ≤ h ≤ 20)
```

These intentionally simple profiles repeat every 24 hours. A 72-hour outage is not a stochastic reliability estimate or measured three-day weather event. Resource, demand, tariff, capacity and availability multipliers are explicit in the canonical scenario JSON. Hydro output is an electrical proxy, not a water/head model. The generator is a limited electrical source without startup, minimum-load or fuel-stock constraints.

## Reference and outage assumptions

Off-grid configurations cannot import or export. A grid-following-only off-grid configuration is rejected. During an outage, grid imports and exports are zero. Ordinary FTM/BTM architectures disconnect local resources in this teaching model, even when the user selects a GFM label; select an explicitly islandable architecture to study island energy adequacy.

An off-grid/islandable system needs a declared GFM/Dual battery reference or a compatible synchronous generator/hydro reference. The engine checks structural presence and scenario availability only. Battery reference availability is not a dynamic startup, black-start-energy, voltage, frequency, fault, protection or transfer-transient proof. An energized label means the declared model assumptions permit local electrical service.

Critical demand is `load × critical_fraction`. Only during an outage is noncritical demand deliberately removed from the target. An always-off-grid system attempts its full load. Served power is allocated to critical demand first for critical-shortfall accounting. Total shortfall includes both deliberate noncritical shedding and supply shortage; critical shortfall excludes noncritical shedding.

## Dispatch order and conservation

The non-optimized policy is: renewable output serves target demand; surplus charges the battery; deficits discharge it; the grid covers remaining deficit when available; a generator then covers what it can; the rest remains unserved. Unused renewable surplus may be exported within its limit, except when the configured export price is negative, in which case it is curtailed.

The battery does not charge from grid or generator in this policy. A price spike does not cause price-aware scheduling. A negative import tariff changes the variable-cost arithmetic but does not trigger opportunistic charging. These are deliberate limitations, not a forecast of rational market dispatch.

Let `η = sqrt(round_trip_efficiency)`. Charging and discharge powers are limited independently by rated kW and remaining energy above/below the SOC bounds:

```text
E_end = E_start + P_charge × η × 1 h − P_discharge / η × 1 h
E_min ≤ E_end ≤ E_max
renewables + generator + discharge + import
  = served + charge + export + curtailment
```

There is no simultaneous charge/discharge or import/export in a step. Aging reduces effective energy capacity while initial energy remains the chosen fraction of that effective capacity. A battery trip makes its converter power zero, not its stored energy disappear. Both energy endpoints and their difference are exposed. There is **no cyclic terminal-SOC constraint**; never compare savings while ignoring depletion of the initial energy endowment.

## Outputs and prohibited interpretations

Outputs include total/critical service, imports/exports, generation, curtailment, battery throughput, energy endpoints, balance residual, per-interval operating state and variable energy cost. Cost is:

```text
Σ(import × import tariff − export × export tariff
  + generator output × generator variable cost) × 1 h
```

It excludes CAPEX, fixed OPEX, demand charges, degradation cost, taxes, financing, fuel inventory and value of lost load. Do not annualize it or present it as project NPV. No renewable fraction or carbon credit is inferred from stored energy because charge provenance is not tracked. No statistical availability, loss-of-load probability or engineering safety certification is produced.

## Traceability and verification

Successful API runs save validated inputs, an input SHA-256, a run ID, model identifier and complete result in SQLite. An input hash identifies the input record; it is not a signed/tamper-evident chain. Rejected cases are not recorded as successful results. UI edits make old results stale and hide their numerical panels until rerun.

Tests cover all 285 applicable numerical combinations, state and power conservation, capacity/power limits, reference failures, study-only gating, tariff accounting, exports, a hand-calculated grid-only case and 100 seeded perturbations. These tests verify internal consistency, not calibration against a real installation. Independent model benchmarks and measured data remain next-release gates.
