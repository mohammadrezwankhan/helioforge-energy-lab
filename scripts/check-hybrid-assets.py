"""Check frozen artifacts against current Python models across supported platforms."""

from __future__ import annotations

import json
import math
import runpy
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]


def compare_results(
    actual: object,
    expected: object,
    path: str = "result",
    differences: list[float] | None = None,
) -> None:
    """Compare complete results without relaxing input or integrity checks."""
    if differences is None:
        differences = []
    if isinstance(expected, dict):
        if not (isinstance(actual, dict) and set(actual) == set(expected)):
            raise AssertionError(f"{path}: fields differ")
        for key in expected:
            compare_results(actual[key], expected[key], f"{path}.{key}", differences)
    elif isinstance(expected, list):
        if not (isinstance(actual, list) and len(actual) == len(expected)):
            raise AssertionError(f"{path}: series length differs")
        for index, (stored, generated) in enumerate(zip(actual, expected, strict=True)):
            compare_results(stored, generated, f"{path}[{index}]", differences)
    elif type(expected) in (int, float):
        if type(actual) not in (int, float):
            raise AssertionError(f"{path}: numeric type differs")
        actual_number = cast(int | float, actual)
        expected_number = cast(int | float, expected)
        if not (math.isfinite(actual_number) and math.isfinite(expected_number)):
            raise AssertionError(f"{path}: nonfinite result")
        if not (math.isclose(actual_number, expected_number, rel_tol=1e-12, abs_tol=1e-12)):
            raise AssertionError(
                f"{path}: {actual!r} differs from model value {expected!r} beyond platform roundoff"
            )
        if actual != expected:
            differences.append(abs(actual_number - expected_number))
    else:
        if not (type(actual) is type(expected) and actual == expected):
            raise AssertionError(f"{path}: metadata differs")


def check_bundle(
    actual: Mapping[str, object],
    expected: Mapping[str, object],
    digest: Callable[[object], str],
) -> list[float]:
    if not (set(actual) == set(expected)):
        raise AssertionError("Bundle fields differ")
    if not (actual["dataset_sha256"] == digest(actual["cases"])):
        raise AssertionError("Invalid dataset digest")
    for key in set(expected) - {"cases", "dataset_sha256"}:
        if not (actual[key] == expected[key]):
            raise AssertionError(f"Bundle metadata differs: {key}")
    actual_cases, expected_cases = actual["cases"], expected["cases"]
    if not isinstance(actual_cases, list) or not isinstance(expected_cases, list):
        raise AssertionError("Bundle cases must be arrays")
    if not (len(actual_cases) == len(expected_cases) == 285):
        raise AssertionError("Incorrect case count")
    differences: list[float] = []
    for stored, generated in zip(actual_cases, expected_cases, strict=True):
        if not isinstance(stored, dict) or not isinstance(generated, dict):
            raise AssertionError("Bundle cases must be objects")
        if not (set(stored) == set(generated)):
            raise AssertionError("Case fields differ")
        if not (stored["id"] == generated["id"]):
            raise AssertionError("Case order or identity differs")
        if not (digest(stored["inputs"]) == digest(generated["inputs"])):
            raise AssertionError(f"{stored['id']}: inputs differ")
        identifier = stored["id"]
        if not isinstance(identifier, str):
            raise AssertionError("Case identifier must be text")
        compare_results(stored["result"], generated["result"], identifier, differences)
    return differences


def main() -> None:
    generator = runpy.run_path(str(ROOT / "scripts/generate-hybrid-assets.py"))
    catalogue = generator["catalog"]()
    expected = generator["build_bundle"](catalogue)

    def read(name: str) -> object:
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    actual = read("hybrid-bundle.json")
    if not isinstance(actual, dict) or any(not isinstance(key, str) for key in actual):
        raise AssertionError("Frozen bundle must be a JSON object")
    differences = check_bundle(actual, expected, generator["digest"])
    if not (generator["digest"](read("hybrid-catalog.json")) == generator["digest"](catalogue)):
        raise AssertionError("Stale catalogue JSON")
    if not (
        generator["digest"](read("hybrid-default.json"))
        == generator["digest"](catalogue["systems"][0]["preset"])
    ):
        raise AssertionError("Stale default JSON")
    matrix = [
        {
            "system_id": system["id"],
            "scenario_id": scenario["id"],
            "capability": "inapplicable"
            if not generator["applicability"](system, scenario)
            else "runnable"
            if system["mode"] == scenario["mode"] == "screening"
            else "study",
        }
        for system in catalogue["systems"]
        for scenario in catalogue["scenarios"]
    ]
    if not (read("hybrid-matrix.json") == {"catalogue_version": catalogue["version"], "matrix": matrix}):
        raise AssertionError("Stale matrix JSON")
    source = (ROOT / "apps/web/src/hybrid-data.ts").read_text(encoding="utf-8")
    browser_catalogue = json.loads(source.split("HYBRID_CATALOG:HybridCatalogue = ", 1)[1].split(";\n", 1)[0])
    browser_bundle = json.loads(source.split("HYBRID_BUNDLE:HybridBundle = ", 1)[1].split(";\n", 1)[0])
    if not (generator["digest"](browser_catalogue) == generator["digest"](catalogue)):
        raise AssertionError("Stale browser catalogue")
    if not (generator["digest"](browser_bundle) == generator["digest"](actual)):
        raise AssertionError("Browser bundle differs from frozen JSON")
    print(  # noqa: T201 -- CLI report output.
        json.dumps(
            {
                "status": "passed",
                "cases": len(actual["cases"]),
                "stored_dataset_sha256": actual["dataset_sha256"],
                "regenerated_dataset_sha256": expected["dataset_sha256"],
                "roundoff_values": len(differences),
                "max_absolute_roundoff": max(differences, default=0),
            }
        )
    )


if __name__ == "__main__":
    main()
