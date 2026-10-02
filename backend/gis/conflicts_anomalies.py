from typing import List, Dict, Any
import numpy as np
from shapely.geometry import shape, mapping

from backend.db import compute_metric_area_perimeter
from backend.gis.topology import polsby_popper_compactness


def detect_conflicts_and_anomalies(
    scene_id: str,
    candidate_parcels: List[Dict[str, Any]],
    reference_parcels: List[Dict[str, Any]],
    buildings: List[Dict[str, Any]],
    roads: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Detect GIS Conflicts (Candidate vs Reference GIS / Buildings / Roads) and Anomalies.
    Never claims Reference GIS is legally authoritative.
    """
    records: List[Dict[str, Any]] = []
    parcel_conflict_status: Dict[str, str] = {}
    parcel_anomaly_status: Dict[str, str] = {}
    seq = 1

    ref_by_pid = {r.get("parcel_id", r["id"]): r for r in reference_parcels}
    areas = [p.get("area_sqm", 100.0) for p in candidate_parcels] or [100.0]
    median_area = float(np.median(areas))

    parsed_buildings = [(b["id"], shape(b["geometry"]), b) for b in buildings]
    parsed_roads = [(r["id"], shape(r["geometry"]).buffer(0.000025), r) for r in roads]

    for p in candidate_parcels:
        pid = p["id"]
        parcel_conflict_status[pid] = "NONE"
        parcel_anomaly_status[pid] = "NONE"
        p_geom = shape(p["geometry"])
        p_area, p_perim = compute_metric_area_perimeter(p_geom)
        comp = polsby_popper_compactness(p_area, p_perim)

        # 1. Compare with Reference GIS Layer
        ref = ref_by_pid.get(pid)
        if ref is None:
            records.append({
                "id": f"{scene_id}_CONF_{seq:03d}",
                "parcel_id": pid,
                "category": "GIS_CONFLICT",
                "anomaly_type": "EXTRA_PARCEL",
                "severity": "MEDIUM",
                "confidence": 0.84,
                "explanation": f"Candidate parcel {pid} has no corresponding record in the Legacy Reference GIS layer (requires surveyor check).",
                "evidence": {"candidate_area_sqm": p_area, "reference_present": False},
                "geometry": p["geometry"],
            })
            parcel_conflict_status[pid] = "EXTRA_PARCEL"
            seq += 1
        else:
            ref_geom = shape(ref["geometry"])
            ref_area, _ = compute_metric_area_perimeter(ref_geom)
            inter = p_geom.intersection(ref_geom)
            union = p_geom.union(ref_geom)
            inter_a, _ = compute_metric_area_perimeter(inter)
            union_a, _ = compute_metric_area_perimeter(union)
            gis_iou = inter_a / max(union_a, 1e-6)
            area_diff_pct = abs(p_area - ref_area) / max(ref_area, 1e-6)

            if gis_iou < 0.88 or area_diff_pct > 0.08:
                sym_diff = p_geom.symmetric_difference(ref_geom)
                records.append({
                    "id": f"{scene_id}_CONF_{seq:03d}",
                    "parcel_id": pid,
                    "category": "GIS_CONFLICT",
                    "anomaly_type": "BOUNDARY_MISMATCH",
                    "severity": "HIGH" if gis_iou < 0.78 else "MEDIUM",
                    "confidence": round(1.0 - gis_iou * 0.5, 3),
                    "explanation": (
                        f"Boundary shift between AI candidate {pid} and non-authoritative Reference GIS "
                        f"(spatial IoU={gis_iou:.2f}, area discrepancy={area_diff_pct * 100:.1f}%)."
                    ),
                    "evidence": {
                        "gis_iou": round(gis_iou, 4),
                        "candidate_area_sqm": p_area,
                        "reference_area_sqm": ref_area,
                        "area_diff_pct": round(area_diff_pct * 100, 2),
                    },
                    "geometry": mapping(sym_diff if not sym_diff.is_empty else p_geom),
                })
                parcel_conflict_status[pid] = "BOUNDARY_MISMATCH"
                seq += 1

        # 2. Check Building Crossing Parcel Boundary
        bldg_area_sum = 0.0
        for bid, b_geom, b_obj in parsed_buildings:
            if p_geom.intersects(b_geom):
                inside_part = p_geom.intersection(b_geom)
                outside_part = b_geom.difference(p_geom)
                in_area, _ = compute_metric_area_perimeter(inside_part)
                out_area, _ = compute_metric_area_perimeter(outside_part)
                bldg_area_sum += in_area
                # If building belongs primarily to this parcel but extends >1.5 m^2 outside
                if b_obj.get("parcel_id") == pid and out_area > 1.5:
                    records.append({
                        "id": f"{scene_id}_ANOM_{seq:03d}",
                        "parcel_id": pid,
                        "category": "ANOMALY",
                        "anomaly_type": "BUILDING_CROSSING_BOUNDARY",
                        "severity": "HIGH",
                        "confidence": 0.91,
                        "explanation": f"Building {bid} extends {out_area:.1f} m² across candidate boundary of parcel {pid}.",
                        "evidence": {"building_id": bid, "encroachment_sqm": out_area, "inside_sqm": in_area},
                        "geometry": mapping(outside_part if not outside_part.is_empty else b_geom),
                    })
                    parcel_anomaly_status[pid] = "BUILDING_CROSSING_BOUNDARY"
                    seq += 1

        # 3. Check Road Corridor Encroachment
        for rid, r_buf, _ in parsed_roads:
            if p_geom.intersects(r_buf):
                enc = p_geom.intersection(r_buf)
                enc_area, _ = compute_metric_area_perimeter(enc)
                if enc_area > 4.5:
                    records.append({
                        "id": f"{scene_id}_CONF_{seq:03d}",
                        "parcel_id": pid,
                        "category": "GIS_CONFLICT",
                        "anomaly_type": "ROAD_PARCEL_CONFLICT",
                        "severity": "MEDIUM",
                        "confidence": 0.85,
                        "explanation": f"Candidate parcel {pid} encroaches {enc_area:.1f} m² into road corridor {rid}.",
                        "evidence": {"road_id": rid, "encroachment_sqm": enc_area},
                        "geometry": mapping(enc),
                    })
                    if parcel_conflict_status[pid] == "NONE":
                        parcel_conflict_status[pid] = "ROAD_PARCEL_CONFLICT"
                    seq += 1

        # 4. Check Extreme Area / Unusual Shape / Building Density / Model Disagreement
        if p_area > median_area * 2.1 or p_area < median_area * 0.35:
            records.append({
                "id": f"{scene_id}_ANOM_{seq:03d}",
                "parcel_id": pid,
                "category": "ANOMALY",
                "anomaly_type": "EXTREME_AREA",
                "severity": "MEDIUM",
                "confidence": 0.82,
                "explanation": f"Parcel {pid} area ({p_area:.1f} m²) deviates significantly from sector median ({median_area:.1f} m²).",
                "evidence": {"parcel_area_sqm": p_area, "sector_median_sqm": round(median_area, 2)},
                "geometry": p["geometry"],
            })
            if parcel_anomaly_status[pid] == "NONE":
                parcel_anomaly_status[pid] = "EXTREME_AREA"
            seq += 1

        if comp < 0.42:
            records.append({
                "id": f"{scene_id}_ANOM_{seq:03d}",
                "parcel_id": pid,
                "category": "ANOMALY",
                "anomaly_type": "UNUSUAL_SHAPE",
                "severity": "LOW",
                "confidence": 0.77,
                "explanation": f"Parcel {pid} has low Polsby-Popper compactness ({comp:.2f}), indicating irregular geometry.",
                "evidence": {"compactness": comp},
                "geometry": p["geometry"],
            })
            if parcel_anomaly_status[pid] == "NONE":
                parcel_anomaly_status[pid] = "UNUSUAL_SHAPE"
            seq += 1

        model_dis = float(p.get("model_disagreement", 0.0))
        if model_dis > 0.09:
            records.append({
                "id": f"{scene_id}_ANOM_{seq:03d}",
                "parcel_id": pid,
                "category": "ANOMALY",
                "anomaly_type": "MODEL_DISAGREEMENT",
                "severity": "MEDIUM",
                "confidence": round(min(0.95, 0.65 + model_dis), 3),
                "explanation": f"Disagreement ({model_dis:.2f}) between RGBD ResUNet and RGB UNet within parcel {pid}.",
                "evidence": {"model_disagreement": round(model_dis, 4)},
                "geometry": p["geometry"],
            })
            if parcel_anomaly_status[pid] == "NONE":
                parcel_anomaly_status[pid] = "MODEL_DISAGREEMENT"
            seq += 1

    return {
        "scene_id": scene_id,
        "records": records,
        "parcel_conflict_status": parcel_conflict_status,
        "parcel_anomaly_status": parcel_anomaly_status,
    }
