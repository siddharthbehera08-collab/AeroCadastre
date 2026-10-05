"""
AeroCadastre Road Vectorization & GIS GeoJSON Generator.
Converts binary road prediction masks into simplified, topologically valid LineString & Polygon geometries.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import cv2
import shapely.geometry
from shapely.validation import make_valid
from rasterio.transform import Affine


def mask_to_road_polygons(
    mask: np.ndarray,
    min_area: float = 20.0,
    simplify_tolerance: float = 1.0,
    transform: Optional[Affine] = None,
) -> List[shapely.geometry.Polygon]:
    """
    Convert a binary road mask into GIS polygon geometries.
    Repairs self-intersections and filters out spurious noise.
    """
    bin_mask = (mask > 0).astype(np.uint8)
    contours, hierarchy = cv2.findContours(
        bin_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    
    if hierarchy is None or len(contours) == 0:
        return []
        
    polygons = []
    hierarchy = hierarchy[0]
    
    for i, h in enumerate(hierarchy):
        parent_idx = h[3]
        if parent_idx == -1:  # Exterior contour
            ext_pts = contours[i].squeeze(axis=1)
            if len(ext_pts) < 3:
                continue
                
            # Collect interior holes
            holes = []
            child_idx = h[2]
            while child_idx != -1:
                hole_pts = contours[child_idx].squeeze(axis=1)
                if len(hole_pts) >= 3:
                    holes.append(hole_pts)
                child_idx = hierarchy[child_idx][0]
                
            # Convert pixel coords to geographic if transform is provided
            if transform is not None:
                ext_geo = [transform * (pt[0], pt[1]) for pt in ext_pts]
                holes_geo = [[transform * (pt[0], pt[1]) for pt in hole] for hole in holes]
            else:
                ext_geo = ext_pts
                holes_geo = holes
                
            poly = shapely.geometry.Polygon(ext_geo, holes_geo)
            if not poly.is_valid:
                poly = make_valid(poly)
                
            if poly.is_empty:
                continue
                
            # Filter small fragments: if transform is provided, min_area in sq degrees is ~1e-9 (e.g. 30 px * (2.7e-6)^2)
            threshold_area = min_area if transform is None else min_area * (abs(transform.a * transform.e))
            if poly.area < threshold_area:
                continue
                
            if simplify_tolerance > 0:
                poly = poly.simplify(simplify_tolerance, preserve_topology=True)
                
            if isinstance(poly, shapely.geometry.Polygon):
                polygons.append(poly)
            elif isinstance(poly, shapely.geometry.MultiPolygon):
                for p in poly.geoms:
                    if p.area >= threshold_area:
                        polygons.append(p)
                        
    return polygons


def road_polygons_to_geojson(
    polygons: List[shapely.geometry.Polygon],
    crs_epsg: Optional[int] = 4326,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format extracted road polygons into a valid GeoJSON FeatureCollection."""
    features = []
    for idx, poly in enumerate(polygons):
        feat = {
            "type": "Feature",
            "id": f"ROAD_EXTRACTED_{idx:05d}",
            "properties": {
                "id": f"ROAD_EXTRACTED_{idx:05d}",
                "feature_type": "ROAD_CORRIDOR",
                "area_sq_units": round(float(poly.area), 2),
                "perimeter_units": round(float(poly.length), 2),
                "is_valid": poly.is_valid,
                "confidence": 0.85,
            },
            "geometry": shapely.geometry.mapping(poly),
        }
        features.append(feat)
        
    doc = {
        "type": "FeatureCollection",
        "metadata": source_metadata or {},
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{crs_epsg}"},
        } if crs_epsg else None,
        "features": features,
    }
    return doc
