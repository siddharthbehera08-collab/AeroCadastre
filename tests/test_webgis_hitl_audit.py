"""
Unit tests for Web-GIS Editing, Human-in-the-Loop Feedback, Audit Trail, and Version History.
Runs completely offline without PostgreSQL daemon dependency.
"""

import json
import os
import sys
from pathlib import Path
import pytest
from shapely.geometry import Polygon, LineString, mapping, shape
from shapely.ops import split as shapely_split, unary_union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.utils.crs import compute_metric_area_perimeter, polsby_popper_compactness
from backend.app.utils.geojson import validate_and_parse_geojson
from backend.app.core.security import assert_operator_can_mutate
from backend.app.schemas.api_schemas import (
    ParcelCreateRequest,
    ParcelUpdateRequest,
    ParcelSplitRequest,
    ParcelMergeRequest,
)


def test_operator_authorization():
    """Verify operator mutation authorization rules."""
    # Authorized surveyors
    assert_operator_can_mutate("Surveyor_Verifier_01")
    assert_operator_can_mutate("Senior_Surveyor_Rao")
    assert_operator_can_mutate("GIS_Cadastral_Officer")

    # Read-only operators must be rejected with 403 HTTPException
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        assert_operator_can_mutate("VIEWER")
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        assert_operator_can_mutate("DEMO_USER")
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        assert_operator_can_mutate("SIH26012_REVIEWER")
    assert exc_info.value.status_code == 403


def test_parcel_geometric_split_logic():
    """Verify geometric subdivision logic with area conservation."""
    # Create 100m x 50m parcel (5000 sqm)
    orig_poly = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0), (0.0, 0.0)])
    orig_area = orig_poly.area
    assert orig_area == 5000.0

    # Vertical split at x = 50.0 (50% ratio)
    cut_line = LineString([(50.0, -10.0), (50.0, 60.0)])
    parts = shapely_split(orig_poly, cut_line)
    sub_polys = [g for g in parts.geoms if g.geom_type == "Polygon"]

    assert len(sub_polys) == 2
    assert sub_polys[0].area == 2500.0
    assert sub_polys[1].area == 2500.0
    # Strict area conservation
    assert (sub_polys[0].area + sub_polys[1].area) == orig_area


def test_parcel_geometric_merge_logic():
    """Verify geometric amalgamation logic of adjacent parcels."""
    poly_a = Polygon([(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0), (0.0, 0.0)])
    poly_b = Polygon([(50.0, 0.0), (100.0, 0.0), (100.0, 50.0), (50.0, 50.0), (50.0, 0.0)])

    merged = unary_union([poly_a, poly_b])
    assert merged.geom_type == "Polygon"
    assert merged.area == (poly_a.area + poly_b.area)
    assert merged.bounds == (0.0, 0.0, 100.0, 50.0)


def test_polsby_popper_compactness():
    """Verify compactness metric bounds [0.0, 1.0]."""
    # Square
    sq = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    area_sq, perim_sq = compute_metric_area_perimeter(sq)
    comp_sq = polsby_popper_compactness(area_sq, perim_sq)
    assert 0.70 <= comp_sq <= 0.85

    # Degenerate / zero area
    assert polsby_popper_compactness(0.0, 100.0) == 0.0
    assert polsby_popper_compactness(100.0, 0.0) == 0.0


def test_hitl_pydantic_schemas():
    """Verify validation and default values on HITL API request schemas."""
    # Split request
    split_req = ParcelSplitRequest(split_axis="VERTICAL", split_ratio=0.5, operator_id="Senior_Surveyor_Rao")
    assert split_req.split_ratio == 0.5

    # Invalid split ratio < 0.15 should fail validation
    with pytest.raises(Exception):
        ParcelSplitRequest(split_axis="VERTICAL", split_ratio=0.05)

    # Merge request
    merge_req = ParcelMergeRequest(
        project_id="PROJ_DEMO",
        scene_id="SCENE_01",
        parcel_id_a="P_001",
        parcel_id_b="P_002",
        operator_id="Senior_Surveyor_Rao",
    )
    assert merge_req.parcel_id_a == "P_001"

    # Update request
    update_req = ParcelUpdateRequest(
        land_use_class="commercial",
        verification_status="HUMAN_VERIFIED",
        operator_id="Senior_Surveyor_Rao",
        reason="Verified against drone orthophoto ground marker",
    )
    assert update_req.verification_status == "HUMAN_VERIFIED"
