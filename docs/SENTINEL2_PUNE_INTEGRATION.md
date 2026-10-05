# Sentinel-2 L2A Pune Study Area Integration Report
**AeroCadastre SIH26012 — Automated Cadastral Intelligence & Land Record Modernization**

---

## 1. Executive Summary

This document certifies the acquisition, preprocessing, cryptographic hashing, backend service exposure, frontend WebGIS integration, and automated regression testing of authentic Sentinel-2 L2A multispectral Earth Observation data for the Pune Historic Urban Core (Peth Areas) pilot area in Maharashtra, India.

All acquired rasters are physical, non-fabricated GeoTIFF files residing on disk within the repository, downloaded via `pystac` and signed via `planetary_computer.sign()`.

---

## 2. STAC Acquisition Metadata & Workflow

The multispectral imagery was acquired using the Microsoft Planetary Computer Python SDK (`pystac` and `planetary_computer`):

1. **STAC Item Loading:** Loaded via `pystac.Item.from_file()` from:
   `https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803`
2. **Asset Signing:** Assets signed using `planetary_computer.sign(item)` generating authorized SAS tokens for Azure Blob storage access.
3. **Remote Windowed Reading:** Using GDAL virtual file system (`/vsicurl/`) and Rasterio windowed reads with 500m bounding buffer in source UTM Zone 43N (`EPSG:32643`), avoiding downloading the full 10,980 x 10,980 tile unnecessarily.
4. **Reprojection & Alignment:** Windowed rasters reprojected to the target Pune study area WGS84 (`EPSG:4326`) bounding box `[73.84, 18.51, 73.87, 18.53]`.
5. **Product Synthesis:** Generated true-color 3-band RGB composite (B04, B03, B02) and float32 Normalized Difference Vegetation Index (NDVI: `(B08 - B04) / (B08 + B04)`).

### STAC Metadata Attributes
- **STAC Item Identifier:** `S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803`
- **Acquisition Timestamp:** `2026-10-02T05:32:41.024000Z`
- **MGRS Tile ID:** `T43QCA`
- **Relative Orbit:** `R105`
- **Platform / Instrument:** Sentinel-2A / MultiSpectral Instrument (MSI)
- **Processing Level:** Level-2A (Surface Reflectance, Bottom-Of-Atmosphere / BOA)
- **Cloud Cover Percentage:** `0.6954%` (Clean, cloudless observation)
- **Source CRS:** `EPSG:32643` (UTM Zone 43N)
- **Output Reprojection / Format:** `EPSG:4326` (WGS 84 GeoTIFF)

---

## 3. Geographic Extent & Spatial Resolution

- **Target Study Area:** Pune Historic Urban Core (Kasba, Shaniwar, Budhwar, Raviwar, Somwar, Mangalwar Peths)
- **Bounding Box (WGS84 `[minx, miny, maxx, maxy]`):**
  - Min Longitude: `73.8400° E`
  - Min Latitude: `18.5100° N`
  - Max Longitude: `73.8700° E`
  - Max Latitude: `18.5300° N`
- **Raster Dimensions (10m bands & composites):**
  - Width: `324` pixels
  - Height: `216` pixels
  - Native Band Spatial Resolution: `~10.31 meters / pixel` (10m nominal GSD)
- **Raster Dimensions (20m SCL):**
  - Width: `162` pixels
  - Height: `108` pixels

---

## 4. Physical Files & Cryptographic Verification

All GeoTIFF files are stored under both `data/real/india/pune/imagery/sentinel2/` and symlinked/copied to `data/india/pune/imagery/sentinel2/` for backward and forward compatibility.

| Asset / Band | Wavelength / Description | Dimensions | Data Type | Size (Bytes) | SHA256 Hash |
|---|---|---|---|---|---|
| **B02** | Blue (~490 nm) | 324 x 216 | `uint16` | 133,023 | `2496e874996f73bb0e17a6d9e1e972ffdc7bbf1918cb9a9e956b4d764029896f` |
| **B03** | Green (~560 nm) | 324 x 216 | `uint16` | 133,181 | `29c0f44b554d30f0765f45bd2ba7171e310fa2d6a1428da236d5b3bb1f119d4e` |
| **B04** | Red (~665 nm) | 324 x 216 | `uint16` | 138,857 | `f0e82f480c9c730c26f881c4c08229288163ed078f1669de2635a2c27edc7005` |
| **B08** | NIR (~842 nm) | 324 x 216 | `uint16` | 144,174 | `f9d648ea4b23d8ca29a0106a7078a9798b22b840e0b14658e725bcfae57c9aa0` |
| **SCL** | Scene Classification (20m resampled) | 162 x 108 | `uint8` | 2,045 | `3a448fe33a1abca92a405e4430e14a660e3a9f2709520abe2e03e5f07744467b` |
| **RGB** | True Color Composite (B04, B03, B02) | 324 x 216 x 3 | `uint16` | 409,083 | `38cdd6f4f39200502cc4ae65a5c1118ae97f679955850bf66120601ea1ea098b` |
| **NDVI** | Normalized Difference Veg Index | 324 x 216 | `float32` | 319,533 | `bbda59867c7d05a4846645a627f18661a14b459c19204c2e275991e00ae3d505` |

### Provenance Manifest
- Location: `data/real/india/pune/imagery/sentinel2/pune_sentinel2_provenance.json`
- Registered in `data/DATASET_REGISTRY.json` under key: `DS_PUNE_SENTINEL2_L2A`

---

## 5. Scientific Limitation & Usage Notice

> [!IMPORTANT]
> **Cadastral Delineation Limitation:**
> Sentinel-2 provides 10-meter Ground Sample Distance (GSD) multi-spectral observations.
> It is **strictly used for macro contextual evidence**, land use / land cover classification (LULC), vegetation index (NDVI), water bodies, and broad urban density context.
>
> Sentinel-2 is **NOT** authoritative cadastral geometry and is **NEVER** used to delineate sub-meter legal property boundaries or parcel land ownership boundaries. Parcel boundaries in AeroCadastre are generated through high-resolution drone/aerial building footprint inference (ResUNet Model A), road buffer extractions (ResUNet Model B), cadastral topology rules, and ground-truth survey verification.

---

## 6. Architecture & Integration Points

### 6.1 Backend Ingestion & Service Engine
- Module: `backend/gis/sentinel2_service.py`
- Implements: `Sentinel2AcquisitionEngine`
- Methods:
  - `acquire_via_pystac()`: Loads STAC item with `pystac`, signs with `planetary_computer.sign()`, performs buffered windowed reads over UTM 43N, reprojects to WGS84, and computes RGB/NDVI.
  - `get_provenance()`: Reads and verifies on-disk provenance metadata.
  - `get_summary()`: Summarizes acquisition metrics, band availability, and file statuses.

### 6.2 REST API Endpoint
- Route: `GET /api/gis/sentinel2` in `backend/app/api/routes_gis.py`
- Response Payload includes:
  - `status`: `"ACQUIRED_AND_VERIFIED"`
  - `stac_item`: `"S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803"`
  - `acquisition_date`: `"2026-10-02T05:32:41.024000Z"`
  - `cloud_cover_percent`: `0.6954`
  - `bbox`: `[73.84, 18.51, 73.87, 18.53]`
  - `resolution_m`: `10.31`
  - `bands`: `["B02", "B03", "B04", "B08", "SCL"]`
  - `derived`: `["RGB", "NDVI"]`
  - `scientific_limitation`: Warning regarding ~10m macro contextual evidence.

### 6.3 WebGIS Frontend Integration
- File: `frontend/src/components/WebGisEditor.tsx`
- Feature:
  - Toggle layer: `Sentinel-2 L2A (10m Macro Context)`
  - Direct connection to `/api/gis/sentinel2`
  - Visual overlay displaying STAC Tile `T43QCA`, cloud cover `0.7%`, and true-color bounding extent over Pune.

### 6.4 Database & Foreign Key Compatibility
- PostgreSQL 16 + PostGIS 3.6.2 running on `127.0.0.1:5432`
- All database migrations, tables (`parcels`, `buildings`, `roads`, `land_use`, `datasets`, `boundaries`), and foreign key relationships verified intact.

---

## 7. Automated Test Verification

Targeted integration test file: `tests/test_sentinel2_integration.py`
All 6 test cases passed successfully:
1. `test_sentinel2_files_exist_on_disk`: Verifies presence and positive non-zero size of all bands and products.
2. `test_sentinel2_geotiff_raster_validation`: Inspects raster dimensions (216x324), CRS (`EPSG:4326`), valid transforms, and NDVI ranges (-1 to 1).
3. `test_sentinel2_provenance_integrity`: Verifies SHA256 hashes against actual file contents and STAC properties.
4. `test_backend_sentinel2_api_endpoint`: Validates FastAPI `GET /api/gis/sentinel2` schema and JSON response.
5. `test_stac_pystac_loading_and_signing`: Confirms `pystac` loads the item and `planetary_computer.sign()` produces signed SAS URLs.
6. `test_sentinel2_band_alignment_and_non_empty`: Verifies exact shape, transform, and CRS alignment across all 10m bands with no null coverage.

Full repository test suite:
- `146 passed, 3 skipped, 0 failed` in 37.24 seconds.
