"""
Phase 16: Synthetic End-to-End Pipeline Integration Test.
Connects all 10 AeroCadastre modules on controlled synthetic fixtures:
  1. Synthetic Evidence Ingestion
  2. Boundary Evidence Engine
  3. Multi-Source Fusion Engine (Model E)
  4. Parcel Boundary Inference Engine (Model F)
  5. Topology Validation Engine (Model G)
  6. GIS Conflict & Anomaly Engine (Model H)
  7. Deterministic Confidence Scoring Engine
  8. AI Council Evaluation Engine (6 agents + precedence fusion)
  9. Field Verification Queue Prioritizer
  10. GIS Exporter with ULPIN Pre-Cadastre Compliance
"""

import json
import os
import sys
from pathlib import Path
import pytest
from shapely.geometry import LineString, Polygon, shape, mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.model_boundary.boundary_evidence import BoundaryEvidenceEngine
from experiments.model_e_fusion.fusion_engine import MultiSourceFusionEngine
from experiments.model_f_parcel_inference.parcel_inference import ParcelInferenceEngine
from experiments.model_g_topology.topology_validator import TopologyValidator
from experiments.model_h_anomaly.anomaly_detector import AnomalyDetector
from experiments.confidence.confidence_engine import ConfidenceEngine
from backend.council.agents import evaluate_parcel_with_council
from backend.gis.exporter import export_and_validate_parcels


FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "synthetic_cadastral"


@pytest.fixture(scope="module")
def synthetic_fixtures():
    """Load controlled synthetic fixtures from disk."""
    bldg_path = FIXTURES_DIR / "synthetic_buildings.geojson"
    road_path = FIXTURES_DIR / "synthetic_roads.geojson"
    terr_path = FIXTURES_DIR / "synthetic_terrain_context.json"

    assert bldg_path.exists(), f"Missing fixture: {bldg_path}"
    assert road_path.exists(), f"Missing fixture: {road_path}"
    assert terr_path.exists(), f"Missing fixture: {terr_path}"

    with open(bldg_path, "r", encoding="utf-8") as f:
        bldgs = json.load(f)
    with open(road_path, "r", encoding="utf-8") as f:
        roads = json.load(f)
    with open(terr_path, "r", encoding="utf-8") as f:
        terrain = json.load(f)

    # Verify synthetic provenance tags
    assert bldgs.get("metadata", {}).get("DATA_MODE") == "SYNTHETIC"
    assert bldgs.get("metadata", {}).get("SYNTHETIC_ONLY") is True
    assert roads.get("metadata", {}).get("DATA_MODE") == "SYNTHETIC"
    assert roads.get("metadata", {}).get("SYNTHETIC_ONLY") is True
    assert terrain.get("DATA_MODE") == "SYNTHETIC"
    assert terrain.get("SYNTHETIC_ONLY") is True

    return {"buildings": bldgs, "roads": roads, "terrain": terrain}


def test_synthetic_cadastral_fixtures_loaded(synthetic_fixtures):
    """Verify fixture geometry structures and CRS metadata."""
    bldgs = synthetic_fixtures["buildings"]
    roads = synthetic_fixtures["roads"]
    terrain = synthetic_fixtures["terrain"]

    assert len(bldgs["features"]) == 4
    assert len(roads["features"]) == 2
    assert terrain["crs"] == "EPSG:32643"
    assert terrain["terrain_attributes"]["slope_mean_deg"] > 0


def test_synthetic_end_to_end_pipeline(synthetic_fixtures, tmp_path):
    """Execute complete 10-stage automated pipeline chain on synthetic data."""
    bldgs = synthetic_fixtures["buildings"]["features"]
    roads = synthetic_fixtures["roads"]["features"]
    terrain = synthetic_fixtures["terrain"]

    # ------------------------------------------------------------------
    # Step 1: Synthesize Candidate Boundary Network Lines
    # Bounding perimeter [375000, 2045000, 375250, 2045250] + dividing road lines
    # ------------------------------------------------------------------
    candidate_lines = [
        LineString([(375000.0, 2045000.0), (375250.0, 2045000.0)]),
        LineString([(375250.0, 2045000.0), (375250.0, 2045250.0)]),
        LineString([(375250.0, 2045250.0), (375000.0, 2045250.0)]),
        LineString([(375000.0, 2045250.0), (375000.0, 2045000.0)]),
        # Road corridors bisecting into 4 quadrants
        LineString([(375000.0, 2045110.0), (375250.0, 2045110.0)]),
        LineString([(375100.0, 2045000.0), (375100.0, 2045250.0)]),
    ]

    # ------------------------------------------------------------------
    # Step 2: Boundary Evidence Extraction
    # ------------------------------------------------------------------
    bnd_engine = BoundaryEvidenceEngine(crs="EPSG:32643")
    inferred_boundaries = bnd_engine.generate_candidate_boundaries(buildings=bldgs, roads=roads)
    assert len(inferred_boundaries) > 0
    for bnd in inferred_boundaries:
        assert bnd["label"] == "INFERRED_BOUNDARY_EVIDENCE"
        assert "boundary_score" in bnd
        assert "features" in bnd

    # ------------------------------------------------------------------
    # Step 3: Multi-Source Evidence Fusion (Model E)
    # ------------------------------------------------------------------
    fusion_engine = MultiSourceFusionEngine()
    fused_edges = []
    for idx, bnd in enumerate(inferred_boundaries, start=1):
        domain_ev = {
            "BUILDING": {"status": "AVAILABLE", "confidence": 0.85, "features": {"dist_to_bldg_m": 12.0}},
            "ROAD": {"status": "AVAILABLE", "confidence": 0.90, "features": {"is_road_adjacent": True}},
            "BOUNDARY": {"status": "AVAILABLE", "confidence": bnd["boundary_score"]},
            "TERRAIN": {
                "status": "AVAILABLE",
                "confidence": 0.82,
                "features": {"slope_deg": terrain["terrain_attributes"]["slope_mean_deg"]},
            },
            "GIS_REFERENCE": {"status": "UNAVAILABLE"},
            "LULC": {"status": "UNAVAILABLE"},
        }
        res = fusion_engine.fuse_evidence(bnd["edge_id"], domain_ev, crs="EPSG:32643")
        fused_edges.append(res)
        assert res["fused_confidence"] > 0.50
        assert res["evidence_completeness"] == 0.75

    # ------------------------------------------------------------------
    # Step 4: Parcel Boundary Inference & Polygonization (Model F)
    # ------------------------------------------------------------------
    parcel_engine = ParcelInferenceEngine(crs="EPSG:32643")
    candidate_parcels = parcel_engine.generate_candidate_parcels(
        candidate_lines=candidate_lines,
        buildings=bldgs,
        roads=roads,
        min_area_m2=500.0,
    )

    assert len(candidate_parcels) == 4, f"Expected 4 quadrant parcels, got {len(candidate_parcels)}"
    for p in candidate_parcels:
        assert p["label"] == "CANDIDATE_PARCEL"
        assert p["boundary_type"] == "INFERRED_PARCEL_BOUNDARY"
        assert p["provenance"]["ulpin_status"] == "NOT_ASSIGNED_PRE_CADASTRE"
        assert "Does NOT confer legal ownership" in p["provenance"]["disclaimer"]
        assert p["properties"]["area_sqm"] > 500.0

    # ------------------------------------------------------------------
    # Step 5: Topology Validation Engine (Model G)
    # ------------------------------------------------------------------
    topo_validator = TopologyValidator()
    topo_report = topo_validator.validate_features(candidate_parcels, layer_name="candidate_parcels")
    assert topo_report["total_features"] == 4
    assert "issues" in topo_report

    # Detect gaps and test repair features
    gaps = topo_validator.detect_parcel_gaps(candidate_parcels, min_gap_area_m2=10.0)
    assert isinstance(gaps, list)

    repaired_parcels, repair_stats = topo_validator.repair_features(candidate_parcels)
    assert len(repaired_parcels) == len(candidate_parcels)
    assert isinstance(repair_stats, dict)

    # ------------------------------------------------------------------
    # Step 6: Anomaly & Conflict Detection (Model H)
    # ------------------------------------------------------------------
    anomaly_detector = AnomalyDetector()
    reference_fixtures = [
        {"id": f"REF_{p['id']}", "geometry": p["geometry"], "properties": {"land_use": "residential"}}
        for p in candidate_parcels
    ]
    comparison = anomaly_detector.compare_parcels_with_reference(
        candidate_parcels=candidate_parcels,
        reference_parcels=reference_fixtures,
        candidate_crs="EPSG:32643",
        reference_crs="EPSG:32643",
    )
    assert comparison["total_candidates"] == 4
    assert comparison["total_references"] == 4
    assert "conflicts" in comparison
    assert "disclaimer" in comparison["provenance"]

    # ------------------------------------------------------------------
    # Step 7: Deterministic Confidence Scoring
    # ------------------------------------------------------------------
    conf_engine = ConfidenceEngine()
    scored_parcels = []
    for p in candidate_parcels:
        c_res = conf_engine.evaluate_confidence(
            target_id=p["id"],
            model_confidence=p["properties"]["fused_confidence"],
            model_disagreement=p["properties"]["fused_uncertainty"],
            compactness=p["properties"]["compactness"],
            is_geom_valid=True,
            is_sliver=False,
            evidence_completeness=p["properties"]["evidence_completeness"],
            gis_iou=1.0,
            reference_reliability=0.90,
        )
        assert c_res["confidence_score"] >= 0.65
        assert c_res["confidence_band"] in ("HIGH", "MEDIUM")
        assert "components" in c_res
        p_dict = dict(p)
        p_dict["confidence"] = c_res["confidence_score"]
        p_dict["confidence_category"] = c_res["confidence_band"]
        p_dict["confidence_breakdown"] = c_res["components"]
        scored_parcels.append(p_dict)

    # ------------------------------------------------------------------
    # Step 8: AI Council Evaluation (6 Agents + Precedence Fusion)
    # ------------------------------------------------------------------
    council_results = []
    for sp in scored_parcels:
        council_res = evaluate_parcel_with_council(
            parcel={
                "id": sp["id"],
                "visible_edges": 4,
                "boundary_prob_mean": 0.88,
                "bldg_prob_mean": 0.86,
                "compactness": sp["properties"]["compactness"],
                "area_sqm": sp["properties"]["area_sqm"],
                "road_access": sp["properties"]["has_road_access"],
            },
            topology_status="VALID",
            conflict_status="NONE",
            anomaly_status="NONE",
            parcel_anomalies=[],
            parcel_changes=[],
            gis_iou=1.0,
        )
        assert council_res["council_version"] == "2.0.0"
        assert len(council_res["agent_reports"]) == 6
        assert council_res["decision"] in ("ACCEPT_FOR_REVIEW", "REQUIRES_VERIFICATION")
        council_results.append(council_res)

    # ------------------------------------------------------------------
    # Step 9: Field Verification Queue Prioritization
    # ------------------------------------------------------------------
    for cres in council_results:
        f_rep = cres["agent_reports"]["FIELD_VERIFICATION_AGENT"]
        assert f_rep["priority"] in ("HIGH", "MEDIUM", "LOW")
        assert "priority_score" in f_rep
        assert len(f_rep["reasons"]) >= 1

    # ------------------------------------------------------------------
    # Step 10: GIS Exporter with ULPIN Pre-Cadastre Compliance
    # ------------------------------------------------------------------
    export_parcels_input = []
    for sp, cres in zip(scored_parcels, council_results):
        export_parcels_input.append({
            "id": sp["id"],
            "parcel_layer": "CANDIDATE",
            "boundary_representation": "INFERRED",
            "land_use_class": "residential",
            "area_sqm": sp["properties"]["area_sqm"],
            "perimeter_m": sp["properties"]["perimeter_m"],
            "confidence": cres["confidence"],
            "confidence_category": cres["confidence_category"],
            "topology_status": "VALID",
            "conflict_status": "NONE",
            "anomaly_status": "NONE",
            "verification_status": cres["recommended_action"],
            "council_decision": cres["decision"],
            "version": 1,
            "crs": "EPSG:32643",
            "provenance": {
                "DATA_MODE": "SYNTHETIC",
                "SYNTHETIC_ONLY": True,
                "engine": "MODEL_F_PARCEL_INFERENCE_ENGINE",
                "disclaimer": "SYNTHETIC CANDIDATE PARCEL. NOT STATUTORY BOUNDARY.",
            },
            "evidence_sources": ["SYNTHETIC_BUILDING", "SYNTHETIC_ROAD", "SYNTHETIC_TERRAIN"],
            "geometry": sp["geometry"],
        })

    export_summary = export_and_validate_parcels(
        project_id="PROJ_SYNTHETIC_E2E",
        scene_id="SCENE_E2E_01",
        export_format="GeoJSON",
        parcels=export_parcels_input,
    )

    assert export_summary["validation_passed"] is True
    assert export_summary["feature_count"] == 4
    exported_file = Path(export_summary["file_path"])
    assert exported_file.exists()

    # Re-read exported GeoJSON and check mandatory attributes
    with open(exported_file, "r", encoding="utf-8") as f:
        exported_geojson = json.load(f)

    for feat in exported_geojson["features"]:
        props = feat["properties"]
        assert props["ulpin_status"] == "NOT_ASSIGNED_PRE_CADASTRE"
        assert props["ulpin_readiness"] == "METADATA_COMPLIANT_AWAITING_STATE_SURVEY_AUTHORITY"
        assert "official_ulpin" not in props or props.get("official_ulpin") is None
        assert props["provenance"]["DATA_MODE"] == "SYNTHETIC"
        assert props["provenance"]["SYNTHETIC_ONLY"] is True
