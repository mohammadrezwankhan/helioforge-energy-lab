"""Regression for incomplete study bundles under optimized Python execution."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


def test_empty_result_set_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checker_path = Path(
        os.environ.get("STUDY_CHECKER_PATH", str(Path(__file__).with_name("check-study-assets.py")))
    )
    specification = importlib.util.spec_from_file_location("study_integrity_probe", checker_path)
    if specification is None or specification.loader is None:
        raise RuntimeError("The study checker could not be imported")
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    original = checker.ROOT / "apps/web/src/roadmap-data.ts"
    source = original.read_text(encoding="utf-8")
    prefix, payload = source.split("STUDY_BUNDLE: StudyBundle = ", 1)
    bundle = json.loads(payload.rsplit("; }", 1)[0])
    bundle["results"] = {}
    fixture = tmp_path / "apps/web/src/roadmap-data.ts"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(
        prefix + "STUDY_BUNDLE: StudyBundle = " + json.dumps(bundle) + "; }",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    with pytest.raises(AssertionError):
        checker.main()
