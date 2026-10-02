from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.api_schemas import CouncilAnalyzeRequest
from backend.app.services.council_service import (
    analyze_parcel_with_council,
    get_council_decision_for_parcel,
)

router = APIRouter(tags=["AI Council"])


@router.post("/api/council/analyze", status_code=status.HTTP_201_CREATED)
def api_analyze_council(
    req: CouncilAnalyzeRequest,
    db: Session = Depends(get_db),
):
    return analyze_parcel_with_council(db, req)


@router.get("/api/council/{parcel_id}")
def api_get_council_decision(
    parcel_id: str,
    db: Session = Depends(get_db),
):
    return get_council_decision_for_parcel(db, parcel_id)
