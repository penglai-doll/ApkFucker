from __future__ import annotations

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


class WebSocketHub:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    @property
    def connections(self) -> tuple[WebSocket, ...]:
        return tuple(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def handle(self, websocket: WebSocket) -> None:
        await self.connect(websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                if str(payload.get("type", "")).strip().lower() == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            self.disconnect(websocket)

    async def broadcast(self, payload: dict[str, object]) -> None:
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except WebSocketDisconnect:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)
