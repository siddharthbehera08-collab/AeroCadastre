-- ============================================================================
-- SIH26012 — AeroCadastre: PostGIS Spatial Database Schema
-- Ministry of Rural Development, Department of Land Resources
-- Supports EPSG:4326 (WGS84 Geographic) and EPSG:32643 (UTM Zone 43N India)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 1. Projects
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    region_name VARCHAR(255) DEFAULT 'Synthetic Urban Sector (India)',
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    projected_crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:32643',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    data_label VARCHAR(128) NOT NULL DEFAULT 'SYNTHETIC DEMO DATA',
    ulpin_metadata_mode VARCHAR(64) NOT NULL DEFAULT 'ULPIN_READY_METADATA',
    bbox_geojson TEXT,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_projects_geom ON projects USING GIST (geom);

-- 2. Datasets
CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    dataset_type VARCHAR(64) NOT NULL, -- DRONE_RGB, ORI, DSM, DTM, REFERENCE_GIS, SYNTHETIC_SCENE
    temporal_epoch VARCHAR(32) NOT NULL DEFAULT 'T1', -- T0, T1, T2
    source_format VARCHAR(64) NOT NULL, -- GeoTIFF, PNG, GeoJSON, Shapefile, GeoPackage, CSV
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    file_path TEXT NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    validation_status VARCHAR(64) NOT NULL DEFAULT 'VALID',
    metadata_json TEXT,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_datasets_geom ON datasets USING GIST (geom);

-- 3. Rasters / Imagery
CREATE TABLE IF NOT EXISTS rasters (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dataset_id VARCHAR(64) REFERENCES datasets(id) ON DELETE SET NULL,
    scene_id VARCHAR(64) NOT NULL,
    raster_type VARCHAR(64) NOT NULL, -- RGB, ORI, DSM, DTM
    temporal_epoch VARCHAR(32) NOT NULL DEFAULT 'T1',
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    width INT NOT NULL,
    height INT NOT NULL,
    bands INT NOT NULL DEFAULT 3,
    pixel_resolution_m DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    nodata_value DOUBLE PRECISION,
    file_path TEXT NOT NULL,
    bounds_geojson TEXT NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rasters_geom ON rasters USING GIST (geom);
CREATE OR REPLACE VIEW imagery AS SELECT * FROM rasters;

-- 4. Buildings
CREATE TABLE IF NOT EXISTS buildings (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    temporal_epoch VARCHAR(32) NOT NULL DEFAULT 'T1',
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    area_sqm DOUBLE PRECISION NOT NULL,
    perimeter_m DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    centroid_lat DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    confidence_category VARCHAR(32) NOT NULL, -- HIGH, MEDIUM, LOW
    model_source VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL DEFAULT 'AI-GENERATED / REQUIRES VERIFICATION',
    verification_status VARCHAR(64) NOT NULL DEFAULT 'PENDING',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST (geom);

-- 5. Roads / Pathways / Access Corridors
CREATE TABLE IF NOT EXISTS roads (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    temporal_epoch VARCHAR(32) NOT NULL DEFAULT 'T1',
    road_class VARCHAR(64) NOT NULL, -- MAIN_ROAD, NARROW_LANE, PATHWAY, ACCESS_CORRIDOR
    width_m DOUBLE PRECISION NOT NULL,
    length_m DOUBLE PRECISION NOT NULL,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    confidence DOUBLE PRECISION NOT NULL,
    model_source VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL DEFAULT 'AI-GENERATED / REQUIRES VERIFICATION',
    verification_status VARCHAR(64) NOT NULL DEFAULT 'PENDING',
    geometry_geojson TEXT NOT NULL,
    corridor_geojson TEXT,
    geom GEOMETRY(Geometry, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST (geom);

-- 6. Land-Use Polygons
CREATE TABLE IF NOT EXISTS land_use (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    temporal_epoch VARCHAR(32) NOT NULL DEFAULT 'T1',
    land_use_class VARCHAR(64) NOT NULL, -- residential, commercial, industrial, agricultural, vegetation, water, vacant, road, mixed_use
    area_sqm DOUBLE PRECISION NOT NULL,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    confidence DOUBLE PRECISION NOT NULL,
    model_source VARCHAR(128) NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    data_label VARCHAR(128) NOT NULL DEFAULT 'SYNTHETIC DEMO DATA',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_land_use_geom ON land_use USING GIST (geom);

-- 7. Parcel Boundaries (Visible, Inferred, Reference, Human Verified)
CREATE TABLE IF NOT EXISTS boundaries (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    parcel_id VARCHAR(64),
    boundary_type VARCHAR(64) NOT NULL, -- VISIBLE, INFERRED, REFERENCE, HUMAN_VERIFIED
    length_m DOUBLE PRECISION NOT NULL,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    confidence DOUBLE PRECISION NOT NULL,
    evidence_sources_json TEXT NOT NULL,
    verification_status VARCHAR(64) NOT NULL DEFAULT 'PENDING',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(LineString, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_boundaries_geom ON boundaries USING GIST (geom);

-- 8. Parcels (Candidate, Reference, Human Verified)
CREATE TABLE IF NOT EXISTS parcels (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    temporal_epoch VARCHAR(32) NOT NULL DEFAULT 'T1',
    parcel_Layer VARCHAR(32) NOT NULL DEFAULT 'CANDIDATE', -- CANDIDATE, REFERENCE
    boundary_representation VARCHAR(64) NOT NULL DEFAULT 'INFERRED', -- VISIBLE, INFERRED, REFERENCE, HUMAN_VERIFIED
    land_use_class VARCHAR(64) NOT NULL DEFAULT 'residential',
    area_sqm DOUBLE PRECISION NOT NULL,
    perimeter_m DOUBLE PRECISION NOT NULL,
    compactness DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    building_count INT NOT NULL DEFAULT 0,
    road_access BOOLEAN NOT NULL DEFAULT TRUE,
    dsm_mean_elevation_m DOUBLE PRECISION DEFAULT 215.0,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    confidence DOUBLE PRECISION NOT NULL,
    confidence_category VARCHAR(32) NOT NULL, -- HIGH, MEDIUM, LOW
    confidence_breakdown_json TEXT NOT NULL,
    evidence_sources_json TEXT NOT NULL,
    topology_status VARCHAR(64) NOT NULL DEFAULT 'VALID',
    conflict_status VARCHAR(64) NOT NULL DEFAULT 'NONE',
    anomaly_status VARCHAR(64) NOT NULL DEFAULT 'NONE',
    verification_status VARCHAR(64) NOT NULL DEFAULT 'AI-GENERATED / REQUIRES VERIFICATION',
    verification_priority VARCHAR(32) NOT NULL DEFAULT 'MEDIUM', -- HIGH, MEDIUM, LOW
    council_decision VARCHAR(64) NOT NULL DEFAULT 'REQUIRES_VERIFICATION',
    ulpin_ready_metadata_json TEXT,
    provenance_json TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_parcels_geom ON parcels USING GIST (geom);

-- 9. Topology Issues
CREATE TABLE IF NOT EXISTS topology_issues (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    issue_type VARCHAR(64) NOT NULL, -- OVERLAP, GAP, SELF_INTERSECTION, INVALID_RING, SLIVER, DUPLICATE, HOLE, DISCONNECTED, INVALID_CRS
    severity VARCHAR(32) NOT NULL, -- HIGH, MEDIUM, LOW
    affected_features_json TEXT NOT NULL,
    area_sqm DOUBLE PRECISION DEFAULT 0.0,
    explanation TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Geometry, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_topology_issues_geom ON topology_issues USING GIST (geom);

-- 10. Anomalies & GIS Conflicts
CREATE TABLE IF NOT EXISTS anomalies (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    parcel_id VARCHAR(64),
    category VARCHAR(64) NOT NULL, -- ANOMALY, GIS_CONFLICT
    anomaly_type VARCHAR(64) NOT NULL, -- BOUNDARY_MISMATCH, BUILDING_CROSSING_BOUNDARY, ROAD_PARCEL_CONFLICT, EXTREME_AREA, UNUSUAL_SHAPE, MODEL_DISAGREEMENT, MISSING_PARCEL, EXTRA_PARCEL
    severity VARCHAR(32) NOT NULL, -- HIGH, MEDIUM, LOW
    confidence DOUBLE PRECISION NOT NULL,
    explanation TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Geometry, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_anomalies_geom ON anomalies USING GIST (geom);

-- 11. Temporal Change Events
CREATE TABLE IF NOT EXISTS changes (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    parcel_id VARCHAR(64),
    from_epoch VARCHAR(32) NOT NULL DEFAULT 'T0',
    to_epoch VARCHAR(32) NOT NULL DEFAULT 'T1',
    change_type VARCHAR(64) NOT NULL, -- NEW_BUILDING, REMOVED_BUILDING, LAND_USE_CHANGE, BOUNDARY_SHIFT, ROAD_CHANGE, AREA_CHANGE
    severity VARCHAR(32) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    summary TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Geometry, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_changes_geom ON changes USING GIST (geom);
CREATE OR REPLACE VIEW change_events AS SELECT * FROM changes;

-- 12. AI Council Decisions
CREATE TABLE IF NOT EXISTS council_decisions (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    parcel_id VARCHAR(64) NOT NULL,
    vision_score DOUBLE PRECISION NOT NULL,
    geometry_score DOUBLE PRECISION NOT NULL,
    gis_score DOUBLE PRECISION NOT NULL,
    ml_score DOUBLE PRECISION NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    field_need VARCHAR(32) NOT NULL,
    final_evidence_score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    decision VARCHAR(64) NOT NULL, -- ACCEPT_FOR_REVIEW, REQUIRES_VERIFICATION, LOW_CONFIDENCE, GEOMETRY_ERROR, CONFLICT_DETECTED
    recommended_action VARCHAR(64) NOT NULL,
    supporting_evidence_json TEXT NOT NULL,
    conflicting_evidence_json TEXT NOT NULL,
    agent_reports_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE OR REPLACE VIEW ai_council_results AS SELECT * FROM council_decisions;

-- 13. Verification Tasks / Records
CREATE TABLE IF NOT EXISTS verification_tasks (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    parcel_id VARCHAR(64) NOT NULL,
    priority VARCHAR(32) NOT NULL, -- HIGH, MEDIUM, LOW
    priority_score DOUBLE PRECISION NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'PENDING', -- PENDING, HUMAN_VERIFIED, REJECTED, FIELD_VISIT_REQUESTED
    reasons_json TEXT NOT NULL,
    council_decision VARCHAR(64) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    centroid_lat DOUBLE PRECISION NOT NULL,
    reviewer_notes TEXT,
    verified_by VARCHAR(128),
    verified_at TIMESTAMP WITH TIME ZONE,
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_verification_tasks_geom ON verification_tasks USING GIST (geom);
CREATE OR REPLACE VIEW verification_records AS SELECT * FROM verification_tasks;

-- 14. Field Routes & Field Tasks
CREATE TABLE IF NOT EXISTS field_routes (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    cluster_id INT NOT NULL,
    route_name VARCHAR(128) NOT NULL,
    task_count INT NOT NULL,
    estimated_distance_m DOUBLE PRECISION NOT NULL,
    ordered_stops_json TEXT NOT NULL,
    disclaimer VARCHAR(255) NOT NULL DEFAULT 'PROTOTYPE FIELD PLANNING TOOL - NOT NAVIGATION GRADE',
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(LineString, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_field_routes_geom ON field_routes USING GIST (geom);
CREATE OR REPLACE VIEW field_tasks AS SELECT * FROM verification_tasks;

-- 15. Feature Versions (Parcel Time Machine)
CREATE TABLE IF NOT EXISTS feature_versions (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    feature_id VARCHAR(64) NOT NULL,
    feature_type VARCHAR(32) NOT NULL DEFAULT 'PARCEL',
    version_number INT NOT NULL,
    temporal_epoch VARCHAR(32) NOT NULL, -- T0 (2024), T1 (2025), T2 (2026 AI), HUMAN_EDIT
    area_sqm DOUBLE PRECISION NOT NULL,
    perimeter_m DOUBLE PRECISION NOT NULL,
    land_use_class VARCHAR(64) NOT NULL,
    building_count INT NOT NULL DEFAULT 0,
    confidence DOUBLE PRECISION NOT NULL,
    status VARCHAR(64) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    change_summary TEXT NOT NULL,
    geometry_geojson TEXT NOT NULL,
    geom GEOMETRY(Polygon, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 16. Model Runs / Experiments
CREATE TABLE IF NOT EXISTS model_runs (
    id VARCHAR(64) PRIMARY KEY,
    task_type VARCHAR(64) NOT NULL, -- BUILDING_SEG, ROAD_SEG, LANDUSE_CLS, BOUNDARY_SEG
    model_name VARCHAR(128) NOT NULL,
    architecture VARCHAR(128) NOT NULL,
    dataset_name VARCHAR(128) NOT NULL DEFAULT 'SYNTHETIC_DEMO_V1',
    epochs INT NOT NULL,
    batch_size INT NOT NULL,
    learning_rate DOUBLE PRECISION NOT NULL,
    train_loss DOUBLE PRECISION NOT NULL,
    val_loss DOUBLE PRECISION NOT NULL,
    iou DOUBLE PRECISION NOT NULL,
    dice_f1 DOUBLE PRECISION NOT NULL,
    precision_score DOUBLE PRECISION NOT NULL,
    recall_score DOUBLE PRECISION NOT NULL,
    training_time_sec DOUBLE PRECISION NOT NULL,
    inference_time_ms DOUBLE PRECISION NOT NULL,
    checkpoint_path TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE OR REPLACE VIEW model_experiments AS SELECT * FROM model_runs;

-- 17. AI Predictions
CREATE TABLE IF NOT EXISTS ai_predictions (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_id VARCHAR(64) NOT NULL,
    model_run_id VARCHAR(64) REFERENCES model_runs(id) ON DELETE SET NULL,
    prediction_type VARCHAR(64) NOT NULL,
    feature_count INT NOT NULL,
    mean_confidence DOUBLE PRECISION NOT NULL,
    inference_time_ms DOUBLE PRECISION NOT NULL,
    artifact_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 18. Evidence & Provenance
CREATE TABLE IF NOT EXISTS evidence (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    feature_id VARCHAR(64) NOT NULL,
    feature_type VARCHAR(64) NOT NULL,
    source_name VARCHAR(128) NOT NULL,
    evidence_type VARCHAR(64) NOT NULL,
    weight DOUBLE PRECISION NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    details_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE OR REPLACE VIEW provenance AS SELECT * FROM evidence;

-- 19. Human-in-the-Loop Feedback Store
CREATE TABLE IF NOT EXISTS human_feedback (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    feature_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(64) NOT NULL, -- GEOMETRY_EDIT, SPLIT, MERGE, CLASS_CHANGE, VERIFY, REJECT
    before_geometry_geojson TEXT,
    after_geometry_geojson TEXT,
    before_class VARCHAR(64),
    after_class VARCHAR(64),
    operator_id VARCHAR(128) NOT NULL DEFAULT 'Surveyor_Verifier_01',
    reason TEXT,
    exported_for_retraining BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 20. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    operation VARCHAR(128) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    old_value_json TEXT,
    new_value_json TEXT,
    source VARCHAR(128) NOT NULL,
    model_name VARCHAR(128),
    confidence DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
