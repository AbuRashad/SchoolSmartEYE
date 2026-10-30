"""Authentication / authorisation dependencies.

Roles follow the RBAC hierarchy of the governance layer
(`app.core.governance_layer`): Teacher -> Principal -> Ministry. A user may
access an endpoint when their scope level is at least that of the lowest role
listed in `require_roles(...)`.
"""
from __future__ import annotations

from typing import Callable

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.governance_layer import SCOPE_LEVEL, Role
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_str}/auth/login", auto_error=False)

ROLE_BY_NAME: dict[str, Role] = {
    "teacher": Role.TEACHER,
    "principal": Role.PRINCIPAL,
    "ministry": Role.MINISTRY,
}


def role_of(user: User) -> Role | None:
    return ROLE_BY_NAME.get(user.role)


def school_scope(user: User) -> str | None:
    """Return the authenticated user's school, or None for ministry-wide reads."""
    if role_of(user) is Role.MINISTRY:
        return None
    if not user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A school-scoped account is required",
        )
    return user.school_id


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_token(token: str | None, db: Session) -> User:
    if not token:
        raise _unauthorized()
    try:
        claims = decode_access_token(token)
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token") from None
    user = db.scalar(select(User).where(User.username == claims["sub"]))
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    return _user_from_token(token, db)


def get_current_user_header_or_query(
    token: str | None = Depends(oauth2_scheme),
    access_token: str | None = Query(default=None, description="JWT for <img>/<video> tags that cannot send headers"),
    db: Session = Depends(get_db),
) -> User:
    """Like `get_current_user`, but also accepts `?access_token=` (used by MJPEG <img> tags)."""
    return _user_from_token(token or access_token, db)


def _check_roles(user: User, roles: tuple[Role, ...]) -> User:
    user_role = role_of(user)
    if user_role is None or SCOPE_LEVEL[user_role] < min(SCOPE_LEVEL[r] for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action",
        )
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Dependency factory: allow users holding any listed role or a higher one."""
    if not roles:
        raise ValueError("require_roles needs at least one role")

    def _dependency(user: User = Depends(get_current_user)) -> User:
        return _check_roles(user, roles)

    return _dependency


def require_roles_header_or_query(*roles: Role) -> Callable[..., User]:
    def _dependency(user: User = Depends(get_current_user_header_or_query)) -> User:
        return _check_roles(user, roles)

    return _dependency


def require_school_staff(user: User = Depends(get_current_user)) -> User:
    """Require a teacher or principal assigned to one school; never Ministry."""
    if role_of(user) not in {Role.TEACHER, Role.PRINCIPAL} or not user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An authorised school account is required",
        )
    return user


def require_school_principal(user: User = Depends(get_current_user)) -> User:
    """Require an actual school principal; ministry is read-only on school records."""
    if role_of(user) is not Role.PRINCIPAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a school principal may modify school records",
        )
    if not user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A school-scoped account is required",
        )
    return user


require_teacher = require_roles(Role.TEACHER)
require_principal = require_roles(Role.PRINCIPAL)
require_ministry = require_roles(Role.MINISTRY)
require_teacher_stream = require_roles_header_or_query(Role.TEACHER)
