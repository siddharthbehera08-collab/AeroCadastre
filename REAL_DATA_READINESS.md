# Real Data Readiness Audit & Ingestion Spec

**Project**: SIH26012 AeroCadastre  
**Audit Date**: `2026-10-02`  
**Target Next Dataset**: Inria Aerial Image Labeling Dataset (Urban Imagery & Building Footprints)  
**Status**: `READY FOR INGESTION` (Parsers & PostGIS Schemas Active)  

---

## 1. Supported Ingestion Formats

The backend ingestion layer ([backend/gis/ingestion.py](file:///d:/SIH26012_AeroCadastre/backend/gis/ingestion.py)) supports inspection and ingestion of the following formats:

| Format | File Extensions | Parsing Library | Extracted Properties | Validation Status |
|---|---|---|---|---|
| **GeoTIFF** | `.tif`, `.tiff` | `rasterio` | CRS, spatial bounds, width, height, bands, nodata value | `WORKING` |
| **PNG / JPEG** | `.png`, `.jpg`, `.jpeg` | `Pillow (PIL)` | Width, height, bands (RGB/RGBA), pixel channels | `WORKING` |
| **GeoJSON** | `.geojson`, `.json` | `json` + `shapely` | Feature count, geometry validity (`ST_IsValid`), properties, CRS | `WORKING` |
| **Shapefile** | `.shp` (or `.zip`) | `pyshp (shapefile)` | Feature geometries, bounding box, field attributes | `WORKING` |
| **GeoPackage** | `.gpkg` | `sqlite3` + `shapely` | Layer names, feature count, SRS identifiers | `WORKING` |
| **CSV** | `.csv` | `csv` | Lat/Lon columns, WKT geometry strings, ULPIN/attribute tables | `WORKING` |
| **DEM / DSM / DTM** | `.npy`, `.tif` | `numpy` / `rasterio` | Elevation grids, mean elevation, nodata masks | `WORKING` |

---

## 2. Inria Aerial Dataset Integration Strategy

When the Inria Aerial Image Labeling Dataset is downloaded:

1. **Orthophoto Ingestion**: Ingest uncompressed TIFF tiles (5000x5000 pixels at 0.3m GSD) into `datasets` and `rasters` tables with spatial bounding boxes.
2. **Ground Truth Extraction**: Convert Inria ground truth building masks to vector polygons via raster-to-polygon vectorization and persist in `buildings` and `parcels` tables.
3. **Metric Projection**: Transform native coordinate systems to local UTM Zone (e.g. EPSG:32643) for millimeter-accurate area and boundary perimeter calculations.
4. **Model Retraining & Validation**: Feed real tiles to the U-Net / SegNet / ResNet feature extractors in `backend/ml/trainer.py` to evaluate real-world precision, recall, and IoU against ground truth.

---

## 3. Ground Truth & Ethics Compliance

- Current active datasets are clearly tagged as `SYNTHETIC DEMO DATA` with legal disclaimers.
- Real Inria data is slated for Phase 2 real-data evaluation and has not been fabricated or simulated.
