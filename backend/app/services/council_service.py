import json
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from shapely.geometry import shape

from backend.app.models.entities import (
    Parcel,
    Anomaly,
    ChangeEvent,
    CouncilDecision,
    VerificationRecord,
)
from backend.app.schemas.api_schemas import CouncilAnalyzeRequest
from backend.app.utils.crs import compute_metric_area_perimeter
from backend.app.utils.geojson import geom_to_geojson_dict
from backend.app.utils.audit import record_audit_log
from backend.council.agents import evaluate_parcel_with_council


def serialize_council_decision(cd: CouncilDecision) -> Dict[str, Any]:
    return {
        "id": cd.id,
        "project_id": cd.project_id,
        "scene_id": cd.scene_id,
        "parcel_id": cd.parcel_id,
        "vision_score": cd.vision_score,
        "geometry_score": cd.geometry_score,
        "gis_score": cd.gis_score,
        "ml_score": cd.ml_score,
        "anomaly_score": cd.anomaly_score,
        "field_need": cd.field_need,
        "final_evidence_score": cd.final_evidence_score,
        "confidence": cd.confidence,
        "decision": cd.decision,
        "recommended_action": cd.recommended_action,
        "supporting_evidence": json.loads(cd.supporting_evidence_json or "[]"),
        "conflicting_evidence": json.loads(cd.conflicting_evidence_json or "[]"),
        "agent_reports": json.loads(cd.agent_reports_json or "{}"),
        "created_at": cd.created_at.isoformat() if cd.created_at else None,
    }


def analyze_parcel_with_council(
    db: Session, req: CouncilAnalyzeRequest
) -> Dict[str, Any]:
    """
    Run the 6-Agent Cadastral AI Council on a specific parcel using live PostGIS state
    and persist the resulting CouncilDecision record.
    """
    parcel = db.query(Parcel).filter(Parcel.id == req.parcel_id).first()
    if not parcel:
        raise HTTPException(
            status_code=404, detail=f"Parcel '{req.parcel_id}' not found."
        )

    anoms = (
        db.query(Anomaly)
        .filter(
            Anomaly.project_id == parcel.project_id,
            Anomaly.parcel_id == parcel.id,
        )
        .all()
    )
    chgs = (
        db.query(ChangeEvent)
        .filter(
            ChangeEvent.project_id == parcel.project_id,
            ChangeEvent.parcel_id == parcel.id,
        )
        .all()
    )

    # Check Reference GIS IoU if reference parcel exists
    ref_parcel = (
        db.query(Parcel)
        .filter(
            Parcel.project_id == parcel.project_id,
            Parcel.scene_id == parcel.scene_id,
            Parcel.parcel_layer == "REFERENCE",
        )
        .all()
    )
    p_geom = shape(geom_to_geojson_dict(parcel.geom, parcel.geometry_geojson))
    gis_iou = 0.90
    for rp in ref_parcel:
        r_geom = shape(geom_to_geojson_dict(rp.geom, rp.geometry_geojson))
        if p_geom.intersects(r_geom):
            ia, _ = compute_metric_area_perimeter(p_geom.intersection(r_geom))
            ua, _ = compute_metric_area_perimeter(p_geom.union(r_geom))
            if ua > 0:
                gis_iou = max(gis_iou, round(ia / ua, 4))

    cb = json.loads(parcel.confidence_breakdown_json or "{}")
    parcel_dict = {
        "id": parcel.id,
        "visible_edges": 4 if parcel.boundary_representation in ("VISIBLE", "HUMAN_VERIFIED") else 2,
        "boundary_prob_mean": float(cb.get("vision_confidence", parcel.confidence)),
        "bldg_prob_mean": float(cb.get("ml_confidence", parcel.confidence)),
        "lu_prob_mean": float(cb.get("ml_confidence", parcel.confidence)),
        "model_disagreement": 0.02,
        "compactness": parcel.compactness,
        "area_sqm": parcel.area_sqm,
        "road_access": parcel.road_access,
    }

    anom_dicts = [{"explanation": a.explanation} for a in anoms]
    chg_dicts = [{"summary": c.summary} for c in chgs]

    council_res = evaluate_parcel_with_council(
        parcel=parcel_dict,
        topology_status=parcel.topology_status,
        conflict_status=parcel.conflict_status,
        anomaly_status=parcel.anomaly_status,
        parcel_anomalies=anom_dicts,
        parcel_changes=chg_dicts,
        gis_iou=gis_iou,
    )

    cd = (
        db.query(CouncilDecision)
        .filter(CouncilDecision.parcel_id == parcel.id)
        .first()
    )
    if cd:
        cd.vision_score = council_res["vision_score"]
        cd.geometry_score = council_res["geometry_score"]
        cd.gis_score = council_res["gis_score"]
        cd.ml_score = council_res["ml_score"]
        cd.anomaly_score = council_res["anomaly_score"]
        cd.field_need = council_res["field_need"]
        cd.final_evidence_score = council_res["final_evidence_score"]
        cd.confidence = council_res["confidence"]
        cd.decision = council_res["decision"]
        cd.recommended_action = council_res["recommended_action"]
        cd.supporting_evidence_json = json.dumps(council_res["supporting_evidence"])
        cd.conflicting_evidence_json = json.dumps(council_res["conflicting_evidence"])
        cd.agent_reports_json = json.dumps(council_res["agent_reports"])
        cd.created_at = datetime.now(timezone.utc)
    else:
        cd = CouncilDecision(
            id=f"{parcel.id}_COUNCIL",
            project_id=parcel.project_id,
            scene_id=parcel.scene_id,
            parcel_id=parcel.id,
            vision_score=council_res["vision_score"],
            geometry_score=council_res["geometry_score"],
            gis_score=council_res["gis_score"],
            ml_score=council_res["ml_score"],
            anomaly_score=council_res["anomaly_score"],
            field_need=council_res["field_need"],
            final_evidence_score=council_res["final_evidence_score"],
            confidence=council_res["confidence"],
            decision=council_res["decision"],
            recommended_action=council_res["recommended_action"],
            supporting_evidence_json=json.dumps(council_res["supporting_evidence"]),
            conflicting_evidence_json=json.dumps(council_res["conflicting_evidence"]),
            agent_reports_json=json.dumps(council_res["agent_reports"]),
        )
        db.add(cd)

    # Synchronize Parcel & VerificationRecord
    if parcel.verification_status != "HUMAN_VERIFIED":
        parcel.confidence = council_res["confidence"]
        parcel.confidence_category = council_res["confidence_category"]
        parcel.confidence_breakdown_json = json.dumps(
            council_res["confidence_breakdown"]
        )
        parcel.council_decision = council_res["decision"]
        parcel.verification_priority = council_res["field_need"]

    vt = (
        db.query(VerificationRecord)
        .filter(VerificationRecord.parcel_id == parcel.id)
        .first()
    )
    if vt and vt.status == "PENDING":
        vt.council_decision = council_res["decision"]
        vt.priority = council_res["field_need"]
        vt.priority_score = council_res["priority_score"]
        vt.confidence = council_res["confidence"]
        vt.reasons_json = json.dumps(council_res["priority_reasons"])

    record_audit_log(
        db=db,
        project_id=parcel.project_id,
        actor="Six_Agent_AI_Council",
        operation="COUNCIL_DELIBERATION",
        target_id=parcel.id,
        new_value={
            "decision": council_res["decision"],
            "confidence": council_res["confidence"],
        },
        source="AI Council Service",
        confidence=council_res["confidence"],
    )

    db.commit()
    db.refresh(cd)
    return serialize_council_decision(cd)


def get_council_decision_for_parcel(db: Session, parcel_id: str) -> Dict[str, Any]:
    cd = (
        db.query(CouncilDecision)
        .filter(CouncilDecision.parcel_id == parcel_id)
        .order_by(CouncilDecision.created_at.desc())
        .first()
    )
    if not cd:
        raise HTTPException(
            status_code=404,
            detail=f"Council decision for parcel '{parcel_id}' not found.",
        )
    return serialize_council_decision(cd)
