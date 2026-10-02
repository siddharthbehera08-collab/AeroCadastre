from typing import Dict, Any, List


def evaluate_parcel_with_council(
    parcel: Dict[str, Any],
    topology_status: str,
    conflict_status: str,
    anomaly_status: str,
    parcel_anomalies: List[Dict[str, Any]],
    parcel_changes: List[Dict[str, Any]],
    gis_iou: float = 0.90,
) -> Dict[str, Any]:
    """
    Run the 6-agent AI Council on a single candidate parcel:
      1. VISION_AGENT
      2. GEOMETRY_AGENT
      3. GIS_AGENT
      4. ML_AGENT
      5. ANOMALY_AGENT
      6. FIELD_VERIFICATION_AGENT
    Plus the COUNCIL_FUSION_ENGINE producing transparent confidence & advisory decision.
    """
    pid = parcel["id"]
    vis_edges = int(parcel.get("visible_edges", 3))
    bnd_conf = float(parcel.get("boundary_prob_mean", 0.84))
    bldg_conf = float(parcel.get("bldg_prob_mean", 0.88))
    lu_conf = float(parcel.get("lu_prob_mean", 0.86))
    model_dis = float(parcel.get("model_disagreement", 0.03))
    compactness = float(parcel.get("compactness", 0.74))
    area_sqm = float(parcel.get("area_sqm", 450.0))
    road_access = bool(parcel.get("road_access", True))

    # 1. VISION AGENT
    vis_ratio = min(1.0, vis_edges / 4.0)
    vision_score = round(0.45 * vis_ratio + 0.30 * bnd_conf + 0.25 * bldg_conf, 3)
    vision_warnings = []
    if vis_edges < 3:
        vision_warnings.append(f"Only {vis_edges}/4 parcel edges are directly visible in drone RGB; remaining edges are inferred.")
    if bnd_conf < 0.72:
        vision_warnings.append("Weak boundary contrast due to canopy occlusion or worn wall markings.")
    vision_report = {
        "agent": "VISION_AGENT",
        "decision": "STRONG_VISUAL_EVIDENCE" if vision_score >= 0.78 else "PARTIAL_VISUAL_EVIDENCE",
        "confidence": vision_score,
        "evidence": [
            f"Visible boundary edges: {vis_edges}/4 ({vis_ratio * 100:.0f}%)",
            f"Boundary neural probability: {bnd_conf:.2f}",
            f"Building roof edge probability: {bldg_conf:.2f}",
        ],
        "warnings": vision_warnings,
    }

    # 2. GEOMETRY AGENT
    topo_penalty = 0.0
    geom_warnings = []
    if topology_status != "VALID":
        topo_penalty = 0.35 if topology_status in ("SELF_INTERSECTION", "OVERLAP", "DUPLICATE", "INVALID_CRS") else 0.18
        geom_warnings.append(f"Topology engine reported status: {topology_status}.")
    if compactness < 0.48:
        geom_warnings.append(f"Low Polsby-Popper compactness ({compactness:.2f}).")

    geometry_score = round(max(0.20, min(0.98, 0.55 + 0.45 * compactness - topo_penalty)), 3)
    geometry_report = {
        "agent": "GEOMETRY_AGENT",
        "decision": "GEOMETRY_VALID" if topology_status == "VALID" else "TOPOLOGY_ALERT",
        "confidence": geometry_score,
        "evidence": [
            f"Metric Area (EPSG:32643): {area_sqm:.1f} m²",
            f"Compactness index: {compactness:.2f}",
            f"Topology status: {topology_status}",
        ],
        "warnings": geom_warnings,
    }

    # 3. GIS AGENT
    conflict_penalty = 0.28 if conflict_status != "NONE" else 0.0
    gis_score = round(max(0.25, min(0.97, 0.75 * gis_iou + (0.20 if road_access else 0.05) - conflict_penalty * 0.5)), 3)
    gis_warnings = []
    if conflict_status != "NONE":
        gis_warnings.append(f"GIS conflict detected against legacy reference layer: {conflict_status} (IoU={gis_iou:.2f}).")
    if not road_access:
        gis_warnings.append("Parcel lacks direct adjacency to primary/secondary road corridor.")
    gis_report = {
        "agent": "GIS_AGENT",
        "decision": "GIS_CONSISTENT" if conflict_status == "NONE" else "GIS_LAYER_CONFLICT",
        "confidence": gis_score,
        "evidence": [
            f"Reference GIS Spatial IoU: {gis_iou:.2f} (Non-authoritative legacy layer)",
            f"Road corridor adjacency: {'Verified' if road_access else 'Missing'}",
            f"CRS alignment: EPSG:4326 / UTM 43N (EPSG:32643)",
        ],
        "warnings": gis_warnings,
    }

    # 4. ML AGENT
    agreement_score = max(0.0, 1.0 - model_dis * 2.5)
    ml_score = round(float(0.40 * bldg_conf + 0.30 * lu_conf + 0.30 * agreement_score), 3)
    ml_warnings = []
    if model_dis > 0.08:
        ml_warnings.append(f"Inter-model disagreement of {model_dis:.2f} between RGBD ResUNet and RGB UNet.")
    ml_report = {
        "agent": "ML_AGENT",
        "decision": "HIGH_MODEL_CONSENSUS" if ml_score >= 0.80 else "MODERATE_UNCERTAINTY",
        "confidence": ml_score,
        "evidence": [
            f"Building ResUNet (RGB+nDSM) confidence: {bldg_conf:.2f}",
            f"Land-Use ResUNet confidence: {lu_conf:.2f}",
            f"Multi-model consensus score: {agreement_score:.2f}",
        ],
        "warnings": ml_warnings,
    }

    # 5. ANOMALY AGENT
    anom_count = len(parcel_anomalies)
    chg_count = len(parcel_changes)
    # Higher anomaly_score means higher anomaly risk (0.0 = clean, 1.0 = severe anomaly)
    raw_anom_risk = min(0.95, 0.12 + 0.28 * anom_count + 0.18 * chg_count + (0.22 if conflict_status != "NONE" else 0.0))
    anomaly_score = round(raw_anom_risk, 3)
    anom_warnings = [a["explanation"] for a in parcel_anomalies] + [c["summary"] for c in parcel_changes]
    anomaly_report = {
        "agent": "ANOMALY_AGENT",
        "decision": "ANOMALY_FLAGGED" if (anom_count > 0 or chg_count > 0) else "NO_ANOMALY",
        "confidence": round(1.0 - anomaly_score * 0.5, 3),
        "anomaly_risk": anomaly_score,
        "evidence": [
            f"Anomalies/Conflicts on parcel: {anom_count}",
            f"Temporal changes (T0->T2): {chg_count}",
            f"Anomaly status: {anomaly_status}",
        ],
        "warnings": anom_warnings,
    }

    # 6. COUNCIL FUSION & TRANSPARENT CONFIDENCE CALCULATION
    # Weighted combination of positive evidence minus anomaly/topology penalties
    final_evidence_score = round(
        float(
            0.26 * vision_score
            + 0.22 * geometry_score
            + 0.20 * gis_score
            + 0.22 * ml_score
            + 0.10 * (1.0 - anomaly_score)
        ),
        3,
    )

    if final_evidence_score >= 0.80 and topology_status == "VALID" and conflict_status == "NONE" and anomaly_status == "NONE":
        conf_category = "HIGH"
    elif final_evidence_score >= 0.64:
        conf_category = "MEDIUM"
    else:
        conf_category = "LOW"

    # Determine Council Decision & Recommended Action
    if topology_status in ("SELF_INTERSECTION", "OVERLAP", "DUPLICATE", "INVALID_CRS"):
        decision = "GEOMETRY_ERROR"
        recommended_action = "GEOMETRY_ERROR"
    elif conflict_status != "NONE" or anomaly_status == "BUILDING_CROSSING_BOUNDARY":
        decision = "CONFLICT_DETECTED"
        recommended_action = "CONFLICT_DETECTED"
    elif final_evidence_score < 0.64:
        decision = "LOW_CONFIDENCE"
        recommended_action = "LOW_CONFIDENCE"
    elif vis_edges < 4 or chg_count > 0 or anom_count > 0 or final_evidence_score < 0.83:
        decision = "REQUIRES_VERIFICATION"
        recommended_action = "REQUIRES_VERIFICATION"
    else:
        decision = "ACCEPT_FOR_REVIEW"
        recommended_action = "ACCEPT_FOR_REVIEW"

    # 7. FIELD VERIFICATION AGENT (AI-Assisted Field Verification Priority)
    uncertainty_term = 1.0 - final_evidence_score
    conflict_term = 0.30 if conflict_status != "NONE" else 0.0
    anomaly_term = 0.25 if anomaly_status != "NONE" else 0.0
    change_term = 0.20 if chg_count > 0 else 0.0
    topo_term = 0.30 if topology_status != "VALID" else 0.0

    priority_score = round(min(1.0, uncertainty_term + conflict_term + anomaly_term + change_term + topo_term), 3)
    if priority_score >= 0.55 or decision in ("GEOMETRY_ERROR", "CONFLICT_DETECTED", "LOW_CONFIDENCE"):
        field_priority = "HIGH"
    elif priority_score >= 0.28 or decision == "REQUIRES_VERIFICATION":
        field_priority = "MEDIUM"
    else:
        field_priority = "LOW"

    reasons = []
    if topology_status != "VALID":
        reasons.append(f"Topology issue: {topology_status}")
    if conflict_status != "NONE":
        reasons.append(f"Reference GIS mismatch: {conflict_status}")
    if anomaly_status != "NONE":
        reasons.append(f"Spatial anomaly: {anomaly_status}")
    if chg_count > 0:
        reasons.append(f"Temporal change detected ({chg_count} event(s) across T0-T2)")
    if vis_edges < 3:
        reasons.append(f"Inferred boundaries ({4 - vis_edges} occluded/unmarked edges)")
    if not reasons:
        reasons.append("Routine human surveyor sign-off required for AI candidate parcel")

    field_report = {
        "agent": "FIELD_VERIFICATION_AGENT",
        "decision": f"{field_priority}_PRIORITY_VERIFICATION",
        "priority": field_priority,
        "priority_score": priority_score,
        "reasons": reasons,
        "evidence_to_check": [
            "Physical boundary markers / compound wall corners",
            "Building roof overhang vs ground plinth line",
            "Legacy revenue sketch alignment",
        ],
    }

    supporting_evidence = (
        vision_report["evidence"][:2]
        + geometry_report["evidence"][:2]
        + ml_report["evidence"][:2]
    )
    conflicting_evidence = (
        vision_warnings + geom_warnings + gis_warnings + ml_warnings + anom_warnings
    )

    confidence_breakdown = {
        "vision_confidence": vision_score,
        "geometry_confidence": geometry_score,
        "gis_consistency": gis_score,
        "ml_confidence": ml_score,
        "topology_status": topology_status,
        "evidence_count": len(supporting_evidence),
        "anomaly_score": anomaly_score,
        "overall_confidence": final_evidence_score,
        "formula": "0.26*Vision + 0.22*Geometry + 0.20*GIS + 0.22*ML + 0.10*(1-AnomalyRisk)",
    }

    return {
        "parcel_id": pid,
        "vision_score": vision_score,
        "geometry_score": geometry_score,
        "gis_score": gis_score,
        "ml_score": ml_score,
        "anomaly_score": anomaly_score,
        "field_need": field_priority,
        "priority_score": priority_score,
        "priority_reasons": reasons,
        "final_evidence_score": final_evidence_score,
        "confidence": final_evidence_score,
        "confidence_category": conf_category,
        "confidence_breakdown": confidence_breakdown,
        "decision": decision,
        "recommended_action": recommended_action,
        "supporting_evidence": supporting_evidence,
        "conflicting_evidence": conflicting_evidence,
        "agent_reports": {
            "VISION_AGENT": vision_report,
            "GEOMETRY_AGENT": geometry_report,
            "GIS_AGENT": gis_report,
            "ML_AGENT": ml_report,
            "ANOMALY_AGENT": anomaly_report,
            "FIELD_VERIFICATION_AGENT": field_report,
        },
    }
