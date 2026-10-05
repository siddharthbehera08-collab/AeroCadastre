# AeroCadastre SIH26012 — Backend REST API Specification & Guide
**Base URL:** `http://localhost:8000/api`  
**API Version:** 2.0.0  
**Specification Framework:** FastAPI / OpenAPI 3.0  

---

## 1. Endpoints Overview Table

| Category | Method | Path | Description | Supported Query / Body Parameters |
| :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | System health and database connection status | None |
| **System** | `GET` | `/dashboard` | Macro summary statistics for active project | `project_id`, `scene_id` |
| **Projects** | `POST` | `/projects` | Create a new cadastral mapping project | `name`, `description`, `crs`, `study_area_bbox` |
| **Datasets** | `POST` | `/projects/{id}/datasets` | Register an optical/terrain/reference dataset | `dataset_type`, `file_path`, `crs`, `modality` |
| **Pipeline** | `POST` | `/projects/{id}/process` | Trigger end-to-end processing pipeline job | `scene_id`, `data_mode` (`REAL` or `SYNTHETIC`) |
| **Pipeline** | `GET` | `/projects/{id}/status` | Check status of active pipeline job | `job_id` |
| **Layers** | `GET` | `/projects/{id}/layers` | Retrieve active vector and raster layer catalog | None |
| **Parcels** | `GET` | `/projects/{id}/parcels` | Query candidate parcel polygons (GeoJSON) | `min_confidence`, `status`, `limit`, `offset` |
| **Evidence** | `GET` | `/projects/{id}/evidence` | Inspect multi-source boundary evidence lines | `scene_id` |
| **Anomalies**| `GET` | `/projects/{id}/anomalies` | Query geometry anomalies and GIS conflicts | `severity`, `type` |
| **Council** | `GET` | `/projects/{id}/verification` | Query AI Council recommendations & field queue | `status`, `priority` |
| **Audit** | `GET` | `/projects/{id}/audit` | Retrieve complete cryptographic provenance trail | `limit` |
| **HITL** | `POST` | `/projects/{id}/verify` | Submit surveyor review action (Approve/Reject/Edit) | `parcel_id`, `action`, `surveyor_id`, `geometry` |
| **Export** | `POST` | `/projects/{id}/export` | Generate ULPIN-compliant GIS export package | `format` (`GeoJSON`, `GeoPackage`, `Shapefile`) |
| **Copilot** | `POST` | `/copilot/query` | Grounded Cadastral AI Copilot question answering | `query`, `parcel_id` |

---

## 2. Request & Response Examples

### Trigger Pipeline Job
`POST /api/projects/PROJ_001/process`
```json
{
  "scene_id": "PUNE_URBAN_01",
  "data_mode": "SYNTHETIC"
}
```

Response:
```json
{
  "job_id": "JOB-1728000000",
  "project_id": "PROJ_001",
  "status": "COMPLETED",
  "stages_completed": 11,
  "execution_time_ms": 29.43,
  "candidate_parcels_count": 4,
  "disclaimer": "SYNTHETIC PIPELINE EXECUTION ONLY. NOT STATUTORY CADASTRE."
}
```

### Cadastral Copilot Query
`POST /api/copilot/query`
```json
{
  "query": "Why was candidate parcel P-01 flagged for field inspection?",
  "parcel_id": "P-01"
}
```

Response:
```json
{
  "query": "Why was candidate parcel P-01 flagged for field inspection?",
  "response": "Candidate parcel P-01 is flagged with 1 inspection issue(s). Current confidence is 0.42 (LOW). Ground verification is strongly advised before boundary confirmation.",
  "grounded": true,
  "disclaimer": "ADVISORY AI ASSISTANCE ONLY. AeroCadastre outputs represent candidate boundaries inferred from multi-source remote sensing and terrain signals."
}
```
