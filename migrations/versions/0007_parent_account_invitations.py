"""Add secure parent account invitations.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_invitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("invited_username", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("verification_method", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.student_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_parent_invitation_token_hash"),
    )
    op.create_index("ix_parent_invitations_school_id", "parent_invitations", ["school_id"])
    op.create_index("ix_parent_invitations_student_id", "parent_invitations", ["student_id"])
    op.create_index("ix_parent_invitations_invited_username", "parent_invitations", ["invited_username"])
    op.create_index("ix_parent_invitations_token_hash", "parent_invitations", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_parent_invitations_token_hash", table_name="parent_invitations")
    op.drop_index("ix_parent_invitations_invited_username", table_name="parent_invitations")
    op.drop_index("ix_parent_invitations_student_id", table_name="parent_invitations")
    op.drop_index("ix_parent_invitations_school_id", table_name="parent_invitations")
    op.drop_table("parent_invitations")
