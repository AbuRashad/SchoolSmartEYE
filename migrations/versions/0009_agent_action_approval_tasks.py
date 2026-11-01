"""Add school-scoped human-approved agent action tasks.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_action_tasks",
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("source_request_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1200), nullable=False),
        sa.Column("assigned_role", sa.String(length=16), nullable=False, server_default="principal"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending_approval"),
        sa.Column("proposed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("action_id"),
    )
    op.create_index("ix_agent_action_tasks_school_id", "agent_action_tasks", ["school_id"])
    op.create_index("ix_agent_action_tasks_source_request_id", "agent_action_tasks", ["source_request_id"])
    op.create_index("ix_agent_action_tasks_status", "agent_action_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_action_tasks_status", table_name="agent_action_tasks")
    op.drop_index("ix_agent_action_tasks_source_request_id", table_name="agent_action_tasks")
    op.drop_index("ix_agent_action_tasks_school_id", table_name="agent_action_tasks")
    op.drop_table("agent_action_tasks")
