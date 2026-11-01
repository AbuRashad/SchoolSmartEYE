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

        version = engine.connect().exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        assert version == "0006"
    finally:
        engine.dispose()
