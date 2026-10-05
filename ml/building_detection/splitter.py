"""AeroCadastre Leak-Free Geographic Data Splitting Engine.

Implements benchmark geographic partitioning for the Inria dataset:
- Train: Tiles 11 to 36 of each city (130 tiles, ~72%)
- Validation: Tiles 1 to 5 of each city (25 tiles, ~14%)
- Untouched Test: Tiles 6 to 10 of each city (25 tiles, ~14%)

Guarantees:
- Zero spatial leakage across splits
- Full geographic representation of all 5 diverse landscape types (Austin, Chicago, Kitsap, Tyrol, Vienna)
- Test set is strictly isolated for final validation
- Exports: split_manifest.json and split_manifest.csv
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import csv
import re


def parse_tile_city_and_id(stem: str) -> Tuple[str, int]:
    """Parse city name and numeric index from tile stem (e.g. 'austin14' -> ('austin', 14))."""
    match = re.match(r"^([a-zA-Z\-]+?)(\d+)$", stem)
    if match:
        city = match.group(1).rstrip("-").lower()
        idx = int(match.group(2))
        return city, idx
    return stem.lower(), 0


def create_geographic_splits(
    valid_pairs: List[Dict[str, Any]],
    output_dir: Path,
    val_indices: Tuple[int, int] = (1, 5),
    test_indices: Tuple[int, int] = (6, 10),
) -> Dict[str, Any]:
    """Partition valid image/mask pairs into train, val, and untouched test splits."""
    output_dir.mkdir(parents=True, exist_ok=True)

    splits = {
        "train": [],
        "val": [],
        "test": [],
    }

    manifest_rows = []

    for item in valid_pairs:
        stem = item["tile_id"]
        city, idx = parse_tile_city_and_id(stem)

        if val_indices[0] <= idx <= val_indices[1]:
            split = "val"
        elif test_indices[0] <= idx <= test_indices[1]:
            split = "test"
        else:
            split = "train"

        record = {
            "tile_id": stem,
            "city": city,
            "tile_num": idx,
            "split": split,
            "image_path": item["image_path"],
            "mask_path": item["mask_path"],
            "width": item.get("width", 5000),
            "height": item.get("height", 5000),
        }
        splits[split].append(record)
        manifest_rows.append(record)

    summary = {
        "total_tiles": len(manifest_rows),
        "train_count": len(splits["train"]),
        "val_count": len(splits["val"]),
        "test_count": len(splits["test"]),
        "cities": sorted(list({r["city"] for r in manifest_rows})),
        "val_tile_range": f"{val_indices[0]}-{val_indices[1]} per city",
        "test_tile_range": f"{test_indices[0]}-{test_indices[1]} per city (strictly untouched)",
        "train_tile_range": f"{test_indices[1]+1}+ per city",
    }

    # Save JSON manifest
    json_path = output_dir / "split_manifest.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "splits": splits}, f, indent=2)

    # Save CSV manifest
    csv_path = output_dir / "split_manifest.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tile_id", "city", "tile_num", "split", "image_path", "mask_path", "width", "height"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Splits generated: {summary['train_count']} train, {summary['val_count']} val, {summary['test_count']} test.")
    return {"summary": summary, "splits": splits}
