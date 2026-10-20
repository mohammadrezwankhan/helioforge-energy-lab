"""Build-time catalogue coverage and exact input/result provenance."""
import hashlib
import json
import runpy
from pathlib import Path

from helioforge.engines.hybrid import simulate_hybrid
from helioforge.hybrid import HybridRequest, applicability, catalog


def test_frozen_bundle_contains_every_eligible_preset_and_no_study_results():
    module = runpy.run_path(str(Path(__file__).resolve().parents[3] / "scripts/generate-hybrid-assets.py"))
    c = catalog()
    bundle = module["build_bundle"](c)
    assert bundle == module["build_bundle"](c)
    expected = {(system["id"], scenario["id"]) for system in c["systems"] for scenario in c["scenarios"]
                if system["mode"] == scenario["mode"] == "screening" and applicability(system, scenario)}
    assert len(expected) == len(bundle["cases"]) == 285
    assert {(entry["inputs"]["system_id"], entry["inputs"]["scenario_id"]) for entry in bundle["cases"]} == expected
    assert len({entry["id"] for entry in bundle["cases"]}) == 285
    for entry in bundle["cases"]:
        p = HybridRequest(**entry["inputs"])
        canonical = json.dumps(p.model_dump(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        assert entry["result"]["input_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
        result = {key: value for key, value in entry["result"].items()
                  if key not in {"bundle_case_id", "bundle_version", "input_sha256"}}
        assert result == simulate_hybrid(p)
        assert "run_id" not in entry["result"]
        assert entry["result"]["max_balance_residual_kw"] < 1e-6
    canonical = json.dumps(bundle["cases"], sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert bundle["dataset_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
