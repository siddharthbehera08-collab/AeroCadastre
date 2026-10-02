from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.api_schemas import AnalysisRunRequest
from backend.app.services.ml_service import run_ai_analysis, get_ai_analysis_by_id

router = APIRouter(tags=["AI Analysis & ML"])


@router.post("/api/analysis/run", status_code=status.HTTP_201_CREATED)
def api_run_analysis(
    req: AnalysisRunRequest,
    db: Session = Depends(get_db),
):
    return run_ai_analysis(db, req)


@router.get("/api/analysis/{id}")
def api_get_analysis(
    id: str,
    db: Session = Depends(get_db),
):
    return get_ai_analysis_by_id(db, id)
