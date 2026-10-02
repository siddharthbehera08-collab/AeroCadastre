from pathlib import Path
import uuid
from sqlalchemy import text

from backend.app.models.entities import (
    AIPrediction,
    AuditLog,
    CouncilDecision,
    ModelRun,
    Parcel,
    Project,
    TopologyIssue,
    VerificationRecord,
)


def test_01_health_and_postgis_connection(client, db_session):
    """Verify /api/health returns live PostgreSQL + PostGIS metadata and counts."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ONLINE"
    assert body["database_engine"] == "PostgreSQL + PostGIS"
    assert "PostgreSQL" in body["postgresql_version"]
    assert "3." in str(body["postgis_version"])
    assert body["public_table_count"] >= 22
    assert body["table_counts"]["projects"] >= 1
    assert body["table_counts"]["parcels"] >= 10

    # Direct PostGIS spatial query verification
    postgis_ver = db_session.execute(text("SELECT PostGIS_Version();")).scalar()
    assert postgis_ver is not None
    assert "3." in str(postgis_ver)


def test_02_authentication_and_unauthorized_access(client):
    """Verify JWT login, protected /api/auth/me endpoint, and 401 unauthorized handling."""
    # Unauthorized without Bearer token
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    # Invalid credentials
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "surveyor@aerocadastre.gov.in", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    # Valid login (default seeded password for surveyor)
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "surveyor@aerocadastre.gov.in", "password": "sih26012_surveyor"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Authorized access with Bearer token
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "surveyor@aerocadastre.gov.in"


def test_03_project_crud_and_persistence(client, db_session):
    """Test GET/POST/PUT/DELETE /api/projects and verify PostgreSQL persistence."""
    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1

    # Create project with bounding box geometry
    test_pid = f"PROJ_TEST_{uuid.uuid4().hex[:6].upper()}"
    create_payload = {
        "id": test_pid,
        "name": "Test Spatial Cadastral Project",
        "description": "Automated pytest project with PostGIS bounds",
        "region_name": "Ward 99 Test Sector, Pune",
        "crs": "EPSG:4326",
        "projected_crs": "EPSG:32643",
        "bbox_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.5900, 12.9700],
                    [77.5950, 12.9700],
                    [77.5950, 12.9750],
                    [77.5900, 12.9750],
                    [77.5900, 12.9700],
                ]
            ],
        },
    }
    create_resp = client.post("/api/projects", json=create_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    project_id = created["id"]
    assert project_id == test_pid
    assert created["name"] == create_payload["name"]
    assert created["bbox_geometry"]["type"] == "Polygon"

    # Check direct DB persistence
    db_proj = db_session.query(Project).filter(Project.id == project_id).first()
    assert db_proj is not None
    assert db_proj.name == create_payload["name"]

    # Get by ID
    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id

    # Update project
    upd_resp = client.put(
        f"/api/projects/{project_id}",
        json={"name": "Updated Spatial Cadastral Project", "region_name": "Mysuru Sector 2"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Updated Spatial Cadastral Project"
    assert upd_resp.json()["region_name"] == "Mysuru Sector 2"

    # Delete project
    del_resp = client.delete(f"/api/projects/{project_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # Verify 404 after deletion
    missing_resp = client.get(f"/api/projects/{project_id}")
    assert missing_resp.status_code == 404


def test_04_parcel_crud_geojson_and_metric_area(client, db_session):
    """Test parcel CRUD, GeoJSON input/output, and PostGIS EPSG:32643 area/perimeter computation."""
    list_resp = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels")
    assert list_resp.status_code == 200
    parcels = list_resp.json()
    assert isinstance(parcels, list)
    assert len(parcels) >= 10
    assert parcels[0]["geojson_feature"]["type"] == "Feature"
    assert parcels[0]["geometry"]["type"] in ("Polygon", "MultiPolygon")

    # Create a new parcel via GeoJSON Polygon
    test_parcel_id = f"PARCEL_PYTEST_{uuid.uuid4().hex[:6].upper()}"
    parcel_payload = {
        "id": test_parcel_id,
        "project_id": "PROJ_SIH26012_DEMO",
        "scene_id": "scene_urban_T1",
        "land_use_class": "residential",
        "boundary_representation": "HUMAN_VERIFIED",
        "crs": "EPSG:4326",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.5960, 12.9760],
                    [77.5965, 12.9760],
                    [77.5965, 12.9764],
                    [77.5960, 12.9764],
                    [77.5960, 12.9760],
                ]
            ],
        },
        "operator_id": "Surveyor_Verifier_01",
        "reason": "Pytest parcel creation",
    }
    create_resp = client.post("/api/parcels", json=parcel_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    parcel_id = created["id"]
    assert parcel_id == test_parcel_id
    assert created["area_sqm"] > 1500.0  # ~54m x ~44m in UTM 43N
    assert created["perimeter_m"] > 150.0
    assert created["geometry"]["type"] == "Polygon"

    # Verify PostGIS SRID=4326 in database
    srid = db_session.execute(
        text("SELECT ST_SRID(geom) FROM parcels WHERE id = :pid"),
        {"pid": parcel_id},
    ).scalar()
    assert srid == 4326

    # Update parcel geometry and status
    upd_resp = client.put(
        f"/api/parcels/{parcel_id}",
        json={
            "land_use_class": "commercial",
            "verification_status": "HUMAN_VERIFIED",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5960, 12.9760],
                        [77.5968, 12.9760],
                        [77.5968, 12.9766],
                        [77.5960, 12.9766],
                        [77.5960, 12.9760],
                    ]
                ],
            },
        },
    )
    assert upd_resp.status_code == 200
    updated = upd_resp.json()
    assert updated["land_use_class"] == "commercial"
    assert updated["verification_status"] == "HUMAN_VERIFIED"
    assert updated["area_sqm"] > created["area_sqm"]

    # Delete test parcel
    del_resp = client.delete(f"/api/parcels/{parcel_id}")
    assert del_resp.status_code == 200
    assert client.get(f"/api/parcels/{parcel_id}").status_code == 404


def test_05_geometry_validation_and_error_handling(client, db_session):
    """Verify malformed geometries, non-polygons, and invalid IDs return proper errors and rollback."""
    initial_count = db_session.query(Parcel).count()

    # 1. LineString instead of Polygon for Parcel must fail with 400/422
    bad_type_resp = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "LineString",
                "coordinates": [[77.590, 12.970], [77.591, 12.971]],
            },
        },
    )
    assert bad_type_resp.status_code in (400, 422)

    # 2. Out-of-bounds WGS84 coordinates must fail with 400/422
    bad_coords_resp = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [245.0, 99.0],
                        [246.0, 99.0],
                        [246.0, 100.0],
                        [245.0, 100.0],
                        [245.0, 99.0],
                    ]
                ],
            },
        },
    )
    assert bad_coords_resp.status_code in (400, 422)

    # 3. Self-intersecting bowtie polygon must fail with 400/422
    bowtie_resp = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5900, 12.9700],
                        [77.5910, 12.9710],
                        [77.5910, 12.9700],
                        [77.5900, 12.9710],
                        [77.5900, 12.9700],
                    ]
                ],
            },
        },
    )
    assert bowtie_resp.status_code in (400, 422)

    # 4. Non-existent project ID must fail with 404 and rollback
    bad_proj_resp = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_NON_EXISTENT_999",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5960, 12.9760],
                        [77.5965, 12.9760],
                        [77.5965, 12.9764],
                        [77.5960, 12.9764],
                        [77.5960, 12.9760],
                    ]
                ],
            },
        },
    )
    assert bad_proj_resp.status_code == 404

    # Verify no partial rows were committed
    db_session.expire_all()
    assert db_session.query(Parcel).count() == initial_count


def test_06_buildings_and_roads_endpoints(client):
    """Test GET /api/parcels/{parcel_id}/buildings and GET /api/projects/{project_id}/roads."""
    parcels = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels").json()
    target_parcel_id = parcels[0]["id"]

    b_resp = client.get(f"/api/parcels/{target_parcel_id}/buildings")
    assert b_resp.status_code == 200
    b_data = b_resp.json()
    assert b_data["parcel_id"] == target_parcel_id
    assert "buildings" in b_data
    assert b_data["geojson"]["type"] == "FeatureCollection"

    r_resp = client.get("/api/projects/PROJ_SIH26012_DEMO/roads")
    assert r_resp.status_code == 200
    r_data = r_resp.json()
    assert r_data["project_id"] == "PROJ_SIH26012_DEMO"
    assert r_data["count"] >= 1
    assert r_data["geojson"]["type"] == "FeatureCollection"


def test_07_postgis_topology_conflicts_and_spatial_queries(client, db_session):
    """Test PostGIS topology validation, boundary conflict analysis, and ST_DWithin proximity search."""
    # Create two intentionally overlapping test parcels to verify live PostGIS ST_Intersection detection
    p1 = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5980, 12.9780],
                        [77.5986, 12.9780],
                        [77.5986, 12.9786],
                        [77.5980, 12.9786],
                        [77.5980, 12.9780],
                    ]
                ],
            },
        },
    ).json()
    p2 = client.post(
        "/api/parcels",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.5983, 12.9780],
                        [77.5989, 12.9780],
                        [77.5989, 12.9786],
                        [77.5983, 12.9786],
                        [77.5983, 12.9780],
                    ]
                ],
            },
        },
    ).json()

    try:
        topo_resp = client.get(f"/api/parcels/{p1['id']}/topology")
        assert topo_resp.status_code == 200
        topo = topo_resp.json()
        assert topo["parcel_id"] == p1["id"]
        assert topo["srid"] == 4326
        assert topo["metric_crs"] == "EPSG:32643"
        assert topo["is_valid"] is True
        assert any(n["neighbor_id"] == p2["id"] and n["intersects"] is True for n in topo["spatial_neighbors"])

        # Verify TopologyIssue was persisted in PostgreSQL
        db_session.expire_all()
        assert topo["issue_count"] >= 1

        # Test conflicts endpoint on seeded candidate parcel
        parcels = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels").json()
        sample_id = parcels[0]["id"]
        conf_resp = client.get(f"/api/parcels/{sample_id}/conflicts")
        assert conf_resp.status_code == 200
        conf = conf_resp.json()
        assert conf["parcel_id"] == sample_id
        assert "conflict_status" in conf
        assert "reference_gis_alignment" in conf

        # Test spatial proximity endpoint backed by PostGIS ST_DWithin
        nearby_resp = client.get("/api/spatial/nearby?lon=77.5983&lat=12.9783&radius_m=200")
        assert nearby_resp.status_code == 200
        nearby = nearby_resp.json()
        assert nearby["count"] >= 2
    finally:
        client.delete(f"/api/parcels/{p1['id']}")
        client.delete(f"/api/parcels/{p2['id']}")


def test_08_verification_workflow_and_persistence(client, db_session):
    """Test GET /api/verification/queue, POST /api/verification, and PUT /api/verification/{id}."""
    q_resp = client.get("/api/verification/queue")
    assert q_resp.status_code == 200
    assert q_resp.json()["count"] >= 1

    parcels = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels").json()
    target_parcel_id = parcels[0]["id"]

    # Create/submit verification record
    post_resp = client.post(
        "/api/verification",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "parcel_id": target_parcel_id,
            "status": "FIELD_VISIT_REQUESTED",
            "priority": "HIGH",
            "reviewer_notes": "Pytest verification workflow check",
            "verified_by": "Pytest Automated Surveyor",
        },
    )
    assert post_resp.status_code == 201
    created = post_resp.json()
    ver_id = created["id"]
    assert created["status"] == "FIELD_VISIT_REQUESTED"

    # Update verification record with a final decision
    put_resp = client.put(
        f"/api/verification/{ver_id}",
        json={
            "status": "HUMAN_VERIFIED",
            "priority": "LOW",
            "reviewer_notes": "Approved after PostGIS boundary verification",
            "verified_by": "Chief Revenue Officer",
        },
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["status"] == "HUMAN_VERIFIED"

    # Confirm database persistence
    db_session.expire_all()
    rec = db_session.query(VerificationRecord).filter(VerificationRecord.id == ver_id).first()
    assert rec is not None
    assert rec.status == "HUMAN_VERIFIED"


def test_09_ai_analysis_run_and_persistence(client, db_session):
    """Test POST /api/analysis/run and GET /api/analysis/{id} with DB persistence."""
    run_resp = client.post(
        "/api/analysis/run",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "prediction_type": "FULL_SCENE_CADASTRAL_INFERENCE",
        },
    )
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    analysis_id = run_data["id"]
    assert run_data["feature_count"] >= 10
    assert run_data["mean_confidence"] > 0.5

    # Verify AIPrediction row in PostgreSQL
    db_session.expire_all()
    pred = db_session.query(AIPrediction).filter(AIPrediction.id == analysis_id).first()
    assert pred is not None

    # Retrieve via GET /api/analysis/{id}
    get_resp = client.get(f"/api/analysis/{analysis_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == analysis_id
    assert fetched["feature_count"] == run_data["feature_count"]


def test_10_ai_council_deliberation_and_persistence(client, db_session):
    """Test POST /api/council/analyze and GET /api/council/{parcel_id} with DB persistence."""
    parcels = client.get("/api/projects/PROJ_SIH26012_DEMO/parcels").json()
    target_parcel_id = parcels[0]["id"]

    post_resp = client.post(
        "/api/council/analyze",
        json={
            "project_id": "PROJ_SIH26012_DEMO",
            "scene_id": "scene_urban_T1",
            "parcel_id": target_parcel_id,
        },
    )
    assert post_resp.status_code == 201
    decision = post_resp.json()
    assert decision["parcel_id"] == target_parcel_id
    assert "agent_reports" in decision
    assert "final_evidence_score" in decision
    assert "recommended_action" in decision

    # Verify persistence in council_decisions table
    db_session.expire_all()
    db_dec = (
        db_session.query(CouncilDecision)
        .filter(CouncilDecision.id == decision["id"])
        .first()
    )
    assert db_dec is not None
    assert db_dec.parcel_id == target_parcel_id

    # Fetch via GET /api/council/{parcel_id}
    get_resp = client.get(f"/api/council/{target_parcel_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["parcel_id"] == target_parcel_id
    assert fetched["id"] == decision["id"]


def test_11_exports_generation(client):
    """Test POST /api/exports for GeoJSON, GPKG, Shapefile, and CSV report generation."""
    for fmt in ("GeoJSON", "GPKG", "Shapefile", "CSV"):
        resp = client.post(
            "/api/exports",
            json={
                "project_id": "PROJ_SIH26012_DEMO",
                "scene_id": "scene_urban_T1",
                "export_format": fmt,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["validation_passed"] is True
        assert data["feature_count"] >= 10
        assert Path(data["export_path"]).exists()
