# SIH26012 — AeroCadastre: Project & Environment Audit

**Problem Statement:** SIH26012 — *AI-Based Automated Urban Parcel Mapping and Cadastral Feature Extraction System using Drone Imagery*  
**Organization:** Ministry of Rural Development, Department of Land Resources (DoLR)  
**Audit Timestamp:** 2026-09-29T00:17:00+05:30  
**Project Root:** `D:\SIH26012_AeroCadastre\`

---

## 1. Storage & Hardware Inspection

| Resource | Status / Capacity | Policy Action |
| :--- | :--- | :--- |
| **C: Drive** | 15.01 GB Free (161.85 GB Used) | **CRITICAL LOW SPACE.** Strictly avoid storing datasets, models, caches, venvs, or node_modules on `C:`. |
| **D: Drive** | **179.51 GB Free** (118.34 GB Used) | Primary storage for all code, synthetic data, ML checkpoints, spatial databases, exports, and package caches (`D:\SIH26012_AeroCadastre\.cache\`). |
| **CPU / Python** | Python 3.12.10 (64-bit) | Native execution for FastAPI, PyTorch, Shapely, PyProj, Rasterio, Scikit-Learn. |
| **PyTorch / Compute** | `torch 2.14.0+cpu` (`cuda: False`) | CPU-only training & inference. Models must be compact, well-regularized architectures (CNN Baseline, Micro-UNet, Micro-ResUNet, Random Forest) operating on 128×128 / 256×256 synthetic scenes so real training completes in seconds/minutes with genuine metrics. |
| **Node.js / Frontend** | Node `v24.13.0`, npm `11.6.2` | NPM cache redirected to `D:\SIH26012_AeroCadastre\.cache\npm`. Next.js + React + TypeScript + Tailwind CSS frontend in `D:\SIH26012_AeroCadastre\frontend\`. |
| **Spatial Database** | `psycopg2`, `asyncpg`, `SQLAlchemy`, `GeoAlchemy2` installed; no local Postgres daemon running on port 5432; Docker not installed | Dual-mode PostGIS Architecture: Full PostgreSQL + PostGIS DDL (`database/postgis_schema.sql`) and `DATABASE_URL` support for live PostGIS servers, plus an embedded PostGIS-compatible spatial engine (`D:\SIH26012_AeroCadastre\database\aerocadastre_postgis.db`) registering real `ST_*` SQL functions (`ST_AsGeoJSON`, `ST_GeomFromGeoJSON`, `ST_Area`, `ST_Perimeter`, `ST_IsValid`, `ST_Intersects`, `ST_Overlaps`, `ST_MakeValid`, `ST_Transform`, etc.) via Shapely/PyProj and R-Tree spatial indexing so all 20 tables and spatial SQL queries execute natively out-of-the-box. |

---

## 2. Existing Codebase Audit

- `C:\Users\LENOVO\.gemini\antigravity\scratch`: Empty prior to session.
- `D:\SIH26012_AeroCadastre\`: Freshly initialized as the dedicated project root on `D:`.

---

## 3. Core Architectural Principles Enforced

1. **Human-in-the-Loop Cadastral Philosophy:**
   - AI never claims legal authority or official ownership determination.
   - All AI outputs are labeled `AI-GENERATED / REQUIRES VERIFICATION` or `INFERRED CANDIDATE GEOMETRY`.
   - Boundaries are explicitly categorized into: `VISIBLE`, `INFERRED`, `REFERENCE`, and `HUMAN_VERIFIED`.
   - ULPIN compatibility is strictly represented as `ULPIN_READY_METADATA` (never fabricating official government ULPINs).

2. **Dataset Policy:**
   - Zero large external dataset downloads during this build.
   - All training, validation, testing, temporal change (`T0`, `T1`, `T2`), and elevation (`DSM`/`DTM`) layers are generated deterministically via `synthetic_data/` and explicitly labeled `SYNTHETIC DEMO DATA`.
   - Modular ingestion adapters (`GeoTIFF`, `PNG/JPEG`, `GeoJSON`, `Shapefile`, `GeoPackage`, `CSV`, `DSM/DTM`) ensure real Indian drone/cadastral datasets (Survey of India, Bhuvan, NAKSHA, SpaceNet, Inria) can be plugged in without architectural changes.

3. **20 Core Features & End-to-End Vertical Slice:**
   - 01. Parcel Boundary Detection (`VISIBLE`, `INFERRED`, `REFERENCE`, `HUMAN_VERIFIED`)
   - 02. Building Detection (Polygon extraction, confidence, area, centroid, model provenance)
   - 03. Road / Pathway / Access Corridor Detection (Vector centerlines & corridors)
   - 04. Land-Use Classification (Configurable multi-class prediction)
   - 05. Multi-Source Geospatial Data Fusion (Imagery + DSM/DTM + Buildings + Roads + Reference GIS + Boundary Evidence)
   - 06. Parcel Polygon Generation (Polygonization, snapping, sliver cleanup, hole validation, provenance)
   - 07. Automated Topology Validation (Self-intersections, invalid rings, duplicates, overlaps, gaps, slivers, holes)
   - 08. Overlap & Gap Detection (Pairwise intersection & unexpected interstitial void detection)
   - 09. GIS Conflict Detection (Candidate vs. Reference GIS comparison: shift, area discrepancy, building/road encroachment)
   - 10. Transparent AI Confidence Scoring (Weighted, explainable breakdown of vision, geometry, GIS consistency, topology, anomaly)
   - 11. Temporal Change Detection (`T0` vs `T1` vs `T2`: new/removed buildings, boundary shift, land-use transition)
   - 12. Anomaly Detection (Deterministic geometric/contextual rules + ML uncertainty anomalies)
   - 13. AI-Assisted Field Verification Priority (`HIGH`, `MEDIUM`, `LOW` with transparent scoring & reasons)
   - 14. Interactive Web-GIS Editor (Select, vertex move/add/delete, split parcel, merge parcels, create/delete, attribute edit, accept/reject/verify, persistent to DB)
   - 15. Validated GIS Export (`GeoJSON`, `Shapefile`, `CSV`, `GeoPackage` with post-export read-back verification)
   - 16. Human-in-the-Loop Learning Store (Records before/after geometry & class deltas as structured retraining samples)
   - 17. Full Evidence & Provenance Tracking (Lineage for every feature and boundary)
   - 18. Smart Field Route Planner (Spatial clustering + 2-opt TSP route sequence with metric distance estimation)
   - 19. Parcel Time Machine (Historical version comparison across `T0`, `T1`, `T2` and human edit versions)
   - 20. Cadastral AI Copilot (Deterministic tool-backed NL query engine connected directly to spatial database state)
   - **Multi-Agent AI Council:** Vision Agent, Geometry Agent, GIS Agent, ML Agent, Anomaly Agent, Field Verification Agent + Council Fusion Engine.
