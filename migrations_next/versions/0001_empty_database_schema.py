"""Create the initial next-generation schema; deliberately insert no records.

Revision ID: ng_0001
Revises:
"""
from alembic import op

from app.db.nextgen import models  # noqa: F401 — register metadata
from app.db.nextgen.base import NextBase
from app.db.nextgen.safety import assert_empty_target

revision = "ng_0001"
down_revision = None
branch_labels = ("nextgen",)
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    assert_empty_target(connection)
    # Structure only: no seed/demo/legacy rows are copied or inserted.
    NextBase.metadata.create_all(bind=connection)


def downgrade() -> None:
    raise RuntimeError(
        "The next-generation baseline is intentionally non-destructive. "
        "Do not drop schema through Alembic; use an explicitly reviewed database reset procedure."
    )
