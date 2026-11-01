"""SQLAlchemy ORM models for persistent school data."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Nullable during migration; school-scoped APIs must fail closed for unassigned rows.
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.school_id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    grade: Mapped[str] = mapped_column(String(64))
    class_section: Mapped[str] = mapped_column(String(32))
    parent_id: Mapped[str] = mapped_column(String(64), index=True)
    photo_initial: Mapped[str] = mapped_column(String(4), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    bracelet: Mapped["Bracelet | None"] = relationship(
        back_populates="student", uselist=False, cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Bracelet(Base):
    __tablename__ = "bracelets"

    bracelet_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), unique=True
    )
    mac_address: Mapped[str] = mapped_column(String(32), unique=True)
    battery_level: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    notes: Mapped[str] = mapped_column(String(256), default="")

    student: Mapped[Student] = relationship(back_populates="bracelet")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("student_id", "date", name="uq_attendance_student_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16))  # present | absent | late | unknown
    arrival_time: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    departure_time: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_seen_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    student: Mapped[Student] = relationship(back_populates="attendance_records")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[str] = mapped_column(String(64), index=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(String(512))
    notification_type: Mapped[str] = mapped_column(String(32))
    sent_at: Mapped[datetime] = mapped_column(UTCDateTime)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class School(Base):
    __tablename__ = "schools"

    school_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    hashed_password: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16))  # teacher | principal | ministry | parent
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SchoolMembership(Base):
    __tablename__ = "school_memberships"
    __table_args__ = (UniqueConstraint("user_id", "school_id", name="uq_school_membership_user_school"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.school_id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ParentStudentLink(Base):
    """Audited, school-owned link between a parent login and one student."""

    __tablename__ = "parent_student_links"
    __table_args__ = (
        UniqueConstraint("user_id", "student_id", "school_id", name="uq_parent_student_school_link"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id", ondelete="CASCADE"), index=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.school_id", ondelete="CASCADE"), index=True)
    verified_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    verification_method: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Nullable until legacy zones receive a verified school ownership mapping.
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.school_id"), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(128))
    zone_type: Mapped[str] = mapped_column(String(32))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    floor: Mapped[int] = mapped_column(Integer, default=1)
    grid_x: Mapped[int] = mapped_column(Integer, default=0)
    grid_y: Mapped[int] = mapped_column(Integer, default=0)


class Camera(Base):
    __tablename__ = "cameras"

    camera_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.zone_id"), index=True)
    label: Mapped[str] = mapped_column(String(128))
    width: Mapped[int] = mapped_column(Integer, default=1280)
    height: Mapped[int] = mapped_column(Integer, default=720)
    fps: Mapped[int] = mapped_column(Integer, default=25)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.zone_id"), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(512))
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SSISnapshot(Base):
    """One School Safety Index measurement; the basis for trends and anomalies."""

    __tablename__ = "ssi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nullable while historical snapshots are mapped through a reviewed ownership process.
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.school_id"), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ssi: Mapped[float] = mapped_column(Float)
    anomaly_coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    coherence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attendance_discrepancy: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="live")


class Drill(Base):
    __tablename__ = "drills"

    drill_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Nullable until legacy drills receive verified school ownership.
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.school_id"), nullable=True, index=True)
    drill_type: Mapped[str] = mapped_column(String(32))
    scheduled_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    response_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(String(512), default="")


class AgentFeedbackRecord(Base):
    __tablename__ = "agent_feedback"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    predicted_state: Mapped[str] = mapped_column(String(32))
    confirmed_state: Mapped[str] = mapped_column(String(32))
    teacher_notes: Mapped[str] = mapped_column(String(1024), default="")
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class ParentInvitation(Base):
    """Single-use, school-scoped invitation; only a token hash is persisted."""

    __tablename__ = "parent_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.school_id", ondelete="CASCADE"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id", ondelete="CASCADE"), index=True)
    invited_username: Mapped[str] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verification_method: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
