"""Early-warning risk scoring from stored attendance history."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as orm

_ABSENT = "absent"
_LATE = "late"


def _risk_level(score: float) -> str:
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def score_records(records: list[orm.AttendanceRecord], window_days: int = 14) -> dict[str, object]:
    """Score one student's records (any order). Score is in [0, 1]."""
    today = date.today()
    since = today - timedelta(days=window_days)
    recs = sorted(
        (r for r in records if since <= r.date <= today),
        key=lambda r: r.date,
    )
    if not recs:
        return {"risk_score": 0.0, "risk_level": "low", "factors": [], "records": 0}
    recent = recs
    n = len(recent)
    absent_rate = sum(r.status == _ABSENT for r in recent) / n
    late_rate = sum(r.status == _LATE for r in recent) / n

    streak = 0
    for r in reversed(recs):
        if r.status != _ABSENT:
            break
        streak += 1

    # Compare the recent half to the earlier half: a rising absence rate is the anomaly.
    half = n // 2
    older, newer = recent[:half], recent[half:]
    rate = lambda rs: (sum(r.status == _ABSENT for r in rs) / len(rs)) if rs else 0.0  # noqa: E731
    deterioration = max(0.0, rate(newer) - rate(older)) if half else 0.0

    score = min(1.0, 1.5 * absent_rate + 0.5 * late_rate + 0.15 * min(streak, 3) + 0.5 * deterioration)
    factors: list[str] = []
    if absent_rate >= 0.2:
        factors.append(f"chronic absence: {absent_rate:.0%} of last {n} days")
    if late_rate >= 0.3:
        factors.append(f"frequent lateness: {late_rate:.0%} of last {n} days")
    if streak >= 2:
        factors.append(f"{streak} consecutive absences")
    if deterioration >= 0.2:
        factors.append("absence rate rising versus earlier period")
    return {
        "risk_score": round(score, 3),
        "risk_level": _risk_level(score),
        "factors": factors,
        "records": n,
        "absent_rate": round(absent_rate, 3),
        "late_rate": round(late_rate, 3),
        "consecutive_absences": streak,
    }


def student_risk(db: Session, student_id: str, window_days: int = 14) -> dict[str, object]:
    since = date.today() - timedelta(days=window_days * 2)
    recs = list(
        db.scalars(
            select(orm.AttendanceRecord).where(
                orm.AttendanceRecord.student_id == student_id,
                orm.AttendanceRecord.date >= since,
            )
        )
    )
    return {"student_id": student_id, **score_records(recs, window_days)}


def school_risk(db: Session, window_days: int = 14) -> list[dict[str, object]]:
    """All active students ranked by descending risk."""
    since = date.today() - timedelta(days=window_days * 2)
    by_student: dict[str, list[orm.AttendanceRecord]] = {}
    for r in db.scalars(select(orm.AttendanceRecord).where(orm.AttendanceRecord.date >= since)):
        by_student.setdefault(r.student_id, []).append(r)
    students = {s.student_id: s for s in db.scalars(select(orm.Student).where(orm.Student.is_active))}
    out = []
    for sid, s in students.items():
        out.append({"student_id": sid, "name": s.name, **score_records(by_student.get(sid, []), window_days)})
    return sorted(out, key=lambda x: x["risk_score"], reverse=True)
