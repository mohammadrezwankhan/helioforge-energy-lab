"""Supporting annual-data, sensitivity and reserve tools with explicit scope."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Annotated

import numpy as np
from pydantic import Field, model_validator

from helioforge.engines.finance import calculate_pv
from helioforge.schemas import PVRequest, StrictModel

PRICE = [0.10] * 6 + [0.18] * 3 + [0.12] * 7 + [0.30] * 5 + [0.14] * 3
Power = Annotated[float, Field(ge=0, le=1e6, allow_inf_nan=False)]
Tariff = Annotated[float, Field(ge=0, le=3, allow_inf_nan=False)]


class Annual(StrictModel):
    capacity_kwh: float = Field(default=10000, ge=1, le=1e6)
    power_kw: float = Field(default=5000, ge=1, le=1e6)
    pv_kwp: float = Field(default=5900, ge=0, le=1e6)
    base_load_kw: float = Field(default=3000, ge=0, le=1e6)
    efficiency: float = Field(default=0.9, ge=0.5, le=1)
    wear: float = Field(default=0.015, ge=0, le=1)
    monthly_peak: float = Field(default=0, ge=0, le=100)
    export_price: float = Field(default=0.04, ge=0, le=3)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    tariff: list[Tariff] = Field(default=PRICE, min_length=24, max_length=24)
    hourly_load_kw: list[Power] = Field(default_factory=list, max_length=8760)
    hourly_pv_kw: list[Power] = Field(default_factory=list, max_length=8760)

    @model_validator(mode="after")
    def consistent(self):
        if self.export_price > min(self.tariff):
            raise ValueError("This rule policy requires import prices at least as high as export prices.")
        if any((self.hourly_load_kw, self.hourly_pv_kw)) and not (
            len(self.hourly_load_kw) == len(self.hourly_pv_kw) == 8760
        ):
            raise ValueError("Provide both complete 8760-hour load and PV arrays, or neither.")
        return self


class Sensitivity(StrictModel):
    capex_eur_kwp: float = Field(default=650, ge=100, le=5000)
    yield_kwh_kwp: float = Field(default=1350, ge=400, le=2200)
    discount: float = Field(default=0.07, ge=0, le=0.4)
    opex: float = Field(default=12, ge=0, le=100)


class Reserve(StrictModel):
    cost_eur: float = Field(default=1750000, ge=0, le=1e10)
    inflation: float = Field(default=0.02, ge=0, le=0.2)
    fund_return: float = Field(default=0.03, ge=0, le=0.2)
    years: int = Field(default=15, ge=1, le=50)


def f(name, label, default, lo, hi, step=1, unit=""):
    return dict(name=name, label=label, default=default, min=lo, max=hi, step=step, unit=unit)


STUDIES = [
    dict(
        id="storage-annual",
        page="storage",
        title="8760-hour dispatch and tariff builder",
        kind="annual",
        summary="A complete seasonal year or supplied hourly series, with a transparent tariff policy and monthly billing.",
        fields=[
            f("capacity_kwh", "Battery energy", 10000, 1, 1e6, 100, "kWh"),
            f("power_kw", "Battery power", 5000, 1, 1e6, 100, "kW"),
            f("pv_kwp", "Synthetic PV capacity", 5900, 0, 1e6, 100, "kWp"),
            f("base_load_kw", "Synthetic base load", 3000, 0, 1e6, 100, "kW"),
            f("efficiency", "Round-trip efficiency", 0.9, 0.5, 1, 0.01),
            f("wear", "Discharge wear", 0.015, 0, 1, 0.001, "EUR/kWh"),
            f("monthly_peak", "Monthly peak charge", 0, 0, 100, 0.1, "EUR/kW"),
            f("export_price", "Export tariff", 0.04, 0, 3, 0.01, "EUR/kWh"),
            f("seed", "Weather seed", 42, 0, 2**32 - 1),
        ],
        data_fields=[
            dict(name="tariff", label="24 hourly import tariffs (EUR/kWh)", default=PRICE),
            dict(name="hourly_load_kw", label="Optional full-year load (8760 kW values)", default=[]),
            dict(name="hourly_pv_kw", label="Optional full-year PV (8760 kW values)", default=[]),
        ],
        equations=[
            "SOC[t+1] = SOC[t] + sqrt(efficiency)*charge - discharge/sqrt(efficiency)",
            "Monthly demand cost = sum(monthly maximum import kW * monthly tariff)",
            "Both initial and terminal SOC = 50%; usable range = 10–90%.",
        ],
        limitations=[
            "Explicit non-leap 8760-hour calendar; no DST. Synthetic seasonal weather is not site-calibrated.",
            "Transparent tariff-threshold policy, NOT the short-horizon MILP or a globally optimal annual solution.",
            "Unconstrained grid connection; no reserve services, outages, demand ratchets, taxes or fixed fees.",
            "No daily result is multiplied by 365. Annual totals sum every generated or supplied hour.",
        ],
        sources=[
            dict(title="NREL REopt documentation and model boundary", url="https://reopt.nrel.gov/tool")
        ],
    ),
    dict(
        id="pv-sensitivity",
        page="pv",
        title="LCOE contour sensitivity",
        kind="heatmap",
        summary="A 9 × 9 CAPEX and yield surface evaluated by the existing discounted PV engine.",
        fields=[
            f("capex_eur_kwp", "Central CAPEX", 650, 100, 5000, 10, "EUR/kWp"),
            f("yield_kwh_kwp", "Central yield", 1350, 400, 2200, 10, "kWh/kWp"),
            f("discount", "Real discount rate", 0.07, 0, 0.4, 0.01),
            f("opex", "Annual OPEX", 12, 0, 100, 1, "EUR/kWp"),
        ],
        data_fields=[],
        equations=["LCOE = discounted lifecycle costs / discounted lifetime MWh"],
        limitations=[
            "Constant money; the parent PV engine retains its 30-year life and year-15 replacement assumptions."
        ],
        sources=[
            dict(
                title="NREL simple LCOE documentation",
                url="https://www.nrel.gov/analysis/tech-lcoe-documentation.html",
            )
        ],
    ),
    dict(
        id="pv-reserve",
        page="pv",
        title="Inverter repowering reserve",
        kind="waterfall",
        summary="Inflation-linked future replacement cost and equal end-of-year reserve contributions.",
        fields=[
            f("cost_eur", "Replacement cost today", 1750000, 0, 1e10, 1000, "EUR"),
            f("inflation", "Cost inflation", 0.02, 0, 0.2, 0.005),
            f("fund_return", "Nominal fund return", 0.03, 0, 0.2, 0.005),
            f("years", "Replacement year", 15, 1, 50),
        ],
        data_fields=[],
        equations=[
            "Future cost = present cost * (1+inflation)^years",
            "Annual deposit = future cost * return / ((1+return)^years - 1); zero return: cost/years",
        ],
        limitations=[
            "Constant annual assumptions; end-of-year contributions, no tax, fees or investment-return guarantee.",
            "First-party algebraic convention; the source reference is not independent validation or a forecast of investment returns."
        ],
        sources=[{"title": "First-party HelioForge reserve implementation and declared equations",
                  "url": "https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/74d6730e38323b69c180d7f4b4945d11010203f3/apps/api/helioforge/engines/toolkit_studies.py"}],
    ),
]


def _bounded_battery_step(soc: float, charge: float, discharge: float, eta: float,
                          floor: float, ceiling: float) -> tuple[float, float, float]:
    """Project stored energy, then reconstruct the nonnegative AC-side flows."""
    end = min(ceiling, max(floor, soc + eta * charge - discharge / eta))
    delta = end - soc
    return max(delta, 0.0) / eta, max(-delta, 0.0) * eta, end


def annual(p: Annual) -> dict:
    rng = np.random.default_rng(p.seed)
    t = np.arange(8760)
    day = t // 24
    hour = t % 24
    if p.hourly_load_kw:
        load = np.array(p.hourly_load_kw)
        pv = np.array(p.hourly_pv_kw)
    else:
        seasonal = np.cos(2 * np.pi * (day - 172) / 365)
        length = 12 + 4 * seasonal
        sun = np.maximum(0, np.sin(np.pi * (hour - (12 - length / 2)) / length))
        sun[(hour < 12 - length / 2) | (hour > 12 + length / 2)] = 0
        # Distinct daily cloud draws and seasonal daylight; never tile a demonstration day.
        cloud = np.repeat(rng.uniform(0.35, 1, 365), 24)
        pv = p.pv_kwp * sun * cloud * (0.8 + 0.15 * seasonal)
        load = p.base_load_kw * (
            1 + 0.15 * np.cos(2 * np.pi * day / 365) + 0.2 * np.exp(-(((hour - 18) / 4) ** 2))
        )
    eta = math.sqrt(p.efficiency)
    initial = 0.5 * p.capacity_kwh
    soc = initial
    low, high = np.quantile(p.tariff, [0.25, 0.75])
    rows = []
    base_cost = cost = 0.0
    base_peaks = np.zeros(12)
    peaks = np.zeros(12)
    monthly = np.zeros(12)
    for t in range(8760):
        stamp = datetime(2025, 1, 1) + timedelta(hours=t)
        m = stamp.month - 1
        price = p.tariff[t % 24]
        net = float(load[t] - pv[t])
        start = soc
        remaining = 8759 - t
        floor = max(0.1 * p.capacity_kwh, initial - remaining * p.power_kw * eta)
        ceiling = min(0.9 * p.capacity_kwh, initial + remaining * p.power_kw / eta)
        charge = discharge = 0.0
        if net < 0 or price <= low:
            charge = min(
                p.power_kw, max(0, (ceiling - soc) / eta), max(0, -net) if price > low else p.power_kw
            )
        elif price >= high:
            discharge = min(p.power_kw, max(0, (soc - floor) * eta), max(0, net))
        charge, discharge, soc = _bounded_battery_step(soc, charge, discharge, eta, floor, ceiling)
        grid = net + charge - discharge
        imp = max(0, grid)
        exp = max(0, -grid)
        base_imp = max(0, net)
        base_exp = max(0, -net)
        period = imp * price - exp * p.export_price + discharge * p.wear
        cost += period
        base_cost += base_imp * price - base_exp * p.export_price
        monthly[m] += period
        peaks[m] = max(peaks[m], imp)
        base_peaks[m] = max(base_peaks[m], base_imp)
        rows.append(
            dict(
                timestamp=stamp.isoformat(),
                load_kw=float(load[t]),
                pv_kw=float(pv[t]),
                charge_kw=charge,
                discharge_kw=discharge,
                grid_import_kw=imp,
                grid_export_kw=exp,
                soc_start_kwh=start,
                soc_end_kwh=soc,
                tariff_eur_kwh=price,
                cost_eur=period,
            )
        )
    cost += float(peaks.sum()) * p.monthly_peak
    base_cost += float(base_peaks.sum()) * p.monthly_peak
    return dict(
        metrics=[
            dict(label="Annual policy cost", value=cost, unit="EUR"),
            dict(label="No-storage cost", value=base_cost, unit="EUR"),
            dict(label="Policy savings (can be negative)", value=base_cost - cost, unit="EUR"),
            dict(label="Terminal battery energy", value=soc, unit="kWh"),
        ],
        series=[
            dict(
                name="Monthly policy cost incl. demand charges",
                x_label="Month",
                y_unit="EUR",
                x=list(range(1, 13)),
                y=(monthly + peaks * p.monthly_peak).tolist(),
            ),
            dict(
                name="Battery energy",
                x_label="Hour",
                y_unit="kWh",
                x=list(range(8760)),
                y=[r["soc_end_kwh"] for r in rows],
            ),
        ],
        table=rows,
        details={"initial_soc_kwh": initial, "terminal_soc_kwh": soc, "annual_grid_model": "unconstrained"},
        warnings=[
            "Rule-based policy may cost more than the no-storage comparator; no savings guarantee.",
            "This annual synthetic scenario is separate from the original 24-hour MILP.",
        ],
    )


def run(study_id: str, inputs: dict) -> dict:
    if study_id == "storage-annual":
        return annual(Annual.model_validate(inputs))
    if study_id == "pv-reserve":
        p = Reserve.model_validate(inputs)
        target = p.cost_eur * (1 + p.inflation) ** p.years
        contribution = (
            target / p.years
            if p.fund_return == 0
            else target * p.fund_return / math.expm1(p.years * math.log1p(p.fund_return))
        )
        rows = []
        balance = 0
        for year in range(1, p.years + 1):
            interest = balance * p.fund_return
            balance += interest + contribution
            rows.append(
                dict(year=year, contribution_eur=contribution, interest_eur=interest, balance_eur=balance)
            )
        return dict(
            metrics=[
                dict(label="Inflated replacement cost", value=target, unit="EUR"),
                dict(label="Annual contribution", value=contribution, unit="EUR"),
            ],
            series=[
                dict(
                    name="Reserve balance",
                    x_label="Year",
                    y_unit="EUR",
                    x=[r["year"] for r in rows],
                    y=[r["balance_eur"] for r in rows],
                )
            ],
            table=rows,
            warnings=[],
        )
    if study_id == "pv-sensitivity":
        p = Sensitivity.model_validate(inputs)
        rows = []
        for capex in np.linspace(p.capex_eur_kwp * 0.7, p.capex_eur_kwp * 1.3, 9):
            for yield_ in np.linspace(p.yield_kwh_kwp * 0.85, p.yield_kwh_kwp * 1.15, 9):
                result = calculate_pv(
                    PVRequest(
                        capex_eur_kwp=float(capex),
                        specific_yield_kwh_kwp=float(yield_),
                        discount_rate=p.discount,
                        opex_eur_kwp_year=p.opex,
                    )
                )
                rows.append(
                    dict(
                        capex_eur_kwp=float(capex),
                        yield_kwh_kwp=float(yield_),
                        lcoe_eur_mwh=result["lcoe_eur_mwh"],
                    )
                )
        return dict(
            metrics=[
                dict(label="Lowest LCOE", value=min(r["lcoe_eur_mwh"] for r in rows), unit="EUR/MWh"),
                dict(label="Highest LCOE", value=max(r["lcoe_eur_mwh"] for r in rows), unit="EUR/MWh"),
            ],
            series=[
                dict(
                    name="LCOE at central CAPEX",
                    x_label="Yield kWh/kWp",
                    y_unit="EUR/MWh",
                    x=[r["yield_kwh_kwp"] for r in rows[36:45]],
                    y=[r["lcoe_eur_mwh"] for r in rows[36:45]],
                )
            ],
            table=rows,
            warnings=[],
        )
    raise ValueError("Unknown supporting study.")
