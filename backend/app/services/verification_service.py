import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from shapely.geometry import shape

from backend.app.models.entities import (
    Parcel,
    VerificationRecord,
    FieldTask,
    HumanFeedback,
)
from backend.app.schemas.api_schemas import (
    VerificationCreateRequest,
    VerificationUpdateRequest,
)
from backend.app.utils.geojson import geom_to_geojson_dict, shape_to_wkb_element
from backend.app.utils.audit import record_audit_log

VALID_VERIFICATION_STATUSES = {
    "PENDING",
    "HUMAN_VERIFIED",
    "REJECTED",
    "FIELD_VISIT_REQUESTED",
    "ACCEPT_CANDIDATE",
}


def serialize_verification_record(vt: VerificationRecord) -> Dict[str, Any]:
    return {
        "id": vt.id,
        "project_id": vt.project_id,
        "scene_id": vt.scene_id,
        "parcel_id": vt.parcel_id,
        "priority": vt.priority,
        "priority_score": vt.priority_score,
        "status": vt.status,
        "reasons": json.loads(vt.reasons_json or "[]"),
        "council_decision": vt.council_decision,
        "confidence": vt.confidence,
        "centroid_lon": vt.centroid_lon,
        "centroid_lat": vt.centroid_lat,
        "reviewer_notes": vt.reviewer_notes,
        "verified_by": vt.verified_by,
        "verified_at": vt.verified_at.isoformat() if vt.verified_at else None,
        "geometry": geom_to_geojson_dict(vt.geom, vt.geometry_geojson),
        "created_at": vt.created_at.isoformat() if vt.created_at else None,
    }


def get_verification_queue(
    db: Session,
    project_id: Optional[str] = None,
    scene_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = db.query(VerificationRecord)
    if project_id:
        q = q.filter(VerificationRecord.project_id == project_id)
    if scene_id:
        q = q.filter(VerificationRecord.scene_id == scene_id)
    if status:
        q = q.filter(VerificationRecord.status == status)
    if priority:
        q = q.filter(VerificationRecord.priority == priority)

    rows = q.order_by(
        VerificationRecord.priority_score.desc(), VerificationRecord.id.asc()
    ).all()
    return [serialize_verification_record(r) for r in rows]


def create_verification_record(
    db: Session, req: VerificationCreateRequest
) -> Dict[str, Any]:
    if req.status not in VALID_VERIFICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid verification status '{req.status}'. Valid values: {sorted(VALID_VERIFICATION_STATUSES)}",
        )

    parcel = db.query(Parcel).filter(Parcel.id == req.parcel_id).first()
    if not parcel:
        raise HTTPException(
            status_code=404, detail=f"Parcel '{req.parcel_id}' not found."
        )

    existing = (
        db.query(VerificationRecord)
        .filter(VerificationRecord.parcel_id == req.parcel_id)
        .first()
    )
    now = datetime.now(timezone.utc)
    geom_dict = geom_to_geojson_dict(parcel.geom, parcel.geometry_geojson)
    shp = shape(geom_dict)
    wkb_geom = shape_to_wkb_element(shp, srid=4326)

    if existing:
        existing.status = req.status
        if req.priority:
            existing.priority = req.priority
        existing.reviewer_notes = req.reviewer_notes
        existing.verified_by = req.verified_by
        existing.verified_at = now
        vt = existing
    else:
        vid = f"{req.parcel_id}_VERIF_{int(now.timestamp() * 1000) % 10000}"
        vt = VerificationRecord(
            id=vid,
            project_id=parcel.project_id,
            scene_id=parcel.scene_id,
            parcel_id=parcel.id,
            priority=req.priority or parcel.verification_priority or "MEDIUM",
            priority_score=0.85 if (req.priority == "HIGH") else 0.50,
            status=req.status,
            reasons_json=json.dumps([req.reviewer_notes or "Surveyor verification"]),
            council_decision=parcel.council_decision,
            confidence=parcel.confidence,
            centroid_lon=round(shp.centroid.x, 7),
            centroid_lat=round(shp.centroid.y, 7),
            reviewer_notes=req.reviewer_notes,
            verified_by=req.verified_by,
            verified_at=now,
            geometry_geojson=json.dumps(geom_dict),
            geom=wkb_geom,
        )
        db.add(vt)

    # Synchronize Parcel status
    parcel.verification_status = req.status
    if req.status in ("HUMAN_VERIFIED", "ACCEPT_CANDIDATE"):
        parcel.boundary_representation = "HUMAN_VERIFIED"
        parcel.confidence = max(parcel.confidence, 0.96)
        parcel.confidence_category = "HIGH"
        parcel.council_decision = "ACCEPT_FOR_REVIEW"

    # Synchronize FieldTask if present
    ft = db.query(FieldTask).filter(FieldTask.parcel_id == parcel.id).first()
    if ft:
        ft.status = "COMPLETED" if req.status == "HUMAN_VERIFIED" else req.status

    db.add(
        HumanFeedback(
            id=f"FB_VERIF_{parcel.id}_{int(now.timestamp() * 1000)}",
            project_id=parcel.project_id,
            feature_id=parcel.id,
            action_type=f"VERIFY_{req.status}",
            before_geometry_geojson=parcel.geometry_geojson,
            after_geometry_geojson=parcel.geometry_geojson,
            before_class=parcel.land_use_class,
            after_class=parcel.land_use_class,
            operator_id=req.verified_by,
            reason=req.reviewer_notes,
        )
    )

    record_audit_log(
        db=db,
        project_id=parcel.project_id,
        actor=req.verified_by,
        operation="CREATE_VERIFICATION",
        target_id=vt.id,
        new_value={"parcel_id": parcel.id, "status": req.status},
        source="Verification Service",
        confidence=parcel.confidence,
    )

    db.commit()
    db.refresh(vt)
    return serialize_verification_record(vt)


def update_verification_record(
    db: Session, verification_id: str, req: VerificationUpdateRequest
) -> Dict[str, Any]:
    vt = (
        db.query(VerificationRecord)
        .filter(
            (VerificationRecord.id == verification_id)
            | (VerificationRecord.parcel_id == verification_id)
        )
        .first()
    )
    if not vt:
        raise HTTPException(
            status_code=404,
            detail=f"Verification record '{verification_id}' not found.",
        )

    old_status = vt.status
    if req.status is not None:
        if req.status not in VALID_VERIFICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid verification status '{req.status}'. Valid values: {sorted(VALID_VERIFICATION_STATUSES)}",
            )
        vt.status = req.status
    if req.priority is not None:
        vt.priority = req.priority
    if req.reviewer_notes is not None:
        vt.reviewer_notes = req.reviewer_notes
    if req.verified_by is not None:
        vt.verified_by = req.verified_by
    vt.verified_at = datetime.now(timezone.utc)

    parcel = db.query(Parcel).filter(Parcel.id == vt.parcel_id).first()
    if parcel and req.status is not None:
        parcel.verification_status = req.status
        if req.status in ("HUMAN_VERIFIED", "ACCEPT_CANDIDATE"):
            parcel.boundary_representation = "HUMAN_VERIFIED"
            parcel.confidence = max(parcel.confidence, 0.96)
            parcel.confidence_category = "HIGH"
            parcel.council_decision = "ACCEPT_FOR_REVIEW"

    ft = db.query(FieldTask).filter(FieldTask.parcel_id == vt.parcel_id).first()
    if ft and req.status is not None:
        ft.status = "COMPLETED" if req.status == "HUMAN_VERIFIED" else req.status

    record_audit_log(
        db=db,
        project_id=vt.project_id,
        actor=req.verified_by or "Surveyor_Verifier_01",
        operation="UPDATE_VERIFICATION",
        target_id=vt.id,
        old_value={"status": old_status},
        new_value={"status": vt.status, "priority": vt.priority},
        source="Verification Service",
        confidence=vt.confidence,
    )

    db.commit()
    db.refresh(vt)
    return serialize_verification_record(vt)
