from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import (
    routes_analysis,
    routes_auth,
    routes_buildings_roads,
    routes_council,
    routes_exports,
    routes_gis,
    routes_health,
    routes_legacy,
    routes_parcels,
    routes_projects,
    routes_verification,
)
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, init_postgis_schema
from backend.app.services.seed_service import ensure_demo_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_postgis_schema()
    db = SessionLocal()
    try:
        ensure_demo_seed_data(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production-grade GeoAI Cadastral Intelligence Backend powered by "
            "FastAPI, PostgreSQL 16, PostGIS 3.6, SQLAlchemy 2.0, GeoAlchemy2, and Alembic."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_projects.router)
    app.include_router(routes_parcels.router)
    app.include_router(routes_buildings_roads.router)
    app.include_router(routes_verification.router)
    app.include_router(routes_gis.router)
    app.include_router(routes_analysis.router)
    app.include_router(routes_council.router)
    app.include_router(routes_exports.router)
    app.include_router(routes_legacy.router)

    return app


app = create_app()
