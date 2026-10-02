import json
from typing import Any, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.entities import AIPrediction, FieldRoute, FieldTask
from backend.app.schemas.api_schemas import AnalysisRunRequest
from backend.app.utils.geojson import shape_to_wkb_element
from shapely.geometry import Point
from backend.gis.pipeline import run_full_scene_pipeline


def serialize_ai_prediction(pred: AIPrediction) -> Dict[str, Any]:
    details = {}
    if pred.details_json:
        try:
            details = json.loads(pred.details_json)
        except Exception:
            details = {}
    return {
        "id": pred.id,
        "project_id": pred.project_id,
        "scene_id": pred.scene_id,
        "model_run_id": pred.model_run_id,
        "prediction_type": pred.prediction_type,
        "feature_count": pred.feature_count,
        "mean_confidence": pred.mean_confidence,
        "inference_time_ms": pred.inference_time_ms,
        "artifact_path": pred.artifact_path,
        "details": details,
        "created_at": pred.created_at.isoformat() if pred.created_at else None,
    }


def _sync_field_tasks_from_routes(db: Session, project_id: str, scene_id: str) -> None:
    """Populate physical field_tasks table from planned field routes."""
    db.query(FieldTask).filter(
        FieldTask.project_id == project_id, FieldTask.scene_id == scene_id
    ).delete(synchronize_session=False)

    routes = (
        db.query(FieldRoute)
        .filter(FieldRoute.project_id == project_id, FieldRoute.scene_id == scene_id)
        .all()
    )
    for rt in routes:
        stops = json.loads(rt.ordered_stops_json or "[]")
        for st in stops:
            lon = float(st.get("lon", 77.592))
            lat = float(st.get("lat", 12.972))
            pt = Point(lon, lat)
            ft_id = f"FT_{rt.id}_{st.get('sequence', 1):02d}"
            db.add(
                FieldTask(
                    id=ft_id,
                    project_id=project_id,
                    scene_id=scene_id,
                    parcel_id=st["parcel_id"],
                    route_id=rt.id,
                    sequence_order=int(st.get("sequence", 1)),
                    priority=st.get("priority", "MEDIUM"),
                    priority_score=float(st.get("priority_score", 0.5)),
                    status="ASSIGNED",
                    assigned_to="Surveyor_Verifier_01",
                    reasons_json=json.dumps(st.get("reasons", [])),
                    centroid_lon=lon,
                    centroid_lat=lat,
                    geometry_geojson=json.dumps(
                        {"type": "Point", "coordinates": [lon, lat]}
                    ),
                    geom=shape_to_wkb_element(pt, srid=4326),
                )
            )
    db.commit()


def run_ai_analysis(db: Session, req: AnalysisRunRequest) -> Dict[str, Any]:
    """
    Execute the multi-model PyTorch GeoAI inference and PostGIS pipeline on the requested scene
    and return the persisted AIPrediction record plus top-level counts and inference_time_ms.
    """
    try:
        pipeline_summary = run_full_scene_pipeline(
            db, project_id=req.project_id, scene_id=req.scene_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _sync_field_tasks_from_routes(db, req.project_id, req.scene_id)

    pred = (
        db.query(AIPrediction)
        .filter(
            AIPrediction.project_id == req.project_id,
            AIPrediction.scene_id == req.scene_id,
        )
        .order_by(AIPrediction.created_at.desc())
        .first()
    )
    if not pred:
        raise HTTPException(
            status_code=500, detail="AI prediction record was not persisted."
        )

    pred.details_json = json.dumps(pipeline_summary)
    db.commit()
    db.refresh(pred)

    out = serialize_ai_prediction(pred)
    out["pipeline_summary"] = pipeline_summary
    out["counts"] = pipeline_summary.get("counts", {})
    out["inference_time_ms"] = pipeline_summary.get("inference_time_ms", pred.inference_time_ms)
    out["status"] = pipeline_summary.get("status", "COMPLETED")
    return out


def get_ai_analysis_by_id(db: Session, analysis_id: str) -> Dict[str, Any]:
    pred = (
        db.query(AIPrediction)
        .filter(
            (AIPrediction.id == analysis_id) | (AIPrediction.scene_id == analysis_id)
        )
        .order_by(AIPrediction.created_at.desc())
        .first()
    )
    if not pred:
        raise HTTPException(
            status_code=404, detail=f"AI analysis run '{analysis_id}' not found."
        )
    return serialize_ai_prediction(pred)
