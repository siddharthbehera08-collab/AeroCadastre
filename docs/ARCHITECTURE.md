# SIH26012 — AeroCadastre: System Architecture

## 1. High-Level Architecture

AeroCadastre is structured into five tightly integrated subsystems residing on `D:\SIH26012_AeroCadastre\`:

1. **Geospatial Ingestion & Synthetic Scene Engine (`synthetic_data/`, `backend/gis/ingestion.py`):**
   - Deterministically generates multi-layer cadastral scenes (`RGB`, `DSM`, `DTM`, `building_mask`, `road_mask`, `landuse_mask`, `boundary_mask`, `parcels.geojson`, `reference_parcels.geojson`) in `EPSG:4326` and metric `EPSG:32643` (UTM Zone 43N India).
   - Provides format/CRS/geometry validation adapters for `GeoTIFF`, `PNG/JPEG`, `GeoJSON`, `Shapefile`, `GeoPackage`, and `CSV`.
2. **GeoAI Deep Learning & Classical ML Engine (`backend/ml/`):**
   - Implements `SimpleCNNSeg`, `MicroUNet`, `MicroResUNet` (4-channel RGB + normalized DSM height fusion), `BCEDiceLoss`, and `RandomForestClassifier`.
   - Computes per-feature neural confidence and inter-model disagreement (`|P_ResUNet_RGBD - P_UNet_RGB|`).
3. **GIS Cadastral Inference, Topology, Conflict, Anomaly & Change Engine (`backend/gis/`):**
   - Distinguishes `VISIBLE`, `INFERRED`, `REFERENCE`, and `HUMAN_VERIFIED` parcel boundaries.
   - Performs Shapely/PostGIS topology validation (`SELF_INTERSECTION`, `OVERLAP`, `GAP`, `SLIVER`, `DUPLICATE`, `HOLE`, `DISCONNECTED`, `INVALID_CRS`).
   - Detects GIS conflicts against legacy reference parcels and road corridors, building boundary encroachments, and temporal changes across `T0 (2024)`, `T1 (2025)`, and `T2 (2026)`.
4. **6-Agent AI Council & Field Verification Engine (`backend/council/`):**
   - `VISION_AGENT`, `GEOMETRY_AGENT`, `GIS_AGENT`, `ML_AGENT`, `ANOMALY_AGENT`, `FIELD_VERIFICATION_AGENT`, and `COUNCIL_FUSION_ENGINE`.
5. **PostGIS / Spatial SQL Database + FastAPI Backend + Next.js Web-GIS (`database/`, `backend/`, `frontend/`):**
   - 20 spatial tables with `ST_*` spatial SQL functions and interactive Web-GIS vertex editing, parcel splitting/merging, Time Machine versioning, Smart Field Routing, Cadastral AI Copilot, and validated GIS exports.
