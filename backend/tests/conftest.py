import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal, init_postgis_schema
from backend.app.main import app
from backend.app.services.seed_service import ensure_demo_seed_data


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_postgis_schema()
    db = SessionLocal()
    try:
        ensure_demo_seed_data(db)
    finally:
        db.close()


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
