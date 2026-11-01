"""Create audited parent-to-student identity links.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_student_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("verified_by_user_id", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verification_method", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.student_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "student_id", "school_id", name="uq_parent_student_school_link"),
    )
    op.create_index("ix_parent_student_links_user_id", "parent_student_links", ["user_id"])
    op.create_index("ix_parent_student_links_student_id", "parent_student_links", ["student_id"])
    op.create_index("ix_parent_student_links_school_id", "parent_student_links", ["school_id"])


def downgrade() -> None:
    op.drop_index("ix_parent_student_links_school_id", table_name="parent_student_links")
    op.drop_index("ix_parent_student_links_student_id", table_name="parent_student_links")
    op.drop_index("ix_parent_student_links_user_id", table_name="parent_student_links")
    op.drop_table("parent_student_links")
