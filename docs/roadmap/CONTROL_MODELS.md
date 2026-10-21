# Averaged inverter control studies

This addition provides two executable research studies alongside the switching
inverter study. It closes the software path for an explicit averaged controller
and a local closed-loop eigenmode calculation. It does **not** turn the
balanced-sequence averaged model into a complete three-phase EMT model, and it
does not add a PLL to the separate single-phase PWM model.

## Studies and API inputs

The Python module exports `STUDIES` and `run(study_id, inputs)`, following the
experimental-study result contract. Inputs are strict, finite, and bounded;
unknown fields fail validation. The studies make no external calls.

### `hybrid-controls` (Hybrid page)

This is a balanced positive-sequence synchronous dq averaged voltage-source
inverter with an LCL output network. The angle is imposed at the specified
nominal grid angular frequency. A d-axis load-current step is applied at a
grid-aligned event time. It uses an outer capacitor-voltage PI and inner
converter-side current PI, vector current-reference saturation, modulation
voltage-vector saturation, and back-calculation anti-windup on both loops. The
two-level linear modulation voltage bound is `Vdc * modulation_index_max / √3`.
Classical RK4 integrates the exact same equations at `time_step_s` and half that
step; matching time points disclose the trajectory-refinement error. An
inadequate refinement is returned with `details.converged=false` and a warning;
it is not silently presented as converged. A nonfinite state or explosive
trajectory fails the run.

Numeric inputs (all optional and defaulted):

```text
duration_s, time_step_s, load_step_time_s, load_step_a,
filter_inductance_h, filter_resistance_ohm, filter_capacitance_f,
grid_inductance_h, grid_resistance_ohm, grid_angular_frequency_rad_s,
grid_voltage_peak_v, dc_bus_v, modulation_index_max,
current_kp_v_per_a, current_ki_v_per_as,
voltage_kp_a_per_v, voltage_ki_a_per_vs,
current_antiwindup_per_s, voltage_antiwindup_per_s,
current_limit_a, trace_points
```

Series names are `capacitor_voltage_d`, `capacitor_voltage_q`,
`filter_current_d`, `filter_current_q`, `grid_current_d`, `grid_current_q`,
`voltage_reference_d`, `current_reference_d`, `current_reference_q`,
`inverter_voltage_d`, `inverter_voltage_q`, `current_integrator_d`,
`current_integrator_q`, `voltage_integrator_d`, and `voltage_integrator_q`.
Each shares a time axis and contains at most 500 points. The `details` object includes `converged`,
`integrator`, coarse/refined step sizes and counts, `output_point_count`,
`load_step_a`, `load_step_time_s`, `grid_voltage_peak_v`, `dc_bus_v`,
`inverter_voltage_limit_v`, `current_limit_a`, both limit-hit counts,
`maximum_abs_voltage_refinement_error_v`,
`maximum_abs_current_refinement_error_a`, the five filter/grid component
parameters, `state_order`, `frame`, and `control_mode`.

### `research-eigenmodes` (Research page)

This uses the same ten states and closed-loop RHS, with zero external load, at
the balanced grid-voltage equilibrium. That equilibrium has `i_f,q = omega*C_f*V_grid,d`
to supply the synchronous capacitor current; controller integrators provide the
corresponding current reference and inverter voltage. A central finite-difference linearization
constructs and returns the actual 10×10 `state_matrix_per_s`; NumPy computes its
eigenvalues. The table contains `mode`, `real_per_s`, `imaginary_per_s`,
`frequency_hz`, `damping_ratio`, and `classification`. `details` includes
`stability`, `maximum_real_part_per_s`, `state_matrix_per_s`, `state_order`,
the `linearization` description, five filter/grid component parameters, all
four PI gains, `current_limit_a`, `equilibrium_state`, `control_mode`, and
`pll_included=false`.

The eigenmode numeric inputs are:

```text
filter_inductance_h, filter_resistance_ohm, filter_capacitance_f,
grid_inductance_h, grid_resistance_ohm, grid_angular_frequency_rad_s,
grid_voltage_peak_v, dc_bus_v, modulation_index_max,
current_limit_a,
current_kp_v_per_a, current_ki_v_per_as,
voltage_kp_a_per_v, voltage_ki_a_per_vs
```

`voltage_ki_a_per_vs` may be negative only in this local study to expose a
wrong-sign unstable mode. It is not accepted as a simulation tuning, and the
result warning states that explicitly. Stability applies only to the
unsaturated local linear model at the one stated equilibrium, not to large
disturbances or all controller operating points.

## Model equations and conventions

The state order is converter-side current `i_f,dq`, capacitor voltage `v_c,dq`,
grid-side current `i_g,dq`, current PI integrator `xi_i,dq`, and voltage PI
integrator `xi_v,dq`. With `J = [[0,1],[-1,0]]`, `omega` the imposed frame rate,
and vectors in d/q order, the plant is:

```text
L_f * d(i_f)/dt = u_inv - v_c - R_f*i_f + omega*L_f*J*i_f
C_f * d(v_c)/dt = i_f - i_g - i_load + omega*C_f*J*v_c
L_g * d(i_g)/dt = v_c - v_grid - R_g*i_g + omega*L_g*J*i_g
```

The cascaded controls are:

```text
e_v = v_ref - v_c
i_ref_raw = i_g + i_load + K_pv*e_v + K_iv*xi_v
i_ref = vector_limit(i_ref_raw, I_max)
e_i = i_ref - i_f
u_raw = v_c + K_pi*e_i + K_ii*xi_i
u_inv = vector_limit(u_raw, Vdc*m_max/sqrt(3))
dxi_v/dt = e_v + (k_aw,v/K_iv)*(i_ref - i_ref_raw)
dxi_i/dt = e_i + (k_aw,i/K_ii)*(u_inv - u_raw)
```

At the no-load equilibrium, capacitor current in q is `omega*C_f*V_grid`; it
must not be mistaken for an unbalanced or zero-current capacitor. The controller
integrator states account for that synchronous-frame current and filter voltage.

## Scientific and validation boundaries

This is an executable, bounded educational model, not a measured or calibrated
inverter. It omits PLL/synchronization dynamics, PWM switching, dead time,
digital delay, sensor filtering, DC-link energy dynamics, three-phase
unbalance/harmonics, protection, and grid-code behavior. The existing
single-phase PWM model remains a separate switching demonstration. Combining
the two does not claim full three-phase EMT fidelity.

Before engineering use, a qualified model owner would need the actual topology,
per-unit/base and dq convention, filter parasitics, controller gains and
anti-windup, modulation limits, sampling/computation delay, PLL dynamics, and
initial conditions, checked against manufacturer records and measured
waveforms. Real field calibration, independent model validation, hardware
testing, operational approval, grid-code or service qualification remain
external prerequisites. No service qualification, field result, safety alarm,
or controller recommendation is made here.

Primary technical references support the modeling conventions and controller
structure, not calibration or accuracy of these defaults:

- Imperix, [TN106: Vector current control](https://imperix.com/doc/implementation/vector-current-control) — dq RL plant equations, PI current-control structure, saturation and experimental/simulation discussion.
- Imperix, [TN135: Neutral Point Clamped Inverter control and modulation](https://imperix.com/doc/implementation/neutral-point-clamped-inverter) — dq control implementation and PI anti-windup under saturation.
- National Renewable Energy Laboratory, [Small-Signal Stability Analysis of Low-Inertia Power Grids with Inverter-Based Resources](https://www.nrel.gov/docs/fy22osti/80613.pdf) — state-space and inverter control-loop considerations, including LCL dynamics.

The tests check the no-load dq equilibrium, load-step response and refinement,
current saturation, bounded/strict input failures, independently recomputed
matrix eigenvalues, a hand-derived closed-loop matrix coefficient, and a
wrong-sign-gain unstable case. They validate software behavior only; they are
not independent scientific or field validation.
