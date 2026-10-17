"""Bounded physical and electromechanical experiments for research and teaching.

Every model here is a transparent screen. It is not a controller, calibrated
digital twin, protection study, service qualification, safety alarm, or
engineering approval. Real-world decisions require fit-for-purpose data and
independent validation.
"""
from __future__ import annotations

import math
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares, root
from shapely.geometry import MultiPolygon, Polygon

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Coordinate = Annotated[float, Field(ge=-100_000, le=100_000, allow_inf_nan=False)]
Point2 = tuple[Coordinate, Coordinate]
Point3 = tuple[Coordinate, Coordinate, Coordinate]
Ring = Annotated[list[Point2], Field(min_length=3, max_length=128)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, allow_inf_nan=False)


class Bus(StrictInput):
    bus_id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal["slack", "pq"]
    p_load_mw: NonNegative = Field(default=0, le=1_000_000)
    q_load_mvar: NonNegative = Field(default=0, le=1_000_000)
    voltage_pu: float = Field(default=1, ge=0.5, le=1.5, allow_inf_nan=False)
    angle_deg: float = Field(default=0, ge=-180, le=180, allow_inf_nan=False)


class Branch(StrictInput):
    from_bus: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    to_bus: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    r_pu: NonNegative = Field(default=0.01, le=10)
    x_pu: NonNegative = Field(default=0.08, le=10)
    b_pu: Finite = Field(default=0, ge=-10, le=10)
    rate_mva: float = Field(default=100, gt=0, le=1_000_000, allow_inf_nan=False)

    @model_validator(mode="after")
    def impedance_is_nonzero(self):
        if self.r_pu == 0 and self.x_pu == 0:
            raise ValueError("Each branch needs non-zero series resistance or reactance.")
        if self.from_bus == self.to_bus:
            raise ValueError("A branch must connect two different buses.")
        return self


_DEFAULT_BUSES = [
    dict(bus_id="grid", kind="slack", p_load_mw=0, q_load_mvar=0, voltage_pu=1, angle_deg=0),
    dict(bus_id="campus", kind="pq", p_load_mw=18, q_load_mvar=5, voltage_pu=1, angle_deg=0),
    dict(bus_id="storage", kind="pq", p_load_mw=8, q_load_mvar=2, voltage_pu=1, angle_deg=0),
]
_DEFAULT_BRANCHES = [
    dict(from_bus="grid", to_bus="campus", r_pu=0.012, x_pu=0.07, b_pu=0.01, rate_mva=80),
    dict(from_bus="campus", to_bus="storage", r_pu=0.008, x_pu=0.045, b_pu=0.004, rate_mva=35),
    dict(from_bus="grid", to_bus="storage", r_pu=0.02, x_pu=0.11, b_pu=0.005, rate_mva=50),
]


class PowerFlowInput(StrictInput):
    base_mva: float = Field(default=100, gt=0, le=1_000_000, allow_inf_nan=False)
    tolerance_pu: float = Field(default=1e-9, gt=0, le=1e-4, allow_inf_nan=False)
    max_iterations: int = Field(default=40, ge=2, le=200, strict=True)
    buses: list[Bus] = Field(default_factory=lambda: [Bus.model_validate(x) for x in _DEFAULT_BUSES], min_length=2, max_length=12)
    branches: list[Branch] = Field(default_factory=lambda: [Branch.model_validate(x) for x in _DEFAULT_BRANCHES], min_length=1, max_length=24)

    @model_validator(mode="after")
    def network_is_connected_and_well_formed(self):
        ids = [bus.bus_id for bus in self.buses]
        if len(ids) != len(set(ids)):
            raise ValueError("Bus IDs must be unique.")
        if sum(bus.kind == "slack" for bus in self.buses) != 1:
            raise ValueError("Provide exactly one slack bus; remaining buses are PQ loads.")
        known = set(ids)
        adjacency = {bus_id: set() for bus_id in ids}
        for branch in self.branches:
            if branch.from_bus not in known or branch.to_bus not in known:
                raise ValueError("Every branch endpoint must name a supplied bus.")
            adjacency[branch.from_bus].add(branch.to_bus)
            adjacency[branch.to_bus].add(branch.from_bus)
        slack = next(bus.bus_id for bus in self.buses if bus.kind == "slack")
        reached = {slack}
        todo = [slack]
        while todo:
            for neighbor in adjacency[todo.pop()]:
                if neighbor not in reached:
                    reached.add(neighbor)
                    todo.append(neighbor)
        if reached != known:
            raise ValueError("All buses must be connected to the slack bus.")
        return self


class SwitchingInput(StrictInput):
    switching_enabled: int = Field(default=1, ge=0, le=1, strict=True)
    dc_link_voltage_v: float = Field(default=650, ge=100, le=2000, allow_inf_nan=False)
    modulation_index: float = Field(default=0.85, ge=0, le=0.95, allow_inf_nan=False)
    fundamental_hz: float = Field(default=50, ge=40, le=70, allow_inf_nan=False)
    switching_hz: float = Field(default=2000, ge=100, le=5000, allow_inf_nan=False)
    filter_inductance_h: float = Field(default=0.003, ge=0.0001, le=0.1, allow_inf_nan=False)
    filter_resistance_ohm: float = Field(default=0.5, ge=0.05, le=20, allow_inf_nan=False)
    grid_voltage_rms_v: float = Field(default=230, ge=10, le=1000, allow_inf_nan=False)
    time_step_s: float = Field(default=0.00002, ge=0.000001, le=0.00005, allow_inf_nan=False)
    simulation_cycles: int = Field(default=2, ge=1, le=5, strict=True)

    @model_validator(mode="after")
    def bounded_time_resolution(self):
        if self.switching_hz * self.time_step_s > 0.05:
            raise ValueError("Time step must provide at least 20 samples per switching period.")
        if self.simulation_cycles / self.fundamental_hz / self.time_step_s > 10_000:
            raise ValueError("Simulation is too long for the selected time step.")
        return self


class EnergizationInput(StrictInput):
    source_voltage_rms_v: float = Field(default=230, ge=1, le=1000, allow_inf_nan=False)
    frequency_hz: float = Field(default=50, ge=40, le=70, allow_inf_nan=False)
    closing_phase_deg: float = Field(default=0, ge=-180, le=180, allow_inf_nan=False)
    resistance_ohm: float = Field(default=5, ge=0.1, le=100, allow_inf_nan=False)
    inductance_h: float = Field(default=0.05, ge=0.001, le=2, allow_inf_nan=False)
    capacitance_f: float = Field(default=0.001, ge=0.0001, le=0.5, allow_inf_nan=False)
    initial_capacitor_voltage_v: float = Field(default=0, ge=-1000, le=1000, allow_inf_nan=False)
    breaker_close_s: float = Field(default=0.005, ge=0, le=0.1, allow_inf_nan=False)
    time_step_s: float = Field(default=0.00002, ge=0.000001, le=0.00005, allow_inf_nan=False)
    simulation_cycles: int = Field(default=2, ge=1, le=5, strict=True)

    @model_validator(mode="after")
    def bounded_energization(self):
        duration = self.simulation_cycles / self.frequency_hz
        natural_omega = 1 / math.sqrt(self.inductance_h * self.capacitance_f)
        if self.breaker_close_s > duration:
            raise ValueError("Breaker closing time must fall inside the simulated window.")
        if self.time_step_s * natural_omega > 0.2:
            raise ValueError("Time step is too large for the selected L-C natural frequency.")
        if duration / self.time_step_s > 10_000:
            raise ValueError("Simulation is too long for the selected time step.")
        return self


class StorageResponseInput(StrictInput):
    nominal_frequency_hz: float = Field(default=50, ge=45, le=65, allow_inf_nan=False)
    deadband_hz: float = Field(default=0.02, ge=0, le=1, allow_inf_nan=False)
    droop_kw_per_hz: float = Field(default=2500, ge=0, le=1_000_000, allow_inf_nan=False)
    power_limit_kw: float = Field(default=1000, ge=0, le=1_000_000, allow_inf_nan=False)
    ramp_kw_per_s: float = Field(default=1000, ge=0, le=10_000_000, allow_inf_nan=False)
    capacity_kwh: float = Field(default=2000, ge=1, le=1_000_000, allow_inf_nan=False)
    initial_soc_fraction: float = Field(default=0.5, ge=0.1, le=0.9, allow_inf_nan=False)
    minimum_soc_fraction: float = Field(default=0.1, ge=0, lt=0.9, allow_inf_nan=False)
    maximum_soc_fraction: float = Field(default=0.9, gt=0.1, le=1, allow_inf_nan=False)
    round_trip_efficiency: float = Field(default=0.9, ge=0.5, le=1, allow_inf_nan=False)
    interval_s: float = Field(default=0.1, gt=0, le=0.5, allow_inf_nan=False)
    frequency_hz: list[Finite] = Field(
        default_factory=lambda: [50, 50, 49.98, 49.95, 49.92, 49.9, 49.9, 49.92, 49.95, 49.98, 50, 50],
        min_length=2, max_length=500,
    )

    @model_validator(mode="after")
    def valid_soc_and_frequency(self):
        if self.minimum_soc_fraction >= self.maximum_soc_fraction:
            raise ValueError("Minimum SOC must be less than maximum SOC.")
        if not self.minimum_soc_fraction <= self.initial_soc_fraction <= self.maximum_soc_fraction:
            raise ValueError("Initial SOC must be between the selected SOC limits.")
        if any(not 45 <= frequency <= 65 for frequency in self.frequency_hz):
            raise ValueError("Frequency observations must remain between 45 and 65 Hz.")
        return self


class AgingObservation(StrictInput):
    cycle_count: float = Field(ge=0, le=10_000, allow_inf_nan=False)
    temperature_c: float = Field(ge=-10, le=60, allow_inf_nan=False)
    capacity_fraction: float = Field(ge=0.1, le=1.05, allow_inf_nan=False)


def _aging_fixture() -> list[dict]:
    rows = []
    cycles = [400, 700, 1000, 1400, 1800, 2200, 2600, 3000, 3400, 3800, 4200, 4600, 5000, 5400, 5800]
    temperatures = [15, 25, 35, 20, 30, 40, 10, 28, 36, 18, 32, 22, 38, 12, 27]
    for index, (count, temperature) in enumerate(zip(cycles, temperatures)):
        retention = 1 - 0.018 * (count / 1000) * math.exp(0.008 * (temperature - 25))
        residual = ((index % 3) - 1) * 0.0002
        rows.append(dict(cycle_count=count, temperature_c=temperature, capacity_fraction=retention + residual))
    return rows


class AgingFitInput(StrictInput):
    observations: list[AgingObservation] = Field(default_factory=lambda: [AgingObservation.model_validate(x) for x in _aging_fixture()], min_length=8, max_length=128)

    @model_validator(mode="after")
    def identifiable_split(self):
        train = [row for i, row in enumerate(self.observations) if i % 5 != 4]
        heldout = [row for i, row in enumerate(self.observations) if i % 5 == 4]
        if len(train) < 6 or len(heldout) < 2:
            raise ValueError("Provide at least six training and two held-out observations in the fixed split.")
        if max(row.cycle_count for row in train) <= min(row.cycle_count for row in train):
            raise ValueError("Training observations need a range of cycle counts.")
        if max(row.temperature_c for row in train) <= min(row.temperature_c for row in train):
            raise ValueError("Training observations need a range of temperatures.")
        return self


class ThermalInput(StrictInput):
    initial_temperature_c: float = Field(default=25, ge=-20, le=120, allow_inf_nan=False)
    ambient_temperature_c: float = Field(default=25, ge=-30, le=80, allow_inf_nan=False)
    thermal_mass_j_per_k: float = Field(default=10_000, ge=1000, le=1_000_000, allow_inf_nan=False)
    cooling_w_per_k: float = Field(default=20, ge=0, le=100_000, allow_inf_nan=False)
    activation_energy_kj_mol: float = Field(default=35, ge=0, le=80, allow_inf_nan=False)
    reference_temperature_c: float = Field(default=25, ge=-20, le=80, allow_inf_nan=False)
    reaction_rate_ref_per_s: float = Field(default=0.002, ge=0, le=0.005, allow_inf_nan=False)
    reaction_energy_j: float = Field(default=25_000, ge=0, le=10_000_000, allow_inf_nan=False)
    duration_s: float = Field(default=60, gt=0, le=120, allow_inf_nan=False)
    time_step_s: float = Field(default=0.05, gt=0, le=0.1, allow_inf_nan=False)
    termination_temperature_c: float = Field(default=100, ge=30, le=150, allow_inf_nan=False)
    reaction_fraction_trip: float = Field(default=0.95, gt=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def bounded_thermal_run(self):
        if self.initial_temperature_c >= self.termination_temperature_c:
            raise ValueError("Initial temperature must be below the termination threshold.")
        if self.duration_s / self.time_step_s > 5000:
            raise ValueError("Thermal run is too long for the selected output interval.")
        return self


class PanelSample(StrictInput):
    position_m: Point3
    normal: Point3
    area_m2: float = Field(gt=0, le=10_000, allow_inf_nan=False)


class SunSample(StrictInput):
    direction: Point3
    dni_w_m2: float = Field(default=800, ge=0, le=1500, allow_inf_nan=False)
    duration_h: float = Field(default=1, ge=0, le=24, allow_inf_nan=False)


_DEFAULT_PANELS = [dict(position_m=(0, 0, 0), normal=(0, 0, 1), area_m2=20)]
_DEFAULT_SUN = [
    dict(direction=(0.5, 0, 0.8660254), dni_w_m2=700, duration_h=0.5),
    dict(direction=(0, 0.5, 0.8660254), dni_w_m2=800, duration_h=0.5),
    dict(direction=(-0.5, 0, 0.8660254), dni_w_m2=750, duration_h=0.5),
    dict(direction=(0, 0, 0), dni_w_m2=0, duration_h=0.5),
]


class RayTraceInput(StrictInput):
    panel_samples: list[PanelSample] = Field(default_factory=lambda: [PanelSample.model_validate(x) for x in _DEFAULT_PANELS], min_length=1, max_length=25)
    sun_vectors: list[SunSample] = Field(default_factory=lambda: [SunSample.model_validate(x) for x in _DEFAULT_SUN], min_length=1, max_length=48)
    occluder_triangles: list[tuple[Point3, Point3, Point3]] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def ray_geometry_is_valid(self):
        for panel in self.panel_samples:
            if np.linalg.norm(np.asarray(panel.normal, dtype=float)) < 1e-12:
                raise ValueError("Panel normal vectors must be non-zero.")
        for triangle in self.occluder_triangles:
            a, b, c = (np.asarray(point, dtype=float) for point in triangle)
            if np.linalg.norm(np.cross(b - a, c - a)) < 1e-10:
                raise ValueError("Occluder triangles must have non-zero area.")
        return self


class Parcel(StrictInput):
    exterior_m: Ring
    holes_m: list[Ring] = Field(default_factory=list, max_length=16)


_DEFAULT_PARCELS = [dict(exterior_m=[[0, 0], [100, 0], [100, 60], [0, 60]], holes_m=[])]


class SetbackInput(StrictInput):
    setback_m: float = Field(default=2, ge=0, le=100, allow_inf_nan=False)
    pv_cover_fraction: float = Field(default=0.3, ge=0, le=0.9, allow_inf_nan=False)
    module_par_transmission_fraction: float = Field(default=0.1, ge=0, le=0.8, allow_inf_nan=False)
    baseline_par_mol_m2_day: float = Field(default=35, ge=0, le=100, allow_inf_nan=False)
    light_half_saturation_mol_m2_day: float = Field(default=12, gt=0, le=100, allow_inf_nan=False)
    photosynthesis_max_g_m2_day: float = Field(default=20, ge=0, le=1000, allow_inf_nan=False)
    parcels: list[Parcel] = Field(default_factory=lambda: [Parcel.model_validate(x) for x in _DEFAULT_PARCELS], min_length=1, max_length=16)

    @model_validator(mode="after")
    def polygons_valid_and_disjoint(self):
        polygons = [Polygon(parcel.exterior_m, parcel.holes_m) for parcel in self.parcels]
        if any(not polygon.is_valid or polygon.is_empty or polygon.area <= 0 for polygon in polygons):
            raise ValueError("Each parcel must be a valid, non-empty polygon with non-zero area and valid holes.")
        if not MultiPolygon(polygons).is_valid:
            raise ValueError("Parcel polygons must not overlap or share invalid boundaries.")
        return self


def _bearing_fixture() -> tuple[list[dict], list[dict]]:
    n = 256
    training = []
    for index in range(6):
        signal = [
            (1 + 0.005 * index) * math.sin(2 * math.pi * 24 * sample / n)
            + (0.008 + 0.0005 * index) * math.sin(2 * math.pi * 43 * sample / n)
            for sample in range(n)
        ]
        training.append(dict(record_id=f"synthetic-training-{index + 1}", signal=signal))
    nominal = [
        math.sin(2 * math.pi * 24 * sample / n) + 0.009 * math.sin(2 * math.pi * 43 * sample / n)
        for sample in range(n)
    ]
    anomaly = [value + 0.35 * math.sin(2 * math.pi * 62 * sample / n)
               for sample, value in enumerate(nominal)]
    return training, [dict(record_id="synthetic-heldout-normal", signal=nominal),
                      dict(record_id="synthetic-heldout-extra-tone", signal=anomaly)]


class VibrationRecord(StrictInput):
    record_id: str = Field(min_length=1, max_length=80)
    signal: list[Annotated[float, Field(ge=-1_000_000, le=1_000_000, allow_inf_nan=False)]] = Field(
        min_length=64, max_length=4096
    )


class BearingInput(StrictInput):
    sample_rate_hz: float = Field(default=256, ge=64, le=20_000, allow_inf_nan=False)
    threshold_sigma: float = Field(default=4, ge=1, le=20, allow_inf_nan=False)
    training_records: list[VibrationRecord] = Field(min_length=3, max_length=16)
    heldout_records: list[VibrationRecord] = Field(min_length=1, max_length=16)

    @model_validator(mode="before")
    @classmethod
    def synthetic_defaults(cls, value):
        if isinstance(value, dict):
            has_training = "training_records" in value
            has_heldout = "heldout_records" in value
            if has_training != has_heldout:
                raise ValueError("Supply both training and held-out records, or omit both to use the synthetic fixture.")
            if not has_training:
                training, heldout = _bearing_fixture()
                return {**value, "training_records": training, "heldout_records": heldout}
        return value

    @model_validator(mode="after")
    def matched_records_and_unique_ids(self):
        lengths = {len(row.signal) for row in [*self.training_records, *self.heldout_records]}
        if len(lengths) != 1:
            raise ValueError("Training and held-out vibration records must have the same sample count.")
        ids = [row.record_id for row in [*self.training_records, *self.heldout_records]]
        if len(ids) != len(set(ids)):
            raise ValueError("Vibration record IDs must be unique.")
        return self


def f(name: str, label: str, default: int | float, low: int | float, high: int | float,
      step: int | float = 1, unit: str = "") -> dict:
    return dict(name=name, label=label, default=default, min=low, max=high, step=step, unit=unit)


def d(name: str, label: str, default) -> dict:
    return dict(name=name, label=label, default=default)


STUDIES: list[dict] = [
    dict(
        id="hybrid-powerflow", page="hybrid", title="Balanced AC nodal power flow", kind="network",
        summary="Solve a bounded balanced PQ/slack network and inspect actual voltage phasors, branch complex powers, losses and ratings.",
        fields=[f("base_mva", "System base", 100, 1, 1_000_000, 1, "MVA"),
                f("tolerance_pu", "Power mismatch tolerance", 1e-9, 1e-12, 1e-4, 1e-9, "p.u."),
                f("max_iterations", "Maximum solver iterations", 40, 2, 200, 1, "iterations")],
        data_fields=[d("buses", "Balanced slack and PQ buses", _DEFAULT_BUSES),
                     d("branches", "Series branches and MVA limits", _DEFAULT_BRANCHES)],
        equations=["I = Ybus·V; Sbus = V·conj(I)", "PQ residuals are calculated P/Q plus specified positive loads; slack voltage magnitude and angle are fixed.",
                   "Branch-end S = V·conj(Ibranch); real branch loss = Pfrom + Pto."],
        limitations=["Balanced positive-sequence per-unit educational model; one slack bus and constant-power PQ loads only.",
                     "No generator PV/Q limits, transformers, controls, protection, unbalanced phases or operational dispatch.",
                     "Non-converged or non-finite solutions fail closed. Overloaded branch ratings are reported, not controlled."],
        sources=[dict(title="MATPOWER Newton power flow documentation", url="https://matpower.org/doc/ref-manual/legacy/functions/newtonpf.html"),
                 dict(title="MATPOWER AC power flow reference manual", url="https://matpower.org/docs/manual.pdf")],
    ),
    dict(
        id="hybrid-switching", page="hybrid", title="PWM inverter/filter transient", kind="waveform",
        summary="Compare single-phase bipolar PWM switching with its averaged voltage in a series RL grid filter.",
        fields=[f("switching_enabled", "0 averaged, 1 explicit PWM", 1, 0, 1, 1),
                f("dc_link_voltage_v", "DC link voltage", 650, 100, 2000, 10, "V"),
                f("modulation_index", "Modulation index", 0.85, 0, 0.95, 0.01),
                f("fundamental_hz", "Grid frequency", 50, 40, 70, 1, "Hz"),
                f("switching_hz", "PWM carrier frequency", 2000, 100, 5000, 100, "Hz"),
                f("filter_inductance_h", "Filter inductance", 0.003, 0.0001, 0.1, 0.0001, "H"),
                f("filter_resistance_ohm", "Filter resistance", 0.5, 0.05, 20, 0.05, "Ω"),
                f("grid_voltage_rms_v", "Grid voltage", 230, 10, 1000, 1, "V RMS"),
                f("time_step_s", "EMT time step", 0.00002, 0.000001, 0.00005, 0.000001, "s"),
                f("simulation_cycles", "Fundamental cycles", 2, 1, 5, 1)],
        data_fields=[],
        equations=["L·di/dt = vinverter(t) − vgrid(t) − R·i", "Switched bridge: vinverter ∈ {−Vdc/2, +Vdc/2} from sinusoidal-reference/carrier comparison.",
                   "Averaged bridge: vinverter = (m·Vdc/2) sin(2πf1t); RL step uses the exact constant-input exponential update."],
        limitations=["Single-phase series-RL filter, ideal bipolar switches and stiff sinusoidal grid; no semiconductor losses, dead time, PLL or control loops.",
                     "Switching mode is explicitly sampled; the averaged mode removes carrier ripple. This is not a validated EMT product study.",
                     "A half-step current-RMS comparison is reported as a numerical resolution check."],
        sources=[dict(title="NREL photovoltaic inverter detailed switching model report", url="https://www.nrel.gov/docs/fy20osti/74462.pdf")],
    ),
    dict(
        id="lessons-energization", page="lessons", title="Timed LRC energization transient", kind="transient",
        summary="Inspect an R-L-C series circuit current and stored/dissipated energy around a single timed breaker closing step.",
        fields=[f("source_voltage_rms_v", "Source voltage", 230, 1, 1000, 1, "V RMS"),
                f("frequency_hz", "Source frequency", 50, 40, 70, 1, "Hz"),
                f("breaker_close_s", "Breaker close time", 0.005, 0, 0.1, 0.0001, "s"),
                f("resistance_ohm", "Series resistance", 5, 0.1, 100, 0.1, "Ω"),
                f("inductance_h", "Series inductance", 0.05, 0.001, 2, 0.001, "H"),
                f("capacitance_f", "Series capacitance", 0.001, 0.0001, 0.5, 0.0001, "F"),
                f("initial_capacitor_voltage_v", "Initial capacitor voltage", 0, -1000, 1000, 1, "V"),
                f("closing_phase_deg", "Source phase", 0, -180, 180, 1, "degrees"),
                f("time_step_s", "Integration output step", 0.00002, 0.000001, 0.00005, 0.000001, "s"),
                f("simulation_cycles", "Source cycles", 2, 1, 5, 1)],
        data_fields=[],
        equations=["L di/dt = vsource − R i − vC after breaker close", "C dvC/dt = i; before the close event, i and vC remain constant.",
                   "E = ½Li² + ½CvC²; dE/dt = vsource·i − Ri² while connected."],
        limitations=["One ideal single-phase series-RLC branch with a source-side close event; no transformer saturation, relay logic, arc or multi-step restoration.",
                     "This lesson is not a black-start study or a certified energization/inrush limit assessment.",
                     "A half-step peak-current comparison and circuit energy residual are reported."],
        sources=[dict(title="U.S. Department of Energy microgrid and black-start overview", url="https://www.energy.gov/cmei/systems/solar-integration-distributed-energy-resources-and-microgrids-basics")],
    ),
    dict(
        id="storage-response", page="storage", title="Sub-second frequency droop response", kind="response",
        summary="Apply frequency droop with a deadband, ramp, power cap, SOC limits and explicit interval energy integration.",
        fields=[f("nominal_frequency_hz", "Nominal frequency", 50, 45, 65, 0.1, "Hz"),
                f("deadband_hz", "Frequency deadband", 0.02, 0, 1, 0.01, "Hz"),
                f("droop_kw_per_hz", "Droop slope", 2500, 0, 1_000_000, 100, "kW/Hz"),
                f("power_limit_kw", "Power limit", 1000, 0, 1_000_000, 10, "kW"),
                f("ramp_kw_per_s", "Power ramp limit", 1000, 0, 10_000_000, 10, "kW/s"),
                f("capacity_kwh", "Storage capacity", 2000, 1, 1_000_000, 10, "kWh"),
                f("initial_soc_fraction", "Initial SOC", 0.5, 0.1, 0.9, 0.01),
                f("minimum_soc_fraction", "Minimum SOC", 0.1, 0, 0.89, 0.01),
                f("maximum_soc_fraction", "Maximum SOC", 0.9, 0.11, 1, 0.01),
                f("round_trip_efficiency", "Round-trip efficiency", 0.9, 0.5, 1, 0.01),
                f("interval_s", "Observation interval", 0.1, 0.001, 0.5, 0.01, "s")],
        data_fields=[d("frequency_hz", "Observed frequency samples", [50, 50, 49.98, 49.95, 49.92, 49.9, 49.9, 49.92, 49.95, 49.98, 50, 50])],
        equations=["Pcommand = −droop·(f − fnominal) outside the selected deadband", "Power is bounded by ramp, rated kW and SOC energy headroom.",
                   "ΔSOC = −P·Δt/(3600·ηdischarge) for discharge; charge uses ηcharge; delivered kWh = ΣP·Δt/3600."],
        limitations=["Deterministic response to supplied frequency samples; each interval holds its measured frequency and output power constant.",
                     "No grid-code, telemetry, controls, inverter current, reserve procurement, metering or service-qualification model."],
        sources=[dict(title="U.S. Department of Energy essential reliability services", url="https://www.energy.gov/cmei/articles/keeping-lights-essential-reliability-services")],
    ),
    dict(
        id="storage-agingfit", page="storage", title="Capacity-fade coefficient fit", kind="fit",
        summary="Fit a small empirical cycle-and-temperature response on supplied records and score a held-out validation split.",
        fields=[], data_fields=[d("observations", "Cycle, temperature and capacity observations", _aging_fixture())],
        equations=["retention = 1 − a·(cycles/1000)·exp(b·(temperature°C − 25))",
                   "SciPy bounded least-squares fit uses records 0–3 of each fixed five-record group; every fifth record is held out."],
        limitations=["The included records are a synthetic software fixture, not cell measurements or scientific validation.",
                     "This two-coefficient empirical curve ignores chemistry, SOC, C-rate, calendar aging, path dependence, uncertainty and censoring.",
                     "Held-out error describes only the supplied records and cannot qualify a warranty or predict field life."],
        sources=[dict(title="SciPy least_squares reference", url="https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html"),
                 dict(title="Primary empirical Li-ion aging model study", url="https://doi.org/10.1016/j.apenergy.2016.03.119")],
    ),
    dict(
        id="compare-thermalphysics", page="compare", title="Lumped thermal reaction screen", kind="thermal",
        summary="Compare lumped cooling with a bounded Arrhenius heat-release term and explicit stop thresholds.",
        fields=[f("initial_temperature_c", "Initial temperature", 25, -20, 120, 1, "°C"),
                f("ambient_temperature_c", "Ambient temperature", 25, -30, 80, 1, "°C"),
                f("thermal_mass_j_per_k", "Effective thermal mass", 10000, 1000, 1_000_000, 100, "J/K"),
                f("cooling_w_per_k", "Lumped cooling coefficient", 20, 0, 100_000, 1, "W/K"),
                f("activation_energy_kj_mol", "Activation energy", 35, 0, 80, 1, "kJ/mol"),
                f("reaction_rate_ref_per_s", "Reference reaction rate", 0.002, 0, 0.005, 0.0001, "1/s"),
                f("reaction_energy_j", "Total reaction energy", 25000, 0, 10_000_000, 100, "J"),
                f("reference_temperature_c", "Reference temperature", 25, -20, 80, 1, "°C"),
                f("duration_s", "Maximum duration", 60, 0.01, 120, 1, "s"),
                f("time_step_s", "Output interval", 0.05, 0.001, 0.1, 0.001, "s"),
                f("termination_temperature_c", "Stop temperature", 100, 30, 150, 1, "°C"),
                f("reaction_fraction_trip", "Stop conversion fraction", 0.95, 0.01, 1, 0.01)],
        data_fields=[],
        equations=["k(T) = kref·exp[−Ea/R·(1/T − 1/Tref)] with absolute temperature in kelvin", "dα/dt = k(T)(1−α)",
                   "Cth·dT/dt = Etotal·dα/dt − UA·(T − Tambient)."],
        limitations=["Single effective thermal mass, constant cooling and one depleted reaction; no spatial gradients or material-specific chemistry.",
                     "Temperature/reaction thresholds only stop this illustrative calculation; this is not a validated safety alarm or hazard assessment."],
        sources=[dict(title="IUPAC Gold Book Arrhenius equation", url="https://goldbook.iupac.org/terms/view/A00446"),
                 dict(title="SciPy solve_ivp initial-value solver", url="https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html")],
    ),
    dict(
        id="pv-raytrace", page="pv", title="Panel-sample ray-triangle shading", kind="raytrace",
        summary="Intersect directional sun rays with supplied terrain/obstacle triangles and integrate direct-beam energy at panel samples.",
        fields=[], data_fields=[d("panel_samples", "Panel positions, normals and sample areas", _DEFAULT_PANELS),
                                d("sun_vectors", "Sun directions, beam irradiance and duration", _DEFAULT_SUN),
                                d("occluder_triangles", "Terrain and obstacle mesh triangles", [])],
        equations=["incidence = max(0, n̂·ŝ); direct energy = DNI·panel area·incidence·duration.",
                   "A ray is shaded when a supplied triangle intersects the half-line from a panel sample toward the sun."],
        limitations=["Directional direct-beam only; no diffuse sky, ground reflection, spectral response, horizon/weather series or panel electrical mismatch.",
                     "Triangles and panel samples are user-supplied local Cartesian geometry; results depend on mesh completeness and coordinate quality."],
        sources=[dict(title="Möller–Trumbore ray/triangle intersection paper", url="https://doi.org/10.1080/10867651.1997.10487468"),
                 dict(title="NREL System Advisor Model 3D shading description", url="https://samrepo.nlr.gov/help/pv_shading.html")],
    ),
    dict(
        id="pv-setbacks", page="pv", title="Parcel setbacks and crop-light screen", kind="geometry",
        summary="Apply planar polygon setbacks to multipolygons with holes, then expose a clearly uncalibrated PAR-to-light-response screen.",
        fields=[f("setback_m", "Inward setback", 2, 0, 100, 0.5, "m"),
                f("pv_cover_fraction", "Crop area under PV cover", 0.3, 0, 0.9, 0.01),
                f("module_par_transmission_fraction", "PAR transmitted beneath modules", 0.1, 0, 0.8, 0.01),
                f("baseline_par_mol_m2_day", "Baseline daily PAR", 35, 0, 100, 1, "mol/m²/day"),
                f("light_half_saturation_mol_m2_day", "Illustrative light half-saturation", 12, 0.1, 100, 1, "mol/m²/day"),
                f("photosynthesis_max_g_m2_day", "Illustrative maximum response", 20, 0, 1000, 1, "g/m²/day")],
        data_fields=[d("parcels", "Planar parcels with optional interior holes", _DEFAULT_PARCELS)],
        equations=["usable geometry = parcel geometry buffered inward by setback distance", "crop DLI = baseline PAR·[1 − cover·(1 − module transmission)]",
                   "illustrative response = Pmax·DLI/(DLI + half-saturation)."],
        limitations=["Planar Shapely geometry in user-supplied metres; no georeferencing, survey, legal boundary, easement or access-road interpretation.",
                     "Crop-light response is a generic saturating curve, not species-, cultivar-, weather- or farm-calibrated agronomy."],
        sources=[dict(title="Shapely 2.1 geometry and polygon buffer manual", url="https://shapely.readthedocs.io/en/stable/manual.html"),
                 dict(title="NREL System Advisor Model shading scope", url="https://samrepo.nlr.gov/help/pv_shading.html")],
    ),
    dict(
        id="research-bearing", page="research", title="Bearing spectrum envelope comparison", kind="spectrum",
        summary="Build a robust per-frequency spectrum envelope from training records and flag threshold exceedances in held-out vibration records.",
        fields=[f("sample_rate_hz", "Sample rate", 256, 64, 20_000, 1, "Hz"),
                f("threshold_sigma", "Robust envelope threshold", 4, 1, 20, 0.5, "scaled MAD")],
        data_fields=[d("training_records", "Baseline vibration records", _bearing_fixture()[0]),
                     d("heldout_records", "Held-out vibration records", _bearing_fixture()[1])],
        equations=["one-sided amplitude spectrum = |rFFT((x−mean(x))·Hann)|·2/sum(Hann)",
                   "per-bin envelope = median(training) + threshold·max(1.4826·MAD, 5% of median, floor)",
                   "held-out record is flagged if any spectral bin exceeds its baseline envelope; maximum_envelope_exceedance_sigma is max((amplitude−envelope)/scale) over exceeded bins, or zero when no bin exceeds."],
        limitations=["The fixture is synthetic; sampling, sensor mounting and training records determine the envelope.",
                     "A spectral threshold exceedance is an anomaly screen only. It does not identify a bearing fault, root cause, severity or remaining life."],
        sources=[dict(title="SciPy real FFT reference", url="https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.rfft.html"),
                 dict(title="ISO 13373-1 condition monitoring and diagnostics of machines", url="https://www.iso.org/standard/21832.html")],
    ),
]


INPUT_MODELS = {
    "hybrid-powerflow": PowerFlowInput,
    "hybrid-switching": SwitchingInput,
    "lessons-energization": EnergizationInput,
    "storage-response": StorageResponseInput,
    "storage-agingfit": AgingFitInput,
    "compare-thermalphysics": ThermalInput,
    "pv-raytrace": RayTraceInput,
    "pv-setbacks": SetbackInput,
    "research-bearing": BearingInput,
}


def _answer(metrics: list[dict], *, series: list[dict] | None = None, table: list[dict] | None = None,
            details: dict | None = None, warnings: list[str] | None = None) -> dict:
    return dict(metrics=metrics, series=series or [], table=table or [], details=details or {}, warnings=warnings or [])


def _metric(label: str, value, unit: str) -> dict:
    return dict(label=label, value=value, unit=unit)


def _series(name: str, x_label: str, y_unit: str, x: list, y: list) -> dict:
    return dict(name=name, x_label=x_label, y_unit=y_unit, x=x, y=y)


def _sample_indices(count: int, maximum: int = 500) -> np.ndarray:
    return np.unique(np.linspace(0, count - 1, min(count, maximum), dtype=int))


def _powerflow(p: PowerFlowInput) -> dict:
    buses = p.buses
    ids = [bus.bus_id for bus in buses]
    index = {bus_id: i for i, bus_id in enumerate(ids)}
    slack = next(i for i, bus in enumerate(buses) if bus.kind == "slack")
    pq = [i for i, bus in enumerate(buses) if bus.kind == "pq"]
    ybus = np.zeros((len(buses), len(buses)), dtype=complex)
    branch_admittances = []
    for branch in p.branches:
        fi, ti = index[branch.from_bus], index[branch.to_bus]
        series_y = 1 / complex(branch.r_pu, branch.x_pu)
        shunt = 0.5j * branch.b_pu
        ybus[fi, fi] += series_y + shunt
        ybus[ti, ti] += series_y + shunt
        ybus[fi, ti] -= series_y
        ybus[ti, fi] -= series_y
        branch_admittances.append((fi, ti, series_y, shunt, branch))

    specified_p = np.asarray([-bus.p_load_mw / p.base_mva for bus in buses], dtype=float)
    specified_q = np.asarray([-bus.q_load_mvar / p.base_mva for bus in buses], dtype=float)
    angle_indices = np.asarray(pq, dtype=int)
    slack_v = buses[slack].voltage_pu * np.exp(1j * math.radians(buses[slack].angle_deg))

    def make_voltage(x: np.ndarray) -> np.ndarray:
        voltage = np.asarray([bus.voltage_pu * np.exp(1j * math.radians(bus.angle_deg)) for bus in buses])
        voltage[slack] = slack_v
        voltage[angle_indices] = x[len(pq):] * np.exp(1j * x[:len(pq)])
        return voltage

    initial_angles = np.radians([buses[i].angle_deg for i in pq])
    initial_magnitudes = [buses[i].voltage_pu for i in pq]
    initial = np.r_[initial_angles, initial_magnitudes]

    def mismatch(x: np.ndarray) -> np.ndarray:
        voltage = make_voltage(x)
        calculated = voltage * np.conj(ybus @ voltage)
        return np.r_[calculated.real[pq] - specified_p[pq], calculated.imag[pq] - specified_q[pq]]

    solve = root(mismatch, initial, method="hybr", options={"maxfev": p.max_iterations * max(3, 2 * len(initial))})
    residual = mismatch(solve.x) if np.all(np.isfinite(solve.x)) else np.asarray([math.inf])
    residual_norm = float(np.max(np.abs(residual))) if residual.size else 0.0
    voltage = make_voltage(solve.x) if np.all(np.isfinite(solve.x)) else np.asarray([], dtype=complex)
    if (not solve.success or residual_norm > p.tolerance_pu or not np.all(np.isfinite(voltage))
            or np.any(np.abs(voltage) < 0.3) or np.any(np.abs(voltage) > 2.0)):
        raise ValueError(f"Balanced AC power flow did not converge within the selected tolerance (residual {residual_norm:.3g} p.u.).")

    bus_power = voltage * np.conj(ybus @ voltage)
    bus_rows = []
    for i, bus in enumerate(buses):
        bus_rows.append(dict(
            bus_id=bus.bus_id,
            kind=bus.kind,
            voltage_pu=float(abs(voltage[i])),
            angle_deg=float(math.degrees(np.angle(voltage[i]))),
            p_injection_mw=float((bus_power[i].real + bus.p_load_mw / p.base_mva) * p.base_mva),
            q_injection_mvar=float((bus_power[i].imag + bus.q_load_mvar / p.base_mva) * p.base_mva),
            p_load_mw=float(bus.p_load_mw),
            q_load_mvar=float(bus.q_load_mvar),
        ))
    branch_rows = []
    for fi, ti, series_y, shunt, branch in branch_admittances:
        current_from = (voltage[fi] - voltage[ti]) * series_y + shunt * voltage[fi]
        current_to = (voltage[ti] - voltage[fi]) * series_y + shunt * voltage[ti]
        power_from = voltage[fi] * np.conj(current_from) * p.base_mva
        power_to = voltage[ti] * np.conj(current_to) * p.base_mva
        apparent = max(abs(power_from), abs(power_to))
        branch_rows.append(dict(
            from_bus=branch.from_bus, to_bus=branch.to_bus,
            from_p_mw=float(power_from.real), from_q_mvar=float(power_from.imag),
            to_p_mw=float(power_to.real), to_q_mvar=float(power_to.imag),
            loss_p_mw=float((power_from + power_to).real), loss_q_mvar=float((power_from + power_to).imag),
            max_end_apparent_mva=float(apparent), rating_mva=branch.rate_mva,
            loading_fraction=float(apparent / branch.rate_mva), over_limit=bool(apparent > branch.rate_mva),
            from_voltage_pu=float(abs(voltage[fi])), to_voltage_pu=float(abs(voltage[ti])),
        ))
    losses = sum(row["loss_p_mw"] for row in branch_rows)
    max_loading = max((row["loading_fraction"] for row in branch_rows), default=0.0)
    warnings = ["Balanced positive-sequence educational load flow; not a controls, protection or field-validated study."]
    if any(row["over_limit"] for row in branch_rows):
        warnings.append("One or more solved branch apparent-power values exceed the supplied branch rating.")
    return _answer(
        [_metric("Solved active branch losses", losses, "MW"),
         _metric("Minimum bus voltage", min(row["voltage_pu"] for row in bus_rows), "p.u."),
         _metric("Maximum branch loading", max_loading, "fraction"),
         _metric("Maximum nodal power mismatch", residual_norm * p.base_mva, "MVA")],
        series=[_series("Bus voltage magnitude", "Bus", "p.u.", ids, [row["voltage_pu"] for row in bus_rows]),
                _series("Bus voltage angle", "Bus", "degrees", ids, [row["angle_deg"] for row in bus_rows])],
        table=branch_rows,
        details={"converged": True, "solver": "SciPy hybrid root on polar voltage variables",
                 "solver_function_evaluations": int(solve.nfev), "residual_max_pu": residual_norm,
                 "base_mva": p.base_mva, "buses": bus_rows, "branches": branch_rows,
                 "slack_bus_id": ids[slack]}, warnings=warnings,
    )


def _switching_simulation(p: SwitchingInput, step_s: float, switched: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    duration = p.simulation_cycles / p.fundamental_hz
    count = max(1, math.ceil(duration / step_s))
    dt = duration / count
    time = np.arange(count + 1, dtype=float) * dt
    current = np.zeros(count + 1, dtype=float)
    inverter_voltage = np.zeros(count, dtype=float)
    grid_peak = p.grid_voltage_rms_v * math.sqrt(2)
    decay = math.exp(-p.filter_resistance_ohm * dt / p.filter_inductance_h)
    gain = (1 - decay) / p.filter_resistance_ohm
    for k in range(count):
        midpoint = (time[k] + time[k + 1]) / 2
        reference = p.modulation_index * math.sin(2 * math.pi * p.fundamental_hz * midpoint)
        if switched:
            phase = (midpoint * p.switching_hz) % 1.0
            carrier = 1 - 4 * abs(phase - 0.5)
            inverter_voltage[k] = p.dc_link_voltage_v / 2 if reference >= carrier else -p.dc_link_voltage_v / 2
        else:
            inverter_voltage[k] = p.dc_link_voltage_v / 2 * reference
        grid_voltage = grid_peak * math.sin(2 * math.pi * p.fundamental_hz * midpoint)
        current[k + 1] = current[k] * decay + (inverter_voltage[k] - grid_voltage) * gain
    return time, current, inverter_voltage


def _rms(values: np.ndarray, start_fraction: float = 0.5) -> float:
    start = min(max(0, int(len(values) * start_fraction)), len(values) - 1)
    return float(np.sqrt(np.mean(np.square(values[start:]))))


def _switching(p: SwitchingInput) -> dict:
    switched = bool(p.switching_enabled)
    time, current, inv_voltage = _switching_simulation(p, p.time_step_s, switched)
    _, refined_current, _ = _switching_simulation(p, p.time_step_s / 2, switched)
    coarse_rms = _rms(current)
    refined_rms = _rms(refined_current)
    convergence = abs(coarse_rms - refined_rms) / max(refined_rms, 1.0)
    ripple = 0.0
    if switched:
        _, average_current, _ = _switching_simulation(p, p.time_step_s, False)
        ripple = _rms(current - average_current)
    indices = _sample_indices(len(time))
    mode = "switching" if switched else "averaged"
    return _answer(
        [_metric("Grid current RMS", coarse_rms, "A"),
         _metric("Grid current peak magnitude", float(np.max(np.abs(current))), "A"),
         _metric("PWM ripple RMS versus averaged case", ripple, "A"),
         _metric("Half-step relative RMS difference", convergence, "fraction")],
        series=[_series(f"{mode.capitalize()} filter current", "Time", "A", time[indices].tolist(), current[indices].tolist()),
                _series("Inverter voltage", "Interval midpoint", "V", time[indices[:-1]].tolist(),
                        inv_voltage[np.minimum(indices[:-1], len(inv_voltage) - 1)].tolist())],
        details={"mode": mode, "internal_time_step_s": p.simulation_cycles / p.fundamental_hz / (len(time) - 1),
                 "internal_steps": len(time) - 1, "convergence_relative_error": convergence,
                 "switching_ripple_rms_a": ripple, "switching_enabled": switched},
        warnings=["Single-phase ideal PWM and series-RL screen; it omits semiconductor, dead-time, control, PLL and grid-impedance dynamics."],
    )


def _energization_simulation(p: EnergizationInput, maximum_step: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    duration = p.simulation_cycles / p.frequency_hz
    base_count = max(1, math.ceil(duration / maximum_step))
    time = np.unique(np.r_[np.linspace(0.0, duration, base_count + 1), p.breaker_close_s])
    current = np.zeros(len(time), dtype=float)
    capacitor_v = np.full(len(time), p.initial_capacitor_voltage_v, dtype=float)
    source_energy = np.zeros(len(time), dtype=float)
    resistor_energy = np.zeros(len(time), dtype=float)
    phase = math.radians(p.closing_phase_deg)
    source_peak = p.source_voltage_rms_v * math.sqrt(2)

    def source(t: float) -> float:
        return source_peak * math.sin(2 * math.pi * p.frequency_hz * t + phase)

    def derivative(t: float, state: np.ndarray) -> np.ndarray:
        i, vc = state
        return np.asarray([(source(t) - p.resistance_ohm * i - vc) / p.inductance_h, i / p.capacitance_f])

    for k in range(len(time) - 1):
        t0, t1 = float(time[k]), float(time[k + 1])
        dt = t1 - t0
        state = np.asarray([current[k], capacitor_v[k]], dtype=float)
        if t0 + 1e-14 < p.breaker_close_s:
            next_state = state.copy()
        else:
            k1 = derivative(t0, state)
            k2 = derivative(t0 + dt / 2, state + dt * k1 / 2)
            k3 = derivative(t0 + dt / 2, state + dt * k2 / 2)
            k4 = derivative(t1, state + dt * k3)
            next_state = state + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        current[k + 1], capacitor_v[k + 1] = next_state
        if t0 >= p.breaker_close_s - 1e-14:
            p0 = source(t0) * current[k]
            p1 = source(t1) * current[k + 1]
            loss0 = p.resistance_ohm * current[k] ** 2
            loss1 = p.resistance_ohm * current[k + 1] ** 2
            source_energy[k + 1] = source_energy[k] + dt * (p0 + p1) / 2
            resistor_energy[k + 1] = resistor_energy[k] + dt * (loss0 + loss1) / 2
        else:
            source_energy[k + 1] = source_energy[k]
            resistor_energy[k + 1] = resistor_energy[k]
    energy_l = 0.5 * p.inductance_h * current**2
    energy_c = 0.5 * p.capacitance_f * capacitor_v**2
    initial_energy = 0.5 * p.capacitance_f * p.initial_capacitor_voltage_v**2
    residual = source_energy[-1] - ((energy_l[-1] + energy_c[-1]) - initial_energy) - resistor_energy[-1]
    return time, current, energy_l, energy_c, np.c_[source_energy, resistor_energy], float(residual)


def _energization(p: EnergizationInput) -> dict:
    time, current, energy_l, energy_c, energy_pair, residual = _energization_simulation(p, p.time_step_s)
    fine_time, fine_current, *_ = _energization_simulation(p, p.time_step_s / 2)
    coarse_peak = float(np.max(np.abs(current)))
    fine_peak = float(np.max(np.abs(fine_current)))
    convergence = abs(coarse_peak - fine_peak) / max(fine_peak, 1.0)
    indices = _sample_indices(len(time))
    source_energy = energy_pair[:, 0]
    resistor_energy = energy_pair[:, 1]
    return _answer(
        [_metric("Peak inrush current", coarse_peak, "A"),
         _metric("Final inductor energy", float(energy_l[-1]), "J"),
         _metric("Final capacitor energy", float(energy_c[-1]), "J"),
         _metric("Resistive energy dissipated", float(resistor_energy[-1]), "J"),
         _metric("Circuit energy residual", residual, "J"),
         _metric("Half-step peak-current difference", convergence, "fraction")],
        series=[_series("Series current", "Time", "A", time[indices].tolist(), current[indices].tolist()),
                _series("Inductor energy", "Time", "J", time[indices].tolist(), energy_l[indices].tolist()),
                _series("Capacitor energy", "Time", "J", time[indices].tolist(), energy_c[indices].tolist()),
                _series("Source work", "Time", "J", time[indices].tolist(), source_energy[indices].tolist()),
                _series("Resistor loss", "Time", "J", time[indices].tolist(), resistor_energy[indices].tolist())],
        details={"breaker_close_s": p.breaker_close_s, "closing_phase_deg": p.closing_phase_deg,
                 "coarse_peak_current_a": coarse_peak, "refined_peak_current_a": fine_peak,
                 "convergence_relative_error": convergence, "energy_balance_residual_j": residual,
                 "internal_samples": len(time)},
        warnings=["A single ideal RLC lesson only; it does not establish black-start capability or certified energization/inrush limits."],
    )


def _storage_response(p: StorageResponseInput) -> dict:
    eta_charge = math.sqrt(p.round_trip_efficiency)
    eta_discharge = eta_charge
    minimum = p.minimum_soc_fraction * p.capacity_kwh
    maximum = p.maximum_soc_fraction * p.capacity_kwh
    soc = p.initial_soc_fraction * p.capacity_kwh
    previous_power = 0.0
    rows = []
    up_energy = down_energy = 0.0
    for i, frequency in enumerate(p.frequency_hz):
        error = p.nominal_frequency_hz - frequency
        magnitude = max(0.0, abs(error) - p.deadband_hz)
        command = math.copysign(p.droop_kw_per_hz * magnitude, error) if magnitude else 0.0
        command = max(-p.power_limit_kw, min(p.power_limit_kw, command))
        ramp = p.ramp_kw_per_s * p.interval_s
        command = max(previous_power - ramp, min(previous_power + ramp, command))
        max_discharge = max(0.0, (soc - minimum) * eta_discharge * 3600 / p.interval_s)
        max_charge = max(0.0, (maximum - soc) * 3600 / (eta_charge * p.interval_s))
        power = max(-max_charge, min(max_discharge, command))
        energy_kwh = power * p.interval_s / 3600
        if power >= 0:
            soc -= energy_kwh / eta_discharge
            up_energy += energy_kwh
        else:
            soc += -energy_kwh * eta_charge
            down_energy += -energy_kwh
        soc = min(maximum, max(minimum, soc))
        rows.append(dict(time_s=i * p.interval_s, frequency_hz=frequency, droop_command_kw=command,
                         response_kw=power, soc_start_kwh=rows[-1]["soc_end_kwh"] if rows else p.initial_soc_fraction * p.capacity_kwh,
                         soc_end_kwh=soc, interval_energy_kwh=energy_kwh))
        previous_power = power
    time = [row["time_s"] for row in rows]
    powers = [row["response_kw"] for row in rows]
    soc_end = [row["soc_end_kwh"] for row in rows]
    return _answer(
        [_metric("Delivered response energy", up_energy, "kWh"),
         _metric("Absorbed response energy", down_energy, "kWh"),
         _metric("Peak absolute response", max((abs(power) for power in powers), default=0), "kW"),
         _metric("Terminal state of charge", soc, "kWh")],
        series=[_series("Storage response power", "Time", "kW", time, powers),
                _series("Battery stored energy", "Time", "kWh", time, soc_end)],
        table=rows,
        details={"nominal_frequency_hz": p.nominal_frequency_hz, "interval_s": p.interval_s,
                 "round_trip_efficiency": p.round_trip_efficiency, "integrated_dt_hours": p.interval_s / 3600},
        warnings=["Illustrative droop policy only; response ramp, power and energy are screened against supplied samples.",
                  "No grid-service qualification, telemetry, test protocol, reserve contract or market eligibility is established."],
    )


def _aging_fit(p: AgingFitInput) -> dict:
    observations = p.observations
    train_indices = [i for i in range(len(observations)) if i % 5 != 4]
    test_indices = [i for i in range(len(observations)) if i % 5 == 4]
    cycles = np.asarray([row.cycle_count for row in observations], dtype=float)
    temperature = np.asarray([row.temperature_c for row in observations], dtype=float)
    capacity = np.asarray([row.capacity_fraction for row in observations], dtype=float)

    def predict(parameters: np.ndarray, selected: np.ndarray) -> np.ndarray:
        coefficient, temperature_sensitivity = parameters
        exponent = np.clip(temperature_sensitivity * (temperature[selected] - 25), -20, 20)
        return 1 - coefficient * (cycles[selected] / 1000) * np.exp(exponent)

    fit = least_squares(lambda parameters: predict(parameters, np.asarray(train_indices)) - capacity[train_indices],
                        x0=np.asarray([0.015, 0.005]), bounds=(np.asarray([0.0, 0.0]), np.asarray([0.2, 0.1])),
                        max_nfev=2000)
    if not fit.success or not np.all(np.isfinite(fit.x)):
        raise ValueError("Capacity-fade coefficient fit did not converge.")
    predicted = predict(fit.x, np.arange(len(observations)))
    if np.any(predicted < 0) or np.any(predicted > 1.2):
        raise ValueError("Fitted capacity curve leaves the bounded 0–1.2 retention domain for supplied observations.")
    residuals = predicted - capacity
    train_rmse = float(np.sqrt(np.mean(np.square(residuals[train_indices]))))
    heldout_rmse = float(np.sqrt(np.mean(np.square(residuals[test_indices]))))
    rows = [dict(observation_index=i, split="held-out" if i in test_indices else "training",
                 cycle_count=float(cycles[i]), temperature_c=float(temperature[i]),
                 measured_capacity_fraction=float(capacity[i]), predicted_capacity_fraction=float(predicted[i]),
                 residual_fraction=float(residuals[i])) for i in range(len(observations))]
    fixture = [row.model_dump() for row in observations] == _aging_fixture()
    label = "Synthetic fixture (software test only)" if fixture else "User-supplied observations (provenance unverified)"
    return _answer(
        [_metric("Training RMSE", train_rmse, "capacity fraction"),
         _metric("Held-out RMSE", heldout_rmse, "capacity fraction"),
         _metric("Fitted cycle loss per 1000 cycles", float(fit.x[0]), "fraction"),
         _metric("Fitted temperature sensitivity", float(fit.x[1]), "1/°C"),
         _metric("Held-out observations", len(test_indices), "records")],
        series=[_series("Measured capacity", "Observation", "fraction", list(range(len(rows))), capacity.tolist()),
                _series("Fitted capacity", "Observation", "fraction", list(range(len(rows))), predicted.tolist())],
        table=rows,
        details={"dataset_label": label, "training_count": len(train_indices), "heldout_count": len(test_indices),
                 "training_indices_zero_based": train_indices, "heldout_indices_zero_based": test_indices,
                 "solver": "SciPy bounded nonlinear least_squares", "fit_success": bool(fit.success)},
        warnings=["This two-parameter curve is a demonstration fit. Held-out records do not constitute scientific validation.",
                  "Chemistry, protocol and observation provenance are unverified; do not use the fit for warranties or service-life commitments."],
    )


def _thermal_simulation(p: ThermalInput, output_step: float) -> tuple[np.ndarray, np.ndarray, str, float]:
    gas_constant = 8.314462618
    reference_k = p.reference_temperature_c + 273.15

    def rhs(_time: float, state: np.ndarray) -> np.ndarray:
        temperature_c, alpha = state
        temperature_k = max(150.0, min(600.0, temperature_c + 273.15))
        exponent = -p.activation_energy_kj_mol * 1000 / gas_constant * (1 / temperature_k - 1 / reference_k)
        rate = p.reaction_rate_ref_per_s * math.exp(max(-30.0, min(30.0, exponent)))
        dalpha = rate * max(0.0, 1 - alpha)
        dheat = p.reaction_energy_j * dalpha
        dtemp = (dheat - p.cooling_w_per_k * (temperature_c - p.ambient_temperature_c)) / p.thermal_mass_j_per_k
        return np.asarray([dtemp, dalpha])

    def temperature_event(_time: float, state: np.ndarray) -> float:
        return p.termination_temperature_c - state[0]

    def reaction_event(_time: float, state: np.ndarray) -> float:
        return p.reaction_fraction_trip - state[1]

    temperature_event.terminal = True
    temperature_event.direction = -1
    reaction_event.terminal = True
    reaction_event.direction = -1
    points = max(1, math.ceil(p.duration_s / output_step))
    times = np.linspace(0, p.duration_s, points + 1)
    solution = solve_ivp(rhs, (0, p.duration_s), [p.initial_temperature_c, 0.0], method="RK45",
                         t_eval=times, max_step=output_step, rtol=1e-8, atol=1e-10,
                         events=(temperature_event, reaction_event))
    if not solution.success or not np.all(np.isfinite(solution.y)):
        raise ValueError("Lumped thermal ODE integration failed or returned non-finite values.")
    time = solution.t
    states = solution.y.T
    reason = "duration reached"
    event_times = []
    for label, event_times_for_kind, states_for_kind in zip(
            ("temperature threshold reached", "reaction fraction threshold reached"),
            solution.t_events, solution.y_events):
        if len(event_times_for_kind):
            event_times.append((float(event_times_for_kind[0]), label, states_for_kind[0]))
    if event_times:
        event_time, reason, event_state = min(event_times, key=lambda row: row[0])
        if not len(time) or abs(time[-1] - event_time) > 1e-12:
            time = np.r_[time, event_time]
            states = np.vstack((states, event_state))
    heat_j = p.reaction_energy_j * float(states[-1, 1])
    return time, states, reason, heat_j


def _thermal(p: ThermalInput) -> dict:
    time, state, reason, heat_j = _thermal_simulation(p, p.time_step_s)
    _, refined_state, _, _ = _thermal_simulation(p, p.time_step_s / 2)
    peak = float(np.max(state[:, 0]))
    refined_peak = float(np.max(refined_state[:, 0]))
    convergence = abs(peak - refined_peak) / max(abs(refined_peak), 1.0)
    indices = _sample_indices(len(time))
    return _answer(
        [_metric("Peak lumped temperature", peak, "°C"),
         _metric("Final lumped temperature", float(state[-1, 0]), "°C"),
         _metric("Final reaction fraction", float(state[-1, 1]), "fraction"),
         _metric("Reaction heat released", heat_j, "J"),
         _metric("Half-step peak-temperature difference", convergence, "fraction")],
        series=[_series("Lumped temperature", "Time", "°C", time[indices].tolist(), state[indices, 0].tolist()),
                _series("Reaction progress", "Time", "fraction", time[indices].tolist(), state[indices, 1].tolist())],
        details={"termination_reason": reason, "termination_time_s": float(time[-1]),
                 "final_temperature_c": float(state[-1, 0]), "final_reaction_fraction": float(state[-1, 1]),
                 "convergence_relative_error": convergence, "heat_released_j": heat_j},
        warnings=["A single lumped Arrhenius example only; threshold termination is not a validated safety alarm or material hazard assessment."],
    )


def _ray_triangle_hit(origin: np.ndarray, direction: np.ndarray, triangle: tuple[Point3, Point3, Point3]) -> bool:
    a, b, c = (np.asarray(point, dtype=float) for point in triangle)
    edge_1 = b - a
    edge_2 = c - a
    pvec = np.cross(direction, edge_2)
    determinant = float(np.dot(edge_1, pvec))
    if abs(determinant) < 1e-12:
        return False
    inverse = 1.0 / determinant
    tvec = origin - a
    u = float(np.dot(tvec, pvec) * inverse)
    if u < -1e-10 or u > 1 + 1e-10:
        return False
    qvec = np.cross(tvec, edge_1)
    v = float(np.dot(direction, qvec) * inverse)
    if v < -1e-10 or u + v > 1 + 1e-10:
        return False
    distance = float(np.dot(edge_2, qvec) * inverse)
    return distance > 1e-6


def _raytrace(p: RayTraceInput) -> dict:
    rows = []
    energy_by_sun = np.zeros(len(p.sun_vectors), dtype=float)
    shaded_count = 0
    incidence_count = 0
    for sun_index, sun in enumerate(p.sun_vectors):
        direction = np.asarray(sun.direction, dtype=float)
        direction_norm = float(np.linalg.norm(direction))
        if direction_norm <= 1e-12 or sun.dni_w_m2 == 0 or sun.duration_h == 0:
            for panel_index, _panel in enumerate(p.panel_samples):
                rows.append(dict(sun_index=sun_index, panel_index=panel_index, shaded=False,
                                 incidence_cosine=0.0, energy_wh=0.0))
            continue
        direction /= direction_norm
        for panel_index, panel in enumerate(p.panel_samples):
            normal = np.asarray(panel.normal, dtype=float)
            normal /= float(np.linalg.norm(normal))
            cosine = max(0.0, float(np.dot(normal, direction)))
            incidence_count += int(cosine > 0)
            origin = np.asarray(panel.position_m, dtype=float)
            shaded = cosine > 0 and any(_ray_triangle_hit(origin, direction, triangle)
                                        for triangle in p.occluder_triangles)
            if shaded:
                shaded_count += 1
            energy_wh = 0.0 if cosine <= 0 or shaded else sun.dni_w_m2 * panel.area_m2 * cosine * sun.duration_h
            energy_by_sun[sun_index] += energy_wh
            rows.append(dict(sun_index=sun_index, panel_index=panel_index, shaded=bool(shaded),
                             incidence_cosine=cosine, energy_wh=float(energy_wh)))
    total_wh = float(np.sum(energy_by_sun))
    return _answer(
        [_metric("Incident direct-beam energy", total_wh / 1000, "kWh"),
         _metric("Shadowed panel/sun samples", shaded_count, "samples"),
         _metric("Front-side incidence samples", incidence_count, "samples")],
        series=[_series("Direct-beam energy by sun sample", "Sun sample", "kWh",
                        [f"Sun {i + 1}" for i in range(len(p.sun_vectors))], (energy_by_sun / 1000).tolist())],
        table=rows,
        details={"panel_sample_count": len(p.panel_samples), "sun_sample_count": len(p.sun_vectors),
                 "triangle_count": len(p.occluder_triangles), "energy_wh": total_wh,
                 "occluder_algorithm": "Moller-Trumbore directional ray/triangle half-line"},
        warnings=["Direct-beam geometry screen only; supplied meshes and panel samples are not surveyed or completeness-checked."],
    )


def _setbacks(p: SetbackInput) -> dict:
    polygons = [Polygon(parcel.exterior_m, parcel.holes_m) for parcel in p.parcels]
    parcel_geometry = MultiPolygon(polygons)
    usable_geometry = parcel_geometry if p.setback_m == 0 else parcel_geometry.buffer(
        -p.setback_m, join_style="mitre", mitre_limit=1_000_000
    )
    parcel_area = float(parcel_geometry.area)
    usable_area = float(usable_geometry.area) if not usable_geometry.is_empty else 0.0
    usable_area = max(0.0, usable_area)
    crop_dli = p.baseline_par_mol_m2_day * (1 - p.pv_cover_fraction * (1 - p.module_par_transmission_fraction))
    response = p.photosynthesis_max_g_m2_day * crop_dli / (crop_dli + p.light_half_saturation_mol_m2_day) if crop_dli else 0.0
    geometry_kind = usable_geometry.geom_type if not usable_geometry.is_empty else "Empty"
    part_count = len(usable_geometry.geoms) if isinstance(usable_geometry, MultiPolygon) else int(not usable_geometry.is_empty)
    return _answer(
        [_metric("Parcel area", parcel_area, "m²"),
         _metric("Usable area after setback", usable_area, "m²"),
         _metric("Usable land", usable_area / 10_000, "ha"),
         _metric("Estimated crop DLI", crop_dli, "mol/m²/day"),
         _metric("Illustrative crop light response", response, "g/m²/day")],
        table=[dict(parcel_index=i, source_area_m2=float(polygon.area)) for i, polygon in enumerate(polygons)],
        details={"setback_m": p.setback_m, "usable_geometry_type": geometry_kind,
                 "usable_component_count": part_count, "holes_preserved": sum(len(parcel.holes_m) for parcel in p.parcels),
                 "pv_cover_fraction": p.pv_cover_fraction, "module_par_transmission_fraction": p.module_par_transmission_fraction,
                 "crop_dli_mol_m2_day": crop_dli, "photosynthesis_response_g_m2_day": response,
                 "geometry_library": "Shapely planar polygon buffer"},
        warnings=["PAR-to-DLI and saturating crop response are illustrative, not species- or site-calibrated agronomy.",
                  "A planar polygon buffer does not establish legal boundaries, surveying, access, topography or land-use permissions."],
    )


def _record_spectrum(signal: list[float]) -> np.ndarray:
    values = np.asarray(signal, dtype=float)
    values -= np.mean(values)
    window = np.hanning(len(values))
    spectrum = np.abs(np.fft.rfft(values * window)) * (2.0 / max(float(np.sum(window)), 1e-12))
    return spectrum


def _bearing(p: BearingInput) -> dict:
    training = np.asarray([_record_spectrum(record.signal) for record in p.training_records])
    heldout = np.asarray([_record_spectrum(record.signal) for record in p.heldout_records])
    median = np.median(training, axis=0)
    mad = np.median(np.abs(training - median[None, :]), axis=0)
    scale = np.maximum.reduce((1.4826 * mad, 0.05 * median, np.full_like(median, 1e-9)))
    envelope = median + p.threshold_sigma * scale
    frequencies = np.fft.rfftfreq(len(p.training_records[0].signal), 1 / p.sample_rate_hz)
    rows = []
    for record, spectrum in zip(p.heldout_records, heldout):
        exceed = np.flatnonzero(spectrum > envelope)
        score = float(np.max((spectrum[exceed] - envelope[exceed]) / scale[exceed])) if len(exceed) else 0.0
        rows.append(dict(record_id=record.record_id, flagged=bool(len(exceed)),
                         maximum_envelope_exceedance_sigma=score, exceedance_bin_count=int(len(exceed)),
                         exceedance_frequencies_hz=[float(frequencies[i]) for i in exceed[:20]]))
    plot_indices = _sample_indices(len(frequencies))
    plot_series = [_series("Training median spectrum", "Frequency", "amplitude", frequencies[plot_indices].tolist(), median[plot_indices].tolist()),
                    _series("Robust upper envelope", "Frequency", "amplitude", frequencies[plot_indices].tolist(), envelope[plot_indices].tolist())]
    for record, spectrum in zip(p.heldout_records, heldout):
        plot_series.append(_series(f"Held-out {record.record_id}", "Frequency", "amplitude",
                                   frequencies[plot_indices].tolist(), spectrum[plot_indices].tolist()))
    flagged_count = sum(row["flagged"] for row in rows)
    return _answer(
        [_metric("Held-out records flagged", flagged_count, "records"),
         _metric("Held-out records evaluated", len(rows), "records"),
         _metric("Training records", len(p.training_records), "records")],
        series=plot_series, table=rows,
        details={"threshold_sigma": p.threshold_sigma, "sample_rate_hz": p.sample_rate_hz,
                 "sample_count": len(p.training_records[0].signal), "training_record_ids": [r.record_id for r in p.training_records],
                 "heldout_record_ids": [r.record_id for r in p.heldout_records],
                 "training_median_amplitude": median.tolist(), "upper_envelope_amplitude": envelope.tolist()},
        warnings=["Spectrum threshold exceedances are anomaly flags only; they do not diagnose bearing faults, root cause, severity or remaining life.",
                  "The built-in training and held-out records are synthetic; the envelope requires sensor- and machine-specific review."],
    )


_RUNNERS = {
    "hybrid-powerflow": _powerflow,
    "hybrid-switching": _switching,
    "lessons-energization": _energization,
    "storage-response": _storage_response,
    "storage-agingfit": _aging_fit,
    "compare-thermalphysics": _thermal,
    "pv-raytrace": _raytrace,
    "pv-setbacks": _setbacks,
    "research-bearing": _bearing,
}


def run(study_id: str, inputs: dict) -> dict:
    """Validate an input record and return finite JSON-ready results for one study."""
    if study_id not in _RUNNERS:
        raise ValueError(f"Unknown physical study: {study_id}")
    if not isinstance(inputs, dict):
        raise TypeError("Study inputs must be a JSON object.")
    model = INPUT_MODELS[study_id].model_validate(inputs)
    result = _RUNNERS[study_id](model)
    # This final guard catches accidental NaN/Infinity before an API registry or renderer sees it.
    import json

    json.dumps(result, allow_nan=False)
    return result
