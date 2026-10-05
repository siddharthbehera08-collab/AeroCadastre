# AeroCadastre SIH26012 — Final AI Council Validation Report

**Date:** 2026-10-04  
**Project Root:** `D:\SIH26012_AeroCadastre`  
**Architecture:** Autonomous Multi-Agent Adjudication across 6 Domain Expert Agents

---

## 1. Domain Specialist Agents Architecture

The AI Council adjudicates every candidate parcel by evaluating multi-modal evidence without opaque black-box voting:

1. **Vision Specialist Agent:** Analyzes optical boundary contrast, building edge alignment, and image sharpness.
2. **Geometry Specialist Agent:** Evaluates planar topology, Polsby-Popper compactness, and vertex density.
3. **GIS Reference Specialist Agent:** Assesses setbacks against reference roads and adjacent municipal footprints.
4. **Historical Cadastre Specialist Agent:** Reviews prior temporal survey records and parcel change logs.
5. **ML Uncertainty Specialist Agent:** Quantifies prediction variance, neural ensemble disagreement, and epistemic uncertainty.
6. **Anomaly & Risk Specialist Agent:** Integrates Isolation Forest footprint anomaly scores and GIS encroachment severity.

---

## 2. Canonical Adjudication Scenarios Validation

Evaluated via `scripts/run_council_scenarios.py`:

| Scenario ID | Dispute / Scenario Context | Council Decision | Field Priority | Overall Confidence | Primary Advisory Reason |
|---|---|---|---|---|---|
| **Scenario 1** | Routine Concordant Evidence | `ACCEPT_FOR_REVIEW` | LOW | 0.920 (HIGH) | Routine human surveyor sign-off required for candidate parcel |
| **Scenario 2** | Road Encroachment Conflict | `CONFLICT_DETECTED` | HIGH | 0.778 (MEDIUM) | Reference GIS mismatch: ROAD_ENCROACHMENT |
| **Scenario 3** | Degraded / Occluded Imagery | `REQUIRES_VERIFICATION`| MEDIUM | 0.684 (MEDIUM) | Inferred boundaries (3 occluded/unmarked edges) |
| **Scenario 4** | Planar Topology Self-Intersection | `GEOMETRY_ERROR` | HIGH | 0.786 (MEDIUM) | Topology issue: SELF_INTERSECTION |
| **Scenario 5** | Morphological Sliver Outlier | `REQUIRES_VERIFICATION`| HIGH | 0.680 (MEDIUM) | Spatial anomaly: SLIVER_POLYGON |
| **Scenario 6** | Neural Head Disagreement | `REQUIRES_VERIFICATION`| MEDIUM | 0.776 (MEDIUM) | Inter-model variance across vision backbones |
| **Scenario 7** | Temporal Parcel Change Event | `REQUIRES_VERIFICATION`| MEDIUM | 0.843 (HIGH) | Temporal change detected across survey timestamps |

---

## 3. Advisory Language Mandate

The AI Council strictly outputs advisory recommendations:
- Council decisions are labeled as `PROPOSED_DECISION` or `RECOMMENDED_ACTION`.
- The system never asserts statutory authority or issues finalized deeds.
- Every decision requires human-in-the-loop verification by a licensed surveyor.
