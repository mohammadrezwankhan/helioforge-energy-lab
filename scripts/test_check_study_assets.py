"""Focused regression tests for study bundle cross-platform replay."""
from __future__ import annotations

import importlib.util
import math
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


def test_two_ulp_bearing_difference_and_unrelated_numeric_change_fail():
    frozen_value = 0.005656854249491658
    two_ulps = math.nextafter(math.nextafter(frozen_value, math.inf), math.inf)
    frozen = _bearing_catalogue([frozen_value])
    too_far = _bearing_catalogue([two_ulps])

    differences, omitted, tolerated = CHECKER.compare_catalogues(frozen, too_far)

    assert differences == [{
        "path": "$[0].data_fields[0].default[0].signal[0]",
        "expected": frozen_value,
        "actual": two_ulps,
    }]
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
