from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db, verify_postgis_connection
from backend.app.models.entities import (
    User,
    Project,
    Dataset,
    Parcel,
    Building,
    Road,
    LandUse,
    AIPrediction,
    ModelRun,
    CouncilDecision,
    TopologyIssue,
    VerificationRecord,
    ChangeEvent,
    FieldTask,
    AuditLog,
)

router = APIRouter(tags=["Health"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    pg_info = verify_postgis_connection(db)
    counts = {
        "users": db.query(User).count(),
        "projects": db.query(Project).count(),
        "datasets": db.query(Dataset).count(),
        "parcels": db.query(Parcel).count(),
        "buildings": db.query(Building).count(),
        "roads": db.query(Road).count(),
        "land_use": db.query(LandUse).count(),
        "ai_predictions": db.query(AIPrediction).count(),
        "model_runs": db.query(ModelRun).count(),
        "council_decisions": db.query(CouncilDecision).count(),
        "topology_issues": db.query(TopologyIssue).count(),
        "verification_records": db.query(VerificationRecord).count(),
        "change_events": db.query(ChangeEvent).count(),
        "field_tasks": db.query(FieldTask).count(),
        "audit_logs": db.query(AuditLog).count(),
    }
    return {
        "status": "ONLINE",
        "project": "SIH26012_AeroCadastre",
        "storage_root": str(settings.PROJECT_ROOT),
        "database_engine": "PostgreSQL + PostGIS",
        "postgresql_version": pg_info["postgresql_version"],
        "postgis_version": pg_info["postgis_version"],
        "public_table_count": pg_info["public_table_count"],
        "data_label": "SYNTHETIC DEMO DATA",
        "legal_disclaimer": "PRELIMINARY / CANDIDATE GEOMETRY - NOT LEGALLY AUTHORITATIVE LAND RECORDS",
        "parcels_in_db": counts["parcels"],
        "experiments_in_db": counts["model_runs"],
        "table_counts": counts,
    }
