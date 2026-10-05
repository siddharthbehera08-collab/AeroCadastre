# Authentic Indian Pune Pilot Demonstration Guide
SIH26012 — AeroCadastre

## Executive Summary

The AeroCadastre Pune Pilot connects authentic Indian geospatial evidence with frozen GPU champion deep-learning models to provide an automated, transparent, and legally compliant cadastral feature extraction system.

---

## 1. Demonstrated Datasets & Layers

### A. Maharashtra Administrative Hierarchy
- **Dataset:** Administrative Boundary Database for State up to Taluk level with HQ
- **Hierarchy:**
  1. **State:** Maharashtra (Capital / HQ: Mumbai)
  2. **District:** Pune District (Collectorate HQ: Pune City)
  3. **Taluks:**
     - **Pune City Taluk** (HQ: Pune City Collectorate & PMC)
     - **Haveli Taluk** (HQ: Pune - NAKSHA peri-urban pilot zone)
     - **Mulshi Taluk** (HQ: Paud)
     - **Khed Taluk** (HQ: Rajgurunagar)
- **API Endpoint:** `/api/gis/admin-boundaries`

### B. Pune Historic Core Pilot
- **Spatial Extent:** Historic Urban Core (Peth Areas, Pune), Maharashtra
- **CRS:** EPSG:4326 (WGS 84) and EPSG:32643 (UTM Zone 43N)
- **Building Footprints:** 1,917 authentic OpenStreetMap vector polygons
- **Road Centerlines:** 413 authentic OpenStreetMap vector segments
- **Elevation Grid:** 100m derived elevation surface from Open-Elevation queries
- **API Endpoint:** `/api/gis/pune-pilot`

### C. Frozen GPU Champion Models
- **Building Detection (Model A):**
  - Checkpoint: `experiments/building_detection/EXP_BUILDING_RESUNET_GPU_001/checkpoints/best_model.pt`
  - SHA256: `b3893d87a8364e05849ecc4b204932dbf1df8d57e204f128e784d44ef2894578`
  - Provenance: Inria Aerial Image Labeling (European Urban Benchmark)
  - Verified Metrics: Test IoU 65.18%, Test Dice 78.92%
- **Road Extraction (Model B):**
  - Checkpoint: `experiments/road_detection/EXP_ROAD_RESUNET_GPU_001/checkpoints/best_model.pth`
  - SHA256: `00782011614c8b11df32e559e1b61080090752b0574a9050bb07e243c0bfc816`
  - Provenance: SpaceNet Paris (Real Urban Road Benchmark)
  - Verified Metrics: Test IoU 31.80%, Test Dice 48.25%

---

## 2. Multi-Agent AI Council Architecture

The 6-agent deliberative council fuses multi-modal signals before any cadastral recommendation is produced:
1. **Vision Agent:** Analyzes optical textures and rooftop boundaries.
2. **Geometry Agent:** Evaluates polygon compactness, collinearity, and right-angles.
3. **GIS Topology Agent:** Checks for parcel overlaps, slivers, and road encroachment.
4. **Elevation/DSM Agent:** Validates vertical height steps and terrain slopes.
5. **Historical Anomaly Agent:** Detects temporal changes and unrecorded subdivisions.
6. **Field Dispatch Agent:** Formulates optimal surveyor inspection routes for flagged anomalies.

---

## 3. Statutory Compliance & Non-Fabrication Rules

1. **No Hallucinated Titles:** Candidate parcel polygons are strictly labeled `AI-inferred preliminary parcel (requires ground verification)`.
2. **Pre-Cadastre ULPIN Compliance:** All exports and database entries maintain `ulpin_status = NOT_ASSIGNED_PRE_CADASTRE`.
3. **Honest Imagery Blocker Reporting:** When real Indian high-resolution drone orthomosaics are unavailable, adapters return `BLOCKED_BY_IMAGERY_DATA` rather than substituting coarse satellite imagery or synthetic textures as real data.
