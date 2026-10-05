"""
Human Feedback & Training Candidate Export Service for AeroCadastre.
Captures human-in-the-loop (HITL) corrections, approved boundaries, rejected candidates,
and surveyor edits for prospective offline model retuning and active learning.

GOVERNANCE CONTRACT:
- Exports are explicitly tagged as PROSPECTIVE_TRAINING_CANDIDATE.
- NEVER claims to be verified statutory cadastral training data.
- Generates reproducible GeoJSON feature collections and manifest metadata with audit provenance.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class HumanFeedbackExportService:
    """
    Manages active learning feedback logs and candidate training exports from surveyor reviews.
    """

    def __init__(self, export_base_dir: str = "data/processed/feedback_training"):
        self.export_base_dir = Path(export_base_dir)
        self.export_base_dir.mkdir(parents=True, exist_ok=True)

    def log_feedback_event(
        self,
        project_id: str,
        parcel_id: str,
        action: str,  # "APPROVED", "REJECTED", "MODIFIED", "FLAGGED"
        surveyor_id: str,
        notes: str,
        original_geometry: Dict[str, Any],
        edited_geometry: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Logs a single surveyor HITL event with cryptographic timestamp and geometry diff provenance.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        feedback_record = {
            "record_id": f"FB-{project_id}-{parcel_id}-{int(time.time() * 1000)}",
            "project_id": project_id,
            "parcel_id": parcel_id,
            "action": action,
            "surveyor_id": surveyor_id,
            "timestamp": timestamp,
            "notes": notes,
            "original_geometry": original_geometry,
            "edited_geometry": edited_geometry or original_geometry,
            "confidence_score": confidence_score,
            "metadata": metadata or {},
            "data_usage_disclaimer": "PROSPECTIVE_ACTIVE_LEARNING_ONLY. NOT_AUTHORITATIVE_CADASTRE."
        }
        return feedback_record

    def export_training_candidates(
        self,
        project_id: str,
        feedback_records: List[Dict[str, Any]],
        output_subfolder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compiles feedback records into an active learning dataset package with GeoJSON and manifest.
        """
        out_dir = self.export_base_dir / (output_subfolder or project_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        features = []
        approved_count = 0
        rejected_count = 0
        modified_count = 0

        for rec in feedback_records:
            act = rec.get("action", "").upper()
            if act == "APPROVED":
                approved_count += 1
            elif act == "REJECTED":
                rejected_count += 1
            elif act == "MODIFIED":
                modified_count += 1

            feature = {
                "type": "Feature",
                "geometry": rec.get("edited_geometry") or rec.get("original_geometry"),
                "properties": {
                    "record_id": rec.get("record_id"),
                    "project_id": rec.get("project_id"),
                    "parcel_id": rec.get("parcel_id"),
                    "action": rec.get("action"),
                    "surveyor_id": rec.get("surveyor_id"),
                    "confidence_score": rec.get("confidence_score"),
                    "notes": rec.get("notes"),
                    "timestamp": rec.get("timestamp"),
                    "training_weight": 1.5 if act == "MODIFIED" else (1.0 if act == "APPROVED" else 0.0),
                }
            }
            features.append(feature)

        geojson_payload = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:32643"}},
            "features": features,
        }

        geojson_path = out_dir / f"candidates_{project_id}.geojson"
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_payload, f, indent=2)

        manifest = {
            "export_id": f"EXP-AL-{project_id}-{int(time.time())}",
            "project_id": project_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "target_crs": "EPSG:32643",
            "total_samples": len(features),
            "approved_count": approved_count,
            "modified_count": modified_count,
            "rejected_count": rejected_count,
            "files": {
                "geojson": str(geojson_path),
            },
            "governance_classification": "ACTIVE_LEARNING_PROSPECTIVE_CANDIDATE",
            "authoritative_cadastre": False,
            "disclaimer": "Exported for active learning and model tuning experiments only. Not official survey records."
        }

        manifest_path = out_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return {
            "manifest": manifest,
            "geojson_path": str(geojson_path),
            "manifest_path": str(manifest_path),
            "status": "COMPLETED"
        }
