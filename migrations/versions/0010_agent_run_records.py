"""Persist school-scoped agent orchestration runs.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("task", sa.String(length=500), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index("ix_agent_runs_school_id", "agent_runs", ["school_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_school_id", table_name="agent_runs")
    op.drop_table("agent_runs")
