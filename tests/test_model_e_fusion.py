"""
Automated unit tests for Model E Multi-Source Fusion Engine.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.model_e_fusion.fusion_engine import MultiSourceFusionEngine
from experiments.model_e_fusion.evaluator import evaluate_fused_batch


def test_fusion_engine_weight_normalization():
    engine = MultiSourceFusionEngine()
    total_w = sum(engine.weights.values())
    assert total_w == pytest.approx(1.0, rel=1e-5)
    assert "BUILDING" in engine.weights
    assert "ROAD" in engine.weights
    assert "TERRAIN" in engine.weights


def test_fusion_complete_evidence():
    engine = MultiSourceFusionEngine()
    evidence = {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.90},
        "ROAD": {"status": "AVAILABLE", "confidence": 0.80},
        "BOUNDARY": {"status": "AVAILABLE", "confidence": 0.85},
        "TERRAIN": {"status": "AVAILABLE", "confidence": 0.95},
        "GIS_REFERENCE": {"status": "AVAILABLE", "confidence": 0.70},
        "LULC": {"status": "AVAILABLE", "confidence": 0.75},
    }
    res = engine.fuse_evidence("TEST_PARCEL_1", evidence)

    assert res["evidence_completeness"] == pytest.approx(1.0, rel=1e-4)
    assert 0.80 <= res["fused_confidence"] <= 0.90
    assert len(res["missing_domains"]) == 0
    assert "input_hash" in res["provenance"]


def test_missing_evidence_is_not_negative():
    engine = MultiSourceFusionEngine()
    # Provide only building evidence (0.25 weight)
    evidence_partial = {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.90},
        "ROAD": {"status": "UNAVAILABLE"},
        "BOUNDARY": {"status": "UNAVAILABLE"},
        "TERRAIN": {"status": "UNAVAILABLE"},
        "GIS_REFERENCE": {"status": "UNAVAILABLE"},
        "LULC": {"status": "UNAVAILABLE"},
    }
    res = engine.fuse_evidence("TEST_PARCEL_2", evidence_partial)

    # Confidence must reflect building score (0.90), NOT drop toward 0.22!
    assert res["fused_confidence"] == pytest.approx(0.90, rel=1e-3)
    assert res["evidence_completeness"] == pytest.approx(0.25, rel=1e-2)
    # But uncertainty must be higher due to missing domains
    assert res["fused_uncertainty"] > 0.30


def test_model_disagreement_calculation():
    engine = MultiSourceFusionEngine()
    evidence = {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.95},
        "ROAD": {"status": "AVAILABLE", "confidence": 0.50},
    }
    res = engine.fuse_evidence("TEST_PARCEL_3", evidence)
    assert res["model_disagreement"] > 0.15


def test_batch_evaluator():
    engine = MultiSourceFusionEngine()
    r1 = engine.fuse_evidence("P1", {"BUILDING": {"status": "AVAILABLE", "confidence": 0.80}})
    r2 = engine.fuse_evidence("P2", {"BUILDING": {"status": "AVAILABLE", "confidence": 0.90}})
    batch_summary = evaluate_fused_batch([r1, r2])

    assert batch_summary["total_records"] == 2
    assert batch_summary["mean_confidence"] == pytest.approx(0.85, rel=1e-2)


def test_fusion_eight_edge_cases():
    """Verify all 8 Phase 6 edge cases for the fusion engine."""
    engine = MultiSourceFusionEngine()

    # Case 1: All evidence available
    c1 = engine.fuse_evidence("P_ALL", {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.90},
        "ROAD": {"status": "AVAILABLE", "confidence": 0.85},
        "BOUNDARY": {"status": "AVAILABLE", "confidence": 0.80},
        "TERRAIN": {"status": "AVAILABLE", "confidence": 0.90},
        "GIS_REFERENCE": {"status": "AVAILABLE", "confidence": 0.75},
        "LULC": {"status": "AVAILABLE", "confidence": 0.70},
    })
    assert c1["evidence_completeness"] == pytest.approx(1.0, rel=1e-3)
    assert len(c1["available_domains"]) == 6

    # Case 2: Building missing
    c2 = engine.fuse_evidence("P_NO_BLDG", {
        "ROAD": {"status": "AVAILABLE", "confidence": 0.85},
        "BOUNDARY": {"status": "AVAILABLE", "confidence": 0.80},
    })
    assert "BUILDING" in c2["missing_domains"]
    assert c2["fused_confidence"] > 0.80

    # Case 3: Road missing
    c3 = engine.fuse_evidence("P_NO_ROAD", {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.90},
        "TERRAIN": {"status": "AVAILABLE", "confidence": 0.85},
    })
    assert "ROAD" in c3["missing_domains"]
    assert c3["fused_confidence"] > 0.85

    # Case 4: Terrain missing
    c4 = engine.fuse_evidence("P_NO_TERRAIN", {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.88},
        "ROAD": {"status": "AVAILABLE", "confidence": 0.82},
    })
    assert "TERRAIN" in c4["missing_domains"]

    # Case 5: GIS missing
    c5 = engine.fuse_evidence("P_NO_GIS", {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.85},
        "ROAD": {"status": "AVAILABLE", "confidence": 0.85},
    })
    assert "GIS_REFERENCE" in c5["missing_domains"]

    # Case 6: Conflicting evidence (e.g. 0.95 vs 0.15)
    c6 = engine.fuse_evidence("P_CONFLICT", {
        "BUILDING": {"status": "AVAILABLE", "confidence": 0.95},
        "ROAD": {"status": "AVAILABLE", "confidence": 0.15},
    })
    assert c6["model_disagreement"] > 0.30

    # Case 7: Invalid evidence (None confidence or malformed status)
    c7 = engine.fuse_evidence("P_INVALID", {
        "BUILDING": {"status": "AVAILABLE", "confidence": None},
        "ROAD": {"status": "CORRUPT_STATUS", "confidence": 0.85},
        "BOUNDARY": {"status": "AVAILABLE", "confidence": 0.80},
    })
    assert "BUILDING" in c7["missing_domains"]
    assert "BOUNDARY" in c7["available_domains"]
    assert c7["fused_confidence"] == pytest.approx(0.80, rel=1e-3)

    # Case 8: Zero usable evidence
    c8 = engine.fuse_evidence("P_ZERO", {})
    assert c8["evidence_completeness"] == 0.0
    assert c8["fused_uncertainty"] == 1.0
    assert len(c8["available_domains"]) == 0

