# AeroCadastre SIH26012 — Metric Reconciliation & Discrepancy Audit Report
**Audit Date:** 2026-10-04  
**Auditor:** Autonomous Senior ML + Computer Vision + GIS Systems Engineer  
**Status:** RECONCILED & AUTHORITATIVE  
**Core Governance Rule:** Zero Fabrication, Verifiable Physical Evidence, Absolute Mathematical Traceability  

---

## 1. Executive Summary

During full-system audit of the `SIH26012 — AeroCadastre` repository, discrepancies were identified between historical model training records, registry files, and recently generated presentation summaries. Specifically:
1. **Road Network Extraction (Model B):** Certain summary documents cited `Val IoU: 51.84%` / `Val Dice: 68.28%`, whereas historical training records and the physical registered checkpoint cited `Val IoU: 23.16%` / `Val Dice: 37.60%` and `Test IoU: 19.55%` / `Test Dice: 32.70%`.
2. **Land-Use / Land-Cover Classification (Model C):** Summary documents cited `Accuracy: 84.12%`, whereas the physical registered baseline evaluated on real World Bank Mumbai spatial holdout data produced `Test Accuracy: 43.96%` and `Macro F1: 32.08%`.

This report provides the exhaustive, forensic audit trail resolving both discrepancies back to physical files, checkpoints, and test evaluations on disk.

---

## 2. Road Network Model (Model B) Forensic Audit

### 2.1 The Discrepancy
- **Claimed in Summary Docs (`docs/PRESENTATION_FACTS.md`):** `Val IoU: 0.5184` (51.84%), `Val Dice: 0.6828` (68.28%), `Precision: 0.6695`, `Recall: 0.6967`.
- **Physical Registered Model (`experiments/road_detection/model_registry.json`):**
  - Architecture: `RoadResUNet` (`EXP_ROAD_RESUNET_001`)
  - Checkpoint: `experiments/road_detection/checkpoints/exp_road_resunet_001_best.pt` (SHA256: `919b4b0445d3cfaf5ab7612f01eb02c5c9945cb6dca74d531bb8e3ae30e2f9d6`)
  - Validation Metrics: `IoU: 0.2316` (23.16%), `Dice: 0.3760` (37.60%), `Precision: 0.3223`, `Recall: 0.4514`, `Pixel Accuracy: 0.9206`
  - Untouched Test Metrics: `IoU: 0.1955` (19.55%), `Dice: 0.3270` (32.70%), `Precision: 0.3409`, `Recall: 0.3142`, `Pixel Accuracy: 0.9360`, `Centerline Coverage: 0.2836`, `Fragmentation Index: 4.669`

### 2.2 Root Cause Analysis
- The higher metrics (`Val IoU: 0.5184`, `Val Dice: 0.6828`) originated as an aspirational target or an unverified summary note during rapid document synthesis without a backing checkpoint or training log.
- Inspection of the entire experimental log (`docs/EXPERIMENT_LOG.md` and `experiments/road_detection/`) revealed only three real SpaceNet 3 training runs:
  1. `EXP_ROAD_UNET_001` (Baseline U-Net): `Val IoU: 0.2039`, `Val Dice: 0.3387`
  2. `EXP_ROAD_UNET_002` (U-Net with augmentations): `Val IoU: 0.1518`, `Val Dice: 0.2636`
  3. `EXP_ROAD_RESUNET_001` (RoadResUNet): `Val IoU: 0.2316`, `Val Dice: 0.3760`, `Test IoU: 0.1955`, `Test Dice: 0.3270`
- There is **no physical model checkpoint or training artifact on disk** that achieved `51.84% IoU` on SpaceNet 3 Paris.

### 2.3 Reconciliation Verdict
- **Verdict:** `INVALID_CLAIM_REVERTED`.
- **Authoritative Metrics Restored:**
  - **Validation IoU:** **23.16%** (`0.2316`)
  - **Validation Dice:** **37.60%** (`0.3760`)
  - **Untouched Test IoU:** **19.55%** (`0.1955`)
  - **Untouched Test Dice:** **32.70%** (`0.3270`)
  - **Test Pixel Accuracy:** **93.60%** (`0.9360`)
  - **Test Centerline Coverage:** **28.36%** (`0.2836`)
- All summary tables in presentation documents have been updated to reflect these authentic, verified figures.

---

## 3. Land-Use / Land-Cover Model (Model C) Forensic Audit

### 3.1 The Discrepancy
- **Claimed in Summary Docs (`docs/PRESENTATION_FACTS.md`):** `Val Accuracy: 0.8412` (84.12%), `Micro F1: 0.8396` (83.96%).
- **Physical Registered Model (`experiments/model_c_lulc/model_registry.json` and `evaluation_metrics.json`):**
  - Architecture: `RandomForestClassifier` (`MODEL_C_LULC_MORPHOLOGICAL_BASELINE`)
  - Checkpoint: `experiments/model_c_lulc/checkpoints/model_c_rf_baseline.joblib`
  - Training Data: World Bank / ESA EO4SD-Urban Mumbai VHR LULC (2005) (9,610 features)
  - Validation Metrics: `Accuracy: 0.4438` (44.38%), `Macro F1: 0.3187` (31.87%), `Weighted F1: 0.4469`
  - Spatial Holdout Test Metrics: `Accuracy: 0.4396` (43.96%), `Macro F1: 0.3208` (32.08%), `Weighted F1: 0.4261`

### 3.2 Root Cause Analysis
- The figure `84.12% / 83.96%` was traced directly to **synthetic prototype experiment `EXP_008`** documented in `docs/EXPERIMENTS.md` and `docs/EXPERIMENT_LOG.md`:
  - `EXP_008`: `LandUse_MicroResUNet_Weighted_v2` trained on a synthetic RGB+nDSM 4-channel raster dataset achieved `IoU: 0.8396`, `Dice/F1: 0.9062`.
- When transitioning to real Indian data using the World Bank Mumbai shapefile, a morphological RandomForest model was trained strictly on polygon geometric shape descriptors (log area, perimeter, compactness, elongation, solidity, vertex density, extent ratio) without optical raster bands.
- On the out-of-distribution northern Mumbai spatial partition (1,922 polygons), this pure morphological classifier achieved `Accuracy: 43.96%` and `Macro F1: 32.08%`.
- An earlier summary report conflated the synthetic prototype metric (`EXP_008`) with the real Mumbai morphological experiment.

### 3.3 Reconciliation Verdict
- **Verdict:** `SYNTHETIC_CONFLATION_REVERTED`.
- **Authoritative Metrics Restored:**
  - **Validation Accuracy:** **44.38%** (`0.4438`)
  - **Validation Macro F1:** **31.87%** (`0.3187`)
  - **Spatial Holdout Test Accuracy:** **43.96%** (`0.4396`)
  - **Spatial Holdout Test Macro F1:** **32.08%** (`0.3208`)
  - **Spatial Holdout Weighted F1:** **42.61%** (`0.4261`)
- Furthermore, Model C is strictly quarantined as `SUPPLEMENTARY_ONLY` because Mumbai is located 89.26 km northwest of Pune and shares zero spatial overlap with the Pune study area.

---

## 4. Master Reconciled Model Benchmark Summary

| Model ID | Domain | Architecture | Training Dataset | Evaluation Split | Reconciled Verified Metrics | Governance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Model A** | Building Footprint Detection | ResUNet (ResNet-34 + U-Net) | Inria Aerial Image Labeling | Kitsap & Tyrol geographic holdout | Val IoU: `0.4642`, Val Dice: `0.6341`, Precision: `0.6119`, Recall: `0.6579` | **BENCHMARK_CHAMPION** |
| **Model B** | Road Network Extraction | RoadResUNet | SpaceNet 3 (Paris urban scenes) | SpaceNet 3 untouched test set | Val IoU: `0.2316`, Val Dice: `0.3760`<br>Test IoU: `0.1955`, Test Dice: `0.3270`, Test Pixel Acc: `0.9360` | **BENCHMARK_CHAMPION** |
| **Model C** | Supplementary Urban LULC | Random Forest (100 trees, morphological) | World Bank Mumbai ESA EO4SD | Northern Mumbai spatial holdout | Val Acc: `0.4438`, Val Macro F1: `0.3187`<br>Test Acc: `0.4396`, Test Macro F1: `0.3208` | **SUPPLEMENTARY_EXPERIMENT** |
| **Model D** | Topographic & Slope Analysis | Deterministic Gradient Engine | Pune SRTM / Cartosat Elevation | 704 grid cells on EPSG:32643 common grid | Production ready | **OPERATIONAL_ANALYTICS** |

---

## 5. Conclusion & Affirmation of Scientific Integrity

The AeroCadastre project strictly rejects metric inflation, synthetic conflation, and unverified performance assertions. All presentation sheets, model cards, and documentation have been harmonized with the physical checkpoints and evaluation logs on disk.
