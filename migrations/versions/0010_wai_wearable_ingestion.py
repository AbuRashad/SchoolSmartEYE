"""Add authenticated WAI devices and typed wearable observations.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wearable_edge_devices",
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("bracelet_id", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("provisioned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["bracelet_id"], ["bracelets.bracelet_id"]),
        sa.ForeignKeyConstraint(["provisioned_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("device_id"),
        sa.UniqueConstraint("school_id", "bracelet_id", name="uq_wearable_edge_school_bracelet"),
    )
    op.create_index("ix_wearable_edge_devices_school_id", "wearable_edge_devices", ["school_id"])
    op.create_index("ix_wearable_edge_devices_bracelet_id", "wearable_edge_devices", ["bracelet_id"])
    op.create_index("ix_wearable_edge_devices_is_active", "wearable_edge_devices", ["is_active"])

    op.create_table(
        "wearable_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("bracelet_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=24), nullable=False),
        sa.Column("heart_rate_bpm", sa.Float(), nullable=True),
        sa.Column("hrv_ms", sa.Float(), nullable=True),
        sa.Column("skin_temperature_c", sa.Float(), nullable=True),
        sa.Column("movement_activity_score", sa.Float(), nullable=True),
        sa.Column("eda_us", sa.Float(), nullable=True),
        sa.Column("battery_level", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("data_status", sa.String(length=24), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.student_id"]),
        sa.ForeignKeyConstraint(["bracelet_id"], ["bracelets.bracelet_id"]),
        sa.ForeignKeyConstraint(["device_id"], ["wearable_edge_devices.device_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id", "device_id", "idempotency_key",
            name="uq_wearable_observation_device_idempotency",
        ),
    )
    for column in ("school_id", "student_id", "bracelet_id", "device_id", "observed_at"):
        op.create_index(f"ix_wearable_observations_{column}", "wearable_observations", [column])


def downgrade() -> None:
    for column in ("observed_at", "device_id", "bracelet_id", "student_id", "school_id"):
        op.drop_index(f"ix_wearable_observations_{column}", table_name="wearable_observations")
    op.drop_table("wearable_observations")
    op.drop_index("ix_wearable_edge_devices_is_active", table_name="wearable_edge_devices")
    op.drop_index("ix_wearable_edge_devices_bracelet_id", table_name="wearable_edge_devices")
    op.drop_index("ix_wearable_edge_devices_school_id", table_name="wearable_edge_devices")
    op.drop_table("wearable_edge_devices")
