# Study bundle replay CI diagnosis

## Finding

The diagnostic at commit `0af61b8` localized the mismatch to generated `research-bearing` signals. The follow-up replay at `6529310` accepted 115 one-ULP differences, then still failed on eight compound samples. Those eight had absolute differences from `8.6736e-19` to `2.2204e-16`; one near-zero result differed by eight ULPs despite an absolute delta of `2.7756e-17`. The fixture comes from `_bearing_fixture()` in `apps/api/helioforge/engines/physical_studies.py`, where two or three weighted `math.sin` terms are added. Cancellation makes output ULP distance large near zero while the absolute error remains at binary64 machine scale.

The checker now compares those named signals against a forward absolute bound of `8 × epsilon × Σ|coefficient|`, where `epsilon` is binary64 machine epsilon and the coefficients come from the exact fixture record formula. The most complex expression has three terms and four rounded multiplies/additions. With each sine bounded by one in magnitude, the L1 coefficient sum bounds propagated absolute error independent of cancellation. The factor eight conservatively covers pairwise one-ULP libm variation in components and accumulated multiply/add rounding (using the standard `γ₄` forward-error bound), with room for platform evaluation order. This is a fixture-specific numerical bound, not the general result tolerance.

For the eight CI cases, the formula-derived bounds are `1.82965e-15` for training record 5, `1.79235e-15` for held-out normal, and `2.41407e-15` for held-out extra-tone. The largest observed delta, `2.22045e-16`, is below each applicable bound. Record IDs, field names, value types, array and record counts, signed zero, all other default values, and all descriptive/source metadata remain exact. A sample beyond its formula-derived bound or a missing/extra sample still fails. Frozen signal bytes remain unchanged.

Study replay now verifies that the stored inputs exactly match the frozen catalogue defaults, checks the canonical stored input digest, and passes those frozen inputs into `evaluate`. It therefore validates the committed experiment rather than regenerating platform-specific defaults before replay. Provenance/source revisions, evidence digests, result metadata and all non-input result values still receive their existing checks; the existing result comparison tolerance remains `1e-12`. Mismatch diagnostics remain bounded to 12 paths and shortened values.

Independent review identified Python's equality of positive and negative zero as an exactness gap. Integration now compares float bits and tests signed-zero changes in both frozen inputs and catalogue defaults; these changes are rejected.

## Local reproduction

The supplied Ubuntu/Python 3.13.17 diagnostic listed 12 differences and every listed value had ULP distance 1; the log indicates further differences were omitted. The current Windows checkout has no platform delta in this fixture, so its default catalogue values match exactly. Under Python 3.12.14 and Python 3.13.15 with the project's pinned API dependencies:

- Python 3.12.14: `scripts/check-study-assets.py` passed for 59 studies, with zero numerical roundoff differences.
- Python 3.13.15: `scripts/check-study-assets.py` passed for 59 studies, with zero numerical roundoff differences.
- Focused checker tests: 7 passed after the formula-derived bound update, covering all eight reported deltas (including the eight-ULP cancellation case), rejection beyond the bound, metadata and shape rejection, exact frozen input/digest validation, byte-preserving full replay, and bounded diagnostics.
- Ruff on the checker and focused tests: passed.

The CI cause is localized to platform-level `math.sin` roundoff in that fixture. The first failed one-ULP-only attempt is preserved in `ci-frozen-replay-failed.log`; it is not being reported as a pass. The bounded absolute comparator rejects any sample outside the formula-derived bound. No remote CI was rerun in this worker slice.

## Commands run

```powershell
$env:PYTHONPATH='apps/api'
C:\Users\MRK\AppData\Local\Programs\Python\Python313\python.exe -m venv C:\Users\MRK\AppData\Local\Temp\helioforge-study-ci-py313
C:\Users\MRK\AppData\Local\Temp\helioforge-study-ci-py313\Scripts\python.exe -m pip install fastapi==0.142.0 starlette==1.7.0 uvicorn==0.54.0 pydantic==2.14.1 numpy==2.4.6 scipy==1.17.1 shapely==2.1.2 httpx==0.28.1
C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe scripts\check-study-assets.py
C:\Users\MRK\AppData\Local\Temp\helioforge-study-ci-py313\Scripts\python.exe scripts\check-study-assets.py
C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe -m pytest scripts\test_check_study_assets.py -q
C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe -m ruff check scripts\check-study-assets.py scripts\test_check_study_assets.py
```

The attempted `python -m pip install -e "apps/api[dev]"` failed because its build backend could not write `apps/api/helioforge_api.egg-info` (`WinError 5`). The temporary Python 3.13.15 environment instead used the exact API dependency versions in `apps/api/pyproject.toml`: FastAPI 0.142.0, Starlette 1.7.0, Uvicorn 0.54.0, Pydantic 2.14.1, NumPy 2.4.6, SciPy 1.17.1, Shapely 2.1.2 and HTTPX 0.28.1. It is not the remote Ubuntu/Python 3.13.17 environment. No study bundle, numerical model, application source, browser artifact, or runtime asset was regenerated or modified. The approved candidate G browser runtime remains outside this checker-only change.

## Limits

The absolute exception is tied to the known generated `math.sin` fixture and does not apply to study inputs or replayed results. Source revision checks still bind the engine bytes, input digests are exact, and result metadata/source fingerprints retain exact comparison; the pre-existing `1e-12` tolerance for numerical replay outputs is unchanged. No data bytes were rewritten.

Independent review matched the coefficient table to the source formula and found no blocking defect. Python does not promise one-ULP `math.sin` variation across every possible library or platform. The derived allowance covers the stated component-roundoff premise and observed environments; a platform exceeding it fails the checker rather than receiving an unsupported pass.
