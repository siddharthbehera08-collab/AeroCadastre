"""AeroCadastre Reusable Building Footprint Inference & GIS Extraction CLI.

Accepts an aerial GeoTIFF or image, loads a trained model checkpoint,
generates probability maps, binary masks, and valid GeoJSON building footprint polygons.

Usage:
    python infer_buildings.py --image <path> --checkpoint <path> --output <dir> [--threshold 0.5] [--patch-size 256]
"""

import argparse
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from PIL import Image
import torch
import rasterio
from rasterio.transform import Affine

from ml.building_detection.models import UNetBaseline, ResUNet
from ml.building_detection.polygonizer import mask_to_polygons, polygons_to_geojson


def run_inference(
    image_path: Path,
    checkpoint_path: Path,
    output_dir: Path,
    threshold: float = 0.5,
    patch_size: int = 256,
    stride: int = 192,
    device_str: str = "auto",
) -> Dict[str, Any]:
    """Execute end-to-end building footprint inference and polygonization."""
    output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() and device_str != "cpu" else "cpu")

    # Load Checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=device)
    arch = checkpoint.get("architecture", "UNetBaseline").lower()
    config = checkpoint.get("config", {})
    base_features = config.get("base_features", 32)

    if arch in ["unetbaseline", "unet"]:
        model = UNetBaseline(in_channels=3, out_channels=1, base_features=base_features)
    elif arch in ["resunet", "residual_unet"]:
        model = ResUNet(in_channels=3, out_channels=1, base_features=base_features)
    else:
        model = UNetBaseline(in_channels=3, out_channels=1, base_features=base_features)

    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    # Read image & geospatial metadata
    crs_epsg = None
    transform = None
    with rasterio.open(image_path) as src:
        crs_str = str(src.crs) if src.crs else "unavailable"
        if src.crs and src.crs.to_epsg():
            crs_epsg = src.crs.to_epsg()
        transform = src.transform
        orig_h, orig_w = src.height, src.width

    img_pil = Image.open(image_path).convert("RGB")
    w, h = img_pil.size

    # Sliding window inference
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

    prob_accum = np.zeros((h, w), dtype=np.float32)
    count_accum = np.zeros((h, w), dtype=np.float32)

    print(f"Running inference on {image_path.name} ({w}x{h})...")
    with torch.no_grad():
        for y in range(0, max(1, h - patch_size + 1), stride):
            for x in range(0, max(1, w - patch_size + 1), stride):
                # Handle boundaries
                x_end = min(x + patch_size, w)
                y_end = min(y + patch_size, h)
                x_start = max(0, x_end - patch_size)
                y_start = max(0, y_end - patch_size)

                patch = img_pil.crop((x_start, y_start, x_end, y_end))
                patch_np = np.array(patch, dtype=np.float32) / 255.0
                patch_np = np.transpose(patch_np, (2, 0, 1))
                patch_np = (patch_np - mean) / std

                tensor = torch.from_numpy(patch_np[None, ...]).to(device)
                logit = model(tensor)
                prob = torch.sigmoid(logit)[0, 0].cpu().numpy()

                prob_accum[y_start:y_end, x_start:x_end] += prob
                count_accum[y_start:y_end, x_start:x_end] += 1.0

    count_accum = np.maximum(count_accum, 1.0)
    full_prob = prob_accum / count_accum
    binary_mask = (full_prob >= threshold).astype(np.uint8)

    # Export outputs
    stem = image_path.stem

    # 1. Probability mask
    prob_uint8 = (full_prob * 255).astype(np.uint8)
    prob_path = output_dir / f"{stem}_probability.png"
    Image.fromarray(prob_uint8).save(prob_path)

    # 2. Binary mask
    mask_uint8 = binary_mask * 255
    mask_path = output_dir / f"{stem}_binary_mask.png"
    Image.fromarray(mask_uint8).save(mask_path)

    # 3. Polygonization & GeoJSON
    polygons = mask_to_polygons(binary_mask, min_area=15.0, simplify_tolerance=1.0, transform=transform)

    metadata = {
        "source_image": image_path.name,
        "image_width": w,
        "image_height": h,
        "model_architecture": checkpoint.get("architecture", "UNetBaseline"),
        "experiment_id": checkpoint.get("experiment_id", "UNKNOWN"),
        "threshold": threshold,
        "crs": crs_str,
        "crs_epsg": crs_epsg,
        "building_count": len(polygons),
        "inference_duration_sec": round(time.time() - start_time, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    geojson_doc = polygons_to_geojson(
        polygons=polygons,
        crs_epsg=crs_epsg,
        source_metadata=metadata,
    )

    geojson_path = output_dir / f"{stem}_footprints.geojson"
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2)

    metadata_path = output_dir / f"{stem}_inference_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Inference complete in {metadata['inference_duration_sec']}s: {len(polygons)} building polygons extracted.")
    print(f"Artifacts saved to {output_dir}")

    return {
        "probability_path": str(prob_path),
        "mask_path": str(mask_path),
        "geojson_path": str(geojson_path),
        "metadata_path": str(metadata_path),
        "building_count": len(polygons),
    }


def main():
    parser = argparse.ArgumentParser(description="AeroCadastre Building Footprint Inference")
    parser.add_argument("--image", required=True, type=Path, help="Path to aerial RGB image / GeoTIFF")
    parser.add_argument("--checkpoint", required=True, type=Path, help="Path to trained PyTorch checkpoint (.pt)")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--threshold", type=float, default=0.5, help="Binary classification threshold")
    parser.add_argument("--patch-size", type=int, default=256, help="Tiling patch size")
    parser.add_argument("--stride", type=int, default=192, help="Tiling stride")
    parser.add_argument("--device", type=str, default="auto", help="Compute device ('cuda', 'cpu', 'auto')")

    args = parser.parse_args()
    run_inference(
        image_path=args.image,
        checkpoint_path=args.checkpoint,
        output_dir=args.output,
        threshold=args.threshold,
        patch_size=args.patch_size,
        stride=args.stride,
        device_str=args.device,
    )


if __name__ == "__main__":
    main()
