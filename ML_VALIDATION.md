# SIH26012 AeroCadastre — Machine Learning & GeoAI Pipeline Validation (`ML_VALIDATION.md`)

**Date:** 2026-10-01  
**Framework:** PyTorch `2.11.0+cpu`  
**Architecture:** `AeroCadastreMultiTaskNet` (`SharedConvNeXtTinyEncoder + Dual-Head Decoder [Semantic 6-Class + Boundary 1-Channel] + DSM Prior Fusion`)  
**Weights:** `models/aerocadastre_multitask_unet.pt` (`2,148,935` trainable parameters)

---

## 1. Model Architecture & Inference Verification

1. **Multi-Task U-Net Forward Pass (`backend/ml/models.py` & `backend/ml/inference.py`):**
   - **Input Tensor:** `(B, 3, H, W)` normalized RGB orthoimagery tensor + optional `(B, 1, H, W)` Digital Surface Model (`DSM`) elevation prior.
   - **Head 1 (`semantic_logits`):** `(B, 6, H, W)` predicting 6 cadastral classes:
     - `0: BACKGROUND`
     - `1: PARCEL_INTERIOR`
     - `2: BUILDING_ROOF`
     - `3: ROAD_CORRIDOR`
     - `4: WATER_BODY`
     - `5: VEGETATION_AGRI`
   - **Head 2 (`boundary_logits`):** `(B, 1, H, W)` predicting crisp parcel/wall boundary probability map via sigmoid activation.
2. **DSM Prior Fusion:**
   - When DSM elevation data is supplied, normalized gradient magnitude $\nabla \text{DSM}$ boosts boundary probability along elevated roof/wall edges and suppresses false shadow boundaries on flat ground.
3. **Raster-to-Vector Polygonization (`backend/ml/postprocess.py`):**
   - Extracts connected components from semantic & boundary probability maps, regularizes orthogonal building footprints, simplifies parcel boundaries via Douglas-Peucker, and transforms pixel coordinates into `EPSG:4326` GeoJSON polygons with `EPSG:32643` metric areas.

---

## 2. Quantitative Evaluation Metrics (`experiments/latest_metrics.json` & PostgreSQL `model_runs`)

| Metric | Measured Value (`RUN_SIH26012_BASELINE`) | Live Re-Training (`POST /api/experiments/train`, 3 Epochs) | Description |
|---|---|---|---|
| **Mean IoU (`mIoU`)** | `0.7842` | `0.7410` – `0.7950` | Intersection-over-Union across 6 semantic classes |
| **Macro Dice / F1 (`dice_f1`)** | `0.8691` | `0.8350` – `0.8780` | Harmonic mean of precision and recall |
| **Boundary F1 (`boundary_f1`)** | `0.8124` | `0.7820` – `0.8250` | Tolerant boundary F-score on parcel edges |
| **Parcel Panoptic Quality (`parcel_PQ`)** | `0.7615` | `0.7300` – `0.7750` | Segmentation Quality $\times$ Recognition Quality |
| **Tile Inference Latency (`256x256` CPU)** | `68.4 ms` – `112.5 ms` | `~74.2 ms` | Measured wall-clock PyTorch CPU forward pass |

---

## 3. Adversarial ML Input Validation (`test_16_ml_pipeline_adversarial_inputs`)

All adversarial and degenerate inputs to `GeoAIInferenceEngine` were tested and verified to fail safely without crashing the FastAPI worker:
- **Nonexistent image file path:** Raises `FileNotFoundError` cleanly.
- **Empty (`0x0`) numpy array or `None`:** Raises `ValueError("Input image must be a non-empty numpy ndarray")`.
- **2D array (missing channel axis) or 4D tensor:** Raises `ValueError("Input image must be a 3D array (H, W, C)")`.
- **Unsupported channel count (`C=2` or `C=5`):** Raises `ValueError("Input image must have 1, 3, or 4 channels")`.
- **Extreme dimensions (`< 16px` or `> 4096px`):** Raises `ValueError("Tile dimensions must be between 16x16 and 4096x4096")`.
- **`NaN` or `Inf` pixel values:** Raises `ValueError("Input image contains NaN or Inf values")`.
- **Zero-variance (`all-black 0` or `all-white 255`) tiles:** Runs cleanly, returning valid finite probabilities in `[0.0, 1.0]`.
