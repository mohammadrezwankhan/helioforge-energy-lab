"""Check frozen artifacts against current Python models across supported platforms."""
from __future__ import annotations

import json
import math
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def compare_results(actual, expected, path="result", differences=None):
    """Compare complete results without relaxing input or integrity checks."""
    if differences is None:
        differences = []
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), f"{path}: fields differ"
        for key in expected:
            compare_results(actual[key], expected[key], f"{path}.{key}", differences)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), f"{path}: series length differs"
        for index, (stored, generated) in enumerate(zip(actual, expected, strict=True)):
            compare_results(stored, generated, f"{path}[{index}]", differences)
    elif type(expected) in (int, float):
        assert type(actual) in (int, float), f"{path}: numeric type differs"
        assert math.isfinite(actual) and math.isfinite(expected), f"{path}: nonfinite result"
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (
            f"{path}: {actual!r} differs from model value {expected!r} beyond platform roundoff")
        if actual != expected:
            differences.append(abs(actual - expected))
    else:
        assert type(actual) is type(expected) and actual == expected, f"{path}: metadata differs"


def check_bundle(actual, expected, digest):
    assert set(actual) == set(expected), "Bundle fields differ"
    assert actual["dataset_sha256"] == digest(actual["cases"]), "Invalid dataset digest"
    for key in set(expected) - {"cases", "dataset_sha256"}:
        assert actual[key] == expected[key], f"Bundle metadata differs: {key}"
    assert len(actual["cases"]) == len(expected["cases"]) == 285, "Incorrect case count"
    differences = []
    for stored, generated in zip(actual["cases"], expected["cases"], strict=True):
        assert set(stored) == set(generated), "Case fields differ"
        assert stored["id"] == generated["id"], "Case order or identity differs"
        assert digest(stored["inputs"]) == digest(generated["inputs"]), f"{stored['id']}: inputs differ"
        compare_results(stored["result"], generated["result"], stored["id"], differences)
    return differences


def main():
    generator = runpy.run_path(str(ROOT / "scripts/generate-hybrid-assets.py"))
    catalogue = generator["catalog"]()
    expected = generator["build_bundle"](catalogue)
    read = lambda name: json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    actual = read("hybrid-bundle.json")
    differences = check_bundle(actual, expected, generator["digest"])
    assert generator["digest"](read("hybrid-catalog.json")) == generator["digest"](catalogue), "Stale catalogue JSON"
    assert generator["digest"](read("hybrid-default.json")) == generator["digest"](catalogue["systems"][0]["preset"]), "Stale default JSON"
    matrix = [{"system_id": system["id"], "scenario_id": scenario["id"],
               "capability": "inapplicable" if not generator["applicability"](system, scenario) else
               "runnable" if system["mode"] == scenario["mode"] == "screening" else "study"}
              for system in catalogue["systems"] for scenario in catalogue["scenarios"]]
    assert read("hybrid-matrix.json") == {"catalogue_version": catalogue["version"], "matrix": matrix}, "Stale matrix JSON"
    source = (ROOT / "apps/web/src/hybrid-data.ts").read_text(encoding="utf-8")
    browser_catalogue = json.loads(source.split("HYBRID_CATALOG:HybridCatalogue = ", 1)[1].split(";\n", 1)[0])
    browser_bundle = json.loads(source.split("HYBRID_BUNDLE:HybridBundle = ", 1)[1].split(";\n", 1)[0])
    assert generator["digest"](browser_catalogue) == generator["digest"](catalogue), "Stale browser catalogue"
    assert generator["digest"](browser_bundle) == generator["digest"](actual), "Browser bundle differs from frozen JSON"
    print(json.dumps({"status": "passed", "cases": len(actual["cases"]),
                      "stored_dataset_sha256": actual["dataset_sha256"],
                      "regenerated_dataset_sha256": expected["dataset_sha256"],
                      "roundoff_values": len(differences), "max_absolute_roundoff": max(differences, default=0)}))


if __name__ == "__main__":
    main()
