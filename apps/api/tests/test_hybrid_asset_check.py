"""The platform check tolerates roundoff, never stale inputs or material results."""
import copy
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CHECKER = runpy.run_path(str(ROOT / "scripts/check-hybrid-assets.py"))
GENERATOR = runpy.run_path(str(ROOT / "scripts/generate-hybrid-assets.py"))


def test_platform_result_roundoff_is_accepted_and_measured():
    differences = []
    CHECKER["compare_results"]({"energy": [314.0, 0.0], "mode": "screening"},
                               {"energy": [314.0 + 5e-14, 2e-13], "mode": "screening"},
                               differences=differences)
    assert len(differences) == 2
    assert max(differences) == 2e-13


@pytest.mark.parametrize("actual,expected", [
    ({"cost": 100.01}, {"cost": 100.0}),
    ({"energy": [1.0]}, {"energy": [1.0, 2.0]}),
    ({"cost": 100.0, "extra": 1}, {"cost": 100.0}),
    ({"mode": "study"}, {"mode": "screening"}),
    ({"value": True}, {"value": 1}),
    ({"value": float("nan")}, {"value": 0.0}),
    ({"value": float("inf")}, {"value": float("inf")}),
])
def test_platform_check_rejects_material_or_structural_changes(actual, expected):
    with pytest.raises(AssertionError):
        CHECKER["compare_results"](actual, expected)


@pytest.fixture(scope="module")
def bundle():
    return GENERATOR["build_bundle"](GENERATOR["catalog"]())


def test_bundle_check_rejects_corrupt_digest(bundle):
    stored = copy.deepcopy(bundle)
    stored["dataset_sha256"] = "0" * 64
    with pytest.raises(AssertionError, match="digest"):
        CHECKER["check_bundle"](stored, bundle, GENERATOR["digest"])


def test_bundle_check_keeps_input_identity_exact_even_with_recomputed_digest(bundle):
    stored = copy.deepcopy(bundle)
    stored["cases"][0]["inputs"]["load_kw"] += 1e-10
    stored["dataset_sha256"] = GENERATOR["digest"](stored["cases"])
    with pytest.raises(AssertionError, match="inputs differ"):
        CHECKER["check_bundle"](stored, bundle, GENERATOR["digest"])


def test_bundle_check_rejects_material_output_even_with_recomputed_digest(bundle):
    stored = copy.deepcopy(bundle)
    stored["cases"][0]["result"]["max_balance_residual_kw"] = 0.01
    stored["dataset_sha256"] = GENERATOR["digest"](stored["cases"])
    with pytest.raises(AssertionError):
        CHECKER["check_bundle"](stored, bundle, GENERATOR["digest"])
