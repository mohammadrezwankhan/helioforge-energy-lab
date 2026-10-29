# Study bundle replay CI diagnosis

## Finding

At commit `81b03a11ba20ddcb002708f16f75e6206faa5407`, the supplied CI log reports `Study catalogue is stale` at the exact comparison between the committed bundle catalogue and `json.loads(json.dumps(catalogue()))`. This occurs before any result replay or numerical tolerance comparison. The log does not include differing paths or values, so the particular catalogue entry that differed is not evidenced by that run.

The catalogue has study definition fields (`id`, field defaults, equations, sources, limitations and related descriptions); it does not contain source-revision, dataset-revision, Python-version, or other runtime identity fields. Therefore, the recorded failure does not establish an identity-metadata mismatch. Updating the frozen data or weakening catalogue/numerical comparisons would not be evidence-based.

The checker now emits a bounded JSON diagnostic on an exact catalogue mismatch, including the first 12 differing JSON paths and shortened expected/current values. The comparison remains exact and still fails. This should make the next CI failure actionable without changing any model input, result, source fingerprint, or tolerance.

## Local reproduction

On the current Windows checkout, the committed bundle and runtime catalogue compare exactly under Python 3.12.14 and Python 3.13.15 with the project's pinned API dependencies:

- Python 3.12.14: `scripts/check-study-assets.py` passed for 59 studies, with zero numerical roundoff differences.
- Python 3.13.15: `scripts/check-study-assets.py` passed for 59 studies, with zero numerical roundoff differences.

The remote browser job used Ubuntu and Python 3.13.17. Its failure was not reproduced on Windows, and this work did not run remote CI. Platform-specific default-series calculations are one possible source of a catalogue-value mismatch, but remain an inference until a future diagnostic reports concrete paths and values.

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

The cause of the Ubuntu-only catalogue mismatch remains unknown because the supplied CI log contains no diff. If the next CI run reports numerical catalogue-value differences, retain the failure and review those values against the model/data provenance before considering any intentional catalogue update. No numerical tolerance or source/data fingerprint check was relaxed here.
