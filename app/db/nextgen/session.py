"""Opt-in connection/session factory for the parallel PostgreSQL database."""
from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def make_next_engine(url: str) -> Engine:
    """Create the secondary engine without touching the legacy engine."""
    if not url:
        raise RuntimeError("NEXT_DATABASE_URL is not configured")
    if not url.startswith(("postgresql+psycopg://", "postgresql://")):
        raise RuntimeError("The next-generation database must use PostgreSQL")
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


def get_next_session_factory() -> sessionmaker[Session]:
    """Build a session factory on demand; no connection occurs at import time."""
    url = settings.next_database_url
    if not url:
        raise RuntimeError("NEXT_DATABASE_URL is not configured")
    return sessionmaker(bind=make_next_engine(url), autoflush=False, expire_on_commit=False)
