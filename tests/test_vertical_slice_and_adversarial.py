import io
import json
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape, mapping
from shapely.affinity import translate

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app
from backend.gis.topology import validate_parcels_topology


def _is_postgres_available():
    try:
        from backend.app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            return True
    except Exception:
        return False


postgres_available = _is_postgres_available()
pytestmark = pytest.mark.skipif(
    not postgres_available,
    reason="Full vertical slice integration test requires a live PostgreSQL/PostGIS instance listening on port 5432.",
)

client = TestClient(app)


def test_01_health_and_dashboard():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ONLINE"
    assert data["data_label"] == "SYNTHETIC DEMO DATA"
    assert "NOT LEGALLY AUTHORITATIVE" in data["legal_disclaimer"]

    r_dash = client.get("/api/dashboard?project_id=PROJ_SIH26012_DEMO&scene_id=scene_urban_T1")
    assert r_dash.status_code == 200
    metrics = r_dash.json()["metrics"]
    assert metrics["candidate_parcels"] >= 8
    assert metrics["buildings_detected"] >= 4
    assert metrics["roads_detected"] >= 2
    assert metrics["model_experiments"] >= 7


def test_02_full_24_step_vertical_slice():
    # Step 1-15: Run full GeoAI pipeline on scene_urban_T1
    r_pipe = client.post("/api/pipeline/run", json={"project_id": "PROJ_SIH26012_DEMO", "scene_id": "scene_urban_T1"})
    assert r_pipe.status_code == 200
    pipe_data = r_pipe.json()
    assert pipe_data["counts"]["candidate_parcels"] >= 8
    assert pipe_data["counts"]["topology_issues"] >= 1
    assert pipe_data["counts"]["anomalies_and_conflicts"] >= 1
    assert pipe_data["counts"]["temporal_changes"] >= 1
    assert pipe_data["counts"]["field_routes"] >= 1

    # Step 16: Load Web-GIS Bundle
    r_bundle = client.get("/api/scenes/scene_urban_T1/bundle")
    assert r_bundle.status_code == 200
    bundle = r_bundle.json()
    assert len(bundle["candidate_parcels"]) >= 8
    assert len(bundle["reference_parcels"]) >= 8
    assert len(bundle["council_decisions"]) == len(bundle["candidate_parcels"])
    assert len(bundle["verification_tasks"]) == len(bundle["candidate_parcels"])

    # Verify intentional overlap between P_001 and P_002 was detected by Topology Engine
    overlaps = [t for t in bundle["topology_issues"] if t["issue_type"] == "OVERLAP"]
    assert len(overlaps) >= 1

    # Step 17-20: Select parcel P_002, edit its geometry back to its reference non-overlapping position, mark HUMAN_VERIFIED
    ref_p2 = next(rp for rp in bundle["reference_parcels"] if rp["id"].endswith("_002"))
    r_edit = client.put(
        "/api/parcels/scene_urban_T1_P_002",
        json={
            "geometry": ref_p2["geometry"],
            "land_use_class": "commercial",
            "verification_status": "HUMAN_VERIFIED",
            "operator_id": "Senior_Surveyor_Rao",
            "reason": "Resolved boundary overlap with P_001 using drone ortho breakline",
        },
    )
    assert r_edit.status_code == 200
    edited = r_edit.json()
    assert edited["verification_status"] == "HUMAN_VERIFIED"
    assert edited["boundary_representation"] == "HUMAN_VERIFIED"
    assert edited["land_use_class"] == "commercial"
    assert edited["version"] >= 2

    # Check Version History (Parcel Time Machine)
    r_hist = client.get("/api/history/scene_urban_T1_P_002")
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert len(hist) >= 4  # T0, T1, T2 + HUMAN_EDIT
    assert any(h["temporal_epoch"] == "HUMAN_EDIT" for h in hist)

    # Check Human-in-the-Loop Feedback Store & Audit Logs
    r_fb = client.get("/api/feedback?project_id=PROJ_SIH26012_DEMO")
    assert r_fb.status_code == 200
    assert any(f["feature_id"] == "scene_urban_T1_P_002" for f in r_fb.json())

    r_aud = client.get("/api/audit-logs?project_id=PROJ_SIH26012_DEMO")
    assert r_aud.status_code == 200
    assert any(a["target_id"] == "scene_urban_T1_P_002" and a["operation"] == "UPDATE_PARCEL" for a in r_aud.json())

    # Step 21-23: Export GeoJSON, Shapefile, CSV, and GeoPackage and verify post-export integrity
    for fmt in ("GeoJSON", "Shapefile", "CSV", "GeoPackage"):
        r_exp = client.post(
            "/api/exports",
            json={"project_id": "PROJ_SIH26012_DEMO", "scene_id": "scene_urban_T1", "export_format": fmt},
        )
        assert r_exp.status_code in (200, 201)
        exp_data = r_exp.json()
        assert exp_data["validation_passed"] is True
        assert exp_data["feature_count"] == len(bundle["candidate_parcels"])
        assert Path(exp_data["file_path"]).exists()


def test_03_parcel_split_merge_and_create():
    # Test splitting parcel P_008 and then merging the two parts back
    r_split = client.post(
        "/api/parcels/scene_urban_T1_P_008/split",
        json={"split_axis": "VERTICAL", "split_ratio": 0.5, "operator_id": "Surveyor_01"},
    )
    assert r_split.status_code == 200
    sp = r_split.json()
    id_a = sp["parcel_a"]["id"]
    id_b = sp["parcel_b"]["id"]
    assert id_a == "scene_urban_T1_P_008"

    # Merge them back together
    r_merge = client.post(
        "/api/parcels/merge",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "parcel_id_a": id_a,
            "parcel_id_b": id_b,
            "operator_id": "Surveyor_01",
        },
    )
    assert r_merge.status_code == 200
    merged = r_merge.json()
    assert merged["id"] == id_a
    assert merged["verification_status"] == "HUMAN_VERIFIED"


def test_04_cadastral_ai_copilot():
    questions = [
        "Why was parcel P-003 flagged?",
        "Which parcels overlap?",
        "Show low-confidence parcels.",
        "Show buildings with low confidence.",
        "What changed between T0 and T2?",
        "Which areas need field verification?",
        "Compare P-002 with its previous state.",
    ]
    for q in questions:
        r = client.post(
            "/api/copilot/query",
            json={"project_id": "PROJ_SIH26012_DEMO", "scene_id": "scene_urban_T1", "question": q},
        )
        assert r.status_code == 200
        res = r.json()
        assert "answer" in res and len(res["answer"]) > 20
        assert "tool_invoked" in res


def test_05_adversarial_break_the_system():
    """
    Deliberately test adversarial & edge cases:
      - empty dataset upload
      - invalid GeoJSON upload
      - wrong CRS / out-of-bounds CRS
      - self-intersecting polygon
      - duplicate parcel
      - huge polygon (> 5,000,000 m^2)
      - tiny polygon (< 1 m^2)
      - missing scene / missing parcel
    """
    # 1. Empty file upload -> 400
    r_empty = client.post(
        "/api/upload",
        data={"project_id": "PROJ_SIH26012_DEMO", "declared_crs": "EPSG:4326"},
        files={"file": ("empty.geojson", b"", "application/json")},
    )
    assert r_empty.status_code == 400

    # 2. Corrupt / invalid GeoJSON upload -> 400
    r_corrupt = client.post(
        "/api/upload",
        data={"project_id": "PROJ_SIH26012_DEMO", "declared_crs": "EPSG:4326"},
        files={"file": ("bad.geojson", b"{not_valid_json", "application/json")},
    )
    assert r_corrupt.status_code == 400

    # 3. Tiny polygon (< 1 m^2) -> 400
    tiny_poly = {
        "type": "Polygon",
        "coordinates": [[[77.5920000, 12.9720000], [77.5920005, 12.9720000], [77.5920005, 12.9720005], [77.5920000, 12.9720005], [77.5920000, 12.9720000]]],
    }
    r_tiny = client.post(
        "/api/parcels",
        json={"project_id": "PROJ_SIH26012_DEMO", "scene_id": "scene_urban_T1", "geometry": tiny_poly},
    )
    assert r_tiny.status_code == 400

    # 4. Huge polygon (> 5,000,000 m^2) -> 400
    huge_poly = {
        "type": "Polygon",
        "coordinates": [[[77.50, 12.90], [77.65, 12.90], [77.65, 13.05], [77.50, 13.05], [77.50, 12.90]]],
    }
    r_huge = client.post(
        "/api/parcels",
        json={"project_id": "PROJ_SIH26012_DEMO", "scene_id": "scene_urban_T1", "geometry": huge_poly},
    )
    assert r_huge.status_code == 400

    # 5. Self-intersection, Invalid CRS, and Duplicate detection in Topology Engine
    bowtie_poly = {
        "type": "Polygon",
        "coordinates": [[[77.5920, 12.9720], [77.5925, 12.9725], [77.5925, 12.9720], [77.5920, 12.9725], [77.5920, 12.9720]]],
    }
    valid_box = {
        "type": "Polygon",
        "coordinates": [[[77.5930, 12.9730], [77.5934, 12.9730], [77.5934, 12.9734], [77.5930, 12.9734], [77.5930, 12.9730]]],
    }
    topo_out = validate_parcels_topology(
        "adversarial_scene",
        [
            {"id": "P_BOWTIE", "crs": "EPSG:4326", "geometry": bowtie_poly},
            {"id": "P_BAD_CRS", "crs": "EPSG:99999", "geometry": valid_box},
            {"id": "P_DUP_1", "crs": "EPSG:4326", "geometry": valid_box},
            {"id": "P_DUP_2", "crs": "EPSG:4326", "geometry": valid_box},
        ],
    )
    issue_types = {iss["issue_type"] for iss in topo_out["issues"]}
    assert "SELF_INTERSECTION" in issue_types
    assert "INVALID_CRS" in issue_types
    assert "DUPLICATE" in issue_types

    # 6. Missing scene & missing parcel -> 404
    assert client.post("/api/pipeline/run", json={"scene_id": "non_existent_scene_999"}).status_code == 404
    assert client.put("/api/parcels/NON_EXISTENT_PARCEL", json={"land_use_class": "vacant"}).status_code == 404
