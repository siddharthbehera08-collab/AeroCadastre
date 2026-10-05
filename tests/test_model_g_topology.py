import os
import sys
import pytest
from shapely.geometry import Polygon, MultiPolygon, LineString, box

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_g_topology.topology_validator import TopologyValidator, polsby_popper_compactness


@pytest.fixture
def validator():
    bounds = (0.0, 0.0, 100.0, 100.0)
    return TopologyValidator(study_area_bounds=bounds, overlap_tolerance_m2=0.50, min_polygon_area_m2=10.0)


def test_polsby_popper_compactness():
    # Square 10x10 -> Area=100, Perim=40 -> 4*pi*100 / 1600 = 400*pi/1600 ~ 0.785
    comp = polsby_popper_compactness(100.0, 40.0)
    assert 0.78 <= comp <= 0.79
    # Empty
    assert polsby_popper_compactness(0.0, 0.0) == 0.0


def test_valid_polygon(validator):
    feat = {
        "id": "poly_1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]
        }
    }
    report = validator.validate_features([feat], layer_name="test")
    assert report["valid_features"] == 1
    assert report["invalid_features"] == 0
    assert len(report["issues"]) == 0


def test_self_intersection(validator):
    # Figure 8 polygon (self-intersecting)
    feat = {
        "id": "poly_self_intersect",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[10, 10], [20, 20], [20, 10], [10, 20], [10, 10]]]
        }
    }
    report = validator.validate_features([feat], layer_name="test")
    assert report["invalid_features"] == 1
    assert any(i["rule_id"] in ["G001_INVALID_GEOMETRY", "G007_SELF_INTERSECTION"] for i in report["issues"])


def test_empty_and_null_geometry(validator):
    feat_empty = {"id": "p_empty", "geometry": {"type": "Polygon", "coordinates": []}}
    feat_null = {"id": "p_null", "geometry": None}
    report = validator.validate_features([feat_empty, feat_null], layer_name="test")
    assert report["invalid_features"] == 2
    rule_ids = [i["rule_id"] for i in report["issues"]]
    assert "G002_EMPTY_GEOMETRY" in rule_ids
    assert "G003_NULL_GEOMETRY" in rule_ids


def test_polygon_overlap_and_duplicate(validator):
    # Two identical polygons (duplicate)
    p1 = {
        "id": "p1",
        "geometry": {"type": "Polygon", "coordinates": [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]}
    }
    p2 = {
        "id": "p2",
        "geometry": {"type": "Polygon", "coordinates": [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]}
    }
    # Third polygon partially overlapping (> 0.5 m^2)
    p3 = {
        "id": "p3",
        "geometry": {"type": "Polygon", "coordinates": [[[15, 10], [25, 10], [25, 20], [15, 20], [15, 10]]]}
    }
    report = validator.validate_features([p1, p2, p3], layer_name="test")
    rule_ids = [i["rule_id"] for i in report["issues"]]
    assert "G008_DUPLICATE_GEOMETRY" in rule_ids
    assert "G009_OVERLAPPING_POLYGONS" in rule_ids


def test_sliver_and_tiny_polygon(validator):
    # Tiny polygon: area 2 m^2
    feat_tiny = {
        "id": "p_tiny",
        "geometry": {"type": "Polygon", "coordinates": [[[10, 10], [11, 10], [11, 12], [10, 12], [10, 10]]]}
    }
    # Sliver polygon: 20x0.5 m -> area=10 m^2, perim=41 m -> compactness < 0.10
    feat_sliver = {
        "id": "p_sliver",
        "geometry": {"type": "Polygon", "coordinates": [[[30, 30], [50, 30], [50, 30.5], [30, 30.5], [30, 30]]]}
    }
    report = validator.validate_features([feat_tiny, feat_sliver], layer_name="test")
    rule_ids = [i["rule_id"] for i in report["issues"]]
    assert "G011_TINY_POLYGON" in rule_ids
    assert "G010_SLIVER_POLYGON" in rule_ids


def test_detect_parcel_gaps(validator):
    # Two parcels surrounding a 20x20 gap (doughnut with a hole)
    # Outer frame composed of 2 C-shaped polygons enclosing an empty middle square (10,10 to 30,30)
    p1 = {
        "id": "p1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [40, 0], [40, 40], [0, 40], [0, 0]], [[10, 10], [10, 30], [30, 30], [30, 10], [10, 10]]]
        }
    }
    p2 = {
        "id": "p2",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[40, 0], [50, 0], [50, 40], [40, 40], [40, 0]]]
        }
    }
    gaps = validator.detect_parcel_gaps([p1, p2], min_gap_area_m2=15.0)
    assert len(gaps) == 1
    assert gaps[0]["rule_id"] == "G014_PARCEL_GAP"
    assert gaps[0]["metric_value"] == pytest.approx(400.0, rel=1e-2)


def test_repair_features(validator):
    # Invalid self-intersecting polygon + duplicate polygon
    p_invalid = {
        "id": "p_inv",
        "geometry": {"type": "Polygon", "coordinates": [[[10, 10], [20, 20], [20, 10], [10, 20], [10, 10]]]}
    }
    p_dup1 = {
        "id": "p_d1",
        "geometry": {"type": "Polygon", "coordinates": [[[30, 30], [40, 30], [40, 40], [30, 40], [30, 30]]]}
    }
    p_dup2 = {
        "id": "p_d2",
        "geometry": {"type": "Polygon", "coordinates": [[[30, 30], [40, 30], [40, 40], [30, 40], [30, 30]]]}
    }
    repaired, actions = validator.repair_features([p_invalid, p_dup1, p_dup2])
    assert actions["fixed_invalid"] >= 1
    assert actions["deduplicated"] == 1
    assert len(repaired) >= 2
