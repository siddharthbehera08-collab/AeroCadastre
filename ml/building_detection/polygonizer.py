"""AeroCadastre Deterministic Building Footprint Polygonizer & GIS Exporter.

Converts segmentation probability maps and binary masks into topologically valid,
GIS-ready building footprints (GeoJSON / Shapely geometries) with CRS georeferencing.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import json
import numpy as np
import cv2
from shapely.geometry import Polygon, MultiPolygon, mapping, shape
from shapely.validation import make_valid
from shapely.ops import unary_union
import rasterio
from rasterio.transform import Affine


def mask_to_polygons(
    binary_mask: np.ndarray,
    min_area: float = 20.0,
    simplify_tolerance: float = 1.0,
    transform: Optional[Affine] = None,
) -> List[Polygon]:
    """Deterministically convert a binary building mask into clean, valid Shapely Polygons.

    Args:
        binary_mask: 2D binary numpy array (H, W) where 1 indicates building.
        min_area: Minimum polygon area (in pixels or map units) to filter noise.
        simplify_tolerance: Douglas-Peucker simplification tolerance (0 for no simplification).
        transform: Optional rasterio Affine transform to map pixel coordinates to CRS coordinates.

    Returns:
        List of valid, clean Shapely Polygon objects.
    """
    mask_u8 = (binary_mask > 0).astype(np.uint8) * 255
    contours, hierarchy = cv2.findContours(
        mask_u8, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours or hierarchy is None:
        return []

    hierarchy = hierarchy[0]
    polygons = []

    # Map raster pixel coordinates to world coordinates if transform provided
    def to_coords(pts: np.ndarray) -> List[Tuple[float, float]]:
        coords = []
        for pt in pts:
            px, py = float(pt[0][0]), float(pt[0][1])
            if transform is not None:
                wx, wy = rasterio.transform.xy(transform, py, px)
                coords.append((wx, wy))
            else:
                coords.append((px, py))
        return coords

    # OpenCV hierarchy: [Next, Previous, First_Child, Parent]
    for idx, (cnt, h) in enumerate(zip(contours, hierarchy)):
        parent_idx = h[3]
        if parent_idx != -1:
            # This is an inner ring (hole), handled with parent
            continue

        if len(cnt) < 3:
            continue

        shell_coords = to_coords(cnt)
        if len(shell_coords) < 3:
            continue

        # Close ring if open
        if shell_coords[0] != shell_coords[-1]:
            shell_coords.append(shell_coords[0])

        # Find holes (children of this contour)
        holes = []
        child_idx = h[2]
        while child_idx != -1:
            child_cnt = contours[child_idx]
            if len(child_cnt) >= 3:
                hole_coords = to_coords(child_cnt)
                if len(hole_coords) >= 3:
                    if hole_coords[0] != hole_coords[-1]:
                        hole_coords.append(hole_coords[0])
                    holes.append(hole_coords)
            child_idx = hierarchy[child_idx][0]

        try:
            poly = Polygon(shell=shell_coords, holes=holes)
            # Ensure valid geometry
            if not poly.is_valid:
                poly = make_valid(poly)

            # Filter or extract components
            if isinstance(poly, Polygon):
                geoms = [poly]
            elif isinstance(poly, MultiPolygon):
                geoms = list(poly.geoms)
            else:
                geoms = [g for g in poly.geoms if isinstance(g, Polygon)]

            for g in geoms:
                if simplify_tolerance > 0:
                    g = g.simplify(simplify_tolerance, preserve_topology=True)
                if g.is_valid and not g.is_empty and g.area >= min_area:
                    polygons.append(g)
        except Exception:
            continue

    return polygons


def validate_and_repair_polygon(poly: Polygon, min_area: float = 10.0) -> Optional[Polygon]:
    """Perform topological validation, self-intersection repair, and filtering."""
    if poly is None or poly.is_empty:
        return None
    if not poly.is_valid:
        poly = make_valid(poly)
    if isinstance(poly, MultiPolygon):
        valid_parts = [p for p in poly.geoms if isinstance(p, Polygon) and p.is_valid and p.area >= min_area]
        if not valid_parts:
            return None
        poly = max(valid_parts, key=lambda p: p.area)
    if not isinstance(poly, Polygon) or poly.area < min_area:
        return None
    return poly


def polygons_to_geojson(
    polygons: List[Polygon],
    crs_epsg: Optional[int] = None,
    properties_list: Optional[List[Dict[str, Any]]] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Export building footprint polygons to standard GeoJSON FeatureCollection."""
    features = []
    for idx, poly in enumerate(polygons):
        poly_valid = validate_and_repair_polygon(poly)
        if poly_valid is None:
            continue

        props = {
            "feature_id": f"BLDG_{idx + 1:05d}",
            "class": "building",
            "area_sq_units": round(float(poly_valid.area), 2),
            "perimeter_units": round(float(poly_valid.length), 2),
            "is_valid": poly_valid.is_valid,
        }
        if properties_list and idx < len(properties_list):
            props.update(properties_list[idx])

        feature = {
            "type": "Feature",
            "geometry": mapping(poly_valid),
            "properties": props,
        }
        features.append(feature)

    geojson_doc = {
        "type": "FeatureCollection",
        "features": features,
    }

    if crs_epsg:
        geojson_doc["crs"] = {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{crs_epsg}"},
        }

    if source_metadata:
        geojson_doc["metadata"] = source_metadata

    return geojson_doc
