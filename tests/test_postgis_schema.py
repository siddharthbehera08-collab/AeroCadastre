"""
Automated unit tests validating the production PostGIS SQL schema definition.
"""

import os
import re
import pytest

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema_production.sql")


def test_schema_file_exists():
    assert os.path.exists(SCHEMA_PATH), f"Missing SQL schema file: {SCHEMA_PATH}"


def test_all_fourteen_tables_defined():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    expected_tables = [
        "parcels",
        "parcel_evidence",
        "model_predictions",
        "boundary_evidence",
        "terrain_features",
        "gis_references",
        "conflicts",
        "anomalies",
        "council_results",
        "verification_queue",
        "verification_actions",
        "audit_log",
        "model_registry",
        "experiment_registry",
    ]

    for table in expected_tables:
        pattern = rf"CREATE TABLE IF NOT EXISTS {table}\s*\("
        assert re.search(pattern, sql, re.IGNORECASE), f"Table '{table}' missing in schema_production.sql"


def test_spatial_geom_columns_and_srid():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    # Verify that standard metric CRS EPSG:32643 is used for geometries
    assert "GEOMETRY(Polygon, 32643)" in sql
    assert "GEOMETRY(LineString, 32643)" in sql
    assert "GEOMETRY(Geometry, 32643)" in sql

    # Verify spatial GIST indexing
    assert "USING GIST" in sql
    assert "idx_parcels_geom" in sql
    assert "idx_boundary_evidence_geom" in sql
    assert "idx_gis_references_geom" in sql


def test_provenance_and_security_columns():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    # Check provenance JSONB columns
    assert "provenance JSONB" in sql
    # Check audit log immutable structure
    assert "audit_log" in sql
    assert "payload_hash" in sql
    # Verify ULPIN disclaimer note
    assert "NEVER fake ULPIN" in sql
