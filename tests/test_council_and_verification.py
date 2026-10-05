"""
Automated unit tests for AI Council and Field Verification Priority Engine.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.council.agents import evaluate_parcel_with_council


def test_council_accept_for_review_on_high_quality_parcel():
    parcel = {
        "id": "PARCEL_PERFECT",
        "visible_edges": 4,
        "boundary_prob_mean": 0.95,
        "bldg_prob_mean": 0.92,
        "lu_prob_mean": 0.90,
        "model_disagreement": 0.02,
        "compactness": 0.85,
        "area_sqm": 500.0,
        "road_access": True,
    }
    res = evaluate_parcel_with_council(
        parcel=parcel,
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
        gis_iou=0.95,
    )
    assert res["decision"] == "ACCEPT_FOR_REVIEW"
    assert res["confidence_category"] == "HIGH"
    assert res["council_version"] == "2.0.0"
    assert "input_hash" in res
    assert "configuration_hash" in res
    assert res["field_need"] in ("LOW", "MEDIUM")


def test_council_geometry_error_precedence():
    parcel = {
        "id": "PARCEL_BROKEN_TOPOLOGY",
        "visible_edges": 4,
        "boundary_prob_mean": 0.95,
        "compactness": 0.80,
    }
    # Even with high vision score, SELF_INTERSECTION must trigger GEOMETRY_ERROR
    res = evaluate_parcel_with_council(
        parcel=parcel,
        topology_status="SELF_INTERSECTION",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
    )
    assert res["decision"] == "GEOMETRY_ERROR"
    assert res["field_need"] == "HIGH"
    assert res["agent_reports"]["GEOMETRY_AGENT"]["decision"] == "TOPOLOGY_ALERT"


def test_council_conflict_detected():
    parcel = {
        "id": "PARCEL_CONFLICT",
        "visible_edges": 3,
        "compactness": 0.70,
    }
    res = evaluate_parcel_with_council(
        parcel=parcel,
        topology_status="VALID",
        conflict_status="EXTRA_PARCEL",
        anomaly_status="NONE",
        parcel_anomalies=[{"explanation": "Extra parcel not in reference GIS"}],
        parcel_changes=[],
        gis_iou=0.40,
    )
    assert res["decision"] == "CONFLICT_DETECTED"
    assert res["field_need"] == "HIGH"
    assert res["agent_reports"]["GIS_AGENT"]["decision"] == "GIS_LAYER_CONFLICT"


def test_all_six_agents_report_provenance():
    parcel = {"id": "PARCEL_TEST"}
    res = evaluate_parcel_with_council(
        parcel=parcel,
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
    )
    agents = res["agent_reports"]
    assert len(agents) == 6
    for agent_name, rep in agents.items():
        assert "decision" in rep
        assert "evidence" in rep
        if "confidence" in rep:
            assert "uncertainty" in rep
        assert "provenance" in rep
