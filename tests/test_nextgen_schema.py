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
        "ng_campuses", "ng_guardians", "ng_students", "ng_student_guardians",
        "ng_classes", "ng_enrollments", "ng_attendance_events", "ng_cameras",
        "ng_edge_devices", "ng_camera_telemetry", "ng_ai_events", "ng_incidents",
        "ng_human_reviews", "ng_metric_observations", "ng_consent_records",
    }
    for table_name in expected:
        columns = NextBase.metadata.tables[table_name].columns
        assert "organization_id" in columns, table_name
        assert "school_id" in columns, table_name


def test_next_database_requires_explicit_postgresql_url():
    try:
        make_next_engine("")
    except RuntimeError as exc:
        assert "NEXT_DATABASE_URL" in str(exc)
    else:
        raise AssertionError("The secondary database must be opt-in")
