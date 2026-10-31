"""Execute narrowly defined catalogue/study checks; never promote plans to passes."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import math
import platform
import runpy
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from helioforge.hybrid import applicability, get_scenario, get_system  # noqa: E402
from helioforge.engines.hybrid import simulate_hybrid  # noqa: E402
from helioforge.studies import StudyRequest, catalogue, evaluate  # noqa: E402

OUT = Path(os.environ.get("HELIOFORGE_EVIDENCE_DIR", ROOT / "docs/remediation-20261028"))
PLAN = ROOT / "docs/remediation-20261028/source-plan"


def read(name):
    with (PLAN / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def finite(value):
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def main():
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = {"schema": "helioforge.acceptance.inventory.v1", "started_at": datetime.now(timezone.utc).isoformat(),
              "source_base": source_sha, "environment": platform.platform(), "python": sys.version,
              "scope": "Local Python execution. Catalogue gates/invariants and study default finite/digest checks only; no browser/hand-benchmark/provider acceptance implied.",
              "catalogue": [], "studies": []}
    rows = read("pairwise_test_design.csv")
    factors = ["workspace", "viewport_px", "engine", "interaction", "motion", "local_state", "load_condition"]
    levels = {f: sorted({r[f] for r in rows}) for f in factors}
    required = {(a, x, b, y) for a, b in itertools.combinations(factors, 2) for x in levels[a] for y in levels[b]}
    present = {(a, r[a], b, r[b]) for r in rows for a, b in itertools.combinations(factors, 2)}
    assert len(rows) == 157 and len(required) == 620 and present == required
    assert math.prod(map(len, levels.values())) == 33696
    report["pair_design_verification"] = {"status": "PASS", "source": "supplied companion CSV, not regenerated",
        "rows": len(rows), "pairs_required": len(required), "pairs_covered": len(present), "contexts": 33696,
        "levels": levels, "runtime_execution": "NOT_RUN in this script"}
    cases = read("catalogue_864_cases.csv")
    assert len(cases) == 864 and Counter(r["classification"] for r in cases) == {"A": 285, "S": 349, "-": 230}
    oracle = runpy.run_path(str(ROOT / "apps/api/tests/test_hybrid.py"))
    for row in cases:
        entry = {"test_id": row["case_id"], "architecture": row["architecture"], "scenario": row["scenario"],
                 "expected": row["classification"], "owner": "integration", "status": "FAIL"}
        try:
            system, scenario = get_system(row["architecture"]), get_scenario(row["scenario"])
            actual = "-" if not applicability(system, scenario) else "A" if system["mode"] == scenario["mode"] == "screening" else "S"
            assert actual == row["classification"], (actual, row["classification"])
            if actual == "A":
                inputs = oracle["config"](system, scenario["id"])
                result = simulate_hybrid(inputs)
                oracle["invariant"](inputs, result)
                entry["actual"] = "Eligible local model executed; bus/SOC/service/direction/endpoint invariants pass."
                entry["input_sha256"] = hashlib.sha256(json.dumps(inputs.model_dump(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                entry["residual_kw"] = result["max_balance_residual_kw"]
            else:
                rejected = False
                try:
                    inputs = oracle["config"](system, scenario["id"])
                    simulate_hybrid(inputs)
                except ValueError as exc:
                    rejected = True
                    entry["actual"] = "Rejected local numerical path: " + str(exc)
                assert rejected, "Unsupported configuration produced numeric success"
            entry["status"] = "PASS"
        except Exception as exc:
            entry["actual"] = repr(exc)
        report["catalogue"].append(entry)
    definitions = {s["id"]: s for s in catalogue()}
    study_rows = read("study_inventory_59.csv")
    assert len(study_rows) == 59 and {s["study_id"] for s in study_rows} == set(definitions)
    for row in study_rows:
        sid = row["study_id"]
        entry = {"test_id": sid, "workspace": row["workspace"], "status": "FAIL", "owner": "integration",
                 "expected": "Default local run finite; exact study, inputs, equations, limitations, sources and valid content digest.",
                 "independent_hand_check": "NOT_RUN", "boundary_acceptance": "NOT_RUN in this suite", "export_UI": "NOT_RUN in this suite"}
        try:
            result = evaluate(StudyRequest(study=sid))
            digest = result.pop("evidence_sha256")
            assert result["study"] == sid and finite(result)
            assert result["inputs"] and result["limitations"] and result["sources"]
            assert hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest() == digest
            entry.update(status="PASS", actual="Default local calculation and content digest verified.", evidence_sha256=digest,
                         input_sha256=hashlib.sha256(json.dumps(result["inputs"], sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        except Exception as exc:
            entry["actual"] = repr(exc)
        report["studies"].append(entry)
        print(sid, entry["status"], flush=True)
    report["summary"] = {suite: dict(Counter(r["status"] for r in report[suite])) for suite in ["catalogue", "studies"]}
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (OUT / "inventory-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"]))
    return int(any(r["status"] == "FAIL" for suite in ["catalogue", "studies"] for r in report[suite]))


if __name__ == "__main__":
    raise SystemExit(main())
