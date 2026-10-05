# GPU Validation & Benchmarking Report

**Date:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Environment:** `D:\SIH26012_AeroCadastre\.venv-gpu`

---

## 1. Hardware & CUDA Runtime Verification

- **Host Device:** `NVIDIA GeForce RTX 4050 Laptop GPU`
- **Total Physical VRAM:** 5.996 GB (~6.00 GB GDDR6)
- **PyTorch Version:** `2.6.0+cu124`
- **CUDA Driver Runtime:** `12.4`
- **CUDA Device Count:** 1 (`cuda:0`)
- **Status:** **CUDA Verified Functional.**

---

## 2. Tensor Matrix Multiplication Benchmark (4096 × 4096 FP32)

Benchmark results executed via `experiments/gpu_validation/run_gpu_benchmark.py`:

| Parameter | CPU (Host Intel 20-core) | CUDA (`NVIDIA RTX 4050`) | Speedup / Delta |
|---|---|---|---|
| **Mean Execution Time** | **0.2370 s** | **0.0281 s** | **8.44x Faster on CUDA** |
| **Active Memory Allocated** | Host RAM | **200.12 MB** | Normal |
| **Peak Memory Allocated** | Host RAM | **264.12 MB** | Well within 6 GB VRAM budget |
| **Memory Reserved by Cache**| Host RAM | **278.00 MB** | Stable caching |

---

## 3. Verification Findings

1. `torch.cuda.is_available()` is confirmed `True`.
2. Hardware matrix multiplication executed on CUDA with proper stream synchronization (`torch.cuda.synchronize()`).
3. 8.44x computational speedup confirmed over multi-threaded CPU execution.
4. Active GPU memory allocation and memory release tracked without errors or leaks.
