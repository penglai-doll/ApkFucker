from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket

from apk_hacker.interfaces.api_fastapi.routes_cases import build_cases_router
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def build_app(*, workspace_root: Path | None = None) -> FastAPI:
    root = _repo_root()
    resolved_workspace_root = workspace_root.expanduser() if workspace_root is not None else root / "cache" / "api" / "workspaces"
    hub = WebSocketHub()

    app = FastAPI(title="APKHacker Local API")
    app.include_router(build_cases_router(workspace_root=resolved_workspace_root))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    return app
