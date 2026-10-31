from sqlalchemy import create_engine, inspect, text

from app.db.nextgen.base import NextBase
from app.db.nextgen import models  # noqa: F401
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
        assert "ng_schools" in inspector.get_table_names()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM ng_schools")).scalar_one() == 0
            assert connection.execute(text("SELECT COUNT(*) FROM ng_students")).scalar_one() == 0
    finally:
        engine.dispose()


def test_next_database_requires_explicit_postgresql_url():
    try:
        make_next_engine("")
    except RuntimeError as exc:
        assert "NEXT_DATABASE_URL" in str(exc)
    else:
        raise AssertionError("The secondary database must be opt-in")
