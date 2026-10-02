# SIH26012 — AeroCadastre: Machine Learning Pipeline (`ML_PIPELINE.md`)

## 1. Implemented Model Architectures (`backend/ml/architectures.py`)

1. **`SimpleCNNSeg` (`EXP_001`):** 3-layer fully convolutional baseline operating on 3-channel RGB imagery with Binary Cross-Entropy loss.
2. **`MicroUNet` (`EXP_002`, `EXP_004`, `EXP_007`):** Encoder-decoder U-Net with skip connections and `BCEDiceLoss` (hybrid Binary Cross-Entropy + Soft Dice Loss).
3. **`MicroResUNet` (`EXP_003`, `EXP_005`, `EXP_008`):** Residual U-Net taking 4-channel fused input (`RGB` + normalized `nDSM` height above local ground terrain).
4. **`RandomForestClassifier` (`EXP_006`):** Classical machine learning baseline using 8 features per pixel (`R, G, B, nDSM` + `5×5` spatial neighborhood mean).

## 2. Iterative Model Improvement Loop (`backend/ml/trainer.py`)

- **Building Segmentation Improvement:**
  - `EXP_001` (`SimpleCNNSeg`): Val IoU = `0.8915`, Dice = `0.9426`
  - `EXP_002` (`MicroUNet` + `BCEDiceLoss`): Val IoU = `0.9798`, Dice = `0.9898`
  - `EXP_003` (`MicroResUNet` + 4-ch `RGB+nDSM` fusion): Val IoU = **`0.9995`**, Dice = **`0.9997`**
- **Land-Use Classification Improvement:**
  - `EXP_007` (`MicroUNet` unweighted CrossEntropy): Val IoU = `0.4924`, Dice = `0.5780` (minority classes under-predicted)
  - `EXP_008` (`MicroResUNet` + inverse-sqrt class weights + CosineAnnealingLR): Val IoU = **`0.8396`**, Dice = **`0.9062`** (`+0.3472 IoU` improvement).
