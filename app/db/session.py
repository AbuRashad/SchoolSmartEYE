"""Engine, session factory and the `get_db` FastAPI dependency."""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def make_engine(url: str) -> Engine:
    """Build an engine for `url` (SQLite or any other SQLAlchemy backend)."""
    if url.startswith("sqlite"):
        kwargs: dict[str, object] = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # A single shared connection so every session sees the same in-memory DB.
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


engine: Engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configure_engine(url: str) -> Engine:
    """Re-point the global engine/session factory (used by tests)."""
    global engine  # noqa: PLW0603
    engine.dispose()
    engine = make_engine(url)
    SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they do not exist (Alembic is the preferred path in production)."""
    from app.db import models  # noqa: F401  (register models on Base.metadata)
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
