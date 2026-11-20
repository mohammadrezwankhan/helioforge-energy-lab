# Physical parameters, units and model boundaries

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

| Term | Units | Source and caveat |
| --- | --- | --- |
| `load_kw`, `served_kw`, `unserved_kw` | kW | Interval-average demand/service in [hybrid.py](../../apps/api/helioforge/engines/hybrid.py) |
| `pv_kw`, `wind_kw`, `hydro_kw` | kW | Synthetic profile output, not metered generation |
| `generator_kw`, `grid_import_kw`, `grid_export_kw` | kW | Limited source/grid flows |
| `charge_kw`, `discharge_kw` | kW | Battery power, not energy |
| `battery_kwh`, `soc_start_kwh`, `soc_end_kwh` | kWh | Energy capacity and state boundaries |
| `initial_soc`, `min_soc`, `max_soc` | Fraction | SOC fractions in request; `soc_pct` returned as percent |
| `round_trip_efficiency` | Fraction | One-way modeled factor is square root |
| `balance_residual_kw` | kW | Algebraic conservation residual, not an independent plant measurement |
| `import_eur_kwh`, `export_eur_kwh` | EUR/kWh | Illustrative hybrid tariffs |
| `variable_cost_eur` | EUR | Simplified hybrid variable energy accounting |
| `peak_charge_eur_per_kw_period` | EUR/kW per modeled period | Storage-only demand charge |
| `wear_eur_per_kwh` | EUR/kWh discharged | Storage-only degradation cost proxy |
| `savings_pct` | Percent or `None` | Storage cost comparison against computed no-battery reference |

The [source package](../../apps/api/pyproject.toml) pins solver and schema versions; `milp` convergence/time limits are declared in [storage.py](../../apps/api/helioforge/engines/storage.py). The 59-study catalogue has its own per-model units, constraints and provenance in [MODEL_REGISTRY.md](../MODEL_REGISTRY.md); do not apply these two models' units indiscriminately across all 59 studies.
