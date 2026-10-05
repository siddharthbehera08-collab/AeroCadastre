# SIH26012 — AeroCadastre: Autonomous GeoAI Cadastral Mapping Platform

**Problem Statement:** SIH26012 — *AI-Based Automated Urban Parcel Mapping and Cadastral Feature Extraction System using Drone Imagery*  
**Ministry / Department:** Ministry of Rural Development, Department of Land Resources (DoLR)  
**Project Root:** `D:\SIH26012_AeroCadastre\`  
**Regression Status:** **149 PASSED**, **0 FAILED** across full automated test suite  

> [!NOTE]
> **Core Operating Principle:**  
> *"AI should not replace the cadastral surveyor. AI should turn the surveyor from a digitizer into a verifier."*

> [!IMPORTANT]
> **Legal & Cadastral Truthfulness Notice:**
> 1. **AI-Assisted Surveyor Verification:** This platform transforms cadastral surveying from manual digitization into evidence-backed adjudication. All AI-inferred parcel boundaries carry the status **`CANDIDATE_PARCEL`** / **`PRELIMINARY_CANDIDATE_GEOMETRY`** and are **never** claimed to be legally binding statutory titles.
> 2. **Cadastral Evidence & Adaptation Status:**
>    - **Implemented & Validated:** ResUNet models validated on Inria (buildings) and SpaceNet (roads); terrain gradient analysis on real Pune DEM; 6-agent AI Council consensus; Sentinel-2 L2A multispectral data (Pune tile `S2A_MSIL2A_20261002T053241_R105_T43QCA`); Google Satellite basemap with Maharashtra administrative hierarchy & Pune OSM evidence overlays; WebGIS HITL verification workflow.
>    - **Prototype / Demo:** Automated candidate parcel inference operates as a high-fidelity prototype; full Indian statutory cadastral extraction remains an active engineering mission pending official sub-meter drone imagery acquisition.
> 3. **ULPIN Compliance:** All generated outputs carry **`NOT_ASSIGNED_PRE_CADASTRE`** in full accordance with national land record modernization frameworks (DILRMP). Official 14-digit Bhu-Aadhaar numbers are assigned exclusively by competent state survey authorities.

---

## 1. System Architecture & End-to-End Workflow

```
Multi-Modal Ingestion (VHR Optical, DEM/Slope Rasters, Reference Vector Layers)
        ↓
Model A (ResUNet Building Detection) + Model B (ResUNet Road Extraction)
        ↓
Model D (Terrain Gradient & Slope Feature Extractor)
        ↓
Model E (Multi-Source Spatial Evidence Fusion with Dynamic Weight Renormalization)
        ↓
Model F (Parcel Inference Engine: Planarization, Ring Extraction, Sliver Filtering)
        ↓
Model G (Topology Validation: Gaps, Overlaps, Compactness, OGC Repair)
        ↓
Model H (GIS Conflict & Anomaly Detector: Cross-Layer Discrepancies)
        ↓
Deterministic Multi-Criteria Bayesian Confidence Engine (HIGH / MEDIUM / LOW / REJECT)
        ↓
AI Council Adjudication (6 Autonomous Domain Agents + Precedence Consensus)
        ↓
Smart Field Route Planner (Priority TSP Optimization) & Cadastral AI Copilot
        ↓
WebGIS HITL Surveyor Review (Split, Merge, Modify, Approve, Reject)
        ↓
ULPIN-Compliant GIS Export (GeoJSON, GeoPackage, Shapefile with Provenance Metadata)
        ↓
Active Learning Feedback Export (Prospective Retraining Candidates)
```

---

## 2. Implemented Subsystems & Components

- **ResUNet Champions:** Model A (Inria benchmark) and Model B (SpaceNet 3 Paris benchmark) checkpoints verified and registered.
- **Terrain Engine (Model D):** Operational on real Pune DEM/slope derivatives (EPSG:32643) across 704 grid cells.
- **Multi-Source Fusion (Model E):** 6-domain fusion engine dynamically renormalizing weights without penalizing missing modalities.
- **Parcel Inference (Model F):** Planarizer and ring extraction yielding candidate parcel polygons.
- **Topology & Anomaly (Models G & H):** Complete validation, gap detection, overlap repair, and cross-layer conflict checks.
- **AI Council:** 6 autonomous agents (Vision, Geometry, GIS, ML, Anomaly, Field Verification) providing advisory consensus.
- **Cadastral AI Copilot:** Grounded natural-language assistant answering inspection questions while strictly refusing ownership claims.
- **Field Route Planner:** Metric TSP nearest-neighbor route planner optimizing surveyor verification visits.
- **Parcel Time Machine:** Version diff engine calculating Hausdorff boundary displacements and IoU variances.

---

## 3. Quick Start & Execution Commands

### 1. Run the Automated Synthetic Demo (`AERO-SYNTH-001`)
Executes all 11 stages of the pipeline end-to-end on controlled synthetic fixtures:
```powershell
python scripts/run_demo.py
```
Output files are saved to `outputs/AERO-SYNTH-001/`.

### 2. Check Real-Data Readiness & Diagnostic Status
Audits the filesystem for real Indian optical imagery, terrain, and reference layers:
```powershell
python scripts/check_real_data_readiness.py
```

### 3. Run Pipeline Performance Profiling
Benchmarks latency, memory, and parcel throughput across all 11 sub-systems:
```powershell
python scripts/profile_pipeline.py
```

### 4. Run Complete Regression Test Suite
Executes all 26 test suites with 121 automated tests:
```powershell
python -m pytest tests/ -v
```

### 5. Start Backend REST API Server (Port 8000)
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 6. Start Frontend WebGIS (Next.js on Port 3000)
```powershell
cd frontend
npm run dev
```

---

## 4. Key Documentation Links

- [Final System Status Report 2026-10-04](file:///D:/SIH26012_AeroCadastre/docs/FINAL_SYSTEM_STATUS_2026-10-04.md)
- [Blocker Gate Matrix](file:///D:/SIH26012_AeroCadastre/docs/BLOCKER_GATE_MATRIX.md)
- [Dataset Provenance & Data Contracts](file:///D:/SIH26012_AeroCadastre/docs/DATA_PROVENANCE.md)
- [Model Card Summary](file:///D:/SIH26012_AeroCadastre/docs/MODEL_CARD_SUMMARY.md)
- [Backend REST API Guide](file:///D:/SIH26012_AeroCadastre/docs/API_GUIDE.md)
- [Synthetic Demo Guide](file:///D:/SIH26012_AeroCadastre/docs/DEMO_GUIDE.md)
