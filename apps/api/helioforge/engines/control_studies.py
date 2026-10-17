"""Averaged grid-following inverter control and local small-signal studies.

The models use a balanced positive-sequence synchronous dq frame with an ideal
imposed grid angle. They intentionally do not claim to model a PLL or PWM
switching ripple. All inputs and output paths are bounded for local research use.
"""
from __future__ import annotations

import json
import math
from typing import Annotated

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

Finite = Annotated[float, Field(allow_inf_nan=False)]
StrictInt = Annotated[int, Field(strict=True)]


class StrictStudy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, validate_default=True)


class _ElectricalInput(StrictStudy):
    filter_inductance_h: Finite = Field(default=0.0015, ge=0.0001, le=0.02)
    filter_resistance_ohm: Finite = Field(default=0.08, gt=0, le=10)
    filter_capacitance_f: Finite = Field(default=20e-6, ge=1e-6, le=0.001)
    grid_inductance_h: Finite = Field(default=0.001, ge=0.0001, le=0.1)
    grid_resistance_ohm: Finite = Field(default=0.05, gt=0, le=10)
    grid_angular_frequency_rad_s: Finite = Field(default=2 * math.pi * 50, ge=250, le=400)
    grid_voltage_peak_v: Finite = Field(default=325.27, ge=50, le=800)
    dc_bus_v: Finite = Field(default=800, ge=100, le=1800)
    modulation_index_max: Finite = Field(default=0.95, ge=0.4, le=0.95)
    current_limit_a: Finite = Field(default=40, gt=0, le=1000)
    current_kp_v_per_a: Finite = Field(default=1.5, ge=-100, le=100)
    current_ki_v_per_as: Finite = Field(default=1000, ge=-100_000, le=100_000)
    voltage_kp_a_per_v: Finite = Field(default=0.2, ge=-100, le=100)
    voltage_ki_a_per_vs: Finite = Field(default=80, ge=-100_000, le=100_000)
    @model_validator(mode="after")
    def dc_headroom(self) -> _ElectricalInput:
        capacitor_q_current = self.grid_angular_frequency_rad_s * self.filter_capacitance_f * self.grid_voltage_peak_v
        equilibrium_voltage = math.hypot(
            self.grid_voltage_peak_v - self.grid_angular_frequency_rad_s * self.filter_inductance_h * capacitor_q_current,
            self.filter_resistance_ohm * capacitor_q_current,
        )
        inverter_limit = self.dc_bus_v * self.modulation_index_max / math.sqrt(3)
        if inverter_limit < equilibrium_voltage * 1.005:
            raise ValueError("DC bus/modulation headroom is insufficient for the unsaturated LCL grid-voltage equilibrium.")
        return self


class HybridControlsInput(_ElectricalInput):
    duration_s: Finite = Field(default=0.04, gt=0, le=0.12)
    time_step_s: Finite = Field(default=0.00005, ge=0.00001, le=0.0005)
    load_step_time_s: Finite = Field(default=0.004, ge=0, le=0.12)
    load_step_a: Finite = Field(default=8.0, ge=0, le=500)
    current_antiwindup_per_s: Finite = Field(default=100, ge=0, le=10_000)
    voltage_antiwindup_per_s: Finite = Field(default=50, ge=0, le=10_000)
    trace_points: StrictInt = Field(default=240, ge=50, le=500)

    @model_validator(mode="after")
    def bounded_aligned_horizon_and_positive_gains(self) -> HybridControlsInput:
        if self.duration_s / self.time_step_s > 6_000 + 1e-8:
            raise ValueError("The coarse simulation is bounded to 6,000 time steps.")
        if self.load_step_time_s >= self.duration_s:
            raise ValueError("load_step_time_s must occur before the end of duration_s.")
        for name, value in (("duration_s", self.duration_s), ("load_step_time_s", self.load_step_time_s)):
            ratio = value / self.time_step_s
            if abs(ratio - round(ratio)) > 1e-7:
                raise ValueError(f"{name} must lie on the requested time_step_s grid.")
        if min(self.current_kp_v_per_a, self.current_ki_v_per_as,
               self.voltage_kp_a_per_v, self.voltage_ki_a_per_vs) <= 0:
            raise ValueError("The simulated PI gains must be positive; use eigenmodes for deliberate wrong-sign cases.")
        required_q_current = self.grid_angular_frequency_rad_s * self.filter_capacitance_f * self.grid_voltage_peak_v
        if required_q_current * 1.005 > self.current_limit_a:
            raise ValueError("current_limit_a must provide headroom above the equilibrium capacitor q-axis current.")
        return self


class EigenmodesInput(_ElectricalInput):
    # Negative outer-loop integral gain is retained as an explicit wrong-sign
    # thought experiment so the unstable result can be tested, never tuned.
    voltage_ki_a_per_vs: Finite = Field(default=80, ge=-100_000, le=100_000)

    @model_validator(mode="after")
    def current_loop_gains_positive(self) -> EigenmodesInput:
        if self.current_kp_v_per_a <= 0 or self.current_ki_v_per_as <= 0 or self.voltage_kp_a_per_v <= 0:
            raise ValueError("Current PI gains and voltage proportional gain must be positive.")
        if self.voltage_ki_a_per_vs == 0:
            raise ValueError("A nonzero outer-loop integral gain is required for the stated capacitor-current equilibrium.")
        required_q_current = self.grid_angular_frequency_rad_s * self.filter_capacitance_f * self.grid_voltage_peak_v
        if required_q_current * 1.005 > self.current_limit_a:
            raise ValueError("current_limit_a must leave the stated unsaturated equilibrium inside the current limit.")
        return self


_CONTROL_LIMITATIONS = [
    "Balanced positive-sequence dq averaged plant; the grid angle is imposed at the nominal frequency. There is no PLL state or synchronization transient.",
    "No PWM switching ripple, dead time, sample/computation delay, sensor filters, DC-link dynamics, unbalance, harmonics, protection, or grid-code behavior is modeled.",
    "The fixed-step RK4 model and local linearization are software research screens, not a calibrated controller, hardware result, field validation, or service qualification.",
]
_SOURCES = [
    {
        "title": "Imperix TN106: Vector current control (dq-frame plant equations, PI loop, and limits)",
        "url": "https://imperix.com/doc/implementation/vector-current-control",
    },
    {
        "title": "NREL: Small-Signal Stability Analysis of Low-Inertia Power Grids with Inverter-Based Resources",
        "url": "https://www.nrel.gov/docs/fy22osti/80613.pdf",
    },
    {
        "title": "Imperix TN135: Neutral Point Clamped Inverter control and modulation (dq PI saturation and anti-windup implementation)",
        "url": "https://imperix.com/doc/implementation/neutral-point-clamped-inverter",
    },
]

STUDIES = [
    {
        "id": "hybrid-controls",
        "page": "hybrid",
        "title": "Averaged inverter control response",
        "summary": "Simulate a balanced dq LCL inverter with cascaded voltage/current PI control, vector limits, back-calculation anti-windup, and a refined RK4 trace.",
        "kind": "electrical",
        "fields": [
            {"name": "duration_s", "label": "Simulation duration", "default": 0.04, "min": 0.001, "max": 0.12, "step": 0.001, "unit": "s"},
            {"name": "time_step_s", "label": "Coarse time step", "default": 0.00005, "min": 0.00001, "max": 0.0005, "step": 0.00001, "unit": "s"},
            {"name": "load_step_time_s", "label": "Load step time", "default": 0.004, "min": 0, "max": 0.12, "step": 0.001, "unit": "s"},
            {"name": "load_step_a", "label": "d-axis load-current step", "default": 8.0, "min": 0, "max": 500, "step": 1, "unit": "A"},
            {"name": "filter_inductance_h", "label": "Converter-side inductance", "default": 0.0015, "min": 0.0001, "max": 0.02, "step": 0.0001, "unit": "H"},
            {"name": "filter_resistance_ohm", "label": "Converter-side resistance", "default": 0.08, "min": 0.001, "max": 10, "step": 0.01, "unit": "Ω"},
            {"name": "filter_capacitance_f", "label": "Filter capacitance", "default": 20e-6, "min": 1e-6, "max": 0.001, "step": 1e-6, "unit": "F"},
            {"name": "grid_inductance_h", "label": "Grid-side inductance", "default": 0.001, "min": 0.0001, "max": 0.1, "step": 0.0001, "unit": "H"},
            {"name": "grid_resistance_ohm", "label": "Grid-side resistance", "default": 0.05, "min": 0.001, "max": 10, "step": 0.01, "unit": "Ω"},
            {"name": "grid_angular_frequency_rad_s", "label": "Imposed grid angular frequency", "default": 2 * math.pi * 50, "min": 250, "max": 400, "step": 1, "unit": "rad/s"},
            {"name": "grid_voltage_peak_v", "label": "Grid d-axis voltage", "default": 325.27, "min": 50, "max": 800, "step": 1, "unit": "V peak"},
            {"name": "dc_bus_v", "label": "DC bus voltage", "default": 800, "min": 100, "max": 1800, "step": 10, "unit": "V"},
            {"name": "modulation_index_max", "label": "Maximum linear modulation index", "default": 0.95, "min": 0.4, "max": 0.95, "step": 0.01, "unit": "ratio"},
            {"name": "current_limit_a", "label": "Vector current-reference limit", "default": 40, "min": 0.1, "max": 1000, "step": 1, "unit": "A"},
            {"name": "current_kp_v_per_a", "label": "Inner current PI proportional gain", "default": 1.5, "min": 0.001, "max": 100, "step": 0.1, "unit": "V/A"},
            {"name": "current_ki_v_per_as", "label": "Inner current PI integral gain", "default": 1000, "min": 0.01, "max": 100000, "step": 10, "unit": "V/(A·s)"},
            {"name": "voltage_kp_a_per_v", "label": "Outer voltage PI proportional gain", "default": 0.2, "min": 0.001, "max": 100, "step": 0.01, "unit": "A/V"},
            {"name": "voltage_ki_a_per_vs", "label": "Outer voltage PI integral gain", "default": 80, "min": 0.01, "max": 100000, "step": 10, "unit": "A/(V·s)"},
            {"name": "current_antiwindup_per_s", "label": "Current PI back-calculation gain", "default": 100, "min": 0, "max": 10000, "step": 10, "unit": "s⁻¹"},
            {"name": "voltage_antiwindup_per_s", "label": "Voltage PI back-calculation gain", "default": 50, "min": 0, "max": 10000, "step": 10, "unit": "s⁻¹"},
            {"name": "trace_points", "label": "Maximum trace points", "default": 240, "min": 50, "max": 500, "step": 10, "unit": "points"},
        ],
        "data_fields": [],
        "equations": [
            "L_f·d i_f/dt = u_inv − v_c − R_f i_f + ωL_f J i_f; C_f·d v_c/dt = i_f − i_g − i_load + ωC_f J v_c; L_g·d i_g/dt = v_c − v_grid − R_g i_g + ωL_g J i_g, with J=[[0,1],[-1,0]].",
            "i_ref = sat_I(i_g+i_load+K_pv(v_ref−v_c)+K_iv∫(v_ref−v_c)dt); u_inv = sat_V(v_c+K_pi(i_ref−i_f)+K_ii∫(i_ref−i_f)dt). Integrators use back-calculation from each vector-limit residual.",
            "The averaged two-level inverter voltage bound is Vdc·m_max/√3. State derivatives are integrated with fixed-step RK4 at dt and dt/2; aligned trajectories are compared as a numerical refinement check.",
        ],
        "limitations": _CONTROL_LIMITATIONS,
        "sources": _SOURCES,
    },
    {
        "id": "research-eigenmodes",
        "page": "research",
        "title": "Closed-loop inverter eigenmodes",
        "summary": "Linearize the unsaturated averaged LCL and cascaded PI model at its grid-voltage equilibrium, then report actual state-matrix eigenvalues and modal damping ratios.",
        "kind": "stability",
        "fields": [
            {"name": "filter_inductance_h", "label": "Converter-side inductance", "default": 0.0015, "min": 0.0001, "max": 0.02, "step": 0.0001, "unit": "H"},
            {"name": "filter_resistance_ohm", "label": "Converter-side resistance", "default": 0.08, "min": 0.001, "max": 10, "step": 0.01, "unit": "Ω"},
            {"name": "filter_capacitance_f", "label": "Filter capacitance", "default": 20e-6, "min": 1e-6, "max": 0.001, "step": 1e-6, "unit": "F"},
            {"name": "grid_inductance_h", "label": "Grid-side inductance", "default": 0.001, "min": 0.0001, "max": 0.1, "step": 0.0001, "unit": "H"},
            {"name": "grid_resistance_ohm", "label": "Grid-side resistance", "default": 0.05, "min": 0.001, "max": 10, "step": 0.01, "unit": "Ω"},
            {"name": "grid_angular_frequency_rad_s", "label": "Imposed grid angular frequency", "default": 2 * math.pi * 50, "min": 250, "max": 400, "step": 1, "unit": "rad/s"},
            {"name": "grid_voltage_peak_v", "label": "Grid d-axis voltage", "default": 325.27, "min": 50, "max": 800, "step": 1, "unit": "V peak"},
            {"name": "dc_bus_v", "label": "DC bus voltage", "default": 800, "min": 100, "max": 1800, "step": 10, "unit": "V"},
            {"name": "modulation_index_max", "label": "Maximum linear modulation index", "default": 0.95, "min": 0.4, "max": 0.95, "step": 0.01, "unit": "ratio"},
            {"name": "current_limit_a", "label": "Vector current-reference limit", "default": 40, "min": 0.1, "max": 1000, "step": 1, "unit": "A"},
            {"name": "current_kp_v_per_a", "label": "Inner current PI proportional gain", "default": 1.5, "min": 0.001, "max": 100, "step": 0.1, "unit": "V/A"},
            {"name": "current_ki_v_per_as", "label": "Inner current PI integral gain", "default": 1000, "min": 0.01, "max": 100000, "step": 10, "unit": "V/(A·s)"},
            {"name": "voltage_kp_a_per_v", "label": "Outer voltage PI proportional gain", "default": 0.2, "min": 0.001, "max": 100, "step": 0.01, "unit": "A/V"},
            {"name": "voltage_ki_a_per_vs", "label": "Outer voltage PI integral gain", "default": 80, "min": -100000, "max": 100000, "step": 10, "unit": "A/(V·s)"},
        ],
        "data_fields": [],
        "equations": [
            "Compute the local matrix A by central-difference linearization of the same ten-state averaged plant/controller used by hybrid-controls at its unsaturated zero-load equilibrium; i_f,q=ωC_fV_grid,d supplies synchronous capacitor current, and PI integrators supply the balancing equilibrium outputs.",
            "λ_k are computed from A; local asymptotic stability requires max Re(λ_k)<0. The reported damping ratio is −Re(λ_k)/|λ_k|, and is a local linear modal quantity only.",
        ],
        "limitations": _CONTROL_LIMITATIONS + [
            "This is the unsaturated local model at an equilibrium; current and modulation limit nonlinearities are inactive. It is not a large-disturbance stability guarantee.",
            "A negative outer voltage integral gain is accepted only to expose an intentionally wrong-sign unstable thought experiment; it is not a candidate tuning.",
        ],
        "sources": _SOURCES,
    },
]


def _hybrid_controls(p: HybridControlsInput) -> dict:
    initial = _equilibrium(p)
    coarse = _integrate(p, initial, p.time_step_s)
    refined = _integrate(p, initial, p.time_step_s / 2)
    aligned_refined = refined[::2]
    if len(aligned_refined) != len(coarse):
        raise ArithmeticError("Coarse and refined simulations did not align to the same time horizon.")

    voltage_error = np.max(np.abs(coarse[:, 2:4] - aligned_refined[:, 2:4]), axis=0)
    current_error = np.max(np.abs(coarse[:, [0, 1, 4, 5]] - aligned_refined[:, [0, 1, 4, 5]]), axis=0)
    max_voltage_error = float(np.max(voltage_error))
    max_current_error = float(np.max(current_error))
    # Relative state increments detect a runaway/overflow even when each value
    # happens to remain finite over the short requested horizon.
    converged = max_voltage_error <= max(0.1, 0.01 * p.grid_voltage_peak_v) and max_current_error <= max(0.1, 0.02 * max(1.0, p.load_step_a))

    sample_count = min(p.trace_points, len(refined))
    sample_indices = np.linspace(0, len(refined) - 1, sample_count, dtype=int)
    sampled = refined[sample_indices]
    times = sample_indices * (p.time_step_s / 2)
    measurements = _signals(sampled, p, np.asarray(times))
    current_limit_hits, inverter_limit_hits = _vector_limit_events(refined, p)
    inverter_limit = _inverter_voltage_limit(p)
    warnings = list(_CONTROL_LIMITATIONS)
    if not converged:
        warnings.append("Coarse/fine RK4 refinement error exceeded the disclosed threshold; reduce time_step_s before interpreting the transient.")
    if current_limit_hits:
        warnings.append("At least one refined integration step reached the vector current-reference limit.")
    if inverter_limit_hits:
        warnings.append("At least one inverter voltage command reached the linear modulation limit.")

    result = {
        "metrics": [
            _metric("Maximum capacitor voltage deviation", max_voltage_error, "V (coarse vs refined)"),
            _metric("Maximum filter/grid current deviation", max_current_error, "A (coarse vs refined)"),
            _metric("Final d-axis capacitor voltage", float(refined[-1, 2]), "V peak"),
            _metric("Final d-axis filter current", float(refined[-1, 0]), "A"),
            _metric("Current-reference limit-hit steps", current_limit_hits, "steps"),
            _metric("Inverter voltage limit-hit steps", inverter_limit_hits, "steps"),
        ],
        "series": measurements["series"],
        "table": [],
        "details": {
            "converged": converged,
            "integrator": "fixed-step classical RK4",
            "time_step_s": p.time_step_s,
            "refined_time_step_s": p.time_step_s / 2,
            "coarse_step_count": len(coarse) - 1,
            "refined_step_count": len(refined) - 1,
            "output_point_count": len(sampled),
            "load_step_a": p.load_step_a,
            "load_step_time_s": p.load_step_time_s,
            "grid_voltage_peak_v": p.grid_voltage_peak_v,
            "dc_bus_v": p.dc_bus_v,
            "inverter_voltage_limit_v": inverter_limit,
            "current_limit_a": p.current_limit_a,
            "current_antiwindup_per_s": p.current_antiwindup_per_s,
            "voltage_antiwindup_per_s": p.voltage_antiwindup_per_s,
            "current_reference_limit_hit_count": current_limit_hits,
            "inverter_voltage_limit_hit_count": inverter_limit_hits,
            "maximum_abs_voltage_refinement_error_v": max_voltage_error,
            "maximum_abs_current_refinement_error_a": max_current_error,
            "filter_inductance_h": p.filter_inductance_h,
            "filter_resistance_ohm": p.filter_resistance_ohm,
            "filter_capacitance_f": p.filter_capacitance_f,
            "grid_inductance_h": p.grid_inductance_h,
            "grid_resistance_ohm": p.grid_resistance_ohm,
            "state_order": ["i_f_d_a", "i_f_q_a", "v_c_d_v", "v_c_q_v", "i_g_d_a", "i_g_q_a", "xi_i_d_as", "xi_i_q_as", "xi_v_d_vs", "xi_v_q_vs"],
            "frame": "balanced positive-sequence dq with ideal imposed grid angle",
            "control_mode": "grid-following cascaded capacitor-voltage/current PI; no PLL state",
        },
        "warnings": warnings,
    }
    json.dumps(result, allow_nan=False)
    return result


def _research_eigenmodes(p: EigenmodesInput) -> dict:
    equilibrium = _equilibrium(p)
    matrix = _linearize(p, equilibrium)
    values = np.linalg.eigvals(matrix)
    if not np.isfinite(matrix).all() or not np.isfinite(values.real).all() or not np.isfinite(values.imag).all():
        raise ArithmeticError("Closed-loop linearization produced a non-finite state matrix or mode.")
    maximum_real = float(np.max(values.real))
    stability = (
        "locally_asymptotically_stable" if maximum_real < -1e-7
        else "unstable" if maximum_real > 1e-7
        else "marginal_or_numerically_indeterminate"
    )
    modes = []
    for index, value in enumerate(sorted(values, key=lambda item: (float(item.real), float(item.imag))), start=1):
        magnitude = float(abs(value))
        modes.append({
            "mode": index,
            "real_per_s": float(value.real),
            "imaginary_per_s": float(value.imag),
            "frequency_hz": float(abs(value.imag) / (2 * math.pi)),
            "damping_ratio": float(-value.real / magnitude) if magnitude > 1e-15 else None,
            "classification": "decaying" if value.real < -1e-7 else "growing" if value.real > 1e-7 else "marginal_or_numerically_indeterminate",
        })
    warnings = list(_CONTROL_LIMITATIONS)
    warnings.append("This is an unsaturated local linearization at one equilibrium; large-disturbance response and protection are outside its scope.")
    if p.voltage_ki_a_per_vs < 0:
        warnings.append("The selected negative outer-loop integral gain is a deliberate wrong-sign instability example, not a tuning recommendation.")
    result = {
        "metrics": [
            _metric("Largest eigenvalue real part", maximum_real, "s⁻¹"),
            _metric("Eigenmodes", len(values), "modes"),
            _metric("Local classification", stability, "state"),
        ],
        "series": [
            {"name": "eigenvalue_real_part", "x_label": "mode", "y_unit": "s⁻¹", "x": list(range(1, len(modes) + 1)), "y": [row["real_per_s"] for row in modes]},
            {"name": "eigenvalue_frequency", "x_label": "mode", "y_unit": "Hz", "x": list(range(1, len(modes) + 1)), "y": [row["frequency_hz"] for row in modes]},
        ],
        "table": modes,
        "details": {
            "stability": stability,
            "maximum_real_part_per_s": maximum_real,
            "state_matrix_per_s": matrix.tolist(),
            "state_order": ["i_f_d_a", "i_f_q_a", "v_c_d_v", "v_c_q_v", "i_g_d_a", "i_g_q_a", "xi_i_d_as", "xi_i_q_as", "xi_v_d_vs", "xi_v_q_vs"],
            "linearization": "central finite difference of the averaged closed-loop RHS at the computed unsaturated zero-load equilibrium, with current and modulation limits inactive",
            "filter_inductance_h": p.filter_inductance_h,
            "filter_resistance_ohm": p.filter_resistance_ohm,
            "filter_capacitance_f": p.filter_capacitance_f,
            "grid_inductance_h": p.grid_inductance_h,
            "grid_resistance_ohm": p.grid_resistance_ohm,
            "current_kp_v_per_a": p.current_kp_v_per_a,
            "current_ki_v_per_as": p.current_ki_v_per_as,
            "voltage_kp_a_per_v": p.voltage_kp_a_per_v,
            "voltage_ki_a_per_vs": p.voltage_ki_a_per_vs,
            "current_limit_a": p.current_limit_a,
            "equilibrium_state": equilibrium.tolist(),
            "control_mode": "grid-following cascaded capacitor-voltage/current PI; no PLL state",
            "pll_included": False,
        },
        "warnings": warnings,
    }
    json.dumps(result, allow_nan=False)
    return result


def _equilibrium(p: _ElectricalInput) -> np.ndarray:
    # A steady dq capacitor current is not zero: it supplies the rotating-frame
    # cross term. The outer voltage PI tracks this filter q current; the inner
    # PI integral provides the corresponding steady decoupling voltage.
    capacitor_q_current = p.grid_angular_frequency_rad_s * p.filter_capacitance_f * p.grid_voltage_peak_v
    xi_voltage_q = capacitor_q_current / p.voltage_ki_a_per_vs if p.voltage_ki_a_per_vs != 0 else 0.0
    xi_current_d = -p.grid_angular_frequency_rad_s * p.filter_inductance_h * capacitor_q_current / p.current_ki_v_per_as
    xi_current_q = p.filter_resistance_ohm * capacitor_q_current / p.current_ki_v_per_as
    return np.array([0.0, capacitor_q_current, p.grid_voltage_peak_v, 0.0, 0.0, 0.0,
                     xi_current_d, xi_current_q, 0.0, xi_voltage_q], dtype=float)


def _inverter_voltage_limit(p: _ElectricalInput) -> float:
    return p.dc_bus_v * p.modulation_index_max / math.sqrt(3)


def _limit_vector(vector: np.ndarray, maximum: float) -> np.ndarray:
    magnitude = float(np.linalg.norm(vector))
    if magnitude <= maximum or magnitude == 0:
        return vector.copy()
    return vector * (maximum / magnitude)


def _controller(state: np.ndarray, p: _ElectricalInput, load: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    i_filter = state[0:2]
    v_cap = state[2:4]
    i_grid = state[4:6]
    xi_current = state[6:8]
    xi_voltage = state[8:10]
    voltage_reference = np.array([p.grid_voltage_peak_v, 0.0])
    voltage_error = voltage_reference - v_cap
    current_ref_raw = i_grid + load + p.voltage_kp_a_per_v * voltage_error + p.voltage_ki_a_per_vs * xi_voltage
    current_ref = _limit_vector(current_ref_raw, getattr(p, "current_limit_a", 1e9))
    current_error = current_ref - i_filter
    inverter_voltage_raw = v_cap + p.current_kp_v_per_a * current_error + p.current_ki_v_per_as * xi_current
    inverter_voltage = _limit_vector(inverter_voltage_raw, _inverter_voltage_limit(p))
    return voltage_reference, current_ref, current_ref_raw, inverter_voltage, inverter_voltage_raw


def _rhs(state: np.ndarray, p: _ElectricalInput, load: np.ndarray) -> np.ndarray:
    if not np.isfinite(state).all():
        raise ArithmeticError("Averaged controller state became non-finite.")
    voltage_reference, current_ref, current_ref_raw, inverter_voltage, inverter_voltage_raw = _controller(state, p, load)
    i_filter = state[0:2]
    v_cap = state[2:4]
    i_grid = state[4:6]
    omega = p.grid_angular_frequency_rad_s
    rotation = np.array([[0.0, 1.0], [-1.0, 0.0]])
    voltage_error = voltage_reference - v_cap
    current_error = current_ref - i_filter
    current_ref_residual = current_ref - current_ref_raw
    inverter_residual = inverter_voltage - inverter_voltage_raw
    # Back-calculation drives the integrator output toward the saturated vector.
    voltage_aw = (
        (getattr(p, "voltage_antiwindup_per_s", 0.0) / p.voltage_ki_a_per_vs) * current_ref_residual
        if p.voltage_ki_a_per_vs != 0 else np.zeros(2)
    )
    d_xi_voltage = voltage_error + voltage_aw
    d_xi_current = current_error + (getattr(p, "current_antiwindup_per_s", 0.0) / p.current_ki_v_per_as) * inverter_residual
    d_i_filter = (inverter_voltage - v_cap - p.filter_resistance_ohm * i_filter
                  + omega * p.filter_inductance_h * (rotation @ i_filter)) / p.filter_inductance_h
    d_v_cap = (i_filter - i_grid - load + omega * p.filter_capacitance_f * (rotation @ v_cap)) / p.filter_capacitance_f
    d_i_grid = (v_cap - np.array([p.grid_voltage_peak_v, 0.0]) - p.grid_resistance_ohm * i_grid
                + omega * p.grid_inductance_h * (rotation @ i_grid)) / p.grid_inductance_h
    return np.concatenate([d_i_filter, d_v_cap, d_i_grid, d_xi_current, d_xi_voltage])


def _integrate(p: HybridControlsInput, initial: np.ndarray, step: float) -> np.ndarray:
    count = int(round(p.duration_s / step))
    event_step = int(round(p.load_step_time_s / step))
    if count > 12_000:
        raise ValueError("Refined simulation is bounded to 12,000 integration steps.")
    states = np.empty((count + 1, len(initial)), dtype=float)
    states[0] = initial
    state = initial.copy()
    for index in range(count):
        load = np.array([p.load_step_a if index >= event_step else 0.0, 0.0])
        k1 = _rhs(state, p, load)
        k2 = _rhs(state + 0.5 * step * k1, p, load)
        k3 = _rhs(state + 0.5 * step * k2, p, load)
        k4 = _rhs(state + step * k3, p, load)
        state = state + (step / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
        if not np.isfinite(state).all() or np.max(np.abs(state)) > 1e9:
            raise ArithmeticError("Averaged controller diverged or exceeded its finite-state bound.")
        states[index + 1] = state
    return states


def _signals(states: np.ndarray, p: HybridControlsInput, times: np.ndarray) -> dict:
    load = np.column_stack((np.where(times >= p.load_step_time_s, p.load_step_a, 0.0), np.zeros(len(times))))
    control_values = [_controller(state, p, load[index]) for index, state in enumerate(states)]
    voltage_reference = np.asarray([item[0] for item in control_values])
    current_reference = np.asarray([item[1] for item in control_values])
    inverter_voltage = np.asarray([item[3] for item in control_values])
    series = []
    for name, values, unit in (
        ("capacitor_voltage_d", states[:, 2], "V peak"),
        ("capacitor_voltage_q", states[:, 3], "V peak"),
        ("filter_current_d", states[:, 0], "A"),
        ("filter_current_q", states[:, 1], "A"),
        ("grid_current_d", states[:, 4], "A"),
        ("grid_current_q", states[:, 5], "A"),
        ("voltage_reference_d", voltage_reference[:, 0], "V peak"),
        ("current_reference_d", current_reference[:, 0], "A"),
        ("current_reference_q", current_reference[:, 1], "A"),
        ("inverter_voltage_d", inverter_voltage[:, 0], "V"),
        ("inverter_voltage_q", inverter_voltage[:, 1], "V"),
        ("current_integrator_d", states[:, 6], "A·s"),
        ("current_integrator_q", states[:, 7], "A·s"),
        ("voltage_integrator_d", states[:, 8], "V·s"),
        ("voltage_integrator_q", states[:, 9], "V·s"),
    ):
        series.append({"name": name, "x_label": "time", "y_unit": unit, "x": times.tolist(), "y": np.asarray(values, dtype=float).tolist()})
    return {"series": series}


def _vector_limit_events(states: np.ndarray, p: HybridControlsInput) -> tuple[int, int]:
    current_limit_hits = 0
    inverter_limit_hits = 0
    for index, state in enumerate(states):
        time = index * (p.time_step_s / 2)
        load = np.array([p.load_step_a if time >= p.load_step_time_s else 0.0, 0.0])
        _, _, current_raw, _, inverter_raw = _controller(state, p, load)
        current_limit_hits += int(np.linalg.norm(current_raw) > p.current_limit_a * (1 + 1e-12))
        inverter_limit_hits += int(np.linalg.norm(inverter_raw) > _inverter_voltage_limit(p) * (1 + 1e-12))
    return current_limit_hits, inverter_limit_hits


def _linearize(p: EigenmodesInput, equilibrium: np.ndarray) -> np.ndarray:
    matrix = np.empty((len(equilibrium), len(equilibrium)), dtype=float)
    no_load = np.zeros(2, dtype=float)
    for column in range(len(equilibrium)):
        step = 1e-6 * max(1.0, abs(float(equilibrium[column])))
        positive = equilibrium.copy()
        negative = equilibrium.copy()
        positive[column] += step
        negative[column] -= step
        matrix[:, column] = (_rhs(positive, p, no_load) - _rhs(negative, p, no_load)) / (2 * step)
    if not np.isfinite(matrix).all():
        raise ArithmeticError("Central-difference linearization produced non-finite coefficients.")
    return matrix


def _metric(label: str, value: float | int | str | None, unit: str) -> dict:
    return {"label": label, "value": value, "unit": unit}


_RUNNERS = {
    "hybrid-controls": (HybridControlsInput, _hybrid_controls),
    "research-eigenmodes": (EigenmodesInput, _research_eigenmodes),
}


def run(study_id: str, inputs: dict) -> dict:
    """Validate and execute one averaged control or eigenmode study."""
    try:
        model, calculate = _RUNNERS[study_id]
    except (KeyError, TypeError) as error:
        raise ValueError(f"Unknown control study: {study_id!r}") from error
    if not isinstance(inputs, dict):
        raise TypeError("Study inputs must be a JSON object.")
    result = calculate(model.model_validate(inputs))
    json.dumps(result, allow_nan=False)
    return result
