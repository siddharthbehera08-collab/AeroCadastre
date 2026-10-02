import json
import math
from typing import List, Dict, Any
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.validation import explain_validity, make_valid
from shapely.ops import unary_union

from backend.db import compute_metric_area_perimeter


def polsby_popper_compactness(area_sqm: float, perimeter_m: float) -> float:
    if perimeter_m <= 1e-6 or area_sqm <= 0:
        return 0.0
    return round(float(min(1.0, (4.0 * math.pi * area_sqm) / (perimeter_m ** 2))), 4)


def validate_parcels_topology(
    scene_id: str,
    parcels: List[Dict[str, Any]],
    roads: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run real GIS topology validation across candidate parcels using Shapely:
    Checks:
      - SELF_INTERSECTION / INVALID_RING
      - DISCONNECTED (MultiPolygon)
      - HOLE (unexpected interior rings)
      - SLIVER (very small area < 15 m^2 or compactness < 0.14)
      - DUPLICATE (IoU > 0.95)
      - OVERLAP (pairwise polygon intersection > 0.5 m^2)
      - GAP (unexpected narrow interstitial void between adjacent parcels)
      - INVALID_CRS
    """
    issues: List[Dict[str, Any]] = []
    parcel_status: Dict[str, str] = {}
    parsed_geoms: List[ tuple[str, Any, Dict[str, Any]] ] = []
    issue_seq = 1

    for p in parcels:
        pid = p["id"]
        parcel_status[pid] = "VALID"
        crs = p.get("crs", "EPSG:4326")
        if crs not in ("EPSG:4326", "EPSG:32643", "EPSG:3857"):
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "INVALID_CRS",
                "severity": "HIGH",
                "affected_features": [pid],
                "area_sqm": 0.0,
                "explanation": f"Parcel {pid} has unsupported or missing CRS '{crs}'.",
                "geometry": p["geometry"],
            })
            parcel_status[pid] = "INVALID_CRS"
            issue_seq += 1

        try:
            geom = shape(p["geometry"])
        except Exception as exc:
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "INVALID_RING",
                "severity": "HIGH",
                "affected_features": [pid],
                "area_sqm": 0.0,
                "explanation": f"Parcel {pid} geometry could not be parsed: {exc}",
                "geometry": {"type": "Point", "coordinates": [77.592, 12.972]},
            })
            parcel_status[pid] = "INVALID_GEOMETRY"
            issue_seq += 1
            continue

        minx, miny, maxx, maxy = geom.bounds
        if crs == "EPSG:4326" and (minx < -180 or maxx > 180 or miny < -90 or maxy > 90):
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "INVALID_CRS",
                "severity": "HIGH",
                "affected_features": [pid],
                "area_sqm": 0.0,
                "explanation": f"Parcel {pid} coordinates ({minx:.2f}, {miny:.2f}) exceed EPSG:4326 geographic bounds.",
                "geometry": mapping(geom.centroid),
            })
            parcel_status[pid] = "INVALID_CRS"
            issue_seq += 1

        if not geom.is_valid:
            reason = explain_validity(geom)
            fixed = make_valid(geom)
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "SELF_INTERSECTION",
                "severity": "HIGH",
                "affected_features": [pid],
                "area_sqm": 0.0,
                "explanation": f"Parcel {pid} has invalid ring / self-intersection: {reason}.",
                "geometry": mapping(fixed if not fixed.is_empty else geom.centroid),
            })
            parcel_status[pid] = "SELF_INTERSECTION"
            issue_seq += 1
            geom = fixed

        if geom.geom_type == "MultiPolygon":
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "DISCONNECTED",
                "severity": "MEDIUM",
                "affected_features": [pid],
                "area_sqm": 0.0,
                "explanation": f"Parcel {pid} consists of {len(geom.geoms)} disconnected polygon parts.",
                "geometry": mapping(geom),
            })
            parcel_status[pid] = "DISCONNECTED"
            issue_seq += 1
            # Use largest part for subsequent checks
            geom = max(geom.geoms, key=lambda g: g.area)

        if isinstance(geom, Polygon) and len(geom.interiors) > 0:
            hole_poly = Polygon(geom.interiors[0])
            h_area, _ = compute_metric_area_perimeter(hole_poly)
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "HOLE",
                "severity": "MEDIUM",
                "affected_features": [pid],
                "area_sqm": h_area,
                "explanation": f"Parcel {pid} contains an unverified interior hole ({h_area:.1f} m²).",
                "geometry": mapping(hole_poly),
            })
            if parcel_status[pid] == "VALID":
                parcel_status[pid] = "HOLE_DETECTED"
            issue_seq += 1

        area_sqm, perim_m = compute_metric_area_perimeter(geom)
        comp = polsby_popper_compactness(area_sqm, perim_m)
        if area_sqm < 15.0 or comp < 0.14:
            issues.append({
                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                "issue_type": "SLIVER",
                "severity": "MEDIUM",
                "affected_features": [pid],
                "area_sqm": area_sqm,
                "explanation": f"Parcel {pid} is a sliver candidate (area={area_sqm:.1f} m², compactness={comp:.2f}).",
                "geometry": mapping(geom),
            })
            if parcel_status[pid] == "VALID":
                parcel_status[pid] = "SLIVER_WARNING"
            issue_seq += 1

        parsed_geoms.append((pid, geom, p))

    # Pairwise checks: DUPLICATE, OVERLAP, and GAP
    n = len(parsed_geoms)
    for i in range(n):
        id_a, geom_a, _ = parsed_geoms[i]
        for j in range(i + 1, n):
            id_b, geom_b, _ = parsed_geoms[j]

            if geom_a.intersects(geom_b):
                inter = geom_a.intersection(geom_b)
                if not inter.is_empty and inter.geom_type in ("Polygon", "MultiPolygon"):
                    inter_area, _ = compute_metric_area_perimeter(inter)
                    union_area, _ = compute_metric_area_perimeter(geom_a.union(geom_b))
                    iou = inter_area / max(union_area, 1e-6)
                    if iou > 0.92:
                        issues.append({
                            "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                            "issue_type": "DUPLICATE",
                            "severity": "HIGH",
                            "affected_features": [id_a, id_b],
                            "area_sqm": inter_area,
                            "explanation": f"Parcels {id_a} and {id_b} are near-duplicates (IoU={iou:.2f}, overlap={inter_area:.1f} m²).",
                            "geometry": mapping(inter),
                        })
                        parcel_status[id_a] = "DUPLICATE"
                        parcel_status[id_b] = "DUPLICATE"
                        issue_seq += 1
                    elif inter_area >= 0.4:
                        issues.append({
                            "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                            "issue_type": "OVERLAP",
                            "severity": "HIGH" if inter_area > 5.0 else "MEDIUM",
                            "affected_features": [id_a, id_b],
                            "area_sqm": inter_area,
                            "explanation": f"Parcel {id_a} overlaps Parcel {id_b} by {inter_area:.2f} m².",
                            "geometry": mapping(inter),
                        })
                        parcel_status[id_a] = "OVERLAP"
                        parcel_status[id_b] = "OVERLAP"
                        issue_seq += 1
            else:
                # Check for unexpected narrow gap between nearby adjacent parcels in same block
                deg_dist = geom_a.distance(geom_b)
                # 1e-6 deg is ~0.11m; 2.2e-5 deg is ~2.4m
                if 1.5e-6 < deg_dist < 2.2e-5:
                    # Construct gap sliver between buffered polygons
                    gap_geom = geom_a.buffer(deg_dist * 0.65).intersection(geom_b.buffer(deg_dist * 0.65))
                    if not gap_geom.is_empty and gap_geom.geom_type in ("Polygon", "MultiPolygon"):
                        gap_area, _ = compute_metric_area_perimeter(gap_geom)
                        if 0.5 <= gap_area <= 85.0:
                            issues.append({
                                "id": f"{scene_id}_TOPO_{issue_seq:03d}",
                                "issue_type": "GAP",
                                "severity": "MEDIUM",
                                "affected_features": [id_a, id_b],
                                "area_sqm": gap_area,
                                "explanation": f"Unexpected interstitial gap ({gap_area:.1f} m²) detected between {id_a} and {id_b}.",
                                "geometry": mapping(gap_geom),
                            })
                            if parcel_status[id_a] == "VALID":
                                parcel_status[id_a] = "GAP_ADJACENT"
                            if parcel_status[id_b] == "VALID":
                                parcel_status[id_b] = "GAP_ADJACENT"
                            issue_seq += 1

    return {
        "scene_id": scene_id,
        "total_parcels": len(parcels),
        "issue_count": len(issues),
        "issues": issues,
        "parcel_topology_status": parcel_status,
    }
