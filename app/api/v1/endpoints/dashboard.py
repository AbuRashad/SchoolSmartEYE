"""Dashboard endpoints fail closed until every feed is school-partitioned."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status

from app.api.deps import (
    _check_roles,
    _user_from_token,
    get_current_school_id,
    require_teacher,
    resolve_school_scope,
)
from app.core.governance_layer import Role
from app.db.session import SessionLocal

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dashboard_unavailable(school_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_DASHBOARD_UNAVAILABLE",
            "message": "Dashboard feeds are paused until their live and cached sources are school-scoped.",
            "school_id": school_id,
        },
    )


@router.get("/summary", dependencies=[Depends(require_teacher)])
def dashboard_summary(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    _dashboard_unavailable(school_id)


@router.get("/alerts", dependencies=[Depends(require_teacher)])
def dashboard_alerts(school_id: str = Depends(get_current_school_id)) -> list[dict[str, str]]:
    _dashboard_unavailable(school_id)


@router.get("/heatmap", dependencies=[Depends(require_teacher)])
def dashboard_heatmap(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    _dashboard_unavailable(school_id)


@router.get("/live", dependencies=[Depends(require_teacher)])
def dashboard_live(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    """REST polling fallback; disabled until the snapshot is tenant-scoped."""
    _dashboard_unavailable(school_id)


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, access_token: str | None = Query(default=None)) -> None:
    # Validate both role and school membership before refusing the shared stream.
    try:
        with SessionLocal() as db:
            user = _user_from_token(access_token, db)
            _check_roles(user, (Role.TEACHER,))
            resolve_school_scope(db, user)
    except HTTPException as exc:
        await websocket.close(code=4401 if exc.status_code == 401 else 4403)
        return

    # The former process-global broadcaster could send the same snapshot to all schools.
    await websocket.close(code=1013, reason="School-scoped dashboard feed is not available yet")
