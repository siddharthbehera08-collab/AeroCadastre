"""Automated unit and integration tests for Pune Common Metric Grid (EPSG:32643)."""
import os
import json
import pytest
import rasterio
import fiona
from shapely.geometry import shape, box

GRID_DIR = r"D:\SIH26012_AeroCadastre\data\real\india\pune\grid"
SPEC_PATH = os.path.join(GRID_DIR, "grid_spec.json")
REF_PATH = os.path.join(GRID_DIR, "grid_reference.tif")
BOUNDS_PATH = os.path.join(GRID_DIR, "grid_bounds.geojson")
TERRAIN_DIR = os.path.join(GRID_DIR, "terrain")
REF_DIR = os.path.join(GRID_DIR, "reference")

EXPECTED_CRS = "EPSG:32643"
EXPECTED_WIDTH = 32
EXPECTED_HEIGHT = 22
EXPECTED_RES = (100.0, 100.0)
EXPECTED_BOUNDS = (377550.0, 2047000.0, 380750.0, 2049200.0)


def test_grid_spec_exists_and_valid():
    """Verify grid_spec.json exists and contains correct metadata."""
    assert os.path.exists(SPEC_PATH), f"Missing {SPEC_PATH}"
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)
    assert spec["crs"] == EXPECTED_CRS
    assert spec["width"] == EXPECTED_WIDTH
    assert spec["height"] == EXPECTED_HEIGHT
    assert spec["pixel_size_x_m"] == 100.0
    assert spec["pixel_size_y_m"] == 100.0
    assert spec["bounds"] == list(EXPECTED_BOUNDS)


def test_grid_reference_raster_alignment():
    """Verify reference raster matches target CRS, dimensions, and transform."""
    assert os.path.exists(REF_PATH), f"Missing {REF_PATH}"
    with rasterio.open(REF_PATH) as src:
        assert src.crs.to_string() == EXPECTED_CRS
        assert src.width == EXPECTED_WIDTH
        assert src.height == EXPECTED_HEIGHT
        assert src.res == EXPECTED_RES
        assert (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top) == EXPECTED_BOUNDS


def test_aligned_terrain_rasters_consistency():
    """Verify all reprojected terrain rasters are identical in CRS, bounds, shape, and nodata."""
    terrain_files = [
        "pune_core_dem.tif",
        "pune_core_slope.tif",
        "pune_core_aspect.tif",
        "pune_core_relief.tif",
        "pune_core_hillshade.tif"
    ]
    for fname in terrain_files:
        fp = os.path.join(TERRAIN_DIR, fname)
        assert os.path.exists(fp), f"Missing terrain raster: {fp}"
        with rasterio.open(fp) as src:
            assert src.crs.to_string() == EXPECTED_CRS, f"CRS mismatch in {fname}: {src.crs}"
            assert src.width == EXPECTED_WIDTH, f"Width mismatch in {fname}"
            assert src.height == EXPECTED_HEIGHT, f"Height mismatch in {fname}"
            assert src.res == EXPECTED_RES, f"Resolution mismatch in {fname}"
            assert (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top) == EXPECTED_BOUNDS
            assert src.nodata == -9999.0
            data = src.read(1)
            valid = data[data != -9999.0]
            assert len(valid) == EXPECTED_WIDTH * EXPECTED_HEIGHT, f"Unintended nodata cells in {fname}"


def test_reference_layers_reprojected_correctly():
    """Verify that OSM building and road reference layers are valid and within common bounds."""
    bldg_fp = os.path.join(REF_DIR, "pune_buildings_utm43n.geojson")
    road_fp = os.path.join(REF_DIR, "pune_roads_utm43n.geojson")
    assert os.path.exists(bldg_fp), f"Missing {bldg_fp}"
    assert os.path.exists(road_fp), f"Missing {road_fp}"

    grid_poly = box(*EXPECTED_BOUNDS)

    with fiona.open(bldg_fp) as src:
        assert len(src) == 1917, f"Expected 1917 buildings, got {len(src)}"
        for feat in src:
            geom = shape(feat["geometry"])
            assert geom.is_valid, "Invalid building geometry found"
            # Centroid must fall within grid bounds
            assert grid_poly.contains(geom.centroid), "Building falls outside common grid bounds"

    with fiona.open(road_fp) as src:
        assert len(src) == 413, f"Expected 413 roads, got {len(src)}"
        for feat in src:
            geom = shape(feat["geometry"])
            assert geom.is_valid, "Invalid road geometry found"
