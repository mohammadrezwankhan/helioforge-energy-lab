"""Catalogue and provenance boundary for separately scoped roadmap experiments."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from pydantic import Field

from helioforge.engines import decision_studies, engineering_studies, toolkit_studies, workflow_studies
from helioforge.schemas import StrictModel

MODULES = (engineering_studies, decision_studies, workflow_studies, toolkit_studies)


class StudyRequest(StrictModel):
    study: str = Field(min_length=3, max_length=80, pattern=r"^[a-z]+-[a-z]+$")
    inputs: dict[str, Any] = Field(default_factory=dict, max_length=40)


def catalogue() -> list[dict]:
    return deepcopy([study for module in MODULES for study in module.STUDIES])


def evaluate(p: StudyRequest) -> dict:
    for module in MODULES:
        study = next((s for s in module.STUDIES if s["id"] == p.study), None)
        if study is None:
            continue
        inputs = {
            f["name"]: deepcopy(f["default"])
            for f in [*study.get("fields", []), *study.get("data_fields", [])]
        }
        inputs.update(p.inputs)
        result = module.run(p.study, inputs)
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
        # Fail closed rather than emitting JavaScript-invalid NaN/Infinity.
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
        result["evidence_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        return result
    raise ValueError("Unknown experimental study.")
