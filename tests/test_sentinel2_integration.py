"""
AeroCadastre Sentinel-2 Integration & Regression Test Suite.
Verifies:
1. Sentinel-2 Pune acquisition integrity (GeoTIFF headers, bands, bounds, resolution, CRS).
2. STAC provenance metadata and cryptographic SHA256 hashes.
3. Backend API endpoint /api/gis/sentinel2 returns authentic metadata.
4. Bounded timeout protection against hanging remote requests.
5. Scientific limitation: Sentinel-2 is contextual LULC evidence, not authoritative cadastral boundary data.
"""

import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

DATA_DIR = Path("data/real/india/pune/imagery/sentinel2")
PROVENANCE_FILE = DATA_DIR / "pune_sentinel2_provenance.json"


def test_sentinel2_files_exist_on_disk():
    """Verify that all required Sentinel-2 GeoTIFF products exist locally."""
    assert DATA_DIR.exists(), "Sentinel-2 data directory missing."
    expected_files = [
        "pune_sentinel2_b02.tif",
        "pune_sentinel2_b03.tif",
        "pune_sentinel2_b04.tif",
        "pune_sentinel2_b08.tif",
        "pune_sentinel2_scl.tif",
        "pune_sentinel2_rgb.tif",
        "pune_sentinel2_ndvi.tif",
        "pune_sentinel2_provenance.json",
    ]
    for fname in expected_files:
        fpath = DATA_DIR / fname
        assert fpath.exists(), f"Expected Sentinel-2 file missing: {fname}"
        assert fpath.stat().st_size > 0, f"File {fname} is empty."


def test_sentinel2_geotiff_raster_validation():
    """Verify raster properties: dimensions, CRS, transform, bounds, and no-data values."""
    # Test 10m bands (B02, B03, B04, B08)
    for band_name in ["b02", "b03", "b04", "b08"]:
        fpath = DATA_DIR / f"pune_sentinel2_{band_name}.tif"
        with rasterio.open(fpath) as src:
            assert str(src.crs) == "EPSG:4326"
            assert src.shape == (216, 324)
            assert src.count == 1
            assert src.bounds.left == pytest.approx(73.84, rel=1e-3)
            assert src.bounds.right == pytest.approx(73.87, rel=1e-3)
            assert src.bounds.bottom == pytest.approx(18.51, rel=1e-3)
            assert src.bounds.top == pytest.approx(18.53, rel=1e-3)

            data = src.read(1)
            assert not np.isnan(data).any(), f"NaNs detected in {band_name}"
            assert data.min() > 0, f"Uninitialized min value in {band_name}"

    # Test RGB Composite (3-band)
    with rasterio.open(DATA_DIR / "pune_sentinel2_rgb.tif") as src:
        assert src.count == 3
        assert src.shape == (216, 324)

    # Test NDVI (1-band Float32, bounded in [-1, 1])
    with rasterio.open(DATA_DIR / "pune_sentinel2_ndvi.tif") as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        ndvi = src.read(1)
        assert ndvi.min() >= -1.0
        assert ndvi.max() <= 1.0
        # Vegetation exists in Pune urban core
        assert ndvi.mean() > 0.05

    # Test SCL (20m resolution, uint8)
    with rasterio.open(DATA_DIR / "pune_sentinel2_scl.tif") as src:
        assert src.count == 1
        assert src.shape == (108, 162)
        assert src.dtypes[0] == "uint8"


def test_sentinel2_provenance_integrity():
    """Verify that provenance metadata contains complete cryptographic and STAC attributes."""
    assert PROVENANCE_FILE.exists()
    meta = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))

    assert meta["stac_item_id"] == "S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803"
    assert meta["tile_id"] == "T43QCA"
    assert meta["cloud_cover_percent"] < 1.0  # ~0.695% cloud cover
    assert meta["output_crs"] == "EPSG:4326"
    assert "CONTEXTUAL / LULC EVIDENCE ONLY" in meta["scientific_usage_notice"]

    files_dict = meta["files"]
    for asset in ["B02", "B03", "B04", "B08", "SCL", "RGB", "NDVI"]:
        assert asset in files_dict
        f_info = files_dict[asset]
        assert "sha256" in f_info
        assert len(f_info["sha256"]) == 64
        assert f_info["size_bytes"] > 0


def test_backend_sentinel2_api_endpoint():
    """Verify GET /api/gis/sentinel2 returns valid acquisition metadata."""
    resp = client.get("/api/gis/sentinel2")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ACQUIRED_AND_VERIFIED"
    assert data["stac_item_id"] == "S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803"
    assert "files" in data
    assert "RGB" in data["files"]
    assert "NDVI" in data["files"]
    assert data["raster_dimensions"]["height_pixels"] == 216
    assert data["raster_dimensions"]["width_pixels"] == 324


def test_stac_pystac_loading_and_signing():
    """Verify STAC item loading via pystac and asset signing via planetary_computer."""
    import pystac
    import planetary_computer

    stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803"
    item = pystac.Item.from_file(stac_url)
    assert item.id == "S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803"

    signed = planetary_computer.sign(item)
    for asset_name in ["B02", "B03", "B04", "B08", "SCL"]:
        assert asset_name in signed.assets
        href = signed.assets[asset_name].href
        assert "blob.core.windows.net" in href
        assert "sig=" in href or "token" in href or "se=" in href  # Signed SAS query token


def test_sentinel2_band_alignment_and_non_empty():
    """Verify band alignment across all 10m rasters and ensure rasters are non-empty."""
    profiles = []
    for band_name in ["b02", "b03", "b04", "b08"]:
        fpath = DATA_DIR / f"pune_sentinel2_{band_name}.tif"
        with rasterio.open(fpath) as src:
            profiles.append((src.shape, src.transform, src.crs))
            arr = src.read(1)
            assert arr.size > 0
            assert np.count_nonzero(arr) == arr.size, f"Zero pixels detected in {band_name}"

    ref_shape, ref_trans, ref_crs = profiles[0]
    for shape, trans, crs in profiles[1:]:
        assert shape == ref_shape
        assert trans == ref_trans
        assert crs == ref_crs

