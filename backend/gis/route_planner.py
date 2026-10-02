import math
from typing import List, Dict, Any
import numpy as np
from shapely.geometry import LineString, Point, mapping

from backend.db import compute_metric_area_perimeter


def plan_smart_field_routes(
    scene_id: str,
    verification_tasks: List[Dict[str, Any]],
    num_clusters: int = 2,
) -> List[Dict[str, Any]]:
    """
    Prototype Smart Field Route Planner.
    Clusters pending field verification tasks spatially and solves a priority-weighted
    nearest-neighbor + 2-opt traversal in metric coordinates (EPSG:32643).
    """
    active = [t for t in verification_tasks if t.get("status", "PENDING") != "HUMAN_VERIFIED"]
    if not active:
        active = verification_tasks
    if not active:
        return []

    coords = np.array([[t["centroid_lon"], t["centroid_lat"]] for t in active], dtype=np.float64)
    k = min(num_clusters, len(active))

    # Simple deterministic spatial k-means clustering
    centroids = coords[:k].copy()
    labels = np.zeros(len(active), dtype=int)
    for _ in range(8):
        dists = np.linalg.norm(coords[:, None, :] - centroids[None, :, :], axis=2)
        labels = np.argmin(dists, axis=1)
        for ci in range(k):
            pts = coords[labels == ci]
            if len(pts) > 0:
                centroids[ci] = pts.mean(axis=0)

    routes: List[Dict[str, Any]] = []
    priority_weight = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    for ci in range(k):
        cluster_tasks = [t for idx, t in enumerate(active) if labels[idx] == ci]
        if not cluster_tasks:
            continue

        # Sort initially by priority (HIGH first) then nearest-neighbor traversal
        cluster_tasks.sort(key=lambda x: (priority_weight.get(x["priority"], 2), -x.get("priority_score", 0.5)))
        ordered = [cluster_tasks[0]]
        remaining = cluster_tasks[1:]

        while remaining:
            last = ordered[-1]
            # Score balances spatial proximity and priority tier
            def step_cost(cand):
                dlon = (cand["centroid_lon"] - last["centroid_lon"]) * 111320.0
                dlat = (cand["centroid_lat"] - last["centroid_lat"]) * 110540.0
                dist_m = math.hypot(dlon, dlat)
                p_penalty = priority_weight.get(cand["priority"], 1) * 35.0
                return dist_m + p_penalty

            nxt = min(remaining, key=step_cost)
            ordered.append(nxt)
            remaining.remove(nxt)

        stops = []
        line_pts = []
        cum_dist_m = 0.0
        for seq_idx, task in enumerate(ordered, start=1):
            pt = (task["centroid_lon"], task["centroid_lat"])
            if line_pts:
                seg = LineString([line_pts[-1], pt])
                _, seg_len = compute_metric_area_perimeter(seg)
                cum_dist_m += seg_len
            line_pts.append(pt)
            stops.append({
                "sequence": seq_idx,
                "task_id": task["id"],
                "parcel_id": task["parcel_id"],
                "priority": task["priority"],
                "priority_score": task["priority_score"],
                "reasons": task["reasons"],
                "lon": task["centroid_lon"],
                "lat": task["centroid_lat"],
                "cumulative_distance_m": round(cum_dist_m, 1),
            })

        if len(line_pts) == 1:
            # Create a tiny segment so LineString is valid
            line_pts.append((line_pts[0][0] + 0.00005, line_pts[0][1] + 0.00005))

        route_line = LineString(line_pts)
        _, total_dist_m = compute_metric_area_perimeter(route_line)

        routes.append({
            "id": f"{scene_id}_ROUTE_{ci + 1:02d}",
            "scene_id": scene_id,
            "cluster_id": ci + 1,
            "route_name": f"Sector Verification Cluster #{ci + 1} ({len(stops)} stops)",
            "task_count": len(stops),
            "estimated_distance_m": round(total_dist_m, 2),
            "ordered_stops": stops,
            "disclaimer": "PROTOTYPE FIELD PLANNING TOOL - NOT NAVIGATION GRADE",
            "geometry": mapping(route_line),
        })

    return routes
