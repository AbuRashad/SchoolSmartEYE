"""Normalized, tenant-safe schema for the parallel SchoolSmartEYE database.

All tenant-owned records carry organization_id + school_id. Composite foreign
keys prevent accidentally attaching a record to a school in another tenant.
No demo rows or legacy data are created by this metadata.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.nextgen.base import NextBase


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Organization(NextBase, TimestampMixin):
    __tablename__ = "ng_organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(24), nullable=False)  # ministry | school_group | operator
    country_code: Mapped[str | None] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class School(NextBase, TimestampMixin):
    __tablename__ = "ng_schools"
    __table_args__ = (UniqueConstraint("id", "organization_id", name="uq_ng_school_org"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("ng_organizations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(64), default="Africa/Cairo", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_ng_school_org"),
        UniqueConstraint("organization_id", "code", name="uq_ng_school_code"),
    )


class Campus(NextBase, TimestampMixin):
    __tablename__ = "ng_campuses"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_campus_scope"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)


class AppUser(NextBase, TimestampMixin):
    __tablename__ = "ng_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="invited", nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Membership(NextBase, TimestampMixin):
    __tablename__ = "ng_memberships"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("user_id", "organization_id", "school_id", "role", name="uq_ng_membership_scope_role"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("ng_users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # ministry_reader | school_admin | principal | teacher | reviewer
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class Guardian(NextBase, TimestampMixin):
    __tablename__ = "ng_guardians"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_guardian_scope"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_ref: Mapped[str | None] = mapped_column(String(160))  # reference to protected contact vault


class Student(NextBase, TimestampMixin):
    __tablename__ = "ng_students"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("school_id", "student_number", name="uq_ng_student_number"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_student_scope"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    student_number: Mapped[str] = mapped_column(String(64), nullable=False)
    given_name: Mapped[str] = mapped_column(String(100), nullable=False)
    family_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class StudentGuardian(NextBase):
    __tablename__ = "ng_student_guardians"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["student_id", "school_id", "organization_id"], ["ng_students.id", "ng_students.school_id", "ng_students.organization_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["guardian_id", "school_id", "organization_id"], ["ng_guardians.id", "ng_guardians.school_id", "ng_guardians.organization_id"], ondelete="CASCADE"),
        UniqueConstraint("student_id", "guardian_id", name="uq_ng_student_guardian"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("ng_students.id", ondelete="CASCADE"), nullable=False, index=True)
    guardian_id: Mapped[str] = mapped_column(ForeignKey("ng_guardians.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(24), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AcademicClass(NextBase, TimestampMixin):
    __tablename__ = "ng_classes"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("school_id", "academic_year", "class_code", name="uq_ng_class_year_code"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_class_scope"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False)
    class_code: Mapped[str] = mapped_column(String(48), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)


class Enrollment(NextBase, TimestampMixin):
    __tablename__ = "ng_enrollments"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["student_id", "school_id", "organization_id"], ["ng_students.id", "ng_students.school_id", "ng_students.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["class_id", "school_id", "organization_id"], ["ng_classes.id", "ng_classes.school_id", "ng_classes.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("student_id", "class_id", name="uq_ng_enrollment_student_class"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("ng_students.id"), nullable=False, index=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("ng_classes.id"), nullable=False, index=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[Date | None] = mapped_column(Date)


class AttendanceEvent(NextBase):
    __tablename__ = "ng_attendance_events"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        Index("ix_ng_attendance_school_time", "school_id", "occurred_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("ng_students.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)  # check_in | check_out | absent | late | correction
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(100))
    recorded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("ng_users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("school_id", "idempotency_key", name="uq_ng_attendance_idempotency"),
        Index("ix_ng_attendance_school_time", "school_id", "occurred_at"),
    )


class Camera(NextBase, TimestampMixin):
    __tablename__ = "ng_cameras"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["campus_id", "school_id", "organization_id"], ["ng_campuses.id", "ng_campuses.school_id", "ng_campuses.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_camera_scope"),
        UniqueConstraint("school_id", "camera_code", name="uq_ng_camera_code"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    campus_id: Mapped[str | None] = mapped_column(ForeignKey("ng_campuses.id"))
    camera_code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    zone_label: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="provisioned", nullable=False)


class EdgeDevice(NextBase, TimestampMixin):
    __tablename__ = "ng_edge_devices"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["camera_id", "school_id", "organization_id"], ["ng_cameras.id", "ng_cameras.school_id", "ng_cameras.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_edge_scope"),
        UniqueConstraint("school_id", "device_code", name="uq_ng_edge_device_code"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    camera_id: Mapped[str | None] = mapped_column(ForeignKey("ng_cameras.id"))
    device_code: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CameraTelemetry(NextBase):
    __tablename__ = "ng_camera_telemetry"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["camera_id", "school_id", "organization_id"], ["ng_cameras.id", "ng_cameras.school_id", "ng_cameras.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["edge_device_id", "school_id", "organization_id"], ["ng_edge_devices.id", "ng_edge_devices.school_id", "ng_edge_devices.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("school_id", "idempotency_key", name="uq_ng_camera_telemetry_idempotency"),
        Index("ix_ng_camera_telemetry_time", "school_id", "observed_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False)
    camera_id: Mapped[str] = mapped_column(ForeignKey("ng_cameras.id"), nullable=False, index=True)
    edge_device_id: Mapped[str | None] = mapped_column(ForeignKey("ng_edge_devices.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    fps: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    payload_version: Mapped[str] = mapped_column(String(24), default="camera.telemetry.v1", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)


class AIEvent(NextBase):
    __tablename__ = "ng_ai_events"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["camera_id", "school_id", "organization_id"], ["ng_cameras.id", "ng_cameras.school_id", "ng_cameras.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("id", "school_id", "organization_id", name="uq_ng_ai_event_scope"),
        Index("ix_ng_ai_events_school_detected", "school_id", "detected_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False)
    camera_id: Mapped[str | None] = mapped_column(ForeignKey("ng_cameras.id"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_model: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(48), nullable=False)
    data_status: Mapped[str] = mapped_column(String(24), default="unverified", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(255))  # object-storage reference only
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Incident(NextBase, TimestampMixin):
    __tablename__ = "ng_incidents"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["ai_event_id", "school_id", "organization_id"], ["ng_ai_events.id", "ng_ai_events.school_id", "ng_ai_events.organization_id"], ondelete="RESTRICT"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ai_event_id: Mapped[str | None] = mapped_column(ForeignKey("ng_ai_events.id"))
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(Text, nullable=False)


class HumanReview(NextBase):
    __tablename__ = "ng_human_reviews"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["ai_event_id", "school_id", "organization_id"], ["ng_ai_events.id", "ng_ai_events.school_id", "ng_ai_events.organization_id"], ondelete="RESTRICT"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ai_event_id: Mapped[str] = mapped_column(ForeignKey("ng_ai_events.id"), nullable=False, index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("ng_users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)  # confirmed | dismissed | escalated
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MetricObservation(NextBase):
    __tablename__ = "ng_metric_observations"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        UniqueConstraint("school_id", "metric_key", "idempotency_key", name="uq_ng_metric_idempotency"),
        Index("ix_ng_metric_time", "school_id", "metric_key", "observed_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    numeric_value: Mapped[float | None] = mapped_column(Float)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(120))
    data_status: Mapped[str] = mapped_column(String(24), default="unverified", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)


class ConsentRecord(NextBase):
    __tablename__ = "ng_consent_records"
    __table_args__ = (ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(24), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(NextBase):
    __tablename__ = "ng_audit_events"
    __table_args__ = (
        ForeignKeyConstraint(["school_id", "organization_id"], ["ng_schools.id", "ng_schools.organization_id"], ondelete="RESTRICT"),
        Index("ix_ng_audit_scope_time", "organization_id", "school_id", "occurred_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("ng_users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
