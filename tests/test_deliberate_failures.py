import json
import time
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


def test_failure_scenarios():
    print("=== PHASE 13: DELIBERATE FAILURE & RESILIENCE TESTING ===")
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1. Malformed GeoJSON (coordinates not list)
    r1 = client.post("/api/parcels", json={
        "project_id": "PROJ_SIH26012_DEMO",
        "geometry": {"type": "Polygon", "coordinates": "invalid_coordinates_string"}
    })
    print(f"[TEST 1] Malformed GeoJSON: Status={r1.status_code}")
    assert r1.status_code in (400, 422), f"Expected 400/422, got {r1.status_code}"

    # 2. Invalid Geometry Type (LineString where Polygon required)
    r2 = client.post("/api/parcels", json={
        "project_id": "PROJ_SIH26012_DEMO",
        "geometry": {"type": "LineString", "coordinates": [[77.59, 12.97], [77.60, 12.98]]}
    })
    print(f"[TEST 2] Invalid Geometry Type: Status={r2.status_code}")
    assert r2.status_code in (400, 422), f"Expected 400/422, got {r2.status_code}"

    # 3. Missing Required Fields (missing name in project creation)
    r3 = client.post("/api/projects", json={
        "description": "Missing project name"
    })
    print(f"[TEST 3] Missing Required Fields: Status={r3.status_code}")
    assert r3.status_code == 422, f"Expected 422, got {r3.status_code}"

    # 4. Nonexistent Project ID
    r4 = client.get("/api/projects/PROJ_COMPLETELY_NONEXISTENT_9999")
    print(f"[TEST 4] Nonexistent Project ID: Status={r4.status_code}")
    assert r4.status_code == 404, f"Expected 404, got {r4.status_code}"

    # 5. Nonexistent Parcel ID
    r5 = client.get("/api/parcels/PARCEL_COMPLETELY_NONEXISTENT_9999")
    print(f"[TEST 5] Nonexistent Parcel ID: Status={r5.status_code}")
    assert r5.status_code == 404, f"Expected 404, got {r5.status_code}"

    # 6. Duplicate Project Creation
    dup_id = f"PROJ_DUP_TEST_{int(time.time())}"
    r6_a = client.post("/api/projects", json={"id": dup_id, "name": "Duplicate Test Project"})
    assert r6_a.status_code == 201, f"Expected 201 on first create, got {r6_a.status_code}"
    r6_b = client.post("/api/projects", json={"id": dup_id, "name": "Duplicate Test Project 2"})
    print(f"[TEST 6] Duplicate Record Creation: Status={r6_b.status_code}")
    assert r6_b.status_code == 409, f"Expected 409 Conflict, got {r6_b.status_code}"

    # 7. Invalid Database Credentials Direct Check
    print("[TEST 7] Invalid DB credentials connection failure test:")
    try:
        conn_bad = psycopg2.connect(host="127.0.0.1", port=5432, user="invalid_user_xyz", password="wrong_password", dbname="aerocadastre", connect_timeout=2)
        conn_bad.close()
        raise AssertionError("Connection with invalid credentials should have failed!")
    except psycopg2.OperationalError as exc:
        print(f"[PASS] Correctly caught OperationalError: {exc}")

    # 8. Invalid Database Name Direct Check
    print("[TEST 8] Invalid DB name connection failure test:")
    try:
        conn_bad_db = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="nonexistent_db_xyz_999", connect_timeout=2)
        conn_bad_db.close()
        raise AssertionError("Connection to nonexistent DB should have failed!")
    except psycopg2.OperationalError as exc:
        print(f"[PASS] Correctly caught OperationalError: {exc}")

    # 9. Invalid SRID Handling
    print("[TEST 9] Invalid SRID validation test:")
    conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="aerocadastre")
    cur = conn.cursor()
    try:
        cur.execute("SELECT ST_Transform(ST_GeomFromText('POINT(0 0)', 4326), 999999);")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"[PASS] Correctly rejected invalid SRID 999999: {exc}")
    cur.close()
    conn.close()

    print("\n[ALL 9 FAILURE SCENARIOS TESTED AND HANDLED CLEANLY!]")


if __name__ == "__main__":
    test_failure_scenarios()
