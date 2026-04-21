from __future__ import annotations

import asyncio
from contextlib import suppress
from queue import Empty
from queue import Queue

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


class WebSocketHub:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, Queue[dict[str, object]]] = {}

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        outbound_queue: Queue[dict[str, object]] = Queue()
        self._connections[websocket] = outbound_queue
        try:
            while True:
                receive_task = asyncio.create_task(websocket.receive_json())
                send_task = asyncio.create_task(asyncio.to_thread(self._poll_payload, outbound_queue))
                done, pending = await asyncio.wait(
                    {receive_task, send_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

                if send_task in done:
                    payload = send_task.result()
                    if payload is not None:
                        await websocket.send_json(payload)
                    continue

                try:
                    payload = receive_task.result()
                except ValueError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if str(payload.get("type", "")).strip().lower() == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            return None
        finally:
            self._connections.pop(websocket, None)

    async def broadcast(self, payload: dict[str, object]) -> None:
        self.broadcast_nowait(payload)

    def broadcast_nowait(self, payload: dict[str, object]) -> None:
        for websocket, outbound_queue in tuple(self._connections.items()):
            try:
                outbound_queue.put_nowait(payload)
            except RuntimeError:
                self._connections.pop(websocket, None)

    @staticmethod
    def _poll_payload(outbound_queue: Queue[dict[str, object]]) -> dict[str, object] | None:
        try:
            return outbound_queue.get(timeout=0.1)
        except Empty:
            return None
