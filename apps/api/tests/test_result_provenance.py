import hashlib
import json

from fastapi.testclient import TestClient

from helioforge.dashboard import dashboard
from helioforge.engines.hybrid import simulate_hybrid
from helioforge.engines.storage import demo_profile
from helioforge.hybrid import HybridRequest
from helioforge.main import app
from helioforge.provenance import PACKAGE_ROOT, attach_result_provenance, input_revision, source_revision
from helioforge.schemas import StorageRequest
from helioforge.store import Store
from helioforge.studies import StudyRequest, evaluate


def test_source_revision_is_deterministic_and_sensitive_to_model_dependency_bytes(tmp_path):
    (tmp_path / "engine.py").write_text("energy = load - pv\n", encoding="utf-8")
    (tmp_path / "schemas.py").write_text("load: float\n", encoding="utf-8")

    first = source_revision(("engine.py", "schemas.py"), root=tmp_path)
    assert first == source_revision(("schemas.py", "engine.py"), root=tmp_path)
    assert len(first) == 64

    (tmp_path / "schemas.py").write_text("load: float = 1\n", encoding="utf-8")
    assert first != source_revision(("engine.py", "schemas.py"), root=tmp_path)


def test_input_changes_do_not_change_code_revision_or_claim_approval(tmp_path):
    (tmp_path / "engine.py").write_text("energy = load - pv\n", encoding="utf-8")
    (tmp_path / "schemas.py").write_text("load: float\n", encoding="utf-8")
    result = {"model": "bounded-example-v1", "data_kind": "synthetic", "warnings": []}
    common = dict(
        model_id="bounded-example",
        source_files=("engine.py", "schemas.py"),
        source_root=tmp_path,
        units={"power": "kW", "energy": "kWh"},
        contract={"title": "Example model contract", "url": "https://example.test/model"},
    )

    first = attach_result_provenance(result, inputs={"load_kw": 10}, **common)
    second = attach_result_provenance(result, inputs={"load_kw": 11}, **common)

    assert first["provenance"]["source_revision"] == second["provenance"]["source_revision"]
    assert first["provenance"]["input"]["sha256"] != second["provenance"]["input"]["sha256"]
    assert first["source_revision"] == first["provenance"]["source_revision"]
    assert first["provenance"]["integrity"]["approval_status"] == "not_assessed"
    assert first["provenance"]["integrity"]["human_approval_recorded"] is False


def test_new_hybrid_result_binds_actual_source_dataset_and_endpoints():
    result = simulate_hybrid(HybridRequest())
    dataset_bytes = (PACKAGE_ROOT / "data" / "hybrid_catalog.json").read_bytes()
    assert result["provenance"]["schema"] == "helioforge.result-provenance.v1"
    assert result["source_revision"] == result["provenance"]["source_revision"]
    assert "provenance.py" in result["provenance"]["source_files"]
    assert result["dataset_revision"] == hashlib.sha256(dataset_bytes).hexdigest()
    assert result["provenance"]["horizon"] == {"duration_hours": result["duration_hours"]}
    assert result["provenance"]["endpoints"]["initial_energy_kwh"] == result["initial_energy_kwh"]
    assert result["provenance"]["endpoints"]["terminal_energy_kwh"] == result["terminal_energy_kwh"]
    assert result["provenance"]["units"] == {"power": "kW", "energy": "kWh", "cost": "EUR"}
    assert result["provenance"]["integrity"]["approval_status"] == "not_assessed"


def test_study_evidence_hash_covers_source_bound_provenance():
    result = evaluate(StudyRequest(study="pv-reserve"))
    without_evidence_hash = {key: value for key, value in result.items() if key != "evidence_sha256"}
    canonical = json.dumps(without_evidence_hash, sort_keys=True, separators=(",", ":"), allow_nan=False)

    assert result["provenance"]["source_revision"] == result["source_revision"]
    assert result["evidence_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert result["provenance"]["equations"] == result["equations"]
    assert result["provenance"]["sources"] == result["sources"]


def test_dashboard_snapshots_are_source_bound_but_existing_store_records_stay_unknown(tmp_path):
    dashboard.cache_clear()
    overview = dashboard()
    assert overview["dispatch"]["provenance"]["schema"] == "helioforge.result-provenance.v1"
    assert overview["finance"]["source_revision"] == overview["finance"]["provenance"]["source_revision"]

    store = Store(str(tmp_path / "legacy.sqlite3"))
    saved = store.save("hybrid", {"hours": 24}, {"model": "hybrid-greedy-hourly-v1", "warnings": []})
    legacy = store.get_run(saved["run_id"])
    assert legacy is not None
    assert "provenance" not in legacy["result"]
    assert "source_revision" not in legacy["result"]


def test_numerical_api_stores_provenance_before_export_and_does_not_stamp_council(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "api.sqlite3"))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        numeric = client.post("/api/finance/evaluate", json={})
        assert numeric.status_code == 200, numeric.text
        body = numeric.json()
        stored = client.get(f"/api/runs/{body['run_id']}").json()
        assert body["provenance"]["schema"] == "helioforge.result-provenance.v1"
        assert stored["result"]["provenance"] == body["provenance"]

        council = client.post("/api/council/review", json={})
        assert council.status_code == 200, council.text
        assert "provenance" not in council.json()


def test_default_storage_provenance_hashes_materialized_solver_inputs_but_store_keeps_request_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "storage-effective-inputs.sqlite3"))
    request = StorageRequest()
    submitted = request.model_dump()
    effective = {**submitted, **demo_profile(request.market)}
    dataset_fields = {"market": effective["market"], **{key: effective[key] for key in ("load_kw", "pv_kw", "import_eur_per_kwh", "export_eur_per_kwh")}}

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/storage/optimize", json={})
        assert response.status_code == 200, response.text
        body = response.json()
        stored = client.get(f"/api/runs/{body['run_id']}").json()

    assert stored["inputs"] == submitted, "the existing store request identity remains unchanged"
    assert stored["result"]["provenance"]["input"]["sha256"] == input_revision(effective)
    assert body["input_sha256"] == input_revision(submitted), "the run request digest remains the submitted JSON digest"
    assert body["provenance"]["input"]["sha256"] != body["input_sha256"]
    assert body["provenance"]["data"]["dataset_revision"] == input_revision(dataset_fields)
    assert body["provenance"]["data"]["identity"]["kind"] == "built_in_demo_profile"


def test_dashboard_storage_provenance_uses_same_materialized_profile():
    dashboard.cache_clear()
    request = StorageRequest()
    effective = {**request.model_dump(), **demo_profile(request.market)}
    dataset_fields = {"market": effective["market"], **{key: effective[key] for key in ("load_kw", "pv_kw", "import_eur_per_kwh", "export_eur_per_kwh")}}

    dispatch = dashboard()["dispatch"]

    assert dispatch["provenance"]["input"]["sha256"] == input_revision(effective)
    assert dispatch["provenance"]["data"]["dataset_revision"] == input_revision(dataset_fields)


def test_saved_council_evidence_includes_original_inputs_for_digest_review(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIOFORGE_DB", str(tmp_path / "council-api.sqlite3"))
    captured = {}

    def capture_local_council(request, evidence):
        captured["evidence"] = evidence
        return {"mode": "local", "warnings": []}

    monkeypatch.setattr("helioforge.main.local_council", capture_local_council)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        calculated = client.post("/api/finance/evaluate", json={}).json()
        reviewed = client.post("/api/council/review", json={"evidence_run_ids": [calculated["run_id"]]})

    assert reviewed.status_code == 200, reviewed.text
    supplied = captured["evidence"]["supplied_records"][0]
    assert supplied["inputs"]["capex_eur"] == 3_200_000
    assert supplied["input_sha256"] == calculated["input_sha256"]
