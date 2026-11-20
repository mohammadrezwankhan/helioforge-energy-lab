# Worked examples and labs

The original native Python examples were executed on **2026-11-19, 22:45:35–22:45:36 UTC**, against source `fb42eb4d9b0c87e692710e8e867ab5190ea831a7`, using Python 3.12.14, NumPy 2.4.6, SciPy 1.17.1 and Pydantic 2.14.3. They call the source functions directly; they do not invoke HTTP, a provider, a browser, a physical device or the saved-run database. Raw inputs, complete outputs, logs and all 819 tracked-file hashes/modes before and after execution are retained in the review evidence.

## Run the portable examples

After [setup](SETUP_AND_REPRODUCIBILITY.md), run from the repository root:

```sh
PYTHONPATH=apps/api python docs/examples/worked_labs.py lab-output
```

Choose an output directory that does not exist; the script deliberately refuses to overwrite an earlier run. On PowerShell set `$env:PYTHONPATH='apps/api'` before the Python command. The [example script](../examples/worked_labs.py) was repaired under the unchanged Ruff 0.17.4 policy: its original inputs, source calls, nine numerical predicates and tolerances are retained, with explicit failure checks in place of optimization-removable assertions. Its usage docstring now names the actual file. The repaired script was separately executed on **2026-11-19, 23:56:23.857682–23:56:26.691022 UTC**, using the same declared pins and a fresh output directory. All eight JSON outputs, including the summary, were byte-identical to the original outputs. It writes each full result plus that summary without source mutation. A separate repeated-path invocation rejected the existing directory before example calculations and preserved all output bytes/modes/times. The original 22:45 execution and the initial 17-diagnostic lint failure remain separate historical records. Runtime/model-package changes require a new dated observation rather than replacing the reference record.

## Lab 1 — two-interval cyclic storage

Use two one-hour intervals with load `[1,1]` kW, PV `[0,0]`, import prices `[0.1,0.3]` EUR/kWh and zero export price/wear. Battery capacity is 2 kWh, power 1 kW, efficiency 1, usable SOC 0–100%, initial/final energy 1 kWh and grid limits 10 kW.

| Quantity | Observed result | Hand check |
|---|---:|---|
| No-battery cost | EUR 0.40 | $1(0.1)+1(0.3)$ |
| Optimized cost | EUR 0.20 | Import 2 kW in hour 1; discharge 1 kW in hour 2 |
| Savings | EUR 0.20 | Baseline minus optimized cost over exactly two hours |
| Terminal SOC | 1 kWh | Charge from 1 to 2 kWh, discharge back to 1 kWh |

This small case exposes the endpoint rule without hidden annualization. Change efficiency below one and check how extra charging/losses alter the result. Keep the four supplied arrays equally sized. Implementation: [apps/api/helioforge/engines/storage.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/storage.py), [apps/api/helioforge/schemas.py:19–53](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/schemas.py#L19-L53).

## Lab 2 — Terminal reference versus island

`terminal_defaults()` uses 8 kW PV, 20 kWh/5 kW battery, 6 kW demand scale, 10 kW grid, 0.9 round-trip efficiency, initial/min/max SOC fractions 0.5/0.1/0.9 and import/export prices 0.25/0.05 EUR/kWh. Run the same inputs with only `gridKw=0` for the island comparison.

| Metric | Reference | Island |
|---|---:|---:|
| Total demand | 129.6 kWh | 129.6 kWh |
| PV available | 60.7660329018012 kWh | 60.7660329018012 kWh |
| Demand served | 129.6 kWh | 67.1743039620402 kWh |
| Unserved demand | 0 kWh | 62.4256960379598 kWh |
| Period cost | EUR 15.60642400948995 | EUR 0 |
| Initial → final stored energy | 10 → 2 kWh | 10 → 2 kWh |
| Maximum bus / SOC residual | 0 kW / 0 kWh | 0 kW / 0 kWh |

The zero-cost island case leaves almost half the demand unserved; it does not demonstrate an economically better supply. Both runs consume 8 kWh of initial inventory. The script also exports the actual `B−A` difference. Python/native-browser parity is exercised separately by the repository's existing Node tests. [apps/api/helioforge/engines/terminal.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/terminal.py), [apps/web/src/terminal-engine.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/terminal-engine.ts).

## Lab 3 — debt-free finance

Set CAPEX EUR 100, two annual gross margins EUR 60, zero OPEX/degradation/escalation, full two-year contracted fraction, no debt and no augmentation. At zero discount, the observed project NPV is EUR 20 and reported IRR is 13.066%. `minimum_dscr` and `covenant_pass` are both null, because debt service is absent. The input explicitly reduces debt tenor and contract duration to the project life. [apps/api/helioforge/engines/finance.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/finance.py), [apps/api/helioforge/schemas.py:56–81](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/schemas.py#L56-L81).

For a separate boundary exercise, `conventional_irr([-100,200])` currently returns null despite NPV being zero at rate 1. The independent native reproduction also checked the expanded endpoint at 2 and an interior 0.5 control. That known endpoint omission is [HF-N02](../../ROADMAP.md); do not turn null into zero or claim this lab validates every cash-flow pattern.

## Lab 4 — default PV screening

The default `PVRequest()` produces CAPEX EUR 32,500,000, first-year generation 66,150 MWh, LCOE EUR 51.38/MWh, 83,334 panels and indicative land 66.67 ha. The example retains every default and yearly row in JSON. Panel count rounds up, while land is a coverage approximation; these values are not a site layout or a bid. Change specific yield while holding the other assumptions fixed, then compare against the `pv-sensitivity` study's finite 9×9 grid. [apps/api/helioforge/engines/finance.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/finance.py), [apps/api/helioforge/engines/toolkit_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/toolkit_studies.py).

## Lab 5 — default hybrid energy screen

`HybridRequest()` selects `remote-triad` with the baseline scenario for 24 hours. Observed demand is 14,222 kWh, served energy 13,933.539333877663 kWh and unserved energy 288.46066612233653 kWh. Stored energy moves from 1,800 to 531.2489020891062 kWh; maximum balance residual is approximately $2.84\times10^{-14}$ kW. Variable grid/generator cost is EUR 0 in this off-grid example, while unmet demand remains visible. The recurrence and profile differ from Terminal. [apps/api/helioforge/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/hybrid.py), [apps/api/helioforge/engines/hybrid.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/hybrid.py).

## Lab 6 — averaged control refinement

`evaluate(StudyRequest(study='hybrid-controls'))` runs the catalogue defaults, including a 0.04 s horizon and 50 µs coarse step. The observed maximum coarse/refined capacitor-voltage discrepancy is 0.0517967023073993 V and maximum filter/grid-current discrepancy 0.006591749848826822 A. The final d-axis capacitor voltage is 325.32257111595044 V peak; final d-axis filter current 7.854616223454734 A. Neither vector limiter was hit in the reference run.

These are numerical consistency observations for an imposed-angle averaged dq model. They do not test a PLL, switching ripple, hardware controller or grid-code requirement. Alter one gain or disturbance, retain both traces and limiter flags, and examine the separate eigenmode study within its local scope. [apps/api/helioforge/engines/control_studies.py:581–986](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/control_studies.py#L581-L986).

## Diagnostic counterexample — annual baseline

The exact-pin 2026-11-19 22:44:27–22:44:29 UTC reproduction used all 8760 hours with load 1 kW, PV 2 kW, buy EUR 0.20/kWh and sell −EUR 0.10/kWh, **zero battery capacity/power/initial SOC**, grid limits 10 kW and a 10-second solver limit. The optimizer reported cost EUR 0, zero grid exchange, 8760 kWh curtailment, zero residuals and gap zero. Its baseline cost was EUR 876.000000000004, despite a feasible no-battery curtailment policy costing zero.

```python
from helioforge.engines.planning_studies import AnnualStorageInput, _annual_storage

result = _annual_storage(AnnualStorageInput(
    load_kw=[1.0] * 8760, pv_kw=[2.0] * 8760,
    import_price_eur_kwh=[0.2] * 24,
    export_price_eur_kwh=[-0.1] * 24,
    capacity_kwh=0.0, power_kw=0.0, initial_soc_kwh=0.0,
    grid_import_limit_kw=10.0, grid_export_limit_kw=10.0,
    solver_time_limit_seconds=10.0,
))
print(result['metrics'])
```

This intentionally uses a private source function for a bounded regression reproduction, not a promised stable public Python API. The current baseline's forced-export behavior explains the difference; it must not be advertised as storage value. The earlier differing-version run remains a separate record. Source: [apps/api/helioforge/engines/planning_studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/engines/planning_studies.py).
