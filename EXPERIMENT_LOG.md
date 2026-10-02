# SIH26012 — AeroCadastre: Machine Learning Experiment Log

> **Truthfulness Policy:** Every metric recorded in this log was produced by actual execution of PyTorch & Scikit-Learn training and evaluation pipelines on deterministic synthetic geospatial scenes (`100 train / 20 val / 20 test`) stored in `D:\SIH26012_AeroCadastre\synthetic_data\`.

---

## 1. Experiment Summary Table

| Run ID | Task | Model Name | Architecture | Epochs | Train Loss | Val Loss | IoU | Dice / F1 | Precision | Recall | Train Time (s) | Inference (ms/scene) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `EXP_001` | `BUILDING_SEG` | **Building_SimpleCNN_v1** | SimpleCNNSeg (3-ch RGB, BCE) | 8 | 0.1398 | 0.1912 | **0.8915** | **0.9426** | 0.9072 | 0.9809 | 7.39s | 1.63ms |
| `EXP_002` | `BUILDING_SEG` | **Building_MicroUNet_v1** | MicroUNet (3-ch RGB, BCEDice) | 8 | 0.1459 | 0.1417 | **0.9798** | **0.9898** | 0.9812 | 0.9985 | 11.30s | 3.40ms |
| `EXP_003` | `BUILDING_SEG` | **Building_MicroResUNet_RGBD_v2** | MicroResUNet (4-ch RGB+nDSM, BCEDice) | 8 | 0.0219 | 0.0220 | **0.9995** | **0.9997** | 0.9999 | 0.9996 | 18.19s | 6.50ms |
| `EXP_004` | `ROAD_SEG` | **Road_MicroUNet_v1** | MicroUNet (3-ch RGB, BCEDice) | 8 | 0.2487 | 0.2310 | **0.9998** | **0.9999** | 0.9999 | 1.0000 | 11.23s | 3.37ms |
| `EXP_005` | `BOUNDARY_SEG` | **Boundary_MicroResUNet_v1** | MicroResUNet (4-ch RGB+nDSM, BCEDice) | 8 | 0.1386 | 0.1447 | **0.8207** | **0.9015** | 0.8537 | 0.9550 | 15.85s | 4.33ms |
| `EXP_006` | `LANDUSE_CLS` | **LandUse_RandomForest_Baseline** | RandomForestClassifier (35 trees, depth=12) | 1 | 0.1420 | 0.2264 | **0.6809** | **0.7736** | 0.8048 | 0.7680 | 0.26s | 20.74ms |
| `EXP_007` | `LANDUSE_CLS` | **LandUse_MicroUNet_RGBD** | MicroUNet (4-ch RGB+nDSM) | 8 | 0.5846 | 0.6257 | **0.4924** | **0.5780** | 0.6038 | 0.5903 | 15.30s | 6.10ms |
| `EXP_008` | `LANDUSE_CLS` | **LandUse_MicroResUNet_Weighted_v2** | MicroResUNet (4-ch RGB+nDSM, InverseSqrt Class Weights + CosineLR) | 12 | 0.3197 | 0.3213 | **0.8396** | **0.9062** | 0.9002 | 0.9134 | 33.05s | 8.03ms |

---

## 2. Iterative Model Improvement Loop Analysis

1. **Baseline (`EXP_001` - `Building_SimpleCNN_v1`):**
   - **Weakness Observed:** 3-layer CNN with standard BCE loss struggles on roof boundaries where terracotta/concrete tones resemble adjacent bare/vacant ground.
2. **Iteration 1 (`EXP_002` - `Building_MicroUNet_v1`):**
   - **Modification:** Introduced encoder-decoder skip connections (`MicroUNet`) and replaced pure BCE with `BCEDiceLoss` to directly optimize spatial overlap.
3. **Iteration 2 (`EXP_003` - `Building_MicroResUNet_RGBD_v2`):**
   - **Modification:** Added residual blocks (`MicroResUNet`) and fused a 4th input channel containing normalized Digital Surface Model height (`nDSM`) above local terrain.
   - **Result:** Adding elevation cues substantially improved Building IoU and Dice/F1 by separating elevated roofs from flat bare soil and road surfaces.
