"""Bounded, synthetic decision studies for portfolio, markets, forecasts and finance.

The models in this module are transparent experiments, not calibrated forecasts,
legal rules, engineering approvals or investment advice. Inputs and outputs stay
local; random studies use per-run NumPy generators with explicit seeds.
"""
from __future__ import annotations

import json
import math
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from helioforge.engines.finance import calculate_finance
from helioforge.schemas import FinanceRequest

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
StrictInt = Annotated[int, Field(strict=True)]
SampleEnergy = Annotated[float, Field(ge=0, le=10_000_000, allow_inf_nan=False)]
EmissionFactor = Annotated[float, Field(ge=0, le=5_000, allow_inf_nan=False)]
SettlementPrice = Annotated[float, Field(ge=-10_000, le=10_000, allow_inf_nan=False)]
RegimeMean = Annotated[float, Field(ge=-10_000, le=10_000, allow_inf_nan=False)]
RegimeVolatility = Annotated[float, Field(ge=0, le=5_000, allow_inf_nan=False)]
CommodityPrice = Annotated[float, Field(gt=0, le=5_000, allow_inf_nan=False)]
CommodityVolatility = Annotated[float, Field(ge=0, le=2, allow_inf_nan=False)]
LogDrift = Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)


class WeatherAsset(_StrictModel):
    name: str = Field(min_length=1, max_length=60)
    generation_mwh: NonNegative = Field(le=10_000_000)
    weather_sensitivity: NonNegative = Field(le=1)


class WeatherInput(_StrictModel):
    horizon_years: StrictInt = Field(default=10, ge=1, le=40)
    common_shock_fraction: float = Field(default=0.75, ge=0, le=1, allow_inf_nan=False)
    seed: StrictInt = Field(default=42, ge=0, le=2**32 - 1)
    assets: list[WeatherAsset] = Field(default_factory=lambda: [
        {"name": "North solar", "generation_mwh": 18_000, "weather_sensitivity": 0.82},
        {"name": "West wind", "generation_mwh": 26_000, "weather_sensitivity": 0.68},
        {"name": "River hydro", "generation_mwh": 14_000, "weather_sensitivity": 0.35},
        {"name": "Coastal solar", "generation_mwh": 21_000, "weather_sensitivity": 0.75},
        {"name": "Hill wind", "generation_mwh": 19_000, "weather_sensitivity": 0.61},
        {"name": "Flexible demand", "generation_mwh": 9_000, "weather_sensitivity": 0.18},
    ], min_length=6, max_length=6)

    @model_validator(mode="after")
    def unique_assets(self) -> WeatherInput:
        if len({asset.name for asset in self.assets}) != len(self.assets):
            raise ValueError("Asset names must be unique.")
        return self


class MeritAsset(_StrictModel):
    name: str = Field(min_length=1, max_length=60)
    variable_cost_eur_mwh: Finite = Field(ge=-1_000, le=10_000)
    bilateral_value_eur_mwh: Finite = Field(ge=-10_000, le=10_000)
    spot_value_eur_mwh: Finite = Field(ge=-10_000, le=10_000)
    balancing_value_eur_mwh: Finite = Field(ge=-10_000, le=10_000)


class MeritInput(_StrictModel):
    bilateral_weight: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    spot_weight: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    balancing_weight: float = Field(default=0.2, ge=0, le=1, allow_inf_nan=False)
    assets: list[MeritAsset] = Field(default_factory=lambda: [
        {"name": "Solar", "variable_cost_eur_mwh": 4, "bilateral_value_eur_mwh": 68, "spot_value_eur_mwh": 61, "balancing_value_eur_mwh": 55},
        {"name": "Onshore wind", "variable_cost_eur_mwh": 7, "bilateral_value_eur_mwh": 68, "spot_value_eur_mwh": 66, "balancing_value_eur_mwh": 59},
        {"name": "Run-of-river hydro", "variable_cost_eur_mwh": 12, "bilateral_value_eur_mwh": 70, "spot_value_eur_mwh": 73, "balancing_value_eur_mwh": 95},
        {"name": "Battery discharge", "variable_cost_eur_mwh": 48, "bilateral_value_eur_mwh": 75, "spot_value_eur_mwh": 102, "balancing_value_eur_mwh": 145},
        {"name": "Gas peaker", "variable_cost_eur_mwh": 112, "bilateral_value_eur_mwh": 95, "spot_value_eur_mwh": 132, "balancing_value_eur_mwh": 185},
        {"name": "Demand response", "variable_cost_eur_mwh": 30, "bilateral_value_eur_mwh": 62, "spot_value_eur_mwh": 85, "balancing_value_eur_mwh": 125},
    ], min_length=1, max_length=24)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> MeritInput:
        if not math.isclose(self.bilateral_weight + self.spot_weight + self.balancing_weight, 1.0,
                            rel_tol=0, abs_tol=1e-9):
            raise ValueError("Bilateral, spot and balancing weights must sum to one.")
        if len({asset.name for asset in self.assets}) != len(self.assets):
            raise ValueError("Asset names must be unique.")
        return self


class CarbonInput(_StrictModel):
    static_factor_kgco2e_mwh: NonNegative = Field(default=400, le=5_000)
    sample_hours: StrictInt = Field(default=24, ge=1, le=8_760)
    generation_scale: float = Field(default=1.0, gt=0, le=100, allow_inf_nan=False)
    generation_mwh: list[SampleEnergy] = Field(default_factory=lambda: [
        0, 0, 0, 0, 0, 0, 2, 5, 9, 14, 18, 20, 21, 20, 17, 13, 8, 3, 0, 0, 0, 0, 0, 0
    ], min_length=1, max_length=8_760)
    marginal_factors_kgco2e_mwh: list[EmissionFactor] = Field(default_factory=lambda: [
        350, 340, 330, 325, 320, 330, 360, 390, 410, 430, 450, 460,
        455, 440, 420, 400, 385, 370, 360, 355, 350, 345, 340, 335
    ], min_length=1, max_length=8_760)

    @model_validator(mode="after")
    def aligned_sample(self) -> CarbonInput:
        if len(self.generation_mwh) != len(self.marginal_factors_kgco2e_mwh):
            raise ValueError("Generation and marginal-factor arrays must have equal lengths.")
        if self.sample_hours > len(self.generation_mwh):
            raise ValueError("Sample hours cannot exceed the supplied hourly data.")
        return self


class CaptureInterval(_StrictModel):
    generation_mwh: NonNegative = Field(le=10_000_000)
    spot_price_eur_mwh: Finite = Field(ge=-10_000, le=10_000)
    generation_exposure: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)


class CaptureInput(_StrictModel):
    penetration_fraction: float = Field(default=0.4, ge=0, le=1, allow_inf_nan=False)
    reference_penetration_fraction: float = Field(default=0.1, ge=0, le=1, allow_inf_nan=False)
    cannibalization_slope_eur_mwh: NonNegative = Field(default=100, le=5_000)
    intervals: list[CaptureInterval] = Field(default_factory=lambda: [
        {"generation_mwh": value, "spot_price_eur_mwh": price, "generation_exposure": exposure}
        for value, price, exposure in zip(
            [0, 0, 0, 0, 0, 0, 2, 5, 9, 14, 18, 20, 21, 20, 17, 13, 8, 3, 0, 0, 0, 0, 0, 0],
            [38, 34, 31, 29, 28, 30, 42, 58, 67, 74, 78, 75, 72, 69, 65, 61, 55, 49, 47, 45, 43, 42, 40, 39],
            [0, 0, 0, 0, 0, 0, .2, .35, .6, .8, .95, 1, 1, .95, .8, .6, .4, .2, 0, 0, 0, 0, 0, 0]
        )
    ], min_length=1, max_length=8_760)


class CountryScenario(_StrictModel):
    country_code: Literal["FR", "DE", "ES", "IT", "NL", "GB"] = "DE"


class NegativeInput(_StrictModel):
    interval_minutes: StrictInt = Field(default=15, ge=15, le=15)
    suspension_duration_minutes: StrictInt = Field(default=60, ge=15, le=10_080)
    negative_threshold_eur_mwh: Finite = Field(default=0, ge=-10_000, le=0)
    prices_eur_mwh: list[SettlementPrice] = Field(default_factory=lambda: [
        22, 20, 19, 18, 17, 16, 14, 13, 10, 6, 2, -3, -8, -12, -10, -4,
        1, 12, 26, 38, 41, 35, 29, 25
    ], min_length=1, max_length=672)
    country_scenario: CountryScenario = Field(default_factory=lambda: CountryScenario())

    @model_validator(mode="after")
    def duration_is_a_whole_number_of_intervals(self) -> NegativeInput:
        if self.suspension_duration_minutes % self.interval_minutes:
            raise ValueError("Suspension duration must be a whole number of 15-minute intervals.")
        return self


class InterconnectionInterval(_StrictModel):
    demand_a_mw: NonNegative = Field(le=1_000_000)
    demand_b_mw: NonNegative = Field(le=1_000_000)
    supply_intercept_a_eur_mwh: Finite = Field(ge=-10_000, le=10_000)
    supply_intercept_b_eur_mwh: Finite = Field(ge=-10_000, le=10_000)


class InterconnectionInput(_StrictModel):
    capacity_mw: NonNegative = Field(default=500, le=1_000_000)
    supply_slope_a_eur_mwh_mw: Positive = Field(default=0.02, le=1_000)
    supply_slope_b_eur_mwh_mw: Positive = Field(default=0.02, le=1_000)
    intervals: list[InterconnectionInterval] = Field(default_factory=lambda: [
        {"demand_a_mw": 800 + i * 3, "demand_b_mw": 750 + i * 2,
         "supply_intercept_a_eur_mwh": 28 + i * .1,
         "supply_intercept_b_eur_mwh": 45 - i * .05}
        for i in range(24)
    ], min_length=1, max_length=8_760)


class RegimesInput(_StrictModel):
    years: StrictInt = Field(default=20, ge=1, le=40)
    paths: StrictInt = Field(default=1_000, ge=20, le=10_000)
    seed: StrictInt = Field(default=42, ge=0, le=2**32 - 1)
    state_means_eur_mwh: list[RegimeMean] = Field(default_factory=lambda: [65, 115, 25], min_length=3, max_length=3)
    state_volatilities_eur_mwh: list[RegimeVolatility] = Field(default_factory=lambda: [15, 45, 25], min_length=3, max_length=3)
    transition_matrix: list[list[float]] = Field(default_factory=lambda: [
        [0.78, 0.08, 0.14], [0.22, 0.64, 0.14], [0.25, 0.05, 0.70]
    ], min_length=3, max_length=3)
    initial_state_probabilities: list[float] = Field(default_factory=lambda: [0.65, 0.15, 0.20],
                                                        min_length=3, max_length=3)

    @model_validator(mode="after")
    def valid_probabilities(self) -> RegimesInput:
        for name, vector in (("initial_state_probabilities", self.initial_state_probabilities),):
            if any(not math.isfinite(x) or x < 0 or x > 1 for x in vector) or not math.isclose(sum(vector), 1, abs_tol=1e-9):
                raise ValueError(f"{name} must contain three probabilities summing to one.")
        for row in self.transition_matrix:
            if any(not math.isfinite(x) or x < 0 or x > 1 for x in row) or not math.isclose(sum(row), 1, abs_tol=1e-9):
                raise ValueError("Each transition-matrix row must contain probabilities summing to one.")
        return self


class CommoditiesInput(_StrictModel):
    years: StrictInt = Field(default=20, ge=1, le=40)
    paths: StrictInt = Field(default=1_000, ge=20, le=5_000)
    seed: StrictInt = Field(default=42, ge=0, le=2**32 - 1)
    starting_prices: list[CommodityPrice] = Field(default_factory=lambda: [35, 80, 75], min_length=3, max_length=3)
    annual_volatilities: list[CommodityVolatility] = Field(default_factory=lambda: [0.25, 0.20, 0.30], min_length=3, max_length=3)
    annual_log_drifts: list[LogDrift] = Field(default_factory=lambda: [0.02, 0.02, 0.02], min_length=3, max_length=3)
    correlation_matrix: list[list[float]] = Field(default_factory=lambda: [
        [1.0, 0.45, 0.65], [0.45, 1.0, 0.35], [0.65, 0.35, 1.0]
    ], min_length=3, max_length=3)

    @model_validator(mode="after")
    def symmetric_psd_correlation(self) -> CommoditiesInput:
        matrix = np.asarray(self.correlation_matrix, dtype=float)
        if matrix.shape != (3, 3) or not np.allclose(matrix, matrix.T, rtol=0, atol=1e-10):
            raise ValueError("Correlation matrix must be symmetric and 3 by 3.")
        if not np.allclose(np.diag(matrix), 1.0, rtol=0, atol=1e-10):
            raise ValueError("Correlation matrix diagonal entries must equal one.")
        if np.min(np.linalg.eigvalsh(matrix)) < -1e-10:
            raise ValueError("Correlation matrix must be positive semidefinite.")
        if np.any(np.abs(matrix) > 1):
            raise ValueError("Correlation entries must be between -1 and 1.")
        return self


class HistogramInput(_StrictModel):
    year: StrictInt = Field(default=1, ge=1, le=40)
    bins: StrictInt = Field(default=16, ge=4, le=64)


class TailInput(_StrictModel):
    strike_eur_mwh: Positive = Field(default=80, le=5_000)
    volume_mwh: NonNegative = Field(default=10_000, le=10_000_000)
    years: StrictInt = Field(default=10, ge=1, le=40)
    paths: StrictInt = Field(default=1_500, ge=100, le=10_000)
    seed: StrictInt = Field(default=42, ge=0, le=2**32 - 1)
    annual_volatility: float = Field(default=0.25, ge=0, le=2, allow_inf_nan=False)
    histogram_year: HistogramInput = Field(default_factory=HistogramInput)

    @model_validator(mode="after")
    def histogram_year_within_contract(self) -> TailInput:
        if self.histogram_year.year > self.years:
            raise ValueError("Histogram year cannot exceed PPA horizon.")
        return self


class SculptInput(_StrictModel):
    target_dscr: float = Field(default=1.3, ge=1, le=5, allow_inf_nan=False)
    requested_debt_eur: NonNegative = Field(default=1_760_000, le=1_000_000_000)
    discount_rate: float = Field(default=0.08, ge=0, le=0.4, allow_inf_nan=False)
    finance_request: FinanceRequest = Field(default_factory=FinanceRequest)

    @model_validator(mode="after")
    def finance_magnitudes_bounded(self) -> SculptInput:
        amounts = (self.finance_request.capex_eur, self.finance_request.annual_gross_margin_eur,
                   self.finance_request.annual_opex_eur, self.finance_request.augmentation_cost_eur)
        if any(value > 1_000_000_000_000 for value in amounts):
            raise ValueError("Finance-request euro amounts are bounded at 1e12 for this study.")
        return self


class TrancheYear(_StrictModel):
    year: StrictInt = Field(ge=1, le=40)
    contracted_mwh: NonNegative = Field(le=10_000_000)
    floor_eur_mwh: Finite = Field(ge=-10_000, le=10_000)
    merchant_mwh: NonNegative = Field(le=10_000_000)
    merchant_price_eur_mwh: Finite = Field(ge=-10_000, le=10_000)
    opex_eur: NonNegative = Field(le=1_000_000_000)


def _default_tranche_years() -> list[dict]:
    rows = []
    for year in range(1, 21):
        rows.append({"year": year, "contracted_mwh": 12_000 if year <= 10 else 0,
                     "floor_eur_mwh": 85, "merchant_mwh": 8_000,
                     "merchant_price_eur_mwh": 75, "opex_eur": 350_000})
    return rows


class TranchesInput(_StrictModel):
    target_dscr: float = Field(default=1.3, ge=1, le=5, allow_inf_nan=False)
    merchant_haircut_fraction: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    interest_rate: float = Field(default=0.055, ge=0, le=0.3, allow_inf_nan=False)
    tenor_years: StrictInt = Field(default=10, ge=1, le=40)
    contract_years: StrictInt = Field(default=10, ge=0, le=40)
    annual_rows: list[TrancheYear] = Field(default_factory=_default_tranche_years, min_length=1, max_length=40)

    @model_validator(mode="after")
    def data_covers_tenor_and_contract(self) -> TranchesInput:
        if self.contract_years > self.tenor_years:
            raise ValueError("Contract years cannot exceed debt tenor for this tranche screen.")
        if len(self.annual_rows) < self.tenor_years:
            raise ValueError("Provide annual cash-flow rows through the debt tenor.")
        if [row.year for row in self.annual_rows] != list(range(1, len(self.annual_rows) + 1)):
            raise ValueError("Annual rows must have unique consecutive years starting at one.")
        return self


class WaterfallInput(_StrictModel):
    capital_eur: NonNegative = Field(default=5_000_000, le=1_000_000_000_000)
    distribution_pool_eur: NonNegative = Field(default=12_000_000, le=1_000_000_000_000)
    years: StrictInt = Field(default=10, ge=1, le=50)
    preferred_return_rate: float = Field(default=0.08, ge=0, le=0.5, allow_inf_nan=False)
    catchup_share: float = Field(default=0.5, gt=0, le=1, allow_inf_nan=False)
    sponsor_promote_share: float = Field(default=0.2, ge=0, lt=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def catchup_exceeds_promote(self) -> WaterfallInput:
        if self.catchup_share <= self.sponsor_promote_share:
            raise ValueError("Catch-up sponsor share must exceed the post-catch-up promote share.")
        return self


def _field(name: str, label: str, default: int | float, minimum: int | float,
           maximum: int | float, step: int | float, unit: str) -> dict:
    return {"name": name, "label": label, "default": default, "min": minimum,
            "max": maximum, "step": step, "unit": unit}


def _data(name: str, label: str, default: object) -> dict:
    return {"name": name, "label": label, "default": default}


def _defaults(model: type[_StrictModel]) -> dict:
    return model().model_dump(mode="json")


class _FinanceRequestInput(_StrictModel):
    finance_request: FinanceRequest = Field(default_factory=FinanceRequest)


STUDIES: list[dict] = [
    {
        "id": "overview-weather", "page": "overview", "title": "Correlated weather stress",
        "summary": "Compare shared and asset-specific weather shocks across six fictional assets.", "kind": "weather",
        "fields": [_field("horizon_years", "Horizon", 10, 1, 40, 1, "years"),
                   _field("common_shock_fraction", "Common shock share", 0.75, 0, 1, 0.05, "fraction"),
                   _field("seed", "Seed", 42, 0, 4_294_967_295, 1, "integer")],
        "data_fields": [_data("assets", "Six synthetic assets", _defaults(WeatherInput)["assets"])],
        "equations": ["z_i,t = sqrt(common_share) z_common,t + sqrt(1−common_share) z_idiosyncratic,i,t", "stress_i,t = generation_i × sensitivity_i × max(0, −z_i,t), capped at 100%"],
        "limitations": ["Synthetic standardized shocks; no weather observations, technology calibration, spatial model or outage probability.",
                        "The reported stress index is a bounded generation-weighted exposure proxy."],
        "sources": [{"title": "NREL solar integration data and studies", "url": "https://www.nrel.gov/grid/solar-power-data.html"}],
    },
    {
        "id": "overview-merit", "page": "overview", "title": "Value versus variable cost",
        "summary": "Compare asset variable costs with bilateral, spot and balancing value assumptions.", "kind": "merit",
        "fields": [_field("bilateral_weight", "Bilateral weight", 0.4, 0, 1, 0.05, "fraction"),
                   _field("spot_weight", "Spot weight", 0.4, 0, 1, 0.05, "fraction"),
                   _field("balancing_weight", "Balancing weight", 0.2, 0, 1, 0.05, "fraction")],
        "data_fields": [_data("assets", "Asset value matrix", _defaults(MeritInput)["assets"])],
        "equations": ["net value_route,i = assumed value_route,i − variable cost_i", "weighted net value_i = Σ_route weight_route × net value_route,i"],
        "limitations": ["All matrix values and route weights are user assumptions; no dispatch, balancing eligibility, fees, shape or contract terms are inferred."],
        "sources": [{"title": "U.S. EIA: Wholesale Electricity Markets", "url": "https://www.eia.gov/electricity/wholesalemarkets/"}],
    },
    {
        "id": "overview-carbon", "page": "overview", "title": "Hourly versus static emissions",
        "summary": "Apply supplied hourly marginal factors and compare with one static factor on the same sampled generation.", "kind": "carbon",
        "fields": [_field("static_factor_kgco2e_mwh", "Static factor", 400, 0, 5_000, 10, "kgCO2e/MWh"),
                   _field("sample_hours", "Sample hours", 24, 1, 8_760, 1, "hours"),
                   _field("generation_scale", "Generation scale", 1, 0.01, 100, 0.1, "multiplier")],
        "data_fields": [_data("generation_mwh", "Hourly generation", _defaults(CarbonInput)["generation_mwh"]),
                        _data("marginal_factors_kgco2e_mwh", "Hourly marginal factors", _defaults(CarbonInput)["marginal_factors_kgco2e_mwh"])],
        "equations": ["hourly emissions = Σ_h generation_h × marginal_factor_h", "static comparison = Σ_h generation_h × annual_static_factor"],
        "limitations": ["Supplied factors are not recalculated or calibrated; this does not estimate lifecycle emissions, avoided credits or annualize a sample day."],
        "sources": [{"title": "UNFCCC electricity-system emission-factor methodology", "url": "https://cdm.unfccc.int/Reference/catalogue/document?doc_id=000001719"}],
    },
    {
        "id": "markets-capture", "page": "markets", "title": "Generation-weighted capture price",
        "summary": "Apply a transparent penetration-linked price adjustment to user-supplied intervals.", "kind": "capture",
        "fields": [_field("penetration_fraction", "Penetration", 0.4, 0, 1, 0.01, "fraction"),
                   _field("reference_penetration_fraction", "Reference penetration", 0.1, 0, 1, 0.01, "fraction"),
                   _field("cannibalization_slope_eur_mwh", "Price slope", 100, 0, 5_000, 5, "EUR/MWh per fraction")],
        "data_fields": [_data("intervals", "Synthetic or user-provided intervals", _defaults(CaptureInput)["intervals"])],
        "equations": ["adjusted_price_t = spot_price_t − slope × (penetration − reference) × exposure_t", "capture price = Σ_t generation_t × adjusted_price_t / Σ_t generation_t"],
        "limitations": ["The linear slope is a user-defined sensitivity, not an estimated market response or price forecast. Capture price is null when supplied generation sums to zero."],
        "sources": [{"title": "Hirth, The market value of variable renewables", "url": "https://doi.org/10.1016/j.eneco.2013.02.004"}],
    },
    {
        "id": "markets-negative", "page": "markets", "title": "Negative settlement intervals",
        "summary": "Count negative 15-minute prices and identify runs reaching a user-configured suspension duration.", "kind": "negative",
        "fields": [_field("interval_minutes", "Interval", 15, 15, 15, 15, "minutes"),
                   _field("suspension_duration_minutes", "Suspension duration", 60, 15, 10_080, 15, "minutes"),
                   _field("negative_threshold_eur_mwh", "Negative threshold", 0, -10_000, 0, 1, "EUR/MWh")],
        "data_fields": [_data("prices_eur_mwh", "15-minute prices", _defaults(NegativeInput)["prices_eur_mwh"]),
                        _data("country_scenario", "Hypothetical jurisdiction label", _defaults(NegativeInput)["country_scenario"])],
        "equations": ["negative interval if price < 0 and price ≤ configured threshold", "triggering run if consecutive_negative_intervals × 15 min ≥ configured duration"],
        "limitations": ["Country label is metadata only. Any suspension setting is a hypothetical user scenario explicitly UNVERIFIED; no subsidy, settlement, legal or eligibility rule is asserted."],
        "sources": [{"title": "Regulation (EU) 2019/943, consolidated text", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02019R0943-20220623"}],
    },
    {
        "id": "markets-interconnection", "page": "markets", "title": "Two-zone interconnection",
        "summary": "Choose the least-cost flow between two zones with quadratic supply curves and a bounded interconnector.", "kind": "interconnection",
        "fields": [_field("capacity_mw", "Interconnector capacity", 500, 0, 1_000_000, 10, "MW"),
                   _field("supply_slope_a_eur_mwh_mw", "Zone A supply slope", 0.02, 0.000001, 1_000, 0.001, "EUR/MWh per MW"),
                   _field("supply_slope_b_eur_mwh_mw", "Zone B supply slope", 0.02, 0.000001, 1_000, 0.001, "EUR/MWh per MW")],
        "data_fields": [_data("intervals", "Zone demand and supply intercepts", _defaults(InterconnectionInput)["intervals"])],
        "equations": ["min_f C_A(d_A+f)+C_B(d_B−f)", "C_i(q)=a_i q + 0.5 b_i q²; −min(capacity,d_A) ≤ f ≤ min(capacity,d_B)"],
        "limitations": ["Single-link two-zone convex dispatch proxy; ignores losses, network loop flows, ramping, reserves, bids, indivisibilities and actual market-coupling constraints."],
        "sources": [{"title": "ENTSO-E Core day-ahead flow-based market coupling", "url": "https://www.entsoe.eu/bites/ccr-core/day-ahead/"}],
    },
    {
        "id": "forecast-regimes", "page": "forecast", "title": "Three-state price regimes",
        "summary": "Generate seeded annual scenario paths from normal, scarcity and oversupply Markov states.", "kind": "regime",
        "fields": [_field("years", "Horizon", 20, 1, 40, 1, "years"),
                   _field("paths", "Paths", 1_000, 20, 10_000, 100, "paths"),
                   _field("seed", "Seed", 42, 0, 4_294_967_295, 1, "integer")],
        "data_fields": [_data("state_means_eur_mwh", "State price means", _defaults(RegimesInput)["state_means_eur_mwh"]),
                        _data("state_volatilities_eur_mwh", "State volatilities", _defaults(RegimesInput)["state_volatilities_eur_mwh"]),
                        _data("transition_matrix", "Transition probabilities", _defaults(RegimesInput)["transition_matrix"]),
                        _data("initial_state_probabilities", "Initial probabilities", _defaults(RegimesInput)["initial_state_probabilities"])],
        "equations": ["S_t ∼ categorical(P[S_{t−1},·])", "price_t | S_t=s ∼ Normal(state_mean_s, state_volatility_s²)"],
        "limitations": ["Seeded annual scenarios only; user-supplied transition probabilities and state parameters are not calibrated, backtested or market forecasts."],
        "sources": [{"title": "Hamilton, A new approach to the economic analysis of nonstationary time series", "url": "https://doi.org/10.2307/1912559"}],
    },
    {
        "id": "forecast-commodities", "page": "forecast", "title": "Correlated commodity shocks",
        "summary": "Simulate correlated gas, carbon and power price paths using a bounded, PSD correlation matrix.", "kind": "commodities",
        "fields": [_field("years", "Horizon", 20, 1, 40, 1, "years"),
                   _field("paths", "Paths", 1_000, 20, 5_000, 100, "paths"),
                   _field("seed", "Seed", 42, 0, 4_294_967_295, 1, "integer")],
        "data_fields": [_data("starting_prices", "Starting gas, carbon and power prices", _defaults(CommoditiesInput)["starting_prices"]),
                        _data("annual_volatilities", "Annual volatilities", _defaults(CommoditiesInput)["annual_volatilities"]),
                        _data("annual_log_drifts", "Annual log drifts", _defaults(CommoditiesInput)["annual_log_drifts"]),
                        _data("correlation_matrix", "Correlation matrix", _defaults(CommoditiesInput)["correlation_matrix"])],
        "equations": ["Z_t = L ε_t, L Lᵀ = correlation matrix", "P_j,t = P_j,t−1 exp((μ_j−0.5σ_j²)+σ_j Z_j,t)"],
        "limitations": ["Synthetic geometric-random-walk shocks with constant user inputs; no forward curves, cointegration, structural fuel dispatch, calibration or forecast claim."],
        "sources": [{"title": "NumPy multivariate normal sampling reference", "url": "https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.multivariate_normal.html"}],
    },
    {
        "id": "forecast-tail", "page": "forecast", "title": "PPA settlement tail risk",
        "summary": "Estimate empirical 95% and 99% loss VaR/CVaR from seeded annual PPA settlement paths.", "kind": "tail",
        "fields": [_field("strike_eur_mwh", "PPA strike", 80, 0.01, 5_000, 1, "EUR/MWh"),
                   _field("volume_mwh", "Settlement volume", 10_000, 0, 10_000_000, 100, "MWh/year"),
                   _field("years", "Horizon", 10, 1, 40, 1, "years"),
                   _field("paths", "Paths", 1_500, 100, 10_000, 100, "paths"),
                   _field("seed", "Seed", 42, 0, 4_294_967_295, 1, "integer"),
                   _field("annual_volatility", "Annual volatility", 0.25, 0, 2, 0.05, "fraction")],
        "data_fields": [_data("histogram_year", "Selected year and histogram bins", _defaults(TailInput)["histogram_year"])],
        "equations": ["spot_t = strike + Σ_{k≤t} Normal(0, (volatility × strike)²)", "loss_t = (spot_t − strike) × volume", "CVaR_α = mean of the largest ceil((1−α)N) empirical losses"],
        "limitations": ["Synthetic arithmetic price walk; signed buyer settlement losses versus strike, not project revenue, calibrated PPA basis, hedge effectiveness or a probability guarantee."],
        "sources": [{"title": "Rockafellar and Uryasev, Optimization of Conditional Value-at-Risk", "url": "https://doi.org/10.21314/JOR.2000.038"}],
    },
    {
        "id": "investment-sculpt", "page": "investment", "title": "DSCR-constrained sculpted debt",
        "summary": "Compare the existing finance screen and annuity sizing with a non-negative-amortization CFADS sculpting bound.", "kind": "sculpt",
        "fields": [_field("target_dscr", "Target DSCR", 1.3, 1, 5, 0.05, "ratio"),
                   _field("requested_debt_eur", "Requested debt", 1_760_000, 0, 1_000_000_000, 10_000, "EUR"),
                   _field("discount_rate", "Project discount rate", 0.08, 0, 0.4, 0.005, "fraction")],
        "data_fields": [_data("finance_request", "Existing project-finance assumptions", _defaults(_FinanceRequestInput)["finance_request"])],
        "equations": ["target service_t = max(0, CFADS_t) / target_DSCR", "debt capacity = largest initial balance whose target-limited service amortizes within tenor without service below interest", "balance_t = balance_{t−1} + interest_t − principal_t"],
        "limitations": ["Uses the existing pre-tax nominal project-finance engine and its rounded annual CFADS. No taxes, DSRA, fees, reserve facility or legal covenant is added; infeasible requests are disclosed."],
        "sources": [{"title": "NREL System Advisor Model help, DSCR debt sizing", "url": "https://sam.nrel.gov/images/web_page_files/sam-help-2025-4-16.pdf"}],
    },
    {
        "id": "investment-tranches", "page": "investment", "title": "Contracted and merchant tranches",
        "summary": "Size debt separately against PPA-floor CFADS and user-haircut merchant cash flows.", "kind": "tranches",
        "fields": [_field("target_dscr", "Target DSCR", 1.3, 1, 5, 0.05, "ratio"),
                   _field("merchant_haircut_fraction", "Merchant factor", 0.5, 0, 1, 0.05, "fraction"),
                   _field("interest_rate", "Debt interest", 0.055, 0, 0.3, 0.005, "fraction"),
                   _field("tenor_years", "Debt tenor", 10, 1, 40, 1, "years"),
                   _field("contract_years", "PPA floor years", 10, 0, 40, 1, "years")],
        "data_fields": [_data("annual_rows", "Annual floor, merchant and operating assumptions", _defaults(TranchesInput)["annual_rows"])],
        "equations": ["contracted_CFADS_t = floor_price_t × contracted_MWh_t − OPEX_t (within floor term)", "merchant_CFADS_t = haircut × merchant_price_t × merchant_MWh_t − OPEX_t", "debt-service ceiling_t = max(0, CFADS_t) / target_DSCR"],
        "limitations": ["User-supplied floor is a hypothetical exposure input, not an executed PPA or eligibility claim. No volume shape, basis, counterparty risk, taxes or post-expiry contracted-volume conversion is inferred."],
        "sources": [{"title": "NREL System Advisor Model help, DSCR debt sizing", "url": "https://sam.nrel.gov/images/web_page_files/sam-help-2025-4-16.pdf"}],
    },
    {
        "id": "investment-waterfall", "page": "investment", "title": "Capital and promote waterfall",
        "summary": "Allocate one exit pool through return of LP capital, accrued preferred return, a 50/50 catch-up and an 80/20 promote.", "kind": "waterfall",
        "fields": [_field("capital_eur", "LP contributed capital", 5_000_000, 0, 1_000_000_000_000, 10_000, "EUR"),
                   _field("distribution_pool_eur", "Exit distribution pool", 12_000_000, 0, 1_000_000_000_000, 10_000, "EUR"),
                   _field("years", "Accrual horizon", 10, 1, 50, 1, "years"),
                   _field("preferred_return_rate", "Preferred return", 0.08, 0, 0.5, 0.005, "fraction"),
                   _field("catchup_share", "Sponsor catch-up share", 0.5, 0.01, 1, 0.05, "fraction"),
                   _field("sponsor_promote_share", "Sponsor promote share", 0.2, 0, 0.99, 0.05, "fraction")],
        "data_fields": [],
        "equations": ["preferred return due = capital × ((1 + preferred_rate)^years − 1)", "catch-up total = promote_share × LP_pref_paid / (catch-up_share − promote_share)", "remaining pool split LP/sponsor = (1 − promote_share)/promote_share"],
        "limitations": ["Explicit single-LP, time-zero contribution and single-exit convention; no interim distributions, taxes, return-of-capital priority to sponsor, clawback, IRR hurdle or legal partnership terms.",
                        "First-party algebraic convention; the source reference is not independent validation or a legal partnership agreement."],
        "sources": [{"title": "First-party HelioForge waterfall implementation and declared equations",
                     "url": "https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/74d6730e38323b69c180d7f4b4945d11010203f3/apps/api/helioforge/engines/decision_studies.py"}],
    },
]


def _metric(label: str, value: int | float | str | None, unit: str) -> dict:
    if isinstance(value, (float, np.floating)):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite result for {label}.")
    elif isinstance(value, np.integer):
        value = int(value)
    return {"label": label, "value": value, "unit": unit}


def _round(value: float, digits: int = 6) -> float:
    result = round(float(value), digits)
    if not math.isfinite(result):
        raise ValueError("Study produced a non-finite result.")
    return result


def _stress_matrix(p: WeatherInput) -> dict:
    rng = np.random.default_rng(p.seed)
    common = rng.standard_normal(p.horizon_years)
    independent = rng.standard_normal((p.horizon_years, len(p.assets)))
    common_share = p.common_shock_fraction
    shocks = math.sqrt(common_share) * common[:, None] + math.sqrt(1 - common_share) * independent
    asset_rows, year_rows, portfolio = [], [], []
    total_generation = math.fsum(asset.generation_mwh for asset in p.assets)
    for index, asset in enumerate(p.assets):
        losses = np.clip(np.maximum(0, -shocks[:, index]) * asset.weather_sensitivity, 0, 1)
        asset_rows.append({"asset": asset.name, "base_generation_mwh": asset.generation_mwh,
                           "mean_stress_loss_pct": _round(float(np.mean(losses)) * 100),
                           "p95_stress_loss_pct": _round(float(np.quantile(losses, 0.95)) * 100)})
    for year in range(p.horizon_years):
        losses = [min(1.0, max(0.0, -float(shocks[year, i])) * asset.weather_sensitivity)
                  for i, asset in enumerate(p.assets)]
        weighted = (math.fsum(asset.generation_mwh * losses[i] for i, asset in enumerate(p.assets)) /
                    total_generation if total_generation else 0.0)
        year_rows.append({"year": year + 1, "common_weather_shock": _round(float(common[year])),
                          "stress_index_pct": _round(weighted * 100)})
        portfolio.append(_round(weighted * 100))
    return {"metrics": [_metric("Mean portfolio stress index", float(np.mean(portfolio)), "%"),
                        _metric("P95 portfolio stress index", float(np.quantile(portfolio, 0.95)), "%"),
                        _metric("Horizon", p.horizon_years, "years")],
            "series": [{"name": "Portfolio stress index", "x_label": "Synthetic year", "y_unit": "%",
                        "x": list(range(1, p.horizon_years + 1)), "y": portfolio}],
            "table": asset_rows, "details": {"annual_stress": year_rows, "seed": p.seed,
                                               "common_shock_fraction": common_share,
                                               "theoretical_standardized_shock_correlation": [
                                                   [1.0 if i == j else common_share
                                                    for j in range(len(p.assets))]
                                                   for i in range(len(p.assets))],
                                               "total_base_generation_mwh": total_generation},
            "warnings": ["Synthetic common-factor weather shocks; standardized normal inputs are illustrative, not site weather or yield distributions.",
                         "Stress index is a bounded downside exposure proxy, not a probability of outage or energy-yield guarantee."]}


def _merit_matrix(p: MeritInput) -> dict:
    rows = []
    for asset in p.assets:
        bilateral = asset.bilateral_value_eur_mwh - asset.variable_cost_eur_mwh
        spot = asset.spot_value_eur_mwh - asset.variable_cost_eur_mwh
        balancing = asset.balancing_value_eur_mwh - asset.variable_cost_eur_mwh
        weighted = p.bilateral_weight * bilateral + p.spot_weight * spot + p.balancing_weight * balancing
        rows.append({"asset": asset.name, "variable_cost_eur_mwh": asset.variable_cost_eur_mwh,
                     "net_bilateral_eur_mwh": _round(bilateral), "net_spot_eur_mwh": _round(spot),
                     "net_balancing_eur_mwh": _round(balancing),
                     "weighted_net_value_eur_mwh": _round(weighted)})
    return {"metrics": [_metric("Assets compared", len(rows), "assets"),
                        _metric("Mean weighted net value", math.fsum(row["weighted_net_value_eur_mwh"] for row in rows) / len(rows), "EUR/MWh")],
            "series": [], "table": rows,
            "details": {"weights": {"bilateral": p.bilateral_weight, "spot": p.spot_weight,
                                    "balancing": p.balancing_weight}},
            "warnings": ["Route values and weights are user assumptions; no dispatch, eligibility, imbalance exposure or transaction costs are modeled."]}


def _carbon(p: CarbonInput) -> dict:
    generation = np.asarray(p.generation_mwh[:p.sample_hours], dtype=float) * p.generation_scale
    factors = np.asarray(p.marginal_factors_kgco2e_mwh[:p.sample_hours], dtype=float)
    hourly = float(np.dot(generation, factors))
    static = float(np.sum(generation)) * p.static_factor_kgco2e_mwh
    hourly_rows = [{"hour": i + 1, "generation_mwh": _round(float(generation[i])),
                    "marginal_factor_kgco2e_mwh": float(factors[i]),
                    "hourly_emissions_kgco2e": _round(float(generation[i] * factors[i]))}
                   for i in range(p.sample_hours)]
    return {"metrics": [_metric("Hourly marginal emissions", _round(hourly), "kgCO2e"),
                        _metric("Static-factor emissions", _round(static), "kgCO2e"),
                        _metric("Difference (hourly minus static)", _round(hourly - static), "kgCO2e"),
                        _metric("Sample generation", _round(float(np.sum(generation))), "MWh")],
            "series": [{"name": "Hourly marginal emissions", "x_label": "Sample hour", "y_unit": "kgCO2e",
                        "x": list(range(1, p.sample_hours + 1)),
                        "y": [_round(float(generation[i] * factors[i])) for i in range(p.sample_hours)]}],
            "table": hourly_rows,
            "details": {"sample_hours": p.sample_hours, "generation_scale": p.generation_scale,
                        "static_factor_kgco2e_mwh": p.static_factor_kgco2e_mwh,
                        "credits_tco2e": 0},
            "warnings": ["Factors are supplied scenario inputs, not a source-derived or calibrated marginal-emissions series.",
                         "No carbon credits are created or deducted; the comparison covers exactly the selected supplied hours and is not annualized."]}


def _capture(p: CaptureInput) -> dict:
    generation = math.fsum(row.generation_mwh for row in p.intervals)
    adjusted = [row.spot_price_eur_mwh - p.cannibalization_slope_eur_mwh *
                (p.penetration_fraction - p.reference_penetration_fraction) * row.generation_exposure
                for row in p.intervals]
    weighted_value = math.fsum(row.generation_mwh * adjusted[i] for i, row in enumerate(p.intervals))
    capture = weighted_value / generation if generation else None
    average_price = math.fsum(adjusted) / len(adjusted)
    table = [{"interval": i + 1, "generation_mwh": row.generation_mwh,
              "spot_price_eur_mwh": row.spot_price_eur_mwh,
              "adjusted_price_eur_mwh": _round(adjusted[i]),
              "generation_exposure": row.generation_exposure}
             for i, row in enumerate(p.intervals)]
    return {"metrics": [_metric("Capture price", _round(capture) if capture is not None else None, "EUR/MWh"),
                        _metric("Generation-weighted revenue", _round(weighted_value), "EUR"),
                        _metric("Mean adjusted interval price", _round(average_price), "EUR/MWh"),
                        _metric("Supplied generation", _round(generation), "MWh")],
            "series": [{"name": "Adjusted price", "x_label": "Interval", "y_unit": "EUR/MWh",
                        "x": list(range(1, len(adjusted) + 1)), "y": [_round(x) for x in adjusted]}],
            "table": table, "details": {"penetration_fraction": p.penetration_fraction,
                                         "reference_penetration_fraction": p.reference_penetration_fraction,
                                         "price_adjustment_eur_mwh": _round(average_price - math.fsum(r.spot_price_eur_mwh for r in p.intervals) / len(p.intervals))},
            "warnings": ["The linear penetration slope is an illustrative user assumption; interval prices and generation are not calibrated market observations.",
                         "Capture price is null when total supplied generation is zero."]}


def _negative(p: NegativeInput) -> dict:
    negative = [price < 0 and price <= p.negative_threshold_eur_mwh for price in p.prices_eur_mwh]
    threshold_intervals = p.suspension_duration_minutes // p.interval_minutes
    runs, current, max_run = 0, 0, 0
    for flag in [*negative, False]:
        if flag:
            current += 1
        else:
            if current >= threshold_intervals:
                runs += 1
            max_run = max(max_run, current)
            current = 0
    intervals = [{"interval": i + 1, "price_eur_mwh": price,
                   "negative_at_threshold": negative[i]}
                  for i, price in enumerate(p.prices_eur_mwh)]
    return {"metrics": [_metric("Negative settlement intervals", sum(negative), "15-minute intervals"),
                        _metric("Negative settlement duration", sum(negative) * p.interval_minutes, "minutes"),
                        _metric("Suspension-triggering runs", runs, "runs"),
                        _metric("Longest negative run", max_run * p.interval_minutes, "minutes")],
            "series": [{"name": "Settlement price", "x_label": "15-minute interval", "y_unit": "EUR/MWh",
                        "x": list(range(1, len(p.prices_eur_mwh) + 1)), "y": list(p.prices_eur_mwh)}],
            "table": intervals,
            "details": {"country_code_scenario_label": p.country_scenario.country_code,
                        "suspension_threshold_intervals": threshold_intervals,
                        "hypothetical_country_rule_status": "UNVERIFIED user scenario; no country rule applied"},
            "warnings": ["Country code is a scenario label only. Suspension duration and threshold are user hypotheses marked UNVERIFIED; no legal or market rule is asserted.",
                         "Counts use the supplied, equally spaced 15-minute series; missing intervals and settlement calendars are not inferred."]}


def _interconnection(p: InterconnectionInput) -> dict:
    rows, flows, gains = [], [], []
    for i, interval in enumerate(p.intervals):
        lower = max(-p.capacity_mw, -interval.demand_a_mw)
        upper = min(p.capacity_mw, interval.demand_b_mw)
        marginal_a_zero = interval.supply_intercept_a_eur_mwh + p.supply_slope_a_eur_mwh_mw * interval.demand_a_mw
        marginal_b_zero = interval.supply_intercept_b_eur_mwh + p.supply_slope_b_eur_mwh_mw * interval.demand_b_mw
        unconstrained = (marginal_b_zero - marginal_a_zero) / (p.supply_slope_a_eur_mwh_mw + p.supply_slope_b_eur_mwh_mw)
        flow = min(upper, max(lower, unconstrained))
        q_a, q_b = interval.demand_a_mw + flow, interval.demand_b_mw - flow
        cost_a = interval.supply_intercept_a_eur_mwh * q_a + 0.5 * p.supply_slope_a_eur_mwh_mw * q_a**2
        cost_b = interval.supply_intercept_b_eur_mwh * q_b + 0.5 * p.supply_slope_b_eur_mwh_mw * q_b**2
        base_cost_a = interval.supply_intercept_a_eur_mwh * interval.demand_a_mw + 0.5 * p.supply_slope_a_eur_mwh_mw * interval.demand_a_mw**2
        base_cost_b = interval.supply_intercept_b_eur_mwh * interval.demand_b_mw + 0.5 * p.supply_slope_b_eur_mwh_mw * interval.demand_b_mw**2
        price_a = interval.supply_intercept_a_eur_mwh + p.supply_slope_a_eur_mwh_mw * q_a
        price_b = interval.supply_intercept_b_eur_mwh + p.supply_slope_b_eur_mwh_mw * q_b
        gain = base_cost_a + base_cost_b - cost_a - cost_b
        rows.append({"interval": i + 1, "flow_a_to_b_mw": _round(flow),
                     "zone_a_supply_mw": _round(q_a), "zone_b_supply_mw": _round(q_b),
                     "zone_a_marginal_price_eur_mwh": _round(price_a),
                     "zone_b_marginal_price_eur_mwh": _round(price_b),
                     "generation_cost_eur": _round(cost_a + cost_b),
                     "welfare_gain_vs_isolated_eur": _round(gain)})
        flows.append(_round(flow))
        gains.append(_round(gain))
    return {"metrics": [_metric("Total absolute flow", _round(math.fsum(abs(x) for x in flows)), "MW-intervals"),
                        _metric("Net welfare gain versus isolated zones", _round(math.fsum(gains)), "EUR per interval-set"),
                        _metric("Configured transfer capacity", p.capacity_mw, "MW")],
            "series": [{"name": "Flow A to B", "x_label": "Interval", "y_unit": "MW",
                        "x": list(range(1, len(flows) + 1)), "y": flows}],
            "table": rows,
            "details": {"flow_sign_convention": "positive exports from zone A to zone B",
                        "supply_curve": "marginal cost = intercept + slope × output"},
            "warnings": ["Two-zone, one-link quadratic supply screen; not a flow-based network or market-coupling solver.",
                         "No losses, loop flows, ramping, bids, reserves, outages or network security limits are represented."]}


def _regimes(p: RegimesInput) -> dict:
    rng = np.random.default_rng(p.seed)
    transition = np.asarray(p.transition_matrix, dtype=float)
    means = np.asarray(p.state_means_eur_mwh, dtype=float)
    sigmas = np.asarray(p.state_volatilities_eur_mwh, dtype=float)
    states = rng.choice(3, size=p.paths, p=np.asarray(p.initial_state_probabilities, dtype=float))
    state_paths, price_paths = [], []
    for _ in range(p.years):
        prices = rng.normal(means[states], sigmas[states])
        state_paths.append(states.copy())
        price_paths.append(prices)
        next_states = np.empty_like(states)
        for state in range(3):
            mask = states == state
            if np.any(mask):
                next_states[mask] = rng.choice(3, size=int(np.sum(mask)), p=transition[state])
        states = next_states
    rows, p50, p10, p90 = [], [], [], []
    for year, prices in enumerate(price_paths, 1):
        q10, q50, q90 = np.quantile(prices, [0.1, 0.5, 0.9])
        row = {"year": year, "p10_eur_mwh": _round(float(q10)),
               "p50_eur_mwh": _round(float(q50)), "p90_eur_mwh": _round(float(q90)),
               "scarcity_state_share": _round(float(np.mean(state_paths[year - 1] == 1))),
               "oversupply_state_share": _round(float(np.mean(state_paths[year - 1] == 2)))}
        rows.append(row)
        p10.append(row["p10_eur_mwh"])
        p50.append(row["p50_eur_mwh"])
        p90.append(row["p90_eur_mwh"])
    return {"metrics": [_metric("Paths", p.paths, "paths"), _metric("Horizon", p.years, "years"),
                        _metric("Seed", p.seed, "integer")],
            "series": [{"name": "P10", "x_label": "Year", "y_unit": "EUR/MWh", "x": list(range(1, p.years + 1)), "y": p10},
                       {"name": "P50", "x_label": "Year", "y_unit": "EUR/MWh", "x": list(range(1, p.years + 1)), "y": p50},
                       {"name": "P90", "x_label": "Year", "y_unit": "EUR/MWh", "x": list(range(1, p.years + 1)), "y": p90}],
            "table": rows, "details": {"seed": p.seed, "paths": p.paths,
                                         "state_labels": ["normal", "scarcity", "oversupply"]},
            "warnings": ["Synthetic annual Markov regime scenarios with user-specified transitions; not a calibrated forecast or confidence interval.",
                         "State means and volatilities are not tied to a market, fuel stack or hourly price process."]}


def _commodities(p: CommoditiesInput) -> dict:
    rng = np.random.default_rng(p.seed)
    corr = np.asarray(p.correlation_matrix, dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    root = eigenvectors @ np.diag(np.sqrt(np.maximum(eigenvalues, 0.0)))
    vol = np.asarray(p.annual_volatilities, dtype=float)
    drift = np.asarray(p.annual_log_drifts, dtype=float)
    prices = np.tile(np.asarray(p.starting_prices, dtype=float), (p.paths, 1))
    rows = []
    series: dict[str, list[float]] = {"gas": [], "carbon": [], "power": []}
    names = ("gas", "carbon", "power")
    for year in range(1, p.years + 1):
        independent = rng.standard_normal((p.paths, 3))
        shocks = independent @ root.T
        prices *= np.exp(drift - 0.5 * vol**2 + shocks * vol)
        row = {"year": year}
        for index, name in enumerate(names):
            q10, q50, q90 = np.quantile(prices[:, index], [0.1, 0.5, 0.9])
            row[f"{name}_p10"] = _round(float(q10))
            row[f"{name}_p50"] = _round(float(q50))
            row[f"{name}_p90"] = _round(float(q90))
            series[name].append(row[f"{name}_p50"])
        rows.append(row)
    return {"metrics": [_metric("Paths", p.paths, "paths"), _metric("Horizon", p.years, "years"),
                        _metric("Seed", p.seed, "integer")],
            "series": [{"name": f"{name.title()} median", "x_label": "Year", "y_unit": "scenario currency/unit",
                        "x": list(range(1, p.years + 1)), "y": values} for name, values in series.items()],
            "table": rows, "details": {"seed": p.seed, "paths": p.paths,
                                         "correlation_matrix": p.correlation_matrix,
                                         "commodity_order": list(names)},
            "warnings": ["Seeded geometric-random-walk scenarios with constant user inputs; not market-forward or econometric cointegration estimates.",
                         "Currency units follow the supplied values; gas, carbon and power quotes are not automatically normalized or converted."]}


def _tail(p: TailInput) -> dict:
    rng = np.random.default_rng(p.seed)
    shocks = rng.normal(0, p.annual_volatility * p.strike_eur_mwh, (p.paths, p.years))
    prices = p.strike_eur_mwh + np.cumsum(shocks, axis=1)
    losses = (prices - p.strike_eur_mwh) * p.volume_mwh
    selected = p.histogram_year.year - 1
    sample_losses = losses[:, selected]
    rows = []
    for confidence in (0.95, 0.99):
        tail_count = max(1, math.ceil((1 - confidence) * p.paths))
        sorted_losses = np.sort(sample_losses)
        var = float(np.quantile(sample_losses, confidence, method="higher"))
        cvar = float(np.mean(sorted_losses[-tail_count:]))
        rows.append((confidence, var, cvar))
    histogram_counts, histogram_edges = np.histogram(prices[:, selected], bins=p.histogram_year.bins)
    path_rows = []
    for i in range(p.paths):
        path_rows.append({"path": i, "prices_eur_mwh": [_round(float(x), 12) for x in prices[i]],
                          "losses_eur": [_round(float(x), 12) for x in losses[i]]})
    return {"metrics": [_metric("95% loss VaR", _round(rows[0][1], 2), "EUR"),
                        _metric("95% loss CVaR", _round(rows[0][2], 2), "EUR"),
                        _metric("99% loss VaR", _round(rows[1][1], 2), "EUR"),
                        _metric("99% loss CVaR", _round(rows[1][2], 2), "EUR"),
                        _metric("Selected histogram year", selected + 1, "year")],
            "series": [{"name": "Loss distribution", "x_label": "Path", "y_unit": "EUR",
                        "x": list(range(p.paths)), "y": [_round(float(x), 2) for x in sample_losses]}],
            "table": [{"confidence": alpha, "loss_var_eur": _round(var, 2),
                       "loss_cvar_eur": _round(cvar, 2),
                       "tail_paths": max(1, math.ceil((1 - alpha) * p.paths))}
                      for alpha, var, cvar in rows],
            "details": {"seed": p.seed, "paths": p.paths,
                        "loss_convention": "positive means buyer settlement cost above fixed strike; negative means settlement benefit",
                        "raw_paths": path_rows,
                        "histogram": {"year": selected + 1, "edges_eur_mwh": [_round(float(x)) for x in histogram_edges],
                                      "counts": [int(x) for x in histogram_counts]}},
            "warnings": ["Seeded arithmetic random walk around the fixed PPA strike; the model is not calibrated to market data or contract terms.",
                         "VaR/CVaR use the selected year's signed buyer settlement-loss distribution; positive values are losses and negative values are benefits."]}


def _debt_schedule(principal: float, cfads: list[float], tenor: int,
                   interest_rate: float, target_dscr: float, *, build_rows: bool = False) -> tuple[bool, list[dict]]:
    balance = float(principal)
    rows: list[dict] = []
    for year, cfad in enumerate(cfads[:tenor], 1):
        opening = balance
        interest = opening * interest_rate
        max_service = max(0.0, cfad) / target_dscr
        if opening > 1e-7:
            if cfad <= 0 or max_service + 1e-7 < interest:
                if build_rows:
                    rows.append({"year": year, "cfads_eur": _round(cfad, 2),
                                 "opening_balance_eur": _round(opening, 2),
                                 "interest_eur": _round(interest, 2), "principal_eur": 0.0,
                                 "debt_service_eur": 0.0, "closing_balance_eur": _round(opening, 2),
                                 "dscr": None, "negative_amortization": True})
                return False, rows
            service = min(max_service, opening + interest)
            principal_paid = max(0.0, service - interest)
            balance = max(0.0, opening - principal_paid)
        else:
            service = interest = principal_paid = balance = 0.0
        if build_rows:
            rows.append({"year": year, "cfads_eur": _round(cfad, 2),
                         "opening_balance_eur": _round(opening, 2),
                         "interest_eur": _round(interest, 2),
                         "principal_eur": _round(principal_paid, 2),
                         "debt_service_eur": _round(service, 2),
                         "closing_balance_eur": _round(balance, 2),
                         "dscr": _round(cfad / service, 6) if service else None,
                         "negative_amortization": False})
    if build_rows:
        for year in range(len(cfads[:tenor]) + 1, len(cfads) + 1):
            rows.append({"year": year, "cfads_eur": _round(cfads[year - 1], 2),
                         "opening_balance_eur": 0.0, "interest_eur": 0.0,
                         "principal_eur": 0.0, "debt_service_eur": 0.0,
                         "closing_balance_eur": 0.0, "dscr": None,
                         "negative_amortization": False})
    feasible = balance <= 1e-6
    return feasible, rows


def _sculpt_capacity(cfads: list[float], tenor: int, rate: float, target_dscr: float,
                     cap: float) -> float:
    low, high = 0.0, cap
    feasible, _ = _debt_schedule(high, cfads, tenor, rate, target_dscr)
    if feasible:
        return cap
    for _ in range(80):
        middle = (low + high) / 2
        feasible, _ = _debt_schedule(middle, cfads, tenor, rate, target_dscr)
        if feasible:
            low = middle
        else:
            high = middle
    return low


def _sculpt(p: SculptInput) -> dict:
    finance_request = p.finance_request.model_copy(update={"discount_rate": p.discount_rate,
                                                          "minimum_dscr": p.target_dscr})
    base = calculate_finance(finance_request)
    cashflows = [float(row["cfads_eur"]) for row in base["rows"]]
    tenor = finance_request.debt_tenor_years
    project_capacity = _sculpt_capacity(cashflows, tenor, finance_request.debt_interest_rate,
                                        p.target_dscr, finance_request.capex_eur)
    capped_request = min(p.requested_debt_eur, finance_request.capex_eur)
    sized_debt = min(capped_request, project_capacity)
    requested_feasible, _ = _debt_schedule(capped_request, cashflows, tenor,
                                           finance_request.debt_interest_rate, p.target_dscr)
    sized_feasible, schedule = _debt_schedule(sized_debt, cashflows, tenor,
                                              finance_request.debt_interest_rate, p.target_dscr,
                                              build_rows=True)
    if not sized_feasible:
        raise ArithmeticError("Sized debt schedule failed its non-negative-amortization feasibility check.")
    active_dscr = [row["dscr"] for row in schedule if row["debt_service_eur"] > 0]
    service_limits = [max(0, cashflows[i]) / p.target_dscr for i in range(tenor)]
    pv_service = math.fsum(service_limits[i] / (1 + finance_request.debt_interest_rate)**(i + 1)
                           for i in range(tenor))
    negative_years = [row["year"] for row in base["rows"][:tenor] if row["cfads_eur"] <= 0]
    warnings = list(base["warnings"])
    if p.requested_debt_eur > finance_request.capex_eur:
        warnings.append("Requested debt was capped at project CAPEX.")
    if not requested_feasible:
        warnings.append("Requested debt is infeasible under the target DSCR and non-negative-amortization screen; the displayed schedule is sized to the feasible amount.")
    if negative_years:
        warnings.append("Nonpositive CFADS years remain visible; debt must be repaid before any zero/negative-CFADS year, or the requested amount is infeasible.")
    minimum_dscr = min(active_dscr) if active_dscr else None
    metrics = [_metric("Project NPV", base["npv_eur"], "EUR"),
               _metric("Pre-tax nominal project IRR", base["irr_pct"], "%"),
               _metric("Existing level-payment debt capacity", base["level_payment_debt_capacity_eur"], "EUR"),
               _metric("PV of DSCR-limited service before feasibility screen", _round(pv_service, 2), "EUR"),
               _metric("Sculpted debt capacity", _round(project_capacity, 2), "EUR"),
               _metric("Sized debt", _round(sized_debt, 2), "EUR"),
               _metric("Minimum DSCR", _round(minimum_dscr, 6) if minimum_dscr is not None else None, "ratio")]
    return {"metrics": metrics,
            "series": [{"name": "CFADS", "x_label": "Year", "y_unit": "EUR",
                        "x": [row["year"] for row in base["rows"]],
                        "y": [row["cfads_eur"] for row in base["rows"]]},
                       {"name": "Sculpted debt service", "x_label": "Year", "y_unit": "EUR",
                        "x": [row["year"] for row in schedule],
                        "y": [row["debt_service_eur"] for row in schedule]}],
            "table": schedule,
            "details": {"requested_debt_eur": p.requested_debt_eur,
                        "capped_requested_debt_eur": _round(capped_request, 2),
                        "requested_debt_feasible": requested_feasible,
                        "project_rows": base["rows"], "sculpt_schedule": schedule,
                        "nonpositive_cfads_years_in_tenor": negative_years,
                        "project_irr_pct": base["irr_pct"],
                        "project_cashflow_model": base["model"],
                        "negative_amortization_allowed": False},
            "warnings": warnings}


def _tranches(p: TranchesInput) -> dict:
    rows = p.annual_rows[:p.tenor_years]
    contracted_cfads, haircut_cfads, full_cfads = [], [], []
    detail = []
    for row in rows:
        contracted_revenue = row.floor_eur_mwh * row.contracted_mwh if row.year <= p.contract_years else 0.0
        merchant_revenue = row.merchant_price_eur_mwh * row.merchant_mwh
        cfads_contract = contracted_revenue - row.opex_eur
        cfads_haircut = contracted_revenue + p.merchant_haircut_fraction * merchant_revenue - row.opex_eur
        cfads_full = contracted_revenue + merchant_revenue - row.opex_eur
        contracted_cfads.append(cfads_contract)
        haircut_cfads.append(cfads_haircut)
        full_cfads.append(cfads_full)
        detail.append({"year": row.year, "contracted_floor_revenue_eur": _round(contracted_revenue, 2),
                       "merchant_revenue_before_haircut_eur": _round(merchant_revenue, 2),
                       "contracted_only_cfads_eur": _round(cfads_contract, 2),
                       "haircut_merchant_cfads_eur": _round(cfads_haircut, 2),
                       "full_merchant_cfads_eur": _round(cfads_full, 2)})
    # With nonnegative interest, initial debt cannot exceed the sum of each
    # year's maximum DSCR-limited service. This data-derived bound preserves
    # valid large cash-flow cases without an arbitrary euro cap.
    def service_bound(cfads: list[float]) -> float:
        return math.fsum(max(0.0, cfad) / p.target_dscr
                         for cfad in cfads[:p.tenor_years])

    contracted_debt = _sculpt_capacity(contracted_cfads, p.tenor_years, p.interest_rate,
                                       p.target_dscr, service_bound(contracted_cfads))
    haircut_debt = _sculpt_capacity(haircut_cfads, p.tenor_years, p.interest_rate,
                                    p.target_dscr, service_bound(haircut_cfads))
    full_debt = _sculpt_capacity(full_cfads, p.tenor_years, p.interest_rate,
                                 p.target_dscr, service_bound(full_cfads))
    negative_years = [row["year"] for row in detail if row["haircut_merchant_cfads_eur"] <= 0]
    return {"metrics": [_metric("Contracted-floor debt capacity", _round(contracted_debt, 2), "EUR"),
                        _metric("Haircut merchant debt capacity", _round(haircut_debt, 2), "EUR"),
                        _metric("Full merchant debt capacity", _round(full_debt, 2), "EUR"),
                        _metric("Merchant haircut", p.merchant_haircut_fraction, "fraction")],
            "series": [{"name": "Haircut merchant CFADS", "x_label": "Year", "y_unit": "EUR",
                        "x": [row["year"] for row in detail],
                        "y": [row["haircut_merchant_cfads_eur"] for row in detail]}],
            "table": detail,
            "details": {"target_dscr": p.target_dscr, "interest_rate": p.interest_rate,
                        "tenor_years": p.tenor_years, "contract_years": p.contract_years,
                        "nonpositive_haircut_cfads_years": negative_years,
                        "capacity_method": "largest debt amortizing at or below target-DSCR service without negative amortization"},
            "warnings": ["PPA floor values and merchant prices are user assumptions, not executed contract terms or market observations.",
                         "Contracted volume earns the floor only during the configured term; expired contracted volume is zero unless separately entered as merchant volume.",
                         "Nonpositive CFADS remains visible and cannot support debt service; no reserve, tax, basis or counterparty-risk model is included."]}


def _waterfall(p: WaterfallInput) -> dict:
    pool = p.distribution_pool_eur
    remaining = pool
    allocations: list[dict] = []

    def allocate(stage: str, lp: float, sponsor: float) -> None:
        nonlocal remaining
        amount = min(remaining, max(0.0, lp + sponsor))
        if amount + 1e-9 < lp + sponsor and lp + sponsor > 0:
            scale = amount / (lp + sponsor)
            lp *= scale
            sponsor *= scale
        remaining = max(0.0, remaining - amount)
        allocations.append({"stage": stage, "lp_eur": _round(lp, 2),
                            "sponsor_eur": _round(sponsor, 2), "amount_eur": _round(lp + sponsor, 2)})

    lp_capital = min(remaining, p.capital_eur)
    allocate("return_of_capital", lp_capital, 0.0)
    pref_due = p.capital_eur * ((1 + p.preferred_return_rate)**p.years - 1)
    pref_paid = min(remaining, pref_due)
    allocate("preferred_return", pref_paid, 0.0)
    catchup_total_due = (p.sponsor_promote_share * pref_paid /
                         (p.catchup_share - p.sponsor_promote_share)) if pref_paid else 0.0
    catchup_total_paid = min(remaining, catchup_total_due)
    allocate("catch_up", catchup_total_paid * (1 - p.catchup_share),
             catchup_total_paid * p.catchup_share)
    promote_pool = remaining
    promote_lp = promote_pool * (1 - p.sponsor_promote_share)
    promote_sponsor = promote_pool * p.sponsor_promote_share
    allocate("promote", promote_lp, promote_sponsor)
    # Round the displayed stage rows to cents; retain the exact conservation proof separately.
    exact_lp = lp_capital + pref_paid + catchup_total_paid * (1 - p.catchup_share) + promote_pool * (1 - p.sponsor_promote_share)
    exact_sponsor = catchup_total_paid * p.catchup_share + promote_pool * p.sponsor_promote_share
    exact_total = exact_lp + exact_sponsor
    if not math.isclose(exact_total, pool, rel_tol=0, abs_tol=1e-6):
        raise ArithmeticError("Waterfall allocations do not reconcile to the distribution pool.")
    return {"metrics": [_metric("LP distribution", _round(exact_lp, 2), "EUR"),
                        _metric("Sponsor distribution", _round(exact_sponsor, 2), "EUR"),
                        _metric("Total allocated", _round(exact_total, 2), "EUR"),
                        _metric("LP preferred return paid", _round(pref_paid, 2), "EUR")],
            "series": [], "table": allocations,
            "details": {"allocations": allocations,
                        "lp_capital_return_eur": _round(lp_capital, 2),
                        "lp_preferred_return_due_eur": _round(pref_due, 2),
                        "lp_preferred_return_eur": _round(pref_paid, 2),
                        "unpaid_preferred_return_eur": _round(max(0.0, pref_due - pref_paid), 2),
                        "sponsor_catchup_eur": _round(catchup_total_paid * p.catchup_share, 2),
                        "lp_catchup_eur": _round(catchup_total_paid * (1 - p.catchup_share), 2),
                        "sponsor_promote_eur": _round(promote_sponsor, 2),
                        "lp_promote_eur": _round(promote_lp, 2),
                        "unallocated_distribution_eur": _round(max(0.0, pool - exact_total), 2),
                        "exact_conservation_residual_eur": _round(pool - exact_total, 8),
                        "convention": "single LP contributes at time zero; return LP capital, compound 8%/configured pref to one exit, split catch-up at configured sponsor share until promote share is reached, then split remaining pool LP/sponsor"},
            "warnings": ["Illustrative waterfall convention only; legal definitions, tax, interim cash flows, clawback and sponsor capital are not modeled.",
                         "The preferred return accrues from the beginning of the configured horizon and is paid only after LP return of capital."]}


_RUNNERS = {
    "overview-weather": (WeatherInput, _stress_matrix),
    "overview-merit": (MeritInput, _merit_matrix),
    "overview-carbon": (CarbonInput, _carbon),
    "markets-capture": (CaptureInput, _capture),
    "markets-negative": (NegativeInput, _negative),
    "markets-interconnection": (InterconnectionInput, _interconnection),
    "forecast-regimes": (RegimesInput, _regimes),
    "forecast-commodities": (CommoditiesInput, _commodities),
    "forecast-tail": (TailInput, _tail),
    "investment-sculpt": (SculptInput, _sculpt),
    "investment-tranches": (TranchesInput, _tranches),
    "investment-waterfall": (WaterfallInput, _waterfall),
}


def run(study_id: str, inputs: dict) -> dict:
    """Validate a study payload and return the common metrics/series/table contract."""
    try:
        model, calculate = _RUNNERS[study_id]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unknown study: {study_id!r}") from exc
    if not isinstance(inputs, dict):
        raise TypeError("Study inputs must be a JSON object.")
    validated = model.model_validate(inputs)
    result = calculate(validated)
    json.dumps(result, allow_nan=False)
    return result
