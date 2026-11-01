"""Add idempotent agent action keys and lifecycle audit events.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_agent_action_school_run_kind",
        "agent_action_tasks",
        ["school_id", "source_request_id", "action_kind"],
    )

    op.create_table(
        "agent_action_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("source_request_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["action_id"], ["agent_action_tasks.action_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_agent_action_audit_school_id", "agent_action_audit_events", ["school_id"])
    op.create_index("ix_agent_action_audit_action_id", "agent_action_audit_events", ["action_id"])
    op.create_index("ix_agent_action_audit_source_request_id", "agent_action_audit_events", ["source_request_id"])
    op.create_index("ix_agent_action_audit_event_type", "agent_action_audit_events", ["event_type"])
    op.create_index("ix_agent_action_audit_created_at", "agent_action_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_action_audit_created_at", table_name="agent_action_audit_events")
    op.drop_index("ix_agent_action_audit_event_type", table_name="agent_action_audit_events")
    op.drop_index("ix_agent_action_audit_source_request_id", table_name="agent_action_audit_events")
    op.drop_index("ix_agent_action_audit_action_id", table_name="agent_action_audit_events")
    op.drop_index("ix_agent_action_audit_school_id", table_name="agent_action_audit_events")
    op.drop_table("agent_action_audit_events")
    op.drop_constraint("uq_agent_action_school_run_kind", "agent_action_tasks", type_="unique")
