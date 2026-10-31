"""Add school ownership to SSI history and safety drills.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ssi_snapshots") as batch_op:
        batch_op.add_column(sa.Column("school_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_ssi_snapshots_school_id_schools", "schools", ["school_id"], ["school_id"]
        )
        batch_op.create_index("ix_ssi_snapshots_school_id", ["school_id"])

    with op.batch_alter_table("drills") as batch_op:
        batch_op.add_column(sa.Column("school_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_drills_school_id_schools", "schools", ["school_id"], ["school_id"]
        )
        batch_op.create_index("ix_drills_school_id", ["school_id"])


def downgrade() -> None:
    with op.batch_alter_table("drills") as batch_op:
        batch_op.drop_index("ix_drills_school_id")
        batch_op.drop_constraint("fk_drills_school_id_schools", type_="foreignkey")
        batch_op.drop_column("school_id")

    with op.batch_alter_table("ssi_snapshots") as batch_op:
        batch_op.drop_index("ix_ssi_snapshots_school_id")
        batch_op.drop_constraint("fk_ssi_snapshots_school_id_schools", type_="foreignkey")
        batch_op.drop_column("school_id")
