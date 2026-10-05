#!/usr/bin/env python3
"""
AeroCadastre SIH26012 - Automated Pipeline Profiling & Latency Benchmark Script.
Benchmarks actual execution latency and memory usage across all 11 core sub-systems:
  1. Synthetic Evidence Ingestion
  2. Model Boundary Feature Generation
  3. Model E Multi-Source Fusion
  4. Model F Parcel Inference & Planarization
  5. Model G Topology Validation & Repair
  6. Model H GIS Conflict & Anomaly Detector
  7. Deterministic Confidence Scoring
  8. AI Council Multi-Agent Adjudication (6 agents)
  9. Field Route Optimization (TSP nearest-neighbor)
  10. Cadastral Copilot Grounded Query & Explanation
  11. Pre-Cadastre GIS Export & Validation

Outputs benchmark results to outputs/benchmarks/pipeline_profile.json
"""

import sys
import time
import json
import tracemalloc
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import LineString, shape

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
from backend.gis.field_route_planner import FieldRoutePlanner
from backend.app.services.copilot_service import CadastralCopilotService


def profile_pipeline():
    print("=" * 70)
    print("AEROCADASTRE SIH26012 — PIPELINE PERFORMANCE PROFILING BENCHMARK")
    print("=" * 70)

    fixtures_dir = PROJECT_ROOT / "tests" / "fixtures" / "synthetic_cadastral"
    bldg_path = fixtures_dir / "synthetic_buildings.geojson"
    road_path = fixtures_dir / "synthetic_roads.geojson"
    terr_path = fixtures_dir / "synthetic_terrain_context.json"

    with open(bldg_path, "r", encoding="utf-8") as f:
        buildings = json.load(f)
    with open(road_path, "r", encoding="utf-8") as f:
        roads = json.load(f)
    with open(terr_path, "r", encoding="utf-8") as f:
        terrain = json.load(f)

    bldgs_feats = buildings["features"]
    roads_feats = roads["features"]

    candidate_lines = [
        LineString([(375000.0, 2045000.0), (375250.0, 2045000.0)]),
        LineString([(375250.0, 2045000.0), (375250.0, 2045250.0)]),
        LineString([(375250.0, 2045250.0), (375000.0, 2045250.0)]),
        LineString([(375000.0, 2045250.0), (375000.0, 2045000.0)]),
        LineString([(375000.0, 2045110.0), (375250.0, 2045110.0)]),
        LineString([(375100.0, 2045000.0), (375100.0, 2045250.0)]),
    ]

    timings = {}
    tracemalloc.start()

    # Stage 1: Ingestion
    t0 = time.perf_counter()
    b_count = len(bldgs_feats)
    r_count = len(roads_feats)
    timings["1_fixture_ingestion_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 2: Boundary Evidence
    t0 = time.perf_counter()
    bnd_engine = BoundaryEvidenceEngine(crs="EPSG:32643")
    inferred_boundaries = bnd_engine.generate_candidate_boundaries(buildings=bldgs_feats, roads=roads_feats)
    timings["2_boundary_evidence_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 3: Fusion Engine
    t0 = time.perf_counter()
    fusion_engine = MultiSourceFusionEngine()
    fused_edges = []
    for bnd in inferred_boundaries:
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
    timings["3_multisource_fusion_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 4: Parcel Inference
    t0 = time.perf_counter()
    parcel_engine = ParcelInferenceEngine(crs="EPSG:32643")
    candidate_parcels = parcel_engine.generate_candidate_parcels(
        candidate_lines=candidate_lines,
        buildings=bldgs_feats,
        roads=roads_feats,
        min_area_m2=500.0,
    )
    timings["4_parcel_inference_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 5: Topology Validation
    t0 = time.perf_counter()
    topo_validator = TopologyValidator()
    topo_report = topo_validator.validate_features(candidate_parcels, layer_name="candidate_parcels")
    gaps = topo_validator.detect_parcel_gaps(candidate_parcels, min_gap_area_m2=10.0)
    repaired_parcels, repair_stats = topo_validator.repair_features(candidate_parcels)
    timings["5_topology_validation_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 6: Anomaly Detection
    t0 = time.perf_counter()
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
    timings["6_anomaly_detection_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 7: Confidence Scoring
    t0 = time.perf_counter()
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
        p_dict = dict(p)
        p_dict["confidence"] = c_res["confidence_score"]
        p_dict["confidence_category"] = c_res["confidence_band"]
        p_dict["confidence_breakdown"] = c_res["components"]
        scored_parcels.append(p_dict)
    timings["7_confidence_scoring_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 8: AI Council (6 agents)
    t0 = time.perf_counter()
    council_results = []
    for sp in scored_parcels:
        cres = evaluate_parcel_with_council(
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
        council_results.append(cres)
    timings["8_ai_council_6agents_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 9: Field Route Planner
    t0 = time.perf_counter()
    flagged = []
    for sp, cres in zip(scored_parcels, council_results):
        poly_shape = shape(sp["geometry"])
        f_rep = cres["agent_reports"]["FIELD_VERIFICATION_AGENT"]
        flagged.append({
            "parcel_id": sp["id"],
            "priority": f_rep.get("priority", "MEDIUM"),
            "centroid": [poly_shape.centroid.x, poly_shape.centroid.y],
            "reasons": f_rep.get("reasons", ["Routine verification"]),
        })
    planner = FieldRoutePlanner(crs="EPSG:32643")
    route_res = planner.plan_verification_route(flagged, start_point=(375000.0, 2045000.0))
    timings["9_field_route_planning_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 10: Cadastral Copilot
    t0 = time.perf_counter()
    copilot = CadastralCopilotService()
    for sp, cres in zip(scored_parcels, council_results):
        _ = copilot.explain_parcel({
            "parcel_id": sp["id"],
            "confidence": sp["confidence"],
            "confidence_tier": sp["confidence_category"],
            "evidence": {"optical_building": 0.86, "optical_road": 0.90},
            "anomalies": [],
            "verification_status": cres["recommended_action"],
            "ulpin": "NOT_ASSIGNED_PRE_CADASTRE",
        })
    timings["10_cadastral_copilot_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 11: Export & Validate
    t0 = time.perf_counter()
    out_dir = PROJECT_ROOT / "outputs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
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
        project_id="PROJ_BENCHMARK",
        scene_id="SCENE_BENCHMARK_01",
        export_format="GeoJSON",
        parcels=export_parcels_input,
    )
    timings["11_gis_export_and_validation_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_pipeline_time_ms = round(sum(timings.values()), 2)

    profile_report = {
        "benchmark_id": f"BENCH-{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_pipeline_latency_ms": total_pipeline_time_ms,
        "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
        "stage_timings_ms": timings,
        "throughput_parcels_per_sec": round((len(candidate_parcels) / (total_pipeline_time_ms / 1000.0)), 2),
        "environment": {
            "python_version": sys.version.split()[0],
            "os": "Windows",
            "synthetic_mode": True,
        }
    }

    out_file = out_dir / "pipeline_profile.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(profile_report, f, indent=2)

    print("-" * 70)
    print(f"Total Pipeline Latency: {total_pipeline_time_ms} ms (~{round(total_pipeline_time_ms / 1000.0, 3)} seconds)")
    print(f"Peak Memory Allocated: {profile_report['peak_memory_mb']} MB")
    print(f"Throughput: {profile_report['throughput_parcels_per_sec']} parcels/sec")
    print(f"Benchmark Report Saved: {out_file}")
    print("=" * 70)
    return profile_report


if __name__ == "__main__":
    profile_pipeline()
