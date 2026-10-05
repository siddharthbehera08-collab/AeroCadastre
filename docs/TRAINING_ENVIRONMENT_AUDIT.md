# AeroCadastre SIH26012 — Training Hardware & Environment Audit

**Date:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Host Platform:** Windows (x86_64)  
**Python Runtime:** Python 3.12.10 (`C:\Users\LENOVO\AppData\Local\Programs\Python\Python312\python.exe`)

---

## 1. Hardware Inventory

| Component | Detected Specification | AeroCadastre Status / Impact |
|---|---|---|
| **Host CPU** | 20 Logical Cores (Intel 13th/14th Gen Hybrid Architecture) | High multi-threaded throughput. Excellent for parallel scikit-learn / LightGBM / XGBoost multi-seed hyperparameter searches and multi-worker raster operations. |
| **System Memory (RAM)** | ~24.87 GB Total (~9.68 GB free physical) | Sufficient for in-memory raster caching, spatial STRtrees, and tabular feature matrices. |
| **Storage (D: Drive)** | `124.08 GB` Free Disk Space | Abundant space for checkpoints, evaluation metrics, logs, and patch caches. All training outputs are stored strictly on `D:`. |
| **Physical GPU** | **NVIDIA GeForce RTX 4050 Laptop GPU** (6,141 MiB VRAM, Driver 596.49, CUDA capability up to 13.2) | Physically installed and idle. |
| **PyTorch Distribution** | **`2.14.0+cpu`** (`torch.cuda.is_available() == False`) | The installed PyTorch wheel in the global Python environment is CPU-only. GPU is physically present on host, but torch calls execute via multi-threaded CPU SIMD instructions (AVX2/AVX-512) unless a CUDA-compiled wheel is linked. |

---

## 2. Deep Learning vs Tabular ML Resource Strategy

### 2.1 Deep Learning (PyTorch CNNs: ResUNet, UNet, Image Quality CNN, Siamese Change Net)
- **Batch Size Optimization:** In CPU mode, excessive batch sizes introduce memory bandwidth thrashing. Recommended batch size: `8` to `16` with `num_workers=0` (to avoid Windows multiprocessing IPC overhead).
- **Inference Optimization:** Inference on test patches utilizes PyTorch JIT and `torch.inference_mode()` with multi-threaded intra-op parallelism (`torch.set_num_threads(8)`).
- **Historical Benchmark Integrity:** Checkpoints for Model A (`EXP_BUILDING_RESUNET_001`, Val IoU 46.42%) and Model B (`EXP_ROAD_RESUNET_001`, Val IoU 23.16%) were trained and evaluated on authoritative benchmark splits (Inria Aerial and SpaceNet 3 Paris).

### 2.2 Tabular & Morphology ML (Scikit-Learn, LightGBM, XGBoost)
- **Parallelization:** Thread pool configured with `n_jobs=-1` (or `n_jobs=8` to avoid CPU thermal throttling).
- **Hyperparameter Tuning:** Grid / randomized cross-validation searches across 20+ parameter combinations over multiple random seeds (e.g., seeds `42`, `101`, `2024`) to guarantee statistical significance and report Mean ± Std metrics.

---

## 3. Real Indian Optical Imagery Blocker Status
- **Status:** `INDIAN_IMAGERY_STATUS = MISSING`
- **Impact:** Pune study area high-resolution drone/aerial optical imagery is missing. All Pune-specific cadastral polygon generation remains classified under the Pre-Cadastre Legal Governance Standard (`INFERRED PARCEL BOUNDARY`, `NOT_ASSIGNED_PRE_CADASTRE`).
- **Data Integrity:** No synthetic or fake real Pune optical imagery is manufactured. Real benchmarks (Inria, SpaceNet, Mumbai LULC, Pune reference geometries) serve as the foundation for all trained models.
