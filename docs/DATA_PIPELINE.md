# SIH26012 — AeroCadastre: Data & Ingestion Pipeline (`DATA_PIPELINE.md`)

## 1. Synthetic Geospatial Scene Generator (`synthetic_data/generator.py`)

Generates 143 deterministic scenes (`100 train`, `20 val`, `20 test`, `3 temporal_demo` across `T0`, `T1`, `T2`) with:
- **Drone RGB Ortho Imagery (`rgb.png`, `rgb.tif`):** `128×128` at `0.5m` resolution with roof textures, shadows, vegetation canopy occlusion, and sensor grain.
- **Digital Surface & Terrain Models (`dsm.npy`, `dsm.tif`):** Ground terrain (`212m–218m`) plus elevated building roofs (`+4.5m to +11.5m`) and tree canopy (`+3.5m`).
- **Segmentation Masks:** `building_mask.png`, `road_mask.png`, `landuse_mask.png` (10 classes), `boundary_mask.png`.
- **Vector Cadastral Layers (`EPSG:4326`):** `parcels.geojson`, `reference_parcels.geojson`, `buildings.geojson`, `roads.geojson`, `boundaries.geojson`.

## 2. Modular Ingestion & Validation Layer (`backend/gis/ingestion.py`)

Validates uploaded datasets (`GeoTIFF`, `PNG/JPEG`, `GeoJSON`, `Shapefile`, `GeoPackage`, `CSV`, `DSM/DTM`) for:
- File existence & non-zero payload
- Coordinate Reference System (`EPSG:4326`, `EPSG:32643`)
- Raster dimensions, band count, and nodata values
- Vector polygon validity (`Shapely` ring closure & self-intersection checks).
