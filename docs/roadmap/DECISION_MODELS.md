# Decision studies: model notes and limits

These twelve experiments are implemented in `apps/api/helioforge/engines/decision_studies.py`. They share the experimental-study contract in [CONTRACT.md](CONTRACT.md): each has a strict bounded Pydantic input, a catalogue entry with defaults and equations, and a result with `metrics`, `series`, `table`, `details` and `warnings`. Unknown inputs, fractional integer fields, non-finite values, oversized arrays and out-of-range magnitudes are rejected. Seeded studies create a fresh NumPy generator per call; the caller's input object is not modified.

The values in the defaults are synthetic. They demonstrate the arithmetic and output shape. Source links provide context for definitions or methods; they do not calibrate these parameters, verify a project, establish eligibility or support an investment recommendation. No model calls an external data provider.

## Overview

### `overview-weather`

For each year, the model combines one shared standard-normal shock and an asset-specific standard-normal shock:

```text
z[i,t] = sqrt(common_share) × common[t] + sqrt(1 − common_share) × independent[i,t]
loss_fraction[i,t] = min(1, max(0, −z[i,t]) × sensitivity[i])
portfolio_stress[t] = Σ(generation[i] × loss_fraction[i,t]) / Σ(generation[i])
```

The six supplied fictional assets make common downside years visible against their different annual generation and sensitivity inputs. The configured common-shock fraction is the theoretical pairwise correlation of standardized shocks; the sample horizon is 1–40 years. This is a standardized correlated stress proxy, not weather data, a yield model, an outage probability or a reliability calculation. NREL's [solar integration data and studies](https://www.nrel.gov/grid/solar-power-data.html) are contextual references only; the study does not retrieve them.

### `overview-merit`

Each route's net value is its supplied value less supplied variable cost. The weighted value is the weighted sum of bilateral, spot and balancing net values; the three route weights must sum to one. The result is a per-MWh matrix, with no dispatch, opportunity cost, balancing-market qualification, losses, fees or realized volume. The [EIA electricity markets overview](https://www.eia.gov/energyexplained/electricity/electricity-markets.php) gives general market context; no U.S. market rule is imported into the calculation.

### `overview-carbon`

For the selected first `sample_hours` of the supplied arrays:

```text
hourly = Σ(generation[h] × marginal_factor[h])
static = Σ(generation[h]) × static_factor
```

Both totals cover exactly the same supplied sample; no day is annualized. No carbon credits are minted or deducted. Factors are user inputs, not an active marginal-emissions model. The [UNFCCC electricity-system emissions methodology](https://cdm.unfccc.int/Reference/catalogue/document?doc_id=000001719) is a reference for emission-factor accounting concepts, not evidence that the supplied factors are valid for any project.

## Markets

### `markets-capture`

The capture-price sensitivity adjusts each supplied interval linearly:

```text
adjusted_price[t] = spot_price[t] − slope × (penetration − reference_penetration) × exposure[t]
capture_price = Σ(generation[t] × adjusted_price[t]) / Σ(generation[t])
```

It reports a null capture price when total generation is zero. The slope is a user-set sensitivity, not a fitted cannibalization curve. Hirth's [market-value study](https://doi.org/10.1016/j.eneco.2013.02.004) motivates measuring generation-weighted value and penetration effects; this implementation does not reproduce its market model or empirical estimates.

### `markets-negative`

The supplied equally spaced 15-minute prices are negative when they are below zero and at or below the configured threshold. A suspension-triggering run is a contiguous negative sequence at least as long as the configured duration. The country code is only a label. The country setting, threshold and duration are explicitly marked **UNVERIFIED user hypotheses**; the model makes no statement about current subsidy, settlement, curtailment or legal rules. [Regulation (EU) 2019/943](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02019R0943-20220623) is linked as a primary market-law reference, not used to encode a jurisdiction rule.

### `markets-interconnection`

For zone `i`, supplied demand is served by a quadratic cost curve `C_i(q)=a_i q + 0.5 b_i q²`, with positive slope `b_i`. A positive `f` sends power from A to B. The model minimizes `C_A(d_A+f)+C_B(d_B−f)` over:

```text
−min(capacity, demand_A) ≤ f ≤ min(capacity, demand_B)
f* = clip((MC_B(d_B) − MC_A(d_A)) / (b_A + b_B), lower_bound, upper_bound)
```

The marginal-cost-spread solution is bounded by capacity and nonnegative zone supply. Zero capacity yields zero flow. This is a one-link, two-zone convex screen, not an AC network, flow-based market-coupling algorithm, or security-constrained dispatch. ENTSO-E's [Core day-ahead coupling description](https://www.entsoe.eu/bites/ccr-core/day-ahead/) provides context for capacity-constrained cross-zonal exchange, but its actual multi-zone constraints are not modeled here.

## Forecast scenarios

### `forecast-regimes`

Each path starts from a user-provided categorical distribution over three states. Each year, state `s` transitions according to row `P[s, :]`, then price is drawn from the selected state's normal distribution. Transition rows and initial probabilities must sum to one. The states are named normal, scarcity and oversupply for presentation only. This is the standard Markov-switching construction associated with Hamilton's [regime-switching time-series paper](https://doi.org/10.2307/1912559), reduced to annual synthetic scenarios. It is neither calibrated nor a price forecast.

### `forecast-commodities`

The user supplies starting gas, carbon and power prices, annual log drifts, volatilities and a symmetric 3×3 correlation matrix. The matrix must have unit diagonal and be positive semidefinite. An eigendecomposition supplies a square root even for a singular PSD matrix. For independent standard-normal vector `ε` and correlation root `L`:

```text
Z = L ε
P[j,t] = P[j,t−1] × exp((μ[j] − 0.5 σ[j]²) + σ[j] Z[j,t])
```

This gives a seeded correlated geometric random walk. It does not fit a cointegrating/error-correction relation, use market forward curves, convert currencies or infer fuel dispatch. NumPy's [multivariate-normal sampling reference](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.multivariate_normal.html) is linked for the correlated-normal simulation concept; this implementation factors the supplied PSD matrix directly.

### `forecast-tail`

The PPA study simulates annual spot-price deviations from the fixed strike as a cumulative arithmetic random walk. For a selected year, signed buyer settlement loss is:

```text
loss[path] = (spot[path] − strike) × volume
VaRα = empirical α quantile of loss
CVaRα = mean of the largest ceil((1 − α) × path_count) losses
```

Positive values mean settlement cost above strike; negative values mean a settlement benefit. It exports each seeded path and a histogram of the selected year's spot prices. VaR and CVaR use a loss convention, and CVaR is the average of the empirical upper tail. Rockafellar and Uryasev's [CVaR paper](https://doi.org/10.21314/JOR.2000.038) is the primary method reference. The simulation is not a calibrated risk estimate, a complete PPA contract, or a probability guarantee.

## Investment screens

### `investment-sculpt`

The model calls the existing `FinanceRequest` and `calculate_finance` implementation. It reuses that engine's nominal pre-tax project rows and CFADS, preserving its augmentation deduction and project IRR convention. The study's target DSCR is applied to both its comparison annuity capacity and sculpt limit. Debt is capped by requested debt and CAPEX.

For each year in the requested tenor, target service is `A[t]=max(0, CFADS[t])/target_DSCR`. A candidate opening balance `B[t−1]` incurs interest `I[t]=r×B[t−1]`. The proposed schedule uses at most `A[t]` and at most the full payoff amount `B[t−1]+I[t]`. It is infeasible while debt remains if CFADS is nonpositive or target service cannot cover interest. For a feasible period:

```text
S[t] = min(A[t], B[t−1] + I[t])
principal[t] = S[t] − I[t] ≥ 0
B[t] = B[t−1] − principal[t] = B[t−1] + I[t] − S[t]
```

The capacity search bisects initial principal between zero and CAPEX. For a fixed service-cap sequence, each recurrence `B[t]=max(0,(1+r)B[t−1]−A[t])` is nondecreasing in initial debt; the conditions that service covers interest and that the terminal balance is zero therefore bound a feasible interval starting at zero. Bisection returns its largest feasible debt to numerical tolerance. A debt request above that limit is shown as infeasible; the output schedule is for the feasible sized amount and labels negative amortization as disallowed. The theoretical discounted sum of target service is shown separately because it can overstate debt when an intermediate service cap is below interest.

NREL's [System Advisor Model help](https://sam.nrel.gov/images/web_page_files/sam-help-2025-4-16.pdf) describes DSCR-based debt sizing from annual available cash flow and variable sculpted debt service. This implementation uses a stricter explicit feasibility screen; it is not SAM's full financial model. Fees, taxes, reserves, separate augmentation funding and covenant documents remain outside scope.

### `investment-tranches`

Annual contracted floor, merchant price, MWh and OPEX are supplied by the user. Within the configured floor term, contracted CFADS is `floor × contracted MWh − OPEX`. The comparison cases add zero, the configured merchant fraction, or all of `merchant price × merchant MWh`, then subtract OPEX. Negative prices and CFADS remain visible. Each case is sized with the same target-service and no-negative-amortization algorithm described above. For each CFADS series, the search upper bound is the sum of its positive target-DSCR service limits; with nonnegative interest, initial debt cannot exceed that cumulative service. This data-derived bound avoids truncating valid capacities at an arbitrary fixed amount. The floor is a hypothetical PPA exposure input, not a signed contract or regulatory eligibility setting; expired contracted MWh are not automatically reassigned to merchant exposure.

### `investment-waterfall`

The default convention is one LP contribution at time zero and one exit distribution after the configured number of years. The waterfall pays the LP's contributed capital first, then its compounded preferred return `capital×((1+rate)^years−1)`. Catch-up distributions split at the configured share until the sponsor's cumulative profit share equals the post-catch-up promote. If `p` is sponsor promote, `c` is the sponsor's catch-up share, and `R` is LP preferred return paid, the required total catch-up is `pR/(c−p)`, allocated `c` to sponsor and `1−c` to LP. Remaining proceeds split `1−p` to LP and `p` to sponsor. The validator requires `c>p`; if the pool is insufficient, each tier receives only the remaining cash. The exact, unrounded LP plus sponsor allocations are checked against the distribution pool; displayed amounts are rounded to cents. This convention omits interim returns, sponsor capital, tax, clawback and legal partnership definitions.

## Output and evidence limits

Every result is JSON-serialized with `allow_nan=False` before it leaves the engine. Null capture price and null DSCR are used when the quantity is undefined or no debt service is present. A zero or negative CFADS is retained as data and cannot be silently treated as debt capacity. Study outputs are numerical screens only; neither a successful run nor a SHA-256 evidence hash would establish factual accuracy, a legal conclusion, lender acceptance or investment suitability.
