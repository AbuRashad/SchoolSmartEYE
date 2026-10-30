"""Add explicit school ownership to student records.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.add_column(sa.Column("school_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_students_school_id_schools", "schools", ["school_id"], ["school_id"]
        )
        batch_op.create_index("ix_students_school_id", ["school_id"], unique=False)

    # Existing single-school records are assigned to the explicitly provisioned tenant.
    op.execute("UPDATE students SET school_id = 'school-primary' WHERE school_id IS NULL")

    with op.batch_alter_table("students") as batch_op:
        batch_op.alter_column("school_id", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_index("ix_students_school_id")
        batch_op.drop_constraint("fk_students_school_id_schools", type_="foreignkey")
        batch_op.drop_column("school_id")
