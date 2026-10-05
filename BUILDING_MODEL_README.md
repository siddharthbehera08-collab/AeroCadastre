# AeroCadastre — AI Building Footprint Extraction Subsystem
### SIH26012: AI-Based Automated Urban Parcel Mapping and Cadastral Feature Extraction System

---

## 1. Primary Objective

The Building Detection AI subsystem is an evidentiary feature extraction engine engineered to automatically segment building footprints from high-resolution aerial and drone imagery.

The core transformation pipeline operates as follows:
```
Raw Aerial / UAV Imagery (0.3m GSD GeoTIFF / RGB)
  │
  ▼
Tile Normalization & Windowing (256x256 / 512x512)
  │
  ▼
Deep Neural Network (UNetBaseline / ResUNet)
  │
  ▼
Continuous Building Probability Map [0.0, 1.0]
  │
  ▼
Calibrated Thresholding (Binary Mask)
  │
  ▼
Deterministic Polygon Extraction & Repair (OpenCV + Shapely)
  │
  ▼
GIS-Ready GeoJSON / Shapefile with Verified CRS & Spatial Metadata
  │
  ▼
Evidence Layer Ingestion into AeroCadastre AI Council & Surveyor Verification Portal
```

---

## 2. Dataset & Verified Statistics

The model is trained and validated on the **Inria Aerial Image Labeling Benchmark**, representing diverse global urban and rural topographies:
- **Austin, Texas:** Dense urban commercial and suburban residential grids.
- **Chicago, Illinois:** High-density urban grid with narrow setbacks, alleys, and skyscraper shadows.
- **Kitsap County, Washington:** Low-density rural and heavily forested small structures.
- **Western Tyrol, Austria:** Alpine rural villages with severe topographic shadows and varied roof pitches.
- **Vienna, Austria:** Historic European high-density core with complex shared rooftops.

### Audited Dataset Metrics
- **Total Training Tiles:** 180 tiles (5000 × 5000 pixels each at 0.3m GSD, covering 1.5 km × 1.5 km per tile).
- **Total Matched Pairs:** 180 / 180 (100% matched, 0 corrupted, 0 missing).
- **Total Test Tiles:** 180 tiles.
- **Total Surface Area Inspected:** 810 km² of high-resolution aerial imagery.
- **Global Class Distribution:**
  - Foreground (Building Pixels): **15.30%**
  - Background (Non-building): **84.70%**
  - Severe Class Imbalance Ratio: **1 : 5.54**
- **Optical Statistics:**
  - Mean RGB: `[0.4012, 0.4220, 0.3884]`
  - Standard Deviation RGB: `[0.1973, 0.1808, 0.1739]`

---

## 3. Strict Geographic Data Splitting Protocol

To eliminate spatial auto-correlation and prevent spatial leakage:
- **Validation Set (14%):** Tiles `01` to `05` across all 5 cities (25 tiles total).
- **Untouched Test Set (14%):** Tiles `06` to `10` across all 5 cities (25 tiles total).
- **Training Set (72%):** Tiles `11` to `36` across all 5 cities (130 tiles total).

> [!IMPORTANT]
> The test set remains strictly quarantined until final model selection. Zero hyperparameters, learning rates, or early stopping decisions are tuned against test data.

---

## 4. Architectures & Loss Formulations

### Architecture 1: Compact U-Net Baseline (`UNetBaseline`)
- **Encoder:** 4 downscaling stages with DoubleConv (Conv3x3 -> BN -> ReLU) and MaxPool2d(2).
- **Base Features:** 32 feature channels at Stage 1, scaling up to 512 at the bottleneck.
- **Decoder:** 4 upscaling stages using Transposed Convolutions and skip connection concatenation.
- **Head:** 1x1 Conv with 1-channel logit output.
- **Total Parameters:** ~7.76 Million.

### Architecture 2: Residual U-Net (`ResUNet`)
- **Encoder:** Residual convolutional blocks with identity shortcuts and 1x1 projection shortcuts to maintain high-frequency boundary gradients.
- **Decoder:** Residual blocks on concatenated skip features for sharp corner delineation.
- **Total Parameters:** ~8.15 Million.

### Loss Functions
1. **Hybrid BCE + Soft Dice Loss (`BCEDiceLoss`):**
   $$\mathcal{L} = w_{\text{bce}} \cdot \mathcal{L}_{\text{BCEWithLogits}} + (1 - w_{\text{bce}}) \cdot \left(1 - \frac{2 |P \cap T| + \epsilon}{|P| + |T| + \epsilon}\right)$$
2. **Focal + Soft Dice Loss (`FocalDiceLoss`):**
   Applies modulating factor $\alpha (1 - p_t)^\gamma$ to down-weight easy background examples and force optimization onto ambiguous boundary pixels.

---

## 5. Evaluation Metrics & Measured Results

| Metric | Baseline UNet (`EXP_001`) | Enhanced Aug UNet (`EXP_002`) | FocalDice UNet (`EXP_003`) | ResUNet (`RESUNET_001`) |
|---|---|---|---|---|
| **Architecture** | UNetBaseline | UNetBaseline | UNetBaseline | ResUNet |
| **Loss** | BCEDice (0.5/0.5) | BCEDice (0.5/0.5) | FocalDice ($\gamma=2.0$) | BCEDice (0.5/0.5) |
| **Augmentation** | Flips | Flips + D4 Rot + Jitter | Flips + D4 Rot + Jitter | Flips + D4 Rot + Jitter |
| **Val IoU** | Measured in report | Measured in report | Measured in report | Measured in report |
| **Val Dice (F1)** | Measured in report | Measured in report | Measured in report | Measured in report |
| **Boundary F1** | Measured in report | Measured in report | Measured in report | Measured in report |
| **Pixel Acc** | Measured in report | Measured in report | Measured in report | Measured in report |

---

## 6. Deterministic Polygonization & GIS Export

The model output is deterministically post-processed:
1. Probability map thresholded at calibrated $\tau = 0.5$.
2. Connected contour hierarchy extraction via OpenCV `findContours(RETR_CCOMP)`.
3. Holes and outer shells constructed into Shapely `Polygon` objects.
4. Topological repair via `shapely.validation.make_valid()`.
5. Area filtering: Discard noise artifacts $< 15.0 \text{ m}^2$.
6. Simplification via Douglas-Peucker ($\epsilon = 1.0$) preserving planar topology.
7. Export to GeoJSON FeatureCollection with SRS geotransform.

---

## 7. CLI Inference Instructions

Run end-to-end inference on any aerial GeoTIFF or image:
```bash
python infer_buildings.py \
    --image path/to/aerial_orthophoto.tif \
    --checkpoint experiments/building_detection/EXP_BUILDING_RESUNET_001/checkpoints/best_model.pt \
    --output experiments/building_detection/predictions/demo_output \
    --threshold 0.5 \
    --patch-size 256 \
    --stride 192
```

Outputs generated:
- `<image_stem>_probability.png`: Continuous probability map $[0, 255]$.
- `<image_stem>_binary_mask.png`: Binary classification mask.
- `<image_stem>_footprints.geojson`: Validated building polygon features with CRS metadata.
- `<image_stem>_inference_metadata.json`: Full provenance audit log.

---

## 8. Cadastral Boundary vs. Building Footprint Disclaimer

> [!CAUTION]
> **Statutory Limitation:**
> In accordance with Indian Land Administration standards (e.g. Survey of India, SVAMITVA Scheme),
> building footprints generated by this AI model **DO NOT** constitute legal cadastral parcel boundaries.
> Physical footprints serve as high-confidence spatial evidence to assist licensed cadastral surveyors.
> Final boundaries must integrate revenue records, boundary walls, GNSS ground truth, and surveyor field verification.
