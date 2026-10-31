import pytest
from sqlalchemy import create_engine, inspect, text

from app.db.nextgen.base import NextBase
from app.db.nextgen import models  # noqa: F401
from app.db.nextgen.safety import assert_empty_target, validate_next_database_url
from app.db.nextgen.session import make_next_engine


def test_nextgen_metadata_is_independent_and_has_no_seed_rows():
    assert "ng_schools" in NextBase.metadata.tables
    assert "ng_students" in NextBase.metadata.tables
    assert "schools" not in NextBase.metadata.tables
    assert "students" not in NextBase.metadata.tables


def test_tenant_owned_tables_include_school_and_organization_scope():
    expected = {
        "ng_campuses", "ng_buildings", "ng_zones", "ng_guardians", "ng_students", "ng_student_guardians",
        "ng_classes", "ng_enrollments", "ng_attendance_events", "ng_cameras",
        "ng_edge_devices", "ng_camera_telemetry", "ng_ai_events", "ng_incidents",
        "ng_human_reviews", "ng_metric_observations", "ng_consent_records",
    }
    for table_name in expected:
        columns = NextBase.metadata.tables[table_name].columns
        assert "organization_id" in columns, table_name
        assert "school_id" in columns, table_name


def test_tenant_relationships_use_composite_foreign_keys():
    for table_name in ("ng_students", "ng_enrollments", "ng_attendance_events", "ng_buildings", "ng_zones", "ng_cameras", "ng_camera_telemetry"):
        constraints = NextBase.metadata.tables[table_name].foreign_key_constraints
        assert any(len(constraint.elements) >= 2 for constraint in constraints), table_name


def test_empty_schema_can_be_created_without_inserting_demo_data():
    engine = create_engine("sqlite:///:memory:")
    try:
        NextBase.metadata.create_all(engine)
        inspector = inspect(engine)
        tables = [name for name in inspector.get_table_names() if name.startswith("ng_")]
        assert "ng_schools" in tables
        assert "ng_students" in tables
        with engine.connect() as connection:
            for table_name in tables:
                count = connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
                assert count == 0, table_name
    finally:
        engine.dispose()


def test_next_database_requires_explicit_postgresql_url():
    with pytest.raises(RuntimeError, match="NEXT_DATABASE_URL"):
        make_next_engine("")


def test_next_database_must_be_postgresql_and_distinct_from_legacy():
    legacy = "postgresql+psycopg://legacy_user:secret@db.example:5432/school_live"
    with pytest.raises(RuntimeError, match="same database"):
        validate_next_database_url(
            "postgresql+psycopg://next_user:other@db.example:5432/school_live",
            legacy,
        )

    assert validate_next_database_url(
        "postgresql://next_user:secret@db.example:5432/school_next",
        legacy,
    ).startswith("postgresql+psycopg://")


def test_first_migration_guard_rejects_existing_user_tables():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            assert_empty_target(connection)
            connection.execute(text("CREATE TABLE existing_students (id INTEGER PRIMARY KEY)"))
            with pytest.raises(RuntimeError, match="must be empty"):
                assert_empty_target(connection)
    finally:
        engine.dispose()


def test_first_migration_guard_allows_only_empty_alembic_version_table():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            assert_empty_target(connection)
            connection.execute(text("INSERT INTO alembic_version VALUES ('old_revision')"))
            with pytest.raises(RuntimeError, match="Alembic history"):
                assert_empty_target(connection)
    finally:
        engine.dispose()


def test_database_identity_normalizes_default_postgresql_port():
    legacy = "postgresql+psycopg://legacy_user:secret@db.example/school_live"
    with pytest.raises(RuntimeError, match="same database"):
        validate_next_database_url(
            "postgresql+psycopg://next_user:other@db.example:5432/school_live",
            legacy,
        )
