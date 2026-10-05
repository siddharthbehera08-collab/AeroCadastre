"""
Deterministic Field Route Planner for AeroCadastre Surveyor Verification.
Optimizes the inspection sequence for parcels flagged for ground verification.
Uses metric distance optimization (EPSG:32643) with priority weighting.
Clearly labeled as planning assistance; does not claim real-world vehicular navigation accuracy.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import LineString, Point, mapping


class FieldRoutePlanner:
    """
    Deterministic surveyor path planner for field verification tasks.
    """

    def __init__(self, crs: str = "EPSG:32643", average_walking_speed_kmh: float = 4.0):
        self.crs = crs
        self.walking_speed_mps = (average_walking_speed_kmh * 1000.0) / 3600.0

    def plan_verification_route(
        self,
        tasks: List[Dict[str, Any]],
        start_point: Optional[Tuple[float, float]] = None,
    ) -> Dict[str, Any]:
        """
        Plans an ordered verification route visiting priority parcels.

        Args:
            tasks: List of dicts, each with 'parcel_id', 'priority' ('HIGH','MEDIUM','LOW'),
                   and 'coordinates' [easting, northing] or 'centroid' [x, y].
            start_point: Optional starting surveyor base coordinates [easting, northing].
        """
        if not tasks:
            return {
                "route_id": "ROUTE_EMPTY",
                "stop_count": 0,
                "ordered_stops": [],
                "total_distance_m": 0.0,
                "estimated_time_min": 0.0,
                "route_geometry": None,
                "disclaimer": "FIELD ROUTE PLANNING ASSISTANCE ONLY. Does NOT guarantee real-world vehicular navigation or statutory access.",
            }

        # Priority weights: HIGH visited before LOW
        priority_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

        # Normalize task points
        valid_tasks = []
        for t in tasks:
            coords = t.get("coordinates") or t.get("centroid") or [0.0, 0.0]
            valid_tasks.append({
                "parcel_id": t["parcel_id"],
                "priority": t.get("priority", "MEDIUM"),
                "priority_val": priority_weights.get(t.get("priority", "MEDIUM"), 2),
                "x": float(coords[0]),
                "y": float(coords[1]),
                "reasons": t.get("reasons", []),
            })

        # Set start coordinate
        if start_point:
            cur_x, cur_y = float(start_point[0]), float(start_point[1])
        else:
            cur_x, cur_y = valid_tasks[0]["x"], valid_tasks[0]["y"]

        # Greedy priority-weighted nearest neighbor tour
        unvisited = list(valid_tasks)
        ordered_stops = []
        total_dist_m = 0.0
        route_coords = [[cur_x, cur_y]]

        stop_num = 1
        while unvisited:
            # Score each candidate: distance / priority_weight (lower is better)
            best_idx = 0
            best_score = float("inf")
            best_dist = 0.0

            for i, cand in enumerate(unvisited):
                dist = math.hypot(cand["x"] - cur_x, cand["y"] - cur_y)
                score = dist / cand["priority_val"]
                if score < best_score:
                    best_score = score
                    best_dist = dist
                    best_idx = i

            chosen = unvisited.pop(best_idx)
            total_dist_m += best_dist
            cur_x, cur_y = chosen["x"], chosen["y"]
            route_coords.append([cur_x, cur_y])

            ordered_stops.append({
                "stop_number": stop_num,
                "parcel_id": chosen["parcel_id"],
                "priority": chosen["priority"],
                "coordinates": [cur_x, cur_y],
                "leg_distance_m": round(best_dist, 2),
                "reasons": chosen["reasons"],
            })
            stop_num += 1

        route_line = LineString(route_coords) if len(route_coords) > 1 else None
        est_time_min = round((total_dist_m / max(0.1, self.walking_speed_mps)) / 60.0, 1)

        return {
            "route_id": f"ROUTE_VERIF_{len(ordered_stops)}_STOPS",
            "stop_count": len(ordered_stops),
            "ordered_stops": ordered_stops,
            "total_distance_m": round(total_dist_m, 2),
            "estimated_walking_time_min": est_time_min,
            "crs": self.crs,
            "route_geometry": mapping(route_line) if route_line else None,
            "disclaimer": "FIELD ROUTE PLANNING ASSISTANCE ONLY. Does NOT guarantee real-world vehicular navigation or statutory access.",
        }
