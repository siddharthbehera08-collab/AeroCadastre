import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import Polygon, LineString, mapping
from shapely.affinity import rotate
import rasterio
from rasterio.transform import from_bounds

from backend.config import SYNTHETIC_DATA_DIR, LAND_USE_CLASSES
from backend.db import compute_metric_area_perimeter

# Base coordinate anchor in India (near Bengaluru / urban survey test zone, EPSG:4326)
BASE_LON = 77.5920
BASE_LAT = 12.9720
SCENE_DEG_SPAN = 0.0024  # ~265m x 265m ground footprint

SCENE_ARCHETYPES = [
    "dense_urban_block",
    "irregular_settlement",
    "sparse_periurban",
    "mixed_commercial_corridor",
    "waterfront_agricultural_edge",
]

# Color palette for synthetic drone RGB rendering
PALETTE = {
    "vacant": (194, 178, 152),
    "residential_ground": (182, 168, 145),
    "commercial_ground": (168, 165, 162),
    "industrial_ground": (155, 158, 162),
    "agricultural": (142, 168, 104),
    "vegetation": (58, 118, 52),
    "water": (44, 98, 138),
    "road_main": (74, 76, 80),
    "road_lane": (98, 96, 92),
    "pathway": (136, 126, 110),
    "wall_visible": (222, 216, 204),
    "roof_terracotta": (176, 88, 66),
    "roof_concrete": (188, 192, 196),
    "roof_metal": (124, 142, 160),
    "roof_commercial": (145, 135, 128),
}


def pixel_to_lonlat(px: float, py: float, size: int, origin_lon: float, origin_lat: float) -> Tuple[float, float]:
    lon = origin_lon + (px / size) * SCENE_DEG_SPAN
    lat = origin_lat + ((size - py) / size) * SCENE_DEG_SPAN
    return round(lon, 7), round(lat, 7)


def poly_px_to_geo(coords_px: List[Tuple[float, float]], size: int, origin_lon: float, origin_lat: float) -> Polygon:
    pts = [pixel_to_lonlat(x, y, size, origin_lon, origin_lat) for x, y in coords_px]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def line_px_to_geo(coords_px: List[Tuple[float, float]], size: int, origin_lon: float, origin_lat: float) -> LineString:
    pts = [pixel_to_lonlat(x, y, size, origin_lon, origin_lat) for x, y in coords_px]
    return LineString(pts)


def generate_single_scene(
    scene_id: str,
    split: str,
    seed: int,
    size: int = 128,
    save_geotiff: bool = False,
    temporal_epoch: str = "T1",
    out_dir: Path = SYNTHETIC_DATA_DIR,
) -> Dict[str, Any]:
    """
    Deterministically generate a rich synthetic drone + cadastral scene.
    Produces:
      - rgb.png (and optional rgb.tif, dsm.tif, dtm.tif)
      - building_mask.png (0/1)
      - road_mask.png (0/1)
      - landuse_mask.png (0..9 class indices)
      - boundary_mask.png (0/1 visible boundary evidence)
      - dsm.npy (elevation in meters)
      - parcels.geojson (ground truth / reference parcels + candidate cues)
      - metadata.json (labeled SYNTHETIC DEMO DATA)
    """
    rng = np.random.default_rng(seed)
    archetype = SCENE_ARCHETYPES[seed % len(SCENE_ARCHETYPES)]

    scene_dir = out_dir / split / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)

    origin_lon = BASE_LON + ((seed % 15) * 0.003)
    origin_lat = BASE_LAT + (((seed // 15) % 15) * 0.003)

    # Initialize images & masks
    rgb_img = Image.new("RGB", (size, size), PALETTE["vacant"])
    rgb_draw = ImageDraw.Draw(rgb_img)

    building_mask = Image.new("L", (size, size), 0)
    bldg_draw = ImageDraw.Draw(building_mask)

    road_mask = Image.new("L", (size, size), 0)
    road_draw = ImageDraw.Draw(road_mask)

    landuse_mask = Image.new("L", (size, size), 7)  # 7 = vacant default
    lu_draw = ImageDraw.Draw(landuse_mask)

    boundary_mask = Image.new("L", (size, size), 0)
    bnd_draw = ImageDraw.Draw(boundary_mask)

    # Smooth terrain DTM (212m to 217m)
    yy, xx = np.mgrid[0:size, 0:size]
    dtm = (
        214.0
        + 1.8 * np.sin(xx / max(12.0, float(size) / 3.0) + (seed % 5))
        + 1.4 * np.cos(yy / max(12.0, float(size) / 3.0) + (seed % 7))
    ).astype(np.float32)
    dsm = dtm.copy()

    # 1. Determine road network layout (Main arterial road + cross lane + access pathway)
    horiz_y = int(rng.integers(int(size * 0.36), int(size * 0.64)))
    vert_x = int(rng.integers(int(size * 0.36), int(size * 0.64)))
    main_w = int(rng.integers(7, 12)) if archetype != "irregular_settlement" else int(rng.integers(5, 8))
    lane_w = int(rng.integers(4, 7))
    path_w = 3

    roads_features = []
    parcels_features = []
    ref_parcels_features = []
    buildings_features = []
    boundaries_features = []

    # Define quadrants separated by the primary road and secondary lane
    quadrants = [
        (3, 3, vert_x - lane_w // 2 - 2, horiz_y - main_w // 2 - 2),
        (vert_x + lane_w // 2 + 2, 3, size - 4, horiz_y - main_w // 2 - 2),
        (3, horiz_y + main_w // 2 + 2, vert_x - lane_w // 2 - 2, size - 4),
        (vert_x + lane_w // 2 + 2, horiz_y + main_w // 2 + 2, size - 4, size - 4),
    ]

    parcel_idx = 1
    bldg_idx = 1
    bnd_idx = 1

    for q_idx, (qx1, qy1, qx2, qy2) in enumerate(quadrants):
        qw = qx2 - qx1
        qh = qy2 - qy1
        if qw < 16 or qh < 16:
            continue

        # Subdivide quadrant into 2 to 4 parcels (regular or irregular)
        nx = 2 if qw > 34 else 1
        ny = 2 if qh > 34 else 1
        dx = qw / nx
        dy = qh / ny

        for ix in range(nx):
            for iy in range(ny):
                px1 = qx1 + ix * dx
                py1 = qy1 + iy * dy
                px2 = px1 + dx
                py2 = py1 + dy

                # Add irregular perturbation for irregular_settlement or specific seeds
                jitter = 3.5 if archetype == "irregular_settlement" else 1.2
                c1 = (px1 + rng.uniform(0, jitter), py1 + rng.uniform(0, jitter))
                c2 = (px2 - rng.uniform(0, jitter), py1 + rng.uniform(0, jitter))
                c3 = (px2 - rng.uniform(0, jitter), py2 - rng.uniform(0, jitter))
                c4 = (px1 + rng.uniform(0, jitter), py2 - rng.uniform(0, jitter))
                parcel_px_pts = [c1, c2, c3, c4]

                # Choose land-use class based on archetype and quadrant
                if archetype == "waterfront_agricultural_edge" and q_idx == 3 and iy == ny - 1:
                    lu_name = "water" if ix == 0 else "agricultural"
                elif archetype == "mixed_commercial_corridor" and iy == 0:
                    lu_name = "commercial" if (ix + q_idx) % 2 == 0 else "mixed_use"
                elif archetype == "sparse_periurban" and (ix + iy + q_idx) % 3 == 0:
                    lu_name = "vegetation"
                else:
                    lu_choices = ["residential", "residential", "commercial", "mixed_use", "vegetation", "vacant", "industrial"]
                    lu_name = lu_choices[(seed + q_idx * 3 + ix + iy) % len(lu_choices)]

                # Temporal evolution for T0 / T1 / T2
                if temporal_epoch == "T0" and parcel_idx in (3, 7):
                    lu_name = "vacant"
                elif temporal_epoch == "T2" and parcel_idx == 5:
                    lu_name = "commercial"

                lu_cls_idx = LAND_USE_CLASSES.index(lu_name)

                # Fill parcel ground color and land-use mask
                ground_col = PALETTE.get(f"{lu_name}_ground", PALETTE.get(lu_name, PALETTE["vacant"]))
                rgb_draw.polygon(parcel_px_pts, fill=ground_col)
                lu_draw.polygon(parcel_px_pts, fill=lu_cls_idx)

                # Determine visible vs inferred boundary edges
                edges = [(c1, c2), (c2, c3), (c3, c4), (c4, c1)]
                visible_edge_count = 0
                for e_i, (p_start, p_end) in enumerate(edges):
                    is_visible = bool(rng.random() > 0.28)
                    if is_visible:
                        visible_edge_count += 1
                        rgb_draw.line([p_start, p_end], fill=PALETTE["wall_visible"], width=1)
                        bnd_draw.line([p_start, p_end], fill=1, width=2)
                    bnd_geo = line_px_to_geo([p_start, p_end], size, origin_lon, origin_lat)
                    _, bnd_len = compute_metric_area_perimeter(bnd_geo)
                    boundaries_features.append({
                        "type": "Feature",
                        "properties": {
                            "id": f"{scene_id}_BND_{bnd_idx:03d}",
                            "parcel_id": f"{scene_id}_P_{parcel_idx:03d}",
                            "boundary_type": "VISIBLE" if is_visible else "INFERRED",
                            "confidence": round(float(rng.uniform(0.82, 0.96) if is_visible else rng.uniform(0.61, 0.79)), 3),
                            "length_m": bnd_len,
                            "evidence_sources": ["Drone_RGB_Edge", "DSM_Breakline"] if is_visible else ["Road_Corridor_Offset", "Adjacent_Parcel_Topology"],
                        },
                        "geometry": mapping(bnd_geo),
                    })
                    bnd_idx += 1

                # Reference GIS polygon (slightly shifted on some parcels to test GIS Conflict Detection)
                ref_shift_px = 2.2 if (parcel_idx % 4 == 0) else 0.3
                ref_pts = [(x + ref_shift_px, y - ref_shift_px * 0.5) for (x, y) in parcel_px_pts]
                ref_poly_geo = poly_px_to_geo(ref_pts, size, origin_lon, origin_lat)
                ref_area, ref_perim = compute_metric_area_perimeter(ref_poly_geo)
                ref_parcels_features.append({
                    "type": "Feature",
                    "properties": {
                        "id": f"{scene_id}_REF_{parcel_idx:03d}",
                        "parcel_id": f"{scene_id}_P_{parcel_idx:03d}",
                        "parcel_layer": "REFERENCE",
                        "boundary_representation": "REFERENCE",
                        "land_use_class": lu_name,
                        "area_sqm": ref_area,
                        "perimeter_m": ref_perim,
                        "source": "Synthetic Legacy Cadastral Map (Non-Authoritative Demo)",
                    },
                    "geometry": mapping(ref_poly_geo),
                })

                # Place 1 or 2 buildings inside residential/commercial/industrial/mixed_use parcels
                bldg_count_in_parcel = 0
                if lu_name in ("residential", "commercial", "industrial", "mixed_use"):
                    num_bldgs = 2 if (dx > 26 and dy > 26 and archetype == "dense_urban_block") else 1
                    if temporal_epoch == "T0" and parcel_idx in (2, 6):
                        num_bldgs = 0  # Building constructed later in T1/T2!
                    elif temporal_epoch == "T2" and parcel_idx == 4:
                        num_bldgs = 2  # Extra building added in T2!

                    for b_sub in range(num_bldgs):
                        margin_x = max(3.0, dx * 0.18)
                        margin_y = max(3.0, dy * 0.18)
                        bx1 = px1 + margin_x + (b_sub * dx * 0.35 if num_bldgs > 1 else 0)
                        by1 = py1 + margin_y
                        bx2 = min(px2 - margin_x, bx1 + dx * (0.38 if num_bldgs > 1 else 0.58))
                        by2 = py2 - margin_y

                        # Intentionally create a building crossing parcel boundary on parcel 3 for anomaly detection!
                        if parcel_idx == 3 and b_sub == 0:
                            bx2 = px2 + 2.5

                        if bx2 - bx1 >= 5.0 and by2 - by1 >= 5.0:
                            b_pts = [(bx1, by1), (bx2, by1), (bx2, by2), (bx1, by2)]
                            roof_palette = [
                                PALETTE["roof_terracotta"],
                                PALETTE["roof_concrete"],
                                PALETTE["roof_metal"],
                                PALETTE["roof_commercial"],
                            ]
                            roof_col = roof_palette[(seed + parcel_idx + b_sub) % len(roof_palette)]
                            # Draw building shadow
                            shadow_pts = [(x + 1.5, y + 1.5) for (x, y) in b_pts]
                            rgb_draw.polygon(shadow_pts, fill=(45, 45, 48))
                            # Draw building roof
                            rgb_draw.polygon(b_pts, fill=roof_col, outline=(90, 85, 80))
                            bldg_draw.polygon(b_pts, fill=1)

                            # Elevate DSM for building height (+4m to +12m)
                            ix1, iy1 = max(0, int(bx1)), max(0, int(by1))
                            ix2, iy2 = min(size, int(bx2)), min(size, int(by2))
                            bldg_height = float(rng.uniform(4.5, 11.5))
                            dsm[iy1:iy2, ix1:ix2] += bldg_height

                            b_geo = poly_px_to_geo(b_pts, size, origin_lon, origin_lat)
                            b_area, b_perim = compute_metric_area_perimeter(b_geo)
                            c_lon, c_lat = b_geo.centroid.x, b_geo.centroid.y
                            buildings_features.append({
                                "type": "Feature",
                                "properties": {
                                    "id": f"{scene_id}_BLDG_{bldg_idx:03d}",
                                    "parcel_id": f"{scene_id}_P_{parcel_idx:03d}",
                                    "area_sqm": b_area,
                                    "perimeter_m": b_perim,
                                    "centroid_lon": round(c_lon, 7),
                                    "centroid_lat": round(c_lat, 7),
                                    "height_m": round(bldg_height, 2),
                                    "confidence": round(float(rng.uniform(0.78, 0.96)), 3),
                                    "temporal_epoch": temporal_epoch,
                                },
                                "geometry": mapping(b_geo),
                            })
                            bldg_idx += 1
                            bldg_count_in_parcel += 1

                # Add vegetation canopy / occlusion patches
                if lu_name == "vegetation" or rng.random() < 0.25:
                    tx = float(rng.uniform(px1 + 3, px2 - 3))
                    ty = float(rng.uniform(py1 + 3, py2 - 3))
                    tr = float(rng.uniform(2.5, 5.0))
                    tree_box = [tx - tr, ty - tr, tx + tr, ty + tr]
                    rgb_draw.ellipse(tree_box, fill=PALETTE["vegetation"])
                    if lu_name == "vegetation":
                        lu_draw.ellipse(tree_box, fill=LAND_USE_CLASSES.index("vegetation"))
                    iy1, ix1 = max(0, int(ty - tr)), max(0, int(tx - tr))
                    iy2, ix2 = min(size, int(ty + tr)), min(size, int(tx + tr))
                    dsm[iy1:iy2, ix1:ix2] += 3.5

                parcel_poly_geo = poly_px_to_geo(parcel_px_pts, size, origin_lon, origin_lat)
                p_area, p_perim = compute_metric_area_perimeter(parcel_poly_geo)
                parcels_features.append({
                    "type": "Feature",
                    "properties": {
                        "id": f"{scene_id}_P_{parcel_idx:03d}",
                        "parcel_layer": "CANDIDATE",
                        "boundary_representation": "VISIBLE" if visible_edge_count >= 3 else "INFERRED",
                        "land_use_class": lu_name,
                        "area_sqm": p_area,
                        "perimeter_m": p_perim,
                        "building_count": bldg_count_in_parcel,
                        "visible_edges": visible_edge_count,
                        "temporal_epoch": temporal_epoch,
                        "data_label": "SYNTHETIC DEMO DATA",
                    },
                    "geometry": mapping(parcel_poly_geo),
                })
                parcel_idx += 1

    # 2. Draw primary & secondary roads on RGB, road_mask, and landuse_mask
    road_cls_idx = LAND_USE_CLASSES.index("road")
    # Horizontal main road
    h_box = [0, horiz_y - main_w // 2, size - 1, horiz_y + main_w // 2]
    rgb_draw.rectangle(h_box, fill=PALETTE["road_main"])
    road_draw.rectangle(h_box, fill=1)
    lu_draw.rectangle(h_box, fill=road_cls_idx)

    h_line_geo = line_px_to_geo([(0, horiz_y), (size - 1, horiz_y)], size, origin_lon, origin_lat)
    _, h_len = compute_metric_area_perimeter(h_line_geo)
    roads_features.append({
        "type": "Feature",
        "properties": {
            "id": f"{scene_id}_RD_001",
            "road_class": "MAIN_ROAD",
            "width_m": round(main_w * 0.5, 2),
            "length_m": h_len,
            "confidence": 0.94,
        },
        "geometry": mapping(h_line_geo),
    })

    # Vertical cross lane
    v_box = [vert_x - lane_w // 2, 0, vert_x + lane_w // 2, size - 1]
    rgb_draw.rectangle(v_box, fill=PALETTE["road_lane"])
    road_draw.rectangle(v_box, fill=1)
    lu_draw.rectangle(v_box, fill=road_cls_idx)

    v_line_geo = line_px_to_geo([(vert_x, 0), (vert_x, size - 1)], size, origin_lon, origin_lat)
    _, v_len = compute_metric_area_perimeter(v_line_geo)
    roads_features.append({
        "type": "Feature",
        "properties": {
            "id": f"{scene_id}_RD_002",
            "road_class": "NARROW_LANE",
            "width_m": round(lane_w * 0.5, 2),
            "length_m": v_len,
            "confidence": 0.89,
        },
        "geometry": mapping(v_line_geo),
    })

    # Add realistic drone sensor grain / slight atmospheric blur
    rgb_arr = np.array(rgb_img, dtype=np.float32)
    noise = rng.normal(0.0, 4.5, size=rgb_arr.shape).astype(np.float32)
    rgb_arr = np.clip(rgb_arr + noise, 0, 255).astype(np.uint8)
    rgb_img = Image.fromarray(rgb_arr)

    # Save PNG masks and RGB
    rgb_path = scene_dir / "rgb.png"
    bldg_mask_path = scene_dir / "building_mask.png"
    road_mask_path = scene_dir / "road_mask.png"
    lu_mask_path = scene_dir / "landuse_mask.png"
    bnd_mask_path = scene_dir / "boundary_mask.png"
    dsm_npy_path = scene_dir / "dsm.npy"

    rgb_img.save(rgb_path)
    building_mask.save(bldg_mask_path)
    road_mask.save(road_mask_path)
    landuse_mask.save(lu_mask_path)
    boundary_mask.save(bnd_mask_path)
    np.save(dsm_npy_path, dsm)

    bounds_poly = poly_px_to_geo([(0, 0), (size, 0), (size, size), (0, size)], size, origin_lon, origin_lat)

    # Optional GeoTIFF export for raster ingestion & GIS testing
    if save_geotiff:
        minx, miny, maxx, maxy = bounds_poly.bounds
        transform = from_bounds(minx, miny, maxx, maxy, size, size)
        rgb_tif_path = scene_dir / "rgb.tif"
        with rasterio.open(
            rgb_tif_path,
            "w",
            driver="GTiff",
            height=size,
            width=size,
            count=3,
            dtype=rgb_arr.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            for band_i in range(3):
                dst.write(rgb_arr[:, :, band_i], band_i + 1)

        dsm_tif_path = scene_dir / "dsm.tif"
        with rasterio.open(
            dsm_tif_path,
            "w",
            driver="GTiff",
            height=size,
            width=size,
            count=1,
            dtype=dsm.dtype,
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(dsm, 1)

    # Save GeoJSON vector files
    parcels_fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": parcels_features}
    ref_parcels_fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": ref_parcels_features}
    buildings_fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": buildings_features}
    roads_fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": roads_features}
    boundaries_fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": boundaries_features}

    (scene_dir / "parcels.geojson").write_text(json.dumps(parcels_fc, indent=2), encoding="utf-8")
    (scene_dir / "reference_parcels.geojson").write_text(json.dumps(ref_parcels_fc, indent=2), encoding="utf-8")
    (scene_dir / "buildings.geojson").write_text(json.dumps(buildings_fc, indent=2), encoding="utf-8")
    (scene_dir / "roads.geojson").write_text(json.dumps(roads_fc, indent=2), encoding="utf-8")
    (scene_dir / "boundaries.geojson").write_text(json.dumps(boundaries_fc, indent=2), encoding="utf-8")

    metadata = {
        "scene_id": scene_id,
        "split": split,
        "seed": seed,
        "archetype": archetype,
        "temporal_epoch": temporal_epoch,
        "data_label": "SYNTHETIC DEMO DATA",
        "legal_disclaimer": "PRELIMINARY / CANDIDATE GEOMETRY - NOT LEGALLY AUTHORITATIVE LAND RECORDS",
        "crs": "EPSG:4326",
        "projected_crs": "EPSG:32643",
        "image_size": [size, size],
        "pixel_resolution_m": 0.5,
        "origin_lonlat": [origin_lon, origin_lat],
        "bounds_geojson": mapping(bounds_poly),
        "counts": {
            "parcels": len(parcels_features),
            "reference_parcels": len(ref_parcels_features),
            "buildings": len(buildings_features),
            "roads": len(roads_features),
            "boundaries": len(boundaries_features),
        },
        "dsm_stats": {
            "min_m": round(float(dsm.min()), 2),
            "max_m": round(float(dsm.max()), 2),
            "mean_m": round(float(dsm.mean()), 2),
        },
    }
    (scene_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def generate_full_synthetic_dataset(
    num_train: int = 100,
    num_val: int = 20,
    num_test: int = 20,
    size: int = 128,
    out_dir: Path = SYNTHETIC_DATA_DIR,
) -> Dict[str, Any]:
    """Generate the complete 100 train / 20 val / 20 test dataset + multi-temporal hero scenes."""
    manifest = {
        "dataset_name": "SIH26012_SYNTHETIC_DEMO_V1",
        "data_label": "SYNTHETIC DEMO DATA",
        "image_size": size,
        "splits": {"train": [], "val": [], "test": [], "temporal_demo": []},
    }

    for i in range(num_train):
        meta = generate_single_scene(f"train_{i:03d}", "train", seed=1000 + i, size=size, save_geotiff=(i == 0), out_dir=out_dir)
        manifest["splits"]["train"].append(meta["scene_id"])

    for i in range(num_val):
        meta = generate_single_scene(f"val_{i:03d}", "val", seed=2000 + i, size=size, save_geotiff=(i == 0), out_dir=out_dir)
        manifest["splits"]["val"].append(meta["scene_id"])

    for i in range(num_test):
        meta = generate_single_scene(f"test_{i:03d}", "test", seed=3000 + i, size=size, save_geotiff=(i < 2), out_dir=out_dir)
        manifest["splits"]["test"].append(meta["scene_id"])

    # Generate multi-temporal scenes (T0=2024, T1=2025, T2=2026) with identical spatial seed for Change Detection & Time Machine
    for epoch in ["T0", "T1", "T2"]:
        meta = generate_single_scene(
            f"scene_urban_{epoch}",
            "temporal_demo",
            seed=4042,
            size=size,
            save_geotiff=True,
            temporal_epoch=epoch,
            out_dir=out_dir,
        )
        manifest["splits"]["temporal_demo"].append(meta["scene_id"])

    manifest_path = out_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    res = generate_full_synthetic_dataset()
    print(
        f"Generated synthetic dataset: train={len(res['splits']['train'])}, "
        f"val={len(res['splits']['val'])}, test={len(res['splits']['test'])}, "
        f"temporal={len(res['splits']['temporal_demo'])}"
    )
