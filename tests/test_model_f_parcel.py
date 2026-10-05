"""
Automated unit tests for Model F Parcel Inference Engine.
"""

import os
import sys
import pytest
from shapely.geometry import LineString, Polygon

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_f_parcel_inference.candidate_network import planarize_and_polygonize_network
from experiments.model_f_parcel_inference.parcel_features import extract_parcel_features
from experiments.model_f_parcel_inference.parcel_inference import ParcelInferenceEngine
from experiments.model_f_parcel_inference.evaluator import evaluate_candidate_parcels


def test_planarize_and_polygonize_network():
    # 4 lines forming a closed 10x10 square
    lines = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (0, 10)]),
        LineString([(0, 10), (0, 0)]),
    ]
    polys = planarize_and_polygonize_network(lines, min_area_m2=15.0)
    assert len(polys) == 1
    assert polys[0].area == pytest.approx(100.0, rel=1e-3)


def test_sliver_filtering():
    # Large valid parcel (100 m^2) and tiny sliver (5 m^2)
    lines = [
        # 10x10 square
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (0, 10)]),
        LineString([(0, 10), (0, 0)]),
        # Tiny triangle (area = 0.5 * 2 * 2 = 2 m^2)
        LineString([(10, 0), (12, 0)]),
        LineString([(12, 0), (10, 2)]),
        LineString([(10, 2), (10, 0)]),
    ]
    polys = planarize_and_polygonize_network(lines, min_area_m2=15.0)
    # Only 10x10 square should remain; tiny triangle filtered out
    assert len(polys) == 1
    assert polys[0].area == 100.0


def test_extract_parcel_features():
    parcel = Polygon([(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)])  # 400 m^2
    bldg = Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])    # 100 m^2 inside
    road = LineString([(0, 0), (20, 0)])                             # along south edge

    feats = extract_parcel_features(parcel, buildings=[bldg], roads=[road])
    assert feats["area_sqm"] == 400.0
    assert feats["perimeter_m"] == 80.0
    assert feats["building_count"] == 1
    assert feats["building_coverage_ratio"] == pytest.approx(0.25, rel=1e-2)
    assert feats["has_road_access"] is True


def test_parcel_inference_engine():
    engine = ParcelInferenceEngine()
    lines = [
        LineString([(0, 0), (50, 0)]),
        LineString([(50, 0), (50, 50)]),
        LineString([(50, 50), (0, 50)]),
        LineString([(0, 50), (0, 0)]),
    ]
    bldgs = [Polygon([(10, 10), (20, 10), (20, 20), (10, 20), (10, 10)])]

    parcels = engine.generate_candidate_parcels(lines, buildings=bldgs)
    assert len(parcels) == 1
    p = parcels[0]
    assert p["label"] == "CANDIDATE_PARCEL"
    assert p["boundary_type"] == "INFERRED_PARCEL_BOUNDARY"
    assert "CAND_PARCEL_" in p["id"]
    assert p["properties"]["area_sqm"] == pytest.approx(2500.0, rel=1e-2)
    assert p["properties"]["building_count"] == 1

    summary = evaluate_candidate_parcels(parcels)
    assert summary["total_candidate_parcels"] == 1
    assert summary["provenance_standard"] == "INFERRED_PARCEL_BOUNDARY"
