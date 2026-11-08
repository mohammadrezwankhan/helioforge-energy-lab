# Deterministic energy-ledger summation

The frozen 336-hour `compare-dunkelflaute` result stores an electric balance residual of `-1.6200374375330284e-11` kWh. Replaying the unchanged model under Python 3.11.17 produced `5.6559201766503975e-11` kWh, while Python 3.12.14 reproduced the stored value. The original branch and its baseline both failed the existing `1e-12` replay comparison on Python 3.11. The failure therefore preceded the SciPy stub update.

The cause is the change to floating-point `sum()` in Python 3.12, combined with different summation behavior for Python floats and NumPy scalars. The [Python documentation](https://docs.python.org/3.12/library/functions.html#sum) records that algorithm change. Repeating only the six sums over the identical frozen hourly ledger reproduces both residuals without calling the optimizer.

The model now uses `math.fsum` for the six energy-category totals in the residual calculation. Their addition and subtraction order is unchanged. The MILP objectives, constraints, direction variables, efficiency, initial and terminal SOC, result schema and replay tolerances are unchanged. This is an arithmetic determinism correction, not a new physical model or a scientific validation claim.

A new regression runs the real optimizer with zero renewable supply, zero initial stored energy and 336 loads of 100.1 kW. Every hourly load is unserved and no energy is charged or discharged, so the independent ledger balance is zero. Before the fix, Python 3.12 reported `-2.0372681319713593e-10` kWh and the new `1e-12` assertion failed. The corrected model passes without relaxing that assertion.

## Executed verification

- Python 3.11.17, 3.12.14 and 3.13.17, each with NumPy 2.4.6 and SciPy 1.17.1: all 1,063 API tests passed, including the new actual-ledger regression.
- All three interpreters passed the existing 59-study result replay and 285-case hybrid replay. The existing absolute/relative tolerances remain unchanged, and no frozen numeric value was rewritten.
- The 32 workflow-study tests passed on Python 3.11 and 3.12 before the full suites ran.
- The new [study acceptance record](summation-study-contracts.json) comes from executing all 59 study cards and 61 targeted test cases successfully. The prior [SciPy stub acceptance record](study-contracts.json) remains unchanged.

The frozen study bundle received exactly 36 updated source/evidence hash fields across the 12 workflow studies whose shared source file changed. Every other field, including all floating-point bit patterns, numerical results and stored timing observations, was preserved. The generated model registry references the new acceptance record and retains the exact source-hash checks.

These are local Linux results. Remote CI, browser acceptance and deployment receipts are separate evidence; passing software checks does not establish field calibration or production approval. The full API suites also emitted the existing Starlette warning about its deprecated `httpx` TestClient integration; no dependency or warning policy was changed for this correction.
