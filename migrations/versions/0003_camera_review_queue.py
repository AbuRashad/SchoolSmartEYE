"""Add the persistent human-review queue for camera-derived events.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenant, user-school linkage, aggregate observations, and audit events are
    # created by revisions 0003 and 0004. This revision owns only this table.
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
