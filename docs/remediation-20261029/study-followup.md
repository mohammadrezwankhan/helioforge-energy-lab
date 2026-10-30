# Study numerical acceptance follow-up

Date: 2026-10-29  
Scope: F10/F14 software acceptance for the 59 registered study IDs. This record covers executable numerical and interface contracts; it does not establish scientific validation, calibration, regulatory approval, or deployment.

## Outcome

The focused runner recorded **59/59 study IDs PASS**. Its linked independent cases executed **61/61 pytest cases PASS** (59 mapped node IDs, with parameter expansion for the annual toolkit ledger case). Per study, it also recorded successful default result/schema and finite-or-null JSON checks, one valid input boundary case, rejection of an unknown input field, exact repeatability after excluding reported wall-clock solver fields, and strict JSON round-trip/evidence-digest preservation.

The machine-readable results, including each expected relation and observed result snapshot, units, test IDs, source hashes, statuses, solver applicability, and uncovered limitations, are in [study-contracts.json](study-contracts.json).

## Commands and observed results

Commands ran with the old audit virtual environment and this checkout's API source on `PYTHONPATH`:

```powershell
$env:PYTHONPATH='C:\Users\MRK\Downloads\misC\helioforge-remediation-20261028\source\apps\api'
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' scripts\acceptance-study-contracts.py
```

Observed result: `status=PASS`, `study_count=59`, `studies_passed=59`, `studies_failed=0`, `targeted_test_nodes=59`, `targeted_tests_passed=59`, `executed_test_cases=61`, `passed_test_cases=61`, and `failed_test_cases=0`. The runner wrote `docs/remediation-20261029/study-contracts.json`.

The acceptance artifact contract and hand case were checked with:

```powershell
$env:PYTHONPATH='C:\Users\MRK\Downloads\misC\helioforge-remediation-20261028\source\apps\api'
& 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' -m pytest apps/api/tests/test_study_acceptance_contracts.py -q
```

Observed result: `2 passed`. The artifact contract check requires all 59 catalogue IDs, a passing mapped test and actual observation for each, explicit boundary/invalid/repeatability/JSON results, and a precise uncovered condition for every model. The thermal screen hand case independently reconstructs 365 EFC, a unit temperature multiplier, and a 3.65% screening index.

## Sources and interpretation

For each study, the artifact hashes its engine module, referenced test file, and `apps/api/helioforge/studies.py`. Linked cases cover hand arithmetic, accounting/physical residuals, null denominator behavior, seeded repeats, and solver/model feasibility where applicable. The broad existing module test suites were not run; only the mapped acceptance node IDs and the new acceptance file were targeted.

The `compare-dunkelflaute` result does not expose a solver optimality status. Its linked case passed interval direction, power/SOC bounds, energy-balance, and terminal-SOC checks; global optimality remains `U`. Other solver-bearing results expose and pass their declared `optimal`, `converged`, or `fit_success` status where applicable. The remaining model-specific physics/data limits are copied into each study record's `uncovered_conditions`.

No engine, model definition, study catalogue, generated dataset, or parent-owned registry was changed. No deployment or external provider execution was performed.
