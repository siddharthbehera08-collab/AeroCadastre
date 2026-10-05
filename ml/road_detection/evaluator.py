"""
AeroCadastre Road Model Test Evaluation Engine.
Evaluates the best checkpoint on the held-out untouched test set.
Computes segmentation metrics, connectivity metrics, and generates visual overlays.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from PIL import Image

from ml.road_detection.models import RoadResUNet, RoadUNetBaseline
from ml.road_detection.dataset import get_dataloaders
from ml.road_detection.metrics import compute_segmentation_metrics, compute_road_connectivity_metrics


def evaluate_test_set(
    checkpoint_path: Path,
    patch_root: Path,
    output_dir: Path,
    batch_size: int = 8,
    model_type: str = "resunet",
    base_features: int = 16,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"Loading checkpoint from {checkpoint_path}...")
    ckpt = torch.load(checkpoint_path, map_location=device)
    
    if model_type == "resunet":
        model = RoadResUNet(in_channels=3, out_channels=1, base_features=base_features)
    else:
        model = RoadUNetBaseline(in_channels=3, out_channels=1, base_features=base_features)
        
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    
    _, _, test_loader = get_dataloaders(patch_root, batch_size=batch_size, seed=42)
    print(f"Test DataLoader ready: {len(test_loader.dataset)} patches.")
    
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for images, masks in test_loader:
            images = images.to(device)
            logits = model(images)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_preds.append(probs)
            all_targets.append(masks.numpy())
            
    preds_np = np.concatenate(all_preds, axis=0)  # (N, 1, H, W)
    targets_np = np.concatenate(all_targets, axis=0)  # (N, 1, H, W)
    
    seg_metrics = compute_segmentation_metrics(preds_np, targets_np)
    conn_metrics = compute_road_connectivity_metrics(preds_np[:, 0] > 0.5, targets_np[:, 0] > 0.5)
    
    results = {
        "model_architecture": ckpt.get("architecture", "RoadResUNet"),
        "test_patch_count": len(test_loader.dataset),
        "test_iou": round(seg_metrics["iou"], 4),
        "test_dice": round(seg_metrics["dice"], 4),
        "test_precision": round(seg_metrics["precision"], 4),
        "test_recall": round(seg_metrics["recall"], 4),
        "test_pixel_accuracy": round(seg_metrics["pixel_accuracy"], 4),
        "test_centerline_coverage": conn_metrics["centerline_coverage"],
        "test_fragmentation_index": conn_metrics["fragmentation_index"],
        "tp": seg_metrics["tp"],
        "fp": seg_metrics["fp"],
        "fn": seg_metrics["fn"],
        "tn": seg_metrics["tn"],
    }
    
    # Save test metrics JSON and CSV
    with open(output_dir / "final_test_metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame([results]).to_csv(output_dir / "final_test_metrics.csv", index=False)
    
    print("\n--- Final Untouched Test Set Evaluation ---")
    for k, v in results.items():
        print(f"  {k}: {v}")
        
    # Generate 8 visual test samples
    viz_dir = output_dir / "test_visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    
    mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)
    
    test_ds = test_loader.dataset
    for idx in range(min(8, len(test_ds))):
        img_t, mask_t = test_ds[idx]
        with torch.no_grad():
            img_in = img_t.unsqueeze(0).to(device)
            logit = model(img_in)
            prob = torch.sigmoid(logit)[0, 0].cpu().numpy()
            bin_pred = (prob >= 0.5).astype(np.uint8) * 255
            
        img_np = img_t.numpy() * std + mean
        img_np = np.clip(img_np * 255.0, 0, 255).astype(np.uint8)
        img_rgb = np.transpose(img_np, (1, 2, 0))
        
        gt_mask = (mask_t[0].numpy() * 255.0).astype(np.uint8)
        prob_map = (prob * 255.0).astype(np.uint8)
        
        # 4-panel comparison
        h, w = img_rgb.shape[:2]
        canvas = np.zeros((h, w * 4, 3), dtype=np.uint8)
        canvas[:, :w] = img_rgb
        canvas[:, w:w*2] = np.stack([gt_mask]*3, axis=-1)
        canvas[:, w*2:w*3] = np.stack([prob_map]*3, axis=-1)
        
        overlay = img_rgb.copy()
        overlay[bin_pred > 0] = [0, 255, 0] # Green road prediction
        blended = (0.6 * img_rgb + 0.4 * overlay).astype(np.uint8)
        canvas[:, w*3:] = blended
        
        Image.fromarray(canvas).save(viz_dir / f"test_sample_{idx+1:02d}.png")
        
    print(f"Visual test overlays saved to {viz_dir}")
    return results


if __name__ == "__main__":
    ckpt = Path(r"D:\SIH26012_AeroCadastre\experiments\road_detection\EXP_ROAD_RESUNET_001\checkpoints\best_model.pth")
    patches = Path(r"D:\SIH26012_AeroCadastre\data\real\spacenet_roads\paris\patches")
    out = Path(r"D:\SIH26012_AeroCadastre\experiments\road_detection\reports\test_evaluation")
    evaluate_test_set(ckpt, patches, out, model_type="resunet")
