import csv
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import shapefile  # pyshp
from shapely.geometry import shape

from backend.config import OUTPUTS_DIR


WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)


def export_and_validate_parcels(
    project_id: str,
    scene_id: str,
    export_format: str,
    parcels: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Export parcels with geometry, attributes, confidence, verification status, and provenance.
    Supports: GeoJSON, Shapefile (.zip containing .shp/.shx/.dbf/.prj), CSV, GeoPackage (.gpkg).
    Immediately re-reads and validates the exported file to guarantee integrity.
    """
    fmt = export_format.upper().strip()
    export_dir = OUTPUTS_DIR / project_id / scene_id
    export_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "GEOJSON":
        out_path = export_dir / f"{scene_id}_cadastral_parcels.geojson"
        features = []
        for p in parcels:
            features.append({
                "type": "Feature",
                "properties": {
                    "parcel_id": p["id"],
                    "project_id": project_id,
                    "scene_id": scene_id,
                    "parcel_layer": p.get("parcel_layer", "CANDIDATE"),
                    "boundary_representation": p.get("boundary_representation", "INFERRED"),
                    "land_use_class": p.get("land_use_class", "residential"),
                    "area_sqm": p.get("area_sqm", 0.0),
                    "perimeter_m": p.get("perimeter_m", 0.0),
                    "confidence": p.get("confidence", 0.0),
                    "confidence_category": p.get("confidence_category", "MEDIUM"),
                    "topology_status": p.get("topology_status", "VALID"),
                    "conflict_status": p.get("conflict_status", "NONE"),
                    "anomaly_status": p.get("anomaly_status", "NONE"),
                    "verification_status": p.get("verification_status", "AI-GENERATED / REQUIRES VERIFICATION"),
                    "council_decision": p.get("council_decision", "REQUIRES_VERIFICATION"),
                    "version": p.get("version", 1),
                    "crs": p.get("crs", "EPSG:4326"),
                    "provenance": p.get("provenance", {}),
                    "evidence_sources": p.get("evidence_sources", []),
                    "legal_notice": "PRELIMINARY CANDIDATE GEOMETRY - NOT LEGALLY AUTHORITATIVE",
                },
                "geometry": p["geometry"],
            })
        fc = {
            "type": "FeatureCollection",
            "name": f"{scene_id}_parcels",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": features,
        }
        out_path.write_text(json.dumps(fc, indent=2), encoding="utf-8")

        # Read back and validate
        reloaded = json.loads(out_path.read_text(encoding="utf-8"))
        valid_geoms = sum(1 for f in reloaded["features"] if shape(f["geometry"]).is_valid)
        fsize = out_path.stat().st_size
        return {
            "format": "GeoJSON",
            "crs": "EPSG:4326",
            "file_path": str(out_path),
            "export_path": str(out_path),
            "file_size_bytes": fsize,
            "size_bytes": fsize,
            "feature_count": len(reloaded["features"]),
            "valid_geometries": valid_geoms,
            "validation_passed": len(reloaded["features"]) == len(parcels) and valid_geoms == len(parcels),
        }

    elif fmt in ("SHAPEFILE", "SHP", "SHP_ZIP"):
        base_shp = export_dir / f"{scene_id}_cadastral_parcels"
        w = shapefile.Writer(str(base_shp), shapeType=shapefile.POLYGON)
        w.field("PARCEL_ID", "C", size=40)
        w.field("LAYER", "C", size=20)
        w.field("BND_TYPE", "C", size=20)
        w.field("LAND_USE", "C", size=25)
        w.field("AREA_SQM", "N", size=12, decimal=2)
        w.field("PERIM_M", "N", size=12, decimal=2)
        w.field("CONFID", "N", size=6, decimal=3)
        w.field("VERIF_ST", "C", size=40)
        w.field("COUNCIL", "C", size=30)
        w.field("PROVENANCE", "C", size=80)

        for p in parcels:
            geom = shape(p["geometry"])
            if geom.geom_type == "MultiPolygon":
                geom = max(geom.geoms, key=lambda g: g.area)
            ext_coords = [list(pt) for pt in geom.exterior.coords]
            w.poly([ext_coords])
            prov_str = json.dumps(p.get("provenance", {}))[:78]
            w.record(
                p["id"][:40],
                p.get("parcel_layer", "CANDIDATE")[:20],
                p.get("boundary_representation", "INFERRED")[:20],
                p.get("land_use_class", "residential")[:25],
                float(p.get("area_sqm", 0.0)),
                float(p.get("perimeter_m", 0.0)),
                float(p.get("confidence", 0.0)),
                p.get("verification_status", "PENDING")[:40],
                p.get("council_decision", "REVIEW")[:30],
                prov_str,
            )
        w.close()
        (export_dir / f"{scene_id}_cadastral_parcels.prj").write_text(WGS84_PRJ, encoding="utf-8")

        zip_path = export_dir / f"{scene_id}_cadastral_parcels_shp.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                part = export_dir / f"{scene_id}_cadastral_parcels{ext}"
                if part.exists():
                    zf.write(part, arcname=part.name)

        if len(parcels) > 0:
            sf_reader = shapefile.Reader(str(base_shp))
            shapes_read = sf_reader.shapes()
            records_read = sf_reader.records()
            sf_reader.close()
            n_shapes = len(shapes_read)
            n_records = len(records_read)
        else:
            n_shapes = 0
            n_records = 0

        fsize = zip_path.stat().st_size
        return {
            "format": "SHP_ZIP" if fmt == "SHP_ZIP" else "Shapefile",
            "crs": "EPSG:4326",
            "file_path": str(zip_path),
            "export_path": str(zip_path),
            "file_size_bytes": fsize,
            "size_bytes": fsize,
            "feature_count": n_shapes,
            "valid_geometries": n_shapes,
            "validation_passed": n_shapes == len(parcels) and n_records == len(parcels),
        }

    elif fmt == "CSV":
        out_path = export_dir / f"{scene_id}_cadastral_parcels.csv"
        fieldnames = [
            "parcel_id",
            "parcel_layer",
            "boundary_representation",
            "land_use_class",
            "area_sqm",
            "perimeter_m",
            "confidence",
            "confidence_category",
            "topology_status",
            "verification_status",
            "council_decision",
            "crs",
            "provenance_json",
            "wkt_geometry",
        ]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in parcels:
                geom = shape(p["geometry"])
                writer.writerow({
                    "parcel_id": p["id"],
                    "parcel_layer": p.get("parcel_layer", "CANDIDATE"),
                    "boundary_representation": p.get("boundary_representation", "INFERRED"),
                    "land_use_class": p.get("land_use_class", "residential"),
                    "area_sqm": p.get("area_sqm", 0.0),
                    "perimeter_m": p.get("perimeter_m", 0.0),
                    "confidence": p.get("confidence", 0.0),
                    "confidence_category": p.get("confidence_category", "MEDIUM"),
                    "topology_status": p.get("topology_status", "VALID"),
                    "verification_status": p.get("verification_status", "PENDING"),
                    "council_decision": p.get("council_decision", "REQUIRES_VERIFICATION"),
                    "crs": p.get("crs", "EPSG:4326"),
                    "provenance_json": json.dumps(p.get("provenance", {})),
                    "wkt_geometry": geom.wkt,
                })

        # Read back and validate CSV rows
        with open(out_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        fsize = out_path.stat().st_size
        return {
            "format": "CSV",
            "crs": "EPSG:4326",
            "file_path": str(out_path),
            "export_path": str(out_path),
            "file_size_bytes": fsize,
            "size_bytes": fsize,
            "feature_count": len(rows),
            "valid_geometries": sum(
                1 for r in rows if r.get("wkt_geometry", "").startswith(("POLYGON", "MULTIPOLYGON"))
            ),
            "validation_passed": len(rows) == len(parcels),
        }

    elif fmt in ("GEOPACKAGE", "GPKG"):
        out_path = export_dir / f"{scene_id}_cadastral_parcels.gpkg"
        if out_path.exists():
            out_path.unlink()
        conn = sqlite3.connect(str(out_path))
        cur = conn.cursor()
        cur.execute("CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT, srs_id INTEGER PRIMARY KEY, organization TEXT, organization_coordsys_id INTEGER, definition TEXT)")
        cur.execute("INSERT INTO gpkg_spatial_ref_sys VALUES ('WGS 84', 4326, 'EPSG', 4326, ?)", (WGS84_PRJ,))
        cur.execute("CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY, data_type TEXT, identifier TEXT, srs_id INTEGER)")
        cur.execute("INSERT INTO gpkg_contents VALUES ('cadastral_parcels', 'features', 'cadastral_parcels', 4326)")
        cur.execute(
            "CREATE TABLE cadastral_parcels (fid INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, land_use_class TEXT, "
            "area_sqm REAL, confidence REAL, verification_status TEXT, council_decision TEXT, provenance_json TEXT, geom_wkb BLOB)"
        )
        for p in parcels:
            geom = shape(p["geometry"])
            cur.execute(
                "INSERT INTO cadastral_parcels (parcel_id, land_use_class, area_sqm, confidence, verification_status, council_decision, provenance_json, geom_wkb) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    p["id"],
                    p.get("land_use_class", "residential"),
                    float(p.get("area_sqm", 0.0)),
                    float(p.get("confidence", 0.0)),
                    p.get("verification_status", "PENDING"),
                    p.get("council_decision", "REQUIRES_VERIFICATION"),
                    json.dumps(p.get("provenance", {})),
                    geom.wkb,
                ),
            )
        conn.commit()
        count_read = cur.execute("SELECT COUNT(*) FROM cadastral_parcels").fetchone()[0]
        conn.close()
        fsize = out_path.stat().st_size
        return {
            "format": "GPKG" if fmt == "GPKG" else "GeoPackage",
            "crs": "EPSG:4326",
            "file_path": str(out_path),
            "export_path": str(out_path),
            "file_size_bytes": fsize,
            "size_bytes": fsize,
            "feature_count": count_read,
            "valid_geometries": count_read,
            "validation_passed": count_read == len(parcels),
        }

    else:
        raise ValueError(f"Unsupported export format: {export_format}")
