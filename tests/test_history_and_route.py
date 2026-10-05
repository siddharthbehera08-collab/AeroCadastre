"""
Tests for Parcel History / Diff Engine and Field Route Planner.

Ensures:
1. Version diffing detects geometric modifications (symmetric diff, Hausdorff, area delta, centroid shift)
   and categorical/status transitions.
2. Field Route Planner calculates deterministic TSP inspection paths with priority weighting,
   proper GeoJSON feature collection structuring, and explicit advisory disclaimer.
"""

import pytest
from shapely.geometry import Polygon, box, Point, mapping
from backend.gis.history_diff import compute_parcel_version_diff
from backend.gis.field_route_planner import FieldRoutePlanner


def test_history_diff_identical_geometry():
    poly = box(100.0, 100.0, 200.0, 200.0)
    attrs_v1 = {"confidence": 0.85, "verification_status": "PENDING"}
    attrs_v2 = {"confidence": 0.85, "verification_status": "PENDING"}

    diff = compute_parcel_version_diff(
        geom_v1=mapping(poly),
        geom_v2=mapping(poly),
        props_v1=attrs_v1,
        props_v2=attrs_v2,
    )

    assert diff["is_major_edit"] is False
    assert diff["spatial_metrics"]["iou"] == 1.0
    assert diff["spatial_metrics"]["hausdorff_displacement_m"] == 0.0
    assert diff["spatial_metrics"]["area_delta_m2"] == 0.0
    assert diff["spatial_metrics"]["centroid_shift_m"] == 0.0
    assert diff["changed_attributes"] == {}
    assert diff["change_classification"] == "ATTRIBUTE_ONLY_UPDATE"


def test_history_diff_boundary_modification():
    poly1 = box(100.0, 100.0, 200.0, 200.0)  # 100x100 = 10,000 m2
    poly2 = box(100.0, 100.0, 250.0, 200.0)  # 150x100 = 15,000 m2

    attrs_v1 = {"verification_status": "PENDING", "surveyor": "None"}
    attrs_v2 = {"verification_status": "HUMAN_VERIFIED", "surveyor": "Rajesh Kumar"}

    diff = compute_parcel_version_diff(
        geom_v1=mapping(poly1),
        geom_v2=mapping(poly2),
        props_v1=attrs_v1,
        props_v2=attrs_v2,
    )

    metrics = diff["spatial_metrics"]
    assert metrics["area_before_m2"] == 10000.0
    assert metrics["area_after_m2"] == 15000.0
    assert metrics["area_delta_m2"] == 5000.0
    assert metrics["iou"] == pytest.approx(10000.0 / 15000.0, 0.01)
    assert metrics["hausdorff_displacement_m"] == 50.0
    assert metrics["centroid_shift_m"] == 25.0
    assert metrics["symmetric_diff_area_m2"] == 5000.0

    assert diff["is_major_edit"] is True
    assert diff["change_classification"] == "SIGNIFICANT_BOUNDARY_REALIGNMENT"
    assert "verification_status" in diff["changed_attributes"]
    assert diff["changed_attributes"]["verification_status"]["before"] == "PENDING"
    assert diff["changed_attributes"]["verification_status"]["after"] == "HUMAN_VERIFIED"
    assert diff["changed_attributes"]["surveyor"]["after"] == "Rajesh Kumar"


def test_field_route_planner_empty_queue():
    planner = FieldRoutePlanner()
    result = planner.plan_verification_route([])

    assert result["stop_count"] == 0
    assert result["total_distance_m"] == 0.0
    assert result["ordered_stops"] == []
    assert "disclaimer" in result
    assert result["route_geometry"] is None


def test_field_route_planner_multi_stops():
    # Depot at (385000, 2045000)
    planner = FieldRoutePlanner()

    # 3 items with different coordinates and priorities
    items = [
        {
            "parcel_id": "P-FAR-CRITICAL",
            "priority": "HIGH",
            "centroid": [386000.0, 2046000.0],
            "reasons": ["Severe boundary conflict with highway"]
        },
        {
            "parcel_id": "P-NEAR-LOW",
            "priority": "LOW",
            "centroid": [385100.0, 2045100.0],
            "reasons": ["Minor sliver gap"]
        },
        {
            "parcel_id": "P-MID-MEDIUM",
            "priority": "MEDIUM",
            "centroid": [385500.0, 2045500.0],
            "reasons": ["Water body boundary encroachment"]
        }
    ]

    result = planner.plan_verification_route(items, start_point=(385000.0, 2045000.0))

    assert result["stop_count"] == 3
    assert result["total_distance_m"] > 0.0
    assert len(result["ordered_stops"]) == 3
    assert result["crs"] == "EPSG:32643"
    assert result["route_geometry"]["type"] == "LineString"
    assert len(result["route_geometry"]["coordinates"]) == 4  # Start point + 3 stops
    assert result["estimated_walking_time_min"] > 0.0
    assert "FIELD ROUTE PLANNING ASSISTANCE ONLY" in result["disclaimer"]
