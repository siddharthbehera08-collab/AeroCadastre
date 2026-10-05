"""AeroCadastre Experiment Tracker & Comparative Analysis Engine.

Collects metrics, parameters, and training logs across all building detection experiments:
- IoU, Dice, Precision, Recall, Boundary F1, Pixel Accuracy
- Parameter counts & model architecture specs
- Training convergence time & throughput
- Exports: experiment_comparison.csv and experiment_comparison.md
"""

from pathlib import Path
from typing import Dict, Any, List
import json
import csv
import torch


def count_parameters(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def generate_experiment_comparison(
    experiments_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """Aggregate all completed experiments in experiments_dir and produce comparison reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    exp_records = []

    # Search for all experiment directories
    for exp_path in sorted(list(experiments_dir.glob("EXP_*"))):
        if not exp_path.is_dir():
            continue

        metrics_file = exp_path / "metrics.json"
        metadata_file = exp_path / "model_metadata.json"

        if not metrics_file.exists():
            continue

        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)

        meta = {}
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

        history = metrics_data.get("history", [])
        if not history:
            continue

        # Find best validation epoch
        best_epoch_data = max(history, key=lambda x: x.get("val_iou", 0.0))

        record = {
            "experiment_id": exp_path.name,
            "architecture": meta.get("architecture", "Unknown"),
            "best_epoch": best_epoch_data.get("epoch", len(history)),
            "total_epochs": len(history),
            "train_loss": best_epoch_data.get("train_loss", 0.0),
            "val_loss": best_epoch_data.get("val_loss", 0.0),
            "val_iou": best_epoch_data.get("val_iou", 0.0),
            "val_dice": best_epoch_data.get("val_dice", 0.0),
            "val_precision": best_epoch_data.get("val_precision", 0.0),
            "val_recall": best_epoch_data.get("val_recall", 0.0),
            "val_boundary_f1": best_epoch_data.get("val_boundary_f1", 0.0),
            "val_pixel_accuracy": best_epoch_data.get("val_pixel_accuracy", 0.0),
            "training_time_sec": meta.get("total_training_time_sec", sum(h.get("duration_sec", 0) for h in history)),
        }
        exp_records.append(record)

    # Sort by Val IoU descending
    exp_records.sort(key=lambda x: x["val_iou"], reverse=True)

    # Save CSV
    csv_path = output_dir / "experiment_comparison.csv"
    if exp_records:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(exp_records[0].keys()))
            writer.writeheader()
            writer.writerows(exp_records)

    # Save Markdown report
    md_path = output_dir / "experiment_comparison.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# AeroCadastre — Building Detection Experiment Comparison Report\n\n")
        f.write("## 1. Overview of Controlled Model Iterations\n")
        f.write("Systematic architectural and loss investigations on the Inria Aerial Image Labeling Benchmark.\n\n")

        f.write("## 2. Comparative Metrics Table\n\n")
        f.write("| Experiment ID | Architecture | Best Epoch | Val Loss | Val IoU | Val Dice (F1) | Val Precision | Val Recall | Val Boundary F1 | Pixel Acc | Time (s) |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in exp_records:
            f.write(
                f"| `{r['experiment_id']}` | {r['architecture']} | {r['best_epoch']} | "
                f"{r['val_loss']:.4f} | **{r['val_iou']*100:.2f}%** | {r['val_dice']*100:.2f}% | "
                f"{r['val_precision']*100:.2f}% | {r['val_recall']*100:.2f}% | "
                f"**{r['val_boundary_f1']*100:.2f}%** | {r['val_pixel_accuracy']*100:.2f}% | "
                f"{r['training_time_sec']:.1f}s |\n"
            )
        f.write("\n")

        f.write("## 3. Analysis of Hypotheses and Results\n")
        f.write("- **EXP_BUILDING_UNET_001 (Baseline):** Establishes reference segmentation with standard BCE + Dice loss.\n")
        f.write("- **EXP_BUILDING_UNET_002 (Enhanced Augmentation):** Introduces D4 rotations and photometric jitter to improve generalization across varied illumination.\n")
        f.write("- **EXP_BUILDING_UNET_003 (Focal + Dice Loss):** Applies hard-mining focal weighting to combat background class dominance and emphasize boundary pixels.\n")
        f.write("- **EXP_BUILDING_RESUNET_001 (Residual U-Net):** Employs deep residual blocks to maintain high-frequency corner/boundary fidelity.\n\n")

        if exp_records:
            best_exp = exp_records[0]
            f.write("## 4. Final Model Selection Decision\n")
            f.write(f"The best performing model according to measured Validation IoU and Boundary F1 is **`{best_exp['experiment_id']}`** ")
            f.write(f"({best_exp['architecture']}) achieving **{best_exp['val_iou']*100:.2f}% IoU**, **{best_exp['val_dice']*100:.2f}% Dice**, ")
            f.write(f"and **{best_exp['val_boundary_f1']*100:.2f}% Boundary F1**.\n")

    print(f"Comparison report generated with {len(exp_records)} experiments.")
    return {"records": exp_records, "csv_path": str(csv_path), "md_path": str(md_path)}


if __name__ == "__main__":
    e_dir = Path("D:/SIH26012_AeroCadastre/experiments/building_detection")
    generate_experiment_comparison(e_dir, e_dir / "reports")
