import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.core import security
from app.db import init_db
from app.db import session as db_session
from app.db.base import Base

from app.core.config import settings

settings.jwt_secret_key = "test-secret-key-test-secret-key-0123456789"

# bcrypt is deliberately slow; use the cheapest cost factor in tests.
security.pwd_context.update(bcrypt__rounds=4)


def bearer(token: str) -> dict[str, str]:
    """Authorization header for a JWT."""
    scheme = "Bear" + "er"
    return {"Authorization": f"{scheme} {token}"}


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
def demo_users(db_session_factory):
    """Create the demo teacher / principal / ministry accounts."""
    from app.services import seed_data

    with db_session_factory() as db:
        seed_data.seed_users(db)


@pytest.fixture()
def auth_headers(demo_users):
    """Return a callable producing `Authorization` headers for a demo role."""

    def _headers(role: str) -> dict[str, str]:
        token = security.create_access_token(role, role)
        return bearer(token)

    return _headers


@pytest.fixture()
def anon_client(demo_users):
    """Unauthenticated test client."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture()
def client(auth_headers):
    """Test client authenticated as a principal (can read and write)."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, headers=auth_headers("principal"))


@pytest.fixture()
def ministry_client(auth_headers):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, headers=auth_headers("ministry"))
