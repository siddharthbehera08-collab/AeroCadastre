"""
Unit Test Suite for Raster Ingestion & Validation Contract.
Tests checksum calculation, metadata inspection, format checking, bounds validation,
and manifest generation.
"""

from pathlib import Path
import pytest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from backend.gis.raster_ingestion import RasterIngestionEngine


@pytest.fixture
def engine():
    return RasterIngestionEngine(target_crs="EPSG:32643")


def test_raster_nonexistent_file(engine):
    """Verify FileNotFoundError on missing raster path."""
    with pytest.raises(FileNotFoundError):
        engine.inspect_and_validate(Path("nonexistent_raster_file.tif"))


def test_raster_invalid_extension(engine, tmp_path):
    """Verify rejection of non-raster file extensions."""
    bad_file = tmp_path / "test_script.sh"
    bad_file.write_text("#!/bin/bash\necho hello", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        engine.inspect_and_validate(bad_file)
    assert "Invalid file extension" in str(exc.value)


def test_raster_oversized_rejection(tmp_path):
    """Verify rejection when file size exceeds maximum limit."""
    small_limit_engine = RasterIngestionEngine(max_file_size_bytes=100)
    fake_tif = tmp_path / "big_fake.tif"
    fake_tif.write_bytes(b"0" * 500)
    with pytest.raises(ValueError) as exc:
        small_limit_engine.inspect_and_validate(fake_tif)
    assert "exceeds maximum allowed limit" in str(exc.value)


def test_inspect_real_pune_dem(engine):
    """Inspect real Pune DEM raster if present."""
    pune_dem = PROJECT_ROOT / "data" / "real" / "india" / "pune" / "grid" / "terrain" / "pune_core_dem.tif"
    if pune_dem.exists():
        info = engine.inspect_and_validate(pune_dem)
        assert info["validation_status"] == "VALID"
        assert len(info["sha256"]) == 64
        assert info["count"] >= 1
        assert info["width"] > 0
        assert info["height"] > 0

        # Test manifest generation
        manifest = engine.generate_manifest(
            inspection_results=info,
            modality="TERRAIN_DEM",
            data_mode="REAL",
        )
        assert manifest["manifest_version"] == "1.0.0"
        assert manifest["modality"] == "TERRAIN_DEM"
        assert manifest["data_mode"] == "REAL"
        assert manifest["provenance"]["sha256"] == info["sha256"]


def test_raster_synthetic_valid_and_mismatched_crs(engine, tmp_path):
    """Test raster validation with synthetic GeoTIFFs using rasterio."""
    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError:
        pytest.skip("rasterio not installed")

    # 1. Valid EPSG:32643 synthetic raster
    valid_tif = tmp_path / "valid_metric.tif"
    transform_valid = from_origin(377550.0, 2049200.0, 10.0, 10.0)
    data = (np.ones((1, 50, 50)) * 42).astype(np.float32)

    with rasterio.open(
        valid_tif,
        "w",
        driver="GTiff",
        height=50,
        width=50,
        count=1,
        dtype="float32",
        crs="EPSG:32643",
        transform=transform_valid,
        nodata=-9999.0,
    ) as dst:
        dst.write(data)

    pune_bounds = (377550.0, 2047000.0, 380750.0, 2049200.0)
    info_valid = engine.inspect_and_validate(valid_tif, study_area_bounds=pune_bounds)
    assert info_valid["validation_status"] == "VALID"
    assert info_valid["crs"] == "EPSG:32643"
    assert info_valid["is_metric"] is True
    assert info_valid["nodata"] == -9999.0
    assert info_valid["grid_compatible"] is True

    # 2. Mismatched CRS (EPSG:4326 geographic)
    mismatch_tif = tmp_path / "wgs84_raster.tif"
    transform_wgs = from_origin(73.84, 18.53, 0.001, 0.001)
    with rasterio.open(
        mismatch_tif,
        "w",
        driver="GTiff",
        height=20,
        width=20,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform_wgs,
    ) as dst:
        dst.write(data[:, :20, :20])

    info_mismatch = engine.inspect_and_validate(mismatch_tif)
    assert info_mismatch["crs"] == "EPSG:4326"
    assert info_mismatch["is_metric"] is False
    assert any("differs from target metric CRS" in w for w in info_mismatch["warnings"])

    # 3. Out-of-bounds raster rejection
    far_bounds = (500000.0, 3000000.0, 501000.0, 3001000.0)
    info_oob = engine.inspect_and_validate(valid_tif, study_area_bounds=far_bounds)
    assert info_oob["grid_compatible"] is False
    assert info_oob["validation_status"] == "INVALID_EXTENT"
    assert any("does not overlap study area extent" in w for w in info_oob["warnings"])

