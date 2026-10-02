import json
from typing import Any, Dict
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models.entities import User, ModelRun, Parcel, FieldTask
from backend.app.schemas.api_schemas import AnalysisRunRequest
from backend.app.services.ml_service import run_ai_analysis, _sync_field_tasks_from_routes
from synthetic_data.generator import generate_full_synthetic_dataset


DEFAULT_USERS = [
    {
        "id": "USR_SURVEYOR_01",
        "email": "surveyor@aerocadastre.gov.in",
        "full_name": "Arjun Mehta (Lead Surveyor)",
        "role": "SURVEYOR",
        "department": "Department of Land Resources (DoLR)",
        "password_env": "DEMO_SURVEYOR_PASSWORD",
    },
    {
        "id": "USR_ADMIN_01",
        "email": "admin@aerocadastre.gov.in",
        "full_name": "Dr. Kavita Nair (GIS Administrator)",
        "role": "ADMINISTRATOR",
        "department": "National Geospatial Cadastral Division",
        "password_env": "DEMO_ADMIN_PASSWORD",
    },
    {
        "id": "USR_DEMO_01",
        "email": "demo@aerocadastre.gov.in",
        "full_name": "SIH26012 Reviewer (Demo User)",
        "role": "DEMO_USER",
        "department": "Smart India Hackathon Evaluation Panel",
        "password_env": "DEMO_REVIEWER_PASSWORD",
    },
]


def seed_initial_postgis_data(db: Session) -> Dict[str, Any]:
    """
    Seed default users, trained ML model runs, and the initial synthetic demo scene
    into PostgreSQL + PostGIS if not already present.
    """
    import os

    # 1. Seed Users
    users_added = 0
    for u in DEFAULT_USERS:
        if not db.query(User).filter(User.email == u["email"]).first():
            raw_pwd = os.getenv(u["password_env"], f"sih26012_{u['role'].lower()}")
            db.add(
                User(
                    id=u["id"],
                    email=u["email"],
                    full_name=u["full_name"],
                    role=u["role"],
                    department=u["department"],
                    hashed_password=hash_password(raw_pwd),
                    is_active=True,
                )
            )
            users_added += 1
    db.commit()

    # 2. Seed ModelRun records from experiments/experiments_summary.json
    exp_file = settings.experiments_dir / "experiments_summary.json"
    runs_added = 0
    if exp_file.exists():
        exp_list = json.loads(exp_file.read_text(encoding="utf-8"))
        for r in exp_list:
            if not db.query(ModelRun).filter(ModelRun.id == r["id"]).first():
                db.add(
                    ModelRun(
                        id=r["id"],
                        task_type=r["task_type"],
                        model_name=r["model_name"],
                        architecture=r["architecture"],
                        dataset_name=r.get("dataset_name", "SYNTHETIC_DEMO_V1"),
                        epochs=int(r["epochs"]),
                        batch_size=int(r["batch_size"]),
                        learning_rate=float(r["learning_rate"]),
                        train_loss=float(r["train_loss"]),
                        val_loss=float(r["val_loss"]),
                        iou=float(r["iou"]),
                        dice_f1=float(r["dice_f1"]),
                        precision_score=float(r["precision_score"]),
                        recall_score=float(r["recall_score"]),
                        training_time_sec=float(r["training_time_sec"]),
                        inference_time_ms=float(r["inference_time_ms"]),
                        checkpoint_path=r["checkpoint_path"],
                        notes=r.get("notes", ""),
                    )
                )
                runs_added += 1
        db.commit()

    # 3. Ensure synthetic files on disk exist
    if not (settings.synthetic_data_dir / "dataset_manifest.json").exists():
        generate_full_synthetic_dataset()

    # 4. Run initial scene inference & PostGIS persistence if parcels table has no scene_urban_T1 rows
    existing_parcels = (
        db.query(Parcel)
        .filter(
            Parcel.project_id == "PROJ_SIH26012_DEMO",
            Parcel.scene_id == "scene_urban_T1",
        )
        .count()
    )
    if existing_parcels == 0:
        run_ai_analysis(
            db,
            AnalysisRunRequest(
                project_id="PROJ_SIH26012_DEMO",
                scene_id="scene_urban_T1",
            ),
        )
    else:
        ft_count = (
            db.query(FieldTask)
            .filter(
                FieldTask.project_id == "PROJ_SIH26012_DEMO",
                FieldTask.scene_id == "scene_urban_T1",
            )
            .count()
        )
        if ft_count == 0:
            _sync_field_tasks_from_routes(db, "PROJ_SIH26012_DEMO", "scene_urban_T1")

    return {
        "users_in_db": db.query(User).count(),
        "model_runs_in_db": db.query(ModelRun).count(),
        "parcels_in_db": db.query(Parcel).count(),
        "field_tasks_in_db": db.query(FieldTask).count(),
    }


ensure_demo_seed_data = seed_initial_postgis_data
