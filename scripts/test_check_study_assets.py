"""Focused regression tests for study bundle cross-platform replay."""
from __future__ import annotations

import importlib.util
import json
import math
from copy import deepcopy
from pathlib import Path

import pytest

CHECKER_PATH = Path(__file__).with_name("check-study-assets.py")
SPEC = importlib.util.spec_from_file_location("check_study_assets", CHECKER_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def _bearing_catalogue(signal: list[float], *, title: str = "Bearing spectrum") -> list[dict]:
    return [{
        "id": "research-bearing",
        "title": title,
        "fields": [{"name": "sample_rate_hz", "default": 256}],
        "data_fields": [{
            "name": "training_records",
            "default": [{"record_id": "synthetic-training-1", "signal": signal}],
        }],
    }]


def _bearing_catalogue_with_records() -> list[dict]:
    catalogue = _bearing_catalogue([0.0])
    catalogue[0]["data_fields"] = [
        {"name": "training_records", "default": [{
            "record_id": "synthetic-training-5", "signal": [0.0] * 152,
        }]},
        {"name": "heldout_records", "default": [
            {"record_id": "synthetic-heldout-normal", "signal": [0.0] * 177},
            {"record_id": "synthetic-heldout-extra-tone", "signal": [0.0] * 256},
        ]},
    ]
    return catalogue


def test_exact_catalogue_comparison_diagnoses_metadata_and_shape_changes():
    frozen = _bearing_catalogue([0.0, 0.25, -0.5])
    title_changed = _bearing_catalogue([0.0, 0.25, -0.5], title="Changed model title")
    missing_sample = _bearing_catalogue([0.0, 0.25])

    metadata_differences, omitted, tolerated = CHECKER.compare_catalogues(frozen, title_changed)
    shape_differences, shape_omitted, shape_tolerated = CHECKER.compare_catalogues(frozen, missing_sample)

    assert metadata_differences == [{
        "path": "$[0].title",
        "expected": "Bearing spectrum",
        "actual": "Changed model title",
    }]
    assert (omitted, tolerated) == (False, 0)
    assert shape_differences == [{
        "path": "$[0].data_fields[0].default[0].signal.length",
        "expected": 3,
        "actual": 2,
    }]
    assert (shape_omitted, shape_tolerated) == (False, 0)


def test_observed_bearing_fixture_one_ulp_difference_is_narrowly_accepted():
    frozen_value = 0.005656854249491658
    linux_value = 0.0056568542494916585
    assert math.nextafter(frozen_value, math.inf) == linux_value
    frozen = _bearing_catalogue([frozen_value])
    current = _bearing_catalogue([linux_value])

    differences, omitted, tolerated = CHECKER.compare_catalogues(frozen, current)

    assert differences == []
    assert omitted is False
    assert tolerated == 1


def test_all_eight_observed_compound_signal_deltas_fit_formula_bound():
    deltas = [
        ("training_records", 0, 32, 0.007071067811864741, 0.007071067811864742, 2),
        ("training_records", 0, 151, 0.8556710930136611, 0.8556710930136613, 2),
        ("heldout_records", 0, 176, -0.0034441508912851004, -0.0034441508912850995, 2),
        ("heldout_records", 1, 21, -0.01669301854734359, -0.016693018547343563, 8),
        ("heldout_records", 1, 36, 0.36644449514070854, 0.3664444951407084, 2),
        ("heldout_records", 1, 191, -0.20155573961773188, -0.201555739617732, 4),
        ("heldout_records", 1, 239, 0.32761971667177836, 0.32761971667177825, 2),
        ("heldout_records", 1, 255, -0.9129794256114008, -0.912979425611401, 2),
    ]
    frozen = _bearing_catalogue_with_records()
    current = deepcopy(frozen)
    roundoff_paths = {"training_records": 0, "heldout_records": 1}

    for field_name, record_index, sample_index, expected, actual, expected_ulps in deltas:
        field_index = roundoff_paths[field_name]
        expected_signal = frozen[0]["data_fields"][field_index]["default"][record_index]["signal"]
        actual_signal = current[0]["data_fields"][field_index]["default"][record_index]["signal"]
        expected_signal[sample_index] = expected
        actual_signal[sample_index] = actual
        record_id = frozen[0]["data_fields"][field_index]["default"][record_index]["record_id"]
        bound = CHECKER.bearing_fixture_absolute_error_bound(field_name, record_id)
        assert abs(actual - expected) <= bound
        assert CHECKER.float_ulp_distance(expected, actual) == expected_ulps

    differences, omitted, tolerated = CHECKER.compare_catalogues(frozen, current)

    assert differences == []
    assert omitted is False
    assert tolerated == 8
    assert max(abs(actual - expected) for _, _, _, expected, actual, _ in deltas) == 2.220446049250313e-16


def test_bearing_delta_beyond_formula_bound_and_other_numeric_changes_fail():
    frozen = _bearing_catalogue([0.0])
    current = deepcopy(frozen)
    bound = CHECKER.bearing_fixture_absolute_error_bound("training_records", "synthetic-training-1")
    current[0]["data_fields"][0]["default"][0]["signal"][0] = math.nextafter(bound, math.inf)

    differences, omitted, tolerated = CHECKER.compare_catalogues(frozen, current)

    assert differences[0]["path"] == "$[0].data_fields[0].default[0].signal[0]"
    assert differences[0]["expected"] == 0.0
    assert differences[0]["actual"] > bound
    assert (omitted, tolerated) == (False, 0)

    changed_metadata = [{
        **frozen[0],
        "fields": [{"name": "sample_rate_hz", "default": 256.0}],
    }]
    metadata_differences, _, _ = CHECKER.compare_catalogues(frozen, changed_metadata)
    assert metadata_differences[0]["path"] == "$[0].fields[0].default"


def test_stored_inputs_must_match_frozen_defaults_and_digest_exactly():
    study = {
        "id": "test-study",
        "fields": [{"name": "capacity_kw", "default": 10.0}],
        "data_fields": [{"name": "samples", "default": [1.0, 2.0]}],
    }
    frozen_inputs = CHECKER.catalogue_default_inputs(study)
    CHECKER.validate_frozen_inputs("test-study", frozen_inputs, study)
    frozen_digest = CHECKER.canonical_input_sha256("test-study", frozen_inputs)

    materially_changed = {**frozen_inputs, "capacity_kw": 11.0}
    with pytest.raises(AssertionError, match="stored inputs differ from frozen catalogue defaults"):
        CHECKER.validate_frozen_inputs("test-study", materially_changed, study)
    assert CHECKER.canonical_input_sha256("test-study", materially_changed) != frozen_digest

    representation_changed = {**frozen_inputs, "capacity_kw": 10}
    with pytest.raises(AssertionError, match="stored inputs differ from frozen catalogue defaults"):
        CHECKER.validate_frozen_inputs("test-study", representation_changed, study)
    assert CHECKER.canonical_input_sha256("test-study", representation_changed) != frozen_digest

    signed_zero_study = {"fields": [{"name": "capacity_kw", "default": 0.0}]}
    with pytest.raises(AssertionError, match="stored inputs differ from frozen catalogue defaults"):
        CHECKER.validate_frozen_inputs("test-study", {"capacity_kw": -0.0}, signed_zero_study)
    signed_zero_differences, _, _ = CHECKER.compare_catalogues(
        _bearing_catalogue([0.0]), _bearing_catalogue([-0.0]))
    assert signed_zero_differences[0]["path"] == "$[0].data_fields[0].default[0].signal[0]"


def test_full_replay_does_not_rewrite_frozen_asset_bytes(capsys):
    source = CHECKER.ROOT / "apps/web/src/roadmap-data.ts"
    before = source.read_bytes()

    assert CHECKER.main() == 0

    capsys.readouterr()
    assert source.read_bytes() == before


def test_catalogue_diagnostic_caps_mismatch_count_and_long_values():
    frozen = {"a": "x" * 500, "b": 1, "c": 2}
    current = {"a": "y" * 500, "b": 3, "c": 4}
    differences, omitted = CHECKER.catalogue_differences(frozen, current, limit=1)
    assert len(differences) == 1
    assert differences[0]["path"] == "$.a"
    assert differences[0]["expected"].endswith("...")
    assert differences[0]["actual"].endswith("...")
    assert omitted is True


def _annual_result(optimal: float, baseline: float) -> dict:
    return {"metrics": [
        {"label": "Optimal annual objective", "value": optimal, "unit": "EUR"},
        {"label": "No-battery baseline objective", "value": baseline, "unit": "EUR"},
        {"label": "Objective change versus baseline", "value": baseline - optimal, "unit": "EUR"},
    ]}


def test_annual_objective_change_uses_exact_identity_and_primitive_tolerance():
    baseline = 247361.86151999998
    stored = _annual_result(247361.86152000123, baseline)
    replay = _annual_result(247361.86152000117, baseline)

    mismatches, roundoff = CHECKER.compare_replayed_results("storage-annualopt", stored, replay)

    assert mismatches == []
    assert any(item["path"] == "storage-annualopt.metrics[0].value" for item in roundoff)
    assert abs(stored["metrics"][2]["value"] - replay["metrics"][2]["value"]) > 1e-12


def test_annual_objective_change_identity_and_primitive_result_mismatches_fail():
    baseline = 247361.86151999998
    stored = _annual_result(247361.86152000123, baseline)
    invalid_identity = deepcopy(stored)
    invalid_identity["metrics"][2]["value"] += 1e-8

    identity_mismatches, _ = CHECKER.compare_replayed_results(
        "storage-annualopt", stored, invalid_identity
    )
    assert any("derived value is not exactly baseline minus optimized objective" in item["reason"]
               for item in identity_mismatches)

    materially_changed_operand = _annual_result(247362.0, baseline)
    operand_mismatches, _ = CHECKER.compare_replayed_results(
        "storage-annualopt", stored, materially_changed_operand
    )
    assert any(item["path"] == "storage-annualopt.metrics[0].value" for item in operand_mismatches)


def test_result_comparison_collects_all_mismatch_paths_and_values():
    stored = {"metrics": [{"value": 1.0}, {"value": 2.0}, {"value": 3.0}]}
    replay = {"metrics": [{"value": 1.0}, {"value": 20.0}, {"value": 30.0}]}

    mismatches, _ = CHECKER.compare_replayed_results("other-study", stored, replay)

    assert [item["path"] for item in mismatches] == [
        "other-study.metrics[1].value", "other-study.metrics[2].value",
    ]
    assert [(item["expected"], item["actual"]) for item in mismatches] == [(20.0, 2.0), (30.0, 3.0)]


def test_result_comparison_reports_missing_list_values_with_their_paths():
    stored = {"series": [1.0, 2.0]}
    replay = {"series": [1.0, 2.0, 3.0]}

    mismatches, _ = CHECKER.compare_replayed_results("study", stored, replay)

    assert {item["path"]: (item["expected"], item["actual"]) for item in mismatches} == {
        "study.series.length": (3, 2),
        "study.series[2]": (3.0, "<missing>"),
    }


def _frozen_registration_result() -> dict:
    source = (CHECKER.ROOT / "apps/web/src/roadmap-data.ts").read_text(encoding="utf-8")
    bundle = json.loads(source.split("STUDY_BUNDLE: StudyBundle = ", 1)[1].rsplit("; }", 1)[0])
    return deepcopy(bundle["results"]["pilots-registration"])


def _registration_result_with_matrix(matrix: list[list[float]]) -> dict:
    result = _frozen_registration_result()
    result["details"]["rotation_matrix"] = deepcopy(matrix)
    observation, _ = CHECKER.registration_angle_observation(result)
    assert observation is not None
    result["metrics"][3]["value"] = observation["computed_angle_degrees"]
    return result


def test_frozen_registration_angle_reconstructs_from_its_saved_matrix():
    result = _frozen_registration_result()

    observation, error = CHECKER.registration_angle_observation(result)

    assert error is None
    assert observation is not None
    assert observation["rotation_matrix"] == result["details"]["rotation_matrix"]
    assert observation["reported_angle_degrees"] == result["metrics"][3]["value"]
    assert result["metrics"][3]["value"] == 1.2074182697257333e-06
    assert math.isclose(observation["computed_angle_degrees"], 1.2074182697257333e-06,
                        rel_tol=1e-12, abs_tol=1e-12)


def test_near_identity_registration_matrices_allow_only_their_own_derived_angles():
    frozen = _frozen_registration_result()
    stored_matrix = frozen["details"]["rotation_matrix"]
    replayed = _registration_result_with_matrix([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 0.999999999999996],
    ])
    stored_observation, stored_error = CHECKER.registration_angle_observation(frozen)
    replayed_observation, replayed_error = CHECKER.registration_angle_observation(replayed)

    assert stored_error is None and replayed_error is None
    assert stored_observation is not None and replayed_observation is not None
    assert math.isclose(replayed_observation["computed_angle_degrees"], 3.6222548091772e-06,
                        rel_tol=1e-12, abs_tol=1e-12)
    assert abs(stored_observation["computed_angle_degrees"] - replayed_observation["computed_angle_degrees"]) > 1e-12
    assert max(abs(stored_matrix[row][column] - replayed_observation["rotation_matrix"][row][column])
               for row in range(3) for column in range(3)) < 1e-12

    mismatches, _ = CHECKER.compare_replayed_results("pilots-registration", frozen, replayed)

    assert mismatches == []


def test_registration_angle_and_matrix_changes_fail_independently():
    frozen = _frozen_registration_result()
    altered_angle = deepcopy(frozen)
    altered_angle["metrics"][3]["value"] += 1e-7
    angle_mismatches, _ = CHECKER.compare_replayed_results("pilots-registration", frozen, altered_angle)
    assert any(item["path"] == "pilots-registration.metrics[3].value"
               and "own matrix" in item["reason"] for item in angle_mismatches)

    altered_matrix = deepcopy(frozen)
    altered_matrix["details"]["rotation_matrix"][0][1] += 1e-6
    matrix_observation, matrix_error = CHECKER.registration_angle_observation(altered_matrix)
    assert matrix_error is None and matrix_observation is not None
    altered_matrix["metrics"][3]["value"] = matrix_observation["computed_angle_degrees"]
    matrix_mismatches, _ = CHECKER.compare_replayed_results("pilots-registration", frozen, altered_matrix)
    assert any(item["path"] == "pilots-registration.details.rotation_matrix[0][1]"
               for item in matrix_mismatches)


def test_registration_angle_rejects_malformed_labels_shapes_types_and_nonfinite_values():
    frozen = _frozen_registration_result()
    cases = []

    wrong_label = deepcopy(frozen)
    wrong_label["metrics"][3]["label"] = "Rotation"
    cases.append((wrong_label, "pilots-registration.metrics[3]"))

    wrong_unit = deepcopy(frozen)
    wrong_unit["metrics"][3]["unit"] = "rad"
    cases.append((wrong_unit, "pilots-registration.metrics[3]"))

    missing_metric = deepcopy(frozen)
    missing_metric["metrics"].pop()
    cases.append((missing_metric, "pilots-registration.metrics.length"))

    bad_shape = deepcopy(frozen)
    bad_shape["details"]["rotation_matrix"][2].pop()
    cases.append((bad_shape, "pilots-registration.details.rotation_matrix"))

    bad_type = deepcopy(frozen)
    bad_type["details"]["rotation_matrix"][0][0] = 1
    cases.append((bad_type, "pilots-registration.details.rotation_matrix[0][0]"))

    nonfinite = deepcopy(frozen)
    nonfinite["details"]["rotation_matrix"][0][0] = math.inf
    cases.append((nonfinite, "pilots-registration.details.rotation_matrix[0][0]"))

    bad_angle_type = deepcopy(frozen)
    bad_angle_type["metrics"][3]["value"] = 0
    cases.append((bad_angle_type, "pilots-registration.metrics[3].value"))

    nonfinite_angle = deepcopy(frozen)
    nonfinite_angle["metrics"][3]["value"] = math.nan
    cases.append((nonfinite_angle, "pilots-registration.metrics[3].value"))

    for malformed, path in cases:
        mismatches, _ = CHECKER.compare_replayed_results("pilots-registration", frozen, malformed)
        assert any(item["path"] == path for item in mismatches), (path, mismatches)


def test_regular_nonzero_registration_rotation_replays_normally():
    theta = math.radians(37.0)
    result = _registration_result_with_matrix([
        [math.cos(theta), -math.sin(theta), 0.0],
        [math.sin(theta), math.cos(theta), 0.0],
        [0.0, 0.0, 1.0],
    ])

    observation, error = CHECKER.registration_angle_observation(result)
    mismatches, _ = CHECKER.compare_replayed_results("pilots-registration", result, deepcopy(result))

    assert error is None
    assert observation is not None
    assert math.isclose(observation["computed_angle_degrees"], 37.0, rel_tol=1e-12, abs_tol=1e-12)
    assert mismatches == []
