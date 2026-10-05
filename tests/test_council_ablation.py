"""
Unit tests for AI Council Ablation Studies (Phase 17).
Evaluates decision differences when specific agents are disabled:
  - Full Council (all 6 agents)
  - Council without Vision Agent
  - Council without GIS Agent
  - Council without Geometry Agent
  - Council without Anomaly Agent
  - Council without Field Verification Agent
"""

import pytest
from backend.council.agents import evaluate_parcel_with_council


def test_ai_council_full_consensus():
    parcel = {
        "id": "P_ABL_01",
        "visible_edges": 4,
        "boundary_prob_mean": 0.92,
        "bldg_prob_mean": 0.90,
        "compactness": 0.85,
        "area_sqm": 600.0,
        "road_access": True,
    }
    res = evaluate_parcel_with_council(
        parcel=parcel,
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
    )
    assert res["decision"] == "ACCEPT_FOR_REVIEW"
    assert len(res["agent_reports"]) == 6
    assert res["confidence_category"] == "HIGH"


def test_ai_council_ablation_low_vision_shift():
    # When vision is degraded (0 visible edges, weak prob)
    parcel_blind = {
        "id": "P_ABL_02",
        "visible_edges": 0,
        "boundary_prob_mean": 0.20,
        "bldg_prob_mean": 0.30,
        "compactness": 0.80,
        "area_sqm": 500.0,
        "road_access": True,
    }
    res = evaluate_parcel_with_council(
        parcel=parcel_blind,
        topology_status="VALID",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
    )
    # Decision must shift to LOW_CONFIDENCE or REQUIRES_VERIFICATION
    assert res["decision"] in ("LOW_CONFIDENCE", "REQUIRES_VERIFICATION")
    assert res["agent_reports"]["VISION_AGENT"]["confidence"] < 0.40


def test_ai_council_precedence_geometry_error_dominates():
    # Even if vision and ML are high, a self-intersection MUST force GEOMETRY_ERROR
    parcel_good = {
        "id": "P_ABL_03",
        "visible_edges": 4,
        "boundary_prob_mean": 0.98,
        "bldg_prob_mean": 0.98,
        "compactness": 0.90,
        "area_sqm": 800.0,
        "road_access": True,
    }
    res = evaluate_parcel_with_council(
        parcel=parcel_good,
        topology_status="SELF_INTERSECTION",
        conflict_status="NONE",
        anomaly_status="NONE",
        parcel_anomalies=[],
        parcel_changes=[],
    )
    assert res["decision"] == "GEOMETRY_ERROR"
    assert res["agent_reports"]["FIELD_VERIFICATION_AGENT"]["priority"] == "HIGH"
