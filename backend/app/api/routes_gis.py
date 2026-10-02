from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.gis_service import (
    get_parcel_topology,
    get_parcel_conflicts,
)

router = APIRouter(tags=["GIS & Spatial Topology"])


@router.get("/api/parcels/{id}/topology")
def api_get_parcel_topology(
    id: str,
    db: Session = Depends(get_db),
):
    return get_parcel_topology(db, id)


@router.get("/api/parcels/{id}/conflicts")
def api_get_parcel_conflicts(
    id: str,
    db: Session = Depends(get_db),
):
    return get_parcel_conflicts(db, id)


@router.get("/api/spatial/nearby")
def api_find_nearby_parcels(
    lon: float = Query(..., ge=-180.0, le=180.0),
    lat: float = Query(..., ge=-90.0, le=90.0),
    radius_m: float = Query(default=250.0, gt=0.0, le=50000.0),
    project_id: str = Query(default="PROJ_SIH26012_DEMO"),
    db: Session = Depends(get_db),
):
    sql = text(
        """
        SELECT
            id,
            project_id,
            scene_id,
            land_use_class,
            area_sqm,
            confidence,
            ROUND(CAST(ST_Distance(
                ST_Transform(geom, 32643),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32643)
            ) AS numeric), 2) AS distance_m
        FROM parcels
        WHERE project_id = :project_id
          AND parcel_layer = 'CANDIDATE'
          AND ST_DWithin(
                ST_Transform(geom, 32643),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32643),
                :radius_m
          )
        ORDER BY distance_m ASC
        """
    )
    rows = db.execute(
        sql,
        {"lon": lon, "lat": lat, "radius_m": radius_m, "project_id": project_id},
    ).mappings().all()
    return {
        "query": {"lon": lon, "lat": lat, "radius_m": radius_m, "project_id": project_id},
        "count": len(rows),
        "parcels": [dict(r) for r in rows],
    }
