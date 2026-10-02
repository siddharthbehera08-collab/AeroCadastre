import json
from typing import Any, Dict, List
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from shapely.geometry import shape, mapping

from backend.app.models.entities import (
    Parcel,
    Building,
    Road,
    TopologyIssue,
    Anomaly,
    VerificationRecord,
    FieldRoute,
    FieldTask,
)
from backend.app.utils.crs import compute_metric_area_perimeter, polsby_popper_compactness
from backend.app.utils.geojson import geom_to_geojson_dict, shape_to_wkb_element
from backend.gis.topology import validate_parcels_topology
from backend.gis.conflicts_anomalies import detect_conflicts_and_anomalies
from backend.gis.route_planner import plan_smart_field_routes


def recompute_scene_topology_and_routes(db: Session, project_id: str, scene_id: str) -> None:
    """Recompute topology issues, conflict flags, and field routes for a scene in PostGIS."""
    cand_parcels = (
        db.query(Parcel)
        .filter(
            Parcel.project_id == project_id,
            Parcel.scene_id == scene_id,
            Parcel.parcel_layer == "CANDIDATE",
        )
        .all()
    )
    parcel_dicts = [
        {
            "id": p.id,
            "crs": p.crs,
            "area_sqm": p.area_sqm,
            "geometry": geom_to_geojson_dict(p.geom, p.geometry_geojson),
        }
        for p in cand_parcels
    ]
    topo_res = validate_parcels_topology(scene_id, parcel_dicts)

    db.query(TopologyIssue).filter(
        TopologyIssue.project_id == project_id,
        TopologyIssue.scene_id == scene_id,
    ).delete(synchronize_session=False)

    for iss in topo_res["issues"]:
        iss_shp = shape(iss["geometry"])
        db.add(
            TopologyIssue(
                id=iss["id"],
                project_id=project_id,
                scene_id=scene_id,
                issue_type=iss["issue_type"],
                severity=iss["severity"],
                affected_features_json=json.dumps(iss["affected_features"]),
                area_sqm=iss["area_sqm"],
                explanation=iss["explanation"],
                resolved=False,
                crs="EPSG:4326",
                geometry_geojson=json.dumps(iss["geometry"]),
                geom=shape_to_wkb_element(iss_shp, srid=4326),
            )
        )

    for p in cand_parcels:
        p.topology_status = topo_res["parcel_topology_status"].get(p.id, "VALID")

    vtasks = (
        db.query(VerificationRecord)
        .filter(
            VerificationRecord.project_id == project_id,
            VerificationRecord.scene_id == scene_id,
        )
        .all()
    )
    v_dicts = [
        {
            "id": vt.id,
            "parcel_id": vt.parcel_id,
            "priority": vt.priority,
            "priority_score": vt.priority_score,
            "status": vt.status,
            "reasons": json.loads(vt.reasons_json or "[]"),
            "centroid_lon": vt.centroid_lon,
            "centroid_lat": vt.centroid_lat,
        }
        for vt in vtasks
    ]
    routes = plan_smart_field_routes(scene_id, v_dicts, num_clusters=2)
    db.query(FieldRoute).filter(
        FieldRoute.project_id == project_id, FieldRoute.scene_id == scene_id
    ).delete(synchronize_session=False)
    for rt in routes:
        rt_shp = shape(rt["geometry"])
        route_uid = f"{project_id}_{rt['id']}" if not rt["id"].startswith(project_id) else rt["id"]
        db.add(
            FieldRoute(
                id=route_uid,
                project_id=project_id,
                scene_id=scene_id,
                cluster_id=rt["cluster_id"],
                route_name=rt["route_name"],
                task_count=rt["task_count"],
                estimated_distance_m=rt["estimated_distance_m"],
                ordered_stops_json=json.dumps(rt["ordered_stops"]),
                disclaimer=rt["disclaimer"],
                geometry_geojson=json.dumps(rt["geometry"]),
                geom=shape_to_wkb_element(rt_shp, srid=4326),
            )
        )


def get_parcel_buildings(db: Session, parcel_id: str) -> List[Dict[str, Any]]:
    """
    Return all buildings intersecting a given parcel using PostGIS ST_Intersects(b.geom, p.geom)
    or linked by parcel_id.
    """
    parcel = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")

    sql = text(
        """
        SELECT
            b.id,
            b.project_id,
            b.parcel_id,
            b.scene_id,
            b.temporal_epoch,
            b.crs,
            b.area_sqm,
            b.perimeter_m,
            b.centroid_lon,
            b.centroid_lat,
            b.confidence,
            b.confidence_category,
            b.model_source,
            b.source_type,
            b.verification_status,
            ST_AsGeoJSON(b.geom) AS postgis_geojson,
            b.geometry_geojson,
            ROUND(CAST(ST_Area(ST_Transform(ST_Intersection(b.geom, p.geom), 32643)) AS numeric), 2) AS intersection_area_sqm
        FROM buildings b
        JOIN parcels p ON p.id = :parcel_id
        WHERE b.project_id = p.project_id
          AND b.scene_id = p.scene_id
          AND (b.parcel_id = :parcel_id OR ST_Intersects(b.geom, p.geom))
        ORDER BY b.id ASC
        """
    )
    rows = db.execute(sql, {"parcel_id": parcel_id}).mappings().all()
    results = []
    for r in rows:
        geom_str = r["postgis_geojson"] or r["geometry_geojson"]
        geom_dict = json.loads(geom_str) if geom_str else {"type": "Polygon", "coordinates": []}
        results.append(
            {
                "id": r["id"],
                "project_id": r["project_id"],
                "parcel_id": r["parcel_id"] or parcel_id,
                "scene_id": r["scene_id"],
                "temporal_epoch": r["temporal_epoch"],
                "crs": r["crs"],
                "area_sqm": float(r["area_sqm"]),
                "perimeter_m": float(r["perimeter_m"]),
                "intersection_area_sqm": float(r["intersection_area_sqm"] or 0.0),
                "centroid_lon": float(r["centroid_lon"]),
                "centroid_lat": float(r["centroid_lat"]),
                "confidence": float(r["confidence"]),
                "confidence_category": r["confidence_category"],
                "model_source": r["model_source"],
                "source_type": r["source_type"],
                "verification_status": r["verification_status"],
                "geometry": geom_dict,
            }
        )
    return results


def get_project_roads(
    db: Session, project_id: str, scene_id: str = None
) -> List[Dict[str, Any]]:
    """Return all roads for a project using PostGIS geometry serialization."""
    q = db.query(Road).filter(Road.project_id == project_id)
    if scene_id:
        q = q.filter(Road.scene_id == scene_id)
    roads = q.order_by(Road.id.asc()).all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "scene_id": r.scene_id,
            "temporal_epoch": r.temporal_epoch,
            "road_class": r.road_class,
            "width_m": r.width_m,
            "length_m": r.length_m,
            "crs": r.crs,
            "confidence": r.confidence,
            "model_source": r.model_source,
            "source_type": r.source_type,
            "verification_status": r.verification_status,
            "geometry": geom_to_geojson_dict(r.geom, r.geometry_geojson),
            "corridor_geometry": (
                json.loads(r.corridor_geojson) if r.corridor_geojson else None
            ),
        }
        for r in roads
    ]


def get_parcel_topology(db: Session, parcel_id: str) -> Dict[str, Any]:
    """
    Evaluate and return PostGIS spatial topology diagnostics and persisted TopologyIssue rows
    for a single parcel.
    """
    parcel = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")

    # 1. Native PostGIS spatial metrics & validity check on target parcel
    metrics_sql = text(
        """
        SELECT
            ST_IsValid(geom) AS is_valid,
            ST_IsValidReason(geom) AS validity_reason,
            ST_SRID(geom) AS srid,
            ROUND(CAST(ST_Area(ST_Transform(geom, 32643)) AS numeric), 2) AS postgis_area_sqm,
            ROUND(CAST(ST_Perimeter(ST_Transform(geom, 32643)) AS numeric), 2) AS postgis_perimeter_m,
            ST_AsGeoJSON(geom) AS geojson_str
        FROM parcels
        WHERE id = :parcel_id
        """
    )
    m_row = db.execute(metrics_sql, {"parcel_id": parcel_id}).mappings().first()

    # 2. Native PostGIS pairwise spatial relationships (neighbors, overlaps, distances)
    neighbors_sql = text(
        """
        SELECT
            b.id AS neighbor_id,
            ST_Intersects(a.geom, b.geom) AS intersects,
            ST_Overlaps(a.geom, b.geom) AS overlaps,
            ST_Touches(a.geom, b.geom) AS touches,
            ROUND(CAST(ST_Area(ST_Transform(ST_Intersection(a.geom, b.geom), 32643)) AS numeric), 2) AS overlap_area_sqm,
            ROUND(CAST(ST_Distance(ST_Transform(a.geom, 32643), ST_Transform(b.geom, 32643)) AS numeric), 2) AS distance_m
        FROM parcels a
        JOIN parcels b
          ON a.project_id = b.project_id
         AND a.scene_id = b.scene_id
         AND b.parcel_layer = 'CANDIDATE'
         AND b.id <> a.id
        WHERE a.id = :parcel_id
          AND ST_DWithin(ST_Transform(a.geom, 32643), ST_Transform(b.geom, 32643), 25.0)
        ORDER BY distance_m ASC
        """
    )
    neighbor_rows = db.execute(neighbors_sql, {"parcel_id": parcel_id}).mappings().all()

    # 3. Persisted topology issues affecting this parcel
    all_issues = (
        db.query(TopologyIssue)
        .filter(
            TopologyIssue.project_id == parcel.project_id,
            TopologyIssue.scene_id == parcel.scene_id,
        )
        .all()
    )
    parcel_issues = []
    for iss in all_issues:
        affected = json.loads(iss.affected_features_json or "[]")
        if parcel_id in affected:
            parcel_issues.append(
                {
                    "id": iss.id,
                    "issue_type": iss.issue_type,
                    "severity": iss.severity,
                    "affected_features": affected,
                    "area_sqm": iss.area_sqm,
                    "explanation": iss.explanation,
                    "resolved": iss.resolved,
                    "geometry": geom_to_geojson_dict(iss.geom, iss.geometry_geojson),
                }
            )

    area_val = float(m_row["postgis_area_sqm"] or parcel.area_sqm)
    perim_val = float(m_row["postgis_perimeter_m"] or parcel.perimeter_m)

    return {
        "parcel_id": parcel.id,
        "project_id": parcel.project_id,
        "scene_id": parcel.scene_id,
        "topology_status": parcel.topology_status,
        "is_valid": bool(m_row["is_valid"]) if m_row else True,
        "validity_reason": m_row["validity_reason"] if m_row else "Valid Geometry",
        "srid": int(m_row["srid"] or 4326) if m_row else 4326,
        "metric_crs": "EPSG:32643",
        "postgis_area_sqm": area_val,
        "postgis_perimeter_m": perim_val,
        "compactness": polsby_popper_compactness(area_val, perim_val),
        "spatial_neighbors": [
            {
                "neighbor_id": nr["neighbor_id"],
                "intersects": bool(nr["intersects"]),
                "overlaps": bool(nr["overlaps"]),
                "touches": bool(nr["touches"]),
                "overlap_area_sqm": float(nr["overlap_area_sqm"] or 0.0),
                "distance_m": float(nr["distance_m"] or 0.0),
            }
            for nr in neighbor_rows
        ],
        "issue_count": len(parcel_issues),
        "issues": parcel_issues,
    }


def get_parcel_conflicts(db: Session, parcel_id: str) -> Dict[str, Any]:
    """
    Evaluate and return GIS conflicts and spatial anomalies for a single parcel using PostGIS
    spatial queries against reference parcels, buildings, and roads, plus persisted Anomaly records.
    """
    parcel = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")

    # 1. Native PostGIS comparison against Reference GIS layer (if present)
    ref_sql = text(
        """
        SELECT
            r.id AS reference_id,
            ROUND(CAST(ST_Area(ST_Transform(r.geom, 32643)) AS numeric), 2) AS reference_area_sqm,
            ROUND(CAST(ST_Area(ST_Transform(ST_Intersection(p.geom, r.geom), 32643)) AS numeric), 2) AS intersection_sqm,
            ROUND(CAST(ST_Area(ST_Transform(ST_Union(p.geom, r.geom), 32643)) AS numeric), 2) AS union_sqm
        FROM parcels p
        JOIN parcels r
          ON r.project_id = p.project_id
         AND r.scene_id = p.scene_id
         AND r.parcel_layer = 'REFERENCE'
         AND ST_Intersects(p.geom, r.geom)
        WHERE p.id = :parcel_id
        ORDER BY intersection_sqm DESC
        LIMIT 1
        """
    )
    ref_row = db.execute(ref_sql, {"parcel_id": parcel_id}).mappings().first()
    ref_alignment = None
    if ref_row and float(ref_row["union_sqm"] or 0) > 0:
        iou = float(ref_row["intersection_sqm"]) / float(ref_row["union_sqm"])
        ref_alignment = {
            "reference_id": ref_row["reference_id"],
            "reference_area_sqm": float(ref_row["reference_area_sqm"]),
            "intersection_sqm": float(ref_row["intersection_sqm"]),
            "spatial_iou": round(iou, 4),
            "legal_notice": "Reference GIS is a non-authoritative legacy layer for discrepancy screening.",
        }

    # 2. Persisted Anomaly & GIS Conflict records for this parcel
    anom_rows = (
        db.query(Anomaly)
        .filter(
            Anomaly.project_id == parcel.project_id,
            Anomaly.parcel_id == parcel_id,
        )
        .order_by(Anomaly.id.asc())
        .all()
    )
    conflicts = []
    anomalies = []
    for a in anom_rows:
        item = {
            "id": a.id,
            "parcel_id": a.parcel_id,
            "category": a.category,
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "confidence": a.confidence,
            "explanation": a.explanation,
            "evidence": json.loads(a.evidence_json or "{}"),
            "geometry": geom_to_geojson_dict(a.geom, a.geometry_geojson),
        }
        if a.category == "GIS_CONFLICT":
            conflicts.append(item)
        else:
            anomalies.append(item)

    return {
        "parcel_id": parcel.id,
        "project_id": parcel.project_id,
        "scene_id": parcel.scene_id,
        "conflict_status": parcel.conflict_status,
        "anomaly_status": parcel.anomaly_status,
        "reference_gis_alignment": ref_alignment,
        "conflict_count": len(conflicts),
        "anomaly_count": len(anomalies),
        "conflicts": conflicts,
        "anomalies": anomalies,
        "all_records": conflicts + anomalies,
    }
