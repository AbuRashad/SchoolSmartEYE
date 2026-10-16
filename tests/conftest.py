import pytest

from app.db import init_db
from app.db import session as db_session
from app.db.base import Base


@pytest.fixture(autouse=True)
def _test_database():
    """Give every test a fresh, isolated in-memory SQLite database."""
    engine = db_session.configure_engine("sqlite://")
    init_db()
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session_factory():
    return db_session.SessionLocal


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
