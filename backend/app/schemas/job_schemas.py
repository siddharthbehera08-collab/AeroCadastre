"""
Job and Processing Schemas for AeroCadastre Backend Orchestration.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class JobStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJobStep(BaseModel):
    step_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_sec: Optional[float] = None
    input_count: int = 0
    output_count: int = 0
    warnings: List[str] = []
    errors: List[str] = []
    provenance: Dict[str, Any] = {}


class ProcessingJobResponse(BaseModel):
    job_id: str
    project_id: str
    scene_id: str
    status: JobStatusEnum
    current_step: Optional[str] = None
    progress_pct: float = 0.0
    created_at: str
    updated_at: str
    steps: List[ProcessingJobStep] = []
    summary_metrics: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}


class DatasetRegisterRequest(BaseModel):
    dataset_name: str
    modality: str = "OPTICAL_VHR"  # OPTICAL_VHR, TERRAIN_DEM, VECTOR_BUILDING, VECTOR_ROAD, CADASTRE_REF
    file_path: str
    declared_crs: str = "EPSG:32643"
    data_mode: str = "SYNTHETIC"  # SYNTHETIC, REAL, BENCHMARK
    description: Optional[str] = ""


class ProcessProjectRequest(BaseModel):
    scene_id: str = "SCENE_PUNE_CORE_01"
    data_mode: str = "SYNTHETIC"
    min_parcel_area_m2: float = 20.0
    operator_id: str = "Surveyor_Verifier_01"
