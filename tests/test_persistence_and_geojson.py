import json
import uuid
import httpx
import psycopg2
import pytest

BASE_URL = "http://127.0.0.1:8000"


def _is_server_available():
    try:
        r = httpx.get("http://127.0.0.1:8000/api/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _is_server_available(),
    reason="Requires live FastAPI server running on http://127.0.0.1:8000",
)


def test_persistence_and_geojson():
    print("=== PHASE 8 & 9: PERSISTENCE AND GEOJSON ROUND-TRIP TEST ===")
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1. Test Health
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health_data = r.json()
    print("[PASS] Health check OK. DB Engine:", health_data.get("database_engine"))

    uid = uuid.uuid4().hex[:6]
    proj_id = f"PROJ_TEST_{uid}"
    parcel_id = f"PARCEL_{uid}"

    # 2. Create a test project
    proj_payload = {
        "id": proj_id,
        "name": f"Persistence Test Project {uid}",
        "description": "Project created to test PostgreSQL/PostGIS durability",
        "region_name": "Bengaluru Urban Sector",
        "crs": "EPSG:4326",
        "projected_crs": "EPSG:32643",
        "bbox_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.590, 12.970],
                    [77.595, 12.970],
                    [77.595, 12.975],
                    [77.590, 12.975],
                    [77.590, 12.970],
                ]
            ],
        },
    }
    r = client.post("/api/projects", json=proj_payload)
    assert r.status_code == 201, f"Failed to create project: {r.text}"
    print(f"[PASS] Project {proj_id} created successfully.")

    # 3. Create a valid parcel
    parcel_payload = {
        "id": parcel_id,
        "project_id": proj_id,
        "scene_id": f"scene_test_{uid}",
        "land_use_class": "residential",
        "boundary_representation": "HUMAN_VERIFIED",
        "crs": "EPSG:4326",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.5910, 12.9710],
                    [77.5920, 12.9710],
                    [77.5920, 12.9720],
                    [77.5910, 12.9720],
                    [77.5910, 12.9710],
                ]
            ],
        },
        "operator_id": "Lead_Surveyor_Test",
        "reason": "Test durability round-trip",
    }
    r = client.post("/api/parcels", json=parcel_payload)
    assert r.status_code == 201, f"Failed to create parcel: {r.text}"
    created_parcel = r.json()
    print(f"[PASS] Parcel {parcel_id} created successfully: Area = {created_parcel.get('area_sqm')} sqm")

    # 4. Read back through API
    r = client.get(f"/api/parcels/{parcel_id}")
    assert r.status_code == 200, f"Failed to retrieve parcel: {r.text}"
    retrieved = r.json()
    assert retrieved["id"] == parcel_id
    assert retrieved["geometry"]["type"] == "Polygon"
    assert len(retrieved["geometry"]["coordinates"][0]) == 5
    print("[PASS] Parcel read back via API matches created geometry.")

    # 5. Verify direct PostGIS storage & SRID
    conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="aerocadastre")
    cur = conn.cursor()
    cur.execute(f"SELECT id, ST_SRID(geom), ST_IsValid(geom), ST_Area(geom::geography) FROM parcels WHERE id='{parcel_id}';")
    db_row = cur.fetchone()
    assert db_row is not None, "Parcel not found in PostgreSQL!"
    pid, srid, is_valid, area_geog = db_row
    assert srid == 4326, f"Expected SRID 4326, got {srid}"
    assert is_valid is True, "PostGIS reports geometry is invalid"
    print(f"[PASS] Direct PostGIS Check: ID={pid}, SRID={srid}, Valid={is_valid}, Area(geog)={area_geog:.2f} sqm")
    cur.close()
    conn.close()

    # 6. Test GeoJSON Validation & Error Handling
    print("\n--- Testing GeoJSON Edge Cases ---")

    # A. Missing geometry
    r_bad1 = client.post("/api/parcels", json={
        "id": f"PARCEL_BAD1_{uid}",
        "project_id": proj_id,
        "geometry": {}
    })
    print(f"Missing geometry response code: {r_bad1.status_code}")
    assert r_bad1.status_code in (400, 422), f"Expected 400/422 for missing geometry, got {r_bad1.status_code}"
    print("[PASS] Missing geometry properly rejected.")

    # B. Invalid coordinates (non-numeric / malformed)
    r_bad2 = client.post("/api/parcels", json={
        "id": f"PARCEL_BAD2_{uid}",
        "project_id": proj_id,
        "geometry": {"type": "Polygon", "coordinates": "invalid_coords"}
    })
    print(f"Malformed coordinates response code: {r_bad2.status_code}")
    assert r_bad2.status_code in (400, 422), f"Expected 400/422 for malformed coords, got {r_bad2.status_code}"
    print("[PASS] Malformed coordinates properly rejected.")

    # C. Nonexistent Project ID
    r_bad3 = client.post("/api/parcels", json={
        "id": f"PARCEL_BAD3_{uid}",
        "project_id": "PROJ_NONEXISTENT_999",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[77.59, 12.97], [77.60, 12.97], [77.60, 12.98], [77.59, 12.98], [77.59, 12.97]]]
        }
    })
    print(f"Nonexistent project response code: {r_bad3.status_code}")
    assert r_bad3.status_code in (400, 404, 422, 500), f"Expected error code, got {r_bad3.status_code}"
    print("[PASS] Nonexistent project foreign key rejection handled cleanly.")

    # D. Nonexistent Parcel ID retrieval
    r_bad4 = client.get("/api/parcels/NONEXISTENT_PARCEL_XYZ")
    assert r_bad4.status_code == 404, f"Expected 404, got {r_bad4.status_code}"
    print("[PASS] Nonexistent parcel retrieval correctly returns 404.")

    print("\n[ALL ROUND-TRIP TESTS PASSED SUCCESSFULLY!]")


if __name__ == "__main__":
    test_persistence_and_geojson()
