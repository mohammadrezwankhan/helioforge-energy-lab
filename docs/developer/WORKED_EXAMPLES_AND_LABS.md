# Worked examples and research labs

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

The examples below are **fictional hand calculations** for learning and validation planning, not source execution receipts or physical plant measurements.

## Lab 1 — single-hour conservation

Assume one hour, `PV=40 kW`, `wind=10 kW`, no hydro or generator, demand `45 kW`, battery charge `5 kW`, and no discharge, import, export or curtailment. The implemented balance form is:

```text
PV + wind + hydro + generator + discharge + import
= served + charge + export + curtailment
40 + 10 = 45 + 5  (kW)
```

Residual is 0 kW for these synthetic values. Check the actual greedy policy's priority ordering before expecting a real `simulate_hybrid` run to match: it charges **only after serving target demand**.

## Lab 2 — round-trip efficiency and stored energy

For a separate hypothetical interval, let round-trip efficiency be 81%, giving one-way factor `sqrt(0.81)=0.9`. Charge 10 kW for 1 h, with no discharge and sufficient capacity: `E_end−E_start=10×0.9=9 kWh`. Later discharge of 9 kW for 1 h consumes `9/0.9=10 kWh` of stored energy. The [hybrid source](../../apps/api/helioforge/engines/hybrid.py) uses this update with explicit SOC bounds. Compare both initial and terminal energies; it does not impose a cyclic terminal-SOC constraint.

## Lab 3 — storage MILP is not the hybrid policy

The [storage engine](../../apps/api/helioforge/engines/storage.py) minimises bought energy minus sold energy plus peak charge and discharge-wear cost. It uses binary direction variables and **equal initial and terminal SOC**. The hybrid model uses a fixed service-first policy and unconstrained terminal energy. Run their model-specific tests separately; matching the word “battery” does not imply comparable objectives.

## Lab 4 — preserve a verified source-specific result

```sh
python -m pytest apps/api/tests
python launch.py --check
```

These commands are prescribed, not executed in this docs commit. Capture their actual outputs, input hashes, environment and historical/source commit before calling them evidence. See the [existing quality report](../../QUALITY_REPORT.md).

## Lab 5 — public preview capabilities

Open the static preview, inspect a labeled *precomputed* example, then use the separate Terminal for a fresh bounded 24-hour case. Without a local Python server, do not describe any changed advanced-study input as a new Python optimisation run.
