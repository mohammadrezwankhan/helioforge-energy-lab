"""Run the local development application; no external services are enabled here."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT / "apps/api") + os.pathsep + env.get("PYTHONPATH", "")
if not (ROOT / "apps/web/dist/index.html").exists():
    raise SystemExit("Build the frontend first: cd apps/web && npm ci && npm run build")
raise SystemExit(
    subprocess.call(  # noqa: S603 -- Current Python, fixed local module argv; owned process lifecycle; no shell.
        [
            sys.executable,
            "-m",
            "uvicorn",
            "helioforge.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
            "--reload-dir",
            str(ROOT / "apps/api"),
        ],
        cwd=ROOT,
        env=env,
    )
)
