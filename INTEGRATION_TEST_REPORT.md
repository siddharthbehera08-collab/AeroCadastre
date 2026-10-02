# SIH26012 AeroCadastre — End-to-End Integration Test Report (`INTEGRATION_TEST_REPORT.md`)

**Date:** 2026-10-01  
**Test Suite:** `backend/tests/test_backend_api.py` + `backend/tests/test_full_system_adversarial.py`  
**Execution Result:** `22/22` Passed (`100.0%`) in `32.78s`

---

## 1. Frontend $\leftrightarrow$ API $\leftrightarrow$ PostGIS Integration Matrix

Every frontend user action in `frontend/src/app/page.tsx`, `frontend/src/components/WebGisEditor.tsx`, `frontend/src/components/TimeMachineView.tsx`, `frontend/src/components/CouncilFlowView.tsx`, and `frontend/src/components/EntrySequence.tsx` was traced and tested through the HTTP contract, FastAPI route, service layer, and PostgreSQL 16.4 + PostGIS 3.6.2 database.

| # | UI Action | Frontend HTTP Request | FastAPI Handler | Service & DB Layer | Verified Response & State Update | Status |
|---|---|---|---|---|---|---|
| 1 | **Login / Role Switch** | `POST /api/auth/token`, `GET /api/auth/me` | `routes_auth.py` | `User` table + PBKDF2-SHA256 + HS256 JWT (`security.py`) | Returns `access_token`, `role` (`ADMIN`, `SURVEYOR`, `VIEWER`); enforces `403` on viewer mutations | `PASS` |
| 2 | **Project Selection** | `GET /api/projects`, `POST /api/projects` | `routes_projects.py` | `Project` + `AuditLog` tables | Returns array of projects (`PROJ_SIH26012_DEMO`); creates/updates/deletes projects in PostgreSQL | `PASS` |
| 3 | **Scene Selection** | `GET /api/scenes?project_id=...` | `routes_legacy.py:list_scenes` | `Parcel`, `Building`, `Road` counts + scene manifest | Returns JSON `Array` of 3 scenes (`scene_urban_T1`, `scene_rural_T1`, `scene_hilly_T1`) with `origin_lonlat`, `crs`, `gsd_m` | `PASS` |
| 4 | **Dashboard Telemetry** | `GET /api/dashboard?project_id=...&scene_id=...` | `routes_legacy.py:get_dashboard_telemetry` | SQL aggregations across `Parcel`, `Building`, `Road`, `TopologyIssue`, `ChangeEvent` | Returns `metrics` with both canonical keys and frontend aliases (`candidate_parcels`, `roads_detected`, `pending_verification`, `gis_conflicts`) | `PASS` |
| 5 | **Scene Spatial Bundle** | `GET /api/scenes/{scene_id}/bundle` | `routes_legacy.py:get_scene_bundle` | PostGIS `ST_AsGeoJSON` serialization of all spatial tables | Returns `candidate_parcels`, `reference_parcels`, `buildings`, `roads`, `land_use`, `boundaries`, `topology_issues`, `council_decisions`, `changes` | `PASS` |
| 6 | **Parcel Loading & Selection** | `GET /api/projects/{id}/parcels`, `GET /api/parcels/{id}` | `routes_parcels.py` | `Parcel` (`Geometry('POLYGON', 4326)`) | Returns GeoJSON `Polygon`, metric `area_sqm` (`EPSG:32643`), `perimeter_m`, `confidence_breakdown`, `ulpin_ready_metadata` | `PASS` |
| 7 | **Building & Road Loading** | `GET /api/parcels/{id}/buildings`, `GET /api/projects/{id}/roads` | `routes_buildings_roads.py` | PostGIS `ST_Intersects(Building.geom, Parcel.geom)` + `Road` table | Returns intersecting building footprints (`roof_type`, `height_m`) and road centerlines (`LINESTRING, 4326`) | `PASS` |
| 8 | **Interactive Parcel Vertex Edit** | `PUT /api/parcels/{id}` | `routes_parcels.py:update_parcel` | `parcel_service.py:update_parcel_record` | Validates polygon via Shapely + PostGIS `ST_IsValid`, recalculates metric area in `EPSG:32643`, increments `version`, writes `FeatureVersion` + `AuditLog` + `HumanFeedback`, re-runs 6-Agent Council | `PASS` |
| 9 | **Parcel Split** | `POST /api/parcels/{id}/split` | `routes_parcels.py:split_existing_parcel` | `parcel_service.py:split_parcel` | Splits parent polygon along `VERTICAL` / `HORIZONTAL` axis at `split_ratio`, creates `P_A` and `P_B` in PostGIS, logs `PARCEL_SPLIT` audit entry | `PASS` |
| 10 | **Parcel Merge** | `POST /api/parcels/merge` | `routes_parcels.py:merge_existing_parcels` | `parcel_service.py:merge_parcels` | Validates shared boundary (`Polygon` union), rejects disjoint/self merges (`400`), persists merged parcel in PostGIS | `PASS` |
| 11 | **Human Verification Action** | `POST /api/verification/{parcel_id}` & `/action` | `routes_verification.py` | `VerificationRecord`, `Parcel`, `HumanFeedback`, `AuditLog` | Transitions parcel status (`VERIFIED`, `REJECTED`, `ESCALATED_TO_FIELD_SURVEY`), appends `HumanFeedback` row | `PASS` |
| 12 | **Multi-Task U-Net Analysis** | `POST /api/analysis/run`, `POST /api/pipeline/run` | `routes_analysis.py`, `routes_legacy.py` | `ml_service.py:run_ai_analysis` + `GeoAIInferenceEngine` | Executes PyTorch `AeroCadastreMultiTaskNet` + DSM fusion, stores `ModelRun` + `AIPrediction`, returns `counts` and `inference_time_ms` | `PASS` |
| 13 | **Live Model Training** | `POST /api/experiments/train` | `routes_legacy.py:run_live_training_experiment` | `backend/ml/trainer.py:train_live_experiment` | Trains Multi-Task U-Net for `N` epochs, persists `ModelRun` with `iou`, `dice_f1`, `boundary_f1`, `parcel_PQ` | `PASS` |
| 14 | **6-Agent AI Council** | `POST /api/council/analyze`, `GET /api/council/{parcel_id}` | `routes_council.py` | `council_service.py:run_council_for_parcel` | Executes all 6 specialized agents over live PostGIS geometry + topology issues, stores `CouncilDecision` | `PASS` |
| 15 | **Temporal Change Detection** | `GET /api/changes` | `routes_legacy.py:list_change_events` | `ChangeEvent` table + `gis/changes.py:compare_epoch_features` | Detects `NEW_BUILDING`, `REMOVED_BUILDING`, `LAND_USE_CHANGE`, `BOUNDARY_SHIFT` across `T0`, `T1`, `T2` | `PASS` |
| 16 | **Parcel Time Machine** | `GET /api/history/{feature_id}` | `routes_legacy.py:get_feature_history` | `FeatureVersion` table | Returns ordered JSON `Array` of historical and human-edited parcel versions (`T0`, `T1`, `T2`, `v1..vN`) | `PASS` |
| 17 | **Field Verification Route** | `GET /api/routes` | `routes_legacy.py:list_field_routes` | `FieldRoute` + `gis/routing.py` | Computes nearest-neighbor + 2-opt tour (`NEAREST_NEIGHBOR_2OPT_HAVERSINE_ROAD_AWARE`) with explicit prototype disclaimer | `PASS` |
| 18 | **Cadastral AI Copilot** | `POST /api/copilot/ask`, `POST /api/copilot/query` | `routes_legacy.py:query_copilot` | `copilot/assistant.py:query_cadastral_copilot` | Queries PostgreSQL/PostGIS live state for parcel conflicts, council votes, area, or project summary | `PASS` |
| 19 | **Dataset Upload & Ingestion** | `POST /api/upload`, `GET /api/datasets` | `routes_legacy.py:upload_dataset` | `gis/ingestion.py:inspect_and_ingest_upload` + `DatasetRecord` | Validates GeoJSON/GPKG/Shapefile/GeoTIFF, extracts CRS & bounds, rejects unsupported/corrupt files (`400`) | `PASS` |
| 20 | **GIS Exports & Download** | `POST /api/exports`, `GET /api/exports/download` | `routes_exports.py` | `export_service.py` + `gis/exporter.py` | Generates valid `GeoJSON`, `GPKG`, `SHP_ZIP`, `CSV` files on disk and streams via `/api/exports/download` | `PASS` |
| 21 | **Audit Logs & Feedback** | `GET /api/audit-logs`, `GET /api/feedback` | `routes_legacy.py` | `AuditLog`, `HumanFeedback` tables | Returns immutable chronological audit and active-learning feedback arrays | `PASS` |

---

## 2. Persistence & Reload Verification

- **Database Round-Trip Verified:** Every mutation (`POST /api/projects`, `POST /api/parcels`, `PUT /api/parcels/{id}`, `POST /api/parcels/{id}/split`, `POST /api/parcels/merge`, `POST /api/verification/{id}`, `POST /api/council/analyze`) commits to PostgreSQL (`aerocadastre`) and survives browser refresh and FastAPI server restarts.
- **Zero Hardcoded Fallbacks:** All API endpoints query SQLAlchemy/PostGIS models directly.
