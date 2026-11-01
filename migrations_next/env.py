"""Alembic environment dedicated to NEXT_DATABASE_URL and NextBase metadata."""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.nextgen import models  # noqa: F401 — register the isolated metadata
from app.db.nextgen.base import NextBase
from app.db.nextgen.safety import validate_next_database_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

next_database_url = validate_next_database_url(settings.next_database_url, settings.database_url)
config.set_main_option("sqlalchemy.url", next_database_url.replace("%", "%%"))
target_metadata = NextBase.metadata


def run_migrations_offline() -> None:
    context.configure(url=next_database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
