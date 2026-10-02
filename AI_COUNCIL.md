# SIH26012 — AeroCadastre: Multi-Agent AI Council (`AI_COUNCIL.md`)

## 1. Domain-Specialized Council Architecture (`backend/council/agents.py`)

Rather than a generic conversational wrapper, the **AI Council** consists of 6 specialized analytical agents that inspect quantitative evidence domains for every candidate parcel:

1. **`VISION_AGENT`:** Evaluates visible boundary edge ratio (`visible_edges / 4`), boundary neural probability (`Boundary_MicroResUNet_v1`), and building edge probability.
2. **`GEOMETRY_AGENT`:** Evaluates metric area ($m^2$), perimeter ($m$), Polsby-Popper compactness, and topology validation status (`VALID`, `OVERLAP`, `GAP_ADJACENT`, `SELF_INTERSECTION`, `SLIVER_WARNING`).
3. **`GIS_AGENT`:** Evaluates spatial IoU against the Legacy Reference GIS layer, road corridor access adjacency, and CRS consistency.
4. **`ML_AGENT`:** Evaluates neural model confidence (`Building_MicroResUNet_RGBD_v2`, `LandUse_MicroResUNet_Weighted_v2`) and inter-model consensus (`1.0 - |P_ResUNet - P_UNet|`).
5. **`ANOMALY_AGENT`:** Evaluates spatial anomalies (`BUILDING_CROSSING_BOUNDARY`, `EXTREME_AREA`, `UNUSUAL_SHAPE`, `MODEL_DISAGREEMENT`) and temporal changes (`T0 → T2`).
6. **`FIELD_VERIFICATION_AGENT`:** Computes the **AI-Assisted Field Verification Priority** (`HIGH`, `MEDIUM`, `LOW`) and numerical `priority_score` with human-readable field inspection instructions.

## 2. Council Fusion Engine Formula

$$\text{Final Evidence Score} = 0.26 \cdot S_{\text{Vision}} + 0.22 \cdot S_{\text{Geometry}} + 0.20 \cdot S_{\text{GIS}} + 0.22 \cdot S_{\text{ML}} + 0.10 \cdot (1 - R_{\text{Anomaly}})$$

Outputs one of five advisory actions:
- `ACCEPT_FOR_REVIEW`
- `REQUIRES_VERIFICATION`
- `LOW_CONFIDENCE`
- `GEOMETRY_ERROR`
- `CONFLICT_DETECTED`
