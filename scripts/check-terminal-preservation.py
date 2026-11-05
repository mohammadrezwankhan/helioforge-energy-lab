"""Fail if the Terminal release removes baseline source wiring or original model code."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
git_path = shutil.which("git")
if git_path is None:
    raise RuntimeError("Git is required for source-bound release evidence")
GIT = str(Path(git_path).resolve())
BASE = "d14b71f50ef400a50d3ccd4792dcd59238c64f56"


def original(name: str) -> str:
    return (
        subprocess.check_output([GIT, "show", f"{BASE}:{name}"], cwd=ROOT, timeout=120)  # noqa: S603 -- Resolved Git, fixed read-only argv, timeout120; no shell.
        .decode()
        .replace("\r\n", "\n")
    )


paths = (
    subprocess.check_output(  # noqa: S603 -- Resolved Git, fixed read-only argv, timeout120; no shell.
        [GIT, "ls-tree", "-r", "--name-only", BASE, "apps/web/src"], cwd=ROOT, timeout=120
    )
    .decode()
    .splitlines()
)
old = "\n".join(original(name) for name in paths if name.endswith(".ts"))
new = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "apps/web/src").glob("*.ts"))
data_names = set(re.findall(r"data-([a-z][a-z0-9-]+)", old))
if not (data_names <= set(re.findall(r"data-([a-z][a-z0-9-]+)", new))):
    raise AssertionError("Removed baseline data identity")
events = set(re.findall(r"addEventListener\(['\"]([^'\"]+)", old))
if not (events <= set(re.findall(r"addEventListener\(['\"]([^'\"]+)", new))):
    raise AssertionError("Removed baseline event kind")
api = "apps/api/helioforge/"
models = (
    subprocess.check_output(  # noqa: S603 -- Resolved Git, fixed read-only argv, timeout120; no shell.
        [GIT, "ls-tree", "-r", "--name-only", BASE, api + "engines"], cwd=ROOT, timeout=120
    )
    .decode()
    .splitlines()
)
preserved = [api + "main.py", api + "schemas.py", api + "data/hybrid_catalog.json", *models]
for name in preserved:
    if not (original(name) == (ROOT / name).read_text(encoding="utf-8")):
        raise AssertionError(f"Original model/contract changed: {name}")
print(  # noqa: T201 -- CLI report output.
    json.dumps(
        {
            "status": "passed",
            "baseline": BASE,
            "data_identities": len(data_names),
            "event_kinds": len(events),
            "unchanged_model_and_contract_files": len(preserved),
        }
    )
)
