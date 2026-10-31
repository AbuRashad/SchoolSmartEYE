"""Add verified school ownership to physical zones.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("zones") as batch_op:
        batch_op.add_column(sa.Column("school_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_zones_school_id_schools", "schools", ["school_id"], ["school_id"]
        )
        batch_op.create_index("ix_zones_school_id", ["school_id"])


def downgrade() -> None:
    with op.batch_alter_table("zones") as batch_op:
        batch_op.drop_index("ix_zones_school_id")
        batch_op.drop_constraint("fk_zones_school_id_schools", type_="foreignkey")
        batch_op.drop_column("school_id")
