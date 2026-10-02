# SIH26012 AeroCadastre — Comprehensive Backend Audit (`BACKEND_AUDIT.md`)

**Date:** 2026-10-01  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Phase:** Backend Engineering Phase — Audit of Existing Architecture, Database, GIS, ML, AI Council, and API Contracts

---

## 1. What Currently Exists

### 1.1 Directory & Module Structure
- **Monolithic Backend Layout (`backend/`)**:
  - `backend/main.py` (1,285 lines): Monolithic FastAPI application containing all route definitions, serialization helpers, topology/route recomputation triggers, and startup seeding.
  - `backend/config.py`: Path resolution and constants (`DEFAULT_SQLITE_URL`, `LAND_USE_CLASSES`, `BOUNDARY_TYPES`, `COUNCIL_ACTIONS`).
  - `backend/db.py`: SQLAlchemy engine setup that defaults to `sqlite:///D:/SIH26012_AeroCadastre/database/aerocadastre_postgis.db` and registers custom Python-level `ST_*` functions (`ST_AsGeoJSON`, `ST_Area`, `ST_Intersects`, etc.) on SQLite connections via Shapely + PyProj.
  - `backend/models.py`: 18 SQLAlchemy declarative models (`Project`, `Dataset`, `Raster`, `Building`, `Road`, `LandUse`, `Boundary`, `Parcel`, `TopologyIssue`, `Anomaly`, `ChangeEvent`, `CouncilDecision`, `VerificationTask`, `FieldRoute`, `FeatureVersion`, `ModelRun`, `AIPrediction`, `Evidence`, `HumanFeedback`, `AuditLog`). Notably, **all geometry columns (`geom`) are defined as `Column(Text)`** storing WKT strings alongside `geometry_geojson = Column(Text)` rather than native PostGIS `Geometry` columns, and there is **no `User` table/model**.
  - `backend/schemas.py`: 8 request-only Pydantic models (`ProjectCreateRequest`, `PipelineRunRequest`, `ParcelCreateRequest`, `ParcelUpdateRequest`, `ParcelSplitRequest`, `ParcelMergeRequest`, `VerificationActionRequest`, `CopilotQueryRequest`, `ExportRequest`). Response schemas are unstructured `Dict[str, Any]` dictionaries.
  - `backend/gis/`:
    - `pipeline.py`: 24-step orchestrator running scene ingestion, PyTorch inference, topology checks, conflict/anomaly detection, temporal change detection, 6-agent AI Council evaluation, and route planning.
    - `topology.py`: Shapely-based topology validator checking `SELF_INTERSECTION`, `INVALID_RING`, `DISCONNECTED`, `HOLE`, `SLIVER`, `DUPLICATE`, `OVERLAP`, `GAP`, and `INVALID_CRS`.
    - `conflicts_anomalies.py`: Compares candidate parcels against reference GIS parcels, buildings, and road corridors (`BOUNDARY_MISMATCH`, `EXTRA_PARCEL`, `BUILDING_CROSSING_BOUNDARY`, `ROAD_PARCEL_CONFLICT`, `EXTREME_AREA`, `UNUSUAL_SHAPE`, `MODEL_DISAGREEMENT`).
    - `changes.py`: Multi-epoch comparator (`T0` 2024 vs `T1` 2025 vs `T2` 2026) generating `ChangeEvent` and `FeatureVersion` records.
    - `exporter.py`: Multi-format GIS exporter (`GeoJSON`, `Shapefile` `.zip`, `CSV` with WKT, `GeoPackage` `.gpkg`) with post-export read-back verification.
    - `ingestion.py`: Upload inspector validating `GeoTIFF`, `PNG/JPG`, `GeoJSON`, `CSV`, and `Shapefile`.
    - `route_planner.py`: Spatial k-means + priority-weighted nearest-neighbor route planner in `EPSG:32643`.
  - `backend/ml/`:
    - `architectures.py`: PyTorch segmentation architectures (`SimpleCNNSeg`, `MicroUNet`, `MicroResUNet`).
    - `inference.py`: `GeoAIInferenceEngine` loading trained `.pt` checkpoints from `D:\SIH26012_AeroCadastre\models\EXP_001..EXP_008`.
    - `trainer.py`: PyTorch training loop with BCE+Dice hybrid loss and IoU/Dice/Precision/Recall evaluation.
  - `backend/council/agents.py`: 6-agent deliberative AI Council (`VISION_AGENT`, `GEOMETRY_AGENT`, `GIS_AGENT`, `ML_AGENT`, `ANOMALY_AGENT`, `FIELD_VERIFICATION_AGENT`) + weighted evidence fusion engine.
  - `backend/copilot/assistant.py`: Deterministic spatial database query assistant.
- **Database Files (`database/`)**:
  - `database/aerocadastre_postgis.db`: SQLite database file currently used in place of PostgreSQL + PostGIS.
  - `database/postgis_schema.sql`: Reference DDL script for PostGIS that was never wired to Alembic or an active PostgreSQL server.
- **Migrations (`alembic/`)**:
  - **Does not exist yet.** Schema creation currently relies on `Base.metadata.create_all(bind=engine)` inside `init_db()`.
- **Tests (`tests/`)**:
  - `tests/test_vertical_slice_and_adversarial.py`: 5 integration/adversarial tests running against the monolithic `backend.main:app` over SQLite.

---

## 2. What Is Genuinely Functional

1. **PyTorch GeoAI Inference & Training (`backend/ml/`)**:
   - Real trained checkpoints (`EXP_001` through `EXP_008`) exist in `D:\SIH26012_AeroCadastre\models\` and execute genuine forward passes (`MicroResUNet` 4-channel RGB+nDSM for buildings, boundaries, and land-use; `MicroUNet` 3-channel RGB for roads and secondary building comparison).
2. **Shapely + PyProj Metric GIS Calculations (`backend/gis/`)**:
   - Coordinate transformation between `EPSG:4326` (WGS84) and `EPSG:32643` (UTM Zone 43N) for metric area ($\text{m}^2$), perimeter ($\text{m}$), and Polsby-Popper compactness is mathematically real.
   - Topology validation (`OVERLAP`, `GAP`, `SELF_INTERSECTION`, `SLIVER`, `DUPLICATE`, `HOLE`, `DISCONNECTED`, `INVALID_CRS`), GIS conflict detection (`BOUNDARY_MISMATCH`, `BUILDING_CROSSING_BOUNDARY`, `ROAD_PARCEL_CONFLICT`), and multi-format export (`GeoJSON`, `Shapefile`, `CSV`, `GeoPackage`) with read-back verification are genuinely functional.
3. **Six-Agent AI Council (`backend/council/agents.py`)**:
   - Evaluates real per-parcel neural probabilities, visible edge ratios, compactness, topology flags, reference GIS IoU, and temporal changes to compute agent scores and weighted evidence fusion (`0.26*Vision + 0.22*Geometry + 0.20*GIS + 0.22*ML + 0.10*(1-AnomalyRisk)`).

---

## 3. What Is Hardcoded

1. **Default SQLite Fallback in `backend/config.py` and `backend/db.py`**:
   - `DEFAULT_SQLITE_URL` is hardcoded as the primary fallback whenever PostgreSQL is unavailable, silently masking database connection issues instead of enforcing PostgreSQL + PostGIS.
   - No `SECRET_KEY` or structured environment settings validation exists.
2. **Synthetic Overlap Injection in `backend/gis/pipeline.py` (Lines 360–364)**:
   - During scene pipeline execution, parcel `idx == 1` (`P_002`) is translated by `14%` toward `P_001` to guarantee an overlap in the demo scene, and `idx == 4` (`P_005`) receives `+0.11` model disagreement. While useful for synthetic demo seeding, general analysis runs on arbitrary parcels/projects should not hardcode index-based perturbations unless explicitly seeding synthetic demo data.
3. **Static Pixel-to-LonLat Span in `backend/gis/pipeline.py` (Line 51)**:
   - `_sample_raster_for_geom` assumes `span = 0.0024` degrees rather than deriving bounds dynamically from the scene metadata's `bounds_geojson`.
4. **Hardcoded Operator Strings**:
   - Default operator IDs (`"Surveyor_Verifier_01"`) are used in place of a real `users` table and JWT/API authentication context.

---

## 4. What Is Synthetic / Demo-Only

1. **Synthetic Drone & Cadastral Scenes (`synthetic_data/`)**:
   - `scene_urban_T0`, `scene_urban_T1`, `scene_urban_T2`, plus `train/`, `val/`, `test/` splits are procedurally generated synthetic urban blocks centered around `(77.5920, 12.9716)` in `EPSG:4326`.
2. **ULPIN Metadata (`ulpin_ready_metadata_json`)**:
   - Uses placeholder `ULPIN_READY_METADATA` dictionaries (`official_ulpin_assigned: False`) rather than connecting to an external government land registry.
3. **Field Route Planner (`backend/gis/route_planner.py`)**:
   - Uses Euclidean/metric (`EPSG:32643`) k-means + priority-weighted nearest-neighbor ordering rather than turn-by-turn street network routing.

---

## 5. What Should Be Retained

- **Trained PyTorch Models & Inference Engine** (`backend/ml/architectures.py`, `backend/ml/inference.py`, `backend/ml/trainer.py`, and `models/*.pt`).
- **Core GIS Algorithms** (`backend/gis/topology.py`, `backend/gis/conflicts_anomalies.py`, `backend/gis/changes.py`, `backend/gis/exporter.py`, `backend/gis/ingestion.py`, `backend/gis/route_planner.py`), enhanced to work seamlessly with **native PostGIS spatial SQL queries (`ST_Intersects`, `ST_Overlaps`, `ST_Touches`, `ST_Distance`, `ST_Area`, `ST_Transform`, `ST_IsValid`, `ST_MakeValid`, `ST_AsGeoJSON`, `ST_GeomFromGeoJSON`)** in addition to Shapely geometry validation.
- **Six-Agent AI Council Logic** (`backend/council/agents.py`) and **Cadastral Copilot** (`backend/copilot/assistant.py`).
- **Backward-Compatible Legacy Endpoints** (`/api/dashboard`, `/api/scenes/{scene_id}/bundle`, `/api/pipeline/run`, etc.) alongside the newly required RESTful endpoints so nothing in the existing ecosystem breaks.

---

## 6. What Should Be Replaced / Refactored

1. **Database Engine & Geometry Storage**:
   - Replace the SQLite `Text`-column workaround with a **real PostgreSQL + PostGIS database** using `GeoAlchemy2.Geometry(..., srid=4326)` columns, GIST spatial indexes, and native PostGIS spatial queries (`ST_AsGeoJSON`, `ST_GeomFromGeoJSON`, `ST_Intersects`, `ST_Overlaps`, `ST_Transform(..., 32643)`, `ST_Area`, `ST_Perimeter`, `ST_Distance`, `ST_IsValid`).
2. **Database Migration System**:
   - Replace ad-hoc `Base.metadata.create_all()` with a proper **Alembic** migration environment (`alembic/`, `alembic.ini`, versioned migration scripts) creating all 15+ core tables (`users`, `projects`, `datasets`, `parcels`, `buildings`, `roads`, `land_use`, `ai_predictions`, `model_runs`, `council_decisions`, `topology_issues`, `verification_records`, `change_events`, `field_tasks`, `audit_logs`, plus supporting tables `rasters`, `boundaries`, `anomalies`, `field_routes`, `feature_versions`, `evidence`, `human_feedback`).
3. **Modular `backend/app/` Architecture**:
   - Refactor the monolithic `backend/main.py` into the clean layered architecture:
     ```text
     backend/
         app/
             main.py
             core/          (config.py, database.py, security.py)
             models/        (SQLAlchemy + GeoAlchemy2 PostGIS models)
             schemas/       (Strict Pydantic v2 request/response/GeoJSON schemas)
             api/           (Modular routers: health, auth, projects, parcels, buildings, roads, verification, gis, analysis, council, exports, legacy)
             services/      (project_service, parcel_service, gis_service, ml_service, council_service, verification_service, export_service, seed_service)
             utils/         (geojson.py, crs.py, audit.py)
         tests/
     alembic/
     ```
4. **Complete Core REST API Coverage**:
   - Implement all missing or partially implemented endpoints required by the specification:
     - `GET /api/projects/{id}`, `PUT /api/projects/{id}`, `DELETE /api/projects/{id}`
     - `GET /api/projects/{project_id}/parcels`, `GET /api/parcels/{id}`
     - `GET /api/parcels/{parcel_id}/buildings`
     - `GET /api/projects/{project_id}/roads`
     - `GET /api/verification/queue`, `POST /api/verification`, `PUT /api/verification/{id}`
     - `GET /api/parcels/{id}/topology`, `GET /api/parcels/{id}/conflicts`
     - `POST /api/analysis/run`, `GET /api/analysis/{id}`
     - `POST /api/council/analyze`, `GET /api/council/{parcel_id}`
     - Authentication endpoints (`POST /api/auth/token`, `GET /api/auth/me`) and optional/enforced bearer token checks for protected endpoints.

---

## 7. Current API Contracts vs. Target API Contracts

| Domain | Existing Endpoint(s) in `backend/main.py` | Missing / New Target Endpoint(s) |
| :--- | :--- | :--- |
| **Health** | `GET /api/health` | Enhance with real PostgreSQL + PostGIS version & table telemetry |
| **Projects** | `GET /api/projects`, `POST /api/projects` | Add `GET /api/projects/{id}`, `PUT /api/projects/{id}`, `DELETE /api/projects/{id}` |
| **Parcels** | `GET /api/parcels`, `POST /api/parcels`, `PUT /api/parcels/{parcel_id}`, `DELETE /api/parcels/{parcel_id}`, `POST /api/parcels/{parcel_id}/split`, `POST /api/parcels/merge` | Add `GET /api/projects/{project_id}/parcels`, `GET /api/parcels/{id}` |
| **Buildings** | Embedded in `/api/scenes/{scene_id}/bundle` | Add `GET /api/parcels/{parcel_id}/buildings` (using PostGIS `ST_Intersects` / `parcel_id` linkage) |
| **Roads** | Embedded in `/api/scenes/{scene_id}/bundle` | Add `GET /api/projects/{project_id}/roads` |
| **Verification** | `POST /api/verification/{parcel_id}` | Add `GET /api/verification/queue`, `POST /api/verification`, `PUT /api/verification/{id}` |
| **GIS** | Embedded in `/api/scenes/{scene_id}/bundle` | Add `GET /api/parcels/{id}/topology`, `GET /api/parcels/{id}/conflicts` (live PostGIS + Shapely topology & conflict queries) |
| **AI Analysis** | `POST /api/pipeline/run`, `GET /api/experiments` | Add `POST /api/analysis/run`, `GET /api/analysis/{id}` (persisting and retrieving `AIPrediction` records) |
| **AI Council** | Embedded in `/api/scenes/{scene_id}/bundle` | Add `POST /api/council/analyze`, `GET /api/council/{parcel_id}` (persisting and retrieving `CouncilDecision` records) |
| **Exports** | `POST /api/exports`, `GET /api/exports/download` | Retain & support project/scene/parcel filtering |

---

## 8. Database Assumptions & Current PostgreSQL/PostGIS Status

- **Current System Status**:
  - Python packages `SQLAlchemy 2.0.54`, `GeoAlchemy2 0.20.0`, `psycopg2-binary 2.9.13`, `asyncpg 0.31.0`, `shapely 2.1.2`, `pyproj 3.8.0`, `rasterio 1.5.1`, and `fiona 1.10.1` are **installed**.
  - `alembic` and `pydantic-settings` are **not yet installed** in Python.
  - PostgreSQL + PostGIS server binaries are **not yet installed/running** on the Windows host.
- **Action Required**:
  - Install PostgreSQL + PostGIS on the local machine, initialize a PostgreSQL cluster on `D:\SIH26012_AeroCadastre\database\pgdata`, enable `CREATE EXTENSION postgis;`, and run Alembic migrations against the live PostgreSQL + PostGIS database.

---

## 9. GIS Assumptions

- **Storage CRS**: `EPSG:4326` (WGS84 geographic longitude/latitude) for GeoJSON interoperability and PostGIS `GEOMETRY(..., 4326)` storage.
- **Metric CRS**: `EPSG:32643` (WGS84 / UTM Zone 43N, India) used via PostGIS `ST_Transform(geom, 32643)` and PyProj for accurate metric area ($\text{m}^2$), perimeter ($\text{m}$), buffer distances, and overlap thresholds.
- **Geometry Validity**: All incoming GeoJSON geometries must be validated for ring closure, coordinate bounds (`[-180..180, -90..90]`), non-empty polygon/linestring structure, and OGC validity (`ST_IsValid` / `shapely.is_valid`).

---

## 10. Risks & Mitigations

1. **Risk — PostgreSQL + PostGIS Installation on Windows**:
   - *Mitigation*: Install official PostgreSQL + PostGIS binaries locally, initialize the database cluster on `D:\SIH26012_AeroCadastre\database\pgdata` (port `5432`), create database `aerocadastre`, and verify `SELECT PostGIS_Full_Version();` before running Alembic migrations.
2. **Risk — Table Naming Alignment**:
   - *Mitigation*: The specification requires core tables `users`, `projects`, `datasets`, `parcels`, `buildings`, `roads`, `land_use`, `ai_predictions`, `model_runs`, `council_decisions`, `topology_issues`, `verification_records`, `change_events`, `field_tasks`, and `audit_logs`. In the existing `models.py`, three of those (`verification_records`, `change_events`, `field_tasks`) were SQL views over `verification_tasks` and `changes`. In the new schema, we will make all 15 required tables **first-class physical PostGIS tables** managed by SQLAlchemy + Alembic (while preserving compatibility aliases if needed).
3. **Risk — Breaking Existing Entry Points**:
   - *Mitigation*: Keep `backend/main.py` re-exporting `app` from `backend.app.main:app` and preserve legacy routes alongside all new RESTful endpoints so both `uvicorn backend.app.main:app` and `uvicorn backend.main:app` work identically.
