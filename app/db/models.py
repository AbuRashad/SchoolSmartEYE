"""SQLAlchemy ORM models for persistent school data."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    hashed_password: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16))  # teacher | principal | ministry
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
