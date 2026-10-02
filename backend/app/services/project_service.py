import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.entities import Project, Parcel
from backend.app.schemas.api_schemas import ProjectCreateRequest, ProjectUpdateRequest
from backend.app.utils.crs import validate_crs_code
from backend.app.utils.geojson import (
    validate_and_parse_geojson,
    geom_to_geojson_dict,
    shape_to_wkb_element,
)
from backend.app.utils.audit import record_audit_log


def serialize_project(db: Session, p: Project) -> Dict[str, Any]:
    parcel_count = (
        db.query(Parcel)
        .filter(Parcel.project_id == p.id, Parcel.parcel_layer == "CANDIDATE")
        .count()
    )
    bbox_geom = None
    if p.geom is not None or p.bbox_geojson:
        bbox_geom = geom_to_geojson_dict(p.geom, p.bbox_geojson)
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description or "",
        "region_name": p.region_name or "",
        "crs": p.crs,
        "projected_crs": p.projected_crs,
        "is_synthetic": p.is_synthetic,
        "data_label": p.data_label,
        "ulpin_metadata_mode": p.ulpin_metadata_mode,
        "bbox_geometry": bbox_geom,
        "parcel_count": parcel_count,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def list_projects(db: Session) -> List[Dict[str, Any]]:
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [serialize_project(db, p) for p in projects]


def get_project_by_id(db: Session, project_id: str) -> Dict[str, Any]:
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(
            status_code=404, detail=f"Project '{project_id}' not found."
        )
    return serialize_project(db, p)


def create_project(
    db: Session, req: ProjectCreateRequest, actor: str = "Surveyor_Verifier_01"
) -> Dict[str, Any]:
    try:
        validate_crs_code(req.crs)
        validate_crs_code(req.projected_crs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pid = req.id or f"PROJ_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    if db.query(Project).filter(Project.id == pid).first():
        raise HTTPException(
            status_code=409, detail=f"Project '{pid}' already exists."
        )

    bbox_str = None
    wkb_geom = None
    if req.bbox_geojson is not None:
        try:
            shp, geojson_dict = validate_and_parse_geojson(
                req.bbox_geojson, expected_types=("Polygon", "MultiPolygon"), crs=req.crs
            )
            bbox_str = json.dumps(geojson_dict)
            wkb_geom = shape_to_wkb_element(shp, srid=4326)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    project = Project(
        id=pid,
        name=req.name.strip(),
        description=req.description or "",
        region_name=req.region_name or "Synthetic Urban Sector (India)",
        crs=req.crs,
        projected_crs=req.projected_crs,
        is_synthetic=True,
        data_label="SYNTHETIC DEMO DATA",
        ulpin_metadata_mode="ULPIN_READY_METADATA",
        bbox_geojson=bbox_str,
        geom=wkb_geom,
    )
    db.add(project)
    record_audit_log(
        db=db,
        project_id=pid,
        actor=actor,
        operation="CREATE_PROJECT",
        target_id=pid,
        new_value={"name": project.name, "crs": project.crs},
    )
    db.commit()
    db.refresh(project)
    return serialize_project(db, project)


def update_project(
    db: Session,
    project_id: str,
    req: ProjectUpdateRequest,
    actor: str = "Surveyor_Verifier_01",
) -> Dict[str, Any]:
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(
            status_code=404, detail=f"Project '{project_id}' not found."
        )

    old_snap = {"name": p.name, "description": p.description, "crs": p.crs}

    if req.crs is not None:
        try:
            validate_crs_code(req.crs)
            p.crs = req.crs
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.projected_crs is not None:
        try:
            validate_crs_code(req.projected_crs)
            p.projected_crs = req.projected_crs
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.name is not None:
        p.name = req.name.strip()
    if req.description is not None:
        p.description = req.description
    if req.region_name is not None:
        p.region_name = req.region_name

    if req.bbox_geojson is not None:
        try:
            shp, geojson_dict = validate_and_parse_geojson(
                req.bbox_geojson, expected_types=("Polygon", "MultiPolygon"), crs=p.crs
            )
            p.bbox_geojson = json.dumps(geojson_dict)
            p.geom = shape_to_wkb_element(shp, srid=4326)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    p.updated_at = datetime.now(timezone.utc)
    record_audit_log(
        db=db,
        project_id=p.id,
        actor=actor,
        operation="UPDATE_PROJECT",
        target_id=p.id,
        old_value=old_snap,
        new_value={"name": p.name, "description": p.description, "crs": p.crs},
    )
    db.commit()
    db.refresh(p)
    return serialize_project(db, p)


def delete_project(
    db: Session, project_id: str, actor: str = "Surveyor_Verifier_01"
) -> Dict[str, Any]:
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(
            status_code=404, detail=f"Project '{project_id}' not found."
        )
    record_audit_log(
        db=db,
        project_id=project_id,
        actor=actor,
        operation="DELETE_PROJECT",
        target_id=project_id,
        old_value={"name": p.name},
    )
    db.delete(p)
    db.commit()
    return {"id": project_id, "deleted": True, "status": "DELETED"}
