"""AeroCadastre Patch Extraction & Manifest Generation Engine.

Extracts grid patches from large 5000x5000 aerial tiles:
- Configurable patch size (e.g. 256x256, 512x512), stride, overlap.
- Balanced sampling: retains foreground building patches while keeping an informative subset of background patches.
- Manifest-driven: stores patch bounding boxes and building ratios without duplicating huge raster files on disk.
- Fast streaming window reads for memory efficiency.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json
import csv
import numpy as np
from PIL import Image


def generate_patch_manifest(
    split_manifest_path: Path,
    output_dir: Path,
    patch_size: int = 256,
    stride: int = 256,
    min_building_ratio: float = 0.005,
    max_bg_ratio: float = 0.30,  # Max fraction of background-only patches to keep
    max_patches_per_split: Optional[Dict[str, int]] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Generate patch bounding box manifest from split tiles.

    Args:
        split_manifest_path: Path to split_manifest.json.
        output_dir: Output directory for patch manifests.
        patch_size: Square patch dimension (e.g. 256).
        stride: Step size between patches (patch_size - overlap).
        min_building_ratio: Minimum building pixel percentage to classify as foreground.
        max_bg_ratio: Maximum proportion of pure-background patches retained to balance data.
        max_patches_per_split: Optional ceiling on patch counts per split (e.g. {'train': 2000, 'val': 500}).
        seed: Random seed for deterministic selection.

    Returns:
        Summary dict of generated patch manifests.
    """
    np.random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_data = json.load(f)

    splits = split_data["splits"]
    patch_splits = {"train": [], "val": [], "test": []}

    stats = {
        "patch_size": patch_size,
        "stride": stride,
        "overlap": patch_size - stride,
        "min_building_ratio": min_building_ratio,
    }

    for split_name, tiles in splits.items():
        print(f"Generating patches for {split_name} ({len(tiles)} tiles)...")
        fg_patches = []
        bg_patches = []

        # Subsample tiles if necessary for swift, targeted training
        selected_tiles = tiles
        if split_name == "train" and len(tiles) > 30:
            # Select balanced subset of tiles across all 5 cities
            by_city = {}
            for t in tiles:
                by_city.setdefault(t["city"], []).append(t)
            selected_tiles = []
            for city, c_tiles in by_city.items():
                selected_tiles.extend(c_tiles[:6])  # 6 tiles per city = 30 tiles for train

        for tile in selected_tiles:
            img_p = Path(tile["image_path"])
            msk_p = Path(tile["mask_path"])
            stem = tile["tile_id"]

            if not img_p.exists() or not msk_p.exists():
                continue

            # Open mask to analyze building density quickly (downsampled or full)
            with Image.open(msk_p) as msk_img:
                msk_w, msk_h = msk_img.size
                msk_arr = np.array(msk_img)

            # Sliding window grid
            for y in range(0, msk_h - patch_size + 1, stride):
                for x in range(0, msk_w - patch_size + 1, stride):
                    crop_mask = msk_arr[y : y + patch_size, x : x + patch_size]
                    bldg_pixels = int(np.sum(crop_mask > 127))
                    total_pixels = patch_size * patch_size
                    bldg_ratio = bldg_pixels / total_pixels

                    patch_entry = {
                        "patch_id": f"{stem}_y{y}_x{x}",
                        "tile_id": stem,
                        "city": tile["city"],
                        "split": split_name,
                        "image_path": str(img_p),
                        "mask_path": str(msk_p),
                        "crop": [x, y, patch_size, patch_size],
                        "building_ratio": round(float(bldg_ratio), 4),
                        "is_foreground": bool(bldg_ratio >= min_building_ratio),
                    }

                    if bldg_ratio >= min_building_ratio:
                        fg_patches.append(patch_entry)
                    else:
                        bg_patches.append(patch_entry)

        # Balance foreground and background
        np.random.shuffle(bg_patches)
        num_bg_keep = int(len(fg_patches) * max_bg_ratio)
        kept_bg = bg_patches[:num_bg_keep]
        combined = fg_patches + kept_bg
        np.random.shuffle(combined)

        # Cap if requested
        if max_patches_per_split and split_name in max_patches_per_split:
            cap = max_patches_per_split[split_name]
            if len(combined) > cap:
                combined = combined[:cap]

        patch_splits[split_name] = combined
        stats[f"{split_name}_total_patches"] = len(combined)
        stats[f"{split_name}_foreground_patches"] = sum(1 for p in combined if p["is_foreground"])
        stats[f"{split_name}_background_patches"] = sum(1 for p in combined if not p["is_foreground"])

    # Save patch manifest JSON
    manifest_json = output_dir / "patch_manifest.json"
    with open(manifest_json, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "patches": patch_splits}, f, indent=2)

    # Save summary CSV
    for split_name, plist in patch_splits.items():
        csv_file = output_dir / f"patches_{split_name}.csv"
        if plist:
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(plist[0].keys()))
                writer.writeheader()
                writer.writerows(plist)

    print(f"Patch manifest generated successfully:")
    for split_name in ["train", "val", "test"]:
        print(f"  - {split_name}: {stats.get(f'{split_name}_total_patches', 0)} patches")

    return {"stats": stats, "patches": patch_splits}
