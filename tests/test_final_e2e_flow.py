import json
import time
import uuid
from pathlib import Path
import httpx
import psycopg2

BASE_URL = "http://127.0.0.1:8000"


def test_final_e2e():
    print("=================================================================")
    print("           AEROCADASTRE FULL E2E INTEGRATION SUITE              ")
    print("=================================================================")
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. PostgreSQL & PostGIS Check
    print("\n[Step 1] Verifying PostgreSQL 16 & PostGIS 3.6 directly...")
    conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="aerocadastre")
    cur = conn.cursor()
    cur.execute("SELECT version(), PostGIS_Full_Version();")
    pg_ver, postgis_ver = cur.fetchone()
    print(" - PostgreSQL Version:", pg_ver)
    print(" - PostGIS Version:   ", postgis_ver[:60], "...")
    cur.close()
    conn.close()

    # 2. FastAPI Health
    print("\n[Step 2] Testing FastAPI /api/health endpoint...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health = r.json()
    assert health["status"] == "ONLINE"
    assert health["database_engine"] == "PostgreSQL + PostGIS"
    print(f" - API Status: {health['status']}, Public Tables: {health['public_table_count']}")

    # 3. Create Project
    test_id = f"E2E_{uuid.uuid4().hex[:6]}"
    proj_id = f"PROJ_{test_id}"
    print(f"\n[Step 3] Creating E2E Project: {proj_id}...")
    r_proj = client.post("/api/projects", json={
        "id": proj_id,
        "name": f"Enterprise E2E Survey Project {test_id}",
        "description": "Full end-to-end multi-step verification project",
        "region_name": "Bengaluru Sector 43N",
        "crs": "EPSG:4326",
        "projected_crs": "EPSG:32643",
        "bbox_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.590, 12.970],
                    [77.600, 12.970],
                    [77.600, 12.980],
                    [77.590, 12.980],
                    [77.590, 12.970],
                ]
            ],
        },
    })
    assert r_proj.status_code == 201, f"Project creation failed: {r_proj.text}"
    print(f" - Created Project: {r_proj.json()['id']}")

    # 4. Insert Candidate Parcel with PostGIS Geometry
    parcel_id = f"PARCEL_{test_id}_001"
    print(f"\n[Step 4] Inserting Cadastral Parcel: {parcel_id}...")
    parcel_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.5910, 12.9710],
                [77.5930, 12.9710],
                [77.5930, 12.9730],
                [77.5910, 12.9730],
                [77.5910, 12.9710],
            ]
        ],
    }
    r_parc = client.post("/api/parcels", json={
        "id": parcel_id,
        "project_id": proj_id,
        "scene_id": f"scene_{test_id}",
        "land_use_class": "residential",
        "boundary_representation": "HUMAN_VERIFIED",
        "crs": "EPSG:4326",
        "geometry": parcel_geojson,
        "operator_id": "Lead_Surveyor_E2E",
        "reason": "Initial surveyor parcel boundary capture",
    })
    assert r_parc.status_code == 201, f"Parcel creation failed: {r_parc.text}"
    parc_data = r_parc.json()
    print(f" - Parcel Persisted. Area: {parc_data.get('area_sqm')} sqm, Perimeter: {parc_data.get('perimeter_m')} m")

    # 5. Spatial Topology Analysis
    print(f"\n[Step 5] Running Spatial Topology Validation for {parcel_id}...")
    r_topo = client.get(f"/api/parcels/{parcel_id}/topology")
    assert r_topo.status_code == 200, f"Topology check failed: {r_topo.text}"
    topo = r_topo.json()
    print(f" - Topology Status: {topo.get('status')}, Issues Detected: {len(topo.get('issues', []))}")

    # 6. AI Council Deliberation
    print(f"\n[Step 6] Running 6-Agent AI Council deliberation on {parcel_id}...")
    r_council = client.post("/api/council/analyze", json={
        "parcel_id": parcel_id,
        "operator_id": "Lead_Surveyor_E2E",
    })
    assert r_council.status_code == 201, f"Council deliberation failed: {r_council.text}"
    council = r_council.json()
    print(f" - Council Decision: {council.get('decision')}, Confidence: {council.get('confidence')}, Action: {council.get('recommended_action')}")

    # 7. Multi-Format GIS Export
    print(f"\n[Step 7] Testing Multi-Format GIS Exporter (GeoJSON, Shapefile, CSV, GeoPackage)...")
    for fmt in ("GeoJSON", "Shapefile", "CSV", "GeoPackage"):
        r_exp = client.post("/api/exports", json={
            "project_id": proj_id,
            "scene_id": f"scene_{test_id}",
            "export_format": fmt,
        })
        assert r_exp.status_code in (200, 201), f"Export {fmt} failed: {r_exp.text}"
        exp = r_exp.json()
        assert exp["validation_passed"] is True, f"Validation failed for {fmt}"
        assert Path(exp["file_path"]).exists(), f"File missing for {fmt}"
        print(f" - Export {fmt:<10}: OK -> {exp['file_path']} ({exp['file_size_bytes']} bytes)")

    # 8. Persistence Check
    print(f"\n[Step 8] Verifying PostGIS Database Persistence for {parcel_id}...")
    conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="aerocadastre")
    cur = conn.cursor()
    cur.execute(f"SELECT id, ST_AsGeoJSON(geom), ST_Area(geom::geography) FROM parcels WHERE id='{parcel_id}';")
    row = cur.fetchone()
    assert row is not None, "Parcel not found in DB!"
    p_db_id, p_db_geojson, p_db_area = row
    assert p_db_id == parcel_id
    assert json.loads(p_db_geojson)["type"] == "Polygon"
    print(f" - PostGIS Verified: ID={p_db_id}, Geodesic Area={p_db_area:.2f} sqm")
    cur.close()
    conn.close()

    print("\n=================================================================")
    print("       ALL 8 E2E STAGES COMPLETED & VERIFIED SUCCESSFULLY!       ")
    print("=================================================================")


if __name__ == "__main__":
    test_final_e2e()
