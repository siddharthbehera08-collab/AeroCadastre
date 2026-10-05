from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# 1. Authentication Schemas
# ============================================================================
class LoginRequest(BaseModel):
    email: str = Field(default="surveyor@aerocadastre.gov.in")
    password: str = Field(default="demo_surveyor_2026")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department: str
    is_active: bool


# ============================================================================
# 2. Project Schemas
# ============================================================================
class ProjectCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = ""
    region_name: Optional[str] = "Synthetic Urban Sector (India)"
    crs: str = "EPSG:4326"
    projected_crs: str = "EPSG:32643"
    bbox_geojson: Optional[Dict[str, Any]] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    region_name: Optional[str] = None
    crs: Optional[str] = None
    projected_crs: Optional[str] = None
    bbox_geojson: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    region_name: Optional[str] = ""
    crs: str
    projected_crs: str
    is_synthetic: bool
    data_label: str
    ulpin_metadata_mode: str
    bbox_geometry: Optional[Dict[str, Any]] = None
    parcel_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================================
# 3. Parcel Schemas
# ============================================================================
class ParcelCreateRequest(BaseModel):
    id: Optional[str] = None
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    land_use_class: str = "residential"
    boundary_representation: str = "HUMAN_VERIFIED"
    crs: str = "EPSG:4326"
    geometry: Dict[str, Any]
    operator_id: str = "Surveyor_Verifier_01"
    reason: Optional[str] = "Manual parcel digitization in Web-GIS"


class ParcelUpdateRequest(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    crs: Optional[str] = "EPSG:4326"
    land_use_class: Optional[str] = None
    boundary_representation: Optional[str] = None
    verification_status: Optional[str] = None
    operator_id: str = "Surveyor_Verifier_01"
    reason: Optional[str] = "Human surveyor verification / geometry correction"


class ParcelSplitRequest(BaseModel):
    split_axis: str = "VERTICAL"
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


class ParcelResponse(BaseModel):
    id: str
    project_id: str
    scene_id: str
    temporal_epoch: str
    parcel_layer: str
    boundary_representation: str
    land_use_class: str
    area_sqm: float
    perimeter_m: float
    compactness: float
    building_count: int
    road_access: bool
    dsm_mean_elevation_m: Optional[float] = 215.0
    crs: str
    confidence: float
    confidence_category: str
    confidence_breakdown: Dict[str, Any]
    evidence_sources: List[str]
    topology_status: str
    conflict_status: str
    anomaly_status: str
    verification_status: str
    verification_priority: str
    council_decision: str
    ulpin_ready_metadata: Dict[str, Any]
    provenance: Dict[str, Any]
    version: int
    geometry: Dict[str, Any]
    geojson_feature: Optional[Dict[str, Any]] = None
    updated_at: Optional[str] = None


class DynamicParcellingRequest(BaseModel):
    aoi_bounds: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box [min_lon, min_lat, max_lon, max_lat] in EPSG:4326.",
    )
    project_id: str = Field(default="PROJ_SIH26012_DEMO")
    resolution: float = Field(default=0.5, ge=0.1, le=20.0)
    persist_to_postgis: bool = Field(default=True)
    operator_id: str = Field(default="Surveyor_Verifier_01")


# ============================================================================
# 4. Verification Schemas
# ============================================================================
class VerificationCreateRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    parcel_id: str = Field(..., min_length=2)
    status: str = Field(
        default="HUMAN_VERIFIED",
        description="HUMAN_VERIFIED, REJECTED, FIELD_VISIT_REQUESTED, PENDING",
    )
    priority: Optional[str] = None
    reviewer_notes: Optional[str] = "Surveyor verification submitted via REST API"
    verified_by: str = "Surveyor_Verifier_01"


class VerificationUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    reviewer_notes: Optional[str] = None
    verified_by: Optional[str] = "Surveyor_Verifier_01"


class VerificationActionRequest(BaseModel):
    action: str
    operator_id: str = "Surveyor_Verifier_01"
    notes: Optional[str] = "Reviewed in Verification Center"


# ============================================================================
# 5. AI Analysis & Council Schemas
# ============================================================================
class AnalysisRunRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    prediction_type: str = "FULL_SCENE_CADASTRAL_INFERENCE"


class PipelineRunRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"


class CouncilAnalyzeRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    parcel_id: str = Field(..., min_length=2)


# ============================================================================
# 6. Export & Copilot Schemas
# ============================================================================
class ExportRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    export_format: str = "GeoJSON"


class CopilotQueryRequest(BaseModel):
    project_id: str = "PROJ_SIH26012_DEMO"
    scene_id: str = "scene_urban_T1"
    question: Optional[str] = None
    query: Optional[str] = None
    selected_parcel_id: Optional[str] = None

