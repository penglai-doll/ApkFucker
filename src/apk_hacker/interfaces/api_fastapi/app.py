from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket

from apk_hacker.interfaces.api_fastapi.routes_cases import build_cases_router
from apk_hacker.interfaces.api_fastapi.routes_execution import build_execution_router
from apk_hacker.interfaces.api_fastapi.routes_reports import build_reports_router
from apk_hacker.interfaces.api_fastapi.routes_settings import build_settings_router
from apk_hacker.interfaces.api_fastapi.routes_workspace import build_workspace_router
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _resolve_path(value: Path | None, fallback: Path) -> Path:
    return value.expanduser() if value is not None else fallback


def build_app(
    *,
    workspace_root: Path | None = None,
    db_root: Path | None = None,
    scripts_root: Path | None = None,
    websocket_hub: WebSocketHub | None = None,
) -> FastAPI:
    root = _repo_root()
    resolved_workspace_root = _resolve_path(workspace_root, root / "cache" / "api" / "workspaces")
    resolved_db_root = _resolve_path(db_root, root / "cache" / "api")
    resolved_scripts_root = _resolve_path(scripts_root, root / "user_data" / "frida_plugins" / "custom")
    hub = websocket_hub or WebSocketHub()

    app = FastAPI(title="APKHacker Local API")
    app.state.workspace_root = resolved_workspace_root
    app.state.db_root = resolved_db_root
    app.state.scripts_root = resolved_scripts_root
    app.state.websocket_hub = hub

    app.include_router(build_cases_router(workspace_root=resolved_workspace_root, db_root=resolved_db_root))
    app.include_router(build_workspace_router(workspace_root=resolved_workspace_root))
    app.include_router(build_execution_router(workspace_root=resolved_workspace_root))
    app.include_router(build_reports_router(workspace_root=resolved_workspace_root, db_root=resolved_db_root))
    app.include_router(build_settings_router(db_root=resolved_db_root))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    return app
