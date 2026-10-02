# SIH26012 — AeroCadastre: Limitations & Future Real-Dataset Readiness

## 1. Honest Current Prototype Limitations (`LIMITATIONS.md`)

1. **Synthetic Data Source:** All imagery, DSM/DTM rasters, and reference parcels in this autonomous build are deterministically generated (`SYNTHETIC DEMO DATA`). Real drone orthophotos have higher radiometric complexity, relief displacement, and shadow variation.
2. **CPU-Compact Neural Models:** Checkpoints (`EXP_001`..`EXP_008`) use compact encoder-decoder backbones (`SimpleCNNSeg`, `MicroUNet`, `MicroResUNet`) trained on CPU at `128×128` resolution. Production deployments on `0.05m–0.10m` GSD drone ortho-mosaics require tiled sliding-window inference (`512×512` / `1024×1024`) on GPU.
3. **Advisory Nature:** AI boundaries and AI Council recommendations are strictly decision-support tools for human surveyors and carry **zero legal authority**.
4. **Field Route Planner:** Uses Euclidean/metric UTM distance and 2-opt spatial clustering (`PROTOTYPE FIELD PLANNING TOOL - NOT NAVIGATION GRADE`), not live turn-by-turn street routing.

---

## 2. Plugging In Real Indian & International Datasets (`FUTURE_DATASETS.md`)

The ingestion (`backend/gis/ingestion.py`) and training (`backend/ml/trainer.py`) interfaces are dataset-agnostic so real datasets can be plugged in directly:
- **Survey of India / SVAMITVA / NAKSHA Urban Pilot Ortho-Rectified Imagery (ORI) & DSM/DTM:** Place tiled `.tif` and `.geojson`/`.shp` training pairs into `D:\SIH26012_AeroCadastre\data\` and run `backend.ml.trainer`.
- **Bhuvan / VEDAS / SpaceNet / Inria Building & Road Benchmarks:** Compatible with the 3-channel (`RGB`) and 4-channel (`RGB + nDSM`) tensor loaders.
- **GNSS / CORS Ground Control & Rover Observations:** Can be ingested via CSV/GeoJSON into the `boundaries` table with `boundary_type = "HUMAN_VERIFIED"`.
