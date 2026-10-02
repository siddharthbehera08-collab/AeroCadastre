# SIH26012 AeroCadastre — Honest Engineering Limitations & Production Roadmap

## 1. Synthetic Training & Demo Imagery vs. Real State Revenue Orthophotos

- **Current State**: The seeded scenes (`scene_urban_T1`, `scene_rural_T1`, `scene_periurban_T1`) and their multi-epoch GeoTIFFs (`0.5m/px`, `EPSG:4326`) are procedurally generated synthetic orthophotos and DSM rasters designed to simulate Indian SVAMITVA / DILRMP cadastral survey conditions (walls, hedges, roofs, road corridors, boundary shifts, and encroachments).
- **Production Requirement**: Before deployment for official state revenue departments, the PyTorch checkpoints (`models/*.pt`) must be fine-tuned on licensed Survey of India / state drone orthophotos (`2–5 cm GSD`) with RTK-GNSS ground control points (GCPs).

---

## 2. Legal Status of Candidate Boundaries

- **Current State**: All AI-extracted parcels and boundaries are explicitly tagged in PostgreSQL (`parcels.verification_status = "AI-GENERATED / REQUIRES VERIFICATION"`) and exported with the disclaimer:
  > `PRELIMINARY / CANDIDATE GEOMETRY - NOT LEGALLY AUTHORITATIVE LAND RECORDS`
- **Production Requirement**: Cadastral boundaries only acquire legal standing after licensed surveyor ground-truthing, neighbor mutation notice periods, and digital signature integration with state RoR (Record of Rights / Bhoomi / Bhulekh) portals.

---

## 3. Single-Zone Metric Projection Default (`EPSG:32643`)

- **Current State**: Metric area (`m²`), perimeter (`m`), and proximity (`ST_DWithin`) queries default to `EPSG:32643` (WGS 84 / UTM Zone 43N, covering `72°E–78°E` across Karnataka, Maharashtra, Goa, Rajasthan, Punjab, etc.), while allowing per-project `projected_crs` overrides (`EPSG:32642` through `EPSG:32646`).
- **Production Requirement**: Pan-India deployments spanning multiple states should dynamically select the UTM zone (`32642`–`32646`) or NSF-LCC projection from each parcel's centroid longitude (`floor((lon + 180) / 6) + 1`).

---

## 4. Synchronous Inference Execution on CPU

- **Current State**: `POST /api/analysis/run` executes PyTorch multi-task inference (`parcel_boundary`, `building_footprint`, `road_extraction`, `land_use`, `change_detection`) synchronously within the request lifecycle (~0.3–1.2 seconds for `256×256` tiles on CPU).
- **Production Requirement**: For gigapixel village-scale GeoTIFF orthomosaics (`10,000 × 10,000+ px`), inference should be offloaded to an asynchronous Celery / Redis GPU worker pool with sliding-window tile stitching (`512×512` tiles with 128px overlap and Hann window blending).

---

## 5. Field Route Planner Scope

- **Current State**: `backend/gis/route_planner.py` computes K-Means spatial clusters and 2-opt Travelling Salesperson (TSP) sequences across high-priority verification centroids.
- **Production Requirement**: Integrate turn-by-turn road-network shortest paths (`pgRouting` `pgr_dijkstra` over `roads` table) to account for physical barriers (canals, railway lines, gated compounds).
