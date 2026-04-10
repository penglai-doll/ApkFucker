from __future__ import annotations

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


class WebSocketHub:
    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                payload = await websocket.receive_json()
                if str(payload.get("type", "")).strip().lower() == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            return None
