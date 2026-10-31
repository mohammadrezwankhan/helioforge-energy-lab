"""Deterministic provenance envelopes for newly computed numerical results.

Digests identify the source bytes and effective inputs used to create a record.
They are not signatures, independent validation, or approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY = "https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/main/"
PROVENANCE_SCHEMA = "helioforge.result-provenance.v1"

_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "storage": {
        "source_files": ("engines/storage.py", "schemas.py"),
        "contract_title": "Storage dispatch methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"power": "kW", "energy": "kWh", "cost": "EUR"},
    },
    "finance": {
        "source_files": ("engines/finance.py", "schemas.py"),
        "contract_title": "Financial screening methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"currency": "EUR", "rate": "fraction per year"},
    },
    "pv": {
        "source_files": ("engines/finance.py", "schemas.py"),
        "contract_title": "PV screening methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"energy": "MWh", "currency": "EUR"},
    },
    "acquisition": {
        "source_files": ("engines/finance.py", "schemas.py"),
        "contract_title": "Acquisition screening methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"currency": "EUR", "multiple": "EV/EBITDA"},
    },
    "forecast": {
        "source_files": ("engines/forecast.py", "schemas.py"),
        "contract_title": "Price scenario model contract",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"price": "EUR/MWh", "probability": "fraction"},
    },
    "drift": {
        "source_files": ("engines/research.py", "schemas.py"),
        "contract_title": "Residual drift screening methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"residual": "fraction", "drift": "%", "threshold": "standard deviations"},
    },
    "reliability": {
        "source_files": ("engines/research.py", "schemas.py"),
        "contract_title": "Conditional reliability screening methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"time": "hours", "probability": "%"},
    },
    "sustainability": {
        "source_files": ("engines/research.py", "schemas.py"),
        "contract_title": "Sustainability screening methodology",
        "contract_path": "docs/METHODOLOGY.md",
        "units": {"generation": "MWh", "emissions": "tCO2e", "intensity": "gCO2e/kWh"},
    },
    "hybrid": {
        "source_files": ("engines/hybrid.py", "hybrid.py", "schemas.py"),
        "dataset_file": "data/hybrid_catalog.json",
        "contract_title": "Hybrid hourly screen methodology",
        "contract_path": "docs/HYBRID_METHODOLOGY.md",
        "units": {"power": "kW", "energy": "kWh", "cost": "EUR"},
    },
}


def _rooted_file(relative_path: str, root: Path) -> Path:
    base = root.resolve()
    candidate = (base / relative_path).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("Provenance paths must stay within the source root.")
    if not candidate.is_file():
        raise FileNotFoundError(f"Provenance source is missing: {relative_path}")
    return candidate


def source_revision(source_files: Sequence[str], *, root: Path = PACKAGE_ROOT) -> str:
    """Hash labeled, sorted source bytes so code changes invalidate the revision."""
    files = sorted(set(source_files))
    if not files:
        raise ValueError("At least one model source file is required.")
    digest = hashlib.sha256(b"helioforge.source-revision.v1\0")
    for relative_path in files:
        path = _rooted_file(relative_path, root)
        digest.update(relative_path.replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def dataset_revision(dataset_file: str, *, root: Path = PACKAGE_ROOT) -> str:
    """Return the raw SHA-256 of a packaged input catalogue or dataset."""
    return hashlib.sha256(_rooted_file(dataset_file, root).read_bytes()).hexdigest()


def input_revision(inputs: Mapping[str, Any]) -> str:
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_STORAGE_DATA_FIELDS = ("load_kw", "pv_kw", "import_eur_per_kwh", "export_eur_per_kwh")


def storage_provenance_inputs(inputs: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Materialize storage defaults through the solver's existing profile function."""
    effective = dict(inputs)
    uses_demo_profile = not bool(effective.get("load_kw"))
    if uses_demo_profile:
        # Use the engine's source of truth instead of duplicating its profile equations.
        from helioforge.engines.storage import demo_profile

        market = str(effective.get("market", "FR"))
        effective.update(demo_profile(market))
    market = str(effective.get("market", "FR"))
    dataset = {"market": market, **{key: effective[key] for key in _STORAGE_DATA_FIELDS}}
    identity = {
        "kind": "built_in_demo_profile" if uses_demo_profile else "user_supplied_unverified",
        "market": market,
        "series_fields": list(_STORAGE_DATA_FIELDS),
        "source": "helioforge.engines.storage.demo_profile" if uses_demo_profile else "submitted storage time series",
    }
    return effective, dataset, identity


def model_source_files(model_id: str, *, extra_source_files: Sequence[str] = ()) -> tuple[str, ...]:
    spec = _MODEL_SPECS.get(model_id)
    if spec is None:
        raise ValueError(f"No source contract is registered for model {model_id!r}.")
    return tuple(sorted(set((*spec["source_files"], *extra_source_files))))


def _contract(model_id: str, source_files: Sequence[str], custom: Mapping[str, Any] | None) -> dict[str, Any]:
    if custom:
        title = str(custom.get("title") or f"{model_id} model contract")
        url = str(custom.get("url") or "")
    else:
        spec = _MODEL_SPECS[model_id]
        title = str(spec["contract_title"])
        url = REPOSITORY + str(spec["contract_path"])
    return {
        "title": title,
        "url": url,
        "implementation_files": [f"helioforge/{path.replace(chr(92), '/') }" for path in source_files],
        "url_scope": "Reference link only; source_revision fingerprints the listed runtime bytes and does not attest that this URL currently contains those bytes.",
    }


def _horizon(inputs: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any] | None:
    if result.get("duration_hours") is not None:
        return {"duration_hours": result["duration_hours"]}
    if inputs.get("hours") is not None:
        return {"duration_hours": inputs["hours"]}
    years = inputs.get("years")
    if years is not None:
        horizon: dict[str, Any] = {"years": years}
        if inputs.get("start_year") is not None:
            horizon["start_year"] = inputs["start_year"]
        return horizon
    interval_count = result.get("intervals")
    if interval_count is not None:
        horizon = {"intervals": interval_count}
        if inputs.get("interval_hours") is not None:
            horizon["interval_hours"] = inputs["interval_hours"]
        return horizon
    return None


def attach_result_provenance(
    result: Mapping[str, Any],
    *,
    model_id: str,
    inputs: Mapping[str, Any],
    source_files: Sequence[str] | None = None,
    source_root: Path = PACKAGE_ROOT,
    dataset_file: str | None = None,
    dataset_root: Path = PACKAGE_ROOT,
    dataset_inputs: Mapping[str, Any] | None = None,
    data_identity: Mapping[str, Any] | None = None,
    units: Mapping[str, str] | None = None,
    horizon: Mapping[str, Any] | None = None,
    endpoints: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Copy a newly computed result and attach an explicit, non-approval envelope."""
    spec = _MODEL_SPECS.get(model_id)
    if source_files is None:
        if spec is None:
            raise ValueError(f"No source contract is registered for model {model_id!r}.")
        source_files = spec["source_files"]
    files = tuple(sorted(set(source_files) | ({"provenance.py"} if source_root.resolve() == PACKAGE_ROOT.resolve() else set())))
    source_digest = source_revision(files, root=source_root)
    input_digest = input_revision(inputs)
    if dataset_file is not None and dataset_inputs is not None:
        raise ValueError("Provide either a dataset file or dataset inputs, not both.")
    dataset_digest = (dataset_revision(dataset_file, root=dataset_root) if dataset_file else
                      input_revision(dataset_inputs) if dataset_inputs is not None else None)
    dataset_digest_scope = ("SHA-256 of exact packaged file bytes" if dataset_file else
                           "SHA-256 of canonical effective dataset inputs" if dataset_inputs is not None else None)
    effective_units = dict(units if units is not None else (spec or {}).get("units", {}))
    effective_horizon = dict(horizon) if horizon is not None else _horizon(inputs, result)
    effective_endpoints = dict(endpoints or {})
    if not effective_endpoints and result.get("initial_energy_kwh") is not None:
        effective_endpoints = {
            "initial_energy_kwh": result.get("initial_energy_kwh"),
            "terminal_energy_kwh": result.get("terminal_energy_kwh"),
            "terminal_soc_policy": "Unconstrained; both energy endpoints are reported.",
        }
    model_version = result.get("model") or result.get("model_version")
    external_sources = result.get("sources", [])
    if not isinstance(external_sources, list):
        external_sources = []
    equations = result.get("equations", [])
    if not isinstance(equations, list):
        equations = []
    limitations = result.get("limitations", result.get("warnings", []))
    if not isinstance(limitations, list):
        limitations = []
    envelope = {
        "schema": PROVENANCE_SCHEMA,
        "status": "source_bound",
        "model": {"id": model_id, "version": model_version},
        "source_revision": source_digest,
        "source_files": [path.replace("\\", "/") for path in files],
        "input": {"sha256": input_digest, "scope": "effective_model_inputs", "canonicalization": "UTF-8 JSON, sorted keys, compact separators, non-finite numbers rejected."},
        "data": {
            "kind": result.get("data_kind", "unknown"),
            "identity": dict(data_identity) if data_identity is not None else None,
            "dataset_revision": dataset_digest,
            "dataset_revision_scope": dataset_digest_scope,
        },
        "units": effective_units,
        "horizon": effective_horizon,
        "endpoints": effective_endpoints,
        "model_contract": _contract(model_id, files, contract) if model_id in _MODEL_SPECS or contract else {
            "title": model_id,
            "url": "",
            "implementation_files": [f"helioforge/{path.replace(chr(92), '/') }" for path in files],
            "url_scope": "Reference path only.",
        },
        "equations": equations,
        "sources": external_sources,
        "limitations": limitations,
        "integrity": {
            "source_hash_algorithm": "SHA-256",
            "input_hash_algorithm": "SHA-256",
            "source_digest_scope": "Labeled bytes of the listed model implementation, schemas, internal dependencies, and provenance envelope helper.",
            "signature_verified": False,
            "human_approval_recorded": False,
            "approval_status": "not_assessed",
        },
    }
    enriched = dict(result)
    enriched["provenance"] = envelope
    enriched["source_revision"] = source_digest
    enriched["input_sha256"] = input_digest
    if dataset_digest is not None:
        enriched["dataset_revision"] = dataset_digest
    return enriched
