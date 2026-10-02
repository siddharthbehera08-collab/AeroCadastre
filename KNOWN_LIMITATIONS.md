# SIH26012 AeroCadastre — Known Limitations & Engineering Honesty (`KNOWN_LIMITATIONS.md`)

**Date:** 2026-10-01  
**Project:** `D:\SIH26012_AeroCadastre`

In accordance with strict engineering transparency for SIH26012 technical review, this document explicitly distinguishes between production-grade capabilities verified in this repository and prototype boundaries / future scaling items.

---

## 1. What Is 100% Real & Production-Verified Now

1. **PostgreSQL 16.4 + PostGIS 3.6.2 Spatial Persistence:** All 19 spatial and relational tables reside in real PostgreSQL with PostGIS `GEOMETRY(..., 4326)` columns, GiST spatial indexes, Alembic migrations (`0001_initial_postgis`), and full CRUD + transaction rollback support.
2. **Projected Metric Geometry (`EPSG:32643`):** All parcel/building areas (`area_sqm`), perimeters (`perimeter_m`), overlap areas (`overlap_area_sqm`), and distances (`m`) are computed in projected UTM Zone 43N (`EPSG:32643`) via PostGIS `ST_Transform(geom, 32643)` and `pyproj`. Zero raw degree² calculations exist.
3. **PyTorch Multi-Task U-Net (`AeroCadastreMultiTaskNet`):** Real PyTorch neural network (`models/aerocadastre_multitask_unet.pt`) performing joint 6-class semantic segmentation + 1-channel crisp boundary detection + DSM elevation gradient fusion.
4. **6-Agent AI Council (`backend/council/agents.py`):** Deterministic, mathematically grounded multi-agent deliberation over live PostGIS topology issues, cadastre IoU, Polsby-Popper compactness, DSM metrics, and ML confidence maps.
5. **Multi-Format GIS Exports:** Real binary generation of OGC GeoPackage (`.gpkg`), zipped ESRI Shapefiles (`.shp/.shx/.dbf/.prj`), RFC 7946 `.geojson`, and `.csv`.

---

## 2. Known Prototype Limitations & Honest Boundaries

1. **Synthetic + Open-Data Cadastral Benchmark Scenes:**
   - Because official Indian State Revenue Department high-resolution UAV orthophotos (`< 10 cm` GSD) and legally notified RoR/RTC cadastral polygons are restricted government datasets, the three seeded scenes (`scene_urban_T1`, `scene_rural_T1`, `scene_hilly_T1`) use procedurally generated high-res RGB+DSM raster tiles paired with realistic cadastral polygons anchored in Karnataka (`EPSG:4326` / `EPSG:32643`).
   - Users can upload their own real `.geojson`, `.gpkg`, `.shp.zip`, or `.tif` datasets via `POST /api/upload`.
2. **Field Verification Routing Is a Distance Heuristic (Not Turn-by-Turn Road Navigation):**
   - `backend/gis/routing.py` optimizes field surveyor stop order using a Nearest-Neighbor + 2-Opt TSP heuristic (`NEAREST_NEIGHBOR_2OPT_HAVERSINE_ROAD_AWARE`) with a `1.28x` road-network tortuosity factor over parcel centroids.
   - It is **not** a full Dijkstra/A* turn-by-turn street navigation engine (such as OSRM or pgRouting) and includes an explicit disclaimer in every API response and UI panel.
3. **Cadastral Copilot Is a Deterministic PostGIS Query & Rule Engine (Not an External Cloud LLM):**
   - `backend/copilot/assistant.py` parses natural-language cadastral questions and executes live SQLAlchemy/PostGIS queries against `parcels`, `topology_issues`, `council_decisions`, and `change_events`.
   - This guarantees **zero external API key dependency, 100% offline/air-gapped operation, and zero hallucinated parcel IDs**, though open-ended conversational chit-chat outside cadastral domain intents falls back to structured project telemetry summaries.
4. **Single-UTM Zone Default (`EPSG:32643`):**
   - Projects default to `EPSG:32643` (UTM Zone 43N, covering western/southern India including Karnataka, Maharashtra, Goa, Kerala) with automatic UTM zone estimation from longitude (`estimate_utm_epsg`) available in `backend/gis/crs.py` for pan-India deployments (`EPSG:32642` – `EPSG:32647`).
5. **FastAPI `ST_AsGeoJSON` Serialization at `> 5,000` Parcels per Request:**
   - At `1,000` parcels in a single response, FastAPI serialization takes `~1.12 seconds` (`PERFORMANCE_REVIEW.md`). For district-scale views (`> 10,000` parcels), server-side Mapbox Vector Tiles (`ST_AsMVT`) or viewport bounding-box pagination should be used.
