"""Source-bound records reject ambiguous identity and retain explicit model limits."""

import hashlib
from pathlib import Path

import pytest

from helioforge.provenance import (
    attach_result_provenance,
    dataset_revision,
    input_revision,
    model_source_files,
    source_revision,
    storage_provenance_inputs,
)


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    (tmp_path / "engine.py").write_bytes(b"energy = load - pv\n")
    return tmp_path


def test_source_identity_requires_present_files_within_its_root(source_root: Path) -> None:
    outside = source_root.parent / "outside-source.py"
    outside.write_bytes(b"outside this model\n")
    with pytest.raises(ValueError, match="within the source root"):
        source_revision(("../outside-source.py",), root=source_root)
    with pytest.raises(ValueError, match="within the source root"):
        dataset_revision("../outside-source.py", root=source_root)
    with pytest.raises(FileNotFoundError, match="source is missing"):
        source_revision(("missing.py",), root=source_root)
    with pytest.raises(FileNotFoundError, match="source is missing"):
        dataset_revision(".", root=source_root)
    with pytest.raises(ValueError, match="At least one"):
        source_revision((), root=source_root)


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_input_cannot_receive_a_provenance_digest(number: float) -> None:
    with pytest.raises(ValueError, match="Out of range float"):
        input_revision({"series": [1, number]})


def test_source_contract_requires_a_known_model_and_deduplicates_dependencies() -> None:
    with pytest.raises(ValueError, match="No source contract"):
        model_source_files("unregistered")
    with pytest.raises(ValueError, match="No source contract"):
        attach_result_provenance({}, model_id="unregistered", inputs={})
    assert model_source_files("storage", extra_source_files=("schemas.py", "custom.py")) == (
        "custom.py",
        "engines/storage.py",
        "schemas.py",
    )


def test_submitted_storage_series_are_preserved_and_labeled_unverified() -> None:
    supplied = {
        "market": "DE",
        "load_kw": [3, 4],
        "pv_kw": [1, 0],
        "import_eur_per_kwh": [-0.1, 0.2],
        "export_eur_per_kwh": [0, 0.05],
        "capacity_kwh": 8,
    }
    effective, dataset, identity = storage_provenance_inputs(supplied)
    assert effective == supplied
    assert effective is not supplied
    assert dataset == {key: value for key, value in supplied.items() if key != "capacity_kwh"}
    assert identity["kind"] == "user_supplied_unverified"
    assert identity["source"] == "submitted storage time series"
    assert identity["market"] == "DE"


def test_dataset_identity_requires_one_unambiguous_input_source(source_root: Path) -> None:
    with pytest.raises(ValueError, match="either a dataset file or dataset inputs"):
        attach_result_provenance(
            {},
            model_id="fixture",
            inputs={},
            source_files=("engine.py",),
            source_root=source_root,
            dataset_file="dataset.csv",
            dataset_root=source_root,
            dataset_inputs={"load_kw": [1]},
        )
    raw = b"timestamp,value\r\n2026-01-01T00:00:00Z,1\r\n"
    (source_root / "dataset.csv").write_bytes(raw)
    result = attach_result_provenance(
        {},
        model_id="fixture",
        inputs={},
        source_files=("engine.py",),
        source_root=source_root,
        dataset_file="dataset.csv",
        dataset_root=source_root,
    )
    assert result["dataset_revision"] == hashlib.sha256(raw).hexdigest()
    assert result["provenance"]["data"]["dataset_revision_scope"] == "SHA-256 of exact packaged file bytes"
    assert result["provenance"]["model_contract"]["implementation_files"] == ["helioforge/engine.py"]
    assert result["provenance"]["integrity"]["signature_verified"] is False


@pytest.mark.parametrize(
    "inputs,result,expected",
    [
        ({"hours": 12}, {}, {"duration_hours": 12}),
        ({"hours": 12, "years": 20}, {"duration_hours": 6}, {"duration_hours": 6}),
        ({"years": 3}, {}, {"years": 3}),
        ({"years": 3, "start_year": 2027}, {}, {"years": 3, "start_year": 2027}),
        ({"interval_hours": 0.25}, {"intervals": 4}, {"intervals": 4, "interval_hours": 0.25}),
        ({}, {"intervals": 4}, {"intervals": 4}),
        ({}, {}, None),
    ],
)
def test_horizon_reports_supplied_model_period_without_inventing_one(
    source_root: Path,
    inputs: dict[str, object],
    result: dict[str, object],
    expected: dict[str, object] | None,
) -> None:
    enriched = attach_result_provenance(
        result,
        model_id="fixture",
        inputs=inputs,
        source_files=("engine.py",),
        source_root=source_root,
    )
    assert enriched["provenance"]["horizon"] == expected
    assert "provenance" not in result


def test_malformed_optional_evidence_does_not_become_verified_metadata(source_root: Path) -> None:
    result = {
        "model_version": "fixture-v1",
        "sources": "not a source list",
        "equations": {"not": "a list"},
        "limitations": None,
        "initial_energy_kwh": 4,
        "terminal_energy_kwh": 3,
    }
    enriched = attach_result_provenance(
        result,
        model_id="fixture",
        inputs={},
        source_files=("engine.py",),
        source_root=source_root,
        contract={"title": None},
    )
    envelope = enriched["provenance"]
    assert envelope["sources"] == envelope["equations"] == envelope["limitations"] == []
    assert envelope["model"] == {"id": "fixture", "version": "fixture-v1"}
    assert envelope["model_contract"]["title"] == "fixture model contract"
    assert envelope["model_contract"]["url"] == ""
    assert envelope["endpoints"] == {
        "initial_energy_kwh": 4,
        "terminal_energy_kwh": 3,
        "terminal_soc_policy": "Unconstrained; both energy endpoints are reported.",
    }
    assert envelope["integrity"]["approval_status"] == "not_assessed"
    assert "provenance" not in result


def test_explicit_period_and_endpoint_contracts_take_precedence(source_root: Path) -> None:
    enriched = attach_result_provenance(
        {"duration_hours": 24, "initial_energy_kwh": 4, "terminal_energy_kwh": 3},
        model_id="fixture",
        inputs={"hours": 24},
        source_files=("engine.py",),
        source_root=source_root,
        horizon={"intervals": 2, "interval_hours": 0.5},
        endpoints={"terminal_soc_policy": "Fixed by the caller's model contract"},
    )
    assert enriched["provenance"]["horizon"] == {"intervals": 2, "interval_hours": 0.5}
    assert enriched["provenance"]["endpoints"] == {
        "terminal_soc_policy": "Fixed by the caller's model contract"
    }
