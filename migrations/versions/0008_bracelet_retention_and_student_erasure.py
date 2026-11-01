"""Add bracelet reading retention and student erasure audit.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bracelet_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bracelet_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("zone_id", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("battery_level", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["bracelet_id"], ["bracelets.bracelet_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.student_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bracelet_readings_bracelet_id", "bracelet_readings", ["bracelet_id"])
    op.create_index("ix_bracelet_readings_student_id", "bracelet_readings", ["student_id"])
    op.create_index("ix_bracelet_readings_recorded_at", "bracelet_readings", ["recorded_at"])

    op.create_table(
        "student_erasure_audits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("erased_by_user_id", sa.Integer(), nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_attendance_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_notification_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_feedback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_bracelet_reading_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_parent_link_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_invitation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_bracelet_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["erased_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_erasure_audits_school_id", "student_erasure_audits", ["school_id"])


def downgrade() -> None:
    op.drop_index("ix_student_erasure_audits_school_id", table_name="student_erasure_audits")
    op.drop_table("student_erasure_audits")
    op.drop_index("ix_bracelet_readings_recorded_at", table_name="bracelet_readings")
    op.drop_index("ix_bracelet_readings_student_id", table_name="bracelet_readings")
    op.drop_index("ix_bracelet_readings_bracelet_id", table_name="bracelet_readings")
    op.drop_table("bracelet_readings")
