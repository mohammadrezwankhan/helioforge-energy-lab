# Study model atlas

This is an accountable map of all **59 registered studies** at the reviewed source, organized in registry order across seven evaluator modules. The registry merges declared catalogue defaults with supplied `inputs`, then validates with the indicated model. A catalogue numeric control is only a UI projection; the full linked schema can expose additional API parameters and constraints. Common envelopes carry inputs, units, equations, limits, sources and a digest. Source references are algorithm context, not independent validation.

[apps/api/helioforge/studies.py:25–101](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/studies.py#L25-L101)

## 01. `hybrid-resonance` — Coupled oscillation modes

Two coupled damped oscillators yield four poles and a normalized response on 96 frequency samples. This is a modal toy system, not a measured inverter impedance or a full plant resonance proof.

**Schema:** `ResonanceInput` · [apps/api/helioforge/engines/engineering_studies.py:52–57](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L52-L57). **Handler:** `_resonance` · [apps/api/helioforge/engines/engineering_studies.py:1082–1141](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1082-L1141).

**Exposed numeric/flag controls:** `mode_1_hz`, `mode_2_hz`, `damping_1`, `damping_2`, `coupling_fraction`.

**Structured inputs:** None in this catalogue entry..

## 02. `hybrid-clipping` — DC clipping recovery

Hourly DC availability, inverter conversion and bounded battery charging quantify clipping recovery. Charging efficiency is fixed at 0.96; it is not a full AC dispatch or optimal daily strategy.

**Schema:** `ClippingInput` · [apps/api/helioforge/engines/engineering_studies.py:60–72](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L60-L72). **Handler:** `_clipping` · [apps/api/helioforge/engines/engineering_studies.py:1144–1204](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1144-L1204).

**Exposed numeric/flag controls:** `pv_dc_kw`, `inverter_ac_kw`, `inverter_efficiency`, `battery_capacity_kwh`, `battery_initial_kwh`, `battery_charge_limit_kw`.

**Structured inputs:** None in this catalogue entry..

## 03. `hybrid-inertia` — Synthetic inertia and RoCoF

A two-state RK4 frequency/governor response uses 0.02 s steps over 15 s, nominal 50 Hz and saturated synthetic inertia. Its RoCoF is a modeled derivative, not EMT or grid-code qualification.

**Schema:** `InertiaInput` · [apps/api/helioforge/engines/engineering_studies.py:75–81](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L75-L81). **Handler:** `_inertia` · [apps/api/helioforge/engines/engineering_studies.py:1207–1302](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1207-L1302).

**Exposed numeric/flag controls:** `trip_mw`, `system_base_mw`, `inertia_seconds`, `damping_mw_per_hz`, `synthetic_inertia_mw_s_per_hz`, `synthetic_inertia_limit_mw`.

**Structured inputs:** None in this catalogue entry..

## 04. `storage-degradation` — Separate battery aging mechanisms

Adds fixed-coefficient SEI, plating and fatigue proxies and caps modeled loss at 0.95. Coefficients are implementation constants (0.006, 0.0002 and 0.000002); displayed operating inputs do not make them fitted or editable material parameters.

**Schema:** `DegradationInput` · [apps/api/helioforge/engines/engineering_studies.py:84–89](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L84-L89). **Handler:** `_degradation` · [apps/api/helioforge/engines/engineering_studies.py:1305–1345](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1305-L1345).

**Exposed numeric/flag controls:** `years`, `temperature_c`, `charge_c_rate`, `equivalent_full_cycles`, `depth_of_discharge_fraction`.

**Structured inputs:** None in this catalogue entry..

## 05. `storage-stacking` — Reserve and arbitrage headroom

MILP shares power between charge, discharge and reserve headroom; reserve MW is converted to kW. Activation energy, cyclic SOC and supplied service prices are explicit. Perfect foresight and request assumptions are not market qualification.

**Schema:** `StackingInput` · [apps/api/helioforge/engines/engineering_studies.py:128–164](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L128-L164). **Handler:** `_stacking` · [apps/api/helioforge/engines/engineering_studies.py:1348–1487](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1348-L1487).

**Exposed numeric/flag controls:** `capacity_kwh`, `power_kw`, `round_trip_efficiency`, `initial_soc_fraction`, `interval_hours`, `reserve_duration_hours`.

**Structured inputs:** `price_eur_mwh`, `reserve_up_price_eur_mw_h`, `reserve_down_price_eur_mw_h`, `reserve_up_request_mw`, `reserve_down_request_mw`.

## 06. `storage-synergy` — Flywheel and battery split-frequency dispatch

A low-pass disturbance split uses alpha=dt/(tau+dt), dispatches flywheel first and battery second, and saturates power/energy with fixed sqrt(0.92) efficiency. It is a frequency-split energy screen, not a controller co-design proof.

**Schema:** `SynergyInput` · [apps/api/helioforge/engines/engineering_studies.py:171–180](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L171-L180). **Handler:** `_synergy` · [apps/api/helioforge/engines/engineering_studies.py:1503–1583](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1503-L1583).

**Exposed numeric/flag controls:** `interval_seconds`, `filter_time_constant_s`, `flywheel_power_kw`, `flywheel_energy_kwh`, `battery_power_kw`, `battery_energy_kwh`.

**Structured inputs:** `disturbance_kw`.

## 07. `pv-backtracking` — Slope-aware tracker backtracking screen

Planar tracker geometry uses local cross-slope and projected sun angles with bounded rotation. It is a simplified source implementation, not a claim of full equivalence to a referenced tracker method.

**Schema:** `BacktrackingInput` · [apps/api/helioforge/engines/engineering_studies.py:195–217](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L195-L217). **Handler:** `_backtracking` · [apps/api/helioforge/engines/engineering_studies.py:1586–1672](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1586-L1672).

**Exposed numeric/flag controls:** `row_pitch_m`, `module_width_m`, `tracker_axis_azimuth_deg`, `terrain_slope_deg`, `terrain_slope_azimuth_deg`, `backtracking`.

**Structured inputs:** `sun_elevation_deg`, `sun_azimuth_deg`.

## 08. `pv-agrivoltaic` — Agrivoltaic PAR and land geometry

Polygon area minus perimeter times setback approximates usable area, then applies a simple coverage/transmission PAR model. This differs from the Shapely buffer in pv-setbacks; no surveyed parcel or calibrated crop yield is inferred.

**Schema:** `AgrivoltaicInput` · [apps/api/helioforge/engines/engineering_studies.py:223–252](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L223-L252). **Handler:** `_agrivoltaic` · [apps/api/helioforge/engines/engineering_studies.py:1675–1708](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1675-L1708).

**Exposed numeric/flag controls:** `ground_coverage_ratio`, `module_transmission_fraction`, `setback_m`, `baseline_par_mol_m2_day`.

**Structured inputs:** `land_polygon_m`.

## 09. `pv-albedo` — Monthly bifacial albedo response

Twelve supplied monthly front/rear irradiance values, performance ratio, bifaciality, albedo and rear view factor yield an energy screen. No annual site-weather calibration is performed.

**Schema:** `AlbedoInput` · [apps/api/helioforge/engines/engineering_studies.py:267–278](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L267-L278). **Handler:** `_albedo` · [apps/api/helioforge/engines/engineering_studies.py:1711–1769](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1711-L1769).

**Exposed numeric/flag controls:** `system_capacity_kwp`, `performance_ratio`, `bifaciality`, `albedo`, `rear_view_factor`.

**Structured inputs:** `front_plane_irradiance_kwh_m2`, `rear_ground_irradiance_kwh_m2`.

## 10. `research-vibration` — Vibration spectrum and drift

Supplied signal or seeded synthetic drifting sinusoid is transformed with Hann coherent-gain amplitude normalization and endpoint treatment. Spectral amplitude is not PSD, diagnosis or a fitted machine health model.

**Schema:** `VibrationInput` · [apps/api/helioforge/engines/engineering_studies.py:281–301](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L281-L301). **Handler:** `_vibration` · [apps/api/helioforge/engines/engineering_studies.py:1785–1845](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1785-L1845).

**Exposed numeric/flag controls:** `sample_rate_hz`, `synthetic_frequency_hz`, `synthetic_drift_hz`, `synthetic_amplitude`, `noise_std`, `sample_count`.

**Structured inputs:** `signal`.

## 11. `research-epd` — Supplier-stage emissions evidence ledger

Sums included life-cycle stages and preserves missing-provenance flags. Duplicate IDs use the first record; a missing provenance field does not automatically exclude an otherwise usable emissions factor. Authenticity remains unverified.

**Schema:** `EPDInput` · [apps/api/helioforge/engines/engineering_studies.py:315–356](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L315-L356). **Handler:** `_epd` · [apps/api/helioforge/engines/engineering_studies.py:1848–1973](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1848-L1973).

**Exposed numeric/flag controls:** `include_materials`, `include_manufacturing`, `include_transport`, `include_use`, `include_end_of_life`, `include_other`.

**Structured inputs:** `records`.

## 12. `research-scr` — Short-circuit strength and voltage drop

Reports SCR=Ssc/P and a linear R/P plus fixed-X/Q voltage-drop proxy in the declared units. It is neither a short-circuit study nor a dynamic stability result.

**Schema:** `SCRInput` · [apps/api/helioforge/engines/engineering_studies.py:359–371](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L359-L371). **Handler:** `_scr` · [apps/api/helioforge/engines/engineering_studies.py:1976–2019](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1976-L2019).

**Exposed numeric/flag controls:** `short_circuit_mva`, `plant_mw`, `active_power_mw`, `reactive_power_mvar`, `voltage_kv`, `line_r_ohm`.

**Structured inputs:** None in this catalogue entry..

## 13. `overview-weather` — Correlated weather stress

Seeded common and independent Gaussian factors create correlated asset weather stress; downside generation is clipped. Common-shock fraction is an assumption, not fitted correlation or outage probability.

**Schema:** `WeatherInput` · [apps/api/helioforge/engines/decision_studies.py:97–111](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L97-L111). **Handler:** `_stress_matrix` · [apps/api/helioforge/engines/decision_studies.py:1182–1254](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1182-L1254).

**Exposed numeric/flag controls:** `horizon_years`, `common_shock_fraction`, `seed`.

**Structured inputs:** `assets`.

## 14. `overview-merit` — Value versus variable cost

Weights bilateral, spot and balancing net values with weights constrained to sum to one. The ordering is a declared value-minus-variable-cost screen, not a market-clearing model.

**Schema:** `MeritInput` · [apps/api/helioforge/engines/decision_studies.py:172–190](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L172-L190). **Handler:** `_merit_matrix` · [apps/api/helioforge/engines/decision_studies.py:1257–1299](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1257-L1299).

**Exposed numeric/flag controls:** `bilateral_weight`, `spot_weight`, `balancing_weight`.

**Structured inputs:** `assets`.

## 15. `overview-carbon` — Hourly versus static emissions

Sums generation times supplied hourly marginal factors and compares a static factor. Sampled hours are not silently annualized and the difference is not a verified carbon credit.

**Schema:** `CarbonInput` · [apps/api/helioforge/engines/decision_studies.py:251–272](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L251-L272). **Handler:** `_carbon` · [apps/api/helioforge/engines/decision_studies.py:1302–1350](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1302-L1350).

**Exposed numeric/flag controls:** `static_factor_kgco2e_mwh`, `sample_hours`, `generation_scale`.

**Structured inputs:** `generation_mwh`, `marginal_factors_kgco2e_mwh`.

## 16. `markets-capture` — Generation-weighted capture price

Computes generation-weighted capture price under an explicit penetration adjustment. Zero generation gives an undefined capture price; the adjustment is a scenario assumption.

**Schema:** `CaptureInput` · [apps/api/helioforge/engines/decision_studies.py:346–354](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L346-L354). **Handler:** `_capture` · [apps/api/helioforge/engines/decision_studies.py:1353–1407](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1353-L1407).

**Exposed numeric/flag controls:** `penetration_fraction`, `reference_penetration_fraction`, `cannibalization_slope_eur_mwh`.

**Structured inputs:** `intervals`.

## 17. `markets-negative` — Negative settlement intervals

Counts 15-minute intervals only when the price is strictly negative and at or below the supplied threshold (`price < 0 and price <= threshold`), then groups the qualifying sequences under the supplied suspension rule. Equality at a negative threshold is included; zero is excluded even when the threshold is zero. Country context remains UNVERIFIED and is not a statement of current law. For threshold −5, prices `[-6, -5, -4, 0]` classify as `[true, true, false, false]`; at threshold 0, `[-1, 0, 1]` classifies as `[true, false, false]`. These are the retained independent synthetic boundary observations, not a newly applied country rule.

**Schema:** `NegativeInput` · [apps/api/helioforge/engines/decision_studies.py:390–405](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L390-L405). **Handler:** `_negative` · [apps/api/helioforge/engines/decision_studies.py:1410–1460](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1410-L1460).

**Exposed numeric/flag controls:** `interval_minutes`, `suspension_duration_minutes`, `negative_threshold_eur_mwh`.

**Structured inputs:** `prices_eur_mwh`, `country_scenario`.

## 18. `markets-interconnection` — Two-zone interconnection

A two-zone flow follows marginal-cost differences divided by combined supply slopes, clipped to link capacity; reported prices come from those curves. It omits real market topology and strategic bidding.

**Schema:** `InterconnectionInput` · [apps/api/helioforge/engines/decision_studies.py:430–438](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L430-L438). **Handler:** `_interconnection` · [apps/api/helioforge/engines/decision_studies.py:1463–1535](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1463-L1535).

**Exposed numeric/flag controls:** `capacity_mw`, `supply_slope_a_eur_mwh_mw`, `supply_slope_b_eur_mwh_mw`.

**Structured inputs:** `intervals`.

## 19. `forecast-regimes` — Three-state price regimes

Seeded paths follow a supplied three-state transition matrix with state-specific means and volatility. The matrix is validated as stochastic, not estimated from market histories.

**Schema:** `RegimesInput` · [apps/api/helioforge/engines/decision_studies.py:449–480](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L449-L480). **Handler:** `_regimes` · [apps/api/helioforge/engines/decision_studies.py:1538–1609](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1538-L1609).

**Exposed numeric/flag controls:** `years`, `paths`, `seed`.

**Structured inputs:** `state_means_eur_mwh`, `state_volatilities_eur_mwh`, `transition_matrix`, `initial_state_probabilities`.

## 20. `forecast-commodities` — Correlated commodity shocks

Correlated geometric random walks use a positive-semidefinite correlation matrix square root and supplied log drifts. This is not a cointegrated commodity-price model.

**Schema:** `CommoditiesInput` · [apps/api/helioforge/engines/decision_studies.py:487–517](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L487-L517). **Handler:** `_commodities` · [apps/api/helioforge/engines/decision_studies.py:1612–1669](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1612-L1669).

**Exposed numeric/flag controls:** `years`, `paths`, `seed`.

**Structured inputs:** `starting_prices`, `annual_volatilities`, `annual_log_drifts`, `correlation_matrix`.

## 21. `forecast-tail` — PPA settlement tail risk

Seeded arithmetic paths price a buyer loss above a fixed strike. VaR uses the higher empirical quantile and CVaR the selected upper loss tail; finite samples and chosen horizon remain explicit.

**Schema:** `TailInput` · [apps/api/helioforge/engines/decision_studies.py:525–538](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L525-L538). **Handler:** `_tail` · [apps/api/helioforge/engines/decision_studies.py:1672–1747](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1672-L1747).

**Exposed numeric/flag controls:** `strike_eur_mwh`, `volume_mwh`, `years`, `paths`, `seed`, `annual_volatility`.

**Structured inputs:** `histogram_year`.

## 22. `investment-sculpt` — DSCR-constrained sculpted debt

Bisection finds debt supportable by CFADS/target DSCR with no negative amortization; nonpositive future CFADS forces earlier repayment. It wraps the shared finance assumptions and is not a lender commitment.

**Schema:** `SculptInput` · [apps/api/helioforge/engines/decision_studies.py:541–557](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L541-L557). **Handler:** `_sculpt` · [apps/api/helioforge/engines/decision_studies.py:1835–1922](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1835-L1922).

**Exposed numeric/flag controls:** `target_dscr`, `requested_debt_eur`, `discount_rate`.

**Structured inputs:** `finance_request`.

## 23. `investment-tranches` — Contracted and merchant tranches

Contracted service capacity expires at contract end; merchant capacity is separately haircutted. Tenor, interest and nonnegative annual inputs govern an indicative debt split.

**Schema:** `TranchesInput` · [apps/api/helioforge/engines/decision_studies.py:589–607](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L589-L607). **Handler:** `_tranches` · [apps/api/helioforge/engines/decision_studies.py:1925–2008](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L1925-L2008).

**Exposed numeric/flag controls:** `target_dscr`, `merchant_haircut_fraction`, `interest_rate`, `tenor_years`, `contract_years`.

**Structured inputs:** `annual_rows`.

## 24. `investment-waterfall` — Capital and promote waterfall

Allocates capital return, compounded preferred return, catch-up and promote while checking conservation to 1e-6. Contract/legal wording and tax treatment are outside the algebra.

**Schema:** `WaterfallInput` · [apps/api/helioforge/engines/decision_studies.py:610–622](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L610-L622). **Handler:** `_waterfall` · [apps/api/helioforge/engines/decision_studies.py:2011–2100](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L2011-L2100).

**Exposed numeric/flag controls:** `capital_eur`, `distribution_pool_eur`, `years`, `preferred_return_rate`, `catchup_share`, `sponsor_promote_share`.

**Structured inputs:** None in this catalogue entry..

## 25. `lessons-duck` — Net load and ramps

Forms net load and interval ramp rates with a null first ramp. The named upward percentile is computed from all ramps, including negative ones; interpret the reported statistic from the actual vector.

**Schema:** `DuckInput` · [apps/api/helioforge/engines/workflow_studies.py:114–128](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L114-L128). **Handler:** `_run_duck` · [apps/api/helioforge/engines/workflow_studies.py:1217–1266](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1217-L1266).

**Exposed numeric/flag controls:** `interval_hours`, `ramp_limit_kw_per_hour`, `ramp_percentile`.

**Structured inputs:** `load_kw`, `solar_kw`, `wind_kw`.

## 26. `lessons-blackstart` — Black-start sequence exercise

Finite-state ordering and per-step power/inrush budgets test a supplied sequence. This is not electromagnetic energization, protection coordination or a field start procedure.

**Schema:** `BlackstartInput` · [apps/api/helioforge/engines/workflow_studies.py:150–163](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L150-L163). **Handler:** `_run_blackstart` · [apps/api/helioforge/engines/workflow_studies.py:1269–1331](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1269-L1331).

**Exposed numeric/flag controls:** `gfm_rated_kw`, `available_power_fraction`, `inrush_budget_kw`, `reserve_fraction`.

**Structured inputs:** `steps`.

## 27. `lessons-hydrogen` — Hydrogen energy pathway

Tracks an explicit hydrogen batch through electrolyzer/compression electricity, 33.3 kWh/kg LHV and fuel-cell efficiency. Useful energy/loss accounting does not supply a process/equipment design.

**Schema:** `HydrogenInput` · [apps/api/helioforge/engines/workflow_studies.py:171–176](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L171-L176). **Handler:** `_run_hydrogen` · [apps/api/helioforge/engines/workflow_studies.py:1334–1390](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1334-L1390).

**Exposed numeric/flag controls:** `electrolyzer_kwh_per_kg`, `compression_kwh_per_kg`, `fuel_cell_electric_efficiency`, `hydrogen_lhv_kwh_per_kg`.

**Structured inputs:** `batch`.

## 28. `compare-pareto` — Comparable-run Pareto screen

Compares supplied candidates only when scenario, sample set, horizon, service basis and sample count match. Supplied LOLE is not recomputed; endpoint energy is visible but not neutralized. Weighted ties follow the implemented ID ordering.

**Schema:** `ParetoInput` · [apps/api/helioforge/engines/workflow_studies.py:247–261](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L247-L261). **Handler:** `_run_pareto` · [apps/api/helioforge/engines/workflow_studies.py:1393–1526](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1393-L1526).

**Exposed numeric/flag controls:** `cost_weight`, `service_weight`, `loss_of_load_weight`.

**Structured inputs:** `candidates`.

## 29. `compare-dunkelflaute` — Fourteen-day storage dispatch

A 336-hour two-stage MILP first minimizes unserved energy, then fixes it within 1e-7 and minimizes curtailment/tiny throughput. Cyclic SOC is enforced; this deterministic stress is not statistical LOLE.

**Schema:** `DunkelflauteInput` · [apps/api/helioforge/engines/workflow_studies.py:280–299](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L280-L299). **Handler:** `_run_dunkelflaute` · [apps/api/helioforge/engines/workflow_studies.py:1529–1687](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1529-L1687).

**Exposed numeric/flag controls:** `energy_capacity_kwh`, `power_limit_kw`, `charge_efficiency`, `discharge_efficiency`, `initial_soc_kwh`.

**Structured inputs:** `load_kw`, `renewable_kw`.

## 30. `compare-thermal` — Thermal and cycle-wear screen

Accumulates temperature-weighted cycle exposure and an illustrative screening loss index. It is not calibrated capacity fade, a heat equation or a safety prediction.

**Schema:** `ThermalInput` · [apps/api/helioforge/engines/workflow_studies.py:340–347](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L340-L347). **Handler:** `_run_thermal` · [apps/api/helioforge/engines/workflow_studies.py:1690–1741](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1690-L1741).

**Exposed numeric/flag controls:** `reference_temperature_c`, `temperature_factor_per_c`, `screening_loss_fraction_per_1000_efc`, `years`.

**Structured inputs:** `regimes`.

## 31. `pilots-photogrammetry` — Paired as-built geometry check

Compares paired-by-index design/as-built XYZ coordinates without alignment. Empty observations yield undefined statistics; it does not reconstruct images or solve unpaired registration.

**Schema:** `PhotogrammetryInput` · [apps/api/helioforge/engines/workflow_studies.py:357–379](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L357-L379). **Handler:** `_run_photogrammetry` · [apps/api/helioforge/engines/workflow_studies.py:1744–1803](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1744-L1803).

**Exposed numeric/flag controls:** `coordinate_scale_m`, `reporting_limit_m`, `percentile`.

**Structured inputs:** `design_points_xyz`, `asbuilt_points_xyz`.

## 32. `pilots-dts` — Distributed temperature profile

Checks fresh nonmissing temperatures and gradients between adjacent original observations; gaps are not filled. Threshold equality triggers the relevant flag, and sensor/threshold validity remains external.

**Schema:** `DtsInput` · [apps/api/helioforge/engines/workflow_studies.py:402–418](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L402-L418). **Handler:** `_run_dts` · [apps/api/helioforge/engines/workflow_studies.py:1806–1904](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1806-L1904).

**Exposed numeric/flag controls:** `hot_spot_threshold_c`, `gradient_threshold_c_per_m`, `maximum_age_hours`, `current_time_hour`.

**Structured inputs:** `samples`.

## 33. `pilots-offgas` — Hypothetical multisensor warning vote

Each sensor contributes at most one vote when any present channel meets its threshold; votes are combined against the requested count. This is hypothetical multisensor logic, not a commissioned alarm.

**Schema:** `OffgasInput` · [apps/api/helioforge/engines/workflow_studies.py:440–458](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L440-L458). **Handler:** `_run_offgas` · [apps/api/helioforge/engines/workflow_studies.py:1907–1975](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1907-L1975).

**Exposed numeric/flag controls:** `temperature_threshold_c`, `co_threshold_ppm`, `voc_threshold_ppm`, `votes_required`.

**Structured inputs:** `sensors`.

## 34. `council-debate` — Finance versus storage debate

Produces deterministic finance/storage evidence comparisons and a flat-value NPV calculation. The transcript is not external model execution or expert sign-off.

**Schema:** `DebateInput` · [apps/api/helioforge/engines/workflow_studies.py:518–535](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L518-L535). **Handler:** `_run_debate` · [apps/api/helioforge/engines/workflow_studies.py:1978–2032](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L1978-L2032).

**Exposed numeric/flag controls:** `capex_eur`, `annual_net_value_eur`, `life_years`, `discount_rate_fraction`.

**Structured inputs:** `finance_evidence`, `storage_evidence`.

## 35. `council-evidence` — Structured evidence manifest

Inspects a structured manifest for format, ranges, timestamps and required contents. It is not OCR, source authenticity, legal review or a trusted signature service.

**Schema:** `ManifestInput` · [apps/api/helioforge/engines/workflow_studies.py:627–632](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L627-L632). **Handler:** `_run_manifest` · [apps/api/helioforge/engines/workflow_studies.py:2035–2112](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L2035-L2112).

**Exposed numeric/flag controls:** `maximum_manifest_age_days`, `maximum_tariff_eur_mwh`, `maximum_warranty_years`, `maximum_single_line_nodes`.

**Structured inputs:** `manifest`.

## 36. `council-consensus` — Bayesian evidence toy model

Updates clipped weighted log odds from supplied likelihood ratios. Dependency groups are flagged but not statistically deduplicated; prior zero/one remains absorbing. It is an uncalibrated Bayesian toy model.

**Schema:** `ConsensusInput` · [apps/api/helioforge/engines/workflow_studies.py:669–681](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L669-L681). **Handler:** `_run_consensus` · [apps/api/helioforge/engines/workflow_studies.py:2128–2206](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L2128-L2206).

**Exposed numeric/flag controls:** `prior_probability`, `maximum_absolute_log_likelihood_ratio`, `evidence_weight`.

**Structured inputs:** `evidence`.

## 37. `storage-annual` — 8760-hour dispatch and tariff builder

A seeded/supplied 8760-hour tariff policy with 50% cyclic SOC, explicit hourly sum and monthly peaks. Import tariffs are nonnegative and export cannot exceed the minimum import tariff; this is not annual MILP optimality.

**Schema:** `Annual` · [apps/api/helioforge/engines/toolkit_studies.py:40–62](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L40-L62). **Handler:** `annual` · [apps/api/helioforge/engines/toolkit_studies.py:221–328](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L221-L328).

**Exposed numeric/flag controls:** `capacity_kwh`, `power_kw`, `pv_kwp`, `base_load_kw`, `efficiency`, `wear`, `monthly_peak`, `export_price`, `seed`.

**Structured inputs:** `tariff`, `hourly_load_kw`, `hourly_pv_kw`.

## 38. `pv-sensitivity` — LCOE contour sensitivity

Evaluates the actual discounted PV engine on a 9 by 9 CAPEX/yield grid. Other lifetime/replacement assumptions remain those of the parent engine; a finite contour is not global uncertainty attribution.

**Schema:** `Sensitivity` · [apps/api/helioforge/engines/toolkit_studies.py:65–69](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L65-L69). **Handler:** `run` · [apps/api/helioforge/engines/toolkit_studies.py:331–409](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L331-L409).

**Exposed numeric/flag controls:** `capex_eur_kwp`, `yield_kwh_kwp`, `discount`, `opex`.

**Structured inputs:** None in this catalogue entry..

## 39. `pv-reserve` — Inverter repowering reserve

Inflates a future replacement target and uses an end-of-year equal-deposit annuity, with a zero-return branch and stable expm1/log1p calculation. Returns are supplied assumptions, not a guarantee.

**Schema:** `Reserve` · [apps/api/helioforge/engines/toolkit_studies.py:72–76](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L72-L76). **Handler:** `run` · [apps/api/helioforge/engines/toolkit_studies.py:331–409](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L331-L409).

**Exposed numeric/flag controls:** `cost_eur`, `inflation`, `fund_return`, `years`.

**Structured inputs:** None in this catalogue entry..

## 40. `hybrid-powerflow` — Balanced AC nodal power flow

One slack and 1–11 PQ buses form a balanced complex-Ybus polar root problem. Solver success, residual and voltage bounds are checked; branch ratings warn rather than constrain dispatch.

**Schema:** `PowerFlowInput` · [apps/api/helioforge/engines/physical_studies.py:152–189](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L152-L189). **Handler:** `_powerflow` · [apps/api/helioforge/engines/physical_studies.py:1006–1139](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1006-L1139).

**Exposed numeric/flag controls:** `base_mva`, `tolerance_pu`, `max_iterations`.

**Structured inputs:** `buses`, `branches`.

## 41. `hybrid-switching` — PWM inverter/filter transient

Ideal single-phase PWM or averaged voltage drives an RL branch using exponential within-step response to sampled forcing. A half-step comparison screens integration error; semiconductor losses and detailed control are absent.

**Schema:** `SwitchingInput` · [apps/api/helioforge/engines/physical_studies.py:192–210](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L192-L210). **Handler:** `_switching` · [apps/api/helioforge/engines/physical_studies.py:1175–1226](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1175-L1226).

**Exposed numeric/flag controls:** `switching_enabled`, `dc_link_voltage_v`, `modulation_index`, `fundamental_hz`, `switching_hz`, `filter_inductance_h`, `filter_resistance_ohm`, `grid_voltage_rms_v`, `time_step_s`, `simulation_cycles`.

**Structured inputs:** None in this catalogue entry..

## 42. `lessons-energization` — Timed LRC energization transient

RK4 integrates the ideal RLC state with breaker time inserted in the grid; work/loss use trapezoidal quadrature. Signed capacitor voltage and sampled extrema are retained; a coarse/refined peak comparison is not protection validation.

**Schema:** `EnergizationInput` · [apps/api/helioforge/engines/physical_studies.py:213–235](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L213-L235). **Handler:** `_energization` · [apps/api/helioforge/engines/physical_studies.py:1286–1327](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1286-L1327).

**Exposed numeric/flag controls:** `source_voltage_rms_v`, `frequency_hz`, `breaker_close_s`, `resistance_ohm`, `inductance_h`, `capacitance_f`, `initial_capacitor_voltage_v`, `closing_phase_deg`, `time_step_s`, `simulation_cycles`.

**Structured inputs:** None in this catalogue entry..

## 43. `storage-response` — Sub-second frequency droop response

Frequency deviation outside a deadband requests droop power, then ramp/power/SOC constraints apply with seconds-to-hours conversion. Terminal SOC is free; this is a discrete energy-response screen.

**Schema:** `StorageResponseInput` · [apps/api/helioforge/engines/physical_studies.py:238–264](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L238-L264). **Handler:** `_storage_response` · [apps/api/helioforge/engines/physical_studies.py:1330–1400](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1330-L1400).

**Exposed numeric/flag controls:** `nominal_frequency_hz`, `deadband_hz`, `droop_kw_per_hz`, `power_limit_kw`, `ramp_kw_per_s`, `capacity_kwh`, `initial_soc_fraction`, `minimum_soc_fraction`, `maximum_soc_fraction`, `round_trip_efficiency`, `interval_s`.

**Structured inputs:** `frequency_hz`.

## 44. `storage-agingfit` — Capacity-fade coefficient fit

Bounded least squares fits two coefficients in 1−a(N/1000)exp[b(T−25)]. Every fifth observation is held out. Synthetic/unverified records and residual summaries do not establish a chemistry model.

**Schema:** `AgingFitInput` · [apps/api/helioforge/engines/physical_studies.py:286–305](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L286-L305). **Handler:** `_aging_fit` · [apps/api/helioforge/engines/physical_studies.py:1403–1488](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1403-L1488).

**Exposed numeric/flag controls:** None; use structured input records..

**Structured inputs:** `observations`.

## 45. `compare-thermalphysics` — Lumped thermal reaction screen

Two-state Arrhenius thermal/reaction ODE uses RK45, event termination and a half-max-step comparison; rate evaluation clips temperature/exponent. The model is uncalibrated and is not a battery safety system.

**Schema:** `ThermalInput` · [apps/api/helioforge/engines/physical_studies.py:308–328](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L308-L328). **Handler:** `_thermal` · [apps/api/helioforge/engines/physical_studies.py:1549–1587](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1549-L1587).

**Exposed numeric/flag controls:** `initial_temperature_c`, `ambient_temperature_c`, `thermal_mass_j_per_k`, `cooling_w_per_k`, `activation_energy_kj_mol`, `reaction_rate_ref_per_s`, `reaction_energy_j`, `reference_temperature_c`, `duration_s`, `time_step_s`, `termination_temperature_c`, `reaction_fraction_trip`.

**Structured inputs:** None in this catalogue entry..

## 46. `pv-raytrace` — Panel-sample ray-triangle shading

Möller–Trumbore half-line intersection marks shading at supplied panel samples and sums incident beam energy. Geometry samples, direct-beam-only assumptions and absent electrical conversion limit yield interpretation.

**Schema:** `RayTraceInput` · [apps/api/helioforge/engines/physical_studies.py:352–374](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L352-L374). **Handler:** `_raytrace` · [apps/api/helioforge/engines/physical_studies.py:1613–1688](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1613-L1688).

**Exposed numeric/flag controls:** None; use structured input records..

**Structured inputs:** `panel_samples`, `sun_vectors`, `occluder_triangles`.

## 47. `pv-setbacks` — Parcel setbacks and crop-light screen

Shapely negative buffers retain parcel holes with mitre joins; remaining area feeds an illustrative saturating crop-light response. It does not establish legal setbacks, surveying accuracy or crop yield.

**Schema:** `SetbackInput` · [apps/api/helioforge/engines/physical_studies.py:385–407](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L385-L407). **Handler:** `_setbacks` · [apps/api/helioforge/engines/physical_studies.py:1691–1748](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1691-L1748).

**Exposed numeric/flag controls:** `setback_m`, `pv_cover_fraction`, `module_par_transmission_fraction`, `baseline_par_mol_m2_day`, `light_half_saturation_mol_m2_day`, `photosynthesis_max_g_m2_day`.

**Structured inputs:** `parcels`.

## 48. `research-bearing` — Bearing spectrum envelope comparison

Training median/MAD amplitude baselines use a positive floor and classify held-out spectral envelopes. The threshold is a statistical screen, not fault identity, calibrated probability or remaining life.

**Schema:** `BearingInput` · [apps/api/helioforge/engines/physical_studies.py:438–467](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L438-L467). **Handler:** `_bearing` · [apps/api/helioforge/engines/physical_studies.py:1758–1835](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1758-L1835).

**Exposed numeric/flag controls:** `sample_rate_hz`, `threshold_sigma`.

**Structured inputs:** `training_records`, `heldout_records`.

## 49. `storage-annualopt` — Full-year storage optimization

Full 8760-hour MILP with cyclic SOC, monthly peaks and proof-status/residual checks. Confirmed negative-export analytical baseline flaw can report savings even with zero battery; do not attribute that difference to storage.

**Schema:** `AnnualStorageInput` · [apps/api/helioforge/engines/planning_studies.py:120–182](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L120-L182). **Handler:** `_annual_storage` · [apps/api/helioforge/engines/planning_studies.py:1087–1335](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1087-L1335).

**Exposed numeric/flag controls:** `capacity_kwh`, `power_kw`, `round_trip_efficiency`, `monthly_demand_charge_eur_kw`, `solver_time_limit_seconds`.

**Structured inputs:** `load_kw`, `pv_kw`, `import_price_eur_kwh`, `export_price_eur_kwh`.

## 50. `compare-reliability` — Chronological reliability ensemble

Seeded chronological weather/generator/storage trials produce annualized loss-of-load statistics and bounded confidence intervals. Finite samples, input assumptions and free trial endpoints remain material; zero events is not zero risk.

**Schema:** `ReliabilityInput` · [apps/api/helioforge/engines/planning_studies.py:185–221](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L185-L221). **Handler:** `_reliability` · [apps/api/helioforge/engines/planning_studies.py:1348–1488](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1348-L1488).

**Exposed numeric/flag controls:** `trials`, `weather_cv`, `battery_capacity_kwh`, `battery_power_kw`, `generator_failure_probability_per_hour`, `generator_repair_probability_per_hour`, `annualization_hours`.

**Structured inputs:** `load_kw`, `renewable_kw`.

## 51. `forecast-cointegration` — Rank-assumed energy-price VECM

Fits a rank-assumed energy-price relation and short-run lag model using the training segment, then recursively forecasts a fixed-origin holdout. It does not perform a Johansen rank test or prove cointegration.

**Schema:** `CointegrationInput` · [apps/api/helioforge/engines/planning_studies.py:228–255](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L228-L255). **Handler:** `_cointegration` · [apps/api/helioforge/engines/planning_studies.py:1542–1633](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1542-L1633).

**Exposed numeric/flag controls:** `training_fraction`, `rank_assumption`, `lag_count`, `forecast_steps`.

**Structured inputs:** `gas_price_eur_mwh`, `carbon_price_eur_t`, `power_price_eur_mwh`.

## 52. `forecast-backtest` — Chronological price forecast backtest

Chronological ARX(1) fitting uses prior data; one-step holdout predictions use observed previous values/drivers. Training-residual intervals exclude full parameter uncertainty; rank deficiency is explicitly flagged.

**Schema:** `BacktestInput` · [apps/api/helioforge/engines/planning_studies.py:258–280](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L258-L280). **Handler:** `_backtest` · [apps/api/helioforge/engines/planning_studies.py:1636–1751](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1636-L1751).

**Exposed numeric/flag controls:** `training_fraction`, `interval_z_score`.

**Structured inputs:** `target_price_eur_mwh`, `gas_price_eur_mwh`, `carbon_price_eur_t`.

## 53. `markets-network` — Six-zone DC optimal power flow

Six-zone linear DC OPF has bounded generation, line flows and angles with a fixed reference; balance duals supply model prices. This is not observed European market clearing or an AC security assessment.

**Schema:** `NetworkInput` · [apps/api/helioforge/engines/planning_studies.py:313–355](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L313-L355). **Handler:** `_network` · [apps/api/helioforge/engines/planning_studies.py:1754–1870](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1754-L1870).

**Exposed numeric/flag controls:** None; use structured input records..

**Structured inputs:** `zone_names`, `demand_mw`, `generator_capacity_mw`, `generator_cost_eur_mwh`, `lines`.

## 54. `investment-contracts` — Contract, tax, and reserve cash flows

Dated generation/contracts, floor prices, merchant sales, debt, taxes, loss carry-forward, working capital and DSRA form explicit cash-flow ledgers. It has a separate bracketed IRR implementation and no jurisdictional/legal guarantee.

**Schema:** `ContractInput` · [apps/api/helioforge/engines/planning_studies.py:397–428](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L397-L428). **Handler:** `_contracts` · [apps/api/helioforge/engines/planning_studies.py:1906–2117](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1906-L2117).

**Exposed numeric/flag controls:** `capex_eur`, `debt_share`, `debt_interest_rate`, `tax_rate`, `dsra_months`, `working_capital_fraction_of_revenue`.

**Structured inputs:** `operating_years`, `contracts`.

## 55. `lessons-hydrogenaux` — Hydrogen auxiliary energy ledger

Adds ideal-gas isothermal compression, demineralized water, fuel-cell auxiliaries and separate heat/electric ledgers to an LHV basis. Equipment-specific efficiencies and constraints remain assumptions.

**Schema:** `HydrogenInput` · [apps/api/helioforge/engines/planning_studies.py:431–445](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L431-L445). **Handler:** `_hydrogen` · [apps/api/helioforge/engines/planning_studies.py:2120–2251](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L2120-L2251).

**Exposed numeric/flag controls:** `hydrogen_kg`, `electrolyzer_kwh_per_kg`, `water_recovery_fraction`, `demineralization_kwh_per_m3`, `fuel_cell_gross_efficiency`, `fuel_cell_auxiliary_fraction`.

**Structured inputs:** None in this catalogue entry..

## 56. `overview-risk` — Portfolio evidence and threshold screen

Checks supplied portfolio evidence and configured risk thresholds; provenance presence is not authenticity or adequacy. It does not discover missing external asset facts.

**Schema:** `RiskInput` · [apps/api/helioforge/engines/planning_studies.py:468–469](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L468-L469). **Handler:** `_risk` · [apps/api/helioforge/engines/planning_studies.py:2254–2318](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L2254-L2318).

**Exposed numeric/flag controls:** None; use structured input records..

**Structured inputs:** `evidence`.

## 57. `pilots-registration` — Unpaired point-cloud registration

Trimmed nearest-neighbor ICP with Kabsch rigid updates starts from centroid translation, disallows scale and requires sufficient rank. Small RMSE change is local convergence, not a global alignment certificate; photos are not processed.

**Schema:** `RegistrationInput` · [apps/api/helioforge/engines/planning_studies.py:491–508](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L491-L508). **Handler:** `_registration` · [apps/api/helioforge/engines/planning_studies.py:2358–2486](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L2358-L2486).

**Exposed numeric/flag controls:** `maximum_correspondence_distance_m`, `trim_fraction`, `maximum_iterations`, `convergence_tolerance_m`.

**Structured inputs:** `design_points_xyz`, `survey_points_xyz`.

## 58. `hybrid-controls` — Averaged inverter control response

Ten-state balanced dq LCL plant with cascaded PI, vector saturation, back-calculation antiwindup and RK4/half-step comparison. Grid angle is imposed; no PLL, DC-link, switching or field tuning claim.

**Schema:** `HybridControlsInput` · [apps/api/helioforge/engines/control_studies.py:85–123](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L85-L123). **Handler:** `_hybrid_controls` · [apps/api/helioforge/engines/control_studies.py:581–672](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L581-L672).

**Exposed numeric/flag controls:** `duration_s`, `time_step_s`, `load_step_time_s`, `load_step_a`, `filter_inductance_h`, `filter_resistance_ohm`, `filter_capacitance_f`, `grid_inductance_h`, `grid_resistance_ohm`, `grid_angular_frequency_rad_s`, `grid_voltage_peak_v`, `dc_bus_v`, `modulation_index_max`, `current_limit_a`, `current_kp_v_per_a`, `current_ki_v_per_as`, `voltage_kp_a_per_v`, `voltage_ki_a_per_vs`, `current_antiwindup_per_s`, `voltage_antiwindup_per_s`, `trace_points`.

**Structured inputs:** None in this catalogue entry..

## 59. `research-eigenmodes` — Closed-loop inverter eigenmodes

Central finite-difference Jacobian at the declared ten-state equilibrium; eigenvalue real-part threshold ±1e-7 defines stable/unstable/marginal. This is local linear classification, not nonlinear/global stability or measured plant validation.

**Schema:** `EigenmodesInput` · [apps/api/helioforge/engines/control_studies.py:126–146](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L126-L146). **Handler:** `_research_eigenmodes` · [apps/api/helioforge/engines/control_studies.py:675–785](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L675-L785).

**Exposed numeric/flag controls:** `filter_inductance_h`, `filter_resistance_ohm`, `filter_capacitance_f`, `grid_inductance_h`, `grid_resistance_ohm`, `grid_angular_frequency_rad_s`, `grid_voltage_peak_v`, `dc_bus_v`, `modulation_index_max`, `current_limit_a`, `current_kp_v_per_a`, `current_ki_v_per_as`, `voltage_kp_a_per_v`, `voltage_ki_a_per_vs`.

**Structured inputs:** None in this catalogue entry..

## Verification and evolution

The established asset check recomputed all 59 bundled cases on 2026-11-19. Its 2473 numeric roundoff differences (maximum approximately 1.3281e−6) passed the existing comparison policies; runtime duration is explicitly observational rather than deterministic. Passing those fixed examples does not exhaust all valid inputs or remove the annual-comparator and IRR findings. Refer to the [evidence ledger](../maintainer/VERIFICATION_EVIDENCE_LEDGER.md) and [roadmap](../../ROADMAP.md).
