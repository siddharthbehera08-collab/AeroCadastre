"""
Parcel History & Time Machine Geometry Diff Engine for AeroCadastre.
Computes deterministic spatial and attribute diffs between parcel versions (Version N vs Version N+1).
Calculates:
  - Symmetric difference area (spatial variance)
  - Intersection over Union (IoU)
  - Hausdorff boundary displacement distance (meters)
  - Centroid shift vector
  - Attribute changes (land use, boundary type, verifier, confidence)
"""

import math
from typing import Dict, Any, Optional, Tuple
from shapely.geometry import shape, Polygon, MultiPolygon


def compute_parcel_version_diff(
    geom_v1: Dict[str, Any],
    geom_v2: Dict[str, Any],
    props_v1: Optional[Dict[str, Any]] = None,
    props_v2: Optional[Dict[str, Any]] = None,
    crs: str = "EPSG:32643",
) -> Dict[str, Any]:
    """
    Computes rigorous geometric and attribute diffs between two versions of a parcel.
    """
    props_v1 = props_v1 or {}
    props_v2 = props_v2 or {}

    poly_1 = shape(geom_v1)
    poly_2 = shape(geom_v2)

    if not poly_1.is_valid:
        poly_1 = poly_1.buffer(0)
    if not poly_2.is_valid:
        poly_2 = poly_2.buffer(0)

    area_1 = float(poly_1.area)
    area_2 = float(poly_2.area)
    area_delta = round(area_2 - area_1, 3)
    area_change_pct = round((abs(area_delta) / max(1e-3, area_1)) * 100.0, 2)

    # 1. Intersection over Union (IoU)
    intersection = poly_1.intersection(poly_2)
    inter_area = float(intersection.area)
    union_poly = poly_1.union(poly_2)
    union_area = float(union_poly.area)
    iou = round(inter_area / max(1e-6, union_area), 4)

    # 2. Symmetric Difference (Area modified)
    sym_diff = poly_1.symmetric_difference(poly_2)
    sym_diff_area = round(float(sym_diff.area), 3)

    # 3. Hausdorff Boundary Displacement (maximum gap between boundaries)
    try:
        hausdorff_dist = round(float(poly_1.boundary.hausdorff_distance(poly_2.boundary)), 3)
    except Exception:
        hausdorff_dist = 0.0

    # 4. Centroid Shift
    c1 = poly_1.centroid
    c2 = poly_2.centroid
    centroid_dist = round(float(c1.distance(c2)), 3)
    dx = round(float(c2.x - c1.x), 3)
    dy = round(float(c2.y - c1.y), 3)

    # 5. Attribute Diffs
    changed_attributes = {}
    all_keys = set(props_v1.keys()).union(props_v2.keys())
    for k in all_keys:
        val1 = props_v1.get(k)
        val2 = props_v2.get(k)
        if val1 != val2:
            changed_attributes[k] = {"before": val1, "after": val2}

    # Significant change determination
    is_major_edit = (iou < 0.90) or (hausdorff_dist > 2.0) or (abs(area_delta) > 10.0)

    return {
        "is_major_edit": is_major_edit,
        "spatial_metrics": {
            "iou": iou,
            "symmetric_diff_area_m2": sym_diff_area,
            "hausdorff_displacement_m": hausdorff_dist,
            "centroid_shift_m": centroid_dist,
            "centroid_vector_dx_dy": [dx, dy],
            "area_before_m2": area_1,
            "area_after_m2": area_2,
            "area_delta_m2": area_delta,
            "area_change_pct": area_change_pct,
        },
        "changed_attributes": changed_attributes,
        "crs": crs,
        "change_classification": (
            "SIGNIFICANT_BOUNDARY_REALIGNMENT"
            if hausdorff_dist > 3.0
            else "MINOR_VERTEX_ADJUSTMENT"
            if sym_diff_area > 0.1
            else "ATTRIBUTE_ONLY_UPDATE"
        ),
    }
