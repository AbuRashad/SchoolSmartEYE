"""Opt-in connection/session factory for the parallel PostgreSQL database."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def make_next_engine(url: str) -> Engine:
    """Create the secondary engine without touching the legacy engine."""
    if not url:
        raise RuntimeError("NEXT_DATABASE_URL is not configured")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("The next-generation database must use PostgreSQL with psycopg")
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


@lru_cache(maxsize=1)
def get_next_session_factory() -> sessionmaker[Session]:
    """Build and cache a session factory only when explicitly requested."""
    url = settings.next_database_url
    if not url:
        raise RuntimeError("NEXT_DATABASE_URL is not configured")
    return sessionmaker(bind=make_next_engine(url), autoflush=False, expire_on_commit=False)
