# SIH26012 AeroCadastre — Performance & Scale Benchmark Review (`PERFORMANCE_REVIEW.md`)

**Date:** 2026-10-01  
**Benchmark Artifact:** [`experiments/performance_benchmarks.json`](file:///d:/SIH26012_AeroCadastre/experiments/performance_benchmarks.json)  
**Test Suite:** `backend/tests/test_full_system_adversarial.py::test_21_performance_benchmarks_10_100_500_1000_parcels`  
**Environment:** Windows 11 x64, Python `3.12.10`, PostgreSQL `16.4` + PostGIS `3.6.2` (`127.0.0.1:5432`)

---

## 1. PostGIS & FastAPI Scale Benchmark (`10`, `100`, `500`, `1,000` Parcels)

We executed real scale benchmarks inserting `10`, `100`, `500`, and `1,000` distinct `POLYGON` parcels (`EPSG:4326` with metric `EPSG:32643` attributes) into PostgreSQL/PostGIS, running GiST-indexed `ST_Intersects` bounding-box spatial queries, and serializing full GeoJSON parcel collections over HTTP via FastAPI:

| Parcel Count (`N`) | Bulk PostGIS Insert (`ms`) | PostGIS GiST `ST_Intersects` Query (`ms`) | FastAPI GeoJSON Serialization (`GET /api/projects/{id}/parcels`) (`ms`) | Throughput (Parcels / sec Insert) |
|---|---|---|---|---|
| **`10` Parcels** | `9.09 ms` | `4.89 ms` | `42.03 ms` | `1,100 parcels/s` |
| **`100` Parcels** | `19.23 ms` | `3.27 ms` | `485.94 ms` | `5,200 parcels/s` |
| **`500` Parcels** | `67.15 ms` | `9.95 ms` | `727.43 ms` | `7,446 parcels/s` |
| **`1,000` Parcels** | `113.47 ms` | `26.12 ms` | `1,125.70 ms` | `8,813 parcels/s` |

---

## 2. Subsystem Latency Profile

| Subsystem Operation | Measured Latency (`ms`) | Bottleneck Analysis & Optimization Notes |
|---|---|---|
| `GET /api/health` (PostGIS check + table counts) | `4.2 ms` – `8.5 ms` | Fast catalog lookup via pooled SQLAlchemy connection |
| `GET /api/scenes/{id}/bundle` (`18` parcels + `8` buildings + `2` roads + topology + council) | `24.6 ms` – `41.8 ms` | Uses stored `geometry_geojson` fallback cache alongside PostGIS `EWKB` to avoid N+1 `ST_AsGeoJSON` round-trips |
| `PUT /api/parcels/{id}` (Shapely repair + `EPSG:32643` area + PostGIS conflict check + 6-Agent Council + `FeatureVersion` + `AuditLog`) | `18.4 ms` – `35.2 ms` | Indexed spatial queries keep interactive map editing responsive (`< 40 ms`) |
| `POST /api/analysis/run` (PyTorch `AeroCadastreMultiTaskNet` 256x256 CPU inference + DSM fusion + vectorization) | `68.4 ms` – `115.0 ms` | Lightweight `ConvNeXt-Tiny` encoder (`2.15M` params) enables sub-120ms CPU tile inference without requiring a dedicated GPU |
| `POST /api/exports` (`GeoJSON`, `GPKG`, `SHP_ZIP`, `CSV` for 18 parcels) | `14.0 ms` – `62.5 ms` | Pure-Python + SQLite/OGC GeoPackage & `pyshp` binary writers stream directly to `outputs/exports/` |
