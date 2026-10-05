# AeroCadastre SIH26012 — GPU Training Infrastructure & Readiness Master Report

**Date:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Dedicated GPU Environment:** `D:\SIH26012_AeroCadastre\.venv-gpu`  
**Host Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (6,141 MiB GDDR6 VRAM, Driver 596.49)

---

## 1. Executive Summary & Verification Findings

In response to the forensic audit, this mission has successfully established, benchmarked, and validated a dedicated CUDA-enabled PyTorch environment for genuine GPU training. 

### Core Milestones Achieved:
1. **Isolated GPU Environment Created on D: Drive:**  
   - Dedicated environment established at `D:\SIH26012_AeroCadastre\.venv-gpu` to preserve system C: drive capacity.
   - Installed official CUDA 12.4 PyTorch binaries: `torch==2.6.0+cu124` and `torchvision==0.21.0+cu124`.
2. **CUDA Availability Confirmed:**  
   - `torch.cuda.is_available() == True`  
   - `torch.cuda.get_device_name(0) == "NVIDIA GeForce RTX 4050 Laptop GPU"`  
   - Detected VRAM: `5.996 GB` (~6.00 GB).
3. **GPU vs CPU Mathematical Benchmark Completed:**  
   - 4096 × 4096 FP32 matrix multiplication evaluated with stream synchronization (`torch.cuda.synchronize()`).
   - CPU Time: `0.2370 s` vs CUDA Time: `0.0281 s` (**8.44x computational speedup**).
4. **Actual AeroCadastre CNN Architectures Verified on CUDA:**  
   - Model A (`ResUNet`) and Model B (`RoadResUNet`) instantiated and tested through full forward, loss, backward, and optimizer step on CUDA.
   - All parameters, loss tensors, and gradients verified as native CUDA tensors.
   - Zero CPU fallback.
5. **VRAM Scaling & Memory Budget Characterized:**  
   - Tested batch sizes 2, 4, 8, 16.
   - At batch size 16 (256×256 inputs), peak VRAM was **1,790.4 MB** (~1.79 GB), well below the 6.0 GB physical VRAM ceiling. Safe training headroom confirmed.
6. **DataLoader Throughput Optimized for Windows:**  
   - `num_workers=0` with `pin_memory=True` achieved **154.3 samples/sec** (compared to 18.0 samples/sec with multi-worker IPC overhead on Windows).
7. **End-to-End Pipeline Dry Run (Smoke Test) Passed:**  
   - 1 real epoch executed on Inria patch subset with automatic mixed precision (`torch.amp.autocast('cuda')`, `GradScaler`).
   - Forward, loss, backward, optimizer step, validation loop, IoU calculation, and checkpoint persistence confirmed (`experiments/gpu_validation/smoke_test/smoke_test_model.pt`).
8. **Anti-Fabrication & Metric Integrity Preserved:**  
   - Historical champion checkpoints and canonical metrics (`Model A Test IoU 42.58%`, `Model B Test IoU 19.55%`) remain intact and untouched.
   - No models were falsely claimed as retrained.

---

## 2. Environment Comparison (Before vs After)

| Component | Baseline Environment (`python`) | Dedicated GPU Environment (`.venv-gpu\Scripts\python.exe`) |
|---|---|---|
| **Python Version** | 3.12.10 | 3.12.10 |
| **PyTorch Build** | `2.14.0+cpu` | **`2.6.0+cu124`** |
| **CUDA Runtime** | None | **12.4** |
| **CUDA Available** | `False` | **`True`** |
| **Device Name** | None | **NVIDIA GeForce RTX 4050 Laptop GPU** |
| **Physical VRAM** | Idle (0 MiB used) | **5.996 GB (~6.00 GB)** |
| **Execution Path** | Host CPU (AVX2/AVX-512) | **NVIDIA Ampere/Ada Tensor Cores (cuda:0)** |

---

## 3. Mathematical Benchmark & CNN Memory Audit

### 3.1 4096 × 4096 FP32 Tensor Benchmark (`experiments/gpu_validation/gpu_benchmark.json`)
- **CPU Time (5 trials):** 0.2370 s
- **CUDA Time (5 trials):** 0.0281 s
- **Speedup Factor:** **8.44x**
- **CUDA Memory Allocated:** 200.12 MB
- **CUDA Peak Memory:** 264.12 MB

### 3.2 Model A (`ResUNet`) & Model B (`RoadResUNet`) Scaling on CUDA (`experiments/gpu_validation/cnn_gpu_validation.json`)

| Architecture | Batch Size | Forward Time | Backward Time | Peak VRAM | Reserved VRAM | OOM Status |
|---|---|---|---|---|---|---|
| **Model A ResUNet** | 2 | 760.87 ms (warmup) | 283.77 ms | 230.1 MB | 318.0 MB | No |
| **Model A ResUNet** | 4 | 69.29 ms | 76.46 ms | 472.8 MB | 686.0 MB | No |
| **Model A ResUNet** | 8 | 79.43 ms | 138.89 ms | 912.4 MB | 1,230.0 MB | No |
| **Model A ResUNet** | 16 | 134.71 ms | 253.87 ms | **1,790.4 MB** | **2,380.0 MB** | No |
| **Model B RoadResUNet** | 2 | 21.93 ms | 31.20 ms | 230.1 MB | 292.0 MB | No |
| **Model B RoadResUNet** | 4 | 25.36 ms | 60.58 ms | 467.9 MB | 652.0 MB | No |
| **Model B RoadResUNet** | 8 | 49.64 ms | 126.27 ms | 907.6 MB | 1,158.0 MB | No |
| **Model B RoadResUNet** | 16 | 133.34 ms | 252.51 ms | **1,788.0 MB** | **2,260.0 MB** | No |

**Conclusion on Batch Size:** Batch size **16** requires only ~1.79 GB of active VRAM (and ~2.38 GB reserved cache), providing over 3.6 GB of headroom on the RTX 4050. It is selected as the production training batch size.

---

## 4. Production Training Configurations Prepared

Two production-ready training configuration files have been authored:
1. [`configs/training/model_a_gpu.yaml`](file:///D:/SIH26012_AeroCadastre/configs/training/model_a_gpu.yaml)
   - Architecture: `ResUNet` (16 base channels)
   - Device: `cuda:0` with AMP (`torch.amp.autocast('cuda')`)
   - Batch size: `16`, `num_workers: 0`, `pin_memory: true`
   - Loss: `BCEDiceLoss` (bce_weight: 0.5)
   - Optimizer: `AdamW` (lr: 1e-3, weight_decay: 1e-4)
   - Scheduler: `CosineAnnealingLR` (T_max: 80, eta_min: 1e-5)
   - Early stopping: Patience 15 epochs
2. [`configs/training/model_b_gpu.yaml`](file:///D:/SIH26012_AeroCadastre/configs/training/model_b_gpu.yaml)
   - Architecture: `RoadResUNet` (16 base channels)
   - Device: `cuda:0` with AMP
   - Batch size: `16`, `num_workers: 0`, `pin_memory: true`
   - Loss: `BCEDiceLoss` (bce_weight: 0.4)
   - Optimizer: `AdamW` (lr: 1e-3, weight_decay: 1e-4)
   - Scheduler: `CosineAnnealingLR`
   - Early stopping: Patience 15 epochs

---

## 5. Regression Test Verification

Ran standard regression test suite:
- Command: `python -m pytest tests/ -q`
- Result: **132 passed, 8 skipped, 4 warnings in 17.49s**
- Status: **Zero test regressions.**

---

## 6. Ready State for Genuine GPU Training

All pre-conditions for genuine GPU training are now met:
- [x] CUDA 12.4 installed and verified with PyTorch 2.6.0.
- [x] RTX 4050 GPU confirmed functional with an 8.44x speedup.
- [x] ResUNet & RoadResUNet forward/backward verified on CUDA.
- [x] VRAM headroom confirmed (batch size 16 uses <2 GB of 6 GB).
- [x] DataLoader throughput verified (154.3 samples/sec).
- [x] Smoke test dry run completed with AMP and checkpointing.
- [x] Production configurations created in `configs/training/`.
- [x] Anti-fabrication rules strictly maintained.
