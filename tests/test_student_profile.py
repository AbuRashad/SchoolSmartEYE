"""Student CRUD + aggregated profile endpoint (`GET /students/{id}/profile`)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db import models as orm
from app.models import IncidentSeverity, SafetyIncident
from app.services import seed_data

API = "/api/v1"
SID = "STU-E2E-1"


@pytest.fixture()
def zone():
    seed_data.populate()
    return seed_data.zones[0]


@pytest.fixture()
def incident_cleanup():
    before = list(seed_data.incidents)
    yield
    seed_data.incidents[:] = before


def _create_student(client) -> None:
    r = client.post(
        f"{API}/students",
        json={"student_id": SID, "name": "E2E Tester", "grade": "Grade 9", "class_section": "A", "parent_id": "PAR-E2E-1"},
    )
    assert r.status_code == 201


def test_crud_and_error_paths(client, zone) -> None:
    _create_student(client)
    created = client.get(f"{API}/students").json()
    assert any(s["student_id"] == SID and s["photo_initial"] == "E" for s in created)

    dup = client.post(
        f"{API}/students",
        json={"student_id": SID, "name": "Dup", "grade": "G", "class_section": "A", "parent_id": "P"},
    )
    assert dup.status_code == 409

    r = client.patch(f"{API}/students/{SID}", json={"grade": "Grade 10", "photo_initial": "T", "is_active": False})
    assert r.status_code == 200
    assert (r.json()["grade"], r.json()["photo_initial"], r.json()["is_active"]) == ("Grade 10", "T", False)

    assert client.patch(f"{API}/students/NOPE", json={"grade": "X"}).status_code == 404
    assert client.get(f"{API}/students/NOPE/profile").status_code == 404
    assert client.delete(f"{API}/students/NOPE").status_code == 404

    assert client.delete(f"{API}/students/{SID}").status_code == 204
    assert client.delete(f"{API}/students/{SID}").status_code == 404


def test_profile_aggregates_all_sections(client, zone, db_session_factory, incident_cleanup) -> None:
    _create_student(client)
    client.patch(f"{API}/students/{SID}", json={"grade": "Grade 10"})
    today = datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc)

    with db_session_factory() as db:
        # 10-day present streak (incl. today), then an absence and a late day
        for offset in range(10):
            d = today - timedelta(days=offset)
            db.add(orm.AttendanceRecord(
                student_id=SID, date=d, status="present",
                arrival_time=datetime(d.year, d.month, d.day, 7, 50, tzinfo=timezone.utc),
                departure_time=datetime(d.year, d.month, d.day, 14, 15, tzinfo=timezone.utc),
                last_seen_zone=zone.zone_id,
            ))
        db.add(orm.AttendanceRecord(student_id=SID, date=today - timedelta(days=11), status="absent"))
        db.add(orm.AttendanceRecord(student_id=SID, date=today - timedelta(days=12), status="late"))
        db.add(orm.Bracelet(
            bracelet_id="BR-E2E-1", student_id=SID, mac_address="AA:BB:CC:DD:EE:01", battery_level=12,
            last_seen_zone=zone.zone_id, last_seen_at=now, firmware_version="2.1.0", notes="Test bracelet",
        ))
        db.add_all([
            orm.Notification(notification_id="N1", parent_id="PAR-E2E-1", student_id=SID, message="Arrived",
                             notification_type="attendance", sent_at=now - timedelta(hours=1), read=False),
            orm.Notification(notification_id="N2", parent_id="PAR-E2E-1", student_id=SID, message="Alert",
                             notification_type="safety", sent_at=now - timedelta(hours=2), read=False),
            orm.Notification(notification_id="N3", parent_id="PAR-E2E-1", student_id=SID, message="Report",
                             notification_type="info", sent_at=now - timedelta(days=1), read=True),
        ])
        db.commit()

    seed_data.incidents.append(SafetyIncident(
        incident_id="INC-E2E-1", zone_id=zone.zone_id, severity=IncidentSeverity.CRITICAL,
        description="Test", detected_at=now, resolved=False,
    ))

    d = client.get(f"{API}/students/{SID}/profile").json()
    assert d["grade"] == "Grade 10"
    assert d["today_status"] == "present"
    assert d["arrival_time"] and d["departure_time"]
    assert d["last_seen_zone"] == zone.zone_id and d["last_seen_zone_label"] == zone.label
    assert d["attendance_streak"] == 10
    assert len(d["weekly_attendance"]) == 7 and len(d["recent_attendance"]) == 30
    assert (d["last_30_days_present"], d["last_30_days_total"]) == (11, 12)
    assert d["monthly_attendance_pct"] == round(11 / 12 * 100, 1)
    assert d["bracelet"]["low_battery"] is True and d["bracelet"]["battery_level"] == 12
    assert d["bracelet"]["last_seen_zone_label"] == zone.label
    assert [n["notification_id"] for n in d["notifications"]] == ["N1", "N2", "N3"]
    assert d["unread_notifications"] == 2
    assert d["safety_status"] == "critical"
    assert d["open_incidents_in_last_zone"] == 1

    # Deleting the student cascades to the bracelet
    assert client.delete(f"{API}/students/{SID}").status_code == 204
    with db_session_factory() as db:
        assert db.get(orm.Bracelet, "BR-E2E-1") is None


def test_profile_for_student_without_data_is_unknown(client, zone) -> None:
    _create_student(client)
    d = client.get(f"{API}/students/{SID}/profile").json()
    assert d["today_status"] == "unknown" and d["safety_status"] == "unknown"
    assert d["bracelet"] is None and d["notifications"] == []
    assert d["attendance_streak"] == 0 and d["monthly_attendance_pct"] == 0.0


def test_profile_for_seeded_student_matches_frontend_contract(client, zone) -> None:
    d = client.get(f"{API}/students/STU-2024-0847/profile").json()
    assert set(d) >= {
        "student_id", "name", "grade", "class_section", "parent_id", "photo_initial", "is_active",
        "safety_status", "today_status", "arrival_time", "departure_time", "last_seen_zone",
        "last_seen_zone_label", "attendance_streak", "monthly_attendance_pct", "last_30_days_present",
        "last_30_days_total", "weekly_attendance", "recent_attendance", "bracelet", "notifications",
        "unread_notifications", "open_incidents_in_last_zone", "engagement_summary",
    }
    assert d["today_status"] == "present"
    assert d["bracelet"]["bracelet_id"] == "BR-0001"
    assert d["unread_notifications"] == 1  # only NTF-004 is unread
