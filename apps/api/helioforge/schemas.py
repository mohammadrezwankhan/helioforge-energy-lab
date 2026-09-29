"""API contracts. Power is kW; energy kWh; money EUR unless explicitly labelled."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Market = Literal["FR", "DE", "ES", "IT", "NL", "GB"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, allow_inf_nan=False)


class StorageRequest(StrictModel):
    market: Market = "FR"
    capacity_kwh: Positive = Field(default=10000, le=1_000_000)
    power_kw: Positive = Field(default=5000, le=500_000)
    round_trip_efficiency: float = Field(default=0.9, gt=0, le=1)
    min_soc_fraction: float = Field(default=0.1, ge=0, lt=1)
    max_soc_fraction: float = Field(default=0.9, gt=0, le=1)
    initial_soc_fraction: float = Field(default=0.5, ge=0, le=1)
    interval_hours: float = Field(default=1, ge=0.25, le=1)
    wear_eur_per_kwh: NonNegative = 0.015
    peak_charge_eur_per_kw_period: NonNegative = 0.0
    grid_import_limit_kw: Positive = 20000
    grid_export_limit_kw: NonNegative = 10000
    import_eur_per_kwh: list[Finite] = Field(default_factory=list, max_length=168)
    export_eur_per_kwh: list[Finite] = Field(default_factory=list, max_length=168)
    load_kw: list[NonNegative] = Field(default_factory=list, max_length=168)
    pv_kw: list[NonNegative] = Field(default_factory=list, max_length=168)

    @model_validator(mode="after")
    def validate_timeseries(self) -> StorageRequest:
        if not self.min_soc_fraction <= self.initial_soc_fraction <= self.max_soc_fraction:
            raise ValueError("Initial SOC must be between minimum and maximum SOC.")
        if self.min_soc_fraction >= self.max_soc_fraction:
            raise ValueError("Minimum SOC must be less than maximum SOC.")
        arrays = [self.import_eur_per_kwh, self.export_eur_per_kwh, self.load_kw, self.pv_kw]
        if any(arrays):
            if not all(arrays) or len({len(x) for x in arrays}) != 1:
                raise ValueError("Provide all four equally sized time series, or leave all four empty.")
            if len(self.load_kw) < 2:
                raise ValueError("At least two intervals are required.")
        elif self.interval_hours != 1:
            raise ValueError("The built-in daily profile uses one-hour intervals; supply custom series otherwise.")
        return self


class FinanceRequest(StrictModel):
    capex_eur: Positive = 3_200_000
    annual_gross_margin_eur: NonNegative = 820_000
    annual_opex_eur: NonNegative = 70_000
    years: int = Field(default=20, ge=2, le=40)
    discount_rate: float = Field(default=0.08, ge=0, le=0.4)
    annual_margin_degradation: float = Field(default=0.018, ge=0, le=0.2)
    escalation_rate: float = Field(default=0.02, ge=0, le=0.2)
    debt_fraction: float = Field(default=0.55, ge=0, le=0.95)
    debt_interest_rate: float = Field(default=0.055, ge=0, le=0.3)
    debt_tenor_years: int = Field(default=10, ge=1, le=40)
    augmentation_year: int | None = Field(default=10, ge=1, le=40)
    augmentation_cost_eur: NonNegative = 450_000
    augmentation_retention_restore: float = Field(default=0.1, ge=0, le=1)
    contracted_fraction: float = Field(default=0.4, ge=0, le=1)
    contract_years: int = Field(default=10, ge=0, le=40)
    merchant_margin_factor: float = Field(default=0.75, ge=0, le=2)
    minimum_dscr: float = Field(default=1.3, ge=1, le=3)

    @model_validator(mode="after")
    def terms_within_life(self) -> FinanceRequest:
        if self.debt_tenor_years > self.years or self.contract_years > self.years:
            raise ValueError("Debt and contract terms cannot exceed project life.")
        if self.augmentation_year is not None and self.augmentation_year > self.years:
            raise ValueError("Augmentation year cannot exceed project life.")
        return self


class PVRequest(StrictModel):
    capacity_kwp: Positive = Field(default=50000, le=10_000_000)
    specific_yield_kwh_kwp: Positive = Field(default=1350, le=2600)
    capex_eur_kwp: Positive = 650
    opex_eur_kwp_year: NonNegative = 12
    degradation_fraction: float = Field(default=0.004, ge=0, le=0.1)
    discount_rate: float = Field(default=0.07, ge=0, le=0.4)
    years: int = Field(default=30, ge=2, le=50)
    capture_price_eur_mwh: NonNegative = 68
    curtailment_fraction: float = Field(default=0.02, ge=0, lt=1)
    inverter_replacement_year: int | None = Field(default=15, ge=1, le=50)
    inverter_replacement_eur_kwp: NonNegative = 35
    panel_kwp: Positive = 0.6
    panel_area_m2: Positive = 2.8
    ground_coverage_ratio: float = Field(default=0.35, gt=0, le=1)

    @model_validator(mode="after")
    def inverter_within_life(self) -> PVRequest:
        if self.inverter_replacement_year and self.inverter_replacement_year > self.years:
            raise ValueError("Inverter replacement must fall within project life.")
        return self


class ForecastRequest(StrictModel):
    market: Market = "FR"
    base_price_eur_mwh: Finite = 80
    long_run_price_eur_mwh: Finite = 70
    mean_reversion: float = Field(default=0.25, gt=0, le=1)
    annual_shock_eur_mwh: NonNegative = Field(default=15, le=250)
    trend_eur_mwh_year: Finite = 0.5
    years: int = Field(default=20, ge=2, le=40)
    paths: int = Field(default=1500, ge=100, le=10000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    start_year: int = Field(default=2027, ge=2000, le=2100)


class ReliabilityRequest(StrictModel):
    shape: Positive = 2.4
    scale_hours: Positive = 45000
    age_hours: NonNegative = 16000
    horizon_hours: Positive = 8760


class DriftRequest(StrictModel):
    expected: list[Positive] = Field(min_length=10, max_length=8760)
    observed: list[NonNegative] = Field(min_length=10, max_length=8760)
    threshold_sigma: Positive = 3

    @model_validator(mode="after")
    def equal_length(self) -> DriftRequest:
        if len(self.expected) != len(self.observed):
            raise ValueError("Expected and observed series must have the same length.")
        return self


class SustainabilityRequest(StrictModel):
    annual_generation_kwh: Positive = 65_000_000
    years: int = Field(default=30, ge=1, le=50)
    degradation_fraction: float = Field(default=0.004, ge=0, lt=1)
    embodied_kgco2e: NonNegative = 38_000_000
    annual_operational_kgco2e: NonNegative = 120_000
    counterfactual_kgco2e_kwh: NonNegative = 0.25
    end_of_life_kgco2e: NonNegative = 1_000_000


class MARequest(StrictModel):
    enterprise_value_eur: Positive = 38_000_000
    annual_ebitda_eur: Positive = 4_100_000
    net_debt_eur: NonNegative = 9_000_000
    years: int = Field(default=20, ge=2, le=40)
    discount_rate: float = Field(default=0.08, ge=0, le=0.4)
    annual_maintenance_capex_eur: NonNegative = 300_000
    annual_degradation: float = Field(default=0.005, ge=0, lt=1)


class CouncilRequest(StrictModel):
    hybrid_run_id: str | None = Field(default=None, min_length=1, max_length=80)
    market: Market = "FR"
    brief: str = Field(default="Review a 5 MW / 10 MWh BTM storage investment for an industrial customer.", min_length=8, max_length=6000)
    mode: Literal["local", "openai"] = "local"
    consent_to_external_processing: bool = False


class PilotUpdate(StrictModel):
    status: Literal["planned", "instrumenting", "running", "validated"]
    evidence_note: str = Field(min_length=8, max_length=1200)
