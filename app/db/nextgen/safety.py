"""Safety checks for the isolated next-generation database."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, make_url


def _database_identity(url: str) -> tuple[str, str, int | None, str | None]:
    parsed = make_url(url)
    return (
        parsed.get_backend_name(),
        (parsed.host or "").strip().lower(),
        parsed.port or (5432 if parsed.get_backend_name() == "postgresql" else None),
        parsed.database,
    )


def validate_next_database_url(next_url: str, legacy_url: str) -> str:
    """Require a PostgreSQL target that is physically distinct from the legacy DB."""
    if not next_url:
        raise RuntimeError("NEXT_DATABASE_URL is not configured")

    parsed = make_url(next_url)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("The next-generation database must use PostgreSQL")
    if parsed.drivername not in ("postgresql", "postgresql+psycopg"):
        raise RuntimeError("Use the psycopg PostgreSQL driver for NEXT_DATABASE_URL")

    if _database_identity(next_url) == _database_identity(legacy_url):
        raise RuntimeError(
            "NEXT_DATABASE_URL points to the same database as DATABASE_URL; "
            "configure a separate PostgreSQL database before continuing"
        )

    return parsed.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


def assert_empty_target(connection: Connection) -> None:
    """Reject a first schema install on any database that already has user tables/data."""
    tables = set(inspect(connection).get_table_names())
    unexpected = tables - {"alembic_version"}
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise RuntimeError(
            "The next-generation database must be empty before ng_0001; "
            f"found existing tables: {names}"
        )

    if "alembic_version" in tables:
        version_rows = connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one()
        if version_rows:
            raise RuntimeError(
                "The next-generation database already has Alembic history; "
                "refusing to treat it as a fresh empty database"
            )
