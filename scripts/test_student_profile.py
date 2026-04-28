"""Thorough test for the student profile endpoint + student CRUD.

Exercises:
- List / Create / Patch / Delete students (+ cascade to bracelets)
- 404 error paths
- Profile aggregation with:
    * today's attendance record
    * 30-day history + streak computation
    * assigned bracelet + low-battery flag
    * parent + student notifications (read / unread)
    * open incident in the last-seen zone → safety downgrade
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    AttendanceStatus,
    Bracelet,
    DailyAttendance,
    IncidentSeverity,
    NotificationMessage,
    SafetyIncident,
)
from app.services import seed_data


def section(title: str) -> None:
    print(f"\n── {title} " + "─" * (70 - len(title)))


def expect(cond: bool, label: str) -> None:
    status = "OK " if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        sys.exit(1)


def main() -> None:
    # Force seed population (TestClient w/o context doesn't trigger lifespan)
    seed_data.populate()
    client = TestClient(app)

    # ── Clean slate for mutable stores (keep zones/cameras/teachers) ---------
    seed_data.students.clear()
    seed_data.bracelets.clear()
    seed_data.attendance_records.clear()
    seed_data.notifications.clear()
    seed_data.incidents.clear()

    # Ensure at least one known zone
    zone_id = seed_data.zones[0].zone_id if seed_data.zones else None
    assert zone_id, "seed_data.zones must contain at least one zone"
    zone_label = seed_data.zones[0].label

    # ── Create student --------------------------------------------------------
    section("POST /students")
    r = client.post(
        "/api/v1/students",
        json={
            "student_id": "STU-E2E-1",
            "name": "E2E Tester",
            "grade": "Grade 9",
            "class_section": "A",
            "parent_id": "PAR-E2E-1",
        },
    )
    expect(r.status_code == 201, f"status=201 (got {r.status_code})")
    expect(r.json()["photo_initial"] == "E", "photo_initial auto-derived from name")

    # Duplicate create → 409
    r2 = client.post(
        "/api/v1/students",
        json={
            "student_id": "STU-E2E-1",
            "name": "Dup",
            "grade": "G",
            "class_section": "A",
            "parent_id": "PAR-E2E-1",
        },
    )
    expect(r2.status_code == 409, f"duplicate → 409 (got {r2.status_code})")

    # ── PATCH student ---------------------------------------------------------
    section("PATCH /students/{id}")
    r = client.patch(
        "/api/v1/students/STU-E2E-1",
        json={"grade": "Grade 10", "is_active": True, "photo_initial": "T"},
    )
    expect(r.status_code == 200, "patch 200")
    body = r.json()
    expect(body["grade"] == "Grade 10", "grade updated")
    expect(body["photo_initial"] == "T", "photo_initial updated")

    r404 = client.patch("/api/v1/students/NOPE", json={"grade": "X"})
    expect(r404.status_code == 404, "patch unknown → 404")

    # ── Seed rich profile data -----------------------------------------------
    section("Seed attendance, bracelet, notifications, incidents")
    today = datetime.now(timezone.utc).date()

    # Build 10-day streak of PRESENT + today PRESENT
    for offset in range(0, 10):
        d = today - timedelta(days=offset)
        seed_data.attendance_records.append(
            DailyAttendance(
                student_id="STU-E2E-1",
                date=d,
                status=AttendanceStatus.PRESENT,
                arrival_time=datetime.combine(d, datetime.min.time()).replace(
                    hour=7, minute=50, tzinfo=timezone.utc
                ),
                departure_time=datetime.combine(d, datetime.min.time()).replace(
                    hour=14, minute=15, tzinfo=timezone.utc
                ),
                last_seen_zone=zone_id,
            )
        )
    # One absent day at offset 11 (breaks streak later)
    seed_data.attendance_records.append(
        DailyAttendance(
            student_id="STU-E2E-1",
            date=today - timedelta(days=11),
            status=AttendanceStatus.ABSENT,
        )
    )
    # One LATE day at offset 12 (still counts toward monthly present)
    seed_data.attendance_records.append(
        DailyAttendance(
            student_id="STU-E2E-1",
            date=today - timedelta(days=12),
            status=AttendanceStatus.LATE,
            last_seen_zone=zone_id,
        )
    )

    # Bracelet (low battery)
    seed_data.bracelets.append(
        Bracelet(
            bracelet_id="BR-E2E-1",
            student_id="STU-E2E-1",
            mac_address="AA:BB:CC:DD:EE:01",
            battery_level=12,
            is_active=True,
            last_seen_zone=zone_id,
            last_seen_at=datetime.now(timezone.utc),
            firmware_version="2.1.0",
            notes="Test bracelet",
        )
    )

    # Notifications (2 unread, 1 read, some for parent, some for student)
    now = datetime.now(timezone.utc)
    seed_data.notifications.extend(
        [
            NotificationMessage(
                notification_id="N1",
                parent_id="PAR-E2E-1",
                student_id="STU-E2E-1",
                message="Child arrived at school",
                notification_type="attendance",
                sent_at=now - timedelta(hours=1),
                read=False,
            ),
            NotificationMessage(
                notification_id="N2",
                parent_id="PAR-E2E-1",
                student_id="STU-E2E-1",
                message="Safety alert: corridor crowding",
                notification_type="safety",
                sent_at=now - timedelta(hours=2),
                read=False,
            ),
            NotificationMessage(
                notification_id="N3",
                parent_id="PAR-E2E-1",
                student_id="STU-E2E-1",
                message="Monthly report ready",
                notification_type="info",
                sent_at=now - timedelta(days=1),
                read=True,
            ),
        ]
    )

    # Open critical incident in last-seen zone → safety = critical
    seed_data.incidents.append(
        SafetyIncident(
            incident_id="INC-E2E-1",
            zone_id=zone_id,
            severity=IncidentSeverity.CRITICAL,
            description="Unauthorized access test",
            detected_at=now,
            resolved=False,
        )
    )

    # ── GET profile -----------------------------------------------------------
    section("GET /students/{id}/profile")
    r = client.get("/api/v1/students/STU-E2E-1/profile")
    expect(r.status_code == 200, "status=200")
    d = r.json()

    expect(d["student_id"] == "STU-E2E-1", "student_id echoed")
    expect(d["grade"] == "Grade 10", "grade reflects PATCH")
    expect(d["today_status"] == "present", "today = present")
    expect(d["arrival_time"] is not None, "arrival_time present")
    expect(d["departure_time"] is not None, "departure_time present")
    expect(d["last_seen_zone"] == zone_id, "last_seen_zone from today's record")
    expect(d["last_seen_zone_label"] == zone_label, "zone label resolved")
    expect(d["attendance_streak"] == 10, f"streak=10 (got {d['attendance_streak']})")
    expect(len(d["weekly_attendance"]) == 7, "weekly has 7 days")
    expect(len(d["recent_attendance"]) == 30, "30d history has 30 entries")
    # Present+late in last 30 days = 11 (10 present + 1 late), total recorded = 12
    expect(
        d["last_30_days_present"] == 11,
        f"30d present count=11 (got {d['last_30_days_present']})",
    )
    expect(
        d["last_30_days_total"] == 12,
        f"30d total recorded=12 (got {d['last_30_days_total']})",
    )
    expect(
        abs(d["monthly_attendance_pct"] - round((11 / 12) * 100, 1)) < 0.1,
        f"monthly % ≈ 91.7 (got {d['monthly_attendance_pct']})",
    )
    expect(d["bracelet"] is not None, "bracelet attached")
    expect(d["bracelet"]["low_battery"] is True, "low_battery flag set")
    expect(d["bracelet"]["battery_level"] == 12, "battery_level=12")
    expect(d["bracelet"]["last_seen_zone_label"] == zone_label, "bracelet zone label")
    expect(len(d["notifications"]) == 3, f"3 notifications (got {len(d['notifications'])})")
    expect(d["unread_notifications"] == 2, f"2 unread (got {d['unread_notifications']})")
    expect(
        d["safety_status"] == "critical",
        f"safety_status=critical (got {d['safety_status']})",
    )
    expect(
        d["open_incidents_in_last_zone"] == 1,
        f"1 open incident (got {d['open_incidents_in_last_zone']})",
    )

    # Profile for unknown student → 404
    r404 = client.get("/api/v1/students/NOPE/profile")
    expect(r404.status_code == 404, "profile unknown → 404")

    # ── DELETE cascades to bracelet ------------------------------------------
    section("DELETE /students/{id} cascade")
    r = client.delete("/api/v1/students/STU-E2E-1")
    expect(r.status_code == 204, "delete 204")
    expect(
        not any(b.bracelet_id == "BR-E2E-1" for b in seed_data.bracelets),
        "bracelet removed by cascade",
    )

    r404 = client.delete("/api/v1/students/STU-E2E-1")
    expect(r404.status_code == 404, "double delete → 404")

    print("\n✅ All student profile + CRUD assertions passed.")


if __name__ == "__main__":
    main()
