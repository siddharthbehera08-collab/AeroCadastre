import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_h_anomaly.anomaly_detector import AnomalyDetector


@pytest.fixture
def detector():
    bounds = (0.0, 0.0, 200.0, 200.0)
    return AnomalyDetector(
        study_area_bounds=bounds,
        default_road_buffer_m=4.0,
        min_building_area_m2=15.0,
        max_road_distance_m=50.0,
        min_road_overlap_m2=2.0
    )


def test_building_road_intersection_conflict(detector):
    # Road along y=50 from x=0 to 100
    road = {
        "id": "r1",
        "geometry": {"type": "LineString", "coordinates": [[0, 50], [100, 50]]},
        "properties": {"highway": "residential"}
    }
    # Building overlapping road corridor (y=48 to 58)
    bldg = {
        "id": "b1",
        "geometry": {"type": "Polygon", "coordinates": [[[20, 48], [40, 48], [40, 58], [20, 58], [20, 48]]]},
        "properties": {}
    }
    report = detector.detect_anomalies([bldg], [road])
    assert report["total_anomalies_detected"] >= 1
    rule_ids = [a["rule_id"] for a in report["anomalies"]]
    assert "H003_BUILDING_ROAD_INTERSECTION" in rule_ids


def test_isolated_building_anomaly(detector):
    # Road at y=10
    road = {
        "id": "r1",
        "geometry": {"type": "LineString", "coordinates": [[0, 10], [100, 10]]},
        "properties": {"highway": "residential"}
    }
    # Building far away at y=150 (dist = 140 m > 50 m)
    bldg = {
        "id": "b_isolated",
        "geometry": {"type": "Polygon", "coordinates": [[[50, 150], [70, 150], [70, 170], [50, 170], [50, 150]]]},
        "properties": {}
    }
    report = detector.detect_anomalies([bldg], [road])
    rule_ids = [a["rule_id"] for a in report["anomalies"]]
    assert "H007_ISOLATED_BUILDING" in rule_ids


def test_short_road_fragment(detector):
    # Road only 5 m long (threshold is 15 m)
    road_short = {
        "id": "r_short",
        "geometry": {"type": "LineString", "coordinates": [[10, 10], [15, 10]]},
        "properties": {"highway": "residential"}
    }
    report = detector.detect_anomalies([], [road_short])
    rule_ids = [a["rule_id"] for a in report["anomalies"]]
    assert "H006_ROAD_FRAGMENT" in rule_ids


def test_compare_parcels_with_reference(detector):
    # Reference parcel 50x50 at (0,0)
    ref = {
        "id": "REF_001",
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [50, 0], [50, 50], [0, 50], [0, 0]]]}
    }
    # Candidate parcel displaced by 8m (high Hausdorff displacement & low IoU)
    cand_displaced = {
        "id": "CAND_DISP",
        "geometry": {"type": "Polygon", "coordinates": [[[8, 0], [58, 0], [58, 50], [8, 50], [8, 0]]]}
    }
    # Candidate extra parcel (no reference overlap)
    cand_extra = {
        "id": "CAND_EXTRA",
        "geometry": {"type": "Polygon", "coordinates": [[[100, 100], [140, 100], [140, 140], [100, 140], [100, 100]]]}
    }

    report = detector.compare_parcels_with_reference([cand_displaced, cand_extra], [ref])
    assert report["total_conflicts"] >= 2
    rule_ids = [c["rule_id"] for c in report["conflicts"]]
    assert "C001_HIGH_BOUNDARY_DISPLACEMENT" in rule_ids
    assert "C004_EXTRA_PARCEL" in rule_ids
    assert "NEVER establish legal encroachment" in report["provenance"]["disclaimer"]
