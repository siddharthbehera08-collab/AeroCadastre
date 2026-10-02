import json
from typing import Any, Dict, Optional, Sequence, Tuple
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import from_shape, to_shape
from shapely import wkt
from shapely.geometry import shape, mapping
from shapely.validation import explain_validity, make_valid

from backend.app.utils.crs import validate_crs_code, project_to_4326


def validate_and_parse_geojson(
    geom_input: Any,
    expected_types: Sequence[str] = ("Polygon", "MultiPolygon"),
    crs: str = "EPSG:4326",
    allow_make_valid: bool = False,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Validate a GeoJSON geometry dictionary or Feature and return (shapely_geom_4326, geojson_dict).
    Raises ValueError on malformed coordinates, invalid CRS, self-intersections (when allow_make_valid=False),
    or unsupported geometry types.
    """
    srid = validate_crs_code(crs)

    if isinstance(geom_input, str):
        try:
            geom_input = json.loads(geom_input)
        except Exception as exc:
            raise ValueError(f"Malformed JSON in geometry payload: {exc}") from exc

    if not isinstance(geom_input, dict):
        raise ValueError("Geometry must be a GeoJSON object (dict).")

    if geom_input.get("type") == "Feature":
        geom_input = geom_input.get("geometry") or {}

    g_type = geom_input.get("type")
    coords = geom_input.get("coordinates")
    if not g_type or coords is None:
        raise ValueError("GeoJSON geometry requires 'type' and 'coordinates' fields.")

    if expected_types and g_type not in expected_types:
        raise ValueError(
            f"Unsupported geometry type '{g_type}'. Expected one of {list(expected_types)}."
        )

    try:
        geom = shape(geom_input)
    except Exception as exc:
        raise ValueError(f"Invalid GeoJSON coordinates structure: {exc}") from exc

    if geom.is_empty:
        raise ValueError("Geometry cannot be empty.")

    if srid != 4326:
        geom = project_to_4326(geom, crs)

    minx, miny, maxx, maxy = geom.bounds
    if minx < -180.0 or maxx > 180.0 or miny < -90.0 or maxy > 90.0:
        raise ValueError(
            f"Geometry coordinates ({minx:.4f}, {miny:.4f}, {maxx:.4f}, {maxy:.4f}) exceed EPSG:4326 WGS84 bounds."
        )

    if not geom.is_valid:
        reason = explain_validity(geom)
        if not allow_make_valid:
            raise ValueError(f"Invalid OGC geometry topology: {reason}")
        geom = make_valid(geom)
        if geom.geom_type == "GeometryCollection":
            polys = [g for g in geom.geoms if g.geom_type in expected_types]
            if not polys:
                raise ValueError(f"Geometry repair failed for: {reason}")
            geom = max(polys, key=lambda g: g.area)

    return geom, mapping(geom)


def shape_to_wkb_element(geom, srid: int = 4326) -> WKBElement:
    """Convert a Shapely geometry into a GeoAlchemy2 WKBElement with SRID."""
    return from_shape(geom, srid=srid)


def geom_to_geojson_dict(
    geom_col: Optional[Any],
    fallback_geojson_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a PostGIS WKBElement, WKT string, or JSON string into a GeoJSON dictionary."""
    if geom_col is not None:
        try:
            if isinstance(geom_col, (WKBElement, WKTElement)):
                shp = to_shape(geom_col)
                return mapping(shp)
            if isinstance(geom_col, str):
                s = geom_col.strip()
                if s.startswith("{"):
                    return json.loads(s)
                return mapping(wkt.loads(s))
        except Exception:
            pass
    if fallback_geojson_str:
        try:
            return json.loads(fallback_geojson_str)
        except Exception:
            pass
    return {"type": "Polygon", "coordinates": []}


def to_geojson_feature(
    feature_id: str,
    geometry_dict: Dict[str, Any],
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": geometry_dict,
        "properties": properties,
    }


def to_geojson_feature_collection(
    features: Sequence[Dict[str, Any]],
    crs_name: str = "EPSG:4326",
) -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": crs_name}},
        "features": list(features),
    }
