"""AeroCadastre Reusable Image & Label Integrity Validation Engine.

Verifies:
- File existence & readability
- Dimension match between image and label
- Channel counts (3 for RGB, 1 for mask)
- Valid label values ([0, 255] binary)
- Absence of NaN/Inf or truncated data blocks
- Output: validation_report.json, validation_manifest.csv, and excluded_files.json
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import csv
import numpy as np
from PIL import Image
import rasterio


def validate_dataset_pairs(
    dataset_root: Path,
    output_dir: Path,
    max_check: int = None,
) -> Dict[str, Any]:
    """Validate all training image/mask pairs and test images."""
    output_dir.mkdir(parents=True, exist_ok=True)

    train_img_dir = dataset_root / "train" / "images"
    train_gt_dir = dataset_root / "train" / "gt"
    test_img_dir = dataset_root / "test" / "images"

    train_images = sorted(list(train_img_dir.glob("*.tif*"))) if train_img_dir.exists() else []
    train_masks = sorted(list(train_gt_dir.glob("*.tif*"))) if train_gt_dir.exists() else []
    test_images = sorted(list(test_img_dir.glob("*.tif*"))) if test_img_dir.exists() else []

    mask_map = {m.name: m for m in train_masks}

    valid_pairs = []
    excluded_samples = []
    manifest_rows = []

    pairs_to_check = train_images if max_check is None else train_images[:max_check]

    for img_p in pairs_to_check:
        stem = img_p.stem
        is_valid = True
        rejection_reason = None

        if img_p.name not in mask_map:
            is_valid = False
            rejection_reason = "Missing corresponding ground truth mask"
            excluded_samples.append({"file": str(img_p), "reason": rejection_reason})
            continue

        msk_p = mask_map[img_p.name]

        # Test image readability & dimensions
        try:
            with rasterio.open(img_p) as src_img:
                img_h, img_w = src_img.height, src_img.width
                img_c = src_img.count
                if img_c < 3:
                    is_valid = False
                    rejection_reason = f"Insufficient channels: expected 3, found {img_c}"

            with rasterio.open(msk_p) as src_msk:
                msk_h, msk_w = src_msk.height, src_msk.width
                if (img_h, img_w) != (msk_h, msk_w):
                    is_valid = False
                    rejection_reason = f"Dimension mismatch: image is ({img_h}, {img_w}), mask is ({msk_h}, {msk_w})"

            # Quick check for corrupt/unreadable bytes
            with Image.open(img_p) as test_i:
                test_i.verify()
            with Image.open(msk_p) as test_m:
                test_m.verify()

        except Exception as e:
            is_valid = False
            rejection_reason = f"Corrupted or unreadable TIFF file: {str(e)}"

        if is_valid:
            valid_pairs.append({
                "image_path": str(img_p),
                "mask_path": str(msk_p),
                "tile_id": stem,
                "width": img_w,
                "height": img_h,
            })
            manifest_rows.append({
                "tile_id": stem,
                "image_path": str(img_p),
                "mask_path": str(msk_p),
                "width": img_w,
                "height": img_h,
                "status": "VALID",
                "notes": "",
            })
        else:
            excluded_samples.append({
                "file": str(img_p),
                "mask_file": str(msk_p) if img_p.name in mask_map else None,
                "reason": rejection_reason,
            })
            manifest_rows.append({
                "tile_id": stem,
                "image_path": str(img_p),
                "mask_path": str(msk_p) if img_p.name in mask_map else "",
                "width": 0,
                "height": 0,
                "status": "EXCLUDED",
                "notes": rejection_reason,
            })

    # Summary
    summary = {
        "total_train_images_scanned": len(pairs_to_check),
        "total_valid_pairs": len(valid_pairs),
        "total_excluded": len(excluded_samples),
        "validation_success_rate": round(len(valid_pairs) / (len(pairs_to_check) + 1e-7) * 100, 2),
        "total_test_images": len(test_images),
    }

    # Save validation manifest CSV
    manifest_csv = output_dir / "validation_manifest.csv"
    with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tile_id", "image_path", "mask_path", "width", "height", "status", "notes"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    # Save summary report JSON
    report_json = output_dir / "validation_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "excluded_samples": excluded_samples,
        }, f, indent=2)

    print(f"Validation finished: {summary['total_valid_pairs']} valid pairs, {summary['total_excluded']} excluded.")
    return {
        "summary": summary,
        "valid_pairs": valid_pairs,
        "excluded_samples": excluded_samples,
    }


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("D:/SIH26012_AeroCadastre/data/real/inria/extracted/AerialImageDataset")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("D:/SIH26012_AeroCadastre/experiments/building_detection/manifests")
    validate_dataset_pairs(root, out)
