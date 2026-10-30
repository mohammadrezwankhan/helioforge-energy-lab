"""Focused regression tests for study bundle cross-platform replay."""
from __future__ import annotations

import importlib.util
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
