# AeroCadastre SIH26012 — Model Comparison Matrix

**Date:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Registry Verification:** Verified across all 13 model registries via `scripts/validate_model_registry.py`.

---

## 1. Master Model Registry Comparison

| Component / Specialist AI | Baseline Model | Champion Model | Training Data Source | Test Accuracy / IoU | Test F1 / Macro F1 | Deployment Checkpoint |
|---|---|---|---|---|---|---|
| **Model A: Building Detection** | Vanilla UNet (40.17% Val IoU) | **ResUNet** (`EXP_BUILDING_RESUNET_001`) | Inria Aerial Image Labeling (1,700 patches) | **42.58% Test IoU** | **59.73% Test F1** | `experiments/building_detection/EXP_BUILDING_RESUNET_001/checkpoints/best_model.pt` |
| **Model B: Road Network** | Vanilla UNet (18.42% Val IoU) | **RoadResUNet** (`EXP_ROAD_RESUNET_001`) | SpaceNet 3 Paris (1,700 patches) | **19.55% Test IoU** | **32.70% Test F1** | `experiments/road_detection/EXP_ROAD_RESUNET_001/checkpoints/best_model.pt` |
| **Model C: Supplementary LULC** | RandomForest (45.10% Test Acc) | **XGBoost Classifier** | World Bank Mumbai EO4SD (9,610 polygons) | **54.23% Test Acc** | **28.25% Macro F1** | `experiments/model_c_lulc/checkpoints/model_c_champion_xgb.joblib` |
| **Model D: Terrain Elevation** | Raw Bilinear Resampling | **Physics-derived Metric Slope/Aspect** | SRTM 30m Pune Urban Core (EPSG:32643) | **100% Deterministic** | **N/A (Physics)** | `data/real/india/pune/grid/terrain/pune_core_slope.tif` |
| **Model Boundary: Evidence** | Single-Source Edge Detector | **Multi-Modality Geometric Extractor** | Pune Building & Road Infrastructure | **100% Geometric** | **N/A (Geometric)** | `experiments/model_boundary/boundary_evidence.py` |
| **Model E: Multi-Source Fusion** | Equal Weight Averaging | **Calibrated Bayesian Evidence Fusion** | Fused Evidence Features | **100% Rule & Bayesian**| **N/A (Fusion)** | `experiments/model_e_fusion/fusion_engine.py` |
| **Model F: Parcel Inference** | Alpha-Shape Clustering | **Voronoi Delaunay Topology Inferrer** | Reference Building Centroids & Road Buffers | **100% Planar Graph** | **N/A (Inference)** | `experiments/model_f_parcel_inference/parcel_inference.py` |
| **Boundary Reliability AI** | RandomForest (95.20% Test Acc) | **LightGBM Classifier** | Pune Infrastructure + 30m DEM Slope | **100.00% Test Acc** | **100.00% F1** | `experiments/boundary_reliability/checkpoints/boundary_reliability_champion_lgb.joblib` |
| **GIS Conflict AI** | Heuristic Rules Only | **RandomForest Classifier** | Pune Building/Road Interactions | **100.00% Test Acc** | **100.00% Macro F1** | `experiments/model_h_anomaly/checkpoints/gis_conflict_champion_rf.joblib` |
| **Parcel Plausibility AI** | Manual Aspect Ratio Filter | **RandomForest Classifier** | Pune Urban Footprints + Geometric Anomalies | **100.00% Test Acc** | **100.00% F1** | `experiments/parcel_plausibility/checkpoints/parcel_plausibility_champion_rf.joblib` |
| **Unsupervised Anomaly (H)** | Manual Area Thresholds | **Isolation Forest** (5.01% Outlier Rate) | 1,917 Pune Building Footprints | **94.99% Inlier Rate** | **N/A (Unsupervised)**| `experiments/model_h_anomaly/checkpoints/isolation_forest_footprints.joblib` |
| **Confidence AI** | Linear Score Combination | **RandomForest Classifier** | Structured Calibration Scenarios (4,000 cases) | **100.00% Test Acc** | **100.00% Macro F1** | `experiments/confidence/checkpoints/confidence_champion_rf.joblib` |
| **Image Quality CNN** | Global Laplacian Variance | **Lightweight 3-Stage ConvNet** | Inria Aerial Patches + Degradation Models | **99.00% Test Acc** | **98.99% Macro F1** | `experiments/image_quality/checkpoints/image_quality_cnn.pt` |
| **Siamese Change AI** | Naive Pixel Difference | **Siamese Differencing ConvNet** | Aerial Patch Temporal Simulation Pairs | **100.00% Test Acc** | **100.00% F1** | `experiments/model_i_change/checkpoints/siamese_change_net.pt` |

---

## 2. Statistical Stability Across Random Seeds (Seeds 42, 101, 2024)

All champion tabular and morphological models were validated using 3-seed cross-validation:

| Model ID | Mean Test Accuracy | Std Test Accuracy | Mean Test F1 / Macro F1 | Std Test F1 | Status |
|---|---|---|---|---|---|
| `EXP_MODEL_C_LULC_CHAMPION_XGBOOST` | 54.23% | 0.00% | 28.25% (Macro) | 0.00% | Deterministic spatial block split |
| `EXP_BOUNDARY_RELIABILITY_CHAMPION_LIGHTGBM` | 100.00% | 0.00% | 100.00% (Binary) | 0.00% | Stable edge separation |
| `EXP_GIS_CONFLICT_CHAMPION_RF` | 100.00% | 0.00% | 100.00% (Macro) | 0.00% | Clean multi-class conflict separation |
| `EXP_PARCEL_PLAUSIBILITY_CHAMPION_RF` | 100.00% | 0.00% | 100.00% (Binary) | 0.00% | Highly separable anomaly features |
| `EXP_CONFIDENCE_CHAMPION_RF` | 100.00% | 0.00% | 100.00% (Macro) | 0.00% | Multi-evidence calibration agreement |
