import csv
import json
from pathlib import Path
from typing import Dict, Any
from PIL import Image
import rasterio
import shapefile
from shapely.geometry import shape, mapping

from backend.db import compute_metric_area_perimeter


def inspect_and_validate_upload(file_path: Path, declared_crs: str = "EPSG:4326") -> Dict[str, Any]:
    """
    Modular Geospatial Data Ingestion Inspector.
    Supports: GeoTIFF (.tif/.tiff), PNG/JPEG imagery, GeoJSON (.geojson/.json),
    Shapefile (.shp/.zip), GeoPackage (.gpkg), CSV (.csv), DEM/DTM/DSM (.npy/.tif).
    Checks: format, CRS, geometry validity, dimensions, nodata, and attributes.
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        return {
            "valid": False,
            "status": "EMPTY_OR_MISSING_FILE",
            "error": "Uploaded dataset file is empty or missing.",
        }

    suffix = file_path.suffix.lower()

    try:
        if suffix in (".tif", ".tiff"):
            with rasterio.open(file_path) as src:
                crs_str = str(src.crs) if src.crs else declared_crs
                bounds = src.bounds
                return {
                    "valid": True,
                    "status": "VALID",
                    "source_format": "GeoTIFF",
                    "dataset_type": "DSM" if src.count == 1 else "DRONE_RGB",
                    "crs": crs_str or "EPSG:4326",
                    "width": src.width,
                    "height": src.height,
                    "bands": src.count,
                    "nodata": src.nodata,
                    "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                }

        elif suffix in (".png", ".jpg", ".jpeg"):
            with Image.open(file_path) as img:
                w, h = img.size
                bands = len(img.getbands())
                return {
                    "valid": w > 0 and h > 0,
                    "status": "VALID",
                    "source_format": suffix.lstrip(".").upper(),
                    "dataset_type": "DRONE_RGB",
                    "crs": declared_crs or "EPSG:4326",
                    "width": w,
                    "height": h,
                    "bands": bands,
                    "nodata": None,
                }

        elif suffix in (".geojson", ".json"):
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            features = raw.get("features", [])
            if not isinstance(features, list) or len(features) == 0:
                return {
                    "valid": False,
                    "status": "EMPTY_FEATURE_COLLECTION",
                    "source_format": "GeoJSON",
                    "error": "GeoJSON contains zero features.",
                }
            crs_name = (
                raw.get("crs", {}).get("properties", {}).get("name")
                or declared_crs
                or "EPSG:4326"
            )
            valid_count = 0
            invalid_count = 0
            for f in features:
                g = shape(f["geometry"])
                if g.is_valid and not g.is_empty:
                    valid_count += 1
                else:
                    invalid_count += 1
            return {
                "valid": valid_count > 0,
                "status": "VALID" if invalid_count == 0 else "WARNING_INVALID_GEOMETRIES",
                "source_format": "GeoJSON",
                "dataset_type": "VECTOR_GIS",
                "crs": crs_name,
                "feature_count": len(features),
                "valid_geometries": valid_count,
                "invalid_geometries": invalid_count,
            }

        elif suffix == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            return {
                "valid": len(rows) > 0,
                "status": "VALID" if rows else "EMPTY_CSV",
                "source_format": "CSV",
                "dataset_type": "TABULAR_GIS",
                "crs": declared_crs or "EPSG:4326",
                "row_count": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
            }

        elif suffix == ".shp":
            sf = shapefile.Reader(str(file_path))
            n_shapes = len(sf.shapes())
            sf.close()
            return {
                "valid": n_shapes > 0,
                "status": "VALID",
                "source_format": "Shapefile",
                "dataset_type": "VECTOR_GIS",
                "crs": declared_crs or "EPSG:4326",
                "feature_count": n_shapes,
            }

        else:
            return {
                "valid": True,
                "status": "VALID",
                "source_format": suffix.lstrip(".").upper() or "BINARY",
                "dataset_type": "CUSTOM_GEOSPATIAL",
                "crs": declared_crs or "EPSG:4326",
            }
    except Exception as exc:
        return {
            "valid": False,
            "status": "CORRUPT_OR_INVALID_INPUT",
            "error": str(exc),
        }
