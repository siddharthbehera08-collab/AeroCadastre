from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_optional_user, assert_operator_can_mutate
from backend.app.schemas.api_schemas import (
    VerificationCreateRequest,
    VerificationUpdateRequest,
    VerificationActionRequest,
)
from backend.app.services.verification_service import (
    get_verification_queue,
    create_verification_record,
    update_verification_record,
)

router = APIRouter(tags=["Verification"])


def _normalize_verification_action(action: str) -> str:
    act = (action or "").strip().upper()
    if act in ("APPROVE", "HUMAN_VERIFIED", "ACCEPT_CANDIDATE", "VERIFY", "ACCEPT"):
        return "HUMAN_VERIFIED"
    if act in ("FLAG", "FIELD_VISIT_REQUESTED", "FLAG_FOR_FIELD"):
        return "FIELD_VISIT_REQUESTED"
    if act in ("REJECT", "REJECTED", "REJECT_CANDIDATE"):
        return "REJECTED"
    return act


@router.get("/api/verification/queue")
def api_get_verification_queue(
    project_id: Optional[str] = Query(default=None),
    scene_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    items = get_verification_queue(
        db,
        project_id=project_id,
        scene_id=scene_id,
        status=status_filter,
        priority=priority,
    )
    return {
        "count": len(items),
        "queue": items,
    }


@router.post("/api/verification", status_code=status.HTTP_201_CREATED)
def api_create_verification(
    req: VerificationCreateRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    assert_operator_can_mutate(req.verified_by)
    return create_verification_record(db, req)


@router.put("/api/verification/{id}")
def api_update_verification(
    id: str,
    req: VerificationUpdateRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    assert_operator_can_mutate(req.verified_by)
    return update_verification_record(db, id, req)


@router.post("/api/verification/{parcel_id}")
@router.post("/api/verification/{parcel_id}/action")
def api_verification_action_legacy(
    parcel_id: str,
    req: VerificationActionRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    assert_operator_can_mutate(req.operator_id)
    mapped_status = _normalize_verification_action(req.action)
    return create_verification_record(
        db,
        VerificationCreateRequest(
            parcel_id=parcel_id,
            status=mapped_status,
            reviewer_notes=req.notes,
            verified_by=req.operator_id,
        ),
    )
