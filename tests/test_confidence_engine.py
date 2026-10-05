"""
Automated unit tests for Deterministic Confidence Engine.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from experiments.confidence.confidence_engine import ConfidenceEngine


def test_confidence_weights_normalization():
    engine = ConfidenceEngine()
    total_w = sum(engine.weights.values())
    assert total_w == pytest.approx(1.0, rel=1e-5)


def test_high_quality_parcel_confidence():
    engine = ConfidenceEngine()
    res = engine.evaluate_confidence(
        target_id="P_EXCELLENT",
        model_confidence=0.95,
        model_disagreement=0.02,
        compactness=0.85,
        is_geom_valid=True,
        is_sliver=False,
        evidence_completeness=0.90,
        gis_iou=0.92,
    )
    assert res["confidence_score"] >= 0.80
    assert res["uncertainty"] <= 0.25
    assert res["confidence_band"] == "HIGH"
    assert "CONF_HIGH_CONSENSUS" in res["reason_codes"]


def test_invalid_geometry_triggers_reject():
    engine = ConfidenceEngine()
    res = engine.evaluate_confidence(
        target_id="P_BROKEN",
        model_confidence=0.95,
        is_geom_valid=False,
    )
    assert res["confidence_band"] == "REJECT"
    assert "CONF_INVALID_GEOMETRY" in res["reason_codes"]


def test_sliver_penalty_and_reasons():
    engine = ConfidenceEngine()
    res = engine.evaluate_confidence(
        target_id="P_SLIVER",
        model_confidence=0.75,
        compactness=0.10,
        is_sliver=True,
        gis_iou=0.70,
    )
    assert res["confidence_band"] in ("LOW", "REJECT")
    assert "CONF_SLIVER_SHAPE" in res["reason_codes"]


def test_incomplete_evidence_elevates_uncertainty():
    engine = ConfidenceEngine()
    res = engine.evaluate_confidence(
        target_id="P_SPARSE",
        model_confidence=0.85,
        evidence_completeness=0.25,
    )
    assert "CONF_DATA_INCOMPLETE" in res["reason_codes"]
    assert res["uncertainty"] > 0.35
