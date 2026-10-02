import json
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
)
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import from_shape, to_shape
from shapely import wkt
from shapely.geometry import shape, mapping

from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    """Core Table 1: Users & Surveyor / Administrator Roles."""

    __tablename__ = "users"
    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False, default="SURVEYOR")  # SURVEYOR, ADMINISTRATOR, DEMO_USER
    department = Column(
        String(255),
        nullable=False,
        default="Department of Land Resources (DoLR)",
    )
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Project(Base):
    """Core Table 2: Cadastral Survey Projects."""

    __tablename__ = "projects"
    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    region_name = Column(String(255), default="Synthetic Urban Sector (India)")
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    projected_crs = Column(String(32), nullable=False, default="EPSG:32643")
    is_synthetic = Column(Boolean, nullable=False, default=True)
    data_label = Column(String(128), nullable=False, default="SYNTHETIC DEMO DATA")
    ulpin_metadata_mode = Column(String(64), nullable=False, default="ULPIN_READY_METADATA")
    bbox_geojson = Column(Text, nullable=True)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Dataset(Base):
    """Core Table 3: Geospatial Datasets (Drone Ortho, DSM, Reference GIS)."""

    __tablename__ = "datasets"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    dataset_type = Column(String(64), nullable=False)
    temporal_epoch = Column(String(32), nullable=False, default="T1")
    source_format = Column(String(64), nullable=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    file_path = Column(Text, nullable=False)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    validation_status = Column(String(64), nullable=False, default="VALID")
    metadata_json = Column(Text, default="{}")
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Parcel(Base):
    """Core Table 4: Cadastral Parcels (Candidate, Reference, Human-Verified)."""

    __tablename__ = "parcels"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    temporal_epoch = Column(String(32), nullable=False, default="T1")
    parcel_layer = Column(String(32), nullable=False, default="CANDIDATE")  # CANDIDATE, REFERENCE
    boundary_representation = Column(
        String(64), nullable=False, default="INFERRED"
    )  # VISIBLE, INFERRED, REFERENCE, HUMAN_VERIFIED
    land_use_class = Column(String(64), nullable=False, default="residential")
    area_sqm = Column(Float, nullable=False)
    perimeter_m = Column(Float, nullable=False)
    compactness = Column(Float, nullable=False, default=0.0)
    building_count = Column(Integer, nullable=False, default=0)
    road_access = Column(Boolean, nullable=False, default=True)
    dsm_mean_elevation_m = Column(Float, default=215.0)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    confidence = Column(Float, nullable=False, default=0.85)
    confidence_category = Column(String(32), nullable=False, default="HIGH")
    confidence_breakdown_json = Column(Text, nullable=False, default="{}")
    evidence_sources_json = Column(Text, nullable=False, default="[]")
    topology_status = Column(String(64), nullable=False, default="VALID")
    conflict_status = Column(String(64), nullable=False, default="NONE")
    anomaly_status = Column(String(64), nullable=False, default="NONE")
    verification_status = Column(
        String(64), nullable=False, default="AI-GENERATED / REQUIRES VERIFICATION"
    )
    verification_priority = Column(String(32), nullable=False, default="MEDIUM")
    council_decision = Column(String(64), nullable=False, default="REQUIRES_VERIFICATION")
    ulpin_ready_metadata_json = Column(Text, nullable=True)
    provenance_json = Column(Text, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=1)
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Building(Base):
    """Core Table 5: Extracted Building Footprints."""

    __tablename__ = "buildings"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parcel_id = Column(String(64), nullable=True, index=True)
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    temporal_epoch = Column(String(32), nullable=False, default="T1")
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    area_sqm = Column(Float, nullable=False)
    perimeter_m = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    centroid_lat = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    confidence_category = Column(String(32), nullable=False)
    model_source = Column(String(128), nullable=False)
    source_type = Column(
        String(64), nullable=False, default="AI-GENERATED / REQUIRES VERIFICATION"
    )
    verification_status = Column(String(64), nullable=False, default="PENDING")
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Road(Base):
    """Core Table 6: Extracted Roads & Access Corridors."""

    __tablename__ = "roads"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    temporal_epoch = Column(String(32), nullable=False, default="T1")
    road_class = Column(String(64), nullable=False)
    width_m = Column(Float, nullable=False)
    length_m = Column(Float, nullable=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    confidence = Column(Float, nullable=False)
    model_source = Column(String(128), nullable=False)
    source_type = Column(
        String(64), nullable=False, default="AI-GENERATED / REQUIRES VERIFICATION"
    )
    verification_status = Column(String(64), nullable=False, default="PENDING")
    geometry_geojson = Column(Text, nullable=False)
    corridor_geojson = Column(Text, nullable=True)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class LandUse(Base):
    """Core Table 7: Land-Use Classification Polygons."""

    __tablename__ = "land_use"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    temporal_epoch = Column(String(32), nullable=False, default="T1")
    land_use_class = Column(String(64), nullable=False)
    area_sqm = Column(Float, nullable=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    confidence = Column(Float, nullable=False)
    model_source = Column(String(128), nullable=False)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    data_label = Column(String(128), nullable=False, default="SYNTHETIC DEMO DATA")
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ModelRun(Base):
    """Core Table 8: ML Training & Evaluation Runs."""

    __tablename__ = "model_runs"
    id = Column(String(64), primary_key=True)
    task_type = Column(String(64), nullable=False, index=True)
    model_name = Column(String(128), nullable=False)
    architecture = Column(String(128), nullable=False)
    dataset_name = Column(String(128), nullable=False, default="SYNTHETIC_DEMO_V1")
    epochs = Column(Integer, nullable=False)
    batch_size = Column(Integer, nullable=False)
    learning_rate = Column(Float, nullable=False)
    train_loss = Column(Float, nullable=False)
    val_loss = Column(Float, nullable=False)
    iou = Column(Float, nullable=False)
    dice_f1 = Column(Float, nullable=False)
    precision_score = Column(Float, nullable=False)
    recall_score = Column(Float, nullable=False)
    training_time_sec = Column(Float, nullable=False)
    inference_time_ms = Column(Float, nullable=False)
    checkpoint_path = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AIPrediction(Base):
    """Core Table 9: Persisted AI Analysis & Inference Runs."""

    __tablename__ = "ai_predictions"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True)
    model_run_id = Column(
        String(64), ForeignKey("model_runs.id", ondelete="SET NULL"), nullable=True
    )
    prediction_type = Column(String(64), nullable=False)
    feature_count = Column(Integer, nullable=False)
    mean_confidence = Column(Float, nullable=False)
    inference_time_ms = Column(Float, nullable=False)
    artifact_path = Column(Text, nullable=True)
    details_json = Column(Text, nullable=True, default="{}")
    created_at = Column(DateTime(timezone=True), default=utc_now)


class CouncilDecision(Base):
    """Core Table 10: Six-Agent AI Council Deliberation Decisions."""

    __tablename__ = "council_decisions"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    parcel_id = Column(String(64), nullable=False, index=True)
    vision_score = Column(Float, nullable=False)
    geometry_score = Column(Float, nullable=False)
    gis_score = Column(Float, nullable=False)
    ml_score = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    field_need = Column(String(32), nullable=False)
    final_evidence_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    decision = Column(String(64), nullable=False)
    recommended_action = Column(String(64), nullable=False)
    supporting_evidence_json = Column(Text, nullable=False)
    conflicting_evidence_json = Column(Text, nullable=False)
    agent_reports_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class TopologyIssue(Base):
    """Core Table 11: Spatial Topology Validation Issues (Overlaps, Gaps, Self-Intersections)."""

    __tablename__ = "topology_issues"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    issue_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    affected_features_json = Column(Text, nullable=False)
    area_sqm = Column(Float, default=0.0)
    explanation = Column(Text, nullable=False)
    resolved = Column(Boolean, nullable=False, default=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class VerificationRecord(Base):
    """Core Table 12: Surveyor Verification Queue & Sign-Off Records."""

    __tablename__ = "verification_records"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    parcel_id = Column(String(64), nullable=False, index=True)
    priority = Column(String(32), nullable=False, default="MEDIUM")
    priority_score = Column(Float, nullable=False, default=0.5)
    status = Column(String(64), nullable=False, default="PENDING")
    reasons_json = Column(Text, nullable=False, default="[]")
    council_decision = Column(String(64), nullable=False, default="REQUIRES_VERIFICATION")
    confidence = Column(Float, nullable=False, default=0.80)
    centroid_lon = Column(Float, nullable=False, default=77.592)
    centroid_lat = Column(Float, nullable=False, default=12.972)
    reviewer_notes = Column(Text, nullable=True)
    verified_by = Column(String(128), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ChangeEvent(Base):
    """Core Table 13: Multi-Temporal Cadastral Change Events (T0 -> T1 -> T2)."""

    __tablename__ = "change_events"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    parcel_id = Column(String(64), nullable=True, index=True)
    from_epoch = Column(String(32), nullable=False, default="T0")
    to_epoch = Column(String(32), nullable=False, default="T1")
    change_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False)
    summary = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class FieldTask(Base):
    """Core Table 14: Field Verification Tasks & Stop Assignments."""

    __tablename__ = "field_tasks"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True, default="scene_urban_T1")
    parcel_id = Column(String(64), nullable=False, index=True)
    route_id = Column(String(64), nullable=True, index=True)
    sequence_order = Column(Integer, nullable=False, default=1)
    priority = Column(String(32), nullable=False, default="HIGH")
    priority_score = Column(Float, nullable=False, default=0.75)
    status = Column(String(64), nullable=False, default="ASSIGNED")
    assigned_to = Column(String(128), nullable=False, default="Surveyor_Verifier_01")
    reasons_json = Column(Text, nullable=False, default="[]")
    centroid_lon = Column(Float, nullable=False, default=77.592)
    centroid_lat = Column(Float, nullable=False, default=12.972)
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    """Core Table 15: Immutable System & Surveyor Audit Logs."""

    __tablename__ = "audit_logs"
    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    operation = Column(String(128), nullable=False)
    target_id = Column(String(64), nullable=False, index=True)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    source = Column(String(128), nullable=False)
    model_name = Column(String(128), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


# Supporting Spatial & Provenance Tables
class Raster(Base):
    __tablename__ = "rasters"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id = Column(
        String(64), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    scene_id = Column(String(64), nullable=False, index=True)
    raster_type = Column(String(64), nullable=False)
    temporal_epoch = Column(String(32), nullable=False, default="T1")
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    bands = Column(Integer, nullable=False, default=3)
    pixel_resolution_m = Column(Float, nullable=False, default=0.5)
    nodata_value = Column(Float, nullable=True)
    file_path = Column(Text, nullable=False)
    bounds_geojson = Column(Text, nullable=False)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Boundary(Base):
    __tablename__ = "boundaries"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True)
    parcel_id = Column(String(64), nullable=True, index=True)
    boundary_type = Column(String(64), nullable=False)
    length_m = Column(Float, nullable=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    confidence = Column(Float, nullable=False)
    evidence_sources_json = Column(Text, nullable=False)
    verification_status = Column(String(64), nullable=False, default="PENDING")
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True)
    parcel_id = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=False)
    anomaly_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=False)
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class FieldRoute(Base):
    __tablename__ = "field_routes"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(String(64), nullable=False, index=True)
    cluster_id = Column(Integer, nullable=False)
    route_name = Column(String(128), nullable=False)
    task_count = Column(Integer, nullable=False)
    estimated_distance_m = Column(Float, nullable=False)
    ordered_stops_json = Column(Text, nullable=False)
    disclaimer = Column(
        String(255),
        nullable=False,
        default="PROTOTYPE FIELD PLANNING TOOL - NOT NAVIGATION GRADE",
    )
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class FeatureVersion(Base):
    __tablename__ = "feature_versions"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id = Column(String(64), nullable=False, index=True)
    feature_type = Column(String(32), nullable=False, default="PARCEL")
    version_number = Column(Integer, nullable=False)
    temporal_epoch = Column(String(32), nullable=False)
    area_sqm = Column(Float, nullable=False)
    perimeter_m = Column(Float, nullable=False)
    land_use_class = Column(String(64), nullable=False)
    building_count = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False)
    status = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=False)
    change_summary = Column(Text, nullable=False)
    geometry_geojson = Column(Text, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id = Column(String(64), nullable=False, index=True)
    feature_type = Column(String(64), nullable=False)
    source_name = Column(String(128), nullable=False)
    evidence_type = Column(String(64), nullable=False)
    weight = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    details_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class HumanFeedback(Base):
    __tablename__ = "human_feedback"
    id = Column(String(64), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    before_geometry_geojson = Column(Text, nullable=True)
    after_geometry_geojson = Column(Text, nullable=True)
    before_class = Column(String(64), nullable=True)
    after_class = Column(String(64), nullable=True)
    operator_id = Column(String(128), nullable=False, default="Surveyor_Verifier_01")
    reason = Column(Text, nullable=True)
    exported_for_retraining = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


# Backward-compatible aliases for legacy pipeline references
VerificationTask = VerificationRecord
RasterAsset = Raster


def _normalize_postgis_geometry(mapper, connection, target):
    """
    Ensure every spatial model instance automatically converts WKT/GeoJSON/Shapely geometry
    into a GeoAlchemy2 WKBElement(srid=4326) for PostGIS and keeps geometry_geojson synchronized.
    """
    raw_geom = getattr(target, "geom", None)
    raw_geojson = getattr(target, "geometry_geojson", None) or getattr(
        target, "bbox_geojson", None
    ) or getattr(target, "bounds_geojson", None)

    shp = None
    if isinstance(raw_geom, (WKBElement, WKTElement)):
        try:
            shp = to_shape(raw_geom)
        except Exception:
            shp = None
    elif isinstance(raw_geom, str) and raw_geom.strip():
        s = raw_geom.strip()
        try:
            shp = shape(json.loads(s)) if s.startswith("{") else wkt.loads(s)
        except Exception:
            shp = None
    elif raw_geom is not None and hasattr(raw_geom, "geom_type"):
        shp = raw_geom

    if shp is None and isinstance(raw_geojson, str) and raw_geojson.strip():
        try:
            shp = shape(json.loads(raw_geojson))
        except Exception:
            shp = None

    if shp is not None and not shp.is_empty:
        target.geom = from_shape(shp, srid=4326)
        if hasattr(target, "geometry_geojson") and not getattr(target, "geometry_geojson", None):
            target.geometry_geojson = json.dumps(mapping(shp))


SPATIAL_MODELS = (
    Project,
    Dataset,
    Parcel,
    Building,
    Road,
    LandUse,
    TopologyIssue,
    VerificationRecord,
    ChangeEvent,
    FieldTask,
    Raster,
    Boundary,
    Anomaly,
    FieldRoute,
    FeatureVersion,
)

for _model_cls in SPATIAL_MODELS:
    event.listen(_model_cls, "before_insert", _normalize_postgis_geometry)
    event.listen(_model_cls, "before_update", _normalize_postgis_geometry)
