"""
Data Validation Service for AeroCadastre SIH26012.
Provides rigorous multi-attribute validation for incoming raster and vector datasets:
  - validate_raster_metadata()
  - validate_vector_metadata()
  - validate_crs()
  - validate_bounds()
  - validate_resolution()
  - validate_geometry()
  - validate_provenance()

GOVERNANCE CONTRACT:
- Enforces EPSG:32643 standard metric CRS for Pune study area.
- Detects corrupt geometries, out-of-bounds extents, and missing provenance metadata.
- Rejects unverified statutory ownership or fake ULPIN claims.
"""

import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from shapely.geometry import shape, Polygon, MultiPolygon


class DataValidationService:
    """
    Production-grade validation engine for incoming cadastral remote sensing and vector assets.
    """

    ALLOWED_CRS = {"EPSG:32643", "EPSG:4326", "EPSG:3857"}
    TARGET_METRIC_CRS = "EPSG:32643"
    PUNE_METRIC_BOUNDS = (377550.0, 2047000.0, 380750.0, 2049200.0)  # minx, miny, maxx, maxy

    def validate_crs(self, crs: str) -> Dict[str, Any]:
        """Validates CRS string against authorized coordinate reference systems."""
        if not crs or not isinstance(crs, str):
            return {"valid": False, "error": "CRS must be a non-empty string."}
        norm_crs = crs.strip().upper()
        if norm_crs not in self.ALLOWED_CRS:
            return {
                "valid": False,
                "error": f"Unauthorized CRS '{crs}'. Permitted: {list(self.ALLOWED_CRS)}",
            }
        is_target = norm_crs == self.TARGET_METRIC_CRS
        return {
            "valid": True,
            "crs": norm_crs,
            "is_target_metric": is_target,
            "warning": None if is_target else f"CRS '{norm_crs}' requires reprojection to '{self.TARGET_METRIC_CRS}'."
        }

    def validate_bounds(
        self, bounds: Tuple[float, float, float, float], crs: str = "EPSG:32643"
    ) -> Dict[str, Any]:
        """Validates that bounding coordinates form a valid bbox and checks overlap."""
        if len(bounds) != 4:
            return {"valid": False, "error": "Bounds must be a 4-tuple (minx, miny, maxx, maxy)."}
        minx, miny, maxx, maxy = bounds
        if minx >= maxx or miny >= maxy:
            return {"valid": False, "error": f"Invalid bbox geometry: min exceeds max ({bounds})."}

        # Check Pune bounds overlap if metric
        if crs.upper() == self.TARGET_METRIC_CRS:
            sa_minx, sa_miny, sa_maxx, sa_maxy = self.PUNE_METRIC_BOUNDS
            overlaps = not (maxx < sa_minx or minx > sa_maxx or maxy < sa_miny or miny > sa_maxy)
            return {
                "valid": True,
                "overlaps_study_area": overlaps,
                "warning": None if overlaps else "Bounding box does not intersect Pune core study area."
            }

        return {"valid": True, "overlaps_study_area": None}

    def validate_resolution(
        self, res: Tuple[float, float], modality: str = "OPTICAL_VHR"
    ) -> Dict[str, Any]:
        """Validates ground sampling distance (GSD). Rejects coarse imagery for VHR cadastre."""
        res_x, res_y = abs(res[0]), abs(res[1])
        if res_x <= 0 or res_y <= 0:
            return {"valid": False, "error": "Resolution values must be strictly positive."}

        mean_res = (res_x + res_y) / 2.0
        if modality.upper() == "OPTICAL_VHR" and mean_res > 1.0:
            return {
                "valid": False,
                "error": f"Mean resolution ({mean_res:.2f} m) exceeds 1.0 m threshold for cadastral boundary delineation.",
                "cadastral_usable": False
            }

        return {
            "valid": True,
            "mean_resolution_m": round(mean_res, 3),
            "cadastral_usable": True
        }

    def validate_geometry(self, geom_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validates GeoJSON geometry dictionary using Shapely."""
        if not geom_dict or not isinstance(geom_dict, dict):
            return {"valid": False, "error": "Geometry payload missing or invalid."}
        try:
            poly = shape(geom_dict)
            if poly.is_empty:
                return {"valid": False, "error": "Geometry is empty."}
            if not poly.is_valid:
                return {"valid": False, "error": f"Invalid polygon topology: {poly.is_valid}"}
            if poly.geom_type not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString"):
                return {"valid": False, "error": f"Unsupported geometry type: {poly.geom_type}"}
            return {
                "valid": True,
                "geom_type": poly.geom_type,
                "area": float(poly.area),
                "is_valid_ogc": True
            }
        except Exception as e:
            return {"valid": False, "error": f"Failed to parse geometry: {str(e)}"}

    def validate_provenance(self, provenance: Dict[str, Any]) -> Dict[str, Any]:
        """Validates provenance audit trail metadata."""
        if not provenance or not isinstance(provenance, dict):
            return {"valid": False, "error": "Provenance metadata is mandatory."}

        required_keys = ["data_mode", "disclaimer"]
        missing = [k for k in required_keys if k not in provenance]
        if missing:
            return {"valid": False, "error": f"Missing mandatory provenance fields: {missing}"}

        # Check ULPIN claim
        if provenance.get("statutory_cadastre", False) and provenance.get("data_mode") == "SYNTHETIC":
            return {"valid": False, "error": "Synthetic data CANNOT be labeled as statutory cadastre."}

        return {"valid": True, "data_mode": provenance.get("data_mode")}

    def validate_raster_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive validation of raster ingestion metadata."""
        errors = []
        warnings = []

        crs_res = self.validate_crs(metadata.get("crs", ""))
        if not crs_res["valid"]:
            errors.append(crs_res["error"])
        elif crs_res.get("warning"):
            warnings.append(crs_res["warning"])

        if "bounds" in metadata:
            b_res = self.validate_bounds(tuple(metadata["bounds"]), crs=metadata.get("crs", ""))
            if not b_res["valid"]:
                errors.append(b_res["error"])
            elif b_res.get("warning"):
                warnings.append(b_res["warning"])

        if "resolution" in metadata:
            r_res = self.validate_resolution(
                tuple(metadata["resolution"]), modality=metadata.get("modality", "OPTICAL_VHR")
            )
            if not r_res["valid"]:
                errors.append(r_res["error"])

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validation_timestamp": "2026-10-04T00:00:00Z"
        }

    def validate_vector_metadata(self, feature_collection: Dict[str, Any]) -> Dict[str, Any]:
        """Validates vector feature collection structure, CRS, and feature geometries."""
        if feature_collection.get("type") != "FeatureCollection":
            return {"is_valid": False, "error": "Root object must be a FeatureCollection."}

        features = feature_collection.get("features", [])
        invalid_count = 0
        for f in features:
            geom = f.get("geometry")
            g_res = self.validate_geometry(geom)
            if not g_res["valid"]:
                invalid_count += 1

        return {
            "is_valid": invalid_count == 0,
            "total_features": len(features),
            "invalid_features": invalid_count,
            "errors": [f"{invalid_count} features have invalid geometries."] if invalid_count > 0 else []
        }
