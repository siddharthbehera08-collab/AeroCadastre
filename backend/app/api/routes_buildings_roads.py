from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import Project
from backend.app.services.gis_service import get_parcel_buildings, get_project_roads
from backend.app.utils.geojson import to_geojson_feature, to_geojson_feature_collection

router = APIRouter(tags=["Buildings & Roads"])


@router.get("/api/parcels/{parcel_id}/buildings")
def api_get_parcel_buildings(
    parcel_id: str,
    format: str = Query(default="json", pattern="^(json|geojson)$"),
    db: Session = Depends(get_db),
):
    buildings = get_parcel_buildings(db, parcel_id)
    features = [
        to_geojson_feature(
            b["id"],
            b["geometry"],
            {k: v for k, v in b.items() if k != "geometry"},
        )
        for b in buildings
    ]
    fc = to_geojson_feature_collection(features)
    if format == "geojson":
        return fc
    return {
        "parcel_id": parcel_id,
        "count": len(buildings),
        "buildings": buildings,
        "geojson": fc,
    }


@router.get("/api/projects/{project_id}/roads")
def api_get_project_roads(
    project_id: str,
    scene_id: Optional[str] = Query(default=None),
    format: str = Query(default="json", pattern="^(json|geojson)$"),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404, detail=f"Project '{project_id}' not found."
        )
    roads = get_project_roads(db, project_id=project_id, scene_id=scene_id)
    features = [
        to_geojson_feature(
            r["id"],
            r["geometry"],
            {k: v for k, v in r.items() if k != "geometry"},
        )
        for r in roads
    ]
    fc = to_geojson_feature_collection(features)
    if format == "geojson":
        return fc
    return {
        "project_id": project_id,
        "count": len(roads),
        "roads": roads,
        "geojson": fc,
    }
