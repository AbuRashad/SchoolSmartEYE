from __future__ import annotations

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException
from starlette.websockets import WebSocketState

from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.api.deps import _user_from_token, _check_roles, require_teacher
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


@router.get("/summary", dependencies=[Depends(require_teacher)])
def dashboard_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    summary = service.get_summary()
    summary["ssiTrend"] = ssi_history.summarize(db, 30)["trend"]
    return summary


@router.get("/alerts", dependencies=[Depends(require_teacher)])
def dashboard_alerts() -> list[dict[str, str]]:
    return service.get_alerts()


@router.get("/heatmap", dependencies=[Depends(require_teacher)])
def dashboard_heatmap() -> dict[str, object]:
    return service.get_heatmap()


@router.get("/live", dependencies=[Depends(require_teacher)])
def dashboard_live() -> dict[str, object]:
    """REST polling fallback — returns the full dashboard snapshot as JSON."""
    return service.get_snapshot()


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, access_token: str | None = Query(default=None)) -> None:
    # WebSocket clients cannot set Authorization headers in the browser API.
    # Validate the short-lived JWT before accepting or sending any dashboard data.
    try:
        with SessionLocal() as db:
            user = _user_from_token(access_token, db)
            _check_roles(user, (Role.TEACHER,))
    except HTTPException as exc:
        await websocket.close(code=4401 if exc.status_code == 401 else 4403)
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
