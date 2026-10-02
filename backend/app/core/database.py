from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from backend.app.core.config import settings

Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_postgis_schema() -> None:
    """Ensure PostGIS extensions and all SQLAlchemy tables exist."""
    import backend.app.models.entities  # noqa: F401

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
        Base.metadata.create_all(bind=conn)


def verify_postgis_connection(db: Session) -> dict:
    """Verify live PostgreSQL and PostGIS extension availability."""
    pg_version = db.execute(text("SELECT version()")).scalar()
    postgis_version = db.execute(text("SELECT PostGIS_Version()")).scalar()
    postgis_full = db.execute(text("SELECT PostGIS_Full_Version()")).scalar()
    table_count = db.execute(
        text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    ).scalar()
    return {
        "postgresql_version": pg_version,
        "postgis_version": postgis_version,
        "postgis_full_version": postgis_full,
        "public_table_count": int(table_count or 0),
    }


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
