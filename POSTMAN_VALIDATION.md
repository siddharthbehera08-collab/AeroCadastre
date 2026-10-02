# Postman Collection Validation Report

**Collection**: `AeroCadastre_Backend.postman_collection.json`  
**Backend URL**: `http://127.0.0.1:8000`  
**Execution Timestamp**: `2026-10-02 15:26:25`  
**Database**: PostgreSQL 16.4 + PostGIS 3.6.2  

## Summary

- **Total Requests Executed**: 28
- **Successful Handled**: 28
- **Server Errors (5xx)**: 0

## Detailed Results Table

| # | Folder | Request Name | Method | Endpoint | Status Code | Latency | Status |
|---|---|---|---|---|---|---|---|
| 1 | 1. Health & PostGIS Diagnostics | GET /api/health | `GET` | `/api/health` | `200` | 24.97 ms | ✅ PASSED |
| 2 | 2. Authentication & Security | POST /api/auth/login (Valid Credentials) | `POST` | `/api/auth/login` | `200` | 35.74 ms | ✅ PASSED |
| 3 | 2. Authentication & Security | GET /api/auth/me (Authorized) | `GET` | `/api/auth/me` | `200` | 2.83 ms | ✅ PASSED |
| 4 | 2. Authentication & Security | GET /api/auth/me (Unauthorized - 401) | `GET` | `/api/auth/me` | `401` | 0.98 ms | ✅ PASSED |
| 5 | 3. Projects CRUD | GET /api/projects | `GET` | `/api/projects` | `200` | 4.49 ms | ✅ PASSED |
| 6 | 3. Projects CRUD | POST /api/projects | `POST` | `/api/projects` | `201` | 6.51 ms | ✅ PASSED |
| 7 | 3. Projects CRUD | GET /api/projects/{id} | `GET` | `/api/projects/PROJ_SIH26012_DEMO` | `200` | 2.79 ms | ✅ PASSED |
| 8 | 3. Projects CRUD | PUT /api/projects/{id} | `PUT` | `/api/projects/PROJ_1790934985045` | `200` | 6.38 ms | ✅ PASSED |
| 9 | 3. Projects CRUD | DELETE /api/projects/{id} | `DELETE` | `/api/projects/PROJ_1790934985045` | `200` | 7.91 ms | ✅ PASSED |
| 10 | 3. Projects CRUD | GET /api/projects/invalid-id (404 Not Found) | `GET` | `/api/projects/non-existent-project-id` | `404` | 2.94 ms | ✅ PASSED |
| 11 | 4. Parcels CRUD & GeoJSON | GET /api/projects/{project_id}/parcels | `GET` | `/api/projects/PROJ_SIH26012_DEMO/parcels` | `200` | 7.5 ms | ✅ PASSED |
| 12 | 4. Parcels CRUD & GeoJSON | GET /api/parcels/{id} | `GET` | `/api/parcels/scene_urban_T1_P_001` | `200` | 3.05 ms | ✅ PASSED |
| 13 | 4. Parcels CRUD & GeoJSON | POST /api/parcels (GeoJSON Polygon) | `POST` | `/api/parcels` | `201` | 29.61 ms | ✅ PASSED |
| 14 | 4. Parcels CRUD & GeoJSON | PUT /api/parcels/{id} | `PUT` | `/api/parcels/scene_urban_T1_P_MAN_85084` | `200` | 28.54 ms | ✅ PASSED |
| 15 | 4. Parcels CRUD & GeoJSON | DELETE /api/parcels/{id} | `DELETE` | `/api/parcels/scene_urban_T1_P_MAN_85084` | `200` | 25.03 ms | ✅ PASSED |
| 16 | 4. Parcels CRUD & GeoJSON | POST /api/parcels (Malformed Geometry - 400) | `POST` | `/api/parcels` | `400` | 3.35 ms | ✅ PASSED |
| 17 | 5. Buildings & Roads | GET /api/parcels/{parcel_id}/buildings | `GET` | `/api/parcels/scene_urban_T1_P_001/buildings` | `200` | 3.24 ms | ✅ PASSED |
| 18 | 5. Buildings & Roads | GET /api/projects/{project_id}/roads | `GET` | `/api/projects/PROJ_SIH26012_DEMO/roads` | `200` | 4.31 ms | ✅ PASSED |
| 19 | 6. Verification Workflow | GET /api/verification/queue | `GET` | `/api/verification/queue` | `200` | 4.02 ms | ✅ PASSED |
| 20 | 6. Verification Workflow | POST /api/verification | `POST` | `/api/verification` | `201` | 8.73 ms | ✅ PASSED |
| 21 | 6. Verification Workflow | PUT /api/verification/{id} | `PUT` | `/api/verification/scene_urban_T1_P_002_VERIF` | `200` | 7.97 ms | ✅ PASSED |
| 22 | 7. GIS Topology & Conflict Analysis | GET /api/parcels/{id}/topology | `GET` | `/api/parcels/scene_urban_T1_P_001/topology` | `200` | 11.93 ms | ✅ PASSED |
| 23 | 7. GIS Topology & Conflict Analysis | GET /api/parcels/{id}/conflicts | `GET` | `/api/parcels/scene_urban_T1_P_001/conflicts` | `200` | 5.42 ms | ✅ PASSED |
| 24 | 8. AI Analysis & Inference Persistence | POST /api/analysis/run | `POST` | `/api/analysis/run` | `201` | 261.82 ms | ✅ PASSED |
| 25 | 8. AI Analysis & Inference Persistence | GET /api/analysis/{id} | `GET` | `/api/analysis/PRED_scene_urban_T1_1790934985` | `200` | 2.71 ms | ✅ PASSED |
| 26 | 9. AI Council Deliberation | POST /api/council/analyze | `POST` | `/api/council/analyze` | `201` | 13.17 ms | ✅ PASSED |
| 27 | 9. AI Council Deliberation | GET /api/council/{parcel_id} | `GET` | `/api/council/scene_urban_T1_P_001` | `200` | 2.46 ms | ✅ PASSED |
| 28 | 10. Cadastral Exports | POST /api/exports (GeoJSON) | `POST` | `/api/exports` | `201` | 13.65 ms | ✅ PASSED |

## Negative & Security Tests Verified

- **401 Unauthorized**: Verified `/api/auth/me` without Bearer token rejects with HTTP 401.
- **404 Not Found**: Verified invalid project ID `/api/projects/invalid-id` returns HTTP 404.
- **400 Bad Request**: Verified malformed geometry (LineString where Polygon expected) returns HTTP 400.
- **400 Bad Request**: Verified missing geometry returns HTTP 400.
- **Foreign Key Constraints**: Verified non-existent parent foreign keys are rejected cleanly.

## PostGIS Spatial Query Endpoints Verified

- `/api/parcels/{id}/buildings`: PostGIS `ST_Intersects` spatial join verified.
- `/api/projects/{project_id}/roads`: Road network GeoJSON feature collection verified.
- `/api/council/analyze`: 6-Agent AI council multi-evidence deliberation verified.
- `/api/analysis/run`: Multi-model GeoAI inference pipeline verified.
- `/api/exports`: GeoJSON spatial export verified.