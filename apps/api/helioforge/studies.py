"""Catalogue and provenance boundary for separately scoped roadmap experiments."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import Field

from helioforge.engines import (
    control_studies,
    decision_studies,
    engineering_studies,
    physical_studies,
    planning_studies,
    toolkit_studies,
    workflow_studies,
)
from helioforge.engines.study_types import StudyDefinition, StudyModule
from helioforge.provenance import PACKAGE_ROOT, REPOSITORY, attach_result_provenance
from helioforge.schemas import StrictModel

MODULES: tuple[StudyModule, ...] = (
    engineering_studies,
    decision_studies,
    workflow_studies,
    toolkit_studies,
    physical_studies,
    planning_studies,
    control_studies,
)


class StudyRequest(StrictModel):
    study: str = Field(min_length=3, max_length=80, pattern=r"^[a-z]+-[a-z]+$")
    inputs: dict[str, Any] = Field(default_factory=dict, max_length=40)


def catalogue() -> list[StudyDefinition]:
    return deepcopy([study for module in MODULES for study in module.STUDIES])


def evaluate(p: StudyRequest) -> dict[str, Any]:
    for module in MODULES:
        study = next((s for s in module.STUDIES if s["id"] == p.study), None)
        if study is None:
            continue
        inputs: dict[str, object] = {
            f["name"]: deepcopy(f["default"])
            for f in [*study.get("fields", []), *study.get("data_fields", [])]
        }
        inputs.update(p.inputs)
        # The numerical engines have a concrete StudyResult contract. The
        # provenance/API envelope is the existing heterogeneous JSON boundary.
        result: dict[str, Any] = dict(module.run(p.study, inputs))
        result.update(
            {
                "study": p.study,
                "model_version": "roadmap-screen-v1",
                "inputs": inputs,
                "data_kind": "synthetic_or_user_supplied_unverified",
                "equations": study.get("equations", []),
                "limitations": study.get("limitations", []),
                "sources": study.get("sources", []),
            }
        )
        if module.__file__ is None:
            raise ValueError(f"Study module has no source file: {module.__name__}")
        module_path = Path(module.__file__).resolve().relative_to(PACKAGE_ROOT).as_posix()
        source_files = ["studies.py", "schemas.py", "engines/study_types.py", module_path]
        # These study modules call the shared finance engine directly; include
        # that numerical dependency in the same source digest.
        if module.__name__.endswith((".decision_studies", ".toolkit_studies")):
            source_files.append("engines/finance.py")
        model_inputs = {"study": p.study, "inputs": inputs}
        horizon: dict[str, object] = {
            key: inputs[key]
            for key in ("duration_hours", "hours", "years", "start_year", "interval_hours")
            if key in inputs
        }
        result = attach_result_provenance(
            result,
            model_id=f"study:{p.study}",
            inputs=model_inputs,
            source_files=source_files,
            units={metric["label"]: str(metric.get("unit", "")) for metric in result.get("metrics", [])},
            horizon=horizon or None,
            data_identity={"study_id": p.study, "kind": result["data_kind"]},
            contract={
                "title": str(study.get("title") or p.study),
                "url": f"{REPOSITORY}apps/api/helioforge/{module_path}",
            },
        )
        # Fail closed rather than emitting JavaScript-invalid NaN/Infinity.
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
        result["evidence_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        return result
    raise ValueError("Unknown experimental study.")
