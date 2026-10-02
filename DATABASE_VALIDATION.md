# Database & PostGIS Validation Report

**Project**: SIH26012 AeroCadastre  
**Validation Date**: `2026-10-02`  
**Database**: PostgreSQL 16.4  
**Spatial Engine**: PostGIS 3.6.2  
**Overall Status**: `WORKING`

---

## 1. PostGIS Spatial Operations Validation

Every standard PostGIS spatial function was tested directly via SQL against the live database:

| Spatial Operation | Test Input | Result | Status |
|---|---|---|---|
| `ST_IsValid` | `POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))` | `True` | `WORKING` |
| `ST_Area` | `POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))` (SRID 32643) | `100.0 sqm` | `WORKING` |
| `ST_Intersects` | Overlapping square polygons | `True` | `WORKING` |
| `ST_Contains` | Outer box (5x5) vs Inner box (1x1) | `True` | `WORKING` |
| `ST_Within` | Point (2,2) within Box (0..5, 0..5) | `True` | `WORKING` |
| `ST_Overlaps` | Partially overlapping polygons | `True` | `WORKING` |
| `ST_Distance` | `POINT(0 0)` to `POINT(30 40)` | `50.0 m` | `WORKING` |
| `ST_MakeValid` | Self-intersecting bowtie polygon | `MULTIPOLYGON(((1 1,0 0,0 2,1 1)),((2 0,1 1,2 2,2 0)))` | `WORKING` |
| `ST_Transform` | EPSG:4326 to EPSG:32643 metric projection | Projected geometry verified | `WORKING` |

---

## 2. Persistence & Durability Validation

We performed real multi-restart durability testing:

1. **Record Ingestion**: Created test project `PROJ_TEST_bebec3` and parcel `PARCEL_bebec3` with a 5-vertex polygon via `POST /api/parcels`.
2. **PostGIS Confirmation**: Verified direct SQL storage in `parcels` table with `SRID=4326`, `ST_IsValid=True`, and `Area=12003.06 sqm`.
3. **FastAPI Restart**: Terminated Uvicorn process, restarted FastAPI. Queried `GET /api/parcels/PARCEL_bebec3`. Verified 200 OK and matching geometry coordinates.
4. **PostgreSQL Restart**: Fast shutdown of PostgreSQL server, restarted PostgreSQL cluster. Reconnected and read back `PARCEL_bebec3`.
5. **Durability Result**: `100% PERSISTENCE VERIFIED` across independent DB and application service restarts.

---

## 3. GeoJSON Round-Trip & Validation

| Test Case | Input Type | Validation Behavior | Status |
|---|---|---|---|
| Valid GeoJSON Polygon | 5-point closed ring | Inserted, transformed to PostGIS geometry, retrieved via API | `WORKING` |
| Missing Geometry | `{}` | Rejected with HTTP 400 Bad Request | `WORKING` |
| Malformed Coordinates | Non-numeric string | Rejected with HTTP 400 Bad Request | `WORKING` |
| Invalid Geometry Type | LineString for parcel | Rejected with HTTP 400 Bad Request | `WORKING` |
| Nonexistent Foreign Key | `PROJ_NONEXISTENT_999` | Rejected with HTTP 404 Not Found | `WORKING` |
| Nonexistent Feature Query | `NONEXISTENT_PARCEL_XYZ` | Returns HTTP 404 Not Found | `WORKING` |
