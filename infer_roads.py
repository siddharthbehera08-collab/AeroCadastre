"""
AeroCadastre Road Inference & GIS Feature Extraction CLI.
Runs sliding-window inference on aerial/satellite GeoTIFFs, outputs probability maps,
binary road masks, and topologically verified GIS GeoJSON corridor geometries.

Usage:
    python infer_roads.py --image <path> --checkpoint <path> --output <dir> [--threshold 0.5]
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
from PIL import Image
import torch
import rasterio

from ml.road_detection.models import RoadResUNet, RoadUNetBaseline
from ml.road_detection.polygonizer import mask_to_road_polygons, road_polygons_to_geojson


def run_road_inference(
    image_path: Path,
    checkpoint_path: Path,
    output_dir: Path,
    threshold: float = 0.5,
    patch_size: int = 256,
    stride: int = 192,
    device_str: str = "auto",
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    
    device = torch.device("cuda" if torch.cuda.is_available() and device_str != "cpu" else "cpu")
    print(f"Loading checkpoint {checkpoint_path} onto {device}...")
    ckpt = torch.load(checkpoint_path, map_location=device)
    
    arch = ckpt.get("architecture", "RoadResUNet").lower()
    if "res" in arch:
        model = RoadResUNet(in_channels=3, out_channels=1, base_features=16)
    else:
        model = RoadUNetBaseline(in_channels=3, out_channels=1, base_features=16)
        
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    
    # Read raster & geospatial metadata
    crs_str = "EPSG:4326"
    crs_epsg = 4326
    transform = None
    
    with rasterio.open(image_path) as src:
        transform = src.transform
        if src.crs and src.crs.to_epsg():
            crs_epsg = src.crs.to_epsg()
            crs_str = f"EPSG:{crs_epsg}"
        arr = src.read()
        h, w = src.shape
        
    # Stretch uint16 to uint8 RGB
    if arr.dtype == np.uint16:
        rgb_8u = np.zeros((h, w, 3), dtype=np.uint8)
        for c in range(min(3, arr.shape[0])):
            b = arr[c].astype(np.float32)
            p2, p98 = np.percentile(b, (2, 98))
            if p98 > p2:
                stretched = np.clip((b - p2) / (p98 - p2) * 255.0, 0, 255).astype(np.uint8)
            else:
                stretched = np.zeros_like(b, dtype=np.uint8)
            rgb_8u[:, :, c] = stretched
    else:
        rgb_8u = np.transpose(arr[:3], (1, 2, 0)).astype(np.uint8)
        
    # Sliding window inference
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
    
    prob_accum = np.zeros((h, w), dtype=np.float32)
    count_accum = np.zeros((h, w), dtype=np.float32)
    
    print(f"Running road segmentation on {image_path.name} ({w}x{h})...")
    with torch.no_grad():
        for y in range(0, max(1, h - patch_size + 1), stride):
            for x in range(0, max(1, w - patch_size + 1), stride):
                x_end = min(x + patch_size, w)
                y_end = min(y + patch_size, h)
                x_start = max(0, x_end - patch_size)
                y_start = max(0, y_end - patch_size)
                
                patch = rgb_8u[y_start:y_end, x_start:x_end].astype(np.float32) / 255.0
                patch_t = np.transpose(patch, (2, 0, 1))
                patch_t = (patch_t - mean) / std
                
                tensor = torch.from_numpy(patch_t[None, ...]).to(device)
                logit = model(tensor)
                prob = torch.sigmoid(logit)[0, 0].cpu().numpy()
                
                prob_accum[y_start:y_end, x_start:x_end] += prob
                count_accum[y_start:y_end, x_start:x_end] += 1.0
                
    count_accum = np.maximum(count_accum, 1.0)
    full_prob = prob_accum / count_accum
    binary_mask = (full_prob >= threshold).astype(np.uint8)
    
    stem = image_path.stem
    # Save probability map
    prob_uint8 = (full_prob * 255).astype(np.uint8)
    prob_path = output_dir / f"{stem}_road_probability.png"
    Image.fromarray(prob_uint8).save(prob_path)
    
    # Save binary mask
    mask_uint8 = binary_mask * 255
    mask_path = output_dir / f"{stem}_road_binary_mask.png"
    Image.fromarray(mask_uint8).save(mask_path)
    
    # Polygonize into GIS GeoJSON
    polygons = mask_to_road_polygons(binary_mask, min_area=30.0, simplify_tolerance=0.00001, transform=transform)
    
    meta = {
        "source_image": image_path.name,
        "width": w,
        "height": h,
        "crs": crs_str,
        "crs_epsg": crs_epsg,
        "threshold": threshold,
        "road_polygons_count": len(polygons),
        "duration_sec": round(time.time() - t0, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    
    geojson_doc = road_polygons_to_geojson(polygons, crs_epsg=crs_epsg, source_metadata=meta)
    geojson_path = output_dir / f"{stem}_road_corridors.geojson"
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2)
        
    with open(output_dir / f"{stem}_inference_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    print(f"Inference completed in {meta['duration_sec']}s: {len(polygons)} road corridor features extracted.")
    return {
        "geojson_path": str(geojson_path),
        "probability_path": str(prob_path),
        "mask_path": str(mask_path),
        "road_polygons_count": len(polygons),
        "duration_sec": meta["duration_sec"],
    }


def main():
    parser = argparse.ArgumentParser(description="AeroCadastre Road Inference CLI")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    
    run_road_inference(args.image, args.checkpoint, args.output, threshold=args.threshold)


if __name__ == "__main__":
    main()
