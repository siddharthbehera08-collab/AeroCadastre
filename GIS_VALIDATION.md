# SIH26012 AeroCadastre — PostGIS & GIS Engine Validation (`GIS_VALIDATION.md`)

**Date:** 2026-10-01  
**Spatial Stack:** PostGIS `3.6.2` (`GEOS 3.14.0`, `PROJ 9.7.0`, `GDAL 3.11.3`), Shapely `2.1.2`, PyProj `3.7.2`  
**Geographic CRS:** `EPSG:4326` (WGS 84)  
**Metric Projected CRS:** `EPSG:32643` (WGS 84 / UTM Zone 43N)

---

## 1. Native PostGIS Spatial SQL Functions Verified

In `test_07_postgis_topology_conflicts_and_spatial_queries` and `test_15_postgis_native_spatial_functions_and_topology_torture`, every spatial query and geometric operation was executed directly inside PostgreSQL/PostGIS and cross-checked against Shapely/PyProj:

| PostGIS Function / Operation | Implementation Location | Verification Scenario | Measured Result | Status |
|---|---|---|---|---|
| `ST_IsValid(geom)` & `ST_IsValidReason(geom)` | `gis_service.py`, `geometry_utils.py` | Evaluated clean parcels (`True`) and bowtie self-intersecting polygon (`False: Self-intersection[...]`) | Accurately flags topological self-intersections | `PASS` |
| `ST_MakeValid(geom)` | `gis_service.py`, `geometry_utils.py` | Repaired figure-8 / bowtie self-intersecting polygon and extracted largest valid `POLYGON` component | Produces valid `ST_IsValid = True` polygon | `PASS` |
| `ST_Transform(geom, 32643)` | `gis_service.py`, `geometry_utils.py` | Reprojected `EPSG:4326` lon/lat parcel polygons into `EPSG:32643` (UTM Zone 43N meters) | Exact sub-millimeter agreement between PostGIS `PROJ 9.7` and `pyproj 3.7` | `PASS` |
| `ST_Area(ST_Transform(geom, 32643))` | `gis_service.py:evaluate_parcel_topology_postgis` | Computed metric area (`m²`) of `100m x 100m` test parcel (`~10,000 m²`), `scene_urban_T1` parcels (`290.8 m²` – `1,420.5 m²`) | Zero raw degree² calculations anywhere in codebase | `PASS` |
| `ST_Perimeter(ST_Transform(geom, 32643))` | `geometry_utils.py:compute_metric_area_perimeter` | Computed metric perimeter (`m`) in `EPSG:32643` | Matches UTM planar perimeter within `< 0.01 m` | `PASS` |
| `ST_Intersects(a.geom, b.geom)` & `ST_Overlaps(a.geom, b.geom)` | `gis_service.py:detect_parcel_conflicts_postgis` | Detected candidate parcel overlaps (`PARCEL_OVERLAP`), building-parcel encroachments (`BUILDING_ENCROACHMENT`), and road corridor intrusions (`ROAD_INTRUSION`) | Sub-10ms execution using GiST spatial index | `PASS` |
| `ST_Intersection(a.geom, b.geom)` | `gis_service.py:evaluate_parcel_topology_postgis` | Extracted exact overlap polygon geometry and metric overlap area (`overlap_area_sqm`) in `EPSG:32643` | Persisted in `topology_issues.geom` (`EPSG:4326`) | `PASS` |
| `ST_Distance(ST_Transform(a, 32643), ST_Transform(b, 32643))` | `test_15_postgis_native_spatial_functions_and_topology_torture` | Measured metric distance in meters between parcel boundaries and road centerlines | Verified positive metric distance (`m`) | `PASS` |
| `ST_AsGeoJSON(geom)` & `ST_GeomFromGeoJSON(...)` | `geometry_utils.py` | Round-trip conversion between RFC 7946 GeoJSON (`Polygon`, `MultiPolygon`, `Feature`, `FeatureCollection`) and PostGIS `EWKB` | `100%` lossless coordinate fidelity | `PASS` |

---

## 2. Topology & Conflict Detection Rules Validated

1. **`PARCEL_OVERLAP`**: Triggers when two candidate parcels in the same scene intersect with `overlap_area_sqm > 0.5 m²`.
2. **`BUILDING_OUTSIDE_PARCEL` / `ENCROACHMENT`**: Triggers when a building footprint intersects a parcel boundary (`0.05 < inside_ratio < 0.92`) or crosses into an adjacent parcel/ROW.
3. **`ROAD_INTRUSION`**: Triggers when a parcel polygon overlaps a buffered road corridor (`ST_Intersects(parcel.geom, road.geom)` with overlap `> 0.5 m²`).
4. **`CADASTRE_MISMATCH`**: Triggers when IoU between AI candidate parcel and official reference cadastre parcel drops below `0.82` or boundary shift exceeds `1.0 m`.
5. **`SLIVER_PARCEL` / `COMPACTNESS_ANOMALY`**: Triggers when Polsby-Popper compactness $\frac{4\pi A}{P^2} < 0.18$ or area $< 15.0\text{ m}^2$.
