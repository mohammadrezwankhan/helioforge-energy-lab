# Parameters, symbols and units

## Shared energy and money notation

| Symbol / field | Unit / sign | Interpretation |
|---|---|---|
| $L, P, c, d, g^+, g^-, q, u$ | kW; nonnegative | Demand, PV, charge, discharge, import, export, curtailment and unserved demand; `u` is an accounting deficit, not generation |
| $s$, `capacity_kwh` / `batteryKwh` | kWh | Stored energy / nominal capacity; effective capacity can differ in hybrid scenarios |
| $\Delta t$ | h in dispatch; s in physical models | Conversion is explicit; sub-second storage response divides seconds by 3600 |
| $\eta_{rt}$, SOC fractions | dimensionless | Round-trip efficiency; per-direction efficiency is its square root in the energy engines |
| `import_eur_per_kwh`, `importPrice` | EUR/kWh | Short-storage / Terminal price conventions; study `price_eur_mwh` needs a factor of 1000 |
| `peak_charge_eur_per_kw_period` | EUR/kW/represented period | Never silently an annual demand charge |
| `monthly_demand_charge_eur_kw` | EUR/kW/month | Annual optimization applies it to twelve explicit monthly maxima |
| `initial_energy_kwh`, `terminal_energy_kwh` | kWh | Hybrid endpoint inventory; comparison must expose their difference |
| NPV, CAPEX, CFADS, debt service | EUR | Project value, initial investment, cash available for debt service, scheduled repayment; these are different cash-flow bases |
| IRR, discount, degradation | fraction internally; reported IRR percent | A null IRR is not zero; supported sign/bracket behavior is engine-specific |
| DSCR | ratio / null | Undefined without debt service; raw ratios govern covenant flags |
| Weibull $k,\lambda, t, h$ | dimensionless; hours | Supplied shape, scale, age and forecast horizon; no failure-data fit is implied |
| $i_f, i_g, v_c, L_f, L_g, C_f, R_f, R_g$ | A, V, H, F, ohm | dq control plant quantities; voltages are peak values, not automatically RMS |
| $\omega, J,\xi_i,\xi_v$ | rad/s; dimensionless; A·s; V·s | Imposed rotating-frame speed, rotation matrix and PI integrator states |
| `current_kp_v_per_a`, `current_ki_v_per_as` | V/A; V/(A·s) | Inner-loop gains; current integral gain must support the equilibrium/antiwindup formulas |
| `voltage_kp_a_per_v`, `voltage_ki_a_per_vs` | A/V; A/(V·s) | Outer-loop gains; negative gain experiments remain bounded study inputs, not field settings |
| Eigenvalue real/imaginary parts | 1/s | Local continuous-time linearization, classification tolerance ±1e−7 |

Sources: [apps/api/helioforge/schemas.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/schemas.py), [apps/api/helioforge/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/hybrid.py), [apps/api/helioforge/engines/terminal.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/terminal.py), [apps/api/helioforge/engines/control_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py), [apps/api/helioforge/engines/planning_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py).

## Authoritative request models

| Interface | Schema and scope |
|---|---|
| Core storage | `StorageRequest`: 2–168 matching supplied intervals, 0.25–1 h; empty arrays select the fixed 24×1 h demo; positive capacity/power; cyclic endpoint |
| Core finance | `FinanceRequest`: 2–40 years; debt/contract/augmentation timing must fit project life; positive CAPEX and bounded fractions |
| PV | `PVRequest`: 2–50 years, positive capacity/yield, explicit replacement, curtailment and ground coverage |
| Forecast | `ForecastRequest`: 2–40 years, 100–10000 paths, 32-bit unsigned seed, explicit synthetic parameters |
| Drift / reliability / carbon / acquisition | `DriftRequest`, `ReliabilityRequest`, `SustainabilityRequest`, `MARequest`; linked source defines finite ranges and array pairing |
| Hybrid | `HybridRequest`: 2–168 one-hour steps, topology/scenario/control validation, ordered SOC and finite ratings |
| Terminal | Eleven camelCase fields with explicit bounds and boolean rejection; fixed 24-hour horizon |
| Study | `StudyRequest` `{study,inputs}` plus the per-study model, including cross-field validation; numeric catalogue controls do not enumerate the complete schema |

Authoritative sources: [apps/api/helioforge/schemas.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/schemas.py), [apps/api/helioforge/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/hybrid.py), [apps/api/helioforge/engines/terminal.py:94–160](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/terminal.py#L94-L160), [apps/api/helioforge/studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/studies.py). Full study schema/handler links appear in the [atlas](STUDY_MODEL_ATLAS.md).

## Teaching companion controls

The current page selects `grid` with a 24-hour horizon. The table uses the page configuration, including its zero battery-power default; the pure model's fallback differs. Values are finite numbers clamped by the declared control bounds. These illustrative inputs are uncalibrated; source implementation and configuration are in [docs/index.html:165–355](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/index.html#L165-L355).

| Control | Configured default | Unit | Minimum | Maximum | Step |
|---|---:|---|---:|---:|---:|
| `demandKW` | 500 | kW | 100 | 1200 | 25 |
| `solarKW` | 600 | kW | 0 | 1400 | 25 |
| `batteryKW` | 0 | kW | 0 | 300 | 10 |
| `carbonGPerKWh` | 400 | g/kWh | 0 | 800 | 25 |

The fixed `batteryKW` contribution carries no kWh capacity or SOC. Do not transfer these controls to Terminal, the native hourly hybrid screen or either storage optimizer without applying that engine's separate schema and assumptions.

## Declared study-control defaults and UI bounds

The following tables are generated from the actual 59-entry catalogue exported during the pinned native lab. They preserve the catalogue's units and bounds **as UI metadata**. A blank declared unit is shown as “not declared”; no unit is guessed from a field name. Validation models may add parameters, stricter constraints, list lengths, positive-definite matrices, chronological ordering or cross-field feasibility. Those remain authoritative. Structured arrays/records are named without copying thousands of synthetic values; consult the source schema and example catalogue for the complete defaults.

### 01. `hybrid-resonance`

[apps/api/helioforge/engines/engineering_studies.py:52–57](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L52-L57)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| mode_1_hz | 12 | Hz | 1 | 80 | 1 |
| mode_2_hz | 24 | Hz | 1 | 100 | 1 |
| damping_1 | 0.04 | fraction | 0.01 | 0.45 | 0.01 |
| damping_2 | 0.07 | fraction | 0.01 | 0.45 | 0.01 |
| coupling_fraction | 0.15 | fraction | 0 | 0.9 | 0.01 |

### 02. `hybrid-clipping`

[apps/api/helioforge/engines/engineering_studies.py:60–72](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L60-L72)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| pv_dc_kw | 1400 | kW | 0 | 100000 | 10 |
| inverter_ac_kw | 1000 | kW | 1 | 100000 | 10 |
| inverter_efficiency | 0.98 | fraction | 0.01 | 1 | 0.01 |
| battery_capacity_kwh | 500 | kWh | 0 | 100000 | 10 |
| battery_initial_kwh | 100 | kWh | 0 | 100000 | 10 |
| battery_charge_limit_kw | 300 | kW | 0 | 100000 | 10 |

### 03. `hybrid-inertia`

[apps/api/helioforge/engines/engineering_studies.py:75–81](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L75-L81)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| trip_mw | 1000 | MW | 1 | 20000 | 50 |
| system_base_mw | 100000 | MW | 1000 | 2000000 | 1000 |
| inertia_seconds | 4 | s | 0.1 | 30 | 0.1 |
| damping_mw_per_hz | 4000 | MW/Hz | 0 | 500000 | 100 |
| synthetic_inertia_mw_s_per_hz | 10000 | MW·s/Hz | 0 | 200000 | 500 |
| synthetic_inertia_limit_mw | 1000 | MW | 0 | 100000 | 50 |

### 04. `storage-degradation`

[apps/api/helioforge/engines/engineering_studies.py:84–89](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L84-L89)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| years | 8 | years | 0 | 30 | 1 |
| temperature_c | 25 | °C | -20 | 60 | 1 |
| charge_c_rate | 1 | C | 0 | 5 | 0.1 |
| equivalent_full_cycles | 2400 | cycles | 0 | 100000 | 100 |
| depth_of_discharge_fraction | 0.8 | fraction | 0 | 1 | 0.01 |

### 05. `storage-stacking`

[apps/api/helioforge/engines/engineering_studies.py:128–164](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L128-L164)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capacity_kwh | 10000 | kWh | 1 | 1000000 | 100 |
| power_kw | 5000 | kW | 1 | 500000 | 50 |
| round_trip_efficiency | 0.9 | fraction | 0.01 | 1 | 0.01 |
| initial_soc_fraction | 0.5 | fraction | 0 | 1 | 0.01 |
| interval_hours | 1 | h | 0.25 | 4 | 0.25 |
| reserve_duration_hours | 0.25 | h | 0 | 4 | 0.25 |

Structured fields: `price_eur_mwh`, `reserve_up_price_eur_mw_h`, `reserve_down_price_eur_mw_h`, `reserve_up_request_mw`, `reserve_down_request_mw`.

### 06. `storage-synergy`

[apps/api/helioforge/engines/engineering_studies.py:171–180](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L171-L180)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| interval_seconds | 1 | s | 0.1 | 60 | 0.1 |
| filter_time_constant_s | 4 | s | 0 | 600 | 0.5 |
| flywheel_power_kw | 500 | kW | 0 | 100000 | 10 |
| flywheel_energy_kwh | 20 | kWh | 0.1 | 100000 | 1 |
| battery_power_kw | 1000 | kW | 0 | 500000 | 10 |
| battery_energy_kwh | 4000 | kWh | 0.1 | 1000000 | 10 |

Structured fields: `disturbance_kw`.

### 07. `pv-backtracking`

[apps/api/helioforge/engines/engineering_studies.py:195–217](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L195-L217)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| row_pitch_m | 6 | m | 0.1 | 30 | 0.1 |
| module_width_m | 2.4 | m | 0.1 | 10 | 0.1 |
| tracker_axis_azimuth_deg | 0 | ° | 0 | 360 | 1 |
| terrain_slope_deg | 5 | ° | 0 | 30 | 1 |
| terrain_slope_azimuth_deg | 90 | ° | 0 | 360 | 1 |
| backtracking | 1 | 0/1 | 0 | 1 | 1 |

Structured fields: `sun_elevation_deg`, `sun_azimuth_deg`.

### 08. `pv-agrivoltaic`

[apps/api/helioforge/engines/engineering_studies.py:223–252](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L223-L252)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| ground_coverage_ratio | 0.35 | fraction | 0 | 0.9 | 0.01 |
| module_transmission_fraction | 0.08 | fraction | 0 | 0.8 | 0.01 |
| setback_m | 2 | m | 0 | 100 | 0.5 |
| baseline_par_mol_m2_day | 35 | mol/m²/day | 0.1 | 100 | 0.5 |

Structured fields: `land_polygon_m`.

### 09. `pv-albedo`

[apps/api/helioforge/engines/engineering_studies.py:267–278](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L267-L278)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| system_capacity_kwp | 5000 | kWp | 1 | 10000000 | 100 |
| performance_ratio | 0.82 | fraction | 0.01 | 1 | 0.01 |
| bifaciality | 0.7 | fraction | 0 | 1 | 0.01 |
| albedo | 0.25 | fraction | 0 | 1 | 0.01 |
| rear_view_factor | 0.25 | fraction | 0 | 1 | 0.01 |

Structured fields: `front_plane_irradiance_kwh_m2`, `rear_ground_irradiance_kwh_m2`.

### 10. `research-vibration`

[apps/api/helioforge/engines/engineering_studies.py:281–301](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L281-L301)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| sample_rate_hz | 256 | Hz | 128 | 20000 | 1 |
| synthetic_frequency_hz | 24 | Hz | 1 | 10000 | 1 |
| synthetic_drift_hz | 3 | Hz | -5000 | 5000 | 0.1 |
| synthetic_amplitude | 1 | signal unit | 0 | 1000000 | 0.1 |
| noise_std | 0.05 | signal unit | 0 | 1000000 | 0.01 |
| sample_count | 1024 | samples | 64 | 8192 | 64 |

Structured fields: `signal`.

### 11. `research-epd`

[apps/api/helioforge/engines/engineering_studies.py:315–356](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L315-L356)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| include_materials | 1 | 0/1 | 0 | 1 | 1 |
| include_manufacturing | 1 | 0/1 | 0 | 1 | 1 |
| include_transport | 1 | 0/1 | 0 | 1 | 1 |
| include_use | 1 | 0/1 | 0 | 1 | 1 |
| include_end_of_life | 1 | 0/1 | 0 | 1 | 1 |
| include_other | 1 | 0/1 | 0 | 1 | 1 |

Structured fields: `records`.

### 12. `research-scr`

[apps/api/helioforge/engines/engineering_studies.py:359–371](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L359-L371)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| short_circuit_mva | 600 | MVA | 0.1 | 2000000 | 10 |
| plant_mw | 100 | MW | 0.1 | 2000000 | 1 |
| active_power_mw | 80 | MW | 0 | 2000000 | 1 |
| reactive_power_mvar | 20 | Mvar | -2000000 | 2000000 | 1 |
| voltage_kv | 20 | kV | 0.1 | 1000 | 0.1 |
| line_r_ohm | 0.1 | Ω/phase | 0 | 100000 | 0.01 |

### 13. `overview-weather`

[apps/api/helioforge/engines/decision_studies.py:97–111](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L97-L111)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| horizon_years | 10 | years | 1 | 40 | 1 |
| common_shock_fraction | 0.75 | fraction | 0 | 1 | 0.05 |
| seed | 42 | integer | 0 | 4294967295 | 1 |

Structured fields: `assets`.

### 14. `overview-merit`

[apps/api/helioforge/engines/decision_studies.py:172–190](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L172-L190)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| bilateral_weight | 0.4 | fraction | 0 | 1 | 0.05 |
| spot_weight | 0.4 | fraction | 0 | 1 | 0.05 |
| balancing_weight | 0.2 | fraction | 0 | 1 | 0.05 |

Structured fields: `assets`.

### 15. `overview-carbon`

[apps/api/helioforge/engines/decision_studies.py:251–272](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L251-L272)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| static_factor_kgco2e_mwh | 400 | kgCO2e/MWh | 0 | 5000 | 10 |
| sample_hours | 24 | hours | 1 | 8760 | 1 |
| generation_scale | 1 | multiplier | 0.01 | 100 | 0.1 |

Structured fields: `generation_mwh`, `marginal_factors_kgco2e_mwh`.

### 16. `markets-capture`

[apps/api/helioforge/engines/decision_studies.py:346–354](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L346-L354)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| penetration_fraction | 0.4 | fraction | 0 | 1 | 0.01 |
| reference_penetration_fraction | 0.1 | fraction | 0 | 1 | 0.01 |
| cannibalization_slope_eur_mwh | 100 | EUR/MWh per fraction | 0 | 5000 | 5 |

Structured fields: `intervals`.

### 17. `markets-negative`

[apps/api/helioforge/engines/decision_studies.py:390–405](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L390-L405)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| interval_minutes | 15 | minutes | 15 | 15 | 15 |
| suspension_duration_minutes | 60 | minutes | 15 | 10080 | 15 |
| negative_threshold_eur_mwh | 0 | EUR/MWh | -10000 | 0 | 1 |

Structured fields: `prices_eur_mwh`, `country_scenario`.

### 18. `markets-interconnection`

[apps/api/helioforge/engines/decision_studies.py:430–438](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L430-L438)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capacity_mw | 500 | MW | 0 | 1000000 | 10 |
| supply_slope_a_eur_mwh_mw | 0.02 | EUR/MWh per MW | 1e-06 | 1000 | 0.001 |
| supply_slope_b_eur_mwh_mw | 0.02 | EUR/MWh per MW | 1e-06 | 1000 | 0.001 |

Structured fields: `intervals`.

### 19. `forecast-regimes`

[apps/api/helioforge/engines/decision_studies.py:449–480](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L449-L480)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| years | 20 | years | 1 | 40 | 1 |
| paths | 1000 | paths | 20 | 10000 | 100 |
| seed | 42 | integer | 0 | 4294967295 | 1 |

Structured fields: `state_means_eur_mwh`, `state_volatilities_eur_mwh`, `transition_matrix`, `initial_state_probabilities`.

### 20. `forecast-commodities`

[apps/api/helioforge/engines/decision_studies.py:487–517](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L487-L517)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| years | 20 | years | 1 | 40 | 1 |
| paths | 1000 | paths | 20 | 5000 | 100 |
| seed | 42 | integer | 0 | 4294967295 | 1 |

Structured fields: `starting_prices`, `annual_volatilities`, `annual_log_drifts`, `correlation_matrix`.

### 21. `forecast-tail`

[apps/api/helioforge/engines/decision_studies.py:525–538](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L525-L538)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| strike_eur_mwh | 80 | EUR/MWh | 0.01 | 5000 | 1 |
| volume_mwh | 10000 | MWh/year | 0 | 10000000 | 100 |
| years | 10 | years | 1 | 40 | 1 |
| paths | 1500 | paths | 100 | 10000 | 100 |
| seed | 42 | integer | 0 | 4294967295 | 1 |
| annual_volatility | 0.25 | fraction | 0 | 2 | 0.05 |

Structured fields: `histogram_year`.

### 22. `investment-sculpt`

[apps/api/helioforge/engines/decision_studies.py:541–557](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L541-L557)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| target_dscr | 1.3 | ratio | 1 | 5 | 0.05 |
| requested_debt_eur | 1760000 | EUR | 0 | 1000000000 | 10000 |
| discount_rate | 0.08 | fraction | 0 | 0.4 | 0.005 |

Structured fields: `finance_request`.

### 23. `investment-tranches`

[apps/api/helioforge/engines/decision_studies.py:589–607](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L589-L607)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| target_dscr | 1.3 | ratio | 1 | 5 | 0.05 |
| merchant_haircut_fraction | 0.5 | fraction | 0 | 1 | 0.05 |
| interest_rate | 0.055 | fraction | 0 | 0.3 | 0.005 |
| tenor_years | 10 | years | 1 | 40 | 1 |
| contract_years | 10 | years | 0 | 40 | 1 |

Structured fields: `annual_rows`.

### 24. `investment-waterfall`

[apps/api/helioforge/engines/decision_studies.py:610–622](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/decision_studies.py#L610-L622)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capital_eur | 5000000 | EUR | 0 | 1000000000000 | 10000 |
| distribution_pool_eur | 12000000 | EUR | 0 | 1000000000000 | 10000 |
| years | 10 | years | 1 | 50 | 1 |
| preferred_return_rate | 0.08 | fraction | 0 | 0.5 | 0.005 |
| catchup_share | 0.5 | fraction | 0.01 | 1 | 0.05 |
| sponsor_promote_share | 0.2 | fraction | 0 | 0.99 | 0.05 |

### 25. `lessons-duck`

[apps/api/helioforge/engines/workflow_studies.py:114–128](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L114-L128)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| interval_hours | 1 | h | 0.25 | 4 | 0.25 |
| ramp_limit_kw_per_hour | 45 | kW/h | 0 | 10000 | 5 |
| ramp_percentile | 95 | % | 50 | 99.9 | 1 |

Structured fields: `load_kw`, `solar_kw`, `wind_kw`.

### 26. `lessons-blackstart`

[apps/api/helioforge/engines/workflow_studies.py:150–163](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L150-L163)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| gfm_rated_kw | 500 | kW | 1 | 100000 | 10 |
| available_power_fraction | 0.8 | fraction | 0.01 | 1 | 0.01 |
| inrush_budget_kw | 250 | kW | 0 | 100000 | 10 |
| reserve_fraction | 0.15 | fraction | 0 | 0.99 | 0.01 |

Structured fields: `steps`.

### 27. `lessons-hydrogen`

[apps/api/helioforge/engines/workflow_studies.py:171–176](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L171-L176)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| electrolyzer_kwh_per_kg | 52 | kWh/kg H2 | 33.3 | 200 | 0.5 |
| compression_kwh_per_kg | 2 | kWh/kg H2 | 0 | 100 | 0.5 |
| fuel_cell_electric_efficiency | 0.5 | fraction | 0 | 1 | 0.01 |
| hydrogen_lhv_kwh_per_kg | 33.3 | kWh/kg H2 | 33.3 | 33.3 | 0.1 |

Structured fields: `batch`.

### 28. `compare-pareto`

[apps/api/helioforge/engines/workflow_studies.py:247–261](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L247-L261)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| cost_weight | 0.4 | fraction | 0 | 1 | 0.05 |
| service_weight | 0.3 | fraction | 0 | 1 | 0.05 |
| loss_of_load_weight | 0.3 | fraction | 0 | 1 | 0.05 |

Structured fields: `candidates`.

### 29. `compare-dunkelflaute`

[apps/api/helioforge/engines/workflow_studies.py:280–299](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L280-L299)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| energy_capacity_kwh | 500 | kWh | 0.001 | 10000000 | 10 |
| power_limit_kw | 120 | kW | 0.001 | 1000000 | 10 |
| charge_efficiency | 0.94 | fraction | 0.01 | 1 | 0.01 |
| discharge_efficiency | 0.94 | fraction | 0.01 | 1 | 0.01 |
| initial_soc_kwh | 250 | kWh | 0 | 10000000 | 10 |

Structured fields: `load_kw`, `renewable_kw`.

### 30. `compare-thermal`

[apps/api/helioforge/engines/workflow_studies.py:340–347](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L340-L347)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| reference_temperature_c | 25 | °C | -40 | 100 | 1 |
| temperature_factor_per_c | 0.025 | 1/°C | 0 | 0.1 | 0.001 |
| screening_loss_fraction_per_1000_efc | 0.025 | fraction | 0 | 1 | 0.005 |
| years | 1 | year | 1 | 30 | 1 |

Structured fields: `regimes`.

### 31. `pilots-photogrammetry`

[apps/api/helioforge/engines/workflow_studies.py:357–379](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L357-L379)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| coordinate_scale_m | 1 | m/unit | 1e-06 | 100000 | 0.1 |
| reporting_limit_m | 0.05 | m | 0 | 100000 | 0.01 |
| percentile | 95 | % | 50 | 99.9 | 1 |

Structured fields: `design_points_xyz`, `asbuilt_points_xyz`.

### 32. `pilots-dts`

[apps/api/helioforge/engines/workflow_studies.py:402–418](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L402-L418)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| hot_spot_threshold_c | 75 | °C | -50 | 200 | 1 |
| gradient_threshold_c_per_m | 0.25 | °C/m | 0 | 100000 | 0.05 |
| maximum_age_hours | 2 | h | 0 | 100000 | 0.25 |
| current_time_hour | 10 | h | 0 | 1000000 | 1 |

Structured fields: `samples`.

### 33. `pilots-offgas`

[apps/api/helioforge/engines/workflow_studies.py:440–458](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L440-L458)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| temperature_threshold_c | 70 | °C | -100 | 500 | 1 |
| co_threshold_ppm | 35 | ppm | 0.001 | 100000 | 1 |
| voc_threshold_ppm | 5 | ppm | 0.001 | 100000 | 0.5 |
| votes_required | 2 | sensors | 1 | 32 | 1 |

Structured fields: `sensors`.

### 34. `council-debate`

[apps/api/helioforge/engines/workflow_studies.py:518–535](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L518-L535)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capex_eur | 1200000 | EUR | 0 | 1000000000000 | 10000 |
| annual_net_value_eur | 230000 | EUR/year | -1000000000 | 1000000000 | 1000 |
| life_years | 15 | year | 1 | 60 | 1 |
| discount_rate_fraction | 0.08 | fraction | 0 | 0.5 | 0.01 |

Structured fields: `finance_evidence`, `storage_evidence`.

### 35. `council-evidence`

[apps/api/helioforge/engines/workflow_studies.py:627–632](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L627-L632)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| maximum_manifest_age_days | 3650 | days | 0 | 36500 | 30 |
| maximum_tariff_eur_mwh | 2000 | EUR/MWh | 0.001 | 100000 | 10 |
| maximum_warranty_years | 50 | years | 0.001 | 100 | 1 |
| maximum_single_line_nodes | 10000 | nodes | 1 | 1000000 | 100 |

Structured fields: `manifest`.

### 36. `council-consensus`

[apps/api/helioforge/engines/workflow_studies.py:669–681](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/workflow_studies.py#L669-L681)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| prior_probability | 0.35 | probability | 0 | 1 | 0.01 |
| maximum_absolute_log_likelihood_ratio | 4 | log ratio | 0 | 20 | 0.25 |
| evidence_weight | 1 | fraction | 0 | 1 | 0.05 |

Structured fields: `evidence`.

### 37. `storage-annual`

[apps/api/helioforge/engines/toolkit_studies.py:40–62](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L40-L62)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capacity_kwh | 10000 | kWh | 1 | 1000000.0 | 100 |
| power_kw | 5000 | kW | 1 | 1000000.0 | 100 |
| pv_kwp | 5900 | kWp | 0 | 1000000.0 | 100 |
| base_load_kw | 3000 | kW | 0 | 1000000.0 | 100 |
| efficiency | 0.9 | not declared | 0.5 | 1 | 0.01 |
| wear | 0.015 | EUR/kWh | 0 | 1 | 0.001 |
| monthly_peak | 0 | EUR/kW | 0 | 100 | 0.1 |
| export_price | 0.04 | EUR/kWh | 0 | 3 | 0.01 |
| seed | 42 | not declared | 0 | 4294967295 | 1 |

Structured fields: `tariff`, `hourly_load_kw`, `hourly_pv_kw`.

### 38. `pv-sensitivity`

[apps/api/helioforge/engines/toolkit_studies.py:65–69](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L65-L69)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capex_eur_kwp | 650 | EUR/kWp | 100 | 5000 | 10 |
| yield_kwh_kwp | 1350 | kWh/kWp | 400 | 2200 | 10 |
| discount | 0.07 | not declared | 0 | 0.4 | 0.01 |
| opex | 12 | EUR/kWp | 0 | 100 | 1 |

### 39. `pv-reserve`

[apps/api/helioforge/engines/toolkit_studies.py:72–76](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py#L72-L76)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| cost_eur | 1750000 | EUR | 0 | 10000000000.0 | 1000 |
| inflation | 0.02 | not declared | 0 | 0.2 | 0.005 |
| fund_return | 0.03 | not declared | 0 | 0.2 | 0.005 |
| years | 15 | not declared | 1 | 50 | 1 |

### 40. `hybrid-powerflow`

[apps/api/helioforge/engines/physical_studies.py:152–189](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L152-L189)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| base_mva | 100 | MVA | 1 | 1000000 | 1 |
| tolerance_pu | 1e-09 | p.u. | 1e-12 | 0.0001 | 1e-09 |
| max_iterations | 40 | iterations | 2 | 200 | 1 |

Structured fields: `buses`, `branches`.

### 41. `hybrid-switching`

[apps/api/helioforge/engines/physical_studies.py:192–210](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L192-L210)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| switching_enabled | 1 | not declared | 0 | 1 | 1 |
| dc_link_voltage_v | 650 | V | 100 | 2000 | 10 |
| modulation_index | 0.85 | not declared | 0 | 0.95 | 0.01 |
| fundamental_hz | 50 | Hz | 40 | 70 | 1 |
| switching_hz | 2000 | Hz | 100 | 5000 | 100 |
| filter_inductance_h | 0.003 | H | 0.0001 | 0.1 | 0.0001 |
| filter_resistance_ohm | 0.5 | Ω | 0.05 | 20 | 0.05 |
| grid_voltage_rms_v | 230 | V RMS | 10 | 1000 | 1 |
| time_step_s | 2e-05 | s | 1e-06 | 5e-05 | 1e-06 |
| simulation_cycles | 2 | not declared | 1 | 5 | 1 |

### 42. `lessons-energization`

[apps/api/helioforge/engines/physical_studies.py:213–235](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L213-L235)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| source_voltage_rms_v | 230 | V RMS | 1 | 1000 | 1 |
| frequency_hz | 50 | Hz | 40 | 70 | 1 |
| breaker_close_s | 0.005 | s | 0 | 0.1 | 0.0001 |
| resistance_ohm | 5 | Ω | 0.1 | 100 | 0.1 |
| inductance_h | 0.05 | H | 0.001 | 2 | 0.001 |
| capacitance_f | 0.001 | F | 0.0001 | 0.5 | 0.0001 |
| initial_capacitor_voltage_v | 0 | V | -1000 | 1000 | 1 |
| closing_phase_deg | 0 | degrees | -180 | 180 | 1 |
| time_step_s | 2e-05 | s | 1e-06 | 5e-05 | 1e-06 |
| simulation_cycles | 2 | not declared | 1 | 5 | 1 |

### 43. `storage-response`

[apps/api/helioforge/engines/physical_studies.py:238–264](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L238-L264)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| nominal_frequency_hz | 50 | Hz | 45 | 65 | 0.1 |
| deadband_hz | 0.02 | Hz | 0 | 1 | 0.01 |
| droop_kw_per_hz | 2500 | kW/Hz | 0 | 1000000 | 100 |
| power_limit_kw | 1000 | kW | 0 | 1000000 | 10 |
| ramp_kw_per_s | 1000 | kW/s | 0 | 10000000 | 10 |
| capacity_kwh | 2000 | kWh | 1 | 1000000 | 10 |
| initial_soc_fraction | 0.5 | not declared | 0.1 | 0.9 | 0.01 |
| minimum_soc_fraction | 0.1 | not declared | 0 | 0.89 | 0.01 |
| maximum_soc_fraction | 0.9 | not declared | 0.11 | 1 | 0.01 |
| round_trip_efficiency | 0.9 | not declared | 0.5 | 1 | 0.01 |
| interval_s | 0.1 | s | 0.001 | 0.5 | 0.01 |

Structured fields: `frequency_hz`.

### 44. `storage-agingfit`

[apps/api/helioforge/engines/physical_studies.py:286–305](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L286-L305)

No scalar controls are exposed in this catalogue entry.

Structured fields: `observations`.

### 45. `compare-thermalphysics`

[apps/api/helioforge/engines/physical_studies.py:308–328](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L308-L328)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| initial_temperature_c | 25 | °C | -20 | 120 | 1 |
| ambient_temperature_c | 25 | °C | -30 | 80 | 1 |
| thermal_mass_j_per_k | 10000 | J/K | 1000 | 1000000 | 100 |
| cooling_w_per_k | 20 | W/K | 0 | 100000 | 1 |
| activation_energy_kj_mol | 35 | kJ/mol | 0 | 80 | 1 |
| reaction_rate_ref_per_s | 0.002 | 1/s | 0 | 0.005 | 0.0001 |
| reaction_energy_j | 25000 | J | 0 | 10000000 | 100 |
| reference_temperature_c | 25 | °C | -20 | 80 | 1 |
| duration_s | 60 | s | 0.01 | 120 | 1 |
| time_step_s | 0.05 | s | 0.001 | 0.1 | 0.001 |
| termination_temperature_c | 100 | °C | 30 | 150 | 1 |
| reaction_fraction_trip | 0.95 | not declared | 0.01 | 1 | 0.01 |

### 46. `pv-raytrace`

[apps/api/helioforge/engines/physical_studies.py:352–374](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L352-L374)

No scalar controls are exposed in this catalogue entry.

Structured fields: `panel_samples`, `sun_vectors`, `occluder_triangles`.

### 47. `pv-setbacks`

[apps/api/helioforge/engines/physical_studies.py:385–407](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L385-L407)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| setback_m | 2 | m | 0 | 100 | 0.5 |
| pv_cover_fraction | 0.3 | not declared | 0 | 0.9 | 0.01 |
| module_par_transmission_fraction | 0.1 | not declared | 0 | 0.8 | 0.01 |
| baseline_par_mol_m2_day | 35 | mol/m²/day | 0 | 100 | 1 |
| light_half_saturation_mol_m2_day | 12 | mol/m²/day | 0.1 | 100 | 1 |
| photosynthesis_max_g_m2_day | 20 | g/m²/day | 0 | 1000 | 1 |

Structured fields: `parcels`.

### 48. `research-bearing`

[apps/api/helioforge/engines/physical_studies.py:438–467](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L438-L467)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| sample_rate_hz | 256 | Hz | 64 | 20000 | 1 |
| threshold_sigma | 4 | scaled MAD | 1 | 20 | 0.5 |

Structured fields: `training_records`, `heldout_records`.

### 49. `storage-annualopt`

[apps/api/helioforge/engines/planning_studies.py:120–182](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L120-L182)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capacity_kwh | 600 | kWh | 0 | 10000000 | 50 |
| power_kw | 150 | kW | 0 | 100000 | 10 |
| round_trip_efficiency | 0.9 | fraction | 0.01 | 1 | 0.01 |
| monthly_demand_charge_eur_kw | 0 | EUR/kW-month | 0 | 100000 | 1 |
| solver_time_limit_seconds | 4 | s | 0.25 | 10 | 0.25 |

Structured fields: `load_kw`, `pv_kw`, `import_price_eur_kwh`, `export_price_eur_kwh`.

### 50. `compare-reliability`

[apps/api/helioforge/engines/planning_studies.py:185–221](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L185-L221)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| trials | 250 | trials | 20 | 5000 | 10 |
| weather_cv | 0.2 | fraction | 0 | 1 | 0.05 |
| battery_capacity_kwh | 80 | kWh | 0 | 10000000 | 10 |
| battery_power_kw | 40 | kW | 0 | 100000 | 5 |
| generator_failure_probability_per_hour | 0.002 | per hour | 0 | 1 | 0.001 |
| generator_repair_probability_per_hour | 0.08 | per hour | 0.001 | 1 | 0.01 |
| annualization_hours | 8760 | hours | 8760 | 8784 | 24 |

Structured fields: `load_kw`, `renewable_kw`.

### 51. `forecast-cointegration`

[apps/api/helioforge/engines/planning_studies.py:228–255](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L228-L255)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| training_fraction | 0.75 | fraction | 0.5 | 0.9 | 0.05 |
| rank_assumption | 1 | rank | 1 | 1 | 1 |
| lag_count | 1 | lags | 1 | 4 | 1 |
| forecast_steps | 12 | observations | 1 | 48 | 1 |

Structured fields: `gas_price_eur_mwh`, `carbon_price_eur_t`, `power_price_eur_mwh`.

### 52. `forecast-backtest`

[apps/api/helioforge/engines/planning_studies.py:258–280](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L258-L280)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| training_fraction | 0.75 | fraction | 0.5 | 0.9 | 0.05 |
| interval_z_score | 1.96 | z | 0.5 | 4 | 0.05 |

Structured fields: `target_price_eur_mwh`, `gas_price_eur_mwh`, `carbon_price_eur_t`.

### 53. `markets-network`

[apps/api/helioforge/engines/planning_studies.py:313–355](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L313-L355)

No scalar controls are exposed in this catalogue entry.

Structured fields: `zone_names`, `demand_mw`, `generator_capacity_mw`, `generator_cost_eur_mwh`, `lines`.

### 54. `investment-contracts`

[apps/api/helioforge/engines/planning_studies.py:397–428](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L397-L428)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| capex_eur | 8000000 | EUR | 0 | 1000000000000 | 100000 |
| debt_share | 0.55 | fraction | 0 | 0.9 | 0.01 |
| debt_interest_rate | 0.055 | fraction | 0 | 0.5 | 0.005 |
| tax_rate | 0.25 | fraction | 0 | 0.6 | 0.01 |
| dsra_months | 6 | months | 0 | 12 | 1 |
| working_capital_fraction_of_revenue | 0.08 | fraction | 0 | 0.5 | 0.01 |

Structured fields: `operating_years`, `contracts`.

### 55. `lessons-hydrogenaux`

[apps/api/helioforge/engines/planning_studies.py:431–445](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L431-L445)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| hydrogen_kg | 100 | kg | 0 | 1000000 | 10 |
| electrolyzer_kwh_per_kg | 52 | kWh/kg | 33.3 | 200 | 0.5 |
| water_recovery_fraction | 0.8 | fraction | 0.01 | 1 | 0.01 |
| demineralization_kwh_per_m3 | 3 | kWh/m³ | 0 | 10000 | 0.5 |
| fuel_cell_gross_efficiency | 0.52 | fraction | 0 | 0.8 | 0.01 |
| fuel_cell_auxiliary_fraction | 0.06 | fraction | 0 | 0.4 | 0.01 |

### 56. `overview-risk`

[apps/api/helioforge/engines/planning_studies.py:468–469](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L468-L469)

No scalar controls are exposed in this catalogue entry.

Structured fields: `evidence`.

### 57. `pilots-registration`

[apps/api/helioforge/engines/planning_studies.py:491–508](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L491-L508)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| maximum_correspondence_distance_m | 1 | m | 0.0001 | 1000000 | 0.1 |
| trim_fraction | 0.8 | fraction | 0.25 | 1 | 0.05 |
| maximum_iterations | 60 | iterations | 1 | 100 | 1 |
| convergence_tolerance_m | 1e-07 | m | 1e-07 | 0.1 | 1e-07 |

Structured fields: `design_points_xyz`, `survey_points_xyz`.

### 58. `hybrid-controls`

[apps/api/helioforge/engines/control_studies.py:85–123](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L85-L123)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| duration_s | 0.04 | s | 0.001 | 0.12 | 0.001 |
| time_step_s | 5e-05 | s | 1e-05 | 0.0005 | 1e-05 |
| load_step_time_s | 0.004 | s | 0 | 0.12 | 0.001 |
| load_step_a | 8.0 | A | 0 | 500 | 1 |
| filter_inductance_h | 0.0015 | H | 0.0001 | 0.02 | 0.0001 |
| filter_resistance_ohm | 0.08 | Ω | 0.001 | 10 | 0.01 |
| filter_capacitance_f | 2e-05 | F | 1e-06 | 0.001 | 1e-06 |
| grid_inductance_h | 0.001 | H | 0.0001 | 0.1 | 0.0001 |
| grid_resistance_ohm | 0.05 | Ω | 0.001 | 10 | 0.01 |
| grid_angular_frequency_rad_s | 314.1592653589793 | rad/s | 250 | 400 | 1 |
| grid_voltage_peak_v | 325.27 | V peak | 50 | 800 | 1 |
| dc_bus_v | 800 | V | 100 | 1800 | 10 |
| modulation_index_max | 0.95 | ratio | 0.4 | 0.95 | 0.01 |
| current_limit_a | 40 | A | 0.1 | 1000 | 1 |
| current_kp_v_per_a | 1.5 | V/A | 0.001 | 100 | 0.1 |
| current_ki_v_per_as | 1000 | V/(A·s) | 0.01 | 100000 | 10 |
| voltage_kp_a_per_v | 0.2 | A/V | 0.001 | 100 | 0.01 |
| voltage_ki_a_per_vs | 80 | A/(V·s) | 0.01 | 100000 | 10 |
| current_antiwindup_per_s | 100 | s⁻¹ | 0 | 10000 | 10 |
| voltage_antiwindup_per_s | 50 | s⁻¹ | 0 | 10000 | 10 |
| trace_points | 240 | points | 50 | 500 | 10 |

### 59. `research-eigenmodes`

[apps/api/helioforge/engines/control_studies.py:126–146](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L126-L146)

| Field | Default | Unit as declared | UI minimum | UI maximum | UI step |
|---|---|---|---|---|---|
| filter_inductance_h | 0.0015 | H | 0.0001 | 0.02 | 0.0001 |
| filter_resistance_ohm | 0.08 | Ω | 0.001 | 10 | 0.01 |
| filter_capacitance_f | 2e-05 | F | 1e-06 | 0.001 | 1e-06 |
| grid_inductance_h | 0.001 | H | 0.0001 | 0.1 | 0.0001 |
| grid_resistance_ohm | 0.05 | Ω | 0.001 | 10 | 0.01 |
| grid_angular_frequency_rad_s | 314.1592653589793 | rad/s | 250 | 400 | 1 |
| grid_voltage_peak_v | 325.27 | V peak | 50 | 800 | 1 |
| dc_bus_v | 800 | V | 100 | 1800 | 10 |
| modulation_index_max | 0.95 | ratio | 0.4 | 0.95 | 0.01 |
| current_limit_a | 40 | A | 0.1 | 1000 | 1 |
| current_kp_v_per_a | 1.5 | V/A | 0.001 | 100 | 0.1 |
| current_ki_v_per_as | 1000 | V/(A·s) | 0.01 | 100000 | 10 |
| voltage_kp_a_per_v | 0.2 | A/V | 0.001 | 100 | 0.01 |
| voltage_ki_a_per_vs | 80 | A/(V·s) | -100000 | 100000 | 10 |

## Non-equivalences to retain

The same word “battery” appears in several independent models. Terminal camelCase inputs, hybrid kW/kWh fields, short-horizon MILP fields and the teaching companion’s battery-power knob are not interchangeable contracts. `storage-annual` and `storage-annualopt` differ in policy, allowed tariffs, inputs and optimization status. Market labels do not establish live prices; percent display is not a fraction input; dq peak voltage is not RMS; spectral amplitude is not PSD; source SHA-256 is not Git SHA; a workspace key suffix is not its schema version.
