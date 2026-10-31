"""Read-only readiness verification for the isolated next-generation database.

This module never creates databases, tables, users, or records. Provisioning is an
explicit infrastructure operation; this verifier only inspects an already
provisioned target and reports whether it is ready for a later reviewed step.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import Connection, make_url

from app.core.config import settings
from app.db.nextgen import models  # noqa: F401 — register metadata
from app.db.nextgen.base import NextBase
from app.db.nextgen.safety import validate_next_database_url

EXPECTED_REVISION = "ng_0001"


def inspect_next_database(connection: Connection) -> dict[str, Any]:
    """Inspect schema, migration revision, and row counts without modifying data."""
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(NextBase.metadata.tables)
    missing_tables = sorted(expected_tables - existing_tables)
    unexpected_tables = sorted(existing_tables - expected_tables - {"alembic_version"})

    revision = None
    if "alembic_version" in existing_tables:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()

    row_counts: dict[str, int] = {}
    if not missing_tables:
        for table_name in sorted(expected_tables):
            # Identifiers are sourced only from trusted SQLAlchemy model metadata.
            quoted_name = connection.dialect.identifier_preparer.quote(table_name)
            row_counts[table_name] = int(
                connection.execute(text(f"SELECT COUNT(*) FROM {quoted_name}")).scalar_one()
            )

    non_empty_tables = {name: count for name, count in row_counts.items() if count != 0}
    checks = {
        "schema_complete": not missing_tables,
        "no_unexpected_tables": not unexpected_tables,
        "migration_revision_valid": revision == EXPECTED_REVISION,
        "all_business_tables_empty": not non_empty_tables and not missing_tables,
    }
    return {
        "status": "ready" if all(checks.values()) else "not_ready",
        "read_only": True,
        "database_name": connection.execute(text("SELECT current_database()")).scalar()
        if connection.dialect.name == "postgresql"
        else None,
        "expected_table_count": len(expected_tables),
        "existing_expected_table_count": len(expected_tables) - len(missing_tables),
        "missing_tables": missing_tables,
        "unexpected_tables": unexpected_tables,
        "migration_revision": revision,
        "row_counts": row_counts,
        "non_empty_tables": non_empty_tables,
        "checks": checks,
    }


def verify_configured_next_database(engine: Engine | None = None) -> dict[str, Any]:
    """Verify NEXT_DATABASE_URL; never log or return credentials or the full URL."""
    next_url = settings.next_database_url
    if not next_url:
        return {
            "status": "not_configured",
            "read_only": True,
            "message": "NEXT_DATABASE_URL is not configured.",
        }

    try:
        safe_url = validate_next_database_url(next_url, settings.database_url)
    except Exception as exc:
        return {
            "status": "not_ready",
            "read_only": True,
            "message": str(exc),
        }

    owned_engine = engine is None
    if engine is None:
        from sqlalchemy import create_engine

        engine = create_engine(safe_url, pool_pre_ping=True, pool_size=1, max_overflow=0)

    try:
        with engine.connect() as connection:
            report = inspect_next_database(connection)
            report["connection"] = "successful"
            parsed = make_url(safe_url)
            report["database_backend"] = parsed.get_backend_name()
            return report
    except Exception as exc:
        return {
            "status": "not_ready",
            "read_only": True,
            "connection": "failed",
            "error_type": type(exc).__name__,
            "message": "Could not inspect the configured next-generation database. "
            "Check network access, credentials, and PostgreSQL availability.",
        }
    finally:
        if owned_engine:
            engine.dispose()
