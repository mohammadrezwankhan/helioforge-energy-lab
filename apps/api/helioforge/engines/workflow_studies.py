"""Deterministic educational workflow studies; no field control or external AI."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from math import exp, log, log2, pi, sin, sqrt
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix, vstack

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/ -]*$")]


class StrictStudy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True, allow_inf_nan=False)


def _duck_load() -> list[float]:
    return [round(92 + 18*sin(2*pi*(h-7)/24) + 8*sin(2*pi*h/8), 3) for h in range(24)]


def _duck_solar() -> list[float]:
    return [round(max(0.0, 72*sin(pi*(h-6)/12)), 3) for h in range(24)]


def _duck_wind() -> list[float]:
    return [round(24 + 8*sin(2*pi*h/11) + 5*sin(2*pi*h/19), 3) for h in range(24)]


class DuckInput(StrictStudy):
    interval_hours: Finite = Field(default=1, gt=0, le=4)
    ramp_limit_kw_per_hour: NonNegative = Field(default=45, le=10_000)
    ramp_percentile: Finite = Field(default=95, ge=50, le=99.9)
    load_kw: list[NonNegative] = Field(default_factory=_duck_load, min_length=2, max_length=168)
    solar_kw: list[NonNegative] = Field(default_factory=_duck_solar, min_length=2, max_length=168)
    wind_kw: list[NonNegative] = Field(default_factory=_duck_wind, min_length=2, max_length=168)

    @model_validator(mode="after")
    def aligned(self) -> DuckInput:
        if len({len(self.load_kw), len(self.solar_kw), len(self.wind_kw)}) != 1:
            raise ValueError("Load, solar, and wind arrays must have equal lengths.")
        if any(v > 100_000 for a in (self.load_kw, self.solar_kw, self.wind_kw) for v in a):
            raise ValueError("Hourly power values are bounded to 100,000 kW.")
        return self


class BlackstartStep(StrictStudy):
    action: Literal["start_gfm", "energize_bus", "connect_load"]
    label: Annotated[str, Field(min_length=1, max_length=100)]
    active_kw: NonNegative = Field(default=0, le=100_000)
    inrush_kw: NonNegative = Field(default=0, le=100_000)


def _blackstart_steps() -> list[dict]:
    return [
        {"action": "start_gfm", "label": "Start grid-forming source", "active_kw": 8, "inrush_kw": 0},
        {"action": "energize_bus", "label": "Energize essential bus", "active_kw": 12, "inrush_kw": 80},
        {"action": "connect_load", "label": "Connect critical load", "active_kw": 45, "inrush_kw": 20},
    ]


class BlackstartInput(StrictStudy):
    gfm_rated_kw: Positive = Field(default=500, le=100_000)
    available_power_fraction: Finite = Field(default=0.8, gt=0, le=1)
    inrush_budget_kw: NonNegative = Field(default=250, le=100_000)
    reserve_fraction: Finite = Field(default=0.15, ge=0, lt=1)
    steps: list[BlackstartStep] = Field(default_factory=_blackstart_steps, min_length=1, max_length=16)

    @model_validator(mode="after")
    def reserve(self) -> BlackstartInput:
        if self.available_power_fraction < self.reserve_fraction:
            raise ValueError("Available fraction must be at least the reserve fraction.")
        return self


class HydrogenBatch(StrictStudy):
    hydrogen_kg: NonNegative = Field(default=100, le=100_000)
    batch_id: Annotated[str, Field(min_length=1, max_length=80)] = "synthetic-batch-01"


class HydrogenInput(StrictStudy):
    electrolyzer_kwh_per_kg: Positive = Field(default=52, ge=33.3, le=200)
    compression_kwh_per_kg: NonNegative = Field(default=2, le=100)
    fuel_cell_electric_efficiency: Finite = Field(default=0.5, ge=0, le=1)
    hydrogen_lhv_kwh_per_kg: Positive = Field(default=33.3, ge=33.3, le=33.3)
    batch: HydrogenBatch = Field(default_factory=HydrogenBatch)


class ParetoCandidate(StrictStudy):
    run_id: Identifier
    scenario_key: Identifier
    sample_set_key: Identifier
    horizon_hours: int = Field(ge=1, le=8760)
    service_basis: Literal["critical_load", "total_load"] = "critical_load"
    cost_eur: Finite = Field(ge=-1_000_000_000, le=1_000_000_000)
    served_load_pct: Finite = Field(ge=0, le=100)
    storage_capacity_kwh: NonNegative = Field(le=100_000_000)
    initial_soc_kwh: NonNegative = Field(le=100_000_000)
    terminal_soc_kwh: NonNegative = Field(le=100_000_000)
    expected_loss_of_load_hours: NonNegative = Field(le=8760)
    sample_count: int = Field(ge=1, le=100_000)

    @model_validator(mode="after")
    def bounds(self) -> ParetoCandidate:
        if max(self.initial_soc_kwh, self.terminal_soc_kwh) > self.storage_capacity_kwh:
            raise ValueError("Initial and terminal SOC must be within storage capacity.")
        if self.expected_loss_of_load_hours > self.horizon_hours:
            raise ValueError("Expected loss-of-load hours cannot exceed the horizon.")
        return self


def _pareto_candidates() -> list[dict]:
    shared = {"scenario_key": "hospital-2030", "sample_set_key": "ensemble-48",
              "horizon_hours": 24, "sample_count": 48}
    return [
        {**shared, "run_id": "run-a", "cost_eur": 2400, "served_load_pct": 97,
         "storage_capacity_kwh": 900, "initial_soc_kwh": 450, "terminal_soc_kwh": 400,
         "expected_loss_of_load_hours": 1.2},
        {**shared, "run_id": "run-b", "cost_eur": 2750, "served_load_pct": 99,
         "storage_capacity_kwh": 1100, "initial_soc_kwh": 550, "terminal_soc_kwh": 520,
         "expected_loss_of_load_hours": 0.5},
        {**shared, "run_id": "run-c", "cost_eur": 2300, "served_load_pct": 92,
         "storage_capacity_kwh": 750, "initial_soc_kwh": 375, "terminal_soc_kwh": 300,
         "expected_loss_of_load_hours": 2.4},
    ]


class ParetoInput(StrictStudy):
    cost_weight: Finite = Field(default=0.4, ge=0, le=1)
    service_weight: Finite = Field(default=0.3, ge=0, le=1)
    loss_of_load_weight: Finite = Field(default=0.3, ge=0, le=1)
    candidates: list[ParetoCandidate] = Field(default_factory=_pareto_candidates, min_length=2, max_length=12)

    @model_validator(mode="after")
    def weights_and_ids(self) -> ParetoInput:
        if abs(self.cost_weight + self.service_weight + self.loss_of_load_weight - 1) > 1e-9:
            raise ValueError("Recommendation weights must sum to one.")
        if len({row.run_id for row in self.candidates}) != len(self.candidates):
            raise ValueError("Candidate run IDs must be unique.")
        return self


def _default_dunkelflaute() -> tuple[list[float], list[float]]:
    loads, renewable = [], []
    for hour in range(336):
        daily = sin(2*pi*(hour % 24 - 7)/24)
        weekly = sin(2*pi*hour/168)
        loads.append(round(275 + 30*daily + 15*weekly + 6*sin(2*pi*hour/53), 3))
        solar = max(0, sin(pi*((hour % 24)-6)/12))*215
        weather = 0.20 if 96 <= hour < 216 else 0.72 + 0.22*sin(2*pi*hour/89)
        wind = max(8, 95 + 60*sin(2*pi*hour/79) + 35*sin(2*pi*hour/43))
        renewable.append(round(solar*weather + wind*(0.36 + 0.64*max(0.1, weather)), 3))
    return loads, renewable


_DUNKEL_LOAD, _DUNKEL_RENEWABLE = _default_dunkelflaute()


class DunkelflauteInput(StrictStudy):
    energy_capacity_kwh: Positive = Field(default=500, le=10_000_000)
    power_limit_kw: Positive = Field(default=120, le=1_000_000)
    charge_efficiency: Finite = Field(default=0.94, gt=0, le=1)
    discharge_efficiency: Finite = Field(default=0.94, gt=0, le=1)
    initial_soc_kwh: NonNegative = Field(default=250, le=10_000_000)
    load_kw: list[NonNegative] = Field(default_factory=lambda: list(_DUNKEL_LOAD), min_length=336, max_length=336)
    renewable_kw: list[NonNegative] = Field(default_factory=lambda: list(_DUNKEL_RENEWABLE), min_length=336, max_length=336)

    @model_validator(mode="after")
    def physical(self) -> DunkelflauteInput:
        if self.initial_soc_kwh > self.energy_capacity_kwh:
            raise ValueError("Initial SOC must fit within storage capacity.")
        if any(v > 100_000 for row in (self.load_kw, self.renewable_kw) for v in row):
            raise ValueError("Hourly power values are bounded to 100,000 kW.")
        return self


class ThermalRegime(StrictStudy):
    regime: Annotated[str, Field(min_length=1, max_length=80)]
    utilization_fraction: Finite = Field(ge=0, le=1)
    cycles_per_day_at_full_utilization: NonNegative = Field(le=20)
    depth_of_discharge_fraction: Finite = Field(ge=0, le=1)
    ambient_temperature_c: Finite = Field(ge=-40, le=100)


def _thermal_regimes() -> list[dict]:
    return [
        {"regime": "Low duty", "utilization_fraction": 0.35, "cycles_per_day_at_full_utilization": 1.0,
         "depth_of_discharge_fraction": 0.45, "ambient_temperature_c": 20},
        {"regime": "Daily shifting", "utilization_fraction": 0.75, "cycles_per_day_at_full_utilization": 1.2,
         "depth_of_discharge_fraction": 0.75, "ambient_temperature_c": 25},
        {"regime": "Hot high duty", "utilization_fraction": 0.95, "cycles_per_day_at_full_utilization": 1.8,
         "depth_of_discharge_fraction": 0.90, "ambient_temperature_c": 35},
    ]


class ThermalInput(StrictStudy):
    reference_temperature_c: Finite = Field(default=25, ge=-40, le=100)
    temperature_factor_per_c: Finite = Field(default=0.025, ge=0, le=0.1)
    screening_loss_fraction_per_1000_efc: Finite = Field(default=0.025, ge=0, le=1)
    years: int = Field(default=1, ge=1, le=30)
    regimes: list[ThermalRegime] = Field(default_factory=_thermal_regimes, min_length=1, max_length=12)


Point = Annotated[list[Finite], Field(min_length=3, max_length=3)]


class PhotogrammetryInput(StrictStudy):
    coordinate_scale_m: Positive = Field(default=1, le=100_000)
    reporting_limit_m: NonNegative = Field(default=0.05, le=100_000)
    percentile: Finite = Field(default=95, ge=50, le=99.9)
    design_points_xyz: list[Point] = Field(default_factory=lambda: [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], max_length=10_000)
    asbuilt_points_xyz: list[Point] = Field(default_factory=lambda: [[0.01, 0, 0], [1, 0.02, 0], [0, 1, -0.03], [0, 0, 1.04]], max_length=10_000)

    @model_validator(mode="after")
    def paired(self) -> PhotogrammetryInput:
        if len(self.design_points_xyz) != len(self.asbuilt_points_xyz):
            raise ValueError("Design and as-built clouds must have equal index-paired lengths.")
        if any(abs(c) > 1_000_000 for cloud in (self.design_points_xyz, self.asbuilt_points_xyz)
               for point in cloud for c in point):
            raise ValueError("Coordinates are bounded to ±1,000,000 input units.")
        return self


class DtsSample(StrictStudy):
    distance_m: NonNegative = Field(le=10_000_000)
    temperature_c: Finite | None = Field(default=None, ge=-50, le=200)
    observed_at_hour: NonNegative = Field(le=1_000_000)


def _dts_samples() -> list[dict]:
    return [
        {"distance_m": 0, "temperature_c": 34, "observed_at_hour": 9.8},
        {"distance_m": 10, "temperature_c": 37, "observed_at_hour": 9.8},
        {"distance_m": 20, "temperature_c": 81, "observed_at_hour": 9.8},
        {"distance_m": 30, "temperature_c": 44, "observed_at_hour": 9.8},
        {"distance_m": 40, "temperature_c": None, "observed_at_hour": 9.7},
    ]


class DtsInput(StrictStudy):
    hot_spot_threshold_c: Finite = Field(default=75, ge=-50, le=200)
    gradient_threshold_c_per_m: NonNegative = Field(default=0.25, le=100_000)
    maximum_age_hours: NonNegative = Field(default=2, le=100_000)
    current_time_hour: NonNegative = Field(default=10, le=1_000_000)
    samples: list[DtsSample] = Field(default_factory=_dts_samples, max_length=10_000)

    @model_validator(mode="after")
    def ordered_and_current(self) -> DtsInput:
        x = [s.distance_m for s in self.samples]
        if any(b <= a for a, b in zip(x, x[1:])):
            raise ValueError("DTS distances must be strictly increasing.")
        if any(b-a < 0.1 for a, b in zip(x, x[1:])):
            raise ValueError("Adjacent DTS samples must be at least 0.1 m apart.")
        if any(s.observed_at_hour > self.current_time_hour for s in self.samples):
            raise ValueError("Observation time cannot be in the future.")
        return self


class OffgasSensor(StrictStudy):
    sensor_id: Identifier
    temperature_c: Finite | None = Field(default=None, ge=-100, le=500)
    co_ppm: NonNegative | None = Field(default=None, le=100_000)
    voc_ppm: NonNegative | None = Field(default=None, le=100_000)


def _offgas_sensors() -> list[dict]:
    return [
        {"sensor_id": "sensor-a", "temperature_c": 68, "co_ppm": 42, "voc_ppm": 1.2},
        {"sensor_id": "sensor-b", "temperature_c": 74, "co_ppm": None, "voc_ppm": 6.5},
        {"sensor_id": "sensor-c", "temperature_c": 43, "co_ppm": 4, "voc_ppm": None},
    ]


class OffgasInput(StrictStudy):
    temperature_threshold_c: Finite = Field(default=70, ge=-100, le=500)
    co_threshold_ppm: Positive = Field(default=35, le=100_000)
    voc_threshold_ppm: Positive = Field(default=5, le=100_000)
    votes_required: int = Field(default=2, ge=1, le=32)
    sensors: list[OffgasSensor] = Field(default_factory=_offgas_sensors, min_length=1, max_length=32)

    @model_validator(mode="after")
    def votes_and_ids(self) -> OffgasInput:
        if self.votes_required > len(self.sensors):
            raise ValueError("Required votes cannot exceed sensor count.")
        ids = [s.sensor_id for s in self.sensors]
        if len(set(ids)) != len(ids):
            raise ValueError("Sensor IDs must be unique.")
        if any(s.temperature_c is None and s.co_ppm is None and s.voc_ppm is None for s in self.sensors):
            raise ValueError("Each sensor must provide at least one reading.")
        return self


class DebateAssertion(StrictStudy):
    topic: Identifier
    statement: Annotated[str, Field(min_length=1, max_length=500)]
    value: Finite
    unit: Annotated[str, Field(min_length=1, max_length=40)]
    source_ref: Annotated[str, Field(min_length=1, max_length=200)]
    comparison_tolerance: NonNegative = Field(default=0, le=1_000_000_000)


def _finance_evidence() -> list[dict]:
    return [
        {"topic": "annual_value", "statement": "Finance case assumes contracted net value.",
         "value": 230000, "unit": "EUR/year", "source_ref": "synthetic:finance-case", "comparison_tolerance": 5000},
        {"topic": "lifetime", "statement": "Finance case assumes fifteen operating years.",
         "value": 15, "unit": "year", "source_ref": "synthetic:finance-case"},
    ]


def _storage_evidence() -> list[dict]:
    return [
        {"topic": "annual_value", "statement": "Storage challenge includes omitted flexibility value.",
         "value": 255000, "unit": "EUR/year", "source_ref": "synthetic:storage-screen", "comparison_tolerance": 5000},
        {"topic": "lifetime", "statement": "Storage challenge assumes a shorter useful life.",
         "value": 12, "unit": "year", "source_ref": "synthetic:storage-screen"},
    ]


class DebateInput(StrictStudy):
    capex_eur: NonNegative = Field(default=1_200_000, le=1_000_000_000_000)
    annual_net_value_eur: Finite = Field(default=230_000, ge=-1_000_000_000, le=1_000_000_000)
    life_years: int = Field(default=15, ge=1, le=60)
    discount_rate_fraction: Finite = Field(default=0.08, ge=0, le=0.5)
    finance_evidence: list[DebateAssertion] = Field(default_factory=_finance_evidence, max_length=16)
    storage_evidence: list[DebateAssertion] = Field(default_factory=_storage_evidence, max_length=16)

    @model_validator(mode="after")
    def unique_topics(self) -> DebateInput:
        for side in (self.finance_evidence, self.storage_evidence):
            if len({x.topic for x in side}) != len(side):
                raise ValueError("Each side may assert a topic once.")
        return self


class ManifestDocument(StrictStudy):
    document_id: Identifier
    kind: Literal["tariff", "warranty", "single_line"]
    field_name: Identifier
    unit: Annotated[str, Field(min_length=1, max_length=40)]
    value: Finite
    issuer: Annotated[str, Field(max_length=200)] | None = None
    source_reference: Annotated[str, Field(max_length=300)] | None = None
    issued_on: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    expires_on: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None

    @model_validator(mode="after")
    def dates(self) -> ManifestDocument:
        from datetime import date
        try:
            issued = date.fromisoformat(self.issued_on)
            expiry = date.fromisoformat(self.expires_on) if self.expires_on else None
        except ValueError as error:
            raise ValueError("Dates must be valid ISO calendar dates.") from error
        if expiry is not None and expiry < issued:
            raise ValueError("Expiry cannot precede issue date.")
        return self


def _manifest_documents() -> list[dict]:
    return [
        {"document_id": "tariff-01", "kind": "tariff", "field_name": "tariff_eur_mwh", "unit": "EUR/MWh",
         "value": 86, "issuer": "Example utility", "source_reference": "synthetic:tariff-record",
         "issued_on": "2026-01-01", "expires_on": "2026-12-31"},
        {"document_id": "warranty-01", "kind": "warranty", "field_name": "warranty_years", "unit": "year",
         "value": 12, "issuer": "Example supplier", "source_reference": "synthetic:warranty-record",
         "issued_on": "2025-06-01", "expires_on": "2037-06-01"},
        {"document_id": "single-line-01", "kind": "single_line", "field_name": "node_count", "unit": "count",
         "value": 18, "issuer": "Project team", "source_reference": "synthetic:diagram-manifest",
         "issued_on": "2026-09-01"},
    ]


class ManifestPayload(StrictStudy):
    as_of_date: Annotated[str, Field(default="2026-10-17", pattern=r"^\d{4}-\d{2}-\d{2}$")]
    documents: list[ManifestDocument] = Field(default_factory=_manifest_documents, max_length=100)

    @model_validator(mode="after")
    def dates_and_ids(self) -> ManifestPayload:
        from datetime import date
        try:
            date.fromisoformat(self.as_of_date)
        except ValueError as error:
            raise ValueError("As-of date must be valid ISO date.") from error
        if len({d.document_id for d in self.documents}) != len(self.documents):
            raise ValueError("Manifest document IDs must be unique.")
        return self


class ManifestInput(StrictStudy):
    maximum_manifest_age_days: int = Field(default=3650, ge=0, le=36_500)
    maximum_tariff_eur_mwh: Positive = Field(default=2000, le=100_000)
    maximum_warranty_years: Positive = Field(default=50, le=100)
    maximum_single_line_nodes: int = Field(default=10000, ge=1, le=1_000_000)
    manifest: ManifestPayload = Field(default_factory=ManifestPayload)


class ConsensusEvidence(StrictStudy):
    evidence_id: Identifier
    likelihood_ratio: Positive = Field(le=1_000_000_000)
    dependency_group: Identifier
    note: Annotated[str, Field(min_length=1, max_length=300)]


def _consensus_evidence() -> list[dict]:
    return [
        {"evidence_id": "meter-summary", "likelihood_ratio": 2.4, "dependency_group": "metering",
         "note": "Synthetic meter summary supports the hypothesis."},
        {"evidence_id": "site-inspection", "likelihood_ratio": 1.5, "dependency_group": "inspection",
         "note": "Synthetic inspection note provides additional support."},
        {"evidence_id": "counter-check", "likelihood_ratio": 0.7, "dependency_group": "metering",
         "note": "Second metering-derived record is directionally adverse."},
    ]


class ConsensusInput(StrictStudy):
    prior_probability: Finite = Field(default=0.35, ge=0, le=1)
    maximum_absolute_log_likelihood_ratio: Finite = Field(default=4, ge=0, le=20)
    evidence_weight: Finite = Field(default=1, ge=0, le=1)
    evidence: list[ConsensusEvidence] = Field(default_factory=_consensus_evidence, max_length=64)

    @model_validator(mode="after")
    def evidence_ids_unique(self) -> ConsensusInput:
        if len({x.evidence_id for x in self.evidence}) != len(self.evidence):
            raise ValueError("Evidence IDs must be unique.")
        return self


def _f(name: str, label: str, default: int | float, low: int | float,
       high: int | float, step: int | float, unit: str) -> dict:
    return {"name": name, "label": label, "default": default,
            "min": low, "max": high, "step": step, "unit": unit}


def _d(name: str, label: str, default) -> dict:
    return {"name": name, "label": label, "default": deepcopy(default)}


def _entry(study_id: str, page: str, title: str, summary: str, kind: str,
           fields: list[dict], data_fields: list[dict], equations: list[str],
           limitations: list[str], sources: list[dict]) -> dict:
    return {"id": study_id, "page": page, "title": title, "summary": summary,
            "kind": kind, "fields": fields, "data_fields": data_fields,
            "equations": equations, "limitations": limitations, "sources": sources}


STUDIES = [
    _entry("lessons-duck", "lessons", "Net load and ramps",
        "Work through renewable subtraction, hourly ramps, and energy closure.", "learning",
        [_f("interval_hours", "Interval duration", 1, 0.25, 4, 0.25, "h"),
         _f("ramp_limit_kw_per_hour", "Illustrative ramp marker", 45, 0, 10000, 5, "kW/h"),
         _f("ramp_percentile", "Ramp percentile", 95, 50, 99.9, 1, "%")],
        [_d("load_kw", "Demand", _duck_load()), _d("solar_kw", "Solar output", _duck_solar()),
         _d("wind_kw", "Wind output", _duck_wind())],
        ["net load[t] = load[t] - solar[t] - wind[t]",
         "ramp[t] = (net load[t] - net load[t-1]) / interval hours",
         "net-load energy = sum(net load[t] * interval hours)"],
        ["Synthetic equal-duration series; no dispatch, forecast, or grid-constraint model."],
        [{"title": "Renewable integration study of net load and ramping",
          "url": "https://docs.nrel.gov/docs/fy18osti/71151.pdf"}]),
    _entry("lessons-blackstart", "lessons", "Black-start sequence exercise",
        "Check a finite-state energization sequence against active-power and inrush budgets.", "learning",
        [_f("gfm_rated_kw", "Grid-forming rated power", 500, 1, 100000, 10, "kW"),
         _f("available_power_fraction", "Available fraction", 0.8, 0.01, 1, 0.01, "fraction"),
         _f("inrush_budget_kw", "Allowed inrush proxy", 250, 0, 100000, 10, "kW"),
         _f("reserve_fraction", "Held reserve fraction", 0.15, 0, 0.99, 0.01, "fraction")],
        [_d("steps", "Ordered exercise steps", _blackstart_steps())],
        ["available budget = rated power * available fraction",
         "step passes if active power + inrush <= rated power * (available fraction - reserve fraction)",
         "states: dark -> grid-forming-ready -> bus-energized -> load-restored"],
        ["Procedural finite-state exercise only; no transient, protection, motor-start, or energization validation.",
         "Budgets and sequence require system-specific operator review."],
        [{"title": "NERC documented black-start procedure practice guide",
          "url": "https://www.nerc.com/pa/comp/guidance/CMEPPracticeGuidesDL/CMEP%20Practice%20Guide%20-%20Evaluating%20Blackstart%20Documented%20Procedures.pdf"}]),
    _entry("lessons-hydrogen", "lessons", "Hydrogen energy pathway",
        "Close the electrolyzer, compression, LHV storage, and fuel-cell energy ledger.", "learning",
        [_f("electrolyzer_kwh_per_kg", "Electrolyzer electricity", 52, 33.3, 200, 0.5, "kWh/kg H2"),
         _f("compression_kwh_per_kg", "Compression electricity", 2, 0, 100, 0.5, "kWh/kg H2"),
         _f("fuel_cell_electric_efficiency", "Fuel-cell efficiency", 0.5, 0, 1, 0.01, "fraction"),
         _f("hydrogen_lhv_kwh_per_kg", "Hydrogen LHV", 33.3, 33.3, 33.3, 0.1, "kWh/kg H2")],
        [_d("batch", "Hydrogen batch", {"hydrogen_kg": 100, "batch_id": "synthetic-batch-01"})],
        ["chemical energy = hydrogen mass * 33.3 kWh/kg (LHV basis)",
         "fuel-cell electricity = chemical energy * electric efficiency",
         "electricity input = useful output + electrolysis + compression + fuel-cell losses"],
        ["Stage parameters are illustrative, not measured plant performance.",
         "Compression boundary, delivery pressure, leakage, and plant auxiliaries are not modeled."],
        [{"title": "DOE hydrogen technical targets and LHV basis",
          "url": "https://www.energy.gov/cmei/fuels/doe-technical-targets-onboard-hydrogen-storage-light-duty-vehicles"},
         {"title": "DOE hydrogen compression energy requirements",
          "url": "https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/9013_energy_requirements_for_hydrogen_gas_compression.pdf"}]),
    _entry("compare-pareto", "compare", "Comparable-run Pareto screen",
        "Show cost, service, SOC endpoints, sampled expected loss-of-load hours, dominance, and a disclosed weighted preference.", "comparison",
        [_f("cost_weight", "Cost weight", 0.4, 0, 1, 0.05, "fraction"),
         _f("service_weight", "Service weight", 0.3, 0, 1, 0.05, "fraction"),
         _f("loss_of_load_weight", "Expected loss-of-load weight", 0.3, 0, 1, 0.05, "fraction")],
        [_d("candidates", "Scenario-tagged run results", _pareto_candidates())],
        ["a dominates b when it is no worse on all objectives and strictly better on one",
         "score = weighted sum of within-group min-max normalized objectives"],
        ["Comparison requires matching scenario, sample-set key, horizon, service basis, and sample count.",
         "Expected loss-of-load hours are supplied estimates; recommendation depends on user weights."],
        [{"title": "A fast and elitist multiobjective genetic algorithm (Pareto dominance)",
          "url": "https://doi.org/10.1109/4235.996017"}]),
    _entry("compare-dunkelflaute", "compare", "Fourteen-day storage dispatch",
        "Dispatch storage over a non-repeating synthetic 336-hour path with fixed initial and terminal SOC.", "comparison",
        [_f("energy_capacity_kwh", "Storage energy", 500, 0.001, 10000000, 10, "kWh"),
         _f("power_limit_kw", "Charge/discharge limit", 120, 0.001, 1000000, 10, "kW"),
         _f("charge_efficiency", "Charge efficiency", 0.94, 0.01, 1, 0.01, "fraction"),
         _f("discharge_efficiency", "Discharge efficiency", 0.94, 0.01, 1, 0.01, "fraction"),
         _f("initial_soc_kwh", "Fixed initial/terminal SOC", 250, 0, 10000000, 10, "kWh")],
        [_d("load_kw", "336 hourly demand values", _DUNKEL_LOAD),
         _d("renewable_kw", "336 hourly renewable values", _DUNKEL_RENEWABLE)],
        ["renewable + discharge + shortfall = load + charge + curtailment",
         "SOC[t+1] = SOC[t] + charge efficiency*charge - discharge/discharge efficiency",
         "charge <= power limit*mode; discharge <= power limit*(1-mode); mode is binary",
         "minimize shortfall subject to SOC[0] = SOC[336] = initial SOC"],
        ["One synthetic 336-hour weather path, not a repeated demo day or statistical LOLE estimate.",
         "Reduced mixed-integer dispatch enforces battery direction but omits degradation, reserves, network, and market constraints."],
        [{"title": "SciPy mixed-integer linear programming with HiGHS",
          "url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html"}]),
    _entry("compare-thermal", "compare", "Thermal and cycle-wear screen",
        "Compare utilization, equivalent full cycles, an explicit temperature multiplier, and three-axis radar data.", "comparison",
        [_f("reference_temperature_c", "Reference temperature", 25, -40, 100, 1, "°C"),
         _f("temperature_factor_per_c", "Assumed exponential factor per °C", 0.025, 0, 0.1, 0.001, "1/°C"),
         _f("screening_loss_fraction_per_1000_efc", "Assumed loss per 1,000 EFC", 0.025, 0, 1, 0.005, "fraction"),
         _f("years", "Screening horizon", 1, 1, 30, 1, "year")],
        [_d("regimes", "Operating regimes", _thermal_regimes())],
        ["EFC = years * 365 * cycles/day * utilization * depth of discharge",
         "thermal multiplier = exp(user factor * (temperature - reference temperature))",
         "screening wear index = EFC * user loss fraction / 1000 * thermal multiplier"],
        ["Temperature factor and cycle-loss rate are assumptions, not fitted cell-aging laws.",
         "Wear index may exceed 100%; it is not a capacity-fade forecast, warranty, or safety limit."],
        [{"title": "NREL Battery Lifetime Analysis and Simulation Tool overview",
          "url": "https://www.nrel.gov/transportation/battery-lifespan.html"}]),
    _entry("pilots-photogrammetry", "pilots", "Paired as-built geometry check",
        "Compute 3D paired-point residuals, RMSE, maximum, and a selected percentile.", "pilot",
        [_f("coordinate_scale_m", "Coordinate-to-metre scale", 1, 0.000001, 100000, 0.1, "m/unit"),
         _f("reporting_limit_m", "User reporting limit", 0.05, 0, 100000, 0.01, "m"),
         _f("percentile", "Error percentile", 95, 50, 99.9, 1, "%")],
        [_d("design_points_xyz", "Design XYZ points, index-paired", [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]),
         _d("asbuilt_points_xyz", "As-built XYZ points, index-paired", [[0.01, 0, 0], [1, 0.02, 0], [0, 1, -0.03], [0, 0, 1.04]])],
        ["error[i] = norm(as-built XYZ[i] - design XYZ[i]) * coordinate scale",
         "3D RMSE = sqrt(mean(error[i]^2))", "selected error = empirical percentile of paired errors"],
        ["Pairs are matched by array index; no registration, nearest-neighbour search, camera model, or drone connector.",
         "The user reporting limit does not establish survey or construction acceptance."],
        [{"title": "ASPRS Positional Accuracy Standards",
          "url": "https://www.asprs.org/Main/Main/Standards/Positional-Accuracy-Standards.aspx"}]),
    _entry("pilots-dts", "pilots", "Distributed temperature profile",
        "Report fresh hot spots, spatial gradients, missing samples, and stale observations.", "pilot",
        [_f("hot_spot_threshold_c", "User hot-spot threshold", 75, -50, 200, 1, "°C"),
         _f("gradient_threshold_c_per_m", "User gradient threshold", 0.25, 0, 100000, 0.05, "°C/m"),
         _f("maximum_age_hours", "Maximum data age", 2, 0, 100000, 0.25, "h"),
         _f("current_time_hour", "Supplied current time", 10, 0, 1000000, 1, "h")],
        [_d("samples", "Spatial temperature samples with timestamps", _dts_samples())],
        ["gradient = abs(adjacent temperature difference) / adjacent distance",
         "fresh when current time - observed time <= user maximum age"],
        ["Sample temperatures and the user threshold are bounded to -50–200 °C; adjacent samples must be at least 0.1 m apart.",
         "Thresholds are user screening values; no cable rating or calibrated alarm is claimed. Missing and stale observations are excluded from current thermal summaries."],
        [{"title": "Spatial patterns and limits in distributed temperature sensing",
          "url": "https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/wrcr.20144"}]),
    _entry("pilots-offgas", "pilots", "Hypothetical multisensor warning vote",
        "Apply temperature, CO, and VOC thresholds and a sensor-level voting rule.", "pilot",
        [_f("temperature_threshold_c", "User temperature threshold", 70, -100, 500, 1, "°C"),
         _f("co_threshold_ppm", "User CO threshold", 35, 0.001, 100000, 1, "ppm"),
         _f("voc_threshold_ppm", "User VOC threshold", 5, 0.001, 100000, 0.5, "ppm"),
         _f("votes_required", "Sensor votes required", 2, 1, 32, 1, "sensors")],
        [_d("sensors", "Temperature/CO/VOC readings", _offgas_sensors())],
        ["sensor vote = any present channel meets or exceeds its user threshold",
         "warning state = sensor votes >= required votes"],
        ["Hypothetical logic only; thresholds are not calibrated alarms, exposure limits, or hazard controls.",
         "No gas analyser, sensor-health connector, cross-sensitivity model, or field alarm is implemented."],
        [{"title": "NIOSH Pocket Guide to Chemical Hazards (reference information only)",
          "url": "https://www.cdc.gov/niosh/npg/"}]),
    _entry("council-debate", "council", "Finance versus storage debate",
        "Create deterministic proposer/challenger rounds and leave unresolved evidence conflicts visible.", "council",
        [_f("capex_eur", "Illustrative capex", 1200000, 0, 1000000000000, 10000, "EUR"),
         _f("annual_net_value_eur", "Illustrative annual value", 230000, -1000000000, 1000000000, 1000, "EUR/year"),
         _f("life_years", "Illustrative life", 15, 1, 60, 1, "year"),
         _f("discount_rate_fraction", "Discount rate", 0.08, 0, 0.5, 0.01, "fraction")],
        [_d("finance_evidence", "Proposer evidence", _finance_evidence()),
         _d("storage_evidence", "Challenger evidence", _storage_evidence())],
        ["NPV = -capex + sum(annual net value / (1 + discount rate)^year)",
         "matched claims converge only when units agree and values fit declared tolerance"],
        ["Rounds are deterministic comparisons of supplied assertions; no LLM or external agent is called.",
         "Conflicts remain disputed; the NPV screen is not approval or a dispatch-finance bridge."],
        [{"title": "NREL levelized cost of energy documentation",
          "url": "https://samrepo.nlr.gov/help/mtf_lcoe.html"}]),
    _entry("council-evidence", "council", "Structured evidence manifest",
        "Check supplied tariff, warranty, and single-line JSON metadata for units, age, expiry, bounds, and provenance.", "council",
        [_f("maximum_manifest_age_days", "Maximum age", 3650, 0, 36500, 30, "days"),
         _f("maximum_tariff_eur_mwh", "Tariff upper bound", 2000, 0.001, 100000, 10, "EUR/MWh"),
         _f("maximum_warranty_years", "Warranty upper bound", 50, 0.001, 100, 1, "years"),
         _f("maximum_single_line_nodes", "Node-count upper bound", 10000, 1, 1000000, 100, "nodes")],
        [_d("manifest", "Structured document manifest",
            {"as_of_date": "2026-10-17", "documents": _manifest_documents()})],
        ["age = as-of date - issue date", "expiry finding when expiry date < as-of date",
         "field check = expected field name and unit plus configured numeric bound"],
        ["Structured JSON metadata only; no OCR, retrieval, signature validation, or authenticity verification.",
         "Provenance references are user-supplied text and are not independently checked."],
        [{"title": "Pydantic JSON validation behavior",
          "url": "https://docs.pydantic.dev/latest/concepts/json/"}]),
    _entry("council-consensus", "council", "Bayesian evidence toy model",
        "Update a binary prior from explicit likelihood ratios and show normalized probability and Shannon entropy.", "council",
        [_f("prior_probability", "Prior probability", 0.35, 0, 1, 0.01, "probability"),
         _f("maximum_absolute_log_likelihood_ratio", "Per-item log-LR cap", 4, 0, 20, 0.25, "log ratio"),
         _f("evidence_weight", "Illustrative evidence weight", 1, 0, 1, 0.05, "fraction")],
        [_d("evidence", "Likelihood ratios and dependency labels", _consensus_evidence())],
        ["posterior odds = prior odds * product(likelihood ratios)",
         "posterior probability = odds / (1 + odds)",
         "binary Shannon entropy = -p log2(p) - (1-p) log2(1-p)"],
        ["Likelihood ratios are hypothetical; raw product assumes conditional independence.",
         "Repeated dependency groups are flagged, not deduplicated; no unanimity or approval is inferred."],
        [{"title": "NIST Bayesian reliability evaluation",
          "url": "https://www.itl.nist.gov/div898/handbook/apr/section2/apr1a.htm"},
         {"title": "Claude Shannon, A Mathematical Theory of Communication",
          "url": "https://www.princeton.edu/~wbialek/rome/refs/shannon_48.pdf"}]),
]


def _metric(label: str, value, unit: str) -> dict:
    return {"label": label, "value": value, "unit": unit}


def _result(metrics: list[dict], *, series: list[dict] | None = None,
            table: list[dict] | None = None, details: dict | None = None,
            warnings: list[str] | None = None) -> dict:
    import json
    result = {"metrics": metrics, "series": series or [], "table": table or [],
              "details": details or {}, "warnings": warnings or []}
    json.dumps(result, allow_nan=False)
    return result


def _run_duck(p: DuckInput) -> dict:
    net = [load - solar - wind for load, solar, wind in zip(p.load_kw, p.solar_kw, p.wind_kw)]
    ramps = [None] + [(net[i] - net[i - 1]) / p.interval_hours for i in range(1, len(net))]
    load_energy = sum(p.load_kw) * p.interval_hours
    renewable_energy = sum(s + w for s, w in zip(p.solar_kw, p.wind_kw)) * p.interval_hours
    net_energy = sum(net) * p.interval_hours
    up_ramps = [r for r in ramps[1:] if r is not None]
    exceed = sum(r > p.ramp_limit_kw_per_hour for r in up_ramps)
    ramp_percentile = float(np.percentile(up_ramps, p.ramp_percentile)) if up_ramps else 0.0
    x = [i * p.interval_hours for i in range(len(net))]
    table = [{"interval": i, "hour": x[i], "load_kw": p.load_kw[i], "solar_kw": p.solar_kw[i],
              "wind_kw": p.wind_kw[i], "net_load_kw": net[i], "ramp_kw_per_hour": ramps[i]}
             for i in range(len(net))]
    return _result([
        _metric("Demand energy", load_energy, "kWh"),
        _metric("Renewable energy", renewable_energy, "kWh"),
        _metric("Net-load energy", net_energy, "kWh"),
        _metric("Energy closure residual", load_energy - renewable_energy - net_energy, "kWh"),
        _metric("Peak net load", max(net), "kW"),
        _metric("Maximum upward ramp", max(up_ramps, default=0), "kW/h"),
        _metric(f"P{p.ramp_percentile:g} upward ramp", ramp_percentile, "kW/h"),
        _metric("Upward ramps above marker", exceed, "intervals"),
    ], series=[{"name": "net_load", "x_label": "hour", "y_unit": "kW", "x": x, "y": net},
               {"name": "ramp", "x_label": "hour", "y_unit": "kW/h", "x": x, "y": ramps}],
       table=table, details={"worked_answers": {"load_energy_kwh": load_energy,
           "renewable_energy_kwh": renewable_energy, "net_load_energy_kwh": net_energy,
           "maximum_upward_ramp_kw_per_hour": max(up_ramps, default=0)},
           "interval_hours": p.interval_hours, "interval_count": len(net)},
       warnings=["Synthetic equal-duration teaching data; not a dispatch or grid-compliance model."])


def _run_blackstart(p: BlackstartInput) -> dict:
    state = "dark"
    available_kw = p.gfm_rated_kw * p.available_power_fraction
    budget_kw = p.gfm_rated_kw * (p.available_power_fraction - p.reserve_fraction)
    rows = []
    for i, step in enumerate(p.steps):
        reason = ""
        next_state = state
        if step.active_kw + step.inrush_kw > budget_kw + 1e-9:
            reason = "active power plus inrush exceeds post-reserve budget"
        elif step.inrush_kw > p.inrush_budget_kw + 1e-9:
            reason = "inrush exceeds configured exercise budget"
        elif step.action == "start_gfm" and state != "dark":
            reason = "source can start only from dark state"
        elif step.action == "start_gfm":
            next_state = "grid_forming_ready"
        elif step.action == "energize_bus" and state != "grid_forming_ready":
            reason = "bus energization requires a ready grid-forming source"
        elif step.action == "energize_bus":
            next_state = "bus_energized"
        elif step.action == "connect_load" and state not in {"bus_energized", "load_restored"}:
            reason = "load connection requires an energized bus"
        elif step.action == "connect_load":
            next_state = "load_restored"
        accepted = not reason
        if accepted:
            state = next_state
        rows.append({"step": i + 1, "label": step.label, "action": step.action,
                     "active_kw": step.active_kw, "inrush_kw": step.inrush_kw,
                     "combined_kw": step.active_kw + step.inrush_kw, "accepted": accepted,
                     "state_after": state, "reason": reason or "within modeled sequence and budgets"})
    accepted_count = sum(row["accepted"] for row in rows)
    return _result([
        _metric("Final exercise state", state, "state"),
        _metric("Accepted steps", accepted_count, "steps"),
        _metric("Rejected steps", len(rows) - accepted_count, "steps"),
        _metric("Available active-power budget", available_kw, "kW"),
        _metric("Post-reserve step budget", budget_kw, "kW"),
    ], table=rows, details={"state_sequence": ["dark"] + [row["state_after"] for row in rows],
        "available_kw": available_kw, "post_reserve_budget_kw": budget_kw,
        "complete": state == "load_restored" and accepted_count == len(rows)},
       warnings=["Finite-state procedural exercise only; no transient, protection, motor-start, or real black-start validation."])


def _run_hydrogen(p: HydrogenInput) -> dict:
    mass = p.batch.hydrogen_kg
    el_in = mass * p.electrolyzer_kwh_per_kg
    compression = mass * p.compression_kwh_per_kg
    chemical = mass * p.hydrogen_lhv_kwh_per_kg
    fc_out = chemical * p.fuel_cell_electric_efficiency
    el_loss = el_in - chemical
    fc_loss = chemical - fc_out
    total_in = el_in + compression
    losses = el_loss + compression + fc_loss
    residual = total_in - fc_out - losses
    efficiency = fc_out / total_in if total_in else None
    return _result([
        _metric("Electrolyzer electricity", el_in, "kWh"),
        _metric("Compression electricity", compression, "kWh"),
        _metric("Stored hydrogen chemical energy", chemical, "kWh LHV"),
        _metric("Fuel-cell electricity", fc_out, "kWh"),
        _metric("Electric round-trip efficiency", efficiency, "fraction"),
        _metric("Energy closure residual", residual, "kWh"),
    ], table=[
        {"stage": "electrolyzer", "electricity_in_kwh": el_in,
         "chemical_energy_out_kwh_lhv": chemical, "loss_kwh": el_loss},
        {"stage": "compression", "electricity_in_kwh": compression,
         "chemical_energy_out_kwh_lhv": 0, "loss_kwh": compression},
        {"stage": "fuel_cell", "chemical_energy_in_kwh_lhv": chemical,
         "electricity_out_kwh": fc_out, "loss_kwh": fc_loss},
    ], details={"batch_id": p.batch.batch_id, "hydrogen_kg": mass,
        "lhv_basis_kwh_per_kg": p.hydrogen_lhv_kwh_per_kg,
        "total_electricity_input_kwh": total_in, "useful_electricity_output_kwh": fc_out,
        "accounted_losses_kwh": losses, "energy_closure_residual_kwh": residual},
       warnings=["LHV ledger with user-entered stage parameters; no pressure, leakage, degradation, or measured plant performance model."])


def _run_pareto(p: ParetoInput) -> dict:
    groups: dict[tuple, list[ParetoCandidate]] = defaultdict(list)
    for row in p.candidates:
        key = (row.scenario_key, row.sample_set_key, row.horizon_hours,
               row.service_basis, row.sample_count)
        groups[key].append(row)
    attributes = {}
    group_rows = []
    recommendations = []
    for number, (key, candidates) in enumerate(groups.items(), 1):
        group_id = f"comparison-{number}"
        comparable = len(candidates) >= 2
        dominators = {row.run_id: [] for row in candidates}
        scores = {}
        if comparable:
            for candidate in candidates:
                for other in candidates:
                    if other.run_id == candidate.run_id:
                        continue
                    no_worse = (other.cost_eur <= candidate.cost_eur and
                        other.served_load_pct >= candidate.served_load_pct and
                        other.expected_loss_of_load_hours <= candidate.expected_loss_of_load_hours)
                    better = (other.cost_eur < candidate.cost_eur or
                        other.served_load_pct > candidate.served_load_pct or
                        other.expected_loss_of_load_hours < candidate.expected_loss_of_load_hours)
                    if no_worse and better:
                        dominators[candidate.run_id].append(other.run_id)
            costs = [x.cost_eur for x in candidates]
            service = [x.served_load_pct for x in candidates]
            lole = [x.expected_loss_of_load_hours for x in candidates]
            def minimize(value, values):
                low, high = min(values), max(values)
                return 1.0 if high == low else (high - value) / (high - low)
            def maximize(value, values):
                low, high = min(values), max(values)
                return 1.0 if high == low else (value - low) / (high - low)
            for row in candidates:
                scores[row.run_id] = (p.cost_weight * minimize(row.cost_eur, costs) +
                    p.service_weight * maximize(row.served_load_pct, service) +
                    p.loss_of_load_weight * minimize(row.expected_loss_of_load_hours, lole))
            winner = max(candidates, key=lambda x: (scores[x.run_id], x.run_id))
            recommendations.append({"comparison_group": group_id, "recommended_run_id": winner.run_id,
                "score": scores[winner.run_id], "weights": {"cost": p.cost_weight,
                "served_load": p.service_weight, "expected_loss_of_load_hours": p.loss_of_load_weight},
                "tie_break": "lexicographically last run_id when normalized scores tie",
                "interpretation": "weighted preference within this comparable group"})
        for row in candidates:
            attributes[row.run_id] = {"comparison_group": group_id, "comparable": comparable,
                "dominated_by": dominators[row.run_id] if comparable else [],
                "pareto_nondominated": comparable and not dominators[row.run_id],
                "weighted_score": scores.get(row.run_id)}
        group_rows.append({"comparison_group": group_id, "scenario_key": key[0],
            "sample_set_key": key[1], "horizon_hours": key[2], "service_basis": key[3],
            "sample_count": key[4], "run_count": len(candidates), "comparable": comparable})
    table = []
    for row in p.candidates:
        table.append({"run_id": row.run_id, "scenario_key": row.scenario_key,
            "sample_set_key": row.sample_set_key, "horizon_hours": row.horizon_hours,
            "sample_count": row.sample_count, "cost_eur": row.cost_eur,
            "served_load_pct": row.served_load_pct, "initial_soc_kwh": row.initial_soc_kwh,
            "terminal_soc_kwh": row.terminal_soc_kwh,
            "expected_loss_of_load_hours": row.expected_loss_of_load_hours,
            **attributes[row.run_id]})
    nondominated = [row["run_id"] for row in table if row["pareto_nondominated"]]
    warnings = ["Comparison requires matching scenario, sample-set key, horizon, service basis, and sample count.",
        "Expected loss-of-load hours are supplied sampled estimates; this study does not compute or validate an ensemble.",
        "Weighted preference uses disclosed within-group min-max scaling and user weights."]
    if not recommendations:
        warnings.append("No group contains two comparable runs; no recommendation or dominance relation is reported.")
    return _result([_metric("Comparable groups", sum(x["comparable"] for x in group_rows), "groups"),
        _metric("Pareto-nondominated runs", len(nondominated), "runs"),
        _metric("Weighted recommendations", len(recommendations), "groups")],
        table=table, details={"groups": group_rows, "recommendations": recommendations,
            "pareto_nondominated_run_ids": nondominated,
            "objective_directions": {"cost_eur": "minimize", "served_load_pct": "maximize",
                                     "expected_loss_of_load_hours": "minimize"}}, warnings=warnings)


def _run_dunkelflaute(p: DunkelflauteInput) -> dict:
    n = 336
    # Variables are charge[N], discharge[N], SOC[N+1], curtail[N], unserved[N], and mode[N].
    c0, d0, soc0 = 0, n, 2*n
    curtailed0, unserved0 = 3*n + 1, 4*n + 1
    mode0 = 5*n + 1
    size = mode0 + n
    aeq = lil_matrix((2*n + 2, size), dtype=float)
    beq = np.zeros(2*n + 2)
    for t in range(n):
        # renewable + discharge + unserved = load + charge + curtailment
        aeq[t, c0+t] = 1
        aeq[t, d0+t] = -1
        aeq[t, curtailed0+t] = 1
        aeq[t, unserved0+t] = -1
        beq[t] = p.renewable_kw[t] - p.load_kw[t]
        # SOC[t+1] = SOC[t] + eta_charge*charge - discharge/eta_discharge
        aeq[n+t, soc0+t] = -1
        aeq[n+t, soc0+t+1] = 1
        aeq[n+t, c0+t] = -p.charge_efficiency
        aeq[n+t, d0+t] = 1/p.discharge_efficiency
    aeq[2*n, soc0] = 1
    beq[2*n] = p.initial_soc_kwh
    aeq[2*n+1, soc0+n] = 1
    beq[2*n+1] = p.initial_soc_kwh
    direction = lil_matrix((2*n, size), dtype=float)
    direction_upper = np.empty(2*n, dtype=float)
    for t in range(n):
        # mode=1 permits charge; mode=0 permits discharge.
        direction[2*t, c0+t] = 1
        direction[2*t, mode0+t] = -p.power_limit_kw
        direction_upper[2*t] = 0
        direction[2*t+1, d0+t] = 1
        direction[2*t+1, mode0+t] = p.power_limit_kw
        direction_upper[2*t+1] = p.power_limit_kw
    constraints_matrix = vstack([aeq.tocsr(), direction.tocsr()], format="csr")
    constraints = LinearConstraint(
        constraints_matrix,
        np.concatenate([beq, np.full(2*n, -np.inf)]),
        np.concatenate([beq, direction_upper]),
    )
    lower_bounds = np.zeros(size, dtype=float)
    upper_bounds = np.array(
        [p.power_limit_kw]*n + [p.power_limit_kw]*n + [p.energy_capacity_kwh]*(n+1) +
        list(p.renewable_kw) + list(p.load_kw) + [1.0]*n,
        dtype=float,
    )
    integrality = np.zeros(size, dtype=np.uint8)
    integrality[mode0:] = 1
    bounds = Bounds(lower_bounds, upper_bounds)

    # Stage 1 minimizes unserved energy; stage 2 breaks ties without sacrificing service.
    objective_1 = np.zeros(size)
    objective_1[unserved0:unserved0+n] = 1
    first = milp(objective_1, integrality=integrality, bounds=bounds, constraints=constraints)
    if not first.success:
        raise RuntimeError(f"336-hour dispatch MILP failed: {first.message}")
    minimum_unserved = float(sum(first.x[unserved0:unserved0+n]))
    aub = lil_matrix((1, size), dtype=float)
    for t in range(n):
        aub[0, unserved0+t] = 1
    objective_2 = np.zeros(size)
    for t in range(n):
        objective_2[curtailed0+t] = 1
        objective_2[c0+t] = 1e-7
        objective_2[d0+t] = 1e-7
    second = milp(objective_2, integrality=integrality, bounds=bounds,
                  constraints=[constraints, LinearConstraint(aub.tocsr(), -np.inf, minimum_unserved + 1e-7)])
    if not second.success:
        raise RuntimeError(f"336-hour dispatch tie-break MILP failed: {second.message}")
    x = second.x
    charge, discharge = x[c0:c0+n], x[d0:d0+n]
    soc = x[soc0:soc0+n+1]
    curtail, unserved = x[curtailed0:curtailed0+n], x[unserved0:unserved0+n]
    power_residual = (sum(p.renewable_kw) + sum(discharge) + sum(unserved) -
                      sum(p.load_kw) - sum(charge) - sum(curtail))
    storage_loss = (1-p.charge_efficiency)*sum(charge) + (1/p.discharge_efficiency-1)*sum(discharge)
    shortfall_hours = int(sum(v > 1e-7 for v in unserved))
    table = [{"hour": t, "load_kw": p.load_kw[t], "renewable_kw": p.renewable_kw[t],
        "charge_kw": float(charge[t]), "discharge_kw": float(discharge[t]),
        "curtailment_kw": float(curtail[t]), "shortfall_kw": float(unserved[t]),
        "soc_start_kwh": float(soc[t]), "soc_end_kwh": float(soc[t+1])} for t in range(n)]
    return _result([
        _metric("Total unserved energy", float(sum(unserved)), "kWh"),
        _metric("Shortfall intervals", shortfall_hours, "hours"),
        _metric("Renewable energy", sum(p.renewable_kw), "kWh"),
        _metric("Curtailed renewable energy", float(sum(curtail)), "kWh"),
        _metric("Battery charge energy", float(sum(charge)), "kWh"),
        _metric("Battery discharge energy", float(sum(discharge)), "kWh"),
        _metric("Terminal SOC", float(soc[-1]), "kWh"),
        _metric("Electric balance residual", power_residual, "kWh"),
    ], series=[
        {"name": "load", "x_label": "hour", "y_unit": "kW", "x": list(range(n)), "y": p.load_kw},
        {"name": "renewable", "x_label": "hour", "y_unit": "kW", "x": list(range(n)), "y": p.renewable_kw},
        {"name": "storage_soc", "x_label": "hour boundary", "y_unit": "kWh",
         "x": list(range(n+1)), "y": [float(v) for v in soc]},
    ], table=table, details={"interval_count": n, "horizon_hours": 336,
        "initial_soc_kwh": p.initial_soc_kwh, "terminal_soc_kwh": float(soc[-1]),
        "soc_min_kwh": float(np.min(soc)), "soc_max_kwh": float(np.max(soc)),
        "storage_loss_kwh": float(storage_loss), "minimum_unserved_energy_kwh": minimum_unserved,
        "electric_balance_residual_kwh": power_residual,
        "optimizer": "scipy.optimize.milp (HiGHS), with binary charge/discharge direction controls",
        "tie_break": "minimize curtailment and then small throughput cost at fixed minimum shortfall"},
       warnings=["One synthetic 336-hour (14-day) weather path; shortfall intervals are not statistical LOLE.",
        "Reduced mixed-integer dispatch enforces one battery direction per interval with efficiency, power, energy, and cyclic SOC; it omits network, market, reserve, and degradation constraints."])


def _run_thermal(p: ThermalInput) -> dict:
    rows, radar = [], []
    for regime in p.regimes:
        efc = p.years*365*regime.cycles_per_day_at_full_utilization*regime.utilization_fraction*regime.depth_of_discharge_fraction
        factor = exp(p.temperature_factor_per_c*(regime.ambient_temperature_c-p.reference_temperature_c))
        wear = 100*p.screening_loss_fraction_per_1000_efc*efc*factor/1000
        axes = ["utilization_pct", "thermal_multiplier", "screening_wear_index_pct"]
        values = [100*regime.utilization_fraction, factor, wear]
        rows.append({"regime": regime.regime, "utilization_pct": values[0],
            "equivalent_full_cycles": efc, "ambient_temperature_c": regime.ambient_temperature_c,
            "thermal_multiplier": factor, "screening_wear_index_pct": wear})
        radar.append({"name": regime.regime, "axes": axes, "values": values})
    return _result([
        _metric("Operating regimes", len(rows), "regimes"),
        _metric("Maximum screening wear index", max(r["screening_wear_index_pct"] for r in rows), "% index"),
        _metric("Maximum equivalent full cycles", max(r["equivalent_full_cycles"] for r in rows), "EFC"),
    ], table=rows, details={"radar_axes": ["utilization_pct", "thermal_multiplier", "screening_wear_index_pct"],
        "radar_series": radar, "assumptions": {"temperature_factor_per_c": p.temperature_factor_per_c,
        "screening_loss_fraction_per_1000_efc": p.screening_loss_fraction_per_1000_efc,
        "reference_temperature_c": p.reference_temperature_c, "years": p.years}},
       warnings=["Exposed screening assumptions are not an electrochemical aging model or capacity-fade prediction."])


def _run_photogrammetry(p: PhotogrammetryInput) -> dict:
    residuals, errors = [], []
    for design, actual in zip(p.design_points_xyz, p.asbuilt_points_xyz):
        delta = [(actual[i]-design[i])*p.coordinate_scale_m for i in range(3)]
        residuals.append(delta)
        errors.append(sqrt(sum(x*x for x in delta)))
    if errors:
        rmse = sqrt(sum(x*x for x in errors)/len(errors))
        maximum = max(errors)
        quantile = float(np.percentile(errors, p.percentile, method="linear"))
        over_limit = sum(error > p.reporting_limit_m for error in errors)
    else:
        rmse = maximum = quantile = None
        over_limit = 0
    table = [{"point_index": i, "dx_m": v[0], "dy_m": v[1], "dz_m": v[2],
              "error_m": errors[i], "above_reporting_limit": errors[i] > p.reporting_limit_m}
             for i, v in enumerate(residuals)]
    warnings = ["Points pair by array index; no registration or nearest-neighbour matching is attempted.",
                "The user reporting limit does not certify survey or construction accuracy."]
    if not errors:
        warnings.append("No point pairs were supplied; error metrics are null.")
    return _result([
        _metric("Paired point count", len(errors), "points"), _metric("3D RMSE", rmse, "m"),
        _metric("Maximum paired error", maximum, "m"),
        _metric(f"P{p.percentile:g} paired error", quantile, "m"),
        _metric("Points above user reporting limit", over_limit, "points"),
    ], series=[{"name": "paired_error", "x_label": "point index", "y_unit": "m",
                "x": list(range(len(errors))), "y": errors}],
       table=table, details={"coordinate_scale_m": p.coordinate_scale_m,
        "reporting_limit_m": p.reporting_limit_m, "percentile": p.percentile,
        "pairing_assumption": "same array index"}, warnings=warnings)


def _run_dts(p: DtsInput) -> dict:
    fresh, missing_count, stale_count = [], 0, 0
    fresh_ids = set()
    for index, sample in enumerate(p.samples):
        age = p.current_time_hour - sample.observed_at_hour
        if sample.temperature_c is None:
            missing_count += 1
        elif age > p.maximum_age_hours:
            stale_count += 1
        else:
            fresh_ids.add(index)
            fresh.append({"distance_m": sample.distance_m, "temperature_c": sample.temperature_c,
                          "age_hours": age})
    hot = [row for row in fresh if row["temperature_c"] >= p.hot_spot_threshold_c]
    gradients = []
    for index, (a, b) in enumerate(zip(p.samples, p.samples[1:])):
        if index not in fresh_ids or index + 1 not in fresh_ids:
            continue
        value = abs(b.temperature_c - a.temperature_c) / (b.distance_m - a.distance_m)
        gradients.append({"from_m": a.distance_m, "to_m": b.distance_m,
                          "gradient_c_per_m": value, "above_threshold": value >= p.gradient_threshold_c_per_m})
    max_temp = max((row["temperature_c"] for row in fresh), default=None)
    max_gradient = max((row["gradient_c_per_m"] for row in gradients), default=None)
    table = [{"distance_m": row["distance_m"], "temperature_c": row["temperature_c"],
              "age_hours": row["age_hours"], "hot_spot": row in hot} for row in fresh]
    for sample in p.samples:
        age = p.current_time_hour-sample.observed_at_hour
        if sample.temperature_c is None or age > p.maximum_age_hours:
            table.append({"distance_m": sample.distance_m, "temperature_c": sample.temperature_c,
                "age_hours": age, "hot_spot": False,
                "data_status": "missing" if sample.temperature_c is None else "stale"})
    warnings = ["Thresholds are user screening values, not calibrated cable alarms or asset limits.",
                "Missing and stale observations are excluded from hot-spot and adjacent-gradient calculations."]
    if not fresh:
        warnings.append("No fresh non-missing sample is available; current maximum temperature is null.")
    return _result([
        _metric("Fresh samples", len(fresh), "samples"),
        _metric("Missing samples", missing_count, "samples"),
        _metric("Stale samples", stale_count, "samples"),
        _metric("Hot spots above user threshold", len(hot), "samples"),
        _metric("Maximum fresh temperature", max_temp, "°C"),
        _metric("Maximum adjacent fresh gradient", max_gradient, "°C/m"),
    ], series=[{"name": "temperature", "x_label": "distance", "y_unit": "°C",
        "x": [s.distance_m for s in p.samples],
        "y": [s.temperature_c if s.temperature_c is not None and
              p.current_time_hour-s.observed_at_hour <= p.maximum_age_hours else None for s in p.samples]}],
       table=table, details={"hot_spots": hot, "adjacent_gradients": gradients,
        "gradient_exceedance_count": sum(row["above_threshold"] for row in gradients),
        "thresholds": {"hot_spot_c": p.hot_spot_threshold_c,
            "gradient_c_per_m": p.gradient_threshold_c_per_m, "maximum_age_hours": p.maximum_age_hours}},
       warnings=warnings)


def _run_offgas(p: OffgasInput) -> dict:
    table, voters = [], []
    exceedances = {"temperature": 0, "co": 0, "voc": 0}
    missing_count = 0
    for sensor in p.sensors:
        flags = {
            "temperature": sensor.temperature_c is not None and sensor.temperature_c >= p.temperature_threshold_c,
            "co": sensor.co_ppm is not None and sensor.co_ppm >= p.co_threshold_ppm,
            "voc": sensor.voc_ppm is not None and sensor.voc_ppm >= p.voc_threshold_ppm,
        }
        missing = [name for name, value in (("temperature", sensor.temperature_c),
            ("co", sensor.co_ppm), ("voc", sensor.voc_ppm)) if value is None]
        missing_count += len(missing)
        for key in flags:
            exceedances[key] += int(flags[key])
        vote = any(flags.values())
        if vote:
            voters.append(sensor.sensor_id)
        table.append({"sensor_id": sensor.sensor_id, "temperature_c": sensor.temperature_c,
            "co_ppm": sensor.co_ppm, "voc_ppm": sensor.voc_ppm, "channel_exceedances": flags,
            "missing_channels": missing, "sensor_vote": vote})
    warning = len(voters) >= p.votes_required
    return _result([
        _metric("Sensors voting", len(voters), "sensors"),
        _metric("Required votes", p.votes_required, "sensors"),
        _metric("Hypothetical warning state", "warning" if warning else "no warning", "state"),
        _metric("Missing channel readings", missing_count, "channels"),
        _metric("Temperature exceedances", exceedances["temperature"], "sensors"),
        _metric("CO exceedances", exceedances["co"], "sensors"),
        _metric("VOC exceedances", exceedances["voc"], "sensors"),
    ], table=table, details={"voting_sensor_ids": voters,
        "thresholds": {"temperature_c": p.temperature_threshold_c,
                       "co_ppm": p.co_threshold_ppm, "voc_ppm": p.voc_threshold_ppm},
        "logic": "one vote per sensor if any present channel meets or exceeds its threshold"},
       warnings=["Hypothetical user-threshold voting only; not calibrated alarms, exposure limits, or hazard controls.",
        "No gas analyser, sensor-health connector, cross-sensitivity model, or field alarm is implemented."])


def _run_debate(p: DebateInput) -> dict:
    if p.discount_rate_fraction == 0:
        pv = p.annual_net_value_eur * p.life_years
    else:
        r = p.discount_rate_fraction
        pv = p.annual_net_value_eur * (1-(1+r)**(-p.life_years))/r
    npv = pv-p.capex_eur
    proposer = {item.topic: item for item in p.finance_evidence}
    challenger = {item.topic: item for item in p.storage_evidence}
    rounds = []
    for topic in dict.fromkeys([*proposer.keys(), *challenger.keys()]):
        a, b = proposer.get(topic), challenger.get(topic)
        if a is None or b is None:
            status = "unpaired"
        elif a.unit != b.unit:
            status = "unit_mismatch_disputed"
        elif abs(a.value-b.value) <= max(a.comparison_tolerance, b.comparison_tolerance):
            status = "convergent_within_declared_tolerance"
        else:
            status = "disputed"
        rounds.append({"round": len(rounds)+1, "topic": topic,
            "proposer": a.model_dump(mode="json") if a else None,
            "challenger": b.model_dump(mode="json") if b else None,
            "status": status, "resolution": "unresolved; evidence persists for human review"})
    disputed = [x["topic"] for x in rounds if x["status"] in
                {"disputed", "unit_mismatch_disputed", "unpaired"}]
    return _result([
        _metric("Illustrative project NPV", npv, "EUR"),
        _metric("Evidence rounds", len(rounds), "rounds"),
        _metric("Unresolved or disputed topics", len(disputed), "topics"),
        _metric("Debate mode", "deterministic Python", "mode"),
    ], table=rounds, details={"npv_eur": npv, "present_value_annual_value_eur": pv,
        "disputed_topics": disputed, "dispute_status_persists": True,
        "proposer_evidence_count": len(p.finance_evidence),
        "challenger_evidence_count": len(p.storage_evidence)},
       warnings=["Deterministic evidence comparison; no LLM or external council role ran.",
        "Unpaired, unit-mismatched, or out-of-tolerance claims remain unresolved.",
        "Flat annual-value NPV is not a dispatch-finance reconciliation or approval."])


def _run_manifest(p: ManifestInput) -> dict:
    from datetime import date
    as_of = date.fromisoformat(p.manifest.as_of_date)
    expected = {"tariff": ("tariff_eur_mwh", "EUR/MWh"),
                "warranty": ("warranty_years", "year"),
                "single_line": ("node_count", "count")}
    findings = []
    for doc in p.manifest.documents:
        issued = date.fromisoformat(doc.issued_on)
        expiry = date.fromisoformat(doc.expires_on) if doc.expires_on else None
        age = (as_of-issued).days
        field, unit = expected[doc.kind]
        issues = []
        if doc.field_name != field:
            issues.append("field_name_mismatch")
        if doc.unit != unit:
            issues.append("unit_mismatch")
        if age < 0:
            issues.append("issued_in_future")
        elif age > p.maximum_manifest_age_days:
            issues.append("manifest_too_old")
        if expiry is not None and expiry < as_of:
            issues.append("expired")
        if not doc.issuer or not doc.source_reference:
            issues.append("provenance_missing")
        if doc.kind == "tariff" and not 0 <= doc.value <= p.maximum_tariff_eur_mwh:
            issues.append("value_out_of_bounds")
        elif doc.kind == "warranty" and not 0 <= doc.value <= p.maximum_warranty_years:
            issues.append("value_out_of_bounds")
        elif doc.kind == "single_line" and (
            not doc.value.is_integer() or not 0 <= doc.value <= p.maximum_single_line_nodes):
            issues.append("value_out_of_bounds_or_non_integer")
        findings.append({"document_id": doc.document_id, "kind": doc.kind,
            "field_name": doc.field_name, "unit": doc.unit, "value": doc.value,
            "issuer": doc.issuer, "source_reference": doc.source_reference,
            "issued_on": doc.issued_on, "expires_on": doc.expires_on, "age_days": age,
            "status": "review" if issues else "checks_passed", "issues": issues})
    return _result([
        _metric("Documents inspected", len(findings), "documents"),
        _metric("Records with findings", sum(x["status"] == "review" for x in findings), "documents"),
        _metric("Records with supplied provenance", sum(bool(x["issuer"] and x["source_reference"]) for x in findings), "documents"),
        _metric("Input mode", "structured JSON manifest", "mode"),
    ], table=findings, details={"as_of_date": p.manifest.as_of_date, "findings": findings,
        "authenticity_checked": False, "ocr_used": False},
       warnings=["Structured JSON metadata only; no OCR or document extraction was used.",
        "Passing format, unit, date, bounds, and provenance-presence checks does not authenticate document or fact content."])


def _logistic(log_odds: float) -> float:
    if log_odds >= 0:
        return 1/(1+exp(-log_odds))
    value = exp(log_odds)
    return value/(1+value)


def _entropy(probability: float) -> float:
    if probability <= 0 or probability >= 1:
        return 0
    return -probability*log2(probability)-(1-probability)*log2(1-probability)


def _run_consensus(p: ConsensusInput) -> dict:
    if p.prior_probability in {0, 1}:
        weighted_log_odds = raw_log_odds = None
        posterior = raw_posterior = p.prior_probability
    else:
        prior = log(p.prior_probability/(1-p.prior_probability))
        weighted_log_odds = raw_log_odds = prior
        for item in p.evidence:
            item_log_lr = log(item.likelihood_ratio)
            clipped = min(p.maximum_absolute_log_likelihood_ratio,
                          max(-p.maximum_absolute_log_likelihood_ratio, item_log_lr))
            raw_log_odds += item_log_lr
            weighted_log_odds += clipped*p.evidence_weight
        posterior, raw_posterior = _logistic(weighted_log_odds), _logistic(raw_log_odds)
    counts: dict[str, int] = defaultdict(int)
    for item in p.evidence:
        counts[item.dependency_group] += 1
    repeated = sorted(group for group, count in counts.items() if count > 1)
    table = []
    for item in p.evidence:
        raw_lr = log(item.likelihood_ratio)
        effective = min(p.maximum_absolute_log_likelihood_ratio,
                        max(-p.maximum_absolute_log_likelihood_ratio, raw_lr))*p.evidence_weight
        table.append({"evidence_id": item.evidence_id,
            "likelihood_ratio": item.likelihood_ratio, "log_likelihood_ratio": raw_lr,
            "effective_log_likelihood_ratio": effective, "dependency_group": item.dependency_group,
            "dependency_group_repeated": item.dependency_group in repeated, "note": item.note})
    entropy = _entropy(posterior)
    return _result([
        _metric("Prior hypothesis probability", p.prior_probability, "probability"),
        _metric("Posterior hypothesis probability", posterior, "probability"),
        _metric("Complement probability", 1-posterior, "probability"),
        _metric("Posterior Shannon entropy", entropy, "bits"),
        _metric("Raw independent-product posterior", raw_posterior, "probability"),
        _metric("Evidence items", len(p.evidence), "items"),
    ], table=table, details={"hypothesis_probability": posterior,
        "complement_probability": 1-posterior, "probability_sum": posterior+(1-posterior),
        "posterior_log_odds": weighted_log_odds, "raw_unclipped_log_odds": raw_log_odds,
        "raw_independent_product_probability": raw_posterior,
        "binary_shannon_entropy_bits": entropy, "repeated_dependency_groups": repeated,
        "log_lr_cap": p.maximum_absolute_log_likelihood_ratio, "evidence_weight": p.evidence_weight},
       warnings=["Toy binary Bayesian update with user-supplied hypothetical likelihood ratios; no calibration is claimed.",
        "Raw product assumes conditional independence; repeated dependency groups are flagged, not automatically deduplicated.",
        "Capping and weighting are disclosed sensitivity assumptions; no unanimity, approval, or action is inferred."])


_RUNNERS = {
    "lessons-duck": (DuckInput, _run_duck),
    "lessons-blackstart": (BlackstartInput, _run_blackstart),
    "lessons-hydrogen": (HydrogenInput, _run_hydrogen),
    "compare-pareto": (ParetoInput, _run_pareto),
    "compare-dunkelflaute": (DunkelflauteInput, _run_dunkelflaute),
    "compare-thermal": (ThermalInput, _run_thermal),
    "pilots-photogrammetry": (PhotogrammetryInput, _run_photogrammetry),
    "pilots-dts": (DtsInput, _run_dts),
    "pilots-offgas": (OffgasInput, _run_offgas),
    "council-debate": (DebateInput, _run_debate),
    "council-evidence": (ManifestInput, _run_manifest),
    "council-consensus": (ConsensusInput, _run_consensus),
}


def run(study_id: str, inputs: dict) -> dict:
    """Validate then run a study without mutating inputs or using global randomness."""
    try:
        model, calculate = _RUNNERS[study_id]
    except KeyError as error:
        raise ValueError(f"Unknown workflow study: {study_id}") from error
    return calculate(model.model_validate(inputs))
