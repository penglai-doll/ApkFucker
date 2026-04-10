from __future__ import annotations

from fastapi import FastAPI, WebSocket

from apk_hacker.interfaces.api_fastapi.routes_cases import build_cases_router
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub

def build_app() -> FastAPI:
    hub = WebSocketHub()

    app = FastAPI(
        title="APKHacker Local API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(build_cases_router())

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    return app
