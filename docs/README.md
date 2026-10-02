# SIH26012 — AeroCadastre: Autonomous GeoAI Cadastral Mapping Platform

**Problem Statement:** SIH26012 — *AI-Based Automated Urban Parcel Mapping and Cadastral Feature Extraction System using Drone Imagery*  
**Ministry / Department:** Ministry of Rural Development, Department of Land Resources (DoLR)  
**Project Root:** `D:\SIH26012_AeroCadastre\`

> [!IMPORTANT]
> **Legal & Cadastral Truthfulness Notice:**
> 1. **AI-Assisted Surveyor Verification:** This platform turns the cadastral surveyor from a manual digitizer into an evidence-backed verifier. AI-generated boundaries are strictly labeled **`AI-GENERATED / REQUIRES VERIFICATION`** or **`INFERRED CANDIDATE GEOMETRY`** and are **never** claimed to be legally authoritative land records.
> 2. **Synthetic Data Policy:** All training, validation, testing, and temporal change scenes included in this build are deterministically generated locally and labeled **`SYNTHETIC DEMO DATA`**.
> 3. **ULPIN Compatibility:** Represented strictly as **`ULPIN_READY_METADATA`** (never fabricating official government ULPINs).

---

## 1. End-to-End Connected Workflow (24-Step Vertical Slice)

```
Drone RGB + DSM/DTM Imagery
        ↓
Multi-Model GeoAI Feature Extraction (Buildings, Roads, Boundaries, Land-Use)
        ↓
Multi-Source Evidence Fusion (Visible vs. Inferred vs. Reference Boundaries)
        ↓
Candidate Parcel Polygon Generation (Metric Area & Perimeter in EPSG:32643 UTM 43N)
        ↓
Automated Topology Validation (Overlaps, Gaps, Self-Intersections, Slivers, Holes)
        ↓
GIS Conflict & Anomaly + Temporal Change Analysis (T0 2024 → T1 2025 → T2 2026)
        ↓
6-Agent AI Council & Transparent Confidence Scoring
        ↓
AI-Assisted Field Verification Priority & Smart Field Route Planning
        ↓
Interactive Web-GIS Surveyor Editing (Vertex Move/Add/Delete, Split, Merge, Verify)
        ↓
PostGIS / Spatial SQL Persistence + Version History (Parcel Time Machine)
        ↓
Validated GIS Export (GeoJSON, Shapefile .zip, CSV, GeoPackage .gpkg)
        ↓
Human-in-the-Loop Feedback Store for Future Model Retraining
```

---

## 2. Real Measured Machine Learning Results (`EXPERIMENT_LOG.md`)

All 8 experiments were trained on `100` synthetic training scenes and evaluated on `20` validation scenes (`128×128` at `0.5m` ground sample distance):

| Run ID | Task | Model Name | Architecture | Val IoU | Val Dice / F1 | Precision | Recall | Train Time |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `EXP_001` | `BUILDING_SEG` | `Building_SimpleCNN_v1` | SimpleCNNSeg (3-ch RGB, BCE) | `0.8915` | `0.9426` | `0.9037` | `0.9850` | `7.39s` |
| `EXP_002` | `BUILDING_SEG` | `Building_MicroUNet_v1` | MicroUNet (3-ch RGB, BCEDice) | `0.9798` | `0.9898` | `0.9803` | `0.9994` | `11.31s` |
| `EXP_003` | `BUILDING_SEG` | **`Building_MicroResUNet_RGBD_v2`** | MicroResUNet (4-ch RGB+nDSM, BCEDice) | **`0.9995`** | **`0.9997`** | `0.9996` | `0.9999` | `18.19s` |
| `EXP_004` | `ROAD_SEG` | **`Road_MicroUNet_v1`** | MicroUNet (3-ch RGB, BCEDice) | **`0.9998`** | **`0.9999`** | `0.9998` | `1.0000` | `11.23s` |
| `EXP_005` | `BOUNDARY_SEG` | **`Boundary_MicroResUNet_v1`** | MicroResUNet (4-ch RGB+nDSM, BCEDice) | **`0.8207`** | **`0.9015`** | `0.8315` | `0.9845` | `15.85s` |
| `EXP_006` | `LANDUSE_CLS` | `LandUse_RandomForest_Baseline` | RandomForest (35 trees, RGB+nDSM+5×5) | `0.6809` | `0.7736` | `0.8384` | `0.7495` | `0.26s` |
| `EXP_007` | `LANDUSE_CLS` | `LandUse_MicroUNet` | MicroUNet (4-ch RGB+nDSM, Unweighted CE) | `0.4924` | `0.5780` | `0.5432` | `0.6258` | `15.30s` |
| `EXP_008` | `LANDUSE_CLS` | **`LandUse_MicroResUNet_Weighted_v2`** | MicroResUNet (4-ch RGB+nDSM, Class-Weighted + CosineLR) | **`0.8396`** | **`0.9062`** | `0.8705` | `0.9539` | `33.05s` |

---

## 3. Quick Start

### Start Backend (FastAPI on Port 8000)
```powershell
cd D:\SIH26012_AeroCadastre
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Start Frontend (Next.js Web-GIS on Port 3000)
```powershell
cd D:\SIH26012_AeroCadastre\frontend
npm run dev
```

### Run Automated End-to-End & Adversarial Test Suite
```powershell
cd D:\SIH26012_AeroCadastre
python -m pytest tests/test_vertical_slice_and_adversarial.py -v
```
