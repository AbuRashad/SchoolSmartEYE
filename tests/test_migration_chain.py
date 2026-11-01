from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings


def test_alembic_upgrade_head_creates_verified_parent_link_schema(tmp_path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration-smoke.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")

    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root / "migrations"))
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        assert "parent_student_links" in inspector.get_table_names()
        assert "parent_invitations" in inspector.get_table_names()
        assert "bracelet_readings" in inspector.get_table_names()
        assert "student_erasure_audits" in inspector.get_table_names()

        reading_columns = {column["name"] for column in inspector.get_columns("bracelet_readings")}
        assert {"bracelet_id", "student_id", "zone_id", "recorded_at", "battery_level"}.issubset(reading_columns)

        audit_columns = {column["name"] for column in inspector.get_columns("student_erasure_audits")}
        assert "student_id" not in audit_columns
        assert {"school_id", "erased_by_user_id", "erased_at", "deleted_feedback_count", "deleted_engagement_snapshot_count", "deleted_feedback_log_count"}.issubset(audit_columns)

        invitation_columns = {column["name"] for column in inspector.get_columns("parent_invitations")}
        assert {"school_id", "student_id", "invited_username", "full_name", "token_hash", "invited_by_user_id", "verification_method", "created_at", "expires_at", "accepted_at", "revoked_at"}.issubset(invitation_columns)

        columns = {column["name"] for column in inspector.get_columns("parent_student_links")}
        assert {
            "user_id",
            "student_id",
            "school_id",
            "verified_by_user_id",
            "verified_at",
            "verification_method",
            "is_active",
            "revoked_by_user_id",
            "revoked_at",
        }.issubset(columns)

        unique_constraints = inspector.get_unique_constraints("parent_student_links")
        assert any(
            item["name"] == "uq_parent_student_school_link"
            and item["column_names"] == ["user_id", "student_id", "school_id"]
            for item in unique_constraints
        )

        foreign_keys = inspector.get_foreign_keys("parent_student_links")
        assert {tuple(item["constrained_columns"]) for item in foreign_keys} >= {
            ("user_id",),
            ("student_id",),
            ("school_id",),
            ("verified_by_user_id",),
            ("revoked_by_user_id",),
        }

        action_columns = {column["name"] for column in inspector.get_columns("agent_action_tasks")}
        assert {"school_id", "source_request_id", "action_kind", "status"}.issubset(action_columns)

        action_unique_indexes = inspector.get_indexes("agent_action_tasks")
        assert any(
            item["name"] == "uq_agent_action_school_run_kind"
            and item.get("unique")
            and item["column_names"] == ["school_id", "source_request_id", "action_kind"]
            for item in action_unique_indexes
        )

        action_audit_columns = {column["name"] for column in inspector.get_columns("agent_action_audit_events")}
        assert {
            "event_id", "school_id", "action_id", "source_request_id",
            "event_type", "actor_type", "actor_user_id", "from_status",
            "to_status", "event_metadata", "created_at",
        }.issubset(action_audit_columns)

        version = engine.connect().exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        assert version == "0011"
    finally:
        engine.dispose()
