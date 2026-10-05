from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_optional_user
from backend.app.schemas.api_schemas import (
    ParcelCreateRequest,
    ParcelUpdateRequest,
    ParcelSplitRequest,
    ParcelMergeRequest,
    DynamicParcellingRequest,
)
from backend.app.services.parcel_service import (
    list_project_parcels,
    get_parcel_by_id,
    create_parcel,
    update_parcel,
    delete_parcel,
    split_parcel,
    merge_parcels,
)

router = APIRouter(tags=["Parcels"])


@router.get("/api/projects/{project_id}/parcels")
def api_list_project_parcels(
    project_id: str,
    scene_id: Optional[str] = None,
    layer: str = "CANDIDATE",
    bbox: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_project_parcels(
        db, project_id=project_id, scene_id=scene_id, layer=layer, bbox=bbox
    )


@router.get("/api/parcels")
def api_list_parcels_query(
    project_id: str = "PROJ_SIH26012_DEMO",
    scene_id: Optional[str] = "scene_urban_T1",
    layer: str = "CANDIDATE",
    bbox: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_project_parcels(
        db, project_id=project_id, scene_id=scene_id, layer=layer, bbox=bbox
    )


@router.post("/api/parcels", status_code=status.HTTP_201_CREATED)
def api_create_parcel(
    req: ParcelCreateRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return create_parcel(db, req)


@router.post("/api/parcels/merge")
def api_merge_parcels(
    req: ParcelMergeRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return merge_parcels(db, req)


@router.get("/api/parcels/{id}")
def api_get_parcel(id: str, db: Session = Depends(get_db)):
    return get_parcel_by_id(db, id)


@router.put("/api/parcels/{id}")
def api_update_parcel(
    id: str,
    req: ParcelUpdateRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return update_parcel(db, id, req)


@router.delete("/api/parcels/{id}")
def api_delete_parcel(
    id: str,
    operator_id: str = "Surveyor_Verifier_01",
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return delete_parcel(db, id, operator_id=operator_id)


@router.post("/api/parcels/{parcel_id}/split")
def api_split_parcel(
    parcel_id: str,
    req: ParcelSplitRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return split_parcel(db, parcel_id, req)


@router.post("/api/parcels/generate-candidates")
def api_generate_candidate_parcels(
    req: DynamicParcellingRequest,
    _user: dict = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Generate dynamic preliminary parcel candidates from real imagery and multi-model GeoAI evidence.
    Returns GeoJSON FeatureCollection with explicit AI-generated provenance and topology validation.
    """
    from backend.app.services.parcel_service import generate_dynamic_candidates

    return generate_dynamic_candidates(
        db=db,
        aoi_bounds=req.aoi_bounds,
        project_id=req.project_id,
        resolution=req.resolution,
        persist_to_postgis=req.persist_to_postgis,
        operator_id=req.operator_id,
    )
