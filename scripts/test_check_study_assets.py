"""Focused regression tests for study catalogue mismatch diagnostics."""
from __future__ import annotations

import importlib.util
from pathlib import Path

CHECKER_PATH = Path(__file__).with_name("check-study-assets.py")
SPEC = importlib.util.spec_from_file_location("check_study_assets", CHECKER_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def test_equal_json_catalogues_produce_no_diagnostics():
    frozen = {"studies": [{"id": "sample", "fields": [{"name": "load", "default": 1.25}]}]}
    assert CHECKER.catalogue_differences(frozen, frozen) == ([], False)


def test_catalogue_diagnostic_names_nested_path_and_values():
    frozen = {"studies": [{"id": "sample", "fields": [{"name": "load", "default": 1.25}]}]}
    current = {"studies": [{"id": "sample", "fields": [{"name": "load", "default": 1.2500000000000002}]}]}

    differences, omitted = CHECKER.catalogue_differences(frozen, current)

    assert differences == [{
        "path": "$.studies[0].fields[0].default",
        "expected": 1.25,
        "actual": 1.2500000000000002,
    }]
    assert omitted is False
    assert frozen != current  # The diagnostic does not make exact catalogue equality tolerant.


def test_catalogue_diagnostic_caps_mismatch_count_and_long_values():
    frozen = {"a": "x" * 500, "b": 1, "c": 2}
    current = {"a": "y" * 500, "b": 3, "c": 4}

    differences, omitted = CHECKER.catalogue_differences(frozen, current, limit=1)

    assert len(differences) == 1
    assert differences[0]["path"] == "$.a"
    assert differences[0]["expected"].endswith("...")
    assert differences[0]["actual"].endswith("...")
    assert omitted is True
