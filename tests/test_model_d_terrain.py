"""
Automated unit tests for Model D Terrain Feature Engine.
Validates raster loading, scene statistics, point sampling, polygon zonal extraction, and provenance.
"""

import os
import sys
import json
import pytest
from shapely.geometry import Polygon, box

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_d_terrain.terrain_features import TerrainFeatureExtractor


@pytest.fixture
def extractor():
    return TerrainFeatureExtractor()


def test_terrain_extractor_initialization(extractor):
    """Verify that all 5 terrain layers are loaded and validated."""
    assert len(extractor.rasters) == 5
    assert set(extractor.rasters.keys()) == {"dem", "slope", "aspect", "relief", "hillshade"}
    assert extractor.crs == "EPSG:32643"
    assert extractor.expected_shape == (22, 32)


def test_scene_statistics_generation(extractor):
    """Verify that whole-scene statistics are calculated without errors."""
    stats = extractor.get_scene_statistics()
    assert stats["crs"] == "EPSG:32643"
    assert "dem" in stats["statistics"]
    assert stats["statistics"]["dem"]["count"] == 704
    assert 540.0 <= stats["statistics"]["dem"]["mean"] <= 580.0
    assert 0.0 <= stats["statistics"]["slope"]["mean"] <= 10.0


def test_point_sampling_in_bounds(extractor):
    """Verify point sampling within Pune study area returns valid numbers."""
    # Centroid of Pune core bounds: ~ (379150, 2048100)
    res = extractor.sample_point(379150.0, 2048100.0)
    assert res["in_bounds"] is True
    vals = res["values"]
    assert vals["dem"] is not None
    assert 540.0 <= vals["dem"] <= 580.0
    assert vals["slope"] is not None


def test_point_sampling_out_of_bounds(extractor):
    """Verify point sampling outside bounds gracefully returns in_bounds=False."""
    res = extractor.sample_point(100000.0, 100000.0)
    assert res["in_bounds"] is False
    assert res["values"]["dem"] is None


def test_polygon_zonal_feature_extraction(extractor):
    """Verify polygon zonal extraction returns expected schema and non-null values."""
    poly = Polygon([
        (378000.0, 2047500.0),
        (378100.0, 2047500.0),
        (378100.0, 2047600.0),
        (378000.0, 2047600.0),
        (378000.0, 2047500.0),
    ])
    feats = extractor.extract_polygon_terrain_features(poly)
    assert "elevation_mean" in feats
    assert "slope_mean" in feats
    assert "steep_slope_flag" in feats
    assert feats["provenance"]["engine"] == "MODEL_D_TERRAIN_FEATURE_ENGINE"
    assert feats["provenance"]["evidence_type"] == "INFERRED_TERRAIN_CONTEXT"
