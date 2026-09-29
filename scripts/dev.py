"""Run the local development application; no external services are enabled here."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT / "apps/api") + os.pathsep + env.get("PYTHONPATH", "")
if not (ROOT / "apps/web/dist/index.html").exists():
    raise SystemExit("Build the frontend first: cd apps/web && npm ci && npm run build")
raise SystemExit(subprocess.call(
    [sys.executable, "-m", "uvicorn", "helioforge.main:app", "--host", "127.0.0.1",
     "--port", "8000", "--reload", "--reload-dir", str(ROOT / "apps/api")], cwd=ROOT, env=env))
