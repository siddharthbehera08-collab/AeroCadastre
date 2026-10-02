from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    description: Optional[str] = ""
    region_name: Optional[str] = "Synthetic Urban Sector (India)"
    crs: str = "EPSG:4326"
    projected_crs: str = "EPSG:32643"


class PipelineRunRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"


class ParcelCreateRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    land_use_class: str = "residential"
    boundary_representation: str = "HUMAN_VERIFIED"
    geometry: Dict[str, Any]
    operator_id: str = "Surveyor_Verifier_01"
    reason: Optional[str] = "Manual parcel digitization in Web-GIS"


class ParcelUpdateRequest(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    land_use_class: Optional[str] = None
    boundary_representation: Optional[str] = None
    verification_status: Optional[str] = None
    operator_id: str = "Surveyor_Verifier_01"
    reason: Optional[str] = "Human surveyor verification / geometry correction"


class ParcelSplitRequest(BaseModel):
    split_axis: str = "VERTICAL"  # VERTICAL, HORIZONTAL, or custom_line
    split_ratio: float = Field(default=0.5, ge=0.15, le=0.85)
    cut_line_geojson: Optional[Dict[str, Any]] = None
    operator_id: str = "Surveyor_Verifier_01"
    reason: Optional[str] = "Parcel subdivision during surveyor review"


class ParcelMergeRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    parcel_id_a: str
    parcel_id_b: str
    operator_id: str = "Surveyor_Verifier_01"
    reason: Optional[str] = "Parcel amalgamation during surveyor review"


class VerificationActionRequest(BaseModel):
    action: str  # HUMAN_VERIFIED, REJECTED, FIELD_VISIT_REQUESTED, ACCEPT_CANDIDATE
    operator_id: str = "Surveyor_Verifier_01"
    notes: Optional[str] = "Reviewed in Verification Center"


class CopilotQueryRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    question: str


class ExportRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    export_format: str = "GeoJSON"  # GeoJSON, Shapefile, CSV, GeoPackage
