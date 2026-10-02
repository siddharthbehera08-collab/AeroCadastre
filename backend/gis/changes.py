import json
from typing import List, Dict, Any, Optional

from backend.config import SYNTHETIC_DATA_DIR


def compare_epoch_features(
    out_scene_id: str,
    p_t0: List[Dict[str, Any]],
    p_t1: List[Dict[str, Any]],
    p_t2: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compare parcel feature lists across epochs T0, T1, and optional T2.
    Detects:
      - NEW_BUILDING
      - REMOVED_BUILDING
      - LAND_USE_CHANGE
      - BOUNDARY_SHIFT (metric area change > 8%)
    """
    if p_t2 is None:
        p_t2 = p_t1

    changes: List[Dict[str, Any]] = []
    versions: List[Dict[str, Any]] = []
    seq = 1

    def slot_map(features):
        m = {}
        for f in features:
            props = f.get("properties", f)
            pid = props["id"]
            slot = "_P_" + pid.split("_P_")[-1] if "_P_" in pid else f"_{pid}"
            m[slot] = {
                "properties": props,
                "geometry": f.get("geometry"),
            }
        return m

    m0, m1, m2 = slot_map(p_t0), slot_map(p_t1), slot_map(p_t2)

    for slot, f1 in sorted(m1.items()):
        canonical_pid = f"{out_scene_id}{slot}"
        f0 = m0.get(slot)
        f2 = m2.get(slot)

        for ver_num, (epoch_code, year_label, feat) in enumerate(
            [
                ("T0", "2024 Historical Archive", f0),
                ("T1", "2025 Drone Baseline", f1),
                ("T2", "2026 AI Candidate Survey", f2),
            ],
            start=1,
        ):
            if feat is None:
                continue
            props = feat["properties"]
            versions.append(
                {
                    "id": f"{canonical_pid}_V{ver_num}_{epoch_code}",
                    "feature_id": canonical_pid,
                    "feature_type": "PARCEL",
                    "version_number": ver_num,
                    "temporal_epoch": epoch_code,
                    "area_sqm": props["area_sqm"],
                    "perimeter_m": props.get("perimeter_m", 100.0),
                    "land_use_class": props["land_use_class"],
                    "building_count": props["building_count"],
                    "confidence": 0.92 if epoch_code != "T2" else 0.85,
                    "status": "HISTORICAL_RECORD"
                    if epoch_code == "T0"
                    else (
                        "AI-GENERATED / REQUIRES VERIFICATION"
                        if epoch_code == "T2"
                        else "BASELINE_CANDIDATE"
                    ),
                    "actor": f"Temporal Ingestion ({year_label})",
                    "change_summary": f"{epoch_code} ({year_label}): Land-use={props['land_use_class']}, Buildings={props['building_count']}, Area={props['area_sqm']:.1f} m²",
                    "geometry": feat["geometry"],
                }
            )

        for ep_from, ep_to, fa, fb in [("T0", "T1", f0, f1), ("T1", "T2", f1, f2)]:
            if not (fa and fb):
                continue
            pa, pb = fa["properties"], fb["properties"]
            if pb["building_count"] > pa["building_count"]:
                changes.append(
                    {
                        "id": f"{out_scene_id}_CHG_{seq:03d}",
                        "parcel_id": canonical_pid,
                        "from_epoch": ep_from,
                        "to_epoch": ep_to,
                        "change_type": "NEW_BUILDING",
                        "severity": "HIGH",
                        "confidence": 0.91,
                        "summary": f"New building footprint detected on parcel {canonical_pid} between {ep_from} ({pa['building_count']} bldgs) and {ep_to} ({pb['building_count']} bldgs).",
                        "metrics": {
                            "before_buildings": pa["building_count"],
                            "after_buildings": pb["building_count"],
                        },
                        "geometry": fb["geometry"],
                    }
                )
                seq += 1
            elif pb["building_count"] < pa["building_count"]:
                changes.append(
                    {
                        "id": f"{out_scene_id}_CHG_{seq:03d}",
                        "parcel_id": canonical_pid,
                        "from_epoch": ep_from,
                        "to_epoch": ep_to,
                        "change_type": "REMOVED_BUILDING",
                        "severity": "MEDIUM",
                        "confidence": 0.87,
                        "summary": f"Building demolition/removal detected on parcel {canonical_pid} between {ep_from} and {ep_to}.",
                        "metrics": {
                            "before_buildings": pa["building_count"],
                            "after_buildings": pb["building_count"],
                        },
                        "geometry": fb["geometry"],
                    }
                )
                seq += 1

            if pa["land_use_class"] != pb["land_use_class"]:
                changes.append(
                    {
                        "id": f"{out_scene_id}_CHG_{seq:03d}",
                        "parcel_id": canonical_pid,
                        "from_epoch": ep_from,
                        "to_epoch": ep_to,
                        "change_type": "LAND_USE_CHANGE",
                        "severity": "MEDIUM",
                        "confidence": 0.86,
                        "summary": f"Land-use transition on parcel {canonical_pid} from '{pa['land_use_class']}' ({ep_from}) to '{pb['land_use_class']}' ({ep_to}).",
                        "metrics": {
                            "from_class": pa["land_use_class"],
                            "to_class": pb["land_use_class"],
                        },
                        "geometry": fb["geometry"],
                    }
                )
                seq += 1

            area_a = float(pa.get("area_sqm", 0.0))
            area_b = float(pb.get("area_sqm", 0.0))
            if area_a > 0 and abs(area_b - area_a) / area_a > 0.08:
                changes.append(
                    {
                        "id": f"{out_scene_id}_CHG_{seq:03d}",
                        "parcel_id": canonical_pid,
                        "from_epoch": ep_from,
                        "to_epoch": ep_to,
                        "change_type": "BOUNDARY_SHIFT",
                        "severity": "HIGH",
                        "confidence": 0.88,
                        "summary": f"Boundary shift / area modification on parcel {canonical_pid} from {area_a:.1f} m² ({ep_from}) to {area_b:.1f} m² ({ep_to}).",
                        "metrics": {"before_area_sqm": area_a, "after_area_sqm": area_b},
                        "geometry": fb["geometry"],
                    }
                )
                seq += 1

    return {"changes": changes, "versions": versions}


def detect_temporal_changes(
    base_scene_prefix: str = "scene_urban",
    out_scene_id: str = "scene_urban_T1",
) -> Dict[str, Any]:
    """
    Compare temporal scenes T0 (2024), T1 (2025), and T2 (2026) in synthetic_data/temporal_demo.
    """
    t0_dir = SYNTHETIC_DATA_DIR / "temporal_demo" / f"{base_scene_prefix}_T0"
    t1_dir = SYNTHETIC_DATA_DIR / "temporal_demo" / f"{base_scene_prefix}_T1"
    t2_dir = SYNTHETIC_DATA_DIR / "temporal_demo" / f"{base_scene_prefix}_T2"

    if not (t0_dir.exists() and t1_dir.exists() and t2_dir.exists()):
        return {"changes": [], "versions": []}

    p_t0 = json.loads((t0_dir / "parcels.geojson").read_text(encoding="utf-8"))[
        "features"
    ]
    p_t1 = json.loads((t1_dir / "parcels.geojson").read_text(encoding="utf-8"))[
        "features"
    ]
    p_t2 = json.loads((t2_dir / "parcels.geojson").read_text(encoding="utf-8"))[
        "features"
    ]
    return compare_epoch_features(out_scene_id, p_t0, p_t1, p_t2)
