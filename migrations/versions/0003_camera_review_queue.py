"""Create persistent, school-scoped camera human-review queue.

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
    op.create_index("ix_camera_review_events_school_id", "camera_review_events", ["school_id"])
    op.create_index("ix_camera_review_events_camera_id", "camera_review_events", ["camera_id"])
    op.create_index("ix_camera_review_events_zone_id", "camera_review_events", ["zone_id"])
    op.create_index("ix_camera_review_events_detected_at", "camera_review_events", ["detected_at"])
    op.create_index("ix_camera_review_events_status", "camera_review_events", ["status"])
    op.create_index("ix_camera_review_events_created_at", "camera_review_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_camera_review_events_created_at", table_name="camera_review_events")
    op.drop_index("ix_camera_review_events_status", table_name="camera_review_events")
    op.drop_index("ix_camera_review_events_detected_at", table_name="camera_review_events")
    op.drop_index("ix_camera_review_events_zone_id", table_name="camera_review_events")
    op.drop_index("ix_camera_review_events_camera_id", table_name="camera_review_events")
    op.drop_index("ix_camera_review_events_school_id", table_name="camera_review_events")
    op.drop_table("camera_review_events")
