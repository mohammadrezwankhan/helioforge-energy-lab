# Model registry

Registry version: `1.0.0` · Content revision: 2026-10-29.

This registry is generated from the Python-backed study catalogue embedded in `apps/web/src/roadmap-data.ts`. It inventories source contracts and default fixtures; the per-study acceptance cards distinguish packaged evidence from checks not run during this documentation change.

## Version identities

| Layer | Identity | Evidence |
|---|---|---|
| Browser application release | 2.0.0 | scripts/build-domain.mjs sets the browser release version on the generated app.json; this source identity does not prove deployment. |
| Python API package | 2.0.0 | apps/api/pyproject.toml |
| Hybrid catalogue | 0.2.0 | 36 architectures, 24 scenarios, 36 lessons |
| Study catalogue | No declared semantic version; SHA-256 `9c89b475d9e929f1cad0792dc955082cc30bf87be305be175e22a6e9a9c5495f` | 59 IDs / 12 workspaces |
| Hybrid example data | hybrid-presets-v1 / helioforge.hybrid-bundle.v1 | 285 bundled cases; dataset digest in JSON |
| Study example data | No declared dataset version; digest `d53241ccab2357c73309dc5bc57d1cd3e6941ab1a3d2c51c2b68df5f82243077` | Synthetic or user-supplied-unverified examples |
| Study model | `roadmap-screen-v1` | Per-study association is listed below |
| Study result schema | U — no standalone schema_version in current envelope | See `docs/roadmap/CONTRACT.md` and individual source module |

A version or digest identifies a source object. It does not prove its scientific accuracy or deployment state.

## Workspaces and linked study contracts

### Hybrid systems lab · `hybrid` {#workspace-hybrid}

Route: `#hybrid` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Coupled oscillation modes · `hybrid-resonance` {#study-hybrid-resonance}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 5 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `42938f1b89cacfef9b64a8aee1cf84dcae30fbdb8c03cea50ab621aae2596df7`, evidence SHA-256 `71b1d4b8286a9a41ad75590b7a75ba7a306ddd5e6f9ab7920970b499abc83095`. Independent hand check: **NOT RUN**.

Equations:
- `q'' + C q' + K q = u`
- `det(s²I + sC + K) = 0`
- `H(jω) = (K − ω²I + jωC)⁻¹`

Model limits:
- Two-mode lumped oscillator proxy; parameters are illustrative, not measured inverter/network impedances.
- Pole screening is not EMT simulation, SSR diagnosis, protection coordination or stability certification.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#hybrid-resonance).

#### DC clipping recovery · `hybrid-clipping` {#study-hybrid-clipping}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `2a6d7f71fc38b9a55d1cb9c9f8548eb89df74e9fc11242677bad3e16d49aa13a`, evidence SHA-256 `3c1d95ca4a34e544e67df0ca8a41951c27be80ad3c95c034caf19508a0d95375`. Independent hand check: **NOT RUN**.

Equations:
- `Pdc,inverter limit = Pac,rated / ηinv`
- `Pclip = max(0, Ppv − Pdc,inverter limit)`
- `Pcharge = min(Pclip, Pcharge,max, (Emax − E0)/(ηcharge Δt))`
- `E1 = E0 + ηcharge Pcharge Δt`

Model limits:
- Single interval, DC-side energy balance; no battery discharge, thermal limits, voltage-window or detailed inverter topology.
- Recovered energy is a physical screening quantity, not a dispatch forecast or project value.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#hybrid-clipping).

#### Synthetic inertia and RoCoF · `hybrid-inertia` {#study-hybrid-inertia}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `316334f9753f6d095fcf9abada759d47c2e6e2142af2c4384eb2c53e2f60a9ce`, evidence SHA-256 `a58003de3f6d9d0c968ebb446cf31e90df0360136da53ccfeb946c79f2fb0a11`. Independent hand check: **NOT RUN**.

Equations:
- `df/dt = f0/(2 H Sbase) · (Pgov + Psyn − ΔPtrip − D Δf)`
- `Psyn = clip(−Msynthetic · df/dt, 0, Psynthetic,max)`
- `dPgov/dt = (clip(Kdroop · max(−Δf,0),0,Preserve) − Pgov)/τ`

Model limits:
- Reduced-order aggregate frequency response; fixed trip and simplified governor/derivative service.
- Not an EMT simulator, protection study, grid-code assessment or certified inertia requirement.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#hybrid-inertia).

#### Balanced AC nodal power flow · `hybrid-powerflow` {#study-hybrid-powerflow}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `75bd8bd8e2d3b29dcaa90947f359e43f163b85b6d115537ab52c2eb828b88e3e`, evidence SHA-256 `1d9b3567ad8f35285ba73e25ef99164b960ef26f48e70b980a4018461aedc78c`. Independent hand check: **NOT RUN**.

Equations:
- `I = Ybus·V; Sbus = V·conj(I)`
- `PQ residuals are calculated P/Q plus specified positive loads; slack voltage magnitude and angle are fixed.`
- `Branch-end S = V·conj(Ibranch); real branch loss = Pfrom + Pto.`

Model limits:
- Balanced positive-sequence per-unit educational model; one slack bus and constant-power PQ loads only.
- No generator PV/Q limits, transformers, controls, protection, unbalanced phases or operational dispatch.
- Non-converged or non-finite solutions fail closed. Overloaded branch ratings are reported, not controlled.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#hybrid-powerflow).

#### PWM inverter/filter transient · `hybrid-switching` {#study-hybrid-switching}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 10 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `40cf32e2f140ef8600c12805d08b9416a762df6a45f75f88fe27bb5a2904546c`, evidence SHA-256 `4740e5cfe1865f4f13882295edf9045f9844f0a513079bdb93428478922860e4`. Independent hand check: **NOT RUN**.

Equations:
- `L·di/dt = vinverter(t) − vgrid(t) − R·i`
- `Switched bridge: vinverter ∈ {−Vdc/2, +Vdc/2} from sinusoidal-reference/carrier comparison.`
- `Averaged bridge: vinverter = (m·Vdc/2) sin(2πf1t); RL step uses the exact constant-input exponential update.`

Model limits:
- Single-phase series-RL filter, ideal bipolar switches and stiff sinusoidal grid; no semiconductor losses, dead time, PLL or control loops.
- Switching mode is explicitly sampled; the averaged mode removes carrier ripple. This is not a validated EMT product study.
- A half-step current-RMS comparison is reported as a numerical resolution check.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#hybrid-switching).

#### Averaged inverter control response · `hybrid-controls` {#study-hybrid-controls}

Model: `roadmap-screen-v1`. Python: [control_studies.py](../apps/api/helioforge/engines/control_studies.py) · Tests: [test_control_studies.py](../apps/api/tests/test_control_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 21 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `58d71dd8e911c20b1c3fc01dc2d8887a8917f80e75d256549465cb3af365d0e8`, evidence SHA-256 `5c4ef5f7b976c6be3dd76495c7f8b6574ef8747bcd1a3b773b7faffb41c7a736`. Independent hand check: **NOT RUN**.

Equations:
- `L_f·d i_f/dt = u_inv − v_c − R_f i_f + ωL_f J i_f; C_f·d v_c/dt = i_f − i_g − i_load + ωC_f J v_c; L_g·d i_g/dt = v_c − v_grid − R_g i_g + ωL_g J i_g, with J=[[0,1],[-1,0]].`
- `i_ref = sat_I(i_g+i_load+K_pv(v_ref−v_c)+K_iv∫(v_ref−v_c)dt); u_inv = sat_V(v_c+K_pi(i_ref−i_f)+K_ii∫(i_ref−i_f)dt). Integrators use back-calculation from each vector-limit residual.`
- `The averaged two-level inverter voltage bound is Vdc·m_max/√3. State derivatives are integrated with fixed-step RK4 at dt and dt/2; aligned trajectories are compared as a numerical refinement check.`

Model limits:
- Balanced positive-sequence dq averaged plant; the grid angle is imposed at the nominal frequency. There is no PLL state or synchronization transient.
- No PWM switching ripple, dead time, sample/computation delay, sensor filters, DC-link dynamics, unbalance, harmonics, protection, or grid-code behavior is modeled.
- The fixed-step RK4 model and local linearization are software research screens, not a calibrated controller, hardware result, field validation, or service qualification.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#hybrid-controls).

### Learning studio · `lessons` {#workspace-lessons}

Route: `#lessons` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Net load and ramps · `lessons-duck` {#study-lessons-duck}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 3 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `c40a02b1ab8a04cb0bd94ee0e23763b034fb77086c82be31fb9ec1591b6f844c`, evidence SHA-256 `859e80d471bf574c94d3edef215551d775d197ad16654ba70a05ce290ddc4ccb`. Independent hand check: **NOT RUN**.

Equations:
- `net load[t] = load[t] - solar[t] - wind[t]`
- `ramp[t] = (net load[t] - net load[t-1]) / interval hours`
- `net-load energy = sum(net load[t] * interval hours)`

Model limits:
- Synthetic equal-duration series; no dispatch, forecast, or grid-constraint model.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#lessons-duck).

#### Black-start sequence exercise · `lessons-blackstart` {#study-lessons-blackstart}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `9584284a0d8d5f8c4a17e1b03cbde839d3d5a46d385a105ce252bc771dffb4fa`, evidence SHA-256 `a94bfaff59524438a7f2c816d99703b6c123d0e27160fd52d3cf0593edcf818f`. Independent hand check: **NOT RUN**.

Equations:
- `available budget = rated power * available fraction`
- `step passes if active power + inrush <= rated power * (available fraction - reserve fraction)`
- `states: dark -> grid-forming-ready -> bus-energized -> load-restored`

Model limits:
- Procedural finite-state exercise only; no transient, protection, motor-start, or energization validation.
- Budgets and sequence require system-specific operator review.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#lessons-blackstart).

#### Hydrogen energy pathway · `lessons-hydrogen` {#study-lessons-hydrogen}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `5c32abfe7e669a83892218dd80d1b40470274d16eb58c9d953df8ea4fe25145b`, evidence SHA-256 `a8e3dd7e6715de6cc54143790fdf170cdb52594814ef8eca030ec596e5c8ca69`. Independent hand check: **NOT RUN**.

Equations:
- `chemical energy = hydrogen mass * 33.3 kWh/kg (LHV basis)`
- `fuel-cell electricity = chemical energy * electric efficiency`
- `electricity input = useful output + electrolysis + compression + fuel-cell losses`

Model limits:
- Stage parameters are illustrative, not measured plant performance.
- Compression boundary, delivery pressure, leakage, and plant auxiliaries are not modeled.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#lessons-hydrogen).

#### Timed LRC energization transient · `lessons-energization` {#study-lessons-energization}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 10 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `94d879bbb2569af4d4553c6451bcc27f7cb7482de76c493d732be9dbac1b49fa`, evidence SHA-256 `4605f2da9463e436145e356516dc219608eb59c67e182996e2ea680db8294a69`. Independent hand check: **NOT RUN**.

Equations:
- `L di/dt = vsource − R i − vC after breaker close`
- `C dvC/dt = i; before the close event, i and vC remain constant.`
- `E = ½Li² + ½CvC²; dE/dt = vsource·i − Ri² while connected.`

Model limits:
- One ideal single-phase series-RLC branch with a source-side close event; no transformer saturation, relay logic, arc or multi-step restoration.
- This lesson is not a black-start study or a certified energization/inrush limit assessment.
- A half-step peak-current comparison and circuit energy residual are reported.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#lessons-energization).

#### Hydrogen auxiliary energy ledger · `lessons-hydrogenaux` {#study-lessons-hydrogenaux}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `ed71591eb49d25c6e5660897b7daa4ebe600b7488789383880669f3fe2b4b423`, evidence SHA-256 `5d6726350869d822150e02cf2bf9b88537347cdddb2789d46b8a4c86dde51128`. Independent hand check: **NOT RUN**.

Equations:
- `water stoichiometry = 9 kg feedwater per kg H₂ / recovery fraction`
- `ideal isothermal compression = m·R_H₂·T·ln(Pout/Pin) / compressor efficiency`
- `electricity input = useful electricity + useful recovered heat + explicit losses`

Model limits:
- Isothermal ideal-gas compressor proxy from supplied outlet pressure; no real-gas, multistage, storage, leakage, purity, or pressure-drop model.
- Hydrogen LHV and 9 kg/kg stoichiometry are fixed screening conventions; plant-specific stack and water data are required.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#lessons-hydrogenaux).

### Scenario compare · `compare` {#workspace-compare}

Route: `#compare` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Comparable-run Pareto screen · `compare-pareto` {#study-compare-pareto}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `4f296a339cebe21478c3d273ea0ae99ce1fe429331b902b55bdc7bdec85afcba`, evidence SHA-256 `22f332e760056403db191bc62dd3d0e3adce59679220837f6574b1ca6d374f64`. Independent hand check: **NOT RUN**.

Equations:
- `a dominates b when it is no worse on all objectives and strictly better on one`
- `score = weighted sum of within-group min-max normalized objectives`

Model limits:
- Comparison requires matching scenario, sample-set key, horizon, service basis, and sample count.
- Expected loss-of-load hours are supplied estimates; recommendation depends on user weights.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#compare-pareto).

#### Fourteen-day storage dispatch · `compare-dunkelflaute` {#study-compare-dunkelflaute}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 5 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `8af60e8d4cf71a8d86659bb5e5c5ba2bf4d25d664bee3104b4f99dc22b87dec5`, evidence SHA-256 `89a51d19bb519a2ef7d5c85c8930429869efb1fb73aa710bb87f67fe052b5eef`. Independent hand check: **NOT RUN**.

Equations:
- `renewable + discharge + shortfall = load + charge + curtailment`
- `SOC[t+1] = SOC[t] + charge efficiency*charge - discharge/discharge efficiency`
- `charge <= power limit*mode; discharge <= power limit*(1-mode); mode is binary`
- `minimize shortfall subject to SOC[0] = SOC[336] = initial SOC`

Model limits:
- One synthetic 336-hour weather path, not a repeated demo day or statistical LOLE estimate.
- Reduced mixed-integer dispatch enforces battery direction but omits degradation, reserves, network, and market constraints.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#compare-dunkelflaute).

#### Thermal and cycle-wear screen · `compare-thermal` {#study-compare-thermal}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `def66335c4dbfa79561796b23366e2d2559bed9833b40065e22a3a4b73aa6720`, evidence SHA-256 `9e7ebf8fafac1e98389c3b5a9de3afa154ae2df791e6b0423168b8d57b085d0c`. Independent hand check: **NOT RUN**.

Equations:
- `EFC = years * 365 * cycles/day * utilization * depth of discharge`
- `thermal multiplier = exp(user factor * (temperature - reference temperature))`
- `screening wear index = EFC * user loss fraction / 1000 * thermal multiplier`

Model limits:
- Temperature factor and cycle-loss rate are assumptions, not fitted cell-aging laws.
- Wear index may exceed 100%; it is not a capacity-fade forecast, warranty, or safety limit.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#compare-thermal).

#### Lumped thermal reaction screen · `compare-thermalphysics` {#study-compare-thermalphysics}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 12 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `08523185b0074291bca13df53a5a252a29e86003a901b3c508fdd30483cec0ff`, evidence SHA-256 `8b86353c3d394d440a10445dd787055e4c3f3c9f3bc1ca3ffd6f5b63db0584f7`. Independent hand check: **NOT RUN**.

Equations:
- `k(T) = kref·exp[−Ea/R·(1/T − 1/Tref)] with absolute temperature in kelvin`
- `dα/dt = k(T)(1−α)`
- `Cth·dT/dt = Etotal·dα/dt − UA·(T − Tambient).`

Model limits:
- Single effective thermal mass, constant cooling and one depleted reaction; no spatial gradients or material-specific chemistry.
- Temperature/reaction thresholds only stop this illustrative calculation; this is not a validated safety alarm or hazard assessment.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#compare-thermalphysics).

#### Chronological reliability ensemble · `compare-reliability` {#study-compare-reliability}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 7 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `dcd927302399abfbfb70039b8f658f8065f372e8b8515ac572ef2720af755509`, evidence SHA-256 `3443d2200bea3e467b6da7795c279ad33f7023d268bf56990a1e6032b5be4881`. Independent hand check: **NOT RUN**.

Equations:
- `LOLE[horizon] = mean over trials of hours with unserved load`
- `EENS[horizon] = mean over trials of Σ unserved kWh`
- `annualized metric = horizon expectation × annualization_hours / horizon_hours`
- `SOC evolves once across each sampled chronology; it is initialized once per trial`

Model limits:
- Weather is a mean-one lognormal AR(1) multiplier; a single thermal unit follows a geometric failure/repair process.
- Annualization assumes the supplied horizon represents a typical year; it does not stitch repeated horizons or certify a resource adequacy standard.
- Two-sided 95% Hoeffding intervals use independent bounded trial-level annualized outcomes and can be wide, especially with few or zero observed loss events; no weather-year sampling or network adequacy model is included.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#compare-reliability).

### Command centre · `overview` {#workspace-overview}

Route: `#overview` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Correlated weather stress · `overview-weather` {#study-overview-weather}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `0402e26d161c32c1c8f0807ad1813a69c9b2856c42973a5f61e7d4db73734382`, evidence SHA-256 `65958eed23736922bd1dfcdb02d5df2a4ea0ddabf40447affa588099bd8ee712`. Independent hand check: **NOT RUN**.

Equations:
- `z_i,t = sqrt(common_share) z_common,t + sqrt(1−common_share) z_idiosyncratic,i,t`
- `stress_i,t = generation_i × sensitivity_i × max(0, −z_i,t), capped at 100%`

Model limits:
- Synthetic standardized shocks; no weather observations, technology calibration, spatial model or outage probability.
- The reported stress index is a bounded generation-weighted exposure proxy.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#overview-weather).

#### Value versus variable cost · `overview-merit` {#study-overview-merit}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `d1e4ec58847b38d434cae98662c115ee1b24ff4a1218aa6420b7435f43efc2d4`, evidence SHA-256 `e8e1666b778d48ca6c37e2dc6333f8d33f7006f6d5eec46226b9a8f5e53e0179`. Independent hand check: **NOT RUN**.

Equations:
- `net value_route,i = assumed value_route,i − variable cost_i`
- `weighted net value_i = Σ_route weight_route × net value_route,i`

Model limits:
- All matrix values and route weights are user assumptions; no dispatch, balancing eligibility, fees, shape or contract terms are inferred.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#overview-merit).

#### Hourly versus static emissions · `overview-carbon` {#study-overview-carbon}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `580b5057ad05badedcad285a52632446d74ebb992fe47b6d8fb029f79418f96c`, evidence SHA-256 `d274a32d97acfccb87cb4e976149159344c30aaa6670ae14d20835a268738a41`. Independent hand check: **NOT RUN**.

Equations:
- `hourly emissions = Σ_h generation_h × marginal_factor_h`
- `static comparison = Σ_h generation_h × annual_static_factor`

Model limits:
- Supplied factors are not recalculated or calibrated; this does not estimate lifecycle emissions, avoided credits or annualize a sample day.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#overview-carbon).

#### Portfolio evidence and threshold screen · `overview-risk` {#study-overview-risk}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 0 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `8f3f9c27d9b4cfc3cf603c15667240f02309ef53bc498bede4c4fb71c87a0267`, evidence SHA-256 `85828d40d7f64615125ed0ca21b2f5f7db6cf5c8fff132b56fee221bd34b422d`. Independent hand check: **NOT RUN**.

Equations:
- `status = missing_value if value is absent; otherwise compare to the supplied min/max threshold`
- `provenance is complete only when a source reference and observation date are both supplied`

Model limits:
- No asset values, thresholds, or sources are fabricated; an empty dataset returns an explicit no-evidence state.
- Threshold comparison does not authenticate records, normalize units, or imply risk approval.
- The NIST publication provides materials-data evaluation context; the source-plus-date completeness rule is this application’s own checklist, not a NIST validation standard.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#overview-risk).

### Storage & flexibility · `storage` {#workspace-storage}

Route: `#storage` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Separate battery aging mechanisms · `storage-degradation` {#study-storage-degradation}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 5 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `0e327f6bfce98f41564a501979eafb300224c6c0e8e6216fdb2082de033c5543`, evidence SHA-256 `54ccb7e438d36c05ca7ba98dc9310bbc98f5492218d77ec6786b8f78d723cad8`. Independent hand check: **NOT RUN**.

Equations:
- `LSEI = kSEI √t · 2^((T−25°C)/10°C)`
- `Lplating = kplate · t · (C-rate/2)² · max(0,(15°C−T)/25°C)`
- `Lfatigue = kfatigue · EFC · (0.5 + 0.5 DOD)`

Model limits:
- Mechanism terms are independently parameterized, additive screening proxies and intentionally uncalibrated.
- No cell chemistry, SOC history, charge protocol, coupled electrochemistry, uncertainty or warranty prediction.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-degradation).

#### Reserve and arbitrage headroom · `storage-stacking` {#study-storage-stacking}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 5 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `5e6af3c975ecd3bba3181c766496fd3b1ca1b81f512783ace95083077614ecd4`, evidence SHA-256 `2b0df56ab0c4825b42a13cdc4a0c3361acc31dd394a42a4c40492b4ad910e5dd`. Independent hand check: **NOT RUN**.

Equations:
- `maximize Σ(price·(d−c)·Δt/1000 + reserve_price·reserve_MW·Δt)`
- `SOC[t+1] = SOC[t] + ηc c[t]Δt − d[t]Δt/ηd`
- `SOC[T] = SOC[0]`
- `c + d + r_up + r_down ≤ P; reserve energy margins use stated activation duration`

Model limits:
- Illustrative perfect-foresight MILP with conservative simultaneous headroom and one terminal-SOC constraint.
- Reserve quantities and prices are user assumptions; no market eligibility, bid acceptance, availability, penalties, taxes or annualization.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-stacking).

#### Flywheel and battery split-frequency dispatch · `storage-synergy` {#study-storage-synergy}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `226e32f06082e55b9b2039b8410779b59459e52f75544ff667cdab1203a72909`, evidence SHA-256 `e99620988ffbb162eba471bdda39280bd7ae66b96e8759b6942946c94d362678`. Independent hand check: **NOT RUN**.

Equations:
- `ℓ[t] = ℓ[t−1] + α(P[t]−ℓ[t−1]); α = Δt/(τ+Δt)`
- `Pflywheel,request = P−ℓ; Pbattery,request = P−Pflywheel`
- `E[t+1] = E[t] − PΔt/ηd for P≥0; E[t+1] = E[t] − PηcΔt for P<0`

Model limits:
- A first-order frequency split and sequential clipping are transparent dispatch proxies, not an optimized controller.
- No voltage, thermal, ramp, converter, degradation, coupled control or field response validation.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-synergy).

#### 8760-hour dispatch and tariff builder · `storage-annual` {#study-storage-annual}

Model: `roadmap-screen-v1`. Python: [toolkit_studies.py](../apps/api/helioforge/engines/toolkit_studies.py) · Tests: [test_toolkit_studies.py](../apps/api/tests/test_toolkit_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 9 bounded numeric field(s), 3 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `67dc3f746227f6ac9d591f65a760c0efc1cbf87e936f0b981ca74ee7e186fa93`, evidence SHA-256 `4828edd3b44c5d6c78b33b4797c2be206b17b9863bd306511e97b51ae0cdb53d`. Independent hand check: **NOT RUN**.

Equations:
- `SOC[t+1] = SOC[t] + sqrt(efficiency)*charge - discharge/sqrt(efficiency)`
- `Monthly demand cost = sum(monthly maximum import kW * monthly tariff)`
- `Both initial and terminal SOC = 50%; usable range = 10–90%.`

Model limits:
- Explicit non-leap 8760-hour calendar; no DST. Synthetic seasonal weather is not site-calibrated.
- Transparent tariff-threshold policy, NOT the short-horizon MILP or a globally optimal annual solution.
- Unconstrained grid connection; no reserve services, outages, demand ratchets, taxes or fixed fees.
- No daily result is multiplied by 365. Annual totals sum every generated or supplied hour.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-annual).

#### Sub-second frequency droop response · `storage-response` {#study-storage-response}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 11 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `f8e2972bdbefc8d10947470e43793990816dd4b9307e73ee665f86c2c089a120`, evidence SHA-256 `0e8d70eeafe5070307b4b577a921be50f1b8ef111ad217346152834515f60ff7`. Independent hand check: **NOT RUN**.

Equations:
- `Pcommand = −droop·(f − fnominal) outside the selected deadband`
- `Power is bounded by ramp, rated kW and SOC energy headroom.`
- `ΔSOC = −P·Δt/(3600·ηdischarge) for discharge; charge uses ηcharge; delivered kWh = ΣP·Δt/3600.`

Model limits:
- Deterministic response to supplied frequency samples; each interval holds its measured frequency and output power constant.
- No grid-code, telemetry, controls, inverter current, reserve procurement, metering or service-qualification model.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-response).

#### Capacity-fade coefficient fit · `storage-agingfit` {#study-storage-agingfit}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 0 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `2b0cfcac393854bf1eea0621e4c05519a4f3a8dddd2f94fe50f0a0628b3bb29f`, evidence SHA-256 `0fd55e00d3ce367e06ebb8d259d95216eb1d0263f0166a5bddbbe1e8b6aa6ac1`. Independent hand check: **NOT RUN**.

Equations:
- `retention = 1 − a·(cycles/1000)·exp(b·(temperature°C − 25))`
- `SciPy bounded least-squares fit uses records 0–3 of each fixed five-record group; every fifth record is held out.`

Model limits:
- The included records are a synthetic software fixture, not cell measurements or scientific validation.
- This two-coefficient empirical curve ignores chemistry, SOC, C-rate, calendar aging, path dependence, uncertainty and censoring.
- Held-out error describes only the supplied records and cannot qualify a warranty or predict field life.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-agingfit).

#### Full-year storage optimization · `storage-annualopt` {#study-storage-annualopt}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 5 bounded numeric field(s), 4 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `6d4028334ec7520fad95532938f96b2cf422dfec43ea3b0a3b45be09d5b7300e`, evidence SHA-256 `ce23df9c5d2081bc61c238a338aad8d570e8e317b3c25c6a9f2698db90205900`. Independent hand check: **NOT RUN**.

Equations:
- `SOC[t+1] = SOC[t] + ηcharge·charge[t] - discharge[t]/ηdischarge`
- `grid import + PV - curtailment + discharge = load + charge + grid export`
- `annual objective = hourly energy/wear costs + Σmonth demand_charge × monthly peak import`
- `SOC[0] = SOC[8760] = supplied initial SOC`

Model limits:
- Non-leap year with equal one-hour intervals; 24-point tariffs repeat by hour of day.
- Import price must strictly exceed export price each hour; simultaneous grid import/export is then dominated.
- Synthetic defaults are not a meter record, billing tariff, reserve product, degradation model, or investment case.
- A time-limit, infeasible, or non-optimal HiGHS result is rejected; the returned schedule is only a proven optimum.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#storage-annualopt).

### PV economics · `pv` {#workspace-pv}

Route: `#pv` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Slope-aware tracker backtracking screen · `pv-backtracking` {#study-pv-backtracking}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `5a6f3cc3d5a62edbed36b0d14b18e55441730e10992058fb7c61aae07204abfe`, evidence SHA-256 `ecd238293d7983a546f8804647ee91e60d4366c043aa59d7fe643ef90ad76eb7`. Independent hand check: **NOT RUN**.

Equations:
- `βcross = atan(tan(slope) · sin(azslope − azaxis))`
- `θideal = atan2(sun_cross · cosβ + sun_up · sinβ, −sun_cross · sinβ + sun_up · cosβ)`
- `θbt = θideal − sign(θideal) arccos(|cos θideal|/GCR) when |cos θideal| < GCR`

Model limits:
- A two-dimensional planar row geometry with a cross-slope projection; edge effects, tracker limits and terrain variation are omitted.
- NREL's slope-aware method includes full reference frames and shaded-fraction treatment; this screen is not its implementation or an energy-yield model.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-backtracking).

#### Agrivoltaic PAR and land geometry · `pv-agrivoltaic` {#study-pv-agrivoltaic}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `20baee265bd2bf692a6288b92e431cb8808a5e2d546093568a21b9d39cde87bf`, evidence SHA-256 `77d5281b58063da339964c6a71a3078c3d8c4d361f3d06d391afbc7831129cb3`. Independent hand check: **NOT RUN**.

Equations:
- `A = ½ |Σ(xᵢyᵢ₊₁ − xᵢ₊₁yᵢ)|`
- `Ausable ≈ max(0, A − perimeter·setback)`
- `PARcrop ≈ PARopen · [1 − GCR · (1 − module transmission)]`

Model limits:
- Perimeter setback subtraction is a conservative area proxy, not an exact polygon offset or cadastral calculation.
- PAR proxy omits time-of-day geometry, crop response, spectral effects, diffuse light, row spacing, equipment access and yield validation.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-agrivoltaic).

#### Monthly bifacial albedo response · `pv-albedo` {#study-pv-albedo}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 5 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `2f933af9a62a5e13d931885ce2394885b0977cd1c9c95cc78bbb27f19f512a8e`, evidence SHA-256 `acad44d4dc0ad9af93f0f0824f70b174add5c949a99f4574e118d84a0f6bef61`. Independent hand check: **NOT RUN**.

Equations:
- `Grear = Gground · albedo · rear_view_factor`
- `Efront,m = Pdc · PR · Gfront,m`
- `Etotal,m = Pdc · PR · (Gfront,m + bifaciality · Grear,m)`
- `Eyear = Σₘ Etotal,m`

Model limits:
- Monthly scalar irradiance screen; rear view factor and PR are user assumptions, not ray tracing or site meteorology.
- No electrical mismatch, row shading, temperature, spectral, terrain or measured validation; annual energy is only as representative as the supplied 12 months.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-albedo).

#### LCOE contour sensitivity · `pv-sensitivity` {#study-pv-sensitivity}

Model: `roadmap-screen-v1`. Python: [toolkit_studies.py](../apps/api/helioforge/engines/toolkit_studies.py) · Tests: [test_toolkit_studies.py](../apps/api/tests/test_toolkit_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `28d019d628356b52ba2e634b617fb4879f0531f42dd272f84373a245867026ed`, evidence SHA-256 `14c9b5706212e0666e3175aaaf1754f8543b9d6bc156f62f08531372b868d934`. Independent hand check: **NOT RUN**.

Equations:
- `LCOE = discounted lifecycle costs / discounted lifetime MWh`

Model limits:
- Constant money; the parent PV engine retains its 30-year life and year-15 replacement assumptions.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-sensitivity).

#### Inverter repowering reserve · `pv-reserve` {#study-pv-reserve}

Model: `roadmap-screen-v1`. Python: [toolkit_studies.py](../apps/api/helioforge/engines/toolkit_studies.py) · Tests: [test_toolkit_studies.py](../apps/api/tests/test_toolkit_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `fe97427ec80a38468af22b4f978a179a982260dbbdc7d78c41364df9974ad5fc`, evidence SHA-256 `f828d0f7794f7d0657ef2f7c5feda826c6991edd0f19c63f43e68b24172e8dd1`. Independent hand check: **NOT RUN**.

Equations:
- `Future cost = present cost * (1+inflation)^years`
- `Annual deposit = future cost * return / ((1+return)^years - 1); zero return: cost/years`

Model limits:
- Constant annual assumptions; end-of-year contributions, no tax, fees or investment-return guarantee.
- First-party algebraic convention; the source reference is not independent validation or a forecast of investment returns.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-reserve).

#### Panel-sample ray-triangle shading · `pv-raytrace` {#study-pv-raytrace}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 0 bounded numeric field(s), 3 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `07fc8b63015690a8a79483c530d31959f076fd2ece8a5c5d19c1631f0b693ea8`, evidence SHA-256 `5f872d05000657728e1843edb375763a76550c22a0abe7c20475d446d21dbbf4`. Independent hand check: **NOT RUN**.

Equations:
- `incidence = max(0, n̂·ŝ); direct energy = DNI·panel area·incidence·duration.`
- `A ray is shaded when a supplied triangle intersects the half-line from a panel sample toward the sun.`

Model limits:
- Directional direct-beam only; no diffuse sky, ground reflection, spectral response, horizon/weather series or panel electrical mismatch.
- Triangles and panel samples are user-supplied local Cartesian geometry; results depend on mesh completeness and coordinate quality.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-raytrace).

#### Parcel setbacks and crop-light screen · `pv-setbacks` {#study-pv-setbacks}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `4215dcbec657d1eb390085f90fc33b89204a95eaae472437cce5b04d77933933`, evidence SHA-256 `46bcd9470a1a7c831ff8b78d5a8f44c0fd6e697fb9da7accb0438e0536e4cbf9`. Independent hand check: **NOT RUN**.

Equations:
- `usable geometry = parcel geometry buffered inward by setback distance`
- `crop DLI = baseline PAR·[1 − cover·(1 − module transmission)]`
- `illustrative response = Pmax·DLI/(DLI + half-saturation).`

Model limits:
- Planar Shapely geometry in user-supplied metres; no georeferencing, survey, legal boundary, easement or access-road interpretation.
- Crop-light response is a generic saturating curve, not species-, cultivar-, weather- or farm-calibrated agronomy.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pv-setbacks).

### Research pillars · `research` {#workspace-research}

Route: `#research` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Vibration spectrum and drift · `research-vibration` {#study-research-vibration}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `85fcfc03ead35873f1e809474a228630a847b952cfd1d9bd61194141cdab1e30`, evidence SHA-256 `4a8f32f1cb2a5aa5c1a91c877c49d474e73f9114a3debcf8db32f48811af428c`. Independent hand check: **NOT RUN**.

Equations:
- `X[k] = Σₙ x[n] exp(−j 2πkn/N)`
- `A[k] = 2|X[k]|/Σw[n] for interior one-sided bins`
- `Spectral drift = late-half dominant frequency − early-half dominant frequency`

Model limits:
- Single evenly spaced, finite record with a Hann window; half-window frequency resolution is limited.
- Peaks and drift are descriptive spectrum statistics, not a fault classifier, causal diagnosis or maintenance recommendation.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#research-vibration).

#### Supplier-stage emissions evidence ledger · `research-epd` {#study-research-epd}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `041ebb0658b8fee3695682f8299af17abb79c0c868ef740b97248365edb181a9`, evidence SHA-256 `9c4ff05f57737f51cfcd7531220e7dc176b6d444728b830c545b0d2f0349e818`. Independent hand check: **NOT RUN**.

Equations:
- `Stage emissionsᵢ = quantityᵢ · supplier/activity factorᵢ`
- `Total included emissions = Σ unique, factor-complete stage records`

Model limits:
- Per-record quantities are bounded at 1e12 declared units and factors at 1e6 kgCO₂e per declared unit to keep the arithmetic finite; choose and document suitable units.
- A traceable arithmetic ledger only: it does not verify EPD validity, product-category rules, allocation, boundary, assurance or Scope 3 category.
- Duplicate IDs retain only their first row; missing factors are reported and excluded, not imputed. Example defaults are synthetic.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#research-epd).

#### Short-circuit strength and voltage drop · `research-scr` {#study-research-scr}

Model: `roadmap-screen-v1`. Python: [engineering_studies.py](../apps/api/helioforge/engines/engineering_studies.py) · Tests: [test_engineering_studies.py](../apps/api/tests/test_engineering_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `44c8d00cc9704c69f52f926523d81d3507cc4dd87f778f8e3cfed9f66b7a2fe7`, evidence SHA-256 `f67ff32f99c448935aa0c875ff3cea9d13322d9cc94a33000ce53fd4a30bd88e`. Independent hand check: **NOT RUN**.

Equations:
- `SCRscreen = Ssc / Pplant`
- `ΔVpu ≈ (R P + X Q)/VLL²`
- `|Zth| ≈ VLL²/Ssc`

Model limits:
- Classical single-infeed ratio and balanced first-order voltage-drop approximation only.
- SCR is not a stability guarantee; interactions, loads, X/R, controls, protection and operating points require detailed network and dynamic studies.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#research-scr).

#### Bearing spectrum envelope comparison · `research-bearing` {#study-research-bearing}

Model: `roadmap-screen-v1`. Python: [physical_studies.py](../apps/api/helioforge/engines/physical_studies.py) · Tests: [test_physical_studies.py](../apps/api/tests/test_physical_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 2 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `64a8f7bd96a1bd58e64532c0787e609a38d8b244218fcf177790f11674789934`, evidence SHA-256 `42c23e10b2a4dc7898ba9b4ea4f7a349c880bbadf7d1fc1c74acb2140ab46cdd`. Independent hand check: **NOT RUN**.

Equations:
- `one-sided amplitude spectrum = |rFFT((x−mean(x))·Hann)|·2/sum(Hann)`
- `per-bin envelope = median(training) + threshold·max(1.4826·MAD, 5% of median, floor)`
- `held-out record is flagged if any spectral bin exceeds its baseline envelope; maximum_envelope_exceedance_sigma is max((amplitude−envelope)/scale) over exceeded bins, or zero when no bin exceeds.`

Model limits:
- The fixture is synthetic; sampling, sensor mounting and training records determine the envelope.
- A spectral threshold exceedance is an anomaly screen only. It does not identify a bearing fault, root cause, severity or remaining life.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#research-bearing).

#### Closed-loop inverter eigenmodes · `research-eigenmodes` {#study-research-eigenmodes}

Model: `roadmap-screen-v1`. Python: [control_studies.py](../apps/api/helioforge/engines/control_studies.py) · Tests: [test_control_studies.py](../apps/api/tests/test_control_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 14 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `c90990ac9fbccada9027b5165ae90ecb5c7cf0ce16c81225fd85d22475083464`, evidence SHA-256 `194c18e7acd8061111a4d872cd6c8d7525f1ec4b9aca2c1fd859c80652d2e2d0`. Independent hand check: **NOT RUN**.

Equations:
- `Compute the local matrix A by central-difference linearization of the same ten-state averaged plant/controller used by hybrid-controls at its unsaturated zero-load equilibrium; i_f,q=ωC_fV_grid,d supplies synchronous capacitor current, and PI integrators supply the balancing equilibrium outputs.`
- `λ_k are computed from A; local asymptotic stability requires max Re(λ_k)<0. The reported damping ratio is −Re(λ_k)/|λ_k|, and is a local linear modal quantity only.`

Model limits:
- Balanced positive-sequence dq averaged plant; the grid angle is imposed at the nominal frequency. There is no PLL state or synchronization transient.
- No PWM switching ripple, dead time, sample/computation delay, sensor filters, DC-link dynamics, unbalance, harmonics, protection, or grid-code behavior is modeled.
- The fixed-step RK4 model and local linearization are software research screens, not a calibrated controller, hardware result, field validation, or service qualification.
- This is the unsaturated local model at an equilibrium; current and modulation limit nonlinearities are inactive. It is not a large-disturbance stability guarantee.
- A negative outer voltage integral gain is accepted only to expose an intentionally wrong-sign unstable thought experiment; it is not a candidate tuning.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#research-eigenmodes).

### Market intelligence · `markets` {#workspace-markets}

Route: `#markets` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Generation-weighted capture price · `markets-capture` {#study-markets-capture}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `685f83ab37b3f6252b0ffe1460acabc7683c5157d5488daf7ae4681beddf3e9f`, evidence SHA-256 `034f015c15b795ee6f8126b00c13e4e2a0127eb2e59b4d644411efc11541caba`. Independent hand check: **NOT RUN**.

Equations:
- `adjusted_price_t = spot_price_t − slope × (penetration − reference) × exposure_t`
- `capture price = Σ_t generation_t × adjusted_price_t / Σ_t generation_t`

Model limits:
- The linear slope is a user-defined sensitivity, not an estimated market response or price forecast. Capture price is null when supplied generation sums to zero.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#markets-capture).

#### Negative settlement intervals · `markets-negative` {#study-markets-negative}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `eacf4af788e4b32d707f5939b6523b6cc83e40b5261a3a472c6c77660c2523e5`, evidence SHA-256 `e9203607487263217ed62dc56ed9ac845566bc4b99d0ddf5fa043cf6db524037`. Independent hand check: **NOT RUN**.

Equations:
- `negative interval if price < 0 and price ≤ configured threshold`
- `triggering run if consecutive_negative_intervals × 15 min ≥ configured duration`

Model limits:
- Country label is metadata only. Any suspension setting is a hypothetical user scenario explicitly UNVERIFIED; no subsidy, settlement, legal or eligibility rule is asserted.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#markets-negative).

#### Two-zone interconnection · `markets-interconnection` {#study-markets-interconnection}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `a342218f216fc5478e138046c13f739e7506300d5efa38efdf97d80d65bbbb9a`, evidence SHA-256 `14e0cd9162051d049bb4b83dff4872288bc3088003d4edf48ea67a2ce6b0bc8a`. Independent hand check: **NOT RUN**.

Equations:
- `min_f C_A(d_A+f)+C_B(d_B−f)`
- `C_i(q)=a_i q + 0.5 b_i q²; −min(capacity,d_A) ≤ f ≤ min(capacity,d_B)`

Model limits:
- Single-link two-zone convex dispatch proxy; ignores losses, network loop flows, ramping, reserves, bids, indivisibilities and actual market-coupling constraints.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#markets-interconnection).

#### Six-zone DC optimal power flow · `markets-network` {#study-markets-network}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 0 bounded numeric field(s), 5 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `352cb15ff3677bce24a97e8505369fbd449df5a7d0d5971b41540e9b0528e691`, evidence SHA-256 `00a574b4a7e187ab687dc394ee394d06d94591832e12d54ded14decb6908e9af`. Independent hand check: **NOT RUN**.

Equations:
- `flow[i,j] = susceptance[i,j]·(angle[i] - angle[j])`
- `generation[i] + net_import[i] = demand[i]`
- `min Σ generator_cost[i]·generation[i] subject to nodal balance, capacity, and branch limits`

Model limits:
- Linear DC active-power approximation with one aggregated generator per zone; no losses, reactive power, voltage, dynamics, or reserves.
- Network parameters and costs are user assumptions; no calibrated six-zone topology or real zonal market is supplied.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#markets-network).

### Forecast studio · `forecast` {#workspace-forecast}

Route: `#forecast` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Three-state price regimes · `forecast-regimes` {#study-forecast-regimes}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 4 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `6f9e112d753bf0d942dc3eefc5d5f58914154a89b279957377f7b9fd172a2cdf`, evidence SHA-256 `31defb04af903be902409a7a79214d90104ac62bf1fbdfd51d626cf80963a9d3`. Independent hand check: **NOT RUN**.

Equations:
- `S_t ∼ categorical(P[S_{t−1},·])`
- `price_t | S_t=s ∼ Normal(state_mean_s, state_volatility_s²)`

Model limits:
- Seeded annual scenarios only; user-supplied transition probabilities and state parameters are not calibrated, backtested or market forecasts.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#forecast-regimes).

#### Correlated commodity shocks · `forecast-commodities` {#study-forecast-commodities}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 4 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `9b982aecc8668d522e4bc837b4efcf02baade464bb8634048df0898cfb3a9980`, evidence SHA-256 `8a81664f0baac4cc18ceadd7dd2143391c565272ffc71295122d31460681d408`. Independent hand check: **NOT RUN**.

Equations:
- `Z_t = L ε_t, L Lᵀ = correlation matrix`
- `P_j,t = P_j,t−1 exp((μ_j−0.5σ_j²)+σ_j Z_j,t)`

Model limits:
- Synthetic geometric-random-walk shocks with constant user inputs; no forward curves, cointegration, structural fuel dispatch, calibration or forecast claim.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#forecast-commodities).

#### PPA settlement tail risk · `forecast-tail` {#study-forecast-tail}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `9cd8d1581533cc8fb1868c81def6688e5786cde3644fda43fbf18ab031efa354`, evidence SHA-256 `cc414c25643cc97ca8992cb08b679f6021b204f074a47f9ae8b18f60f0c8e98a`. Independent hand check: **NOT RUN**.

Equations:
- `spot_t = strike + Σ_{k≤t} Normal(0, (volatility × strike)²)`
- `loss_t = (spot_t − strike) × volume`
- `CVaR_α = mean of the largest ceil((1−α)N) empirical losses`

Model limits:
- Synthetic arithmetic price walk; signed buyer settlement losses versus strike, not project revenue, calibrated PPA basis, hedge effectiveness or a probability guarantee.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#forecast-tail).

#### Rank-assumed energy-price VECM · `forecast-cointegration` {#study-forecast-cointegration}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 3 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `7d4537493146637d22ad2b6e70ea84513aaca87189d84c444180f31954ae3c5c`, evidence SHA-256 `b41a38367b9f62b444b127367732935a075e99c6e3e1fec7feedfa8c4d721b76`. Independent hand check: **NOT RUN**.

Equations:
- `ECT[t] = power[t] - α - βgas·gas[t] - βcarbon·carbon[t]`
- `Δy[t] = c + loading·ECT[t-1] + Σ Γj·Δy[t-j] + ε[t]`
- `long-run relation and short-run VECM coefficients are fit on the first chronological segment only`

Model limits:
- Rank one is an explicit assumption; no Johansen rank test, unit-root test, or seasonal adjustment is performed.
- This OLS error-correction screen is not a likelihood-based Johansen estimator or a calibrated commodity forecast.
- Synthetic examples do not substitute for timestamp-aligned, currency-consistent, real market observations.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#forecast-cointegration).

#### Chronological price forecast backtest · `forecast-backtest` {#study-forecast-backtest}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 2 bounded numeric field(s), 3 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `6a6896f8518a7cf0bd9075158a7054d44fc678244e22ea80a4b494ede7a49363`, evidence SHA-256 `b7514eef2960733e4d188dbe7fd36976cc31556470b4fb1ab72446411e088f4e`. Independent hand check: **NOT RUN**.

Equations:
- `target[t] = β0 + β1·target[t-1] + β2·gas[t-1] + β3·carbon[t-1] + ε[t]`
- `MAE = mean(|actual - forecast|); RMSE = sqrt(mean((actual - forecast)^2))`
- `interval coverage = held-out actuals inside fitted training residual interval / holdout count`

Model limits:
- Uses rolling one-step actual target lags and the preceding observed gas/carbon values; multi-step future drivers are not forecast.
- Prediction intervals use a normal residual approximation and omit parameter uncertainty.
- A chronological holdout is an evaluation, not independent market calibration or a guarantee of future performance.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#forecast-backtest).

### Investment desk · `investment` {#workspace-investment}

Route: `#investment` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### DSCR-constrained sculpted debt · `investment-sculpt` {#study-investment-sculpt}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `dd9ed5077bd5f46e5e0dc2f76fad6f593a4d88272dd0f7fdbc1f7b68c60194f7`, evidence SHA-256 `7f1eef49684d1cfbe7d4185e47301cd74fd1d168151f33c7c828ca61ffd57c19`. Independent hand check: **NOT RUN**.

Equations:
- `target service_t = max(0, CFADS_t) / target_DSCR`
- `debt capacity = largest initial balance whose target-limited service amortizes within tenor without service below interest`
- `balance_t = balance_{t−1} + interest_t − principal_t`

Model limits:
- Uses the existing pre-tax nominal project-finance engine and its rounded annual CFADS. No taxes, DSRA, fees, reserve facility or legal covenant is added; infeasible requests are disclosed.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#investment-sculpt).

#### Contracted and merchant tranches · `investment-tranches` {#study-investment-tranches}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 5 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `33c2d99f5f21fb454c314174d09b3a41406b840af739e85863308b1c1a4450f4`, evidence SHA-256 `143ec198d1a264f24eba3e6a4f50dbaec1a85108fbaacd53351ba46f0a8454e0`. Independent hand check: **NOT RUN**.

Equations:
- `contracted_CFADS_t = floor_price_t × contracted_MWh_t − OPEX_t (within floor term)`
- `merchant_CFADS_t = haircut × merchant_price_t × merchant_MWh_t − OPEX_t`
- `debt-service ceiling_t = max(0, CFADS_t) / target_DSCR`

Model limits:
- User-supplied floor is a hypothetical exposure input, not an executed PPA or eligibility claim. No volume shape, basis, counterparty risk, taxes or post-expiry contracted-volume conversion is inferred.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#investment-tranches).

#### Capital and promote waterfall · `investment-waterfall` {#study-investment-waterfall}

Model: `roadmap-screen-v1`. Python: [decision_studies.py](../apps/api/helioforge/engines/decision_studies.py) · Tests: [test_decision_studies.py](../apps/api/tests/test_decision_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 0 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `80637a51f24f187bb37eb39ad714e957e643c018eed8891e8035977730423bc6`, evidence SHA-256 `4d69d195973aeeb02ab07f78dca12eb0d5f364e063444558a277ba214ca2f923`. Independent hand check: **NOT RUN**.

Equations:
- `preferred return due = capital × ((1 + preferred_rate)^years − 1)`
- `catch-up total = promote_share × LP_pref_paid / (catch-up_share − promote_share)`
- `remaining pool split LP/sponsor = (1 − promote_share)/promote_share`

Model limits:
- Explicit single-LP, time-zero contribution and single-exit convention; no interim distributions, taxes, return-of-capital priority to sponsor, clawback, IRR hurdle or legal partnership terms.
- First-party algebraic convention; the source reference is not independent validation or a legal partnership agreement.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#investment-waterfall).

#### Contract, tax, and reserve cash flows · `investment-contracts` {#study-investment-contracts}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 6 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `02bd4e8946ae89f9daabf4b18c33c2fe6187b105925a407048584382c2133798`, evidence SHA-256 `b9e66691c614d34db10e4e0633e8383902b04439fde417870779fd93395abe33`. Independent hand check: **NOT RUN**.

Equations:
- `contracted volume = min(generation, annual contract volume) while term is in force`
- `contracted settlement price = max(user floor price, supplied merchant price)`
- `taxable income = EBITDA - straight-line depreciation - interest (equity tax case); tax loss carries forward within this screen`
- `equity CF = EBITDA - cash tax - debt service - DSRA funding + DSRA release - Δworking capital`
- `project CF = -CAPEX - initial working capital; subsequent CF = EBITDA - project tax - Δworking capital`

Model limits:
- Annual calendar-year floor and merchant-price screen; no partial-year settlement, take-or-pay, VAT, tax jurisdiction rules, loss caps, depreciation conventions, fees, or default.
- Debt is level-payment; DSRA equals configured months of scheduled service and is funded from equity at close, then released after the final debt year.
- Rates and terms are user assumptions; no signed contract or tax/legal advice is represented. Nonconventional IRR is null.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#investment-contracts).

### Construction & pilots · `pilots` {#workspace-pilots}

Route: `#pilots` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Paired as-built geometry check · `pilots-photogrammetry` {#study-pilots-photogrammetry}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `75676277e4f66bf40a75f8e2dc2ecca75e6f9474083c5731d07f175859086f29`, evidence SHA-256 `390ffec5d3cffcd21004820749913b489ff8a1ec3776ad06463e5ba48301f6b3`. Independent hand check: **NOT RUN**.

Equations:
- `error[i] = norm(as-built XYZ[i] - design XYZ[i]) * coordinate scale`
- `3D RMSE = sqrt(mean(error[i]^2))`
- `selected error = empirical percentile of paired errors`

Model limits:
- Pairs are matched by array index; no registration, nearest-neighbour search, camera model, or drone connector.
- The user reporting limit does not establish survey or construction acceptance.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pilots-photogrammetry).

#### Distributed temperature profile · `pilots-dts` {#study-pilots-dts}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `f59e798220b3d7b1be3368ff8c1cc719e24f83737ef58e0746ddc750bd062640`, evidence SHA-256 `947c2de4f18bb9348d6a9f6a9b3e4add3b88a49b1f21724184b01b6692b18818`. Independent hand check: **NOT RUN**.

Equations:
- `gradient = abs(adjacent temperature difference) / adjacent distance`
- `fresh when current time - observed time <= user maximum age`

Model limits:
- Sample temperatures and the user threshold are bounded to -50–200 °C; adjacent samples must be at least 0.1 m apart.
- Thresholds are user screening values; no cable rating or calibrated alarm is claimed. Missing and stale observations are excluded from current thermal summaries.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pilots-dts).

#### Hypothetical multisensor warning vote · `pilots-offgas` {#study-pilots-offgas}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `b91d1186ba0f6ff26716ae33b92353cc69d9be8d89716e0b4f3bb0280ba49d4a`, evidence SHA-256 `3917f701da3cefd434c2eceb1548842944107e1e76ffea54389293e6a9b41456`. Independent hand check: **NOT RUN**.

Equations:
- `sensor vote = any present channel meets or exceeds its user threshold`
- `warning state = sensor votes >= required votes`

Model limits:
- Hypothetical logic only; thresholds are not calibrated alarms, exposure limits, or hazard controls.
- No gas analyser, sensor-health connector, cross-sensitivity model, or field alarm is implemented.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pilots-offgas).

#### Unpaired point-cloud registration · `pilots-registration` {#study-pilots-registration}

Model: `roadmap-screen-v1`. Python: [planning_studies.py](../apps/api/helioforge/engines/planning_studies.py) · Tests: [test_planning_studies.py](../apps/api/tests/test_planning_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `367874488470d723caec10abe36fedca2e97198ff8fe0a753f2adb1d39fe018a`, evidence SHA-256 `2781e5d644a0041bcfb805e79f0fd5f55a991a37ddbfd89f999ba4d7207837fd`. Independent hand check: **NOT RUN**.

Equations:
- `nearest-neighbor correspondences are recomputed after every transform`
- `Kabsch rigid fit minimizes Σ ||R·source[i] + t - target[i]||² with det(R)=+1`
- `trim high-residual correspondences; repeat until RMSE change ≤ tolerance or iteration cap`

Model limits:
- Requires supplied XYZ point clouds; no drone imagery ingestion or 3D reconstruction is performed.
- Unpaired ICP can converge to a local alignment; coordinate frames, units, point density, outliers, and registration quality require survey review.
- No scale, non-rigid deformation, georeferencing, or survey certification is modeled.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#pilots-registration).

### Agent council · `council` {#workspace-council}

Route: `#council` · Public delivery: bundled synthetic examples · New study calculations: local Python API. *Documentation links describe source; starting each actual run and its export was not verified in this documentation task.*

#### Finance versus storage debate · `council-debate` {#study-council-debate}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 2 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `b4d3ef0a82d47eb5426bbea1e0f487fc37b60f67eeafbacc7463f8e1c0a947a7`, evidence SHA-256 `773495176ce865887aa32a44db0c1d68524c8265fc152d980b8174c257354866`. Independent hand check: **NOT RUN**.

Equations:
- `NPV = -capex + sum(annual net value / (1 + discount rate)^year)`
- `matched claims converge only when units agree and values fit declared tolerance`

Model limits:
- Rounds are deterministic comparisons of supplied assertions; no LLM or external agent is called.
- Conflicts remain disputed; the NPV screen is not approval or a dispatch-finance bridge.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#council-debate).

#### Structured evidence manifest · `council-evidence` {#study-council-evidence}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 4 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `e181e55e9cb797e400b89ef29b9add70c3536e1bb1ad75327e280c26de8ae2b9`, evidence SHA-256 `ca55f0d38e64683c1c029844bea50202dbfdd92d5548850ba884fa82cec7f598`. Independent hand check: **NOT RUN**.

Equations:
- `age = as-of date - issue date`
- `expiry finding when expiry date < as-of date`
- `field check = expected field name and unit plus configured numeric bound`

Model limits:
- Structured JSON metadata only; no OCR, retrieval, signature validation, or authenticity verification.
- Provenance references are user-supplied text and are not independently checked.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#council-evidence).

#### Bayesian evidence toy model · `council-consensus` {#study-council-consensus}

Model: `roadmap-screen-v1`. Python: [workflow_studies.py](../apps/api/helioforge/engines/workflow_studies.py) · Tests: [test_workflow_studies.py](../apps/api/tests/test_workflow_studies.py), [test_studies_api.py](../apps/api/tests/test_studies_api.py).

Input schema: 3 bounded numeric field(s), 1 JSON data field(s). Units are supplied only where the catalogue declares them. Result schema version: **U**.

Default fixture: `synthetic_or_user_supplied_unverified`, input SHA-256 `d96dd3dcd89a139aefc25cc6f7c6ac371c8e5f2e1eecc9b95615e4b45e907ed9`, evidence SHA-256 `142ae1b303c71245e60acbc32b5e97e7dc674256c5b83fa4d0eaafb3db42a77a`. Independent hand check: **NOT RUN**.

Equations:
- `posterior odds = prior odds * product(likelihood ratios)`
- `posterior probability = odds / (1 + odds)`
- `binary Shannon entropy = -p log2(p) - (1-p) log2(1-p)`

Model limits:
- Likelihood ratios are hypothetical; raw product assumes conditional independence.
- Repeated dependency groups are flagged, not deduplicated; no unanimity or approval is inferred.

Acceptance status: **SOFTWARE_CHECKS_PASS**. Source-bound numerical, boundary, repeatability and JSON checks are recorded; browser export evidence is separate. This is software acceptance, not scientific or field validation. [Open the full acceptance card](MODEL_REGISTRY.json#council-consensus).

## Registry data

[Machine-readable per-study records and acceptance cards](MODEL_REGISTRY.json). Each card includes input names, declared units and bounds, equation strings, source links, bundled fixture digests, model limits, validation-status unknowns, and exact test-module paths.
