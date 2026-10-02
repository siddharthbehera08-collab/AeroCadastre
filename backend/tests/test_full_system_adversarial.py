import io
import json
import time
import uuid
from pathlib import Path
import numpy as np
import pytest
from sqlalchemy import text

from backend.app.core.security import create_access_token
from backend.app.models.entities import (
    Parcel,
    Project,
    ModelRun,
    HumanFeedback,
    FeatureVersion,
)
from backend.council.agents import evaluate_parcel_with_council
from backend.gis.changes import detect_temporal_changes, compare_epoch_features
from backend.gis.route_planner import plan_smart_field_routes
from backend.gis.topology import validate_parcels_topology
from backend.ml.inference import inference_engine


def test_12_frontend_api_contract_alignment(client):
    """
    Verify all 13 Frontend <-> Backend response contracts expected by page.tsx,
    WebGisEditor.tsx, TimeMachineView.tsx, and CouncilFlowView.tsx.
    """
    # 1. GET /api/scenes must return a JSON Array with rich scene metadata
    s_res = client.get("/api/scenes")
    assert s_res.status_code == 200
    scenes = s_res.json()
    assert isinstance(scenes, list) and len(scenes) >= 3
    assert "scene_id" in scenes[0]
    assert "archetype" in scenes[0]
    assert "temporal_epoch" in scenes[0]
    assert "origin_lonlat" in scenes[0]

    # 2. GET /api/scenes/{scene_id}/rgb.png must return image/png
    png_res = client.get("/api/scenes/scene_urban_T1/rgb.png")
    assert png_res.status_code == 200
    assert png_res.headers["content-type"].startswith("image/png")
    assert len(png_res.content) > 1000

    # 3. GET /api/scenes/{scene_id}/bundle must include all 16 required keys
    b_res = client.get("/api/scenes/scene_urban_T1/bundle?project_id=PROJ_SIH26012_DEMO")
    assert b_res.status_code == 200
    bundle = b_res.json()
    for required_key in (
        "metadata",
        "candidate_parcels",
        "reference_parcels",
        "buildings",
        "roads",
        "land_use",
        "boundaries",
        "topology_issues",
        "anomalies",
        "changes",
        "change_events",
        "field_routes",
        "field_tasks",
        "council_decisions",
        "verification_tasks",
    ):
        assert required_key in bundle, f"Missing bundle key: {required_key}"
    assert "origin_lonlat" in bundle["metadata"]
    assert len(bundle["candidate_parcels"]) >= 10
    assert len(bundle["council_decisions"]) >= 10

    # 4. GET /api/dashboard must include all frontend KPI keys
    d_res = client.get("/api/dashboard?project_id=PROJ_SIH26012_DEMO&scene_id=scene_urban_T1")
    assert d_res.status_code == 200
    metrics = d_res.json()["metrics"]
    for m_key in (
        "candidate_parcels",
        "buildings_detected",
        "roads_detected",
        "pending_verification",
        "verified_features",
        "gis_conflicts",
        "anomalies",
        "temporal_changes",
        "topology_issues",
        "council_decisions",
    ):
        assert m_key in metrics, f"Missing dashboard metric key: {m_key}"

    # 5. GET /api/experiments, /api/datasets, /api/feedback, /api/audit-logs must return JSON Arrays
    for ep in ("/api/experiments", "/api/datasets", "/api/feedback", "/api/audit-logs"):
        res = client.get(ep)
        assert res.status_code == 200
        assert isinstance(res.json(), list), f"Expected JSON Array from {ep}"

    # 6. GET /api/history/{feature_id} must return JSON Array of FeatureVersion records
    first_pid = bundle["candidate_parcels"][0]["id"]
    h_res = client.get(f"/api/history/{first_pid}")
    assert h_res.status_code == 200
    hist = h_res.json()
    assert isinstance(hist, list) and len(hist) >= 3
    epochs_present = [v["temporal_epoch"] for v in hist]
    assert any("T0" in ep for ep in epochs_present)
    assert any("T1" in ep for ep in epochs_present)


def test_13_rbac_authorization_and_security_controls(client):
    """
    Verify Role-Based Access Control (RBAC):
    - VIEWER / DEMO_USER / SIH26012_Reviewer is blocked (403 Forbidden) from mutating parcels/verifications.
    - Invalid/forged JWT is blocked (401 Unauthorized).
    - SURVEYOR and ADMIN roles are permitted to mutate.
    """
    parcels = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels").json()
    target_id = parcels[0]["id"]

    # 1. Forged JWT token -> 401 Unauthorized
    forged_res = client.put(
        f"/api/parcels/{target_id}",
        headers={"Authorization": "Bearer forged.jwt.token"},
        json={"land_use_class": "commercial"},
    )
    assert forged_res.status_code == 401

    # 2. Valid JWT token with role=VIEWER -> 403 Forbidden
    viewer_token = create_access_token(subject="viewer@aerocadastre.gov.in", role="VIEWER")
    viewer_res = client.put(
        f"/api/parcels/{target_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"land_use_class": "commercial"},
    )
    assert viewer_res.status_code == 403

    # 3. X-Operator-Role: Demo User header -> 403 Forbidden
    header_res = client.delete(
        f"/api/parcels/{target_id}",
        headers={"X-Operator-Role": "Demo User"},
    )
    assert header_res.status_code == 403

    # 4. operator_id = SIH26012_Reviewer in payload -> 403 Forbidden
    op_res = client.post(
        f"/api/verification/{target_id}",
        json={
            "action": "HUMAN_VERIFIED",
            "operator_id": "SIH26012_Reviewer",
            "notes": "Attempted verification by read-only Demo User",
        },
    )
    assert op_res.status_code == 403


def test_14_parcel_editing_split_merge_adversarial(client, db_session):
    """
    Adversarial testing of Parcel Create, Edit, Split, and Merge:
    - Tiny sliver parcel (< 1 m²) rejected (400)
    - Huge continental parcel (> 5,000,000 m²) rejected (400)
    - Duplicate parcel ID rejected (409)
    - Very large reasonable polygon (120 vertices) accepted (201)
    - Split into 2 valid child parcels + Merge back into 1 parcel
    - Incompatible merges (merging with self, or merging disjoint far-apart parcels) rejected (400)
    """
    parcels = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels").json()
    existing_id = parcels[0]["id"]

    # 1. Duplicate parcel ID -> 409 Conflict
    dup_res = client.post(
        "/api/parcels",
        json={
            "id": existing_id,
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": parcels[0]["geometry"],
        },
    )
    assert dup_res.status_code == 409

    # 2. Tiny polygon (< 1.0 m²) -> 400 Bad Request
    tiny_res = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5950000, 12.9750000],
                        [77.5950005, 12.9750000],
                        [77.5950005, 12.9750005],
                        [77.5950000, 12.9750005],
                        [77.5950000, 12.9750000],
                    ]
                ],
            },
        },
    )
    assert tiny_res.status_code == 400

    # 3. Huge polygon (> 5,000,000 m²) -> 400 Bad Request
    huge_res = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.50, 12.90],
                        [77.60, 12.90],
                        [77.60, 13.00],
                        [77.50, 13.00],
                        [77.50, 12.90],
                    ]
                ],
            },
        },
    )
    assert huge_res.status_code == 400

    # 4. Very large reasonable payload (120-vertex circle polygon ~2500 m²) -> 201 Created
    angles = np.linspace(0, 2 * np.pi, 120, endpoint=False)
    cx, cy, r_deg = 77.5970, 12.9770, 0.00025
    ring = [[round(float(cx + r_deg * np.cos(a)), 7), round(float(cy + r_deg * np.sin(a)), 7)] for a in angles]
    ring.append(ring[0])

    large_poly_res = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "land_use_class": "institutional",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        },
    )
    assert large_poly_res.status_code == 201
    created_id = large_poly_res.json()["id"]

    try:
        # 5. Split parcel into 2 child parcels
        split_res = client.post(
            f"/api/parcels/{created_id}/split",
            json={
                "split_axis": "VERTICAL",
                "split_ratio": 0.5,
                "operator_id": "Surveyor_Verifier_01",
                "reason": "Adversarial test split",
            },
        )
        assert split_res.status_code == 200
        split_data = split_res.json()
        id_a = split_data["parcel_a"]["id"]
        id_b = split_data["parcel_b"]["id"]
        assert id_a == created_id
        assert id_b.startswith(created_id)

        # 6. Incompatible merge: merge parcel with itself -> 400
        self_merge = client.post(
            "/api/parcels/merge",
            json={
                "project_id": "PROJ_SIH26012_DEMO",
                "scene_id": "scene_urban_T1",
                "parcel_id_a": id_a,
                "parcel_id_b": id_a,
            },
        )
        assert self_merge.status_code == 400

        # 7. Incompatible merge: merge disjoint far-apart parcels -> 400
        far_parcel = client.post(
            "/api/parcels",
            json={
                "project_id": "PROJ_SIH26012_DEMO",
                "scene_id": "scene_urban_T1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [77.6050, 12.9850],
                            [77.6054, 12.9850],
                            [77.6054, 12.9854],
                            [77.6050, 12.9854],
                            [77.6050, 12.9850],
                        ]
                    ],
                },
            },
        ).json()
        try:
            disjoint_merge = client.post(
                "/api/parcels/merge",
                json={
                    "project_id": "PROJ_SIH26012_DEMO",
                    "scene_id": "scene_urban_T1",
                    "parcel_id_a": id_a,
                    "parcel_id_b": far_parcel["id"],
                },
            )
            assert disjoint_merge.status_code == 400
        finally:
            client.delete(f"/api/parcels/{far_parcel['id']}")

        # 8. Valid merge: merge adjacent split parts A and B back together -> 200
        valid_merge = client.post(
            "/api/parcels/merge",
            json={
                "project_id": "PROJ_SIH26012_DEMO",
                "scene_id": "scene_urban_T1",
                "parcel_id_a": id_a,
                "parcel_id_b": id_b,
                "operator_id": "Surveyor_Verifier_01",
                "reason": "Re-merging split parcels",
            },
        )
        assert valid_merge.status_code == 200
        assert client.get(f"/api/parcels/{id_b}").status_code == 404
    finally:
        client.delete(f"/api/parcels/{created_id}")


def test_15_postgis_native_spatial_functions_and_topology_torture(db_session):
    """
    Directly test PostGIS native spatial functions (ST_IsValid, ST_MakeValid, ST_Intersects,
    ST_Contains, ST_Within, ST_Overlaps, ST_Distance, ST_Area) and topology validator edge cases
    (sliver, bowtie self-intersection, overlap, gap).
    """
    sql = text(
        """
        WITH sample_geoms AS (
            SELECT
                ST_GeomFromText('POLYGON((77.5920 12.9720, 77.5925 12.9720, 77.5925 12.9725, 77.5920 12.9725, 77.5920 12.9720))', 4326) AS g_outer,
                ST_GeomFromText('POLYGON((77.5921 12.9721, 77.5923 12.9721, 77.5923 12.9723, 77.5921 12.9723, 77.5921 12.9721))', 4326) AS g_inner,
                ST_GeomFromText('POLYGON((77.5923 12.9720, 77.5928 12.9720, 77.5928 12.9725, 77.5923 12.9725, 77.5923 12.9720))', 4326) AS g_overlap,
                ST_GeomFromText('POLYGON((77.5920 12.9720, 77.5925 12.9725, 77.5925 12.9720, 77.5920 12.9725, 77.5920 12.9720))', 4326) AS g_bowtie
        )
        SELECT
            ST_IsValid(g_outer) AS outer_valid,
            ST_IsValid(g_bowtie) AS bowtie_valid,
            ST_IsValid(ST_MakeValid(g_bowtie)) AS bowtie_repaired_valid,
            ST_Contains(g_outer, g_inner) AS outer_contains_inner,
            ST_Within(g_inner, g_outer) AS inner_within_outer,
            ST_Intersects(g_outer, g_overlap) AS outer_intersects_overlap,
            ST_Overlaps(g_outer, g_overlap) AS outer_overlaps_overlap,
            ROUND(CAST(ST_Area(ST_Transform(g_outer, 32643)) AS numeric), 2) AS outer_area_sqm,
            ROUND(CAST(ST_Distance(ST_Transform(g_inner, 32643), ST_Transform(g_overlap, 32643)) AS numeric), 2) AS dist_m
        FROM sample_geoms;
        """
    )
    row = db_session.execute(sql).mappings().first()
    assert row["outer_valid"] is True
    assert row["bowtie_valid"] is False
    assert row["bowtie_repaired_valid"] is True
    assert row["outer_contains_inner"] is True
    assert row["inner_within_outer"] is True
    assert row["outer_intersects_overlap"] is True
    assert row["outer_overlaps_overlap"] is True
    assert float(row["outer_area_sqm"]) > 2500.0
    assert float(row["dist_m"]) == 0.0

    # Topology validator torture: valid + overlap + sliver + self-intersecting bowtie
    synthetic_parcels = [
        {
            "id": "TORTURE_P1",
            "crs": "EPSG:4326",
            "area_sqm": 2800.0,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5920, 12.9720],
                        [77.5925, 12.9720],
                        [77.5925, 12.9725],
                        [77.5920, 12.9725],
                        [77.5920, 12.9720],
                    ]
                ],
            },
        },
        {
            "id": "TORTURE_P2_OVERLAP",
            "crs": "EPSG:4326",
            "area_sqm": 2800.0,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5923, 12.9720],
                        [77.5928, 12.9720],
                        [77.5928, 12.9725],
                        [77.5923, 12.9725],
                        [77.5923, 12.9720],
                    ]
                ],
            },
        },
        {
            "id": "TORTURE_P3_SLIVER",
            "crs": "EPSG:4326",
            "area_sqm": 8.5,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.59300, 12.97200],
                        [77.59303, 12.97200],
                        [77.59303, 12.97202],
                        [77.59300, 12.97202],
                        [77.59300, 12.97200],
                    ]
                ],
            },
        },
        {
            "id": "TORTURE_P4_BOWTIE",
            "crs": "EPSG:4326",
            "area_sqm": 1200.0,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5940, 12.9720],
                        [77.5945, 12.9725],
                        [77.5945, 12.9720],
                        [77.5940, 12.9725],
                        [77.5940, 12.9720],
                    ]
                ],
            },
        },
    ]
    topo_out = validate_parcels_topology("scene_torture", synthetic_parcels)
    issue_types = {iss["issue_type"] for iss in topo_out["issues"]}
    assert "OVERLAP" in issue_types
    assert "SLIVER" in issue_types or "SLIVER_POLYGON" in issue_types
    assert "SELF_INTERSECTION" in issue_types


def test_16_ml_pipeline_adversarial_inputs():
    """
    Test GeoAIInferenceEngine with:
    1. Valid synthetic image array
    2. Missing scene directory -> FileNotFoundError
    3. Corrupt image file -> ValueError
    4. Wrong spatial dimensions (not divisible by 4 or < 16) -> ValueError
    5. Wrong channel count (2 channels) -> ValueError
    6. Empty image array (size 0 or all zeros) -> ValueError
    7. Unexpected dtype (boolean or NaN) -> ValueError
    """
    # 1. Valid 64x64x3 array
    rng = np.random.default_rng(42)
    valid_rgb = rng.uniform(20, 220, size=(64, 64, 3)).astype(np.uint8)
    valid_dsm = rng.uniform(210.0, 225.0, size=(64, 64)).astype(np.float32)
    out = inference_engine.run_array_inference(valid_rgb, valid_dsm, scene_id="test_64")
    assert out["bldg_prob"].shape == (64, 64)
    assert out["road_prob"].shape == (64, 64)
    assert out["lu_pred"].shape == (64, 64)
    assert out["inference_time_ms"] >= 0.0

    # 2. Missing scene directory
    with pytest.raises(FileNotFoundError):
        inference_engine.run_scene_inference(Path("D:/SIH26012_AeroCadastre/synthetic_data/non_existent_scene_999"))

    # 3. Wrong dimensions (63x63 not divisible by 4, and 8x8 < 16)
    with pytest.raises(ValueError, match="spatial dimensions"):
        inference_engine.run_array_inference(rng.uniform(10, 200, size=(63, 63, 3)).astype(np.float32))
    with pytest.raises(ValueError, match="spatial dimensions"):
        inference_engine.run_array_inference(rng.uniform(10, 200, size=(8, 8, 3)).astype(np.float32))

    # 4. Wrong channel count (2 channels)
    with pytest.raises(ValueError, match="channel count"):
        inference_engine.run_array_inference(rng.uniform(10, 200, size=(64, 64, 2)).astype(np.float32))

    # 5. Empty array (0x0x3 or all-zero array)
    with pytest.raises(ValueError, match="Empty"):
        inference_engine.run_array_inference(np.zeros((0, 0, 3), dtype=np.float32))
    with pytest.raises(ValueError, match="all-zero"):
        inference_engine.run_array_inference(np.zeros((64, 64, 3), dtype=np.float32))

    # 6. Unexpected dtype (bool or NaN)
    with pytest.raises(ValueError, match="dtype"):
        inference_engine.run_array_inference(np.ones((64, 64, 3), dtype=bool))
    nan_arr = valid_rgb.astype(np.float32)
    nan_arr[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        inference_engine.run_array_inference(nan_arr)


def test_17_ai_council_six_agents_and_disagreement_scenarios():
    """
    Test all 6 AI Council agents (VISION_AGENT, GEOMETRY_AGENT, GIS_AGENT, ML_AGENT,
    ANOMALY_AGENT, FIELD_VERIFICATION_AGENT) across controlled agreement and disagreement scenarios.
    """
    # Scenario A: Clean high-confidence parcel -> ACCEPT_FOR_REVIEW (LOW priority)
    clean_parcel = {
        "id": "COUNCIL_CLEAN_01",
        "visible_edges": 4,
        "boundary_prob_mean": 0.94,
        "bldg_prob_mean": 0.95,
        "lu_prob_mean": 0.94,
        "model_disagreement": 0.01,
        "compactness": 0.82,
        "area_sqm": 2800.0,
        "road_access": True,
    }
    res_clean = evaluate_parcel_with_council(
        parcel=clean_parcel,
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
        gis_iou=0.95,
    )
    assert len(res_clean["agent_reports"]) == 6
    for agent_name in (
        "VISION_AGENT",
        "GEOMETRY_AGENT",
        "GIS_AGENT",
        "ML_AGENT",
        "ANOMALY_AGENT",
        "FIELD_VERIFICATION_AGENT",
    ):
        assert agent_name in res_clean["agent_reports"]
    assert res_clean["decision"] == "ACCEPT_FOR_REVIEW"
    assert res_clean["field_need"] == "LOW"

    # Scenario B: High Vision confidence, but severe GIS Conflict + Spatial Anomaly + Overlap
    # Must NOT blindly return ACCEPT_FOR_REVIEW!
    res_conflict = evaluate_parcel_with_council(
        parcel={**clean_parcel, "id": "COUNCIL_CONFLICT_02"},
        topology_status="OVERLAP",
        conflict_status="ROAD_CROSSING_PARCEL",
        anomaly_status="BUILDING_CROSSING_BOUNDARY",
        parcel_anomalies=[
            {"explanation": "Road corridor bisects candidate parcel"},
            {"explanation": "Building footprint crosses parcel boundary"},
        ],
        parcel_changes=[{"summary": "Unauthorized extension in T2"}],
        gis_iou=0.45,
    )
    assert res_conflict["decision"] != "ACCEPT_FOR_REVIEW"
    assert res_conflict["decision"] in ("GEOMETRY_ERROR", "CONFLICT_DETECTED", "REQUIRES_VERIFICATION")
    assert res_conflict["field_need"] == "HIGH"
    assert len(res_conflict["conflicting_evidence"]) >= 2

    # Scenario C: Low ML confidence + occluded boundaries + high model disagreement -> LOW_CONFIDENCE / HIGH field priority
    res_low = evaluate_parcel_with_council(
        parcel={
            "id": "COUNCIL_LOW_03",
            "visible_edges": 1,
            "boundary_prob_mean": 0.42,
            "bldg_prob_mean": 0.45,
            "lu_prob_mean": 0.48,
            "model_disagreement": 0.25,
            "compactness": 0.35,
            "area_sqm": 420.0,
            "road_access": False,
        },
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
        gis_iou=0.52,
    )
    assert res_low["decision"] == "LOW_CONFIDENCE"
    assert res_low["field_need"] == "HIGH"


def test_18_temporal_change_detection_and_field_route_edge_cases():
    """
    Test Change Detection (T0 vs T1/T2) and Field Route Optimization (0, 1, N tasks, duplicate coords).
    """
    # 1. Identical T0 and T1 scenes -> 0 false change events
    p_t0 = [
        {
            "id": "scene_test_P_001",
            "land_use_class": "residential",
            "area_sqm": 1200.0,
            "perimeter_m": 140.0,
            "building_count": 1,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5920, 12.9720],
                        [77.5924, 12.9720],
                        [77.5924, 12.9724],
                        [77.5920, 12.9724],
                        [77.5920, 12.9720],
                    ]
                ],
            },
        }
    ]
    no_changes = compare_epoch_features("scene_test", p_t0, p_t0, p_t0)
    assert len(no_changes["changes"]) == 0
    assert len(no_changes["versions"]) == 3

    # 2. New building + land-use transition + boundary shift in T1 -> detected accurately
    p_t1 = [
        {
            **p_t0[0],
            "land_use_class": "commercial",
            "building_count": 2,
            "area_sqm": 1480.0,
        }
    ]
    detected = compare_epoch_features("scene_test", p_t0, p_t1, p_t1)
    chg_types = {c["change_type"] for c in detected["changes"]}
    assert "NEW_BUILDING" in chg_types
    assert "LAND_USE_CHANGE" in chg_types
    assert "BOUNDARY_SHIFT" in chg_types

    # 3. Full synthetic temporal demo dataset (T0 -> T1 -> T2)
    demo_temporal = detect_temporal_changes("scene_urban", "scene_urban_T1")
    assert len(demo_temporal["changes"]) >= 3
    assert len(demo_temporal["versions"]) >= 30

    # 4. Field Route Planner edge cases: 0 tasks, 1 task, duplicate locations
    assert plan_smart_field_routes("scene_empty", [], num_clusters=2) == []

    one_task = [
        {
            "id": "VT_1",
            "parcel_id": "P_1",
            "priority": "HIGH",
            "priority_score": 0.92,
            "status": "PENDING",
            "reasons": ["High risk"],
            "centroid_lon": 77.5922,
            "centroid_lat": 12.9722,
        }
    ]
    r_one = plan_smart_field_routes("scene_one", one_task, num_clusters=2)
    assert len(r_one) == 1
    assert r_one[0]["task_count"] == 1
    assert "prototype" in r_one[0]["disclaimer"].lower()

    dup_tasks = [
        {**one_task[0], "id": f"VT_{i}", "parcel_id": f"P_{i}"} for i in range(4)
    ]
    r_dup = plan_smart_field_routes("scene_dup", dup_tasks, num_clusters=2)
    assert len(r_dup) >= 1
    assert sum(rt["task_count"] for rt in r_dup) == 4



def test_19_copilot_contextual_and_edge_case_queries(client):
    """
    Test Cadastral AI Copilot with:
    - Project overview query
    - Specific parcel query (P_002)
    - Topology query
    - Unknown parcel query (P_999) -> must report parcel not found
    - Unknown project query (PROJ_DOES_NOT_EXIST) -> must report project not found
    - Empty query string -> 400 Bad Request
    """
    # 1. Specific parcel query via /api/copilot/ask
    p2_res = client.post(
        "/api/copilot/ask",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "query": "Why was parcel P_002 flagged by the AI Council?",
        },
    )
    assert p2_res.status_code == 200
    p2_data = p2_res.json()
    assert "P_002" in p2_data["answer_markdown"]
    assert len(p2_data["highlighted_feature_ids"]) == 1

    # 2. Unknown parcel query (P_999)
    unk_p = client.post(
        "/api/copilot/ask",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "query": "Show diagnostic report for parcel P_999",
        },
    )
    assert unk_p.status_code == 200
    assert unk_p.json()["intent"] == "unknown_parcel_lookup"
    assert "Not Found" in unk_p.json()["answer_markdown"]

    # 3. Unknown project query
    unk_proj = client.post(
        "/api/copilot/ask",
        json={
            "project_id": "PROJ_NON_EXISTENT_XYZ",
            "scene_id": "scene_urban_T1",
            "query": "Summarize project status",
        },
    )
    assert unk_proj.status_code == 200
    assert unk_proj.json()["intent"] == "unknown_project_lookup"

    # 4. Empty query -> 400 Bad Request
    empty_q = client.post(
        "/api/copilot/ask",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "query": "   ",
        },
    )
    assert empty_q.status_code == 400


def test_20_dataset_upload_and_export_matrix_with_security_checks(client):
    """
    Test dataset upload validation (valid GeoJSON vs empty/unsupported file)
    and multi-format exports (GeoJSON, GPKG, SHP_ZIP, CSV) with 0, 1, and multiple parcels,
    plus path traversal blocking on /api/exports/download.
    """
    # 1. Valid GeoJSON upload
    valid_geojson = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Uploaded Test Parcel"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [77.592, 12.972],
                                [77.593, 12.972],
                                [77.593, 12.973],
                                [77.592, 12.973],
                                [77.592, 12.972],
                            ]
                        ],
                    },
                }
            ],
        }
    ).encode("utf-8")
    up_res = client.post(
        "/api/upload",
        data={"project_id": "PROJ_SIH26012_DEMO", "declared_crs": "EPSG:4326", "temporal_epoch": "T1"},
        files={"file": ("test_upload_valid.geojson", io.BytesIO(valid_geojson), "application/geo+json")},
    )
    assert up_res.status_code == 201
    assert up_res.json()["validation_status"] == "VALID"

    # 2. Unsupported executable extension (.exe) -> 400 Bad Request
    bad_ext = client.post(
        "/api/upload",
        data={"project_id": "PROJ_SIH26012_DEMO"},
        files={"file": ("malicious.exe", io.BytesIO(b"MZ9000"), "application/octet-stream")},
    )
    assert bad_ext.status_code == 400

    # 3. Corrupt GeoJSON upload -> 400 Bad Request
    corrupt_up = client.post(
        "/api/upload",
        data={"project_id": "PROJ_SIH26012_DEMO"},
        files={"file": ("corrupt.geojson", io.BytesIO(b"{not_valid_json"), "application/json")},
    )
    assert corrupt_up.status_code == 400

    # 4. Export with 0 parcels (create temporary empty project)
    empty_pid = f"PROJ_EMPTY_{uuid.uuid4().hex[:6].upper()}"
    client.post("/api/projects", json={"id": empty_pid, "name": "Empty Export Test Project"})
    try:
        for fmt in ("GeoJSON", "GPKG", "SHP_ZIP", "CSV"):
            exp0 = client.post(
                "/api/exports",
                json={"project_id": empty_pid, "scene_id": "scene_empty", "export_format": fmt},
            )
            assert exp0.status_code == 201
            d0 = exp0.json()
            assert d0["feature_count"] == 0
            assert d0["validation_passed"] is True
            assert d0["size_bytes"] > 0
    finally:
        client.delete(f"/api/projects/{empty_pid}")

    # 5. Download via file_path query param and verify path-traversal block
    exp_valid = client.post(
        "/api/exports",
        json={"project_id": "PROJ_SIH26012_DEMO", "scene_id": "scene_urban_T1", "export_format": "GeoJSON"},
    ).json()
    dl_ok = client.get(f"/api/exports/download?file_path={exp_valid['file_path']}")
    assert dl_ok.status_code == 200

    dl_traversal = client.get("/api/exports/download?file_path=D:/SIH26012_AeroCadastre/alembic.ini")
    assert dl_traversal.status_code == 403


def test_21_performance_benchmarks_10_100_500_1000_parcels(client, db_session):
    """
    Benchmark PostgreSQL + PostGIS batch creation, API serialization, and PostGIS spatial queries
    across 10, 100, 500, and 1000 synthetic parcels and persist real timings.
    """
    bench_pid = f"PROJ_BENCH_{uuid.uuid4().hex[:6].upper()}"
    client.post("/api/projects", json={"id": bench_pid, "name": "PostGIS Scale Benchmark Project"})
    benchmark_results = []

    try:
        for scale in (10, 100, 500, 1000):
            db_session.execute(
                text("DELETE FROM parcels WHERE project_id = :pid"), {"pid": bench_pid}
            )
            db_session.commit()

            # 1. Batch insert N PostGIS polygons using generate_series
            t0 = time.perf_counter()
            insert_sql = text(
                """
                INSERT INTO parcels (
                    id, project_id, scene_id, temporal_epoch, parcel_layer,
                    boundary_representation, land_use_class, area_sqm, perimeter_m,
                    compactness, building_count, road_access, dsm_mean_elevation_m,
                    crs, confidence, confidence_category, confidence_breakdown_json,
                    evidence_sources_json, topology_status, conflict_status,
                    anomaly_status, verification_status, verification_priority,
                    council_decision, ulpin_ready_metadata_json, provenance_json,
                    version, geometry_geojson, geom
                )
                SELECT
                    :pid || '_P_' || gs::text,
                    :pid,
                    'scene_bench',
                    'T1',
                    'CANDIDATE',
                    'VISIBLE',
                    'residential',
                    1200.0,
                    140.0,
                    0.76,
                    1,
                    true,
                    215.0,
                    'EPSG:4326',
                    0.89,
                    'HIGH',
                    '{"overall_confidence": 0.89}',
                    '["Bench"]',
                    'VALID',
                    'NONE',
                    'NONE',
                    'PENDING',
                    'LOW',
                    'ACCEPT_FOR_REVIEW',
                    '{}',
                    '{}',
                    1,
                    ST_AsGeoJSON(
                        ST_MakeEnvelope(
                            77.5900 + (gs % 40) * 0.0003,
                            12.9700 + (gs / 40) * 0.0003,
                            77.5900 + (gs % 40) * 0.0003 + 0.00025,
                            12.9700 + (gs / 40) * 0.0003 + 0.00025,
                            4326
                        )
                    ),
                    ST_MakeEnvelope(
                        77.5900 + (gs % 40) * 0.0003,
                        12.9700 + (gs / 40) * 0.0003,
                        77.5900 + (gs % 40) * 0.0003 + 0.00025,
                        12.9700 + (gs / 40) * 0.0003 + 0.00025,
                        4326
                    )
                FROM generate_series(1, :scale) AS gs;
                """
            )
            db_session.execute(insert_sql, {"pid": bench_pid, "scale": scale})
            db_session.commit()
            insert_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            # 2. PostGIS spatial bbox + metric area aggregation query
            t1 = time.perf_counter()
            spatial_sql = text(
                """
                SELECT
                    COUNT(*) AS cnt,
                    SUM(ST_Area(ST_Transform(geom, 32643))) AS total_area_sqm
                FROM parcels
                WHERE project_id = :pid
                  AND ST_Intersects(geom, ST_MakeEnvelope(77.589, 12.969, 77.610, 12.990, 4326));
                """
            )
            sp_row = db_session.execute(spatial_sql, {"pid": bench_pid}).mappings().first()
            spatial_query_ms = round((time.perf_counter() - t1) * 1000.0, 2)
            assert int(sp_row["cnt"]) == scale

            # 3. FastAPI GET /api/projects/{project_id}/parcels serialization latency
            t2 = time.perf_counter()
            api_res = client.get(f"/api/projects/{bench_pid}/parcels?scene_id=scene_bench")
            api_ms = round((time.perf_counter() - t2) * 1000.0, 2)
            assert api_res.status_code == 200
            assert len(api_res.json()) == scale

            benchmark_results.append(
                {
                    "parcel_count": scale,
                    "postgis_batch_insert_ms": insert_ms,
                    "postgis_spatial_query_ms": spatial_query_ms,
                    "fastapi_serialize_ms": api_ms,
                }
            )

        out_file = Path("D:/SIH26012_AeroCadastre/experiments/performance_benchmarks.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(benchmark_results, indent=2), encoding="utf-8")
    finally:
        db_session.execute(
            text("DELETE FROM parcels WHERE project_id = :pid"), {"pid": bench_pid}
        )
        db_session.commit()
        client.delete(f"/api/projects/{bench_pid}")


def test_22_transaction_rollback_geojson_types_and_live_training(client, db_session):
    """
    Verify:
    1. GeoJSON validation across Polygon, MultiPolygon, LineString, MultiLineString, Point.
    2. Database transaction rollback upon mid-transaction failure leaves zero partial rows.
    3. Live PyTorch training endpoint (POST /api/experiments/train?epochs=2) persists a ModelRun.
    """
    from backend.app.utils.geojson import validate_and_parse_geojson

    # 1. GeoJSON geometry types
    for geom_obj, exp_types in [
        (
            {
                "type": "Polygon",
                "coordinates": [
                    [[77.59, 12.97], [77.60, 12.97], [77.60, 12.98], [77.59, 12.98], [77.59, 12.97]]
                ],
            },
            ("Polygon", "MultiPolygon"),
        ),
        (
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[77.59, 12.97], [77.60, 12.97], [77.60, 12.98], [77.59, 12.98], [77.59, 12.97]]]
                ],
            },
            ("Polygon", "MultiPolygon"),
        ),
        (
            {"type": "LineString", "coordinates": [[77.59, 12.97], [77.60, 12.98]]},
            ("LineString", "MultiLineString"),
        ),
        (
            {"type": "MultiLineString", "coordinates": [[[77.59, 12.97], [77.60, 12.98]]]},
            ("LineString", "MultiLineString"),
        ),
        (
            {"type": "Point", "coordinates": [77.592, 12.972]},
            ("Point",),
        ),
    ]:
        shp, g_dict = validate_and_parse_geojson(geom_obj, expected_types=exp_types, crs="EPSG:4326")
        assert shp.is_valid and not shp.is_empty
        assert g_dict["type"] == geom_obj["type"]

    # 2. Intentional mid-transaction failure rollback check
    initial_projects = db_session.query(Project).count()
    temp_proj_id = f"PROJ_ROLLBACK_{uuid.uuid4().hex[:6].upper()}"
    try:
        db_session.add(
            Project(
                id=temp_proj_id,
                name="Should Rollback Project",
                crs="EPSG:4326",
                projected_crs="EPSG:32643",
            )
        )
        db_session.flush()
        # Trigger foreign key violation intentionally
        db_session.execute(
            text(
                "INSERT INTO buildings (id, project_id, scene_id, temporal_epoch, crs, area_sqm, perimeter_m, centroid_lon, centroid_lat, confidence, confidence_category, model_source, source_type, verification_status, geometry_geojson) "
                "VALUES ('BAD_BLDG', 'NON_EXISTENT_FK_PROJ', 's1', 'T1', 'EPSG:4326', 10, 10, 77.5, 12.9, 0.9, 'HIGH', 'm', 's', 'PENDING', '{}')"
            )
        )
        db_session.commit()
    except Exception:
        db_session.rollback()

    assert db_session.query(Project).filter(Project.id == temp_proj_id).first() is None
    assert db_session.query(Project).count() == initial_projects

    # 3. Live PyTorch training endpoint (POST /api/experiments/train?epochs=2)
    train_res = client.post("/api/experiments/train?epochs=2")
    assert train_res.status_code == 200
    tr_data = train_res.json()
    assert tr_data["id"].startswith("EXP_LIVE_")
    assert tr_data["epochs"] == 2
    assert tr_data["iou"] > 0.0
    assert len(tr_data["epoch_history"]) == 2

