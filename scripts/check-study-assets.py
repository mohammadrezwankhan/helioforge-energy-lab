"""Verify frozen study examples without changing the artifact tested by CI.

Use the same 1e-12 absolute/relative cross-platform tolerance as the hybrid
asset checker, only for numerical values. Inputs, metadata and stored digests
remain exact. A difference beyond tolerance fails rather than regenerating it.
"""
import hashlib
import json
import math
import runpy
from pathlib import Path

from helioforge.studies import StudyRequest, catalogue, evaluate

ROOT = Path(__file__).resolve().parents[1]
compare = runpy.run_path(str(ROOT / "scripts/check-hybrid-assets.py"))["compare_results"]
source = (ROOT / "apps/web/src/roadmap-data.ts").read_text(encoding="utf-8")
bundle = json.loads(source.split("STUDY_BUNDLE: StudyBundle = ", 1)[1].rsplit("; }", 1)[0])
assert bundle["catalogue"] == json.loads(json.dumps(catalogue())), "Study catalogue is stale"
assert set(bundle["results"]) == {s["id"] for s in catalogue()}
differences = []
timing_observations = []
for sid, original in bundle["results"].items():
    stored = dict(original)
    digest = stored.pop("evidence_sha256")
    assert hashlib.sha256(json.dumps(stored, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest() == digest, sid
    fresh = json.loads(json.dumps(evaluate(StudyRequest(study=sid)), allow_nan=False))
    fresh.pop("evidence_sha256")
    assert stored["inputs"] == fresh["inputs"], sid + ": inputs changed"
    # Measured wall time is execution telemetry, not a deterministic model output.
    # Validate and retain both timings; compare all other output fields unchanged.
    if sid == "storage-annualopt":
        timings = {"stored_seconds": stored["details"].pop("solver_runtime_seconds"),
                   "fresh_seconds": fresh["details"].pop("solver_runtime_seconds")}
        assert all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in timings.values())
        timing_observations.append({"path": sid + ".details.solver_runtime_seconds", **timings})
    compare(stored, fresh, sid, differences)
print(json.dumps({"status": "PASS", "studies": len(bundle["results"]), "numeric_roundoff_differences": len(differences),
                  "max_roundoff": max(differences, default=0), "execution_timing_observations": timing_observations,
                  "artifact_rewritten": False}))
