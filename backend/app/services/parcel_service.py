import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from shapely.geometry import shape, mapping, LineString
from shapely.ops import unary_union, split as shapely_split

from backend.app.models.entities import (
    Project,
    Parcel,
    VerificationRecord,
    FieldTask,
    CouncilDecision,
    FeatureVersion,
    HumanFeedback,
)
from backend.app.schemas.api_schemas import (
    ParcelCreateRequest,
    ParcelUpdateRequest,
    ParcelSplitRequest,
    ParcelMergeRequest,
)
from backend.app.utils.crs import compute_metric_area_perimeter, polsby_popper_compactness
from backend.app.utils.geojson import (
    validate_and_parse_geojson,
    geom_to_geojson_dict,
    shape_to_wkb_element,
    to_geojson_feature,
)
from backend.app.core.security import assert_operator_can_mutate
from backend.app.utils.audit import record_audit_log
from backend.app.services.gis_service import recompute_scene_topology_and_routes


def serialize_parcel(p: Parcel) -> Dict[str, Any]:
    geom_dict = geom_to_geojson_dict(p.geom, p.geometry_geojson)
    props = {
        "id": p.id,
        "project_id": p.project_id,
        "scene_id": p.scene_id,
        "temporal_epoch": p.temporal_epoch,
        "parcel_layer": p.parcel_layer,
        "boundary_representation": p.boundary_representation,
        "land_use_class": p.land_use_class,
        "area_sqm": p.area_sqm,
        "perimeter_m": p.perimeter_m,
        "compactness": p.compactness,
        "building_count": p.building_count,
        "road_access": p.road_access,
        "dsm_mean_elevation_m": p.dsm_mean_elevation_m,
        "crs": p.crs,
        "confidence": p.confidence,
        "confidence_category": p.confidence_category,
        "confidence_breakdown": json.loads(p.confidence_breakdown_json or "{}"),
        "evidence_sources": json.loads(p.evidence_sources_json or "[]"),
        "topology_status": p.topology_status,
        "conflict_status": p.conflict_status,
        "anomaly_status": p.anomaly_status,
        "verification_status": p.verification_status,
        "verification_priority": p.verification_priority,
        "council_decision": p.council_decision,
        "ulpin_ready_metadata": json.loads(p.ulpin_ready_metadata_json or "{}"),
        "provenance": json.loads(p.provenance_json or "{}"),
        "version": p.version,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
    return {
        **props,
        "geometry": geom_dict,
        "geojson_feature": to_geojson_feature(p.id, geom_dict, props),
    }


def list_project_parcels(
    db: Session,
    project_id: str,
    scene_id: Optional[str] = None,
    layer: str = "CANDIDATE",
    bbox: Optional[str] = None,
) -> List[Dict[str, Any]]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404, detail=f"Project '{project_id}' not found."
        )

    q = db.query(Parcel).filter(
        Parcel.project_id == project_id,
        Parcel.parcel_layer == layer,
    )
    if scene_id:
        q = q.filter(Parcel.scene_id == scene_id)

    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError("bbox must have 4 comma-separated floats: minx,miny,maxx,maxy")
            minx, miny, maxx, maxy = parts
            q = q.filter(
                text(
                    "ST_Intersects(geom, ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))"
                ).bindparams(minx=minx, miny=miny, maxx=maxx, maxy=maxy)
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid bbox parameter: {exc}"
            ) from exc

    rows = q.order_by(Parcel.id.asc()).all()
    return [serialize_parcel(p) for p in rows]


def get_parcel_by_id(db: Session, parcel_id: str) -> Dict[str, Any]:
    p = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")
    return serialize_parcel(p)


def create_parcel(db: Session, req: ParcelCreateRequest) -> Dict[str, Any]:
    assert_operator_can_mutate(req.operator_id)
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(
            status_code=404, detail=f"Project '{req.project_id}' not found."
        )

    try:
        geom, geom_dict = validate_and_parse_geojson(
            req.geometry,
            expected_types=("Polygon", "MultiPolygon"),
            crs=req.crs,
            allow_make_valid=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    area_sqm, perim_m = compute_metric_area_perimeter(geom)
    if area_sqm < 1.0 or area_sqm > 5000000.0:
        raise HTTPException(
            status_code=400,
            detail=f"Parcel area ({area_sqm:.2f} m²) outside valid cadastral bounds [1.0, 5000000.0].",
        )

    comp = polsby_popper_compactness(area_sqm, perim_m)
    pid = (
        req.id
        or f"{req.scene_id}_P_MAN_{int(datetime.now(timezone.utc).timestamp() * 1000) % 100000:05d}"
    )
    if db.query(Parcel).filter(Parcel.id == pid).first():
        raise HTTPException(status_code=409, detail=f"Parcel '{pid}' already exists.")

    geom_json = json.dumps(geom_dict)
    wkb_geom = shape_to_wkb_element(geom, srid=4326)

    # Count buildings intersecting this new parcel in PostGIS
    bldg_count_sql = text(
        """
        SELECT count(*) FROM buildings
        WHERE project_id = :project_id
          AND scene_id = :scene_id
          AND ST_Intersects(geom, ST_GeomFromGeoJSON(:geojson))
        """
    )
    bldg_count = int(
        db.execute(
            bldg_count_sql,
            {
                "project_id": req.project_id,
                "scene_id": req.scene_id,
                "geojson": geom_json,
            },
        ).scalar()
        or 0
    )

    prov = {
        "feature_id": pid,
        "created_by": req.operator_id,
        "evidence_models": ["Human_Surveyor_WebGIS_Digitization"],
        "confidence": 0.99,
        "boundary_representation": req.boundary_representation,
        "crs": "EPSG:4326",
        "metric_crs": "EPSG:32643",
        "source_layers": ["Drone_RGB", "PostGIS_Surveyor_Digitization"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modified_by": req.operator_id,
        "verification_status": "HUMAN_VERIFIED",
        "data_label": "SYNTHETIC DEMO DATA",
    }

    ulpin_meta = {
        "mode": "ULPIN_READY_METADATA",
        "official_ulpin_assigned": False,
        "centroid_lon": round(geom.centroid.x, 7),
        "centroid_lat": round(geom.centroid.y, 7),
        "projected_crs": "EPSG:32643",
    }

    new_p = Parcel(
        id=pid,
        project_id=req.project_id,
        scene_id=req.scene_id,
        temporal_epoch="T1",
        parcel_layer="CANDIDATE",
        boundary_representation=req.boundary_representation,
        land_use_class=req.land_use_class,
        area_sqm=area_sqm,
        perimeter_m=perim_m,
        compactness=comp,
        building_count=bldg_count,
        road_access=True,
        dsm_mean_elevation_m=215.0,
        crs="EPSG:4326",
        confidence=0.99,
        confidence_category="HIGH",
        confidence_breakdown_json=json.dumps(
            {
                "vision_confidence": 0.99,
                "geometry_confidence": 0.99,
                "gis_consistency": 0.99,
                "ml_confidence": 0.99,
                "overall_confidence": 0.99,
            }
        ),
        evidence_sources_json=json.dumps(["Human_Surveyor_Digitization"]),
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        verification_status="HUMAN_VERIFIED",
        verification_priority="LOW",
        council_decision="ACCEPT_FOR_REVIEW",
        ulpin_ready_metadata_json=json.dumps(ulpin_meta),
        provenance_json=json.dumps(prov),
        version=1,
        geometry_geojson=geom_json,
        geom=wkb_geom,
    )
    db.add(new_p)

    db.add(
        FeatureVersion(
            id=f"{pid}_V1_HUMAN",
            project_id=req.project_id,
            feature_id=pid,
            feature_type="PARCEL",
            version_number=1,
            temporal_epoch="HUMAN_CREATE",
            area_sqm=area_sqm,
            perimeter_m=perim_m,
            land_use_class=req.land_use_class,
            building_count=bldg_count,
            confidence=0.99,
            status="HUMAN_VERIFIED",
            actor=req.operator_id,
            change_summary=req.reason or "Manual parcel creation",
            geometry_geojson=geom_json,
            geom=wkb_geom,
        )
    )

    db.add(
        VerificationRecord(
            id=f"{pid}_VERIF",
            project_id=req.project_id,
            scene_id=req.scene_id,
            parcel_id=pid,
            priority="LOW",
            priority_score=0.1,
            status="HUMAN_VERIFIED",
            reasons_json=json.dumps([req.reason or "Manual creation by surveyor"]),
            council_decision="ACCEPT_FOR_REVIEW",
            confidence=0.99,
            centroid_lon=round(geom.centroid.x, 7),
            centroid_lat=round(geom.centroid.y, 7),
            reviewer_notes=req.reason,
            verified_by=req.operator_id,
            verified_at=datetime.now(timezone.utc),
            geometry_geojson=geom_json,
            geom=wkb_geom,
        )
    )

    db.add(
        HumanFeedback(
            id=f"FB_{pid}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            project_id=req.project_id,
            feature_id=pid,
            action_type="CREATE_PARCEL",
            before_geometry_geojson=None,
            after_geometry_geojson=geom_json,
            before_class=None,
            after_class=req.land_use_class,
            operator_id=req.operator_id,
            reason=req.reason,
        )
    )

    record_audit_log(
        db=db,
        project_id=req.project_id,
        actor=req.operator_id,
        operation="CREATE_PARCEL",
        target_id=pid,
        new_value={"area_sqm": area_sqm, "land_use_class": req.land_use_class},
        source="PostGIS Parcel Service",
        confidence=0.99,
    )

    db.flush()
    recompute_scene_topology_and_routes(db, req.project_id, req.scene_id)
    db.commit()
    db.refresh(new_p)
    return serialize_parcel(new_p)


def update_parcel(
    db: Session, parcel_id: str, req: ParcelUpdateRequest
) -> Dict[str, Any]:
    assert_operator_can_mutate(req.operator_id)
    p = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")

    before_geom_str = p.geometry_geojson
    before_cls = p.land_use_class
    old_snap = {
        "area_sqm": p.area_sqm,
        "land_use_class": p.land_use_class,
        "verification_status": p.verification_status,
    }

    if req.geometry is not None:
        try:
            geom, geom_dict = validate_and_parse_geojson(
                req.geometry,
                expected_types=("Polygon", "MultiPolygon"),
                crs=req.crs or p.crs or "EPSG:4326",
                allow_make_valid=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        area_sqm, perim_m = compute_metric_area_perimeter(geom)
        if area_sqm < 1.0 or area_sqm > 5000000.0:
            raise HTTPException(
                status_code=400,
                detail=f"Edited area ({area_sqm:.2f} m²) outside valid cadastral bounds.",
            )
        p.area_sqm = area_sqm
        p.perimeter_m = perim_m
        p.compactness = polsby_popper_compactness(area_sqm, perim_m)
        p.geometry_geojson = json.dumps(geom_dict)
        p.geom = shape_to_wkb_element(geom, srid=4326)
        p.boundary_representation = req.boundary_representation or "HUMAN_VERIFIED"

    if req.land_use_class is not None:
        p.land_use_class = req.land_use_class

    if req.boundary_representation is not None:
        p.boundary_representation = req.boundary_representation

    if req.verification_status is not None:
        p.verification_status = req.verification_status
        vt = (
            db.query(VerificationRecord)
            .filter(VerificationRecord.parcel_id == parcel_id)
            .first()
        )
        ft = db.query(FieldTask).filter(FieldTask.parcel_id == parcel_id).first()
        if req.verification_status == "HUMAN_VERIFIED":
            p.boundary_representation = "HUMAN_VERIFIED"
            p.confidence = max(p.confidence, 0.96)
            p.confidence_category = "HIGH"
            p.council_decision = "ACCEPT_FOR_REVIEW"
            if vt:
                vt.status = "HUMAN_VERIFIED"
                vt.verified_by = req.operator_id
                vt.verified_at = datetime.now(timezone.utc)
                vt.reviewer_notes = req.reason
            if ft:
                ft.status = "COMPLETED"
        elif req.verification_status in ("FIELD_VISIT_REQUESTED", "REJECTED"):
            if vt:
                vt.status = req.verification_status
                vt.priority = "HIGH"
                vt.reviewer_notes = req.reason
                vt.verified_by = req.operator_id
                vt.verified_at = datetime.now(timezone.utc)
            if ft:
                ft.status = req.verification_status
                ft.priority = "HIGH"

    p.version = (p.version or 1) + 1
    p.updated_at = datetime.now(timezone.utc)
    prov = json.loads(p.provenance_json or "{}")
    prov["modified_by"] = req.operator_id
    prov["modified_at"] = datetime.now(timezone.utc).isoformat()
    prov["verification_status"] = p.verification_status
    p.provenance_json = json.dumps(prov)

    existing_vers = (
        db.query(FeatureVersion)
        .filter(
            FeatureVersion.project_id == p.project_id,
            FeatureVersion.feature_id == parcel_id,
        )
        .count()
    )
    v_num = existing_vers + 1
    db.add(
        FeatureVersion(
            id=f"{parcel_id}_V{v_num}_HUMAN_{int(datetime.now(timezone.utc).timestamp() * 1000) % 10000}",
            project_id=p.project_id,
            feature_id=parcel_id,
            feature_type="PARCEL",
            version_number=v_num,
            temporal_epoch="HUMAN_EDIT",
            area_sqm=p.area_sqm,
            perimeter_m=p.perimeter_m,
            land_use_class=p.land_use_class,
            building_count=p.building_count,
            confidence=p.confidence,
            status=p.verification_status,
            actor=req.operator_id,
            change_summary=req.reason
            or f"Human edit v{v_num}: Area={p.area_sqm:.1f} m², Status={p.verification_status}",
            geometry_geojson=p.geometry_geojson,
            geom=p.geom,
        )
    )

    db.add(
        HumanFeedback(
            id=f"FB_{parcel_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            project_id=p.project_id,
            feature_id=parcel_id,
            action_type="GEOMETRY_OR_ATTRIBUTE_EDIT",
            before_geometry_geojson=before_geom_str,
            after_geometry_geojson=p.geometry_geojson,
            before_class=before_cls,
            after_class=p.land_use_class,
            operator_id=req.operator_id,
            reason=req.reason,
        )
    )

    record_audit_log(
        db=db,
        project_id=p.project_id,
        actor=req.operator_id,
        operation="UPDATE_PARCEL",
        target_id=parcel_id,
        old_value=old_snap,
        new_value={
            "area_sqm": p.area_sqm,
            "land_use_class": p.land_use_class,
            "verification_status": p.verification_status,
            "version": p.version,
        },
        source="PostGIS Parcel Service",
        confidence=p.confidence,
    )

    db.flush()
    recompute_scene_topology_and_routes(db, p.project_id, p.scene_id)
    db.commit()
    db.refresh(p)
    return serialize_parcel(p)


def delete_parcel(
    db: Session, parcel_id: str, operator_id: str = "Surveyor_Verifier_01"
) -> Dict[str, Any]:
    assert_operator_can_mutate(operator_id)
    p = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")
    proj_id, sc_id = p.project_id, p.scene_id

    record_audit_log(
        db=db,
        project_id=proj_id,
        actor=operator_id,
        operation="DELETE_PARCEL",
        target_id=parcel_id,
        old_value=p.geometry_geojson,
        source="PostGIS Parcel Service",
    )
    db.query(VerificationRecord).filter(VerificationRecord.parcel_id == parcel_id).delete(
        synchronize_session=False
    )
    db.query(FieldTask).filter(FieldTask.parcel_id == parcel_id).delete(
        synchronize_session=False
    )
    db.query(CouncilDecision).filter(CouncilDecision.parcel_id == parcel_id).delete(
        synchronize_session=False
    )
    db.delete(p)
    db.flush()
    recompute_scene_topology_and_routes(db, proj_id, sc_id)
    db.commit()
    return {"deleted": parcel_id, "status": "OK"}


def split_parcel(
    db: Session, parcel_id: str, req: ParcelSplitRequest
) -> Dict[str, Any]:
    assert_operator_can_mutate(req.operator_id)
    if req.split_axis.upper() not in ("VERTICAL", "HORIZONTAL") and not req.cut_line_geojson:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid split_axis '{req.split_axis}'. Must be VERTICAL or HORIZONTAL.",
        )

    p = db.query(Parcel).filter(Parcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found.")

    geom = shape(geom_to_geojson_dict(p.geom, p.geometry_geojson))
    minx, miny, maxx, maxy = geom.bounds

    if req.cut_line_geojson:
        try:
            cut_line = shape(req.cut_line_geojson)
            if cut_line.geom_type not in ("LineString", "MultiLineString"):
                raise ValueError("cut_line_geojson must be a LineString.")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid cut_line_geojson: {exc}") from exc
    elif req.split_axis.upper() == "HORIZONTAL":
        ymid = miny + (maxy - miny) * req.split_ratio
        cut_line = LineString([(minx - 0.001, ymid), (maxx + 0.001, ymid)])
    else:
        xmid = minx + (maxx - minx) * req.split_ratio
        cut_line = LineString([(xmid, miny - 0.001), (xmid, maxy + 0.001)])

    parts = shapely_split(geom, cut_line)
    polys = [g for g in parts.geoms if g.geom_type == "Polygon" and g.area > 0]
    if len(polys) < 2:
        raise HTTPException(
            status_code=400, detail="Split line did not divide parcel into 2 polygons."
        )

    poly_a, poly_b = polys[0], polys[1]
    area_a, perim_a = compute_metric_area_perimeter(poly_a)
    area_b, perim_b = compute_metric_area_perimeter(poly_b)
    if area_a < 1.0 or area_b < 1.0:
        raise HTTPException(
            status_code=400,
            detail=f"Split would produce sliver parcel smaller than 1.0 m² ({area_a:.2f} m², {area_b:.2f} m²).",
        )

    before_geom_str = p.geometry_geojson
    p.area_sqm = area_a
    p.perimeter_m = perim_a
    p.compactness = polsby_popper_compactness(area_a, perim_a)
    p.geometry_geojson = json.dumps(mapping(poly_a))
    p.geom = shape_to_wkb_element(poly_a, srid=4326)
    p.boundary_representation = "HUMAN_VERIFIED"
    p.verification_status = "HUMAN_VERIFIED"
    p.version = (p.version or 1) + 1

    new_id = f"{parcel_id}_B"
    if db.query(Parcel).filter(Parcel.id == new_id).first():
        new_id = f"{parcel_id}_B_{int(datetime.now(timezone.utc).timestamp() % 1000)}"

    p_b = Parcel(
        id=new_id,
        project_id=p.project_id,
        scene_id=p.scene_id,
        temporal_epoch=p.temporal_epoch,
        parcel_layer="CANDIDATE",
        boundary_representation="HUMAN_VERIFIED",
        land_use_class=p.land_use_class,
        area_sqm=area_b,
        perimeter_m=perim_b,
        compactness=polsby_popper_compactness(area_b, perim_b),
        building_count=max(0, p.building_count // 2),
        road_access=True,
        dsm_mean_elevation_m=p.dsm_mean_elevation_m,
        crs=p.crs,
        confidence=0.95,
        confidence_category="HIGH",
        confidence_breakdown_json=p.confidence_breakdown_json,
        evidence_sources_json=p.evidence_sources_json,
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        verification_status="HUMAN_VERIFIED",
        verification_priority="LOW",
        council_decision="ACCEPT_FOR_REVIEW",
        ulpin_ready_metadata_json=p.ulpin_ready_metadata_json,
        provenance_json=json.dumps(
            {
                "feature_id": new_id,
                "parent_parcel_id": parcel_id,
                "created_by": req.operator_id,
                "operation": "SPLIT_PARCEL",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        version=1,
        geometry_geojson=json.dumps(mapping(poly_b)),
        geom=shape_to_wkb_element(poly_b, srid=4326),
    )
    db.add(p_b)

    db.add(
        HumanFeedback(
            id=f"FB_SPLIT_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            project_id=p.project_id,
            feature_id=parcel_id,
            action_type="SPLIT",
            before_geometry_geojson=before_geom_str,
            after_geometry_geojson=json.dumps(
                {"part_a": mapping(poly_a), "part_b": mapping(poly_b)}
            ),
            before_class=p.land_use_class,
            after_class=p.land_use_class,
            operator_id=req.operator_id,
            reason=req.reason,
        )
    )
    record_audit_log(
        db=db,
        project_id=p.project_id,
        actor=req.operator_id,
        operation="SPLIT_PARCEL",
        target_id=parcel_id,
        old_value=before_geom_str,
        new_value={"parcel_a": parcel_id, "parcel_b": new_id},
        source="PostGIS Parcel Service",
        confidence=0.95,
    )
    db.flush()
    recompute_scene_topology_and_routes(db, p.project_id, p.scene_id)
    db.commit()
    return {"parcel_a": serialize_parcel(p), "parcel_b": serialize_parcel(p_b)}


def merge_parcels(db: Session, req: ParcelMergeRequest) -> Dict[str, Any]:
    assert_operator_can_mutate(req.operator_id)
    if req.parcel_id_a == req.parcel_id_b:
        raise HTTPException(
            status_code=400, detail="Cannot merge a parcel with itself."
        )

    pa = db.query(Parcel).filter(Parcel.id == req.parcel_id_a).first()
    pb = db.query(Parcel).filter(Parcel.id == req.parcel_id_b).first()
    if not pa or not pb:
        raise HTTPException(
            status_code=404, detail="One or both parcels to merge were not found."
        )

    if pa.project_id != pb.project_id or pa.scene_id != pb.scene_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot merge parcels belonging to different projects or scenes.",
        )

    ga = shape(geom_to_geojson_dict(pa.geom, pa.geometry_geojson))
    gb = shape(geom_to_geojson_dict(pb.geom, pb.geometry_geojson))
    if ga.distance(gb) > 0.00015:
        raise HTTPException(
            status_code=400,
            detail="Incompatible parcel merge: parcels are spatially disjoint beyond snap tolerance.",
        )

    merged = unary_union([ga.buffer(0.00002), gb.buffer(0.00002)]).buffer(-0.00002)
    if merged.geom_type == "MultiPolygon":
        merged = merged.convex_hull

    area_m, perim_m = compute_metric_area_perimeter(merged)
    before_json = json.dumps(
        {
            "a": geom_to_geojson_dict(pa.geom, pa.geometry_geojson),
            "b": geom_to_geojson_dict(pb.geom, pb.geometry_geojson),
        }
    )

    pa.area_sqm = area_m
    pa.perimeter_m = perim_m
    pa.compactness = polsby_popper_compactness(area_m, perim_m)
    pa.building_count = (pa.building_count or 0) + (pb.building_count or 0)
    pa.geometry_geojson = json.dumps(mapping(merged))
    pa.geom = shape_to_wkb_element(merged, srid=4326)
    pa.boundary_representation = "HUMAN_VERIFIED"
    pa.verification_status = "HUMAN_VERIFIED"
    pa.version = (pa.version or 1) + 1

    db.query(VerificationRecord).filter(VerificationRecord.parcel_id == pb.id).delete(
        synchronize_session=False
    )
    db.query(FieldTask).filter(FieldTask.parcel_id == pb.id).delete(
        synchronize_session=False
    )
    db.query(CouncilDecision).filter(CouncilDecision.parcel_id == pb.id).delete(
        synchronize_session=False
    )
    db.delete(pb)

    db.add(
        HumanFeedback(
            id=f"FB_MERGE_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            project_id=pa.project_id,
            feature_id=pa.id,
            action_type="MERGE",
            before_geometry_geojson=before_json,
            after_geometry_geojson=pa.geometry_geojson,
            before_class=pa.land_use_class,
            after_class=pa.land_use_class,
            operator_id=req.operator_id,
            reason=req.reason,
        )
    )
    record_audit_log(
        db=db,
        project_id=pa.project_id,
        actor=req.operator_id,
        operation="MERGE_PARCELS",
        target_id=pa.id,
        old_value={"merged_from": [req.parcel_id_a, req.parcel_id_b]},
        new_value={"merged_into": pa.id, "area_sqm": area_m},
        source="PostGIS Parcel Service",
        confidence=0.96,
    )
    db.flush()
    recompute_scene_topology_and_routes(db, pa.project_id, pa.scene_id)
    db.commit()
    db.refresh(pa)
    return serialize_parcel(pa)

