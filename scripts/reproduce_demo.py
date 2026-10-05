#!/usr/bin/env python3
"""
AeroCadastre SIH26012 — Automated Reproducibility & Benchmark Replay.
Executes the full pipeline from raw fixtures to final GIS candidate parcels,
verifying that output parcel geometries and confidence metrics remain mathematically identical.
"""

import sys
import json
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_demo import run_synthetic_demo


def compute_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def reproduce_demo():
    print("=" * 70)
    print("AEROCADASTRE SIH26012 — REPRODUCIBILITY AUDIT")
    print("=" * 70)

    # Run pass 1
    print("[Pass 1] Executing synthetic pipeline...")
    manifest1 = run_synthetic_demo()
    geojson_path = PROJECT_ROOT / "outputs" / "AERO-SYNTH-001" / "SYNTH_QUAD_SCENE_01" / "SYNTH_QUAD_SCENE_01_cadastral_parcels.geojson"
    assert geojson_path.exists(), f"Missing output GeoJSON: {geojson_path}"
    hash1 = compute_file_sha256(geojson_path)
    print(f"[Pass 1] Candidate Parcels Hash: {hash1}")

    # Run pass 2
    print("[Pass 2] Re-executing synthetic pipeline from scratch...")
    manifest2 = run_synthetic_demo()
    hash2 = compute_file_sha256(geojson_path)
    print(f"[Pass 2] Candidate Parcels Hash: {hash2}")

    print("-" * 70)
    if hash1 == hash2:
        print("REPRODUCIBILITY CONFIRMED: Identical SHA256 cryptographic hash across runs!")
        print(f"Verified {manifest1['parcels_inferred']} candidate parcels with stable polygon geometry.")
        print("=" * 70)
        return True
    else:
        print("REPRODUCIBILITY WARNING: Output hashes differ across sequential runs.")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = reproduce_demo()
    sys.exit(0 if success else 1)
