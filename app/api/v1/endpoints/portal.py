"""School-scoped portal boundary.

The previous endpoint returned a hard-coded student's personal data to any
teacher account. Until authenticated student/parent identity linking is
implemented, return only the verified school scope and an explicit unavailable
state; never fabricate or disclose a student profile.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_teacher, resolve_school_scope
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/portal", tags=["portal"], dependencies=[Depends(require_teacher)])


@router.get("/student")
def get_student(
    school_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    scope = resolve_school_scope(db, current_user, school_id)
    return {
        "school_id": scope,
        "available": False,
        "status": "identity_link_required",
        "message": (
            "Student portal data is unavailable until the authenticated account "
            "is explicitly linked to a student within this school."
        ),
        "student": None,
    }
