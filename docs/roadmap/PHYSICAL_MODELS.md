# Advanced physical studies

**Status:** executable bounded research screens with synthetic examples. The equations and software paths have internal hand-case and invariant tests. No model here has been calibrated against a real plant, cell, crop, sensor, mesh, or operator record.

The module exports `STUDIES`, `INPUT_MODELS`, and `run(study_id, inputs)`. Its result follows `docs/roadmap/CONTRACT.md`: `metrics`, `series`, `table`, `details`, and `warnings`, with JSON-finite numeric results. Numeric parameters belong to `fields`; uploaded or structured arrays belong to `data_fields`. The parent integration still needs to register `physical_studies` in `helioforge/studies.py`. The runtime dependency `shapely==2.1.2` has been added by the integration owner for inward polygon buffers that preserve holes and multipolygons.

## Studies and renderer keys

The current source uses these exact IDs, pages, input names, chart series, and `details` keys. Scalar names are form controls; names in parentheses describe records inside the associated data array.

| ID / page | Inputs | Series names | `details` keys |
|---|---|---|---|
| `hybrid-powerflow` / `hybrid` | `base_mva`, `tolerance_pu`, `max_iterations`; `buses` (`bus_id`, `kind`, `p_load_mw`, `q_load_mvar`, `voltage_pu`, `angle_deg`); `branches` (`from_bus`, `to_bus`, `r_pu`, `x_pu`, `b_pu`, `rate_mva`) | `Bus voltage magnitude`, `Bus voltage angle` | `converged`, `solver`, `solver_function_evaluations`, `residual_max_pu`, `base_mva`, `buses`, `branches`, `slack_bus_id` |
| `hybrid-switching` / `hybrid` | `switching_enabled` (0 averaged / 1 PWM), `dc_link_voltage_v`, `modulation_index`, `fundamental_hz`, `switching_hz`, `filter_inductance_h`, `filter_resistance_ohm`, `grid_voltage_rms_v`, `time_step_s`, `simulation_cycles` | `Switching filter current` or `Averaged filter current`, `Inverter voltage` | `mode`, `internal_time_step_s`, `internal_steps`, `convergence_relative_error`, `switching_ripple_rms_a`, `switching_enabled` |
| `lessons-energization` / `lessons` | `source_voltage_rms_v`, `frequency_hz`, `breaker_close_s`, `resistance_ohm`, `inductance_h`, `capacitance_f`, `initial_capacitor_voltage_v`, `closing_phase_deg`, `time_step_s`, `simulation_cycles` | `Series current`, `Inductor energy`, `Capacitor energy`, `Source work`, `Resistor loss` | `breaker_close_s`, `closing_phase_deg`, `coarse_peak_current_a`, `refined_peak_current_a`, `convergence_relative_error`, `energy_balance_residual_j`, `internal_samples` |
| `storage-response` / `storage` | `nominal_frequency_hz`, `deadband_hz`, `droop_kw_per_hz`, `power_limit_kw`, `ramp_kw_per_s`, `capacity_kwh`, `initial_soc_fraction`, `minimum_soc_fraction`, `maximum_soc_fraction`, `round_trip_efficiency`, `interval_s`; `frequency_hz` samples | `Storage response power`, `Battery stored energy` | `nominal_frequency_hz`, `interval_s`, `round_trip_efficiency`, `integrated_dt_hours` |
| `storage-agingfit` / `storage` | `observations` (`cycle_count`, `temperature_c`, `capacity_fraction`) | `Measured capacity`, `Fitted capacity` | `dataset_label`, `training_count`, `heldout_count`, `training_indices_zero_based`, `heldout_indices_zero_based`, `solver`, `fit_success` |
| `compare-thermalphysics` / `compare` | `initial_temperature_c`, `ambient_temperature_c`, `thermal_mass_j_per_k`, `cooling_w_per_k`, `activation_energy_kj_mol`, `reference_temperature_c`, `reaction_rate_ref_per_s`, `reaction_energy_j`, `duration_s`, `time_step_s`, `termination_temperature_c`, `reaction_fraction_trip` | `Lumped temperature`, `Reaction progress` | `termination_reason`, `termination_time_s`, `final_temperature_c`, `final_reaction_fraction`, `convergence_relative_error`, `heat_released_j` |
| `pv-raytrace` / `pv` | `panel_samples` (`position_m`, `normal`, `area_m2`); `sun_vectors` (`direction`, `dni_w_m2`, `duration_h`); `occluder_triangles` (three 3-D points per triangle) | `Direct-beam energy by sun sample` | `panel_sample_count`, `sun_sample_count`, `triangle_count`, `energy_wh`, `occluder_algorithm` |
| `pv-setbacks` / `pv` | `setback_m`, `pv_cover_fraction`, `module_par_transmission_fraction`, `baseline_par_mol_m2_day`, `light_half_saturation_mol_m2_day`, `photosynthesis_max_g_m2_day`; `parcels` (`exterior_m`, `holes_m`) | No time series; parcel records and metrics are shown as table/metrics | `setback_m`, `usable_geometry_type`, `usable_component_count`, `holes_preserved`, `pv_cover_fraction`, `module_par_transmission_fraction`, `crop_dli_mol_m2_day`, `photosynthesis_response_g_m2_day`, `geometry_library` |
| `research-bearing` / `research` | `sample_rate_hz`, `threshold_sigma`; `training_records` and `heldout_records` (`record_id`, `signal`) | `Training median spectrum`, `Robust upper envelope`, and one `Held-out <record_id>` series per held-out record | `threshold_sigma`, `sample_rate_hz`, `sample_count`, `training_record_ids`, `heldout_record_ids`, `training_median_amplitude`, `upper_envelope_amplitude` |

The `storage-agingfit` default observations and both `research-bearing` record groups are labelled synthetic. Every held-out comparison retains the supplied order and reports the indices used by the fixed split. `run()` rejects unknown IDs, unknown fields, non-finite values, invalid array dimensions and invalid study-specific combinations. Traces are downsampled to at most 500 plotted points; calculations keep their bounded internal resolution.

## Equation and model boundaries

`hybrid-powerflow` builds a balanced positive-sequence admittance matrix from series impedance and half-line shunt susceptance. It solves the real and reactive constant-power residuals at PQ buses using polar voltage variables while holding one slack bus fixed. Results include each bus phasor and complex branch power at both ends; active losses are the sum of branch-end active powers. A nonconverged, over-tolerance, nonfinite, or implausible-voltage solution raises an error. Branch rating exceedances are surfaced as data and warnings. PV buses, transformer taps, phase imbalance, controls and protection are excluded.

`hybrid-switching` solves `L di/dt = vinverter − vgrid − R i` for a single-phase RL filter. Its ideal full bridge uses sinusoidal-reference/carrier comparison with bipolar `±Vdc/2` output; averaged mode uses `(m·Vdc/2)sin(2πf1t)`. The exact constant-input RL update is evaluated per step. A second run at half the input step reports the relative RMS-current difference. This omits control loops, dead time, switching loss, an LCL capacitor and measured grid impedance.

`lessons-energization` holds the ideal series-RLC branch open until `breaker_close_s`, then integrates `L di/dt = vsource − Ri − vC` and `C dvC/dt = i` with RK4. It includes source work, resistor dissipation, inductor energy, and capacitor energy and reports their balance residual. A half-step peak-current comparison is included. This is an educational single-branch close event, not black-start capability or certified inrush assessment; transformer saturation, breaker arcs, relays and restoration sequence are absent.

`storage-response` applies frequency droop outside the deadband, then limits output by ramp, power rating and SOC energy headroom. Each supplied frequency and resulting power is held constant over `interval_s`; charge/discharge energy and SOC use efficiency-adjusted `power × Δt / 3600`. This is not a grid-service qualification, reserve contract, telemetry or operator test.

`storage-agingfit` fits `retention = 1 − a·(cycles/1000)·exp(b·(temperature°C − 25))` using bounded SciPy nonlinear least squares. Every fifth record is held out; train and held-out RMSE are reported separately. The generated fixture has a known coefficient for software testing and is explicitly synthetic. A successful fit or low fixture error is not scientific validation and does not establish transferability across chemistry, cell design or cycling protocol.

`compare-thermalphysics` integrates temperature and reaction fraction in a single lumped thermal mass. It uses the IUPAC Arrhenius rate equation with absolute temperature, `dα/dt = k(T)(1−α)`, and `Cth·dT/dt = Etotal·dα/dt − UA(T−Tambient)`. Temperature and conversion events stop the ODE and are returned as termination reasons. Thresholds only bound this numerical screen; they are not validated safety alarms, material hazard limits, or a substitute for calorimetry and thermal-runaway testing.

`pv-raytrace` intersects a directional half-line from each panel sample against supplied triangles with Möller–Trumbore barycentric tests. Direct-beam energy is `DNI × sample area × max(0, panel normal · sun direction) × duration`, and any forward triangle hit shadows that sample. It omits diffuse sky, reflections, terrain/weather data, electrical mismatch and geometry verification.

`pv-setbacks` uses Shapely planar negative polygon buffers with mitred joins, preserving the input multipolygon and hole topology. Crop daily light integral is a simple PAR transmission/coverage expression. Its saturating photosynthesis response is a generic curve whose parameters need crop- and site-specific measurement and calibration. It is not a legal boundary or land-use determination.

`research-bearing` compares Hann-windowed one-sided real FFT magnitudes. It builds a per-frequency median and scaled-MAD envelope from training records, then marks a held-out record when any bin exceeds that envelope. Each table row's `maximum_envelope_exceedance_sigma` is the largest `(held-out amplitude − envelope amplitude) / robust scale` among bins strictly above the envelope, or exactly zero when no bin exceeds; it is not deviation from the training median. These are anomaly flags only. The included records are synthetic, and a threshold exceedance is not a fault diagnosis, severity measure or remaining-life estimate.

## External evidence still required

| Model | Evidence required before a real-world claim |
|---|---|
| AC power flow | Validated one-line, bus/branch parameters and operating point, with comparison against a reviewed independent load-flow case. |
| PWM filter | Device and control parameters, switching/dead-time behavior, filter/grid impedance and a reviewed reference EMT model. |
| Energization | Transformer saturation/inrush parameters, breaker point-on-wave behavior, protection settings and site restoration evidence. |
| Storage response | Metered frequency and BESS limits, inverter/control test evidence, and jurisdiction/operator service qualification. |
| Capacity aging | Traceable cell-specific cycling and capacity observations across temperature, independent holdouts, chemistry/protocol context and uncertainty review. |
| Thermal reaction | Material-specific calorimetry and cooling data, spatial/abuse testing and review by qualified safety engineers. |
| PV ray tracing | Surveyed terrain/obstacle mesh, measured panel geometry and validated sun/weather inputs, compared against site shading observations. |
| Setbacks and crop light | Authoritative survey/GIS and applicable local setback requirements; measured crop PAR/DLI, transmission and species-specific response data. |
| Bearing spectrum | Calibrated sensor/time-series records, machine- and bearing-specific training/held-out labels and qualified diagnostics review. |

No such evidence was supplied or externally validated for this implementation. Synthetic fixtures test code behavior only.

## Local verification

From the repository root, after the parent integration adds the module to the study registry and installs the runtime dependency:

```powershell
.venv\Scripts\python.exe -m pytest apps/api/tests/test_physical_studies.py -q
.venv\Scripts\python.exe -m ruff check apps/api/helioforge/engines/physical_studies.py apps/api/tests/test_physical_studies.py
```

The module does not alter API routes or register itself; those edits belong to the integration owner.

## Primary references

- [MATPOWER Newton power flow reference](https://matpower.org/doc/ref-manual/legacy/functions/newtonpf.html) and [MATPOWER manual](https://matpower.org/docs/manual.pdf).
- [NREL photovoltaic inverter switching-model report](https://www.nrel.gov/docs/fy20osti/74462.pdf).
- [U.S. DOE microgrid and black-start overview](https://www.energy.gov/cmei/systems/solar-integration-distributed-energy-resources-and-microgrids-basics) and [essential reliability services](https://www.energy.gov/cmei/articles/keeping-lights-essential-reliability-services).
- [SciPy bounded nonlinear least squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html); empirical Li-ion cycle/calendar aging model paper, [Applied Energy DOI 10.1016/j.apenergy.2016.03.119](https://doi.org/10.1016/j.apenergy.2016.03.119).
- [IUPAC Gold Book Arrhenius equation](https://goldbook.iupac.org/terms/view/A00446) and [SciPy solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).
- Möller and Trumbore, [Fast, Minimum Storage Ray/Triangle Intersection](https://doi.org/10.1080/10867651.1997.10487468); [NREL SAM 3-D PV shading description](https://samrepo.nlr.gov/help/pv_shading.html).
- [Shapely 2.1 user manual](https://shapely.readthedocs.io/en/stable/manual.html).
- [SciPy real FFT](https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.rfft.html) and [ISO 13373-1](https://www.iso.org/standard/21832.html).
