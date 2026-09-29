# HelioForge API 0.2.0

Python 3.11+ / FastAPI / SciPy HiGHS. See the root README, `docs/METHODOLOGY.md` and `docs/HYBRID_METHODOLOGY.md`. The canonical hybrid catalogue is included as package data.

From this directory: `python -m pip install -e ".[dev]"`. From the repository root: `python scripts/dev.py`. The packaged API can also be launched with `python -m uvicorn helioforge.main:app --host 127.0.0.1 --port 8000`. Use the provided frontend distribution for the dashboard.
