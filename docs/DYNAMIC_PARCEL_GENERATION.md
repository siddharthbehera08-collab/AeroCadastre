# Dynamic Multi-Evidence AI Parcel Candidate Generation

## 1. System Architecture

AeroCadastre implements a production-grade, multi-evidence dynamic parcel synthesis pipeline that converts satellite and aerial imagery over arbitrary Areas of Interest (AOI) into topologically validated preliminary cadastral parcel candidates.

```
                         User Selects AOI on WebGIS
                                      │
                                      ▼
             High-Res Aerial / Pune Sentinel-2 Multispectral Imagery
                                      │
                 ┌────────────────────┼────────────────────┐
                 ▼                    ▼                    ▼
          Model A: Building     Model B: Road       Model C: Boundary
             Segmentation          Corridors           Lines
          (MicroResUNet /      (MicroUNet /       (MicroResUNet)
           Inria Champion)     SpaceNet Champion)
                 │                    │                    │
                 ▼                    ▼                    ▼
         Building Centroid      Right-of-Way        Visible Compound
          Structural Seeds       Exclusion           Walls & Ditches
                 │                    │                    │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                      Model D: 4-Class LULC Context
                        (Residential/Commercial/
                         Industrial/Agricultural)
                                      │
                                      ▼
              ================ MULTI-SOURCE FUSION ================
              1. Right-of-Way Corridor Exclusion (Subtract roads)
              2. Structural Seed Derivation (Building footprints)
              3. Constrained Voronoi Tessellation across usable land
              4. Polygon Cleaning & Metric Sliver Removal (< 25 m²)
              5. Metric Topology Validation (Overlaps, Gaps, Rings)
              6. Multi-Evidence & Confidence Scoring
              7. 6-Agent AI Council Deliberation (Advisory)
                                      │
                                      ▼
                   Preliminary Parcel Candidates (GeoJSON)
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
         PostGIS Persistence                      Next.js WebGIS View
      (`parcels` table, status:                - Interactive Vertex Editing
       "AI-GENERATED / REQUIRES                - Surveyor Verification
        VERIFICATION")                         - Statutory Disclaimers
```

---

## 2. Machine Learning Model Inventory & Roles

| Model | Architecture | Checkpoint | Input | Function |
|---|---|---|---|---|
| **Building Primary** | `Building_MicroResUNet_RGBD_v2` | `EXP_003` / `EXP_BUILDING_RESUNET_001_AerialInria.pt` | RGB (or RGB+nDSM) | Detects roof footprints. Serves as structural centroid property seeds. |
| **Road Primary** | `Road_MicroUNet_v1` | `EXP_004` / `EXP_ROAD_RESUNET_001_SpaceNetParis.pt` | 3-channel RGB | Extracts road corridors. Buffered to carve out public transportation rights-of-way. |
| **Boundary Primary** | `Boundary_MicroResUNet_v1` | `EXP_005` | 4-channel RGBD | Detects visible physical boundaries (walls, hedges, bunds). |
| **Land Use Primary** | `LandUse_MicroUNet` | `EXP_007` / `EXP_008` | RGB+nDSM | Predicts zonal land use (Residential, Commercial, Industrial, Agricultural). |

---

## 3. Reality Check & Scientific Rigor

1. **Did we generate parcel candidates from real imagery?**  
   **Yes.** The system was executed and validated directly on authentic Sentinel-2 multispectral imagery of Pune, Maharashtra (`pune_sentinel2_rgb.tif`) and real Inria European aerial orthophotography (`austin10_*.png`).
2. **Which real imagery was used?**  
   - Copernicus / Microsoft Planetary Computer Sentinel-2 L2A (`S2A_MSIL2A_20261002T053241_R105_T43QCA_20261002T101803`) over Pune Historic Urban Core (Kasba Peth).
   - Inria Aerial Image Labeling orthophotography (0.3m ground sample distance).
3. **Which models were actually executed?**  
   PyTorch ResUNet checkpoints for Building Footprint Extraction (`EXP_BUILDING_RESUNET_001`), Road Network Segmentation (`EXP_ROAD_RESUNET_001`), Visible Boundary Detection (`EXP_005`), and LULC Classification (`EXP_007`).
4. **Which evidence layers contributed?**  
   - Real Sentinel-2 optical reflectance bands (B02, B03, B04).
   - High-resolution building footprints (Inria / Pune OpenStreetMap 1,917 building vectors).
   - Road network right-of-ways (SpaceNet / Pune 413 road corridor vectors).
   - AI-predicted physical boundaries and LULC classifications.
5. **Were any synthetic parcels used in dynamic generation?**  
   **No.** Dynamic candidate parcels are synthesized on-the-fly from the requested AOI bounds.
6. **Were any values hardcoded?**  
   **No.** Coordinates, areas, perimeters, confidences, and geometries are computed geometrically from input data and neural outputs.
7. **What percentage of the pipeline is genuinely dynamic?**  
   **100% of the dynamic parcelling pipeline.** Bounding box -> Neural inference -> Voronoi synthesis -> Sliver removal -> Topology audit -> PostGIS persistence -> GeoJSON delivery.
8. **Are the resulting polygons legal cadastral boundaries?**  
   **Strictly NO.** They are labeled `AI-GENERATED / PRELIMINARY_CANDIDATE_GEOMETRY / REQUIRES_HUMAN_VERIFICATION`. Only statutory revenue ground surveys by licensed surveyors carry legal authority under Indian revenue acts (e.g. Maharashtra Land Revenue Code, 1966).
9. **What Indian data is still required for real cadastral validation?**  
   High-resolution drone orthophoto tiles (< 5 cm GSD, such as SVAMITVA / NAKSHA survey drone datasets) and digitized revenue village map records (7/12 extracts, toposheets).

---

## 4. API Specification

### Endpoint: `POST /api/parcels/generate-candidates`

#### Request Payload:
```json
{
  "aoi_bounds": [73.852, 18.515, 73.858, 18.522],
  "project_id": "PROJ_SIH26012_DEMO",
  "resolution": 0.5,
  "persist_to_postgis": true,
  "operator_id": "Surveyor_Verifier_01"
}
```

#### Response Structure:
```json
{
  "type": "FeatureCollection",
  "metadata": {
    "scene_id": "aoi_dyn_473516",
    "project_id": "PROJ_SIH26012_DEMO",
    "aoi_bounds": [73.852, 18.515, 73.858, 18.522],
    "candidate_parcel_count": 26,
    "buildings_detected": 1059,
    "road_corridors_excluded": 240,
    "mean_confidence": 0.439,
    "processing_time_ms": 476.98,
    "disclaimer": "AI-GENERATED PRELIMINARY CANDIDATE GEOMETRY... Ground verification mandatory."
  },
  "features": [
    {
      "type": "Feature",
      "id": "aoi_dyn_473516_P_001",
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "properties": {
        "id": "aoi_dyn_473516_P_001",
        "parcel_layer": "CANDIDATE",
        "boundary_representation": "INFERRED",
        "land_use_class": "residential",
        "area_sqm": 6396.72,
        "perimeter_m": 331.4,
        "building_count": 25,
        "road_access": true,
        "confidence": 0.4611,
        "confidence_category": "LOW",
        "topology_status": "VALID",
        "verification_status": "AI-GENERATED / REQUIRES VERIFICATION",
        "council_decision": "REQUIRES_VERIFICATION"
      }
    }
  ]
}
```
