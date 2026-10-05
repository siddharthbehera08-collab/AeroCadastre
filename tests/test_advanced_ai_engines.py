"""
Unit Test Suite for Image Quality AI, Boundary Reliability AI, and Parcel Plausibility AI.
Tests:
1. ImageQualityAIEngine: blur detection, shadow estimation, overall radiometric score.
2. BoundaryReliabilityEngine: distance offsets from buildings and roads, slope penalties.
3. ParcelPlausibilityEngine: Polsby-Popper compactness, aspect ratio, road access penalty, sliver rejection.
"""

import numpy as np
import pytest
from shapely.geometry import box, Polygon

from experiments.image_quality.quality_engine import ImageQualityAIEngine
from experiments.boundary_reliability.boundary_reliability_engine import BoundaryReliabilityEngine
from experiments.parcel_plausibility.plausibility_engine import ParcelPlausibilityEngine


def test_image_quality_engine_sharp_and_blurred():
    engine = ImageQualityAIEngine()

    # Sharp synthetic image (high contrast checkerboard)
    sharp_img = np.zeros((100, 100), dtype=np.float32)
    sharp_img[::2, ::2] = 200.0
    sharp_img[1::2, 1::2] = 200.0

    sharp_res = engine.evaluate_raster_quality(sharp_img)
    assert sharp_res["sharpness_score"] > 0.50
    assert sharp_res["overall_quality_score"] > 0.50

    # Completely flat blurred/uniform image
    flat_img = np.ones((100, 100), dtype=np.float32) * 128.0
    flat_res = engine.evaluate_raster_quality(flat_img)
    assert flat_res["laplacian_variance"] == 0.0
    assert "EXCESSIVE_BLUR_DETECTED" in flat_res["issues_detected"]
    assert flat_res["cadastral_readiness"] == "POOR_QUALITY_REJECTED"


def test_boundary_reliability_engine_scoring():
    engine = BoundaryReliabilityEngine(crs="EPSG:32643")

    # High reliability: close to road, sensible building offset, gentle slope, high visual prob
    good_res = engine.evaluate_edge_reliability(
        edge_geom=None,
        dist_to_building_m=5.0,
        dist_to_road_m=3.0,
        terrain_slope_deg=4.5,
        visual_prob=0.88
    )
    assert good_res["reliability_score"] >= 0.75
    assert good_res["reliability_tier"] == "HIGH"
    assert "PLAUSIBLE_BUILDING_OFFSET" in good_res["cues"]

    # Degraded reliability: steep slope (30 deg), far from infrastructure, low visual prob
    poor_res = engine.evaluate_edge_reliability(
        edge_geom=None,
        dist_to_building_m=80.0,
        dist_to_road_m=90.0,
        terrain_slope_deg=32.0,
        visual_prob=0.30
    )
    assert poor_res["reliability_score"] < 0.50
    assert poor_res["reliability_tier"] == "LOW"
    assert "HIGH_SLOPE_DEGRADATION_PENALTY" in poor_res["cues"]


def test_parcel_plausibility_engine():
    engine = ParcelPlausibilityEngine()

    # 1. Standard rectangular urban parcel (e.g. 20m x 25m = 500 m2)
    standard_poly = box(0.0, 0.0, 20.0, 25.0)
    res_std = engine.evaluate_parcel_plausibility(standard_poly, has_road_access=True)
    assert res_std["plausibility_status"] == "PLAUSIBLE"
    assert res_std["plausibility_score"] >= 0.70
    assert res_std["metrics"]["area_m2"] == 500.0
    assert res_std["metrics"]["compactness"] > 0.70

    # 2. Extreme sliver parcel (1m x 100m = 100 m2, aspect ratio 100)
    sliver_poly = box(0.0, 0.0, 1.0, 100.0)
    res_sliver = engine.evaluate_parcel_plausibility(sliver_poly, has_road_access=False)
    assert res_sliver["plausibility_status"] in ("SUSPICIOUS", "IMPLAUSIBLE")
    assert any("ASPECT_RATIO" in r for r in res_sliver["reasons"])
    assert any("LANDLOCKED" in r for r in res_sliver["reasons"])
