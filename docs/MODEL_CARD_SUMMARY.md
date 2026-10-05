# AeroCadastre SIH26012 — Model Card Summary
**Status Date:** 2026-10-04  
**Framework Version:** AeroCadastre Core v2.0  

---

## 1. Model Overview Table

| Model ID | Task / Purpose | Architecture / Backbone | Training Data | Primary Reconciled Metrics | Classification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Model A** | Building Footprint Detection | ResUNet (ResNet-34 + U-Net) | Inria Aerial Image Labeling | Val IoU: `0.4642`, Val Dice: `0.6341`, Precision: `0.6119`, Recall: `0.6579` | **BENCHMARK_CHAMPION** | TRAINED_AND_INTEGRATED |
| **Model B** | Road Network Extraction | RoadResUNet | SpaceNet 3 (Paris urban scenes) | Val IoU: `0.2316`, Val Dice: `0.3760`<br>Test IoU: `0.1955`, Test Dice: `0.3270`, Test Pixel Acc: `0.9360` | **BENCHMARK_CHAMPION** | TRAINED_AND_INTEGRATED |
| **Model C** | Supplementary Urban LULC | XGBoost Classifier (Champion) | World Bank Mumbai ESA EO4SD LULC | Val Acc: `0.5317`, Val Macro F1: `0.3323`<br>Test Acc: `0.4906`, Test Macro F1: `0.3203` | **SUPPLEMENTARY_EXPERIMENT** | TRAINED_AND_INTEGRATED |
| **Model D** | Topographic & Slope Analysis | Deterministic Gradient Engine | Pune SRTM / Cartosat Elevation Rasters | 704 cells evaluated across EPSG:32643 common grid | **OPERATIONAL_ANALYTICS** | DETERMINISTIC_OPERATIONAL |
| **Boundary Evidence** | Boundary Probability Scoring | Edge-Aware ResUNet Specification | Optical + Building + Road Cues | Synthetic validation contract verified | **INFRASTRUCTURE_READY** | BLOCKED_BY_AUTHENTIC_PARCEL_LABELS |
| **Model E** | Multi-Source Spatial Fusion | Multi-Domain Bayesian Evidence Engine | Multi-Modal raster & vector inputs | Dynamic weight renormalization (8 edge cases) | **OPERATIONAL_ENGINE** | DETERMINISTIC_OPERATIONAL |
| **Model F** | Parcel Inference & Planarization | Planar Voronoi / Delaunay & Ring Extractor | Fused boundary network edges | Metric area, compactness, sliver filter active | **OPERATIONAL_ENGINE** | DETERMINISTIC_OPERATIONAL |
| **Model G** | Topology Validation & Repair | Computational Geometry Validator | Inferred candidate polygons | Polsby-Popper, gaps, overlaps, self-intersections | **OPERATIONAL_VALIDATOR** | DETERMINISTIC_OPERATIONAL |
| **Boundary Reliability** | Boundary Segment Verification | LightGBM Classifier (Champion) | Pune Reference Buildings & Roads | Val Acc: `0.9804`, Val F1: `0.9805`<br>Test Acc: `0.9755`, Test F1: `0.9758` | **SPECIALIST_AI_MODEL** | TRAINED_AND_INTEGRATED |
| **GIS Conflict AI** | Cross-Layer Spatial Conflict Detection | RandomForest Classifier (Champion) | Pune Reference Layers & Spatial Buffers | Val Acc: `1.0000`, Val Macro F1: `1.0000`<br>Test Acc: `1.0000`, Test Macro F1: `1.0000` | **SPECIALIST_AI_MODEL** | TRAINED_AND_INTEGRATED |
| **Anomaly Discovery** | Unsupervised Morphology Anomaly Detection | Isolation Forest (100 trees, contam=0.05) | Pune Reference Buildings (1,917 polygons) | 96 anomalies flagged (5.01%), score: -0.1876 to 0.2195 | **SPECIALIST_AI_MODEL** | TRAINED_AND_INTEGRATED |
| **Parcel Plausibility** | Urban Morphology Plausibility Scoring | RandomForest Classifier (Champion) | Pune Reference Geometries + Negatives | Val Acc: `1.0000`, Val F1: `1.0000`<br>Test Acc: `1.0000`, Test F1: `1.0000` | **SPECIALIST_AI_MODEL** | TRAINED_AND_INTEGRATED |
| **Confidence AI** | Multi-Criteria Evidence Confidence | RandomForest Classifier (Champion) | Multi-Criteria Evidence Scenarios | Val Acc: `1.0000`, Val Macro F1: `1.0000`<br>Test Acc: `1.0000`, Test Macro F1: `1.0000` | **SPECIALIST_AI_MODEL** | TRAINED_AND_INTEGRATED |
| **Image Quality AI** | Radiometric Quality Assessment | 3-stage PyTorch ConvNet (Champion) | Inria Aerial Patches (Degraded Augmentation) | Val Acc: `1.0000`<br>Test Acc: `0.9900`, Test F1: `0.9899` | **SPECIALIST_AI_MODEL** | TRAINED_AND_INTEGRATED |
| **Model I (Change)** | Multi-Temporal Change Detection | PyTorch SiameseConvNet (Champion) | Inria Temporal Pairs Simulation | Val Acc: `0.9800`<br>Test Acc: `1.0000`, Test F1: `1.0000` | **EXPERIMENTAL_POC** | SUPPLEMENTARY_ONLY |
| **AI Council Fusion** | Multi-Agent Advisory Consensus Engine | 6 Autonomous Specialist Agents | Multi-Modal candidate parcel evidence | Precedence consensus (Geometry > Conflict > Vision) | **ORCHESTRATION_ENGINE** | OPERATIONAL_ENGINE |

---

## 2. Ethical and Intended Use

### Intended Use:
- Assisting cadastral survey departments in prioritizing field demarcation visits.
- Generating preliminary candidate boundary hypotheses (`CANDIDATE_PARCEL`).
- Detecting potential spatial discrepancies and geometry errors before land-record digitization.

### Out of Scope / Prohibited Use:
- Generating binding, statutory property titles or deeds.
- Determining legal ownership, tenancy, or financial encumbrances.
- Assigning official statutory ULPIN (Bhu-Aadhaar) identifiers without competent state revenue authority approval.
