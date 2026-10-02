from typing import Any, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.entities import Parcel, Project
from backend.app.schemas.api_schemas import ExportRequest
from backend.app.services.parcel_service import serialize_parcel
from backend.app.utils.audit import record_audit_log
from backend.gis.exporter import export_and_validate_parcels


def generate_validated_export(db: Session, req: ExportRequest) -> Dict[str, Any]:
    project = db.query(Project).filter(Project.id == req.project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{req.project_id}' not found.",
        )

    parcels = (
        db.query(Parcel)
        .filter(
            Parcel.project_id == req.project_id,
            Parcel.scene_id == req.scene_id,
            Parcel.parcel_layer == "CANDIDATE",
        )
        .order_by(Parcel.id.asc())
        .all()
    )

    serialized = [serialize_parcel(p) for p in parcels]
    try:
        res = export_and_validate_parcels(
            req.project_id, req.scene_id, req.export_format, serialized
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    res["export_path"] = res.get("file_path")
    record_audit_log(
        db=db,
        project_id=req.project_id,
        actor="Surveyor_Verifier_01",
        operation=f"EXPORT_{req.export_format.upper()}",
        target_id=req.scene_id,
        new_value=res,
        source="Validated GIS Exporter",
    )
    db.commit()
    return res
