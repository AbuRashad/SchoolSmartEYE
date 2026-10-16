"""Persisted operational data, SSI history trends, attendance risk and agent feedback."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.db import models as orm
from app.services import attendance_risk, seed_data, ssi_history

API = "/api/v1"


@pytest.fixture()
def seeded(db_session_factory):
    seed_data.populate()
    return db_session_factory


def test_operational_seed_is_persisted_and_idempotent(seeded) -> None:
    with seeded() as db:
        assert db.query(orm.Zone).count() == 12
        assert db.query(orm.Camera).count() == 12
        assert db.query(orm.Incident).count() == 5
        assert db.query(orm.SSISnapshot).count() == 30
        assert db.query(orm.Drill).count() == 3
        assert db.query(orm.AgentFeedbackRecord).count() == 3
        assert seed_data.seed_operational(db) is False
        assert db.query(orm.Zone).count() == 12


def test_zones_endpoint_reads_from_db(client, seeded) -> None:
    zones = client.get(f"{API}/zones").json()
    assert len(zones) == 12
    assert zones[0]["zone_id"] == "zone-main-gate"


def test_ssi_history_trend_and_anomaly(db_session_factory) -> None:
    now = datetime.now(timezone.utc)
    with db_session_factory() as db:
        for i in range(10):
            val = 60.0 + i * 2
            if i == 5:
                val = 20.0
            ssi_history.record_snapshot(db, val, recorded_at=now - timedelta(days=9 - i))
        summary = ssi_history.summarize(db, 30)
    assert summary["trend"] == "improving"
    assert [a["ssi"] for a in summary["anomalies"]] == [20.0]


def test_ssi_history_insufficient_data(db_session_factory) -> None:
    with db_session_factory() as db:
        assert ssi_history.summarize(db)["trend"] == "insufficient_data"


def test_ssi_endpoints_use_stored_history(anon_client, db_session_factory) -> None:
    seed_data.populate()
    h = anon_client.get(f"{API}/ssi/history").json()
    assert len(h["scores"]) == 30 and h["trend"] in {"improving", "stable", "declining"}
    assert anon_client.get(f"{API}/ssi/live").status_code == 200
    anon_client.get(f"{API}/ssi/live")  # throttled: second call must not add another row
    with db_session_factory() as db:
        live = db.query(orm.SSISnapshot).filter_by(source="live").count()
    assert live == 1
    assert anon_client.get(f"{API}/dashboard/summary").json()["ssiTrend"]


def test_attendance_risk_scoring(db_session_factory) -> None:
    today = date.today()

    def rec(offset: int, status: str) -> orm.AttendanceRecord:
        return orm.AttendanceRecord(student_id="S", date=today - timedelta(days=offset), status=status)

    healthy = attendance_risk.score_records([rec(i, "present") for i in range(10)])
    assert healthy["risk_level"] == "low" and healthy["factors"] == []
    # Newer days absent, older present -> chronic + streak + deterioration
    bad = attendance_risk.score_records([rec(i, "absent" if i < 5 else "present") for i in range(10)])
    assert bad["risk_level"] == "high"
    assert bad["consecutive_absences"] == 5 and bad["factors"]
    assert attendance_risk.score_records([])["risk_level"] == "low"


def test_risk_endpoints_require_teacher_and_rank(anon_client, client, seeded) -> None:
    assert anon_client.get(f"{API}/risk/attendance").status_code == 401
    body = client.get(f"{API}/risk/attendance").json()
    assert body["total"] == 10
    scores = [s["risk_score"] for s in body["students"]]
    assert scores == sorted(scores, reverse=True)
    sid = body["students"][0]["student_id"]
    assert client.get(f"{API}/risk/attendance/{sid}").status_code == 200
    assert client.get(f"{API}/risk/attendance/NOPE").status_code == 404


def test_agent_feedback_requires_teacher_and_persists(anon_client, auth_headers, seeded) -> None:
    payload = {
        "session_id": "SES-X", "student_id": "STU-2024-0847",
        "predicted_state": "distracted", "confirmed_state": "engaged",
    }
    assert anon_client.post(f"{API}/agent/feedback", json=payload).status_code == 401
    r = anon_client.post(f"{API}/agent/feedback", json=payload, headers=auth_headers("teacher"))
    assert r.status_code == 201
    with seeded() as db:
        assert db.get(orm.AgentFeedbackRecord, r.json()["feedback_id"]) is not None
    # Public reads stay public
    assert anon_client.get(f"{API}/agent/feedback/metrics").json()["total_feedback"] == 4
    assert anon_client.get(f"{API}/agent/insights").status_code == 200


def test_feedback_calibrates_and_shapes_recommendations(anon_client, auth_headers, seeded) -> None:
    for i in range(2):
        anon_client.post(
            f"{API}/agent/feedback",
            json={"session_id": f"S{i}", "student_id": "STU-2024-0847",
                  "predicted_state": "drowsy", "confirmed_state": "engaged"},
            headers=auth_headers("teacher"),
        )
    cal = anon_client.get(f"{API}/agent/feedback/metrics").json()["calibration"]
    assert cal["drowsy"]["low_confidence"] is True
    rec = anon_client.get(f"{API}/agent/recommendations/STU-2024-0847").json()
    assert rec["recommendations"] and rec["confidence_notes"]
    assert anon_client.get(f"{API}/agent/recommendations/NOPE").status_code == 404
