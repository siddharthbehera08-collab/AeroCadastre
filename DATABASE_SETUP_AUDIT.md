# PostgreSQL + PostGIS Setup & Database Audit

**Project**: SIH26012 AeroCadastre GeoAI Cadastral Intelligence Platform  
**Target Root**: `D:\SIH26012_AeroCadastre`  
**Database Cluster**: `D:\PostgreSQL\data`  
**PostgreSQL Binaries**: `D:\PostgreSQL\16`  
**Audit Timestamp**: `2026-10-02`  

---

## 1. Executive Summary

| Component | Target Spec | Actual Configured / Detected | Status |
|---|---|---|---|
| **Database Engine** | PostgreSQL 16 x86_64 | PostgreSQL 16.4 (MSVC build 1940 64-bit) | `WORKING` |
| **Spatial Extension** | PostGIS 3.6+ | PostGIS 3.6.2 (GEOS 3.14.1dev, PROJ 8.2.1, WAGYU 0.5.0) | `WORKING` |
| **Topology Extension**| PostGIS Topology | PostGIS Topology 3.6.2 enabled | `WORKING` |
| **Database Name** | `aerocadastre` | `aerocadastre` (owner: `aerocadastre`) | `WORKING` |
| **Local Dev User** | `aerocadastre` / `postgres` | `aerocadastre` / `postgres` with trust/password auth on 127.0.0.1 | `WORKING` |
| **Port & Host** | `127.0.0.1:5432` | `127.0.0.1:5432` (localhost only) | `WORKING` |
| **ORM & Driver** | SQLAlchemy 2.0 + psycopg2 | SQLAlchemy 2.0.54 + psycopg2 2.9.9 + GeoAlchemy2 0.20.0 | `WORKING` |
| **Migrations** | Alembic 1.13+ | Alembic `0001_initial_postgis` (head) | `WORKING` |
| **FastAPI Backend** | FastAPI 0.110+ Uvicorn | Connected to PostgreSQL + PostGIS (`/api/health` 200 OK) | `WORKING` |

---

## 2. Directory & Path Audit

- **PostgreSQL Binaries Directory**: `D:\PostgreSQL\16`
  - `postgres.exe` (v16.4)
  - `initdb.exe` (v16.4)
  - `pg_ctl.exe` (v16.4)
  - Core spatial runtime libraries: `libgeos_c.dll`, `libproj_8_2.dll`, `libprotobuf-c-1.dll`, `libxml2-2.dll`, `libgsl-28.dll`
- **PostgreSQL Data Cluster**: `D:\PostgreSQL\data`
  - Fully initialized with `initdb -U postgres -A trust -E UTF8 --locale=C`
  - Configured in `postgresql.conf`: `listen_addresses = '127.0.0.1'`, `port = 5432`, `shared_buffers = 128MB`
  - Configured in `pg_hba.conf`: localhost trust authentication for local development.
- **Archive Source Files**:
  - `D:\SIH26012_AeroCadastre\database\downloads\postgres-windows-x86_64.txz` (Extracted clean to `D:\PostgreSQL\16`)
  - `D:\SIH26012_AeroCadastre\database\downloads\postgis_pg16.zip` (PostGIS 3.6.2 extensions and libraries extracted and linked)

---

## 3. Schema & Table Audit

The database schema initializes **24 total tables** in the `public` schema with native PostGIS `Geometry(GEOMETRY, 4326)` columns and GiST spatial indexes:

1. `users` (surveyor and admin credentials & roles)
2. `projects` (cadastral survey projects with boundary geometries)
3. `datasets` (spatial datasets, drone orthos, DSM, reference GIS layers)
4. `parcels` (cadastral parcel candidates and reference records)
5. `buildings` (AI-extracted building footprints)
6. `roads` (AI-extracted road corridors and centerlines)
7. `land_use` (multi-class land-use segmentation polygons)
8. `model_runs` (training and inference run records)
9. `ai_predictions` (persisted GeoAI inference runs)
10. `council_decisions` (6-agent AI council multi-evidence deliberation records)
11. `topology_issues` (spatial overlap, gap, sliver, and intersection issues)
12. `verification_records` (surveyor verification queue and sign-off records)
13. `change_events` (multi-temporal changes between T0, T1, and T2)
14. `field_tasks` (field verification tasks and stops)
15. `audit_logs` (immutable system and surveyor audit trail)
16. `rasters` (drone raster assets and bounds)
17. `boundaries` (cadastral boundary lines)
18. `anomalies` (spatial conflicts and land-use anomalies)
19. `field_routes` (field verification routing traversal lines)
20. `feature_versions` (parcel time machine version history)
21. `evidence` (multi-source evidence items)
22. `human_feedback` (human surveyor geometry corrections)
23. `alembic_version` (migration revision tracking)
24. `spatial_ref_sys` (standard EPSG spatial reference database)

---

## 4. Operational Scripts Created

- [manage_postgres.py](file:///d:/SIH26012_AeroCadastre/database/manage_postgres.py): Start, stop, restart, and status CLI utility for the PostgreSQL engine.
- [test_postgis_schema.py](file:///d:/SIH26012_AeroCadastre/database/test_postgis_schema.py): Direct SQL schema and PostGIS spatial function verification script.
- [init_db_roles.py](file:///d:/SIH26012_AeroCadastre/database/init_db_roles.py): PostgreSQL roles and database initialization helper.

---

## 5. Security & Configuration Audit

- **Environment File**: `.env` and `.env.example` configured with `DATABASE_URL=postgresql+psycopg2://postgres@127.0.0.1:5432/aerocadastre`.
- **Git Ignore**: `.gitignore` updated to ignore `database/pgsql/`, `database/pgdata/`, and all `.txz`/`.bin`/`.zip` archives.
- **Host Binding**: PostgreSQL is strictly bound to `127.0.0.1` and is NOT exposed externally.
