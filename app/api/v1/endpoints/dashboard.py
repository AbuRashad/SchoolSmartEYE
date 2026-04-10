from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
        for connection in self.active_connections:
            try:
                await connection.send_json(service.get_snapshot())
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


manager = DashboardConnectionManager()


@router.get("/summary")
def dashboard_summary() -> dict[str, object]:
    return service.get_summary()


@router.get("/alerts")
def dashboard_alerts() -> list[dict[str, str]]:
    return service.get_alerts()


@router.get("/heatmap")
def dashboard_heatmap() -> dict[str, object]:
    return service.get_heatmap()


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket) -> None:
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
        manager.disconnect(websocket)
        return
