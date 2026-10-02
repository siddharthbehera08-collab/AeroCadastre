import math
from typing import Tuple
from pyproj import Transformer
from shapely.ops import transform as shapely_transform

_TO_UTM43N = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
_FROM_UTM43N = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
_TO_UTM43N_FROM_3857 = Transformer.from_crs("EPSG:3857", "EPSG:32643", always_xy=True)

SUPPORTED_CRS_SRIDS = {
    "EPSG:4326": 4326,
    "EPSG:32643": 32643,
    "EPSG:3857": 3857,
    "WGS84": 4326,
}


def validate_crs_code(crs_str: str) -> int:
    norm = (crs_str or "EPSG:4326").strip().upper()
    if norm not in SUPPORTED_CRS_SRIDS:
        raise ValueError(
            f"Unsupported CRS '{crs_str}'. Supported CRS: {list(SUPPORTED_CRS_SRIDS.keys())}"
        )
    return SUPPORTED_CRS_SRIDS[norm]


def project_to_4326(geom, source_crs: str = "EPSG:4326"):
    srid = validate_crs_code(source_crs)
    if srid == 4326:
        return geom
    if srid == 32643:
        return shapely_transform(_FROM_UTM43N.transform, geom)
    if srid == 3857:
        tf = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
        return shapely_transform(tf.transform, geom)
    return geom


def compute_metric_area_perimeter(geom) -> Tuple[float, float]:
    """Compute metric area (m²) and perimeter/length (m) in EPSG:32643 (UTM Zone 43N)."""
    if geom is None or geom.is_empty:
        return 0.0, 0.0
    try:
        minx, miny, maxx, maxy = geom.bounds
        if -180.0 <= minx <= 180.0 and -90.0 <= miny <= 90.0 and (maxx - minx) < 10.0:
            projected = shapely_transform(_TO_UTM43N.transform, geom)
            return float(round(projected.area, 2)), float(round(projected.length, 2))
        return float(round(geom.area, 2)), float(round(geom.length, 2))
    except Exception:
        return 0.0, 0.0


def polsby_popper_compactness(area_sqm: float, perimeter_m: float) -> float:
    if perimeter_m <= 1e-6 or area_sqm <= 0:
        return 0.0
    return round(float(min(1.0, (4.0 * math.pi * area_sqm) / (perimeter_m ** 2))), 4)
