"""Secure, one-time parent account invitations."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_principal
from app.core.security import hash_password
from app.db import models as orm
from app.db.session import get_db

router = APIRouter(prefix="/parent/invitations", tags=["parent-invitations"])
INVITATION_TTL = timedelta(hours=48)


class InvitationCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    parent_username: str = Field(min_length=4, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    parent_full_name: str = Field(min_length=2, max_length=128)
    verification_method: Literal["school_records", "in_person", "official_email"]


class InvitationCreated(BaseModel):
    invitation_id: int
    student_id: str
    parent_username: str
    expires_at: str
    invitation_token: str
    delivery_notice: str


class InvitationAccept(BaseModel):
    invitation_token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=12, max_length=128)


class InvitationAccepted(BaseModel):
    username: str
    role: Literal["parent"] = "parent"
    linked_student_id: str


class InvitationAdminOut(BaseModel):
    invitation_id: int
    student_id: str
    parent_username: str
    created_at: str
    expires_at: str
    status: Literal["pending", "accepted", "expired", "revoked"]


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("", response_model=InvitationCreated, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_principal)])
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
    principal: orm.User = Depends(require_principal),
) -> InvitationCreated:
    """Issue a one-time activation token after staff have verified the adult."""
    student = db.scalar(select(orm.Student).where(
        orm.Student.student_id == payload.student_id,
        orm.Student.school_id == school_id,
        orm.Student.is_active.is_(True),
    ))
    if student is None:
        raise HTTPException(status_code=404, detail="Eligible student not found")
    existing = db.scalar(select(orm.User.id).where(
        orm.User.username == payload.parent_username
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Account name is unavailable")
    now = datetime.now(timezone.utc)
    # Supersede pending invitations for this same identity and student.
    pending = db.scalars(select(orm.ParentInvitation).where(
        orm.ParentInvitation.school_id == school_id,
        orm.ParentInvitation.student_id == student.student_id,
        orm.ParentInvitation.invited_username == payload.parent_username,
        orm.ParentInvitation.accepted_at.is_(None),
        orm.ParentInvitation.revoked_at.is_(None),
    )).all()
    for item in pending:
        item.revoked_at = now
    token = secrets.token_urlsafe(32)
    invitation = orm.ParentInvitation(
        school_id=school_id,
        student_id=student.student_id,
        invited_username=payload.parent_username,
        full_name=payload.parent_full_name.strip(),
        token_hash=_token_digest(token),
        invited_by_user_id=principal.id,
        verification_method=payload.verification_method,
        created_at=now,
        expires_at=now + INVITATION_TTL,
    )
    db.add(invitation)
    try:
        db.commit()
        db.refresh(invitation)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invitation could not be issued") from None
    return InvitationCreated(
        invitation_id=invitation.id,
        student_id=student.student_id,
        parent_username=invitation.invited_username,
        expires_at=invitation.expires_at.isoformat(),
        invitation_token=token,
        delivery_notice="Copy this token once and deliver it through a school-approved private channel. It will not be shown again.",
    )


@router.post("/accept", response_model=InvitationAccepted)
def accept_invitation(
    payload: InvitationAccept,
    db: Session = Depends(get_db),
) -> InvitationAccepted:
    """Create the parent login and verified student link atomically."""
    now = datetime.now(timezone.utc)
    invitation = db.scalar(select(orm.ParentInvitation).where(
        orm.ParentInvitation.token_hash == _token_digest(payload.invitation_token)
    ).with_for_update())
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= now
    ):
        raise HTTPException(status_code=400, detail="Invitation is invalid or no longer available")
    student = db.scalar(select(orm.Student).where(
        orm.Student.student_id == invitation.student_id,
        orm.Student.school_id == invitation.school_id,
        orm.Student.is_active.is_(True),
    ))
    school = db.get(orm.School, invitation.school_id)
    inviter = db.get(orm.User, invitation.invited_by_user_id)
    if student is None or school is None or not school.is_active or inviter is None or not inviter.is_active:
        raise HTTPException(status_code=400, detail="Invitation is invalid or no longer available")
    if db.scalar(select(orm.User.id).where(orm.User.username == invitation.invited_username)) is not None:
        raise HTTPException(status_code=409, detail="Account name is unavailable")
    parent = orm.User(
        username=invitation.invited_username,
        full_name=invitation.full_name,
        hashed_password=hash_password(payload.password),
        role="parent",
        is_active=True,
    )
    db.add(parent)
    invitation.accepted_at = now
    try:
        db.flush()
        db.add(orm.ParentStudentLink(
            user_id=parent.id,
            student_id=student.student_id,
            school_id=invitation.school_id,
            verified_by_user_id=invitation.invited_by_user_id,
            verified_at=invitation.created_at,
            verification_method=invitation.verification_method,
            is_active=True,
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invitation could not be accepted") from None
    return InvitationAccepted(username=parent.username, linked_student_id=student.student_id)


@router.get("", response_model=list[InvitationAdminOut],
            dependencies=[Depends(require_principal)])
def list_invitations(
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> list[InvitationAdminOut]:
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(orm.ParentInvitation).where(
        orm.ParentInvitation.school_id == school_id
    ).order_by(orm.ParentInvitation.created_at.desc()).limit(100)).all()
    result = []
    for item in rows:
        state = ("accepted" if item.accepted_at else "revoked" if item.revoked_at
                 else "expired" if item.expires_at <= now else "pending")
        result.append(InvitationAdminOut(
            invitation_id=item.id, student_id=item.student_id,
            parent_username=item.invited_username, created_at=item.created_at.isoformat(),
            expires_at=item.expires_at.isoformat(), status=state,
        ))
    return result


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_principal)])
def revoke_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> None:
    item = db.scalar(select(orm.ParentInvitation).where(
        orm.ParentInvitation.id == invitation_id,
        orm.ParentInvitation.school_id == school_id,
        orm.ParentInvitation.accepted_at.is_(None),
        orm.ParentInvitation.revoked_at.is_(None),
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Pending invitation not found")
    item.revoked_at = datetime.now(timezone.utc)
    db.commit()
