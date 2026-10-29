"""Verify frozen study examples without changing the artifact tested by CI.

Use the same 1e-12 absolute/relative cross-platform tolerance as the hybrid
asset checker, only for numerical values. Inputs, metadata and stored digests
remain exact. A difference beyond tolerance fails rather than regenerating it.
"""
import hashlib
import json
import math
import runpy
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

def _display_value(value: Any, limit: int = 180) -> Any:
    """Keep failure output readable when a mismatched value is a long default series."""
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if len(encoded) <= limit:
        return value
    return encoded[: limit - 3] + "..."


def catalogue_differences(expected: Any, actual: Any, *, limit: int = 12) -> tuple[list[dict[str, Any]], bool]:
    """Return bounded JSON paths and values for strict catalogue mismatches.

    This is diagnostic only: callers still use exact JSON-value equality to decide
    whether the frozen catalogue is stale.
    """
    if limit < 1:
        raise ValueError("Diagnostic limit must be positive.")

    differences: list[dict[str, Any]] = []
    truncated = False

    def add(path: str, expected_value: Any, actual_value: Any) -> None:
        nonlocal truncated
        if len(differences) >= limit:
            truncated = True
            return
        differences.append({
            "path": path,
            "expected": _display_value(expected_value),
            "actual": _display_value(actual_value),
        })

    def child_path(path: str, key: str) -> str:
        return f"{path}.{key}" if key.isidentifier() else f"{path}[{json.dumps(key)}]"

    def visit(want: Any, got: Any, path: str) -> None:
        if truncated or want == got:
            return
        if isinstance(want, dict) and isinstance(got, dict):
            for key in sorted(want.keys() - got.keys()):
                add(child_path(path, str(key)), want[key], "<missing>")
                if truncated:
                    return
            for key in sorted(got.keys() - want.keys()):
                add(child_path(path, str(key)), "<missing>", got[key])
                if truncated:
                    return
            for key in sorted(want.keys() & got.keys()):
                visit(want[key], got[key], child_path(path, str(key)))
                if truncated:
                    return
            return
        if isinstance(want, list) and isinstance(got, list):
            if len(want) != len(got):
                add(path + ".length", len(want), len(got))
                if truncated:
                    return
            for index, (left, right) in enumerate(zip(want, got)):
                visit(left, right, f"{path}[{index}]")
                if truncated:
                    return
            return
        add(path, want, got)

    visit(expected, actual, "$")
    return differences, truncated


def main() -> int:
    from helioforge.studies import StudyRequest, catalogue, evaluate

    compare = runpy.run_path(str(ROOT / "scripts/check-hybrid-assets.py"))["compare_results"]
    source = (ROOT / "apps/web/src/roadmap-data.ts").read_text(encoding="utf-8")
    bundle = json.loads(source.split("STUDY_BUNDLE: StudyBundle = ", 1)[1].rsplit("; }", 1)[0])
    current_catalogue = json.loads(json.dumps(catalogue()))
    if bundle["catalogue"] != current_catalogue:
        mismatch_paths, omitted = catalogue_differences(bundle["catalogue"], current_catalogue)
        print(json.dumps({
            "status": "FAIL",
            "check": "study_catalogue_exact_match",
            "mismatch_paths": mismatch_paths,
            "additional_differences_omitted": omitted,
        }, ensure_ascii=True), file=sys.stderr)
        raise AssertionError("Study catalogue is stale; see bounded mismatch paths above.")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
