from __future__ import annotations

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


class WebSocketHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        try:
            while True:
                try:
                    payload = await websocket.receive_json()
                except ValueError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if str(payload.get("type", "")).strip().lower() == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            return None
        finally:
            self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, object]) -> None:
        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(payload)
            except (RuntimeError, WebSocketDisconnect):
                self._connections.discard(websocket)
