"""
Unit Test Suite for Data Validation Service.
Tests CRS validation, bounds checking, resolution constraints, geometry OGC validity,
and provenance audit compliance.
"""

import pytest
from backend.app.services.data_validation_service import DataValidationService


@pytest.fixture
def validator():
    return DataValidationService()


def test_validate_crs_authorized_and_unauthorized(validator):
    valid_res = validator.validate_crs("EPSG:32643")
    assert valid_res["valid"] is True
    assert valid_res["is_target_metric"] is True
    assert valid_res["warning"] is None

    wgs84_res = validator.validate_crs("EPSG:4326")
    assert wgs84_res["valid"] is True
    assert wgs84_res["is_target_metric"] is False
    assert "reprojection" in wgs84_res["warning"]

    invalid_res = validator.validate_crs("EPSG:999999")
    assert invalid_res["valid"] is False
    assert "Unauthorized CRS" in invalid_res["error"]


def test_validate_bounds_geometry_and_overlap(validator):
    # Valid Pune metric bbox
    pune_box = (378000.0, 2047500.0, 379000.0, 2048500.0)
    res = validator.validate_bounds(pune_box, crs="EPSG:32643")
    assert res["valid"] is True
    assert res["overlaps_study_area"] is True

    # Inverted min/max coordinates
    bad_box = (379000.0, 2048500.0, 378000.0, 2047500.0)
    res_bad = validator.validate_bounds(bad_box)
    assert res_bad["valid"] is False
    assert "min exceeds max" in res_bad["error"]

    # Disjoint bounding box
    disjoint_box = (500000.0, 3000000.0, 501000.0, 3001000.0)
    res_disjoint = validator.validate_bounds(disjoint_box, crs="EPSG:32643")
    assert res_disjoint["valid"] is True
    assert res_disjoint["overlaps_study_area"] is False


def test_validate_resolution_optical_threshold(validator):
    # Sub-meter drone/satellite imagery (GSD 0.2m)
    vhr_res = validator.validate_resolution((0.2, 0.2), modality="OPTICAL_VHR")
    assert vhr_res["valid"] is True
    assert vhr_res["cadastral_usable"] is True

    # Coarse Sentinel-2 imagery (10m) rejected for VHR boundary extraction
    coarse_res = validator.validate_resolution((10.0, 10.0), modality="OPTICAL_VHR")
    assert coarse_res["valid"] is False
    assert coarse_res["cadastral_usable"] is False
    assert "exceeds 1.0 m threshold" in coarse_res["error"]


def test_validate_geometry_ogc_conformance(validator):
    # Valid polygon
    valid_poly = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
    }
    res = validator.validate_geometry(valid_poly)
    assert res["valid"] is True
    assert res["area"] == 100.0

    # Self-intersecting bowtie polygon
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 10], [10, 0], [0, 10], [0, 0]]]
    }
    res_bowtie = validator.validate_geometry(bowtie)
    assert res_bowtie["valid"] is False
    assert "Invalid polygon topology" in res_bowtie["error"]


def test_validate_provenance_and_statutory_claims(validator):
    # Legal / synthetic contradiction
    bad_prov = {
        "data_mode": "SYNTHETIC",
        "disclaimer": "Test disclaimer",
        "statutory_cadastre": True
    }
    res = validator.validate_provenance(bad_prov)
    assert res["valid"] is False
    assert "CANNOT be labeled as statutory cadastre" in res["error"]
