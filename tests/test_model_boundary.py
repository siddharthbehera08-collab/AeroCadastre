"""
Automated unit tests for Model Boundary Evidence Engine.
"""

import os
import sys
import pytest
from shapely.geometry import Polygon, LineString, mapping

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_boundary.boundary_features import calculate_line_azimuth, extract_boundary_features
from experiments.model_boundary.boundary_evidence import BoundaryEvidenceEngine
from experiments.model_boundary.evaluator import evaluate_boundary_candidates


def test_calculate_line_azimuth():
    # North line: (0,0) to (0,10) -> dx=0, dy=10 -> arctan2(0, 10) = 0 deg
    line_n = LineString([(0, 0), (0, 10)])
    assert calculate_line_azimuth(line_n) == pytest.approx(0.0, abs=1.0)

    # East line: (0,0) to (10,0) -> dx=10, dy=0 -> arctan2(10, 0) = 90 deg
    line_e = LineString([(0, 0), (10, 0)])
    assert calculate_line_azimuth(line_e) == pytest.approx(90.0, abs=1.0)


def test_extract_boundary_features():
    edge = LineString([(0, 0), (0, 20)])
    road = LineString([(3, 0), (3, 20)])  # parallel road at 3m distance
    bldg = Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])

    feats = extract_boundary_features(edge, nearby_roads=[road], nearby_buildings=[bldg])
    assert feats["length_m"] == 20.0
    assert feats["min_road_dist_m"] == pytest.approx(3.0, abs=0.1)
    assert feats["min_bldg_dist_m"] == pytest.approx(5.0, abs=0.1)
    assert feats["is_parallel_road"] == 1.0


def test_boundary_evidence_candidate_generation():
    engine = BoundaryEvidenceEngine()
    bldgs = [
        Polygon([(10, 10), (20, 10), (20, 20), (10, 20), (10, 10)]),
        Polygon([(30, 10), (40, 10), (40, 20), (30, 20), (30, 10)]),
    ]
    roads = [
        LineString([(0, 0), (50, 0)])
    ]

    candidates = engine.generate_candidate_boundaries(bldgs, roads)
    assert len(candidates) >= 3  # road left/right + 2 building setbacks

    for c in candidates:
        assert c["label"] == "INFERRED_BOUNDARY_EVIDENCE"
        assert "boundary_score" in c
        assert "uncertainty" in c
        assert c["boundary_score"] + c["uncertainty"] == pytest.approx(1.0, abs=1e-2)
        assert c["provenance"]["engine"] == "MODEL_BOUNDARY_EVIDENCE_ENGINE"


def test_boundary_evaluator():
    engine = BoundaryEvidenceEngine()
    bldgs = [Polygon([(10, 10), (20, 10), (20, 20), (10, 20), (10, 10)])]
    roads = [LineString([(0, 0), (50, 0)])]

    candidates = engine.generate_candidate_boundaries(bldgs, roads)
    summary = evaluate_boundary_candidates(candidates)

    assert summary["total_candidates"] == len(candidates)
    assert 0.0 < summary["mean_score"] <= 1.0
    assert summary["provenance_standard"] == "INFERRED_BOUNDARY_EVIDENCE"
