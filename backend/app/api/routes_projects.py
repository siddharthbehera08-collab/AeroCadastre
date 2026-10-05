from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_optional_user
from backend.app.schemas.api_schemas import ProjectCreateRequest, ProjectUpdateRequest
from backend.app.services.project_service import (
    list_projects,
    get_project_by_id,
    create_project,
    update_project,
    delete_project,
)

router = APIRouter(tags=["Projects"])


@router.get("/api/projects")
def api_list_projects(db: Session = Depends(get_db)):
    return list_projects(db)


@router.post("/api/projects", status_code=status.HTTP_201_CREATED)
def api_create_project(
    req: ProjectCreateRequest,
    user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    res = create_project(db, req, actor=user.get("sub", "Surveyor_Verifier_01"))
    return {**res, "status": "CREATED"}


@router.get("/api/projects/{id}")
def api_get_project(id: str, db: Session = Depends(get_db)):
    return get_project_by_id(db, id)


@router.put("/api/projects/{id}")
def api_update_project(
    id: str,
    req: ProjectUpdateRequest,
    user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return update_project(db, id, req, actor=user.get("sub", "Surveyor_Verifier_01"))


@router.delete("/api/projects/{id}")
def api_delete_project(
    id: str,
    user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return delete_project(db, id, actor=user.get("sub", "Surveyor_Verifier_01"))


# ============================================================================
# Project Orchestration & Ingestion Sub-Resources
# ============================================================================
from backend.app.schemas.job_schemas import (
    DatasetRegisterRequest,
    ProcessProjectRequest,
)
from backend.app.services.orchestration_service import OrchestrationService

orchestrator = OrchestrationService()


@router.post("/api/projects/{id}/datasets", status_code=status.HTTP_201_CREATED)
def api_register_dataset(
    id: str,
    req: DatasetRegisterRequest,
    user: dict = Depends(get_optional_user),
):
    return orchestrator.register_dataset(project_id=id, req=req)


@router.get("/api/projects/{id}/datasets")
def api_list_project_datasets(id: str):
    return orchestrator.get_project_datasets(project_id=id)


@router.post("/api/projects/{id}/process")
def api_process_project(
    id: str,
    req: ProcessProjectRequest,
    user: dict = Depends(get_optional_user),
):
    return orchestrator.create_and_run_pipeline(project_id=id, req=req)


@router.get("/api/projects/{id}/status")
def api_get_project_status(id: str):
    return orchestrator.get_project_status(project_id=id)


@router.get("/api/projects/{id}/layers")
def api_get_project_layers(id: str):
    return orchestrator.get_project_layers(project_id=id)


@router.get("/api/projects/{id}/parcels")
def api_get_project_candidate_parcels(id: str):
    return orchestrator.get_project_parcels(project_id=id)


@router.get("/api/projects/{id}/evidence")
def api_get_project_evidence(id: str):
    return orchestrator.get_project_evidence(project_id=id)


@router.get("/api/projects/{id}/anomalies")
def api_get_project_anomalies(id: str):
    return orchestrator.get_project_anomalies(project_id=id)


@router.get("/api/projects/{id}/verification")
def api_get_project_verification(id: str):
    return orchestrator.get_project_verification(project_id=id)


@router.get("/api/projects/{id}/audit")
def api_get_project_audit(id: str):
    return orchestrator.get_project_audit(project_id=id)


@router.post("/api/projects/{id}/verify")
def api_verify_project_parcel(
    id: str,
    payload: dict,
    user: dict = Depends(get_optional_user),
):
    parcel_id = payload.get("parcel_id", "")
    decision = payload.get("decision", "APPROVED")
    notes = payload.get("notes", "")
    actor = user.get("sub", "Surveyor_Verifier_01")
    return orchestrator.update_verification_decision(
        project_id=id,
        parcel_id=parcel_id,
        decision=decision,
        operator_id=actor,
        notes=notes,
    )


@router.post("/api/projects/{id}/export")
def api_export_project_parcels(
    id: str,
    payload: dict = {},
    user: dict = Depends(get_optional_user),
):
    fmt = payload.get("export_format", "GeoJSON")
    scene_id = payload.get("scene_id", f"{id}_EXPORT")
    return orchestrator.export_project_parcels(
        project_id=id,
        scene_id=scene_id,
        export_format=fmt,
    )

