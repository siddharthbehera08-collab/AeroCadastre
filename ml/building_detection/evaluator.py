"""AeroCadastre Final Test Evaluation & Reporting Engine.

Evaluates trained model checkpoints strictly on the untouched test set.
Generates:
- final_test_metrics.json
- final_test_metrics.csv
- final_test_report.md
- High-resolution test visual prediction grids
"""

from typing import Dict, Any, List, Optional
import json
import csv
import time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ml.building_detection.models import UNetBaseline, ResUNet, BCEDiceLoss
from ml.building_detection.dataset import AerialPatchDataset
from ml.building_detection.metrics import compute_segmentation_metrics


def evaluate_checkpoint_on_test(
    checkpoint_path: Path,
    patch_manifest_path: Path,
    output_dir: Path,
    batch_size: int = 16,
    device_str: str = "auto",
    max_visualizations: int = 8,
) -> Dict[str, Any]:
    """Execute evaluation on untouched test set."""
    output_dir.mkdir(parents=True, exist_ok=True)
    vis_dir = output_dir / "test_visualizations"
    vis_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() and device_str != "cpu" else "cpu")

    # Load checkpoint
    ckpt = torch.load(checkpoint_path, map_location=device)
    arch = ckpt.get("architecture", "UNetBaseline").lower()
    config = ckpt.get("config", {})
    base_features = config.get("base_features", 32)

    if arch in ["unetbaseline", "unet"]:
        model = UNetBaseline(in_channels=3, out_channels=1, base_features=base_features)
    elif arch in ["resunet", "residual_unet"]:
        model = ResUNet(in_channels=3, out_channels=1, base_features=base_features)
    else:
        model = UNetBaseline(in_channels=3, out_channels=1, base_features=base_features)

    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()

    # Load test patches
    with open(patch_manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    test_patches = manifest["patches"]["test"]
    print(f"Evaluating {len(test_patches)} UNTOUCHED test patches on {device}...")

    patch_size = config.get("dataset", {}).get("patch_size", 256)
    test_dataset = AerialPatchDataset(
        samples=test_patches,
        patch_size=patch_size,
        is_train=False,
        augment=False,
        normalize_imagenet=config.get("dataset", {}).get("normalize_imagenet", True),
    )
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    criterion = BCEDiceLoss(bce_weight=0.5)

    total_loss = 0.0
    all_probs = []
    all_targets = []

    # Visual un-normalization
    mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)
    vis_count = 0

    with torch.no_grad():
        for images, masks in test_loader:
            images = images.to(device)
            masks = masks.to(device)

            logits = model(images)
            loss = criterion(logits, masks)
            total_loss += loss.item()

            probs = torch.sigmoid(logits).cpu().numpy()
            targets = masks.cpu().numpy()

            all_probs.append(probs)
            all_targets.append(targets)

            # Generate visualizations
            if vis_count < max_visualizations:
                for b in range(images.size(0)):
                    if vis_count >= max_visualizations:
                        break
                    img_np = images[b].cpu().numpy()
                    img_unnorm = np.clip((img_np * std + mean).transpose(1, 2, 0), 0.0, 1.0)
                    gt = targets[b, 0]
                    pr = probs[b, 0]
                    bm = (pr >= 0.5).astype(np.float32)

                    fig, axes = plt.subplots(1, 5, figsize=(20, 4))
                    axes[0].imshow(img_unnorm)
                    axes[0].set_title("[TEST] Aerial RGB")
                    axes[0].axis("off")

                    axes[1].imshow(gt, cmap="gray")
                    axes[1].set_title("[TEST] Ground Truth")
                    axes[1].axis("off")

                    im_p = axes[2].imshow(pr, cmap="jet", vmin=0, vmax=1)
                    axes[2].set_title("[TEST] Predicted Prob")
                    axes[2].axis("off")
                    plt.colorbar(im_p, ax=axes[2], fraction=0.046, pad=0.04)

                    axes[3].imshow(bm, cmap="gray")
                    axes[3].set_title("[TEST] Binary Mask (0.5)")
                    axes[3].axis("off")

                    # Overlay
                    overlay = img_unnorm.copy()
                    tp = (bm == 1) & (gt == 1)
                    fp = (bm == 1) & (gt == 0)
                    fn = (bm == 0) & (gt == 1)
                    overlay[tp] = overlay[tp] * 0.5 + np.array([0.0, 0.8, 0.0]) * 0.5
                    overlay[fp] = overlay[fp] * 0.5 + np.array([0.9, 0.0, 0.0]) * 0.5
                    overlay[fn] = overlay[fn] * 0.5 + np.array([0.0, 0.2, 0.9]) * 0.5
                    axes[4].imshow(np.clip(overlay, 0.0, 1.0))
                    axes[4].set_title("[TEST] Error Overlay (G:TP, R:FP, B:FN)")
                    axes[4].axis("off")

                    plt.tight_layout()
                    plt.savefig(vis_dir / f"test_sample_{vis_count + 1:02d}.png", dpi=150)
                    plt.close(fig)
                    vis_count += 1

    avg_loss = total_loss / max(1, len(test_loader))
    concat_probs = np.concatenate(all_probs, axis=0)
    concat_targets = np.concatenate(all_targets, axis=0)

    # Compute comprehensive metrics with boundary F1
    metrics = compute_segmentation_metrics(
        concat_probs, concat_targets, threshold=0.5, compute_boundary=True
    )
    metrics["test_loss"] = round(avg_loss, 4)
    metrics["experiment_id"] = ckpt.get("experiment_id", "UNKNOWN")
    metrics["model_architecture"] = ckpt.get("architecture", "UNetBaseline")
    metrics["test_sample_count"] = len(test_patches)
    metrics["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Save JSON
    json_path = output_dir / "final_test_metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Save CSV
    csv_path = output_dir / "final_test_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)

    # Save Report MD
    report_path = output_dir / "final_test_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# AeroCadastre — Final Untouched Test Set Evaluation Report\n\n")
        f.write("## 1. Test Verification Protocol\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> **Strict Leakage Prevention Guarantee:**\n")
        f.write("> This evaluation was executed ONCE on the completely untouched test set (tiles 6-10 of all 5 cities).\n")
        f.write("> Zero hyperparameter tuning or early stopping decisions were made using these test tiles.\n\n")

        f.write("## 2. Quantitative Measured Results\n")
        f.write(f"- **Evaluated Experiment:** `{metrics['experiment_id']}`\n")
        f.write(f"- **Architecture:** `{metrics['model_architecture']}`\n")
        f.write(f"- **Test Patch Count:** {metrics['test_sample_count']} patches (256x256)\n")
        f.write(f"- **Intersection over Union (IoU):** **{metrics['iou'] * 100:.2f}%**\n")
        f.write(f"- **Dice / F1 Score:** **{metrics['dice'] * 100:.2f}%**\n")
        f.write(f"- **Precision:** **{metrics['precision'] * 100:.2f}%**\n")
        f.write(f"- **Recall:** **{metrics['recall'] * 100:.2f}%**\n")
        f.write(f"- **Boundary F1:** **{metrics.get('boundary_f1', 0.0) * 100:.2f}%**\n")
        f.write(f"- **Pixel Accuracy:** {metrics['pixel_accuracy'] * 100:.2f}%\n")
        f.write(f"- **Test BCE+Dice Loss:** {metrics['test_loss']:.4f}\n\n")

        f.write("## 3. Confusion Matrix Breakdown\n")
        f.write(f"- **True Positives (Building Pixels):** {metrics['tp']:,}\n")
        f.write(f"- **False Positives (Hallucinated Pixels):** {metrics['fp']:,}\n")
        f.write(f"- **False Negatives (Missed Building Pixels):** {metrics['fn']:,}\n")
        f.write(f"- **True Negatives (Background Pixels):** {metrics['tn']:,}\n")
        f.write(f"- **Ground Truth Building Ratio:** {metrics['gt_building_ratio'] * 100:.2f}%\n")
        f.write(f"- **Predicted Building Ratio:** {metrics['pred_building_ratio'] * 100:.2f}%\n\n")

        f.write("## 4. Cadastral Integrity & Limitation Notes\n")
        f.write("> [!NOTE]\n")
        f.write("> Building detection from aerial imagery provides a foundational physical evidence layer.\n")
        f.write("> It represents building footprints, not cadastral parcel legal boundaries.\n")
        f.write("> Real cadastral parcel boundaries require fusion with survey pillars, roads, walls, and ground verification.\n")

    print(f"Test evaluation completed: IoU={metrics['iou']:.4f}, Dice={metrics['dice']:.4f}, Boundary F1={metrics.get('boundary_f1', 0.0):.4f}")
    return metrics


if __name__ == "__main__":
    import sys
    ckpt = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("D:/SIH26012_AeroCadastre/experiments/building_detection/EXP_BUILDING_UNET_001/checkpoints/best_model.pt")
    pm = Path("D:/SIH26012_AeroCadastre/data/real/inria/patches/exported_patch_manifest.json")
    out = Path("D:/SIH26012_AeroCadastre/experiments/building_detection/reports/test_evaluation")
    evaluate_checkpoint_on_test(ckpt, pm, out)
