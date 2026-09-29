"""Pre-tax, nominal, unlevered screening plus a separate debt-service schedule.

These are assumption-led scenarios, not project-specific investment recommendations.
"""
from __future__ import annotations

import math

from scipy.optimize import brentq

from helioforge.schemas import FinanceRequest, MARequest, PVRequest


def npv(rate: float, cashflows: list[float]) -> float:
    if rate <= -1:
        raise ValueError("Discount rate must exceed -100%.")
    return math.fsum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def conventional_irr(cashflows: list[float]) -> float | None:
    """Return the unique conventional IRR, or None; never pick an arbitrary root."""
    signs = [1 if x > 0 else -1 for x in cashflows if abs(x) > 1e-9]
    changes = sum(a != b for a, b in zip(signs, signs[1:]))
    if changes != 1 or cashflows[0] >= 0 or not any(cf > 0 for cf in cashflows[1:]):
        return None
    left, right = -.95, 1.0
    while npv(right, cashflows) > 0 and right < 1024:
        right *= 2
    if npv(left, cashflows) * npv(right, cashflows) >= 0:
        return None
    return float(brentq(lambda r: npv(r, cashflows), left, right, xtol=1e-11))


def annuity(principal: float, rate: float, years: int) -> float:
    if not principal:
        return 0.0
    return principal / years if rate == 0 else principal * rate / (1 - (1 + rate) ** -years)


def calculate_finance(p: FinanceRequest) -> dict:
    rows, cashflows = [], [-p.capex_eur]
    raw_dscrs: list[float] = []
    debt = p.capex_eur * p.debt_fraction
    payment = annuity(debt, p.debt_interest_rate, p.debt_tenor_years)
    balance, running, payback = debt, -p.capex_eur, None
    restoration = 0.0
    for year in range(1, p.years + 1):
        if p.augmentation_year == year:
            restoration = p.augmentation_retention_restore
        retention = min(1.0, (1-p.annual_margin_degradation)**(year-1) +
                        restoration * (1-p.annual_margin_degradation)**max(0, year-(p.augmentation_year or year)))
        contracted = p.contracted_fraction if year <= p.contract_years else 0
        # Contract fraction protects that fraction of the gross-margin assumption from merchant haircut.
        gross = p.annual_gross_margin_eur * retention * (contracted + (1-contracted)*p.merchant_margin_factor)
        opex = p.annual_opex_eur * (1+p.escalation_rate)**(year-1)
        augmentation = p.augmentation_cost_eur if year == p.augmentation_year else 0
        cfads = gross - opex - augmentation  # Conservative: augmentation paid before debt service.
        service = payment if year <= p.debt_tenor_years else 0
        interest = balance*p.debt_interest_rate if service else 0
        principal = min(balance, max(0, service-interest))
        balance = max(0, balance-principal)
        old_running = running
        running += cfads
        if payback is None and old_running < 0 <= running and cfads > 0:
            payback = year-1 + (-old_running/cfads)
        cashflows.append(cfads)
        if service:
            raw_dscrs.append(cfads/service)
        rows.append({"year": year, "gross_margin_eur": round(gross, 2), "opex_eur": round(opex, 2),
                     "augmentation_eur": augmentation, "cfads_eur": round(cfads, 2),
                     "debt_service_eur": round(service, 2), "interest_eur": round(interest, 2),
                     "debt_balance_eur": round(balance, 2), "equity_cashflow_eur": round(cfads-service, 2),
                     "dscr": round(cfads/service, 6) if service else None,
                     "cumulative_eur": round(running, 2), "contracted_fraction": contracted})
    irr = conventional_irr(cashflows)
    dscrs = [row["dscr"] for row in rows if row["dscr"] is not None]
    # Level-debt-service sizing, NOT sculpting. Worst year caps the annuity payment.
    min_cfads = max(0, min(r["cfads_eur"] for r in rows[:p.debt_tenor_years]))
    allowable_payment = min_cfads / p.minimum_dscr
    debt_capacity = allowable_payment / annuity(1, p.debt_interest_rate, p.debt_tenor_years)
    warnings = ["Pre-tax nominal screening; no VAT, working capital, DSRA, inflation-linked revenue or terminal value.",
                "Gross margin is an independent user assumption, not the daily dispatch result annualized.",
                "Augmentation is deducted before debt service; debt is level-payment, not sculpted."]
    if irr is None:
        warnings.append("IRR unavailable: non-conventional cash flows or no unique bracketed conventional root; use NPV.")
    return {"model": "project-finance-v1", "npv_eur": round(npv(p.discount_rate, cashflows), 2),
            "irr_pct": round(irr*100, 3) if irr is not None else None,
            "payback_years": round(payback, 2) if payback is not None else None,
            "minimum_dscr": min(dscrs) if dscrs else None,
            "dscr_covenant": p.minimum_dscr,
            "covenant_pass": all(x >= p.minimum_dscr for x in raw_dscrs) if raw_dscrs else None,
            "level_payment_debt_capacity_eur": round(min(p.capex_eur, debt_capacity), 2),
            "capex_eur": p.capex_eur, "rows": rows, "warnings": warnings}


def calculate_pv(p: PVRequest) -> dict:
    capex = p.capacity_kwp*p.capex_eur_kwp
    costs, energy, cfs, rows = capex, 0.0, [-capex], []
    for y in range(1, p.years+1):
        generation = p.capacity_kwp*p.specific_yield_kwh_kwp*(1-p.curtailment_fraction)*(1-p.degradation_fraction)**(y-1)
        opex = p.capacity_kwp*p.opex_eur_kwp_year
        replacement = p.capacity_kwp*p.inverter_replacement_eur_kwp if y == p.inverter_replacement_year else 0
        revenue = generation/1000*p.capture_price_eur_mwh
        costs += (opex+replacement)/(1+p.discount_rate)**y
        energy += generation/(1+p.discount_rate)**y
        cfs.append(revenue-opex-replacement)
        rows.append({"year": y, "generation_mwh": round(generation/1000, 2),
                     "cashflow_eur": round(cfs[-1], 2), "replacement_eur": replacement})
    panels = math.ceil(p.capacity_kwp/p.panel_kwp)
    area = panels*p.panel_area_m2/p.ground_coverage_ratio
    return {"model": "discounted-pv-v1", "capex_eur": capex, "lcoe_eur_mwh": round(costs/energy*1000, 3),
            "npv_eur": round(npv(p.discount_rate, cfs), 2), "first_year_generation_mwh": rows[0]["generation_mwh"],
            "panel_count": panels, "indicative_land_ha": round(area/10000, 2),
            "capture_price_eur_mwh": p.capture_price_eur_mwh, "rows": rows,
            "warnings": ["Yield and capture price are user assumptions, not site-specific PVGIS results.",
                         "Constant money basis; no escalation. Discount rate must be consistent with that basis.",
                         "Land-area estimate excludes setbacks, terrain, roads and interconnection; not a technical layout."]}


def screen_acquisition(p: MARequest) -> dict:
    cfs = [-p.enterprise_value_eur] + [p.annual_ebitda_eur*(1-p.annual_degradation)**(y-1)
                                    - p.annual_maintenance_capex_eur for y in range(1, p.years+1)]
    irr = conventional_irr(cfs)
    dcf_value = npv(p.discount_rate, [0, *cfs[1:]])
    return {"model": "ma-screen-v1", "ev_ebitda": round(p.enterprise_value_eur/p.annual_ebitda_eur, 2),
            "implied_equity_value_eur": p.enterprise_value_eur-p.net_debt_eur,
            "screening_dcf_eur": round(dcf_value, 2), "valuation_gap_eur": round(dcf_value-p.enterprise_value_eur, 2),
            "unlevered_irr_pct": round(irr*100, 3) if irr is not None else None,
            "warnings": ["Pre-tax enterprise screening only: EBITDA less maintenance capex is a proxy, not full FCFF.",
                         "No tax, working capital, terminal value or technology-specific production model.",
                         "Negative implied equity is reported, not silently floored at zero."]}
