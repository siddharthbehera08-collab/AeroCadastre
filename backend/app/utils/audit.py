import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import AuditLog


def record_audit_log(
    db: Session,
    project_id: str,
    actor: str,
    operation: str,
    target_id: str,
    source: str = "AeroCadastre Backend API",
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    model_name: Optional[str] = None,
    confidence: Optional[float] = None,
) -> AuditLog:
    ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    log_entry = AuditLog(
        id=f"AUD_{operation[:12]}_{ts_ms}_{target_id[-8:]}",
        project_id=project_id,
        actor=actor,
        operation=operation,
        target_id=target_id,
        old_value_json=(
            json.dumps(old_value)
            if isinstance(old_value, (dict, list))
            else (str(old_value) if old_value is not None else None)
        ),
        new_value_json=(
            json.dumps(new_value)
            if isinstance(new_value, (dict, list))
            else (str(new_value) if new_value is not None else None)
        ),
        source=source,
        model_name=model_name,
        confidence=confidence,
    )
    db.add(log_entry)
    return log_entry
