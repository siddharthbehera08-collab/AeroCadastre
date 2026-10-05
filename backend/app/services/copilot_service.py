"""
Cadastral AI Copilot Service for AeroCadastre.
Provides grounded, deterministic, audit-safe explanations for surveyors and GIS analysts.

CRITICAL GOVERNANCE RULES:
1. NEVER fabricates land ownership, legal titles, deeds, or names of individuals.
2. NEVER fabricates official statutory ULPIN.
3. Explicitly quotes computed spatial evidence:
   - ResUNet building/road evidence presence and alignment.
   - Terrain slope, aspect, and elevation gradients.
   - Discrepancy flags (overlaps, gaps, slivers, boundary conflicts).
   - Multi-criteria Bayesian confidence score breakdown.
   - AI Council deliberation decisions.
4. Always includes statutory disclaimer:
   "Advisory AI assistance only. Inferred boundaries require ground verification by a licensed cadastral surveyor."
"""

from typing import Dict, Any, List, Optional


class CadastralCopilotService:
    """
    Deterministic explanations and conversational copilot for cadastral feature inspection.
    """

    STATUTORY_DISCLAIMER = (
        "ADVISORY AI ASSISTANCE ONLY. AeroCadastre outputs represent candidate boundaries "
        "inferred from multi-source remote sensing and terrain signals. They do NOT constitute "
        "statutory land titles, legal ownership records, or authorized cadastral maps. "
        "Final demarcation requires ground verification by a licensed authority under Indian law."
    )

    def explain_parcel(self, parcel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a structured, evidence-grounded explanation for a candidate parcel.
        """
        parcel_id = parcel_data.get("parcel_id", "UNKNOWN")
        confidence = parcel_data.get("confidence", 0.0)
        confidence_tier = parcel_data.get("confidence_tier", "LOW")
        evidence = parcel_data.get("evidence", {})
        anomalies = parcel_data.get("anomalies", [])
        status = parcel_data.get("verification_status", "PENDING")
        ulpin = parcel_data.get("ulpin", "NOT_ASSIGNED_PRE_CADASTRE")

        # Explain confidence drivers
        drivers = []
        if evidence.get("optical_building", 0.0) > 0.5:
            drivers.append("Strong building footprint support (Model A ResUNet)")
        if evidence.get("optical_road", 0.0) > 0.5:
            drivers.append("Bounded by detected road network corridor (Model B ResUNet)")
        if evidence.get("osm_reference", 0.0) > 0.5:
            drivers.append("Consistent with auxiliary OpenStreetMap reference geometry")
        if evidence.get("terrain_slope", 0.0) < 15.0:
            drivers.append("Favorable flat/moderate terrain gradient suitable for standard parcel geometry")

        # Explain risk / flag factors
        flags = []
        if anomalies:
            for a in anomalies:
                flags.append(f"Geometry anomaly detected: {a.get('type', 'ANOMALY')} ({a.get('description', '')})")
        if confidence < 0.6:
            flags.append("Low overall Bayesian confidence due to missing or weak multi-source evidence")

        # Formulate grounded textual explanation
        if flags:
            summary = (
                f"Candidate parcel {parcel_id} is flagged with {len(flags)} inspection issue(s). "
                f"Current confidence is {confidence:.2f} ({confidence_tier}). "
                f"Ground verification is strongly advised before boundary confirmation."
            )
        else:
            summary = (
                f"Candidate parcel {parcel_id} demonstrates high multi-modal alignment with confidence "
                f"score {confidence:.2f} ({confidence_tier}). Supported by {len(drivers)} corroborating signal(s)."
            )

        return {
            "parcel_id": parcel_id,
            "ulpin_status": "NOT_ASSIGNED_PRE_CADASTRE" if ulpin in ["NOT_ASSIGNED_PRE_CADASTRE", None] else ulpin,
            "verification_status": status,
            "confidence_score": confidence,
            "confidence_tier": confidence_tier,
            "summary": summary,
            "supporting_evidence": drivers,
            "risk_factors": flags,
            "recommended_action": (
                "SCHEDULE_FIELD_VISIT" if (confidence < 0.7 or len(flags) > 0) else "READY_FOR_OFFICE_REVIEW"
            ),
            "disclaimer": self.STATUTORY_DISCLAIMER,
        }

    def answer_query(self, query: str, parcel_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answers surveyor domain questions while strictly rejecting ownership or ULPIN queries.
        """
        q_lower = query.lower()

        # Governance safety check: ownership or legal title inquiries
        if any(term in q_lower for term in ["owner", "who owns", "proprietor", "patta", "title deed", "ownership"]):
            return {
                "query": query,
                "response": (
                    "AeroCadastre does NOT track, store, or infer land ownership, property titles, or individual identities. "
                    "Cadastral ownership records are legally maintained exclusively by state Revenue Departments "
                    "(e.g., Mahabhulekh / Bhulekh portals under the DILRMP framework)."
                ),
                "grounded": True,
                "disclaimer": self.STATUTORY_DISCLAIMER
            }

        # ULPIN inquiry check
        if "ulpin" in q_lower:
            return {
                "query": query,
                "response": (
                    "Official 14-digit Bhu-Aadhaar (ULPIN) identifiers can only be assigned by authorized Survey of India "
                    "or state cadastral authorities upon statutory demarcation. Candidate parcels generated by AeroCadastre "
                    "are assigned 'NOT_ASSIGNED_PRE_CADASTRE'."
                ),
                "grounded": True,
                "disclaimer": self.STATUTORY_DISCLAIMER
            }

        # Specific parcel inspection query
        if parcel_data:
            explanation = self.explain_parcel(parcel_data)
            return {
                "query": query,
                "response": explanation["summary"],
                "details": explanation,
                "grounded": True,
                "disclaimer": self.STATUTORY_DISCLAIMER
            }

        return {
            "query": query,
            "response": (
                "Cadastral Copilot is active. You can query parcel boundary evidence, anomaly reasons, "
                "Bayesian confidence breakdowns, and field inspection recommendations."
            ),
            "grounded": True,
            "disclaimer": self.STATUTORY_DISCLAIMER
        }
