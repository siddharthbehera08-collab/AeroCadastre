"""Initial PostGIS spatial schema for SIH26012 AeroCadastre

Revision ID: 0001_initial_postgis
Revises: None
Create Date: 2026-10-01 00:50:00

Creates all 15 required core tables + 7 supporting spatial tables with
native PostGIS Geometry(GEOMETRY, 4326) columns and GIST spatial indexes:
  Core tables:
    1. users
    2. projects
    3. datasets
    4. parcels
    5. buildings
    6. roads
    7. land_use
    8. ai_predictions
    9. model_runs
   10. council_decisions
   11. topology_issues
   12. verification_records
   13. change_events
   14. field_tasks
   15. audit_logs
  Supporting tables:
   16. rasters
   17. boundaries
   18. anomalies
   19. field_routes
   20. feature_versions
   21. evidence
   22. human_feedback
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.app.core.database import Base
import backend.app.models.entities  # noqa: F401

revision: str = "0001_initial_postgis"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
