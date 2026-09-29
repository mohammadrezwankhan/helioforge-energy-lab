# Numerical methodology and model boundaries

**Version 0.2.0 (retained research engines) · screening, not an investment recommendation.** Parameters and outputs include units. The source code and regression tests are the executable specification; the following explains the calculation boundaries.

## 1. BTM storage dispatch

For interval `t`, `c` and `d` are charging and discharging AC power in kW; `g+` and `g-` are grid import/export; `q` is curtailed PV; `s` is battery energy in kWh. `Δt` is hours. Charging and discharging efficiencies each equal the square root of the supplied round-trip efficiency.

```text
energy balance: g+ + PV - q + d = site load + c + g-
SOC transition: s[t+1] = s[t] + η_charge*c[t]*Δt - d[t]*Δt/η_discharge
terminal condition: s[N] = s[0]
SOC limits: capacity*minimum_fraction ≤ s[t] ≤ capacity*maximum_fraction
```

Binary direction variables prevent simultaneous charging/discharging and simultaneous importing/exporting. Power, grid and curtailment limits are explicit. Objective:

```text
Σ Δt * (import_price*g+ - export_price*g- + discharge_wear*d)
+ modeled_period_peak_charge * max(g+)
```

Prices are EUR/kWh internally; plotted tariff values are EUR/MWh. Wear is a marginal EUR/kWh-discharge assumption, not an electrochemical degradation model. Negative import and export prices are allowed. PV curtailment is optimized, not assumed impossible.

The no-battery baseline is a second optimization with identical load, PV, grid, price and curtailment constraints, and zero battery power. This avoids a biased comparator under negative prices or constrained export. Savings equal baseline objective minus storage objective. Percentage savings are not asserted when baseline cost is nonpositive.

The peak tariff applies to the **entire modeled period**, once. It is not automatically a monthly or annual demand charge. The synthetic default is a 24-hour illustration; custom input supports 2–168 equal-duration intervals. It does not handle time zones, daylight-saving changes, annual settlement, demand ratchets, forecast error, reserve commitments or service stacking. Full-year value requires new validated data and an annual billing model. Do not multiply the sample result by 365 and call it a business case.

SciPy's `milp` wraps HiGHS. This release rejects non-optimal/infeasible results rather than fabricating a schedule. Numerical tolerances and solver status must remain visible in any future asynchronous solver implementation.

## 2. Project finance

The default annual gross margin is **an independent assumption**, not dispatch revenue. Before contract expiry, the assumed contracted fraction is protected from the merchant-margin factor; the merchant portion receives that factor. After expiry all margin receives it. This is a stylised exposure model, not a signed contract or counterparty-default simulation.

Gross margin retention decreases with annual degradation; the augmentation year restores a bounded fraction. OPEX escalates at its own rate. Augmentation is deducted in its specified year.

```text
project_CF[0] = -CAPEX
project_CF[t] = adjusted_gross_margin[t] - OPEX[t] - augmentation[t]
NPV = Σ project_CF[t] / (1 + discount_rate)^t
DSCR[t] = CFADS[t] / debt_service[t]   (only where debt service > 0)
```

This conservative screen deducts augmentation before CFADS. It therefore exposes a funding-year covenant problem that might otherwise be hidden in a good project IRR. Real lenders may fund augmentation through reserves, equity or separate facilities; those mechanisms are not modeled here.

Debt uses level annuity service, with a separate zero-interest branch and explicit amortization. No debt means DSCR is null/not applicable, not infinity, zero or a pass. The annual equity cash-flow rows deduct debt service; initial equity required is CAPEX less the initial debt draw. This release does not report an equity IRR. The reported level-payment debt capacity uses the minimum debt-year CFADS divided by the covenant, then discounts that constant service as an annuity. It is not debt sculpting and may be much lower than capital-expenditure-based leverage.

IRR is reported only for conventional cash flows with a single sign change and a root in the implemented search range. Nonconventional cash flows receive null rather than an arbitrarily selected root. Payback is the first interpolated undiscounted crossing; it does not guarantee cash remains positive thereafter.

Finance is pre-tax, nominal and annual. Discount-rate and escalation assumptions must be internally consistent. Excluded: taxes, VAT, working capital, DSRA, fees, salvage, default, refinancing, sculpting and waterfall priorities. Do not mix these finance outputs with the independent constant-money PV or price scenario without an explicit conversion and reconciliation.

## 3. PV economics

Capacity is DC kWp. Year-one generation is capacity × specific yield × (1 − curtailment). Generation then degrades annually. CAPEX is capacity × unit CAPEX; annual OPEX and a scheduled inverter replacement are included. Constant-money assumptions are used.

```text
LCOE (EUR/MWh) = discounted lifecycle costs / discounted generation in MWh
PV NPV = discounted assumed capture-price revenue - discounted lifecycle costs
```

All conversion factors are explicit. Discounted energy is not confused with undiscounted lifetime yield. Panel count rounds upward. Indicative site area divides panel area by ground-coverage ratio, then converts square metres to hectares. This is **not a technical layout**: access roads, buffers, topography, shading, setbacks, geotechnics and electrical design need engineering review. PVGIS is a primary-source link, not an active yield connector.

## 4. Reliability and performance

The drift screen uses the first third of paired observations as a calibration baseline, with median residual and a scaled median absolute deviation. The scale has a small floor to avoid division by zero. This is a robust demonstration, not a trained anomaly classifier, a seasonal weather-normalization pipeline or a fault diagnosis.

For a user-specified Weibull model, survival is `S(t)=exp(-(t/scale)^shape)`. Conditional failure over horizon `h` at current age `a` is `1-S(a+h)/S(a)`, implemented through the exponent difference for stability. Conditional median remaining life solves `S(a+r)/S(a)=0.5`. Parameter fitting, censoring, confidence intervals, fleet heterogeneity and field validation are outside scope.

## 5. Carbon and biodiversity

The screening inventory sums embodied, recurring operational and end-of-life emissions. Lifetime energy includes generation degradation. Intensity is total kgCO₂e divided by lifetime kWh, multiplied by 1,000 for gCO₂e/kWh. Net counterfactual avoidance subtracts lifecycle emissions from counterfactual displaced-generation emissions; negative avoidance is retained.

This is not a certified LCA, regulatory disclosure or marginal-emissions dispatch calculation. Boundaries, supplier inventory, electricity factors, recycling allocation and counterfactual justification require review. Biodiversity is represented by an evidence-oriented pilot workflow, **not an invented universal impact score**.

## 6. Long-term price scenarios

The seeded generator evolves annual price using mean reversion toward a user-defined trending target plus additive Gaussian shocks. It retains negative outcomes. The displayed p10/p50/p90 values are numerical quantiles across simulated paths, not independently calibrated forecast confidence or investor probability-of-exceedance conventions.

Market selection is metadata; it does not fit separate French, German, Spanish, Italian, Dutch or British forecasts. All sample prices are EUR-normalized; British projects require an explicit real GBP tariff and dated FX basis before commercial use. The model excludes fuel/carbon forward curves, supply-stack dispatch, interconnection, demand-weather drivers, hourly shape, capture factors and backtesting.

## 7. Acquisition screen

The M&A engine compares asking enterprise value with a discounted `EBITDA − maintenance CAPEX` proxy. It reports EV/EBITDA, enterprise DCF, valuation gap and implied equity value (`EV − net debt`). Negative implied equity remains negative. Taxes, working capital, growth, terminal value and technology-specific diligence are excluded. This is not a fairness opinion or a substitute for a financial model.

## 8. Model separation is intentional

Storage, finance, PV, carbon and forecast examples are separate screening cases. No hidden automated revenue bridge connects them. The export contains inputs and warnings so a future analyst can construct and test that bridge explicitly. Eight agent opinions cannot replace missing meter data, regulatory eligibility, engineering diligence or finance reconciliation.

The new hybrid hourly engine has a separate specification in [HYBRID_METHODOLOGY.md](HYBRID_METHODOLOGY.md). It is not the battery MILP described above.
