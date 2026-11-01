"""Verified parent identity links and minimal parent-facing student views."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_parent, require_principal
from app.db import models as orm
from app.db.session import get_db

router = APIRouter(prefix="/parent", tags=["parent-identity"])


class ParentLinkCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    parent_username: str = Field(min_length=1, max_length=64)
    verification_method: Literal["school_records", "in_person", "official_email"]


class ParentLinkOut(BaseModel):
    student_id: str
    parent_username: str
    verification_method: str
    verified_at: str
    is_active: bool


class ParentStudentOut(BaseModel):
    student_id: str
    name: str
    grade: str
    class_section: str


class ParentAttendanceOut(BaseModel):
    date: str
    status: str
    arrival_time: str | None
    departure_time: str | None


class ParentNotificationOut(BaseModel):
    notification_id: str
    message: str
    notification_type: str
    sent_at: str
    read: bool


class ParentStudentSummary(BaseModel):
    student: ParentStudentOut
    attendance: list[ParentAttendanceOut]
    notifications: list[ParentNotificationOut]
    data_notice: str = (
        "Attendance and notifications are persisted school records. "
        "Live location and camera-derived safety status are not exposed by this endpoint."
    )


def _verified_link_query(user_id: int, student_id: str | None = None):
    query = (
        select(orm.ParentStudentLink, orm.Student)
        .join(
            orm.Student,
            (orm.Student.student_id == orm.ParentStudentLink.student_id)
            & (orm.Student.school_id == orm.ParentStudentLink.school_id),
        )
        .where(
            orm.ParentStudentLink.user_id == user_id,
            orm.ParentStudentLink.is_active.is_(True),
            orm.ParentStudentLink.verified_at.is_not(None),
            orm.ParentStudentLink.verified_by_user_id.is_not(None),
        )
    )
    if student_id is not None:
        query = query.where(orm.Student.student_id == student_id)
    return query


@router.post(
    "/links",
    response_model=ParentLinkOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_principal)],
)
def create_parent_link(
    payload: ParentLinkCreate,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
    principal: orm.User = Depends(require_principal),
) -> ParentLinkOut:
    """A principal attests that an existing parent login belongs to this student.

    Identity verification happens outside this API against official school records.
    The client cannot supply user_id, school_id, verifier, or verification timestamp.
    """
    student = db.scalar(
        select(orm.Student).where(
            orm.Student.student_id == payload.student_id,
            orm.Student.school_id == school_id,
        )
    )
    parent = db.scalar(
        select(orm.User).where(
            orm.User.username == payload.parent_username,
            orm.User.role == "parent",
            orm.User.is_active.is_(True),
        )
    )
    if student is None or parent is None:
        raise HTTPException(status_code=404, detail="Student or eligible parent account not found")

    now = datetime.now(timezone.utc)
    link = db.scalar(
        select(orm.ParentStudentLink).where(
            orm.ParentStudentLink.user_id == parent.id,
            orm.ParentStudentLink.student_id == student.student_id,
            orm.ParentStudentLink.school_id == school_id,
        )
    )
    if link is not None and link.is_active:
        raise HTTPException(status_code=409, detail="An active verified parent link already exists")

    if link is None:
        link = orm.ParentStudentLink(
            user_id=parent.id,
            student_id=student.student_id,
            school_id=school_id,
            verified_by_user_id=principal.id,
            verified_at=now,
            verification_method=payload.verification_method,
            is_active=True,
        )
        db.add(link)
    else:
        link.verified_by_user_id = principal.id
        link.verified_at = now
        link.verification_method = payload.verification_method
        link.is_active = True

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Parent link could not be created") from None

    return ParentLinkOut(
        student_id=student.student_id,
        parent_username=parent.username,
        verification_method=link.verification_method,
        verified_at=link.verified_at.isoformat(),
        is_active=link.is_active,
    )


@router.delete(
    "/links/{student_id}/{parent_username}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_principal)],
)
def revoke_parent_link(
    student_id: str,
    parent_username: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> Response:
    parent = db.scalar(select(orm.User).where(orm.User.username == parent_username, orm.User.role == "parent"))
    if parent is None:
        raise HTTPException(status_code=404, detail="Verified parent link not found")
    link = db.scalar(
        select(orm.ParentStudentLink).where(
            orm.ParentStudentLink.user_id == parent.id,
            orm.ParentStudentLink.student_id == student_id,
            orm.ParentStudentLink.school_id == school_id,
            orm.ParentStudentLink.is_active.is_(True),
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Verified parent link not found")
    link.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/students", response_model=list[ParentStudentOut])
def list_linked_students(
    parent: orm.User = Depends(require_parent),
    db: Session = Depends(get_db),
) -> list[ParentStudentOut]:
    rows = db.execute(_verified_link_query(parent.id).order_by(orm.Student.name)).all()
    return [
        ParentStudentOut(
            student_id=student.student_id,
            name=student.name,
            grade=student.grade,
            class_section=student.class_section,
        )
        for _, student in rows
    ]


@router.get("/students/{student_id}/summary", response_model=ParentStudentSummary)
def get_linked_student_summary(
    student_id: str,
    parent: orm.User = Depends(require_parent),
    db: Session = Depends(get_db),
) -> ParentStudentSummary:
    row = db.execute(_verified_link_query(parent.id, student_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")

    _, student = row
    since = date.today() - timedelta(days=6)
    attendance_rows = db.scalars(
        select(orm.AttendanceRecord)
        .join(orm.Student, orm.Student.student_id == orm.AttendanceRecord.student_id)
        .where(
            orm.Student.student_id == student_id,
            orm.Student.school_id == student.school_id,
            orm.AttendanceRecord.date >= since,
        )
        .order_by(orm.AttendanceRecord.date.desc())
        .limit(7)
    ).all()
    notification_rows = db.scalars(
        select(orm.Notification)
        .where(
            orm.Notification.student_id == student_id,
            orm.Notification.parent_id == student.parent_id,
        )
        .order_by(orm.Notification.sent_at.desc())
        .limit(10)
    ).all()

    return ParentStudentSummary(
        student=ParentStudentOut(
            student_id=student.student_id,
            name=student.name,
            grade=student.grade,
            class_section=student.class_section,
        ),
        attendance=[
            ParentAttendanceOut(
                date=item.date.isoformat(),
                status=item.status,
                arrival_time=item.arrival_time.isoformat() if item.arrival_time else None,
                departure_time=item.departure_time.isoformat() if item.departure_time else None,
            )
            for item in attendance_rows
        ],
        notifications=[
            ParentNotificationOut(
                notification_id=item.notification_id,
                message=item.message,
                notification_type=item.notification_type,
                sent_at=item.sent_at.isoformat(),
                read=item.read,
            )
            for item in notification_rows
        ],
    )
