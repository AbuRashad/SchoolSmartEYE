"""Persist school-scoped camera health telemetry.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "camera_health_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("camera_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fps", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("consecutive_missed_heartbeats", sa.Integer(), nullable=False),
        sa.Column("reconnect_count", sa.Integer(), nullable=False),
        sa.Column("frozen_frame", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "idempotency_key", name="uq_camera_health_school_idempotency"),
    )
    op.create_index("ix_camera_health_snapshots_school_id", "camera_health_snapshots", ["school_id"])
    op.create_index("ix_camera_health_snapshots_camera_id", "camera_health_snapshots", ["camera_id"])
    op.create_index("ix_camera_health_snapshots_status", "camera_health_snapshots", ["status"])
    op.create_index("ix_camera_health_snapshots_observed_at", "camera_health_snapshots", ["observed_at"])
    op.create_index("ix_camera_health_snapshots_created_at", "camera_health_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_camera_health_snapshots_created_at", table_name="camera_health_snapshots")
    op.drop_index("ix_camera_health_snapshots_observed_at", table_name="camera_health_snapshots")
    op.drop_index("ix_camera_health_snapshots_status", table_name="camera_health_snapshots")
    op.drop_index("ix_camera_health_snapshots_camera_id", table_name="camera_health_snapshots")
    op.drop_index("ix_camera_health_snapshots_school_id", table_name="camera_health_snapshots")
    op.drop_table("camera_health_snapshots")
