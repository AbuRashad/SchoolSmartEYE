"""Create the initial next-generation schema; deliberately insert no records.

Revision ID: ng_0001
Revises:
"""
from alembic import op

from app.db.nextgen import models  # noqa: F401 — register metadata
from app.db.nextgen.base import NextBase

revision = "ng_0001"
down_revision = None
branch_labels = ("nextgen",)
depends_on = None


def upgrade() -> None:
    # The first isolated baseline creates structure only. No seed/demo/migration
    # data is inserted. Follow-up revisions should use normal Alembic operations.
    NextBase.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    NextBase.metadata.drop_all(bind=op.get_bind())
