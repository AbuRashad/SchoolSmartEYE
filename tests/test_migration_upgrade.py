from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings


def test_alembic_upgrade_head_creates_wai_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "school_smarteye_migrations.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setattr(settings, "database_url", database_url)

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert "wearable_edge_devices" in tables
        assert "wearable_observations" in tables
        assert "camera_edge_devices" in tables
        assert "camera_health_snapshots" in tables
        student_columns = {column["name"] for column in inspector.get_columns("students")}
        assert "school_id" in student_columns
        with engine.connect() as connection:
            school = connection.execute(
                text("SELECT school_id FROM schools WHERE school_id = 'school-primary'")
            ).scalar_one()
            assert school == "school-primary"
    finally:
        engine.dispose()
