"""school membership and nullable student tenant scope

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("school_id"),
    )
    op.create_table(
        "school_memberships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "school_id", name="uq_school_membership_user_school"),
    )
    op.create_index("ix_school_memberships_user_id", "school_memberships", ["user_id"])
    op.create_index("ix_school_memberships_school_id", "school_memberships", ["school_id"])
    op.add_column("students", sa.Column("school_id", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_students_school_id_schools", "students", "schools", ["school_id"], ["school_id"]
    )
    op.create_index("ix_students_school_id", "students", ["school_id"])


def downgrade() -> None:
    op.drop_index("ix_students_school_id", table_name="students")
    op.drop_constraint("fk_students_school_id_schools", "students", type_="foreignkey")
    op.drop_column("students", "school_id")
    op.drop_index("ix_school_memberships_school_id", table_name="school_memberships")
    op.drop_index("ix_school_memberships_user_id", table_name="school_memberships")
    op.drop_table("school_memberships")
    op.drop_table("schools")
