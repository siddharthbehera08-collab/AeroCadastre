# SIH26012 AeroCadastre — REST & Spatial API Validation (`API_VALIDATION.md`)

**Date:** 2026-10-01  
**Framework:** FastAPI `0.135.2` + Pydantic `2.11`  
**OpenAPI Spec:** `http://127.0.0.1:8000/openapi.json` (`42` mounted route operations)

---

## 1. Complete Endpoint Validation Matrix

Every endpoint was tested across valid payloads, missing required fields (`422`), wrong data types (`422`), nonexistent IDs (`404`), duplicate keys (`409`), malformed GeoJSON (`400/422`), unauthorized tokens (`401`), and insufficient RBAC permissions (`403`).

| Method & Path | Auth / RBAC | Valid Status | Invalid / Edge Statuses Verified | Backed By PostgreSQL Table(s) |
|---|---|---|---|---|
| `GET /api/health` | Public | `200 OK` | Returns PostGIS version + live table counts | `pg_catalog`, `postgis_full_version()` |
| `POST /api/auth/token` | Public | `200 OK` | `401` wrong password / unknown user, `422` missing fields | `users` |
| `GET /api/auth/me` | Bearer JWT | `200 OK` | `401` missing or forged token | `users` |
| `GET /api/projects` | Public / JWT | `200 OK` | Returns JSON `Array` of `ProjectResponse` | `projects` |
| `POST /api/projects` | `ADMIN`/`SURVEYOR` | `201 Created` | `403` `VIEWER`, `409` duplicate ID, `422` invalid AOI | `projects`, `audit_logs` |
| `GET /api/projects/{id}` | Public / JWT | `200 OK` | `404` nonexistent project | `projects` |
| `PUT /api/projects/{id}` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` nonexistent project | `projects`, `audit_logs` |
| `DELETE /api/projects/{id}` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` nonexistent project | `projects` (cascades) |
| `GET /api/projects/{id}/parcels` | Public / JWT | `200 OK` | `200 []` for empty project; filters by `scene_id`, `is_reference` | `parcels` |
| `GET /api/parcels/{id}` | Public / JWT | `200 OK` | `404` nonexistent parcel | `parcels` |
| `POST /api/parcels` | `ADMIN`/`SURVEYOR` | `201 Created` | `403` `VIEWER`, `409` duplicate ID, `400/422` invalid/micro/huge geometry | `parcels`, `feature_versions`, `audit_logs` |
| `PUT /api/parcels/{id}` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` missing, `400/422` invalid geometry | `parcels`, `feature_versions`, `human_feedback`, `audit_logs` |
| `DELETE /api/parcels/{id}` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` nonexistent parcel | `parcels`, `audit_logs` |
| `POST /api/parcels/{id}/split` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` missing, `400` bad axis, `422` extreme ratio | `parcels`, `feature_versions`, `audit_logs` |
| `POST /api/parcels/merge` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `400` self-merge or disjoint non-touching merge | `parcels`, `feature_versions`, `audit_logs` |
| `GET /api/parcels/{id}/buildings` | Public / JWT | `200 OK` | `404` nonexistent parcel | `buildings`, `parcels` (`ST_Intersects`) |
| `GET /api/projects/{id}/roads` | Public / JWT | `200 OK` | Returns `LINESTRING, 4326` road features | `roads` |
| `GET /api/parcels/{id}/topology` | Public / JWT | `200 OK` | `404` nonexistent parcel | `parcels`, `buildings`, `roads`, `topology_issues` |
| `GET /api/parcels/{id}/conflicts` | Public / JWT | `200 OK` | `404` nonexistent parcel | `topology_issues`, PostGIS spatial SQL |
| `GET /api/verification/queue` | Public / JWT | `200 OK` | Filters by `project_id`, `scene_id`, `status` | `verification_records`, `parcels` |
| `POST /api/verification` | `ADMIN`/`SURVEYOR` | `201 Created` | `403` `VIEWER`, `404` nonexistent parcel, `422` invalid status | `verification_records`, `parcels`, `human_feedback`, `audit_logs` |
| `PUT /api/verification/{id}` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` nonexistent record | `verification_records`, `parcels`, `human_feedback`, `audit_logs` |
| `POST /api/verification/{parcel_id}` | `ADMIN`/`SURVEYOR` | `200 OK` | `403` `VIEWER`, `404` nonexistent parcel | `verification_records`, `parcels`, `human_feedback`, `audit_logs` |
| `POST /api/analysis/run` | `ADMIN`/`SURVEYOR` | `200 OK` | `404` nonexistent project | `model_runs`, `ai_predictions`, `audit_logs` |
| `GET /api/analysis/{id}` | Public / JWT | `200 OK` | `404` nonexistent model run | `model_runs`, `ai_predictions` |
| `POST /api/council/analyze` | Public / JWT | `200 OK` | `404` nonexistent parcel | `council_decisions`, `parcels`, `topology_issues` |
| `GET /api/council/{parcel_id}` | Public / JWT | `200 OK` | `404` nonexistent parcel | `council_decisions` |
| `POST /api/exports` | Public / JWT | `200 OK` | `422` unsupported format (`GeoJSON`, `GPKG`, `SHP_ZIP`, `CSV` supported) | `parcels`, `buildings`, `roads`, `audit_logs` |
| `GET /api/exports/download` | Public / JWT | `200 OK` | `403` path traversal attempt, `404` missing file | Filesystem (`outputs/exports/`) |
| `GET /api/scenes` | Public / JWT | `200 OK` | Returns JSON `Array` of scenes with manifest metadata | `parcels`, `buildings`, `roads` |
| `GET /api/scenes/{id}/bundle` | Public / JWT | `200 OK` | Returns full spatial bundle for `WebGisEditor.tsx` | All spatial tables |
| `GET /api/dashboard` | Public / JWT | `200 OK` | Live SQL KPI aggregation | All tables |
| `GET /api/history/{feature_id}` | Public / JWT | `200 OK` | Returns JSON `Array` of `FeatureVersion` rows | `feature_versions` |
| `GET /api/changes` | Public / JWT | `200 OK` | Returns JSON `Array` of `ChangeEvent` rows | `change_events` |
| `GET /api/routes` | Public / JWT | `200 OK` | Returns JSON `Array` of `FieldRoute` rows | `field_routes` |
| `POST /api/copilot/ask` | Public / JWT | `200 OK` | `422` empty query; handles unknown parcel/project cleanly | `parcels`, `topology_issues`, `council_decisions`, `change_events` |
| `POST /api/upload` | `ADMIN`/`SURVEYOR` | `200 OK` | `400` unsupported extension / empty file | `datasets`, `audit_logs` |
| `GET /api/datasets` | Public / JWT | `200 OK` | Returns JSON `Array` of `DatasetRecord` rows | `datasets` |
| `GET /api/experiments` | Public / JWT | `200 OK` | Returns JSON `Array` of `ModelRun` rows | `model_runs` |
| `POST /api/experiments/train` | `ADMIN`/`SURVEYOR` | `200 OK` | Trains PyTorch Multi-Task U-Net & saves `ModelRun` | `model_runs` |
| `GET /api/feedback` | Public / JWT | `200 OK` | Returns JSON `Array` of `HumanFeedback` rows | `human_feedback` |
| `GET /api/audit-logs` | Public / JWT | `200 OK` | Returns JSON `Array` of `AuditLog` rows | `audit_logs` |
