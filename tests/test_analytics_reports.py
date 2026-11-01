from datetime import datetime, timezone

from app.db import models as orm
from app.services import seed_data


def _add_foreign_school(db) -> None:
    db.add(orm.School(school_id="ANALYTICS-FOREIGN", name="Foreign Analytics School", is_active=True))
    db.flush()
    db.add(orm.Student(
        student_id="ANALYTICS-FOREIGN-STUDENT", school_id="ANALYTICS-FOREIGN",
        name="Foreign Student", grade="G7", class_section="A", parent_id="P-FOREIGN",
    ))
    db.add(orm.AttendanceRecord(
        student_id="ANALYTICS-FOREIGN-STUDENT",
        date=datetime.now(timezone.utc).date(),
        status="present",
    ))
    db.add(orm.Zone(
        zone_id="ANALYTICS-FOREIGN-ZONE", school_id="ANALYTICS-FOREIGN",
        label="Foreign Zone", zone_type="classroom", capacity=20, floor=1, grid_x=9, grid_y=9,
    ))
    db.flush()
    db.add(orm.Incident(
        incident_id="ANALYTICS-FOREIGN-INCIDENT", zone_id="ANALYTICS-FOREIGN-ZONE",
        severity="critical", description="Foreign-only incident",
        detected_at=datetime.now(timezone.utc), resolved=False,
    ))


def test_analytics_overview_excludes_other_school_data(client, db_session_factory) -> None:
    seed_data.populate()
    with db_session_factory() as db:
        _add_foreign_school(db)
        db.commit()

    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["school_id"] == "DEMO-SCHOOL-001"
    assert data["students"]["active"] == 10
    assert data["attendance"]["daily"][-1]["recorded"] == 10
    assert data["data_status"] == "demo"
    assert "not live school telemetry" in data["data_notice"]
    assert "ANALYTICS-FOREIGN-INCIDENT" not in response.text
    assert "Foreign-only incident" not in response.text


def test_report_previews_are_generated_from_authenticated_school_only(ministry_client, db_session_factory) -> None:
    seed_data.populate()
    with db_session_factory() as db:
        _add_foreign_school(db)
        db.commit()

    response = ministry_client.get("/api/v1/reports/list")
    assert response.status_code == 200
    reports = response.json()
    assert len(reports) == 3
    assert all(report["persisted"] is False for report in reports)
    assert all(report["data_status"] == "demo" for report in reports)
    assert all("not live school telemetry" in report["data_notice"] for report in reports)
    attendance_preview = next(report for report in reports if report["report_type"] == "operational")
    assert sum(attendance_preview["data"]["attendance_by_status"].values()) == 10
    assert all(report["report_id"].startswith("DEMO-SCHOOL-001:") for report in reports)
    assert "ANALYTICS-FOREIGN" not in response.text
    assert "Foreign-only incident" not in response.text

    stats = ministry_client.get("/api/v1/reports/stats")
    assert stats.status_code == 200
    assert stats.json()["generated_on_request"] is True
    assert stats.json()["stored_artifacts"] is False
