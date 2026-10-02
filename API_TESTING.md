# SIH26012 AeroCadastre — API Testing & Verification Report

## 1. Automated Pytest Suite (`backend/tests/test_backend_api.py`)

The backend is verified independently of the frontend using `pytest` and FastAPI's `TestClient` connected directly to the live **PostgreSQL 16.4 + PostGIS 3.6.2** database (`postgresql+psycopg2://postgres@127.0.0.1:5432/aerocadastre`).

### Run Command

```powershell
python -m pytest backend/tests/test_backend_api.py -v
```

### Test Matrix

| Test Function | Endpoints Covered | Verified Assertions |
|---|---|---|
| `test_01_health_and_postgis_connection` | `GET /api/health` | `status == "ONLINE"`, `database_engine == "PostgreSQL + PostGIS"`, `PostGIS_Version()` >= `3.6`, 22 public tables present, seeded counts > 0. |
| `test_02_authentication_and_unauthorized_access` | `POST /api/auth/login`, `GET /api/auth/me` | `401 Unauthorized` without Bearer token, `401` on invalid password, `200 OK` + JWT issuance on valid credentials, `200 OK` on `/api/auth/me` with Bearer token. |
| `test_03_project_crud_and_persistence` | `GET/POST/PUT/DELETE /api/projects` | Project creation with PostGIS `Polygon` bounding box (`201`), direct SQLAlchemy DB query verification, update (`200`), delete (`200`), post-delete `404`. |
| `test_04_parcel_crud_geojson_and_metric_area` | `GET /api/projects/{id}/parcels`, `GET/POST/PUT/DELETE /api/parcels` | GeoJSON `Polygon` ingestion, `EPSG:32643` metric area (`m²`) & perimeter (`m`) calculation, PostGIS `ST_SRID(geom) == 4326` verification, geometry update, deletion (`200`) & `404`. |
| `test_05_geometry_validation_and_error_handling` | `POST /api/parcels` (Negative cases) | Rejects `LineString` for parcel (`400`/`422`), rejects out-of-bounds WGS84 coordinates `[245, 99]` (`400`/`422`), rejects self-intersecting bowtie polygon (`400`/`422`), rejects non-existent `project_id` (`404`), and verifies clean transaction rollback with zero orphan rows. |
| `test_06_buildings_and_roads_endpoints` | `GET /api/parcels/{id}/buildings`, `GET /api/projects/{id}/roads` | PostGIS `ST_Intersects` building lookup + intersection area (`m²`), road network retrieval, and valid GeoJSON `FeatureCollection` output. |
| `test_07_postgis_topology_conflicts_and_spatial_queries` | `GET /api/parcels/{id}/topology`, `GET /api/parcels/{id}/conflicts`, `GET /api/spatial/nearby` | Creates two overlapping test parcels, verifies PostGIS `ST_Intersects` / `ST_Overlaps` / `ST_Intersection` overlap detection, verifies `TopologyIssue` persistence, tests Reference GIS IoU conflict analysis, and tests `ST_DWithin` proximity search. |
| `test_08_verification_workflow_and_persistence` | `GET /api/verification/queue`, `POST /api/verification`, `PUT /api/verification/{id}` | Inspects active-learning priority queue, creates verification record (`201`), updates reviewer sign-off (`HUMAN_VERIFIED`), and verifies synchronized state in `verification_records` and `parcels`. |
| `test_09_ai_analysis_run_and_persistence` | `POST /api/analysis/run`, `GET /api/analysis/{id}` | Runs PyTorch multi-task inference + polygonization pipeline, persists `AIPrediction` and spatial entities in PostGIS, and retrieves run telemetry by ID. |
| `test_10_ai_council_deliberation_and_persistence` | `POST /api/council/analyze`, `GET /api/council/{parcel_id}` | Runs 6-agent AI Council deliberation on a candidate parcel, persists `CouncilDecision` in PostgreSQL, and retrieves decision history via `GET /api/council/{parcel_id}`. |
| `test_11_exports_generation` | `POST /api/exports` | Generates and validates `GeoJSON`, `GPKG`, `Shapefile` (`.zip`), and `CSV` exports on disk. |

---

## 2. Direct PostGIS Spatial SQL Verification

In addition to HTTP API tests, direct SQL queries against `postgresql+psycopg2://postgres@127.0.0.1:5432/aerocadastre` verify:
- `SELECT PostGIS_Full_Version();` -> `POSTGIS="3.6.2 3.6.2" [EXTENSION] PGSQL="160" GEOS="3.14.1dev-CAPI-1.20.4" PROJ="8.2.1" TOPOLOGY`
- `SELECT COUNT(*), ST_SRID(geom), SUM(ST_IsValid(geom)::int) FROM parcels GROUP BY ST_SRID(geom);` -> Confirming 100% of stored parcel geometries have `SRID=4326` and pass `ST_IsValid(geom)`.
- `SELECT id, ROUND(ST_Area(ST_Transform(geom, 32643))::numeric, 2) AS utm_area_sqm FROM parcels LIMIT 5;` -> Confirming metric area calculations in `EPSG:32643` (UTM Zone 43N).
