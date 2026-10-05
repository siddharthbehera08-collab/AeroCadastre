"""AeroCadastre Building Segmentation Metrics.

Implements rigorous, mathematically verified evaluation metrics:
- Intersection over Union (IoU / Jaccard Index)
- Dice Coefficient (Dice / F1 Score)
- Precision & Recall
- Pixel Accuracy
- Boundary Precision, Recall, and Boundary F1 (relaxed contour matching)
- Confusion Matrix (TP, FP, TN, FN)
- Building Pixel Ratio
"""

from typing import Dict, Any, Union
import numpy as np
import scipy.ndimage as ndi


def extract_boundary(mask: np.ndarray, dilation_radius: int = 1) -> np.ndarray:
    """Extract 1-pixel boundary of binary mask using morphological erosion."""
    binary_mask = (mask > 0).astype(bool)
    if not np.any(binary_mask):
        return np.zeros_like(mask, dtype=bool)
    struct = ndi.generate_binary_structure(2, 1)
    eroded = ndi.binary_erosion(binary_mask, structure=struct)
    boundary = binary_mask ^ eroded
    if dilation_radius > 0:
        struct_dilate = ndi.iterate_structure(struct, dilation_radius)
        boundary = ndi.binary_dilation(boundary, structure=struct_dilate)
    return boundary


def compute_boundary_f1(
    pred_mask: np.ndarray,
    target_mask: np.ndarray,
    tolerance: int = 2,
) -> Dict[str, float]:
    """Compute relaxed boundary precision, recall, and Boundary F1.

    Args:
        pred_mask: Binary prediction mask (H, W).
        target_mask: Binary ground truth mask (H, W).
        tolerance: Pixel distance tolerance for boundary matching (default 2 pixels).

    Returns:
        dict with boundary_precision, boundary_recall, boundary_f1.
    """
    pred_b = extract_boundary(pred_mask, dilation_radius=0)
    target_b = extract_boundary(target_mask, dilation_radius=0)

    num_pred = int(np.sum(pred_b))
    num_target = int(np.sum(target_b))

    if num_pred == 0 and num_target == 0:
        return {"boundary_precision": 1.0, "boundary_recall": 1.0, "boundary_f1": 1.0}
    if num_pred == 0 or num_target == 0:
        return {"boundary_precision": 0.0, "boundary_recall": 0.0, "boundary_f1": 0.0}

    # Dilate for relaxed tolerance matching
    struct = ndi.generate_binary_structure(2, 1)
    struct_tol = ndi.iterate_structure(struct, tolerance) if tolerance > 0 else struct
    target_b_dilated = ndi.binary_dilation(target_b, structure=struct_tol)
    pred_b_dilated = ndi.binary_dilation(pred_b, structure=struct_tol)

    # Precision: fraction of predicted boundary pixels close to a true boundary pixel
    tp_prec = np.sum(pred_b & target_b_dilated)
    precision = float(tp_prec) / (float(num_pred) + 1e-7)

    # Recall: fraction of true boundary pixels close to a predicted boundary pixel
    tp_rec = np.sum(target_b & pred_b_dilated)
    recall = float(tp_rec) / (float(num_target) + 1e-7)

    f1 = (2.0 * precision * recall) / (precision + recall + 1e-7)

    return {
        "boundary_precision": round(float(np.clip(precision, 0.0, 1.0)), 4),
        "boundary_recall": round(float(np.clip(recall, 0.0, 1.0)), 4),
        "boundary_f1": round(float(np.clip(f1, 0.0, 1.0)), 4),
    }


def compute_segmentation_metrics(
    probs: Union[np.ndarray, list],
    targets: Union[np.ndarray, list],
    threshold: float = 0.5,
    compute_boundary: bool = False,
) -> Dict[str, Any]:
    """Compute comprehensive segmentation metrics from probabilities and binary targets.

    Args:
        probs: Array of predicted probabilities [0, 1] of shape (..., H, W).
        targets: Array of binary ground truth targets {0, 1} of shape (..., H, W).
        threshold: Decision threshold for binarization (default 0.5).
        compute_boundary: Whether to calculate boundary F1 (computationally heavier).

    Returns:
        dict with IoU, Dice, Precision, Recall, F1, Pixel Accuracy, Confusion Matrix, etc.
    """
    probs = np.asarray(probs, dtype=np.float32)
    targets = np.asarray(targets, dtype=np.float32)

    preds = (probs >= threshold).astype(np.float32)
    targets_bin = (targets > 0.5).astype(np.float32)

    tp = float(np.sum(preds * targets_bin))
    fp = float(np.sum(preds * (1.0 - targets_bin)))
    fn = float(np.sum((1.0 - preds) * targets_bin))
    tn = float(np.sum((1.0 - preds) * (1.0 - targets_bin)))

    total_pixels = tp + fp + fn + tn

    # IoU / Jaccard
    iou = tp / (tp + fp + fn + 1e-7)

    # Dice / F1
    dice = (2.0 * tp) / (2.0 * tp + fp + fn + 1e-7)

    # Precision & Recall
    precision = tp / (tp + fp + 1e-7)
    recall = tp / (tp + fn + 1e-7)

    # Pixel Accuracy
    pixel_acc = (tp + tn) / (total_pixels + 1e-7)

    # Building pixel ratios
    gt_building_ratio = float(np.sum(targets_bin)) / (total_pixels + 1e-7)
    pred_building_ratio = float(np.sum(preds)) / (total_pixels + 1e-7)

    metrics = {
        "iou": round(float(iou), 4),
        "dice": round(float(dice), 4),
        "f1": round(float(dice), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "pixel_accuracy": round(float(pixel_acc), 4),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "total_pixels": int(total_pixels),
        "gt_building_ratio": round(gt_building_ratio, 4),
        "pred_building_ratio": round(pred_building_ratio, 4),
    }

    if compute_boundary:
        # If batch, compute average boundary metrics across items
        if preds.ndim == 4:
            b_precs, b_recs, b_f1s = [], [], []
            for i in range(preds.shape[0]):
                p_2d = preds[i, 0] if preds.shape[1] == 1 else preds[i]
                t_2d = targets_bin[i, 0] if targets_bin.shape[1] == 1 else targets_bin[i]
                res = compute_boundary_f1(p_2d, t_2d)
                b_precs.append(res["boundary_precision"])
                b_recs.append(res["boundary_recall"])
                b_f1s.append(res["boundary_f1"])
            metrics["boundary_precision"] = round(float(np.mean(b_precs)), 4)
            metrics["boundary_recall"] = round(float(np.mean(b_recs)), 4)
            metrics["boundary_f1"] = round(float(np.mean(b_f1s)), 4)
        elif preds.ndim == 3:
            p_2d = preds[0] if preds.shape[0] == 1 else preds
            t_2d = targets_bin[0] if targets_bin.shape[0] == 1 else targets_bin
            b_res = compute_boundary_f1(p_2d, t_2d)
            metrics.update(b_res)
        elif preds.ndim == 2:
            b_res = compute_boundary_f1(preds, targets_bin)
            metrics.update(b_res)

    return metrics
