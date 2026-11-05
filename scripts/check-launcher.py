"""Local process launch and synthetic database recovery checks. No production data."""

from __future__ import annotations

import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
checks: list[str] = []


def passed(name: str) -> None:
    checks.append(name)
    print("PASS", name, flush=True)  # noqa: T201 -- CLI report output.


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        if os.name == "nt":
            process.terminate()
        else:
            process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise


with tempfile.TemporaryDirectory(prefix="helioforge-launch-check-") as folder:
    tmp = Path(folder)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    db = tmp / "original.sqlite3"
    env = os.environ.copy()
    env["HELIOFORGE_DB"] = str(db)
    env["ENABLE_OPENAI"] = "true"  # Launcher must deliberately override this.
    preflight = subprocess.run(
        [sys.executable, "launch.py", "--check"], cwd=ROOT, capture_output=True, text=True
    )
    if not (preflight.returncode == 0):
        raise AssertionError(preflight.stderr)
    passed("Packaged runtime preflight passes without installing or starting anything")
    procs: list[subprocess.Popen[bytes]] = []
    try:

        def start(database: Path) -> tuple[subprocess.Popen[bytes], dict[str, object]]:
            env["HELIOFORGE_DB"] = str(database)
            with (tmp / (database.stem + "-server.log")).open("a") as log:
                proc = subprocess.Popen(  # noqa: S603 -- Current Python, fixed local module argv; owned process lifecycle; no shell.
                    [sys.executable, "launch.py", "--port", str(port), "--no-browser"],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            procs.append(proc)
            for _ in range(120):
                if proc.poll() is not None:
                    raise RuntimeError((tmp / (database.stem + "-server.log")).read_text())
                try:
                    response = httpx.get(url + "/api/health", timeout=0.4)
                    if response.status_code == 200:
                        health: object = response.json()
                        if not isinstance(health, dict) or any(not isinstance(key, str) for key in health):
                            raise ValueError("Local health response must be a JSON object")
                        return proc, health
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            raise RuntimeError("Local launcher did not become ready")

        process, health = start(db)
        if not (health["version"] == "0.3.0" and health["openai_enabled"] is False):
            raise AssertionError
        passed("Local launcher starts the packaged app on a custom loopback port with external AI disabled")
        with httpx.Client(base_url=url, timeout=40) as c:
            index = c.get("/")
            if not (index.status_code == 200 and "HelioForge Champion" in index.text):
                raise AssertionError
            if "script-src" not in index.headers["content-security-policy"]:
                raise AssertionError
            if not (c.get("/app.js").status_code == 200):
                raise AssertionError
            if not (c.get("/styles.css").status_code == 200):
                raise AssertionError
            passed("Served HTML, compiled JavaScript and CSS are available with the declared CSP header")
            if not (c.get("/api/health", headers={"host": "hostile.example"}).status_code == 400):
                raise AssertionError
            r = c.post("/api/storage/optimize", json={}, headers={"origin": url})
            if not (r.status_code == 200):
                raise AssertionError(r.text)
            saved = c.get("/api/runs/" + r.json()["run_id"]).json()
            passed(
                "Custom-port origin works; unexpected hostname is rejected;"
                " real synthetic calculation is saved"
            )
        collision = subprocess.run(  # noqa: S603 -- Current Python, fixed local module argv; owned process lifecycle; no shell.
            [sys.executable, "launch.py", "--port", str(port), "--no-browser"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if not (collision.returncode == 2 and "in use" in collision.stderr):
            raise AssertionError
        if process.poll() is not None:
            raise AssertionError
        passed("Occupied-port launch is rejected without stopping the already-running app")
        stop(process)
        process, health = start(db)
        if not (httpx.get(url + "/api/runs/" + saved["run_id"], timeout=10).json() == saved):
            raise AssertionError
        passed("A saved calculation survives a real process stop and restart with identical inputs/results")
        stop(process)
        backup = tmp / "restored.sqlite3"
        with sqlite3.connect(db) as source, sqlite3.connect(backup) as target:
            source.backup(target)
            if not (target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"):
                raise AssertionError
        process, health = start(backup)
        if not (httpx.get(url + "/api/runs/" + saved["run_id"], timeout=10).json() == saved):
            raise AssertionError
        passed(
            "Synthetic SQLite backup/restore rehearsal passes integrity"
            " check and restores the exact saved run"
        )
        stop(process)
        if os.name != "nt":
            if not (process.returncode == 0):
                raise AssertionError
            passed("Ctrl+C stops the local launcher and child server cleanly on the tested Linux environment")
    finally:
        for process in procs:
            stop(process)
report = {
    "checks_passed": len(checks),
    "checks": checks,
    "platform": sys.platform,
    "python": sys.version,
    "limitations": (
        "Small synthetic database only. Windows/macOS scripts and automatic browser opening not executed."
    ),
}
out = ROOT / "docs/champion/launcher-validation.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n")
print(f"{len(checks)} local launcher/recovery checks passed.")  # noqa: T201 -- CLI report output.
