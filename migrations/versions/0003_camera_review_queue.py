"""Add missing tenant/governance schema and camera review queue.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The ORM already defines these tenant/governance tables, but the two
    # previous revisions did not create them. Add them before dependent tables.
    op.create_table(
        "schools",
        sa.Column("school_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("users", sa.Column("school_id", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_users_school_id_schools", "users", "schools", ["school_id"], ["school_id"]
    )
    op.create_index("ix_users_school_id", "users", ["school_id"])

    op.create_table(
        "governance_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.String(length=64), sa.ForeignKey("schools.school_id"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_governance_audit_events_school_id", "governance_audit_events", ["school_id"])
    op.create_index("ix_governance_audit_events_actor_user_id", "governance_audit_events", ["actor_user_id"])
    op.create_index("ix_governance_audit_events_event_type", "governance_audit_events", ["event_type"])
    op.create_index("ix_governance_audit_events_created_at", "governance_audit_events", ["created_at"])

    op.create_table(
        "aggregate_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("school_id", sa.String(length=64), sa.ForeignKey("schools.school_id"), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("data_status", sa.String(length=24), nullable=False, server_default="live_unverified"),
        sa.Column("validation_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("metric_version", sa.String(length=24), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("school_id", "idempotency_key", name="uq_observation_school_idempotency"),
    )
    op.create_index("ix_aggregate_observations_school_id", "aggregate_observations", ["school_id"])
    op.create_index("ix_aggregate_observations_metric_key", "aggregate_observations", ["metric_key"])
    op.create_index("ix_aggregate_observations_observed_at", "aggregate_observations", ["observed_at"])

    op.create_table(
        "camera_review_events",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("school_id", sa.String(length=64), sa.ForeignKey("schools.school_id"), nullable=False),
        sa.Column("camera_id", sa.String(length=64), nullable=True),
        sa.Column("zone_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="low"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_ref", sa.String(length=256), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=1024), nullable=False, server_default=""),
        sa.UniqueConstraint("school_id", "idempotency_key", name="uq_camera_review_school_idempotency"),
    )
    for column in ("school_id", "camera_id", "zone_id", "detected_at", "status", "created_at"):
        op.create_index(f"ix_camera_review_events_{column}", "camera_review_events", [column])


def downgrade() -> None:
    for column in ("created_at", "status", "detected_at", "zone_id", "camera_id", "school_id"):
        op.drop_index(f"ix_camera_review_events_{column}", table_name="camera_review_events")
    op.drop_table("camera_review_events")

    for column in ("observed_at", "metric_key", "school_id"):
        op.drop_index(f"ix_aggregate_observations_{column}", table_name="aggregate_observations")
    op.drop_table("aggregate_observations")

    for column in ("created_at", "event_type", "actor_user_id", "school_id"):
        op.drop_index(f"ix_governance_audit_events_{column}", table_name="governance_audit_events")
    op.drop_table("governance_audit_events")

    op.drop_index("ix_users_school_id", table_name="users")
    op.drop_constraint("fk_users_school_id_schools", "users", type_="foreignkey")
    op.drop_column("users", "school_id")
    op.drop_table("schools")
