"""Advanced planning models with explicit data, calibration, and evidence limits.

These local studies are deterministic apart from explicitly seeded ensembles. They
are research screens, not operating instructions, calibrated forecasts, or approvals.
"""
from __future__ import annotations

import json
import math
from datetime import date
from time import perf_counter
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import csc_matrix
from scipy.spatial import cKDTree

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
StrictInt = Annotated[int, Field(strict=True)]
PowerKW = Annotated[float, Field(ge=0, le=100_000, allow_inf_nan=False)]
EnergyKWh = Annotated[float, Field(ge=0, le=100_000_000, allow_inf_nan=False)]
Price = Annotated[float, Field(ge=-10_000, le=10_000, allow_inf_nan=False)]
Coordinates = Annotated[float, Field(ge=-1_000_000, le=1_000_000, allow_inf_nan=False)]
NetworkMW = Annotated[float, Field(ge=0, le=1_000_000, allow_inf_nan=False)]
NetworkCost = Annotated[float, Field(ge=0, le=100_000, allow_inf_nan=False)]
RiskValue = Annotated[float, Field(ge=-1_000_000_000_000, le=1_000_000_000_000, allow_inf_nan=False)]


class StrictStudy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, validate_default=True)


def _annual_load() -> list[float]:
    hour = np.arange(8760) % 24
    day = np.arange(8760) // 24
    profile = 260 + 52 * np.sin(2 * np.pi * (hour - 8) / 24) + 28 * np.cos(2 * np.pi * day / 365)
    return np.round(np.maximum(profile, 100), 3).tolist()


def _annual_pv() -> list[float]:
    hour = np.arange(8760) % 24
    day = np.arange(8760) // 24
    daylight = np.maximum(0, np.sin(np.pi * (hour - 6) / 12))
    season = np.maximum(0.2, 0.78 + 0.22 * np.cos(2 * np.pi * (day - 172) / 365))
    return np.round(100 * daylight * season, 3).tolist()


def _day_tariff() -> list[float]:
    return [0.12] * 24


def _week_load() -> list[float]:
    hours = np.arange(168)
    return np.round(100 + 12 * np.sin(2 * np.pi * (hours - 8) / 24), 3).tolist()


def _week_renewable() -> list[float]:
    hours = np.arange(168) % 24
    return np.round(np.maximum(0, 80 * np.sin(np.pi * (hours - 6) / 12)), 3).tolist()


def _price_history() -> dict[str, list[float]]:
    t = np.arange(120, dtype=float)
    common = 40 + 0.11 * t + 2.8 * np.sin(t / 8)
    gas = common + 4 * np.sin(t / 13) + 25
    carbon = 1.7 * common + 3 * np.cos(t / 10) + 18
    power = 12 + 0.82 * gas + 0.29 * carbon + 1.4 * np.sin(t / 4)
    return {"gas_price_eur_mwh": np.round(gas, 5).tolist(),
            "carbon_price_eur_t": np.round(carbon, 5).tolist(),
            "power_price_eur_mwh": np.round(power, 5).tolist()}


class AnnualStorageInput(StrictStudy):
    load_kw: list[PowerKW] = Field(default_factory=_annual_load, min_length=8760, max_length=8760)
    pv_kw: list[PowerKW] = Field(default_factory=_annual_pv, min_length=8760, max_length=8760)
    import_price_eur_kwh: list[Price] = Field(default_factory=_day_tariff, min_length=24, max_length=8760)
    export_price_eur_kwh: list[Price] = Field(default_factory=lambda: [0.04] * 24, min_length=24, max_length=8760)
    capacity_kwh: NonNegative = Field(default=600, le=10_000_000)
    power_kw: NonNegative = Field(default=150, le=100_000)
    initial_soc_kwh: EnergyKWh = Field(default=300)
    minimum_soc_fraction: Finite = Field(default=0.1, ge=0, le=1)
    maximum_soc_fraction: Finite = Field(default=0.9, ge=0, le=1)
    round_trip_efficiency: Finite = Field(default=0.9, gt=0, le=1)
    grid_import_limit_kw: PowerKW = Field(default=100_000)
    grid_export_limit_kw: PowerKW = Field(default=100_000)
    monthly_demand_charge_eur_kw: NonNegative = Field(default=0, le=100_000)
    discharge_wear_eur_kwh: NonNegative = Field(default=0.005, le=10_000)
    solver_time_limit_seconds: Finite = Field(default=4.0, ge=0.25, le=10)

    @model_validator(mode="after")
    def valid_horizon_and_limits(self) -> AnnualStorageInput:
        if len(self.pv_kw) != 8760:
            raise ValueError("PV data must contain exactly 8,760 hourly values for a non-leap year.")
        if len(self.import_price_eur_kwh) not in (24, 8760) or len(self.export_price_eur_kwh) not in (24, 8760):
            raise ValueError("Tariffs must contain 24 hourly values or 8,760 hourly values.")
        if len(self.import_price_eur_kwh) == 8760 and len(self.export_price_eur_kwh) == 24:
            exports = self.export_price_eur_kwh * 365
        elif len(self.import_price_eur_kwh) == 24 and len(self.export_price_eur_kwh) == 8760:
            exports = self.export_price_eur_kwh
        elif len(self.import_price_eur_kwh) == 24:
            imports = self.import_price_eur_kwh * 365
            exports = self.export_price_eur_kwh * 365
            if any(buy <= sell for buy, sell in zip(imports, exports)):
                raise ValueError("Import price must exceed export price each hour to rule out grid arbitrage.")
        else:
            exports = self.export_price_eur_kwh
        imports = self.import_price_eur_kwh if len(self.import_price_eur_kwh) == 8760 else self.import_price_eur_kwh * 365
        if any(buy <= sell for buy, sell in zip(imports, exports)):
            raise ValueError("Import price must exceed export price each hour to rule out grid arbitrage.")
        low, high = self.capacity_kwh * self.minimum_soc_fraction, self.capacity_kwh * self.maximum_soc_fraction
        if low > high or not low <= self.initial_soc_kwh <= high:
            raise ValueError("Initial SOC must fall inside the configured SOC limits.")
        if self.power_kw > self.capacity_kwh:
            raise ValueError("Battery power may not exceed its energy capacity in this hourly screen.")
        if any(load - pv > self.grid_import_limit_kw for load, pv in zip(self.load_kw, self.pv_kw)):
            raise ValueError("No-battery baseline must be able to serve every supplied hourly load under the grid limit.")
        return self


class ReliabilityInput(StrictStudy):
    load_kw: list[PowerKW] = Field(default_factory=_week_load, min_length=24, max_length=8760)
    renewable_kw: list[PowerKW] = Field(default_factory=_week_renewable, min_length=24, max_length=8760)
    trials: StrictInt = Field(default=250, ge=20, le=5000)
    seed: StrictInt = Field(default=42, ge=0, le=2**32 - 1)
    weather_cv: Finite = Field(default=0.2, ge=0, le=1)
    weather_ar1: Finite = Field(default=0.9, ge=0, lt=1)
    generator_capacity_kw: PowerKW = Field(default=30)
    generator_failure_probability_per_hour: Finite = Field(default=0.002, ge=0, le=1)
    generator_repair_probability_per_hour: Finite = Field(default=0.08, gt=0, le=1)
    battery_capacity_kwh: NonNegative = Field(default=80, le=10_000_000)
    battery_power_kw: PowerKW = Field(default=40)
    initial_soc_kwh: EnergyKWh = Field(default=40)
    minimum_soc_fraction: Finite = Field(default=0, ge=0, le=1)
    maximum_soc_fraction: Finite = Field(default=1, ge=0, le=1)
    round_trip_efficiency: Finite = Field(default=0.9, gt=0, le=1)
    annualization_hours: StrictInt = Field(default=8760, ge=8760, le=8784)

    @model_validator(mode="after")
    def aligned_profiles_and_soc(self) -> ReliabilityInput:
        if len(self.load_kw) != len(self.renewable_kw):
            raise ValueError("Load and renewable arrays must have the same horizon length.")
        low, high = self.battery_capacity_kwh * self.minimum_soc_fraction, self.battery_capacity_kwh * self.maximum_soc_fraction
        if low > high or not low <= self.initial_soc_kwh <= high:
            raise ValueError("Initial SOC must fall inside the configured SOC limits.")
        if self.trials * len(self.load_kw) > 2_000_000:
            raise ValueError("The ensemble is bounded to at most two million trial-hours; reduce trials or the horizon.")
        if self.annualization_hours not in (8760, 8784):
            raise ValueError("Annualization hours must describe a non-leap or leap calendar year (8,760 or 8,784).")
        return self


def _history() -> dict[str, list[float]]:
    return _price_history()


class CointegrationInput(StrictStudy):
    gas_price_eur_mwh: list[Price] = Field(default_factory=lambda: _history()["gas_price_eur_mwh"], min_length=40, max_length=5000)
    carbon_price_eur_t: list[Price] = Field(default_factory=lambda: _history()["carbon_price_eur_t"], min_length=40, max_length=5000)
    power_price_eur_mwh: list[Price] = Field(default_factory=lambda: _history()["power_price_eur_mwh"], min_length=40, max_length=5000)
    training_fraction: Finite = Field(default=0.75, ge=0.5, le=0.9)
    lag_count: StrictInt = Field(default=1, ge=1, le=4)
    forecast_steps: StrictInt = Field(default=12, ge=1, le=48)
    rank_assumption: Literal[1] = 1

    @model_validator(mode="after")
    def aligned(self) -> CointegrationInput:
        if len({len(self.gas_price_eur_mwh), len(self.carbon_price_eur_t), len(self.power_price_eur_mwh)}) != 1:
            raise ValueError("Gas, carbon, and power observations must be aligned and equal length.")
        n_train = int(len(self.gas_price_eur_mwh) * self.training_fraction)
        if n_train < 24 or len(self.gas_price_eur_mwh) - n_train < self.forecast_steps:
            raise ValueError("The chronological train/holdout split is too short for the requested lags and forecast.")
        return self


class BacktestInput(StrictStudy):
    target_price_eur_mwh: list[Price] = Field(default_factory=lambda: _history()["power_price_eur_mwh"], min_length=36, max_length=5000)
    gas_price_eur_mwh: list[Price] = Field(default_factory=lambda: _history()["gas_price_eur_mwh"], min_length=36, max_length=5000)
    carbon_price_eur_t: list[Price] = Field(default_factory=lambda: _history()["carbon_price_eur_t"], min_length=36, max_length=5000)
    training_fraction: Finite = Field(default=0.75, ge=0.5, le=0.9)
    interval_z_score: Finite = Field(default=1.96, ge=0.5, le=4)

    @model_validator(mode="after")
    def aligned(self) -> BacktestInput:
        if len({len(self.target_price_eur_mwh), len(self.gas_price_eur_mwh), len(self.carbon_price_eur_t)}) != 1:
            raise ValueError("Target, gas, and carbon observations must be aligned and equal length.")
        if int(len(self.target_price_eur_mwh) * self.training_fraction) < 24:
            raise ValueError("The training segment must contain at least 24 observations.")
        return self


class NetworkLine(StrictStudy):
    from_zone: StrictInt = Field(ge=0, le=5)
    to_zone: StrictInt = Field(ge=0, le=5)
    susceptance_mw_per_rad: Positive = Field(le=1_000_000)
    limit_mw: Positive = Field(le=1_000_000)


def _network_lines() -> list[dict]:
    return [{"from_zone": i, "to_zone": (i + 1) % 6,
             "susceptance_mw_per_rad": 1000, "limit_mw": 220} for i in range(6)] + [
        {"from_zone": 0, "to_zone": 3, "susceptance_mw_per_rad": 500, "limit_mw": 100}]


class NetworkInput(StrictStudy):
    zone_names: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=lambda: ["North", "South", "East", "West", "Hub", "Coast"], min_length=6, max_length=6)
    demand_mw: list[NetworkMW] = Field(default_factory=lambda: [100, 80, 50, 60, 40, 70], min_length=6, max_length=6)
    generator_capacity_mw: list[NetworkMW] = Field(default_factory=lambda: [300, 0, 200, 0, 150, 100], min_length=6, max_length=6)
    generator_cost_eur_mwh: list[NetworkCost] = Field(default_factory=lambda: [20, 20, 35, 35, 70, 100], min_length=6, max_length=6)
    lines: list[NetworkLine] = Field(default_factory=_network_lines, min_length=5, max_length=12)

    @model_validator(mode="after")
    def network_is_connected(self) -> NetworkInput:
        if len(set(self.zone_names)) != 6:
            raise ValueError("Six unique zone names are required.")
        edges: set[tuple[int, int]] = set()
        graph = {i: set() for i in range(6)}
        for line in self.lines:
            if line.from_zone == line.to_zone:
                raise ValueError("Network lines must connect distinct zones.")
            edge = tuple(sorted((line.from_zone, line.to_zone)))
            if edge in edges:
                raise ValueError("Parallel duplicate lines are not supported in this screen.")
            edges.add(edge)
            graph[line.from_zone].add(line.to_zone)
            graph[line.to_zone].add(line.from_zone)
        visited, stack = set(), [0]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(graph[node] - visited)
        if len(visited) != 6:
            raise ValueError("The six-zone network must be connected.")
        return self


class ContractTerm(StrictStudy):
    start_year: StrictInt = Field(ge=2000, le=2100)
    end_year: StrictInt = Field(ge=2000, le=2100)
    annual_volume_mwh: NonNegative = Field(le=10_000_000)
    floor_price_eur_mwh: Price


class OperatingYear(StrictStudy):
    year: StrictInt = Field(ge=2000, le=2100)
    generation_mwh: NonNegative = Field(le=10_000_000)
    merchant_price_eur_mwh: Price
    opex_eur: NonNegative = Field(le=1_000_000_000_000)


def _operating_years() -> list[dict]:
    return [{"year": 2027 + i, "generation_mwh": [18_000, 17_820, 17_640, 17_460, 17_280][i],
             "merchant_price_eur_mwh": [78, 72, 76, 84, 82][i], "opex_eur": 350_000 * (1.025 ** i)}
            for i in range(5)]


class ContractInput(StrictStudy):
    capex_eur: NonNegative = Field(default=8_000_000, le=1_000_000_000_000)
    debt_share: Finite = Field(default=0.55, ge=0, le=0.9)
    debt_interest_rate: Finite = Field(default=0.055, ge=0, le=0.5)
    debt_tenor_years: StrictInt = Field(default=4, ge=1, le=30)
    tax_rate: Finite = Field(default=0.25, ge=0, le=0.6)
    depreciation_years: StrictInt = Field(default=20, ge=1, le=40)
    dsra_months: Finite = Field(default=6, ge=0, le=12)
    working_capital_fraction_of_revenue: Finite = Field(default=0.08, ge=0, le=0.5)
    operating_years: list[OperatingYear] = Field(default_factory=_operating_years, min_length=1, max_length=30)
    contracts: list[ContractTerm] = Field(default_factory=lambda: [
        {"start_year": 2027, "end_year": 2029, "annual_volume_mwh": 12_000, "floor_price_eur_mwh": 85}
    ], max_length=10)

    @model_validator(mode="after")
    def dated_terms_fit_horizon(self) -> ContractInput:
        years = [row.year for row in self.operating_years]
        if years != list(range(years[0], years[0] + len(years))):
            raise ValueError("Operating years must be unique, consecutive calendar years.")
        if self.debt_tenor_years > len(years):
            raise ValueError("Debt tenor cannot exceed the supplied operating horizon.")
        intervals = sorted((term.start_year, term.end_year) for term in self.contracts)
        if any(start > end for start, end in intervals):
            raise ValueError("Contract start year must be on or before contract end year.")
        if any(intervals[i][1] >= intervals[i + 1][0] for i in range(len(intervals) - 1)):
            raise ValueError("Overlapping contract terms must be split into one unambiguous term per year.")
        if any(start < years[0] or end > years[-1] for start, end in intervals):
            raise ValueError("Contract years must fall inside the supplied operating horizon.")
        return self


class HydrogenInput(StrictStudy):
    hydrogen_kg: NonNegative = Field(default=100, le=1_000_000)
    electrolyzer_kwh_per_kg: Positive = Field(default=52, ge=33.3, le=200)
    hydrogen_lhv_kwh_per_kg: Positive = Field(default=33.3, ge=33.3, le=33.3)
    water_stoichiometric_kg_per_kg_h2: Positive = Field(default=9, ge=9, le=9)
    water_recovery_fraction: Finite = Field(default=0.8, gt=0, le=1)
    demineralization_kwh_per_m3: NonNegative = Field(default=3, le=10_000)
    electrolyzer_auxiliary_kwh_per_kg: NonNegative = Field(default=1.5, le=100)
    electrolyzer_outlet_pressure_bar: Positive = Field(default=30, lt=350)
    delivery_pressure_bar: Positive = Field(default=350, ge=350, le=350)
    compressor_isothermal_efficiency: Finite = Field(default=0.65, gt=0, le=1)
    compressor_temperature_k: Positive = Field(default=298.15, ge=250, le=400)
    fuel_cell_gross_efficiency: Finite = Field(default=0.52, ge=0, le=0.8)
    fuel_cell_auxiliary_fraction: Finite = Field(default=0.06, ge=0, le=0.4)
    fuel_cell_heat_recovery_fraction: Finite = Field(default=0.3, ge=0, le=1)


class RiskObservation(StrictStudy):
    asset: Annotated[str, Field(min_length=1, max_length=80)]
    metric: Annotated[str, Field(min_length=1, max_length=80)]
    value: RiskValue | None
    threshold: RiskValue
    direction: Literal["max", "min"]
    unit: Annotated[str, Field(min_length=1, max_length=40)]
    source_reference: Annotated[str, Field(max_length=500)] | None = None
    observed_on: Annotated[str, Field(max_length=10)] | None = None

    @model_validator(mode="after")
    def valid_date(self) -> RiskObservation:
        if self.observed_on is not None:
            try:
                date.fromisoformat(self.observed_on)
            except ValueError as error:
                raise ValueError("observed_on must be an ISO calendar date.") from error
        return self


class RiskInput(StrictStudy):
    evidence: list[RiskObservation] = Field(default_factory=list, max_length=500)


Point3 = tuple[Coordinates, Coordinates, Coordinates]


def _default_points() -> tuple[list[list[float]], list[list[float]]]:
    design = np.array([[0., 0., 0.], [2., 0., 0.], [0., 3., 0.], [0., 0., 4.], [1., 2., 3.], [2., 1., 1.]])
    survey = design + np.array([0.08, -0.04, 0.03])
    return (design.tolist(), survey[[2, 5, 1, 3, 0, 4]].tolist())


class RegistrationInput(StrictStudy):
    design_points_xyz: list[Point3] = Field(default_factory=lambda: _default_points()[0], min_length=3, max_length=2000)
    survey_points_xyz: list[Point3] = Field(default_factory=lambda: _default_points()[1], min_length=3, max_length=2000)
    maximum_correspondence_distance_m: Positive = Field(default=1.0, le=1_000_000)
    trim_fraction: Finite = Field(default=0.8, ge=0.25, le=1)
    maximum_iterations: StrictInt = Field(default=60, ge=1, le=100)
    convergence_tolerance_m: Positive = Field(default=1e-7, le=0.1)

    @field_validator("design_points_xyz", "survey_points_xyz", mode="before")
    @classmethod
    def coerce_json_xyz_to_tuple(cls, value):
        if isinstance(value, list):
            return [tuple(point) if isinstance(point, list) else point for point in value]
        return value


def _f(name: str, label: str, default, low, high, step, unit: str) -> dict:
    return {"name": name, "label": label, "default": default, "min": low, "max": high, "step": step, "unit": unit}


def _d(name: str, label: str, default) -> dict:
    return {"name": name, "label": label, "default": default}


def _entry(study_id: str, page: str, title: str, summary: str, kind: str,
           fields: list[dict], data_fields: list[dict], equations: list[str],
           limitations: list[str], sources: list[dict]) -> dict:
    return {"id": study_id, "page": page, "title": title, "summary": summary, "kind": kind,
            "fields": fields, "data_fields": data_fields, "equations": equations,
            "limitations": limitations, "sources": sources}


_hist = _history()
STUDIES = [
    _entry("storage-annualopt", "storage", "Full-year storage optimization",
        "Optimize 8,760 hourly intervals with battery direction, SOC, grid limits, and twelve monthly demand peaks.", "dispatch",
        [_f("capacity_kwh", "Battery capacity", 600, 0, 10_000_000, 50, "kWh"),
         _f("power_kw", "Charge/discharge power", 150, 0, 100_000, 10, "kW"),
         _f("round_trip_efficiency", "Round-trip efficiency", 0.9, 0.01, 1, 0.01, "fraction"),
         _f("monthly_demand_charge_eur_kw", "Monthly demand charge", 0, 0, 100_000, 1, "EUR/kW-month"),
         _f("solver_time_limit_seconds", "MILP time limit", 4, 0.25, 10, 0.25, "s")],
        [_d("load_kw", "Non-leap-year hourly load", _annual_load()), _d("pv_kw", "Non-leap-year hourly PV", _annual_pv()),
         _d("import_price_eur_kwh", "Hourly import tariff (24 points or annual)", _day_tariff()),
         _d("export_price_eur_kwh", "Hourly export tariff (24 points or annual)", [0.04] * 24)],
        ["SOC[t+1] = SOC[t] + ηcharge·charge[t] - discharge[t]/ηdischarge",
         "grid import + PV - curtailment + discharge = load + charge + grid export",
         "annual objective = hourly energy/wear costs + Σmonth demand_charge × monthly peak import",
         "SOC[0] = SOC[8760] = supplied initial SOC"],
        ["Non-leap year with equal one-hour intervals; 24-point tariffs repeat by hour of day.",
         "Import price must strictly exceed export price each hour; simultaneous grid import/export is then dominated.",
         "Synthetic defaults are not a meter record, billing tariff, reserve product, degradation model, or investment case.",
         "A time-limit, infeasible, or non-optimal HiGHS result is rejected; the returned schedule is only a proven optimum."],
        [{"title": "SciPy mixed-integer linear programming (HiGHS) reference",
          "url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html"},
         {"title": "NREL: Storage Futures Study—Economic Potential of Four-Hour Storage",
          "url": "https://www.nrel.gov/docs/fy21osti/77449.pdf"}]),
    _entry("compare-reliability", "compare", "Chronological reliability ensemble",
        "Seeded Monte Carlo samples weather variation and generator failures while preserving battery chronology.", "reliability",
        [_f("trials", "Independent ensemble members", 250, 20, 5000, 10, "trials"),
         _f("weather_cv", "Weather coefficient of variation", 0.2, 0, 1, 0.05, "fraction"),
         _f("battery_capacity_kwh", "Battery capacity", 80, 0, 10_000_000, 10, "kWh"),
         _f("battery_power_kw", "Battery power", 40, 0, 100_000, 5, "kW"),
         _f("generator_failure_probability_per_hour", "Generator failure probability", 0.002, 0, 1, 0.001, "per hour"),
         _f("generator_repair_probability_per_hour", "Generator repair probability", 0.08, 0.001, 1, 0.01, "per hour"),
         _f("annualization_hours", "Reporting year hours", 8760, 8760, 8784, 24, "hours")],
        [_d("load_kw", "Hourly demand", _week_load()), _d("renewable_kw", "Hourly weather-dependent renewable output", _week_renewable())],
        ["LOLE[horizon] = mean over trials of hours with unserved load",
         "EENS[horizon] = mean over trials of Σ unserved kWh",
         "annualized metric = horizon expectation × annualization_hours / horizon_hours",
         "SOC evolves once across each sampled chronology; it is initialized once per trial"],
        ["Weather is a mean-one lognormal AR(1) multiplier; a single thermal unit follows a geometric failure/repair process.",
         "Annualization assumes the supplied horizon represents a typical year; it does not stitch repeated horizons or certify a resource adequacy standard.",
         "Two-sided 95% Hoeffding intervals use independent bounded trial-level annualized outcomes and can be wide, especially with few or zero observed loss events; no weather-year sampling or network adequacy model is included."],
        [{"title": "NREL Advanced Guide to Understanding Power System Model Results for Long-Term Resource Plans",
          "url": "https://docs.nrel.gov/docs/fy24osti/88337.pdf"},
         {"title": "Hoeffding: Probability Inequalities for Sums of Bounded Random Variables",
          "url": "https://doi.org/10.1080/01621459.1963.10500830"}]),
    _entry("forecast-cointegration", "forecast", "Rank-assumed energy-price VECM",
        "Fit a gas/carbon/power long-run relation and short-run error-correction dynamics, then hold out later observations.", "forecast",
        [_f("training_fraction", "Chronological training fraction", 0.75, 0.5, 0.9, 0.05, "fraction"),
         _f("rank_assumption", "Assumed cointegration rank", 1, 1, 1, 1, "rank"),
         _f("lag_count", "Lagged differences", 1, 1, 4, 1, "lags"),
         _f("forecast_steps", "Forecast path length", 12, 1, 48, 1, "observations")],
        [_d("gas_price_eur_mwh", "Observed gas prices", _hist["gas_price_eur_mwh"]),
         _d("carbon_price_eur_t", "Observed carbon prices", _hist["carbon_price_eur_t"]),
         _d("power_price_eur_mwh", "Observed power prices", _hist["power_price_eur_mwh"])],
        ["ECT[t] = power[t] - α - βgas·gas[t] - βcarbon·carbon[t]",
         "Δy[t] = c + loading·ECT[t-1] + Σ Γj·Δy[t-j] + ε[t]",
         "long-run relation and short-run VECM coefficients are fit on the first chronological segment only"],
        ["Rank one is an explicit assumption; no Johansen rank test, unit-root test, or seasonal adjustment is performed.",
         "This OLS error-correction screen is not a likelihood-based Johansen estimator or a calibrated commodity forecast.",
         "Synthetic examples do not substitute for timestamp-aligned, currency-consistent, real market observations."],
        [{"title": "Johansen and Juselius (1990), likelihood inference on cointegration",
          "url": "https://doi.org/10.1111/j.1468-0084.1990.mp52002003.x"}]),
    _entry("forecast-backtest", "forecast", "Chronological price forecast backtest",
        "Fit an ARX one-step model on early rows and score later rolling-origin forecasts with empirical interval coverage.", "forecast",
        [_f("training_fraction", "Chronological training fraction", 0.75, 0.5, 0.9, 0.05, "fraction"),
         _f("interval_z_score", "Normal residual interval multiplier", 1.96, 0.5, 4, 0.05, "z")],
        [_d("target_price_eur_mwh", "Target price observations", _hist["power_price_eur_mwh"]),
         _d("gas_price_eur_mwh", "Gas observations", _hist["gas_price_eur_mwh"]),
         _d("carbon_price_eur_t", "Carbon observations", _hist["carbon_price_eur_t"])],
        ["target[t] = β0 + β1·target[t-1] + β2·gas[t-1] + β3·carbon[t-1] + ε[t]",
         "MAE = mean(|actual - forecast|); RMSE = sqrt(mean((actual - forecast)^2))",
         "interval coverage = held-out actuals inside fitted training residual interval / holdout count"],
        ["Uses rolling one-step actual target lags and the preceding observed gas/carbon values; multi-step future drivers are not forecast.",
         "Prediction intervals use a normal residual approximation and omit parameter uncertainty.",
         "A chronological holdout is an evaluation, not independent market calibration or a guarantee of future performance."],
        [{"title": "Hyndman and Athanasopoulos, Forecasting: Principles and Practice—time-series cross-validation",
          "url": "https://otexts.com/fpp3/tscv.html"}]),
    _entry("markets-network", "markets", "Six-zone DC optimal power flow",
        "Dispatch six zonal generators through a connected linear DC network with branch limits and nodal prices.", "network",
        [],
        [_d("zone_names", "Six zone names", ["North", "South", "East", "West", "Hub", "Coast"]),
         _d("demand_mw", "Zonal demand", [100, 80, 50, 60, 40, 70]),
         _d("generator_capacity_mw", "One generator capacity per zone", [300, 0, 200, 0, 150, 100]),
         _d("generator_cost_eur_mwh", "Marginal generation cost", [20, 20, 35, 35, 70, 100]),
         _d("lines", "Branch susceptance and thermal limits", _network_lines())],
        ["flow[i,j] = susceptance[i,j]·(angle[i] - angle[j])",
         "generation[i] + net_import[i] = demand[i]",
         "min Σ generator_cost[i]·generation[i] subject to nodal balance, capacity, and branch limits"],
        ["Linear DC active-power approximation with one aggregated generator per zone; no losses, reactive power, voltage, dynamics, or reserves.",
         "Network parameters and costs are user assumptions; no calibrated six-zone topology or real zonal market is supplied."],
        [{"title": "MATPOWER mathematical model: linear DC power flow and OPF formulation",
          "url": "https://matpower.org/doc/dev-manual/math-model.html"}]),
    _entry("investment-contracts", "investment", "Contract, tax, and reserve cash flows",
        "Build separate project and equity cash flows with dated floor volumes, merchant sales, tax losses, DSRA, and working capital.", "finance",
        [_f("capex_eur", "Initial project CAPEX", 8_000_000, 0, 1_000_000_000_000, 100_000, "EUR"),
         _f("debt_share", "Initial debt share", 0.55, 0, 0.9, 0.01, "fraction"),
         _f("debt_interest_rate", "Debt interest rate", 0.055, 0, 0.5, 0.005, "fraction"),
         _f("tax_rate", "Illustrative tax rate", 0.25, 0, 0.6, 0.01, "fraction"),
         _f("dsra_months", "Debt-service reserve coverage", 6, 0, 12, 1, "months"),
         _f("working_capital_fraction_of_revenue", "Working capital / revenue", 0.08, 0, 0.5, 0.01, "fraction")],
        [_d("operating_years", "Dated annual operating observations", _operating_years()),
         _d("contracts", "Calendar-year floor volume terms", [{"start_year": 2027, "end_year": 2029,
            "annual_volume_mwh": 12_000, "floor_price_eur_mwh": 85}])],
        ["contracted volume = min(generation, annual contract volume) while term is in force",
         "contracted settlement price = max(user floor price, supplied merchant price)",
         "taxable income = EBITDA - straight-line depreciation - interest (equity tax case); tax loss carries forward within this screen",
         "equity CF = EBITDA - cash tax - debt service - DSRA funding + DSRA release - Δworking capital",
         "project CF = -CAPEX - initial working capital; subsequent CF = EBITDA - project tax - Δworking capital"],
        ["Annual calendar-year floor and merchant-price screen; no partial-year settlement, take-or-pay, VAT, tax jurisdiction rules, loss caps, depreciation conventions, fees, or default.",
         "Debt is level-payment; DSRA equals configured months of scheduled service and is funded from equity at close, then released after the final debt year.",
         "Rates and terms are user assumptions; no signed contract or tax/legal advice is represented. Nonconventional IRR is null."],
        [{"title": "IRS Publication 542: Corporations, losses, and tax provisions (jurisdictional reference only)",
          "url": "https://www.irs.gov/pub/irs-pdf/p542.pdf"}]),
    _entry("lessons-hydrogenaux", "lessons", "Hydrogen auxiliary energy ledger",
        "Account for demineralized water, electrolysis, idealized compression to 350 bar, fuel-cell auxiliaries, useful output, and losses.", "learning",
        [_f("hydrogen_kg", "Hydrogen mass", 100, 0, 1_000_000, 10, "kg"),
         _f("electrolyzer_kwh_per_kg", "Electrolyzer electricity", 52, 33.3, 200, 0.5, "kWh/kg"),
         _f("water_recovery_fraction", "Water treatment recovery", 0.8, 0.01, 1, 0.01, "fraction"),
         _f("demineralization_kwh_per_m3", "Demineralization energy", 3, 0, 10_000, 0.5, "kWh/m³"),
         _f("fuel_cell_gross_efficiency", "Fuel-cell gross efficiency", 0.52, 0, 0.8, 0.01, "fraction"),
         _f("fuel_cell_auxiliary_fraction", "Fuel-cell parasitic fraction", 0.06, 0, 0.4, 0.01, "fraction")],
        [],
        ["water stoichiometry = 9 kg feedwater per kg H₂ / recovery fraction",
         "ideal isothermal compression = m·R_H₂·T·ln(Pout/Pin) / compressor efficiency",
         "electricity input = useful electricity + useful recovered heat + explicit losses"],
        ["Isothermal ideal-gas compressor proxy from supplied outlet pressure; no real-gas, multistage, storage, leakage, purity, or pressure-drop model.",
         "Hydrogen LHV and 9 kg/kg stoichiometry are fixed screening conventions; plant-specific stack and water data are required."],
        [{"title": "DOE Hydrogen Program Record 9013: energy requirements for hydrogen gas compression",
          "url": "https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/9013_energy_requirements_for_hydrogen_gas_compression.pdf"}]),
    _entry("overview-risk", "overview", "Portfolio evidence and threshold screen",
        "Compare supplied asset prices, debt, emissions, yield, or other numeric evidence with user-supplied limits and provenance.", "risk",
        [], [_d("evidence", "Asset metric values, limits, units, and source records", [])],
        ["status = missing_value if value is absent; otherwise compare to the supplied min/max threshold",
         "provenance is complete only when a source reference and observation date are both supplied"],
        ["No asset values, thresholds, or sources are fabricated; an empty dataset returns an explicit no-evidence state.",
         "Threshold comparison does not authenticate records, normalize units, or imply risk approval."],
        [{"title": "NIST: Guide to Evaluating Data Quality",
          "url": "https://www.nist.gov/publications/guide-evaluating-data-quality"}]),
    _entry("pilots-registration", "pilots", "Unpaired point-cloud registration",
        "Register unordered design and survey XYZ points with trimmed nearest-neighbor ICP and a rigid Kabsch transform.", "survey",
        [_f("maximum_correspondence_distance_m", "Maximum match distance", 1, 0.0001, 1_000_000, 0.1, "m"),
         _f("trim_fraction", "Retained correspondence fraction", 0.8, 0.25, 1, 0.05, "fraction"),
         _f("maximum_iterations", "Maximum ICP iterations", 60, 1, 100, 1, "iterations"),
         _f("convergence_tolerance_m", "RMSE change tolerance", 0.0000001, 0.0000001, 0.1, 0.0000001, "m")],
        [_d("design_points_xyz", "Design points (XYZ m)", _default_points()[0]),
         _d("survey_points_xyz", "Unordered surveyed points (XYZ m)", _default_points()[1])],
        ["nearest-neighbor correspondences are recomputed after every transform",
         "Kabsch rigid fit minimizes Σ ||R·source[i] + t - target[i]||² with det(R)=+1",
         "trim high-residual correspondences; repeat until RMSE change ≤ tolerance or iteration cap"],
        ["Requires supplied XYZ point clouds; no drone imagery ingestion or 3D reconstruction is performed.",
         "Unpaired ICP can converge to a local alignment; coordinate frames, units, point density, outliers, and registration quality require survey review.",
         "No scale, non-rigid deformation, georeferencing, or survey certification is modeled."],
        [{"title": "Kabsch (1976), a solution for the best rotation between vector sets",
          "url": "https://doi.org/10.1107/S0567739476001873"},
         {"title": "SciPy cKDTree nearest-neighbor query reference",
          "url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html"}]),
]


def _metric(label: str, value, unit: str) -> dict:
    return {"label": label, "value": value, "unit": unit}


def _result(metrics: list[dict], *, series: list[dict] | None = None,
            table: list[dict] | None = None, details: dict | None = None,
            warnings: list[str] | None = None) -> dict:
    result = {"metrics": metrics, "series": series or [], "table": table or [],
              "details": details or {}, "warnings": warnings or []}
    json.dumps(result, allow_nan=False)
    return result


def _tariff(values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return np.tile(arr, 365) if arr.size == 24 else arr


def _month_index() -> np.ndarray:
    return np.repeat(np.arange(12), np.asarray([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]) * 24)


def _annual_storage(p: AnnualStorageInput) -> dict:
    n = 8760
    load = np.asarray(p.load_kw, dtype=float)
    pv = np.asarray(p.pv_kw, dtype=float)
    buy = _tariff(p.import_price_eur_kwh)
    sell = _tariff(p.export_price_eur_kwh)
    month = _month_index()
    eta = math.sqrt(p.round_trip_efficiency)
    peak_idx = 7 * n + 1
    charge_idx = np.arange(n)
    discharge_idx = n + charge_idx
    import_idx = 2 * n + charge_idx
    export_idx = 3 * n + charge_idx
    curtail_idx = 4 * n + charge_idx
    soc_idx = 5 * n + np.arange(n + 1)
    direction_idx = 6 * n + 1 + charge_idx
    variable_count = 7 * n + 13

    # Sparse equality and inequality rows for the complete hourly MILP.
    balance_rows = np.arange(n)
    soc_rows = n + np.arange(n)
    charge_rows = 2 * n + np.arange(n)
    discharge_rows = 3 * n + np.arange(n)
    peak_rows = 4 * n + np.arange(n)
    row_parts = [np.repeat(balance_rows, 5), np.repeat(soc_rows, 4),
                 np.repeat(charge_rows, 2), np.repeat(discharge_rows, 2),
                 np.repeat(peak_rows, 2)]
    col_parts = [np.column_stack((import_idx, export_idx, discharge_idx, charge_idx, curtail_idx)).ravel(),
                 np.column_stack((charge_idx, discharge_idx, soc_idx[:-1], soc_idx[1:])).ravel(),
                 np.column_stack((charge_idx, direction_idx)).ravel(),
                 np.column_stack((discharge_idx, direction_idx)).ravel(),
                 np.column_stack((import_idx, peak_idx + month)).ravel()]
    data_parts = [np.tile([1.0, -1.0, 1.0, -1.0, -1.0], n),
                  np.tile([-eta, 1.0 / eta, -1.0, 1.0], n),
                  np.column_stack((np.ones(n), -p.power_kw * np.ones(n))).ravel(),
                  np.column_stack((np.ones(n), p.power_kw * np.ones(n))).ravel(),
                  np.column_stack((np.ones(n), -np.ones(n))).ravel()]
    matrix = csc_matrix((np.concatenate(data_parts),
                         (np.concatenate(row_parts), np.concatenate(col_parts))),
                        shape=(5 * n, variable_count))
    rhs = load - pv
    lower_rows = np.concatenate((rhs, np.zeros(n), np.full(3 * n, -np.inf)))
    upper_rows = np.concatenate((rhs, np.zeros(n), np.zeros(n),
                                 np.full(n, p.power_kw), np.zeros(n)))
    constraints = LinearConstraint(matrix, lower_rows, upper_rows)

    objective = np.zeros(variable_count, dtype=float)
    objective[discharge_idx] = p.discharge_wear_eur_kwh
    objective[import_idx] = buy
    objective[export_idx] = -sell
    objective[peak_idx:peak_idx + 12] = p.monthly_demand_charge_eur_kw
    lower = np.zeros(variable_count, dtype=float)
    upper = np.full(variable_count, np.inf, dtype=float)
    upper[charge_idx] = p.power_kw
    upper[discharge_idx] = p.power_kw
    upper[import_idx] = p.grid_import_limit_kw
    upper[export_idx] = p.grid_export_limit_kw
    upper[curtail_idx] = pv
    soc_min, soc_max = p.capacity_kwh * p.minimum_soc_fraction, p.capacity_kwh * p.maximum_soc_fraction
    lower[soc_idx], upper[soc_idx] = soc_min, soc_max
    lower[soc_idx[0]] = upper[soc_idx[0]] = p.initial_soc_kwh
    lower[soc_idx[-1]] = upper[soc_idx[-1]] = p.initial_soc_kwh
    upper[direction_idx] = 1
    upper[peak_idx:peak_idx + 12] = p.grid_import_limit_kw
    # With nonnegative tariffs, either positive export value or positive
    # discharge wear makes a same-hour lossy cycle strictly costly. If export
    # is free and wear is zero, however, the cycle can consume otherwise-
    # curtailed PV at no objective cost. Keep the binaries in that degenerate
    # case (and whenever a tariff is negative).
    binary_direction_required = bool(np.any(buy < 0) or np.any(sell < 0)
                                     or (p.discharge_wear_eur_kwh <= 0 and np.any(sell <= 0)))
    integrality = np.zeros(variable_count, dtype=np.uint8)
    if binary_direction_required:
        integrality[direction_idx] = 1
    solve_started = perf_counter()
    solved = milp(objective, integrality=integrality, bounds=Bounds(lower, upper),
                  constraints=constraints,
                  options={"time_limit": p.solver_time_limit_seconds, "mip_rel_gap": 0.0})
    solver_runtime = perf_counter() - solve_started
    if solved.status != 0 or solved.x is None or solved.fun is None:
        gap = getattr(solved, "mip_gap", None)
        raise ValueError(f"Annual MILP did not prove an optimal schedule (status={solved.status}, gap={gap!r}): {solved.message}")
    gap = float(solved.mip_gap) if getattr(solved, "mip_gap", None) is not None else 0.0
    if not math.isfinite(gap) or gap > 1e-10:
        raise ValueError(f"Annual MILP returned no requested optimality proof (relative gap={gap!r}).")

    x = solved.x
    charge = x[charge_idx]
    discharge = x[discharge_idx]
    imports = x[import_idx]
    exports = x[export_idx]
    curtailment = x[curtail_idx]
    soc = x[soc_idx]
    residual = imports - exports + pv - curtailment + discharge - load - charge
    soc_residual = soc[1:] - soc[:-1] - eta * charge + discharge / eta
    peaks = x[peak_idx:peak_idx + 12]
    energy_cost = float(np.dot(imports, buy) - np.dot(exports, sell) + np.sum(discharge) * p.discharge_wear_eur_kwh)
    demand_cost = float(np.sum(peaks) * p.monthly_demand_charge_eur_kw)

    # The no-battery baseline has the same load/PV, tariffs, export/import bounds,
    # curtailment rule, and monthly demand charge. With buy > sell it has a unique
    # per-hour dispatch and can be solved exactly without a second 8,760-binary MILP.
    net = load - pv
    base_import = np.maximum(net, 0)
    base_export = np.minimum(np.maximum(-net, 0), p.grid_export_limit_kw)
    base_curtail = np.maximum(-net - base_export, 0)
    if np.any(base_import > p.grid_import_limit_kw + 1e-8):
        raise ArithmeticError("The no-battery comparator is infeasible under the supplied grid-import limit.")
    base_peaks = np.asarray([np.max(base_import[month == i]) for i in range(12)])
    baseline = float(np.dot(base_import, buy) - np.dot(base_export, sell)
                     + np.sum(base_peaks) * p.monthly_demand_charge_eur_kw)
    max_balance = float(np.max(np.abs(residual)))
    max_soc_residual = float(np.max(np.abs(soc_residual)))
    if max_balance > 1e-5 or max_soc_residual > 1e-5:
        raise ArithmeticError("The annual MILP solution failed its power or SOC balance check.")
    table = [{"hour": i, "load_kw": float(load[i]), "pv_kw": float(pv[i]),
              "charge_kw": float(charge[i]), "discharge_kw": float(discharge[i]),
              "grid_import_kw": float(imports[i]), "grid_export_kw": float(exports[i]),
              "curtail_kw": float(curtailment[i]), "soc_start_kwh": float(soc[i]),
              "soc_end_kwh": float(soc[i + 1]), "month": int(month[i] + 1)} for i in range(n)]
    return _result([
        _metric("Optimal annual objective", float(solved.fun), "EUR"),
        _metric("No-battery baseline objective", baseline, "EUR"),
        _metric("Objective change versus baseline", baseline - float(solved.fun), "EUR"),
        _metric("Battery charge energy", float(np.sum(charge)), "kWh"),
        _metric("Battery discharge energy", float(np.sum(discharge)), "kWh"),
        _metric("PV curtailment", float(np.sum(curtailment)), "kWh"),
    ], series=[
        {"name": "grid_import", "x_label": "hour of non-leap year", "y_unit": "kW", "x": list(range(n)), "y": imports.tolist()},
        {"name": "battery_soc", "x_label": "hour boundary", "y_unit": "kWh", "x": list(range(n + 1)), "y": soc.tolist()},
        {"name": "monthly_peak_import", "x_label": "month", "y_unit": "kW", "x": list(range(1, 13)), "y": peaks.tolist()},
    ], table=table, details={"interval_count": n, "horizon_hours": n, "initial_soc_kwh": p.initial_soc_kwh,
        "terminal_soc_kwh": float(soc[-1]), "minimum_soc_kwh": float(np.min(soc)),
        "maximum_soc_kwh": float(np.max(soc)), "maximum_monthly_peak_import_kw": float(np.max(peaks)),
        "monthly_peaks_kw": peaks.tolist(), "solver": "SciPy milp / HiGHS",
        "solver_status": "optimal", "solver_status_code": int(solved.status),
        "solver_message": str(solved.message), "relative_mip_gap": gap,
        "solver_runtime_seconds": solver_runtime,
        "solver_time_limit_seconds": p.solver_time_limit_seconds,
        "mip_node_count": int(solved.mip_node_count) if getattr(solved, "mip_node_count", None) is not None else None,
        "max_balance_residual_kw": max_balance, "max_soc_residual_kwh": max_soc_residual,
        "max_simultaneous_charge_discharge_kw": float(np.max(np.minimum(charge, discharge))),
        "annual_energy_cost_eur": energy_cost, "annual_demand_charge_eur": demand_cost,
        "baseline_monthly_peaks_kw": base_peaks.tolist(), "baseline_curtailment_kwh": float(np.sum(base_curtail)),
        "tariff_expansion": "24-hour vectors repeat for all 365 days; annual vectors are used as supplied",
        "grid_direction": "No grid binary required because import tariff strictly exceeds export tariff in every hour; simultaneous flow is strictly dominated",
        "battery_direction": "hourly binary charge/discharge exclusivity" if binary_direction_required else
            "strict-cost dominance proof: with nonnegative tariffs, positive export value or positive discharge wear makes every same-hour lossy cycle more costly; no integer direction variables needed",
        "binary_direction_required": binary_direction_required,
        "integer_variable_count": int(np.sum(integrality)),
        "baseline_method": "exact analytical no-battery dispatch with identical energy, grid, PV-curtailment, and monthly-peak constraints"},
        warnings=["Synthetic default profiles are illustrative and do not establish a commercial annual bill.",
                  "Demand charges apply once to each non-leap calendar month; the supplied year has no time-zone or daylight-saving transitions."])


def _bounded_mean_ci(values: np.ndarray, upper_bound: float,
                     confidence: float = 0.95) -> tuple[float, float, float]:
    """Two-sided Hoeffding interval for independent outcomes in [0, upper_bound]."""
    mean = float(np.mean(values))
    alpha = 1 - confidence
    half = upper_bound * math.sqrt(math.log(2 / alpha) / (2 * values.size))
    return mean, max(0.0, mean - half), min(upper_bound, mean + half)


def _reliability(p: ReliabilityInput) -> dict:
    rng = np.random.default_rng(p.seed)
    load, renewable = np.asarray(p.load_kw), np.asarray(p.renewable_kw)
    n = len(load)
    factor = p.annualization_hours / n
    log_sigma = math.sqrt(math.log1p(p.weather_cv ** 2))
    log_mean = -0.5 * log_sigma * log_sigma
    eta = math.sqrt(p.round_trip_efficiency)
    soc_low = p.battery_capacity_kwh * p.minimum_soc_fraction
    soc_high = p.battery_capacity_kwh * p.maximum_soc_fraction
    lole, eens, terminal_soc, weather_paths = [], [], [], []
    for _ in range(p.trials):
        innovations = rng.normal(size=n)
        weather = np.empty(n)
        weather[0] = innovations[0]
        for i in range(1, n):
            weather[i] = p.weather_ar1 * weather[i - 1] + math.sqrt(1 - p.weather_ar1 ** 2) * innovations[i]
        renewable_factor = np.exp(log_mean + log_sigma * weather)
        weather_paths.append(float(np.mean(renewable_factor)))
        available = np.empty(n, dtype=bool)
        stationary_up = p.generator_repair_probability_per_hour / (
            p.generator_repair_probability_per_hour + p.generator_failure_probability_per_hour)
        available[0] = rng.random() < stationary_up
        for i in range(1, n):
            if available[i - 1]:
                available[i] = rng.random() >= p.generator_failure_probability_per_hour
            else:
                available[i] = rng.random() < p.generator_repair_probability_per_hour
        soc = p.initial_soc_kwh
        unserved = np.zeros(n)
        for i in range(n):
            supply = renewable[i] * renewable_factor[i] + (p.generator_capacity_kw if available[i] else 0)
            net = supply - load[i]
            if net >= 0:
                charge = min(net, p.battery_power_kw,
                             max(0.0, soc_high - soc) / eta if eta else 0.0)
                soc += eta * charge
            else:
                discharge = min(-net, p.battery_power_kw, max(0.0, soc - soc_low) * eta)
                soc -= discharge / eta
                unserved[i] = max(0.0, -net - discharge)
            soc = min(soc_high, max(soc_low, soc))
        lole.append(float(np.count_nonzero(unserved > 1e-9)) * factor)
        eens.append(float(np.sum(unserved)) * factor)
        terminal_soc.append(soc)
    lole_arr, eens_arr = np.asarray(lole), np.asarray(eens)
    lole_bound = float(p.annualization_hours)
    eens_bound = float(np.sum(load) * factor)
    lole_mean, lole_low, lole_high = _bounded_mean_ci(lole_arr, lole_bound)
    eens_mean, eens_low, eens_high = _bounded_mean_ci(eens_arr, eens_bound)
    lole_event_trials = int(np.count_nonzero(lole_arr > 0))
    eens_event_trials = int(np.count_nonzero(eens_arr > 0))
    low_event_warning_threshold = 30
    low_event_warning = (lole_event_trials < low_event_warning_threshold
                         or eens_event_trials < low_event_warning_threshold)
    warnings = ["Annualization scales a representative supplied horizon to the configured year length; it does not repeat the horizon as observed history.",
                "Weather and outage processes are synthetic and simplified; no empirical weather years, common-cause outages, network flows, or adequacy standard are calibrated."]
    if low_event_warning:
        warnings.append(
            f"Few loss events were observed across the ensemble (LOLE events in {lole_event_trials}/{p.trials} trials; "
            f"EENS events in {eens_event_trials}/{p.trials}). The bounded Hoeffding intervals remain conservative; "
            "zero observed events do not imply zero underlying risk.")
    return _result([
        _metric("Expected annualized loss-of-load hours", lole_mean, "h/year"),
        _metric("Expected annualized unserved energy", eens_mean, "kWh/year"),
        _metric("Ensemble members", p.trials, "trials"),
        _metric("Expected terminal battery energy", float(np.mean(terminal_soc)), "kWh"),
    ], series=[{"name": "annualized_trial_lole", "x_label": "ensemble member", "y_unit": "h/year",
                "x": list(range(p.trials)), "y": lole},
               {"name": "annualized_trial_eens", "x_label": "ensemble member", "y_unit": "kWh/year",
                "x": list(range(p.trials)), "y": eens}],
       table=[{"trial": i, "annualized_lole_hours": lole[i], "annualized_eens_kwh": eens[i],
               "terminal_soc_kwh": terminal_soc[i], "mean_weather_multiplier": weather_paths[i]}
              for i in range(p.trials)],
       details={"horizon_hours": n, "annualization_hours": p.annualization_hours,
                "annualization_factor": factor, "trial_count": p.trials, "seed": p.seed,
                "lole_horizon_mean_hours": lole_mean / factor,
                "lole_annualized_95_ci_hours": [lole_low, lole_high],
                "eens_annualized_95_ci_kwh": [eens_low, eens_high],
                "lole_outcome_upper_bound_hours_per_year": lole_bound,
                "eens_outcome_upper_bound_kwh_per_year": eens_bound,
                "lole_event_trial_count": lole_event_trials,
                "eens_event_trial_count": eens_event_trials,
                "low_event_warning_threshold_trials": low_event_warning_threshold,
                "low_event_warning_triggered": low_event_warning,
                "mean_weather_multiplier": float(np.mean(weather_paths)),
                "soc_resets_within_trial": False,
                "soc_initialization": "supplied initial SOC once at the beginning of each independent trial; chronological transitions thereafter",
                "generator_state_model": "one thermal unit with stationary initial availability and geometric hourly failure/repair transitions",
                "confidence_interval": "two-sided 95% Hoeffding interval: sample mean +/- R*sqrt(log(2/0.05)/(2*n)), clipped to [0,R] for independent trial-level annualized outcomes with support [0,R]"},
       warnings=warnings)


def _fit_vecm(train: np.ndarray, lag_count: int) -> tuple[np.ndarray, np.ndarray, float]:
    gas, carbon, power = train.T
    long_run_x = np.column_stack((np.ones(len(train)), gas, carbon))
    long_run_parameters, _, rank, singular = np.linalg.lstsq(long_run_x, power, rcond=None)
    if rank < 3 or singular[-1] <= 1e-12 * singular[0]:
        raise ValueError("Gas and carbon level observations do not identify a stable rank-one long-run relation.")
    ect = power - long_run_x @ long_run_parameters
    differences = np.diff(train, axis=0)
    design, target = [], []
    for t in range(lag_count + 1, len(train)):
        # Predict Δy_t using only changes observed through t-1. The latest
        # allowed lag is Δy_(t-1) = differences[t-2]; differences[t-1] is the
        # target and must never appear among its own regressors.
        prior_changes = [differences[t - 1 - lag] for lag in range(1, lag_count + 1)]
        design.append([1.0, ect[t - 1], *np.asarray(prior_changes).ravel()])
        target.append(differences[t - 1])
    x, y = np.asarray(design), np.asarray(target)
    parameters, _, short_rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if short_rank < x.shape[1]:
        raise ValueError("VECM short-run design is rank deficient; add observations or reduce lag_count.")
    residual = y - x @ parameters
    return long_run_parameters, parameters, float(np.sqrt(np.mean(residual ** 2)))


def _vecm_predict_path(last_level: np.ndarray, history_differences: np.ndarray,
                       long_run: np.ndarray, short_run: np.ndarray,
                       steps: int, lag_count: int) -> np.ndarray:
    y = last_level.astype(float).copy()
    differences = [row.copy() for row in history_differences[-lag_count:][::-1]]
    beta_gas, beta_carbon = long_run[1], long_run[2]
    forecasts = []
    for _ in range(steps):
        ect = y[2] - long_run[0] - beta_gas * y[0] - beta_carbon * y[1]
        x = np.asarray([1.0, ect, *np.asarray(differences).ravel()])
        delta = x @ short_run
        y = y + delta
        forecasts.append(y.copy())
        differences.insert(0, delta)
        differences = differences[:lag_count]
    return np.asarray(forecasts)


def _cointegration(p: CointegrationInput) -> dict:
    levels = np.column_stack((p.gas_price_eur_mwh, p.carbon_price_eur_t, p.power_price_eur_mwh))
    train_n = int(len(levels) * p.training_fraction)
    train = levels[:train_n]
    holdout = levels[train_n:]
    long_run, short_run, residual_rmse = _fit_vecm(train, p.lag_count)
    forecast = _vecm_predict_path(train[-1], np.diff(train, axis=0), long_run,
                                  short_run, len(holdout), p.lag_count)
    if not np.isfinite(forecast).all() or np.max(np.abs(forecast)) > 1_000_000_000:
        raise ValueError("The fitted VECM produced an unstable or non-finite recursive forecast path.")
    error = forecast - holdout
    holdout_rmse = float(np.sqrt(np.mean(error ** 2)))
    power_rmse = float(np.sqrt(np.mean(error[:, 2] ** 2)))
    short_lags = short_run.shape[0] - 2
    path_len = min(p.forecast_steps, len(holdout))
    forecast_path = forecast[:path_len]
    ect_train = train[:, 2] - long_run[0] - long_run[1] * train[:, 0] - long_run[2] * train[:, 1]
    return _result([
        _metric("Assumed cointegration rank", 1, "rank"),
        _metric("In-sample VECM residual RMSE", residual_rmse, "price units"),
        _metric("Chronological holdout RMSE (power)", power_rmse, "EUR/MWh"),
        _metric("Chronological holdout RMSE (all series)", holdout_rmse, "series units"),
    ], series=[{"name": "training_error_correction_term", "x_label": "training observation", "y_unit": "EUR/MWh",
                "x": list(range(train_n)), "y": ect_train.tolist()},
               {"name": "heldout_power_actual", "x_label": "holdout step", "y_unit": "EUR/MWh",
                "x": list(range(len(holdout))), "y": holdout[:, 2].tolist()},
               {"name": "heldout_power_forecast", "x_label": "holdout step", "y_unit": "EUR/MWh",
                "x": list(range(len(holdout))), "y": forecast[:, 2].tolist()}],
       table=[{"step": i + 1, "gas_forecast": row[0], "carbon_forecast": row[1], "power_forecast_eur_mwh": row[2],
               "power_actual_eur_mwh": float(holdout[i, 2]), "power_error_eur_mwh": float(error[i, 2])}
              for i, row in enumerate(forecast_path)],
       details={"rank_assumption": 1, "rank_test_performed": False,
                "cointegration_stationarity_test_performed": False,
                "validation_status": "assumed_rank_one_fit_with_chronological_holdout",
                "training_observations": train_n, "holdout_observations": len(holdout),
                "lag_count": p.lag_count, "short_run_lag_terms": short_lags,
                "long_run_parameters": {"intercept": float(long_run[0]), "gas_beta": float(long_run[1]),
                                         "carbon_beta": float(long_run[2]), "power_beta_normalization": 1.0},
                "short_run_parameters_by_series": short_run.tolist(),
                "in_sample_vecm_rmse_all_series": residual_rmse,
                "holdout_rmse_all_series": holdout_rmse,
                "holdout_rmse_power_eur_mwh": power_rmse,
                "forecast_path": forecast_path[:, 2].tolist(),
                "training_fraction": p.training_fraction,
                "fitted_on_holdout": False},
       warnings=["The rank-one relation is an OLS assumption, not a Johansen or unit-root test result.",
                 "Holdout predictions are fixed-origin and recursively use forecast levels; no future market driver is observed beyond the supplied holdout itself.",
                 "Use time-aligned, consistent real gas/carbon/power series before interpreting fit quality."])


def _backtest(p: BacktestInput) -> dict:
    target = np.asarray(p.target_price_eur_mwh, dtype=float)
    gas = np.asarray(p.gas_price_eur_mwh, dtype=float)
    carbon = np.asarray(p.carbon_price_eur_t, dtype=float)
    train_n = int(len(target) * p.training_fraction)
    train_design = np.column_stack((np.ones(train_n - 1), target[:train_n - 1],
                                    gas[:train_n - 1], carbon[:train_n - 1]))
    train_y = target[1:train_n]
    parameters, _, rank, _ = np.linalg.lstsq(train_design, train_y, rcond=None)
    train_residual = train_y - train_design @ parameters
    sigma = float(np.sqrt(np.mean(train_residual ** 2)))
    forecasts = np.asarray([parameters @ [1.0, target[t - 1], gas[t - 1], carbon[t - 1]]
                            for t in range(train_n, len(target))])
    actual = target[train_n:]
    errors = forecasts - actual
    absolute = np.abs(errors)
    mae = float(np.mean(absolute))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    lower, upper = forecasts - p.interval_z_score * sigma, forecasts + p.interval_z_score * sigma
    coverage = float(np.mean((actual >= lower) & (actual <= upper)))
    return _result([
        _metric("Held-out mean absolute error", mae, "EUR/MWh"),
        _metric("Held-out root mean square error", rmse, "EUR/MWh"),
        _metric("Held-out prediction-interval coverage", coverage, "fraction"),
        _metric("Holdout observations", len(actual), "observations"),
    ], series=[{"name": "actual_price", "x_label": "chronological holdout step", "y_unit": "EUR/MWh",
                "x": list(range(len(actual))), "y": actual.tolist()},
               {"name": "rolling_one_step_forecast", "x_label": "chronological holdout step", "y_unit": "EUR/MWh",
                "x": list(range(len(actual))), "y": forecasts.tolist()},
               {"name": "interval_lower", "x_label": "chronological holdout step", "y_unit": "EUR/MWh",
                "x": list(range(len(actual))), "y": lower.tolist()},
               {"name": "interval_upper", "x_label": "chronological holdout step", "y_unit": "EUR/MWh",
                "x": list(range(len(actual))), "y": upper.tolist()}],
       table=[{"observation": train_n + i, "actual_eur_mwh": float(actual[i]),
               "forecast_eur_mwh": float(forecasts[i]), "error_eur_mwh": float(errors[i]),
               "interval_lower_eur_mwh": float(lower[i]), "interval_upper_eur_mwh": float(upper[i]),
               "covered": bool(lower[i] <= actual[i] <= upper[i])} for i in range(len(actual))],
       details={"training_observations": train_n - 1, "holdout_observations": len(actual),
                "first_training_target_index": 1, "last_training_target_index": train_n - 1,
                "first_holdout_target_index": train_n, "training_fraction": p.training_fraction,
                "model": "OLS ARX(1), rolling one-step: target[t] ~ const + target[t-1] + gas[t-1] + carbon[t-1]",
                "coefficients": {"intercept": float(parameters[0]), "target_lag": float(parameters[1]),
                                 "gas_lag": float(parameters[2]), "carbon_lag": float(parameters[3])},
                "training_design_rank": int(rank), "training_design_columns": int(train_design.shape[1]),
                "coefficients_fully_identified": bool(rank == train_design.shape[1]),
                "training_residual_standard_deviation_eur_mwh": sigma,
                "interval_z_score": p.interval_z_score, "mae_eur_mwh": mae, "rmse_eur_mwh": rmse,
                "prediction_interval_coverage_fraction": coverage,
                "fit_uses_holdout_targets": False,
                "future_exogenous_assumption": "preceding observed gas and carbon values are available at each one-step origin"},
       warnings=["Training fits use only rows before the holdout; scoring is rolling one-step, not a multi-year recursive forecast.",
                 "Intervals use training residual spread without parameter uncertainty and do not imply calibrated forecast probability.",
                 "A rank-deficient design can forecast a constant or redundant dataset, but its individual coefficients are not uniquely identified.",
                 "Synthetic example rows are for method demonstration only."])


def _network(p: NetworkInput) -> dict:
    zone_count = 6
    variable_count = 12
    objective = np.zeros(variable_count)
    objective[:zone_count] = p.generator_cost_eur_mwh
    equality = np.zeros((zone_count, variable_count))
    equality[np.arange(zone_count), np.arange(zone_count)] = 1
    for line in p.lines:
        i, j, b = line.from_zone, line.to_zone, line.susceptance_mw_per_rad
        # KCL: generation + inflow - outflow = demand.
        equality[i, 6 + i] -= b
        equality[i, 6 + j] += b
        equality[j, 6 + i] += b
        equality[j, 6 + j] -= b
    rhs = np.asarray(p.demand_mw, dtype=float)
    inequalities = np.zeros((2 * len(p.lines), variable_count))
    bounds_rhs = np.zeros(2 * len(p.lines))
    for k, line in enumerate(p.lines):
        i, j, b = line.from_zone, line.to_zone, line.susceptance_mw_per_rad
        inequalities[2 * k, 6 + i] = b
        inequalities[2 * k, 6 + j] = -b
        inequalities[2 * k + 1, 6 + i] = -b
        inequalities[2 * k + 1, 6 + j] = b
        bounds_rhs[2 * k:2 * k + 2] = line.limit_mw
    bounds = [(0, capacity) for capacity in p.generator_capacity_mw] + [(0, 0)] + [(None, None)] * 5
    solved = linprog(objective, A_ub=inequalities, b_ub=bounds_rhs, A_eq=equality, b_eq=rhs,
                     bounds=bounds, method="highs")
    if not solved.success or solved.x is None:
        raise ValueError(f"Six-zone DC-OPF failed (status={solved.status}): {solved.message}")
    generation = solved.x[:zone_count]
    angles = solved.x[6:]
    prices = np.asarray(solved.eqlin.marginals, dtype=float)
    line_rows = []
    nodal_net = np.zeros(zone_count)
    for line in p.lines:
        flow = line.susceptance_mw_per_rad * (angles[line.from_zone] - angles[line.to_zone])
        nodal_net[line.from_zone] -= flow
        nodal_net[line.to_zone] += flow
        line_rows.append({"from_zone": p.zone_names[line.from_zone], "to_zone": p.zone_names[line.to_zone],
                          "flow_mw": float(flow), "limit_mw": line.limit_mw,
                          "loading_fraction": float(abs(flow) / line.limit_mw)})
    residual = generation + nodal_net - rhs
    zone_rows = [{"zone": p.zone_names[i], "demand_mw": float(rhs[i]), "generation_mw": float(generation[i]),
                  "net_import_mw": float(nodal_net[i]), "nodal_price_eur_mwh": float(prices[i]),
                  "reference_angle_rad": float(angles[i])} for i in range(zone_count)]
    return _result([
        _metric("Total generation", float(np.sum(generation)), "MW"),
        _metric("Total demand", float(np.sum(rhs)), "MW"),
        _metric("System dispatch cost", float(solved.fun), "EUR/h"),
        _metric("Maximum zonal price", float(np.max(prices)), "EUR/MWh"),
        _metric("Maximum branch loading", max(row["loading_fraction"] for row in line_rows), "fraction"),
    ], series=[{"name": "generation", "x_label": "zone", "y_unit": "MW",
                "x": list(p.zone_names), "y": generation.tolist()},
               {"name": "nodal_price", "x_label": "zone", "y_unit": "EUR/MWh",
                "x": list(p.zone_names), "y": prices.tolist()},
               {"name": "line_flow", "x_label": "branch", "y_unit": "MW",
                "x": [f"{row['from_zone']}–{row['to_zone']}" for row in line_rows],
                "y": [row["flow_mw"] for row in line_rows]}],
       table=zone_rows, details={"total_generation_mw": float(np.sum(generation)),
           "total_demand_mw": float(np.sum(rhs)), "nodal_prices_eur_mwh": prices.tolist(),
           "generator_dispatch_mw": generation.tolist(), "line_flows": line_rows,
           "angles_rad": angles.tolist(), "max_balance_residual_mw": float(np.max(np.abs(residual))),
           "price_duals_source": "HiGHS nodal balance equality marginals",
           "solver_status": "optimal", "solver_message": str(solved.message),
           "dispatch_cost_eur_per_hour": float(solved.fun)},
       warnings=["Single-period linear DC approximation uses user-supplied branch susceptance, thermal limits, costs, and capacities.",
                 "Nodal duals are screening prices for this simplified optimization, not observed market prices or settlement prices."])


def _tax_and_loss(taxable_income: float, opening_loss: float, rate: float) -> tuple[float, float, float]:
    if taxable_income < 0:
        return 0.0, opening_loss - taxable_income, taxable_income
    used = min(opening_loss, taxable_income)
    remaining = opening_loss - used
    return max(0.0, taxable_income - used) * rate, remaining, taxable_income - used


def _irr(cashflows: list[float]) -> float | None:
    signs = [1 if value > 1e-8 else -1 if value < -1e-8 else 0 for value in cashflows]
    signs = [value for value in signs if value]
    if len(signs) < 2 or sum(a != b for a, b in zip(signs, signs[1:])) != 1:
        return None

    def npv(rate: float) -> float:
        return math.fsum(value / ((1 + rate) ** period) for period, value in enumerate(cashflows))

    low, high = -0.999, 10.0
    f_low, f_high = npv(low), npv(high)
    if not math.isfinite(f_low) or not math.isfinite(f_high) or f_low * f_high > 0:
        return None
    for _ in range(120):
        mid = (low + high) / 2
        f_mid = npv(mid)
        if abs(f_mid) <= 1e-8 or high - low < 1e-12:
            return mid * 100
        if f_low * f_mid <= 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return ((low + high) / 2) * 100


def _contracts(p: ContractInput) -> dict:
    operating = p.operating_years
    n = len(operating)
    debt_draw = p.capex_eur * p.debt_share
    debt_open = debt_draw
    tenor = p.debt_tenor_years
    if debt_draw == 0:
        annual_service = 0.0
    elif p.debt_interest_rate == 0:
        annual_service = debt_draw / tenor
    else:
        rate = p.debt_interest_rate
        # expm1/log1p preserve the small denominator when r is close to zero.
        denominator = -math.expm1(-tenor * math.log1p(rate))
        annual_service = debt_draw * rate / denominator
    first_year = operating[0]
    first_term = next((item for item in p.contracts
                       if item.start_year <= first_year.year <= item.end_year), None)
    first_contract_volume = min(first_year.generation_mwh, first_term.annual_volume_mwh) if first_term else 0.0
    first_contract_price = max(first_term.floor_price_eur_mwh, first_year.merchant_price_eur_mwh) if first_term else 0.0
    first_revenue = ((first_contract_volume * first_contract_price if first_term else 0.0)
                     + max(0.0, first_year.generation_mwh - first_contract_volume)
                     * first_year.merchant_price_eur_mwh)
    initial_working_capital = first_revenue * p.working_capital_fraction_of_revenue
    first_service = annual_service if debt_draw > 0 else 0.0
    dsra_balance = first_service * p.dsra_months / 12
    dsra_initial = dsra_balance
    project_cashflows = [-p.capex_eur - initial_working_capital]
    equity_cashflows = [-(p.capex_eur - debt_draw) - initial_working_capital - dsra_initial]
    project_loss = equity_loss = 0.0
    prior_wc = initial_working_capital
    rows, dsra_series = [], [dsra_balance]
    tax_total, interest_total, contract_revenue_total, merchant_revenue_total = 0.0, 0.0, 0.0, 0.0
    reconciliation_residual = 0.0
    for index, year in enumerate(operating, start=1):
        term = next((item for item in p.contracts if item.start_year <= year.year <= item.end_year), None)
        contract_volume = min(year.generation_mwh, term.annual_volume_mwh) if term else 0.0
        merchant_volume = max(0.0, year.generation_mwh - contract_volume)
        contract_settled_price = max(term.floor_price_eur_mwh, year.merchant_price_eur_mwh) if term else None
        contract_revenue = contract_volume * contract_settled_price if term else 0.0
        merchant_revenue = merchant_volume * year.merchant_price_eur_mwh
        revenue = contract_revenue + merchant_revenue
        ebitda = revenue - year.opex_eur
        dep = p.capex_eur / p.depreciation_years if index <= p.depreciation_years else 0.0
        debt_service = 0.0
        interest = 0.0
        principal = 0.0
        opening_debt = debt_open
        if index <= tenor and debt_open > 1e-8:
            interest = debt_open * p.debt_interest_rate
            debt_service = min(debt_open + interest, annual_service)
            if index == tenor:
                debt_service = debt_open + interest
            principal = max(0.0, debt_service - interest)
            debt_open = max(0.0, debt_open - principal)
        project_tax, project_loss, project_taxable_after_losses = _tax_and_loss(
            ebitda - dep, project_loss, p.tax_rate)
        equity_tax, equity_loss, equity_taxable_after_losses = _tax_and_loss(
            ebitda - dep - interest, equity_loss, p.tax_rate)
        target_wc = (revenue * p.working_capital_fraction_of_revenue) if index < n else 0.0
        delta_wc = target_wc - prior_wc
        prior_wc = target_wc
        project_cf = ebitda - project_tax - delta_wc
        next_service = annual_service if index < tenor and debt_draw > 0 else 0.0
        reserve_target = next_service * p.dsra_months / 12
        dsra_transfer = reserve_target - dsra_balance
        dsra_balance = reserve_target
        dsra_series.append(dsra_balance)
        equity_cf = ebitda - equity_tax - debt_service - dsra_transfer - delta_wc
        project_cashflows.append(project_cf)
        equity_cashflows.append(equity_cf)
        expected_project_cf = ebitda - project_tax - delta_wc
        reconciliation_residual += project_cf - expected_project_cf
        tax_total += equity_tax
        interest_total += interest
        contract_revenue_total += contract_revenue
        merchant_revenue_total += merchant_revenue
        rows.append({"year": year.year, "generation_mwh": year.generation_mwh,
            "contracted_volume_mwh": contract_volume, "contract_floor_price_eur_mwh": term.floor_price_eur_mwh if term else None,
            "contract_settled_price_eur_mwh": contract_settled_price,
            "contract_revenue_eur": contract_revenue, "merchant_volume_mwh": merchant_volume,
            "merchant_price_eur_mwh": year.merchant_price_eur_mwh, "merchant_revenue_eur": merchant_revenue,
            "total_revenue_eur": revenue, "opex_eur": year.opex_eur, "ebitda_eur": ebitda,
            "depreciation_eur": dep, "debt_opening_eur": opening_debt, "interest_eur": interest,
            "principal_eur": principal, "debt_service_eur": debt_service, "debt_closing_eur": debt_open,
            "project_taxable_income_after_losses_eur": project_taxable_after_losses,
            "project_cash_tax_eur": project_tax, "project_nol_closing_eur": project_loss,
            "equity_taxable_income_after_losses_eur": equity_taxable_after_losses,
            "equity_cash_tax_eur": equity_tax, "equity_nol_closing_eur": equity_loss,
            "working_capital_balance_eur": target_wc, "working_capital_cash_change_eur": delta_wc,
            "dsra_transfer_eur": dsra_transfer, "dsra_closing_eur": dsra_balance,
            "project_cashflow_eur": project_cf, "equity_cashflow_eur": equity_cf})
    if abs(debt_open) < 1e-7:
        debt_open = 0.0
    project_irr = _irr(project_cashflows)
    equity_irr = _irr(equity_cashflows)
    final_debt_balance = debt_open
    return _result([
        _metric("Contract-floor revenue", contract_revenue_total, "EUR"),
        _metric("Merchant revenue", merchant_revenue_total, "EUR"),
        _metric("Project IRR", project_irr, "%"),
        _metric("Equity IRR", equity_irr, "%"),
        _metric("Total equity cash tax", tax_total, "EUR"),
        _metric("Debt remaining", final_debt_balance, "EUR"),
    ], series=[{"name": "project_cashflow", "x_label": "period (0 is close)", "y_unit": "EUR",
                "x": list(range(n + 1)), "y": project_cashflows},
               {"name": "equity_cashflow", "x_label": "period (0 is close)", "y_unit": "EUR",
                "x": list(range(n + 1)), "y": equity_cashflows},
               {"name": "debt_service_reserve", "x_label": "year boundary", "y_unit": "EUR",
                "x": list(range(n + 1)), "y": dsra_series}],
       table=rows, details={"project_cashflows_eur": project_cashflows,
           "equity_cashflows_eur": equity_cashflows, "project_irr_pct": project_irr,
           "equity_irr_pct": equity_irr, "initial_debt_draw_eur": debt_draw,
           "initial_equity_at_close_eur": p.capex_eur - debt_draw + initial_working_capital + dsra_initial,
           "debt_service_eur_per_year": annual_service, "debt_closing_balance_eur": final_debt_balance,
           "total_equity_cash_tax_eur": tax_total, "total_debt_interest_eur": interest_total,
           "project_tax_loss_carryforward_eur": project_loss,
           "tax_loss_carryforward_eur": equity_loss,
           "tax_loss_model": "unlimited within-model carryforward; only offsets later positive taxable income; no carryback",
           "depreciation_model": "straight-line over configured years from first operating year",
           "dsra_balance_eur": dsra_series, "dsra_initial_funding_eur": dsra_initial,
           "dsra_terminal_release_eur": dsra_initial if n >= tenor else dsra_balance,
           "terminal_working_capital_eur": prior_wc,
           "working_capital_initial_funding_eur": initial_working_capital,
           "contract_revenue_eur": contract_revenue_total,
           "merchant_revenue_eur": merchant_revenue_total,
           "project_cashflow_reconciliation_eur": reconciliation_residual,
           "project_cashflow_reconciliation": "every annual row equals EBITDA minus project cash tax minus the change in working capital",
           "equity_irr_convention": "null unless cash flows have one sign change and an NPV root exists between -99.9% and 1,000%"},
       warnings=["Contract terms are annual calendar-year minimum prices on generated contracted volume; short generation is not supplemented by take-or-pay.",
                 "The tax and loss carryforward ledger is a generic screen, not a jurisdiction-specific tax calculation.",
                 "DSRA starts funded from equity at close, tracks the next scheduled debt service, and is released when the debt schedule ends.",
                 "Project and equity cash flows are reported separately; nonconventional or rootless IRR remains null."])


def _hydrogen(p: HydrogenInput) -> dict:
    mass = p.hydrogen_kg
    stoichiometric_water = p.water_stoichiometric_kg_per_kg_h2 * mass
    water_feed = stoichiometric_water / p.water_recovery_fraction
    water_loss = max(0.0, water_feed - stoichiometric_water)
    water_treatment = (water_feed / 1000) * p.demineralization_kwh_per_m3
    electrolysis = mass * p.electrolyzer_kwh_per_kg
    chemical = mass * p.hydrogen_lhv_kwh_per_kg
    electrolysis_loss = electrolysis - chemical
    process_aux = mass * p.electrolyzer_auxiliary_kwh_per_kg
    r_h2_j_per_kg_k = 4124.2
    compression_specific = (r_h2_j_per_kg_k * p.compressor_temperature_k
        * math.log(p.delivery_pressure_bar / p.electrolyzer_outlet_pressure_bar)
        / (3_600_000 * p.compressor_isothermal_efficiency))
    compression = mass * compression_specific
    gross_fc = chemical * p.fuel_cell_gross_efficiency
    fc_aux = gross_fc * p.fuel_cell_auxiliary_fraction
    useful_electricity = gross_fc - fc_aux
    fc_conversion_loss = chemical - gross_fc
    useful_heat = fc_conversion_loss * p.fuel_cell_heat_recovery_fraction
    unrecovered_fc_loss = fc_conversion_loss - useful_heat
    total_input = electrolysis + compression + water_treatment + process_aux
    total_losses = electrolysis_loss + compression + water_treatment + process_aux + fc_aux + unrecovered_fc_loss
    residual = total_input - useful_electricity - useful_heat - total_losses
    table = [
        {"stage": "Demineralized-water intake", "energy_input_kwh": water_treatment,
         "useful_output_kwh": 0.0, "loss_kwh": water_treatment, "material_kg": water_feed},
        {"stage": "Electrolyzer", "energy_input_kwh": electrolysis,
         "useful_output_kwh": chemical, "loss_kwh": electrolysis_loss, "material_kg": mass},
        {"stage": "Hydrogen compression", "energy_input_kwh": compression,
         "useful_output_kwh": 0.0, "loss_kwh": compression, "material_kg": mass},
        {"stage": "Electrolyzer auxiliaries", "energy_input_kwh": process_aux,
         "useful_output_kwh": 0.0, "loss_kwh": process_aux, "material_kg": mass},
        {"stage": "Fuel cell", "energy_input_kwh": chemical,
         "useful_output_kwh": useful_electricity, "loss_kwh": fc_aux + unrecovered_fc_loss,
         "material_kg": mass},
    ]
    return _result([
        _metric("Electricity input including auxiliaries", total_input, "kWh"),
        _metric("Useful fuel-cell electricity", useful_electricity, "kWh"),
        _metric("Recovered useful heat", useful_heat, "kWh"),
        _metric("Electricity round-trip efficiency", useful_electricity / total_input if total_input else None, "fraction"),
        _metric("Energy balance residual", residual, "kWh"),
    ], series=[{"name": "energy_by_stage", "x_label": "stage", "y_unit": "kWh",
                "x": [row["stage"] for row in table], "y": [row["energy_input_kwh"] for row in table]}],
       table=table, details={"hydrogen_mass_kg": mass,
           "stoichiometric_water_kg": stoichiometric_water, "water_feed_kg": water_feed,
           "water_reject_kg": water_loss, "water_treatment_electricity_kwh": water_treatment,
           "electrolyzer_electricity_kwh": electrolysis, "hydrogen_chemical_energy_lhv_kwh": chemical,
           "electrolyzer_conversion_loss_kwh": electrolysis_loss,
           "electrolyzer_auxiliary_kwh": process_aux,
           "compressor_specific_work_kwh_per_kg": compression_specific,
           "compression_electricity_kwh": compression,
           "compression_pressure_in_bar": p.electrolyzer_outlet_pressure_bar,
           "compression_pressure_out_bar": p.delivery_pressure_bar,
           "compression_thermodynamic_model": "ideal-gas reversible isothermal work divided by user efficiency",
           "fuel_cell_gross_electricity_kwh": gross_fc,
           "fuel_cell_auxiliary_kwh": fc_aux, "fuel_cell_useful_electricity_kwh": useful_electricity,
           "fuel_cell_conversion_loss_kwh": fc_conversion_loss,
           "fuel_cell_recovered_heat_kwh": useful_heat,
           "unrecovered_fuel_cell_loss_kwh": unrecovered_fc_loss,
           "total_energy_input_kwh": total_input, "total_losses_kwh": total_losses,
           "energy_balance_residual_kwh": residual},
       warnings=["Water stoichiometry, recovery, stack consumption, compressor efficiency, and fuel-cell performance are supplied or illustrative assumptions.",
                 "The compressor uses ideal-gas isothermal work; DOE compression records show real station requirements depend on initial state, pressure, staging, and equipment.",
                 "No equipment sizing, safety controls, plant certification, or measured hydrogen-quality record is provided."])


def _risk(p: RiskInput) -> dict:
    table = []
    breach_count = missing_count = missing_provenance_count = 0
    for row in p.evidence:
        missing_provenance = not row.source_reference or not row.observed_on
        if row.value is None:
            status = "missing_value"
            missing_count += 1
        else:
            breach = row.value > row.threshold if row.direction == "max" else row.value < row.threshold
            status = "breach" if breach else "within_threshold"
            if breach:
                breach_count += 1
            if missing_provenance:
                status += "_unverified"
        if missing_provenance:
            missing_provenance_count += 1
        table.append({"asset": row.asset, "metric": row.metric, "value": row.value,
            "threshold": row.threshold, "direction": row.direction, "unit": row.unit,
            "source_reference": row.source_reference, "observed_on": row.observed_on,
            "provenance_status": "complete" if not missing_provenance else "incomplete",
            "status": status})
    warnings = ["Threshold checks compare supplied values and limits only; units, source facts, and records are not independently validated."]
    if not table:
        warnings.append("No asset values, thresholds, or provenance were supplied; portfolio risk is unknown.")
    return _result([
        _metric("Supplied asset metric rows", len(table), "rows"),
        _metric("Threshold breaches", breach_count, "rows"),
        _metric("Missing values", missing_count, "rows"),
        _metric("Incomplete provenance", missing_provenance_count, "rows"),
        _metric("Evidence state", "no supplied evidence" if not table else "screened user evidence", "state"),
    ], table=table, details={"breach_count": breach_count,
        "missing_value_count": missing_count, "missing_provenance_count": missing_provenance_count,
        "asset_count": len({row.asset for row in p.evidence}), "evidence_row_count": len(table),
        "thresholds_and_values_are_user_supplied": True, "external_sources_fetched": False,
        "decision": "unknown" if not table else "screen only; no portfolio approval inferred"}, warnings=warnings)


def _kabsch(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(source) < 3:
        raise ValueError("At least three inlier correspondences are required for rigid registration.")
    source_center = np.mean(source, axis=0)
    target_center = np.mean(target, axis=0)
    source_centered, target_centered = source - source_center, target - target_center
    if np.linalg.matrix_rank(source_centered, tol=1e-10) < 2 or np.linalg.matrix_rank(target_centered, tol=1e-10) < 2:
        raise ValueError("Point correspondences must span at least a plane; collinear points do not identify 3D rotation.")
    u, _, vt = np.linalg.svd(source_centered.T @ target_centered)
    correction = np.eye(3)
    correction[2, 2] = np.linalg.det(vt.T @ u.T)
    rotation = vt.T @ correction @ u.T
    translation = target_center - rotation @ source_center
    return rotation, translation


def _minimum_retained_count(candidate_count: int, retained_fraction: float) -> int:
    return max(3, int(math.ceil(candidate_count * retained_fraction)))


def _registration(p: RegistrationInput) -> dict:
    source = np.asarray(p.survey_points_xyz, dtype=float)
    target = np.asarray(p.design_points_xyz, dtype=float)
    tree = cKDTree(target)
    rotation = np.eye(3)
    translation = np.mean(target, axis=0) - np.mean(source, axis=0)
    previous_rmse = None
    converged = False
    retained = np.zeros(0, dtype=int)
    nearest_indices = np.zeros(0, dtype=int)
    distances = np.zeros(0)
    iterations = 0
    for iterations in range(1, p.maximum_iterations + 1):
        transformed = source @ rotation.T + translation
        distances_all, target_indices_all = tree.query(transformed, k=1)
        candidate = np.flatnonzero(distances_all <= p.maximum_correspondence_distance_m)
        if candidate.size < 3:
            raise ValueError("Fewer than three point pairs fall within maximum_correspondence_distance_m.")
        keep_count = _minimum_retained_count(candidate.size, p.trim_fraction)
        retained = candidate[np.argsort(distances_all[candidate])[:keep_count]]
        nearest_indices = target_indices_all[retained]
        delta_rotation, delta_translation = _kabsch(transformed[retained], target[nearest_indices])
        rotation = delta_rotation @ rotation
        translation = delta_rotation @ translation + delta_translation
        transformed = source @ rotation.T + translation
        distances, nearest_indices = tree.query(transformed, k=1)
        candidate = np.flatnonzero(distances <= p.maximum_correspondence_distance_m)
        if candidate.size >= 3:
            keep_count = _minimum_retained_count(candidate.size, p.trim_fraction)
            retained = candidate[np.argsort(distances[candidate])[:keep_count]]
            nearest_indices = nearest_indices[retained]
            distances = distances[retained]
        rmse = float(np.sqrt(np.mean(distances ** 2))) if distances.size else math.inf
        if previous_rmse is not None and abs(previous_rmse - rmse) <= p.convergence_tolerance_m:
            converged = True
            break
        previous_rmse = rmse
    if not np.isfinite(distances).all() or distances.size < 3:
        raise ArithmeticError("Registration produced no finite inlier residual set.")
    transformed = source @ rotation.T + translation
    final_distances_all, final_indices_all = tree.query(transformed, k=1)
    candidate = np.flatnonzero(final_distances_all <= p.maximum_correspondence_distance_m)
    keep_count = _minimum_retained_count(candidate.size, p.trim_fraction) if candidate.size >= 3 else 0
    retained = candidate[np.argsort(final_distances_all[candidate])[:keep_count]] if keep_count else np.zeros(0, dtype=int)
    if retained.size < 3:
        raise ValueError("Final transform has fewer than three valid inlier correspondences.")
    final_distances = final_distances_all[retained]
    rmse = float(np.sqrt(np.mean(final_distances ** 2)))
    quantile95 = float(np.quantile(final_distances, 0.95))
    angle_cos = min(1.0, max(-1.0, (np.trace(rotation) - 1) / 2))
    rotation_degrees = math.degrees(math.acos(angle_cos))
    retained_set = {int(index) for index in retained}
    point_rows = [{"survey_point_index": i, "design_point_index": int(final_indices_all[i]),
                   "nearest_neighbor_error_m": float(final_distances_all[i]),
                   "retained_inlier": i in retained_set,
                   "exclusion_reason": None if i in retained_set else
                       "maximum_correspondence_distance" if final_distances_all[i] > p.maximum_correspondence_distance_m
                       else "trimmed_high_residual"}
                  for i in range(len(source))]
    return _result([
        _metric("Final trimmed registration RMSE", rmse, "m"),
        _metric("Final inlier count", int(retained.size), "points"),
        _metric("Discarded survey points", int(len(source) - retained.size), "points"),
        _metric("Rigid rotation", rotation_degrees, "degrees"),
    ], series=[{"name": "inlier_residual", "x_label": "trimmed nearest-neighbor pair", "y_unit": "m",
                "x": list(range(len(final_distances))), "y": final_distances.tolist()}],
       table=point_rows,
       details={"rotation_matrix": rotation.tolist(), "translation_m": translation.tolist(),
           "registration_rmse_m": rmse, "median_residual_m": float(np.median(final_distances)),
           "p95_residual_m": quantile95, "maximum_residual_m": float(np.max(final_distances)),
           "inlier_count": int(retained.size), "survey_point_count": len(source),
           "design_point_count": len(target), "discarded_survey_point_count": int(len(source) - retained.size),
           "eligible_correspondence_count": int(candidate.size),
           "minimum_retained_count": keep_count,
           "actual_retained_fraction": float(retained.size / candidate.size),
           "iterations": iterations, "converged": converged,
           "maximum_correspondence_distance_m": p.maximum_correspondence_distance_m,
           "trim_fraction": p.trim_fraction, "photos_used": False,
           "photo_reconstruction": False,
           "alignment_method": "identity-initialized trimmed nearest-neighbor ICP with rigid Kabsch updates; no scale"},
       warnings=["Unpaired ICP is sensitive to initial pose, point density, local geometry, and nearest-neighbor ambiguity; inspect residuals and transform.",
                 "A residual statistic is not a survey accuracy certificate; coordinate reference and instrument uncertainty are user responsibilities.",
                 "This model consumes supplied XYZ point clouds only; no drone imagery or photo-derived reconstruction is present."])


_RUNNERS = {
    "storage-annualopt": (AnnualStorageInput, _annual_storage),
    "compare-reliability": (ReliabilityInput, _reliability),
    "forecast-cointegration": (CointegrationInput, _cointegration),
    "forecast-backtest": (BacktestInput, _backtest),
    "markets-network": (NetworkInput, _network),
    "investment-contracts": (ContractInput, _contracts),
    "lessons-hydrogenaux": (HydrogenInput, _hydrogen),
    "overview-risk": (RiskInput, _risk),
    "pilots-registration": (RegistrationInput, _registration),
}


def run(study_id: str, inputs: dict) -> dict:
    """Validate and execute one advanced planning study."""
    try:
        model, calculate = _RUNNERS[study_id]
    except (KeyError, TypeError) as error:
        raise ValueError(f"Unknown planning study: {study_id!r}") from error
    if not isinstance(inputs, dict):
        raise TypeError("Study inputs must be a JSON object.")
    result = calculate(model.model_validate(inputs))
    json.dumps(result, allow_nan=False)
    return result
