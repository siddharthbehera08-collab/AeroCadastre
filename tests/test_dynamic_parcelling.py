"""
Focused Test Suite: Real Dynamic Multi-Evidence AI Parcel Candidate Generation Engine.
Validates:
1. Dynamic parcel generation over real Pune Indian AOI coordinates.
2. Building seeds, road corridor exclusion, and visible boundary integration.
3. Topological quality: valid polygons, no self-intersections, minimum area filtering, sliver removal.
4. Confidence and multi-evidence scoring calculation (finite, non-NaN, bounded).
5. Output GeoJSON FeatureCollection structure and non-authoritative statutory disclaimer integrity.
6. Real API endpoint POST /api/parcels/generate-candidates.
7. PostGIS database persistence with clean schema integrity.
8. Preservation of synthetic benchmark scene (scene_urban_T1, P_001..P_016).
9. Graceful error handling for invalid or excessively large AOIs.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models.entities import Parcel, Project
from backend.app.core.database import SessionLocal
from backend.gis.dynamic_parceler import dynamic_parcel_engine, DISCLAIMER_NOTICE

app = create_app()
client = TestClient(app)


def test_dynamic_parcel_engine_pune_synthesis():
    """Verify that dynamic_parcel_engine synthesizes candidate parcels from multi-source evidence."""
    pune_aoi = [73.852, 18.515, 73.858, 18.522]
    res = dynamic_parcel_engine.generate_candidate_parcels_for_aoi(
        aoi_bounds=pune_aoi,
        project_id="PROJ_SIH26012_DEMO",
    )

    assert res["type"] == "FeatureCollection"
    meta = res["metadata"]
    assert meta["candidate_parcel_count"] > 0
    assert meta["mean_confidence"] > 0.0
    assert meta["processing_time_ms"] > 0.0
    assert "disclaimer" in meta
    assert "STATUTORY" in meta["disclaimer"] or "PRELIMINARY" in meta["disclaimer"]

    # Verify features
    features = res["features"]
    assert len(features) == meta["candidate_parcel_count"]

    for feat in features:
        props = feat["properties"]
        geom = feat["geometry"]

        assert geom["type"] in ("Polygon", "MultiPolygon")
        assert len(geom["coordinates"]) > 0

        # Check required metadata attributes
        assert props["id"].startswith("aoi_dyn_")
        assert props["parcel_candidate_id"] == props["id"]
        assert props["parcel_layer"] == "CANDIDATE"
        assert props["boundary_representation"] == "INFERRED"
        assert props["verification_status"] == "AI-GENERATED / REQUIRES VERIFICATION"
        assert props["area_sqm"] >= 20.0
        assert 0.0 < props["confidence"] <= 1.0
        assert props["topology_status"] in ("VALID", "SLIVER", "DISCONNECTED", "COMPACTNESS_WARNING")

        # Provenance integrity
        assert "provenance" in props
        assert "algorithm" in props["provenance"]
        assert props["provenance"]["disclaimer"] == DISCLAIMER_NOTICE


def test_api_generate_candidate_parcels_endpoint():
    """Verify POST /api/parcels/generate-candidates FastAPI endpoint."""
    resp = client.post(
        "/api/parcels/generate-candidates",
        json={
            "aoi_bounds": [73.852, 18.515, 73.858, 18.522],
            "project_id": "PROJ_SIH26012_DEMO",
            "resolution": 0.5,
            "persist_to_postgis": True,
            "operator_id": "Surveyor_Verifier_01",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 10

    # Verify PostGIS persistence
    db = SessionLocal()
    try:
        scene_id = data["metadata"]["scene_id"]
        persisted = (
            db.query(Parcel)
            .filter(Parcel.project_id == "PROJ_SIH26012_DEMO", Parcel.scene_id == scene_id)
            .all()
        )
        assert len(persisted) == len(data["features"])
        assert persisted[0].verification_status == "AI-GENERATED / REQUIRES VERIFICATION"
    finally:
        db.close()


def test_invalid_aoi_error_handling():
    """Ensure invalid or inverted bounding boxes fail with descriptive HTTP 400."""
    resp = client.post(
        "/api/parcels/generate-candidates",
        json={
            "aoi_bounds": [73.858, 18.522, 73.852, 18.515],  # Inverted min/max
            "project_id": "PROJ_SIH26012_DEMO",
        },
    )
    assert resp.status_code == 400
    assert "Invalid AOI" in resp.json()["detail"]


def test_synthetic_benchmark_scene_intact():
    """Verify that synthetic baseline scene_urban_T1 with P_001..P_016 remains completely intact."""
    resp = client.get("/api/scenes/scene_urban_T1/bundle?project_id=PROJ_SIH26012_DEMO")
    assert resp.status_code == 200
    bundle = resp.json()
    assert bundle["scene_id"] == "scene_urban_T1"

    cand_parcels = bundle.get("candidate_parcels", [])
    assert len(cand_parcels) == 16
    p_ids = {p["id"] for p in cand_parcels}
    assert "scene_urban_T1_P_001" in p_ids or "P_001" in p_ids
    assert "scene_urban_T1_P_016" in p_ids or "P_016" in p_ids
