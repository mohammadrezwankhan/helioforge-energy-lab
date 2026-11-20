# Assumptions and scientific applicability

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

## What the source actually supports

The hourly hybrid algorithm is a deterministic **single-bus adequacy screen** using repeated synthetic diurnal profiles, explicit grid/outage topology, service priority, simple reserve limits and battery energy accounting. A “grid-forming” label checks availability of a declared reference in the model; it does not prove inverter dynamics, black start or fault ride-through. The 24-hour browser Terminal is another bounded, nonoptimizing calculator.

The separate storage MILP uses an illustrative profile (including six national price multipliers), fixed time resolution and equal initial/terminal SOC; it can evaluate optimized *model costs*, not guarantee market remuneration or investment returns. Negative price, infeasible grid import, peak tariff and wear assumptions materially change conclusions. [Methodology](../HYBRID_METHODOLOGY.md) and [storage source](../../apps/api/helioforge/engines/storage.py) are authoritative.

## Important gaps before external use

No site-specific validation of impedances, equipment faults, protective relays, calibrated wind/PV, full three-phase EMT, live investment models, accredited education, cybersecurity certification, financial approval or real SCADA/BMS control has been provided by this new documentation. External provider/device calls require their own credentials, explicit consent, provenance, ownership and legal assessment. A generated example or old CI run is not evidence of today's deployment.

See [59-study applicability ledger](../roadmap/COMPLETION.md) and the [latest dated quality report](../../QUALITY_REPORT.md). Retain unanswered external assumptions as review gates, not hidden defaults.
