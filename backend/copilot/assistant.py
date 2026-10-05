import json
import re
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Project,
    Parcel,
    Building,
    TopologyIssue,
    Anomaly,
    ChangeEvent,
    CouncilDecision,
    VerificationRecord,
    FeatureVersion,
    ModelRun,
)


def _format_copilot_response(
    tool_invoked: str,
    answer: str,
    highlight_ids: List[str],
    data: Dict[str, Any],
    suggested_tab: Optional[str] = None,
    citations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "tool_invoked": tool_invoked,
        "intent": tool_invoked,
        "answer": answer,
        "answer_markdown": answer,
        "highlight_feature_ids": highlight_ids,
        "highlighted_feature_ids": highlight_ids,
        "suggested_tab": suggested_tab,
        "citations": citations or ["PostGIS Spatial Engine", "6-Agent AI Council"],
        "data": data,
    }


def query_cadastral_copilot(
    db: Session,
    project_id: str,
    scene_id: str,
    question: str,
    selected_parcel_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic tool-backed Cadastral AI Copilot.
    Executes live queries against the PostgreSQL + PostGIS project tables and returns
    grounded answers, supporting data records, and feature IDs to highlight on the map.
    """
    q = (question or "").strip()
    if not q:
        raise HTTPException(
            status_code=400, detail="Copilot query/question cannot be empty."
        )
    if len(q) > 4000:
        raise HTTPException(
            status_code=400, detail="Copilot query exceeds maximum length (4000 chars)."
        )

    q_low = q.lower()

    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return _format_copilot_response(
            tool_invoked="unknown_project_lookup",
            answer=f"### Project Not Found (`{project_id}`)\nProject `{project_id}` does not exist in the PostgreSQL cadastral database. Please select a valid project.",
            highlight_ids=[],
            data={"project_id": project_id, "exists": False, "parcels": 0},
            citations=["PostgreSQL Project Registry"],
        )

    parcels = (
        db.query(Parcel)
        .filter(
            Parcel.project_id == project_id,
            Parcel.scene_id == scene_id,
            Parcel.parcel_layer == "CANDIDATE",
        )
        .order_by(Parcel.id.asc())
        .all()
    )
    buildings = (
        db.query(Building)
        .filter(Building.project_id == project_id, Building.scene_id == scene_id)
        .all()
    )
    topo_issues = (
        db.query(TopologyIssue)
        .filter(
            TopologyIssue.project_id == project_id, TopologyIssue.scene_id == scene_id
        )
        .all()
    )
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.project_id == project_id, Anomaly.scene_id == scene_id)
        .all()
    )
    changes = (
        db.query(ChangeEvent)
        .filter(ChangeEvent.project_id == project_id, ChangeEvent.scene_id == scene_id)
        .all()
    )
    councils = (
        db.query(CouncilDecision)
        .filter(
            CouncilDecision.project_id == project_id,
            CouncilDecision.scene_id == scene_id,
        )
        .all()
    )
    verif_tasks = (
        db.query(VerificationRecord)
        .filter(
            VerificationRecord.project_id == project_id,
            VerificationRecord.scene_id == scene_id,
        )
        .all()
    )

    if not parcels:
        return _format_copilot_response(
            tool_invoked="empty_scene_state",
            answer=f"### No Candidate Parcels in `{scene_id}` (Project `{project_id}`)\nThe database currently contains **0 candidate parcels** for scene `{scene_id}` in project `{project_id}`. Run the AI Analysis pipeline or upload a dataset first.",
            highlight_ids=[],
            data={"project_id": project_id, "scene_id": scene_id, "parcels": 0},
            citations=["PostGIS Spatial Engine"],
        )

    # Check if user mentioned a specific parcel number/ID (e.g., P-002, P_002, scene_urban_T1_P_002)
    explicit_id_match = re.search(r"(scene_[a-z0-9_]+_p_\d+)", q_low)
    match_p = re.search(r"\bp[-_]?(\d{1,4})\b", q_low)
    target_parcel = None
    requested_parcel_label = None

    if explicit_id_match:
        req_id = explicit_id_match.group(1)
        requested_parcel_label = req_id
        target_parcel = next((p for p in parcels if p.id.lower() == req_id), None)
    elif match_p:
        num = int(match_p.group(1))
        requested_parcel_label = f"P_{num:03d}"
        suffix = f"_p_{num:03d}"
        target_parcel = next(
            (p for p in parcels if p.id.lower().endswith(suffix) or p.id.lower() == q_low),
            None,
        )
    elif selected_parcel_id and any(
        w in q_low for w in ["this parcel", "selected parcel", "current parcel"]
    ):
        requested_parcel_label = selected_parcel_id
        target_parcel = next((p for p in parcels if p.id == selected_parcel_id), None)

    # If user explicitly asked about a parcel number/ID that does NOT exist, report honestly!
    if requested_parcel_label and target_parcel is None:
        available_ids = ", ".join(f"`{p.id}`" for p in parcels[:6])
        return _format_copilot_response(
            tool_invoked="unknown_parcel_lookup",
            answer=(
                f"### Parcel `{requested_parcel_label}` Not Found\n"
                f"Parcel `{requested_parcel_label}` does not exist in project `{project_id}` / scene `{scene_id}`.\n\n"
                f"**Available candidate parcels ({len(parcels)} total):** {available_ids}..."
            ),
            highlight_ids=[],
            data={
                "requested_parcel": requested_parcel_label,
                "exists": False,
                "available_count": len(parcels),
            },
            citations=["PostGIS Parcel Table"],
        )

    # 1. Specific Parcel Explainability / Evidence / Time Machine Comparison
    if target_parcel:
        pid = target_parcel.id
        cd = next((c for c in councils if c.parcel_id == pid), None)
        p_anoms = [a for a in anomalies if a.parcel_id == pid]
        p_chgs = [c for c in changes if c.parcel_id == pid]
        p_topo = [
            t for t in topo_issues if pid in json.loads(t.affected_features_json or "[]")
        ]
        p_vers = (
            db.query(FeatureVersion)
            .filter(
                FeatureVersion.project_id == project_id,
                FeatureVersion.feature_id == pid,
            )
            .order_by(FeatureVersion.version_number.asc())
            .all()
        )

        if any(w in q_low for w in ["compare", "previous", "history", "t0", "time machine"]):
            ver_lines = [
                f"- **{v.temporal_epoch}** (v{v.version_number}): Area={v.area_sqm:.1f} m², Land-Use=`{v.land_use_class}`, Buildings={v.building_count}, Status=`{v.status}`"
                for v in p_vers
            ]
            ans = (
                f"### Temporal Comparison for Parcel `{pid}`\n"
                + ("\n".join(ver_lines) if ver_lines else "No multi-epoch history found.")
                + (
                    "\n\n**Detected Change Events:**\n"
                    + "\n".join(
                        f"- `{c.change_type}` ({c.from_epoch}→{c.to_epoch}): {c.summary}"
                        for c in p_chgs
                    )
                    if p_chgs
                    else "\n\nNo structural or land-use transition flagged across T0–T2."
                )
            )
            return _format_copilot_response(
                tool_invoked="inspect_parcel_temporal_history",
                answer=ans,
                highlight_ids=[pid],
                data={
                    "parcel_id": pid,
                    "versions": len(p_vers),
                    "changes": [c.summary for c in p_chgs],
                },
                suggested_tab="timemachine",
                citations=["Parcel Time Machine", "PostGIS FeatureVersion Lineage"],
            )

        supp = json.loads(cd.supporting_evidence_json or "[]") if cd else []
        conf_ev = json.loads(cd.conflicting_evidence_json or "[]") if cd else []
        ans = (
            f"### Diagnostic Report for Parcel `{pid}`\n"
            f"- **AI Confidence:** `{target_parcel.confidence:.2f}` (`{target_parcel.confidence_category}`)\n"
            f"- **Metric Area / Perimeter:** `{target_parcel.area_sqm:.1f} m²` / `{target_parcel.perimeter_m:.1f} m` (`EPSG:32643`)\n"
            f"- **Boundary Representation:** `{target_parcel.boundary_representation}`\n"
            f"- **AI Council Decision:** `{target_parcel.council_decision}` (Verification Priority: `{target_parcel.verification_priority}`)\n"
            f"- **Topology / Conflict / Anomaly:** `{target_parcel.topology_status}` / `{target_parcel.conflict_status}` / `{target_parcel.anomaly_status}`\n\n"
            f"**Supporting Evidence:**\n"
            + ("\n".join(f"- {s}" for s in supp) if supp else "- Standard PostGIS geometry & vision evidence")
            + (
                "\n\n**Warnings & Flag Reasons:**\n"
                + "\n".join(f"- {w}" for w in conf_ev)
                if conf_ev
                else "\n\nNo conflicting evidence warnings."
            )
        )
        return _format_copilot_response(
            tool_invoked="explain_parcel_evidence_and_flags",
            answer=ans,
            highlight_ids=[pid],
            data={
                "parcel_id": pid,
                "confidence": target_parcel.confidence,
                "council_decision": target_parcel.council_decision,
                "topology_issues": [t.explanation for t in p_topo],
                "anomalies": [a.explanation for a in p_anoms],
            },
            suggested_tab="council",
            citations=["6-Agent AI Council", "PostGIS Parcel Inspector"],
        )

    # 1b. Real Building Detection Model / Inria Benchmark queries
    if any(w in q_low for w in ["inria", "aerial model", "building model", "resunet", "aerial building"]):
        ans_lines = [
            "### AeroCadastre Real Aerial Building Detection Engine (Inria Benchmark)",
            "- **Active Champion Model:** `EXP_BUILDING_RESUNET_001` (Residual U-Net, 2.05M parameters)",
            "- **Validation Metrics:** Val IoU = `46.42%` (+6.25% vs baseline), Val Dice = `63.41%`, Boundary F1 = `32.96%`, Precision = `61.19%`, Recall = `65.79%`",
            "- **Untouched Test Metrics (250 multi-city patches):** Test IoU = `42.58%`, Test Dice = `59.73%`, Boundary F1 = `28.86%`, Pixel Accuracy = `82.52%`",
            "- **Inference & GIS Extraction CLI:** `python infer_buildings.py --image <path> --checkpoint models/EXP_BUILDING_RESUNET_001_AerialInria.pt --output <dir>`",
            "- **Cadastral Boundary Rule:** Building footprints serve as physical rooftop evidence and do *not* automatically establish legal cadastral parcel boundaries (setbacks, road ROW, and compound walls must be reconciled by the AI Council).",
        ]
        return _format_copilot_response(
            tool_invoked="query_aerial_building_model",
            answer="\n".join(ans_lines),
            highlight_ids=[],
            data={"model": "EXP_BUILDING_RESUNET_001", "val_iou": 0.4642, "test_iou": 0.4258},
            suggested_tab="analysis",
            citations=["Inria Aerial Benchmark", "EXP_BUILDING_RESUNET_001", "GeoAI Vision Model Registry"],
        )

    # 2. Overlap / Gap / Topology queries
    if any(w in q_low for w in ["overlap", "gap", "topology", "self-intersection", "sliver"]):
        if not topo_issues:
            return _format_copilot_response(
                tool_invoked="query_topology_issues",
                answer=f"All {len(parcels)} candidate parcels in `{scene_id}` currently pass topology validation with zero unresolved overlaps or gaps.",
                highlight_ids=[],
                data={"issue_count": 0},
                suggested_tab="map",
                citations=["PostGIS Topology Engine"],
            )
        affected_ids = []
        lines = [
            f"### Active Topology Issues in `{scene_id}` ({len(topo_issues)} found)"
        ]
        for t in topo_issues:
            aff = json.loads(t.affected_features_json or "[]")
            affected_ids.extend(aff)
            lines.append(
                f"- **`{t.id}` [{t.issue_type} — {t.severity}]:** {t.explanation} (Affected: `{', '.join(aff)}`)"
            )
        return _format_copilot_response(
            tool_invoked="query_topology_issues",
            answer="\n".join(lines),
            highlight_ids=sorted(list(set(affected_ids))),
            data={"issue_count": len(topo_issues)},
            suggested_tab="map",
            citations=["PostGIS ST_Overlaps / ST_IsValid"],
        )

    # 3. Low-Confidence Buildings or Parcels
    if "building" in q_low and ("low" in q_low or "confiden" in q_low):
        sorted_b = sorted(buildings, key=lambda b: b.confidence)[:5]
        lines = [f"### Lowest-Confidence Building Footprints in `{scene_id}`"]
        for b in sorted_b:
            lines.append(
                f"- **`{b.id}`**: Confidence=`{b.confidence:.2f}` (`{b.confidence_category}`), Area=`{b.area_sqm:.1f} m²`, Model=`{b.model_source}`"
            )
        return _format_copilot_response(
            tool_invoked="query_low_confidence_buildings",
            answer="\n".join(lines),
            highlight_ids=[b.id for b in sorted_b],
            data={"buildings": [b.id for b in sorted_b]},
            suggested_tab="analysis",
            citations=["Building_MicroResUNet_RGBD_v2"],
        )

    if "low" in q_low and "confiden" in q_low:
        sorted_p = sorted(parcels, key=lambda p: p.confidence)
        low_p = [p for p in sorted_p if p.confidence < 0.80] or sorted_p[:4]
        lines = [
            f"### Candidate Parcels Requiring Attention by Confidence (`{scene_id}`)"
        ]
        for p in low_p:
            lines.append(
                f"- **`{p.id}`**: Confidence=`{p.confidence:.2f}` (`{p.confidence_category}`), Boundary=`{p.boundary_representation}`, Council=`{p.council_decision}`"
            )
        return _format_copilot_response(
            tool_invoked="query_low_confidence_parcels",
            answer="\n".join(lines),
            highlight_ids=[p.id for p in low_p],
            data={"parcel_ids": [p.id for p in low_p]},
            suggested_tab="verification",
            citations=["Multi-Task GeoAI Confidence Engine"],
        )

    # 4. GIS Conflicts & Anomalies
    if any(w in q_low for w in ["conflict", "anomaly", "mismatch", "crossing", "encroach"]):
        lines = [
            f"### GIS Conflicts & Spatial Anomalies in `{scene_id}` ({len(anomalies)} detected)"
        ]
        pids = []
        for a in anomalies:
            if a.parcel_id:
                pids.append(a.parcel_id)
            lines.append(
                f"- **`{a.id}` [{a.category}: {a.anomaly_type} — {a.severity}]:** {a.explanation}"
            )
        return _format_copilot_response(
            tool_invoked="query_conflicts_and_anomalies",
            answer="\n".join(lines),
            highlight_ids=sorted(list(set(pids))),
            data={"count": len(anomalies)},
            suggested_tab="map",
            citations=["GIS Conflict & Anomaly Detector"],
        )

    # 5. Temporal Change Detection (T0 vs T1 vs T2)
    if any(w in q_low for w in ["change", "t0", "t1", "t2", "temporal", "new building"]):
        lines = [
            f"### Temporal Change Analysis (T0 → T1 → T2) for `{scene_id}` ({len(changes)} events)"
        ]
        pids = []
        for c in changes:
            if c.parcel_id:
                pids.append(c.parcel_id)
            lines.append(
                f"- **`{c.id}` [{c.change_type} | {c.from_epoch}→{c.to_epoch}]:** {c.summary}"
            )
        return _format_copilot_response(
            tool_invoked="query_temporal_changes",
            answer="\n".join(lines),
            highlight_ids=sorted(list(set(pids))),
            data={"change_count": len(changes)},
            suggested_tab="changes",
            citations=["Multi-Temporal Change Detector (T0/T1/T2)"],
        )

    # 6. Field Verification Queue
    if any(w in q_low for w in ["verif", "field", "priority", "surveyor", "visit", "queue"]):
        high_tasks = [t for t in verif_tasks if t.priority == "HIGH"]
        med_tasks = [t for t in verif_tasks if t.priority == "MEDIUM"]
        lines = [
            f"### AI-Assisted Field Verification Queue (`{scene_id}`)",
            f"- **HIGH Priority:** {len(high_tasks)} parcels | **MEDIUM Priority:** {len(med_tasks)} parcels",
        ]
        for t in sorted(verif_tasks, key=lambda x: -x.priority_score)[:6]:
            reasons = ", ".join(json.loads(t.reasons_json or "[]"))
            lines.append(
                f"- **`{t.parcel_id}` [{t.priority} — Score `{t.priority_score:.2f}` | Status: `{t.status}`]:** {reasons}"
            )
        return _format_copilot_response(
            tool_invoked="query_verification_queue",
            answer="\n".join(lines),
            highlight_ids=[t.parcel_id for t in high_tasks]
            or [t.parcel_id for t in verif_tasks[:3]],
            data={
                "high_priority_count": len(high_tasks),
                "total_tasks": len(verif_tasks),
            },
            suggested_tab="verification",
            citations=["Surveyor Verification Queue", "Field Route Planner"],
        )

    # 7. Default Comprehensive Project Status Summary
    runs = db.query(ModelRun).all()
    best_bldg = max(
        (r for r in runs if r.task_type == "BUILDING_SEG"),
        key=lambda x: x.iou,
        default=None,
    )
    ans = (
        f"### SIH26012 Cadastral Project Overview (`{scene_id}` — SYNTHETIC DEMO DATA)\n"
        f"- **Candidate Parcels:** {len(parcels)} (`AI-GENERATED / REQUIRES VERIFICATION`)\n"
        f"- **Detected Buildings:** {len(buildings)} | **Topology Issues:** {len(topo_issues)} | **Conflicts/Anomalies:** {len(anomalies)}\n"
        f"- **Temporal Changes (T0–T2):** {len(changes)} | **Pending Verification Tasks:** {sum(1 for t in verif_tasks if t.status == 'PENDING')}\n"
        + (
            f"- **Active Building Model:** `{best_bldg.model_name}` (Validation IoU=`{best_bldg.iou:.4f}`, Dice=`{best_bldg.dice_f1:.4f}`)\n"
            if best_bldg
            else ""
        )
        + "\n*Ask about specific parcels (e.g. 'Why was P_002 flagged?'), overlaps, GIS conflicts, temporal changes, or verification priorities.*"
    )
    return _format_copilot_response(
        tool_invoked="project_status_summary",
        answer=ans,
        highlight_ids=[p.id for p in parcels[:2]],
        data={
            "parcels": len(parcels),
            "buildings": len(buildings),
            "topology_issues": len(topo_issues),
            "anomalies": len(anomalies),
        },
        suggested_tab="overview",
        citations=["PostGIS Spatial Database", "PyTorch Model Registry"],
    )
