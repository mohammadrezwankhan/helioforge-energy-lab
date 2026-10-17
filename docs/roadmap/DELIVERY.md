# Full-spectrum implementation and audit — 17 October 2026

> Historical 39-study baseline. The [59-study completion ledger](COMPLETION.md) supersedes the implementation gaps and publication boundary below. [Current verification](VERIFICATION.md) records the expanded release.

This release adds 39 independently named experiments across all 12 existing views. Numerical results come from Python, are saved through the local API, and include inputs, equations, source references, model limits and SHA-256 evidence digests. The browser includes reproducible examples for offline inspection and exports. Edited calculations require the local Python app. The original 19 runnable / 17 study-only hybrid architecture boundary remains intact.

This is a research implementation of the roadmap. It does **not** establish a production Astra deployment, scientific calibration, regulatory compliance, WCAG AAA certification or a minimum frame rate on arbitrary hardware. The table below distinguishes working software from those claims.

## Page-by-page delivery

| View | Distinct models | Interactive delivery and boundary |
|---|---|---|
| Command centre | Correlated weather stress, bilateral/spot/balancing merit order, hourly marginal-carbon ledger | Year/observation scrubber, portfolio stress graphic, ±6° pointer tilt with reduced-motion fallback, configurable CAPEX highlighting, JSON-LD/CSV/GeoJSON drawer. Portfolio records remain fictional; GeoJSON geometry is null without source coordinates. |
| Hybrid systems | Coupled-oscillator resonance, DC clipping recovery, reduced swing-equation inertia/RoCoF | Four camera presets, power-dependent particle speed/density and direction, depth-sorted asset kW/SOC labels, wind availability animation. These use asset dispatch, not solved branch flows. No EMT, protection coordination, voltage-field contour solution or certified grid-forming controller is implied. |
| Learning studio | Duck-curve ramps, finite-state black-start exercise, hydrogen energy ledger | 36-lesson hexagonal tree, conceptual switchable breadboard, actual self-check status, formula inspector and locally signed progress. Tier order is guidance, not enforced accreditation. Continuity lighting is not a transient/arc model; the hydrogen ledger explicitly excludes unmodeled auxiliaries. |
| Scenario compare | Comparability-aware Pareto ranking, 336-hour Dunkelflaute MILP, temperature/utilization wear proxy | Pinned-run cards, overlay and context-aware deltas, rotatable radar, user-weighted frontier recommendations. LOLE is a supplied comparable metric, not an estimate inferred from one deterministic trace. Thermal wear is not a validated thermal-runaway prediction. |
| Storage | SEI/plating/fatigue proxies, energy/reserve-headroom MILP, flywheel/battery filtering, separate 8,760-hour dispatch | Actual dispatch interval scrubber, isometric conduit and SOC vessel, 24 editable hourly tariff sliders, complete 8,760-row CSV. Annual data has seasonal and day-to-day variation; the annual dispatch is a disclosed feasible heuristic, not the daily MILP repeated 365 times or a proven annual optimum. Reserve headroom is not sub-second service qualification. |
| PV economics | Slope/backtracking proxy, land/PAR screening, seasonal albedo, 81-cell LCOE sensitivity, repowering reserve | Actual tracker-angle heliodon sketch, selectable sensitivity grid, local-coordinate polygon editor and setback approximation, inflation-linked reserve schedule. No ray-traced terrain/shadow or crop-growth simulation is claimed. |
| Research | Vibration FFT, quantity-factor EPD ledger, SCR voltage proxy | Four-concept prism, source residual/rolling-mean/threshold controls, existing Weibull sandbox and source equations, dossier export. EPD authenticity, acoustic diagnostics and stability certification require independent evidence. The operational-efficiency controls use the existing residual engine. |
| Markets | Capture-price erosion, negative-price sequence exposure, two-zone interconnection clearing | Signed positive/negative price pillars, six editable country tariff stacks and modal, reviewer-supplied dated source timeline, ENTSO-E area links. No live prices, six-zone network solution or effective EEG/Spanish legal entitlement is invented. All legal scenarios remain unverified. |
| Forecast | Markov regimes, correlated gas/carbon/power paths, empirical PPA VaR/CVaR | Quantile tunnels, selected-year histogram, editable parameters, seed/inputs/full-path JSON and CSV exports; original negative-price probabilities are now visible. Correlation is explicitly not statistical cointegration or calibration to current curves. |
| Investment | Debt sculpting, contracted/merchant debt capacity, preference/catch-up/promote waterfall | Covenant solver, signed-scale cashflow bars and DSCR covenant plane, numerical controls and sliders, IC memo. Negative CFADS cannot be cured by relabeling debt service; no approval or elimination of actual default risk is claimed. |
| Pilots | Paired-point calibration errors, DTS gradients/staleness, off-gas vote rules | Drag/drop opens the existing evidence-note form; saving remains explicit. Synthetic telemetry inspector and signed registry. No drone reconstruction, live Modbus acquisition, calibrated warning system or automated field validation is claimed. |
| Council | Rule-based cross-examination, structured evidence manifest checks, dependency-aware Bayesian updates | Transcript replay and filters, actual ECDSA signing/verification, co-signing an inspected identical payload, determination export. Signer keys do not verify human identity/authority. Manifest consistency is not OCR or authenticity verification of arbitrary drawings/warranties. Optional provider adapter remains consent-gated and off by default. |

Every experiment shares an input editor, accessible result table, observation scrubber, provenance details and full exports. Inputs remain distinct by study; changing them hides stale numerical outputs. Invalid files/results do not trigger success states. Camera, chart and decorative geometry are explanatory.

## Corrections to the supplied audit

- Canonical source initially lacked visual changes present only in the standalone preview. Those visuals now live in TypeScript/CSS, and `check-preview.mjs` asserts exact compiled-script and stylesheet parity.
- The old flow diagram mixed an independent PV example with the battery case. Its replacement reads one interval from the storage dispatch, with its own capacity, power, load, PV, grid and tariff values.
- PV degradation reduces generation, not CAPEX. The existing fourth research pillar was construction, not a fully solved grid-integration engine.
- An augmentation-year CFADS deficit is meaningful. It must not be called an artificial annuity failure or removed by a success animation.
- Existing council code already has an optional external adapter. Deterministic local output remains labeled as such; no external agents were invoked by the application in this release.
- SHA-256 alone is not a signature. Browser evidence now uses real ephemeral P-256 keys and verifies signatures. A local completion record is not proof of mastery or independent people.

## Independent review and repairs

A separate read-only reviewer found five concrete defects in the new studies: simultaneous charge/discharge in the 14-day LP, an arbitrary €1T tranche cap, near-zero DTS spacing, unbounded EPD factors and unbounded disturbance amplitudes. All were reproduced and repaired with regression tests. The reviewer reran the counterexamples and signed off only those five findings. The Dunkelflaute optimizer now uses direction binaries; the surplus-only counterexample curtails 3,360 kWh with zero simultaneous operation and terminal SOC closure.

Integration additionally corrected Learning/Compare catalogue route names, HTML numeric-step validity, live editor/JSON synchronization, forecast probability visibility, signed-scale graphics and the reserve formula near zero return using `expm1`/`log1p`. Previously accepted extreme research inputs now fail validation before overflow.

## Mathematical documentation

- [Engineering model notes](ENGINEERING_MODELS.md)
- [Portfolio, market and finance notes](DECISION_MODELS.md)
- [Learning, comparison and workflow notes](WORKFLOW_MODELS.md)
- [Shared input/result contract](CONTRACT.md)
- [Verification record](VERIFICATION.md)

## Publication boundary

This work creates a local signed Git commit and reproducible static package. Git push, public deployment, paid-provider execution and live-service credentials are separate actions and were not performed. The public website therefore does not prove the state of this local branch. Local browser evidence keys are ephemeral; no private keys, runtime databases or external secrets belong in the package.
