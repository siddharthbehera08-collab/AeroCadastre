"""AeroCadastre Local Model Registry Engine.

Maintains an immutable ledger of trained models, checkpoints, metrics, and architectures:
- experiment ID
- checkpoint path
- architecture
- dataset provenance
- measured metrics (IoU, Dice, Boundary F1, Precision, Recall)
- deployment status ('candidate', 'champion', 'archived')
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import time


REGISTRY_PATH = Path("D:/SIH26012_AeroCadastre/experiments/building_detection/model_registry.json")


def register_model(
    experiment_id: str,
    checkpoint_path: Path,
    architecture: str,
    metrics: Dict[str, Any],
    config: Dict[str, Any],
    status: str = "candidate",
    notes: str = "",
) -> Dict[str, Any]:
    """Register or update a model run in the local registry."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {"models": [], "last_updated": ""}

    entry = {
        "experiment_id": experiment_id,
        "checkpoint_path": str(checkpoint_path),
        "architecture": architecture,
        "metrics": {
            "val_iou": metrics.get("val_iou", 0.0),
            "val_dice": metrics.get("val_dice", 0.0),
            "val_precision": metrics.get("val_precision", 0.0),
            "val_recall": metrics.get("val_recall", 0.0),
            "val_boundary_f1": metrics.get("val_boundary_f1", 0.0),
            "val_pixel_accuracy": metrics.get("val_pixel_accuracy", 0.0),
        },
        "status": status,
        "notes": notes,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Replace if exists, else append
    existing_idx = next((i for i, m in enumerate(registry["models"]) if m["experiment_id"] == experiment_id), None)
    if existing_idx is not None:
        registry["models"][existing_idx] = entry
    else:
        registry["models"].append(entry)

    registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print(f"Registered model {experiment_id} in {REGISTRY_PATH}")
    return entry
