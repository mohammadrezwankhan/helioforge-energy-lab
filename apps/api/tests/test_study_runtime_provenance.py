"""Shared validation/dispatch code must participate in study source fingerprints."""

from pathlib import Path

from helioforge.provenance import PACKAGE_ROOT, source_revision
from helioforge.studies import MODULES, StudyRequest, evaluate


def test_every_study_module_binds_the_shared_runtime_dispatch_dependency() -> None:
    for module in MODULES:
        result = evaluate(StudyRequest(study=module.STUDIES[0]["id"]))
        files = result["provenance"]["source_files"]
        assert "engines/study_types.py" in files
        assert result["source_revision"] == source_revision(files)


def test_runtime_dispatch_change_invalidates_the_bound_source_revision(tmp_path: Path) -> None:
    result = evaluate(StudyRequest(study="overview-weather"))
    files = result["provenance"]["source_files"]
    for relative in files:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((PACKAGE_ROOT / relative).read_bytes())
    assert source_revision(files, root=tmp_path) == result["source_revision"]

    dispatch_path = tmp_path / "engines/study_types.py"
    original_dispatch = (PACKAGE_ROOT / "engines/study_types.py").read_bytes()
    dispatch_path.write_bytes(original_dispatch + b"\n# Changed dispatch implementation.\n")

    assert source_revision(files, root=tmp_path) != result["source_revision"]
