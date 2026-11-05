"""Malformed evidence metadata must produce findings without aborting review."""

import pytest

from helioforge.council import inspect_supplied_evidence, local_council
from helioforge.schemas import CouncilRequest


@pytest.mark.parametrize("kind", [None, True, 1, 1.5, {}, [], ""])
def test_unknown_kind_metadata_is_reported_without_a_lookup_crash(kind: object) -> None:
    review = inspect_supplied_evidence({"supplied_records": [{"kind": kind, "result": {}}]})
    assert review["status"] == "checklist_only"
    assert review["records_checked"] == 1
    assert review["records"][0]["kind"] == (kind if isinstance(kind, str) else None)
    assert "malformed_input_digest" in review["records"][0]["finding_codes"]


def test_missing_kind_and_result_preserve_separate_record_findings() -> None:
    review = inspect_supplied_evidence({"supplied_records": [{}, None]})
    assert review["records_checked"] == 2
    assert set(review["records"][0]["finding_codes"]) == {"malformed_result", "malformed_input_digest"}
    assert review["records"][1]["finding_codes"] == ["malformed_record"]


@pytest.mark.parametrize("value", [True, False, None, "24", float("nan"), float("inf")])
@pytest.mark.parametrize("section,number", [("dispatch", "duration_hours"), ("finance", "npv_eur")])
def test_local_review_rejects_nonfinite_or_nonnumeric_calculation_metadata(
    value: object, section: str, number: str
) -> None:
    evidence: dict[str, object] = {
        "dispatch": {"duration_hours": 24.0},
        "finance": {"npv_eur": 1000.0},
    }
    record = evidence[section]
    assert isinstance(record, dict)
    record[number] = value
    with pytest.raises(ValueError, match="must be a finite number"):
        local_council(CouncilRequest(), evidence)


@pytest.mark.parametrize("section", ["dispatch", "finance"])
@pytest.mark.parametrize("value", [None, [], "record"])
def test_local_review_rejects_nonobject_calculation_records(section: str, value: object) -> None:
    evidence: dict[str, object] = {
        "dispatch": {"duration_hours": 24.0},
        "finance": {"npv_eur": 1000.0},
    }
    evidence[section] = value
    with pytest.raises(ValueError, match="must be an object"):
        local_council(CouncilRequest(), evidence)
