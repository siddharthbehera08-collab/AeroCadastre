# FORENSIC TRAINING AUDIT REPORT

**Date of Audit:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Target Document Audited:** `docs/FULL_SCALE_TRAINING_FINAL_REPORT_2026-10-04.md`  
**Audit Objective:** Determine with absolute scientific honesty what was genuinely trained, what was reused, what was lightly benchmarked, what was synthetically generated, and what was merely integrated.

---

## 1. Hardware & GPU Forensic Verification

### Executed Forensic Command:
```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.device_count()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
```

### Exact Terminal Output:
```text
2.14.0+cpu
False
0
NO CUDA
```

### Physical vs Runtime Audit Finding:
- **Physical Hardware:** The machine physically contains an `NVIDIA GeForce RTX 4050 Laptop GPU` (6,141 MiB VRAM, Driver 596.49, CUDA capability 13.2).
- **Software Runtime:** The installed PyTorch distribution is `2.14.0+cpu`.
- **Forensic Determination:** **Deep-learning training in this environment did NOT use the RTX 4050 GPU.**
- **Zero-Fabrication Mandate:** Any claim or implication that deep neural network training occurred on the GPU is **FALSE**. All PyTorch operations executed via multi-threaded CPU instructions.

---

## 2. Model-by-Model Forensic Investigation

---

### Model A: Building Detection (`EXP_BUILDING_RESUNET_001`)

- **Was it retrained in the latest mission?** **NO.**
- **Status Classification:** `REUSED_EXISTING_CHECKPOINT`
- **Forensic Evidence:**
  - **Checkpoint File:** `experiments/building_detection/EXP_BUILDING_RESUNET_001/checkpoints/best_model.pt`
  - **File Size:** 24,522,958 bytes (~24.5 MB)
  - **Checkpoint Creation Timestamp:** `2026-10-03 00:51:38` (over 24 hours prior to the latest mission)
  - **Checkpoint Last Modified Timestamp:** `2026-10-03 00:55:08`
  - **SHA256 Hash:** `891d2779a5585b95a0eb3207aa1b64ff13554e1bb1b2e2d93eef57d76b1fca82`
  - **Internal Checkpoint Metadata:** `epochs: 5`, `batch_size: 8`, `max_train_samples: 400`, `max_val_samples: 120`, `device: auto` (fell back to CPU on Oct 3).
  - **Training Duration in Latest Mission:** `TRAINING_DURATION_NOT_VERIFIED` (0 seconds; no retraining occurred).
- **Audit Conclusion:** The latest mission simply loaded the Oct 3 historical checkpoint and reported historical test metrics (`42.58% Test IoU`, `59.73% Test Dice`). **It was NOT retrained.**

---

### Model B: Road Extraction (`EXP_ROAD_RESUNET_001`)

- **Was it retrained in the latest mission?** **NO.**
- **Status Classification:** `REUSED_EXISTING_CHECKPOINT`
- **Forensic Evidence:**
  - **Checkpoint File:** `experiments/road_detection/EXP_ROAD_RESUNET_001/checkpoints/best_model.pth`
  - **File Size:** 24,522,638 bytes (~24.5 MB)
  - **Checkpoint Creation Timestamp:** `2026-10-03 14:13:42`
  - **Checkpoint Last Modified Timestamp:** `2026-10-03 14:23:12`
  - **SHA256 Hash:** `ad2d10d3da903274df22beab0ae4ddad6454e6fa16b0dfc6fe505d9cba4ba81f`
  - **Internal Checkpoint Metadata:** `epochs: 5`, `base_features: 16`, `device: cpu`, `timestamp: 2026-10-03T08:41:16Z`. Contains full Adam optimizer state (`step: 750`).
  - **Training Duration in Latest Mission:** `TRAINING_DURATION_NOT_VERIFIED` (0 seconds; no retraining occurred).
- **Canonical Metrics Verification:** The authentic verified test metrics are **Test IoU = 19.55%** and **Test Dice = 32.70%**. Historical claims of 51.84% / 68.28% are unverified artifacts and strictly rejected.
- **Audit Conclusion:** Model B was **REUSED_EXISTING_CHECKPOINT**. No new training took place in this session.

---

### Model C: Supplementary LULC (`EXP_MODEL_C_LULC_CHAMPION_XGBOOST`)

- **Was it trained during the latest mission?** **YES (Light Multi-Seed Benchmark).**
- **Status Classification:** `SHORT_BENCHMARK`
- **Forensic Evidence:**
  - **Script Executed:** `experiments/run_full_scale_hparam_search.py`
  - **Execution Window:** `2026-10-04 09:51:38` to `09:51:53` (Duration: **15.2 seconds**)
  - **Checkpoint File:** `experiments/model_c_lulc/checkpoints/model_c_champion_xgb.joblib`
  - **File Size:** 423,808 bytes
  - **Creation/Modification Timestamp:** `2026-10-04 09:51:53`
  - **SHA256 Hash:** `0c1e873010f1e4443e2aac5933d1478e31cfbf3686458e69a33c080f7c1930d5`
  - **Trained Parameters:** XGBoost (`n_estimators: 50`, `max_depth: 4`, `learning_rate: 0.05`).
  - **Data Source:** Real World Bank Mumbai LULC shapefile (9,610 polygons).
  - **Data Split:** Spatial block coordinate partitioning based on Northing (`centroid_y`). 70% Train, 15% Val, 15% Test.
  - **Reported Metrics:** **54.23% Test Accuracy**, **28.25% Macro F1**.
  - **Data Leakage Risk:** **LOW.** The spatial Northing split isolates geographic blocks. Test set features were strictly untouched during hyperparameter selection.
- **Audit Conclusion:** Genuinely trained and evaluated on real Mumbai data, but it was a **fast 15-second benchmark** over 11 parameter configurations across 3 seeds. It is a legitimate supplementary baseline, but not a heavy deep learning model.

---

### Boundary Reliability AI (`EXP_BOUNDARY_RELIABILITY_CHAMPION_LIGHTGBM`)

- **Was it trained during the latest mission?** **YES.**
- **Status Classification:** `DERIVED_DATA_EXPERIMENT`
- **Forensic Evidence:**
  - **Execution Window:** `2026-10-04 09:51:53` to `09:51:54` (Duration: **0.8 seconds**)
  - **Checkpoint File:** `experiments/boundary_reliability/checkpoints/boundary_reliability_champion_lgb.joblib`
  - **File Size:** 38,108 bytes
  - **Timestamp:** `2026-10-04 09:51:53`
  - **SHA256 Hash:** `603bcfc34c4090982add3398978c9bf4e8dacc02c129f40e53348bd6c12acf5d`
- **Label Generation Forensic Inspection:**
  - **Positive Labels (Class 1):** Extracted directly from building exterior coordinates (`b.exterior.coords`) where `d_bldg` was hardcoded to `0.0`.
  - **Negative Labels (Class 0):** Generated as random line segments placed across bounding coordinates where `d_bldg` was sampled as `uniform(5.0, 45.0)`.
- **CIRCULAR LABEL GENERATION FLAGGED:**
  > [!CAUTION]
  > The target label `y = 1` vs `y = 0` was constructed directly by whether `d_bldg == 0.0` vs `d_bldg >= 5.0`. The classifier simply learned the label generation formula (`dist_to_building`). The **100.00% accuracy** is an artifact of circular definition and **MUST NOT** be presented to judges as real-world boundary reliability accuracy.

---

### GIS Conflict AI (`EXP_GIS_CONFLICT_CHAMPION_RF`)

- **Was it trained during the latest mission?** **YES.**
- **Status Classification:** `CONTROLLED_SYNTHETIC_EXPERIMENT`
- **Forensic Evidence:**
  - **Execution Window:** `2026-10-04 09:51:54` to `09:51:55` (Duration: **0.7 seconds**)
  - **Checkpoint File:** `experiments/model_h_anomaly/checkpoints/gis_conflict_champion_rf.joblib`
  - **File Size:** 80,441 bytes
  - **Timestamp:** `2026-10-04 09:51:54`
  - **SHA256 Hash:** `37e84becab8df5115259b89dd317cf569421eca9b833a3cf6059c911daa6aa7b`
- **Sample Generation Forensic Inspection:**
  - **Class 0 (NO_CONFLICT):** Normal building footprints with `encroachment_severity = 0.0`.
  - **Class 1 (REFERENCE_CONFLICT):** Parcels manually created with `d_road = 0.0` and `severity = 0.35` / `0.90`.
  - **Class 2 (GEOMETRIC_CONFLICT):** Footprints hardcoded with `d_b = 0.0` and `severity = 0.40` / `0.85`.
  - **Class 3 (FIELD_VERIFICATION):** Footprints hardcoded with `d_road = 1.2`, `d_b = 0.8`, `severity = 0.08` / `0.40`.
- **DETERMINISTIC RULE LEAKAGE FLAGGED:**
  > [!WARNING]
  > The classes were assigned based on deterministic constants in the generator. The RandomForest simply memorized these exact threshold boundaries. The **100.00% accuracy** represents valid unit-testing of conflict logic, but is **NOT production real-world accuracy**.

---

### Parcel Plausibility AI (`EXP_PARCEL_PLAUSIBILITY_CHAMPION_RF`)

- **Was it trained during the latest mission?** **YES.**
- **Status Classification:** `CONTROLLED_SYNTHETIC_EXPERIMENT`
- **Forensic Evidence:**
  - **Execution Window:** `2026-10-04 09:51:55` to `09:51:55` (Duration: **0.6 seconds**)
  - **Checkpoint File:** `experiments/parcel_plausibility/checkpoints/parcel_plausibility_champion_rf.joblib`
  - **File Size:** 43,369 bytes
  - **Timestamp:** `2026-10-04 09:51:55`
  - **SHA256 Hash:** `44d296fa15d4ea01aa102bfb6f3ab2d22038819bfb1bc4168a45c9882f1cbfbe`
- **Sample Generation Forensic Inspection:**
  - **Positives (Class 1):** Real Pune OSM footprints with `road_access = 1.0` and natural compactness.
  - **Negatives (Class 0):** Synthetic slivers (`aspect_ratio = 25.0`), micro-fragments (`area < 5 m²`), needles, and noisy polygons (`vertex_count > 50`), all assigned `road_access = 0.0`.
- **LABEL-CONSTRUCTION LEAKAGE FLAGGED:**
  > [!WARNING]
  > The negative examples have non-overlapping geometric distributions from the positive examples (e.g. `road_access` was 1.0 for all positives and 0.0 for all negatives). The model trivially separated the classes. The **100.00% accuracy** is an internal sanity test, not an empirical generalization metric.

---

### Confidence AI (`EXP_CONFIDENCE_CHAMPION_RF`)

- **Was it trained during the latest mission?** **YES.**
- **Status Classification:** `SYNTHETIC_CALIBRATION_EXPERIMENT`
- **Forensic Evidence:**
  - **Execution Window:** `2026-10-04 09:51:55` to `09:51:56` (Duration: **0.9 seconds**)
  - **Checkpoint File:** `experiments/confidence/checkpoints/confidence_champion_rf.joblib`
  - **File Size:** 55,865 bytes
  - **Timestamp:** `2026-10-04 09:51:56`
  - **SHA256 Hash:** `7d288ff518e61b3d67d5c46fbf83c7ac3539995113084567d591c1415261318b`
- **Sample Generation Forensic Inspection:**
  - 4,000 synthetic rows created via `np.random.uniform`.
  - Class 0 (High): Features uniform in `[0.85, 0.99]`.
  - Class 1 (Medium): Features uniform in `[0.55, 0.84]`.
  - Class 2 (Low): Features uniform in `[0.30, 0.54]`.
  - Class 3 (Reject): Features uniform in `[0.05, 0.30]`.
- **SYNTHETIC CALIBRATION ONLY FLAGGED:**
  > [!NOTE]
  > The features do not overlap across target classes. The **100.00% accuracy** is purely a mathematical verification that the RandomForest interpolates the calibration ladder. It is not human-grounded production confidence validation.

---

### Image Quality CNN

- **Was it trained during the latest mission?** **NO (Trained in Earlier Oct 4 Session).**
- **Status Classification:** `SYNTHETIC_AUGMENTATION_EXPERIMENT`
- **Forensic Evidence:**
  - **Checkpoint File:** `experiments/image_quality/checkpoints/image_quality_cnn_champion.pt`
  - **File Size:** 113,381 bytes
  - **Creation Timestamp:** `2026-10-04 09:31:56` (earlier session)
  - **Training Duration:** **16.4 seconds** (5 epochs on 150 training samples, CPU).
  - **SHA256 Hash:** `cc5ad1b4d06a4a49c9523e1645e7f2757270ad9bba97b4ec5a8e0cb2049d53f2`
- **Dataset & Leakage Audit:**
  - **Base Images:** 250 Inria aerial image patches (`data/real/inria/patches/train/images/*.png`).
  - **Source Tiles:** Patches were sourced from Austin tiles (`austin11` through `austin16`).
  - **Source Tile Separation:**
    - Train: `austin11`, `austin12`, `austin13`, `austin14`
    - Val: `austin14`, `austin15`
    - Test: `austin15`, `austin16`
  - **Leakage Determination:** **CLEAN.** Train and Test have **zero source tile overlap**.
  - **Limitation:** Degraded labels (blur, gaussian noise, exposure reduction) were applied via synthetic PIL filters. Real atmospheric hazing, motion blur, and sensor blooming were not tested.

---

### Siamese Change Detection AI

- **Was it trained during the latest mission?** **NO (Trained in Earlier Oct 4 Session).**
- **Status Classification:** `EXPERIMENTAL_POC`
- **Forensic Evidence:**
  - **Checkpoint File:** `experiments/model_i_change/checkpoints/siamese_change_net_champion.pt`
  - **File Size:** 113,348 bytes
  - **Creation Timestamp:** `2026-10-04 09:32:38` (earlier session)
  - **Training Duration:** **18.1 seconds** (4 epochs on 150 training sample pairs, CPU).
  - **SHA256 Hash:** `58b873aedbc13501f2f81938fae2764b85c2c56a87756ae77f0a8cffae457591`
- **Temporal Pair Forensic Inspection:**
  - **Class 0 (No Change):** Pair `(img1, img1 * random_jitter)` created from the same patch with slight radiometric scaling.
  - **Class 1 (Change):** Pair `(img1, img2)` where `img2` is a completely different geographic patch offset by 19 indices.
- **EXPERIMENTAL POC MANDATE:**
  > [!IMPORTANT]
  > True multi-temporal co-registered drone orthomosaics for Pune do **NOT** exist. This model validates the Siamese differencing architecture and tensor flow, but distinguishing `img1` from an entirely different scene `img2` is trivial. The **100.00% accuracy** does NOT reflect subtle real-world boundary encroachments or demolition events.

---

## 3. Comprehensive Model Audit Summary Table

| Model | Actually Retrained in Latest Mission? | Dataset | Real / Derived / Synthetic | Epochs / Trials | Duration | Device | Checkpoint New? | Leakage Risk | Forensic Status |
|---|---|---|---|---|---|---|---|---|---|
| **Model A: Building** | **NO** | Inria Aerial | Real Benchmark | 5 epochs (historical) | N/A | CPU | **NO** (Oct 3) | Low | `REUSED_EXISTING_CHECKPOINT` |
| **Model B: Road** | **NO** | SpaceNet 3 Paris | Real Benchmark | 5 epochs (historical) | N/A | CPU | **NO** (Oct 3) | Low | `REUSED_EXISTING_CHECKPOINT` |
| **Model C: LULC** | **YES** | Mumbai EO4SD | Real Benchmark | 11 configs × 3 seeds | 15.2s | CPU | **YES** (Oct 4) | Low (Spatial Northing split) | `SHORT_BENCHMARK` |
| **Boundary Reliability** | **YES** | Pune OSM + DEM | Derived / Synthetic | 3 configs × 3 seeds | 0.8s | CPU | **YES** (Oct 4) | **HIGH (Circular label definition)** | `DERIVED_DATA_EXPERIMENT` |
| **GIS Conflict AI** | **YES** | Pune Geometries | Controlled Synthetic | 3 configs × 3 seeds | 0.7s | CPU | **YES** (Oct 4) | **HIGH (Rule leakage in labels)** | `CONTROLLED_SYNTHETIC_EXPERIMENT` |
| **Parcel Plausibility** | **YES** | Pune Geometries | Controlled Synthetic | 3 configs × 3 seeds | 0.6s | CPU | **YES** (Oct 4) | **HIGH (Non-overlapping features)** | `CONTROLLED_SYNTHETIC_EXPERIMENT` |
| **Unsupervised Anomaly** | **NO** | 1,917 Pune Footprints | Real Reference | 1 trial (contamination=0.05) | 1.2s | CPU | **NO** (09:30 session) | None | `SHORT_BENCHMARK` |
| **Confidence AI** | **YES** | Synthetic Grid | Synthetic Calibration | 3 configs × 3 seeds | 0.9s | CPU | **YES** (Oct 4) | **HIGH (Separable synthetic ranges)** | `SYNTHETIC_CALIBRATION_EXPERIMENT` |
| **Image Quality CNN** | **NO** | Inria + PIL Augmentations | Semi-Synthetic | 5 epochs | 16.4s | CPU | **NO** (09:31 session) | Low (Tile-level split verified) | `SYNTHETIC_AUGMENTATION_EXPERIMENT` |
| **Siamese Change AI** | **NO** | Inria Paired Simulation | Simulated Pairs | 4 epochs | 18.1s | CPU | **NO** (09:32 session) | Low (Different scene pairing) | `EXPERIMENTAL_POC` |
| **Model D: Terrain** | N/A | SRTM 30m Pune | Real Physical DEM | Deterministic Math | <1.0s | CPU | N/A | None | `DETERMINISTIC_ENGINE` |
| **Model E: Fusion** | N/A | Multimodal Features | Derived Evidence | Rule / Bayesian Engine | <1.0s | CPU | N/A | None | `DETERMINISTIC_ENGINE` |
| **Model F: Parcel** | N/A | Planar Graph | Planar Geometries | Voronoi / Delaunay Graph | <1.0s | CPU | N/A | None | `DETERMINISTIC_ENGINE` |

---

## 4. Direct Answers to the 10 Critical Audit Questions

### 1. Which models were genuinely trained from scratch in this latest mission?
- **Model C (Supplementary LULC XGBoost)** on 9,610 real Mumbai polygons.
- **Boundary Reliability AI (LightGBM)** on derived boundary segments.
- **GIS Conflict AI (RandomForest)** on geometric conflict scenarios.
- **Parcel Plausibility AI (RandomForest)** on morphological feature vectors.
- **Confidence AI (RandomForest)** on multi-source evidence calibration rows.

### 2. Which models were reused?
- **Model A (Building ResUNet):** Reused checkpoint from `2026-10-03 00:55:08` (`best_model.pt`).
- **Model B (Road RoadResUNet):** Reused checkpoint from `2026-10-03 14:23:12` (`best_model.pth`).
- **Image Quality CNN:** Reused checkpoint from `2026-10-04 09:31:56` (`image_quality_cnn_champion.pt`).
- **Siamese Change Detection AI:** Reused checkpoint from `2026-10-04 09:32:38` (`siamese_change_net_champion.pt`).
- **Isolation Forest Footprint Anomaly Detector:** Reused checkpoint from `2026-10-04 09:30:55`.

### 3. Which models were tiny benchmarks?
- **Model C LULC:** 15.2 seconds across 11 parameter configurations.
- **Isolation Forest:** 1.2 seconds fit on 1,917 footprint vectors.

### 4. Which models used synthetic data?
- **Confidence AI:** 100% synthetic numeric feature ranges (`np.random.uniform`).
- **GIS Conflict AI:** Classes 1, 2, and 3 were synthetic buffered / shifted parcels.
- **Parcel Plausibility AI:** Negatives were synthetically generated sliver/micro/needle polygons.
- **Boundary Reliability AI:** Negatives were randomly placed line segments.

### 5. Which models used derived labels?
- **Boundary Reliability AI:** Label 1 vs 0 derived directly from `seg.distance(building) == 0`.
- **GIS Conflict AI:** Classes derived from geometric rule thresholds.
- **Parcel Plausibility AI:** Labels derived from synthetic morphology generators.

### 6. Which models have potential leakage?
- **Boundary Reliability AI (Circular definition leakage):** The feature `dist_b` directly dictates whether the label is 1 or 0.
- **GIS Conflict AI (Rule leakage):** The feature values (`d_road = 0.0`, `d_b = 0.0`) are hardcoded constants per class.
- **Parcel Plausibility AI (Separability leakage):** Positives have `road_access = 1.0`; negatives have `road_access = 0.0`.
- **Confidence AI (Non-overlapping range leakage):** Synthetic distributions for High, Medium, Low, and Reject have non-overlapping intervals.

### 7. Which metrics are trustworthy?
- **Model A Test Metrics:** `42.58% IoU`, `59.73% Dice` on Inria Aerial holdout test patches.
- **Model B Test Metrics:** `19.55% IoU`, `32.70% Dice` on SpaceNet 3 Paris holdout test patches.
- **Model C Test Metrics:** `54.23% Test Accuracy`, `28.25% Macro F1` on Mumbai LULC (with spatial Northing isolation).
- **Isolation Forest Anomaly Rate:** `5.01% Outliers` (96 anomalies identified among 1,917 real Pune footprints).
- **Image Quality CNN:** `99.00% Test Accuracy` on synthetic PIL image degradations with tile-separated splits.

### 8. Which metrics must NOT be presented to judges as real-world production performance?
- **DO NOT PRESENT:**
  - `100.00%` on Boundary Reliability AI (circular label artifact).
  - `100.00%` on GIS Conflict AI (synthetic rule artifact).
  - `100.00%` on Parcel Plausibility AI (synthetic anomaly artifact).
  - `100.00%` on Confidence AI (synthetic calibration artifact).
  - `100.00%` on Siamese Change Detection AI (distinct patch artifact).
  - Any historical unverified claims of `51.84% / 68.28%` for road extraction or `84.12%` for LULC.

### 9. Which models still need serious, large-scale training?
- **Model A & Model B:** Need high-epoch multi-hour training with CUDA acceleration on larger real drone datasets if GPU PyTorch is enabled.
- **Boundary Reliability AI:** Needs real boundary annotations where ground truth fences/hedges/curbs are verified by licensed surveyors, not synthetic random line crosscuts.
- **Siamese Change AI:** Needs genuine multi-temporal orthoimagery pairs depicting actual historical parcel subdivisions or structural construction in India.
- **Model C LULC:** Needs genuine multispectral imagery (Sentinel-2, Planet, or drone multispectral) rather than polygon morphology alone.

### 10. Is the RTX 4050 actually being used?
- **NO.** PyTorch is `2.14.0+cpu`. `torch.cuda.is_available()` returns `False`. The physical RTX 4050 GPU was **completely idle** throughout all past and current training sessions.
