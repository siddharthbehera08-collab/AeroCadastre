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
