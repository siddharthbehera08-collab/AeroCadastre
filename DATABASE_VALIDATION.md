# SIH26012 AeroCadastre — PostgreSQL + PostGIS Database Validation (`DATABASE_VALIDATION.md`)

**Date:** 2026-10-01  
**Database Engine:** `PostgreSQL 16.4, compiled by Visual C++ build 1940, 64-bit`  
**Spatial Extension:** `PostGIS 3.6.2 (3.6.2 5111791)` with `GEOS 3.14.0-CAPI-1.20.4`, `PROJ 9.7.0`, `GDAL 3.11.3`  
**Connection URI:** `postgresql+psycopg2://postgres:***@127.0.0.1:5432/aerocadastre`  
**Migration Revision:** Alembic `0001_initial_postgis` (`alembic_version`)

---

## 1. Schema & Spatial Table Inventory

All **19** core relational and spatial tables are deployed in PostgreSQL (`public` schema) with GiST spatial indexes (`USING gist (geom)`), foreign key constraints (`ON DELETE CASCADE`), and `EPSG:4326` geometry storage:

| Table Name | Spatial Column (`geometry_columns`) | SRID | Primary Key | Key Foreign Keys & Constraints | Seeded / Active Rows |
|---|---|---|---|---|---|
| `users` | — | — | `id` (`VARCHAR(64)`) | `username UNIQUE`, `role` (`ADMIN`, `SURVEYOR`, `VIEWER`) | `3` |
| `projects` | `aoi_geom` (`POLYGON`) | `4326` | `id` (`VARCHAR(64)`) | `crs_epsg`, `metric_epsg` (`32643`) | `1+` |
| `datasets` | `bounds_geom` (`POLYGON`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `3+` |
| `parcels` | `geom` (`POLYGON`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `36` (`18` cand + `18` ref) |
| `buildings` | `geom` (`POLYGON`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id`, `parcel_id` | `20` |
| `roads` | `geom` (`LINESTRING`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `6` |
| `land_use` | `geom` (`POLYGON`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `18` |
| `boundaries` | `geom` (`LINESTRING`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `18` |
| `topology_issues` | `geom` (`GEOMETRY`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `10+` |
| `anomalies` | `geom` (`GEOMETRY`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `8` |
| `council_decisions` | — | — | `id` (`SERIAL`) | `project_id -> projects.id (CASCADE)`, `parcel_id` | `18+` |
| `verification_records` | — | — | `id` (`VARCHAR(64)`) | `project_id -> projects.id`, `parcel_id -> parcels.id` | `10+` |
| `change_events` | `geom` (`GEOMETRY`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `5` |
| `field_tasks` | `waypoint_geom` (`POINT`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `8` |
| `field_routes` | `geom` (`LINESTRING`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id (CASCADE)` | `3` |
| `ai_predictions` | `geom` (`GEOMETRY`) | `4326` | `id` (`VARCHAR(64)`) | `project_id -> projects.id`, `model_run_id -> model_runs.id` | `4+` |
| `model_runs` | — | — | `id` (`VARCHAR(64)`) | `model_name`, `iou`, `dice_f1`, `boundary_f1`, `parcel_PQ` | `3+` |
| `feature_versions` | `geom` (`GEOMETRY`) | `4326` | `id` (`SERIAL`) | `project_id -> projects.id`, `feature_id`, `version_number` | `42+` |
| `human_feedback` | — | — | `id` (`SERIAL`) | `project_id -> projects.id`, `feature_id`, `action_type` | `4+` |
| `audit_logs` | — | — | `id` (`SERIAL`) | `project_id`, `actor`, `operation`, `target_id` | `20+` |

---

## 2. CRUD & Transaction Rollback Verification

1. **Direct SQL & ORM Parity:** Every `CREATE`, `READ`, `UPDATE`, and `DELETE` operation through FastAPI was verified via direct SQL queries against `aerocadastre`.
2. **Transaction Atomicity (`test_22_transaction_rollback_geojson_types_and_live_training`):**
   - Simulated a mid-transaction failure after inserting a `Parcel` and before committing its `AuditLog`.
   - Verified `db.rollback()` cleanly aborted the unit of work, leaving `0` orphaned rows in `parcels` or `audit_logs`.
3. **Foreign Key & Duplicate Constraint Enforcement:**
   - Inserting duplicate `Project.id` or `Parcel.id` returns `409 Conflict`.
   - Deleting a temporary test `Project` cascades cleanly to dependent `Parcel`, `Road`, `TopologyIssue`, and `CouncilDecision` records.
