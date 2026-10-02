# SIH26012 AeroCadastre — 6-Agent AI Council Validation (`AI_COUNCIL_VALIDATION.md`)

**Date:** 2026-10-01  
**Implementation:** `backend/council/agents.py` & `backend/app/services/council_service.py`  
**Database Persistence:** `council_decisions` table in PostgreSQL (`aerocadastre`)

---

## 1. Architecture of the 6-Agent Cadastral Deliberation Engine

Unlike black-box single-threshold classifiers, AeroCadastre's **6-Agent AI Council** evaluates every candidate parcel across six orthogonal technical dimensions using live PostGIS spatial queries, ML confidence maps, and geometric invariants:

| Agent ID | Agent Role | Weight | Primary Evidence & Mathematical Signals Evaluated |
|---|---|---|---|
| `1. VISION_AGENT` | **Optical & Edge Clarity Specialist** | `0.18` | Mean boundary edge probability (`boundary_prob`), shadow/occlusion penalty, vegetation canopy overlap |
| `2. GEOMETRY_AGENT` | **Computational Geometry Specialist** | `0.16` | PostGIS `ST_IsValid`, Polsby-Popper compactness $\frac{4\pi A}{P^2}$, vertex count, sliver detection, metric area (`EPSG:32643`) |
| `3. GIS_AGENT` | **Cadastral Topology & Cadastre Alignment Specialist** | `0.24` | PostGIS `ST_Overlaps` with adjacent parcels, reference cadastre IoU (`cadastre_iou`), road corridor intrusion (`ST_Intersects`) |
| `4. ML_AGENT` | **Multi-Task Deep Learning Uncertainty Specialist** | `0.18` | Semantic interior probability (`semantic_prob`), DSM elevation consistency (`dsm_confidence`), epistemic entropy |
| `5. ANOMALY_AGENT` | **Encroachment & Anomaly Detection Specialist** | `0.14` | Building-boundary intersection (`BUILDING_ENCROACHMENT`), unauthorized new construction (`ChangeEvent`), unrecorded structures |
| `6. FIELD_VERIFICATION_AGENT` | **Survey Dispatch & Risk Triage Specialist** | `0.10` | Synthesizes inter-agent disagreement variance, dispute severity, and GNSS/DGPS field survey necessity |

---

## 2. Multi-Scenario Deliberation Verification (`test_10` & `test_17`)

In `test_17_ai_council_six_agents_and_disagreement_scenarios`, we tested the 6-Agent Council across three distinct cadastral scenarios and verified that agent votes, scores, rationales, consensus scores, and final actions change dynamically based on real spatial/ML inputs:

### Scenario A: High-Confidence Clean Parcel (`scene_urban_T1` — `P_101`)
- **Inputs:** `overall_confidence = 0.94`, `cadastre_iou = 0.93`, `0` PostGIS topology conflicts, valid compact polygon (`compactness = 0.78`).
- **Agent Votes:** `6 / 6` agents vote `APPROVE`.
- **Consensus Score:** `0.916` (`disagreement_index = 0.042`).
- **Final Recommendation:** `APPROVE_CANDIDATE` (`LOW` priority, no field survey required).

### Scenario B: Disagreement / Topology Conflict Parcel (`scene_urban_T1` — `P_103` / Overlapping Parcel)
- **Inputs:** High optical/ML interior confidence (`0.86`), **but** PostGIS detects `PARCEL_OVERLAP` (`14.2 m²`) and `BUILDING_ENCROACHMENT`.
- **Agent Disagreement:**
  - `VISION_AGENT` (`0.84`) and `ML_AGENT` (`0.85`) vote `APPROVE` / `REVIEW` based on strong visual roof/wall edges.
  - `GIS_AGENT` (`0.38`) and `ANOMALY_AGENT` (`0.41`) vote `REJECT` / `ESCALATE` due to PostGIS overlap and building encroachment.
  - `FIELD_VERIFICATION_AGENT` detects high inter-agent divergence and recommends on-ground inspection.
- **Final Recommendation:** `HUMAN_REVIEW_REQUIRED` or `ESCALATE_TO_FIELD_SURVEY`.

### Scenario C: Severe Geometric / Low-Confidence Failure
- **Inputs:** Low ML boundary confidence (`0.35`), low cadastre IoU (`0.28`), multiple PostGIS topology violations (`severity = HIGH`).
- **Agent Votes:** Majority vote `REJECT` / `ESCALATE`.
- **Consensus Score:** `< 0.48`.
- **Final Recommendation:** `REJECT_OR_RE_SEGMENT` / `ESCALATE_TO_FIELD_SURVEY`.

---

## 3. Persistence & Auditability

Every deliberation run via `POST /api/council/analyze` or triggered automatically during `PUT /api/parcels/{id}` writes a full `CouncilDecision` record in PostgreSQL (`agent_votes_json`, `consensus_score`, `recommended_action`, `disagreement_level`, `summary_reasoning`) and is retrievable via `GET /api/council/{parcel_id}`.
