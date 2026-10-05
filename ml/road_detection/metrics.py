"""
AeroCadastre Road Evaluation Metrics Engine.
Computes standard segmentation metrics (IoU, Dice, Precision, Recall, F1, Pixel Accuracy)
and road-specific spatial graph connectivity metrics.
"""

from typing import Dict, Any, Tuple
import numpy as np
import torch
import cv2


def compute_segmentation_metrics(
    preds: np.ndarray,
    targets: np.ndarray,
    threshold: float = 0.5,
    smooth: float = 1e-6,
) -> Dict[str, float]:
    """
    Compute pixel-level segmentation metrics for binary road detection.
    
    Args:
        preds: Predicted probabilities or logits array, shape (N, H, W) or (H, W).
        targets: Ground truth binary array {0, 1}, matching shape.
        threshold: Binarization cutoff.
    """
    if isinstance(preds, torch.Tensor):
        preds = preds.detach().cpu().numpy()
    if isinstance(targets, torch.Tensor):
        targets = targets.detach().cpu().numpy()
        
    bin_preds = (preds >= threshold).astype(np.uint8).ravel()
    bin_targets = (targets >= 0.5).astype(np.uint8).ravel()
    
    tp = np.sum((bin_preds == 1) & (bin_targets == 1))
    fp = np.sum((bin_preds == 1) & (bin_targets == 0))
    fn = np.sum((bin_preds == 0) & (bin_targets == 1))
    tn = np.sum((bin_preds == 0) & (bin_targets == 0))
    
    iou = (tp + smooth) / (tp + fp + fn + smooth)
    dice = (2.0 * tp + smooth) / (2.0 * tp + fp + fn + smooth)
    precision = (tp + smooth) / (tp + fp + smooth)
    recall = (tp + smooth) / (tp + fn + smooth)
    f1 = (2.0 * precision * recall + smooth) / (precision + recall + smooth)
    accuracy = (tp + tn) / (tp + fp + fn + tn + smooth)
    
    return {
        "iou": float(iou),
        "dice": float(dice),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "pixel_accuracy": float(accuracy),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
    }


def compute_road_connectivity_metrics(
    pred_mask: np.ndarray,
    target_mask: np.ndarray,
) -> Dict[str, float]:
    """
    Compute topological road connectivity metrics.
    Measures component fragmentation and centerline skeleton preservation.
    """
    if pred_mask.ndim == 3:
        # Iterate across batch samples and average
        frag_list = []
        cov_list = []
        for i in range(pred_mask.shape[0]):
            res = compute_road_connectivity_metrics(pred_mask[i], target_mask[i])
            frag_list.append(res["fragmentation_index"])
            cov_list.append(res["centerline_coverage"])
        return {
            "pred_components": 0,
            "gt_components": 0,
            "fragmentation_index": round(float(np.mean(frag_list)), 3) if frag_list else 1.0,
            "centerline_coverage": round(float(np.mean(cov_list)), 4) if cov_list else 1.0,
        }

    pred_bin = (pred_mask > 0).astype(np.uint8)
    target_bin = (target_mask > 0).astype(np.uint8)
    
    # 1. Connected Component Analysis
    num_pred_cc, _ = cv2.connectedComponents(pred_bin, connectivity=8)
    num_gt_cc, _ = cv2.connectedComponents(target_bin, connectivity=8)
    
    pred_cc = max(0, num_pred_cc - 1)
    gt_cc = max(0, num_gt_cc - 1)
    
    fragmentation = float(pred_cc / max(1, gt_cc))
    
    # 2. Centerline Coverage
    # Simple morphological skeletonization via erosion/dilation
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    skel = np.zeros(target_bin.shape, np.uint8)
    temp = target_bin.copy()
    for _ in range(10):
        eroded = cv2.erode(temp, kernel)
        opened = cv2.dilate(eroded, kernel)
        sub = cv2.subtract(temp, opened)
        skel = cv2.bitwise_or(skel, sub)
        temp = eroded.copy()
        if cv2.countNonZero(temp) == 0:
            break
            
    skel_total = np.sum(skel > 0)
    if skel_total > 0:
        covered = np.sum((skel > 0) & (pred_bin == 1))
        centerline_recall = float(covered / skel_total)
    else:
        centerline_recall = 1.0 if np.sum(pred_bin) == 0 else 0.0
        
    return {
        "pred_components": int(pred_cc),
        "gt_components": int(gt_cc),
        "fragmentation_index": round(fragmentation, 3),
        "centerline_coverage": round(centerline_recall, 4),
    }

