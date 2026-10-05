-- ============================================================================
-- AeroCadastre SIH26012: Production-Oriented PostGIS Database Schema
-- Standard CRS: EPSG:32643 (UTM Zone 43N) & EPSG:4326 (WGS 84)
-- ============================================================================

-- Ensure PostGIS spatial extension is available
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 1. MODEL REGISTRY
CREATE TABLE IF NOT EXISTS model_registry (
    id VARCHAR(64) PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    model_family VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL,
    checkpoint_uri VARCHAR(256),
    feature_schema JSONB,
    metrics JSONB,
    provenance JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. EXPERIMENT REGISTRY
CREATE TABLE IF NOT EXISTS experiment_registry (
    id VARCHAR(64) PRIMARY KEY,
    experiment_name VARCHAR(128) NOT NULL,
    model_id VARCHAR(64) REFERENCES model_registry(id) ON DELETE CASCADE,
    dataset_name VARCHAR(128) NOT NULL,
    split_method VARCHAR(64),
    train_metrics JSONB,
    val_metrics JSONB,
    test_metrics JSONB,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. GIS REFERENCES (Legacy cadastral maps, OSM base layers, SOI toposheets)
CREATE TABLE IF NOT EXISTS gis_references (
    id VARCHAR(64) PRIMARY KEY,
    source_name VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL, -- OSM, SOI, REVENUE_MAP
    survey_year INTEGER,
    reliability_score DOUBLE PRECISION DEFAULT 0.75,
    crs VARCHAR(32) DEFAULT 'EPSG:32643',
    geom GEOMETRY(Geometry, 32643) NOT NULL,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gis_references_geom ON gis_references USING GIST (geom);

-- 4. BOUNDARY EVIDENCE (Candidate edge line segments)
CREATE TABLE IF NOT EXISTS boundary_evidence (
    id VARCHAR(64) PRIMARY KEY,
    edge_type VARCHAR(64) NOT NULL, -- ROAD_MARGIN, BUILDING_SETBACK, VORONOI
    boundary_score DOUBLE PRECISION NOT NULL,
    boundary_strength VARCHAR(16) NOT NULL, -- HIGH, MEDIUM, LOW
    uncertainty DOUBLE PRECISION NOT NULL,
    length_m DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(LineString, 32643) NOT NULL,
    evidence_sources JSONB,
    provenance JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_boundary_evidence_geom ON boundary_evidence USING GIST (geom);

-- 5. TERRAIN FEATURES (Topographic context for parcels/polygons)
CREATE TABLE IF NOT EXISTS terrain_features (
    id VARCHAR(64) PRIMARY KEY,
    grid_cell_row INTEGER,
    grid_cell_col INTEGER,
    elevation_mean DOUBLE PRECISION NOT NULL,
    slope_mean DOUBLE PRECISION NOT NULL,
    aspect_mean DOUBLE PRECISION,
    relief_mean DOUBLE PRECISION,
    hillshade_mean DOUBLE PRECISION,
    steep_slope_flag BOOLEAN DEFAULT FALSE,
    flood_prone_flag BOOLEAN DEFAULT FALSE,
    geom GEOMETRY(Polygon, 32643),
    provenance JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_terrain_features_geom ON terrain_features USING GIST (geom);

-- 6. PARCELS (Candidate & Verified Cadastral Parcels)
CREATE TABLE IF NOT EXISTS parcels (
    id VARCHAR(64) PRIMARY KEY,
    candidate_id VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(32) DEFAULT 'CANDIDATE', -- CANDIDATE, VERIFIED, REJECTED
    boundary_type VARCHAR(64) DEFAULT 'INFERRED_PARCEL_BOUNDARY',
    area_sqm DOUBLE PRECISION NOT NULL,
    perimeter_m DOUBLE PRECISION NOT NULL,
    compactness DOUBLE PRECISION NOT NULL,
    building_count INTEGER DEFAULT 0,
    building_coverage_ratio DOUBLE PRECISION DEFAULT 0.0,
    has_road_access BOOLEAN DEFAULT FALSE,
    confidence_score DOUBLE PRECISION NOT NULL,
    uncertainty DOUBLE PRECISION NOT NULL,
    confidence_band VARCHAR(16) NOT NULL, -- HIGH, MEDIUM, LOW, REJECT
    geom GEOMETRY(Polygon, 32643) NOT NULL,
    provenance JSONB,
    ulpin_metadata JSONB, -- Metadata readiness only; NEVER fake ULPIN
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_parcels_geom ON parcels USING GIST (geom);

-- 7. PARCEL EVIDENCE (Multi-source evidence attachments)
CREATE TABLE IF NOT EXISTS parcel_evidence (
    id VARCHAR(64) PRIMARY KEY,
    parcel_id VARCHAR(64) REFERENCES parcels(id) ON DELETE CASCADE,
    domain VARCHAR(32) NOT NULL, -- BUILDING, ROAD, BOUNDARY, TERRAIN, LULC, GIS_REFERENCE
    status VARCHAR(16) NOT NULL, -- AVAILABLE, UNAVAILABLE
    confidence DOUBLE PRECISION,
    weight DOUBLE PRECISION NOT NULL,
    model_version VARCHAR(64),
    features JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_parcel_evidence_pid ON parcel_evidence(parcel_id);

-- 8. MODEL PREDICTIONS (Raw inference outputs from neural models)
CREATE TABLE IF NOT EXISTS model_predictions (
    id VARCHAR(64) PRIMARY KEY,
    model_id VARCHAR(64) REFERENCES model_registry(id) ON DELETE SET NULL,
    target_entity VARCHAR(64) NOT NULL, -- BUILDING, ROAD, LULC
    prediction_confidence DOUBLE PRECISION NOT NULL,
    prediction_class VARCHAR(64),
    geom GEOMETRY(Geometry, 32643),
    raw_probabilities JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_model_predictions_geom ON model_predictions USING GIST (geom);

-- 9. CONFLICTS (Spatial discrepancies between candidate parcels & legacy reference GIS)
CREATE TABLE IF NOT EXISTS conflicts (
    id VARCHAR(64) PRIMARY KEY,
    candidate_id VARCHAR(64) REFERENCES parcels(id) ON DELETE CASCADE,
    reference_id VARCHAR(64) REFERENCES gis_references(id) ON DELETE SET NULL,
    conflict_type VARCHAR(64) NOT NULL, -- HIGH_BOUNDARY_DISPLACEMENT, LOW_IOU, EXTRA_PARCEL
    severity VARCHAR(16) NOT NULL, -- CRITICAL, WARNING, INFO
    metric_value DOUBLE PRECISION,
    explanation TEXT NOT NULL,
    geom GEOMETRY(Geometry, 32643),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conflicts_geom ON conflicts USING GIST (geom);

-- 10. ANOMALIES (Topological and physical anomalies)
CREATE TABLE IF NOT EXISTS anomalies (
    id VARCHAR(64) PRIMARY KEY,
    parcel_id VARCHAR(64) REFERENCES parcels(id) ON DELETE CASCADE,
    rule_id VARCHAR(64) NOT NULL, -- H003_BUILDING_ROAD_INTERSECTION, G014_PARCEL_GAP
    severity VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    geom GEOMETRY(Geometry, 32643),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_anomalies_geom ON anomalies USING GIST (geom);

-- 11. COUNCIL RESULTS (Deliberations of the 6-agent AI Council)
CREATE TABLE IF NOT EXISTS council_results (
    id VARCHAR(64) PRIMARY KEY,
    parcel_id VARCHAR(64) REFERENCES parcels(id) ON DELETE CASCADE,
    council_version VARCHAR(32) NOT NULL,
    ruleset_version VARCHAR(32) NOT NULL,
    input_hash VARCHAR(32) NOT NULL,
    configuration_hash VARCHAR(32) NOT NULL,
    decision VARCHAR(64) NOT NULL, -- ACCEPT_FOR_REVIEW, REQUIRES_VERIFICATION, LOW_CONFIDENCE, GEOMETRY_ERROR, CONFLICT_DETECTED
    recommended_action VARCHAR(64) NOT NULL,
    final_evidence_score DOUBLE PRECISION NOT NULL,
    agent_reports JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_council_results_pid ON council_results(parcel_id);

-- 12. VERIFICATION QUEUE (Field and desktop survey task prioritization)
CREATE TABLE IF NOT EXISTS verification_queue (
    id VARCHAR(64) PRIMARY KEY,
    parcel_id VARCHAR(64) REFERENCES parcels(id) ON DELETE CASCADE,
    priority VARCHAR(16) NOT NULL, -- HIGH, MEDIUM, LOW
    priority_score DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) DEFAULT 'QUEUED', -- QUEUED, IN_PROGRESS, RESOLVED
    assigned_surveyor VARCHAR(128),
    reasons JSONB NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_verification_queue_status ON verification_queue(status, priority);

-- 13. VERIFICATION ACTIONS (Surveyor inspections, edits, splits, merges)
CREATE TABLE IF NOT EXISTS verification_actions (
    id VARCHAR(64) PRIMARY KEY,
    parcel_id VARCHAR(64) REFERENCES parcels(id) ON DELETE CASCADE,
    surveyor_name VARCHAR(128) NOT NULL,
    action_type VARCHAR(64) NOT NULL, -- ACCEPT, REJECT, EDIT, SPLIT, MERGE
    before_geom GEOMETRY(Polygon, 32643),
    after_geom GEOMETRY(Polygon, 32643),
    reason TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 14. AUDIT LOG (Immutable audit log for governance and compliance)
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    performed_by VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(64),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
