from datetime import datetime, timedelta, timezone
import json

from sqlalchemy import select

from app.core.config import settings
from app.db import models as orm
from app.models import EngagementSnapshot, EngagementState
from app.services import seed_data
from app.services.retention import purge_expired_bracelet_readings


def test_student_delete_erases_relational_memory_and_feedback_file(client, db_session_factory, monkeypatch, tmp_path):
    seed_data.populate()
    student_id = "ERASE-TEST-STUDENT"
    with db_session_factory() as db:
        db.add(orm.Student(
            student_id=student_id, school_id="DEMO-SCHOOL-001",
            name="Temporary Erasure Student", grade="G8", class_section="ER",
            parent_id="P-ERASE",
        ))
        db.commit()
    monkeypatch.setattr(settings, "video_log_dir", str(tmp_path))
    log_path = tmp_path / "agent_performance.jsonl"
    log_path.write_text(
        json.dumps({"feedback_id": "FB-ERASE", "student_id": student_id, "teacher_notes": "private"}) + "\n"
        + json.dumps({"feedback_id": "FB-KEEP", "student_id": "OTHER-STUDENT"}) + "\n",
        encoding="utf-8",
    )
    seed_data.engagement_snapshots.append(EngagementSnapshot(
        student_id=student_id,
        recorded_at=datetime.now(timezone.utc),
        state=EngagementState.ENGAGED,
        score=0.9,
        session_id="ERASE-SESSION",
        zone_id="zone-classroom-1a",
        audio_context=None,
        audio_visual_mismatch=False,
    ))

    with db_session_factory() as db:
        student = db.get(orm.Student, student_id)
        principal = db.scalar(select(orm.User).where(orm.User.username == "principal"))
        db.add(orm.Notification(
            notification_id="NOTIF-ERASE", parent_id=student.parent_id,
            student_id=student_id, message="private notification",
            notification_type="attendance", sent_at=datetime.now(timezone.utc),
        ))
        db.add(orm.AgentFeedbackRecord(
            feedback_id="FB-ERASE-DB", session_id="ERASE-SESSION", student_id=student_id,
            predicted_state="engaged", confirmed_state="engaged",
            teacher_notes="private teacher note", recorded_at=datetime.now(timezone.utc),
        ))
        db.add(orm.Bracelet(
            bracelet_id="BR-ERASE", student_id=student_id,
            mac_address="AA:BB:CC:DD:EE:FA", battery_level=90,
        ))
        db.flush()
        db.add(orm.BraceletReading(
            bracelet_id="BR-ERASE", student_id=student_id, zone_id="zone-classroom-1a",
            recorded_at=datetime.now(timezone.utc), battery_level=90,
        ))
        db.add(orm.ParentStudentLink(
            user_id=principal.id, student_id=student_id, school_id=student.school_id,
            verified_by_user_id=principal.id, verified_at=datetime.now(timezone.utc),
            verification_method="school_records", is_active=True,
        ))
        db.add(orm.ParentInvitation(
            school_id=student.school_id, student_id=student_id,
            invited_username="erasure-parent", full_name="Erasure Parent",
            token_hash="e" * 64, invited_by_user_id=principal.id,
            verification_method="school_records", created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        db.commit()

    response = client.delete(f"/api/v1/students/{student_id}")
    assert response.status_code == 204

    with db_session_factory() as db:
        assert db.get(orm.Student, student_id) is None
        assert db.scalar(select(orm.AttendanceRecord.id).where(orm.AttendanceRecord.student_id == student_id)) is None
        assert db.scalar(select(orm.Notification.notification_id).where(orm.Notification.student_id == student_id)) is None
        assert db.scalar(select(orm.AgentFeedbackRecord.feedback_id).where(orm.AgentFeedbackRecord.student_id == student_id)) is None
        assert db.scalar(select(orm.BraceletReading.id).where(orm.BraceletReading.student_id == student_id)) is None
        assert db.scalar(select(orm.Bracelet.bracelet_id).where(orm.Bracelet.student_id == student_id)) is None
        assert db.scalar(select(orm.ParentStudentLink.id).where(orm.ParentStudentLink.student_id == student_id)) is None
        assert db.scalar(select(orm.ParentInvitation.id).where(orm.ParentInvitation.student_id == student_id)) is None
        audit = db.scalar(select(orm.StudentErasureAudit).order_by(orm.StudentErasureAudit.id.desc()))
        assert audit is not None
        assert audit.school_id == "DEMO-SCHOOL-001"
        assert audit.deleted_notification_count >= 1
        assert audit.deleted_feedback_count >= 1
        assert audit.deleted_bracelet_reading_count == 1
        assert audit.deleted_engagement_snapshot_count >= 1
        assert audit.deleted_feedback_log_count == 1
        assert not hasattr(audit, "student_id")

    assert student_id not in log_path.read_text(encoding="utf-8")
    assert "OTHER-STUDENT" in log_path.read_text(encoding="utf-8")
    assert all(item.student_id != student_id for item in seed_data.engagement_snapshots)


def test_student_erasure_is_school_scoped_and_requires_principal(client, auth_headers, db_session_factory):
    seed_data.populate()
    # A teacher cannot invoke the destructive erasure operation.
    from fastapi.testclient import TestClient
    from app.main import app
    teacher_client = TestClient(app, headers=auth_headers("teacher"))
    assert teacher_client.delete("/api/v1/students/STU-2024-0847").status_code == 403
    assert client.delete("/api/v1/students/NOT-A-STUDENT").status_code == 404

    with db_session_factory() as db:
        db.add(orm.School(school_id="FOREIGN-ERASURE-SCHOOL", name="Foreign School", is_active=True))
        db.flush()
        db.add(orm.Student(
            student_id="FOREIGN-ERASURE-STUDENT", school_id="FOREIGN-ERASURE-SCHOOL",
            name="Foreign Student", grade="G8", class_section="A", parent_id="PRIVATE-PARENT",
        ))
        db.commit()
    assert client.delete("/api/v1/students/FOREIGN-ERASURE-STUDENT").status_code == 404
    with db_session_factory() as db:
        assert db.get(orm.Student, "FOREIGN-ERASURE-STUDENT") is not None


def test_bracelet_retention_purges_readings_older_than_30_days(db_session_factory):
    seed_data.populate()
    now = datetime.now(timezone.utc)
    with db_session_factory() as db:
        db.add(orm.Bracelet(
            bracelet_id="BR-RETENTION", student_id="STU-2024-0856",
            mac_address="AA:BB:CC:DD:EE:FB", battery_level=80,
        ))
        db.flush()
        db.add_all([
            orm.BraceletReading(
                bracelet_id="BR-RETENTION", student_id="STU-2024-0856",
                zone_id="zone-classroom-1a", recorded_at=now - timedelta(days=30, seconds=1),
                battery_level=80,
            ),
            orm.BraceletReading(
                bracelet_id="BR-RETENTION", student_id="STU-2024-0856",
                zone_id="zone-classroom-1a", recorded_at=now - timedelta(days=29),
                battery_level=75,
            ),
        ])
        db.commit()
        deleted = purge_expired_bracelet_readings(db, now=now)
        assert deleted == 1
        remaining = db.scalars(select(orm.BraceletReading).where(
            orm.BraceletReading.bracelet_id == "BR-RETENTION"
        )).all()
        assert len(remaining) == 1
        assert remaining[0].recorded_at > now - timedelta(days=30)


def test_bracelet_ping_persists_reading_and_history_is_limited_to_30_days(client, db_session_factory):
    seed_data.populate()
    response = client.post(
        "/api/v1/bracelets/BR-0001/ping",
        json={"zone_id": "zone-cafeteria", "battery_level": 61},
    )
    assert response.status_code == 200
    history = client.get("/api/v1/bracelets/BR-0001/readings")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["zone_id"] == "zone-cafeteria"
    assert client.get("/api/v1/bracelets/BR-0001/readings?days=31").status_code == 422
    assert client.delete("/api/v1/bracelets/BR-0001").status_code == 204
    with db_session_factory() as db:
        assert db.scalar(select(orm.BraceletReading.id).where(
            orm.BraceletReading.bracelet_id == "BR-0001"
        )) is None


def test_ollama_settings_have_local_endpoint_and_deterministic_default(monkeypatch):
    from app.core.config import Settings
    monkeypatch.delenv("SCHOOLSMARTEYE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    config = Settings(_env_file=None)
    assert config.schoolsmarteye_llm_provider == "deterministic"
    assert config.ollama_base_url == "http://127.0.0.1:11434"
    assert config.ollama_model == ""
    assert config.ollama_timeout_seconds == 12
    assert config.bracelet_reading_retention_days == 30

    from app.services import llm_agent_runtime
    assert llm_agent_runtime._ollama_chat_url() == "http://127.0.0.1:11434/api/chat"
