"""Frozen browser results must bind the actual packaged model source bytes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helioforge.provenance import source_revision
from tests.study_contract_assertions import record, sequence, text

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("relative", "marker", "expected_count"),
    [
        ("examples/hybrid-bundle.json", None, 285),
        ("examples/dashboard-snapshot.json", None, 8),
        ("apps/web/src/roadmap-data.ts", "STUDY_BUNDLE: StudyBundle = ", 59),
    ],
)
def test_frozen_result_source_fingerprints_match_the_packaged_implementation(
    relative: str, marker: str | None, expected_count: int
) -> None:
    artifact = ROOT / relative
    before = artifact.read_bytes()
    encoded = before.decode()
    if marker is not None:
        encoded = encoded.split(marker, 1)[1].rsplit("; }", 1)[0]
    pending: list[object] = [json.loads(encoded)]
    checked = 0
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if "provenance" in value:
                provenance = record(value["provenance"])
                paths = [text(item) for item in sequence(provenance["source_files"])]
                expected = source_revision(paths)
                assert provenance["source_revision"] == expected
                assert value["source_revision"] == expected
                checked += 1
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    assert checked == expected_count
    assert artifact.read_bytes() == before
