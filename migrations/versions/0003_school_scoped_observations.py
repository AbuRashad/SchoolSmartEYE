"""Add school tenancy and aggregate observation ingestion.

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
        "schools",
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("school_id"),
    )
    op.execute(
        "INSERT INTO schools (school_id, name, created_at) "
        "VALUES ('school-primary', 'Primary School', CURRENT_TIMESTAMP)"
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("school_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key("fk_users_school_id_schools", "schools", ["school_id"], ["school_id"])
        batch_op.create_index("ix_users_school_id", ["school_id"], unique=False)
    op.execute("UPDATE users SET school_id = 'school-primary' WHERE role = 'principal'")

    op.create_table(
        "aggregate_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.String(length=64), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("data_status", sa.String(length=24), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("metric_version", sa.String(length=24), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "idempotency_key", name="uq_observation_school_idempotency"),
    )
    op.create_index("ix_aggregate_observations_school_id", "aggregate_observations", ["school_id"])
    op.create_index("ix_aggregate_observations_metric_key", "aggregate_observations", ["metric_key"])
    op.create_index("ix_aggregate_observations_observed_at", "aggregate_observations", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_aggregate_observations_observed_at", table_name="aggregate_observations")
    op.drop_index("ix_aggregate_observations_metric_key", table_name="aggregate_observations")
    op.drop_index("ix_aggregate_observations_school_id", table_name="aggregate_observations")
    op.drop_table("aggregate_observations")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_school_id")
        batch_op.drop_constraint("fk_users_school_id_schools", type_="foreignkey")
        batch_op.drop_column("school_id")
    op.drop_table("schools")
