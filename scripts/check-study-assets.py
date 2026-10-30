"""Verify frozen study examples without changing the artifact tested by CI.

Use the same 1e-12 absolute/relative cross-platform tolerance as the hybrid
asset checker, only for numerical results. Replay inputs, metadata and stored
digests remain exact. The named generated bearing-fixture signals alone use a
formula-derived absolute roundoff bound for cross-platform math.sin values.
Frozen bytes are never rewritten.
"""
import hashlib
import json
import math
import struct
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _exact_json_equal(expected: Any, actual: Any) -> bool:
    """Compare JSON structures without Python's `1 == 1.0` type coercion."""
    if type(expected) is not type(actual):
        return False
    if isinstance(expected, float):
        return struct.pack(">d", expected) == struct.pack(">d", actual)
    if isinstance(expected, dict):
        return (expected.keys() == actual.keys()
                and all(_exact_json_equal(expected[key], actual[key]) for key in expected))
    if isinstance(expected, list):
        return (len(expected) == len(actual)
                and all(_exact_json_equal(left, right) for left, right in zip(expected, actual, strict=True)))
    return expected == actual


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
        if truncated or _exact_json_equal(want, got):
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


def float_ulp_distance(left: float, right: float) -> int:
    """Count representable binary64 steps between finite values."""
    if not math.isfinite(left) or not math.isfinite(right):
        raise ValueError("ULP distance is defined here only for finite values.")
    if left == right:
        return 0

    sign_bit = 1 << 63
    mask = (1 << 64) - 1

    def ordered(value: float) -> int:
        bits = struct.unpack(">Q", struct.pack(">d", value))[0]
        return (~bits & mask) if bits & sign_bit else bits | sign_bit

    return abs(ordered(left) - ordered(right))


_BEARING_FIXTURE_FIELDS = {"training_records", "heldout_records"}


def bearing_fixture_coefficients(field_name: str, record_id: Any) -> tuple[float, ...] | None:
    """Return the literal sine weights used for one named source fixture record."""
    if field_name == "training_records":
        for index in range(6):
            if record_id == f"synthetic-training-{index + 1}":
                return (1 + 0.005 * index, 0.008 + 0.0005 * index)
    elif field_name == "heldout_records":
        if record_id == "synthetic-heldout-normal":
            return (1.0, 0.009)
        if record_id == "synthetic-heldout-extra-tone":
            return (1.0, 0.009, 0.35)
    return None


def bearing_fixture_absolute_error_bound(field_name: str, record_id: Any) -> float:
    """Bound platform roundoff from this fixture's weighted sine expression.

    The largest expression has three terms and four rounded multiplies/adds.
    `8 * epsilon * L1(weights)` is a conservative binary64 forward-error budget:
    it covers pairwise one-ULP libm variation and accumulated arithmetic rounding
    while remaining independent of cancellation in the final sample.
    """
    coefficients = bearing_fixture_coefficients(field_name, record_id)
    if coefficients is None:
        raise ValueError("No generated bearing-fixture formula is registered for this record.")
    return 8 * sys.float_info.epsilon * math.fsum(abs(value) for value in coefficients)


def _normalize_bearing_fixture_roundoff(expected: list, actual: list) -> tuple[list, int]:
    """Normalize only machine-level deltas in the named generated bearing signals."""
    normalized = deepcopy(actual)
    tolerated = 0
    if len(expected) != len(normalized):
        return normalized, tolerated

    for expected_study, actual_study in zip(expected, normalized, strict=True):
        if not isinstance(expected_study, dict) or not isinstance(actual_study, dict):
            continue
        if expected_study.get("id") != "research-bearing" or actual_study.get("id") != "research-bearing":
            continue

        for field_name in _BEARING_FIXTURE_FIELDS:
            expected_fields = [field for field in expected_study.get("data_fields", [])
                               if isinstance(field, dict) and field.get("name") == field_name]
            actual_fields = [field for field in actual_study.get("data_fields", [])
                             if isinstance(field, dict) and field.get("name") == field_name]
            if len(expected_fields) != 1 or len(actual_fields) != 1:
                continue
            expected_records = expected_fields[0].get("default")
            actual_records = actual_fields[0].get("default")
            if not isinstance(expected_records, list) or not isinstance(actual_records, list):
                continue
            if len(expected_records) != len(actual_records):
                continue

            for expected_record, actual_record in zip(expected_records, actual_records, strict=True):
                if not isinstance(expected_record, dict) or not isinstance(actual_record, dict):
                    continue
                if expected_record.get("record_id") != actual_record.get("record_id"):
                    continue
                coefficients = bearing_fixture_coefficients(field_name, expected_record.get("record_id"))
                if coefficients is None:
                    continue
                expected_signal = expected_record.get("signal")
                actual_signal = actual_record.get("signal")
                if not isinstance(expected_signal, list) or not isinstance(actual_signal, list):
                    continue
                if len(expected_signal) != len(actual_signal):
                    continue

                for index, (expected_value, actual_value) in enumerate(zip(expected_signal, actual_signal, strict=True)):
                    if type(expected_value) is type(actual_value) and expected_value == actual_value:
                        continue
                    if type(expected_value) is not float or type(actual_value) is not float:
                        continue
                    if not math.isfinite(expected_value) or not math.isfinite(actual_value):
                        continue
                    if abs(expected_value - actual_value) <= bearing_fixture_absolute_error_bound(
                        field_name, expected_record["record_id"]
                    ):
                        actual_signal[index] = expected_value
                        tolerated += 1

    return normalized, tolerated


def compare_catalogues(expected: list, actual: list, *, limit: int = 12) -> tuple[list[dict[str, Any]], bool, int]:
    """Compare catalogue exactly, except for bounded absolute error in bearing fixture samples."""
    normalized, tolerated = _normalize_bearing_fixture_roundoff(expected, actual)
    differences, omitted = catalogue_differences(expected, normalized, limit=limit)
    return differences, omitted, tolerated


def catalogue_default_inputs(study: dict) -> dict[str, Any]:
    """Materialize the same declared defaults as `studies.evaluate` for one frozen entry."""
    return {
        field["name"]: field["default"]
        for field in [*study.get("fields", []), *study.get("data_fields", [])]
    }


def validate_frozen_inputs(study_id: str, stored_inputs: Any, frozen_study: dict) -> None:
    """Require the replay record to use exactly the frozen catalogue defaults."""
    expected_inputs = catalogue_default_inputs(frozen_study)
    if not _exact_json_equal(stored_inputs, expected_inputs):
        differences, omitted = catalogue_differences(expected_inputs, stored_inputs)
        raise AssertionError(
            f"{study_id}: stored inputs differ from frozen catalogue defaults: "
            + json.dumps({"mismatch_paths": differences, "additional_differences_omitted": omitted}, ensure_ascii=True)
        )


def canonical_input_sha256(study_id: str, inputs: dict[str, Any]) -> str:
    payload = json.dumps({"study": study_id, "inputs": inputs}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _annual_storage_objective_change(result: Any) -> tuple[float, float] | None:
    """Return (exact formula value, reported value) for the annual objective delta."""
    labels = (
        "Optimal annual objective",
        "No-battery baseline objective",
        "Objective change versus baseline",
    )
    if not isinstance(result, dict) or not isinstance(result.get("metrics"), list):
        return None
    metrics = result["metrics"]
    if len(metrics) < 3:
        return None
    if any(not isinstance(metric, dict) or metric.get("label") != label or metric.get("unit") != "EUR"
           for metric, label in zip(metrics[:3], labels, strict=True)):
        return None
    values = [metric.get("value") for metric in metrics[:3]]
    if any(type(value) is not float or not math.isfinite(value) for value in values):
        return None
    return values[1] - values[0], values[2]


def _same_binary64(left: float, right: float) -> bool:
    return struct.pack(">d", left) == struct.pack(">d", right)


def _result_mismatches(actual: Any, expected: Any, path: str, skip_paths: set[str],
                       mismatches: list[dict[str, Any]], roundoff: list[dict[str, Any]]) -> None:
    """Collect every mismatch while retaining the established result tolerance."""
    if path in skip_paths:
        return
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(expected.keys() - actual.keys()):
            child = f"{path}.{key}" if str(key).isidentifier() else f"{path}[{json.dumps(key)}]"
            mismatches.append({"path": child, "expected": _display_value(expected[key]), "actual": "<missing>"})
        for key in sorted(actual.keys() - expected.keys()):
            child = f"{path}.{key}" if str(key).isidentifier() else f"{path}[{json.dumps(key)}]"
            mismatches.append({"path": child, "expected": "<missing>", "actual": _display_value(actual[key])})
        for key in sorted(expected.keys() & actual.keys()):
            child = f"{path}.{key}" if str(key).isidentifier() else f"{path}[{json.dumps(key)}]"
            _result_mismatches(actual[key], expected[key], child, skip_paths, mismatches, roundoff)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            mismatches.append({"path": path + ".length", "expected": len(expected), "actual": len(actual)})
        common_length = min(len(actual), len(expected))
        for index, (actual_item, expected_item) in enumerate(zip(actual[:common_length], expected[:common_length])):
            _result_mismatches(actual_item, expected_item, f"{path}[{index}]", skip_paths, mismatches, roundoff)
        for index in range(common_length, len(expected)):
            mismatches.append({"path": f"{path}[{index}]", "expected": _display_value(expected[index]),
                               "actual": "<missing>"})
        for index in range(common_length, len(actual)):
            mismatches.append({"path": f"{path}[{index}]", "expected": "<missing>",
                               "actual": _display_value(actual[index])})
    elif type(expected) in (int, float) and type(actual) in (int, float):
        if not math.isfinite(actual) or not math.isfinite(expected):
            mismatches.append({"path": path, "expected": expected, "actual": actual, "reason": "nonfinite numeric result"})
        elif math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
            if actual != expected:
                roundoff.append({"path": path, "absolute": abs(actual - expected)})
        else:
            mismatches.append({"path": path, "expected": expected, "actual": actual,
                               "reason": "numeric result exceeds existing 1e-12 relative/absolute tolerance"})
    elif type(actual) is not type(expected) or actual != expected:
        mismatches.append({"path": path, "expected": _display_value(expected), "actual": _display_value(actual),
                           "reason": "metadata differs"})


def compare_replayed_results(study_id: str, stored: Any, fresh: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compare a replay, treating a derived annual objective difference through its operands."""
    mismatches: list[dict[str, Any]] = []
    roundoff: list[dict[str, Any]] = []
    skip_paths: set[str] = set()
    if study_id == "storage-annualopt":
        path = study_id + ".metrics[2].value"
        stored_values = _annual_storage_objective_change(stored)
        fresh_values = _annual_storage_objective_change(fresh)
        for role, values in (("stored", stored_values), ("replayed", fresh_values)):
            if values is None or not _same_binary64(*values):
                expected_value = values[0] if values is not None else "<valid objective operands required>"
                actual_value = values[1] if values is not None else "<missing or malformed objective metrics>"
                mismatches.append({
                    "path": path,
                    "expected": expected_value,
                    "actual": actual_value,
                    "reason": f"{role} derived value is not exactly baseline minus optimized objective",
                })
        if stored_values is not None and fresh_values is not None \
                and _same_binary64(*stored_values) and _same_binary64(*fresh_values):
            # The delta is mathematically derived from metrics[0:2]. Comparing it
            # independently near zero magnifies harmless differences in those
            # large operands. Their existing tolerance implies the delta bound:
            # |Δ(baseline - objective)| <= |Δbaseline| + |Δobjective|.
            skip_paths.add(path)
    _result_mismatches(stored, fresh, study_id, skip_paths, mismatches, roundoff)
    return mismatches, roundoff


def main() -> int:
    from helioforge.studies import StudyRequest, catalogue, evaluate

    source = (ROOT / "apps/web/src/roadmap-data.ts").read_text(encoding="utf-8")
    bundle = json.loads(source.split("STUDY_BUNDLE: StudyBundle = ", 1)[1].rsplit("; }", 1)[0])
    current_catalogue = json.loads(json.dumps(catalogue()))
    mismatch_paths, omitted, tolerated_fixture_values = compare_catalogues(bundle["catalogue"], current_catalogue)
    if mismatch_paths:
        print(json.dumps({
            "status": "FAIL",
            "check": "study_catalogue_exact_match",
            "mismatch_paths": mismatch_paths,
            "additional_differences_omitted": omitted,
            "roundoff_bearing_fixture_samples": tolerated_fixture_values,
        }, ensure_ascii=True), file=sys.stderr)
        raise AssertionError("Study catalogue is stale; see bounded mismatch paths above.")
    frozen_catalogue_by_id = {study["id"]: study for study in bundle["catalogue"]}
    assert set(bundle["results"]) == {s["id"] for s in catalogue()}
    differences = []
    result_mismatches = []
    timing_observations = []
    derived_observations = []
    for sid, original in bundle["results"].items():
        stored = dict(original)
        digest = stored.pop("evidence_sha256")
        assert hashlib.sha256(json.dumps(stored, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest() == digest, sid
        validate_frozen_inputs(sid, stored["inputs"], frozen_catalogue_by_id[sid])
        assert stored["input_sha256"] == canonical_input_sha256(sid, stored["inputs"]), sid + ": input digest differs from frozen inputs"
        fresh = json.loads(json.dumps(evaluate(StudyRequest(study=sid, inputs=stored["inputs"])), allow_nan=False))
        fresh.pop("evidence_sha256")
        assert stored["inputs"] == fresh["inputs"], sid + ": inputs changed"
        assert stored["input_sha256"] == fresh["input_sha256"], sid + ": input digest changed during replay"
        # Measured wall time is execution telemetry, not a deterministic model output.
        # Validate and retain both timings; compare all other output fields unchanged.
        if sid == "storage-annualopt":
            timings = {"stored_seconds": stored["details"].pop("solver_runtime_seconds"),
                       "fresh_seconds": fresh["details"].pop("solver_runtime_seconds")}
            assert all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in timings.values())
            timing_observations.append({"path": sid + ".details.solver_runtime_seconds", **timings})
            derived_observations.append({"path": sid + ".metrics[2].value",
                                         "policy": "Exact baseline-minus-objective identity in both records; original tolerance on both operands.",
                                         "stored_objective_metrics": stored["metrics"][:3],
                                         "replayed_objective_metrics": fresh["metrics"][:3]})
        mismatches, roundoff = compare_replayed_results(sid, stored, fresh)
        result_mismatches.extend(mismatches)
        differences.extend(item["absolute"] for item in roundoff)
    if result_mismatches:
        print(json.dumps({"status": "FAIL", "check": "study_result_replay",
                          "mismatch_count": len(result_mismatches), "mismatches": result_mismatches},
                         ensure_ascii=True), file=sys.stderr)
        raise AssertionError(f"Study replay results differ at {len(result_mismatches)} paths; see diagnostics above.")
    print(json.dumps({"status": "PASS", "studies": len(bundle["results"]), "numeric_roundoff_differences": len(differences),
                      "max_roundoff": max(differences, default=0), "execution_timing_observations": timing_observations,
                      "derived_metric_observations": derived_observations,
                      "roundoff_bearing_fixture_samples": tolerated_fixture_values, "artifact_rewritten": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
