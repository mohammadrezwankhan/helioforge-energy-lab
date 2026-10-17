"""Bounded engineering experiments for the hybrid, storage, PV and research views.

These are transparent educational screens. Inputs are validated independently for
each study; no study is a controller, compliance determination, calibrated model,
or field prediction. All default datasets are explicitly illustrative.
"""
from __future__ import annotations

import json
import math
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
EPDQuantity = Annotated[float, Field(ge=0, le=1_000_000_000_000, allow_inf_nan=False)]
EPDEmissionFactor = Annotated[float, Field(ge=0, le=1_000_000, allow_inf_nan=False)]
DisturbanceKW = Annotated[float, Field(ge=-1_000_000, le=1_000_000, allow_inf_nan=False)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, allow_inf_nan=False)


class ResonanceInput(StrictInput):
    mode_1_hz: float = Field(default=12, ge=1, le=80, allow_inf_nan=False)
    mode_2_hz: float = Field(default=24, ge=1, le=100, allow_inf_nan=False)
    damping_1: float = Field(default=0.04, ge=0.01, le=0.45, allow_inf_nan=False)
    damping_2: float = Field(default=0.07, ge=0.01, le=0.45, allow_inf_nan=False)
    coupling_fraction: float = Field(default=0.15, ge=0, le=0.9, allow_inf_nan=False)


class ClippingInput(StrictInput):
    pv_dc_kw: NonNegative = Field(default=1400, le=100_000)
    inverter_ac_kw: float = Field(default=1000, ge=1, le=100_000, allow_inf_nan=False)
    inverter_efficiency: float = Field(default=0.98, gt=0, le=1, allow_inf_nan=False)
    battery_capacity_kwh: NonNegative = Field(default=500, le=100_000)
    battery_initial_kwh: NonNegative = Field(default=100, le=100_000)
    battery_charge_limit_kw: NonNegative = Field(default=300, le=100_000)

    @model_validator(mode="after")
    def initial_energy_within_capacity(self) -> ClippingInput:
        if self.battery_initial_kwh > self.battery_capacity_kwh:
            raise ValueError("Initial battery energy cannot exceed capacity.")
        return self


class InertiaInput(StrictInput):
    trip_mw: float = Field(default=1000, ge=1, le=20_000, allow_inf_nan=False)
    system_base_mw: float = Field(default=100_000, ge=1000, le=2_000_000, allow_inf_nan=False)
    inertia_seconds: float = Field(default=4, ge=0.1, le=30, allow_inf_nan=False)
    damping_mw_per_hz: NonNegative = Field(default=4000, le=500_000)
    synthetic_inertia_mw_s_per_hz: NonNegative = Field(default=10_000, le=200_000)
    synthetic_inertia_limit_mw: NonNegative = Field(default=1000, le=100_000)


class DegradationInput(StrictInput):
    years: NonNegative = Field(default=8, le=30)
    temperature_c: Finite = Field(default=25, ge=-20, le=60)
    charge_c_rate: NonNegative = Field(default=1, le=5)
    equivalent_full_cycles: NonNegative = Field(default=2400, le=100_000)
    depth_of_discharge_fraction: float = Field(default=0.8, ge=0, le=1, allow_inf_nan=False)


_DEFAULT_PRICE = [80, 72, 65, 60, 58, 62, 80, 105, 120, 110, 95, 85,
                  75, 70, 68, 75, 95, 130, 145, 125, 110, 100, 90, 84]
_DEFAULT_RESERVE_UP_PRICE = [18.0] * 24
_DEFAULT_RESERVE_DOWN_PRICE = [12.0] * 24
_DEFAULT_RESERVE_UP = [0.25] * 24
_DEFAULT_RESERVE_DOWN = [0.25] * 24


class StackingInput(StrictInput):
    capacity_kwh: float = Field(default=10_000, ge=1, le=1_000_000, allow_inf_nan=False)
    power_kw: float = Field(default=5000, ge=1, le=500_000, allow_inf_nan=False)
    round_trip_efficiency: float = Field(default=0.9, ge=0.01, le=1, allow_inf_nan=False)
    initial_soc_fraction: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    interval_hours: Positive = Field(default=1, ge=0.25, le=4)
    reserve_duration_hours: NonNegative = Field(default=0.25, le=4)
    price_eur_mwh: list[Finite] = Field(default_factory=lambda: list(_DEFAULT_PRICE), min_length=2, max_length=168)
    reserve_up_price_eur_mw_h: list[NonNegative] = Field(
        default_factory=lambda: list(_DEFAULT_RESERVE_UP_PRICE), min_length=2, max_length=168)
    reserve_down_price_eur_mw_h: list[NonNegative] = Field(
        default_factory=lambda: list(_DEFAULT_RESERVE_DOWN_PRICE), min_length=2, max_length=168)
    reserve_up_request_mw: list[NonNegative] = Field(
        default_factory=lambda: list(_DEFAULT_RESERVE_UP), min_length=2, max_length=168)
    reserve_down_request_mw: list[NonNegative] = Field(
        default_factory=lambda: list(_DEFAULT_RESERVE_DOWN), min_length=2, max_length=168)

    @model_validator(mode="after")
    def validate_dispatch_bounds(self) -> StackingInput:
        arrays = [self.price_eur_mwh, self.reserve_up_price_eur_mw_h,
                  self.reserve_down_price_eur_mw_h, self.reserve_up_request_mw,
                  self.reserve_down_request_mw]
        if len({len(values) for values in arrays}) != 1:
            raise ValueError("Price, reserve price and requested service arrays must have equal lengths.")
        if not 0.1 <= self.initial_soc_fraction <= 0.9:
            raise ValueError("Initial SOC must be inside the selected SOC limits.")
        return self


class SynergyInput(StrictInput):
    interval_seconds: Positive = Field(default=1, ge=0.1, le=60)
    filter_time_constant_s: NonNegative = Field(default=4, le=600)
    flywheel_power_kw: NonNegative = Field(default=500, le=100_000)
    flywheel_energy_kwh: float = Field(default=20, ge=0.1, le=100_000, allow_inf_nan=False)
    battery_power_kw: NonNegative = Field(default=1000, le=500_000)
    battery_energy_kwh: float = Field(default=4000, ge=0.1, le=1_000_000, allow_inf_nan=False)
    disturbance_kw: list[DisturbanceKW] = Field(default_factory=lambda: [0, 0, 150, 400, 200, 0, -100, 0],
                                         min_length=2, max_length=3600)


_DEFAULT_SUN_ELEVATION = [5, 12, 24, 38, 50, 55, 50, 38, 24, 12, 5]
_DEFAULT_SUN_AZIMUTH = [80, 96, 112, 128, 144, 180, 216, 232, 248, 264, 280]


class BacktrackingInput(StrictInput):
    row_pitch_m: float = Field(default=6, ge=0.1, le=30, allow_inf_nan=False)
    module_width_m: float = Field(default=2.4, ge=0.1, le=10, allow_inf_nan=False)
    tracker_axis_azimuth_deg: Finite = Field(default=0, ge=0, le=360)
    terrain_slope_deg: Finite = Field(default=5, ge=0, le=30)
    terrain_slope_azimuth_deg: Finite = Field(default=90, ge=0, le=360)
    backtracking: int = Field(default=1, ge=0, le=1, strict=True)
    sun_elevation_deg: list[Finite] = Field(default_factory=lambda: list(_DEFAULT_SUN_ELEVATION),
                                             min_length=1, max_length=48)
    sun_azimuth_deg: list[Finite] = Field(default_factory=lambda: list(_DEFAULT_SUN_AZIMUTH),
                                           min_length=1, max_length=48)

    @model_validator(mode="after")
    def validate_sun_series(self) -> BacktrackingInput:
        if len(self.sun_elevation_deg) != len(self.sun_azimuth_deg):
            raise ValueError("Sun elevation and azimuth arrays must have equal lengths.")
        if any(not 0 <= x <= 90 for x in self.sun_elevation_deg):
            raise ValueError("Solar elevation must be between 0 and 90 degrees.")
        if self.module_width_m / self.row_pitch_m > 1:
            raise ValueError("Module width cannot exceed row pitch in this planar row model.")
        return self


_DEFAULT_POLYGON = [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)]


class AgrivoltaicInput(StrictInput):
    ground_coverage_ratio: float = Field(default=0.35, ge=0, le=0.9, allow_inf_nan=False)
    module_transmission_fraction: float = Field(default=0.08, ge=0, le=0.8, allow_inf_nan=False)
    setback_m: NonNegative = Field(default=2, le=100)
    baseline_par_mol_m2_day: float = Field(default=35, ge=0.1, le=100, allow_inf_nan=False)
    land_polygon_m: list[tuple[Finite, Finite]] = Field(default_factory=lambda: list(_DEFAULT_POLYGON),
                                                         min_length=3, max_length=128)

    @model_validator(mode="after")
    def validate_polygon(self) -> AgrivoltaicInput:
        points = self.land_polygon_m
        if len(set(points)) != len(points):
            raise ValueError("Land polygon vertices must be distinct; do not repeat the first vertex at the end.")
        if any(abs(coord) > 100_000 for point in points for coord in point):
            raise ValueError("Land polygon coordinates must stay within ±100 km of the local origin.")
        if _polygon_area(points) <= 1e-9:
            raise ValueError("Land polygon must have non-zero area.")
        n = len(points)
        for i in range(n):
            a, b = points[i], points[(i + 1) % n]
            for j in range(i + 1, n):
                if j in {i, (i + 1) % n} or (j + 1) % n in {i, (i + 1) % n}:
                    continue
                c, d = points[j], points[(j + 1) % n]
                if _segments_intersect(a, b, c, d):
                    raise ValueError("Land polygon must be a simple non-self-intersecting polygon.")
        return self


_DEFAULT_FRONT_IRRADIANCE = [55, 75, 115, 145, 165, 175, 180, 155, 120, 85, 55, 45]
_DEFAULT_REAR_IRRADIANCE = [48, 65, 95, 120, 135, 142, 145, 128, 100, 72, 48, 38]


class AlbedoInput(StrictInput):
    system_capacity_kwp: float = Field(default=5000, ge=1, le=10_000_000, allow_inf_nan=False)
    performance_ratio: float = Field(default=0.82, ge=0.01, le=1, allow_inf_nan=False)
    bifaciality: float = Field(default=0.7, ge=0, le=1, allow_inf_nan=False)
    albedo: float = Field(default=0.25, ge=0, le=1, allow_inf_nan=False)
    rear_view_factor: float = Field(default=0.25, ge=0, le=1, allow_inf_nan=False)
    front_plane_irradiance_kwh_m2: list[NonNegative] = Field(
        default_factory=lambda: list(_DEFAULT_FRONT_IRRADIANCE), min_length=12, max_length=12)
    rear_ground_irradiance_kwh_m2: list[NonNegative] = Field(
        default_factory=lambda: list(_DEFAULT_REAR_IRRADIANCE), min_length=12, max_length=12)


class VibrationInput(StrictInput):
    sample_rate_hz: float = Field(default=256, ge=128, le=20_000, allow_inf_nan=False)
    synthetic_frequency_hz: float = Field(default=24, ge=1, le=10_000, allow_inf_nan=False)
    synthetic_drift_hz: Finite = Field(default=3, ge=-5000, le=5000)
    synthetic_amplitude: NonNegative = Field(default=1, le=1_000_000)
    noise_std: NonNegative = Field(default=0.05, le=1_000_000)
    sample_count: int = Field(default=1024, ge=64, le=8192, strict=True)
    signal: list[Finite] = Field(default_factory=list, max_length=8192)

    @model_validator(mode="after")
    def check_nyquist(self) -> VibrationInput:
        if self.synthetic_frequency_hz >= self.sample_rate_hz / 2:
            raise ValueError("Synthetic frequencies must be below Nyquist.")
        if max(self.synthetic_frequency_hz, self.synthetic_frequency_hz + self.synthetic_drift_hz) >= self.sample_rate_hz / 2:
            raise ValueError("Synthetic spectral drift magnitude must remain below Nyquist.")
        if self.signal and len(self.signal) < 64:
            raise ValueError("A supplied signal must contain at least 64 samples.")
        return self


class EPDRecord(StrictInput):
    record_id: str = Field(min_length=1, max_length=100)
    supplier: str | None = Field(default=None, max_length=200)
    stage: Literal["materials", "manufacturing", "transport", "use", "end_of_life", "other"]
    quantity: EPDQuantity
    unit: str | None = Field(default=None, max_length=40)
    emission_factor_kgco2e_per_unit: EPDEmissionFactor | None = None
    evidence_id: str | None = Field(default=None, max_length=200)
    data_quality: Literal["supplier_primary", "supplier_secondary", "secondary"] = "secondary"


class EPDInput(StrictInput):
    include_materials: int = Field(default=1, ge=0, le=1, strict=True)
    include_manufacturing: int = Field(default=1, ge=0, le=1, strict=True)
    include_transport: int = Field(default=1, ge=0, le=1, strict=True)
    include_use: int = Field(default=1, ge=0, le=1, strict=True)
    include_end_of_life: int = Field(default=1, ge=0, le=1, strict=True)
    include_other: int = Field(default=1, ge=0, le=1, strict=True)
    records: list[EPDRecord] = Field(default_factory=lambda: [
        EPDRecord(record_id="demo-material", supplier="Illustrative supplier", stage="materials",
                  quantity=1000, unit="kg", emission_factor_kgco2e_per_unit=2.1,
                  evidence_id="SYNTHETIC-EXAMPLE-1", data_quality="supplier_secondary"),
        EPDRecord(record_id="demo-transport", supplier="Illustrative carrier", stage="transport",
                  quantity=0.2, unit="t_km", emission_factor_kgco2e_per_unit=75,
                  evidence_id="SYNTHETIC-EXAMPLE-2", data_quality="secondary"),
        EPDRecord(record_id="demo-end-of-life", supplier=None, stage="end_of_life",
                  quantity=1, unit="item", emission_factor_kgco2e_per_unit=None,
                  evidence_id=None, data_quality="secondary"),
    ], max_length=1000)


class SCRInput(StrictInput):
    short_circuit_mva: float = Field(default=600, ge=0.1, le=2_000_000, allow_inf_nan=False)
    plant_mw: float = Field(default=100, ge=0.1, le=2_000_000, allow_inf_nan=False)
    active_power_mw: NonNegative = Field(default=80, le=2_000_000)
    reactive_power_mvar: Finite = Field(default=20, ge=-2_000_000, le=2_000_000)
    voltage_kv: float = Field(default=20, ge=0.1, le=1000, allow_inf_nan=False)
    line_r_ohm: NonNegative = Field(default=0.1, le=100_000)

    @model_validator(mode="after")
    def dispatch_within_rating(self) -> SCRInput:
        if self.active_power_mw > self.plant_mw:
            raise ValueError("Active power cannot exceed the stated plant rating.")
        return self


INPUT_MODELS: dict[str, type[StrictInput]] = {
    "hybrid-resonance": ResonanceInput,
    "hybrid-clipping": ClippingInput,
    "hybrid-inertia": InertiaInput,
    "storage-degradation": DegradationInput,
    "storage-stacking": StackingInput,
    "storage-synergy": SynergyInput,
    "pv-backtracking": BacktrackingInput,
    "pv-agrivoltaic": AgrivoltaicInput,
    "pv-albedo": AlbedoInput,
    "research-vibration": VibrationInput,
    "research-epd": EPDInput,
    "research-scr": SCRInput,
}


def _field(name: str, label: str, default: int | float, minimum: int | float,
           maximum: int | float, step: int | float, unit: str) -> dict:
    return {"name": name, "label": label, "default": default, "min": minimum,
            "max": maximum, "step": step, "unit": unit}


def _data_field(name: str, label: str, default) -> dict:
    return {"name": name, "label": label, "default": default}


STUDIES: list[dict] = [
    {
        "id": "hybrid-resonance", "page": "hybrid", "title": "Coupled oscillation modes",
        "summary": "Inspect poles and a normalized response of two coupled damped modes.",
        "kind": "resonance", "fields": [
            _field("mode_1_hz", "Mode 1 frequency", 12, 1, 80, 1, "Hz"),
            _field("mode_2_hz", "Mode 2 frequency", 24, 1, 100, 1, "Hz"),
            _field("damping_1", "Mode 1 damping ratio", 0.04, 0.01, 0.45, 0.01, "fraction"),
            _field("damping_2", "Mode 2 damping ratio", 0.07, 0.01, 0.45, 0.01, "fraction"),
            _field("coupling_fraction", "Coupling fraction", 0.15, 0, 0.9, 0.01, "fraction"),
        ], "data_fields": [],
        "equations": ["q'' + C q' + K q = u", "det(s²I + sC + K) = 0", "H(jω) = (K − ω²I + jωC)⁻¹"],
        "limitations": ["Two-mode lumped oscillator proxy; parameters are illustrative, not measured inverter/network impedances.",
                        "Pole screening is not EMT simulation, SSR diagnosis, protection coordination or stability certification."],
        "sources": [{"title": "Tutorial on Sub-synchronous Resonance Protection Applied to Inverter Based Renewables (IEEE)",
                     "url": "https://ieeexplore.ieee.org/document/9429840/"}],
    },
    {
        "id": "hybrid-clipping", "page": "hybrid", "title": "DC clipping recovery",
        "summary": "Bound DC-coupled battery charging to PV inverter clipping, battery power and energy headroom.",
        "kind": "clipping", "fields": [
            _field("pv_dc_kw", "Available PV DC", 1400, 0, 100000, 10, "kW"),
            _field("inverter_ac_kw", "Inverter AC rating", 1000, 1, 100000, 10, "kW"),
            _field("inverter_efficiency", "Inverter efficiency", 0.98, 0.01, 1, 0.01, "fraction"),
            _field("battery_capacity_kwh", "Battery capacity", 500, 0, 100000, 10, "kWh"),
            _field("battery_initial_kwh", "Initial battery energy", 100, 0, 100000, 10, "kWh"),
            _field("battery_charge_limit_kw", "Battery charge limit", 300, 0, 100000, 10, "kW"),
        ], "data_fields": [],
        "equations": ["Pdc,inverter limit = Pac,rated / ηinv", "Pclip = max(0, Ppv − Pdc,inverter limit)",
                      "Pcharge = min(Pclip, Pcharge,max, (Emax − E0)/(ηcharge Δt))", "E1 = E0 + ηcharge Pcharge Δt"],
        "limitations": ["Single interval, DC-side energy balance; no battery discharge, thermal limits, voltage-window or detailed inverter topology.",
                        "Recovered energy is a physical screening quantity, not a dispatch forecast or project value."],
        "sources": [{"title": "NREL System Advisor Model: PV and battery system models", "url": "https://sam.nrel.gov/photovoltaic.html"}],
    },
    {
        "id": "hybrid-inertia", "page": "hybrid", "title": "Synthetic inertia and RoCoF",
        "summary": "Integrate an aggregate swing model after a generation trip with bounded droop and derivative response.",
        "kind": "frequency", "fields": [
            _field("trip_mw", "Generation trip", 1000, 1, 20000, 50, "MW"),
            _field("system_base_mw", "System base", 100000, 1000, 2000000, 1000, "MW"),
            _field("inertia_seconds", "Aggregate inertia", 4, 0.1, 30, 0.1, "s"),
            _field("damping_mw_per_hz", "Load damping", 4000, 0, 500000, 100, "MW/Hz"),
            _field("synthetic_inertia_mw_s_per_hz", "Synthetic inertia gain", 10000, 0, 200000, 500, "MW·s/Hz"),
            _field("synthetic_inertia_limit_mw", "Synthetic response limit", 1000, 0, 100000, 50, "MW"),
        ], "data_fields": [],
        "equations": ["df/dt = f0/(2 H Sbase) · (Pgov + Psyn − ΔPtrip − D Δf)",
                      "Psyn = clip(−Msynthetic · df/dt, 0, Psynthetic,max)",
                      "dPgov/dt = (clip(Kdroop · max(−Δf,0),0,Preserve) − Pgov)/τ"],
        "limitations": ["Reduced-order aggregate frequency response; fixed trip and simplified governor/derivative service.",
                        "Not an EMT simulator, protection study, grid-code assessment or certified inertia requirement."],
        "sources": [{"title": "Fast Frequency Response Concepts and Bulk Power System Reliability Needs (NREL)",
                     "url": "https://www.nlr.gov/grid/ieee-standard-1547/bulk-power-reliability-needs"}],
    },
    {
        "id": "storage-degradation", "page": "storage", "title": "Separate battery aging mechanisms",
        "summary": "Compare uncalibrated calendar SEI, low-temperature plating and cycling-fatigue contributions.",
        "kind": "degradation", "fields": [
            _field("years", "Elapsed time", 8, 0, 30, 1, "years"),
            _field("temperature_c", "Mean temperature", 25, -20, 60, 1, "°C"),
            _field("charge_c_rate", "Charge C-rate", 1, 0, 5, 0.1, "C"),
            _field("equivalent_full_cycles", "Equivalent full cycles", 2400, 0, 100000, 100, "cycles"),
            _field("depth_of_discharge_fraction", "Depth of discharge", 0.8, 0, 1, 0.01, "fraction"),
        ], "data_fields": [],
        "equations": ["LSEI = kSEI √t · 2^((T−25°C)/10°C)",
                      "Lplating = kplate · t · (C-rate/2)² · max(0,(15°C−T)/25°C)",
                      "Lfatigue = kfatigue · EFC · (0.5 + 0.5 DOD)"],
        "limitations": ["Mechanism terms are independently parameterized, additive screening proxies and intentionally uncalibrated.",
                        "No cell chemistry, SOC history, charge protocol, coupled electrochemistry, uncertainty or warranty prediction."],
        "sources": [{"title": "Coupling Lithium Plating with SEI Formation in a Pseudo-3D Model (Journal of The Electrochemical Society)",
                     "url": "https://doi.org/10.1149/1945-7111/ac716a"},
                    {"title": "A Generic Cycle Life Model Based on Fatigue Theory and Equivalent Cycle Counting (IEEE OJIES)",
                     "url": "https://doi.org/10.1109/OJIES.2020.3015396"}],
    },
    {
        "id": "storage-stacking", "page": "storage", "title": "Reserve and arbitrage headroom",
        "summary": "Bound an illustrative reserve-plus-arbitrage dispatch against explicit price and service arrays.",
        "kind": "stacking", "fields": [
            _field("capacity_kwh", "Usable energy capacity", 10000, 1, 1000000, 100, "kWh"),
            _field("power_kw", "Power rating", 5000, 1, 500000, 50, "kW"),
            _field("round_trip_efficiency", "Round-trip efficiency", 0.9, 0.01, 1, 0.01, "fraction"),
            _field("initial_soc_fraction", "Initial SOC", 0.5, 0, 1, 0.01, "fraction"),
            _field("interval_hours", "Interval duration", 1, 0.25, 4, 0.25, "h"),
            _field("reserve_duration_hours", "Reserve activation duration", 0.25, 0, 4, 0.25, "h"),
        ], "data_fields": [
            _data_field("price_eur_mwh", "Energy price (€/MWh)", _DEFAULT_PRICE),
            _data_field("reserve_up_price_eur_mw_h", "Upward reserve price (€/MW·h)", _DEFAULT_RESERVE_UP_PRICE),
            _data_field("reserve_down_price_eur_mw_h", "Downward reserve price (€/MW·h)", _DEFAULT_RESERVE_DOWN_PRICE),
            _data_field("reserve_up_request_mw", "Requested upward service (MW)", _DEFAULT_RESERVE_UP),
            _data_field("reserve_down_request_mw", "Requested downward service (MW)", _DEFAULT_RESERVE_DOWN),
        ],
        "equations": ["maximize Σ(price·(d−c)·Δt/1000 + reserve_price·reserve_MW·Δt)",
                      "SOC[t+1] = SOC[t] + ηc c[t]Δt − d[t]Δt/ηd", "SOC[T] = SOC[0]",
                      "c + d + r_up + r_down ≤ P; reserve energy margins use stated activation duration"],
        "limitations": ["Illustrative perfect-foresight MILP with conservative simultaneous headroom and one terminal-SOC constraint.",
                        "Reserve quantities and prices are user assumptions; no market eligibility, bid acceptance, availability, penalties, taxes or annualization."],
        "sources": [{"title": "NREL Annual Technology Baseline: storage uses and revenue streams", "url": "https://atb.nrel.gov/electricity/2024/utility-scale_battery_storage"}],
    },
    {
        "id": "storage-synergy", "page": "storage", "title": "Flywheel and battery split-frequency dispatch",
        "summary": "Route high-frequency disturbance to a flywheel and the residual to a bounded battery, tracking both energy states.",
        "kind": "synergy", "fields": [
            _field("interval_seconds", "Sample interval", 1, 0.1, 60, 0.1, "s"),
            _field("filter_time_constant_s", "Frequency split time constant", 4, 0, 600, 0.5, "s"),
            _field("flywheel_power_kw", "Flywheel power limit", 500, 0, 100000, 10, "kW"),
            _field("flywheel_energy_kwh", "Flywheel energy capacity", 20, 0.1, 100000, 1, "kWh"),
            _field("battery_power_kw", "Battery power limit", 1000, 0, 500000, 10, "kW"),
            _field("battery_energy_kwh", "Battery energy capacity", 4000, 0.1, 1000000, 10, "kWh"),
        ], "data_fields": [_data_field("disturbance_kw", "Requested power trace (+ discharge / − charge; ±1 GW/sample)",
                                           [0, 0, 150, 400, 200, 0, -100, 0])],
        "equations": ["ℓ[t] = ℓ[t−1] + α(P[t]−ℓ[t−1]); α = Δt/(τ+Δt)",
                      "Pflywheel,request = P−ℓ; Pbattery,request = P−Pflywheel",
                      "E[t+1] = E[t] − PΔt/ηd for P≥0; E[t+1] = E[t] − PηcΔt for P<0"],
        "limitations": ["A first-order frequency split and sequential clipping are transparent dispatch proxies, not an optimized controller.",
                        "No voltage, thermal, ramp, converter, degradation, coupled control or field response validation."],
        "sources": [{"title": "DOE Energy Storage: Technology Basics", "url": "https://www.energy.gov/oe/energy-storage"}],
    },
    {
        "id": "pv-backtracking", "page": "pv", "title": "Slope-aware tracker backtracking screen",
        "summary": "Compare ideal tracker angles with a planar row-shadow backtracking correction over supplied sun positions.",
        "kind": "tracker", "fields": [
            _field("row_pitch_m", "Row pitch", 6, 0.1, 30, 0.1, "m"),
            _field("module_width_m", "Collector width", 2.4, 0.1, 10, 0.1, "m"),
            _field("tracker_axis_azimuth_deg", "Tracker-axis azimuth", 0, 0, 360, 1, "°"),
            _field("terrain_slope_deg", "Terrain slope", 5, 0, 30, 1, "°"),
            _field("terrain_slope_azimuth_deg", "Terrain downslope azimuth", 90, 0, 360, 1, "°"),
            _field("backtracking", "Apply backtracking correction", 1, 0, 1, 1, "0/1"),
        ], "data_fields": [
            _data_field("sun_elevation_deg", "Solar elevation (°)", _DEFAULT_SUN_ELEVATION),
            _data_field("sun_azimuth_deg", "Solar azimuth (°)", _DEFAULT_SUN_AZIMUTH),
        ],
        "equations": ["βcross = atan(tan(slope) · sin(azslope − azaxis))",
                      "θideal = atan2(sun_cross · cosβ + sun_up · sinβ, −sun_cross · sinβ + sun_up · cosβ)",
                      "θbt = θideal − sign(θideal) arccos(|cos θideal|/GCR) when |cos θideal| < GCR"],
        "limitations": ["A two-dimensional planar row geometry with a cross-slope projection; edge effects, tracker limits and terrain variation are omitted.",
                        "NREL's slope-aware method includes full reference frames and shaded-fraction treatment; this screen is not its implementation or an energy-yield model."],
        "sources": [{"title": "Slope-Aware Backtracking for Single-Axis Trackers (NREL/TP-5K00-76626)",
                     "url": "https://docs.nrel.gov/docs/fy20osti/76626.pdf"}],
    },
    {
        "id": "pv-agrivoltaic", "page": "pv", "title": "Agrivoltaic PAR and land geometry",
        "summary": "Screen a simple crop-light tradeoff and polygon land area after a conservative perimeter setback deduction.",
        "kind": "agrivoltaic", "fields": [
            _field("ground_coverage_ratio", "Ground coverage ratio", 0.35, 0, 0.9, 0.01, "fraction"),
            _field("module_transmission_fraction", "Module PAR transmission", 0.08, 0, 0.8, 0.01, "fraction"),
            _field("setback_m", "Illustrative setback", 2, 0, 100, 0.5, "m"),
            _field("baseline_par_mol_m2_day", "Open-field daily PAR", 35, 0.1, 100, 0.5, "mol/m²/day"),
        ], "data_fields": [_data_field("land_polygon_m", "Local land-boundary polygon vertices (m)", _DEFAULT_POLYGON)],
        "equations": ["A = ½ |Σ(xᵢyᵢ₊₁ − xᵢ₊₁yᵢ)|", "Ausable ≈ max(0, A − perimeter·setback)",
                      "PARcrop ≈ PARopen · [1 − GCR · (1 − module transmission)]"],
        "limitations": ["Perimeter setback subtraction is a conservative area proxy, not an exact polygon offset or cadastral calculation.",
                        "PAR proxy omits time-of-day geometry, crop response, spectral effects, diffuse light, row spacing, equipment access and yield validation."],
        "sources": [{"title": "Adapting Agrivoltaics (NREL)", "url": "https://www.nrel.gov/docs/fy24osti/88444.pdf"}],
    },
    {
        "id": "pv-albedo", "page": "pv", "title": "Monthly bifacial albedo response",
        "summary": "Combine monthly front-plane and reflected rear irradiance with bifaciality, albedo, view factor and PR.",
        "kind": "bifacial", "fields": [
            _field("system_capacity_kwp", "System DC capacity", 5000, 1, 10000000, 100, "kWp"),
            _field("performance_ratio", "Performance ratio", 0.82, 0.01, 1, 0.01, "fraction"),
            _field("bifaciality", "Rear/front response ratio", 0.7, 0, 1, 0.01, "fraction"),
            _field("albedo", "Ground albedo", 0.25, 0, 1, 0.01, "fraction"),
            _field("rear_view_factor", "Rear ground view factor", 0.25, 0, 1, 0.01, "fraction"),
        ], "data_fields": [
            _data_field("front_plane_irradiance_kwh_m2", "Monthly front-plane irradiation", _DEFAULT_FRONT_IRRADIANCE),
            _data_field("rear_ground_irradiance_kwh_m2", "Monthly rear ground irradiation before albedo", _DEFAULT_REAR_IRRADIANCE),
        ],
        "equations": ["Grear = Gground · albedo · rear_view_factor", "Efront,m = Pdc · PR · Gfront,m",
                      "Etotal,m = Pdc · PR · (Gfront,m + bifaciality · Grear,m)", "Eyear = Σₘ Etotal,m"],
        "limitations": ["Monthly scalar irradiance screen; rear view factor and PR are user assumptions, not ray tracing or site meteorology.",
                        "No electrical mismatch, row shading, temperature, spectral, terrain or measured validation; annual energy is only as representative as the supplied 12 months."],
        "sources": [{"title": "Photovoltaic Bifacial Irradiance and Performance Modeling Toolkit (NREL)",
                     "url": "https://www.nrel.gov/pv/pv-bifacial-irradiance-toolkit"}],
    },
    {
        "id": "research-vibration", "page": "research", "title": "Vibration spectrum and drift",
        "summary": "Estimate one-sided FFT amplitudes and compare early/late half-record spectral peaks.",
        "kind": "vibration", "fields": [
            _field("sample_rate_hz", "Sample rate", 256, 128, 20000, 1, "Hz"),
            _field("synthetic_frequency_hz", "Synthetic primary frequency", 24, 1, 10000, 1, "Hz"),
            _field("synthetic_drift_hz", "Synthetic sweep across record", 3, -5000, 5000, 0.1, "Hz"),
            _field("synthetic_amplitude", "Primary amplitude", 1, 0, 1000000, 0.1, "signal unit"),
            _field("noise_std", "Synthetic noise standard deviation", 0.05, 0, 1000000, 0.01, "signal unit"),
            _field("sample_count", "Synthetic sample count", 1024, 64, 8192, 64, "samples"),
        ], "data_fields": [_data_field("signal", "Supplied evenly spaced signal (empty uses seeded synthetic signal)", [])],
        "equations": ["X[k] = Σₙ x[n] exp(−j 2πkn/N)", "A[k] = 2|X[k]|/Σw[n] for interior one-sided bins",
                      "Spectral drift = late-half dominant frequency − early-half dominant frequency"],
        "limitations": ["Single evenly spaced, finite record with a Hann window; half-window frequency resolution is limited.",
                        "Peaks and drift are descriptive spectrum statistics, not a fault classifier, causal diagnosis or maintenance recommendation."],
        "sources": [{"title": "Discrete Fourier transform and spectral analysis (SciPy User Guide)",
                     "url": "https://docs.scipy.org/doc/scipy/tutorial/signal.html"}],
    },
    {
        "id": "research-epd", "page": "research", "title": "Supplier-stage emissions evidence ledger",
        "summary": "Sum supplied supplier-stage quantities and factors while surfacing duplicate IDs and missing evidence.",
        "kind": "epd", "fields": [
            _field("include_materials", "Include materials stage", 1, 0, 1, 1, "0/1"),
            _field("include_manufacturing", "Include manufacturing stage", 1, 0, 1, 1, "0/1"),
            _field("include_transport", "Include transport stage", 1, 0, 1, 1, "0/1"),
            _field("include_use", "Include use stage", 1, 0, 1, 1, "0/1"),
            _field("include_end_of_life", "Include end-of-life stage", 1, 0, 1, 1, "0/1"),
            _field("include_other", "Include other stage", 1, 0, 1, 1, "0/1"),
        ], "data_fields": [
            _data_field("records", "Supplier-stage records (quantity ≤1e12; factor ≤1e6 kgCO₂e/unit)", [
                {"record_id": "demo-material", "supplier": "Illustrative supplier", "stage": "materials",
                 "quantity": 1000, "unit": "kg", "emission_factor_kgco2e_per_unit": 2.1,
                 "evidence_id": "SYNTHETIC-EXAMPLE-1", "data_quality": "supplier_secondary"},
                {"record_id": "demo-transport", "supplier": "Illustrative carrier", "stage": "transport",
                 "quantity": 0.2, "unit": "t_km", "emission_factor_kgco2e_per_unit": 75,
                 "evidence_id": "SYNTHETIC-EXAMPLE-2", "data_quality": "secondary"},
                {"record_id": "demo-end-of-life", "supplier": None, "stage": "end_of_life", "quantity": 1,
                 "unit": "item", "emission_factor_kgco2e_per_unit": None, "evidence_id": None,
                 "data_quality": "secondary"},
            ])
        ],
        "equations": ["Stage emissionsᵢ = quantityᵢ · supplier/activity factorᵢ", "Total included emissions = Σ unique, factor-complete stage records"],
        "limitations": ["Per-record quantities are bounded at 1e12 declared units and factors at 1e6 kgCO₂e per declared unit to keep the arithmetic finite; choose and document suitable units.",
                        "A traceable arithmetic ledger only: it does not verify EPD validity, product-category rules, allocation, boundary, assurance or Scope 3 category.",
                        "Duplicate IDs retain only their first row; missing factors are reported and excluded, not imputed. Example defaults are synthetic."],
        "sources": [{"title": "Category 1 Purchased Goods and Services: Scope 3 Calculation Guidance (GHG Protocol)",
                     "url": "https://ghgprotocol.org/sites/default/files/standards/Scope3_Calculation_Guidance_0.pdf"}],
    },
    {
        "id": "research-scr", "page": "research", "title": "Short-circuit strength and voltage drop",
        "summary": "Calculate a simple Ssc/P screening ratio and a balanced small-voltage-drop estimate from R, X, P and Q.",
        "kind": "grid-strength", "fields": [
            _field("short_circuit_mva", "Grid short-circuit capacity", 600, 0.1, 2000000, 10, "MVA"),
            _field("plant_mw", "Plant active-power rating", 100, 0.1, 2000000, 1, "MW"),
            _field("active_power_mw", "Operating active power", 80, 0, 2000000, 1, "MW"),
            _field("reactive_power_mvar", "Operating reactive power", 20, -2000000, 2000000, 1, "Mvar"),
            _field("voltage_kv", "Line-to-line voltage", 20, 0.1, 1000, 0.1, "kV"),
            _field("line_r_ohm", "Equivalent series resistance", 0.1, 0, 100000, 0.01, "Ω/phase"),
        ], "data_fields": [],
        "equations": ["SCRscreen = Ssc / Pplant", "ΔVpu ≈ (R P + X Q)/VLL²", "|Zth| ≈ VLL²/Ssc"],
        "limitations": ["Classical single-infeed ratio and balanced first-order voltage-drop approximation only.",
                        "SCR is not a stability guarantee; interactions, loads, X/R, controls, protection and operating points require detailed network and dynamic studies."],
        "sources": [{"title": "Experimental Evaluation of SCR and X/R Ratio on GFM and GFL Inverters (IEEE PESGM)",
                     "url": "https://ieeexplore.ieee.org/document/11225025/"},
                    {"title": "Grid Strength Assessment in Weak Distribution Systems: Beyond Short Circuit Ratio (IEEE PESGM)",
                     "url": "https://ieeexplore.ieee.org/abstract/document/11693070/"}],
    },
]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1]
                   - points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points))) / 2)


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a, b, c, d) -> bool:
    epsilon = 1e-9

    def on_segment(start, end, point) -> bool:
        return (abs(_orientation(start, end, point)) <= epsilon
                and min(start[0], end[0]) - epsilon <= point[0] <= max(start[0], end[0]) + epsilon
                and min(start[1], end[1]) - epsilon <= point[1] <= max(start[1], end[1]) + epsilon)

    orientations = (_orientation(a, b, c), _orientation(a, b, d),
                    _orientation(c, d, a), _orientation(c, d, b))
    if ((orientations[0] > epsilon and orientations[1] < -epsilon
         or orientations[0] < -epsilon and orientations[1] > epsilon)
            and (orientations[2] > epsilon and orientations[3] < -epsilon
                 or orientations[2] < -epsilon and orientations[3] > epsilon)):
        return True
    return ((abs(orientations[0]) <= epsilon and on_segment(a, b, c))
            or (abs(orientations[1]) <= epsilon and on_segment(a, b, d))
            or (abs(orientations[2]) <= epsilon and on_segment(c, d, a))
            or (abs(orientations[3]) <= epsilon and on_segment(c, d, b)))


def _answer(metrics: list[dict], *, series: list[dict] | None = None,
            table: list[dict] | None = None, details: dict | None = None,
            warnings: list[str] | None = None) -> dict:
    result = {"metrics": metrics, "series": series or [], "table": table or [],
              "details": details or {}, "warnings": warnings or []}
    # Fail closed if a future calculation accidentally creates NaN/Infinity or a non-JSON value.
    json.dumps(result, allow_nan=False)
    return result


def _m(label: str, value: float | int | str | None, unit: str) -> dict:
    if isinstance(value, (float, np.floating)):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite result for {label}.")
    return {"label": label, "value": value, "unit": unit}


def _resonance(p: ResonanceInput) -> dict:
    w1, w2 = 2 * math.pi * p.mode_1_hz, 2 * math.pi * p.mode_2_hz
    stiffness = np.array([[w1 * w1, p.coupling_fraction * w1 * w2],
                          [p.coupling_fraction * w1 * w2, w2 * w2]], dtype=float)
    damping = np.diag([2 * p.damping_1 * w1, 2 * p.damping_2 * w2])
    identity = np.eye(2)
    zeros = np.zeros((2, 2))
    state_matrix = np.block([[zeros, identity], [-stiffness, -damping]])
    poles = np.linalg.eigvals(state_matrix)
    positive_imaginary = sorted((pole for pole in poles if pole.imag > 1e-8), key=lambda pole: pole.imag)
    modes = [{"real_per_s": float(pole.real), "imag_per_s": float(pole.imag),
              "frequency_hz": float(abs(pole) / (2 * math.pi)),
              "damping_ratio": float(-pole.real / abs(pole)), "stable": bool(pole.real < 0)}
             for pole in positive_imaginary]
    frequencies_hz = np.linspace(0.1, max(p.mode_1_hz, p.mode_2_hz) * 2, 96)
    response = []
    forcing = np.array([1.0, 0.0], dtype=complex)
    for frequency in frequencies_hz:
        omega = 2 * math.pi * frequency
        transfer = np.linalg.solve(stiffness - omega * omega * identity + 1j * omega * damping, forcing)
        response.append(float(abs(transfer[0])))
    max_response_index = int(np.argmax(response))
    min_damping = min((mode["damping_ratio"] for mode in modes), default=None)
    return _answer([
        _m("Oscillatory pole count", len(modes), "poles"),
        _m("Minimum modal damping ratio", min_damping, "fraction"),
        _m("Peak normalized response frequency", frequencies_hz[max_response_index], "Hz"),
    ], series=[{"name": "Normalized mode-1 response", "x_label": "Frequency (Hz)",
                "y_unit": "normalized displacement per force", "x": frequencies_hz.tolist(), "y": response}],
        details={"mode_1_hz": p.mode_1_hz, "mode_2_hz": p.mode_2_hz, "modes": modes,
                 "all_eigenvalues": [{"real_per_s": float(x.real), "imag_per_s": float(x.imag)} for x in poles],
                 "coupled_stiffness_rad2_s2": stiffness.tolist(), "damping_matrix_per_s": damping.tolist()},
        warnings=["Coupled damped oscillator eigenvalues are a normalized proxy, not inverter impedance data or SSR certification."])


def _clipping(p: ClippingInput) -> dict:
    interval_hours, charge_efficiency = 1.0, 0.96
    inverter_dc_limit_kw = p.inverter_ac_kw / p.inverter_efficiency
    inverter_dc_kw = min(p.pv_dc_kw, inverter_dc_limit_kw)
    clipped_dc_kw = max(0.0, p.pv_dc_kw - inverter_dc_kw)
    headroom_kwh = max(0.0, p.battery_capacity_kwh - p.battery_initial_kwh)
    charge_dc_kw = min(clipped_dc_kw, p.battery_charge_limit_kw,
                       headroom_kwh / (charge_efficiency * interval_hours))
    charge_dc_kwh = charge_dc_kw * interval_hours
    stored_kwh = charge_dc_kwh * charge_efficiency
    clipped_kwh = clipped_dc_kw * interval_hours
    curtailed_kwh = max(0.0, clipped_kwh - charge_dc_kwh)
    direct_ac_kwh = inverter_dc_kw * p.inverter_efficiency * interval_hours
    dc_balance_residual = p.pv_dc_kw * interval_hours - inverter_dc_kw * interval_hours - charge_dc_kwh - curtailed_kwh
    dc_sweep = np.linspace(0, max(p.pv_dc_kw, 2 * inverter_dc_limit_kw), 60)
    ilr_sweep = dc_sweep / p.inverter_ac_kw
    clipped_ac_sweep = np.maximum(0.0, dc_sweep - inverter_dc_limit_kw) * p.inverter_efficiency
    return _answer([
        _m("DC-to-AC inverter loading ratio", p.pv_dc_kw / p.inverter_ac_kw, "kWp/kWac"),
        _m("PV direct AC energy", direct_ac_kwh, "kWh"),
        _m("Clipped DC energy available", clipped_kwh, "kWh DC"),
        _m("Clipped DC energy recovered", stored_kwh, "kWh stored"),
        _m("Unrecovered clipped DC energy", curtailed_kwh, "kWh DC"),
        _m("Ending battery energy", p.battery_initial_kwh + stored_kwh, "kWh"),
    ], table=[{"flow": "PV DC input", "energy_kwh": p.pv_dc_kw * interval_hours},
             {"flow": "Inverter DC input", "energy_kwh": inverter_dc_kw * interval_hours},
             {"flow": "Battery charge DC", "energy_kwh": charge_dc_kwh},
             {"flow": "Unrecovered clipping", "energy_kwh": curtailed_kwh}],
        series=[{"name": "AC-equivalent clipped power vs DC ILR", "x_label": "DC-to-AC ratio (kWp/kWac)",
                 "y_unit": "kW AC", "x": ilr_sweep.tolist(), "y": clipped_ac_sweep.tolist()}],
        details={"inverter_dc_limit_kw": inverter_dc_limit_kw, "inverter_dc_input_kw": inverter_dc_kw,
                 "battery_charge_dc_kw": charge_dc_kw, "battery_stored_energy_gain_kwh": stored_kwh,
                 "dc_balance_residual_kwh": dc_balance_residual,
                 "fixed_interval_hours": interval_hours, "fixed_charge_efficiency": charge_efficiency},
        warnings=["One-interval DC bus balance; no battery discharge, detailed DC/DC conversion, thermal constraints or inverter voltage limits."])


def _inertia(p: InertiaInput) -> dict:
    dt, horizon_seconds, nominal_frequency_hz = 0.02, 15.0, 50.0
    governor_droop_mw_per_hz, governor_reserve_mw, governor_time_constant_s = 5000.0, 1500.0, 0.8
    count = int(math.ceil(horizon_seconds / dt))
    times = np.linspace(0.0, count * dt, count + 1)
    frequency_deviation = 0.0
    governor_mw = 0.0
    frequency_path: list[float] = []
    rocof_path: list[float] = []
    synthetic_path: list[float] = []
    governor_path: list[float] = []
    coefficient = nominal_frequency_hz / (2 * p.inertia_seconds * p.system_base_mw)

    def swing_rocof(df_hz: float, pgov: float) -> tuple[float, float]:
        non_inertial = pgov - p.trip_mw - p.damping_mw_per_hz * df_hz
        base = coefficient * non_inertial
        if base < 0 and p.synthetic_inertia_mw_s_per_hz > 0:
            unsaturated = base / (1 + coefficient * p.synthetic_inertia_mw_s_per_hz)
            desired = -p.synthetic_inertia_mw_s_per_hz * unsaturated
            if desired <= p.synthetic_inertia_limit_mw:
                return unsaturated, desired
            return coefficient * (non_inertial + p.synthetic_inertia_limit_mw), p.synthetic_inertia_limit_mw
        return base, 0.0

    def derivative(state: tuple[float, float]) -> tuple[float, float]:
        df, pgov = state
        rocof, _ = swing_rocof(df, pgov)
        governor_target = min(governor_reserve_mw, governor_droop_mw_per_hz * max(0.0, -df))
        return rocof, (governor_target - pgov) / governor_time_constant_s

    for index in range(count + 1):
        rocof, synthetic = swing_rocof(frequency_deviation, governor_mw)
        frequency_path.append(nominal_frequency_hz + frequency_deviation)
        rocof_path.append(rocof)
        synthetic_path.append(synthetic)
        governor_path.append(governor_mw)
        if index == count:
            break
        state = (frequency_deviation, governor_mw)
        k1 = derivative(state)
        k2 = derivative((state[0] + dt * k1[0] / 2, state[1] + dt * k1[1] / 2))
        k3 = derivative((state[0] + dt * k2[0] / 2, state[1] + dt * k2[1] / 2))
        k4 = derivative((state[0] + dt * k3[0], state[1] + dt * k3[1]))
        frequency_deviation += dt * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        governor_mw = min(governor_reserve_mw, max(0.0, governor_mw + dt * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6))
    min_frequency = min(frequency_path)
    return _answer([
        _m("Initial RoCoF", rocof_path[0], "Hz/s"),
        _m("Maximum absolute RoCoF", max(abs(x) for x in rocof_path), "Hz/s"),
        _m("Minimum frequency", min_frequency, "Hz"),
        _m("Frequency nadir deviation", nominal_frequency_hz - min_frequency, "Hz"),
        _m("Peak synthetic inertia response", max(synthetic_path), "MW"),
        _m("Peak governor response", max(governor_path), "MW"),
    ], series=[{"name": "Frequency", "x_label": "Time (s)", "y_unit": "Hz", "x": times.tolist(), "y": frequency_path},
              {"name": "RoCoF", "x_label": "Time (s)", "y_unit": "Hz/s", "x": times.tolist(), "y": rocof_path},
              {"name": "Synthetic inertia response", "x_label": "Time (s)", "y_unit": "MW", "x": times.tolist(), "y": synthetic_path}],
        details={"time_s": times.tolist(), "frequency_hz": frequency_path, "rocof_hz_per_s": rocof_path,
                 "synthetic_inertia_mw": synthetic_path, "governor_response_mw": governor_path,
                 "integration": "fixed-step RK4", "step_seconds": dt,
                 "horizon_seconds": horizon_seconds, "nominal_frequency_hz": nominal_frequency_hz,
                 "fixed_governor_droop_mw_per_hz": governor_droop_mw_per_hz,
                 "fixed_governor_reserve_mw": governor_reserve_mw,
                 "fixed_governor_time_constant_seconds": governor_time_constant_s},
        warnings=["Synthetic reduced-order swing/droop model for an illustrative 1 GW trip; not EMT, protection or frequency-security certification."])


def _degradation(p: DegradationInput) -> dict:
    sei_rate_per_sqrt_year, plating_rate_per_c_rate_squared_year, fatigue_loss_per_efc = 0.006, 0.0002, 0.000002
    sei = sei_rate_per_sqrt_year * math.sqrt(p.years) * 2 ** ((p.temperature_c - 25) / 10)
    plating = (plating_rate_per_c_rate_squared_year * p.years * (p.charge_c_rate / 2) ** 2
               * max(0.0, (15 - p.temperature_c) / 25))
    fatigue = fatigue_loss_per_efc * p.equivalent_full_cycles * (0.5 + 0.5 * p.depth_of_discharge_fraction)
    total = min(0.95, sei + plating + fatigue)
    losses = {"sei": sei, "plating": plating, "fatigue": fatigue}
    return _answer([
        _m("SEI calendar contribution", sei * 100, "% capacity"),
        _m("Lithium-plating contribution", plating * 100, "% capacity"),
        _m("Cycling-fatigue contribution", fatigue * 100, "% capacity"),
        _m("Total modeled capacity loss", total * 100, "% capacity"),
        _m("Remaining normalized capacity", 1 - total, "fraction"),
    ], table=[{"mechanism": name, "loss_pct": value * 100} for name, value in losses.items()],
        details={"loss_fraction_by_mechanism": losses, "uncapped_sum_fraction": sei + plating + fatigue,
                 "capacity_loss_cap_fraction": 0.95},
        warnings=["Mechanism coefficients are user-editable illustrative values, not calibrated cell-life predictions.",
                  "Terms are added independently; interactions, SOC history, chemistry and operating protocol are omitted."])


def _stacking(p: StackingInput) -> dict:
    n, dt = len(p.price_eur_mwh), p.interval_hours
    eta = math.sqrt(p.round_trip_efficiency)
    charge = np.arange(n)
    discharge = np.arange(n, 2 * n)
    up = np.arange(2 * n, 3 * n)
    down = np.arange(3 * n, 4 * n)
    soc = np.arange(4 * n, 5 * n + 1)
    mode = np.arange(5 * n + 1, 6 * n + 1)
    size = 6 * n + 1
    objective = np.zeros(size)
    objective[charge] = np.asarray(p.price_eur_mwh) * dt / 1000
    objective[discharge] = -np.asarray(p.price_eur_mwh) * dt / 1000
    objective[up] = -np.asarray(p.reserve_up_price_eur_mw_h) * dt
    objective[down] = -np.asarray(p.reserve_down_price_eur_mw_h) * dt
    lower, upper = np.zeros(size), np.full(size, np.inf)
    power_mw = p.power_kw / 1000
    upper[charge] = upper[discharge] = p.power_kw
    upper[up] = np.asarray(p.reserve_up_request_mw)
    upper[down] = np.asarray(p.reserve_down_request_mw)
    soc_min, soc_max = p.capacity_kwh * 0.1, p.capacity_kwh * 0.9
    lower[soc], upper[soc] = soc_min, soc_max
    initial = p.capacity_kwh * p.initial_soc_fraction
    lower[soc[0]] = upper[soc[0]] = initial
    lower[soc[-1]] = upper[soc[-1]] = initial
    upper[mode] = 1
    integrality = np.zeros(size, dtype=int)
    integrality[mode] = 1
    matrix = lil_matrix((6 * n, size), dtype=float)
    lo = np.full(6 * n, -np.inf)
    hi = np.full(6 * n, np.inf)
    row = 0
    for t in range(n):
        # Conservative headroom reserves power for both offered directions and energy for the named activation duration.
        matrix[row, [charge[t], discharge[t], up[t], down[t]]] = [1, 1, 1000, 1000]
        hi[row] = p.power_kw
        row += 1
        matrix[row, [charge[t], mode[t]]] = [1, -p.power_kw]
        hi[row] = 0
        row += 1
        matrix[row, [discharge[t], mode[t]]] = [1, p.power_kw]
        hi[row] = p.power_kw
        row += 1
        matrix[row, [soc[t + 1], soc[t], charge[t], discharge[t]]] = [1, -1, -eta * dt, dt / eta]
        lo[row] = hi[row] = 0
        row += 1
        matrix[row, [soc[t], up[t]]] = [1, -1000 * p.reserve_duration_hours / eta]
        lo[row] = soc_min
        row += 1
        matrix[row, [soc[t], down[t]]] = [1, 1000 * p.reserve_duration_hours * eta]
        hi[row] = soc_max
        row += 1
    # Reserve margins need not be zero-duration arbitrage; the variables are held at their requested capacity for the full duration.
    constraints = LinearConstraint(matrix.tocsr(), lo[:row], hi[:row])
    solved = milp(objective, integrality=integrality, bounds=Bounds(lower, upper), constraints=constraints,
                  options={"time_limit": 10.0, "mip_rel_gap": 1e-8})
    if not solved.success or solved.x is None:
        raise ValueError("No feasible storage reserve/arbitrage schedule under the supplied SOC and service limits.")
    x = solved.x
    rows = []
    for t in range(n):
        rows.append({"interval": t, "price_eur_mwh": p.price_eur_mwh[t],
                     "charge_kw": float(x[charge[t]]), "discharge_kw": float(x[discharge[t]]),
                     "up_reserve_mw": float(x[up[t]]), "down_reserve_mw": float(x[down[t]]),
                     "soc_start_kwh": float(x[soc[t]]), "soc_end_kwh": float(x[soc[t + 1]]),
                     "up_energy_margin_kwh": float(x[soc[t]] - soc_min),
                     "down_energy_margin_kwh": float(soc_max - x[soc[t]]),
                     "reserve_up_requested_mw": p.reserve_up_request_mw[t],
                     "reserve_down_requested_mw": p.reserve_down_request_mw[t]})
    arbitrage = sum((row["discharge_kw"] - row["charge_kw"]) * dt * row["price_eur_mwh"] / 1000
                    for row in rows)
    up_revenue = sum(row["up_reserve_mw"] * p.reserve_up_price_eur_mw_h[t] * dt for t, row in enumerate(rows))
    down_revenue = sum(row["down_reserve_mw"] * p.reserve_down_price_eur_mw_h[t] * dt for t, row in enumerate(rows))
    return _answer([
        _m("Optimized arbitrage revenue", arbitrage, "EUR"),
        _m("Illustrative upward reserve revenue", up_revenue, "EUR"),
        _m("Illustrative downward reserve revenue", down_revenue, "EUR"),
        _m("Total modeled gross value", arbitrage + up_revenue + down_revenue, "EUR"),
        _m("Terminal SOC", float(x[soc[-1]]), "kWh"),
    ], series=[{"name": "SOC", "x_label": "Interval", "y_unit": "kWh",
                "x": list(range(n + 1)), "y": [float(v) for v in x[soc]]}], table=rows,
        details={"duration_hours": n * dt, "solver": "SciPy/HiGHS MILP", "solver_status": "optimal",
                 "initial_soc_kwh": initial, "terminal_soc_kwh": float(x[soc[-1]]),
                 "power_limit_mw": power_mw, "reserve_activation_duration_hours": p.reserve_duration_hours},
        warnings=["Explicit synthetic prices and service quantities are scenario assumptions, not market data or eligibility/award claims.",
                  "Perfect foresight; symmetric efficiency, fixed reserve activation duration and conservative offered-headroom constraints.",
                  "One modeled horizon only; no annualization, degradation, network limits, non-delivery penalties, taxes or availability." ])


def _energy_step(energy_kwh: float, power_kw: float, dt_h: float, capacity_kwh: float, eta: float) -> tuple[float, float]:
    power = power_kw
    if power >= 0:
        power = min(power, energy_kwh * eta / dt_h)
        energy_kwh -= power * dt_h / eta
    else:
        power = max(power, -(capacity_kwh - energy_kwh) / (eta * dt_h))
        energy_kwh -= power * dt_h * eta
    return float(power), float(min(capacity_kwh, max(0.0, energy_kwh)))


def _synergy(p: SynergyInput) -> dict:
    dt_h = p.interval_seconds / 3600
    alpha = p.interval_seconds / (p.filter_time_constant_s + p.interval_seconds)
    flywheel_capacity, battery_capacity = p.flywheel_energy_kwh, p.battery_energy_kwh
    flywheel_energy = flywheel_capacity * 0.5
    battery_energy = battery_capacity * 0.5
    eta = math.sqrt(0.92)
    low_pass = 0.0
    flywheel_path, battery_path, unmet_path = [], [], []
    flywheel_soc, battery_soc = [flywheel_energy], [battery_energy]
    residuals = []
    for disturbance in p.disturbance_kw:
        low_pass += alpha * (disturbance - low_pass)
        high_pass = disturbance - low_pass
        flywheel_power, flywheel_energy = _energy_step(
            flywheel_energy, min(p.flywheel_power_kw, max(-p.flywheel_power_kw, high_pass)),
            dt_h, flywheel_capacity, eta)
        battery_request = disturbance - flywheel_power
        battery_power, battery_energy = _energy_step(
            battery_energy, min(p.battery_power_kw, max(-p.battery_power_kw, battery_request)),
            dt_h, battery_capacity, eta)
        unmet = disturbance - flywheel_power - battery_power
        flywheel_path.append(flywheel_power)
        battery_path.append(battery_power)
        unmet_path.append(unmet)
        flywheel_soc.append(flywheel_energy)
        battery_soc.append(battery_energy)
        residuals.append(disturbance - (flywheel_power + battery_power + unmet))
    unmet_energy = sum(abs(x) for x in unmet_path) * dt_h
    index = list(range(len(p.disturbance_kw)))
    return _answer([
        _m("Peak flywheel power", max((abs(x) for x in flywheel_path), default=0.0), "kW"),
        _m("Peak battery power", max((abs(x) for x in battery_path), default=0.0), "kW"),
        _m("Peak unmet power", max((abs(x) for x in unmet_path), default=0.0), "kW"),
        _m("Unmet power energy", unmet_energy, "kWh"),
        _m("Ending flywheel energy", flywheel_energy, "kWh"),
        _m("Ending battery energy", battery_energy, "kWh"),
    ], series=[{"name": "Requested disturbance", "x_label": "Sample", "y_unit": "kW", "x": index, "y": p.disturbance_kw},
              {"name": "Flywheel dispatch", "x_label": "Sample", "y_unit": "kW", "x": index, "y": flywheel_path},
              {"name": "Battery dispatch", "x_label": "Sample", "y_unit": "kW", "x": index, "y": battery_path},
              {"name": "Unmet power", "x_label": "Sample", "y_unit": "kW", "x": index, "y": unmet_path}],
        details={"flywheel_energy_kwh": flywheel_soc, "battery_energy_kwh": battery_soc,
                 "maximum_power_balance_residual_kw": max((abs(x) for x in residuals), default=0.0),
                 "sample_interval_seconds": p.interval_seconds, "split_time_constant_seconds": p.filter_time_constant_s,
                 "fixed_initial_soc_fraction": 0.5, "fixed_round_trip_efficiency": 0.92},
        warnings=["Frequency split and sequential saturations are synthetic; no optimized dispatch or measured flywheel/battery response."])


def _backtracking(p: BacktrackingInput) -> dict:
    gcr = p.module_width_m / p.row_pitch_m
    axis = math.radians(p.tracker_axis_azimuth_deg)
    slope_az = math.radians(p.terrain_slope_azimuth_deg)
    cross_slope = math.atan(math.tan(math.radians(p.terrain_slope_deg)) * math.sin(slope_az - axis))
    ideal_angles, tracker_angles, shaded = [], [], []
    for elevation_deg, azimuth_deg in zip(p.sun_elevation_deg, p.sun_azimuth_deg):
        elevation = math.radians(elevation_deg)
        relative_azimuth = math.radians(azimuth_deg - p.tracker_axis_azimuth_deg)
        horizontal_cross = math.cos(elevation) * math.sin(relative_azimuth)
        vertical = math.sin(elevation)
        sun_along_ground = horizontal_cross * math.cos(cross_slope) + vertical * math.sin(cross_slope)
        sun_normal = -horizontal_cross * math.sin(cross_slope) + vertical * math.cos(cross_slope)
        if sun_normal <= 1e-9:
            ideal = 0.0
            angle = 0.0
            shade_fraction = 0.0
        else:
            ideal = math.atan2(sun_along_ground, sun_normal)
            angle = ideal
            ratio = abs(math.cos(ideal)) / gcr
            if p.backtracking and ratio < 1:
                angle = ideal - math.copysign(math.acos(max(-1.0, min(1.0, ratio))), ideal)
            local_sun_elevation = math.atan2(sun_normal, abs(sun_along_ground))
            shadow_length = p.module_width_m * abs(math.sin(angle)) / max(math.tan(local_sun_elevation), 1e-8)
            projected_width = p.module_width_m * abs(math.cos(angle))
            free_gap = max(0.0, p.row_pitch_m - projected_width)
            overlap = max(0.0, shadow_length - free_gap)
            shade_fraction = min(1.0, overlap / max(projected_width, 1e-8))
        ideal_angles.append(math.degrees(ideal))
        tracker_angles.append(math.degrees(angle))
        shaded.append(shade_fraction)
    return _answer([
        _m("Ground coverage ratio", gcr, "fraction"),
        _m("Mean ideal tracker angle", float(np.mean(ideal_angles)), "°"),
        _m("Mean corrected tracker angle", float(np.mean(tracker_angles)), "°"),
        _m("Mean row-shaded fraction", float(np.mean(shaded)), "fraction"),
        _m("Maximum row-shaded fraction", max(shaded), "fraction"),
    ], series=[{"name": "Ideal tracker rotation", "x_label": "Sun sample", "y_unit": "°", "x": list(range(len(ideal_angles))), "y": ideal_angles},
              {"name": "Backtracked rotation", "x_label": "Sun sample", "y_unit": "°", "x": list(range(len(tracker_angles))), "y": tracker_angles},
              {"name": "Planar row shade", "x_label": "Sun sample", "y_unit": "fraction", "x": list(range(len(shaded))), "y": shaded}],
        table=[{"sample": i, "solar_elevation_deg": p.sun_elevation_deg[i],
                "solar_azimuth_deg": p.sun_azimuth_deg[i], "ideal_angle_deg": ideal_angles[i],
                "tracker_angle_deg": tracker_angles[i], "shaded_fraction": shaded[i]}
               for i in range(len(shaded))],
        details={"cross_axis_slope_deg": math.degrees(cross_slope), "ground_coverage_ratio": gcr,
                 "shaded_fraction_by_sample": shaded},
        warnings=["Illustrative local-slope projection and planar row geometry; not the complete NREL slope-aware tracker algorithm or an annual yield estimate."])


def _agrivoltaic(p: AgrivoltaicInput) -> dict:
    area = _polygon_area(p.land_polygon_m)
    perimeter = sum(math.dist(p.land_polygon_m[i], p.land_polygon_m[(i + 1) % len(p.land_polygon_m)])
                    for i in range(len(p.land_polygon_m)))
    usable = max(0.0, area - perimeter * p.setback_m)
    crop_par = p.baseline_par_mol_m2_day * (1 - p.ground_coverage_ratio * (1 - p.module_transmission_fraction))
    return _answer([
        _m("Land polygon area", area, "m²"),
        _m("Polygon perimeter", perimeter, "m"),
        _m("Conservative usable area", usable, "m²"),
        _m("Estimated crop PAR", crop_par, "mol/m²/day"),
        _m("Estimated PV-covered area", usable * p.ground_coverage_ratio, "m²"),
    ], details={"setback_deduction_area_m2": min(area, perimeter * p.setback_m),
                "crop_par_fraction_of_open_field": crop_par / p.baseline_par_mol_m2_day,
                "polygon_vertices_m": [list(point) for point in p.land_polygon_m]},
        warnings=["Setback area is deducted as perimeter × distance; this is not an exact inward polygon buffer.",
                  "PAR is a simple area-average shade/transmission proxy, not a crop-yield, ecology, permitting or agronomic conclusion."])


def _albedo(p: AlbedoInput) -> dict:
    months = list(range(1, 13))
    rows, front_total, total = [], 0.0, 0.0
    for i in range(12):
        front = p.front_plane_irradiance_kwh_m2[i]
        rear_ground = p.rear_ground_irradiance_kwh_m2[i] * p.albedo * p.rear_view_factor
        front_energy = p.system_capacity_kwp * p.performance_ratio * front
        rear_energy = p.system_capacity_kwp * p.performance_ratio * p.bifaciality * rear_ground
        row_energy = front_energy + rear_energy
        front_total += front_energy
        total += row_energy
        rows.append({"month": i + 1, "front_irradiance_kwh_m2": front,
                     "rear_ground_irradiance_kwh_m2": p.rear_ground_irradiance_kwh_m2[i],
                     "rear_effective_irradiance_kwh_m2": rear_ground,
                     "front_energy_kwh": front_energy, "rear_energy_kwh": rear_energy,
                     "energy_with_rear_kwh": row_energy})
    return _answer([
        _m("Annual front-side energy", front_total, "kWh"),
        _m("Annual rear-side contribution", total - front_total, "kWh"),
        _m("Annual energy with rear response", total, "kWh"),
        _m("Rear contribution share", (total - front_total) / total if total else 0.0, "fraction"),
    ], series=[{"name": "Monthly energy with rear response", "x_label": "Month", "y_unit": "kWh",
                "x": months, "y": [row["energy_with_rear_kwh"] for row in rows]},
              {"name": "Monthly front-side energy", "x_label": "Month", "y_unit": "kWh",
                "x": months, "y": [row["front_energy_kwh"] for row in rows]}],
        table=rows, details={"annual_front_energy_kwh": front_total,
                             "annual_rear_energy_kwh": total - front_total,
                             "annual_total_energy_kwh": total},
        warnings=["Monthly irradiation, PR, bifaciality and view-factor screening only; no site ray tracing, mismatch or measured weather year."])


def _fft_amplitude(signal: np.ndarray, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(len(signal))
    spectrum = np.fft.rfft((signal - np.mean(signal)) * window)
    amplitude = 2 * np.abs(spectrum) / max(float(np.sum(window)), 1e-12)
    amplitude[0] *= 0.5
    if len(signal) % 2 == 0:
        amplitude[-1] *= 0.5
    frequency = np.fft.rfftfreq(len(signal), d=1 / sample_rate)
    return frequency, amplitude


def _vibration(p: VibrationInput) -> dict:
    if p.signal:
        signal = np.asarray(p.signal, dtype=float)
        source = "user_supplied"
    else:
        count = p.sample_count
        time_s = np.arange(count, dtype=float) / p.sample_rate_hz
        duration = count / p.sample_rate_hz
        phase = 2 * math.pi * (p.synthetic_frequency_hz * time_s
                               + 0.5 * (p.synthetic_drift_hz / duration) * time_s ** 2)
        rng = np.random.default_rng(42)
        signal = p.synthetic_amplitude * np.sin(phase)
        signal += 0.25 * np.sin(2 * math.pi * 55 * time_s)
        if p.noise_std:
            signal += rng.normal(0, p.noise_std, count)
        source = "seeded_synthetic"
    frequency, amplitude = _fft_amplitude(signal, p.sample_rate_hz)
    peak_index = int(np.argmax(amplitude[1:]) + 1) if len(amplitude) > 1 else 0
    midpoint = len(signal) // 2
    early_f, early_a = _fft_amplitude(signal[:midpoint], p.sample_rate_hz)
    late_f, late_a = _fft_amplitude(signal[midpoint:], p.sample_rate_hz)
    early_peak = int(np.argmax(early_a[1:]) + 1) if len(early_a) > 1 else 0
    late_peak = int(np.argmax(late_a[1:]) + 1) if len(late_a) > 1 else 0
    peak_rows = sorted((i for i in range(1, len(amplitude))), key=lambda i: amplitude[i], reverse=True)[:10]
    return _answer([
        _m("Dominant frequency", float(frequency[peak_index]), "Hz"),
        _m("Dominant peak amplitude", float(amplitude[peak_index]), "signal unit"),
        _m("Early-half dominant frequency", float(early_f[early_peak]), "Hz"),
        _m("Late-half dominant frequency", float(late_f[late_peak]), "Hz"),
        _m("Spectral drift", float(late_f[late_peak] - early_f[early_peak]), "Hz"),
    ], series=[{"name": "One-sided Hann amplitude spectrum", "x_label": "Frequency (Hz)",
                "y_unit": "signal unit", "x": frequency.tolist(), "y": amplitude.tolist()}],
        table=[{"frequency_hz": float(frequency[i]), "amplitude": float(amplitude[i])} for i in peak_rows],
        details={"sample_count": len(signal), "sample_rate_hz": p.sample_rate_hz,
                 "signal_source": source, "seed": 42 if source == "seeded_synthetic" else None,
                 "frequency_resolution_hz": p.sample_rate_hz / len(signal)},
        warnings=["Evenly spaced finite signal with Hann window and simple half-record peak comparison; no classifier or fault diagnosis.",
                  "Synthetic examples are reproducible but do not represent measured equipment vibration."])


def _epd(p: EPDInput) -> dict:
    stage_include = {"materials": bool(p.include_materials), "manufacturing": bool(p.include_manufacturing),
                     "transport": bool(p.include_transport), "use": bool(p.include_use),
                     "end_of_life": bool(p.include_end_of_life), "other": bool(p.include_other)}
    seen: set[str] = set()
    duplicate_ids: list[str] = []
    missing_ids: list[str] = []
    included: list[dict] = []
    all_rows: list[dict] = []
    stage_totals: dict[str, float] = {}
    complete_evidence = 0
    for record in p.records:
        if record.record_id in seen:
            if record.record_id not in duplicate_ids:
                duplicate_ids.append(record.record_id)
            all_rows.append({"record_id": record.record_id, "supplier": record.supplier,
                             "stage": record.stage, "quantity": record.quantity,
                             "unit": record.unit, "emissions_kgco2e": None,
                             "status": "duplicate_skipped", "evidence_id": record.evidence_id,
                             "data_quality": record.data_quality})
            continue
        seen.add(record.record_id)
        missing = []
        if not record.supplier:
            missing.append("supplier")
        if not record.unit:
            missing.append("unit")
        if record.emission_factor_kgco2e_per_unit is None:
            missing.append("emission_factor")
        if not record.evidence_id:
            missing.append("evidence_id")
        if missing:
            missing_ids.append(record.record_id)
        emissions = (record.quantity * record.emission_factor_kgco2e_per_unit
                     if record.emission_factor_kgco2e_per_unit is not None else None)
        selected_for_boundary = stage_include[record.stage]
        if emissions is not None and selected_for_boundary:
            included.append({"record_id": record.record_id, "emissions_kgco2e": emissions})
            stage_totals[record.stage] = stage_totals.get(record.stage, 0.0) + emissions
        if not missing:
            complete_evidence += 1
        all_rows.append({"record_id": record.record_id, "supplier": record.supplier,
                         "stage": record.stage, "quantity": record.quantity, "unit": record.unit,
                         "emission_factor_kgco2e_per_unit": record.emission_factor_kgco2e_per_unit,
                         "emissions_kgco2e": emissions,
                         "status": ("missing:" + ",".join(missing) if missing
                                    else "included" if selected_for_boundary else "excluded_by_stage_boundary"),
                         "evidence_id": record.evidence_id, "data_quality": record.data_quality})
    total = sum(row["emissions_kgco2e"] for row in included)
    valid_unique_count = len(seen)
    evidence_completeness = complete_evidence / valid_unique_count if valid_unique_count else 0.0
    warnings = ["Supplier-stage arithmetic ledger; input evidence, emission factors and product-declaration boundaries are not verified."]
    if duplicate_ids:
        warnings.append("Duplicate record IDs were retained in the audit details but only their first occurrence was eligible for inclusion.")
    if missing_ids:
        warnings.append("Records with missing supplier, unit, factor or evidence are explicitly flagged; absent factors are not imputed.")
    return _answer([
        _m("Included emissions", total, "kgCO₂e"),
        _m("Unique records", valid_unique_count, "records"),
        _m("Included factor-complete records", len(included), "records"),
        _m("Duplicate record IDs", len(duplicate_ids), "IDs"),
        _m("Records with missing fields", len(missing_ids), "records"),
        _m("Evidence completeness", evidence_completeness, "fraction"),
    ], series=[{"name": "Included emissions by stage", "x_label": "Lifecycle stage", "y_unit": "kgCO₂e",
                "x": list(stage_totals), "y": list(stage_totals.values())}],
        table=all_rows,
        details={"stage_totals_kgco2e": stage_totals, "duplicate_record_ids": duplicate_ids,
                 "missing_record_ids": missing_ids, "first_occurrence_included_only": True,
                 "unique_records": valid_unique_count, "selected_stages": stage_include}, warnings=warnings)


def _scr(p: SCRInput) -> dict:
    ratio = p.short_circuit_mva / p.plant_mw
    line_x_ohm = 0.3
    drop_pu = (p.line_r_ohm * p.active_power_mw + line_x_ohm * p.reactive_power_mvar) / (p.voltage_kv ** 2)
    zth_ohm = p.voltage_kv ** 2 / p.short_circuit_mva
    capacity_curve = np.linspace(max(p.plant_mw * 0.1, 0.1), p.plant_mw, 32)
    scr_curve = p.short_circuit_mva / capacity_curve
    return _answer([
        _m("SCR at plant rating", ratio, "MVA/MW"),
        _m("Approximate voltage-drop magnitude", abs(drop_pu) * 100, "%"),
        _m("Approximate Thevenin impedance magnitude", zth_ohm, "Ω"),
    ], series=[{"name": "Ssc/P screening curve", "x_label": "IBR active-power rating (MW)",
                "y_unit": "SCR ratio", "x": capacity_curve.tolist(), "y": scr_curve.tolist()}],
        details={"voltage_drop_signed_pu": drop_pu, "voltage_drop_magnitude_pct": abs(drop_pu) * 100,
                 "short_circuit_mva": p.short_circuit_mva, "plant_mw": p.plant_mw,
                 "active_power_mw": p.active_power_mw, "reactive_power_mvar": p.reactive_power_mvar,
                 "voltage_kv_line_to_line": p.voltage_kv, "fixed_line_reactance_ohm": line_x_ohm},
        warnings=["The single-infeed Ssc/P ratio is a grid-strength screen, not a stability or compliance guarantee.",
                  "Voltage-drop approximation assumes balanced three-phase conditions and a small series drop; use a validated load flow and dynamic study for decisions."])


_RUNNERS = {
    "hybrid-resonance": _resonance,
    "hybrid-clipping": _clipping,
    "hybrid-inertia": _inertia,
    "storage-degradation": _degradation,
    "storage-stacking": _stacking,
    "storage-synergy": _synergy,
    "pv-backtracking": _backtracking,
    "pv-agrivoltaic": _agrivoltaic,
    "pv-albedo": _albedo,
    "research-vibration": _vibration,
    "research-epd": _epd,
    "research-scr": _scr,
}


def run(study_id: str, inputs: dict) -> dict:
    """Validate one study's strict input model and return finite JSON-ready results."""
    if study_id not in _RUNNERS:
        raise ValueError(f"Unknown engineering study: {study_id}")
    if not isinstance(inputs, dict):
        raise TypeError("Study inputs must be a JSON object.")
    model = INPUT_MODELS[study_id].model_validate(inputs)
    return _RUNNERS[study_id](model)
