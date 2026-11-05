"""Execute narrowly defined catalogue/study checks; never promote plans to passes."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import platform
import runpy
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
git_path = shutil.which("git")
if git_path is None:
    raise RuntimeError("Git is required for source-bound release evidence")
GIT = str(Path(git_path).resolve())
sys.path.insert(0, str(ROOT / "apps/api"))
from helioforge.engines.hybrid import simulate_hybrid  # noqa: E402
from helioforge.hybrid import applicability, get_scenario, get_system  # noqa: E402
from helioforge.studies import StudyRequest, catalogue, evaluate  # noqa: E402

OUT = Path(os.environ.get("HELIOFORGE_EVIDENCE_DIR", ROOT / "docs/remediation-20261028"))
PLAN = ROOT / "docs/remediation-20261028/source-plan"


def read(name: str) -> list[dict[str, str]]:
    with (PLAN / name).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if any(
        not isinstance(key, str) or not isinstance(value, str) for row in rows for key, value in row.items()
    ):
        raise ValueError(f"Acceptance plan {name} must contain complete text columns")
    return rows


def finite(value: object) -> bool:
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def main() -> int:
    source_sha = subprocess.check_output([GIT, "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=120).strip()  # noqa: S603 -- Resolved Git, fixed read-only argv, timeout120; no shell.
    catalogue_checks: list[dict[str, object]] = []
    study_checks: list[dict[str, object]] = []
    suites = {"catalogue": catalogue_checks, "studies": study_checks}
    report: dict[str, object] = {
        "schema": "helioforge.acceptance.inventory.v1",
        "started_at": datetime.now(UTC).isoformat(),
        "source_base": source_sha,
        "environment": platform.platform(),
        "python": sys.version,
        "scope": (
            "Local Python execution. Catalogue gates/invariants and study"
            " default finite/digest checks only; no"
            " browser/hand-benchmark/provider acceptance implied."
        ),
        "catalogue": catalogue_checks,
        "studies": study_checks,
    }
    rows = read("pairwise_test_design.csv")
    factors = ["workspace", "viewport_px", "engine", "interaction", "motion", "local_state", "load_condition"]
    levels = {f: sorted({r[f] for r in rows}) for f in factors}
    required = {
        (a, x, b, y) for a, b in itertools.combinations(factors, 2) for x in levels[a] for y in levels[b]
    }
    present = {(a, r[a], b, r[b]) for r in rows for a, b in itertools.combinations(factors, 2)}
    if not (len(rows) == 157 and len(required) == 620 and present == required):
        raise AssertionError
    if not (math.prod(map(len, levels.values())) == 33696):
        raise AssertionError
    report["pair_design_verification"] = {
        "status": "PASS",
        "source": "supplied companion CSV, not regenerated",
        "rows": len(rows),
        "pairs_required": len(required),
        "pairs_covered": len(present),
        "contexts": 33696,
        "levels": levels,
        "runtime_execution": "NOT_RUN in this script",
    }
    cases = read("catalogue_864_cases.csv")
    if not (
        len(cases) == 864 and Counter(r["classification"] for r in cases) == {"A": 285, "S": 349, "-": 230}
    ):
        raise AssertionError
    oracle = runpy.run_path(str(ROOT / "apps/api/tests/test_hybrid.py"))
    for row in cases:
        entry: dict[str, object] = {
            "test_id": row["case_id"],
            "architecture": row["architecture"],
            "scenario": row["scenario"],
            "expected": row["classification"],
            "owner": "integration",
            "status": "FAIL",
        }
        try:
            system, scenario = get_system(row["architecture"]), get_scenario(row["scenario"])
            actual = (
                "-"
                if not applicability(system, scenario)
                else "A"
                if system["mode"] == scenario["mode"] == "screening"
                else "S"
            )
            if not (actual == row["classification"]):
                raise AssertionError((actual, row["classification"]))
            if actual == "A":
                inputs = oracle["config"](system, scenario["id"])
                result = simulate_hybrid(inputs)
                oracle["invariant"](inputs, result)
                entry["actual"] = (
                    "Eligible local model executed; bus/SOC/service/direction/endpoint invariants pass."
                )
                entry["input_sha256"] = hashlib.sha256(
                    json.dumps(inputs.model_dump(), sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                entry["residual_kw"] = result["max_balance_residual_kw"]
            else:
                rejected = False
                try:
                    inputs = oracle["config"](system, scenario["id"])
                    simulate_hybrid(inputs)
                except ValueError as exc:
                    rejected = True
                    entry["actual"] = "Rejected local numerical path: " + str(exc)
                if not (rejected):
                    raise AssertionError("Unsupported configuration produced numeric success")
            entry["status"] = "PASS"
        except Exception as exc:
            entry["actual"] = repr(exc)
        catalogue_checks.append(entry)
    definitions = {s["id"]: s for s in catalogue()}
    study_rows = read("study_inventory_59.csv")
    if not (len(study_rows) == 59 and {s["study_id"] for s in study_rows} == set(definitions)):
        raise AssertionError
    for row in study_rows:
        sid = row["study_id"]
        entry = {
            "test_id": sid,
            "workspace": row["workspace"],
            "status": "FAIL",
            "owner": "integration",
            "expected": (
                "Default local run finite; exact study, inputs, equations,"
                " limitations, sources and valid content digest."
            ),
            "independent_hand_check": "NOT_RUN",
            "boundary_acceptance": "NOT_RUN in this suite",
            "export_UI": "NOT_RUN in this suite",
        }
        try:
            result = evaluate(StudyRequest(study=sid))
            digest = result.pop("evidence_sha256")
            if not (result["study"] == sid and finite(result)):
                raise AssertionError
            if not (result["inputs"] and result["limitations"] and result["sources"]):
                raise AssertionError
            if not (
                hashlib.sha256(
                    json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                ).hexdigest()
                == digest
            ):
                raise AssertionError
            entry.update(
                status="PASS",
                actual="Default local calculation and content digest verified.",
                evidence_sha256=digest,
                input_sha256=hashlib.sha256(
                    json.dumps(result["inputs"], sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            )
        except Exception as exc:
            entry["actual"] = repr(exc)
        study_checks.append(entry)
        print(sid, entry["status"], flush=True)  # noqa: T201 -- CLI report output.
    report["summary"] = {
        suite: dict(Counter(r["status"] for r in suites[suite])) for suite in ["catalogue", "studies"]
    }
    report["finished_at"] = datetime.now(UTC).isoformat()
    (OUT / "inventory-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"]))  # noqa: T201 -- CLI report output.
    return int(any(r["status"] == "FAIL" for suite in ["catalogue", "studies"] for r in suites[suite]))


if __name__ == "__main__":
    raise SystemExit(main())
