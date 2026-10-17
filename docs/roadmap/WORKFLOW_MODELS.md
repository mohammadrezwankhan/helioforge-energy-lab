# Learning, comparison, pilot, and council study models

This page documents the twelve deterministic Python experiments in
apps/api/helioforge/engines/workflow_studies.py. They are reduced-order
educational screens with bounded input validation. They do not change the
existing hybrid architecture capability boundary, authorize field actions, or
call an external agent. Each result includes assumptions and limitations.

## Learning

The net-load study computes demand minus solar and wind, interval ramp rates,
and interval energy. Its reported closure is demand energy minus renewable
energy minus net-load energy. The upward-ramp marker and reported percentile
are user selected. The default hourly points are synthetic.

The black-start study walks supplied steps through
dark → grid-forming-ready → bus-energized → load-restored. Each step must follow
the sequence, keep active power plus inrush below the available rating after
reserve, and fit the configured inrush budget. This is a finite-state procedure
exercise. It has no dynamic transient, relay/protection, motor-start, or site
procedure model. NERC procedure guidance motivates the exercise but does not
validate its illustrative thresholds.

The hydrogen study carries a batch through electrolyzer electricity,
compression electricity, stored chemical energy on a lower-heating-value basis,
and fuel-cell electricity. The default hydrogen LHV is 33.3 kWh/kg, as listed
by DOE. For mass m, electrolyzer specific use e, compression use c, LHV L, and
fuel-cell efficiency η, the ledger is m*e + m*c = m*L*η + losses. Input
constraints require electrolyzer electricity to be at least the LHV basis, so
the example does not report a negative electrolysis loss. Pressure, delivery
boundary, leakage, auxiliaries, and measured efficiency are excluded.

## Comparison

The Pareto study takes candidate cost, served-load percentage, initial and
terminal SOC, expected loss-of-load hours, sample count, and explicit
scenario/sample-set metadata. It only forms dominance relations and weighted
recommendations within a group matching scenario key, sample-set key, horizon,
service basis, and sample count. Cost and expected loss-of-load hours are
minimized; service is maximized. The score applies disclosed user weights to
per-group min-max scales. It does not estimate an ensemble, and a weighted
preference is not a universal decision rule. If scores tie, run ID provides a
deterministic lexical tie-break.

The dunkelflaute study solves a 336-hour mixed-integer dispatch for one
synthetic 14-day renewable path. Binary controls enforce that the battery
charges or discharges in each interval, with a shared power limit. Its balance
is renewable plus discharge plus unserved energy equals load plus charge plus
curtailment. SOC advances by charge efficiency times charge minus discharge
divided by discharge efficiency. Initial and terminal SOC are fixed equal.
The optimization first minimizes shortfall, then breaks ties by curtailment and
a small throughput term. This is one specified path: shortfall hours are not
statistical LOLE. The model still omits grid/network limits, reserve products,
market prices, and battery aging.

The thermal study calculates equivalent full cycles from years, daily cycles,
utilization, and depth of discharge. It then applies exp(k*(temperature -
reference temperature)) and a user-specified loss index per 1,000 equivalent
cycles. The returned radar data has utilization, temperature multiplier, and
screening wear axes. Both coefficients are explicit assumptions; the result is
not a battery-life prediction. The index is intentionally not clipped to 100%.

## Pilot evidence

The photogrammetry study compares equal-length point arrays by index. Per-point
error is the 3D Euclidean residual after applying the input coordinate scale;
RMSE is sqrt(mean(error squared)), with maximum and empirical percentile
reported. Empty paired arrays produce null error statistics; unequal arrays
are rejected. It does not register clouds or find nearest neighbours. ASPRS
positional accuracy guidance is a reporting reference, not a claim that this
study meets a survey standard.

The DTS study computes adjacent absolute temperature gradients for fresh,
non-missing samples. Input validation requires at least 0.1 m between samples
and bounds temperatures and the hot-spot threshold to -50–200 °C. User
thresholds label hot spots and gradient exceedances; missing and stale samples
remain visible in the result. If no fresh samples exist, maximum temperature is
null. It has no cable-rating or alarm-calibration model.

The off-gas study casts one vote per sensor record when any present temperature,
CO, or VOC reading meets its user-entered threshold. Missing channels are
counted. “Warning” is a hypothetical screen output only, not a calibrated alarm,
exposure limit, detector interface, or safety control.

## Council

The debate study computes a flat annual-value NPV and pairs supplied finance
proposer and storage challenger assertions by topic. A pair converges only
when units match and the numeric difference fits its declared tolerance.
Unpaired, mismatched, or conflicting claims stay unresolved. The process is
deterministic Python; no LLM or external council role executes.

The evidence study accepts a structured JSON manifest for tariff, warranty, and
single-line metadata. It checks field names, units, values, dates, user-set age
limits, expiry, and whether issuer/source-reference fields are present. It does
not extract documents, run OCR, verify signatures, retrieve evidence, or
authenticate a source.

The consensus study updates a binary prior using user-supplied likelihood
ratios, then reports the complement probability and Shannon binary entropy.
The raw product assumes conditional independence. Repeated dependency groups
are flagged but not automatically removed. The optional cap and evidence
weight are shown as sensitivity assumptions; neither a high posterior nor
consensus grants approval or an operational decision.

## Primary references

- [NREL renewable-integration ramping study](https://docs.nrel.gov/docs/fy18osti/71151.pdf) for net-load/ramping terminology.
- [NERC black-start procedure practice guide](https://www.nerc.com/pa/comp/guidance/CMEPPracticeGuidesDL/CMEP%20Practice%20Guide%20-%20Evaluating%20Blackstart%20Documented%20Procedures.pdf) for restoration-procedure context.
- [DOE hydrogen LHV basis](https://www.energy.gov/cmei/fuels/doe-technical-targets-onboard-hydrogen-storage-light-duty-vehicles) and [DOE compression-energy record](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/9013_energy_requirements_for_hydrogen_gas_compression.pdf).
- [Deb et al. Pareto-dominance optimization paper](https://doi.org/10.1109/4235.996017) and [SciPy mixed-integer linear programming documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
- [NREL battery-life modeling overview](https://www.nrel.gov/transportation/battery-lifespan.html); it describes richer fitted models and is not a calibration source for this simplified thermal screen. [NREL SAM LCOE documentation](https://samrepo.nlr.gov/help/mtf_lcoe.html) provides financial-model context only.
- [ASPRS positional-accuracy standards](https://www.asprs.org/Main/Main/Standards/Positional-Accuracy-Standards.aspx) and [Rose et al. DTS spatial-pattern limitations](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/wrcr.20144).
- [NIOSH Pocket Guide](https://www.cdc.gov/niosh/npg/) is contextual reference only; no exposure thresholds are embedded by this study.
- [NIST Bayesian reliability explanation](https://www.itl.nist.gov/div898/handbook/apr/section2/apr1a.htm) and [Shannon's original communication theory paper](https://www.princeton.edu/~wbialek/rome/refs/shannon_48.pdf).

These references support terminology or general equations. They do not
calibrate, certify, or independently validate study defaults.
