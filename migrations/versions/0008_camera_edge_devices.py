"""Add revocable camera edge-agent identities.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "camera_edge_devices",
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("camera_id", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("provisioned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["provisioned_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("device_id"),
        sa.UniqueConstraint("school_id", "camera_id", name="uq_camera_edge_school_camera"),
    )
    op.create_index("ix_camera_edge_devices_school_id", "camera_edge_devices", ["school_id"])
    op.create_index("ix_camera_edge_devices_camera_id", "camera_edge_devices", ["camera_id"])
    op.create_index("ix_camera_edge_devices_is_active", "camera_edge_devices", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_camera_edge_devices_is_active", table_name="camera_edge_devices")
    op.drop_index("ix_camera_edge_devices_camera_id", table_name="camera_edge_devices")
    op.drop_index("ix_camera_edge_devices_school_id", table_name="camera_edge_devices")
    op.drop_table("camera_edge_devices")
