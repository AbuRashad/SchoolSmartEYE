"""Add append-only governance audit events.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "governance_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_governance_audit_events_school_id", "governance_audit_events", ["school_id"])
    op.create_index("ix_governance_audit_events_actor_user_id", "governance_audit_events", ["actor_user_id"])
    op.create_index("ix_governance_audit_events_event_type", "governance_audit_events", ["event_type"])
    op.create_index("ix_governance_audit_events_created_at", "governance_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_governance_audit_events_created_at", table_name="governance_audit_events")
    op.drop_index("ix_governance_audit_events_event_type", table_name="governance_audit_events")
    op.drop_index("ix_governance_audit_events_actor_user_id", table_name="governance_audit_events")
    op.drop_index("ix_governance_audit_events_school_id", table_name="governance_audit_events")
    op.drop_table("governance_audit_events")
