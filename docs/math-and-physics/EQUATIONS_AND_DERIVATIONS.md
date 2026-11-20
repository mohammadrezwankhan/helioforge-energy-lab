# Equations, algorithms and derivations

The equations below describe the pinned implementation, not a calibrated site model. Power is normally kW, storage energy kWh, dispatch time hours and money EUR. The physical/control studies deliberately switch to SI seconds, amperes, volts, henries and farads. Every study has its own boundary; the [59-study atlas](STUDY_MODEL_ATLAS.md) maps those boundaries and schema/handler source locations.

## 1. Short-horizon storage MILP

Let $c_t, d_t, g_t^+, g_t^-, q_t$ be nonnegative charge, discharge, import, export and PV curtailment powers. Let $s_t$ be stored energy, $L_t$ load, $P_t$ available PV, $\Delta t$ interval hours and $\eta=\sqrt{\eta_{rt}}$. Conservation gives

$$g_t^+-g_t^-+d_t-c_t-q_t=L_t-P_t,$$
$$s_{t+1}=s_t+\eta c_t\Delta t-d_t\Delta t/\eta.$$

The first equation moves all controllable flows to the left; the second applies losses on opposite sides of the stored-energy boundary. Both use battery-terminal powers. Equal charging/discharging efficiencies multiply to the input round-trip efficiency. Initial and terminal energy are fixed to the same declared fraction of capacity. Separate binary variables prohibit simultaneous battery charge/discharge and simultaneous grid import/export, including under negative tariffs. A peak variable $z$ bounds every import power. [apps/api/helioforge/engines/storage.py:107–165](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/storage.py#L107-L165).

The objective is

$$\min\sum_t\Delta t\,[p_t^{buy}g_t^+-p_t^{sell}g_t^-+w d_t]+k_{peak}z.$$

Here $w$ is EUR/kWh discharged and $k_{peak}$ is EUR/kW **for the represented period**. The model contains $8n+2$ variables and $7n$ explicit constraint rows, with bounds supplying endpoint/box restrictions. SciPy `milp` uses a 10-second limit and relative MIP gap target $10^{-7}$. The no-battery case is independently solved with the same load/PV/tariffs/grid/curtailment/peak rules. A positive difference is therefore relative to that comparator and horizon, not automatic annual profit. [apps/api/helioforge/engines/storage.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/storage.py). SciPy's [MILP API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) supplies solver terminology; the repository source determines its actual options.

Power/SOC rows are rounded for output, so checks of displayed rows need their documented tolerances. The existing tests use tolerances of approximately 0.003 kW for rounded balance, 0.004 kWh for rounded recurrence and 0.002 kWh for the terminal endpoint; do not interpret rounded rows as exact internal optimizer residuals. [apps/api/tests/test_engines.py:45–65](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/tests/test_engines.py#L45-L65). The [two-interval lab](../developer/WORKED_EXAMPLES_AND_LABS.md) has a hand-checkable EUR 0.40 baseline and EUR 0.20 optimized cost.

## 2. Hybrid hourly energy screen

The hybrid engine uses a one-hour greedy recurrence, not a cost MILP. For hour $h=t\bmod24$, its synthetic profiles include

$$L_t=L_0\,[0.78+0.18\sin^2((h-8)\pi/12)+0.25\,\mathbf1_{17\le h\le20}]\, f_L,$$
$$P_{PV, t}=P_{PV,0}\max(0,\sin((h-6)\pi/12))\, f_{PV},$$
$$P_{wind, t}=P_{wind,0}[0.38+0.16\sin(0.43h+1)]\, f_W,\qquad P_{hydro, t}=0.6P_{hydro,0}f_H.$$

The code evaluates topology, outage and voltage-reference availability before dispatch. It serves renewable power directly, charges surplus, discharges storage, imports available grid power, dispatches an available generator, then records unmet target load. Negative export value leads to curtailment. It does not charge from the grid for arbitrage. Outage indexes are absolute simulation hours, not a daily repeating outage. Only the applicable off-grid/islandable topologies can remain energized without the grid; grid-following labels alone do not supply a voltage reference. [apps/api/helioforge/engines/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/hybrid.py), [apps/api/helioforge/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/hybrid.py).

SOC uses the same $\sqrt{\eta_{rt}}$ energy convention, but the terminal SOC is **unconstrained**. Aging modifies effective capacity; a trip can remove battery power without deleting stored energy. Served target load, scheduled noncritical shedding, unserved load and critical unserved load have different meanings. Variable cost covers import minus export plus generator fuel proxy; it excludes investment, fixed costs and a full lifetime degradation valuation. Report stored-energy change alongside any period-cost comparison. The 19/17 architecture boundary remains in force.

## 3. Native browser Terminal

Terminal deliberately uses a different synthetic demand shape:

$$L_h=L_0[0.9+0.1\cos((h-19)2\pi/24)],$$
$$P_h=\begin{cases}0,&h\le6\text{ or }h\ge18,\\P_0\sin((h-6)\pi/12),&6<h<18.\end{cases}$$

It runs 24 direct greedy hourly steps with PV, battery and grid only. The residual convention is

$$r_{bus}=g^++P+d+u-L-c-g^--q,$$
$$r_{SOC}=s_{t+1}-s_t-\eta c+d/\eta.$$

The term $u$ represents **unserved demand** in the accounting equation; it is not a physical power source. `CONVERGED` means the direct step sequence completed; there is no iterative optimization convergence estimate. End-of-day energy is free. The default run starts at 10 kWh and ends at 2 kWh, so its EUR 15.606424 period cost includes consuming 8 kWh of initial stored energy. [apps/web/src/terminal-engine.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/terminal-engine.ts), [apps/api/helioforge/engines/terminal.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/terminal.py).

For a metric $Y$ and input $X$, local elasticity is approximately $(\Delta Y/\Delta X)(X/Y)$. The perturbation is the larger of $0.001|X|$ and $10^{-8}$ times its allowed range; central differences are preferred when both sides validate, otherwise a one-sided result is reported. Zero baseline metrics produce null elasticity. The grid of a sweep is finite, and the conditional Pareto calculation requires matching total load and served energy within $10^{-9}$; it does not equalize SOC endpoints. [apps/web/src/terminal-engine.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/terminal-engine.ts), [apps/api/helioforge/engines/terminal.py:368–643](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/terminal.py#L368-L643).

## 4. Annual and reliability studies

`storage-annual` sums 8760 explicit hours on a non-leap calendar, with 24-hour import tariffs repeated daily. It uses transparent lower/upper tariff thresholds, optional grid charging, an initial/final 50% SOC and a 10–90% usable window. Reachability bounds preserve the terminal target. Monthly maximum imports contribute demand charges. This is a rule policy, not a globally optimal annual solution. [apps/api/helioforge/engines/toolkit_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py).

`storage-annualopt` instead has $7n+13$ variables for $n=8760$, 12 monthly peaks, hourly battery-direction variables, cyclic SOC, grid/curtailment limits and a sparse MILP. Battery integrality is retained when negative tariffs or degenerate zero-cost cycling require it. The input schema requires import prices above export prices, which makes simultaneous grid directions strictly dominated. Status zero and a finite reported relative gap at most $10^{-10}$ are required; requested gap is zero. Balance and SOC checks use a $10^{-5}$ scale. [apps/api/helioforge/engines/planning_studies.py:1083–1355](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py#L1083-L1355).

**Confirmed limitation:** its analytical no-battery baseline exports available surplus even when the export tariff is negative. With zero battery, load 1 kW, PV 2 kW, buy EUR 0.20/kWh and sell −EUR 0.10/kWh for all 8760 hours, the optimizer curtails the surplus at zero cost while the baseline costs EUR 876. A feasible no-battery curtailment comparator also costs zero. The reported difference is a comparator-policy difference, not battery value. Exact-pin and differing-version reproductions are retained separately. The source implementation is unchanged; see [HF-N01](../../ROADMAP.md).

`compare-reliability` runs a seeded chronological ensemble with correlated renewable variation, generator failure/repair transitions and per-trial battery energy. It reports loss-of-load hours using an unserved-power threshold $10^{-9}$, scales the sampled horizon to the declared 8760/8784-hour year and reports bounded 95% Hoeffding intervals. Trials range from 20 to 5000 with a two-million trial-hour cap. The storage endpoint is not cyclic across a trial. Zero observed loss events do not establish zero risk; independent failures, weather assumptions and limited synthetic trials define the scope. [apps/api/helioforge/engines/planning_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py).

## 5. Finance, PV and research screens

For annual cash flows $C_t$ and discount rate $r>-1$,

$$NPV(r)=\sum_{t=0}^{N}\frac{C_t}{(1+r)^t}.$$

The core project calculation starts with negative CAPEX and discounts CFADS after augmentation expenditure. Equity cash flows account for debt service separately. Level-payment debt service is $D i/[1-(1+i)^{-n}]$, with a separate zero-interest branch. DSCR is CFADS/debt service when debt service is positive; debt-free minimum DSCR and covenant result are null. Covenant evaluation uses unrounded ratios. [apps/api/helioforge/engines/finance.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/finance.py), [apps/api/helioforge/schemas.py:56–81](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/schemas.py#L56-L81).

`conventional_irr` omits cash flows of magnitude at most $10^{-9}$ only when counting sign changes; NPV and root evaluation still use the original complete cash-flow sequence. It requires an initially negative flow and one sign change, and uses `brentq` with a bracket beginning at −0.95 and 1, expanding the right side up to 1024. **A bracket endpoint with exactly zero NPV is currently rejected by the product `>=0` guard**, so a unique conventional IRR is not always returned. Interior `[-100,150]` gives approximately 0.5; `[-100,200]` at 1 and `[-100,300]` at 2 return null. The separate `investment-contracts` study uses its own bounded bisection convention; do not combine their guarantees. [apps/api/helioforge/engines/finance.py:61–98](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/finance.py#L61-L98), [apps/api/helioforge/engines/planning_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py). The [Brent API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html) describes the library operation, not this repository's endpoint guard.

PV LCOE divides discounted lifetime cost by discounted generation, converting kWh to MWh. Degradation, curtailment, annual OPEX and an optional inverter replacement are explicit. Panel count rounds upward; land area is a ground-coverage approximation. Acquisition uses EV less net debt for implied equity and an EBITDA-minus-maintenance screening cash flow; it is not a complete tax/working-capital/terminal-value valuation. [apps/api/helioforge/engines/finance.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/finance.py).

Drift first forms relative residuals $(observed-expected)/expected$. The baseline is the first $\max(5,\lfloor n/3\rfloor)$ observations; the output's `baseline_fraction=1/3` is a label, not the exact fraction for every short series. Median and MAD establish baseline/scale with a 0.005 fractional scale floor; alerts use strict $|z|>threshold$. The recent drift statistic uses the final five residuals. [apps/api/helioforge/engines/research.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/research.py).

The Weibull screen uses $S(t)=\exp[-(t/\lambda)^k]$ and conditional future failure $1-S(t+h)/S(t)$, evaluated stably through the cumulative-hazard difference. Shape and scale are supplied, not estimated from failure observations. Carbon intensity divides lifecycle emissions by degraded lifetime generation; counterfactual avoided emissions may be negative. Forecast paths use declared seeded synthetic processes rather than fitted market forecasts. [apps/api/helioforge/engines/research.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/research.py), [apps/api/helioforge/engines/forecast.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/forecast.py).

## 6. Averaged inverter controls and eigenmodes

The control study has ten states: two components each of filter current $i_f$, capacitor voltage $v_c$, grid current $i_g$, current-PI integral $\xi_i$ and voltage-PI integral $\xi_v$. With $J=\begin{bmatrix}0&1\\-1&0\end{bmatrix}$,

$$L_f\dot i_f=v_{inv}-v_c-R_f i_f+\omega L_f Ji_f,$$
$$C_f\dot v_c=i_f-i_g-i_{load}+\omega C_fJv_c,$$
$$L_g\dot i_g=v_c-v_g-R_g i_g+\omega L_gJi_g.$$

The outer PI generates a vector-limited current reference. The inner PI generates inverter voltage limited to $V_{DC}m_{max}/\sqrt3$. Back-calculation adds saturated-minus-raw residuals scaled by antiwindup gain divided by the corresponding integral gain. The equilibrium includes nonzero capacitor q-axis current $\omega C_fV_g$; zeroing every current would violate the rotating-frame balance. [apps/api/helioforge/engines/control_studies.py:788–889](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L788-L889).

The transient uses fixed-step RK4, preserves the event time and repeats with half the step; output uses the refined trace. Voltage/current discrepancies are compared with explicit finite tolerances, not used as a global stability proof. The local eigenmode study forms a central-difference Jacobian with perturbations $10^{-6}\max(1,|x_j|)$ and reports ten eigenvalues. Largest real part below $-10^{-7}$ is classified stable, above $10^{-7}$ unstable and otherwise marginal. This is a numerical classification at the declared equilibrium, with imposed grid angle and no PLL. Switching ripple, digital delay, DC-link dynamics, protection and grid-code qualification remain outside this averaged model. [apps/api/helioforge/engines/control_studies.py:581–986](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L581-L986).

## 7. Selected physical-study conventions

Balanced AC power flow uses a complex admittance network, one slack bus and PQ buses; residual and voltage checks qualify the numerical root. Branch ratings generate warnings rather than constraining an optimal dispatch. The separate six-zone network study is a linear DC OPF, not this AC solver. [apps/api/helioforge/engines/physical_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py), [apps/api/helioforge/engines/planning_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py).

The energization study integrates an ideal RLC state with RK4 and uses trapezoidal work/loss ledgers. Its capacitor voltage can be signed; peak values come from sampled trajectories, with a coarse/refined comparison. The PWM study is a single-phase ideal switching/averaged RL illustration, not the ten-state averaged controller. Both vibration and bearing routines remove the mean and apply a Hann window, using the common amplitude factor $2/\max(\sum w,10^{-12})$. The engineering `_fft_amplitude` routine then halves the DC bin and, for even record lengths, the Nyquist bin. The bearing `_record_spectrum` routine retains the common factor at every bin without those endpoint corrections. In the retained independent 64-sample alternating-signal observation, the Nyquist amplitudes were 1 (engineering) and 2 (bearing); the interior-bin control agreed to floating-point precision. These are the current implementation conventions, not power spectral densities or field validation. [apps/api/helioforge/engines/engineering_studies.py:1772–1782](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/engineering_studies.py#L1772-L1782) [apps/api/helioforge/engines/physical_studies.py:1751–1755](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/physical_studies.py#L1751-L1755) Ray tracing reports incident beam energy, not electrical conversion yield. See the [atlas](STUDY_MODEL_ATLAS.md) for every remaining registered model and its limits.

## 8. Independent teaching companion

The existing `docs/index.html` selects the analytical `grid` proxy. At time $t$ in hours, it evaluates

$$P_{solar}=S\max(0,\sin(\pi(t-6)/12)),$$
$$P_{demand}=D\left[0.8+0.18\cos(2\pi(t-19)/24)+0.12\exp(-((t-19)/3)^2)\right],$$
$$P_{import}=\max(P_{demand}-P_{solar}-B,0).$$

Its displayed solar share is $\min(100,100P_{solar}/P_{demand})$ percent and its emissions rate is $P_{import}I/1000$ kg/h, for grid factor $I$ in g/kWh. This is an instantaneous illustrative profile over 0–24 hours, with a fixed externally supplied battery power $B$. There is no storage energy state, charging schedule, export revenue, generator or network model. The page configuration sets $B=0$ initially, although the generic model specification's fallback is 100 kW; the configured page default takes precedence. These source equations are not a new runtime observation, and the page does not call the native hybrid or MILP engines. [docs/index.html:165–355](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/index.html#L165-L355).

## External references and their scope

[SciPy MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) and [Brent root finding](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html) provide primary algorithm/API context. [REopt](https://www.nlr.gov/reopt/) and its [model description](https://www.nlr.gov/reopt/about) are related energy-optimization references, not an implementation identity, affiliation or independent validation of HelioForge. Their current websites/documentation may use versions different from the pinned runtime. Repository equations, actual tolerances and dated local results control the claims here.
