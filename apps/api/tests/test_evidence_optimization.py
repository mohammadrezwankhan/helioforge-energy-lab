"""Production evidence identity checks must survive optimized Python execution."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("optimized", [False, True])
def test_receipt_finalizer_rejects_runtime_hash_mismatch_before_reading_receipts(
    tmp_path: Path, optimized: bool
) -> None:
    root = Path(__file__).resolve().parents[3]
    isolated = tmp_path / "isolated-project"
    scripts = isolated / "scripts"
    scripts.mkdir(parents=True)
    for filename in ["finalize-followup.py", "xml_guard.py"]:
        shutil.copy2(root / "scripts" / filename, scripts / filename)
    site = tmp_path / "site"
    (site / "run").mkdir(parents=True)
    (site / "run/index.html").write_text("known fixture runtime", encoding="utf-8")
    (site / "app.json").write_text(json.dumps({"runtimeSha256": "0" * 64}), encoding="utf-8")
    options = ["-O"] if optimized else []
    # Fixed interpreter and copied owned script; no shell, external service or user-selected code.
    completed = subprocess.run(  # noqa: S603 -- isolated production guard regression with a 20-second bound.
        [sys.executable, *options, str(scripts / "finalize-followup.py")],
        cwd=isolated,
        env={**os.environ, "HELIOFORGE_ACCEPTANCE_SITE": str(site)},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode != 0
    assert "AssertionError" in completed.stderr
    assert "FileNotFoundError" not in completed.stderr
    assert not (isolated / "docs").exists()
