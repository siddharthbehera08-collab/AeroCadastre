"""
Unit tests for Cadastral Copilot Service and Human Feedback Export Service.
Verifies:
1. Copilot safely refuses ownership and legal title queries.
2. Copilot correctly handles ULPIN queries without fabricating statutory IDs.
3. Copilot provides grounded evidence breakdowns for candidate parcels.
4. Feedback export service properly writes active learning candidate GeoJSON and manifest files.
"""

import json
import pytest
from pathlib import Path
from backend.app.services.copilot_service import CadastralCopilotService
from backend.app.services.feedback_export_service import HumanFeedbackExportService


def test_copilot_refuses_ownership_query():
    copilot = CadastralCopilotService()
    res = copilot.answer_query("Who is the legal owner of parcel P-102?")
    assert "ownership" in res["response"].lower() or "owner" in res["response"].lower()
    assert "Mahabhulekh" in res["response"] or "Revenue Departments" in res["response"]
    assert "ADVISORY AI ASSISTANCE ONLY" in res["disclaimer"]


def test_copilot_ulpin_inquiry_handling():
    copilot = CadastralCopilotService()
    res = copilot.answer_query("What is the official ULPIN number?")
    assert "NOT_ASSIGNED_PRE_CADASTRE" in res["response"]
    assert "Bhu-Aadhaar" in res["response"] or "Survey of India" in res["response"]


def test_copilot_explain_flagged_parcel():
    copilot = CadastralCopilotService()
    parcel_data = {
        "parcel_id": "P-FLAGGED-01",
        "confidence": 0.42,
        "confidence_tier": "LOW",
        "evidence": {
            "optical_building": 0.2,
            "optical_road": 0.1,
            "osm_reference": 0.0,
            "terrain_slope": 22.5
        },
        "anomalies": [
            {"type": "BOUNDARY_OVERLAP", "description": "Overlaps adjacent parcel P-FLAGGED-02 by 12 m2"}
        ],
        "verification_status": "NEEDS_REVIEW"
    }

    explanation = copilot.explain_parcel(parcel_data)
    assert explanation["parcel_id"] == "P-FLAGGED-01"
    assert explanation["ulpin_status"] == "NOT_ASSIGNED_PRE_CADASTRE"
    assert explanation["recommended_action"] == "SCHEDULE_FIELD_VISIT"
    assert len(explanation["risk_factors"]) > 0
    assert "BOUNDARY_OVERLAP" in explanation["risk_factors"][0]


def test_copilot_explain_high_confidence_parcel():
    copilot = CadastralCopilotService()
    parcel_data = {
        "parcel_id": "P-HIGH-01",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
        "evidence": {
            "optical_building": 0.88,
            "optical_road": 0.92,
            "osm_reference": 0.85,
            "terrain_slope": 3.2
        },
        "anomalies": [],
        "verification_status": "ACCEPT_CANDIDATE"
    }

    explanation = copilot.explain_parcel(parcel_data)
    assert explanation["recommended_action"] == "READY_FOR_OFFICE_REVIEW"
    assert len(explanation["supporting_evidence"]) >= 3
    assert len(explanation["risk_factors"]) == 0


def test_feedback_export_service_workflow(tmp_path):
    export_svc = HumanFeedbackExportService(export_base_dir=str(tmp_path))

    sample_geom = {
        "type": "Polygon",
        "coordinates": [[[385000, 2045000], [385100, 2045000], [385100, 2045100], [385000, 2045100], [385000, 2045000]]]
    }

    event1 = export_svc.log_feedback_event(
        project_id="PROJ-TEST",
        parcel_id="P-01",
        action="APPROVED",
        surveyor_id="SURV-RAJESH",
        notes="Boundary confirmed against field demarcation peg",
        original_geometry=sample_geom,
        confidence_score=0.88
    )

    event2 = export_svc.log_feedback_event(
        project_id="PROJ-TEST",
        parcel_id="P-02",
        action="MODIFIED",
        surveyor_id="SURV-RAJESH",
        notes="Adjusted northern boundary to exclude irrigation ditch",
        original_geometry=sample_geom,
        edited_geometry=sample_geom,
        confidence_score=0.65
    )

    records = [event1, event2]
    result = export_svc.export_training_candidates(project_id="PROJ-TEST", feedback_records=records)

    assert result["status"] == "COMPLETED"
    assert Path(result["geojson_path"]).exists()
    assert Path(result["manifest_path"]).exists()

    with open(result["manifest_path"], "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    assert manifest_data["total_samples"] == 2
    assert manifest_data["approved_count"] == 1
    assert manifest_data["modified_count"] == 1
    assert manifest_data["governance_classification"] == "ACTIVE_LEARNING_PROSPECTIVE_CANDIDATE"
    assert manifest_data["authoritative_cadastre"] is False
