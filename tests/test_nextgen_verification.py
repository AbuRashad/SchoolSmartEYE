from sqlalchemy import create_engine, text

from app.db.nextgen import models  # noqa: F401
from app.db.nextgen.base import NextBase
from app.db.nextgen.verification import EXPECTED_REVISION, inspect_next_database


def test_verifier_reports_empty_complete_schema_as_ready():
    engine = create_engine("sqlite:///:memory:")
    try:
        NextBase.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(
                text("INSERT INTO alembic_version VALUES (:revision)"),
                {"revision": EXPECTED_REVISION},
            )
        with engine.connect() as connection:
            report = inspect_next_database(connection)
        assert report["status"] == "ready"
        assert report["read_only"] is True
        assert report["checks"]["all_business_tables_empty"] is True
        assert report["non_empty_tables"] == {}
        assert report["migration_revision"] == EXPECTED_REVISION
    finally:
        engine.dispose()


def test_verifier_flags_any_business_data_as_not_ready():
    engine = create_engine("sqlite:///:memory:")
    try:
        NextBase.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(
                text("INSERT INTO alembic_version VALUES (:revision)"),
                {"revision": EXPECTED_REVISION},
            )
            connection.execute(
                text(
                    "INSERT INTO ng_organizations "
                    "(id, name, organization_type, status, created_at, updated_at) "
                    "VALUES ('org-1', 'Example', 'school_group', 'active', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
        with engine.connect() as connection:
            report = inspect_next_database(connection)
        assert report["status"] == "not_ready"
        assert report["non_empty_tables"]["ng_organizations"] == 1
        assert report["checks"]["all_business_tables_empty"] is False
    finally:
        engine.dispose()


def test_verifier_flags_missing_tables_and_wrong_revision():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(text("INSERT INTO alembic_version VALUES ('unexpected')"))
        with engine.connect() as connection:
            report = inspect_next_database(connection)
        assert report["status"] == "not_ready"
        assert report["checks"]["schema_complete"] is False
        assert report["checks"]["migration_revision_valid"] is False
    finally:
        engine.dispose()
