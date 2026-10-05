"""
AeroCadastre GIS & Demonstrator Integration Test Suite.
Verifies:
1. Authentic Maharashtra Administrative Boundary hierarchy (/api/gis/admin-boundaries).
2. Authentic Pune Pilot Vector layers & GPU Champion Provenance (/api/gis/pune-pilot).
3. Pre-Cadastre and legal compliance notices on GIS endpoints.
4. Clean DB bootstrap stability (ModelRuns -> AIPredictions).
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_admin_boundaries_hierarchy():
    """Verify Maharashtra administrative boundary API returns State, District, and Taluk levels."""
    resp = client.get("/api/gis/admin-boundaries")
    assert resp.status_code == 200
    data = resp.json()

    assert data["type"] == "FeatureCollection"
    assert "metadata" in data
    assert data["metadata"]["state_name"] == "Maharashtra"
    assert data["metadata"]["census_2011_code"] == "27"

    features = data["features"]
    assert len(features) >= 3

    # Check State
    state_feat = next((f for f in features if f["properties"].get("admin_level") == 1), None)
    assert state_feat is not None
    assert state_feat["properties"]["state_name"] == "Maharashtra"

    # Check District
    dist_feat = next((f for f in features if f["properties"].get("admin_level") == 2), None)
    assert dist_feat is not None
    assert dist_feat["properties"]["district_name"] == "Pune"
    assert "hq_lat" in dist_feat["properties"] and "hq_lon" in dist_feat["properties"]

    # Check Taluks
    taluks = [f for f in features if f["properties"].get("admin_level") == 3]
    assert len(taluks) >= 2
    taluk_names = [t["properties"]["taluk_name"] for t in taluks]
    assert "Pune City" in taluk_names or "Haveli" in taluk_names


def test_pune_pilot_vector_and_gpu_champions():
    """Verify Pune historic core vector evidence and frozen GPU champion provenance."""
    resp = client.get("/api/gis/pune-pilot")
    assert resp.status_code == 200
    data = resp.json()

    # Vector counts
    assert data["building_count"] >= 1000
    assert data["road_count"] >= 300
    assert len(data["buildings_geojson"]["features"]) == data["building_count"]
    assert len(data["roads_geojson"]["features"]) == data["road_count"]

    # GPU Champion Checkpoints & SHA256 Verification
    champions = data["gpu_champions"]
    assert "model_a_building" in champions
    assert champions["model_a_building"]["id"] == "EXP_BUILDING_RESUNET_GPU_001"
    assert champions["model_a_building"]["sha256"] == "b3893d87a8364e05849ecc4b204932dbf1df8d57e204f128e784d44ef2894578"
    assert champions["model_a_building"]["test_iou"] >= 0.60

    assert "model_b_road" in champions
    assert champions["model_b_road"]["id"] == "EXP_ROAD_RESUNET_GPU_001"
    assert champions["model_b_road"]["sha256"] == "00782011614c8b11df32e559e1b61080090752b0574a9050bb07e243c0bfc816"
    assert champions["model_b_road"]["test_iou"] >= 0.30

    # Legal Disclaimer Integrity
    assert "INFERRED PARCEL EVIDENCE" in data["legal_notice"]
    assert "NOT AUTHORITATIVE TITLE" in data["legal_notice"]


def test_database_bootstrap_model_runs_fk_integrity():
    """Verify that ModelRun parent records exist and satisfy foreign key constraints for AIPredictions."""
    from backend.app.core.database import SessionLocal
    from backend.app.models.entities import ModelRun, AIPrediction

    db = SessionLocal()
    try:
        # Check that parent model runs exist
        m_runs = db.query(ModelRun).all()
        assert len(m_runs) >= 8
        m_ids = {r.id for r in m_runs}
        assert "EXP_003" in m_ids

        # Check AIPredictions referencing model_runs
        preds = db.query(AIPrediction).all()
        for p in preds:
            if p.model_run_id:
                assert p.model_run_id in m_ids, f"Orphaned model_run_id: {p.model_run_id}"
    finally:
        db.close()
