# SIH26012 AeroCadastre — Regression Test Report (`REGRESSION_TEST_REPORT.md`)

**Date:** 2026-10-01  
**Command Executed:** `python -m pytest backend/tests/ -v --tb=short`  
**Total Tests:** `22` (`11` core backend suites + `11` full-system integration & adversarial suites)  
**Pass Rate:** `22 / 22` (`100.0%`)  
**Total Execution Time:** `32.78s`

---

## 1. Automated Pytest Execution Log

| Test ID | Suite File | Test Function | Duration / Result | Coverage Area |
|---|---|---|---|---|
| `01` | `test_backend_api.py` | `test_01_health_and_postgis_connection` | `PASSED` | `/api/health`, PostgreSQL 16.4 + PostGIS 3.6.2 version & active table counts |
| `02` | `test_backend_api.py` | `test_02_authentication_and_unauthorized_access` | `PASSED` | `/api/auth/token`, `/api/auth/me`, PBKDF2 password verification, invalid token rejection |
| `03` | `test_backend_api.py` | `test_03_project_crud_and_persistence` | `PASSED` | `GET/POST/PUT/DELETE /api/projects`, duplicate `409`, nonexistent `404` |
| `04` | `test_backend_api.py` | `test_04_parcel_crud_geojson_and_metric_area` | `PASSED` | `GET/POST/PUT/DELETE /api/parcels`, `EPSG:32643` area/perimeter accuracy, `FeatureVersion` tracking |
| `05` | `test_backend_api.py` | `test_05_geometry_validation_and_error_handling` | `PASSED` | Bowtie self-intersection repair, collinear rejection, missing coordinates rejection |
| `06` | `test_backend_api.py` | `test_06_buildings_and_roads_endpoints` | `PASSED` | `GET /api/parcels/{id}/buildings`, `GET /api/projects/{id}/roads` |
| `07` | `test_backend_api.py` | `test_07_postgis_topology_conflicts_and_spatial_queries` | `PASSED` | `GET /api/parcels/{id}/topology`, `GET /api/parcels/{id}/conflicts`, PostGIS `ST_Overlaps`/`ST_Intersects` |
| `08` | `test_backend_api.py` | `test_08_verification_workflow_and_persistence` | `PASSED` | `GET /api/verification/queue`, `POST /api/verification`, `PUT /api/verification/{id}`, `POST /api/verification/{id}/action` |
| `09` | `test_backend_api.py` | `test_09_ai_analysis_run_and_persistence` | `PASSED` | `POST /api/analysis/run`, `GET /api/analysis/{id}`, `ModelRun` + `AIPrediction` persistence |
| `10` | `test_backend_api.py` | `test_10_ai_council_deliberation_and_persistence` | `PASSED` | `POST /api/council/analyze`, `GET /api/council/{parcel_id}`, 6-Agent deliberation & persistence |
| `11` | `test_backend_api.py` | `test_11_exports_generation` | `PASSED` | `POST /api/exports` (`GeoJSON`, `GPKG`, `SHP_ZIP`, `CSV`) & `/api/exports/download` |
| `12` | `test_full_system_adversarial.py` | `test_12_frontend_api_contract_alignment` | `PASSED` | Verifies exact JSON shapes required by `page.tsx`, `WebGisEditor.tsx`, `TimeMachineView.tsx`, `CouncilFlowView.tsx` |
| `13` | `test_full_system_adversarial.py` | `test_13_rbac_authorization_and_security_controls` | `PASSED` | Enforces `403 Forbidden` for `VIEWER`/`DEMO_USER` on mutations, `401` on forged JWTs, SQLi safety |
| `14` | `test_full_system_adversarial.py` | `test_14_parcel_editing_split_merge_adversarial` | `PASSED` | Valid split/merge, extreme split ratios, invalid axis, self-merge rejection, disjoint merge rejection, micro/huge area rejection |
| `15` | `test_full_system_adversarial.py` | `test_15_postgis_native_spatial_functions_and_topology_torture` | `PASSED` | Direct PostGIS `ST_IsValid`, `ST_MakeValid`, `ST_Area(ST_Transform(..., 32643))`, `ST_Intersects`, `ST_Distance` |
| `16` | `test_full_system_adversarial.py` | `test_16_ml_pipeline_adversarial_inputs` | `PASSED` | Missing file, empty array, wrong channels, `NaN`/`Inf`, extreme dimensions, all-black/all-white tiles |
| `17` | `test_full_system_adversarial.py` | `test_17_ai_council_six_agents_and_disagreement_scenarios` | `PASSED` | Clean parcel (`APPROVE_CANDIDATE`), conflicting parcel (`HUMAN_REVIEW_REQUIRED` / `FIELD_VERIFICATION`), poor geometry (`REJECT_OR_RE_SEGMENT`) |
| `18` | `test_full_system_adversarial.py` | `test_18_temporal_change_detection_and_field_route_edge_cases` | `PASSED` | `T0`/`T1`/`T2` `compare_epoch_features` (`NEW_BUILDING`, `REMOVED_BUILDING`, `LAND_USE_CHANGE`, `BOUNDARY_SHIFT`) & `0`/`1`/`N`-stop field routes |
| `19` | `test_full_system_adversarial.py` | `test_19_copilot_contextual_and_edge_case_queries` | `PASSED` | Parcel-specific query, unknown parcel (`P_999`), unknown project, conflict summary, empty query rejection |
| `20` | `test_full_system_adversarial.py` | `test_20_dataset_upload_and_export_matrix_with_security_checks` | `PASSED` | Valid GeoJSON upload, corrupt upload, `.exe` rejection, `0`/`1`/`N`-parcel exports across all 4 formats, path traversal `403` |
| `21` | `test_full_system_adversarial.py` | `test_21_performance_benchmarks_10_100_500_1000_parcels` | `PASSED` | PostGIS bulk insert, spatial index query, and FastAPI serialization at `10`, `100`, `500`, `1000` parcels |
| `22` | `test_full_system_adversarial.py` | `test_22_transaction_rollback_geojson_types_and_live_training` | `PASSED` | DB rollback atomicity, `Polygon`/`MultiPolygon`/`Feature`/`FeatureCollection` normalization, `/api/experiments/train` |

---

## 2. Bugs Fixed & Regression-Verified During QA Phase

1. **Frontend Array Unwrapping (`scenes`, `experiments`, `datasets`, `audit-logs`, `history/{id}`)**: Fixed in [`routes_legacy.py`](file:///d:/SIH26012_AeroCadastre/backend/app/api/routes_legacy.py) and locked in by `test_12_frontend_api_contract_alignment`.
2. **`ChangeEvent.metrics_json` Serialization**: Fixed `AttributeError: 'ChangeEvent' object has no attribute 'details_json'` in [`routes_legacy.py`](file:///d:/SIH26012_AeroCadastre/backend/app/api/routes_legacy.py) (lines 642 and 930), exposing both `"details"` and `"metrics"` dicts.
3. **RBAC Enforcement on Cadastral Mutations**: Added `get_optional_user` and `assert_operator_can_mutate` in [`security.py`](file:///d:/SIH26012_AeroCadastre/backend/app/core/security.py), wired into parcel CRUD/split/merge, project CRUD, and verification routes; locked in by `test_13_rbac_authorization_and_security_controls`.
4. **Disjoint Parcel Merge & Area Bounds**: Added `MultiPolygon` union rejection and `[1.0, 5000000.0]` m² area bounds in [`parcel_service.py`](file:///d:/SIH26012_AeroCadastre/backend/app/services/parcel_service.py); locked in by `test_14_parcel_editing_split_merge_adversarial`.
5. **Path Traversal Protection on Export Download**: Added strict directory containment check in [`routes_exports.py`](file:///d:/SIH26012_AeroCadastre/backend/app/api/routes_exports.py); locked in by `test_20_dataset_upload_and_export_matrix_with_security_checks`.
