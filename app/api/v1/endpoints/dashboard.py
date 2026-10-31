from __future__ import annotations

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException
from starlette.websockets import WebSocketState

from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.api.deps import _user_from_token, _check_roles, get_current_school_id, require_teacher, resolve_school_scope
from app.core.governance_layer import Role
from app.services import ssi_history
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
service = DashboardService()


class DashboardConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def send_snapshot(self, websocket: WebSocket) -> None:
        await websocket.send_json(service.get_snapshot())

    async def broadcast_snapshot(self) -> None:
        stale_connections: list[WebSocket] = []
        snapshot = service.get_snapshot()
        for connection in self.active_connections:
            try:
                if connection.client_state is WebSocketState.CONNECTED:
                    await connection.send_json(snapshot)
                else:
                    stale_connections.append(connection)
            except RuntimeError:
                stale_connections.append(connection)
            except WebSocketDisconnect:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


manager = DashboardConnectionManager()

def _dashboard_unavailable(school_id: str) -> None:
    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_DASHBOARD_UNAVAILABLE",
            "message": "Dashboard feeds are paused until their live and cached sources are school-scoped.",
            "school_id": school_id,
        },
    )



@router.get("/summary", dependencies=[Depends(require_teacher)])
def dashboard_summary(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> dict[str, object]:
    _dashboard_unavailable(school_id)
    summary = service.get_summary()
    summary["ssiTrend"] = ssi_history.summarize(db, 30)["trend"]
    return summary


@router.get("/alerts", dependencies=[Depends(require_teacher)])
def dashboard_alerts(school_id: str = Depends(get_current_school_id)) -> list[dict[str, str]]:
    _dashboard_unavailable(school_id)
    return service.get_alerts()


@router.get("/heatmap", dependencies=[Depends(require_teacher)])
def dashboard_heatmap(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    _dashboard_unavailable(school_id)
    return service.get_heatmap()


@router.get("/live", dependencies=[Depends(require_teacher)])
def dashboard_live(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    """REST polling fallback; disabled until the snapshot is tenant-scoped."""
    _dashboard_unavailable(school_id)
    return service.get_snapshot()


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, access_token: str | None = Query(default=None)) -> None:
    # WebSocket clients cannot set Authorization headers in the browser API.
    # Validate the short-lived JWT before accepting or sending any dashboard data.
    try:
        with SessionLocal() as db:
            user = _user_from_token(access_token, db)
            _check_roles(user, (Role.TEACHER,))
            resolve_school_scope(db, user)
    except HTTPException as exc:
        await websocket.close(code=4401 if exc.status_code == 401 else 4403)
        return
    # The process-global manager broadcasts a shared snapshot to every client.
    # Until it is partitioned by verified school membership, refuse the socket.
    await websocket.close(code=1013, reason="School-scoped dashboard feed is not available yet")
    return
    await manager.connect(websocket)
    try:
        await manager.send_snapshot(websocket)
        while True:
            message = await websocket.receive_text()
            if message in {"refresh", "subscribe", "ping"}:
                await manager.send_snapshot(websocket)
            elif message == "broadcast":
                await manager.broadcast_snapshot()
            elif message == "close":
                await websocket.close()
                break
    except WebSocketDisconnect:
        return
    finally:
        manager.disconnect(websocket)
