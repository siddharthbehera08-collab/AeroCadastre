# AeroCadastre SIH26012 — Evaluation & Demonstration Walkthrough Script
**Mission Objective:** Walkthrough guide for hackathon evaluators, survey directors, and technical judges.  
**Demonstration Scenario:** `AERO-SYNTH-001` (Controlled Synthetic Pune Cadastral Quadrant)  

---

## 1. Introduction: The Problem & The AeroCadastre Paradigm (2 Minutes)

- **The Problem:**
  Traditional cadastral mapping under modernization schemes (DILRMP, SVAMITVA) relies on exhaustive manual on-screen digitizing of drone orthoimagery, leading to boundary disputes, topological slivers, and slow survey cycles.
- **The Solution:**
  AeroCadastre transforms the surveyor from a manual digitizer into an **evidence-backed adjudicator**. Multi-source AI extracts building footprints, road corridors, and terrain slopes, fusing them into preliminary candidate parcels with transparent confidence scoring.
- **The Scientific Grounding Rule:**
  AeroCadastre adheres strictly to scientific truthfulness:
  1. We do **not** claim building footprints are legal boundary deeds.
  2. We do **not** fabricate fake satellite imagery or artificial ULPINs.
  3. All preliminary parcel polygons are labeled `CANDIDATE_PARCEL` with status `NOT_ASSIGNED_PRE_CADASTRE`.

---

## 2. Live Technical Walkthrough (5 Minutes)

### Step 1: Run the Automated End-to-End Pipeline
Run the demonstration script from the terminal:
```powershell
python scripts/run_demo.py
```
**Explain what happens:**
- Loads synthetic fixtures (4 buildings, 2 roads, terrain slopes).
- Boundary Evidence Engine generates 8 candidate boundary lines.
- Multi-Source Fusion Engine (Model E) renormalizes weights dynamically.
- Parcel Inference Engine (Model F) planarizes and polygonizes the network into 4 candidate parcels.
- Topology Validator (Model G) detects 0 overlaps and verifies compactness.
- Anomaly Detector (Model H) checks cross-layer road intersections.
- Deterministic Confidence Engine scores each parcel with explainable Bayesian priors.
- AI Council (6 agents) deliberates and reaches advisory consensus.
- Field Route Planner schedules an optimized 4-stop inspection tour (449.33 m).
- Cadastral Copilot generates natural-language explanation cards.
- Pre-Cadastre GIS Exporter saves validated GeoJSON with complete audit provenance.

### Step 2: Show Pipeline Performance Profiling
Run the latency profiler:
```powershell
python scripts/profile_pipeline.py
```
**Point to the results:**
- Total Pipeline Latency: **~29 ms** (~0.029 seconds).
- Throughput: **~135 parcels/second**.
- Peak Memory: **0.18 MB**.

### Step 3: Run Reproducibility & Model Registry Verification
Show the reproducibility check:
```powershell
python scripts/reproduce_demo.py
```
**Point out:**
- Identical SHA256 cryptographic identity confirmed across sequential pipeline executions.

---

## 3. Real-Data Readiness & Blocker Transparency (2 Minutes)

Run the real-data readiness diagnostic tool:
```powershell
python scripts/check_real_data_readiness.py
```
**Explain the honest diagnostic matrix to the judges:**
- **Terrain:** GREEN (SRTM/Cartosat elevation and slope derivatives verified for Pune on EPSG:32643 across 704 cells).
- **Reference Layers:** YELLOW (Pune OSM buildings and roads are auxiliary references only).
- **Optical Imagery:** RED (`BLOCKED_BY_IMAGERY_DATA`).
- **Key Takeaway:**
  *"The complete software pipeline—fusion, parcel inference, topology validation, AI Council, and GIS export—is 100% operational and verified. Real-world Pune cadastral inference remains ethically and scientifically blocked until authentic, licensed sub-meter optical imagery is acquired."*

---

## 4. Closing & Judge Q&A Takeaways

1. **Does AeroCadastre replace the cadastral surveyor?**  
   *No. AeroCadastre is an advisory decision-support system. Final demarcation requires statutory ground verification by a licensed surveyor.*
2. **How does the system handle missing sensor inputs?**  
   *Model E uses dynamic weight renormalization. Missing evidence is never penalized as negative evidence.*
3. **Can the AI assign official property numbers?**  
   *No. Candidate parcels are tagged `NOT_ASSIGNED_PRE_CADASTRE`. Official 14-digit Bhu-Aadhaar numbers are assigned exclusively by state revenue authorities.*
