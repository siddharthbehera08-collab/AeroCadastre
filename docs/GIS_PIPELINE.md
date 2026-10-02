# SIH26012 — AeroCadastre: GIS, Topology & Cadastral Pipeline (`GIS_PIPELINE.md`)

## 1. Boundary Representation Taxonomy

Every parcel boundary segment is explicitly categorized:
- **`VISIBLE`:** Directly supported by physical wall/fence/hedge contrast in drone RGB and DSM breaklines.
- **`INFERRED`:** Reconstructed from road corridor offset, adjacent building plinths, or parcel block geometry where canopy occlusion hides physical walls.
- **`REFERENCE`:** Legacy non-authoritative cadastral reference map boundary.
- **`HUMAN_VERIFIED`:** Inspected, edited, and signed off by a human cadastral surveyor in the Web-GIS editor.

## 2. Automated Topology Validation (`backend/gis/topology.py`)

Uses `Shapely 2.1` and metric UTM Zone 43N (`EPSG:32643`) projections to detect:
- `SELF_INTERSECTION` & `INVALID_RING` (`explain_validity` + `make_valid`)
- `OVERLAP` (Pairwise polygon intersection $\ge 0.4\text{ m}^2$)
- `GAP` (Unexpected interstitial void between adjacent parcels in the same block)
- `DUPLICATE` (Pairwise spatial IoU $> 0.92$)
- `SLIVER` (Area $< 15\text{ m}^2$ or Polsby-Popper compactness $4\pi A / P^2 < 0.14$)
- `HOLE` & `DISCONNECTED` (`MultiPolygon` parts)
- `INVALID_CRS`

## 3. GIS Conflict, Anomaly & Temporal Change Analysis

- **GIS Conflict Detection (`backend/gis/conflicts_anomalies.py`):** Compares candidate parcels against Reference GIS (`BOUNDARY_MISMATCH`, `EXTRA_PARCEL`, `ROAD_PARCEL_CONFLICT`).
- **Anomaly Detection:** Flags `BUILDING_CROSSING_BOUNDARY`, `EXTREME_AREA`, `UNUSUAL_SHAPE`, and `MODEL_DISAGREEMENT`.
- **Temporal Change Detection (`backend/gis/changes.py`):** Compares `T0 (2024)`, `T1 (2025)`, and `T2 (2026)` to flag `NEW_BUILDING`, `REMOVED_BUILDING`, and `LAND_USE_CHANGE`.
