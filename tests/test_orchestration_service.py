"""
Unit & Integration Test Suite for AeroCadastre Orchestration Service & Ingestion API.
Tests project dataset registration, automated processing pipeline execution,
sub-resource querying, surveyor parcel verification, and GIS export.
Runs completely offline without PostgreSQL daemon dependency.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.app.services.orchestration_service import OrchestrationService, OrchestrationStore
from backend.app.schemas.job_schemas import (
    DatasetRegisterRequest,
    ProcessProjectRequest,
    JobStatusEnum,
)

client = TestClient(app)


@pytest.fixture
def clean_orchestrator():
    store = OrchestrationStore()
    return OrchestrationService(store=store)


def test_dataset_registration(clean_orchestrator):
    """Test registering a raster/vector dataset for a project."""
    req = DatasetRegisterRequest(
        dataset_name="pune_historic_core_ortho_synthetic.tif",
        modality="OPTICAL_VHR",
        file_path="data/synthetic/pune_ortho.tif",
        declared_crs="EPSG:32643",
        data_mode="SYNTHETIC",
        description="Controlled synthetic test orthomosaic for urban cadastral testing",
    )
    res = clean_orchestrator.register_dataset("PROJ_TEST_01", req)
    assert res["id"].startswith("DS_")
    assert res["project_id"] == "PROJ_TEST_01"
    assert res["name"] == "pune_historic_core_ortho_synthetic.tif"

    datasets = clean_orchestrator.get_project_datasets("PROJ_TEST_01")
    assert len(datasets) == 1
    assert datasets[0]["id"] == res["id"]


def test_pipeline_execution_and_sub_resources(clean_orchestrator):
    """Test full 10-stage automated pipeline execution through the orchestrator."""
    proj_id = "PROJ_PIPELINE_DEMO"
    proc_req = ProcessProjectRequest(
        scene_id="SCENE_01",
        data_mode="SYNTHETIC",
        min_parcel_area_m2=50.0,
        operator_id="Senior_Surveyor_Rao",
    )
    job = clean_orchestrator.create_and_run_pipeline(proj_id, proc_req)

    assert job["job_id"].startswith("JOB_")
    assert job["status"] == JobStatusEnum.READY_FOR_REVIEW.value
    assert job["progress_pct"] == 100.0
    assert len(job["steps"]) == 7
    assert job["summary_metrics"]["candidate_parcels_count"] == 4

    # 1. Check Project Status
    status_info = clean_orchestrator.get_project_status(proj_id)
    assert status_info["parcel_count"] == 4
    assert status_info["is_ready_for_review"] is True

    # 2. Check Candidate Parcels GeoJSON
    parcels_fc = clean_orchestrator.get_project_parcels(proj_id)
    assert parcels_fc["type"] == "FeatureCollection"
    assert len(parcels_fc["features"]) == 4
    for feat in parcels_fc["features"]:
        assert feat["properties"]["ulpin_status"] == "NOT_ASSIGNED_PRE_CADASTRE"
        assert feat["properties"]["confidence"] >= 0.50

    # 3. Check Evidence Items
    evidence = clean_orchestrator.get_project_evidence(proj_id)
    assert len(evidence) > 0
    assert "fused_confidence" in evidence[0]

    # 4. Check Layers
    layers = clean_orchestrator.get_project_layers(proj_id)
    assert len(layers) == 5

    # 5. Check Verification Tasks
    v_tasks = clean_orchestrator.get_project_verification(proj_id)
    assert len(v_tasks) == 4
    assert v_tasks[0]["status"] == "PENDING"
    assert v_tasks[0]["priority"] in ("HIGH", "MEDIUM", "LOW")

    # 6. Check Audit Trail
    audit_logs = clean_orchestrator.get_project_audit(proj_id)
    assert len(audit_logs) >= 1
    assert audit_logs[0]["operation"] == "PROCESS_PIPELINE"


def test_surveyor_parcel_verification_and_export(clean_orchestrator):
    """Test surveyor decision update and parcel export."""
    proj_id = "PROJ_VERIFY_EXPORT"
    proc_req = ProcessProjectRequest(scene_id="SCENE_02", data_mode="SYNTHETIC")
    clean_orchestrator.create_and_run_pipeline(proj_id, proc_req)

    # Surveyor approves parcel CAND_PARCEL_0001
    v_res = clean_orchestrator.update_verification_decision(
        project_id=proj_id,
        parcel_id="CAND_PARCEL_0001",
        decision="APPROVED",
        operator_id="Senior_Surveyor_Rao",
        notes="Boundary verified against stone marker and building footprint",
    )
    assert v_res["status"] == "APPROVED"

    # Export candidate parcels
    export_res = clean_orchestrator.export_project_parcels(
        project_id=proj_id,
        scene_id="SCENE_02_EXPORT",
        export_format="GeoJSON",
    )
    assert export_res["validation_passed"] is True
    assert export_res["feature_count"] == 4
    assert Path(export_res["file_path"]).exists()


def test_fastapi_orchestration_endpoints():
    """Verify FastAPI routes for dataset registration, processing, and querying."""
    proj_id = "PROJ_API_TEST"

    # 1. Register Dataset
    ds_payload = {
        "dataset_name": "sample_drone.tif",
        "modality": "OPTICAL_VHR",
        "file_path": "data/sample.tif",
        "declared_crs": "EPSG:32643",
        "data_mode": "SYNTHETIC",
    }
    r_ds = client.post(f"/api/projects/{proj_id}/datasets", json=ds_payload)
    assert r_ds.status_code == 201
    assert r_ds.json()["name"] == "sample_drone.tif"

    # 2. Trigger Pipeline Processing
    proc_payload = {"scene_id": "SCENE_API_01", "data_mode": "SYNTHETIC"}
    r_proc = client.post(f"/api/projects/{proj_id}/process", json=proc_payload)
    assert r_proc.status_code == 200
    p_data = r_proc.json()
    assert p_data["status"] == "READY_FOR_REVIEW"
    assert p_data["summary_metrics"]["candidate_parcels_count"] == 4

    # 3. Query Status, Parcels, Layers, Verification, Audit
    r_stat = client.get(f"/api/projects/{proj_id}/status")
    assert r_stat.status_code == 200
    assert r_stat.json()["is_ready_for_review"] is True

    r_parcels = client.get(f"/api/projects/{proj_id}/parcels")
    assert r_parcels.status_code == 200
    assert len(r_parcels.json()["features"]) == 4

    r_layers = client.get(f"/api/projects/{proj_id}/layers")
    assert r_layers.status_code == 200
    assert len(r_layers.json()) == 5

    r_ver = client.get(f"/api/projects/{proj_id}/verification")
    assert r_ver.status_code == 200
    assert len(r_ver.json()) == 4

    # 4. Surveyor verify parcel
    r_v = client.post(
        f"/api/projects/{proj_id}/verify",
        json={"parcel_id": "CAND_PARCEL_0001", "decision": "APPROVED", "notes": "Approved by API"},
    )
    assert r_v.status_code == 200
    assert r_v.json()["status"] == "APPROVED"

    # 5. Export
    r_exp = client.post(
        f"/api/projects/{proj_id}/export",
        json={"export_format": "GeoJSON"},
    )
    assert r_exp.status_code == 200
    assert r_exp.json()["validation_passed"] is True
