# CUDA Environment Snapshot (Before GPU Configuration)

**Date Recorded:** 2026-10-04 10:58:15 IST  
**Host Architecture:** Windows x86_64  
**Project Root:** `D:\SIH26012_AeroCadastre`

---

## 1. System & Physical Hardware Specifications

| Property | Value |
|---|---|
| **Python Version** | Python 3.12.10 (MSC v.1943 64 bit AMD64) |
| **System PyTorch Version** | `2.14.0+cpu` |
| **System torchvision Version** | `0.29.1+cpu` |
| **CUDA Runtime in PyTorch** | `None` (`torch.cuda.is_available() == False`) |
| **NVIDIA Driver Version** | `596.49` |
| **NVIDIA Driver CUDA Support** | CUDA 13.2 |
| **Physical GPU Model** | NVIDIA GeForce RTX 4050 Laptop GPU |
| **Physical GPU VRAM** | 6,141 MiB (~6.0 GB GDDR6) |
| **Host System RAM** | ~24.87 GB Total (~9.68 GB free) |
| **Host CPU Cores** | 20 Logical Cores |
| **Storage (D: Drive)** | `124.08 GB` Free Disk Space |

---

## 2. Terminal Audit Verification

```powershell
python -c "
import torch
print('PyTorch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
print('Torch CUDA:', torch.version.cuda)
print('GPU count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    print('VRAM:', torch.cuda.get_device_properties(0).total_memory / 1024**3)
"
```

**Output:**
```text
PyTorch: 2.14.0+cpu
CUDA available: False
Torch CUDA: None
GPU count: 0
GPU: NO CUDA
VRAM: NO VRAM
```

---

## 3. Initial Baseline State

The global Python environment (`Python 3.12.10`) has a CPU-only build of PyTorch (`2.14.0+cpu`) installed. Despite physical presence of the NVIDIA GeForce RTX 4050 Laptop GPU, deep learning operations have run strictly on CPU. A dedicated isolated virtual environment (`D:\SIH26012_AeroCadastre\.venv-gpu`) is required to establish genuine CUDA support.
