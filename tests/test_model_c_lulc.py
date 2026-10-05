"""
Unit and Integration Tests for Model C Supplementary Land-Use Classification Experiment
Validates dataset loading, CRS, class schema, non-overlap with Pune, deterministic feature
extraction, baseline model loading, output schema, class probability validity, and data immutability.
"""

import os
import sys
import json
import pytest
import fiona
from shapely.geometry import Polygon, box
import numpy as np
import joblib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_c_lulc.feature_extractor import LULCMorphologicalFeatureExtractor
from experiments.model_c_lulc.spatial_audit import perform_spatial_audit
EXP_DIR = os.path.join(PROJECT_ROOT, "experiments", "model_c_lulc")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "real", "worldbank", "mumbai_lulc")
SHP_2005 = os.path.join(DATA_DIR, "processed", "2005", "EO4SD_MUMBAI_LULCVHR_2005.shp")
SHP_2015 = os.path.join(DATA_DIR, "processed", "2015", "EO4SD_MUMBAI_LULCVHR_2015.shp")
CHECKPOINT_PATH = os.path.join(EXP_DIR, "checkpoints", "model_c_rf_baseline.joblib")
METRICS_PATH = os.path.join(EXP_DIR, "evaluation_metrics.json")
REGISTRY_PATH = os.path.join(EXP_DIR, "model_registry.json")
CLASS_SCHEMA_PATH = os.path.join(EXP_DIR, "class_schema.json")
SPATIAL_AUDIT_PATH = os.path.join(EXP_DIR, "spatial_audit.json")
PUNE_CONTRACT_PATH = os.path.join(EXP_DIR, "PUNE_INFERENCE_CONTRACT.md")
DATA_USAGE_PATH = os.path.join(EXP_DIR, "DATA_USAGE.md")


def test_documentation_and_contracts_exist():
    """Verify all Model C contract, specification, and governance files exist."""
    assert os.path.exists(os.path.join(EXP_DIR, "MODEL_C_SPECIFICATION.md"))
    assert os.path.exists(DATA_USAGE_PATH)
    assert os.path.exists(CLASS_SCHEMA_PATH)
    assert os.path.exists(PUNE_CONTRACT_PATH)
    assert os.path.exists(REGISTRY_PATH)


def test_dataset_loading_and_feature_counts():
    """Verify that both 2005 and 2015 shapefiles load cleanly and have 9,610 features each."""
    assert os.path.exists(SHP_2005), f"Missing 2005 shapefile at {SHP_2005}"
    assert os.path.exists(SHP_2015), f"Missing 2015 shapefile at {SHP_2015}"

    with fiona.open(SHP_2005) as src_2005:
        assert len(src_2005) == 9610, f"Expected 9610 features, got {len(src_2005)}"
        assert src_2005.driver == "ESRI Shapefile"

    with fiona.open(SHP_2015) as src_2015:
        assert len(src_2015) == 9610, f"Expected 9610 features, got {len(src_2015)}"
        assert src_2015.driver == "ESRI Shapefile"


def test_dataset_crs():
    """Verify that the dataset CRS is EPSG:32643."""
    with fiona.open(SHP_2005) as src:
        crs_str = str(src.crs)
        assert "32643" in crs_str or "WGS 84 / UTM zone 43N" in crs_str, f"Unexpected CRS: {crs_str}"


def test_class_schema_and_integrity():
    """Verify class schema definitions and mapping integrity."""
    with open(CLASS_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    l1_classes = schema["classes_level_1"]
    assert len(l1_classes) == 5
    l1_names = [c["source_name"] for c in l1_classes]
    expected_l1 = [
        "Artificial Surfaces",
        "Agricultural Area",
        "Natural and Semi-natural Areas",
        "Wetlands",
        "Water",
    ]
    for exp in expected_l1:
        assert exp in l1_names, f"Missing class {exp} in schema"

    # Verify that source shapefile contains only these 5 L1 classes
    with fiona.open(SHP_2005) as src:
        found_l1 = set(f["properties"]["N_L1"] for f in src)
        assert found_l1 == set(expected_l1), f"Unexpected classes in data: {found_l1}"


def test_spatial_separation_no_pune_mumbai_confusion():
    """Verify that Mumbai and Pune are strictly spatially disjoint and non-overlapping."""
    audit = perform_spatial_audit()
    assert audit["spatial_relationship"]["pune_overlap"] is False
    assert audit["spatial_relationship"]["overlap_percentage"] == 0.0
    assert audit["spatial_relationship"]["minimum_distance_km"] > 80.0
    assert audit["governance_flags"]["PUNE_OVERLAP"] is False
    assert audit["governance_flags"]["GROUND_TRUTH_FOR_PUNE"] is False
    assert audit["governance_flags"]["DATA_ROLE"] == "SUPPLEMENTARY_ONLY"


def test_data_usage_governance_flags():
    """Verify DATA_USAGE.md has mandatory governance declarations."""
    with open(DATA_USAGE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "DATA_ROLE: SUPPLEMENTARY_ONLY" in content
    assert "GROUND_TRUTH_FOR_PUNE: FALSE" in content
    assert "PUNE_OVERLAP: FALSE" in content
    assert "GEOGRAPHIC_REGION: MUMBAI" in content
    assert "TARGET_REGION: PUNE" in content


def test_deterministic_feature_extraction():
    """Verify that morphological feature extraction is deterministic and produces expected metrics."""
    extractor = LULCMorphologicalFeatureExtractor()
    poly = Polygon([(0, 0), (100, 0), (100, 50), (0, 50), (0, 0)])

    f1 = extractor.extract_features_single(poly)
    f2 = extractor.extract_features_single(poly)

    assert f1 == f2, "Feature extraction must be strictly deterministic"
    assert "log_area" in f1
    assert "compactness" in f1
    assert "solidity" in f1
    assert f1["solidity"] == pytest.approx(1.0, rel=1e-3)
    assert f1["vertex_count"] == 5.0

    batch = extractor.extract_features_batch([poly, poly])
    assert batch.shape == (2, len(extractor.feature_names))
    assert np.allclose(batch[0], batch[1])


def test_baseline_model_loading_and_inference():
    """Verify that the serialized baseline model loads and generates valid predictions and probabilities."""
    assert os.path.exists(CHECKPOINT_PATH), f"Missing model checkpoint: {CHECKPOINT_PATH}"
    model = joblib.load(CHECKPOINT_PATH)

    extractor = LULCMorphologicalFeatureExtractor()
    test_poly = Polygon([(10, 10), (50, 10), (50, 40), (10, 40), (10, 10)])
    feats = extractor.extract_features_batch([test_poly])

    pred = model.predict(feats)
    assert len(pred) == 1
    assert isinstance(pred[0], str)

    proba = model.predict_proba(feats)
    assert proba.shape == (1, 5)
    # Probabilities must be in [0, 1] and sum to 1.0
    assert np.all(proba >= 0.0)
    assert np.all(proba <= 1.0)
    assert np.sum(proba) == pytest.approx(1.0, rel=1e-5)


def test_model_registry_integrity():
    """Verify model registry contains valid metadata, metrics, and supplementary status."""
    assert os.path.exists(REGISTRY_PATH), f"Missing model registry at {REGISTRY_PATH}"
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reg = json.load(f)

    assert reg["status"] == "SUPPLEMENTARY_EXPERIMENT"
    assert reg["ground_truth_for_pune"] is False
    assert reg["pune_overlap"] is False
    assert len(reg["downstream_dependencies_unblocked"]) == 0
    assert "MODEL_C_LULC" in reg["model_id"]
    assert reg["test_accuracy"] > 0.40
    assert reg["test_macro_f1"] > 0.25


def test_source_data_immutability():
    """Verify that source shapefile files are unmodified and intact."""
    assert os.path.exists(SHP_2005)
    assert os.path.exists(SHP_2015)
    size_2005 = os.path.getsize(SHP_2005)
    size_2015 = os.path.getsize(SHP_2015)
    assert size_2005 == 5176776, f"Expected size 5176776, got {size_2005}"
    assert size_2015 == 5176776, f"Expected size 5176776, got {size_2015}"
